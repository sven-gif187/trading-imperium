"""Tests fuer Execution: Circuit Breaker, Retry, Idempotency, OrderManager."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_circuit_breaker():
    from execution.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
    cb = CircuitBreaker(fail_threshold=3, reset_timeout=1)
    # Normal funktioniert
    assert cb.call(lambda: 42) == 42
    # Fehler zaehlen
    for _ in range(3):
        try:
            cb.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
    # Jetzt sollte er OPEN sein
    try:
        cb.call(lambda: 42)
        assert False, "Sollte CircuitBreakerOpenError werfen"
    except Exception as e:
        assert "gesperrt" in str(e).lower() or "CircuitBreaker" in type(e).__name__
    # Nach reset_timeout (1s) -> HALF_OPEN
    time.sleep(1.1)
    assert cb.call(lambda: 99) == 99
    assert cb.state.value == "closed"
    print("✅ CircuitBreaker OK")

def test_idempotency():
    from execution.idempotency import IdempotencyGuard
    ig = IdempotencyGuard(ttl=2)
    cid = ig.create_id("intent1", "BTC/USDC")
    assert ig.check_and_lock(cid)       # Erstes Mal: OK
    assert not ig.check_and_lock(cid)   # Zweites Mal: BLOCKIERT
    ig.release(cid)
    assert ig.check_and_lock(cid)       # Nach Release: wieder OK
    ig.release(cid)
    print("✅ IdempotencyGuard OK")

def test_order_manager():
    from execution.order_manager import OrderManager
    om = OrderManager()
    om.history = []  # Reset
    # Order platzieren
    o = om.place("test_001", "BTC/USDC", "BUY", 100, "MACD", "Test-Buy")
    assert o["status"] == "pending"
    assert len(om.get_open_orders()) == 1
    # Fill
    om.update_fill("test_001", "binance_123", 67000, 0.00149, 0.1)
    assert len(om.get_open_orders()) == 0
    assert len(om.get_history()) == 1
    assert om.get_history()[0]["status"] == "filled"
    # Stats
    stats = om.get_stats()
    assert stats["total_filled"] >= 1
    print("✅ OrderManager OK")

def test_retry_policy():
    from execution.retry_policy import RetryPolicy
    rp = RetryPolicy(max_retries=2, base_delay=0.01, max_delay=0.1)
    # Erfolgreicher Call
    assert rp.execute(lambda: "ok") == "ok"
    # Call der erst beim 2. Versuch klappt
    attempts = [0]
    def flaky():
        attempts[0] += 1
        if attempts[0] < 2:
            raise ConnectionError("test")
        return "success"
    assert rp.execute(flaky) == "success"
    assert attempts[0] == 2
    print("✅ RetryPolicy OK")

if __name__ == "__main__":
    test_circuit_breaker()
    test_idempotency()
    test_order_manager()
    test_retry_policy()
    print("\n🎯 Alle Execution-Tests bestanden!")
