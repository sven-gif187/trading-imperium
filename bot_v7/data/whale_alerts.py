"""
Trading Imperium V5 – Whale Alert Integration
Ueberwacht grosse On-Chain Transaktionen.
Grosse BTC-Transfers zu Boersen = Verkaufsdruck (bearisch)
Grosse BTC-Transfers von Boersen = Akkumulation (bullisch)
"""
import time
import threading
from typing import Dict, List
from core.logger import log

try:
    import requests
except ImportError:
    requests = None

# Bekannte Exchange-Adressen (vereinfacht)
EXCHANGE_KEYWORDS = ["binance", "coinbase", "kraken", "bitfinex", "huobi",
                     "okx", "bybit", "kucoin", "bitstamp", "gemini"]


class WhaleAlertProvider:
    """Ueberwacht grosse Krypto-Transaktionen."""

    # Kostenlose Alternative: blockchain.info fuer BTC
    BTC_API = "https://blockchain.info/unconfirmed-transactions?format=json"
    # Whale Alert API (kostenlos mit Limit)
    WHALE_API = "https://api.whale-alert.io/v1/transactions"

    def __init__(self, api_key="", min_value_usd=500000, cache_minutes=10):
        self.api_key = api_key
        self.min_value_usd = min_value_usd
        self.cache_minutes = cache_minutes
        self._cache = []
        self._cache_time = 0
        self._lock = threading.Lock()

    def fetch_alerts(self) -> List[Dict]:
        """Holt grosse Transaktionen."""
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache

        alerts = []
        if not requests:
            return alerts

        # Methode 1: Whale Alert API (wenn Key vorhanden)
        if self.api_key:
            alerts = self._fetch_whale_alert()

        # Methode 2: Blockchain.info (kostenlos, nur BTC)
        if not alerts:
            alerts = self._fetch_blockchain_info()

        with self._lock:
            self._cache = alerts
            self._cache_time = time.time()

        return alerts

    def _fetch_whale_alert(self) -> List[Dict]:
        """Whale Alert API (benoetigt kostenlosen API-Key)."""
        alerts = []
        try:
            params = {
                "api_key": self.api_key,
                "min_value": self.min_value_usd,
                "start": int(time.time()) - 3600,  # Letzte Stunde
                "cursor": "",
            }
            r = requests.get(self.WHALE_API, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for tx in data.get("transactions", [])[:20]:
                    alert = {
                        "hash": tx.get("hash", "")[:16],
                        "blockchain": tx.get("blockchain", "bitcoin"),
                        "symbol": tx.get("symbol", "BTC").upper(),
                        "amount": tx.get("amount", 0),
                        "amount_usd": tx.get("amount_usd", 0),
                        "from": tx.get("from", {}).get("owner", "unknown"),
                        "to": tx.get("to", {}).get("owner", "unknown"),
                        "from_type": tx.get("from", {}).get("owner_type", "unknown"),
                        "to_type": tx.get("to", {}).get("owner_type", "unknown"),
                        "time": tx.get("timestamp", 0),
                    }
                    # Klassifizieren
                    alert["direction"] = self._classify_direction(alert)
                    alerts.append(alert)
                log.info("WHALE", f"Whale Alert: {len(alerts)} Transaktionen")
        except Exception as e:
            log.warn("WHALE", f"API Fehler: {str(e)[:40]}")
        return alerts

    def _fetch_blockchain_info(self) -> List[Dict]:
        """Blockchain.info fuer grosse BTC-Transaktionen (kostenlos)."""
        alerts = []
        try:
            r = requests.get(self.BTC_API, timeout=10)
            if r.status_code == 200:
                data = r.json()
                txs = data.get("txs", [])
                for tx in txs:
                    total_out = sum(o.get("value", 0) for o in tx.get("out", []))
                    total_btc = total_out / 1e8
                    # Nur grosse Transaktionen (>5 BTC)
                    if total_btc > 5:
                        alerts.append({
                            "hash": tx.get("hash", "")[:16],
                            "blockchain": "bitcoin",
                            "symbol": "BTC",
                            "amount": round(total_btc, 4),
                            "amount_usd": 0,  # Kein USD-Wert in dieser API
                            "from": "unknown",
                            "to": "unknown",
                            "direction": "unknown",
                            "time": tx.get("time", 0),
                        })
                alerts = sorted(alerts, key=lambda x: x["amount"], reverse=True)[:15]
                log.info("WHALE", f"Blockchain.info: {len(alerts)} grosse BTC-TXs")
        except Exception as e:
            log.warn("WHALE", f"Blockchain.info: {str(e)[:40]}")
        return alerts

    def _classify_direction(self, alert) -> str:
        """Klassifiziert ob Transfer bullisch oder bearisch ist."""
        from_ex = any(kw in alert.get("from", "").lower() for kw in EXCHANGE_KEYWORDS)
        to_ex = any(kw in alert.get("to", "").lower() for kw in EXCHANGE_KEYWORDS)
        from_type = alert.get("from_type", "")
        to_type = alert.get("to_type", "")

        if to_ex or to_type == "exchange":
            return "TO_EXCHANGE"  # Bearisch: will verkaufen
        elif from_ex or from_type == "exchange":
            return "FROM_EXCHANGE"  # Bullisch: zieht ab, will halten
        return "UNKNOWN"

    def get_signal(self) -> Dict:
        """
        Berechnet Whale-Signal.
        Viele Transfers ZU Boersen = bearisch (Verkaufsdruck)
        Viele Transfers VON Boersen = bullisch (Akkumulation)
        """
        alerts = self.fetch_alerts()
        if not alerts:
            return {"score": 0.5, "label": "NEUTRAL", "details": "Keine Whale-Daten"}

        to_exchange = sum(1 for a in alerts if a.get("direction") == "TO_EXCHANGE")
        from_exchange = sum(1 for a in alerts if a.get("direction") == "FROM_EXCHANGE")
        total = to_exchange + from_exchange

        if total == 0:
            return {"score": 0.5, "label": "NEUTRAL",
                    "details": f"{len(alerts)} Whales, keine Exchange-Transfers"}

        from_ratio = from_exchange / total
        if from_ratio > 0.6:
            score = 0.7
            label = "BULLISH"
        elif from_ratio < 0.4:
            score = 0.3
            label = "BEARISH"
        else:
            score = 0.5
            label = "NEUTRAL"

        details = (f"{len(alerts)} Whales: {to_exchange} zur Boerse (sell), "
                  f"{from_exchange} von Boerse (hodl)")

        return {
            "score": round(score, 2),
            "label": label,
            "to_exchange": to_exchange,
            "from_exchange": from_exchange,
            "total_alerts": len(alerts),
            "details": details,
        }

    def get_largest(self, n=5) -> List[Dict]:
        """Die N groessten Transaktionen."""
        alerts = self.fetch_alerts()
        return sorted(alerts, key=lambda x: x.get("amount", 0), reverse=True)[:n]

    def get_status(self):
        return {
            "cached_alerts": len(self._cache),
            "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1,
            "has_api_key": bool(self.api_key),
        }
