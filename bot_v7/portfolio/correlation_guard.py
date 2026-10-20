"""
Trading Imperium V5 – Correlation Guard
Verhindert zu viele korrelierte Positionen.
Wenn du schon SOL, ADA, AVAX hast (alle L1), blockt er weiteres L1-Kaufen.
"""
from typing import Dict, List, Tuple
from core.logger import log

# Sektor-Zuordnung (identisch mit exposure.py)
SECTORS = {
    "BTC": "store_of_value", "ETH": "L1", "SOL": "L1", "ADA": "L1",
    "AVAX": "L1", "DOT": "L1", "NEAR": "L1", "ATOM": "L1",
    "SUI": "L1", "APT": "L1", "LINK": "defi", "UNI": "defi",
    "OP": "L2", "ARB": "L2", "INJ": "defi", "RENDER": "ai",
    "FIL": "storage", "DOGE": "meme", "XRP": "payments", "MATIC": "L2",
}

# Korrelations-Matrix (welche Sektoren stark korrelieren)
HIGH_CORRELATION = {
    ("L1", "L1"): 0.85,
    ("L1", "L2"): 0.75,
    ("L2", "L2"): 0.80,
    ("defi", "defi"): 0.70,
    ("defi", "L1"): 0.65,
}


class CorrelationGuard:
    """Prueft ob eine neue Position zu stark mit bestehenden korreliert."""

    def __init__(self, max_correlated_positions=3, max_sector_coins=3):
        self.max_correlated = max_correlated_positions
        self.max_sector_coins = max_sector_coins

    def check(self, symbol: str, positions: Dict) -> Dict:
        """
        Prueft ob ein neuer Kauf zu viel Korrelation bringt.
        Returns: {"ok": bool, "reason": str, "correlation_score": float}
        """
        asset = symbol.split("/")[0] if "/" in symbol else symbol
        sector = SECTORS.get(asset, "other")

        # 1. Wie viele Coins aus dem gleichen Sektor sind schon da?
        same_sector = []
        for pos_sym in positions:
            pos_asset = pos_sym.split("/")[0] if "/" in pos_sym else pos_sym
            if positions[pos_sym].get("active", True):
                pos_sector = SECTORS.get(pos_asset, "other")
                if pos_sector == sector:
                    same_sector.append(pos_asset)

        if len(same_sector) >= self.max_sector_coins:
            coins_str = ", ".join(same_sector[:5])
            return {
                "ok": False,
                "reason": f"Schon {len(same_sector)} Coins im Sektor '{sector}': {coins_str}",
                "sector": sector,
                "same_sector_count": len(same_sector),
                "correlation_score": 0.9,
            }

        # 2. Korrelations-Score berechnen
        total_corr = 0.0
        corr_count = 0
        for pos_sym in positions:
            pos_asset = pos_sym.split("/")[0] if "/" in pos_sym else pos_sym
            if not positions[pos_sym].get("active", True):
                continue
            pos_sector = SECTORS.get(pos_asset, "other")
            pair = tuple(sorted([sector, pos_sector]))
            corr = HIGH_CORRELATION.get(pair, 0.2)
            total_corr += corr
            corr_count += 1

        avg_corr = total_corr / max(corr_count, 1)

        if avg_corr > 0.75 and corr_count >= 2:
            return {
                "ok": False,
                "reason": f"Zu hohe Korrelation ({avg_corr:.0%}) mit {corr_count} Positionen",
                "sector": sector,
                "correlation_score": round(avg_corr, 2),
            }

        return {
            "ok": True,
            "reason": "OK",
            "sector": sector,
            "same_sector_count": len(same_sector),
            "correlation_score": round(avg_corr, 2),
        }

    def get_portfolio_correlation(self, positions: Dict) -> Dict:
        """Berechnet die Gesamt-Korrelation des Portfolios."""
        assets = []
        for sym, pos in positions.items():
            if pos.get("active", True):
                asset = sym.split("/")[0] if "/" in sym else sym
                assets.append(asset)

        if len(assets) < 2:
            return {"avg_correlation": 0, "pairs": 0, "risk_level": "LOW"}

        total_corr = 0
        pairs = 0
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                s1 = SECTORS.get(assets[i], "other")
                s2 = SECTORS.get(assets[j], "other")
                pair = tuple(sorted([s1, s2]))
                corr = HIGH_CORRELATION.get(pair, 0.2)
                total_corr += corr
                pairs += 1

        avg = total_corr / max(pairs, 1)
        risk = "LOW" if avg < 0.4 else "MEDIUM" if avg < 0.65 else "HIGH"

        return {
            "avg_correlation": round(avg, 2),
            "pairs": pairs,
            "positions": len(assets),
            "risk_level": risk,
        }

    def get_sector_breakdown(self, positions: Dict) -> Dict:
        """Zeigt wie viele Coins pro Sektor gehalten werden."""
        sectors = {}
        for sym, pos in positions.items():
            if not pos.get("active", True):
                continue
            asset = sym.split("/")[0] if "/" in sym else sym
            sector = SECTORS.get(asset, "other")
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(asset)
        return sectors

    def get_status(self):
        return {"max_correlated": self.max_correlated, "max_sector_coins": self.max_sector_coins}
