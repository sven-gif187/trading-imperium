"""
Trading Imperium V6 – Grid Trading Bot
Platziert Kauf/Verkauf-Orders in einem Preisraster. Ideal fuer Seitwaertsmaerkte.
"""
import time
from typing import Dict, List
from core.events import DecisionIntent, Side
from core.logger import log


class GridTrader:
    """Grid-Trading Strategie fuer Seitwaertsmaerkte."""

    def __init__(self, grid_size_pct=1.0, num_grids=5, amount_per_grid=100):
        self.grid_size_pct = grid_size_pct
        self.num_grids = num_grids
        self.amount_per_grid = amount_per_grid
        self.active_grids = {}  # symbol -> {"levels": [...], "filled": {...}}
        self.total_profit = 0
        self.trades_count = 0

    def setup_grid(self, symbol, current_price) -> Dict:
        """Erstellt ein Grid um den aktuellen Preis."""
        levels = []
        for i in range(-self.num_grids, self.num_grids + 1):
            price = current_price * (1 + i * self.grid_size_pct / 100)
            side = "BUY" if i < 0 else "SELL" if i > 0 else "CENTER"
            levels.append({"price": round(price, 2), "side": side,
                          "filled": False, "level": i})
        self.active_grids[symbol] = {
            "center": current_price, "levels": levels,
            "created": time.time(), "profit": 0}
        log.info("GRID", f"{symbol}: Grid erstellt um {current_price:,.2f}$ "
                        f"({self.num_grids} Level, {self.grid_size_pct}% Abstand)")
        return self.active_grids[symbol]

    def check_triggers(self, symbol, current_price) -> List[Dict]:
        """Prueft ob ein Grid-Level getriggert wurde."""
        if symbol not in self.active_grids:
            return []
        grid = self.active_grids[symbol]
        triggers = []
        for level in grid["levels"]:
            if level["filled"] or level["side"] == "CENTER":
                continue
            if level["side"] == "BUY" and current_price <= level["price"]:
                level["filled"] = True
                triggers.append({"side": "BUY", "price": level["price"],
                                "level": level["level"]})
                log.info("GRID", f"{symbol}: BUY Level {level['level']} @ {level['price']:,.2f}$")
            elif level["side"] == "SELL" and current_price >= level["price"]:
                level["filled"] = True
                triggers.append({"side": "SELL", "price": level["price"],
                                "level": level["level"]})
                profit = self.amount_per_grid * (self.grid_size_pct / 100)
                grid["profit"] += profit
                self.total_profit += profit
                log.info("GRID", f"{symbol}: SELL Level {level['level']} @ {level['price']:,.2f}$ (+{profit:.2f}$)")
            self.trades_count += 1
        return triggers

    def create_intents(self, symbol, triggers, balance_usd) -> List[DecisionIntent]:
        """Erstellt DecisionIntents aus Grid-Triggern."""
        intents = []
        for t in triggers:
            if t["side"] == "BUY" and balance_usd >= self.amount_per_grid:
                intent = DecisionIntent(
                    symbol=symbol, side=Side.BUY, confidence=0.6,
                    entry_price=t["price"], amount_usd=self.amount_per_grid,
                    strategy_id="GRID_TRADING", strategy_name="Grid Trading",
                    entry_reason=f"Grid Level {t['level']} @ {t['price']:,.2f}$",
                    score=5, agent_id="grid_trader")
                intents.append(intent)
        return intents

    def is_active(self, symbol) -> bool:
        return symbol in self.active_grids

    def remove_grid(self, symbol):
        if symbol in self.active_grids:
            profit = self.active_grids[symbol]["profit"]
            del self.active_grids[symbol]
            log.info("GRID", f"{symbol}: Grid entfernt. Profit: {profit:+.2f}$")

    def get_status(self):
        return {"active_grids": len(self.active_grids), "total_profit": round(self.total_profit, 2),
                "trades": self.trades_count, "grid_size": self.grid_size_pct,
                "symbols": list(self.active_grids.keys())}
