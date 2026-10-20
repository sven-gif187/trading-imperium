"""
Trading Imperium V5 – Structured Logger
Jeder Log-Eintrag hat: Timestamp, Modul, Level, Message, optional trace_id.
"""
import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict
from collections import deque
from config.settings import DATA_DIR


class Logger:
    """Strukturiertes Logging-System für das gesamte Trading-System."""

    def __init__(self, max_memory: int = 1000):
        self._lock = threading.Lock()
        self._log_memory = deque(maxlen=max_memory)
        self._callbacks = []  # UI-Callbacks für Live-Updates
        # === [15.09.2026] Log-Ziel umlenkbar ===
        #
        # ANLASS: In der Nacht zum 15.09. lief fraktal_tor_test.py und
        # schrieb dabei 23 Zeilen mit dem Attrappen-Symbol TEST/USDC in
        # das ECHTE data_store/system.log - mitten zwischen die Zeilen
        # des laufenden Echtgeld-Bots. Kein Schaden am Handel, aber im
        # Log stehen jetzt erfundene Kaeufe neben echten.
        #
        # Derselbe Fehlertyp wie bei befund68_test.py, der in die echte
        # Warteschlange des laufenden Bots schrieb und eine Muenze
        # dauerhaft vom Handel aussperrte. Die Ursache ist beide Male
        # dieselbe: Ein Test importiert Produktionsmodule, und die
        # schreiben dorthin, wo sie immer hinschreiben.
        #
        # Ein Test darf den Zustand des laufenden Systems nicht
        # beruehren - auch nicht sein Protokoll.
        #
        # Vorgabe unveraendert: ohne die Variable schreibt der Logger
        # wie bisher nach data_store/system.log. Der laufende Bot merkt
        # von dieser Zeile nichts.
        self._log_file = (os.environ.get("TI_LOG_FILE")
                          or os.path.join(DATA_DIR, "system.log"))
        self._rot_check = 0  # [LOGROTATION 16.07.]

    def _format(self, level: str, module: str, msg: str, trace_id: str = "") -> Dict:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat()[:19],
            "level": level,
            "module": module,
            "msg": msg,
        }
        if trace_id:
            entry["trace_id"] = trace_id
        return entry

    def _emit(self, entry: Dict):
        with self._lock:
            self._log_memory.append(entry)

        # Alle UI-Callbacks benachrichtigen
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception:
                pass

        # In Datei schreiben
        try:
            line = f"[{entry['ts']}] [{entry['level']}] [{entry['module']}] {entry['msg']}\n"
            # [LOGROTATION 16.07.] ab ~20 MB rotieren (eine Vorgaenger-Datei)
            self._rot_check += 1
            if self._rot_check >= 500:
                self._rot_check = 0
                try:
                    if os.path.getsize(self._log_file) > 20 * 1024 * 1024:
                        _old = self._log_file + ".1"
                        if os.path.exists(_old):
                            os.remove(_old)
                        os.replace(self._log_file, _old)
                except Exception:
                    pass
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def info(self, module: str, msg: str, trace_id: str = ""):
        self._emit(self._format("INFO", module, msg, trace_id))

    def warn(self, module: str, msg: str, trace_id: str = ""):
        self._emit(self._format("WARN", module, msg, trace_id))

    def error(self, module: str, msg: str, trace_id: str = ""):
        self._emit(self._format("ERROR", module, msg, trace_id))

    def trade(self, module: str, msg: str, trace_id: str = ""):
        """Spezial-Level für Trade-Events (immer sichtbar)."""
        self._emit(self._format("TRADE", module, msg, trace_id))

    def signal(self, module: str, msg: str, trace_id: str = ""):
        """Spezial-Level für Signal-Events."""
        self._emit(self._format("SIGNAL", module, msg, trace_id))

    def risk(self, module: str, msg: str, trace_id: str = ""):
        """Spezial-Level für Risk-Events."""
        self._emit(self._format("RISK", module, msg, trace_id))

    def add_callback(self, callback):
        """Registriert einen Callback für Live-Log-Updates (z.B. UI)."""
        self._callbacks.append(callback)

    def get_recent(self, limit: int = 50, level: Optional[str] = None) -> List[Dict]:
        """Gibt die letzten Log-Einträge zurück."""
        with self._lock:
            logs = list(self._log_memory)
        if level:
            logs = [l for l in logs if l["level"] == level]
        return logs[-limit:]

    def get_formatted(self, limit: int = 30) -> str:
        """Gibt formatierte Log-Einträge als String zurück."""
        entries = self.get_recent(limit)
        lines = []
        icons = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌", "TRADE": "🛒", "SIGNAL": "📊", "RISK": "🛡️"}
        for e in entries:
            icon = icons.get(e["level"], "•")
            lines.append(f"[{e['ts'][11:]}] {icon} [{e['module']}] {e['msg']}")
        return "\n".join(lines)


# Globale Logger-Instanz
log = Logger()
