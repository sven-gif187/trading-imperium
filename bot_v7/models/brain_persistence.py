"""
BRAIN PERSISTENCE
=================
Loest 2 kritische V6-Bugs:

1. Strategy Brain vergisst alles bei jedem Neustart
   -> Performance wird jetzt persistent gespeichert

2. V6 startet bei Null statt mit V4-Wissen
   -> Initial-Load aus V4 strategy_stats.json (278 Trades, +1.597 EUR)

Verwendung:
    from models.brain_persistence import BrainPersistence

    # Beim Start (in app.py oder strategy_brain Init):
    bp = BrainPersistence()
    initial_perf = bp.load_performance()
    self.strategy_brain.performance = initial_perf

    # Nach jedem Trade:
    bp.save_performance(self.strategy_brain.performance)
"""

import json
import os
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger("brain_persistence")


class BrainPersistence:
    """Persistiert das Performance-Lernen des StrategyBrain."""

    DEFAULT_FILE = "data_store/brain_performance.json"
    V4_STATS_FILE = "v4_data/strategy_stats.json"

    # Mapping: V4 Strategy-IDs -> V6 Strategy-IDs (V6 nutzt teils andere Namen)
    V4_TO_V6_MAPPING = {
        "RSI_OVERSOLD":      "RSI_OVERSOLD",
        "BOLLINGER_BOUNCE":  "BOLLINGER_BOUNCE",
        "RSI_DIVERGENCE":    "RSI_DIVERGENZ",        # V6 schreibt es anders
        "MACD_CROSS":        "MACD_CROSS",
        "EMA_TREND":         "EMA_TREND",
        "ICHIMOKU_CLOUD":    "ICHIMOKU",              # V6 schreibt es kuerzer
        "MOMENTUM_BREAKOUT": "MOMENTUM_BREAKOUT",
        "TSI_SIGNAL":        "TSI",                   # V6 schreibt es kuerzer
        "STOCHRSI_REVERSAL": "STOCHRSI_REVERSAL",
        "MULTI_SIGNAL":      "MULTI_SIGNAL",
        "FIBONACCI_SUPPORT": "FIBONACCI_SUPPORT",
        "DCA_FEAR_GREED":    "DCA_FEAR_GREED",
    }

    def __init__(self, persistence_file: str = None, v4_stats_file: str = None):
        self.persistence_file = persistence_file or self.DEFAULT_FILE
        self.v4_stats_file = v4_stats_file or self.V4_STATS_FILE

    def load_performance(self) -> Dict[str, Dict]:
        """
        Laedt die Performance.

        1. Versucht zuerst die persistente Datei (gelernte V6-Performance)
        2. Falls die nicht da: bootstrap aus V4-Daten
        3. Falls auch das nicht: leeres Dict
        """
        # 1. Persistierte V6-Performance
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                perf = data.get("performance", {})
                if perf:
                    logger.info(f"Loaded persisted brain performance: {len(perf)} strategies")
                    return perf
            except Exception as e:
                logger.warning(f"Could not load persisted performance: {e}")

        # 2. Bootstrap aus V4-Daten
        if os.path.exists(self.v4_stats_file):
            try:
                with open(self.v4_stats_file, "r", encoding="utf-8") as f:
                    v4_stats = json.load(f)
                bootstrapped = self._bootstrap_from_v4(v4_stats)
                logger.info(f"Bootstrapped brain from V4 data: {len(bootstrapped)} strategies")
                return bootstrapped
            except Exception as e:
                logger.warning(f"Could not bootstrap from V4: {e}")

        # 3. Leeres Dict (Brain startet bei Null)
        return {}

    def _bootstrap_from_v4(self, v4_stats: Dict) -> Dict[str, Dict]:
        """Wandelt V4 strategy_stats in V6 Brain-Performance Format um."""
        v6_perf = {}
        for v4_id, stats in v4_stats.items():
            v6_id = self.V4_TO_V6_MAPPING.get(v4_id, v4_id)
            trades = stats.get("trades", 0)
            wins = stats.get("wins", 0)
            total_pnl = stats.get("total_pnl", 0.0)
            win_rate = stats.get("win_rate", 0.0)
            v6_perf[v6_id] = {
                "trades": trades,
                "wins": wins,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "source": "v4_bootstrap",
                "v6_trades_added": 0,
            }
        return v6_perf

    def save_performance(self, performance: Dict[str, Dict]) -> bool:
        """Speichert die aktuelle Brain-Performance."""
        try:
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            payload = {
                "saved_at": datetime.now().astimezone().isoformat(),
                "performance": performance,
                "total_strategies": len(performance),
                "total_trades": sum(p.get("trades", 0) for p in performance.values()),
            }
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            logger.error(f"Could not save brain performance: {e}")
            return False

    def get_status(self) -> Dict:
        """Diagnose."""
        status = {
            "persistence_file": self.persistence_file,
            "exists": os.path.exists(self.persistence_file),
            "v4_bootstrap_available": os.path.exists(self.v4_stats_file),
        }
        if status["exists"]:
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status["saved_at"] = data.get("saved_at", "?")
                status["total_strategies"] = data.get("total_strategies", 0)
                status["total_trades"] = data.get("total_trades", 0)
            except Exception:
                pass
        return status
