"""
Trading Imperium V5 – Training Pipeline
Automatisches Training des ML-Modells mit Walk-Forward-Validierung.
"""
import time
from typing import Dict, Optional
from core.logger import log

class TrainPipeline:
    def __init__(self, feature_store, signal_model, data_agent):
        self.feature_store = feature_store
        self.signal_model = signal_model
        self.data_agent = data_agent
        self.last_train_time = 0
        self.train_interval = 86400  # 1x pro Tag

    def should_train(self):
        return (time.time() - self.last_train_time) > self.train_interval

    def run(self, symbols, timeframe="1h", limit=500):
        """Sammelt Daten und trainiert das Modell."""
        log.info("TRAIN", "Training-Pipeline gestartet...")

        # 1. Daten sammeln
        from features.indicators import calc_all_indicators
        all_data = []
        for sym in symbols[:8]:
            try:
                snap = self.data_agent.fetch_snapshot(sym, timeframe, limit)
                if snap and hasattr(snap, '_df') and len(snap._df) > 50:
                    df = calc_all_indicators(snap._df)
                    self.feature_store.store(sym, timeframe, df)
                    all_data.append(df)
                    log.info("TRAIN", f"  {sym}: {len(df)} Kerzen")
                time.sleep(0.5)
            except Exception as e:
                log.warn("TRAIN", f"  {sym}: {str(e)[:40]}")

        if not all_data:
            log.warn("TRAIN", "Keine Daten gesammelt")
            return False

        # 2. Zusammenführen
        import pandas as pd
        combined = pd.concat(all_data, ignore_index=True)
        log.info("TRAIN", f"Gesamt: {len(combined)} Datenpunkte")

        # 3. Trainieren
        success = self.signal_model.train(combined)
        self.last_train_time = time.time()

        if success:
            log.info("TRAIN", "Training erfolgreich!")
        else:
            log.warn("TRAIN", "Training fehlgeschlagen (zu wenig Daten oder sklearn fehlt)")

        return success

    def get_status(self):
        return {"last_train": self.last_train_time,
                "model": self.signal_model.get_status(),
                "features": self.feature_store.get_stats()}
