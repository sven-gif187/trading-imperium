# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Spannen-Stichprobe (Basispunkte) je Muenze an einer Boerse: Median und p90.
Grundlage fuer SPREAD_BP der Papier-Engine (Format wie engine.py: (median_bp, p90_bp)).

Aufruf: python spanne_stichprobe.py [boerse=bitvavo] [proben=120] [abstand_s=2.5]
Ergebnis: berichte/<datum>_spanne_<boerse>.json
"""
import json
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
boerse = sys.argv[1] if len(sys.argv) > 1 else "bitvavo"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
abstand = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
SYMS = ("BTC/USDC", "ETH/USDC", "SOL/USDC")


def stichprobe(sym):
    ex = getattr(ccxt, boerse)({"enableRateLimit": True, "timeout": 20000})
    werte, fehler = [], 0
    for _ in range(n):
        try:
            ob = ex.fetch_order_book(sym, limit=5)
            b, a = ob["bids"][0][0], ob["asks"][0][0]
            werte.append((a - b) / ((a + b) / 2) * 10000)
        except Exception:
            fehler += 1
        time.sleep(abstand)
    werte.sort()
    p90 = werte[int(0.9 * (len(werte) - 1))] if werte else None
    return sym, {"proben": len(werte), "fehler": fehler, "median_bp": round(st.median(werte), 3) if werte else None,
                 "p90_bp": round(p90, 3) if p90 is not None else None,
                 "max_bp": round(max(werte), 3) if werte else None}


start = datetime.now(timezone.utc)
with ThreadPoolExecutor(len(SYMS)) as p:
    erg = dict(p.map(stichprobe, SYMS))
for s, e in erg.items():
    print(f"{boerse} {s}: Median {e['median_bp']} bp | p90 {e['p90_bp']} bp | max {e['max_bp']} bp | {e['proben']} Proben")
ziel = Path(__file__).resolve().parent.parent / "berichte" / f"{start:%Y-%m-%d}_spanne_{boerse}.json"
ziel.write_text(json.dumps({"boerse": boerse, "start_utc": start.isoformat(),
                            "ende_utc": datetime.now(timezone.utc).isoformat(), "abstand_s": abstand,
                            "ergebnis": erg}, indent=1, ensure_ascii=False), encoding="utf-8")
print("gespeichert:", ziel)
