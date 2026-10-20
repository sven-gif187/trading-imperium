"""
Trading Imperium V5 – RSI Divergenz Detektor
Erkennt bullische und bearische RSI-Divergenzen automatisch.
Bullisch: Preis macht tieferes Tief, RSI macht hoeheres Tief → Kaufsignal
Bearisch: Preis macht hoeheres Hoch, RSI macht tieferes Hoch → Verkaufssignal
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from core.logger import log


class RSIDivergenceDetector:
    """Erkennt RSI-Divergenzen als starke Umkehrsignale."""

    def __init__(self, lookback=30, min_swing_pct=1.0):
        self.lookback = lookback
        self.min_swing_pct = min_swing_pct
        self.signals = []

    def detect(self, df) -> Dict:
        """
        Analysiert DataFrame auf RSI-Divergenzen.
        Returns: {"bullish": bool, "bearish": bool, "strength": float, "details": str}
        """
        if df is None or len(df) < self.lookback + 10:
            return {"bullish": False, "bearish": False, "strength": 0, "details": "Zu wenig Daten"}

        close = df["Close"].values
        rsi = df.get("RSI", pd.Series([50] * len(df))).values

        # NaN entfernen
        if np.isnan(rsi[-1]):
            return {"bullish": False, "bearish": False, "strength": 0, "details": "RSI nicht verfuegbar"}

        # Swing-Punkte finden
        lows = self._find_swing_lows(close, window=5)
        highs = self._find_swing_highs(close, window=5)

        # Nur letzte N Kerzen betrachten
        recent_lows = [(i, close[i], rsi[i]) for i in lows if i > len(close) - self.lookback]
        recent_highs = [(i, close[i], rsi[i]) for i in highs if i > len(close) - self.lookback]

        bullish = self._check_bullish(recent_lows)
        bearish = self._check_bearish(recent_highs)

        result = {
            "bullish": bullish["found"],
            "bearish": bearish["found"],
            "bullish_strength": bullish["strength"],
            "bearish_strength": bearish["strength"],
            "strength": max(bullish["strength"], bearish["strength"]),
            "details": bullish["details"] if bullish["found"] else bearish["details"] if bearish["found"] else "Keine Divergenz",
        }

        if bullish["found"]:
            log.info("RSI-DIV", f"BULLISCHE Divergenz! Staerke: {bullish['strength']:.0%} – {bullish['details']}")
            self.signals.append({"type": "bullish", "strength": bullish["strength"], "time": len(df)})
        if bearish["found"]:
            log.info("RSI-DIV", f"BEARISCHE Divergenz! Staerke: {bearish['strength']:.0%} – {bearish['details']}")
            self.signals.append({"type": "bearish", "strength": bearish["strength"], "time": len(df)})

        # Max 50 Signale behalten
        self.signals = self.signals[-50:]
        return result

    def _check_bullish(self, lows) -> Dict:
        """Bullisch: Preis tieferes Tief, RSI hoeheres Tief."""
        if len(lows) < 2:
            return {"found": False, "strength": 0, "details": ""}

        for i in range(len(lows) - 1):
            idx1, price1, rsi1 = lows[i]
            idx2, price2, rsi2 = lows[i + 1]

            # Preis macht tieferes Tief
            price_lower = price2 < price1 * (1 - self.min_swing_pct / 100)
            # RSI macht hoeheres Tief
            rsi_higher = rsi2 > rsi1 + 2

            if price_lower and rsi_higher:
                # Staerke: wie gross ist die Divergenz?
                price_diff = abs((price2 - price1) / price1) * 100
                rsi_diff = rsi2 - rsi1
                strength = min((price_diff * 0.3 + rsi_diff * 0.05), 1.0)

                return {
                    "found": True,
                    "strength": round(strength, 2),
                    "details": f"Preis: {price1:.0f}→{price2:.0f} (tiefer), RSI: {rsi1:.0f}→{rsi2:.0f} (hoeher)",
                }

        return {"found": False, "strength": 0, "details": ""}

    def _check_bearish(self, highs) -> Dict:
        """Bearisch: Preis hoeheres Hoch, RSI tieferes Hoch."""
        if len(highs) < 2:
            return {"found": False, "strength": 0, "details": ""}

        for i in range(len(highs) - 1):
            idx1, price1, rsi1 = highs[i]
            idx2, price2, rsi2 = highs[i + 1]

            price_higher = price2 > price1 * (1 + self.min_swing_pct / 100)
            rsi_lower = rsi2 < rsi1 - 2

            if price_higher and rsi_lower:
                price_diff = abs((price2 - price1) / price1) * 100
                rsi_diff = rsi1 - rsi2
                strength = min((price_diff * 0.3 + rsi_diff * 0.05), 1.0)

                return {
                    "found": True,
                    "strength": round(strength, 2),
                    "details": f"Preis: {price1:.0f}→{price2:.0f} (hoeher), RSI: {rsi1:.0f}→{rsi2:.0f} (tiefer)",
                }

        return {"found": False, "strength": 0, "details": ""}

    def _find_swing_lows(self, data, window=5):
        """Findet lokale Tiefpunkte."""
        lows = []
        for i in range(window, len(data) - window):
            if data[i] == min(data[i - window:i + window + 1]):
                lows.append(i)
        return lows

    def _find_swing_highs(self, data, window=5):
        """Findet lokale Hochpunkte."""
        highs = []
        for i in range(window, len(data) - window):
            if data[i] == max(data[i - window:i + window + 1]):
                highs.append(i)
        return highs

    def get_score(self) -> float:
        """Score fuer Strategy Brain: -1 (bearisch) bis +1 (bullisch)."""
        recent = [s for s in self.signals if s.get("time", 0) > 0][-3:]
        if not recent:
            return 0
        bull = sum(s["strength"] for s in recent if s["type"] == "bullish")
        bear = sum(s["strength"] for s in recent if s["type"] == "bearish")
        return round(min(max(bull - bear, -1), 1), 2)

    def get_status(self):
        return {
            "total_signals": len(self.signals),
            "recent_bullish": sum(1 for s in self.signals[-10:] if s["type"] == "bullish"),
            "recent_bearish": sum(1 for s in self.signals[-10:] if s["type"] == "bearish"),
            "current_score": self.get_score(),
        }
