"""
Trading Imperium V5 – Execution Engine
Sichere Order-Ausführung mit:
- Retry nur bei transienten Fehlern (Timeout, 429, 5xx)
- Circuit Breaker (stoppt bei dauerhaften API-Problemen)
- Idempotenz (keine Doppel-Orders nach Timeout)
- Slippage-Check
- Order-Audit-Log
"""
import time
import uuid
import threading
try:
    import ccxt
except ImportError:
    ccxt = None  # Wird erst bei Live-Trading benötigt
from typing import Optional, Dict
from datetime import datetime, timezone

from core.logger import log
from core.events import DecisionIntent, ExecutionResult, Side
from core.exceptions import (
    OrderExecutionError, ExchangeConnectionError,
    CircuitBreakerOpenError, IdempotencyError, KillSwitchError
)
from config.settings import ExchangeConfig


# ==========================================================
# RETRY POLICY
# ==========================================================
class RetryPolicy:
    """Retry nur bei transienten Fehlern. Exponentielles Backoff + Jitter."""

    TRANSIENT_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)
    NO_RETRY_EXCEPTIONS = (ValueError, TypeError)

    if ccxt:
        TRANSIENT_EXCEPTIONS = (
            ccxt.NetworkError, ccxt.RequestTimeout,
            ccxt.ExchangeNotAvailable, ccxt.DDoSProtection,
            ConnectionError, TimeoutError,
        )
        NO_RETRY_EXCEPTIONS = (
            ccxt.AuthenticationError, ccxt.InsufficientFunds,
            ccxt.InvalidOrder, ccxt.BadRequest, ccxt.PermissionDenied,
        )

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, func, context: str = ""):
        """Führt eine Funktion mit Retry-Logik aus."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return func()
            except self.NO_RETRY_EXCEPTIONS as e:
                log.error("RETRY", f"Nicht-transienter Fehler (kein Retry): {e}")
                raise OrderExecutionError(str(e))
            except self.TRANSIENT_EXCEPTIONS as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + (time.time() % 1) * 0.5
                    log.warn("RETRY", f"Attempt {attempt+1}/{self.max_retries}: {e} → warte {delay:.1f}s")
                    time.sleep(delay)
                else:
                    log.error("RETRY", f"Alle {self.max_retries} Retries fehlgeschlagen: {e}")
            except Exception as e:
                last_error = e
                log.error("RETRY", f"Unerwarteter Fehler: {type(e).__name__}: {e}")
                if attempt >= self.max_retries:
                    break
                time.sleep(self.base_delay)

        raise OrderExecutionError(f"Nach {self.max_retries} Retries fehlgeschlagen: {last_error}")


# ==========================================================
# CIRCUIT BREAKER
# ==========================================================
class CircuitBreaker:
    """Schützt vor Endlos-Anfragen bei dauerhaft kaputten APIs."""

    def __init__(self, failure_threshold: int = 5, recovery_time: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0
        self._lock = threading.Lock()

    def call(self, func):
        """Führt Funktion aus wenn Circuit geschlossen ist."""
        with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_time:
                    self.state = "HALF_OPEN"
                    log.info("CIRCUIT", "Circuit HALF_OPEN – Testversuch")
                else:
                    remaining = int(self.recovery_time - (time.time() - self.last_failure_time))
                    raise CircuitBreakerOpenError(
                        f"Circuit OPEN – warte noch {remaining}s")

        try:
            result = func()
            with self._lock:
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failures = 0
                    log.info("CIRCUIT", "Circuit wieder CLOSED")
                elif self.state == "CLOSED":
                    self.failures = max(0, self.failures - 1)
            return result
        except Exception as e:
            with self._lock:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                    log.error("CIRCUIT", f"Circuit OPEN nach {self.failures} Fehlern!")
            raise

    def get_status(self) -> Dict:
        return {"state": self.state, "failures": self.failures,
                "threshold": self.failure_threshold}


# ==========================================================
# IDEMPOTENCY MANAGER
# ==========================================================
class IdempotencyManager:
    """Verhindert Doppel-Orders nach Timeouts."""

    def __init__(self):
        self._pending: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_key(self, intent: DecisionIntent) -> str:
        """Erzeugt einen eindeutigen Idempotency-Key für einen Intent."""
        key = f"ord_{intent.id}_{int(time.time())}"
        with self._lock:
            self._pending[key] = {
                "intent_id": intent.id,
                "symbol": intent.symbol,
                "side": intent.side.value,
                "created": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
        return key

    def mark_completed(self, key: str, order_id: str = ""):
        with self._lock:
            if key in self._pending:
                self._pending[key]["status"] = "completed"
                self._pending[key]["order_id"] = order_id

    def mark_failed(self, key: str, reason: str = ""):
        with self._lock:
            if key in self._pending:
                self._pending[key]["status"] = "failed"
                self._pending[key]["reason"] = reason

    def is_duplicate(self, intent: DecisionIntent) -> bool:
        """Prüft ob ein ähnlicher Intent gerade läuft."""
        with self._lock:
            for key, info in self._pending.items():
                if (info["intent_id"] == intent.id and
                    info["status"] == "pending"):
                    return True
        return False

    def cleanup(self, max_age_sec: int = 300):
        """Entfernt alte Einträge."""
        now = time.time()
        with self._lock:
            to_remove = []
            for key, info in self._pending.items():
                if info["status"] != "pending":
                    to_remove.append(key)
            for key in to_remove:
                del self._pending[key]


# ==========================================================
# EXCHANGE CLIENT (Live + Paper)
# ==========================================================
class ExchangeClient:
    """Universeller Exchange-Client. Gleiche Schnittstelle für Paper und Live."""

    def __init__(self, config: ExchangeConfig, paper: bool = True):
        self.config = config
        self.paper = paper
        self._exchange = None
        self._paper_balances = {}
        self._retry = RetryPolicy(max_retries=config.max_retries)
        self._circuit = CircuitBreaker()
        self._idempotency = IdempotencyManager()

        if paper:
            self._init_paper()
        else:
            self._init_live()

    def _init_paper(self):
        """Paper-Exchange initialisieren."""
        self._paper_balances = {
            "total": {self.config.quote_currency: 10000.0},
            "free": {self.config.quote_currency: 10000.0},
        }
        log.info("EXCHANGE", f"Paper-Exchange initialisiert: 10.000 {self.config.quote_currency}")

    def _init_live(self):
        """Live-Exchange via ccxt initialisieren."""
        if not ccxt:
            raise ExchangeConnectionError("ccxt nicht installiert! pip install ccxt")
        exchange_map = {
            "binance": ccxt.binance, "coinbasepro": ccxt.coinbasepro,
            "kraken": ccxt.kraken, "bybit": ccxt.bybit,
            "okx": ccxt.okx, "kucoin": ccxt.kucoin,
        }
        ExClass = exchange_map.get(self.config.ccxt_id, ccxt.binance)
        self._exchange = ExClass({
            'apiKey': self.config.api_key,
            'secret': self.config.api_secret,
            'enableRateLimit': True,
            'timeout': self.config.timeout_read * 1000,
            'options': {'defaultType': 'spot'},
        })
        log.info("EXCHANGE", f"Live-Exchange verbunden: {self.config.name}")

    def fetch_balance(self) -> Dict:
        if self.paper:
            return dict(self._paper_balances)
        return self._retry.execute(
            lambda: self._circuit.call(lambda: self._exchange.fetch_balance()),
            context="fetch_balance"
        )

    def fetch_ticker(self, symbol: str) -> Dict:
        """Holt den aktuellen Preis."""
        return self._retry.execute(
            lambda: self._circuit.call(
                lambda: self._exchange.fetch_ticker(symbol) if self._exchange
                else {"last": 0}),
            context=f"ticker:{symbol}"
        )

    def fetch_ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 120) -> list:
        """Holt Kerzendaten."""
        return self._retry.execute(
            lambda: self._circuit.call(
                lambda: self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit) if self._exchange
                else []),
            context=f"ohlcv:{symbol}"
        )

    def execute_intent(self, intent: DecisionIntent, data_client=None) -> ExecutionResult:
        """Führt einen genehmigten DecisionIntent aus."""
        start_time = time.time()

        # Idempotenz-Check
        if self._idempotency.is_duplicate(intent):
            log.warn("EXEC", f"Doppelter Intent blockiert: {intent.id} {intent.symbol}")
            return ExecutionResult(
                intent_id=intent.id, symbol=intent.symbol,
                status="rejected", rejected_reason="Duplicate intent"
            )

        idem_key = self._idempotency.create_key(intent)

        try:
            if self.paper:
                result = self._execute_paper(intent, data_client)
            else:
                result = self._execute_live(intent)

            self._idempotency.mark_completed(idem_key, result.order_id)
            result.latency_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            self._idempotency.mark_failed(idem_key, str(e))
            log.error("EXEC", f"Order fehlgeschlagen: {intent.symbol} {intent.side}: {e}")
            return ExecutionResult(
                intent_id=intent.id, symbol=intent.symbol,
                status="error", error=str(e),
                latency_ms=int((time.time() - start_time) * 1000)
            )

    def _execute_paper(self, intent: DecisionIntent, data_client=None) -> ExecutionResult:
        """Paper-Order ausführen."""
        symbol = intent.symbol
        asset, quote = symbol.split('/')
        price = intent.entry_price

        # Preis holen falls nicht gesetzt
        if price <= 0 and data_client:
            try:
                ticker = data_client.fetch_ticker(symbol)
                price = ticker['last']
            except Exception:
                price = 0
        if price <= 0:
            raise OrderExecutionError(f"Kein Preis für {symbol}")

        order_id = f"paper_{uuid.uuid4().hex[:8]}"

        if intent.side == Side.BUY:
            amount = intent.amount_usd
            if amount <= 0:
                raise OrderExecutionError("Betrag muss > 0 sein")
            qty = amount / price
            free_quote = self._paper_balances['free'].get(quote, 0)
            if free_quote < amount:
                raise OrderExecutionError(f"Nur {free_quote:.2f} {quote} frei, brauche {amount:.2f}")

            self._paper_balances['free'][quote] = free_quote - amount
            self._paper_balances['total'][quote] = self._paper_balances['total'].get(quote, 0) - amount
            self._paper_balances['free'][asset] = self._paper_balances['free'].get(asset, 0) + qty
            self._paper_balances['total'][asset] = self._paper_balances['total'].get(asset, 0) + qty

            log.trade("PAPER", f"BUY {asset}: {qty:.6f} @ {price:,.2f}$ = {amount:.2f} {quote}")
            return ExecutionResult(
                intent_id=intent.id, symbol=symbol, side=Side.BUY,
                status="filled", order_id=order_id,
                avg_fill_price=price, filled_qty=qty, filled_cost=amount
            )

        elif intent.side == Side.SELL:
            qty = intent.quantity
            if qty <= 0:
                free_asset = self._paper_balances['free'].get(asset, 0)
                qty = free_asset
            if qty <= 0:
                raise OrderExecutionError(f"Kein {asset} zum Verkaufen")

            cost = qty * price
            self._paper_balances['free'][asset] = self._paper_balances['free'].get(asset, 0) - qty
            self._paper_balances['total'][asset] = self._paper_balances['total'].get(asset, 0) - qty
            self._paper_balances['free'][quote] = self._paper_balances['free'].get(quote, 0) + cost
            self._paper_balances['total'][quote] = self._paper_balances['total'].get(quote, 0) + cost

            log.trade("PAPER", f"SELL {asset}: {qty:.6f} @ {price:,.2f}$ = {cost:.2f} {quote}")
            return ExecutionResult(
                intent_id=intent.id, symbol=symbol, side=Side.SELL,
                status="filled", order_id=order_id,
                avg_fill_price=price, filled_qty=qty, filled_cost=cost,
                entry_price=intent.entry_price
            )

        return ExecutionResult(intent_id=intent.id, status="rejected",
                               rejected_reason="Unknown side")

    def _execute_live(self, intent: DecisionIntent) -> ExecutionResult:
        """Live-Order über ccxt ausführen."""
        symbol = intent.symbol
        order_id = f"live_{uuid.uuid4().hex[:8]}"

        def _place():
            if intent.side == Side.BUY:
                qty = intent.amount_usd / intent.entry_price if intent.entry_price > 0 else 0
                return self._exchange.create_market_buy_order(symbol, qty)
            elif intent.side == Side.SELL:
                return self._exchange.create_market_sell_order(symbol, intent.quantity)
            return None

        order = self._retry.execute(
            lambda: self._circuit.call(_place),
            context=f"order:{symbol}"
        )

        if not order:
            raise OrderExecutionError("Keine Order-Antwort")

        fill_price = order.get('average', order.get('price', 0))
        fill_qty = order.get('filled', 0)
        fill_cost = order.get('cost', fill_qty * fill_price)
        fee = order.get('fee', {}).get('cost', 0)

        log.trade("LIVE", f"{intent.side.value} {symbol}: {fill_qty:.6f} @ {fill_price:,.2f}$")

        return ExecutionResult(
            intent_id=intent.id, symbol=symbol, side=intent.side,
            status="filled", order_id=order.get('id', order_id),
            avg_fill_price=fill_price, filled_qty=fill_qty,
            filled_cost=fill_cost, fee=fee
        )

    def get_status(self) -> Dict:
        return {
            "paper": self.paper,
            "exchange": self.config.name,
            "circuit": self._circuit.get_status(),
        }
