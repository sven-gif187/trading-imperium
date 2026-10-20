"""
Trading Imperium V5 – Fill Reconciler
Gleicht Boersen-Fills mit internem State ab.
Erkennt: fehlende Fills, unbekannte Orders, Preis-Abweichungen.
"""
import time
from typing import Dict, List
from core.logger import log


class FillReconciler:
    """Vergleicht was die Boerse meldet mit was wir lokal wissen."""

    def __init__(self, order_manager):
        self.order_manager = order_manager
        self.discrepancies: List[Dict] = []
        self.last_reconcile = 0

    def reconcile(self, exchange_orders: List[Dict], exchange_trades: List[Dict] = None):
        """
        Hauptfunktion: Gleicht Boerse mit lokalem State ab.
        exchange_orders: Offene Orders von der Boerse
        exchange_trades: Letzte Trades von der Boerse
        """
        self.last_reconcile = time.time()
        issues = []

        # 1. Offene Orders abgleichen
        local_open = self.order_manager.get_open_orders()
        exchange_ids = {str(o.get("id", "")) for o in exchange_orders}

        for local in local_open:
            eid = local.get("exchange_id")
            if eid and str(eid) not in exchange_ids:
                # Lokal offen aber nicht bei Boerse -> wurde gefuellt oder gecancellt
                issues.append({
                    "type": "missing_at_exchange",
                    "client_id": local["client_id"],
                    "symbol": local["symbol"],
                    "action": "Vermutlich gefuellt oder gecancellt",
                })
                log.warn("RECONCILE", f"Order {local['client_id'][:20]} lokal offen aber nicht bei Boerse")

        # 2. Unbekannte Boersen-Orders
        local_ids = {o.get("exchange_id") for o in local_open if o.get("exchange_id")}
        for ex_order in exchange_orders:
            eid = str(ex_order.get("id", ""))
            if eid and eid not in local_ids:
                issues.append({
                    "type": "unknown_exchange_order",
                    "exchange_id": eid,
                    "symbol": ex_order.get("symbol", "?"),
                    "action": "Unbekannte Order bei Boerse gefunden",
                })
                log.warn("RECONCILE", f"Unbekannte Order bei Boerse: {eid}")

        # 3. Trade-Abgleich (Slippage prüfen)
        if exchange_trades:
            recent_history = self.order_manager.get_history(20)
            for trade in exchange_trades[-10:]:
                trade_price = trade.get("price", 0)
                trade_id = trade.get("order", "")
                # Passende lokale Order finden
                for local in recent_history:
                    if local.get("exchange_id") == trade_id:
                        expected = local.get("fill_price", 0)
                        if expected > 0 and trade_price > 0:
                            slippage_pct = abs((trade_price - expected) / expected) * 100
                            if slippage_pct > 0.5:
                                issues.append({
                                    "type": "slippage",
                                    "symbol": local["symbol"],
                                    "expected": expected,
                                    "actual": trade_price,
                                    "slippage_pct": round(slippage_pct, 3),
                                })
                                log.warn("RECONCILE", f"Slippage {local['symbol']}: {slippage_pct:.3f}%")

        self.discrepancies = issues
        if issues:
            log.info("RECONCILE", f"Abgleich: {len(issues)} Diskrepanzen gefunden")
        else:
            log.info("RECONCILE", "Abgleich OK: keine Diskrepanzen")

        return issues

    def get_status(self):
        return {
            "last_reconcile": self.last_reconcile,
            "discrepancies": len(self.discrepancies),
            "details": self.discrepancies[-5:],
        }
