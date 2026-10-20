"""
Trading Imperium V5 – Data Quality
Prueft Daten auf Luecken, Ausreisser und Inkonsistenzen.
Verhindert dass der Bot auf schlechten Daten handelt.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from core.logger import log


class DataQualityChecker:
    """Prueft Datenqualitaet bevor sie an die KI gehen."""

    def __init__(self):
        self.total_checks = 0
        self.total_issues = 0

    def check_ohlcv(self, df, symbol="?") -> Dict:
        """
        Prueft einen OHLCV-DataFrame auf Qualitaet.
        Returns: {"ok": bool, "score": 0-100, "issues": [...]}
        """
        self.total_checks += 1
        issues = []
        score = 100

        if df is None or len(df) == 0:
            return {"ok": False, "score": 0, "issues": ["Keine Daten"]}

        # 1. Fehlende Werte
        missing = df[["Open", "High", "Low", "Close", "Volume"]].isnull().sum().sum()
        if missing > 0:
            pct = missing / (len(df) * 5) * 100
            issues.append(f"{missing} fehlende Werte ({pct:.1f}%)")
            score -= min(pct * 2, 30)

        # 2. Zero-Volume Kerzen
        zero_vol = (df["Volume"] == 0).sum()
        if zero_vol > len(df) * 0.1:
            issues.append(f"{zero_vol} Kerzen ohne Volumen ({zero_vol/len(df)*100:.0f}%)")
            score -= 15

        # 3. OHLC-Konsistenz (High >= Low, High >= Open/Close etc.)
        invalid_hl = (df["High"] < df["Low"]).sum()
        if invalid_hl > 0:
            issues.append(f"{invalid_hl} Kerzen mit High < Low!")
            score -= 20

        invalid_ho = (df["High"] < df["Open"]).sum() + (df["High"] < df["Close"]).sum()
        if invalid_ho > 0:
            issues.append(f"{invalid_ho} Kerzen mit inkonsistentem High")
            score -= 10

        # 4. Ausreisser (Preis-Spruenge > 20% in einer Kerze)
        if len(df) > 1:
            returns = df["Close"].pct_change().dropna()
            outliers = (returns.abs() > 0.20).sum()
            if outliers > 0:
                issues.append(f"{outliers} extreme Preissprünge (>20%)")
                score -= outliers * 5

        # 5. Luecken im Zeitstempel (wenn Index DateTimeIndex)
        if hasattr(df.index, 'freq') or isinstance(df.index, pd.DatetimeIndex):
            try:
                diffs = df.index.to_series().diff().dropna()
                if len(diffs) > 0:
                    median_diff = diffs.median()
                    gaps = (diffs > median_diff * 3).sum()
                    if gaps > 0:
                        issues.append(f"{gaps} Zeitluecken erkannt")
                        score -= gaps * 3
            except Exception:
                pass

        # 6. Zu wenig Daten
        if len(df) < 50:
            issues.append(f"Nur {len(df)} Kerzen (brauche mind. 50)")
            score -= 20

        # 7. Stale Data (letzte Kerze zu alt?)
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
            try:
                last = df.index[-1]
                age_hours = (pd.Timestamp.now(tz='UTC') - last.tz_localize('UTC')).total_seconds() / 3600
                if age_hours > 24:
                    issues.append(f"Letzte Kerze {age_hours:.0f}h alt!")
                    score -= 15
            except Exception:
                pass

        score = max(0, min(100, int(score)))
        ok = score >= 60 and len(issues) < 3

        if issues:
            self.total_issues += len(issues)
            log.warn("DQ", f"{symbol}: Score {score}/100 – {', '.join(issues[:3])}")

        return {"ok": ok, "score": score, "issues": issues, "rows": len(df)}

    def check_indicator(self, series, name="?", min_val=None, max_val=None) -> Dict:
        """Prueft einen einzelnen Indikator auf Gueltigkeit."""
        issues = []

        if series is None or len(series) == 0:
            return {"ok": False, "issues": [f"{name}: keine Daten"]}

        nan_pct = series.isna().sum() / len(series) * 100
        if nan_pct > 50:
            issues.append(f"{name}: {nan_pct:.0f}% NaN")

        if min_val is not None:
            below = (series.dropna() < min_val).sum()
            if below > 0:
                issues.append(f"{name}: {below}x unter Minimum {min_val}")

        if max_val is not None:
            above = (series.dropna() > max_val).sum()
            if above > 0:
                issues.append(f"{name}: {above}x ueber Maximum {max_val}")

        return {"ok": len(issues) == 0, "issues": issues}

    def auto_fix(self, df) -> Tuple[pd.DataFrame, List[str]]:
        """Versucht Daten automatisch zu reparieren."""
        fixes = []
        df = df.copy()

        # NaN fuellen
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                na_count = df[col].isna().sum()
                if na_count > 0:
                    df[col] = df[col].ffill().bfill()
                    fixes.append(f"{col}: {na_count} NaN gefuellt (forward-fill)")

        # Volume NaN -> 0
        if "Volume" in df.columns:
            na_vol = df["Volume"].isna().sum()
            if na_vol > 0:
                df["Volume"] = df["Volume"].fillna(0)
                fixes.append(f"Volume: {na_vol} NaN -> 0")

        # High < Low reparieren
        if "High" in df.columns and "Low" in df.columns:
            invalid = df["High"] < df["Low"]
            if invalid.sum() > 0:
                df.loc[invalid, ["High", "Low"]] = df.loc[invalid, ["Low", "High"]].values
                fixes.append(f"{invalid.sum()} High/Low getauscht")

        if fixes:
            log.info("DQ", f"Auto-Fix: {', '.join(fixes)}")

        return df, fixes

    def get_status(self):
        return {"total_checks": self.total_checks, "total_issues": self.total_issues}
