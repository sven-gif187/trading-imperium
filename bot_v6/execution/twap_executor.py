"""
Trading Imperium V6 – TWAP Order-Splitting
Teilt grosse Orders in kleinere Teilorders auf. Reduziert Slippage.
"""
import time
import threading
from typing import Dict, List
from core.logger import log


class TWAPExecutor:
    """Teilt grosse Orders in 3-5 Teilorders auf."""

    def __init__(self, min_split_usd=500, max_parts=5, delay_sec=30):
        self.min_split_usd = min_split_usd  # Nur Orders >= 500$ aufteilen
        self.max_parts = max_parts
        self.delay_sec = delay_sec
        self.active_twaps = {}
        self.completed = []

    def should_split(self, amount_usd) -> bool:
        return amount_usd >= self.min_split_usd

    def calculate_parts(self, amount_usd) -> List[float]:
        """Teilt Betrag in gleiche Teile."""
        if amount_usd < self.min_split_usd:
            return [amount_usd]
        n_parts = min(max(int(amount_usd / 100), 2), self.max_parts)
        part_size = amount_usd / n_parts
        return [round(part_size, 2)] * n_parts

    def execute_twap(self, intent, execution_engine, callback=None):
        """Fuehrt TWAP-Order in Hintergrund-Thread aus."""
        parts = self.calculate_parts(intent.amount_usd)
        if len(parts) <= 1:
            return None  # Kein Split noetig

        twap_id = f"twap_{int(time.time()*1000)}"
        self.active_twaps[twap_id] = {
            "symbol": intent.symbol, "total": intent.amount_usd,
            "parts": len(parts), "filled": 0, "status": "running"}

        def _run():
            import random
            original_amount = intent.amount_usd
            for i, part in enumerate(parts):
                # Abbruch-Check
                if self.active_twaps.get(twap_id, {}).get("status") == "cancelled":
                    log.info("TWAP", f"{intent.symbol}: Abgebrochen bei Teil {i+1}/{len(parts)}")
                    break
                try:
                    intent.amount_usd = part
                    result = execution_engine.execute(intent)
                    if result.status == "filled":
                        self.active_twaps[twap_id]["filled"] += 1
                        log.info("TWAP", f"{intent.symbol} Teil {i+1}/{len(parts)}: "
                                        f"{result.filled_qty:.6f} @ {result.avg_fill_price:,.2f}$")
                    if callback:
                        callback(result)
                except Exception as e:
                    log.error("TWAP", f"Teil {i+1}: {e}")
                if i < len(parts) - 1:
                    wait = self.delay_sec + random.randint(-10, 10)
                    time.sleep(max(5, wait))
            intent.amount_usd = original_amount
            if self.active_twaps.get(twap_id, {}).get("status") != "cancelled":
                self.active_twaps[twap_id]["status"] = "done"
            self.completed.append(twap_id)
            log.info("TWAP", f"Fertig: {intent.symbol} {len(parts)} Teile")

        threading.Thread(target=_run, daemon=True).start()
        return twap_id

    def get_status(self):
        active = sum(1 for t in self.active_twaps.values() if t["status"] == "running")
        return {"active": active, "completed": len(self.completed),
                "min_split": self.min_split_usd}

    def cancel_all(self):
        """Stoppt alle laufenden TWAPs sofort."""
        cancelled = 0
        for tid, t in self.active_twaps.items():
            if t["status"] == "running":
                t["status"] = "cancelled"
                cancelled += 1
        if cancelled:
            log.info("TWAP", f"{cancelled} laufende TWAPs abgebrochen")
        self.active_twaps.clear()
        return cancelled
