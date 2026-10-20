"""
Trading Imperium V5 – Model Registry
Verwaltet ML-Modell-Versionen. Speichert, laedt, vergleicht Modelle.
"""
import os
import json
import time
import pickle
from typing import Dict, List, Optional
from config.settings import DATA_DIR
from core.logger import log

MODEL_DIR = os.path.join(DATA_DIR, "models")
REGISTRY_FILE = os.path.join(MODEL_DIR, "registry.json")
os.makedirs(MODEL_DIR, exist_ok=True)


class ModelRegistry:
    """Verwaltet alle ML-Modell-Versionen."""

    def __init__(self):
        self.models = {}  # version -> metadata
        self.active_model = None
        self.active_version = None
        self._load_registry()

    def register(self, version, model, metrics, model_type="signal"):
        """Registriert ein neues Modell."""
        meta = {
            "version": version,
            "type": model_type,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": metrics,
            "filepath": os.path.join(MODEL_DIR, f"{model_type}_{version}.pkl"),
            "active": False,
        }
        # Modell speichern
        try:
            with open(meta["filepath"], "wb") as f:
                pickle.dump(model, f)
            self.models[version] = meta
            self._save_registry()
            log.info("REGISTRY", f"Modell registriert: {version} ({model_type}) "
                                 f"Acc: {metrics.get('test_acc', '?')}")
            return True
        except Exception as e:
            log.error("REGISTRY", f"Registrierung fehlgeschlagen: {e}")
            return False

    def activate(self, version):
        """Aktiviert ein Modell als das aktuelle."""
        if version not in self.models:
            log.warn("REGISTRY", f"Version {version} nicht gefunden")
            return False
        # Alle deaktivieren
        for v in self.models:
            self.models[v]["active"] = False
        # Neues aktivieren
        self.models[version]["active"] = True
        self.active_version = version
        try:
            with open(self.models[version]["filepath"], "rb") as f:
                self.active_model = pickle.load(f)
            self._save_registry()
            log.info("REGISTRY", f"Modell aktiviert: {version}")
            return True
        except Exception as e:
            log.error("REGISTRY", f"Laden fehlgeschlagen: {e}")
            return False

    def get_best(self, metric="test_acc"):
        """Gibt das Modell mit der besten Metrik zurueck."""
        if not self.models:
            return None
        best_v = max(self.models.keys(),
                     key=lambda v: self.models[v].get("metrics", {}).get(metric, 0))
        return best_v

    def load(self, version):
        """Laedt ein Modell von Disk."""
        if version not in self.models:
            return None
        try:
            with open(self.models[version]["filepath"], "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def compare(self) -> List[Dict]:
        """Vergleicht alle registrierten Modelle."""
        comparison = []
        for v, meta in sorted(self.models.items(), reverse=True):
            comparison.append({
                "version": v,
                "type": meta.get("type", "?"),
                "registered": meta.get("registered_at", "?"),
                "active": meta.get("active", False),
                "metrics": meta.get("metrics", {}),
            })
        return comparison

    def cleanup(self, keep_n=5):
        """Behaelt nur die N neuesten Modelle."""
        if len(self.models) <= keep_n:
            return 0
        sorted_versions = sorted(self.models.keys(), reverse=True)
        to_delete = sorted_versions[keep_n:]
        for v in to_delete:
            filepath = self.models[v].get("filepath", "")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            del self.models[v]
        self._save_registry()
        log.info("REGISTRY", f"Cleanup: {len(to_delete)} alte Modelle entfernt")
        return len(to_delete)

    def _load_registry(self):
        if not os.path.exists(REGISTRY_FILE):
            return
        try:
            with open(REGISTRY_FILE, "r") as f:
                data = json.load(f)
            self.models = data.get("models", {})
            self.active_version = data.get("active_version")
            if self.active_version and self.active_version in self.models:
                self.activate(self.active_version)
        except Exception:
            self.models = {}

    def _save_registry(self):
        try:
            data = {"models": self.models, "active_version": self.active_version}
            with open(REGISTRY_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def get_status(self):
        return {
            "total_models": len(self.models),
            "active_version": self.active_version,
            "best": self.get_best(),
        }
