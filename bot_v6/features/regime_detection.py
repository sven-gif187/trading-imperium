"""
Trading Imperium V5 – Erweiterte Regime Detection
Automatische Markterkennung basierend auf mehreren Indikatoren gleichzeitig.
4 Regimes: TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Tuple
from core.logger import log


class RegimeDetector:
    """Erkennt Marktregime aus mehreren Indikatoren."""

    REGIMES = {
        "TRENDING_UP": {"color": "#00ff88", "desc": "Starker Aufwaertstrend"},
        "TRENDING_DOWN": {"color": "#ff4655", "desc": "Starker Abwaertstrend"},
        "RANGING": {"color": "#f1c40f", "desc": "Seitwaertsmarkt"},
        "VOLATILE": {"color": "#e056fd", "desc": "Hohe Volatilitaet"},
    }

    def __init__(self):
        self.current_regime = "RANGING"
        self.confidence = 0.5
        self.history = []

    def detect(self, df) -> Tuple[str, float]:
        """
        Erkennt das aktuelle Marktregime.
        Returns: (regime, confidence)
        """
        if df is None or len(df) < 50:
            return "RANGING", 0.5

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # 1. ADX (Trendstaerke)
        try:
            adx_df = ta.adx(high, low, close, length=14)
            adx = adx_df.iloc[-1, 0] if adx_df is not None else 20
            plus_di = adx_df.iloc[-1, 1] if adx_df is not None else 0
            minus_di = adx_df.iloc[-1, 2] if adx_df is not None else 0
        except Exception:
            adx, plus_di, minus_di = 20, 0, 0

        # 2. Volatilitaet (ATR / Preis)
        try:
            atr = ta.atr(high, low, close, length=14)
            vol_ratio = (atr.iloc[-1] / close.iloc[-1]) if atr is not None and close.iloc[-1] > 0 else 0
            avg_vol = atr.mean() / close.mean() if close.mean() > 0 else 0
            vol_spike = vol_ratio / (avg_vol + 1e-10)
        except Exception:
            vol_ratio, vol_spike = 0, 1

        # 3. EMA Ausrichtung
        try:
            ema20 = ta.ema(close, length=20).iloc[-1]
            ema50 = ta.ema(close, length=50).iloc[-1]
            price = close.iloc[-1]
            ema_aligned_up = price > ema20 > ema50
            ema_aligned_down = price < ema20 < ema50
        except Exception:
            ema_aligned_up, ema_aligned_down = False, False

        # 4. Bollinger Band Breite
        try:
            bb = ta.bbands(close, length=20, std=2)
            if bb is not None:
                bb_width = (bb.iloc[-1, 0] - bb.iloc[-1, 2]) / close.iloc[-1] * 100
            else:
                bb_width = 2
        except Exception:
            bb_width = 2

        # 5. Returns Distribution
        returns = close.pct_change().dropna().tail(20)
        returns_std = returns.std() * 100 if len(returns) > 5 else 1

        # === REGIME BESTIMMUNG ===
        scores = {"TRENDING_UP": 0, "TRENDING_DOWN": 0, "RANGING": 0, "VOLATILE": 0}

        # Hohe Volatilitaet?
        if vol_spike > 2.0 or returns_std > 3:
            scores["VOLATILE"] += 3
        if bb_width > 5:
            scores["VOLATILE"] += 1

        # Starker Trend?
        if adx > 30:
            if plus_di > minus_di and ema_aligned_up:
                scores["TRENDING_UP"] += 3
            elif minus_di > plus_di and ema_aligned_down:
                scores["TRENDING_DOWN"] += 3
        elif adx > 20:
            if ema_aligned_up:
                scores["TRENDING_UP"] += 1
            elif ema_aligned_down:
                scores["TRENDING_DOWN"] += 1

        # Seitwaerts?
        if adx < 20:
            scores["RANGING"] += 2
        if bb_width < 2:
            scores["RANGING"] += 1

        # Bestes Regime waehlen
        best = max(scores, key=scores.get)
        total = sum(scores.values()) or 1
        confidence = scores[best] / total

        self.current_regime = best
        self.confidence = round(confidence, 2)
        self.history.append({"regime": best, "confidence": confidence})
        if len(self.history) > 100:
            self.history = self.history[-100:]

        return best, round(confidence, 2)

    def get_regime_history(self, n=10) -> list:
        return self.history[-n:]

    def get_status(self):
        return {"regime": self.current_regime, "confidence": self.confidence,
                "history_len": len(self.history)}
