"""
Trading Imperium V5 – Drawdown Guard
Ueberwacht den maximalen Drawdown und stoppt bei Ueberschreitung.
"""
import time
from typing import Dict
from core.logger import log


class DrawdownGuard:
    """Stoppt Trading wenn Drawdown zu gross wird."""

    def __init__(self, max_drawdown_pct=15.0):
        self.max_drawdown_pct = max_drawdown_pct
        self.peak_equity = 0.0
        self.current_drawdown_pct = 0.0
        self.max_seen_drawdown = 0.0
        self.triggered = False

    def update(self, current_equity):
        """Aktualisiert Drawdown-Berechnung mit aktuellem Portfolio-Wert."""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if self.peak_equity > 0:
            self.current_drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100
        else:
            self.current_drawdown_pct = 0

        self.max_seen_drawdown = max(self.max_seen_drawdown, self.current_drawdown_pct)

        if self.current_drawdown_pct >= self.max_drawdown_pct and not self.triggered:
            self.triggered = True
            log.error("DRAWDOWN", f"MAX DRAWDOWN {self.current_drawdown_pct:.1f}% >= {self.max_drawdown_pct}%!")
            return True  # Signal: Stop Trading!

        return False

    def is_safe(self):
        """Darf getradet werden?"""
        return not self.triggered and self.current_drawdown_pct < self.max_drawdown_pct

    def reset(self, new_peak=None):
        """Reset nach manueller Freigabe oder neuem Tag."""
        self.triggered = False
        if new_peak:
            self.peak_equity = new_peak
        log.info("DRAWDOWN", f"Reset. Peak: {self.peak_equity:.2f}$")

    def get_status(self):
        return {
            "peak": round(self.peak_equity, 2),
            "current_dd": round(self.current_drawdown_pct, 2),
            "max_dd_seen": round(self.max_seen_drawdown, 2),
            "limit": self.max_drawdown_pct,
            "triggered": self.triggered,
            "safe": self.is_safe(),
        }
