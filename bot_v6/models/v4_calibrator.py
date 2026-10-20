"""
V4 PERFORMANCE CALIBRATOR
=========================
Liest die echte V4-Performance (strategy_stats.json) und kalibriert
die Strategie-Gewichte fuer V6 entsprechend.

Loest das V6-Hauptproblem: V6 behandelt alle Strategien gleichberechtigt.
V4 hat real bewiesen welche funktionieren und welche nicht.

Verwendung:
    from models.v4_calibrator import V4Calibrator
    cal = V4Calibrator.load("v4_data/strategy_stats.json")
    weight = cal.get_weight("DCA_FEAR_GREED")     # 1.00 (bester Performer)
    weight = cal.get_weight("STOCHRSI_REVERSAL")  # 0.00 (Verlierer, gesperrt)

Im Signal-Flow:
    final_score = v4_score * cal.get_weight(strategy_id)
"""

import json
import os
from typing import Dict, Optional


class V4Calibrator:
    """
    Berechnet Strategie-Gewichte basierend auf realer V4-Performance.

    Gewichts-Logik (in dieser Reihenfolge):
    1. Negative PnL          -> Gewicht 0.0  (gesperrt)
    2. Win-Rate < 55%        -> Gewicht 0.5  (gedaempft)
    3. Trades < 5            -> Gewicht 0.7  (zu wenig Daten)
    4. Sonst                 -> proportional zu PnL/Trade, max 1.0
    """

    # KEINE statische BLACKLIST mehr!
    # Stattdessen entscheidet das System dynamisch nach total_pnl.
    # So kann eine vorher schlechte Strategie wieder ins System wenn sie sich erholt.

    # Inaktiv in V4 (nie ausgeloest, kein Performance-Signal)
    INACTIVE = {"BOLLINGER_BOUNCE", "MULTI_SIGNAL"}

    # Strategien die sehr risiko-asymmetrisch sind (hohe WR, hohe Verluste)
    # werden bei negativem PnL haerter gesperrt
    DANGER_ZONE = {"STOCHRSI_REVERSAL", "MANUELL"}

    def __init__(self, stats: Dict[str, dict]):
        self.stats = stats
        self.weights: Dict[str, float] = {}
        self._compute_weights()

    @classmethod
    def load(cls, path: str) -> "V4Calibrator":
        """Laedt strategy_stats.json. Faellt zurueck auf default Gewichte wenn nicht vorhanden."""
        if not os.path.exists(path):
            return cls(stats={})
        with open(path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        return cls(stats=stats)

    def _compute_weights(self):
        """Berechnet Gewichte fuer alle Strategien."""
        if not self.stats:
            # Fallback: Gleichgewichtung
            for sid in ["DCA_FEAR_GREED", "FIBONACCI_SUPPORT", "ICHIMOKU_CLOUD",
                        "TSI_SIGNAL", "MACD_CROSS", "RSI_OVERSOLD", "MOMENTUM_BREAKOUT"]:
                self.weights[sid] = 1.0
            return

        # Finde besten avg_pnl der profitablen Strategien (fuer Normalisierung)
        profitable = [s for s in self.stats.values()
                      if s.get('total_pnl', 0) > 0 and s.get('trades', 0) > 0]
        max_avg = max((s['avg_pnl'] for s in profitable), default=1.0)

        for sid, s in self.stats.items():
            if sid in self.INACTIVE:
                self.weights[sid] = 0.0  # Standardmaessig aus
                continue

            trades = s.get('trades', 0)
            total_pnl = s.get('total_pnl', 0.0)
            avg_pnl = s.get('avg_pnl', 0.0)
            win_rate = s.get('win_rate', 0.0)

            # Dynamisch: Verlust = gesperrt (egal ob auf Liste oder nicht)
            if total_pnl <= 0:
                self.weights[sid] = 0.0
                continue
            # Danger-Zone: hat in der Vergangenheit asymmetrische Verluste produziert
            # Hier extra konservativ - braucht klar profitable Performance
            if sid in self.DANGER_ZONE and total_pnl < 50:
                self.weights[sid] = 0.0
                continue
            if trades < 5:
                self.weights[sid] = 0.7
                continue
            if win_rate < 55.0:
                self.weights[sid] = 0.5
                continue

            # Normalisiert auf max avg_pnl, gewichtet mit Win-Rate
            wr_factor = min(win_rate / 80.0, 1.0)   # 80% WR = voller Faktor
            pnl_factor = min(avg_pnl / max(max_avg, 0.01), 1.0)
            self.weights[sid] = round(0.4 + 0.6 * (wr_factor * pnl_factor), 3)

    def get_weight(self, strategy_id: str) -> float:
        """Gewicht einer Strategie (0.0 = gesperrt, 1.0 = maximales Vertrauen)."""
        return self.weights.get(strategy_id, 1.0)  # Unbekannte: Default 1.0

    def is_blocked(self, strategy_id: str) -> bool:
        """Ist eine Strategie hart gesperrt?"""
        return self.weights.get(strategy_id, 1.0) == 0.0

    def calibrate_score(self, strategy_id: str, raw_score: float) -> float:
        """Wendet Strategie-Gewicht auf Roh-Score an."""
        return raw_score * self.get_weight(strategy_id)

    def get_ranking(self) -> list:
        """Strategien sortiert nach Gewicht (besten zuerst)."""
        return sorted(self.weights.items(), key=lambda x: -x[1])

    def get_status(self) -> dict:
        """Diagnose fuer Dashboard."""
        return {
            "active": True,
            "version": "v4_calibrator_1.0",
            "weights": self.weights,
            "blocked": [sid for sid, w in self.weights.items() if w == 0.0],
            "top_performers": [sid for sid, w in self.get_ranking() if w > 0.7][:5],
            "stats_loaded": len(self.stats) > 0,
        }

    def report(self) -> str:
        """Menschenlesbarer Report."""
        lines = ["V4 CALIBRATOR – Strategie-Gewichte aus realer Performance", "=" * 60]
        for sid, w in self.get_ranking():
            stat = self.stats.get(sid, {})
            trades = stat.get('trades', 0)
            pnl = stat.get('total_pnl', 0.0)
            wr = stat.get('win_rate', 0.0)
            status = "BLOCKED" if w == 0.0 else f"weight={w:.2f}"
            lines.append(f"  {sid:<22} {status:<14} ({trades} trades, {wr:.0f}% WR, {pnl:+.2f}€)")
        return "\n".join(lines)
