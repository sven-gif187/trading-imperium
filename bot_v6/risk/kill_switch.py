"""
Trading Imperium V5 – Kill Switch
Notfallstopp. Wenn aktiviert, wird KEIN Trade mehr ausgefuehrt.
Kann durch: Tages-Verlust, Drawdown, oder manuell ausgeloest werden.
"""
import time
from typing import Dict, Optional
from core.logger import log


class KillSwitch:
    """Notfallstopp fuer den Bot."""

    def __init__(self, max_daily_loss=50.0):
        self.max_daily_loss = max_daily_loss
        self.daily_loss = 0.0
        self.active = False
        self.trigger_reason = ""
        self.trigger_time = 0
        self.trigger_count = 0

    def check(self):
        """Prueft ob Kill-Switch ausgeloest werden muss."""
        if self.active:
            return True

        if self.daily_loss >= self.max_daily_loss:
            self.activate(f"Tages-Verlust {self.daily_loss:.2f}$ >= {self.max_daily_loss:.2f}$")
            return True

        return False

    def activate(self, reason="Manuell"):
        """Aktiviert den Kill-Switch."""
        if not self.active:
            self.active = True
            self.trigger_reason = reason
            self.trigger_time = time.time()
            self.trigger_count += 1
            log.error("KILL", f"KILL-SWITCH AKTIVIERT: {reason}")

    def deactivate(self):
        """Deaktiviert den Kill-Switch (manuell)."""
        self.active = False
        self.trigger_reason = ""
        log.info("KILL", "Kill-Switch deaktiviert")

    def add_loss(self, amount):
        """Registriert einen Verlust."""
        self.daily_loss += abs(amount)
        self.check()

    def reset_daily(self):
        """Tages-Reset (z.B. um Mitternacht)."""
        self.daily_loss = 0.0
        if self.active and "Tages-Verlust" in self.trigger_reason:
            self.deactivate()
        log.info("KILL", f"Tages-Reset. Verlust: 0.00$/{self.max_daily_loss:.2f}$")

    def get_status(self):
        return {
            "active": self.active,
            "reason": self.trigger_reason,
            "daily_loss": round(self.daily_loss, 2),
            "limit": self.max_daily_loss,
            "trigger_count": self.trigger_count,
        }
