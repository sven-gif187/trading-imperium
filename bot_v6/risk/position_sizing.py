"""
Trading Imperium V5 – Position Sizing
Berechnet die optimale Positionsgroesse basierend auf Risiko und Kontext.
"""
from typing import Dict
from core.logger import log


class PositionSizer:
    """Berechnet Positionsgroessen basierend auf Risiko-Parametern."""

    def __init__(self, default_pct=15.0, min_usd=5.0, max_pct=50.0):
        self.default_pct = default_pct
        self.min_usd = min_usd
        self.max_pct = max_pct

    def calculate(self, total_equity, confidence=0.5, cycle_phase="",
                  volatility=0.0, regime="UNKNOWN"):
        """
        Berechnet die optimale Positionsgroesse in USD.
        Anpassungen basierend auf Confidence, Zyklus, Volatilitaet.
        """
        if total_equity <= 0:
            return 0.0

        # Basis: default_pct vom Equity
        base = total_equity * (self.default_pct / 100)

        # Confidence-Multiplikator (0.5 bis 1.5x)
        conf_mult = 0.5 + confidence  # confidence 0-1 -> mult 0.5-1.5

        # Zyklus-Multiplikator
        cycle_mult = {
            "EUPHORIA": 0.5, "DISTRIBUTION": 0.7,
            "EARLY_BEAR": 0.6, "MID_BEAR": 0.5,
            "DEEP_BEAR": 0.8, "CAPITULATION": 1.0,
            "ACCUMULATION": 1.0,
        }.get(cycle_phase, 0.8)

        # Volatilitaets-Anpassung (hohe Vol = kleinere Positionen)
        vol_mult = 1.0
        if volatility > 0.03:   # > 3% Volatilitaet
            vol_mult = 0.7
        elif volatility > 0.05:
            vol_mult = 0.5

        # Regime-Anpassung
        regime_mult = {"TRENDING": 1.1, "RANGING": 0.9, "VOLATILE": 0.7}.get(regime, 1.0)

        # Finale Berechnung
        amount = base * conf_mult * cycle_mult * vol_mult * regime_mult

        # Grenzen einhalten
        amount = max(amount, self.min_usd)
        amount = min(amount, total_equity * (self.max_pct / 100))

        return round(amount, 2)

    def kelly_fraction(self, win_rate, avg_win, avg_loss):
        """Kelly-Kriterium fuer optimale Positionsgroesse."""
        if avg_loss == 0 or win_rate <= 0:
            return 0
        b = avg_win / abs(avg_loss)  # Gewinn/Verlust Verhaeltnis
        p = win_rate / 100  # Win-Rate als Dezimal
        q = 1 - p
        kelly = (b * p - q) / b
        # Half-Kelly fuer Sicherheit
        return max(0, min(kelly * 0.5, 0.25))

    def get_status(self):
        return {"default_pct": self.default_pct, "min_usd": self.min_usd, "max_pct": self.max_pct}
