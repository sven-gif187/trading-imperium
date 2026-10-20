"""
Trading Imperium V6 – Backtesting Optimizer
Findet die besten Parameter (SL%, Trail%, Position%) durch Grid-Search.
"""
import itertools
import time
from typing import Dict, List
from core.logger import log


class BacktestOptimizer:
    """Optimiert Trading-Parameter durch Backtesting."""

    def __init__(self):
        self.best_result = None
        self.all_results = []
        self.is_running = False

    def grid_search(self, backtest_engine, df, coin="BTC/USDC",
                    sl_range=(2, 3, 4, 5, 6),
                    trail_range=(0.5, 1.0, 1.5, 2.0, 3.0),
                    pos_range=(10, 15, 20, 25)) -> Dict:
        """
        Testet alle Kombinationen von SL%, Trail%, Position%.
        Returns: Beste Parameter + Ranking aller Kombinationen.
        """
        self.is_running = True
        self.all_results = []
        combinations = list(itertools.product(sl_range, trail_range, pos_range))
        total = len(combinations)

        log.info("OPTIMIZE", f"Grid-Search: {total} Kombinationen ({len(sl_range)} SL x "
                             f"{len(trail_range)} Trail x {len(pos_range)} Pos)")

        for i, (sl, trail, pos) in enumerate(combinations):
            try:
                result = backtest_engine.run(df, coin=coin,
                    stop_loss_pct=sl, trailing_pct=trail, position_size_pct=pos)
                entry = {
                    "sl": sl, "trail": trail, "pos": pos,
                    "pnl": result.total_pnl,
                    "pnl_pct": result.total_pnl_pct,
                    "trades": result.total_trades,
                    "win_rate": result.win_rate,
                    "max_dd": result.max_drawdown,
                    "sharpe": result.sharpe if hasattr(result, 'sharpe') else 0,
                    "profit_factor": result.profit_factor if hasattr(result, 'profit_factor') else 0,
                }
                self.all_results.append(entry)

                if i % 10 == 0:
                    log.info("OPTIMIZE", f"  {i+1}/{total} getestet...")
            except Exception:
                pass

        if not self.all_results:
            self.is_running = False
            return {"error": "Keine Ergebnisse"}

        # Sortieren nach P&L
        self.all_results.sort(key=lambda x: x["pnl"], reverse=True)
        self.best_result = self.all_results[0]

        # Score berechnen (gewichtete Bewertung)
        for r in self.all_results:
            r["score"] = (
                r["pnl_pct"] * 0.3 +
                r["win_rate"] * 0.3 +
                (100 - r["max_dd"]) * 0.2 +
                r.get("sharpe", 0) * 10 * 0.2
            )
        self.all_results.sort(key=lambda x: x["score"], reverse=True)
        self.best_result = self.all_results[0]

        self.is_running = False
        log.info("OPTIMIZE", f"Beste Parameter: SL={self.best_result['sl']}% "
                             f"Trail={self.best_result['trail']}% Pos={self.best_result['pos']}% "
                             f"-> P&L: {self.best_result['pnl']:+.2f}$ "
                             f"WR: {self.best_result['win_rate']:.0f}%")
        return {
            "best": self.best_result,
            "top5": self.all_results[:5],
            "worst": self.all_results[-1],
            "total_tested": len(self.all_results),
        }

    def format_results(self, result) -> str:
        """Formatiert Optimizer-Ergebnisse als Text."""
        if "error" in result:
            return f"Fehler: {result['error']}"
        best = result["best"]
        lines = [
            "=" * 65,
            "  PARAMETER OPTIMIZER – Ergebnisse",
            "=" * 65,
            f"  Getestet: {result['total_tested']} Kombinationen",
            "",
            f"  BESTE PARAMETER:",
            f"    Stop-Loss:    {best['sl']}%",
            f"    Trailing:     {best['trail']}%",
            f"    Position:     {best['pos']}%",
            f"    P&L:          {best['pnl']:+.2f}$ ({best['pnl_pct']:+.2f}%)",
            f"    Win-Rate:     {best['win_rate']:.0f}%",
            f"    Max DD:       {best['max_dd']:.1f}%",
            f"    Trades:       {best['trades']}",
            "",
            "  TOP 5:",
            f"  {'SL%':>5} {'Trail%':>7} {'Pos%':>5} {'P&L':>10} {'WR':>5} {'DD':>6} {'Score':>7}",
            "  " + "-" * 50,
        ]
        for r in result.get("top5", []):
            lines.append(f"  {r['sl']:>5} {r['trail']:>7} {r['pos']:>5} "
                        f"{r['pnl']:>+10.2f} {r['win_rate']:>4.0f}% {r['max_dd']:>5.1f}% {r['score']:>7.1f}")
        lines.append("=" * 65)
        return "\n".join(lines)

    def get_status(self):
        return {"running": self.is_running, "results": len(self.all_results),
                "best": self.best_result}
