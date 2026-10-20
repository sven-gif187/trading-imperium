"""
Trading Imperium V6 – Reinforcement Learning Feedback Loop
Lernt aus Trade-Ergebnissen und passt Strategie-Gewichtungen an.
"""
import os
import json
import time
from typing import Dict
from config.settings import DATA_DIR
from core.logger import log

RL_FILE = os.path.join(DATA_DIR, "rl_weights.json")


class RLFeedbackAgent:
    """Einfacher Q-Learning Agent der Strategie-Gewichtungen anpasst."""

    def __init__(self, learning_rate=0.1, decay=0.95):
        self.lr = learning_rate
        self.decay = decay
        self.weights = {}  # strategy_id -> weight (0.5 bis 2.0)
        self.history = []  # [(strategy, reward, timestamp)]
        self._load()

    def record_trade(self, strategy_id, pnl):
        """Speichert Trade-Ergebnis als Reward."""
        if not strategy_id:
            return

        # Reward: +1 fuer Gewinn, -1 fuer Verlust, skaliert nach Groesse
        if pnl > 0:
            reward = min(1 + (pnl / 100), 2.0)
        elif pnl < 0:
            reward = max(-1 - (abs(pnl) / 100), -2.0)
        else:
            reward = 0

        # Q-Update: weight = weight + lr * (reward - weight)
        current = self.weights.get(strategy_id, 1.0)
        new_weight = current + self.lr * (reward - (current - 1.0))
        new_weight = max(0.3, min(2.0, new_weight))  # Grenzen

        self.weights[strategy_id] = round(new_weight, 3)
        self.history.append({
            "strategy": strategy_id, "pnl": round(pnl, 2),
            "reward": round(reward, 2), "weight": self.weights[strategy_id],
            "time": time.strftime("%Y-%m-%d %H:%M"),
        })

        if len(self.history) > 1000:
            self.history = self.history[-1000:]

        log.info("RL", f"{strategy_id}: PnL {pnl:+.2f}$ -> Reward {reward:+.1f} -> "
                       f"Weight {self.weights[strategy_id]:.3f}")
        self._save()

    def get_weight(self, strategy_id) -> float:
        """Gibt die aktuelle Gewichtung fuer eine Strategie zurueck."""
        return self.weights.get(strategy_id, 1.0)

    def get_best_strategy(self) -> str:
        """Gibt die Strategie mit der hoechsten Gewichtung zurueck."""
        if not self.weights:
            return ""
        return max(self.weights, key=self.weights.get)

    def apply_to_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Multipliziert Strategie-Scores mit RL-Gewichtungen."""
        adjusted = {}
        for strat, score in scores.items():
            w = self.weights.get(strat, 1.0)
            adjusted[strat] = round(score * w, 3)
        return adjusted

    def decay_all(self):
        """Laesst alle Gewichtungen langsam Richtung 1.0 verfallen."""
        for s in self.weights:
            current = self.weights[s]
            self.weights[s] = round(1.0 + (current - 1.0) * self.decay, 3)
        self._save()

    def _load(self):
        if not os.path.exists(RL_FILE):
            return
        try:
            with open(RL_FILE, "r") as f:
                data = json.load(f)
            self.weights = data.get("weights", {})
            self.history = data.get("history", [])
            if self.weights:
                best = self.get_best_strategy()
                log.info("RL", f"Geladen: {len(self.weights)} Strategien, Beste: {best}")
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(RL_FILE), exist_ok=True)
            with open(RL_FILE, "w") as f:
                json.dump({"weights": self.weights, "history": self.history[-1000:]}, f, indent=1)
        except Exception:
            pass

    def get_status(self):
        return {
            "weights": dict(self.weights),
            "best": self.get_best_strategy(),
            "total_trades": len(self.history),
        }
