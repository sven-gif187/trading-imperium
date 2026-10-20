"""
Trading Imperium V5 – Retry Policy
Wann wird wiederholt, wann nicht. Exponentielles Backoff + Jitter.
"""
import time
import random
import ccxt
from core.logger import log
from core.exceptions import OrderExecutionError

# Fehler die wiederholt werden duerfen
RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}
# Fehler die NICHT wiederholt werden (echte Fehler)
NON_RETRYABLE_HTTP = {400, 401, 403, 404, 409, 422}

RETRYABLE_EXCEPTIONS = (
    ccxt.RateLimitExceeded, ccxt.NetworkError,
    ccxt.ExchangeNotAvailable, ConnectionError, TimeoutError,
)
NON_RETRYABLE_EXCEPTIONS = (
    ccxt.AuthenticationError, ccxt.InsufficientFunds,
    ccxt.InvalidOrder, ccxt.BadRequest,
)


class RetryPolicy:
    """Retry mit exponentiellem Backoff + Jitter. Nur bei transienten Fehlern."""

    def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.total_retries = 0

    def execute(self, func):
        """Fuehrt func aus mit automatischem Retry bei transienten Fehlern."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return func()
            except NON_RETRYABLE_EXCEPTIONS as e:
                # Sofort werfen, NICHT wiederholen
                raise
            except ccxt.RateLimitExceeded as e:
                delay = self._backoff(attempt, rate_limited=True)
                log.warn("RETRY", f"Rate-Limit! Warte {delay:.1f}s (Versuch {attempt+1}/{self.max_retries})")
                time.sleep(delay)
                last_error = str(e)
            except RETRYABLE_EXCEPTIONS as e:
                if attempt >= self.max_retries:
                    raise
                delay = self._backoff(attempt)
                log.warn("RETRY", f"Netzwerk: {str(e)[:60]}. Retry in {delay:.1f}s ({attempt+1}/{self.max_retries})")
                time.sleep(delay)
                last_error = str(e)
            except Exception as e:
                if attempt >= self.max_retries:
                    raise
                delay = self._backoff(attempt)
                log.warn("RETRY", f"Fehler: {str(e)[:60]}. Retry {attempt+1}/{self.max_retries}")
                time.sleep(delay)
                last_error = str(e)

            self.total_retries += 1

        raise OrderExecutionError(f"Max {self.max_retries} retries: {last_error}")

    def _backoff(self, attempt, rate_limited=False):
        """Exponentielles Backoff + Jitter."""
        if rate_limited:
            # Bei Rate-Limit laenger warten
            base = max(self.base_delay * 2, 3.0)
        else:
            base = self.base_delay
        delay = base * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.3)
        return min(delay + jitter, self.max_delay)

    def get_status(self):
        return {"max_retries": self.max_retries, "total_retries": self.total_retries}
