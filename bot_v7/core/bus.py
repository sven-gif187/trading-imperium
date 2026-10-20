"""
Trading Imperium V5 – Event Bus
Zentrales Kommunikationssystem. Alle Module kommunizieren über Events,
niemals direkt miteinander. Das macht das System modular und testbar.

Beispiel:
    bus = EventBus()
    bus.subscribe("SIGNAL", risk_agent.on_signal)
    bus.subscribe("RISK_APPROVED", execution_agent.on_approved)
    bus.publish("SIGNAL", intent)
"""
import os
import threading
import time
import traceback
from collections import defaultdict
from typing import Callable, Any, List, Dict
from datetime import datetime, timezone
from core.events import SystemEvent
from core.logger import log
from config.settings import DATA_DIR

# [SICHTBARKEIT 06.08.2026] Dauerhafte Fehlerakte des Event-Bus.
# Bewusst eine EIGENE Datei: system.log rotiert bei 20 MB (logger.py:50-61)
# und wuerde genau die seltenen Fehler wegwerfen, die man ein halbes Jahr
# spaeter sucht. Diese Datei rotiert nicht und wird nur angehaengt.
BUS_ERROR_FILE = os.path.join(DATA_DIR, "bus_errors.log")


class EventBus:
    """Thread-sicherer Event-Bus für die Kommunikation zwischen Modulen."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._event_log: List[Dict] = []
        self._max_log = 500
        self._stats = defaultdict(int)  # Zählt Events pro Typ
        self._running = True

    def subscribe(self, event_type: str, callback: Callable):
        """Registriert einen Callback für einen Event-Typ."""
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Entfernt einen Callback."""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None, source: str = ""):
        """Veröffentlicht ein Event an alle Subscriber."""
        if not self._running:
            return

        event = SystemEvent(
            type=event_type,
            data=data if isinstance(data, dict) else {"payload": data},
            source=source,
            timestamp=datetime.now(timezone.utc)
        )

        # Event loggen
        self._stats[event_type] += 1
        self._event_log.append({
            "type": event_type,
            "source": source,
            "time": event.timestamp.isoformat(),
        })
        if len(self._event_log) > self._max_log:
            self._event_log = self._event_log[-self._max_log:]

        # Alle Subscriber benachrichtigen
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))

        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                # Fehler in einem Subscriber darf nicht andere blockieren.
                #
                # [SICHTBARKEIT 06.08.2026] Vorher endete der Fehler AUSSCHLIESSLICH
                # in self._event_log - einer Liste im Arbeitsspeicher, gedeckelt auf
                # 500 Eintraege (Zeile 27/61) und bei jedem Neustart weg. Damit war
                # ein abgebrochener Kauf-Kandidat spurlos: system.log zeigte am
                # 06.08.2026 14.986 erzeugte BUY-Signale und NULL Risk-Pruefungen,
                # ohne einen einzigen Hinweis, wo sie geblieben sind.
                # Ab jetzt: laut ins system.log UND dauerhaft in die Fehlerakte.
                _quelle = f"{event_type}->{getattr(cb, '__name__', repr(cb))}"
                _zeit = datetime.now(timezone.utc).isoformat()
                self._stats["BUS_ERROR"] += 1
                self._event_log.append({
                    "type": "BUS_ERROR",
                    "source": _quelle,
                    "error": str(e),
                    "time": _zeit,
                })
                # 1) Sofort sichtbar - im Terminal, im Log, in der UI
                try:
                    log.error("BUS", f"Subscriber-Fehler {_quelle}: "
                                     f"{type(e).__name__}: {str(e)[:200]}")
                except Exception:
                    pass
                # 2) Dauerhaft mit vollem Stacktrace - ueberlebt Rotation+Neustart
                try:
                    with open(BUS_ERROR_FILE, "a", encoding="utf-8") as f:
                        f.write(f"\n{'=' * 78}\n[{_zeit}] {_quelle}\n"
                                f"Event-Quelle: {source or '-'}\n"
                                f"{traceback.format_exc()}")
                except Exception:
                    pass

    def publish_async(self, event_type: str, data: Any = None, source: str = ""):
        """Veröffentlicht ein Event in einem separaten Thread (nicht-blockierend)."""
        threading.Thread(
            target=self.publish,
            args=(event_type, data, source),
            daemon=True
        ).start()

    def get_stats(self) -> Dict[str, int]:
        """Gibt Event-Statistiken zurück."""
        return dict(self._stats)

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Gibt die letzten Events zurück."""
        return self._event_log[-limit:]

    def shutdown(self):
        """Stoppt den Event-Bus."""
        self._running = False
        self._subscribers.clear()
