"""
Trading Imperium V5 – Regime Model
ML-basierte Marktregime-Erkennung (Bull/Bear/Sideways/Volatile).
Ergaenzt die regelbasierte Erkennung in features/market_regime.py.
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from core.logger import log


class RegimeModel:
    """ML-Modell das Marktregime klassifiziert."""

    REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"]

    def __init__(self):
        self.model = None
        self.is_trained = False
        self.version = "rules_v1"

    def predict(self, df) -> Tuple[str, float]:
        """
        Vorhersage des Marktregimes.
        Returns: (regime, confidence)
        """
        if self.is_trained and self.model is not None:
            return self._predict_ml(df)
        return self._predict_rules(df)

    def _predict_rules(self, df) -> Tuple[str, float]:
        """Regelbasierte Regime-Erkennung (Fallback)."""
        if df is None or len(df) < 30:
            return "RANGING", 0.5

        close = df["Close"]
        returns = close.pct_change().dropna()

        # ADX fuer Trend-Staerke
        adx = df.get("ADX", pd.Series([20] * len(df))).iloc[-1]

        # Volatilitaet
        vol = returns.tail(14).std()
        avg_vol = returns.std()
        vol_ratio = vol / (avg_vol + 1e-10)

        # Trend-Richtung
        ema20 = close.rolling(20).mean().iloc[-1]
        ema50 = close.rolling(50).mean().iloc[-1]
        price = close.iloc[-1]

        # Entscheidung
        if vol_ratio > 2.0:
            return "VOLATILE", min(0.5 + vol_ratio * 0.1, 0.95)

        if adx > 30:
            if price > ema20 > ema50:
                return "TRENDING_UP", min(0.6 + (adx - 30) * 0.01, 0.95)
            elif price < ema20 < ema50:
                return "TRENDING_DOWN", min(0.6 + (adx - 30) * 0.01, 0.95)

        if adx > 20:
            trend_pct = (price - ema50) / (ema50 + 1e-10) * 100
            if trend_pct > 2:
                return "TRENDING_UP", 0.6
            elif trend_pct < -2:
                return "TRENDING_DOWN", 0.6

        return "RANGING", 0.7

    def _predict_ml(self, df) -> Tuple[str, float]:
        """ML-basierte Vorhersage."""
        try:
            features = self._extract_features(df)
            X = np.array(features).reshape(1, -1)
            pred = self.model.predict(X)[0]
            proba = self.model.predict_proba(X)[0]
            confidence = float(max(proba))
            regime = self.REGIMES[pred] if pred < len(self.REGIMES) else "RANGING"
            return regime, round(confidence, 2)
        except Exception:
            return self._predict_rules(df)

    def train(self, df, min_samples=200):
        """Trainiert das Regime-Modell."""
        if df is None or len(df) < min_samples:
            return False
        try:
            from sklearn.ensemble import RandomForestClassifier
            df = df.copy()

            # Labels generieren (basierend auf zukuenftigem Verhalten)
            returns = df["Close"].pct_change()
            vol = returns.rolling(14).std()
            avg_vol = returns.rolling(50).std()
            trend = df["Close"].rolling(20).mean() - df["Close"].rolling(50).mean()

            # Regime-Labels
            df["regime_label"] = 2  # Default: RANGING
            df.loc[(trend > 0) & (vol < avg_vol * 1.5), "regime_label"] = 0  # TRENDING_UP
            df.loc[(trend < 0) & (vol < avg_vol * 1.5), "regime_label"] = 1  # TRENDING_DOWN
            df.loc[vol > avg_vol * 2, "regime_label"] = 3  # VOLATILE
            df = df.dropna()

            features = []
            for i in range(len(df)):
                features.append(self._extract_features(df.iloc[max(0, i-30):i+1]))
            X = np.array(features)
            y = df["regime_label"].values

            split = int(len(X) * 0.8)
            self.model = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42)
            self.model.fit(X[:split], y[:split])

            acc = self.model.score(X[split:], y[split:])
            self.is_trained = True
            self.version = f"rf_regime_{int(acc * 100)}"
            log.info("REGIME-ML", f"Trainiert! Accuracy: {acc:.1%}")
            return True
        except ImportError:
            log.warn("REGIME-ML", "scikit-learn fehlt")
            return False
        except Exception as e:
            log.error("REGIME-ML", f"Training: {e}")
            return False

    def _extract_features(self, df):
        """Extrahiert Features fuer Regime-Klassifikation."""
        if df is None or len(df) < 5:
            return [0] * 8
        close = df["Close"]
        returns = close.pct_change().dropna()
        return [
            returns.mean() * 100 if len(returns) > 0 else 0,
            returns.std() * 100 if len(returns) > 0 else 0,
            float(df.get("ADX", pd.Series([20])).iloc[-1]),
            float(df.get("RSI", pd.Series([50])).iloc[-1]),
            (close.iloc[-1] / close.rolling(20).mean().iloc[-1] - 1) * 100 if len(close) > 20 else 0,
            (close.iloc[-1] / close.rolling(50).mean().iloc[-1] - 1) * 100 if len(close) > 50 else 0,
            returns.tail(5).mean() * 100 if len(returns) > 5 else 0,
            float(df.get("volume_ratio", pd.Series([1])).iloc[-1]) if "volume_ratio" in df.columns else 1,
        ]

    def get_status(self):
        return {"trained": self.is_trained, "version": self.version}
