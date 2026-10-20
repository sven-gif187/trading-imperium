"""Tests fuer Backtest Engine, Fees, Slippage, Metrics, Monte Carlo."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_fees():
    from backtest.fees import FeeCalculator
    fc = FeeCalculator("binance")
    fee = fc.calculate(1000, "taker")
    assert 0.5 < fee < 2.0  # 0.1% von 1000 = 1.0
    rt = fc.calculate_roundtrip(1000)
    assert rt > fee
    be = fc.breakeven_pct()
    assert be > 0
    print("✅ FeeCalculator OK")

def test_slippage():
    from backtest.slippage import SlippageModel
    sm = SlippageModel(base_bps=5)
    r = sm.calculate(67000, 100, side="buy")
    assert r["price"] > 67000  # Kauf = hoeherer Preis
    r = sm.calculate(67000, 100, side="sell")
    assert r["price"] < 67000  # Verkauf = niedrigerer Preis
    assert r["slippage_pct"] > 0
    print("✅ SlippageModel OK")

def test_metrics():
    from backtest.metrics import BacktestMetrics
    equity = [10000, 10100, 10050, 10200, 10300, 10150, 10400, 10500]
    trades = [
        {"type": "SELL", "pnl": 100}, {"type": "SELL", "pnl": -50},
        {"type": "SELL", "pnl": 150}, {"type": "SELL", "pnl": 100},
        {"type": "SELL", "pnl": -150}, {"type": "SELL", "pnl": 200},
    ]
    m = BacktestMetrics.all_metrics(trades, equity)
    assert m["win_rate"] > 50
    assert m["profit_factor"] > 1
    assert m["max_drawdown"] > 0
    assert m["total_trades"] == 6
    assert m["max_loss_streak"] >= 1
    assert "sharpe" in m
    assert "sortino" in m
    print("✅ BacktestMetrics OK")

def test_monte_carlo():
    from backtest.monte_carlo import MonteCarloSim
    trades = [{"type": "SELL", "pnl": p} for p in [10, -5, 15, -3, 8, 12, -7, 20, -2, 6]]
    mc = MonteCarloSim(n_simulations=100)
    r = mc.run(trades, 10000)
    assert "final" in r
    assert r["final"]["median"] > 0
    assert r["profit_probability"] > 0
    assert "ruin_probability" in r
    print("✅ MonteCarlo OK")

if __name__ == "__main__":
    test_fees()
    test_slippage()
    test_metrics()
    test_monte_carlo()
    print("\n🎯 Alle Backtest-Tests bestanden!")
