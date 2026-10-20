"""
Trading Imperium V5 – Exposure Manager
Ueberwacht Exposure pro Coin und Sektor. Verhindert Uebergewichtung.
"""
from typing import Dict
from core.logger import log

SECTORS = {
    "BTC": "store_of_value", "ETH": "L1", "SOL": "L1", "ADA": "L1",
    "AVAX": "L1", "DOT": "L1", "NEAR": "L1", "ATOM": "L1",
    "SUI": "L1", "APT": "L1", "LINK": "defi", "UNI": "defi",
    "OP": "L2", "ARB": "L2", "INJ": "defi", "RENDER": "ai",
    "FIL": "storage", "DOGE": "meme", "XRP": "payments", "MATIC": "L2",
}

class ExposureManager:
    """Berechnet und prueft Exposure-Limits."""

    def __init__(self, max_coin_pct=20.0, max_sector_pct=40.0):
        self.max_coin_pct = max_coin_pct
        self.max_sector_pct = max_sector_pct

    def check_coin_exposure(self, symbol, amount_usd, total_equity, positions):
        """Prueft ob ein Trade die Coin-Exposure ueberschreiten wuerde."""
        asset = symbol.split("/")[0] if "/" in symbol else symbol
        current = sum(p.get("value", 0) for k, p in positions.items()
                      if k.split("/")[0] == asset)
        new_total = current + amount_usd
        # [FAIL-SAFE 05.08.2026] Ohne belastbare Equity KEINE Freigabe.
        # Vorher: pct = ... if total_equity > 0 else 0. Bei nicht
        # ermittelbarer Equity wurde pct=0 gesetzt, die Grenze konnte nie
        # ueberschritten werden und die Funktion gab ok=True zurueck - ein
        # Risiko-Gate, das bei fehlenden Daten JEDEN Kauf durchwinkt.
        # Ein Gate muss selbst fail-safe sein und darf sich nicht darauf
        # verlassen, dass jeder Aufrufer vorher prueft.
        if not total_equity or total_equity <= 0:
            return {"ok": False,
                    "reason": "Exposure nicht pruefbar: Equity unbekannt "
                              "oder <= 0",
                    "adjusted_amount": 0}
        pct = new_total / total_equity * 100

        if pct > self.max_coin_pct:
            allowed = max(0, (total_equity * self.max_coin_pct / 100) - current)
            return {"ok": False, "reason": f"{asset} wuerde {pct:.0f}% sein (max {self.max_coin_pct}%)",
                    "adjusted_amount": allowed}
        return {"ok": True, "pct": round(pct, 1), "adjusted_amount": amount_usd}

    def check_sector_exposure(self, symbol, amount_usd, total_equity, positions):
        """Prueft ob ein Trade die Sektor-Exposure ueberschreiten wuerde."""
        asset = symbol.split("/")[0] if "/" in symbol else symbol
        sector = SECTORS.get(asset, "other")
        sector_value = sum(p.get("value", 0) for k, p in positions.items()
                          if SECTORS.get(k.split("/")[0], "other") == sector)
        new_total = sector_value + amount_usd
        # [FAIL-SAFE 05.08.2026] Gleiche Begruendung wie in
        # check_coin_exposure: ohne Equity keine Freigabe.
        if not total_equity or total_equity <= 0:
            return {"ok": False, "sector": sector,
                    "reason": "Sektor-Exposure nicht pruefbar: Equity "
                              "unbekannt oder <= 0"}
        pct = new_total / total_equity * 100

        if pct > self.max_sector_pct:
            return {"ok": False, "reason": f"Sektor '{sector}' wuerde {pct:.0f}% sein (max {self.max_sector_pct}%)"}
        return {"ok": True, "sector": sector, "pct": round(pct, 1)}

    def get_exposure_map(self, positions, total_equity):
        """Komplette Exposure-Uebersicht."""
        coins = {}
        sectors = {}
        for sym, pos in positions.items():
            asset = sym.split("/")[0] if "/" in sym else sym
            val = pos.get("value", 0)
            pct = (val / total_equity * 100) if total_equity > 0 else 0
            coins[asset] = round(pct, 1)
            sector = SECTORS.get(asset, "other")
            sectors[sector] = sectors.get(sector, 0) + pct
        return {"coins": coins, "sectors": {k: round(v, 1) for k, v in sectors.items()}}
