"""
Trading Imperium V5 – Event-System
Die drei zentralen Datenobjekte die durch das System fließen:
1. MarketSnapshot  → Was passiert am Markt?
2. DecisionIntent  → Was will die KI tun?
3. ExecutionResult → Was ist wirklich passiert?
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum
import uuid


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class IntentStatus(Enum):
    PENDING = "PENDING"           # Warte auf Risk-Check
    APPROVED = "APPROVED"         # Risk-Agent hat freigegeben
    REJECTED = "REJECTED"         # Risk-Agent hat blockiert
    EXECUTED = "EXECUTED"         # Order wurde ausgeführt
    FAILED = "FAILED"             # Ausführung fehlgeschlagen
    EXPIRED = "EXPIRED"           # TTL abgelaufen


class MarketRegime(Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class CyclePhase(Enum):
    DISTRIBUTION = "DISTRIBUTION"
    EARLY_BEAR = "EARLY_BEAR"
    MID_BEAR = "MID_BEAR"
    DEEP_BEAR = "DEEP_BEAR"
    CAPITULATION = "CAPITULATION"
    ACCUMULATION = "ACCUMULATION"
    EUPHORIA = "EUPHORIA"


# ==========================================================
# 1. MARKET SNAPSHOT – Was passiert am Markt?
# ==========================================================
@dataclass
class MarketSnapshot:
    """Ein kompletter Schnappschuss der Marktlage für einen Coin."""
    symbol: str                                    # z.B. "BTC/USDC"
    timeframe: str = "5m"                          # Kerzen-Timeframe
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # OHLCV
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    # Indikatoren
    indicators: Dict[str, float] = field(default_factory=dict)
    # z.B. {"rsi": 42.5, "adx": 28.3, "ema20": 67500, "macd": -120, ...}

    # Sentiment & Kontext
    sentiment: Dict[str, float] = field(default_factory=dict)
    # z.B. {"fear_greed": 25, "news_score": -0.3, "btc_dominance": 58.2}

    # Regime
    regime: MarketRegime = MarketRegime.UNKNOWN
    cycle_phase: CyclePhase = CyclePhase.ACCUMULATION

    # Portfolio-Kontext
    portfolio_context: Dict = field(default_factory=dict)
    # z.B. {"usdc_balance": 5000, "btc_total": 0.05, "open_positions": 3}


# ==========================================================
# 2. DECISION INTENT – Was will die KI tun?
# ==========================================================
@dataclass
class DecisionIntent:
    """Ein Trade-Vorschlag von einem Signal-Agent. Muss vom Risk-Agent genehmigt werden."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    side: Side = Side.HOLD
    confidence: float = 0.0                        # 0.0 bis 1.0
    target_weight: Optional[float] = None          # Ziel-Gewichtung im Portfolio (0.0 bis 1.0)
    entry_price: float = 0.0
    amount_usd: float = 0.0                        # Geplanter Betrag in USD
    quantity: float = 0.0                          # Geplante Menge

    # Risiko-Parameter
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    max_slippage_pct: float = 0.5

    # Begründung
    strategy_id: str = ""                          # z.B. "RSI_OVERSOLD"
    strategy_name: str = ""                        # z.B. "RSI Oversold"
    entry_reason: str = ""                         # Menschenlesbare Begründung
    score: int = 0                                 # Signal-Score (0-10)

    # Meta
    model_version: str = "v5.0"
    agent_id: str = ""                             # Welcher Agent hat das erzeugt?
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 120                         # Intent verfällt nach X Sekunden
    status: IntentStatus = IntentStatus.PENDING

    # Risk-Agent Feedback
    risk_approved: bool = False
    risk_reason: str = ""
    risk_adjusted_amount: Optional[float] = None   # Risk-Agent kann Betrag anpassen

    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds


# ==========================================================
# 3. EXECUTION RESULT – Was ist wirklich passiert?
# ==========================================================
@dataclass
class ExecutionResult:
    """Das tatsächliche Ergebnis einer Order-Ausführung."""
    intent_id: str = ""                            # Referenz zum DecisionIntent
    symbol: str = ""
    side: Side = Side.HOLD
    status: str = "pending"                        # "filled", "partial", "rejected", "error"

    # Order-Details
    order_id: str = ""                             # Exchange Order-ID
    client_order_id: str = ""                      # Unsere eindeutige ID (Idempotenz!)
    avg_fill_price: float = 0.0
    filled_qty: float = 0.0
    filled_cost: float = 0.0                       # Gesamtkosten in Quote-Currency
    fee: float = 0.0
    slippage_pct: float = 0.0                      # Tatsächliche Slippage

    # P&L (bei Sells)
    pnl: float = 0.0
    pnl_pct: float = 0.0
    entry_price: float = 0.0

    # Fehler
    error: Optional[str] = None
    rejected_reason: Optional[str] = None

    # [E9-LIVE 29.07.] True = Boerse hat weniger gefuellt als bestellt.
    # status bleibt "filled" (die Teilmenge IST ausgefuehrt), aber
    # filled_qty ist die echte Menge - Register und Boerse bleiben synchron.
    partial: bool = False

    # Meta
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: int = 0                            # Wie lange hat die Order gedauert?


# ==========================================================
# SYSTEM EVENTS – Für den Event-Bus
# ==========================================================
@dataclass
class SystemEvent:
    """Ein allgemeines System-Event für den Event-Bus."""
    type: str = ""                                 # z.B. "MARKET_UPDATE", "TRADE_EXECUTED", "RISK_ALERT"
    data: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""                               # Welches Modul hat das Event erzeugt?
    priority: int = 0                              # 0=normal, 1=important, 2=critical


# Event-Typen als Konstanten
EVENT_MARKET_UPDATE = "MARKET_UPDATE"
EVENT_SIGNAL = "SIGNAL"
EVENT_RISK_CHECK = "RISK_CHECK"
EVENT_RISK_APPROVED = "RISK_APPROVED"
EVENT_RISK_REJECTED = "RISK_REJECTED"
EVENT_ORDER_PLACED = "ORDER_PLACED"
EVENT_ORDER_FILLED = "ORDER_FILLED"
EVENT_ORDER_FAILED = "ORDER_FAILED"
EVENT_TRADE_CLOSED = "TRADE_CLOSED"
EVENT_KILL_SWITCH = "KILL_SWITCH"
EVENT_HEARTBEAT = "HEARTBEAT"
EVENT_ERROR = "ERROR"
EVENT_NEWS_UPDATE = "NEWS_UPDATE"
EVENT_REGIME_CHANGE = "REGIME_CHANGE"
EVENT_CYCLE_UPDATE = "CYCLE_UPDATE"
