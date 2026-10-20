"""
Trading Imperium V5 – Custom Exceptions
Klare Fehlerklassen statt generisches Exception-Catching.
"""


class TradingError(Exception):
    """Basis-Fehler für alle Trading-Fehler."""
    pass


class RiskVetoError(TradingError):
    """Risk-Agent hat den Trade blockiert."""
    def __init__(self, reason: str = "Risk check failed"):
        self.reason = reason
        super().__init__(f"🛡️ Risk-Veto: {reason}")


class InsufficientBalanceError(TradingError):
    """Nicht genug Balance für die Order."""
    pass


class OrderExecutionError(TradingError):
    """Order konnte nicht ausgeführt werden."""
    pass


class ExchangeConnectionError(TradingError):
    """Verbindung zur Börse fehlgeschlagen."""
    pass


class KillSwitchError(TradingError):
    """Kill-Switch wurde ausgelöst."""
    def __init__(self, reason: str = "Daily loss limit reached"):
        self.reason = reason
        super().__init__(f"🛑 KILL-SWITCH: {reason}")


class DataError(TradingError):
    """Daten konnten nicht geladen werden."""
    pass


class ConfigError(TradingError):
    """Konfigurationsfehler."""
    pass


class CircuitBreakerOpenError(TradingError):
    """Circuit Breaker ist offen – API ist temporär gesperrt."""
    pass


class IdempotencyError(TradingError):
    """Doppelte Order erkannt."""
    pass


class SicherheitsbauteilFehlt(TradingError):
    """Ein Bauteil ohne das nicht gehandelt werden darf, konnte nicht laden.

    [13.08.2026] Absichtlich KEIN abfangbarer Betriebsfehler, sondern ein
    Startabbruch. Bisher wurden solche Ausfaelle nur geloggt, und der Bot
    lief weiter - beim Exit-Monitor hiess das: Handel ohne jede
    Stop-Loss-Ueberwachung, sichtbar nur als eine Zeile im Log.

    Regel dahinter (MASTERPROMPT.md, Abschnitt 3.5): CRITICAL bedeutet,
    den Handel sicher zu blockieren, bis der Zustand wiederhergestellt
    ist. Lieber gar nicht handeln als ohne Sicherung handeln.

    Wird in app.py.__init__ geworfen und NICHT gefangen - der Prozess
    endet mit einer lauten Meldung auf der Konsole und im Log.
    """
    def __init__(self, bauteil: str, ursache: str, folge: str):
        self.bauteil = bauteil
        self.ursache = ursache
        self.folge = folge
        super().__init__(
            f"SICHERHEITSBAUTEIL FEHLT: {bauteil} | Ursache: {ursache} | "
            f"Folge bei Weiterbetrieb: {folge}")
