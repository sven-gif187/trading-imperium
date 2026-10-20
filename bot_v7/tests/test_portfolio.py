"""Tests fuer Portfolio Agent, Rebalancer, Correlation Guard."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_correlation_guard():
    from portfolio.correlation_guard import CorrelationGuard
    cg = CorrelationGuard(max_sector_coins=3)
    positions = {
        "SOL": {"active": True}, "ADA": {"active": True}, "AVAX": {"active": True}
    }
    # 3 L1-Coins schon da -> 4. wird blockiert
    r = cg.check("NEAR/USDC", positions)
    assert not r["ok"]
    assert "Sektor" in r["reason"] or "3" in r["reason"]
    # Anderer Sektor -> OK
    r = cg.check("LINK/USDC", positions)
    assert r["ok"]
    # Portfolio-Korrelation
    corr = cg.get_portfolio_correlation(positions)
    assert corr["avg_correlation"] > 0.5  # Alle L1 = hoch korreliert
    print("✅ CorrelationGuard OK")

def test_rebalancer():
    from portfolio.rebalancer import Rebalancer
    rb = Rebalancer(threshold_pct=5, min_trade_usd=10)
    positions = {"BTC": {"value": 3000}, "ETH": {"value": 1000}}
    target = {"BTC": 50, "ETH": 30}
    trades = rb.calculate_trades(positions, 10000, target, {"BTC/USDC": 67000, "ETH/USDC": 2000})
    # BTC ist 30% (soll 50%) -> Kauf, ETH ist 10% (soll 30%) -> Kauf
    buy_trades = [t for t in trades if t["action"] == "BUY"]
    assert len(buy_trades) >= 1
    print("✅ Rebalancer OK")

def test_sector_breakdown():
    from portfolio.correlation_guard import CorrelationGuard
    cg = CorrelationGuard()
    positions = {
        "BTC": {"active": True}, "ETH": {"active": True},
        "SOL": {"active": True}, "LINK": {"active": True},
    }
    sectors = cg.get_sector_breakdown(positions)
    assert "L1" in sectors
    assert "defi" in sectors
    assert "ETH" in sectors["L1"]
    print("✅ SectorBreakdown OK")

if __name__ == "__main__":
    test_correlation_guard()
    test_rebalancer()
    test_sector_breakdown()
    print("\n🎯 Alle Portfolio-Tests bestanden!")
