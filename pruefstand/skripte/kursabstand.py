# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Kursabstand Zielboerse gegen Kursquelle Binance (gleichzeitig abgefragt) und Ordergrenzen.

Der Bot entscheidet auf Binance-Kursen. Handelt er woanders, zaehlt der Abstand der
Mittelkurse (Basis) als zusaetzliche Unschaerfe. Je Muenze 5 Proben im Abstand von 3 s.
Aufruf: python kursabstand.py [ziel=bitvavo]
"""
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ziel = sys.argv[1] if len(sys.argv) > 1 else "bitvavo"
opt = {"enableRateLimit": True, "timeout": 30000}
q, z = ccxt.binance(opt), getattr(ccxt, ziel)(opt)
with ThreadPoolExecutor(2) as p:
    list(p.map(lambda e: e.load_markets(), (q, z)))


def mitte(ex, sym):
    ob = ex.fetch_order_book(sym, limit=5)
    return (ob["bids"][0][0] + ob["asks"][0][0]) / 2


for sym in ("BTC/USDC", "ETH/USDC", "SOL/USDC"):
    m = z.markets.get(sym, {})
    lim = m.get("limits", {})
    abst = []
    for _ in range(5):
        with ThreadPoolExecutor(2) as p:
            a, b = p.map(lambda e: mitte(e, sym), (q, z))
        abst.append((b / a - 1) * 100)
        time.sleep(3)
    print(f"{sym}: {ziel} gegen Binance Median {st.median(abst):+.4f} % (Spanne {min(abst):+.4f} .. {max(abst):+.4f}) | "
          f"min. Menge {lim.get('amount', {}).get('min')} | min. Wert {lim.get('cost', {}).get('min')} USDC")
