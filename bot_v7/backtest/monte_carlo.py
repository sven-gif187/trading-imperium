"""
Trading Imperium V5 – Monte Carlo Simulation
Stress-testet die Strategie durch zufaelliges Mischen der Trade-Reihenfolge.
Zeigt: Wie schlimm KOENNTE es werden? Best/Worst/Median Case.
"""
import random
import numpy as np
from typing import Dict, List
from core.logger import log
from backtest.metrics import BacktestMetrics


class MonteCarloSim:
    """Monte Carlo Simulation fuer Stress-Tests."""

    def __init__(self, n_simulations=500):
        self.n_simulations = n_simulations

    def run(self, trades: List[Dict], initial_balance=10000) -> Dict:
        """
        Mischt Trade-Ergebnisse zufaellig und simuliert N Durchlaeufe.
        trades: Liste von Trades mit "pnl" Feld
        Returns: Statistiken ueber alle Simulationen
        """
        pnls = [t.get("pnl", 0) for t in trades if t.get("type") == "SELL" and "pnl" in t]

        if len(pnls) < 5:
            return {"error": "Zu wenig Trades (min 5)"}

        final_balances = []
        max_drawdowns = []
        max_loss_streaks = []

        for _ in range(self.n_simulations):
            # Trades zufaellig mischen
            shuffled = list(pnls)
            random.shuffle(shuffled)

            # Equity-Kurve simulieren
            balance = initial_balance
            equity = [balance]
            peak = balance
            max_dd = 0
            streak = 0
            max_streak = 0

            for pnl in shuffled:
                balance += pnl
                equity.append(balance)
                if balance > peak:
                    peak = balance
                dd = ((peak - balance) / peak * 100) if peak > 0 else 0
                max_dd = max(max_dd, dd)
                if pnl < 0:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0

            final_balances.append(balance)
            max_drawdowns.append(max_dd)
            max_loss_streaks.append(max_streak)

        # Statistiken
        finals = np.array(final_balances)
        dds = np.array(max_drawdowns)
        streaks = np.array(max_loss_streaks)

        result = {
            "simulations": self.n_simulations,
            "trades_used": len(pnls),
            "initial": initial_balance,
            "final": {
                "median": round(float(np.median(finals)), 2),
                "mean": round(float(np.mean(finals)), 2),
                "best": round(float(np.max(finals)), 2),
                "worst": round(float(np.min(finals)), 2),
                "p5": round(float(np.percentile(finals, 5)), 2),   # 5% worst case
                "p25": round(float(np.percentile(finals, 25)), 2),
                "p75": round(float(np.percentile(finals, 75)), 2),
                "p95": round(float(np.percentile(finals, 95)), 2),  # 95% best case
            },
            "drawdown": {
                "median": round(float(np.median(dds)), 1),
                "worst": round(float(np.max(dds)), 1),
                "p95": round(float(np.percentile(dds, 95)), 1),
            },
            "loss_streak": {
                "median": int(np.median(streaks)),
                "worst": int(np.max(streaks)),
            },
            "ruin_probability": round(float(np.mean(finals < initial_balance * 0.5)) * 100, 1),
            "profit_probability": round(float(np.mean(finals > initial_balance)) * 100, 1),
        }

        log.info("MONTE", f"Fertig: {self.n_simulations} Sims | "
                          f"Median: {result['final']['median']:.0f}$ | "
                          f"Worst: {result['final']['worst']:.0f}$ | "
                          f"Ruin: {result['ruin_probability']:.1f}%")
        return result

    def summary_text(self, result) -> str:
        if "error" in result:
            return f"Monte Carlo Fehler: {result['error']}"
        f = result["final"]
        d = result["drawdown"]
        lines = [
            f"{'=' * 55}",
            f"  MONTE CARLO SIMULATION ({result['simulations']}x)",
            f"{'=' * 55}",
            f"  Start-Balance:  {result['initial']:,.2f}$",
            f"  Trades:         {result['trades_used']}",
            f"{'─' * 55}",
            f"  ENDKAPITAL:",
            f"    Best Case:    {f['best']:>10,.2f}$ (Top 5%: {f['p95']:,.2f}$)",
            f"    75. Perzentil:{f['p75']:>10,.2f}$",
            f"    Median:       {f['median']:>10,.2f}$",
            f"    25. Perzentil:{f['p25']:>10,.2f}$",
            f"    Worst Case:   {f['worst']:>10,.2f}$ (Bottom 5%: {f['p5']:,.2f}$)",
            f"{'─' * 55}",
            f"  MAX DRAWDOWN:",
            f"    Median:       {d['median']:>9.1f}%",
            f"    95. Perzentil:{d['p95']:>9.1f}%",
            f"    Worst:        {d['worst']:>9.1f}%",
            f"{'─' * 55}",
            f"  Gewinn-Wahrsch: {result['profit_probability']:>9.1f}%",
            f"  Ruin-Wahrsch:   {result['ruin_probability']:>9.1f}% (unter 50% vom Start)",
            f"  Max Verlustserie: {result['loss_streak']['worst']} (Median: {result['loss_streak']['median']})",
            f"{'=' * 55}",
        ]
        return "\n".join(lines)
