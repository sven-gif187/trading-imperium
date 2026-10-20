"""
Trading Imperium V6 – Hyperparameter Tuning
Nutzt Optuna (falls installiert) oder eigenen Random Search.
Findet optimale Strategie-Parameter.
"""
import time
import random
import json
import os
from typing import Dict, List, Callable
from config.settings import DATA_DIR
from core.logger import log

RESULTS_FILE = os.path.join(DATA_DIR, "hyperopt_results.json")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


class HyperOptimizer:
    """Hyperparameter-Tuning fuer Trading-Strategien."""

    def __init__(self):
        self.best_params = {}
        self.all_trials = []
        self.is_running = False

    def optimize(self, backtest_engine, df, coin="BTC/USDC",
                 n_trials=50, timeout_sec=300) -> Dict:
        """
        Fuehrt Hyperparameter-Tuning durch.
        Nutzt Optuna wenn verfuegbar, sonst Random Search.
        """
        self.is_running = True
        log.info("HYPEROPT", f"Starte {'Optuna' if HAS_OPTUNA else 'Random Search'} "
                             f"({n_trials} Trials, max {timeout_sec}s)")

        if HAS_OPTUNA:
            result = self._optuna_optimize(backtest_engine, df, coin, n_trials, timeout_sec)
        else:
            result = self._random_search(backtest_engine, df, coin, n_trials)

        self.is_running = False
        self._save_results(result)
        return result

    def _optuna_optimize(self, bt, df, coin, n_trials, timeout_sec) -> Dict:
        def objective(trial):
            sl = trial.suggest_float("stop_loss_pct", 1.5, 8.0, step=0.5)
            trail = trial.suggest_float("trailing_pct", 0.3, 4.0, step=0.3)
            pos = trial.suggest_float("position_size_pct", 5, 35, step=5)
            rsi_buy = trial.suggest_int("rsi_buy_threshold", 25, 40)
            rsi_sell = trial.suggest_int("rsi_sell_threshold", 65, 80)
            min_score = trial.suggest_int("min_signal_score", 2, 5)

            try:
                result = bt.run(df, coin=coin, stop_loss_pct=sl,
                              trailing_pct=trail, position_size_pct=pos)
                # Ziel: Maximiere risiko-adjustierte Rendite
                score = result.total_pnl_pct * 0.4 + result.win_rate * 0.3 - result.max_drawdown * 0.3
                return score
            except Exception:
                return -999

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, timeout=timeout_sec)

        best = study.best_params
        best_score = study.best_value
        self.best_params = best
        self.all_trials = [{"params": t.params, "score": t.value,
                           "number": t.number} for t in study.trials if t.value is not None]

        log.info("HYPEROPT", f"Optuna Best: Score {best_score:.2f} | {best}")
        return {"method": "optuna", "best_params": best, "best_score": round(best_score, 2),
                "trials": len(self.all_trials), "top5": sorted(self.all_trials, key=lambda x: x["score"], reverse=True)[:5]}

    def _random_search(self, bt, df, coin, n_trials) -> Dict:
        results = []
        for i in range(n_trials):
            params = {
                "stop_loss_pct": round(random.uniform(1.5, 8), 1),
                "trailing_pct": round(random.uniform(0.3, 4), 1),
                "position_size_pct": random.choice([5, 10, 15, 20, 25, 30]),
            }
            try:
                r = bt.run(df, coin=coin, **params)
                score = r.total_pnl_pct * 0.4 + r.win_rate * 0.3 - r.max_drawdown * 0.3
                results.append({"params": params, "score": round(score, 2),
                               "pnl": r.total_pnl, "wr": r.win_rate, "dd": r.max_drawdown})
            except Exception:
                pass
            if i % 10 == 0:
                log.info("HYPEROPT", f"  {i+1}/{n_trials}...")

        results.sort(key=lambda x: x["score"], reverse=True)
        self.best_params = results[0]["params"] if results else {}
        self.all_trials = results

        if results:
            log.info("HYPEROPT", f"Best: Score {results[0]['score']} | {results[0]['params']}")

        return {"method": "random_search", "best_params": self.best_params,
                "best_score": results[0]["score"] if results else 0,
                "trials": len(results), "top5": results[:5]}

    def format_results(self, result) -> str:
        lines = [
            "=" * 65,
            f"  HYPEROPT ({result.get('method', '?')}) – {result.get('trials', 0)} Trials",
            "=" * 65,
            f"  Beste Parameter:", ""]
        for k, v in result.get("best_params", {}).items():
            lines.append(f"    {k}: {v}")
        lines.extend(["", f"  Score: {result.get('best_score', 0)}", "",
                      "  Top 5:", f"  {'Score':>8} {'SL%':>5} {'Trail%':>7} {'Pos%':>5}", "  " + "-" * 30])
        for r in result.get("top5", []):
            p = r.get("params", {})
            lines.append(f"  {r.get('score', 0):>8.2f} {p.get('stop_loss_pct', '?'):>5} "
                        f"{p.get('trailing_pct', '?'):>7} {p.get('position_size_pct', '?'):>5}")
        return "\n".join(lines)

    def _save_results(self, result):
        try:
            os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
            with open(RESULTS_FILE, "w") as f:
                json.dump(result, f, indent=1, default=str)
        except Exception:
            pass

    def get_status(self):
        return {"running": self.is_running, "best_params": self.best_params,
                "trials": len(self.all_trials), "has_optuna": HAS_OPTUNA}
