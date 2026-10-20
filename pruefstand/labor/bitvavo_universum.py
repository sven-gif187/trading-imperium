# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""Gibt es die 12 Labor-Coins bei Bitvavo gegen USDC (sonst EUR)? Spanne je Paar aus 10 Proben (bp)."""
import json
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE", "NEAR", "UNI", "ATOM"]
ex = ccxt.bitvavo({"enableRateLimit": True, "timeout": 20000})
ex.load_markets()


def probe(sym):
    if sym not in ex.markets:
        return sym, None
    w = []
    for _ in range(10):
        try:
            ob = ex.fetch_order_book(sym, limit=5)
            b, a = ob["bids"][0][0], ob["asks"][0][0]
            w.append((a - b) / ((a + b) / 2) * 10000)
        except Exception:
            pass
        time.sleep(1.5)
    return sym, round(st.median(w), 2) if w else "keine Daten"


syms = [f"{c}/USDC" for c in COINS] + [f"{c}/EUR" for c in COINS]
with ThreadPoolExecutor(8) as p:
    erg = dict(p.map(probe, syms))
for c in COINS:
    print(f"{c:5s} USDC: {'fehlt' if erg[c + '/USDC'] is None else str(erg[c + '/USDC']) + ' bp':>12s} | "
          f"EUR: {'fehlt' if erg[c + '/EUR'] is None else str(erg[c + '/EUR']) + ' bp':>12s}")
(Path(__file__).resolve().parent / "ergebnisse" / "bitvavo_universum.json").write_text(
    json.dumps(erg, indent=1), encoding="utf-8")
