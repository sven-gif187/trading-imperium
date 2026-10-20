"""
Trading Imperium V5 – Multi-Timeframe Signal Aggregation
Kombiniert Signale aus 5m, 15m, 1h, 4h zu einem gewichteten Gesamtsignal.
Alle Timeframes muessen uebereinstimmen fuer starke Signale (Confluence).
"""
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Tuple
from core.logger import log


TIMEFRAMES = {
    "5m":  {"weight": 0.15, "desc": "Kurzfristig"},
    "15m": {"weight": 0.25, "desc": "Trading"},
    "1h":  {"weight": 0.35, "desc": "Mittelfristig"},
    "4h":  {"weight": 0.25, "desc": "Trend"},
}


class MultiTimeframeAggregator:
    """Kombiniert Signale aus mehreren Timeframes."""

    def __init__(self, client=None):
        self.client = client
        self.last_signals = {}

    def set_client(self, client):
        self.client = client

    def analyze(self, symbol) -> Dict:
        """
        Analysiert einen Coin ueber alle Timeframes.
        Returns: {"score": -1 bis +1, "confluence": 0-100%, "signals": {...}}
        """
        if not self.client:
            return {"score": 0, "confluence": 0, "error": "Kein Client"}

        signals = {}
        for tf, cfg in TIMEFRAMES.items():
            try:
                bars = self.client.fetch_ohlcv(symbol, tf, limit=60)
                if not bars or len(bars) < 30:
                    continue
                df = pd.DataFrame(bars, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
                sig = self._analyze_tf(df, tf)
                signals[tf] = sig
            except Exception as e:
                log.warn("MTF", f"{symbol} {tf}: {str(e)[:30]}")

        if not signals:
            return {"score": 0, "confluence": 0, "signals": {}}

        # Gewichteter Score
        total_weight = 0
        weighted_score = 0
        for tf, sig in signals.items():
            w = TIMEFRAMES[tf]["weight"]
            weighted_score += sig["score"] * w
            total_weight += w

        final_score = weighted_score / total_weight if total_weight > 0 else 0

        # Confluence: Wie viele TFs stimmen ueberein?
        directions = [1 if s["score"] > 0.1 else -1 if s["score"] < -0.1 else 0 for s in signals.values()]
        if directions:
            bullish = sum(1 for d in directions if d > 0)
            bearish = sum(1 for d in directions if d < 0)
            confluence = max(bullish, bearish) / len(directions) * 100
        else:
            confluence = 0

        result = {
            "score": round(final_score, 3),
            "confluence": round(confluence, 0),
            "direction": "BULLISH" if final_score > 0.1 else "BEARISH" if final_score < -0.1 else "NEUTRAL",
            "signals": signals,
            "timeframes_analyzed": len(signals),
        }

        if confluence >= 75:
            log.info("MTF", f"{symbol}: {result['direction']} (Confluence {confluence:.0f}%, Score {final_score:+.3f})")

        self.last_signals[symbol] = result
        return result

    def _analyze_tf(self, df, tf) -> Dict:
        """Analysiert einen einzelnen Timeframe."""
        close = df["Close"]
        rsi = ta.rsi(close, length=14)
        ema20 = ta.ema(close, length=20)
        ema50 = ta.ema(close, length=50)
        macd_df = ta.macd(close)

        last_close = close.iloc[-1]
        last_rsi = rsi.iloc[-1] if rsi is not None and len(rsi) > 0 else 50
        last_ema20 = ema20.iloc[-1] if ema20 is not None and len(ema20) > 0 else last_close
        last_ema50 = ema50.iloc[-1] if ema50 is not None and len(ema50) > 0 else last_close

        score = 0
        reasons = []

        # RSI
        if last_rsi < 30:
            score += 0.3; reasons.append(f"RSI oversold ({last_rsi:.0f})")
        elif last_rsi < 40:
            score += 0.1
        elif last_rsi > 70:
            score -= 0.3; reasons.append(f"RSI overbought ({last_rsi:.0f})")
        elif last_rsi > 60:
            score -= 0.1

        # EMA Trend
        if last_close > last_ema20 > last_ema50:
            score += 0.2; reasons.append("Uptrend")
        elif last_close < last_ema20 < last_ema50:
            score -= 0.2; reasons.append("Downtrend")

        # MACD
        if macd_df is not None and len(macd_df) > 0:
            macd_val = macd_df.iloc[-1, 0]
            macd_sig = macd_df.iloc[-1, 2]
            if macd_val > macd_sig:
                score += 0.15
            else:
                score -= 0.15

        # Momentum (5-Kerzen Veraenderung)
        momentum = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) > 5 else 0
        if momentum > 0.01:
            score += 0.1
        elif momentum < -0.01:
            score -= 0.1

        return {"score": round(max(-1, min(1, score)), 3), "rsi": round(last_rsi, 1),
                "trend": "UP" if last_close > last_ema20 else "DOWN",
                "reasons": reasons}

    def get_status(self):
        return {"symbols_analyzed": len(self.last_signals),
                "timeframes": list(TIMEFRAMES.keys())}
