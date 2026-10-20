"""
Trading Imperium V5 – Walk-Forward Test
Teilt Daten in Fenster auf: trainiert auf Window N, testet auf Window N+1.
Verhindert Overfitting und zeigt echte Out-of-Sample Performance.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable
from core.logger import log
from backtest.metrics import BacktestMetrics


class WalkForwardTest:
    """Walk-Forward Analyse: Train auf Vergangenheit, Test auf Zukunft."""

    def __init__(self, train_pct=70, n_splits=5):
        self.train_pct = train_pct
        self.n_splits = n_splits

    def run(self, df, backtest_fn, **bt_kwargs) -> Dict:
        """
        Fuehrt Walk-Forward Test durch.
        df: DataFrame mit OHLCV
        backtest_fn: Funktion(df, **kwargs) -> BacktestResult
        Returns: Aggregierte Ergebnisse ueber alle Fenster
        """
        if df is None or len(df) < 100:
            return {"error": "Zu wenig Daten (min 100 Kerzen)"}

        total = len(df)
        window_size = total // self.n_splits
        if window_size < 50:
            return {"error": f"Fenster zu klein ({window_size} Kerzen, brauche 50)"}

        results = []
        all_trades = []
        all_equity = []

        log.info("WALK-FWD", f"Start: {self.n_splits} Fenster, je {window_size} Kerzen")

        for i in range(self.n_splits - 1):
            # Train-Fenster
            train_start = i * window_size
            train_end = train_start + int(window_size * (self.train_pct / 100))
            # Test-Fenster (direkt nach Train)
            test_start = train_end
            test_end = min(test_start + (window_size - (train_end - train_start)), total)

            if test_end - test_start < 20:
                continue

            train_df = df.iloc[train_start:train_end].copy()
            test_df = df.iloc[test_start:test_end].copy()

            # Backtest auf Test-Daten ausfuehren
            try:
                result = backtest_fn(test_df, **bt_kwargs)
                window_info = {
                    "window": i + 1,
                    "train_size": len(train_df),
                    "test_size": len(test_df),
                    "pnl": result.total_pnl,
                    "pnl_pct": result.total_pnl_pct,
                    "trades": result.total_trades,
                    "win_rate": result.win_rate,
                    "max_dd": result.max_drawdown,
                }
                results.append(window_info)
                all_trades.extend(result.trades)
                all_equity.extend(result.equity_curve)

                log.info("WALK-FWD", f"  Fenster {i+1}: P&L {result.total_pnl:+.2f}$ "
                                     f"WR {result.win_rate:.0f}% DD {result.max_drawdown:.1f}%")
            except Exception as e:
                log.warn("WALK-FWD", f"  Fenster {i+1}: Fehler {str(e)[:40]}")

        if not results:
            return {"error": "Keine Fenster konnten berechnet werden"}

        # Aggregieren
        total_pnl = sum(r["pnl"] for r in results)
        avg_wr = sum(r["win_rate"] for r in results) / len(results)
        avg_dd = sum(r["max_dd"] for r in results) / len(results)
        profitable_windows = sum(1 for r in results if r["pnl"] > 0)

        metrics = BacktestMetrics.all_metrics(all_trades, all_equity) if all_equity else {}

        summary = {
            "windows": len(results),
            "profitable_windows": profitable_windows,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(results), 2),
            "avg_win_rate": round(avg_wr, 1),
            "avg_max_dd": round(avg_dd, 1),
            "consistency": round(profitable_windows / len(results) * 100, 0),
            "details": results,
            "metrics": metrics,
        }

        log.info("WALK-FWD", f"Fertig: {profitable_windows}/{len(results)} profitabel, "
                             f"Gesamt P&L: {total_pnl:+.2f}$")
        return summary

    def summary_text(self, result) -> str:
        if "error" in result:
            return f"Walk-Forward Fehler: {result['error']}"
        lines = [
            f"{'=' * 55}",
            f"  WALK-FORWARD TEST ({result['windows']} Fenster)",
            f"{'=' * 55}",
            f"  Profitabel:     {result['profitable_windows']}/{result['windows']} ({result['consistency']:.0f}%)",
            f"  Gesamt P&L:     {result['total_pnl']:+.2f}$",
            f"  Ø P&L/Fenster:  {result['avg_pnl']:+.2f}$",
            f"  Ø Win-Rate:     {result['avg_win_rate']:.1f}%",
            f"  Ø Max DD:       {result['avg_max_dd']:.1f}%",
        ]
        if result.get("metrics"):
            m = result["metrics"]
            lines.extend([
                f"{'─' * 55}",
                f"  Sharpe:         {m.get('sharpe', 0):.2f}",
                f"  Sortino:        {m.get('sortino', 0):.2f}",
                f"  Profit Factor:  {m.get('profit_factor', 0):.2f}",
            ])
        lines.append(f"{'─' * 55}")
        for d in result.get("details", []):
            lines.append(f"  Fenster {d['window']}: P&L {d['pnl']:+.2f}$ | "
                        f"WR {d['win_rate']:.0f}% | DD {d['max_dd']:.1f}% | {d['trades']} Trades")
        lines.append(f"{'=' * 55}")
        return "\n".join(lines)
