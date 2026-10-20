"""
Trading Imperium V5 – Training Labels
Erzeugt Labels fuer ML-Training: War ein Trade profitabel?
"""
import pandas as pd
import numpy as np
from core.logger import log


class LabelGenerator:
    """Erzeugt Labels aus historischen Daten fuer ML-Training."""

    def __init__(self, forward_periods=5, profit_threshold=0.005):
        """
        forward_periods: Wie viele Kerzen in die Zukunft schauen
        profit_threshold: Ab wieviel % gilt es als profitabel (0.005 = 0.5%)
        """
        self.forward_periods = forward_periods
        self.profit_threshold = profit_threshold

    def generate_binary(self, df):
        """
        Label: 1 = profitabel (>threshold), 0 = nicht profitabel.
        Schaut forward_periods Kerzen in die Zukunft.
        """
        df = df.copy()
        df["future_return"] = df["Close"].shift(-self.forward_periods) / df["Close"] - 1
        df["label"] = (df["future_return"] > self.profit_threshold).astype(int)
        df["label_strength"] = df["future_return"].clip(-0.05, 0.05)  # Staerke begrenzt
        return df

    def generate_triple(self, df, loss_threshold=None):
        """
        3 Klassen: 0=Sell, 1=Hold, 2=Buy.
        Buy wenn future_return > threshold, Sell wenn < -threshold.
        """
        if loss_threshold is None:
            loss_threshold = -self.profit_threshold
        df = df.copy()
        df["future_return"] = df["Close"].shift(-self.forward_periods) / df["Close"] - 1
        df["label"] = 1  # Default: Hold
        df.loc[df["future_return"] > self.profit_threshold, "label"] = 2  # Buy
        df.loc[df["future_return"] < loss_threshold, "label"] = 0  # Sell
        return df

    def generate_optimal_entries(self, df, window=20, top_pct=0.2):
        """
        Markiert die besten Entry-Punkte in einem Rolling Window.
        Die top_pct% besten Einstiege bekommen Label 1.
        """
        df = df.copy()
        df["future_return"] = df["Close"].shift(-self.forward_periods) / df["Close"] - 1
        df["rank"] = df["future_return"].rolling(window).rank(pct=True)
        df["label"] = (df["rank"] > (1 - top_pct)).astype(int)
        return df

    def add_exit_labels(self, df, stop_loss_pct=0.04, take_profit_pct=0.03):
        """
        Fuer jeden Punkt: Was waere passiert mit SL/TP?
        Result: 'win', 'loss', 'timeout'
        """
        df = df.copy()
        results = []
        closes = df["Close"].values
        highs = df["High"].values
        lows = df["Low"].values

        for i in range(len(df) - self.forward_periods):
            entry = closes[i]
            sl = entry * (1 - stop_loss_pct)
            tp = entry * (1 + take_profit_pct)
            outcome = "timeout"
            for j in range(1, min(self.forward_periods + 1, len(df) - i)):
                if lows[i + j] <= sl:
                    outcome = "loss"; break
                if highs[i + j] >= tp:
                    outcome = "win"; break
            results.append(outcome)

        # Padding fuer die letzten Kerzen
        results.extend(["unknown"] * self.forward_periods)
        df["exit_label"] = results[:len(df)]
        df["exit_binary"] = (df["exit_label"] == "win").astype(int)
        return df

    def get_label_stats(self, df):
        """Statistiken ueber die Labels."""
        if "label" not in df.columns:
            return {"error": "Keine Labels vorhanden"}
        counts = df["label"].value_counts().to_dict()
        total = len(df.dropna(subset=["label"]))
        return {
            "total_samples": total,
            "distribution": {k: f"{v} ({v/total*100:.1f}%)" for k, v in counts.items()},
            "forward_periods": self.forward_periods,
            "threshold": self.profit_threshold,
        }
