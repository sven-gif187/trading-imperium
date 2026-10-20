"""
Trading Imperium V5 – Circuit Breaker
Schuetzt vor Endlosschaeden wenn die API krank ist.
CLOSED -> OPEN (nach N Fehlern) -> HALF_OPEN (nach Cooldown) -> CLOSED
"""
import time
import threading
from enum import Enum
from core.logger import log
from core.exceptions import CircuitBreakerOpenError


class CircuitState(Enum):
    CLOSED = "closed"       # Normal, alles laeuft
    OPEN = "open"           # Gesperrt, kein Request durch
    HALF_OPEN = "half_open" # Testmodus, ein Request durch


class CircuitBreaker:
    """Sperrt API-Zugriff nach wiederholten Fehlern."""

    def __init__(self, fail_threshold=5, reset_timeout=60):
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.fail_count = 0
        self.state = CircuitState.CLOSED
        self.last_fail_time = 0
        self.total_trips = 0  # Wie oft wurde der Breaker ausgeloest
        self._lock = threading.Lock()

    def call(self, func):
        """Fuehrt func aus, wirft CircuitBreakerOpenError wenn gesperrt."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                elapsed = time.time() - self.last_fail_time
                if elapsed > self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    log.info("CIRCUIT", "HALF_OPEN: teste Verbindung...")
                else:
                    remaining = int(self.reset_timeout - elapsed)
                    raise CircuitBreakerOpenError(f"API gesperrt fuer {remaining}s")

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                log.info("CIRCUIT", "CLOSED: API wieder gesund")
            self.fail_count = 0
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        with self._lock:
            self.fail_count += 1
            self.last_fail_time = time.time()
            if self.fail_count >= self.fail_threshold:
                self.state = CircuitState.OPEN
                self.total_trips += 1
                log.error("CIRCUIT", f"OPEN! {self.fail_count} Fehler. Gesperrt fuer {self.reset_timeout}s")

    def reset(self):
        """Manueller Reset (z.B. nach API-Key-Aenderung)."""
        with self._lock:
            self.fail_count = 0
            self.state = CircuitState.CLOSED
            log.info("CIRCUIT", "Manuell zurueckgesetzt")

    def get_status(self):
        return {
            "state": self.state.value,
            "failures": self.fail_count,
            "total_trips": self.total_trips,
            "threshold": self.fail_threshold,
        }
