"""
Trading Imperium V6 – Health Monitor
Überwacht den Systemzustand: Heartbeats, API-Latenz, Thread-Status,
Fehlerquoten. Löst Alarme aus bei Problemen.
Features: Selbsttest, Auto-Restart-Tracking, Diagnose mit Exception-Details.
"""
import time
import threading
import traceback
try:
    import psutil
except ImportError:
    psutil = None
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone


class HealthMonitor:
    """Überwacht die Gesundheit aller System-Komponenten."""

    def __init__(self):
        self._components: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._alerts: List[Dict] = []
        self._restart_callbacks: Dict[str, Callable] = {}
        self._max_restart_attempts = 3

    def register(self, name: str, restart_fn: Optional[Callable] = None):
        """Registriert eine Komponente zur Überwachung.
        Optional: restart_fn wird bei toter Komponente aufgerufen (max 3x)."""
        with self._lock:
            self._components[name] = {
                "last_heartbeat": time.time(),
                "status": "starting",
                "errors": 0,
                "latency_ms": 0,
                "last_error": "",
                "last_error_time": 0,
                "restart_attempts": 0,
                "restart_failed": False,  # True wenn 3x Restart fehlgeschlagen
                "registered_at": time.time(),
            }
            if restart_fn:
                self._restart_callbacks[name] = restart_fn

    def heartbeat(self, name: str, status: str = "ok", latency_ms: int = 0):
        """Sendet einen Heartbeat für eine Komponente."""
        with self._lock:
            if name in self._components:
                self._components[name]["last_heartbeat"] = time.time()
                self._components[name]["status"] = status
                self._components[name]["latency_ms"] = latency_ms
                # Reset restart counter bei erfolgreichem Heartbeat
                if self._components[name]["restart_attempts"] > 0:
                    self._components[name]["restart_attempts"] = 0
                    self._components[name]["restart_failed"] = False

    def report_error(self, name: str, error: str, exception: Optional[Exception] = None):
        """Meldet einen Fehler MIT konkretem Grund für eine Komponente."""
        # Volle Exception-Details extrahieren
        if exception:
            error_detail = f"{type(exception).__name__}: {str(exception)}"
            tb = traceback.format_exc()
        else:
            error_detail = str(error)
            tb = ""

        with self._lock:
            if name in self._components:
                self._components[name]["errors"] += 1
                self._components[name]["status"] = "error"
                self._components[name]["last_error"] = error_detail[:300]
                self._components[name]["last_error_time"] = time.time()
            self._alerts.append({
                "component": name,
                "error": error_detail[:300],
                "traceback": tb[:500] if tb else "",
                "time": datetime.now(timezone.utc).isoformat()
            })
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]

    def check_all(self, timeout_sec: int = 120) -> Dict:
        """Prüft den Zustand aller Komponenten + triggert Auto-Restart."""
        now = time.time()
        result = {
            "healthy": True,
            "uptime_sec": int(now - self._start_time),
            "components": {},
            "dead_components": [],
            "dead_with_reason": {},  # Detaillierte Tot-Meldungen
            "permanently_dead": [],  # Nach 3 Restarts immer noch tot
        }

        components_to_restart = []

        with self._lock:
            for name, info in self._components.items():
                age = now - info["last_heartbeat"]
                is_alive = age < timeout_sec
                # Grace-Period: Frisch registrierte Komponenten kriegen 30s
                if not is_alive and (now - info["registered_at"]) < 30:
                    is_alive = True
                    info["status"] = "starting"

                comp_status = {
                    "status": info["status"] if is_alive else "dead",
                    "last_seen_sec_ago": int(age),
                    "errors": info["errors"],
                    "latency_ms": info["latency_ms"],
                    "last_error": info.get("last_error", ""),
                    "restart_attempts": info.get("restart_attempts", 0),
                    "restart_failed": info.get("restart_failed", False),
                }
                result["components"][name] = comp_status
                if not is_alive:
                    result["healthy"] = False
                    result["dead_components"].append(name)
                    # Detail-Meldung mit konkretem Grund
                    reason = info.get("last_error", "")
                    if not reason:
                        reason = f"Kein Heartbeat seit {int(age)}s"
                    result["dead_with_reason"][name] = reason

                    # Permanently dead (nach 3 Restarts)
                    if info.get("restart_failed"):
                        result["permanently_dead"].append(name)
                    elif info.get("restart_attempts", 0) < self._max_restart_attempts:
                        if name in self._restart_callbacks:
                            components_to_restart.append(name)

        # Auto-Restart außerhalb des Locks
        for name in components_to_restart:
            self._attempt_restart(name)

        # System-Metriken
        try:
            if psutil:
                result["cpu_pct"] = psutil.cpu_percent(interval=0)
                result["ram_pct"] = psutil.virtual_memory().percent
            else:
                result["cpu_pct"] = 0
                result["ram_pct"] = 0
        except Exception:
            result["cpu_pct"] = 0
            result["ram_pct"] = 0

        return result

    def _attempt_restart(self, name: str):
        """Versucht eine tote Komponente neu zu starten (max 3x)."""
        with self._lock:
            if name not in self._components:
                return
            attempts = self._components[name].get("restart_attempts", 0)
            if attempts >= self._max_restart_attempts:
                self._components[name]["restart_failed"] = True
                return
            self._components[name]["restart_attempts"] = attempts + 1
            callback = self._restart_callbacks.get(name)

        if callback:
            try:
                from core.logger import log
                log.warn("HEALTH", f"Auto-Restart Versuch {attempts + 1}/{self._max_restart_attempts}: {name}")
                callback()
                # Heartbeat sofort nach Restart
                with self._lock:
                    self._components[name]["last_heartbeat"] = time.time()
                    self._components[name]["status"] = "restarted"
            except Exception as e:
                self.report_error(name, f"Restart fehlgeschlagen: {e}", exception=e)
                with self._lock:
                    if attempts + 1 >= self._max_restart_attempts:
                        self._components[name]["restart_failed"] = True

    def run_diagnostic(self, components_dict: Dict[str, Callable]) -> Dict:
        """Selbsttest aller Komponenten beim Start.
        components_dict: {name: test_callable} - jede Test-Funktion soll keine Exception werfen.
        """
        from core.logger import log
        log.info("HEALTH", "🔍 Starte System-Selbsttest...")
        results = {"passed": [], "failed": {}, "total": len(components_dict)}

        for name, test_fn in components_dict.items():
            try:
                test_fn()
                results["passed"].append(name)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                results["failed"][name] = error_msg
                self.report_error(name, error_msg, exception=e)
                log.warn("HEALTH", f"  ❌ {name}: {error_msg}")

        passed = len(results["passed"])
        total = results["total"]
        log.info("HEALTH", f"🔍 Selbsttest: {passed}/{total} OK"
                          + (f" | Fehler: {list(results['failed'].keys())}" if results["failed"] else ""))
        return results

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """Gibt die letzten Alarme zurück."""
        return self._alerts[-limit:]

    def get_uptime(self) -> str:
        """Gibt die Uptime als lesbaren String zurück."""
        sec = int(time.time() - self._start_time)
        hours, remainder = divmod(sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    def get_dead_with_reason(self) -> Dict[str, str]:
        """Schnellzugriff: Welche Komponenten sind tot und warum?"""
        result = self.check_all()
        return result.get("dead_with_reason", {})
