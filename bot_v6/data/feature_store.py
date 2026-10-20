"""
Trading Imperium V5 – Feature Store
Speichert berechnete Features für ML-Training und schnellen Zugriff.
"""
import os, json, time
import pandas as pd
from typing import Dict, List, Optional
from config.settings import DATA_DIR
from core.logger import log

FEATURE_DIR = os.path.join(DATA_DIR, "features")
os.makedirs(FEATURE_DIR, exist_ok=True)

class FeatureStore:
    def __init__(self):
        self.cache = {}

    def store(self, symbol, timeframe, df):
        """Speichert Features für ein Symbol."""
        key = f"{symbol.replace('/', '_')}_{timeframe}"
        self.cache[key] = {"df": df, "time": time.time()}
        # Auch auf Disk speichern für ML-Training
        try:
            path = os.path.join(FEATURE_DIR, f"{key}.csv")
            df.tail(500).to_csv(path)
        except Exception as e:
            log.warn("FEATURES", f"Speichern {key}: {e}")

    def get(self, symbol, timeframe):
        key = f"{symbol.replace('/', '_')}_{timeframe}"
        cached = self.cache.get(key)
        if cached and (time.time() - cached["time"]) < 300:
            return cached["df"]
        # Von Disk laden
        try:
            path = os.path.join(FEATURE_DIR, f"{key}.csv")
            if os.path.exists(path):
                df = pd.read_csv(path, index_col=0, parse_dates=True)
                self.cache[key] = {"df": df, "time": time.time()}
                return df
        except: pass
        return None

    def get_training_data(self, symbols, timeframe="1h"):
        """Sammelt alle gespeicherten Features für ML-Training."""
        all_data = []
        for sym in symbols:
            df = self.get(sym, timeframe)
            if df is not None and len(df) > 50:
                df["symbol"] = sym
                all_data.append(df)
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return None

    def get_stats(self):
        files = [f for f in os.listdir(FEATURE_DIR) if f.endswith('.csv')]
        return {"cached": len(self.cache), "stored": len(files)}
