"""
Trading Imperium V5 – Backtest Engine
Simuliert Trading auf historischen Daten mit realistischen Fees + Slippage.
Berechnet Kennzahlen: Sharpe, Drawdown, Win-Rate, Profit Factor.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from core.logger import log


class BacktestResult:
    """Ergebnis eines Backtests."""
    def __init__(self):
        self.trades = []
        self.equity_curve = []
        self.initial_balance = 0
        self.final_balance = 0
        self.coin = ""
        self.timeframe = ""
        self.period = ""

    @property
    def total_pnl(self):
        return self.final_balance - self.initial_balance

    @property
    def total_pnl_pct(self):
        return ((self.final_balance / self.initial_balance) - 1) * 100 if self.initial_balance > 0 else 0

    @property
    def total_trades(self):
        return len([t for t in self.trades if t["type"] == "SELL"])

    @property
    def wins(self):
        return len([t for t in self.trades if t["type"] == "SELL" and t.get("pnl", 0) > 0])

    @property
    def losses(self):
        return len([t for t in self.trades if t["type"] == "SELL" and t.get("pnl", 0) <= 0])

    @property
    def win_rate(self):
        return (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0

    @property
    def max_drawdown(self):
        if not self.equity_curve:
            return 0
        peak = self.equity_curve[0]
        max_dd = 0
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = ((peak - val) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    @property
    def profit_factor(self):
        gross_profit = sum(t["pnl"] for t in self.trades if t["type"] == "SELL" and t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trades if t["type"] == "SELL" and t.get("pnl", 0) < 0))
        return round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0

    @property
    def avg_trade_pnl(self):
        sells = [t["pnl"] for t in self.trades if t["type"] == "SELL"]
        return round(sum(sells) / len(sells), 2) if sells else 0

    @property
    def sharpe_ratio(self):
        if not self.equity_curve or len(self.equity_curve) < 10:
            return 0
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if returns.std() == 0:
            return 0
        return round((returns.mean() / returns.std()) * np.sqrt(252), 2)

    def summary(self) -> Dict:
        return {
            "coin": self.coin, "timeframe": self.timeframe, "period": self.period,
            "initial": round(self.initial_balance, 2), "final": round(self.final_balance, 2),
            "pnl": round(self.total_pnl, 2), "pnl_pct": round(self.total_pnl_pct, 2),
            "trades": self.total_trades, "wins": self.wins, "losses": self.losses,
            "win_rate": round(self.win_rate, 1), "max_drawdown": self.max_drawdown,
            "profit_factor": self.profit_factor, "avg_trade": self.avg_trade_pnl,
            "sharpe": self.sharpe_ratio,
        }

    def summary_text(self) -> str:
        s = self.summary()
        return (f"{'═' * 50}\n"
                f"  BACKTEST: {s['coin']} | {s['timeframe']} | {s['period']}\n"
                f"{'═' * 50}\n"
                f"  Start:        {s['initial']:>10,.2f}$\n"
                f"  Ende:         {s['final']:>10,.2f}$\n"
                f"  P&L:          {s['pnl']:>+10,.2f}$ ({s['pnl_pct']:+.2f}%)\n"
                f"{'─' * 50}\n"
                f"  Trades:       {s['trades']:>10}\n"
                f"  Wins:         {s['wins']:>10}\n"
                f"  Losses:       {s['losses']:>10}\n"
                f"  Win-Rate:     {s['win_rate']:>9.1f}%\n"
                f"  Max Drawdown: {s['max_drawdown']:>9.1f}%\n"
                f"  Profit Factor:{s['profit_factor']:>9.2f}\n"
                f"  Avg Trade:    {s['avg_trade']:>+9.2f}$\n"
                f"  Sharpe Ratio: {s['sharpe']:>9.2f}\n"
                f"{'═' * 50}")


class BacktestEngine:
    """Fuehrt Backtests auf historischen Daten aus."""

    def __init__(self, config=None, exchange="binance"):
        from backtest.fees import FeeCalculator
        from backtest.slippage import SlippageModel
        from backtest.metrics import BacktestMetrics
        self.fee_calc = FeeCalculator(exchange)
        self.slippage = SlippageModel(base_bps=5)
        self.metrics = BacktestMetrics
        self.config = config

    def run(self, df: pd.DataFrame, coin: str = "BTC/USDC",
            initial_balance: float = 10000, strategy: str = "multi_signal",
            stop_loss_pct: float = 4.0, trailing_pct: float = 1.5,
            position_size_pct: float = 20.0) -> BacktestResult:
        """
        Führt einen Backtest auf einem DataFrame aus.
        df muss Spalten haben: Open, High, Low, Close, Volume (+ Index als Date)
        """
        result = BacktestResult()
        result.initial_balance = initial_balance
        result.coin = coin
        result.timeframe = "?"

        if df is None or len(df) < 50:
            result.final_balance = initial_balance
            return result

        # Indikatoren berechnen
        df = self._add_indicators(df)

        balance = initial_balance
        position = None  # {"entry": price, "qty": qty, "highest": price}
        result.equity_curve = [balance]

        for i in range(50, len(df)):
            price = df["Close"].iloc[i]
            high = df["High"].iloc[i]
            row = df.iloc[i]

            if position is None:
                # Kein Trade offen → Kaufsignal prüfen
                score = self._calc_signal_score(row, strategy)
                if score >= 4:
                    amount = balance * (position_size_pct / 100)
                    fee = self.fee_calc.calculate(amount)
                    slip_info = self.slippage.calculate(price, amount, avg_volume=0, side="buy"); slip = slip_info["slippage_usd"]
                    cost = amount + fee + slip
                    if cost > balance:
                        continue
                    qty = (amount - fee - slip) / price
                    balance -= cost
                    position = {"entry": price, "qty": qty, "highest": price, "score": score}
                    result.trades.append({
                        "type": "BUY", "price": price, "qty": qty,
                        "amount": cost, "time": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(i),
                    })
            else:
                # Trade offen → Verkaufssignal prüfen
                position["highest"] = max(position["highest"], high)
                entry = position["entry"]
                pnl_pct = ((price / entry) - 1) * 100
                fall_from_high = ((position["highest"] - price) / position["highest"]) * 100

                sell = False
                reason = ""

                # Stop-Loss
                if stop_loss_pct > 0 and pnl_pct <= -stop_loss_pct:
                    sell = True
                    reason = "Stop-Loss"

                # Trailing Stop
                elif trailing_pct > 0 and pnl_pct > 0.3 and fall_from_high >= trailing_pct:
                    sell = True
                    reason = "Trailing-Stop"

                # RSI überkauft
                elif row.get("RSI", 50) > 80 and pnl_pct > 1.0:
                    sell = True
                    reason = "RSI overbought"

                if sell:
                    revenue = position["qty"] * price
                    fee = self.fee_calc.calculate(revenue)
                    slip_info = self.slippage.calculate(price, revenue, avg_volume=0, side="sell"); slip = slip_info["slippage_usd"]
                    net = revenue - fee - slip
                    pnl = net - (position["qty"] * entry)
                    balance += net
                    result.trades.append({
                        "type": "SELL", "price": price, "qty": position["qty"],
                        "amount": net, "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
                        "reason": reason,
                        "time": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(i),
                    })
                    position = None

            # Equity aktualisieren
            equity = balance
            if position:
                equity += position["qty"] * price
            result.equity_curve.append(equity)

        # Falls noch Position offen → zum Schlusskurs schließen
        if position:
            price = df["Close"].iloc[-1]
            revenue = position["qty"] * price
            fee = self.fee_calc.calculate(revenue)
            net = revenue - fee
            pnl = net - (position["qty"] * position["entry"])
            balance += net
            result.trades.append({
                "type": "SELL", "price": price, "qty": position["qty"],
                "amount": net, "pnl": round(pnl, 2), "reason": "End-of-Test",
            })

        result.final_balance = balance
        result.period = f"{len(df)} Kerzen"
        return result

    def run_multi(self, data_agent, coins: List[str], timeframe: str = "1h",
                  limit: int = 500, **kwargs) -> List[BacktestResult]:
        """Backtest über mehrere Coins mit Live-Daten."""
        results = []
        for coin in coins:
            try:
                snap = data_agent.fetch_snapshot(coin, timeframe, limit)
                if snap and hasattr(snap, '_df'):
                    r = self.run(snap._df, coin=coin, **kwargs)
                    r.timeframe = timeframe
                    results.append(r)
                    log.info("BACKTEST", f"{coin}: P&L {r.total_pnl:+.2f}$ | "
                                         f"WR {r.win_rate:.0f}% | DD {r.max_drawdown:.1f}%")
            except Exception as e:
                log.error("BACKTEST", f"{coin}: {str(e)[:60]}")
        return results

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Berechnet alle nötigen Indikatoren."""
        df = df.copy()
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df["EMA20"] = ta.ema(df["Close"], length=20)
        df["EMA50"] = ta.ema(df["Close"], length=50)
        macd = ta.macd(df["Close"])
        if macd is not None:
            df["MACD"] = macd.iloc[:, 0]
            df["MACD_signal"] = macd.iloc[:, 2]
        bb = ta.bbands(df["Close"], length=20, std=2)
        if bb is not None:
            for c in bb.columns:
                df[c] = bb[c]
        try:
            h, l, c = df["High"], df["Low"], df["Close"]
            pdm = h.diff().clip(lower=0)
            mdm = (-l.diff()).clip(lower=0)
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            pdi = 100 * (pdm.rolling(14).mean() / atr)
            mdi = 100 * (mdm.rolling(14).mean() / atr)
            dx = (pdi - mdi).abs() / (pdi + mdi + 1e-10) * 100
            df["ADX"] = dx.rolling(14).mean()
        except Exception:
            df["ADX"] = 20
        return df

    def _calc_signal_score(self, row, strategy: str = "multi_signal") -> int:
        """Berechnet den Signal-Score für eine Kerze (wie V4 Signal Agent)."""
        score = 0
        rsi = row.get("RSI", 50)
        adx = row.get("ADX", 20)
        macd = row.get("MACD", 0)
        macd_sig = row.get("MACD_signal", 0)
        price = row.get("Close", 0)
        ema20 = row.get("EMA20", 0)
        ema50 = row.get("EMA50", 0)

        # RSI
        if rsi < 35:
            score += 2
        elif rsi < 45:
            score += 1

        # MACD Cross
        if macd > macd_sig and macd < 0:
            score += 2

        # EMA Trend
        if price > ema20 > ema50 and ema20 > 0:
            score += 1

        # ADX Trend
        if adx > 25:
            score += 1

        # Bollinger
        bbl = row.get("BBL_20_2.0", None)
        if bbl is not None and price < bbl and rsi < 40:
            score += 2

        return score

    def ranking(self, results: List[BacktestResult]) -> str:
        """Erstellt eine Rangliste aller Backtest-Ergebnisse."""
        if not results:
            return "Keine Ergebnisse."

        sorted_r = sorted(results, key=lambda r: r.total_pnl, reverse=True)
        lines = [f"{'═' * 65}",
                 f"  BACKTEST RANGLISTE ({len(results)} Coins)",
                 f"{'═' * 65}",
                 f"  {'#':<4}{'Coin':<12}{'P&L':>10}{'WR':>8}{'Trades':>8}{'DD':>8}{'Sharpe':>8}",
                 f"{'─' * 65}"]

        for i, r in enumerate(sorted_r):
            s = r.summary()
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f" {i+1}."
            coin = s["coin"].split("/")[0]
            lines.append(f"  {medal:<4}{coin:<12}{s['pnl']:>+10,.2f}{s['win_rate']:>7.0f}%"
                        f"{s['trades']:>8}{s['max_drawdown']:>7.1f}%{s['sharpe']:>8.2f}")

        best = sorted_r[0].summary()
        lines.append(f"{'─' * 65}")
        lines.append(f"  Bester: {best['coin'].split('/')[0]} mit {best['pnl']:+,.2f}$ "
                    f"({best['pnl_pct']:+.2f}%)")
        lines.append(f"{'═' * 65}")
        return "\n".join(lines)

    def walk_forward(self, df, n_splits=5, **kwargs):
        """Walk-Forward Test: trainiert auf Fenster N, testet auf N+1."""
        from backtest.walk_forward import WalkForwardTest
        wf = WalkForwardTest(n_splits=n_splits)
        return wf.run(df, lambda d, **kw: self.run(d, **{**kwargs, **kw}), **kwargs)

    def monte_carlo(self, trades, initial_balance=10000, n_sims=500):
        """Monte Carlo Simulation: mischt Trades zufaellig N mal."""
        from backtest.monte_carlo import MonteCarloSim
        mc = MonteCarloSim(n_simulations=n_sims)
        return mc.run(trades, initial_balance)

    def full_analysis(self, df, coin="BTC/USDC", **kwargs):
        """Komplette Analyse: Backtest + Walk-Forward + Monte Carlo."""
        from backtest.walk_forward import WalkForwardTest
        from backtest.monte_carlo import MonteCarloSim

        # 1. Normaler Backtest
        result = self.run(df, coin=coin, **kwargs)

        # 2. Walk-Forward
        wf = WalkForwardTest(n_splits=5)
        wf_result = wf.run(df, lambda d, **kw: self.run(d, coin=coin, **{**kwargs, **kw}), **kwargs)

        # 3. Monte Carlo
        mc = MonteCarloSim(n_simulations=500)
        mc_result = mc.run(result.trades, result.initial_balance)

        # 4. Erweiterte Metriken
        metrics = self.metrics.all_metrics(result.trades, result.equity_curve)

        return {
            "backtest": result,
            "walk_forward": wf_result,
            "monte_carlo": mc_result,
            "metrics": metrics,
            "fees_total": self.fee_calc.total_fees_paid,
            "slippage_total": self.slippage.total_slippage_usd,
        }
