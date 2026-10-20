"""
Trading Imperium V6 – Adaptive Position Sizing (KI)
Passt Positionsgroesse dynamisch an basierend auf Volatilitaet, Win-Rate und Drawdown.
"""
import math
from typing import Dict
from core.logger import log


class AdaptivePositionSizer:
    """KI-basierte dynamische Positionsgroesse."""

    def __init__(self, base_pct=15.0, min_pct=3.0, max_pct=40.0):
        self.base_pct = base_pct
        self.min_pct = min_pct
        self.max_pct = max_pct
        self.trade_results = []  # Letzte N Trades
        self.adjustments = []

    def calculate(self, total_equity, confidence=0.5, volatility=0.02,
                  win_rate=50.0, current_drawdown=0, streak=0,
                  regime="UNKNOWN", fear_greed=50) -> Dict:
        """Berechnet optimale Positionsgroesse."""
        if total_equity <= 0:
            return {"amount": 0, "pct": 0, "reason": "Kein Kapital"}

        pct = self.base_pct
        reasons = []

        # 1. Win-Rate Anpassung (Kelly-inspiriert)
        if win_rate > 60:
            pct *= 1.2; reasons.append(f"Hohe WR ({win_rate:.0f}%)")
        elif win_rate < 40 and len(self.trade_results) > 10:
            pct *= 0.6; reasons.append(f"Niedrige WR ({win_rate:.0f}%)")

        # 2. Volatilitaets-Anpassung
        if volatility > 0.04:
            pct *= 0.6; reasons.append(f"Hohe Vol ({volatility:.1%})")
        elif volatility > 0.025:
            pct *= 0.8
        elif volatility < 0.01:
            pct *= 1.2; reasons.append("Niedrige Vol")

        # 3. Drawdown-Schutz
        if current_drawdown > 10:
            pct *= 0.4; reasons.append(f"DD {current_drawdown:.0f}%!")
        elif current_drawdown > 5:
            pct *= 0.7; reasons.append(f"DD {current_drawdown:.0f}%")

        # 4. Verlustserie
        if streak >= 3:
            pct *= 0.5; reasons.append(f"{streak}x Verlust")
        elif streak >= 2:
            pct *= 0.7

        # 5. Confidence
        pct *= (0.5 + confidence * 0.5)

        # 6. Regime
        regime_mult = {"TRENDING_UP": 1.1, "RANGING": 0.8, "VOLATILE": 0.6,
                       "TRENDING_DOWN": 0.7}.get(regime, 1.0)
        pct *= regime_mult

        # 7. Fear & Greed (Extreme = groessere Positionen bei Fear)
        if fear_greed < 15:
            pct *= 1.3; reasons.append("Extreme Fear")
        elif fear_greed > 80:
            pct *= 0.5; reasons.append("Extreme Greed")

        # Grenzen
        pct = max(self.min_pct, min(self.max_pct, pct))
        amount = total_equity * (pct / 100)

        result = {
            "amount": round(amount, 2),
            "pct": round(pct, 1),
            "base_pct": self.base_pct,
            "reasons": reasons,
        }

        self.adjustments.append(result)
        if len(self.adjustments) > 100:
            self.adjustments = self.adjustments[-100:]

        return result

    def record_result(self, pnl):
        self.trade_results.append(pnl)
        if len(self.trade_results) > 50:
            self.trade_results = self.trade_results[-50:]

    def get_win_rate(self) -> float:
        if not self.trade_results:
            return 50.0
        wins = sum(1 for p in self.trade_results if p > 0)
        return wins / len(self.trade_results) * 100

    def get_status(self):
        return {"base_pct": self.base_pct, "trades_tracked": len(self.trade_results),
                "win_rate": round(self.get_win_rate(), 1)}
