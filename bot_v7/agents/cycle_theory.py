"""
Trading Imperium V5 – Zyklustheorie
BTC 4-Jahres-Zyklus Erkennung. Bestimmt die aktuelle Phase
und passt Trading-Verhalten entsprechend an.
"""
from datetime import datetime, timezone
from typing import Dict
from core.logger import log


# BTC Halving-Daten
HALVINGS = [
    datetime(2012, 11, 28, tzinfo=timezone.utc),
    datetime(2016, 7, 9, tzinfo=timezone.utc),
    datetime(2020, 5, 11, tzinfo=timezone.utc),
    datetime(2024, 4, 20, tzinfo=timezone.utc),
    datetime(2028, 4, 15, tzinfo=timezone.utc),  # Geschätzt
]

# Historische ATHs
ATH_HISTORY = {
    "2013": 1_150,
    "2017": 19_783,
    "2021": 69_045,
    "2025": 109_114,  # Aktuelles Zyklus-ATH (Stand März 2026)
}

# [PATCH 63, ab 28.08.2026] Das Allzeithoch wird geholt, nicht gepflegt.
#
# Vorher stand hier fest 109_114 (Stand 20.01.2025). Am 20.08.2026 lag das
# echte Hoch bei 126.200 $ (06.10.2025, geprueft gegen Binance USDT, Binance
# USDC und Bybit). Der Bot hielt den Baerenmarkt dadurch fuer 9 Prozentpunkte
# flacher als er war - EARLY_BEAR statt MID_BEAR, und damit 20 % groessere
# Positionen (get_position_multiplier: 0.6 statt 0.5).
#
# Rueckfall ist bewusst der HOECHSTE bekannte Wert, nie ein niedrigerer:
# ein zu niedriges Hoch macht den Baerenmarkt kuenstlich flach.
_ATH_RUECKFALL = 126_200
_ATH_PUFFER = {"wert": None, "datum": None}


