"""
Trading Imperium V5 – Marktregime-Erkennung
Bestimmt ob der Markt trending, ranging oder volatil ist.
"""
import pandas as pd
from core.logger import log

class RegimeDetector:
    def __init__(self):
        self.current_regime = "UNKNOWN"
        self.regime_history = []

    def detect(self, df, adx=None, atr=None):
        """Erkennt das Marktregime basierend auf ADX, ATR und Preis-Struktur."""
        if df is None or len(df) < 50:
            return "UNKNOWN"

        adx_val = adx if adx is not None else df.get("ADX", pd.Series([20])).iloc[-1]
        close = df["Close"]
        returns = close.pct_change().dropna()

        # ADX-basiert
        if adx_val > 30:
            regime = "TRENDING"
        elif adx_val > 20:
            # Prüfe ob Trend oder Range
            ema20 = close.rolling(20).mean().iloc[-1]
            ema50 = close.rolling(50).mean().iloc[-1]
            if abs(ema20 - ema50) / ema50 > 0.02:
                regime = "TRENDING"
            else:
                regime = "RANGING"
        else:
            regime = "RANGING"

        # Volatilitäts-Check
        recent_vol = returns.tail(14).std()
        avg_vol = returns.std()
        if recent_vol > avg_vol * 1.8:
            regime = "VOLATILE"

        self.current_regime = regime
        self.regime_history.append(regime)
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]

        return regime

    def get_regime_stats(self):
        if not self.regime_history:
            return {}
        total = len(self.regime_history)
        return {r: round(self.regime_history.count(r) / total * 100, 1)
                for r in set(self.regime_history)}
