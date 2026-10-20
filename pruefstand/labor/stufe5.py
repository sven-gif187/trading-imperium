# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Strategie-Labor Stufe 5: Robustheit (STRATEGIE_LABOR.md 4, Stufe 5) - Advocatus-Diaboli-Pruefliste.

Je Kandidat K1/K2/K3 bei K = 0,15 % (Bitvavo) und K = 0,30 % (doppelt), zusaetzlich 1,00 %:
  - Teilzeitraeume P1 2018-03..2020-12, P2 2021, P3 2022-01..heute (2021 allein darf nichts tragen)
  - Marktlage Bulle/Seitwaerts/Baer
  - ohne den besten Coin der Strategie (groesster Rundenertrag) und ohne DOGE (2021-Ausreisser)
  - Ausfuehrung einen Tag spaeter
  - Nachbarparameter: Schwankungsziel 20 % / 30 % (K1/K2), Halteband Top 5 / Top 8 (K3)
  - Kostenbremse in der woertlichen Lesart "oder"
Deflated Sharpe ueber ALLE hier gerechneten Varianten (Mehrfachtest-Korrektur).
Ergebnis: ergebnisse/stufe5.json und stufe5.md
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import backtest as bt  # noqa: E402

ERG = HIER / "ergebnisse"
PERIODEN = {"P1 2018-2020": ("2018-03-05", "2020-12-31"), "P2 2021": ("2021-01-01", "2021-12-31"),
            "P3 2022-heute": ("2022-01-01", "2026-12-31")}


def basis(name):
    return {"K1": lambda **kw: bt.K1Trend(**kw),
            "K2": lambda **kw: bt.K1Trend(filter_btc200=True, **kw),
            "K3": lambda **kw: bt.K3Rotation(**kw)}[name]


def kurz(e, m, lage):
    g = bt.kennzahlen(e)
    out = {"jahr": g["rendite_jahr_pct"], "mdd": g["max_rueckgang_pct"], "sharpe": g["sharpe"], "calmar": g["calmar"],
           "runden_mon": g["runden_je_monat"], "kostenanteil": g["kostenanteil_brutto_pct"]}
    for p, (a, b) in PERIODEN.items():
        x = bt.kennzahlen(e, a, b)
        out[p] = {"jahr": x.get("rendite_jahr_pct"), "sharpe": x.get("sharpe"), "mdd": x.get("max_rueckgang_pct")}
    for L in ("Bulle", "Seitwaerts", "Baer"):
        x = bt.kennzahlen(e, tage_filter=lambda d, L=L: lage.get(d) == L)
        out[L] = {"jahr": x.get("rendite_jahr_pct"), "sharpe": x.get("sharpe")}
    return out


def bester_coin(e):
    s = defaultdict(float)
    for r in e.runden:
        s[r.coin] += r.fluss
    return max(s, key=s.get), {k: round(v, 0) for k, v in sorted(s.items(), key=lambda x: -x[1])[:4]}


def main():
    m = bt.Markt.laden()
    start = m.datum[200]
    lage = bt.marktlage(m)
    alle_coins = list(bt.COINS)
    out, sr_alle, r_alle = {}, {}, {}

    def lauf(label, fabrik, k, coins=None, **simkw):
        bt.COINS[:] = coins or alle_coins
        try:
            s = fabrik()
            z = bt.ziele_berechnen(s, m, start)
            e = bt.simuliere(s, m, k, start, ziele=z, **simkw)
        finally:
            bt.COINS[:] = alle_coins
        r = bt.renditen(e.equity)
        sr_alle[label] = st.mean(r) / st.stdev(r)
        r_alle[label] = r
        out[label] = kurz(e, m, lage)
        o = out[label]
        print(f"{label:52s} Jahr {o['jahr']:7.1f} %  MaxDD {o['mdd']:6.1f} %  Sharpe {o['sharpe']:5.2f} | "
              f"P1 {o['P1 2018-2020']['jahr']} P2 {o['P2 2021']['jahr']} P3 {o['P3 2022-heute']['jahr']} | "
              f"Baer {o['Baer']['jahr']}", flush=True)
        return e

    for name in ("K1", "K2", "K3"):
        f = basis(name)
        e = lauf(f"{name} Basis K0.15", f, 0.15)
        bc, top = bester_coin(e)
        out[f"{name} Basis K0.15"]["beste_coins_usd"] = top
        lauf(f"{name} Kosten doppelt K0.30", f, 0.30)
        lauf(f"{name} Kosten K1.00", f, 1.00)
        lauf(f"{name} ohne besten Coin ({bc}) K0.15", f, 0.15, coins=[c for c in alle_coins if c != bc])
        if bc != "DOGE":
            lauf(f"{name} ohne DOGE K0.15", f, 0.15, coins=[c for c in alle_coins if c != "DOGE"])
        lauf(f"{name} Ausfuehrung +1 Tag K0.15", f, 0.15, verzoegerung=1)
        lauf(f"{name} Bremse 'oder' K0.15", f, 0.15, bremse_oder=True)
        if name in ("K1", "K2"):
            for zv in (0.20, 0.30):
                lauf(f"{name} Schwankungsziel {int(zv * 100)} % K0.15", lambda zv=zv: f(ziel_vol=zv), 0.15)
        else:
            for band in (5, 8):
                lauf(f"K3 Halteband Top {band} K0.15", lambda band=band: f(band=band), 0.15)
    # Deflated Sharpe je Basisvariante gegen ALLE Varianten (Mehrfachtest)
    for name in ("K1", "K2", "K3"):
        lab = f"{name} Basis K0.15"
        out[lab]["deflated_sharpe_alle_varianten"] = round(bt.deflated_sharpe(r_alle[lab], list(sr_alle.values())), 3)
        out[lab]["varianten_gezaehlt"] = len(sr_alle)
        print(f"Deflated Sharpe {lab}: {out[lab]['deflated_sharpe_alle_varianten']} (N = {len(sr_alle)})")
    ERG.mkdir(exist_ok=True)
    (ERG / "stufe5.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gespeichert:", ERG / "stufe5.json")


if __name__ == "__main__":
    main()
