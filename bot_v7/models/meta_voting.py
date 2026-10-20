"""
Trading Imperium V6 – Meta-Learning Voting System
Agenten die schlecht performen verlieren Stimmrecht.
Agenten die gut performen bekommen mehr Gewicht.
"""
import time
import json
import os
from typing import Dict
from config.settings import DATA_DIR
from core.logger import log

VOTES_FILE = os.path.join(DATA_DIR, "agent_votes.json")


class MetaVotingSystem:
    """
    Meta-Learning: Jeder Agent hat ein Stimmgewicht (0.1 bis 2.0).
    Nach jedem Trade wird bewertet welche Agenten "richtig" lagen.
    Falsche Agenten verlieren Stimmrecht, richtige gewinnen.
    """

    def __init__(self):
        self.agent_weights = {
            "technical": 1.0,    # RSI, MACD, Bollinger
            "ensemble": 1.0,     # Ensemble Score
            "vwap": 1.0,         # VWAP Bias
            "orderbook": 1.0,    # Bid/Ask Imbalance
            "fear_greed": 1.0,   # Sentiment
            "regime": 1.0,       # Markt-Regime
            "mtf": 1.0,          # Multi-Timeframe
            "funding": 1.0,      # Funding Rates
            "onchain": 1.0,      # On-Chain Metriken
        }
        self.predictions = {}  # trade_id -> {agent: prediction}
        self.history = []
        self.total_adjustments = 0
        self._load()

    def record_prediction(self, trade_id, agent_predictions: Dict[str, str]):
        """
        Speichert was jeder Agent vorhergesagt hat.
        agent_predictions: {"technical": "BUY", "vwap": "NEUTRAL", ...}
        """
        self.predictions[trade_id] = {
            "predictions": agent_predictions,
            "time": time.time(),
        }

    def evaluate_trade(self, trade_id, actual_pnl):
        """
        Bewertet die Vorhersagen der Agenten nach Trade-Ergebnis.
        Gewinn: Agenten die BUY gesagt haben bekommen +weight
        Verlust: Agenten die BUY gesagt haben verlieren weight
        """
        pred = self.predictions.get(trade_id)
        if not pred:
            return

        was_profitable = actual_pnl > 0
        lr = 0.05  # Learning Rate

        for agent, prediction in pred["predictions"].items():
            if agent not in self.agent_weights:
                continue

            current = self.agent_weights[agent]

            if prediction == "BUY":
                if was_profitable:
                    # Agent lag richtig -> mehr Gewicht
                    self.agent_weights[agent] = min(2.0, current + lr)
                else:
                    # Agent lag falsch -> weniger Gewicht
                    self.agent_weights[agent] = max(0.1, current - lr * 2)
            elif prediction == "SELL" or prediction == "BEARISH":
                if not was_profitable:
                    # Agent hat korrekt gewarnt -> mehr Gewicht
                    self.agent_weights[agent] = min(2.0, current + lr)

        self.total_adjustments += 1
        self.history.append({
            "trade_id": trade_id, "pnl": round(actual_pnl, 2),
            "weights_after": dict(self.agent_weights),
            "time": time.strftime("%H:%M"),
        })
        if len(self.history) > 100:
            self.history = self.history[-100:]

        self._save()

        # Log die staerksten und schwaechsten Agenten
        sorted_agents = sorted(self.agent_weights.items(), key=lambda x: x[1], reverse=True)
        best = sorted_agents[0]
        worst = sorted_agents[-1]
        log.info("META", f"Trade PnL {actual_pnl:+.2f}$ | "
                        f"Bester: {best[0]} ({best[1]:.2f}) | "
                        f"Schwaechster: {worst[0]} ({worst[1]:.2f})")

    def get_weighted_score(self, agent_scores: Dict[str, float]) -> float:
        """
        Berechnet gewichteten Score basierend auf Agent-Performance.
        agent_scores: {"technical": 0.7, "vwap": 0.3, ...}
        """
        total_weight = 0
        weighted_sum = 0
        for agent, score in agent_scores.items():
            weight = self.agent_weights.get(agent, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def get_agent_ranking(self):
        """Gibt Agenten sortiert nach Performance zurueck."""
        return sorted(self.agent_weights.items(), key=lambda x: x[1], reverse=True)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(VOTES_FILE), exist_ok=True)
            with open(VOTES_FILE, "w") as f:
                json.dump({"weights": self.agent_weights,
                          "history": self.history[-50:],
                          "adjustments": self.total_adjustments}, f, indent=1)
        except Exception:
            pass

    def _load(self):
        try:
            if os.path.exists(VOTES_FILE):
                with open(VOTES_FILE, "r") as f:
                    data = json.load(f)
                self.agent_weights = data.get("weights", self.agent_weights)
                self.history = data.get("history", [])
                self.total_adjustments = data.get("adjustments", 0)
                if self.total_adjustments > 0:
                    log.info("META", f"Geladen: {self.total_adjustments} Bewertungen")
        except Exception:
            pass

    def get_status(self):
        ranking = self.get_agent_ranking()
        return {
            "weights": dict(self.agent_weights),
            "best_agent": ranking[0] if ranking else ("?", 0),
            "worst_agent": ranking[-1] if ranking else ("?", 0),
            "total_evaluations": self.total_adjustments,
        }
