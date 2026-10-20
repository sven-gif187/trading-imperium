"""
Trading Imperium V6 – Futures/Perpetuals Trading
Handelt USDC-M Perpetual Futures mit Hebel auf Binance.
Nutzt Funding Rates als Zusatzsignal.
"""
import time
import threading
from typing import Dict, Optional
from core.logger import log

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False


class FuturesTrader:
    """Handelt Perpetual Futures mit einstellbarem Hebel."""

    def __init__(self, max_leverage=3, mode="cross"):
        self.max_leverage = max_leverage
        self.mode = mode  # "cross" oder "isolated"
        self.client = None
        self.open_positions = {}
        self.total_pnl = 0
        self.trades_count = 0
        self._paper_mode = True
        self._paper_positions = {}
        self._paper_balance = 1000  # Futures Paper Balance

    def connect(self, api_key="", api_secret="", testnet=True):
        """Verbindet mit Binance Futures."""
        if not HAS_CCXT:
            log.warn("FUTURES", "ccxt nicht installiert")
            return False
        try:
            params = {
                "enableRateLimit": True, "timeout": 15000,
                "options": {"defaultType": "future", "adjustForTimeDifference": True}
            }
            if api_key and api_secret:
                params["apiKey"] = api_key
                params["secret"] = api_secret
            if testnet:
                params["options"]["sandboxMode"] = True

            self.client = ccxt.binance(params)
            self._paper_mode = not (api_key and api_secret)
            log.info("FUTURES", f"Verbunden ({'Paper' if self._paper_mode else 'Live'}, Max {self.max_leverage}x)")
            return True
        except Exception as e:
            log.warn("FUTURES", f"Verbindung fehlgeschlagen: {str(e)[:50]}")
            return False

    def open_long(self, symbol, amount_usd, leverage=2, entry_price=0) -> Dict:
        """Oeffnet eine Long-Position."""
        leverage = min(leverage, self.max_leverage)

        if self._paper_mode:
            return self._paper_open(symbol, "LONG", amount_usd, leverage, entry_price)

        try:
            self.client.set_leverage(leverage, symbol)
            self.client.set_margin_mode(self.mode, symbol)
            qty = round((amount_usd * leverage) / entry_price, 6) if entry_price > 0 else 0
            order = self.client.create_market_buy_order(symbol, qty)
            self.open_positions[symbol] = {
                "side": "LONG", "entry": order.get("average", entry_price),
                "qty": qty, "leverage": leverage, "time": time.time()}
            log.trade("FUTURES", f"LONG {symbol} {qty} @ {leverage}x = {amount_usd * leverage:.2f}$")
            return {"status": "filled", "side": "LONG", "qty": qty}
        except Exception as e:
            log.error("FUTURES", f"Long Fehler: {e}")
            return {"status": "error", "error": str(e)}

    def open_short(self, symbol, amount_usd, leverage=2, entry_price=0) -> Dict:
        """Oeffnet eine Short-Position."""
        leverage = min(leverage, self.max_leverage)

        if self._paper_mode:
            return self._paper_open(symbol, "SHORT", amount_usd, leverage, entry_price)

        try:
            self.client.set_leverage(leverage, symbol)
            qty = round((amount_usd * leverage) / entry_price, 6) if entry_price > 0 else 0
            order = self.client.create_market_sell_order(symbol, qty)
            self.open_positions[symbol] = {
                "side": "SHORT", "entry": order.get("average", entry_price),
                "qty": qty, "leverage": leverage, "time": time.time()}
            log.trade("FUTURES", f"SHORT {symbol} {qty} @ {leverage}x")
            return {"status": "filled", "side": "SHORT", "qty": qty}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def close_position(self, symbol, current_price=0) -> Dict:
        """Schliesst eine offene Position."""
        pos = self.open_positions.get(symbol) or self._paper_positions.get(symbol)
        if not pos:
            return {"status": "no_position"}

        if self._paper_mode:
            return self._paper_close(symbol, current_price)

        try:
            if pos["side"] == "LONG":
                order = self.client.create_market_sell_order(symbol, pos["qty"])
            else:
                order = self.client.create_market_buy_order(symbol, pos["qty"])
            close_price = order.get("average", current_price)
            pnl = self._calc_pnl(pos, close_price)
            self.total_pnl += pnl
            self.trades_count += 1
            del self.open_positions[symbol]
            log.trade("FUTURES", f"CLOSE {symbol}: P&L {pnl:+.2f}$ ({pos['side']} {pos['leverage']}x)")
            return {"status": "closed", "pnl": pnl}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _calc_pnl(self, pos, close_price) -> float:
        entry = pos["entry"]
        lev = pos["leverage"]
        qty = pos["qty"]
        if pos["side"] == "LONG":
            return (close_price - entry) / entry * qty * entry * lev
        else:
            return (entry - close_price) / entry * qty * entry * lev

    def _paper_open(self, symbol, side, amount, leverage, price) -> Dict:
        if self._paper_balance < amount:
            return {"status": "rejected", "error": "Balance zu niedrig"}
        self._paper_balance -= amount
        qty = round((amount * leverage) / price, 6) if price > 0 else amount
        self._paper_positions[symbol] = {
            "side": side, "entry": price, "qty": qty,
            "leverage": leverage, "margin": amount, "time": time.time()}
        log.trade("FUTURES", f"[PAPER] {side} {symbol} {qty:.6f} @ {leverage}x ({amount:.2f}$ Margin)")
        return {"status": "filled", "side": side, "qty": qty}

    def _paper_close(self, symbol, current_price) -> Dict:
        pos = self._paper_positions.get(symbol)
        if not pos:
            return {"status": "no_position"}
        pnl = self._calc_pnl(pos, current_price)
        self._paper_balance += pos["margin"] + pnl
        self.total_pnl += pnl
        self.trades_count += 1
        del self._paper_positions[symbol]
        log.trade("FUTURES", f"[PAPER] CLOSE {symbol}: P&L {pnl:+.2f}$ (Margin {pos['margin']:.2f}$)")
        return {"status": "closed", "pnl": round(pnl, 2)}

    def check_liquidation(self, symbol, current_price) -> bool:
        """Prueft ob Position liquidiert werden muss."""
        pos = self._paper_positions.get(symbol) or self.open_positions.get(symbol)
        if not pos:
            return False
        entry = pos["entry"]
        lev = pos["leverage"]
        if pos["side"] == "LONG":
            liq_pct = -100 / lev * 0.9
            return ((current_price - entry) / entry * 100) < liq_pct
        else:
            liq_pct = 100 / lev * 0.9
            return ((current_price - entry) / entry * 100) > liq_pct

    def get_all_positions(self) -> Dict:
        return {**self.open_positions, **self._paper_positions}

    def get_status(self):
        all_pos = self.get_all_positions()
        return {
            "mode": "paper" if self._paper_mode else "live",
            "open_positions": len(all_pos),
            "total_pnl": round(self.total_pnl, 2),
            "trades": self.trades_count,
            "max_leverage": self.max_leverage,
            "balance": round(self._paper_balance, 2) if self._paper_mode else "?",
            "positions": {k: {"side": v["side"], "leverage": v["leverage"]}
                         for k, v in all_pos.items()},
        }
