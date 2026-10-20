"""
Trading Imperium V6 – Erweiterter DCA Bot
Dollar Cost Averaging mit dynamischen Intervallen basierend auf F&G und Volatilitaet.
"""
import time
from typing import Dict, List
from core.events import DecisionIntent, Side
from core.logger import log


class AdvancedDCA:
    """DCA mit dynamischen Intervallen und Betrag-Anpassung."""

    def __init__(self, base_amount=100, base_interval_min=60):
        self.base_amount = base_amount
        self.base_interval = base_interval_min * 60
        self.last_dca_time = {}  # coin -> timestamp
        self.dca_history = []
        self.total_invested = 0

    def should_dca(self, symbol, fear_greed=50, volatility=0, regime="UNKNOWN") -> Dict:
        """Prueft ob DCA ausgefuehrt werden soll und passt Betrag/Intervall an."""
        now = time.time()
        last = self.last_dca_time.get(symbol, 0)

        # Dynamisches Intervall basierend auf F&G
        if fear_greed < 15:
            interval = self.base_interval * 0.25  # 4x oefter bei Extreme Fear
            amount_mult = 2.0
        elif fear_greed < 25:
            interval = self.base_interval * 0.5   # 2x oefter
            amount_mult = 1.5
        elif fear_greed < 40:
            interval = self.base_interval * 0.75
            amount_mult = 1.2
        elif fear_greed > 80:
            interval = self.base_interval * 3.0   # 3x seltener bei Gier
            amount_mult = 0.5
        elif fear_greed > 65:
            interval = self.base_interval * 2.0
            amount_mult = 0.7
        else:
            interval = self.base_interval
            amount_mult = 1.0

        # Volatilitaets-Anpassung
        if volatility > 0.03:
            amount_mult *= 0.8  # Weniger bei hoher Vola
        elif volatility < 0.01:
            amount_mult *= 1.1  # Mehr bei niedriger Vola

        # Baerenmarkt: mehr investieren (guenstig!)
        if "BEAR" in regime or "CAPITULATION" in regime:
            amount_mult *= 1.3

        if (now - last) < interval:
            return {"execute": False, "next_in_sec": int(interval - (now - last))}

        amount = round(self.base_amount * amount_mult, 2)
        return {
            "execute": True, "amount": amount, "interval": int(interval),
            "amount_mult": round(amount_mult, 2),
            "reason": f"DCA (F&G:{fear_greed}, Mult:{amount_mult:.1f}x)",
        }

    def record_dca(self, symbol, amount, price, qty):
        """Speichert ausgefuehrten DCA-Kauf."""
        self.last_dca_time[symbol] = time.time()
        self.total_invested += amount
        self.dca_history.append({
            "symbol": symbol, "amount": amount, "price": price,
            "qty": qty, "time": time.strftime("%Y-%m-%d %H:%M"),
        })
        if len(self.dca_history) > 500:
            self.dca_history = self.dca_history[-500:]

    def get_status(self):
        return {"total_invested": round(self.total_invested, 2),
                "dca_count": len(self.dca_history),
                "active_coins": len(self.last_dca_time),
                "base_amount": self.base_amount}
