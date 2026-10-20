"""
Trading Imperium V6 – Strategy Marketplace / Export
Exportiert und importiert Trading-Strategien als JSON.
"""
import json
import os
import time
from typing import Dict, List
from config.settings import DATA_DIR
from core.logger import log

STRATEGY_DIR = os.path.join(DATA_DIR, "strategies")
os.makedirs(STRATEGY_DIR, exist_ok=True)


class StrategyExporter:
    """Exportiert und importiert Trading-Strategien."""

    def export_strategy(self, config, journal, rl_weights=None, name="Meine Strategie") -> str:
        """Exportiert aktuelle Strategie als JSON-Datei."""
        stats = journal.get_stats()
        strategy = {
            "name": name,
            "version": "6.0.0",
            "created": time.strftime("%Y-%m-%d %H:%M"),
            "author": "Trading Imperium V6",
            "parameters": {
                "stop_loss_pct": config.risk.stop_loss_pct,
                "trailing_stop_pct": config.risk.trailing_stop_pct,
                "position_size_pct": config.trading.position_size_pct,
                "max_open_positions": config.risk.max_open_positions,
                "coins": config.trading.coins,
                "default_timeframe": config.trading.default_timeframe,
                "btc_dca_enabled": config.trading.btc_dca_enabled,
                "btc_dca_pct": config.trading.btc_dca_pct,
            },
            "risk_settings": {
                "daily_loss_limit": config.risk.daily_loss_limit,
                "max_drawdown_pct": config.risk.max_drawdown_pct,
                "cooldown_after_loss": config.risk.cooldown_after_loss,
            },
            "performance": {
                "total_trades": stats.get("total_trades", 0),
                "win_rate": stats.get("win_rate", 0),
                "total_pnl": stats.get("total_pnl", 0),
                "strategies": stats.get("strategies", {}),
            },
            "rl_weights": rl_weights or {},
        }

        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in name if c.isalnum() or c in "_ -").strip()
        filename = f"strategy_{safe_name}_{ts}.json"
        path = os.path.join(STRATEGY_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(strategy, f, indent=2, ensure_ascii=False, default=str)

        log.info("EXPORT", f"Strategie exportiert: {path}")
        return path

    def import_strategy(self, filepath, config) -> Dict:
        """Importiert eine Strategie aus JSON."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                strategy = json.load(f)

            params = strategy.get("parameters", {})
            risk = strategy.get("risk_settings", {})

            # Parameter anwenden
            if "stop_loss_pct" in params:
                config.risk.stop_loss_pct = params["stop_loss_pct"]
            if "trailing_stop_pct" in params:
                config.risk.trailing_stop_pct = params["trailing_stop_pct"]
            if "position_size_pct" in params:
                config.trading.position_size_pct = params["position_size_pct"]
            if "max_open_positions" in params:
                config.risk.max_open_positions = params["max_open_positions"]
            if "coins" in params:
                config.trading.coins = params["coins"]
            if "daily_loss_limit" in risk:
                config.risk.daily_loss_limit = risk["daily_loss_limit"]

            config.save()
            perf = strategy.get("performance", {})
            log.info("IMPORT", f"Strategie '{strategy.get('name', '?')}' importiert "
                              f"(WR: {perf.get('win_rate', 0):.0f}%, {perf.get('total_trades', 0)} Trades)")
            return {"status": "ok", "name": strategy.get("name"), "performance": perf,
                    "rl_weights": strategy.get("rl_weights", {})}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_strategies(self) -> List[Dict]:
        """Listet alle gespeicherten Strategien."""
        strategies = []
        for f in sorted(os.listdir(STRATEGY_DIR), reverse=True):
            if f.endswith(".json"):
                path = os.path.join(STRATEGY_DIR, f)
                try:
                    with open(path, "r") as fh:
                        data = json.load(fh)
                    strategies.append({
                        "file": f, "name": data.get("name", "?"),
                        "created": data.get("created", "?"),
                        "win_rate": data.get("performance", {}).get("win_rate", 0),
                        "trades": data.get("performance", {}).get("total_trades", 0),
                    })
                except Exception:
                    pass
        return strategies

    def get_status(self):
        return {"strategies_saved": len(self.list_strategies()),
                "directory": STRATEGY_DIR}
