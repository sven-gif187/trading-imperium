"""Fuehrt alle Tests aus."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("  TRADING IMPERIUM V6 – TEST SUITE")
print("=" * 60)

from tests.test_risk import *
from tests.test_execution import *
from tests.test_backtest import *
from tests.test_portfolio import *
from tests.test_data import *
from tests.test_v6_modules import *

print("\n" + "=" * 60)
test_kill_switch()
test_drawdown_guard()
test_exposure()
test_position_sizing()
print("─" * 60)
test_circuit_breaker()
test_idempotency()
test_order_manager()
test_retry_policy()
print("─" * 60)
test_fees()
test_slippage()
test_metrics()
test_monte_carlo()
print("─" * 60)
test_correlation_guard()
test_rebalancer()
test_sector_breakdown()
print("─" * 60)
test_cache()
test_data_quality()
test_sentiment()
print("─" * 60)
test_ensemble_signal()
test_rl_feedback()
test_vwap()
test_grid_trader()
test_dca_advanced()
test_adaptive_sizing()
test_twap()
test_smart_entry()
test_orderbook()
print("=" * 60)
print("🏆 ALLE TESTS BESTANDEN!")
print("=" * 60)
