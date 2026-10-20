"""
Trading Imperium V5 – ML Signal Model
Trainiert ein Modell das Entry-Qualität bewertet.
Nutzt die Features aus dem Feature Store.
"""
import os, json, time
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from config.settings import DATA_DIR
from core.logger import log

MODEL_DIR = os.path.join(DATA_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

class SignalModel:
    """ML-basiertes Signal-Modell. Startet mit Regeln, lernt über Zeit."""

    FEATURES = [
        "RSI", "ADX", "MACD", "MACD_hist", "ATR",
        "volume_ratio", "close_to_ema20", "volatility", "high_low_range",
    ]

    def __init__(self):
        self.model = None
        self.version = "rules_v1"
        self.is_trained = False
        self.training_history = []

    def predict(self, row) -> Tuple[float, str]:
        """
        Gibt (score, reason) zurück.
        Score: 0.0-1.0 (0=nicht kaufen, 1=starkes Signal)
        """
        if self.is_trained and self.model is not None:
            return self._predict_ml(row)
        return self._predict_rules(row)

    def _predict_rules(self, row) -> Tuple[float, str]:
        """Regelbasierte Vorhersage (Fallback wenn kein ML-Modell)."""
        score = 0
        reasons = []
        rsi = row.get("RSI", 50)
        adx = row.get("ADX", 20)
        macd = row.get("MACD", 0)
        macd_sig = row.get("MACD_signal", 0)
        vol_ratio = row.get("volume_ratio", 1)

        if rsi < 35: score += 0.2; reasons.append(f"RSI niedrig ({rsi:.0f})")
        elif rsi < 45: score += 0.1; reasons.append(f"RSI ok ({rsi:.0f})")
        if macd > macd_sig and macd < 0: score += 0.2; reasons.append("MACD cross")
        if adx > 25: score += 0.15; reasons.append(f"Trend stark ({adx:.0f})")
        if vol_ratio > 1.5: score += 0.15; reasons.append(f"Volume hoch ({vol_ratio:.1f}x)")

        bbl = row.get("BBL_20_2.0", None)
        price = row.get("Close", 0)
        if bbl and price < bbl and rsi < 40:
            score += 0.2; reasons.append("Unter Bollinger")

        return min(score, 1.0), " + ".join(reasons) if reasons else "Kein Signal"

    def _predict_ml(self, row) -> Tuple[float, str]:
        """ML-basierte Vorhersage."""
        try:
            features = [row.get(f, 0) for f in self.FEATURES]
            features = [0 if pd.isna(v) else v for v in features]
            X = np.array(features).reshape(1, -1)
            score = float(self.model.predict_proba(X)[0][1])
            return score, f"ML Score: {score:.2f} (v{self.version})"
        except Exception as e:
            log.warn("ML", f"Predict fehlgeschlagen: {e}")
            return self._predict_rules(row)

    def train(self, df, min_samples=100):
        """Trainiert das Modell auf historischen Daten."""
        if df is None or len(df) < min_samples:
            log.warn("ML", f"Zu wenig Daten ({len(df) if df is not None else 0}/{min_samples})")
            return False

        try:
            from sklearn.ensemble import GradientBoostingClassifier
            # Labels erstellen: War der nächste Trade profitabel?
            df = df.copy()
            df["future_return"] = df["Close"].shift(-5) / df["Close"] - 1
            df["label"] = (df["future_return"] > 0.005).astype(int)  # >0.5% = gut
            df = df.dropna()

            # Features extrahieren
            feature_cols = [f for f in self.FEATURES if f in df.columns]
            X = df[feature_cols].fillna(0).values
            y = df["label"].values

            if len(X) < min_samples:
                return False

            # Train/Test Split
            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            # Trainieren
            self.model = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
            self.model.fit(X_train, y_train)

            # Evaluieren
            train_acc = self.model.score(X_train, y_train)
            test_acc = self.model.score(X_test, y_test)

            self.is_trained = True
            self.version = f"gb_v{int(time.time()) % 10000}"

            self.training_history.append({
                "version": self.version, "samples": len(X),
                "train_acc": round(train_acc, 3), "test_acc": round(test_acc, 3),
                "time": time.strftime("%Y-%m-%d %H:%M"),
            })

            log.info("ML", f"Modell trainiert! Train: {train_acc:.1%} Test: {test_acc:.1%} ({len(X)} Samples)")
            self._save()
            return True
        except ImportError:
            log.warn("ML", "scikit-learn nicht installiert: pip install scikit-learn")
            return False
        except Exception as e:
            log.error("ML", f"Training fehlgeschlagen: {e}")
            return False

    def _save(self):
        try:
            import pickle
            path = os.path.join(MODEL_DIR, f"signal_model_{self.version}.pkl")
            with open(path, "wb") as f:
                pickle.dump(self.model, f)
            # Meta speichern
            meta = os.path.join(MODEL_DIR, "model_meta.json")
            with open(meta, "w") as f:
                json.dump({"version": self.version, "is_trained": self.is_trained,
                           "history": self.training_history[-10:]}, f, indent=2)
        except Exception as e:
            log.warn("ML", f"Model save: {e}")

    def get_status(self):
        return {"version": self.version, "trained": self.is_trained,
                "history": self.training_history[-3:]}
