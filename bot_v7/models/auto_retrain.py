"""
Trading Imperium V6 – Automatisches Modell-Retraining
Trainiert XGBoost-Modell woechentlich auf frischen Marktdaten.
"""
import os
import time
import threading
from typing import Dict
from config.settings import DATA_DIR
from core.logger import log


class AutoRetrainer:
    """Trainiert ML-Modelle automatisch auf neuen Daten."""

    RETRAIN_FILE = os.path.join(DATA_DIR, "last_retrain.txt")

    def __init__(self, interval_hours=168):  # 168h = 1 Woche
        self.interval_sec = interval_hours * 3600
        self.last_retrain = self._load_last()
        self.is_training = False
        self.last_result = {}

    def should_retrain(self) -> bool:
        return (time.time() - self.last_retrain) > self.interval_sec

    def retrain(self, data_agent, signal_model, xgboost_model, coins, tf="1h"):
        """Retraint das Modell auf frischen Daten."""
        if self.is_training:
            log.info("RETRAIN", "Training laeuft bereits...")
            return
        self.is_training = True
        threading.Thread(target=self._do_retrain,
                        args=(data_agent, signal_model, xgboost_model, coins, tf),
                        daemon=True).start()

    def _do_retrain(self, data_agent, signal_model, xgboost_model, coins, tf):
        import pandas as pd
        import numpy as np
        log.info("RETRAIN", f"Starte Retraining ({len(coins)} Coins, {tf})...")
        try:
            all_data = []
            for coin in coins[:5]:
                try:
                    snap = data_agent.fetch_snapshot(coin, tf, limit=500)
                    if snap and hasattr(snap, '_df') and snap._df is not None:
                        df = snap._df.copy()
                        df["coin"] = coin
                        # [GEFUNDENE-PROBLEME #18, 12.08.2026] Zeitstempel als
                        # SPALTE mitgeben. Beim Stapeln unten geht der Index
                        # verloren (ignore_index=True) - ohne diese Spalte kann
                        # train() keinen zeitlichen Holdout bilden und bricht bei
                        # mehreren Muenzen bewusst ab, statt heimlich die letzte
                        # Muenze als "Test" auszugeben.
                        try:
                            df["ts"] = df.index
                        except Exception:
                            pass
                        # [GEFUNDENE-PROBLEME #18] KEINE Labels mehr hier.
                        # Hier stand "future_ret > 0.01" (1 %), waehrend
                        # xgboost_model.train() die Spalte still mit 0,5 %
                        # ueberschrieb - die 1 % waren also immer wirkungslos,
                        # und niemand sah, welche Schwelle wirklich galt.
                        # Jetzt gibt es genau eine Definition:
                        # XGBoostSignalModel.LABEL_SCHWELLE.
                        # Ausserdem MUSS das Label je Muenze gerechnet werden -
                        # shift(-5) ueber die Stapelgrenze hinweg haette an der
                        # Naht den Kurs der naechsten Muenze vorhergesagt.
                        all_data.append(df)
                except Exception:
                    pass
                time.sleep(1)

            if not all_data:
                log.warn("RETRAIN", "Keine Daten gesammelt")
                self.is_training = False
                return

            combined = pd.concat(all_data, ignore_index=True)
            combined = combined.dropna()

            # Features
            feature_cols = [c for c in combined.columns if c in
                ["RSI", "MACD", "MACD_signal", "ADX", "Volume", "Close"]]

            # FIX: Sichere Pruefung auf Array-Groesse (kein 'if X:' das numpy crasht)
            if feature_cols is None or len(feature_cols) < 3:
                log.warn("RETRAIN", "Zu wenig Features")
                self.is_training = False
                return

            # WICHTIG: train() erwartet einen DataFrame, KEINE numpy arrays!
            # Vorher: X = combined[feature_cols].values (crasht mit "truth value ambiguous")
            # Jetzt: kompletter DataFrame uebergeben
            train_df = combined.copy()

            # Pruefen ob genug Samples vorhanden sind (sicher fuer numpy/DataFrames)
            n_samples = len(train_df) if train_df is not None else 0
            if n_samples < 50:
                log.warn("RETRAIN", f"Zu wenig Samples: {n_samples}")
                self.is_training = False
                return

            # XGBoost Training (uebergibt DataFrame, nicht numpy!)
            try:
                success = xgboost_model.train(train_df, min_samples=50)
                # train() liefert bool (True/False), nicht float!
                if success:
                    stats = xgboost_model.training_stats
                    test_acc = stats.get("test_acc", 0)
                    log.info("RETRAIN", f"XGBoost trainiert: Accuracy {test_acc:.1%}")
                    self.last_result = {"accuracy": test_acc, "samples": n_samples,
                                       "features": len(feature_cols),
                                       "time": time.strftime("%Y-%m-%d %H:%M")}
                else:
                    log.warn("RETRAIN", "XGBoost Training fehlgeschlagen (siehe XGB-Log)")
            except Exception as e:
                # Vollstaendiger Fehler statt Truncation
                error_msg = str(e)
                log.warn("RETRAIN", f"XGBoost Fehler: {error_msg[:200]}")

            self.last_retrain = time.time()
            self._save_last()
            log.info("RETRAIN", "Retraining abgeschlossen!")

        except Exception as e:
            log.error("RETRAIN", f"Fehler: {str(e)[:60]}")
        finally:
            self.is_training = False

    def _load_last(self) -> float:
        try:
            if os.path.exists(self.RETRAIN_FILE):
                return float(open(self.RETRAIN_FILE).read().strip())
        except Exception:
            pass
        return 0

    def _save_last(self):
        try:
            os.makedirs(os.path.dirname(self.RETRAIN_FILE), exist_ok=True)
            with open(self.RETRAIN_FILE, "w") as f:
                f.write(str(self.last_retrain))
        except Exception:
            pass

    def get_status(self):
        age_h = (time.time() - self.last_retrain) / 3600 if self.last_retrain else -1
        return {"is_training": self.is_training, "last_retrain_hours_ago": round(age_h, 1),
                "should_retrain": self.should_retrain(), "last_result": self.last_result}
