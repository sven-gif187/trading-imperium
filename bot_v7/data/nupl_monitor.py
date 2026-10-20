"""
Trading Imperium V6 – NUPL Monitor (Net Unrealized Profit/Loss)
Holt NUPL-Daten und blockiert Kaeufe bei Euphorie (NUPL > 0.7).
Quellen: glassnode-freie Approximation via Marktdaten.
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


class NUPLMonitor:
    """
    NUPL = (Market Cap - Realized Cap) / Market Cap
    Approximation ohne Glassnode-API:
    - Nutzt BTC Preis vs 200-Tage-Durchschnitt als Proxy
    - NUPL > 0.7 = Euphorie (KEINE Kaeufe!)
    - NUPL 0.5-0.7 = Gier
    - NUPL 0.25-0.5 = Optimismus
    - NUPL 0-0.25 = Hoffnung
    - NUPL < 0 = Kapitulation (KAUFEN!)
    """

    ZONES = {
        "EUPHORIE": {"min": 0.7, "max": 1.0, "color": "#ff0000", "action": "KEINE KAEUFE"},
        "GIER": {"min": 0.5, "max": 0.7, "color": "#ff6600", "action": "Vorsicht"},
        "OPTIMISMUS": {"min": 0.25, "max": 0.5, "color": "#ffcc00", "action": "Normal"},
        "HOFFNUNG": {"min": 0.0, "max": 0.25, "color": "#00cc00", "action": "Kaufen"},
        "KAPITULATION": {"min": -1.0, "max": 0.0, "color": "#00ff88", "action": "STARK KAUFEN"},
    }

    def __init__(self, cache_minutes=60):
        self.cache_minutes = cache_minutes
        self.current_nupl = 0.3
        self.current_zone = "HOFFNUNG"
        self._cache_time = 0
        self._sma200 = 0

    def calculate(self, btc_price, price_history_200d=None) -> Dict:
        """Berechnet NUPL-Approximation."""
        now = time.time()
        if (now - self._cache_time) < self.cache_minutes * 60 and self._sma200 > 0:
            # Nur Preis updaten, SMA200 bleibt
            pass
        elif price_history_200d and len(price_history_200d) >= 50:
            self._sma200 = sum(price_history_200d[-200:]) / min(len(price_history_200d), 200)
            self._cache_time = now
        elif self._sma200 == 0:
            # Fallback: Schaetze SMA200 als 80% des aktuellen Preises
            self._sma200 = btc_price * 0.80

        if self._sma200 <= 0 or btc_price <= 0:
            return {"nupl": 0.3, "zone": "HOFFNUNG", "action": "Normal"}

        # NUPL Approximation: (Preis - SMA200) / Preis
        nupl = (btc_price - self._sma200) / btc_price
        nupl = max(-1.0, min(1.0, nupl))

        # Zone bestimmen
        zone = "HOFFNUNG"
        action = "Normal"
        for z_name, z_data in self.ZONES.items():
            if z_data["min"] <= nupl < z_data["max"]:
                zone = z_name
                action = z_data["action"]
                break

        self.current_nupl = round(nupl, 3)
        self.current_zone = zone

        return {
            "nupl": self.current_nupl,
            "zone": zone,
            "action": action,
            "sma200": round(self._sma200, 2),
            "btc_price": btc_price,
            "buy_blocked": nupl > 0.7,
        }

    def should_block_buys(self) -> bool:
        """True wenn NUPL > 0.7 (Euphorie)."""
        return self.current_nupl > 0.7

    def get_buy_multiplier(self) -> float:
        """Kaufmenge-Multiplikator basierend auf NUPL."""
        if self.current_nupl < -0.2:
            return 2.0  # Kapitulation: doppelt kaufen
        elif self.current_nupl < 0:
            return 1.5
        elif self.current_nupl < 0.25:
            return 1.2
        elif self.current_nupl < 0.5:
            return 1.0
        elif self.current_nupl < 0.7:
            return 0.5  # Gier: halbe Position
        else:
            return 0.0  # Euphorie: nicht kaufen

    def get_status(self):
        return {"nupl": self.current_nupl, "zone": self.current_zone,
                "sma200": round(self._sma200, 2), "buy_blocked": self.should_block_buys()}
