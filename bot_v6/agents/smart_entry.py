"""
Trading Imperium V6 – Smart Entry Timing
Wartet auf Pullback nach Kaufsignal statt direkt am Peak zu kaufen.
"""
import time
import threading
from typing import Dict, Optional
from core.events import DecisionIntent, Side
from core.logger import log


class SmartEntryAgent:
    """Wartet auf optimalen Einstiegspunkt nach Signal."""

    def __init__(self, max_wait_sec=300, pullback_pct=1.0, max_miss_pct=2.0):
        self.max_wait_sec = max_wait_sec   # Max 5 Min warten
        self.pullback_pct = pullback_pct   # Warte auf 1% Pullback
        self.max_miss_pct = max_miss_pct   # Kaufe trotzdem wenn >2% gestiegen
        self.pending = {}  # symbol -> {"intent": ..., "signal_price": ..., "time": ...}
        self.stats = {"improved": 0, "timeout": 0, "missed": 0}

    def queue_entry(self, intent, signal_price):
        """Stellt einen Kauf in die Warteschlange."""
        self.pending[intent.symbol] = {
            "intent": intent,
            "signal_price": signal_price,
            "lowest_since": signal_price,
            "time": time.time(),
        }
        log.info("SMART-ENTRY", f"{intent.symbol}: Warte auf Pullback (Signal @ {signal_price:,.2f}$)")

    def check(self, symbol, current_price, execute_fn):
        """Prueft ob es Zeit ist zu kaufen."""
        if symbol not in self.pending:
            return None

        entry = self.pending[symbol]
        intent = entry["intent"]
        signal_price = entry["signal_price"]
        elapsed = time.time() - entry["time"]

        # Tiefsten Preis seit Signal tracken
        if current_price < entry["lowest_since"]:
            entry["lowest_since"] = current_price

        # Pullback erkannt?
        pullback = ((signal_price - current_price) / signal_price) * 100
        if pullback >= self.pullback_pct:
            intent.entry_price = current_price
            log.info("SMART-ENTRY", f"{symbol}: Pullback {pullback:.1f}%! Kaufe @ {current_price:,.2f}$ "
                                    f"(Signal war {signal_price:,.2f}$)")
            self.stats["improved"] += 1
            del self.pending[symbol]
            return execute_fn(intent)

        # Timeout: Preis steigt ohne Pullback
        rise = ((current_price - signal_price) / signal_price) * 100
        if rise >= self.max_miss_pct or elapsed >= self.max_wait_sec:
            intent.entry_price = current_price
            reason = f"Timeout {elapsed:.0f}s" if elapsed >= self.max_wait_sec else f"Preis +{rise:.1f}%"
            log.info("SMART-ENTRY", f"{symbol}: {reason}, kaufe trotzdem @ {current_price:,.2f}$")
            self.stats["timeout"] += 1
            del self.pending[symbol]
            return execute_fn(intent)

        return None

    def cancel(self, symbol):
        if symbol in self.pending:
            del self.pending[symbol]

    def get_status(self):
        return {"pending": len(self.pending), "stats": self.stats,
                "symbols": list(self.pending.keys())}
