# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Stufe 5c: Strategien auf dem bei Bitvavo gegen USDC handelbaren Universum
(BTC, ETH, SOL, XRP, ADA, DOGE - geprueft 14.10.2026, bitvavo_universum.py).
Kosten 0,15 % (BTC/ETH/SOL-Spannen) und 0,30 % (ADA/DOGE-Spannen 12-19 bp beruecksichtigt).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import backtest as bt  # noqa: E402
from stufe5 import PERIODEN  # noqa: E402

UNI6 = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"]
FABRIK = {"M1 BTC halten": bt.M1BTCHalten, "M2 Korb 6 gleich": bt.M2Korb, "M3 BTC-200": bt.M3BTC200,
          "K1 Trend": bt.K1Trend, "K2 Trend+Filter": lambda: bt.K1Trend(filter_btc200=True),
          "K3 Rotation Top 2/Band 4": lambda: bt.K3Rotation(top=2, band=4)}

m = bt.Markt.laden()
start = m.datum[200]
alle = list(bt.COINS)
out = {}
for name, f in FABRIK.items():
    bt.COINS[:] = UNI6
    try:
        s = f()
        z = bt.ziele_berechnen(s, m, start)
        for k in (0.15, 0.30):
            e = bt.simuliere(s, m, k, start, ziele=z)
            g = bt.kennzahlen(e)
            zeile = {"jahr": g["rendite_jahr_pct"], "mdd": g["max_rueckgang_pct"], "sharpe": g["sharpe"],
                     "runden_mon": g["runden_je_monat"], "fenster": bt.kennzahlen(e, "2026-08-13", "2026-10-13").get("rendite_gesamt_pct")}
            for p, (a, b) in PERIODEN.items():
                x = bt.kennzahlen(e, a, b)
                zeile[p] = (x.get("rendite_jahr_pct"), x.get("sharpe"))
            out[f"{name} | K{k}"] = zeile
            print(f"{name:26s} K{k:4.2f} Jahr {zeile['jahr']:7.1f} % MaxDD {zeile['mdd']:6.1f} % Sharpe {zeile['sharpe']:5.2f} "
                  f"Runden/Mon {zeile['runden_mon']:4.1f} | P1 {zeile['P1 2018-2020']} | P2 {zeile['P2 2021']} | "
                  f"P3 {zeile['P3 2022-heute']} | 13.08.-13.10.: {zeile['fenster']} %", flush=True)
    finally:
        bt.COINS[:] = alle
(HIER / "ergebnisse" / "stufe5c_bitvavo6.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
