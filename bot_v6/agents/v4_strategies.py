"""
V4 STRATEGIES – BRIDGE TO V6
============================
Portiert die 7 profitablen V4-Strategien als V6-Modul.

Basis: Reale V4-Performance (266 Trades, +1.269,60€ Gewinn)
- Behalten: DCA_FEAR_GREED, FIBONACCI_SUPPORT, ICHIMOKU_CLOUD,
            TSI_SIGNAL, MACD_CROSS, RSI_OVERSOLD, MOMENTUM_BREAKOUT
- Entfernt: STOCHRSI_REVERSAL (-63€), MANUELL (-50€), RSI_DIVERGENCE (-27€), EMA_TREND (-19€)
- Inaktiv:  BOLLINGER_BOUNCE, MULTI_SIGNAL (in V4 nie ausgeloest)

Verwendung im V6 SignalAgent:
    from agents.v4_strategies import V4StrategyEnsemble
    ensemble = V4StrategyEnsemble()
    score, reason, strategy_id = ensemble.evaluate_buy(coin, df, price, fear_greed)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


# ==========================================================
# Strategie-Metadaten (aus V4 1:1)
# ==========================================================
V4_STRATEGIES = {
    "DCA_FEAR_GREED":     {"name": "Fear & Greed DCA",     "typ": "accumulation"},
    "FIBONACCI_SUPPORT":  {"name": "Fibonacci Support",     "typ": "hybrid"},
    "ICHIMOKU_CLOUD":     {"name": "Ichimoku Cloud",        "typ": "trend_following"},
    "EMA_TREND":          {"name": "EMA Triple Trend",      "typ": "trend_following"},
    "TSI_SIGNAL":         {"name": "TSI (True Strength)",   "typ": "momentum"},
    "MACD_CROSS":         {"name": "MACD Crossover",        "typ": "trend_following"},
    "RSI_OVERSOLD":       {"name": "RSI Oversold Bounce",   "typ": "mean_reversion"},
    "MOMENTUM_BREAKOUT":  {"name": "Momentum Breakout",     "typ": "momentum"},
}


# ==========================================================
# Helper – aus V4 portiert
# ==========================================================
def calc_fibonacci_levels(df: pd.DataFrame) -> dict:
    """Fibonacci-Retracement-Levels aus letzten 100 Kerzen."""
    if len(df) < 20:
        last = df['Close'].iloc[-1] if 'Close' in df.columns else 0
        return {'23.6': last, '38.2': last, '50.0': last, '61.8': last, '78.6': last}
    high = df['High'].tail(100).max() if 'High' in df.columns else df['Close'].tail(100).max()
    low = df['Low'].tail(100).min() if 'Low' in df.columns else df['Close'].tail(100).min()
    diff = high - low
    return {
        '23.6': high - diff * 0.236,
        '38.2': high - diff * 0.382,
        '50.0': high - diff * 0.500,
        '61.8': high - diff * 0.618,
        '78.6': high - diff * 0.786,
    }


def _safe_get(df: pd.DataFrame, col: str, default: float) -> float:
    """Sicherer DataFrame-Zugriff mit Fallback."""
    if col in df.columns and len(df) > 0:
        val = df[col].iloc[-1]
        if pd.notna(val):
            return float(val)
    return default


# ==========================================================
# V4 STRATEGIE-EVALUATION (aus V4 1:1 portiert)
# ==========================================================
class V4StrategyEnsemble:
    """
    Ensemble der 7 profitablen V4-Strategien.

    Jede Strategie liefert (signal: bool, score: 0-9, reason: str).
    Der Ensemble-Aufruf evaluate_buy() gibt das beste Signal zurueck.
    """

    def __init__(self):
        self.last_scores = {}     # strategy_id -> score (fuer Diagnose)
        self.last_reasons = {}    # strategy_id -> reason
        self.eval_count = 0

    # ------------------------------------------------------
    # MEAN REVERSION
    # ------------------------------------------------------
    def _rsi_oversold(self, df, price) -> Tuple[bool, int, str]:
        rsi = _safe_get(df, 'RSI', 50)
        adx = _safe_get(df, 'ADX', 20)
        if rsi < 30:
            return True, 9, f"RSI={rsi:.0f} EXTREM ueberverkauft!"
        elif rsi < 35:
            return True, 7, f"RSI={rsi:.0f} stark ueberverkauft"
        elif rsi < 45 and adx < 25:
            return True, 5, f"RSI={rsi:.0f} ueberverkauft (Range ADX={adx:.0f})"
        elif rsi < 48 and adx < 20:
            return True, 4, f"RSI={rsi:.0f} leicht ueberv. (ruhig ADX={adx:.0f})"
        return False, 2, f"RSI={rsi:.0f}"

    # ------------------------------------------------------
    # TREND FOLLOWING
    # ------------------------------------------------------
    def _ema_trend(self, df, price) -> Tuple[bool, int, str]:
        ema20 = _safe_get(df, 'EMA20', price)
        ema50 = _safe_get(df, 'EMA50', price)
        adx = _safe_get(df, 'ADX', 20)
        if price > ema20 > ema50 and adx > 20:
            score = 8 if adx > 30 else 6
            return True, score, f"Starker Trend: P>{ema20:.0f}>{ema50:.0f} ADX={adx:.0f}"
        elif price > ema50:
            return True, 4, f"Ueber EMA50"
        return False, 2, "Kein Aufwaertstrend"

    def _macd_cross(self, df, price) -> Tuple[bool, int, str]:
        if 'MACD' not in df.columns or len(df) < 3:
            return False, 2, "Kein MACD-Signal"
        macd_bull = df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]
        macd_prev = df['MACD'].iloc[-2] > df['MACD_signal'].iloc[-2]
        adx = _safe_get(df, 'ADX', 20)
        if macd_bull and not macd_prev:  # Frischer Crossover
            score = 9 if adx > 25 else 6
            return True, score, f"MACD Crossover! ADX={adx:.0f}"
        elif macd_bull and adx > 20:
            return True, 5, f"MACD bullisch, ADX={adx:.0f}"
        return False, 2, "Kein MACD-Signal"

    def _ichimoku_cloud(self, df, price) -> Tuple[bool, int, str]:
        if 'ICH_tenkan' not in df.columns or 'ICH_kijun' not in df.columns:
            return False, 2, "Ichimoku-Daten fehlen"
        tenkan = _safe_get(df, 'ICH_tenkan', price)
        kijun = _safe_get(df, 'ICH_kijun', price)
        span_a = _safe_get(df, 'ICH_span_a', 0)
        span_b = _safe_get(df, 'ICH_span_b', 0)
        cloud_top = max(span_a, span_b) if (span_a and span_b) else 0
        above_cloud = price > cloud_top if cloud_top else price > kijun
        tk_cross = tenkan > kijun
        if above_cloud and tk_cross:
            return True, 8, "Ueber Cloud + TK-Cross bullisch"
        elif above_cloud:
            return True, 5, "Ueber Ichimoku Cloud"
        elif tk_cross and price > kijun:
            return True, 4, "TK-Cross, Preis > Kijun"
        return False, 2, "Unter/in Ichimoku Cloud"

    # ------------------------------------------------------
    # MOMENTUM
    # ------------------------------------------------------
    def _momentum_breakout(self, df, price) -> Tuple[bool, int, str]:
        vol_high = bool(_safe_get(df, 'Vol_high', 0))
        ema20 = _safe_get(df, 'EMA20', price)
        macd_bull = False
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            macd_bull = df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]
        if vol_high and price > ema20:
            recent_high = df['High'].tail(20).max() if 'High' in df.columns else price
            if price >= recent_high * 0.998:
                return True, 9, "BREAKOUT! Volume-Spike + neues Hoch"
            elif macd_bull:
                return True, 6, "Momentum stark, Vol hoch"
        return False, 2, "Kein Breakout"

    def _tsi_signal(self, df, price) -> Tuple[bool, int, str]:
        if 'TSI' not in df.columns or 'TSI_signal' not in df.columns or len(df) < 3:
            return False, 2, "TSI-Daten fehlen"
        tsi = float(df['TSI'].iloc[-1])
        tsi_sig = float(df['TSI_signal'].iloc[-1])
        tsi_prev_bull = df['TSI'].iloc[-2] > df['TSI_signal'].iloc[-2]
        if tsi > tsi_sig and not tsi_prev_bull and tsi < 10:
            return True, 8, f"TSI Bullish Cross ({tsi:.1f})"
        elif tsi > tsi_sig and tsi > 0:
            return True, 5, f"TSI bullisch ({tsi:.1f})"
        return False, 2, "TSI neutral"

    # ------------------------------------------------------
    # HYBRID
    # ------------------------------------------------------
    def _fibonacci_support(self, df, price) -> Tuple[bool, int, str]:
        fibs = calc_fibonacci_levels(df)
        rsi = _safe_get(df, 'RSI', 50)
        macd_bull = False
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            macd_bull = df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]
        # 78.6% Support + RSI tief = stärkstes Signal
        if abs(price - fibs['78.6']) / max(price, 1e-9) < 0.005 and rsi < 40:
            return True, 9, f"Fib 78.6% Support ({fibs['78.6']:.2f}) + RSI tief"
        elif abs(price - fibs['61.8']) / max(price, 1e-9) < 0.005:
            return True, 7, f"Fib 61.8% Support ({fibs['61.8']:.2f})"
        elif abs(price - fibs['38.2']) / max(price, 1e-9) < 0.005 and macd_bull:
            return True, 5, "Fib 38.2% + MACD bullisch"
        return False, 2, "Kein Fib-Level in Reichweite"

    # ------------------------------------------------------
    # ACCUMULATION (V4 STAR – +935€ Gewinn allein!)
    # ------------------------------------------------------
    def _dca_fear_greed(self, df, price, fear_greed) -> Tuple[bool, int, str]:
        rsi = _safe_get(df, 'RSI', 50)
        fg = fear_greed
        if fg <= 15:
            return True, 9, f"EXTREME FEAR ({fg}) -> Maximaler Kauf!"
        elif fg <= 25:
            return True, 8, f"Fear ({fg}) -> Starker Kauf"
        elif fg <= 40 and rsi < 50:
            return True, 6, f"Fear ({fg}) + RSI={rsi:.0f} -> Kaufen"
        elif fg <= 50 and rsi < 45:
            return True, 4, f"Neutral ({fg}) RSI={rsi:.0f} -> DCA"
        return False, 2, f"F&G={fg} – noch kein DCA-Signal"

    # ------------------------------------------------------
    # ÖFFENTLICHE API
    # ------------------------------------------------------
    def evaluate_all(self, df: pd.DataFrame, price: float,
                     fear_greed: int = 50) -> dict:
        """
        Wertet ALLE 7 V4-Strategien aus.

        Returns: { strategy_id: (signal: bool, score: 0-9, reason: str) }
        """
        self.eval_count += 1
        results = {}
        evaluators = {
            "DCA_FEAR_GREED":    lambda: self._dca_fear_greed(df, price, fear_greed),
            "FIBONACCI_SUPPORT": lambda: self._fibonacci_support(df, price),
            "ICHIMOKU_CLOUD":    lambda: self._ichimoku_cloud(df, price),
            "EMA_TREND":         lambda: self._ema_trend(df, price),
            "TSI_SIGNAL":        lambda: self._tsi_signal(df, price),
            "MACD_CROSS":        lambda: self._macd_cross(df, price),
            "RSI_OVERSOLD":      lambda: self._rsi_oversold(df, price),
            "MOMENTUM_BREAKOUT": lambda: self._momentum_breakout(df, price),
        }
        for sid, fn in evaluators.items():
            try:
                signal, score, reason = fn()
                results[sid] = (signal, score, reason)
                self.last_scores[sid] = score
                self.last_reasons[sid] = reason
            except Exception as e:
                results[sid] = (False, 0, f"Fehler: {e}")
        return results

    def evaluate_buy(self, df: pd.DataFrame, price: float,
                     fear_greed: int = 50,
                     calibrator: Optional[object] = None) -> Tuple[float, str, str]:
        """
        Wertet alle 7 V4-Strategien aus und gibt das beste Signal zurueck.

        WICHTIG: Wenn ein Calibrator uebergeben wird, wird nach KALIBRIERTEM Score
        gerankt - so gewinnt z.B. DCA_FEAR_GREED (Gewicht 0.91) mit Score 8
        gegen RSI_OVERSOLD (Gewicht 0.43) mit Score 9.

        Returns:
            (confidence, reason, strategy_id)
            confidence: 0.0 - 1.0  (kalibrierter Score wenn Calibrator vorhanden)
            reason:     Erklaerungstext
            strategy_id: z.B. "DCA_FEAR_GREED" oder "" wenn kein Signal
        """
        results = self.evaluate_all(df, price, fear_greed)

        # [FIX 04.08.2026] Ranking wieder ueber den ROHEN Score, wie in V4
        # (trading_imperium_v4_25_ALARM.py:6014-6019). Begruendung, gemessen:
        #   * Die Gewichte kamen aus v4_data/strategy_stats.json, mtime
        #     06.05.2026 - seit 90 Tagen eingefroren und aus einem anderen
        #     System. Bei sechs von zwoelf Strategien stimmte nicht einmal
        #     das Vorzeichen (EMA_TREND +132,96$ in der Quelle gegen real
        #     -1658,57$ am 04.08.).
        #   * Vier Strategien standen auf Gewicht 0,0 und wurden per
        #     'continue' komplett uebersprungen - darunter STOCHRSI_REVERSAL,
        #     die im V4-Journal die hoechste Trefferquote hatte (WR 94 %).
        #     Die Sperre war eine Einbahnstrasse: uebersprungen -> keine
        #     Trades -> kein neues Gewicht -> dauerhaft gesperrt.
        #   * Dadurch gewann DCA_FEAR_GREED (Gewicht 0,909) praktisch jeden
        #     Argmax; alle 523 BUYs im V6-Journal trugen diese eine ID.
        # Der Calibrator bleibt geladen und liefert weiter get_status() fuer
        # das Dashboard - er entscheidet nur nicht mehr die Auswahl.
        # FOLGE, bewusst in Kauf genommen: der zurueckgegebene Score ist jetzt
        # der rohe (0..1) statt des gedaempften. In signal_agent.py:156-165
        # ergibt das haeufiger +3 oder +4 Punkte statt +2, die Kaufschwelle
        # min_score=3 wird also oefter erreicht. Das ist die V4-Semantik;
        # V4 hielt dagegen mit min_score 5 bzw. 6 (:6050-6053), V6 mit 3.
        active = []
        gesperrt = []
        for sid, (sig, score, reason) in results.items():
            if not sig:
                continue
            raw = score / 9.0
            if calibrator is not None and hasattr(calibrator, "get_weight"):
                if calibrator.get_weight(sid) == 0.0:
                    gesperrt.append(sid)      # nur noch protokolliert
            active.append((sid, raw, raw, reason))

        if not active:
            return 0.0, "Keine V4-Strategie aktiv", ""

        # Sortieren nach ROHEM Score - jede Strategie mit Signal konkurriert
        active.sort(key=lambda x: x[1], reverse=True)
        best_sid, best_raw, _best_raw2, best_reason = active[0]
        if gesperrt and best_sid in gesperrt:
            best_reason = f"[frueher gesperrt] {best_reason}"
        return best_raw, best_reason, best_sid

    def evaluate_sell(self, strategy_id: str, df: pd.DataFrame, price: float,
                      entry_price: float, highest_price: float,
                      trail_pct: float = 1.0) -> Tuple[bool, str]:
        """V4 Sell-Logik 1:1 portiert."""
        if entry_price <= 0:
            return False, ""
        rsi = _safe_get(df, 'RSI', 50)
        adx = _safe_get(df, 'ADX', 20)
        p_diff = ((price / entry_price) - 1) * 100
        macd_bull = True
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            macd_bull = df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]

        # Universal: Stop-Loss bei -4%
        if p_diff <= -4.0:
            return True, f"STOP-LOSS {p_diff:.2f}%"

        # Strategie-spezifische Exits
        if strategy_id == "RSI_OVERSOLD":
            if rsi > 70 and p_diff > 0.3:
                return True, f"RSI overbought ({rsi:.0f}), +{p_diff:.2f}%"
            if rsi > 60 and p_diff > 1.5:
                return True, f"RSI erholt ({rsi:.0f}), +{p_diff:.2f}%"
        elif strategy_id == "MACD_CROSS":
            if not macd_bull and p_diff > 0.3:
                return True, f"MACD bearish Flip +{p_diff:.2f}%"
        elif strategy_id == "ICHIMOKU_CLOUD":
            kijun = _safe_get(df, 'ICH_kijun', price)
            if price < kijun and p_diff > 0.3:
                return True, f"Unter Kijun-Sen +{p_diff:.2f}%"
        elif strategy_id == "EMA_TREND":
            ema20 = _safe_get(df, 'EMA20', price)
            if price < ema20 and p_diff > 0.3:
                return True, f"Unter EMA20, Trend gebrochen +{p_diff:.2f}%"
        elif strategy_id == "MOMENTUM_BREAKOUT":
            vol_high = bool(_safe_get(df, 'Vol_high', 0))
            if not vol_high and p_diff > 0.5:
                return True, f"Volumen sinkt +{p_diff:.2f}%"
        elif strategy_id == "TSI_SIGNAL":
            if 'TSI' in df.columns and 'TSI_signal' in df.columns:
                if df['TSI'].iloc[-1] < df['TSI_signal'].iloc[-1] and p_diff > 0.3:
                    return True, f"TSI bearish Cross +{p_diff:.2f}%"
        elif strategy_id == "DCA_FEAR_GREED":
            if rsi > 75 and p_diff > 2.0:
                return True, f"RSI extrem hoch + Gewinn +{p_diff:.2f}%"

        # Universal: Trailing Stop (ADX-adaptiv)
        if p_diff > 0.3 and highest_price > 0:
            fall = ((highest_price - price) / highest_price) * 100
            effective_trail = trail_pct * 0.7 if adx < 20 else trail_pct * 1.3 if adx > 30 else trail_pct
            if fall >= effective_trail:
                return True, f"TRAIL +{p_diff:.2f}% (Fall {fall:.1f}%)"

        return False, ""

    def get_status(self) -> dict:
        """Diagnose fuer Dashboard."""
        return {
            "active": True,
            "version": "v4_bridge_1.0",
            "strategies": list(V4_STRATEGIES.keys()),
            "eval_count": self.eval_count,
            "last_scores": dict(self.last_scores),
            "last_reasons": dict(self.last_reasons),
        }


# Convenience-Singleton
v4_ensemble = V4StrategyEnsemble()
