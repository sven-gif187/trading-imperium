"""
Trading Imperium V6 – Health Monitor mit Auto-Restart
Ueberwacht Agenten und startet sie bei Crash/Freeze automatisch neu.
"""
import time
import threading
from typing import Dict, Callable
from core.logger import log


class AutoRestartMonitor:
    """Ueberwacht Agenten und restartet bei Freeze."""

    def __init__(self, timeout_sec=120):
        self.timeout_sec = timeout_sec
        self.agents = {}  # name -> {"last_seen": timestamp, "restart_fn": callable, "restarts": int}
        self.alerts = []
        self._running = False

    def register(self, name, restart_fn=None):
        """Registriert einen Agenten zur Ueberwachung."""
        self.agents[name] = {
            "last_seen": time.time(),
            "restart_fn": restart_fn,
            "restarts": 0,
            "status": "ok",
        }

    def heartbeat(self, name):
        """Agent meldet sich als lebendig."""
        if name in self.agents:
            self.agents[name]["last_seen"] = time.time()
            self.agents[name]["status"] = "ok"

    def start(self):
        """Startet den Monitor-Thread."""
        self._running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        log.info("MONITOR", f"Auto-Restart Monitor gestartet ({len(self.agents)} Agenten)")

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            now = time.time()
            for name, agent in self.agents.items():
                age = now - agent["last_seen"]
                if age > self.timeout_sec:
                    agent["status"] = "frozen"
                    if agent["restart_fn"] and agent["restarts"] < 5:
                        agent["restarts"] += 1
                        log.warn("MONITOR", f"Agent '{name}' antwortet nicht ({age:.0f}s) – Neustart #{agent['restarts']}")
                        try:
                            agent["restart_fn"]()
                            agent["last_seen"] = time.time()
                            agent["status"] = "restarted"
                        except Exception as e:
                            log.error("MONITOR", f"Neustart '{name}' fehlgeschlagen: {e}")
                            agent["status"] = "error"
                        self.alerts.append({
                            "agent": name, "action": "restart",
                            "time": time.strftime("%H:%M:%S"),
                            "attempt": agent["restarts"],
                        })
                    elif agent["restarts"] >= 5:
                        agent["status"] = "dead"
                elif age > self.timeout_sec * 0.7:
                    agent["status"] = "slow"
            time.sleep(30)

    def get_agent_status(self, name) -> str:
        """Gibt Ampel-Status zurueck: ok, slow, frozen, error, dead."""
        return self.agents.get(name, {}).get("status", "unknown")

    def get_ampel(self, name) -> str:
        """Gibt Ampel-Emoji zurueck."""
        status = self.get_agent_status(name)
        return {"ok": "🟢", "slow": "🟡", "frozen": "🔴",
                "restarted": "🟡", "error": "🔴", "dead": "💀"}.get(status, "⚪")

    def get_all_status(self) -> Dict:
        result = {}
        for name, agent in self.agents.items():
            result[name] = {
                "status": agent["status"],
                "ampel": self.get_ampel(name),
                "age_sec": int(time.time() - agent["last_seen"]),
                "restarts": agent["restarts"],
            }
        return result

    def get_alerts(self, n=10):
        return self.alerts[-n:]
