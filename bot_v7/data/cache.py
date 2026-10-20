"""
Trading Imperium V5 – Data Cache
Lokaler Cache fuer API-Responses. Verhindert Rate-Limits und beschleunigt Zugriffe.
"""
import time
import json
import os
import threading
from typing import Any, Optional, Dict
from config.settings import DATA_DIR
from core.logger import log

CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


class DataCache:
    """In-Memory + Disk Cache mit TTL (Time-to-Live)."""

    def __init__(self, default_ttl=300):
        self.default_ttl = default_ttl  # 5 Minuten Standard
        self._memory = {}  # key -> {"value": ..., "expires": timestamp}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key, default=None):
        """Holt Wert aus Cache. None wenn abgelaufen oder nicht vorhanden."""
        with self._lock:
            # Memory-Cache
            if key in self._memory:
                entry = self._memory[key]
                if time.time() < entry["expires"]:
                    self._hits += 1
                    return entry["value"]
                else:
                    del self._memory[key]

        # Disk-Cache
        disk_val = self._load_disk(key)
        if disk_val is not None:
            self._hits += 1
            return disk_val

        self._misses += 1
        return default

    def set(self, key, value, ttl=None):
        """Speichert Wert im Cache."""
        ttl = ttl or self.default_ttl
        with self._lock:
            self._memory[key] = {
                "value": value,
                "expires": time.time() + ttl,
            }

    def set_persistent(self, key, value, ttl=None):
        """Speichert Wert sowohl im Memory als auch auf Disk."""
        self.set(key, value, ttl)
        self._save_disk(key, value, ttl)

    def invalidate(self, key):
        """Loescht einen Eintrag."""
        with self._lock:
            self._memory.pop(key, None)
        path = os.path.join(CACHE_DIR, f"{self._safe_key(key)}.json")
        if os.path.exists(path):
            os.remove(path)

    def clear(self):
        """Loescht den gesamten Cache."""
        with self._lock:
            self._memory.clear()
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, f))
                except Exception:
                    pass
        log.info("CACHE", "Cache geleert")

    def cleanup(self):
        """Entfernt abgelaufene Eintraege."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._memory.items() if now >= v["expires"]]
            for k in expired:
                del self._memory[k]
        return len(expired)

    def _save_disk(self, key, value, ttl):
        try:
            path = os.path.join(CACHE_DIR, f"{self._safe_key(key)}.json")
            data = {"value": value, "expires": time.time() + (ttl or self.default_ttl)}
            with open(path, "w") as f:
                json.dump(data, f, default=str)
        except Exception:
            pass

    def _load_disk(self, key):
        try:
            path = os.path.join(CACHE_DIR, f"{self._safe_key(key)}.json")
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                data = json.load(f)
            if time.time() < data.get("expires", 0):
                # In Memory cachen fuer naechsten Zugriff
                with self._lock:
                    self._memory[key] = data
                return data["value"]
            else:
                os.remove(path)
        except Exception:
            pass
        return None

    def _safe_key(self, key):
        return key.replace("/", "_").replace(":", "_").replace(" ", "_")[:80]

    def get_status(self):
        with self._lock:
            active = sum(1 for v in self._memory.values() if time.time() < v["expires"])
        disk_files = len([f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {"memory_entries": active, "disk_entries": disk_files,
                "hits": self._hits, "misses": self._misses,
                "hit_rate": round(hit_rate, 1)}
