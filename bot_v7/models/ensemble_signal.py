"""
Trading Imperium V6 – Ensemble Signal Aggregation
Kombiniert ML + Regeln + LLM + On-Chain + VWAP zu einem gewichteten Score.
"""
from typing import Dict
from core.logger import log


class EnsembleSignal:
    """Kombiniert alle Signalquellen zu einem Gesamt-Score."""

    WEIGHTS = {
        "technical": 0.30,     # RSI, MACD, Bollinger etc
        "ml_model": 0.20,      # XGBoost/GradientBoosting
        "fear_greed": 0.15,    # Sentiment
        "funding": 0.10,       # Funding Rates
        "onchain": 0.08,       # On-Chain Metriken
        "vwap": 0.07,          # VWAP Bias
        "reddit": 0.05,        # Reddit Sentiment
        "capitol": 0.03,       # Politiker-Trades
        "whale": 0.02,         # Whale Alerts
    }

    def __init__(self):
        self.last_scores = {}
        self.last_ensemble = 0.5

    def calculate(self, signals: Dict[str, float]) -> Dict:
        """
        Berechnet gewichteten Ensemble-Score.
        signals: {"technical": 0.7, "ml_model": 0.6, ...}
        Returns: {"score": 0.0-1.0, "label": str, "breakdown": {...}}
        """
        total_weight = 0
        weighted_sum = 0
        breakdown = {}

        for source, weight in self.WEIGHTS.items():
            if source in signals:
                val = signals[source]
                weighted_sum += val * weight
                total_weight += weight
                breakdown[source] = {"value": round(val, 3), "weight": weight,
                                     "contribution": round(val * weight, 4)}

        score = weighted_sum / total_weight if total_weight > 0 else 0.5

        # Confluence-Bonus: wenn viele Quellen uebereinstimmen
        bullish = sum(1 for v in signals.values() if v > 0.6)
        bearish = sum(1 for v in signals.values() if v < 0.4)
        total = len(signals)
        if total > 0:
            if bullish / total > 0.7:
                score = min(score * 1.1, 1.0)  # 10% Bonus
            elif bearish / total > 0.7:
                score = max(score * 0.9, 0.0)

        if score > 0.6:
            label = "STRONG_BUY" if score > 0.75 else "BUY"
        elif score < 0.4:
            label = "STRONG_SELL" if score < 0.25 else "SELL"
        else:
            label = "NEUTRAL"

        self.last_scores = signals
        self.last_ensemble = score

        return {
            "score": round(score, 3),
            "label": label,
            "sources": len(signals),
            "breakdown": breakdown,
            "confluence_bullish": bullish,
            "confluence_bearish": bearish,
        }

    def get_status(self):
        return {"last_score": round(self.last_ensemble, 3),
                "sources": len(self.last_scores), "weights": self.WEIGHTS}
