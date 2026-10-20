"""
Trading Imperium V5 – Capitol Trades
Holt Politician-Trades von capitoltrades.com.
Politiker handeln oft mit Insiderwissen – deren Trades als Signal nutzen.
"""
import time
import json
import threading
from typing import Dict, List, Optional
from core.logger import log

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


# Top-Politiker zum Tracken
TOP_POLITICIANS = [
    {"name": "Nancy Pelosi", "id": "P000197"},
    {"name": "Dan Crenshaw", "id": "C001120"},
    {"name": "Tommy Tuberville", "id": "T000278"},
    {"name": "Josh Gottheimer", "id": "G000583"},
    {"name": "Mark Green", "id": "G000590"},
    {"name": "Michael McCaul", "id": "M001157"},
]

# Crypto-relevante Unternehmen (Aktien die mit Krypto korrelieren)
CRYPTO_RELATED = {
    "COIN": "Coinbase",
    "MSTR": "MicroStrategy",
    "MARA": "Marathon Digital",
    "RIOT": "Riot Platforms",
    "CLSK": "CleanSpark",
    "SQ": "Block/Square",
    "PYPL": "PayPal",
    "NVDA": "NVIDIA",
    "AMD": "AMD",
    "TSM": "TSMC",
}


class CapitolTradesProvider:
    """Holt und analysiert Politiker-Trades."""

    BASE_URL = "https://www.capitoltrades.com"

    def __init__(self, cache_minutes=60):
        self.cache_minutes = cache_minutes
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()

    def fetch_recent_trades(self, days=90) -> List[Dict]:
        """Holt die neuesten Politiker-Trades."""
        with self._lock:
            if self._cache.get("trades") and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache["trades"]

        trades = []

        if not requests:
            log.warn("CAPITOL", "requests nicht installiert")
            return trades

        try:
            url = f"{self.BASE_URL}/trades?txDate={days}d"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code == 200 and BeautifulSoup:
                soup = BeautifulSoup(r.text, "html.parser")
                # Versuche Tabellen-Rows zu finden
                rows = soup.select("table tbody tr") or soup.select(".trade-row") or []

                for row in rows[:50]:
                    try:
                        cells = row.find_all("td") or row.find_all("div")
                        if len(cells) >= 4:
                            trade = {
                                "politician": cells[0].get_text(strip=True) if len(cells) > 0 else "",
                                "ticker": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                                "type": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                "size": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                                "date": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                                "source": "capitoltrades.com",
                            }
                            if trade["ticker"]:
                                trades.append(trade)
                    except Exception:
                        continue

                log.info("CAPITOL", f"Gescrapt: {len(trades)} Trades von {len(rows)} Rows")

            elif r.status_code == 200:
                # Fallback ohne BeautifulSoup: JSON-Daten suchen
                try:
                    # Manche Seiten liefern JSON in Script-Tags
                    text = r.text
                    if '"trades"' in text or '"data"' in text:
                        # Versuche JSON zu extrahieren
                        import re
                        json_match = re.search(r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*</script>', text)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            log.info("CAPITOL", f"JSON-Daten gefunden")
                except Exception:
                    pass

                log.info("CAPITOL", f"Seite geladen (Status {r.status_code}), {len(trades)} Trades extrahiert")

        except Exception as e:
            log.warn("CAPITOL", f"Fehler: {str(e)[:60]}")

        # Fallback: Quiver Quantitative API (kostenlos, limitiert)
        if not trades:
            trades = self._fetch_quiver_fallback()

        with self._lock:
            self._cache = {"trades": trades}
            self._cache_time = time.time()

        return trades

    def _fetch_quiver_fallback(self) -> List[Dict]:
        """Fallback: Quiver Quantitative fuer Kongress-Trades."""
        trades = []
        try:
            url = "https://api.quiverquant.com/beta/live/congresstrading"
            headers = {"Accept": "application/json"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data[:30]:
                    trades.append({
                        "politician": item.get("Representative", ""),
                        "ticker": item.get("Ticker", ""),
                        "type": item.get("Transaction", ""),
                        "size": item.get("Range", ""),
                        "date": item.get("TransactionDate", ""),
                        "source": "quiverquant",
                    })
                log.info("CAPITOL", f"Quiver Fallback: {len(trades)} Trades")
        except Exception as e:
            log.warn("CAPITOL", f"Quiver Fallback Fehler: {str(e)[:40]}")
        return trades

    def get_crypto_relevant_trades(self) -> List[Dict]:
        """Filtert nur Trades die fuer Crypto relevant sind."""
        all_trades = self.fetch_recent_trades()
        relevant = []
        for t in all_trades:
            ticker = t.get("ticker", "").upper()
            if ticker in CRYPTO_RELATED:
                t["crypto_relevance"] = CRYPTO_RELATED[ticker]
                relevant.append(t)
        return relevant

    def get_signal(self) -> Dict:
        """
        Berechnet ein Trading-Signal aus Politiker-Trades.
        Returns: {"score": 0.0-1.0, "label": str, "details": str}
        """
        trades = self.fetch_recent_trades()
        crypto_trades = self.get_crypto_relevant_trades()

        if not trades:
            return {"score": 0.5, "label": "NEUTRAL", "details": "Keine Daten verfuegbar"}

        # Zaehle Kaufe vs Verkaeufe in Crypto-Aktien
        buys = sum(1 for t in crypto_trades if "buy" in t.get("type", "").lower()
                   or "purchase" in t.get("type", "").lower())
        sells = sum(1 for t in crypto_trades if "sell" in t.get("type", "").lower()
                    or "sale" in t.get("type", "").lower())

        total = buys + sells
        if total == 0:
            return {"score": 0.5, "label": "NEUTRAL",
                    "details": f"{len(trades)} Trades, keine Crypto-relevanten"}

        buy_ratio = buys / total
        if buy_ratio > 0.65:
            label = "BULLISH"
            score = 0.7 + (buy_ratio - 0.65) * 0.5
        elif buy_ratio < 0.35:
            label = "BEARISH"
            score = 0.3 - (0.35 - buy_ratio) * 0.5
        else:
            label = "NEUTRAL"
            score = 0.5

        details = (f"{len(trades)} Trades gesamt, {len(crypto_trades)} Crypto-relevant. "
                  f"Kaufe: {buys}, Verkaeufe: {sells} ({buy_ratio:.0%} buy)")

        log.info("CAPITOL", f"Signal: {label} ({score:.2f}) – {details}")

        return {
            "score": round(max(0, min(1, score)), 2),
            "label": label,
            "buys": buys,
            "sells": sells,
            "crypto_trades": len(crypto_trades),
            "total_trades": len(trades),
            "details": details,
        }

    def get_top_politician_trades(self, politician_name=None) -> List[Dict]:
        """Trades eines bestimmten Politikers oder aller Top-Politiker."""
        trades = self.fetch_recent_trades()
        if politician_name:
            return [t for t in trades if politician_name.lower() in t.get("politician", "").lower()]
        # Top-Politiker filtern
        top_names = [p["name"].lower() for p in TOP_POLITICIANS]
        return [t for t in trades if any(n in t.get("politician", "").lower() for n in top_names)]

    def format_summary(self) -> str:
        """Zusammenfassung fuer UI oder Telegram."""
        signal = self.get_signal()
        crypto = self.get_crypto_relevant_trades()

        lines = [f"🏛️ CAPITOL TRADES",
                 f"Signal: {signal['label']} ({signal['score']:.2f})",
                 f"Trades: {signal['total_trades']} gesamt, {signal['crypto_trades']} Crypto-relevant"]

        if crypto:
            lines.append(f"Crypto-Trades:")
            for t in crypto[:5]:
                lines.append(f"  {t['politician']}: {t['type']} {t['ticker']} ({t.get('crypto_relevance', '')})")

        return "\n".join(lines)

    def get_status(self):
        return {
            "cached_trades": len(self._cache.get("trades", [])),
            "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1,
            "top_politicians": [p["name"] for p in TOP_POLITICIANS],
            "crypto_tickers": list(CRYPTO_RELATED.keys()),
        }
