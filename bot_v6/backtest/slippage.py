"""
Trading Imperium V5 – Slippage Model
Simuliert realistische Slippage basierend auf Volumen und Ordergroesse.
"""
import random
import numpy as np
from typing import Dict


class SlippageModel:
    """Berechnet realistische Slippage fuer Backtests."""

    def __init__(self, base_bps=5, volume_impact=True):
        """
        base_bps: Basis-Slippage in Basispunkten (5 = 0.05%)
        volume_impact: Groessere Orders = mehr Slippage
        """
        self.base_bps = base_bps
        self.volume_impact = volume_impact
        self.total_slippage_usd = 0.0

    def calculate(self, price, amount_usd, avg_volume=0, side="buy"):
        """
        Berechnet Slippage-bereinigten Preis.
        Returns: {"price": adjusted_price, "slippage_pct": float, "slippage_usd": float}
        """
        # Basis-Slippage (random um Realismus zu erhoehen)
        base_slip = self.base_bps / 10000  # bps -> dezimal
        random_factor = random.uniform(0.3, 1.5)
        slip = base_slip * random_factor

        # Volume-Impact: Grosse Orders relativ zum Volumen = mehr Slippage
        if self.volume_impact and avg_volume > 0:
            order_ratio = amount_usd / avg_volume
            if order_ratio > 0.01:  # >1% des Volumens
                slip += order_ratio * 0.005  # Extra Slippage
            if order_ratio > 0.05:  # >5% des Volumens
                slip += order_ratio * 0.01

        # Richtung: Kauf = hoeherer Preis, Verkauf = niedrigerer Preis
        if side == "buy":
            adjusted = price * (1 + slip)
        else:
            adjusted = price * (1 - slip)

        slippage_usd = abs(adjusted - price) * (amount_usd / price)
        self.total_slippage_usd += slippage_usd

        return {
            "price": round(adjusted, 6),
            "slippage_pct": round(slip * 100, 4),
            "slippage_usd": round(slippage_usd, 4),
        }

    def get_status(self):
        return {"base_bps": self.base_bps, "volume_impact": self.volume_impact,
                "total_slippage": round(self.total_slippage_usd, 2)}
