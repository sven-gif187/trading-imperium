"""
Trading Imperium V6 – DXY (Dollar Index) Monitor
Wenn DXY steigt -> Crypto faellt. Bot haelt sich zurueck.
"""
import time
from typing import Dict
from core.logger import log

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False


class DXYMonitor:
    """
    Ueberwacht den US Dollar Index (DXY).
    DXY steigt = Dollar staerker = Crypto schwaecher
    DXY faellt = Dollar schwaecher = Crypto staerker
    """

    def __init__(self, cache_minutes=60):
        self.cache_minutes = cache_minutes
        self.current_dxy = 0
        self.dxy_change_24h = 0
        self.trend = "NEUTRAL"  # RISING, FALLING, NEUTRAL
        self._cache_time = 0
        self._history = []

    def fetch(self) -> Dict:
        """Holt DXY-Daten (ueber Proxy-API oder ccxt)."""
        now = time.time()
        if (now - self._cache_time) < self.cache_minutes * 60 and self.current_dxy > 0:
            return self.get_status()

        if not HAS_REQ:
            return self.get_status()

        # Methode 1: Yahoo Finance Proxy
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=5d"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in closes if c is not None]
                if closes:
                    self.current_dxy = round(closes[-1], 2)
                    if len(closes) >= 2:
                        self.dxy_change_24h = round(((closes[-1] / closes[-2]) - 1) * 100, 2)
                    self._history.append(self.current_dxy)
                    if len(self._history) > 30:
                        self._history = self._history[-30:]
                    self._update_trend()
                    self._cache_time = now
                    log.info("DXY", f"DXY: {self.current_dxy} ({self.dxy_change_24h:+.2f}%) -> {self.trend}")
        except Exception as e:
            log.warn("DXY", f"Fetch Fehler: {str(e)[:40]}")

        return self.get_status()

    def _update_trend(self):
        if len(self._history) < 3:
            self.trend = "NEUTRAL"
            return
        recent = self._history[-3:]
        if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            self.trend = "RISING"  # DXY steigt = schlecht fuer Crypto
        elif all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            self.trend = "FALLING"  # DXY faellt = gut fuer Crypto
        else:
            self.trend = "NEUTRAL"

    def should_reduce_exposure(self) -> bool:
        """True wenn DXY stark steigt (schlecht fuer Crypto)."""
        return self.trend == "RISING" and self.dxy_change_24h > 0.3

    def get_buy_multiplier(self) -> float:
        """Position-Multiplikator basierend auf DXY."""
        if self.trend == "RISING" and self.dxy_change_24h > 0.5:
            return 0.5  # Halbe Position bei starkem DXY
        elif self.trend == "RISING":
            return 0.75
        elif self.trend == "FALLING" and self.dxy_change_24h < -0.3:
            return 1.3  # Mehr kaufen bei fallendem DXY
        return 1.0

    def get_status(self):
        return {"dxy": self.current_dxy, "change_24h": self.dxy_change_24h,
                "trend": self.trend, "reduce_exposure": self.should_reduce_exposure(),
                "buy_multiplier": self.get_buy_multiplier()}
