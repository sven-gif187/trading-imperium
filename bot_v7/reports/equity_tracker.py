"""
Trading Imperium V6 – Equity Tracker
Zeichnet Vermoegensverlauf auf. Getrennt: Gesamt-Kapital + BTC-Akkumulation.
"""
import os
import json
import time
from typing import Dict, List
from config.settings import DATA_DIR
from core.logger import log

EQUITY_FILE = os.path.join(DATA_DIR, "equity_history.json")


class EquityTracker:
    """Trackt den Vermoegensverlauf ueber Zeit."""

    def __init__(self):
        self.total_equity = []    # [(timestamp, value)]
        self.btc_equity = []      # [(timestamp, btc_value_usd)]
        self.trade_equity = []    # [(timestamp, trade_pnl_cumulative)]
        self._cumulative_pnl = 0
        self._load()

    def record(self, usdc_balance, btc_value_usd, trade_pnl_session):
        """Nimmt einen Datenpunkt auf."""
        ts = time.time()
        total = usdc_balance + btc_value_usd
        self.total_equity.append((ts, round(total, 2)))
        self.btc_equity.append((ts, round(btc_value_usd, 2)))
        self.trade_equity.append((ts, round(trade_pnl_session, 2)))

        # Max 2000 Datenpunkte (ca. 1 Woche bei 5-Min Intervall)
        for lst in [self.total_equity, self.btc_equity, self.trade_equity]:
            if len(lst) > 2000:
                lst[:] = lst[-2000:]

    def get_chart_data(self, points=100) -> Dict:
        """Gibt Daten fuer Chart-Darstellung zurueck."""
        def downsample(data, n):
            if len(data) <= n:
                return data
            step = max(1, len(data) // n)
            return data[::step]

        return {
            "total": downsample(self.total_equity, points),
            "btc": downsample(self.btc_equity, points),
            "trades": downsample(self.trade_equity, points),
        }

    def get_stats(self) -> Dict:
        if not self.total_equity:
            return {"peak": 0, "current": 0, "drawdown": 0}
        values = [v for _, v in self.total_equity]
        peak = max(values)
        current = values[-1]
        drawdown = ((peak - current) / peak * 100) if peak > 0 else 0
        return {
            "peak": round(peak, 2),
            "current": round(current, 2),
            "drawdown": round(drawdown, 2),
            "data_points": len(self.total_equity),
        }

    def save(self):
        try:
            os.makedirs(os.path.dirname(EQUITY_FILE), exist_ok=True)
            data = {
                "total": self.total_equity[-500:],
                "btc": self.btc_equity[-500:],
                "trades": self.trade_equity[-500:],
            }
            with open(EQUITY_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load(self):
        try:
            if os.path.exists(EQUITY_FILE):
                with open(EQUITY_FILE, "r") as f:
                    data = json.load(f)
                self.total_equity = [tuple(x) for x in data.get("total", [])]
                self.btc_equity = [tuple(x) for x in data.get("btc", [])]
                self.trade_equity = [tuple(x) for x in data.get("trades", [])]
                if self.total_equity:
                    log.info("EQUITY", f"Historie geladen: {len(self.total_equity)} Punkte")
        except Exception:
            pass
