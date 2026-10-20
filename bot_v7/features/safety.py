"""
Live-Trading Safety Module

Drei Klassen:
1. CashReservation - verhindert parallele BUYs die Cash ueberziehen
2. RateLimitTracker - trackt API-Aufrufe (Sliding Window)
3. RejectionCounter - Auto-Sleep nach zuvielen Rejects in Folge
"""
import threading
import time
from collections import deque
from typing import Dict, Optional

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a, **kw): pass
        def warn(self, *a, **kw): pass
        def error(self, *a, **kw): pass
    log = _Log()


class CashReservation:
    """Thread-safe Cash-Reservation gegen Race Conditions.

    Workflow:
      1. Vor BUY: reserve(client_id, amount, current_balance)
      2. Wenn True: Order ausfuehren
      3. Nach Fill/Reject/Error: release(client_id)

    Auto-Cleanup: Reservations alt > 60s werden automatisch freigegeben.
    """

    def __init__(self, timeout_sec: int = 60):
        self._lock = threading.RLock()
        self._reservations: Dict[str, Dict] = {}  # client_id -> {amount, ts}
        self._timeout = timeout_sec
        self._total_reserved_count = 0
        self._total_rejected_count = 0

    def _cleanup_expired(self):
        """Loescht abgelaufene Reservations. Caller hat Lock."""
        now = time.time()
        expired = [cid for cid, r in self._reservations.items()
                   if now - r["ts"] > self._timeout]
        for cid in expired:
            del self._reservations[cid]
            log.warn("SAFETY", f"Cash-Reservation expired (Timeout {self._timeout}s): {cid[:30]}")

    def reserve(self, client_id: str, amount: float, current_balance: float) -> bool:
        """Versuche, amount aus current_balance zu reservieren.

        Returns True bei Erfolg, False bei Nicht-Genug-Cash.
        """
        with self._lock:
            self._cleanup_expired()
            total_reserved = sum(r["amount"] for r in self._reservations.values())
            available = current_balance - total_reserved

            if amount > available:
                self._total_rejected_count += 1
                log.warn("SAFETY",
                         f"Cash-Reserve abgelehnt: {amount:.2f}$ benoetigt, "
                         f"{available:.2f}$ frei ({len(self._reservations)} pending)")
                return False

            self._reservations[client_id] = {"amount": amount, "ts": time.time()}
            self._total_reserved_count += 1
            return True

    def release(self, client_id: str):
        """Reservation aufheben (immer aufrufen nach Order-Versuch)."""
        with self._lock:
            self._reservations.pop(client_id, None)

    def get_reserved_total(self) -> float:
        with self._lock:
            self._cleanup_expired()
            return sum(r["amount"] for r in self._reservations.values())

    def get_status(self) -> Dict:
        with self._lock:
            self._cleanup_expired()
            return {
                "open_reservations": len(self._reservations),
                "total_reserved_usd": round(sum(r["amount"] for r in self._reservations.values()), 2),
                "total_reserve_count": self._total_reserved_count,
                "total_rejected_count": self._total_rejected_count,
            }


class RateLimitTracker:
    """Tracked API-Calls fuer Binance-Weight-Limits.

    Binance Spot: 1200 weight / minute
    Wir nutzen 1000 als Soft-Limit (200 Buffer).

    Typische Weights:
      create_market_buy_order = 6
      fetch_balance = 10
      fetch_ticker = 2
      fetch_open_orders = 6
    """

    def __init__(self, limit_per_minute: int = 1000):
        self._lock = threading.RLock()
        self._calls = deque()  # (timestamp, weight) tuples
        self._limit = limit_per_minute
        self._window_sec = 60
        self._total_calls = 0
        self._total_blocked = 0

    def _cleanup_old(self):
        """Entferne Aufrufe aelter als 60s. Caller hat Lock."""
        cutoff = time.time() - self._window_sec
        while self._calls and self._calls[0][0] < cutoff:
            self._calls.popleft()

    def check_and_consume(self, weight: int = 1) -> bool:
        """Pruefe ob weight noch im Budget ist und verbrauche es.

        Returns True wenn ok, False wenn Limit erreicht.
        """
        with self._lock:
            self._cleanup_old()
            current_usage = sum(w for _, w in self._calls)

            if current_usage + weight > self._limit:
                self._total_blocked += 1
                log.warn("SAFETY",
                         f"Rate-Limit erreicht: {current_usage}/{self._limit} weight "
                         f"in 60s - Call blockiert (weight {weight})")
                return False

            self._calls.append((time.time(), weight))
            self._total_calls += 1
            return True

    def get_usage(self) -> Dict:
        with self._lock:
            self._cleanup_old()
            current = sum(w for _, w in self._calls)
            return {
                "current_weight": current,
                "limit": self._limit,
                "usage_pct": round(current / self._limit * 100, 1) if self._limit else 0,
                "total_calls": self._total_calls,
                "total_blocked": self._total_blocked,
            }


class RejectionCounter:
    """Auto-Sleep nach zuvielen Rejected Orders in Folge.

    Workflow:
      1. Nach Order-Fill: reset()
      2. Nach Order-Reject/Error: increment()
      3. Wenn count >= max_in_row: is_sleeping() returns True bis sleep_duration vorbei
    """

    def __init__(self, max_in_row: int = 10, sleep_duration_sec: int = 900):
        self._lock = threading.Lock()
        self._count = 0
        self._sleep_until = 0.0
        self._max = max_in_row
        self._sleep_duration = sleep_duration_sec
        self._total_rejects = 0
        self._total_sleeps = 0

    def increment(self, reason: str = ""):
        """Bei Rejected Order aufrufen."""
        with self._lock:
            self._count += 1
            self._total_rejects += 1
            if self._count >= self._max:
                self._sleep_until = time.time() + self._sleep_duration
                self._total_sleeps += 1
                self._count = 0  # Reset counter
                log.warn("SAFETY",
                         f"REJECTION-LIMIT: {self._max} Rejects in Folge! "
                         f"Bot pausiert {self._sleep_duration//60} Min "
                         f"(Letzter Grund: {reason[:80]})")

    def reset(self):
        """Bei Filled Order aufrufen."""
        with self._lock:
            self._count = 0

    def is_sleeping(self) -> bool:
        """True wenn Bot in Sleep-Mode ist (sollte keine neuen Orders senden)."""
        with self._lock:
            return time.time() < self._sleep_until

    def remaining_sleep_sec(self) -> int:
        with self._lock:
            remaining = max(0, self._sleep_until - time.time())
            return int(remaining)

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "rejects_in_row": self._count,
                "max_allowed": self._max,
                "sleeping": time.time() < self._sleep_until,
                "remaining_sleep_sec": int(max(0, self._sleep_until - time.time())),
                "total_rejects": self._total_rejects,
                "total_sleeps": self._total_sleeps,
            }
