"""
Trading Imperium V6 – Shadow Mode (Schatten-Trades)
Laeuft parallel mit anderen Parametern und vergleicht Performance.
"""
import time
import threading
from typing import Dict, List
from core.logger import log


class ShadowTrader:
    """
    Fuehrt virtuelle Trades mit alternativen Parametern durch.
    Vergleicht Performance mit der aktiven Strategie in Echtzeit.
    """

    def __init__(self, name="Shadow"):
        self.name = name
        self.trades = []
        self.open_positions = {}
        self.total_pnl = 0
        self.total_trades = 0
        self.wins = 0
        self.params = {}  # Alternative Parameter

    def configure(self, sl_pct=5, trail_pct=2, pos_pct=20, min_score=4):
        """Setzt alternative Parameter."""
        self.params = {
            "sl_pct": sl_pct, "trail_pct": trail_pct,
            "pos_pct": pos_pct, "min_score": min_score}

    def should_buy(self, score, balance_usd) -> bool:
        """Prueft ob Shadow-Strategie kaufen wuerde."""
        return score >= self.params.get("min_score", 4) and balance_usd > 10

    def simulate_buy(self, symbol, price, amount_usd):
        """Simuliert einen Kauf."""
        qty = amount_usd / price if price > 0 else 0
        self.open_positions[symbol] = {
            "entry": price, "qty": qty, "highest": price,
            "amount": amount_usd, "time": time.time()}

    def check_sell(self, symbol, current_price) -> bool:
        """Prueft ob Position verkauft werden sollte."""
        if symbol not in self.open_positions:
            return False
        pos = self.open_positions[symbol]
        entry = pos["entry"]
        highest = pos["highest"]

        if current_price > highest:
            pos["highest"] = current_price
            highest = current_price

        pnl_pct = ((current_price / entry) - 1) * 100
        fall = ((highest - current_price) / highest * 100) if highest > 0 else 0

        # Stop-Loss
        if pnl_pct <= -self.params.get("sl_pct", 5):
            return True
        # Trailing
        if pnl_pct > 0.3 and fall >= self.params.get("trail_pct", 2):
            return True
        return False

    def simulate_sell(self, symbol, price):
        """Simuliert einen Verkauf."""
        if symbol not in self.open_positions:
            return 0
        pos = self.open_positions[symbol]
        pnl = (price - pos["entry"]) * pos["qty"]
        self.total_pnl += pnl
        self.total_trades += 1
        if pnl > 0:
            self.wins += 1
        self.trades.append({
            "symbol": symbol, "entry": pos["entry"],
            "exit": price, "pnl": round(pnl, 2),
            "time": time.strftime("%H:%M"),
        })
        if len(self.trades) > 100:
            self.trades = self.trades[-100:]
        del self.open_positions[symbol]
        return pnl

    def get_win_rate(self):
        return (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0

    def get_status(self):
        return {
            "name": self.name,
            "params": self.params,
            "pnl": round(self.total_pnl, 2),
            "trades": self.total_trades,
            "wins": self.wins,
            "win_rate": round(self.get_win_rate(), 1),
            "open": len(self.open_positions),
        }


class ShadowModeManager:
    """Verwaltet mehrere Shadow-Trader und vergleicht Performance."""

    def __init__(self):
        self.shadows = []
        self.active_pnl = 0  # Tracking der aktiven Strategie

        # 3 Shadow-Strategien mit verschiedenen Parametern
        s1 = ShadowTrader("Konservativ")
        s1.configure(sl_pct=3, trail_pct=1.0, pos_pct=10, min_score=5)
        self.shadows.append(s1)

        s2 = ShadowTrader("Aggressiv")
        s2.configure(sl_pct=6, trail_pct=2.5, pos_pct=30, min_score=3)
        self.shadows.append(s2)

        s3 = ShadowTrader("Balanced")
        s3.configure(sl_pct=4, trail_pct=1.5, pos_pct=20, min_score=4)
        self.shadows.append(s3)

    def on_signal(self, symbol, score, price, balance_usd):
        """Prueft ob Shadow-Strategien kaufen wuerden."""
        for shadow in self.shadows:
            if shadow.should_buy(score, balance_usd):
                amount = balance_usd * (shadow.params["pos_pct"] / 100)
                shadow.simulate_buy(symbol, price, amount)

    def on_price_update(self, symbol, current_price):
        """Prueft Sell-Conditions fuer alle Shadows."""
        for shadow in self.shadows:
            if shadow.check_sell(symbol, current_price):
                shadow.simulate_sell(symbol, current_price)

    def record_active_pnl(self, pnl):
        """Trackt PnL der aktiven Strategie zum Vergleich."""
        self.active_pnl += pnl

    def get_comparison(self) -> str:
        """Vergleicht alle Strategien."""
        lines = [f"{'Strategie':<15} {'P&L':>10} {'Trades':>7} {'WR':>6}",
                 "-" * 40,
                 f"{'AKTIV':<15} {self.active_pnl:>+10.2f} {'':>7} {'':>6}"]
        for s in self.shadows:
            st = s.get_status()
            lines.append(f"{st['name']:<15} {st['pnl']:>+10.2f} {st['trades']:>7} {st['win_rate']:>5.0f}%")
        return "\n".join(lines)

    def get_best_shadow(self):
        """Gibt die Shadow-Strategie mit bestem PnL zurueck."""
        if not self.shadows:
            return None
        return max(self.shadows, key=lambda s: s.total_pnl)

    def get_status(self):
        return {
            "active_pnl": round(self.active_pnl, 2),
            "shadows": [s.get_status() for s in self.shadows],
            "best": self.get_best_shadow().get_status() if self.shadows else {},
        }
