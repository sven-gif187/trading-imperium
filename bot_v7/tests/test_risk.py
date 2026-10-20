"""Tests fuer Risk Engine, Exposure, Drawdown, KillSwitch, PositionSizing."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_kill_switch():
    from risk.kill_switch import KillSwitch
    ks = KillSwitch(max_daily_loss=50)
    assert not ks.active
    ks.add_loss(30)
    assert not ks.active
    ks.add_loss(25)
    assert ks.active
    ks.reset_daily()
    assert not ks.active
    print("✅ KillSwitch OK")

def test_drawdown_guard():
    from risk.drawdown_guard import DrawdownGuard
    dd = DrawdownGuard(max_drawdown_pct=10)
    dd.update(10000)
    dd.update(10500)
    assert dd.peak_equity == 10500
    triggered = dd.update(9000)
    assert triggered
    assert not dd.is_safe()
    dd.reset(10000)
    dd.update(10000)
    assert dd.is_safe()
    print("✅ DrawdownGuard OK")

def test_exposure():
    from risk.exposure import ExposureManager
    em = ExposureManager(max_coin_pct=20, max_sector_pct=40)
    positions = {"SOL/USDC": {"value": 1500}, "ADA/USDC": {"value": 1000}}
    r = em.check_coin_exposure("ETH/USDC", 2500, 10000, positions)
    assert not r["ok"]  # 25% > 20%
    r = em.check_coin_exposure("ETH/USDC", 1500, 10000, positions)
    assert r["ok"]  # 15% < 20%
    r = em.check_sector_exposure("AVAX/USDC", 1000, 10000, positions)
    assert r["ok"]  # 25+10 = 35% < 40%
    r = em.check_sector_exposure("AVAX/USDC", 2000, 10000, positions)
    assert not r["ok"]  # 25+20 = 45% > 40%
    print("✅ ExposureManager OK")

def test_position_sizing():
    from risk.position_sizing import PositionSizer
    ps = PositionSizer(default_pct=15, min_usd=5, max_pct=50)
    amt = ps.calculate(10000, confidence=0.8, cycle_phase="ACCUMULATION")
    assert 5 <= amt <= 5000
    bear = ps.calculate(10000, confidence=0.5, cycle_phase="DEEP_BEAR")
    bull = ps.calculate(10000, confidence=0.5, cycle_phase="ACCUMULATION")
    assert bear <= bull
    k = ps.kelly_fraction(win_rate=60, avg_win=20, avg_loss=10)
    assert 0 < k < 0.25
    print("✅ PositionSizer OK")

if __name__ == "__main__":
    test_kill_switch()
    test_drawdown_guard()
    test_exposure()
    test_position_sizing()
    print("\n🎯 Alle Risk-Tests bestanden!")
