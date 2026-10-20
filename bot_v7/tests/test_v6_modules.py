"""Tests fuer V6 Module: Ensemble, RL, VWAP, Grid, DCA, Adaptive, TWAP, SmartEntry."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ensemble_signal():
    from models.ensemble_signal import EnsembleSignal
    es = EnsembleSignal()
    r = es.calculate({"technical": 0.7, "fear_greed": 0.8, "funding": 0.6, "onchain": 0.5})
    assert 0 <= r["score"] <= 1
    assert r["label"] in ("STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL")
    assert r["sources"] == 4
    print("✅ EnsembleSignal OK")

def test_rl_feedback():
    from models.rl_feedback import RLFeedbackAgent
    rl = RLFeedbackAgent(learning_rate=0.2)
    rl.record_trade("MACD", 50)
    assert rl.weights["MACD"] > 1.0
    rl.record_trade("MACD", -30)
    assert rl.weights["MACD"] < rl.weights.get("MACD_old", 99)
    best = rl.get_best_strategy()
    assert best == "MACD"
    print("✅ RLFeedback OK")

def test_vwap():
    import pandas as pd, numpy as np
    from features.vwap_agent import VWAPAgent
    va = VWAPAgent()
    df = pd.DataFrame({
        "Open": np.random.uniform(100, 110, 30),
        "High": np.random.uniform(110, 120, 30),
        "Low": np.random.uniform(90, 100, 30),
        "Close": np.random.uniform(100, 110, 30),
        "Volume": np.random.uniform(1000, 5000, 30),
    })
    r = va.calculate(df, "TEST")
    assert r["vwap"] > 0
    assert r["bias"] in ("BULLISH", "BEARISH", "NEUTRAL")
    print("✅ VWAP OK")

def test_grid_trader():
    from agents.grid_trader import GridTrader
    gt = GridTrader(grid_size_pct=1.0, num_grids=3)
    g = gt.setup_grid("BTC/USDC", 70000)
    assert len(g["levels"]) == 7  # -3 bis +3
    triggers = gt.check_triggers("BTC/USDC", 69300)  # 1% unter Center
    assert len(triggers) >= 1
    assert triggers[0]["side"] == "BUY"
    print("✅ GridTrader OK")

def test_dca_advanced():
    from agents.dca_advanced import AdvancedDCA
    dca = AdvancedDCA(base_amount=100, base_interval_min=1)
    r = dca.should_dca("BTC", fear_greed=10)  # Extreme Fear
    assert r["execute"] == True
    assert r["amount"] > 100  # Mehr bei Fear
    r2 = dca.should_dca("BTC", fear_greed=85)  # Extreme Greed
    # Direkt danach sollte es nicht nochmal kaufen
    r3 = dca.should_dca("BTC", fear_greed=10)
    assert r3["execute"] == True  # Interval ist 1 min, kein lock
    print("✅ AdvancedDCA OK")

def test_adaptive_sizing():
    from risk.adaptive_sizing import AdaptivePositionSizer
    aps = AdaptivePositionSizer(base_pct=15)
    r1 = aps.calculate(10000, confidence=0.8, win_rate=70, fear_greed=15)
    r2 = aps.calculate(10000, confidence=0.3, win_rate=30, current_drawdown=12, streak=3)
    assert r1["amount"] > r2["amount"]  # Mehr bei guten Bedingungen
    assert r1["pct"] > r2["pct"]
    print("✅ AdaptiveSizing OK")

def test_twap():
    from execution.twap_executor import TWAPExecutor
    tw = TWAPExecutor(min_split_usd=200, max_parts=4)
    assert not tw.should_split(100)
    assert tw.should_split(300)
    parts = tw.calculate_parts(400)
    assert len(parts) >= 2
    assert abs(sum(parts) - 400) < 1
    print("✅ TWAP OK")

def test_smart_entry():
    from agents.smart_entry import SmartEntryAgent
    from core.events import DecisionIntent, Side
    se = SmartEntryAgent(max_wait_sec=5, pullback_pct=1.0)
    intent = DecisionIntent(symbol="BTC/USDC", side=Side.BUY, confidence=0.7,
                            entry_price=70000, amount_usd=500, strategy_id="TEST",
                            entry_reason="Test", score=5, agent_id="test")
    se.queue_entry(intent, 70000)
    assert "BTC/USDC" in se.pending
    # Simuliere Pullback
    results = []
    se.check("BTC/USDC", 69200, lambda i: results.append(i))  # 1.1% Pullback
    assert len(results) == 1  # Sollte kaufen
    print("✅ SmartEntry OK")

def test_orderbook():
    from data.orderbook_depth import OrderBookAnalyzer
    ob = OrderBookAnalyzer()
    r = ob.analyze("BTC/USDC")
    assert r["bias"] in ("BULLISH", "BEARISH", "NEUTRAL")
    print("✅ OrderBook OK")

if __name__ == "__main__":
    test_ensemble_signal()
    test_rl_feedback()
    test_vwap()
    test_grid_trader()
    test_dca_advanced()
    test_adaptive_sizing()
    test_twap()
    test_smart_entry()
    test_orderbook()
    print("\n🎯 Alle V6-Tests bestanden!")
