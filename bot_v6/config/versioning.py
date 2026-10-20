"""
Trading Imperium V6 – Config Versionierung
Speichert bei jeder Aenderung ein Backup der Config.
"""
import os
import json
import time
import shutil
from typing import List
from config.settings import DATA_DIR
from core.logger import log

BACKUP_DIR = os.path.join(DATA_DIR, "config_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


class ConfigVersioning:
    """Verwaltet Config-Backups."""

    def __init__(self, max_backups=10):
        self.max_backups = max_backups

    def save_backup(self, config_data: dict):
        """Speichert ein Backup der aktuellen Config."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(BACKUP_DIR, f"config_{ts}.json")
        try:
            with open(path, "w") as f:
                json.dump(config_data, f, indent=2, default=str)
            self._cleanup()
            log.info("CONFIG", f"Backup gespeichert: {ts}")
            return path
        except Exception as e:
            log.warn("CONFIG", f"Backup Fehler: {e}")
            return None

    def list_backups(self) -> List[dict]:
        """Gibt alle verfuegbaren Backups zurueck."""
        backups = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.startswith("config_") and f.endswith(".json"):
                path = os.path.join(BACKUP_DIR, f)
                backups.append({
                    "file": f,
                    "path": path,
                    "size": os.path.getsize(path),
                    "time": f.replace("config_", "").replace(".json", ""),
                })
        return backups[:self.max_backups]

    def restore(self, filename) -> dict:
        """Stellt eine Config aus einem Backup wieder her."""
        path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            log.info("CONFIG", f"Wiederhergestellt: {filename}")
            return data
        except Exception as e:
            log.error("CONFIG", f"Restore Fehler: {e}")
            return None

    def _cleanup(self):
        files = sorted(os.listdir(BACKUP_DIR))
        while len(files) > self.max_backups:
            os.remove(os.path.join(BACKUP_DIR, files.pop(0)))
