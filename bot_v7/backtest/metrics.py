"""
Trading Imperium V5 – Backtest Metrics
Alle Performance-Kennzahlen an einem Ort.
"""
import numpy as np
import pandas as pd
from typing import Dict, List


class BacktestMetrics:
    """Berechnet alle wichtigen Trading-Kennzahlen."""

    @staticmethod
    def sharpe_ratio(equity_curve, risk_free_rate=0.0, periods=252):
        """Sharpe Ratio (annualisiert)."""
        if len(equity_curve) < 10:
            return 0.0
        returns = pd.Series(equity_curve).pct_change().dropna()
        if returns.std() == 0:
            return 0.0
        excess = returns.mean() - (risk_free_rate / periods)
        return round((excess / returns.std()) * np.sqrt(periods), 2)

    @staticmethod
    def sortino_ratio(equity_curve, risk_free_rate=0.0, periods=252):
        """Sortino Ratio (nur Downside-Risiko)."""
        if len(equity_curve) < 10:
            return 0.0
        returns = pd.Series(equity_curve).pct_change().dropna()
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 99.0
        excess = returns.mean() - (risk_free_rate / periods)
        return round((excess / downside.std()) * np.sqrt(periods), 2)

    @staticmethod
    def max_drawdown(equity_curve):
        """Maximaler Drawdown in Prozent."""
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = ((peak - val) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    @staticmethod
    def max_drawdown_duration(equity_curve):
        """Laengste Drawdown-Dauer in Perioden."""
        if not equity_curve:
            return 0
        peak = equity_curve[0]
        dd_start = 0
        max_dur = 0
        in_dd = False
        for i, val in enumerate(equity_curve):
            if val >= peak:
                peak = val
                if in_dd:
                    dur = i - dd_start
                    max_dur = max(max_dur, dur)
                in_dd = False
            else:
                if not in_dd:
                    dd_start = i
                    in_dd = True
        if in_dd:
            max_dur = max(max_dur, len(equity_curve) - dd_start)
        return max_dur

    @staticmethod
    def profit_factor(trades):
        """Profit Factor = Bruttogewinn / Bruttoverlust."""
        gross_profit = sum(t["pnl"] for t in trades if t.get("type") == "SELL" and t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t.get("type") == "SELL" and t.get("pnl", 0) < 0))
        return round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0

    @staticmethod
    def win_rate(trades):
        """Win-Rate in Prozent."""
        sells = [t for t in trades if t.get("type") == "SELL"]
        if not sells:
            return 0.0
        wins = sum(1 for t in sells if t.get("pnl", 0) > 0)
        return round(wins / len(sells) * 100, 1)

    @staticmethod
    def avg_trade(trades):
        """Durchschnittlicher Trade-P&L."""
        sells = [t["pnl"] for t in trades if t.get("type") == "SELL" and "pnl" in t]
        return round(sum(sells) / len(sells), 2) if sells else 0.0

    @staticmethod
    def avg_win_loss_ratio(trades):
        """Verhaeltnis durchschnittlicher Gewinn / durchschnittlicher Verlust."""
        wins = [t["pnl"] for t in trades if t.get("type") == "SELL" and t.get("pnl", 0) > 0]
        losses = [abs(t["pnl"]) for t in trades if t.get("type") == "SELL" and t.get("pnl", 0) < 0]
        avg_w = sum(wins) / len(wins) if wins else 0
        avg_l = sum(losses) / len(losses) if losses else 1
        return round(avg_w / avg_l, 2) if avg_l > 0 else 99.0

    @staticmethod
    def max_consecutive_losses(trades):
        """Maximale Verlustserie."""
        sells = [t for t in trades if t.get("type") == "SELL"]
        max_streak = 0
        current = 0
        for t in sells:
            if t.get("pnl", 0) < 0:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak

    @staticmethod
    def calmar_ratio(equity_curve):
        """Calmar Ratio = Jahresrendite / Max Drawdown."""
        if len(equity_curve) < 2:
            return 0.0
        total_return = (equity_curve[-1] / equity_curve[0] - 1) * 100
        dd = BacktestMetrics.max_drawdown(equity_curve)
        return round(total_return / dd, 2) if dd > 0 else 99.0

    @staticmethod
    def all_metrics(trades, equity_curve):
        """Berechnet ALLE Kennzahlen auf einmal."""
        return {
            "sharpe": BacktestMetrics.sharpe_ratio(equity_curve),
            "sortino": BacktestMetrics.sortino_ratio(equity_curve),
            "calmar": BacktestMetrics.calmar_ratio(equity_curve),
            "max_drawdown": BacktestMetrics.max_drawdown(equity_curve),
            "max_dd_duration": BacktestMetrics.max_drawdown_duration(equity_curve),
            "profit_factor": BacktestMetrics.profit_factor(trades),
            "win_rate": BacktestMetrics.win_rate(trades),
            "avg_trade": BacktestMetrics.avg_trade(trades),
            "win_loss_ratio": BacktestMetrics.avg_win_loss_ratio(trades),
            "max_loss_streak": BacktestMetrics.max_consecutive_losses(trades),
            "total_trades": len([t for t in trades if t.get("type") == "SELL"]),
        }
