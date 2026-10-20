"""
Trading Imperium V5 – Funding Rate Monitor
Holt Binance Futures Funding Rates als Sentiment-Signal.
Hohe positive Rate = Markt ueberhitzt (Long-heavy) → vorsichtig
Hohe negative Rate = Markt ueberverkauft (Short-heavy) → Kaufgelegenheit
"""
import time
import threading
from typing import Dict, List
from core.logger import log

try:
    import requests
except ImportError:
    requests = None


class FundingRateMonitor:
    """Ueberwacht Binance Futures Funding Rates."""

    BINANCE_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
               "AVAXUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"]

    def __init__(self, cache_minutes=15):
        self.cache_minutes = cache_minutes
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()

    def fetch_rates(self) -> Dict[str, float]:
        """Holt aktuelle Funding Rates fuer alle Coins."""
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache

        rates = {}
        if not requests:
            log.warn("FUNDING", "requests nicht installiert")
            return rates

        for symbol in self.SYMBOLS:
            try:
                params = {"symbol": symbol, "limit": 1}
                r = requests.get(self.BINANCE_URL, params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        rate = float(data[-1].get("fundingRate", 0))
                        rates[symbol.replace("USDT", "")] = round(rate * 100, 4)  # In Prozent
            except Exception as e:
                log.warn("FUNDING", f"{symbol}: {str(e)[:30]}")
            time.sleep(0.2)  # Rate-Limit

        if rates:
            log.info("FUNDING", f"Rates geladen: {len(rates)} Coins")

        with self._lock:
            self._cache = rates
            self._cache_time = time.time()

        return rates

    def get_signal(self) -> Dict:
        """
        Berechnet Gesamt-Signal aus Funding Rates.
        Returns: {"score": 0-1, "label": str, "btc_rate": float, "avg_rate": float}
        """
        rates = self.fetch_rates()
        if not rates:
            return {"score": 0.5, "label": "NEUTRAL", "btc_rate": 0, "avg_rate": 0,
                    "details": "Keine Daten"}

        btc_rate = rates.get("BTC", 0)
        avg_rate = sum(rates.values()) / len(rates)

        # Interpretation:
        # Stark positiv (>0.03%) = ueberhitzt, Longs zahlen → BEARISH Signal
        # Stark negativ (<-0.01%) = ueberverkauft, Shorts zahlen → BULLISH Signal
        # Normal (0.01%) = neutral

        if avg_rate > 0.05:
            score = 0.2  # Sehr ueberhitzt → bearish
            label = "OVERHEATED"
        elif avg_rate > 0.03:
            score = 0.35  # Ueberhitzt
            label = "HIGH"
        elif avg_rate > 0.01:
            score = 0.5  # Normal
            label = "NEUTRAL"
        elif avg_rate > -0.01:
            score = 0.55
            label = "NEUTRAL"
        elif avg_rate > -0.03:
            score = 0.65  # Leicht ueberverkauft → bullish
            label = "LOW"
        else:
            score = 0.8  # Stark ueberverkauft → sehr bullish
            label = "OVERSOLD"

        details = f"BTC: {btc_rate:+.4f}% | Avg: {avg_rate:+.4f}% | {label}"
        log.info("FUNDING", details)

        return {
            "score": round(score, 2),
            "label": label,
            "btc_rate": btc_rate,
            "avg_rate": round(avg_rate, 4),
            "rates": rates,
            "details": details,
        }

    def is_overheated(self) -> bool:
        """Ist der Markt ueberhitzt? (Funding Rate zu hoch)"""
        signal = self.get_signal()
        return signal.get("label") in ("OVERHEATED", "HIGH")

    def is_oversold(self) -> bool:
        """Ist der Markt ueberverkauft? (Funding Rate negativ)"""
        signal = self.get_signal()
        return signal.get("label") in ("OVERSOLD", "LOW")

    def get_status(self):
        return {
            "cached_rates": len(self._cache),
            "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1,
            "btc_rate": self._cache.get("BTC", "?"),
        }
