"""
Trading Imperium V6 – DXY (Dollar Index) Filter
Wenn DXY steigt -> Krypto faellt meistens. Bot haelt sich zurueck.
"""
import time
import threading
from typing import Dict
from core.logger import log

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False


class DXYFilter:
    """Ueberwacht den US Dollar Index als Gegenindikator."""

    def __init__(self, cache_minutes=30):
        self.cache_minutes = cache_minutes
        self.current_dxy = 0
        self.dxy_change_pct = 0
        self.trend = "NEUTRAL"
        self._cache_time = 0
        self._history = []

    def fetch(self) -> Dict:
        """Holt DXY-Daten."""
        if (time.time() - self._cache_time) < self.cache_minutes * 60 and self.current_dxy > 0:
            return self._result()

        if not HAS_REQ:
            return self._result()

        try:
            # DXY ueber freien Proxy (exchangerate.host oder aehnlich)
            # Fallback: EURUSD invertieren als DXY-Proxy
            r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=EUR,JPY,GBP,CHF", timeout=10)
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                if rates:
                    # DXY ist gewichteter Korb: EUR 57.6%, JPY 13.6%, GBP 11.9%, etc.
                    eur = 1 / rates.get("EUR", 1)
                    jpy = rates.get("JPY", 110) / 110
                    gbp = 1 / rates.get("GBP", 1)
                    dxy_approx = (eur ** 0.576) * (jpy ** 0.136) * (gbp ** 0.119) * 100
                    self.current_dxy = round(dxy_approx, 2)
        except Exception:
            pass

        # Fallback: CoinGecko BTC-Korrelation nutzen
        if self.current_dxy == 0:
            try:
                r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=eur", timeout=10)
                if r.status_code == 200:
                    eur_rate = r.json().get("tether", {}).get("eur", 0.92)
                    self.current_dxy = round((1 / eur_rate) * 100, 2) if eur_rate > 0 else 100
            except Exception:
                self.current_dxy = 100

        # Trend bestimmen
        self._history.append(self.current_dxy)
        if len(self._history) > 48:
            self._history = self._history[-48:]
        if len(self._history) >= 2:
            self.dxy_change_pct = ((self._history[-1] / self._history[0]) - 1) * 100

        if self.dxy_change_pct > 0.3:
            self.trend = "RISING"  # DXY steigt -> schlecht fuer Krypto
        elif self.dxy_change_pct < -0.3:
            self.trend = "FALLING"  # DXY faellt -> gut fuer Krypto
        else:
            self.trend = "NEUTRAL"

        self._cache_time = time.time()
        if self.trend == "RISING":
            log.info("DXY", f"DXY {self.current_dxy:.2f} STEIGT ({self.dxy_change_pct:+.2f}%) -> Vorsicht!")

        return self._result()

    def _result(self):
        return {"dxy": self.current_dxy, "change_pct": round(self.dxy_change_pct, 2),
                "trend": self.trend}

    def should_reduce_exposure(self) -> bool:
        """Bei steigendem DXY: Exposure reduzieren."""
        return self.trend == "RISING" and self.dxy_change_pct > 0.5

    def get_score_modifier(self) -> float:
        """Score-Modifier: -0.2 bei steigendem DXY, +0.1 bei fallendem."""
        if self.trend == "RISING": return -0.2
        elif self.trend == "FALLING": return 0.1
        return 0

    def get_status(self):
        return {"dxy": self.current_dxy, "trend": self.trend,
                "change_pct": round(self.dxy_change_pct, 2),
                "reduce_exposure": self.should_reduce_exposure()}
