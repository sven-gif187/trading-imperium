"""
Trading Imperium V5 – Portfolio Features
Berechnet Portfolio-Kontext als Features fuer ML-Modelle.
"""
import time
from typing import Dict, List
from core.logger import log


class PortfolioFeatureCalculator:
    """Wandelt aktuellen Portfolio-Zustand in ML-Features um."""

    def calculate(self, balance, positions, prices, cycle_phase="",
                  fear_greed=50, daily_pnl=0) -> Dict:
        """
        Berechnet Portfolio-Features die das ML-Modell als Input bekommt.
        Returns: Dict mit Feature-Namen und Werten.
        """
        usdc = balance.get("total", {}).get("USDC", 0) + balance.get("total", {}).get("USDT", 0)
        btc = balance.get("total", {}).get("BTC", 0)

        # Investiertes Kapital
        invested = 0
        position_count = 0
        largest_position_pct = 0
        sector_counts = {}

        from portfolio.correlation_guard import SECTORS

        for sym, pos in positions.items():
            if not pos.get("active", True):
                continue
            val = pos.get("value", 0)
            invested += val
            position_count += 1
            asset = sym.split("/")[0] if "/" in sym else sym
            sector = SECTORS.get(asset, "other")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        total_equity = usdc + invested
        cash_pct = (usdc / total_equity * 100) if total_equity > 0 else 100
        invested_pct = 100 - cash_pct

        # Diversifikation (Shannon Entropy)
        diversification = 0
        if position_count > 0 and total_equity > 0:
            import math
            for sym, pos in positions.items():
                if pos.get("active", True) and pos.get("value", 0) > 0:
                    w = pos["value"] / total_equity
                    if w > 0:
                        diversification -= w * math.log(w + 1e-10)

        # Zyklusphase als numerischer Wert
        cycle_map = {
            "EUPHORIA": 6, "DISTRIBUTION": 5, "EARLY_BEAR": 4,
            "MID_BEAR": 3, "DEEP_BEAR": 2, "CAPITULATION": 1,
            "ACCUMULATION": 0, "UNKNOWN": 3,
        }
        cycle_num = cycle_map.get(cycle_phase, 3)

        features = {
            # Balance Features
            "pf_cash_pct": round(cash_pct, 1),
            "pf_invested_pct": round(invested_pct, 1),
            "pf_total_equity": round(total_equity, 2),
            "pf_position_count": position_count,
            "pf_diversification": round(diversification, 3),
            "pf_sector_count": len(sector_counts),

            # Markt-Kontext
            "pf_fear_greed": fear_greed,
            "pf_cycle_phase": cycle_num,
            "pf_daily_pnl": round(daily_pnl, 2),
            "pf_daily_pnl_pct": round((daily_pnl / total_equity * 100) if total_equity > 0 else 0, 2),

            # BTC-Exposure
            "pf_btc_value": round(btc * prices.get("BTC/USDC", prices.get("BTC/USDT", 0)), 2),
            "pf_btc_pct": round((btc * prices.get("BTC/USDC", prices.get("BTC/USDT", 0)) / total_equity * 100) if total_equity > 0 else 0, 1),
        }

        return features

    def feature_names(self) -> List[str]:
        """Liste aller Feature-Namen (fuer ML-Modell Kompatibilitaet)."""
        return [
            "pf_cash_pct", "pf_invested_pct", "pf_total_equity",
            "pf_position_count", "pf_diversification", "pf_sector_count",
            "pf_fear_greed", "pf_cycle_phase", "pf_daily_pnl", "pf_daily_pnl_pct",
            "pf_btc_value", "pf_btc_pct",
        ]
