"""
Trading Imperium V5 – Order Manager
Place / Cancel / Status mit lokalem Tracking.
Jede Order wird lokal gespeichert und mit der Boerse abgeglichen.
"""
import time
import json
import os
import threading
from typing import Dict, List, Optional
from config.settings import DATA_DIR
from core.logger import log

ORDER_HISTORY_FILE = os.path.join(DATA_DIR, "order_history.json")


class OrderManager:
    """Verwaltet alle Orders mit lokalem Tracking."""

    def __init__(self):
        self._lock = threading.Lock()
        self.orders: Dict[str, Dict] = {}
        self.history: List[Dict] = []
        self._load()

    def place(self, client_id: str, symbol: str, side: str, amount: float,
              strategy: str = "", reason: str = "") -> Dict:
        """Registriert eine neue Order lokal BEVOR sie an die Boerse geht."""
        order = {
            "client_id": client_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "strategy": strategy,
            "reason": reason,
            "status": "pending",
            "exchange_id": None,
            "fill_price": None,
            "fill_qty": None,
            "fee": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        with self._lock:
            self.orders[client_id] = order
        log.info("ORDERS", f"Registriert: {side} {symbol} {amount:.2f}$ ({client_id[:20]})")
        return order

    def update_fill(self, client_id: str, exchange_id: str, fill_price: float,
                    fill_qty: float, fee: float = 0):
        """Aktualisiert Order mit Fill-Daten von der Boerse."""
        with self._lock:
            if client_id not in self.orders:
                log.warn("ORDERS", f"Unbekannte Order: {client_id[:20]}")
                return
            o = self.orders[client_id]
            o["status"] = "filled"
            o["exchange_id"] = exchange_id
            o["fill_price"] = fill_price
            o["fill_qty"] = fill_qty
            o["fee"] = fee
            o["updated_at"] = time.time()
            o["latency_ms"] = int((time.time() - o["created_at"]) * 1000)
            # In History verschieben
            self.history.append(dict(o))
            del self.orders[client_id]
            self._save()
        log.info("ORDERS", f"Filled: {o['side']} {o['symbol']} {fill_qty:.6f} @ {fill_price:,.2f}$")

    def update_rejected(self, client_id: str, reason: str):
        """Markiert Order als abgelehnt."""
        with self._lock:
            if client_id in self.orders:
                o = self.orders[client_id]
                o["status"] = "rejected"
                o["reason"] = reason
                o["updated_at"] = time.time()
                self.history.append(dict(o))
                del self.orders[client_id]
                self._save()
        log.warn("ORDERS", f"Rejected: {reason}")

    def update_error(self, client_id: str, error: str):
        """Markiert Order als fehlerhaft."""
        with self._lock:
            if client_id in self.orders:
                o = self.orders[client_id]
                o["status"] = "error"
                o["error"] = error[:200]
                o["updated_at"] = time.time()
                self.history.append(dict(o))
                del self.orders[client_id]
                self._save()
        log.error("ORDERS", f"Error: {error[:60]}")

    def cancel(self, client_id: str, exchange=None):
        """Versucht eine offene Order zu canceln."""
        with self._lock:
            if client_id not in self.orders:
                return False
            o = self.orders[client_id]
            if o["exchange_id"] and exchange:
                try:
                    exchange.cancel_order(o["exchange_id"], o["symbol"])
                    log.info("ORDERS", f"Cancelled: {client_id[:20]}")
                except Exception as e:
                    log.warn("ORDERS", f"Cancel fehlgeschlagen: {e}")
            o["status"] = "cancelled"
            self.history.append(dict(o))
            del self.orders[client_id]
            self._save()
        return True

    def get_open_orders(self) -> List[Dict]:
        """Alle offenen Orders."""
        with self._lock:
            return list(self.orders.values())

    def get_history(self, last_n=50) -> List[Dict]:
        """Letzte N Orders aus der History."""
        return self.history[-last_n:]

    def get_stats(self) -> Dict:
        filled = [o for o in self.history if o["status"] == "filled"]
        rejected = [o for o in self.history if o["status"] == "rejected"]
        errors = [o for o in self.history if o["status"] == "error"]
        return {
            "open": len(self.orders),
            "total_filled": len(filled),
            "total_rejected": len(rejected),
            "total_errors": len(errors),
            "avg_latency_ms": int(sum(o.get("latency_ms", 0) for o in filled) / max(len(filled), 1)),
        }

    def _load(self):
        if not os.path.exists(ORDER_HISTORY_FILE):
            return
        try:
            with open(ORDER_HISTORY_FILE, "r") as f:
                self.history = json.load(f)
        except Exception:
            self.history = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(ORDER_HISTORY_FILE), exist_ok=True)
            tmp = ORDER_HISTORY_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.history[-500:], f, indent=1, default=str)
            os.replace(tmp, ORDER_HISTORY_FILE)
        except Exception:
            pass
