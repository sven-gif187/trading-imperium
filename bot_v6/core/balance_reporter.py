"""
Trading Imperium V6 - Balance Reporter v4 FINAL
Liest Positionen aus risk_engine.open_positions
mit entry_price, qty, highest_price.
Bekommt Echtzeit-Preise aus data_agent.price_cache.
"""
import time
import threading
from typing import Optional, Dict


class BalanceReporter:
    def __init__(self, app, interval_sec: int = 30):
        self.app = app
        self.interval_sec = interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._initial_equity: Optional[float] = None
        self._first_run = True

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="balance-reporter")
        self._thread.start()
        try:
            from core.logger import log
            log.info("BALANCE", "Balance-Reporter v4 gestartet (alle 30s)")
        except Exception:
            pass

    def stop(self):
        self._running = False

    def _loop(self):
        time.sleep(5)
        while self._running:
            try:
                self._report()
            except Exception as e:
                try:
                    from core.logger import log
                    log.warn("BALANCE", f"Fehler: {str(e)[:120]}")
                except Exception:
                    pass
            time.sleep(self.interval_sec)

    def _get_usdc_balance(self) -> float:
        try:
            if hasattr(self.app, "execution"):
                bal = self.app.execution.get_balance()
                if bal and "total" in bal:
                    total = bal["total"]
                    return float(total.get("USDC", 0)) + float(total.get("USDT", 0))
        except Exception:
            pass
        return 0.0

    def _get_prices(self) -> Dict[str, float]:
        prices = {}
        try:
            if hasattr(self.app, "data_agent") and hasattr(self.app.data_agent, "price_cache"):
                cache = self.app.data_agent.price_cache
                if cache and isinstance(cache, dict):
                    for sym, price in cache.items():
                        if price:
                            if "/" in sym:
                                coin = sym.split("/")[0]
                                prices[coin] = float(price)
                                prices[sym] = float(price)
                            else:
                                prices[sym] = float(price)
        except Exception:
            pass
        return prices

    def _get_open_positions(self) -> Dict:
        try:
            if hasattr(self.app, "risk_engine") and hasattr(self.app.risk_engine, "open_positions"):
                positions = {}
                for sym, pos in self.app.risk_engine.open_positions.items():
                    if pos.get("active", False):
                        positions[sym] = pos
                return positions
        except Exception:
            pass
        return {}

    def _get_realized_pnl(self) -> float:
        for attr in ["session_pnl", "_session_pnl", "realized_pnl", "_realized_pnl", "total_pnl", "_total_pnl"]:
            v = getattr(self.app, attr, None)
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    pass
        for attr in ["trade_journal", "journal", "_journal"]:
            j = getattr(self.app, attr, None)
            if j and hasattr(j, "get_stats"):
                try:
                    return float(j.get_stats().get("total_pnl", 0))
                except Exception:
                    pass
        return 0.0

    def _report(self):
        from core.logger import log

        usdc_free = self._get_usdc_balance()
        prices = self._get_prices()
        positions = self._get_open_positions()
        realized_pnl = self._get_realized_pnl()

        if self._first_run:
            self._first_run = False
            log.info("BALANCE",
                     f"Diagnose: usdc={usdc_free:.2f}$, prices={len(prices)}, "
                     f"positions={list(positions.keys())}, realized={realized_pnl:+.2f}$")

        positions_value = 0.0
        unrealized_pnl = 0.0
        coin_lines = []
        no_price = []

        for symbol, pos in positions.items():
            entry = pos.get("entry_price", 0) or pos.get("entry", 0)
            qty = pos.get("qty", 0) or pos.get("quantity", 0)

            if not entry or not qty:
                continue

            coin = symbol.split("/")[0] if "/" in symbol else symbol
            current = prices.get(symbol, 0) or prices.get(coin, 0)

            if current <= 0:
                no_price.append(coin)
                positions_value += qty * entry
                coin_lines.append(f"{coin}={qty:.4f} @{entry:.2f}$ (?)")
                continue

            current_value = qty * current
            positions_value += current_value
            pnl = (current - entry) * qty
            pnl_pct = ((current / entry) - 1) * 100
            unrealized_pnl += pnl
            coin_lines.append(f"{coin}={qty:.4f} ({pnl_pct:+.2f}%, {pnl:+.2f}$)")

        # === [E10-KAPITAL 29.07.2026] BTC-SPARPLAN MIT AUSWEISEN ===
        # Der Sparplan zieht USDC ab, bucht die BTC aber nur in seine
        # eigene Datei. Bis hierher fehlte er in JEDER Anzeige: gemeldet
        # wurden 370.60 $, tatsaechlich waren es 467.14 $ - die Differenz
        # von 96.54 $ waren 27 Sparplan-Kaeufe. Der Nutzer sah -25.9 %
        # statt der echten -6.6 %.
        sparplan_wert = 0.0
        sparplan_btc = 0.0
        try:
            acc = getattr(self.app, "btc_accumulator", None)
            if acc is not None:
                sparplan_btc = float(getattr(acc, "total_btc", 0) or 0)
                if sparplan_btc > 0:
                    p = prices.get("BTC/USDC", 0) or prices.get("BTC/USDT", 0) or 0
                    sparplan_wert = (sparplan_btc * p) if p > 0 else \
                        float(getattr(acc, "total_invested_usd", 0) or 0)
        except Exception:
            sparplan_wert = 0.0

        total_equity = usdc_free + positions_value + sparplan_wert

        if self._initial_equity is None and total_equity > 0:
            self._initial_equity = total_equity - unrealized_pnl

        roi_pct = 0.0
        if self._initial_equity and self._initial_equity > 0:
            roi_pct = ((total_equity / self._initial_equity) - 1) * 100

        sparplan_text = ""
        if sparplan_wert > 0:
            sparplan_text = f" | Sparplan: {sparplan_wert:.2f}$ ({sparplan_btc:.8f} BTC)"
        log.info("BALANCE",
                 f"USDC: {usdc_free:.2f}$ | Positionen: {positions_value:.2f}$"
                 f"{sparplan_text} | Total: {total_equity:.2f}$ (ROI: {roi_pct:+.2f}%)")
        log.info("BALANCE",
                 f"Realisiert: {realized_pnl:+.2f}$ | Unrealisiert: {unrealized_pnl:+.2f}$")
        if coin_lines:
            log.info("BALANCE", f"Coins: {chr(124).join([str(c) for c in coin_lines])}")
        if no_price:
            log.info("BALANCE", f"Keine Live-Preise fuer: {chr(44).join(no_price)}")
