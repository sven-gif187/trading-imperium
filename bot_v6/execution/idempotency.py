"""
Trading Imperium V5 – Idempotenz Guard
Verhindert Doppel-Orders durch eindeutige Client-Order-IDs.
Wenn ein Request timeoutet, weisst du nicht ob er ankam.
Deshalb bekommt jede Order eine eindeutige ID.
"""
import time
import json
import os
import threading
from typing import Dict
from config.settings import DATA_DIR
from core.logger import log

IDEMPOTENCY_FILE = os.path.join(DATA_DIR, "idempotency_keys.json")


class IdempotencyGuard:
    """Speichert alle gesendeten Order-Keys. Verhindert Doppel-Orders."""

    def __init__(self, ttl=300):
        self._lock = threading.Lock()
        self._pending: Dict[str, Dict] = {}
        self._ttl = ttl  # Sekunden bis ein Key verfaellt
        self._blocked_count = 0
        self._load()

    def create_id(self, intent_id: str, symbol: str) -> str:
        """Erzeugt eindeutige Client-Order-ID."""
        return f"TI5_{intent_id}_{symbol.replace('/', '')}_{int(time.time())}"

    def check_and_lock(self, client_id: str) -> bool:
        """Prueft ob Order schon gesendet. True = darf senden."""
        with self._lock:
            self._cleanup()
            if client_id in self._pending:
                self._blocked_count += 1
                log.warn("IDEMP", f"DOPPELTE Order blockiert: {client_id[:30]}")
                return False
            self._pending[client_id] = {
                "time": time.time(),
                "status": "pending",
            }
            self._save()
            return True

    def confirm(self, client_id: str, order_id: str = ""):
        """Bestaetigt dass Order ausgefuehrt wurde."""
        with self._lock:
            if client_id in self._pending:
                self._pending[client_id]["status"] = "confirmed"
                self._pending[client_id]["order_id"] = order_id
                self._save()

    def release(self, client_id: str):
        """Gibt den Lock frei (bei Fehler oder nach Ausfuehrung)."""
        with self._lock:
            self._pending.pop(client_id, None)
            self._save()

    def is_pending(self, client_id: str) -> bool:
        """Ist diese Order noch in Bearbeitung?"""
        with self._lock:
            return client_id in self._pending and self._pending[client_id]["status"] == "pending"

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._pending.items() if now - v["time"] > self._ttl]
        for k in expired:
            del self._pending[k]

    def _load(self):
        if not os.path.exists(IDEMPOTENCY_FILE):
            return
        try:
            with open(IDEMPOTENCY_FILE, "r") as f:
                self._pending = json.load(f)
            # Alte Eintraege bereinigen
            self._cleanup()
        except Exception:
            self._pending = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(IDEMPOTENCY_FILE), exist_ok=True)
            with open(IDEMPOTENCY_FILE, "w") as f:
                json.dump(self._pending, f, indent=1, default=str)
        except Exception:
            pass

    def get_status(self):
        return {
            "pending": sum(1 for v in self._pending.values() if v.get("status") == "pending"),
            "confirmed": sum(1 for v in self._pending.values() if v.get("status") == "confirmed"),
            "blocked_total": self._blocked_count,
        }