def _ath_ermitteln():
    """Hoechster Kurs, den die Boerse kennt. Einmal je Bot-Start."""
    if _ATH_PUFFER["wert"]:
        return _ATH_PUFFER["wert"], _ATH_PUFFER["datum"]
    hoch, datum = _ATH_RUECKFALL, "Rueckfall"
    try:
        import ccxt
        from datetime import datetime, timezone
        ex = ccxt.binance({"enableRateLimit": True})
        k = ex.fetch_ohlcv("BTC/USDT", "1w", limit=400)
        if k:
            h = max(x[2] for x in k)
            if h > hoch:                     # nie nach unten korrigieren
                w = [x for x in k if x[2] == h][0][0]
                hoch = h
                datum = datetime.fromtimestamp(
                    w / 1000, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    _ATH_PUFFER["wert"], _ATH_PUFFER["datum"] = hoch, datum
    return hoch, datum


CURRENT_ATH, CURRENT_ATH_DATE = _ath_ermitteln()


class CycleTheory:
    """BTC 4-Jahres-Zyklus Analyse."""

    def __init__(self):
        self.current_phase = "UNKNOWN"
        self.days_since_halving = 0
        self.pct_from_ath = 0
        self.cycle_progress = 0
        self.update()

    def update(self, btc_price: float = 0) -> str:
        """Aktualisiert die Zyklusphase basierend auf Zeit und Preis."""
        now = datetime.now(timezone.utc)

        # Letztes Halving finden
        last_halving = HALVINGS[0]
        next_halving = HALVINGS[-1]
        for i, h in enumerate(HALVINGS):
            if h <= now:
                last_halving = h
                if i + 1 < len(HALVINGS):
                    next_halving = HALVINGS[i + 1]

        self.days_since_halving = (now - last_halving).days
        cycle_length = (next_halving - last_halving).days
        self.cycle_progress = round((self.days_since_halving / cycle_length) * 100, 1) if cycle_length > 0 else 0

        # ATH-Abstand
        if btc_price > 0:
            self.pct_from_ath = round(((btc_price / CURRENT_ATH) - 1) * 100, 1)
        else:
            self.pct_from_ath = -40  # Default

        # Phase bestimmen
        self.current_phase = self._determine_phase()
        return self.current_phase

    def _determine_phase(self) -> str:
        """Bestimmt die Zyklusphase anhand von Zeit + Preis."""
        days = self.days_since_halving
        pct = self.pct_from_ath

        # Zeitbasiert (Tage seit Halving)
        if days < 180:
            time_phase = "POST_HALVING"
        elif days < 365:
            time_phase = "BULL_EARLY"
        elif days < 550:
            time_phase = "BULL_PEAK"
        elif days < 730:
            time_phase = "DISTRIBUTION"
        elif days < 1000:
            time_phase = "BEAR"
        elif days < 1200:
            time_phase = "DEEP_BEAR"
        else:
            time_phase = "ACCUMULATION"

        # Preisbasiert (Abstand vom ATH)
        if pct > -5:
            price_phase = "EUPHORIA"
        elif pct > -20:
            price_phase = "DISTRIBUTION"
        elif pct > -35:
            price_phase = "EARLY_BEAR"
        elif pct > -50:
            price_phase = "MID_BEAR"
        elif pct > -70:
            price_phase = "DEEP_BEAR"
        elif pct > -80:
            price_phase = "CAPITULATION"
        else:
            price_phase = "ACCUMULATION"

        # Kombiniert: Preis wiegt schwerer als Zeit
        # Wenn beides übereinstimmt -> klar
        # Wenn nicht -> Preis gewinnt
        phase_priority = {
            "CAPITULATION": 0, "DEEP_BEAR": 1, "MID_BEAR": 2,
            "EARLY_BEAR": 3, "ACCUMULATION": 4, "DISTRIBUTION": 5,
            "EUPHORIA": 6, "POST_HALVING": 4, "BULL_EARLY": 5,
            "BULL_PEAK": 6, "BEAR": 2,
        }

        # Normalisiere auf Standard-Phasen
        phase_map = {
            "POST_HALVING": "ACCUMULATION", "BULL_EARLY": "ACCUMULATION",
            "BULL_PEAK": "DISTRIBUTION", "BEAR": "MID_BEAR",
        }
        final = price_phase
        if final in phase_map:
            final = phase_map[final]

        return final

    def get_trading_mode(self) -> str:
        """Gibt den empfohlenen Trading-Modus zurück."""
        modes = {
            "EUPHORIA": "PROFIT_TAKING",
            "DISTRIBUTION": "CAUTIOUS",
            "EARLY_BEAR": "BEAR_DCA_ONLY",
            "MID_BEAR": "BEAR_DCA_ONLY",
            "DEEP_BEAR": "BEAR_DCA_ONLY",
            "CAPITULATION": "MAX_ACCUMULATE",
            "ACCUMULATION": "ACCUMULATE",
        }
        return modes.get(self.current_phase, "NORMAL")

    def get_position_multiplier(self) -> float:
        """Multiplikator für Positionsgröße je nach Phase."""
        multipliers = {
            "EUPHORIA": 0.5,        # Halbe Positionen
            "DISTRIBUTION": 0.7,    # Reduziert
            "EARLY_BEAR": 0.6,      # Nur DCA
            "MID_BEAR": 0.5,        # Kleine DCA
            "DEEP_BEAR": 0.8,       # Grössere DCA (gute Preise!)
            "CAPITULATION": 1.0,    # Volle DCA (beste Preise!)
            "ACCUMULATION": 1.0,    # Voll rein
        }
        return multipliers.get(self.current_phase, 0.8)

    def get_status(self) -> Dict:
        return {
            "phase": self.current_phase,
            "mode": self.get_trading_mode(),
            "days_since_halving": self.days_since_halving,
            "cycle_progress": self.cycle_progress,
            "pct_from_ath": self.pct_from_ath,
            "ath": CURRENT_ATH,
            "position_multiplier": self.get_position_multiplier(),
        }

    def get_summary(self) -> str:
        return (f"Zyklus: {self.current_phase} | "
                f"{self.pct_from_ath:+.1f}% vom ATH | "
                f"Tag {self.days_since_halving} nach Halving | "
                f"Modus: {self.get_trading_mode()}")
