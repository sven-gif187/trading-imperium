"""
Trading Imperium V6 – VWAP + Volume Profile
Berechnet VWAP und identifiziert High-Volume-Nodes als Support/Resistance.
"""
import numpy as np
import pandas as pd
from typing import Dict
from core.logger import log


class VWAPAgent:
    """VWAP + Volume Profile fuer Confirmation-Signale."""

    def __init__(self):
        self.last_vwap = {}
        self.last_bias = {}

    def calculate(self, df, symbol="?") -> Dict:
        """Berechnet VWAP und Volume Profile."""
        if df is None or len(df) < 10:
            return {"vwap": 0, "bias": "NEUTRAL", "strength": 0}

        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        volume = df["Volume"].values

        # VWAP = Summe(Preis * Volume) / Summe(Volume)
        typical_price = (high + low + close) / 3
        cum_vol = np.cumsum(volume)
        cum_tp_vol = np.cumsum(typical_price * volume)
        vwap = cum_tp_vol / (cum_vol + 1e-10)
        current_vwap = vwap[-1]
        current_price = close[-1]

        # Bias: Preis ueber VWAP = bullisch
        pct_diff = ((current_price - current_vwap) / current_vwap) * 100 if current_vwap > 0 else 0

        if pct_diff > 0.5:
            bias = "BULLISH"
            strength = min(pct_diff / 3, 1.0)
        elif pct_diff < -0.5:
            bias = "BEARISH"
            strength = min(abs(pct_diff) / 3, 1.0)
        else:
            bias = "NEUTRAL"
            strength = 0

        # Volume Profile: High-Volume-Nodes
        price_bins = np.linspace(close.min(), close.max(), 20)
        vol_profile = np.zeros(len(price_bins) - 1)
        for i in range(len(close)):
            bin_idx = np.searchsorted(price_bins, close[i]) - 1
            bin_idx = max(0, min(bin_idx, len(vol_profile) - 1))
            vol_profile[bin_idx] += volume[i]

        # Point of Control (hoechstes Volumen)
        poc_idx = np.argmax(vol_profile)
        poc_price = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2

        self.last_vwap[symbol] = current_vwap
        self.last_bias[symbol] = bias

        return {
            "vwap": round(current_vwap, 2),
            "price": round(current_price, 2),
            "bias": bias,
            "strength": round(strength, 2),
            "pct_diff": round(pct_diff, 2),
            "poc": round(poc_price, 2),
        }

    def get_score(self, symbol="?") -> float:
        """Score fuer Strategy Brain: -0.5 bis +0.5."""
        bias = self.last_bias.get(symbol, "NEUTRAL")
        if bias == "BULLISH": return 0.3
        elif bias == "BEARISH": return -0.3
        return 0

    def get_status(self):
        return {"symbols": len(self.last_vwap)}
