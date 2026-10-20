# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 6 · Halteband (Hysterese) gegen Hin-und-her-Handel.

(a) Rueckkauf derselben Muenze nach einem Verkauf (E7, v6): Abstand, Preis gegen Verkaufskurs.
    Hin-und-her-Kosten einer Runde "verkauft bei Ps, zurueckgekauft bei Pb" gegen "durchgehalten":
        kosten_pct = (Pb/Ps - 1) * 100 + K          (positiv = Durchhalten waere billiger gewesen)
    Pruefung der Wiedereinstiegs-Sperre (risk/reentry_guard.py: 90 min, 6 h nur >= 1 % unter Verkauf).
(b) Rauschen gegen Nachzieh-Abstand: Wie oft faellt der Kurs innerhalb von 1 h / 4 h um mindestens den
    Abstand d vom laufenden Hoch, ab ZUFAELLIGEN Minuten (reines Rauschen, unabhaengig vom Signal)?
    -> Ein Nachzieh-Abstand im Rauschband erzeugt Ausstiege ohne Information.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict

import numpy as np

from a5_basis import K_BITVAVO, K_BYBIT, Kerzen, V6, block_bootstrap, lade, runden_e7, speichere, ts_ms


def main():
    R = runden_e7()
    rows = lade(V6)
    buys = defaultdict(list)
    for r in rows:
        if str(r.get("type", "")).upper() == "BUY":
            buys[r["coin"]].append((ts_ms(r["time"]), float(r["price"]), r.get("strategy")))
    erg = {"rueckkauf": {}, "sperre_verletzt": [], "rauschen": {}}
    za = []
    for r in R:
        nb = [b for b in buys[r["coin"]] if b[0] > r["verkauf_ms"]]
        if not nb:
            continue
        b = min(nb)
        gap_h = (b[0] - r["verkauf_ms"]) / 3_600_000
        diff = (b[1] / r["verkauf_preis"] - 1) * 100
        art = r["ausstieg"] if r["ausstieg"] in ("STOP_LOSS", "BREAKEVEN_LOCK", "TRAILING_STOP") else "SIGNAL"
        za.append({"art": art, "phase": r["phase"], "gap_h": gap_h, "diff": diff, "tag": r["tag"],
                   "nominal": r["kauf_nominal"]})
        if gap_h < 1.5 or (gap_h < 6 and diff > -1.0):
            erg["sperre_verletzt"].append({"verkauf": r["t"][:16], "coin": r["coin"], "art": art,
                                           "abstand_h": round(gap_h, 2), "preis_diff_pct": round(diff, 3),
                                           "kaufweg": b[2]})
    for fenster in (6, 24, 72):
        for gruppe in ("alle", "art", "phase"):
            g = defaultdict(list)
            for z in za:
                if z["gap_h"] <= fenster:
                    k = "alle" if gruppe == "alle" else z[gruppe]
                    g[k].append(z)
            for k, zs in g.items():
                e = {"n": len(zs), "abstand_median_h": st.median(z["gap_h"] for z in zs),
                     "teurer_zurueck": sum(z["diff"] > 0 for z in zs),
                     "preis_diff_mittel_pct": st.mean(z["diff"] for z in zs)}
                for K in (K_BITVAVO, K_BYBIT):
                    kost = [z["diff"] + K for z in zs]
                    p, lo, hi = block_bootstrap([z["tag"] for z in zs], kost, "mittel")
                    e[f"K{K:.3f}"] = {"kosten_mittel_pct": p, "ci95": [lo, hi],
                                      "kosten_usd": sum(z["nominal"] * c / 100 for z, c in zip(zs, kost))}
                erg["rueckkauf"][f"{fenster}h|{gruppe}|{k}"] = e
    erg["rueckkauf_gesamt"] = {"verkaeufe_mit_folgekauf": len(za), "verkaeufe": len(R)}
    # (b) Rauschen: Anteil Startminuten, ab denen der Kurs binnen T um >= d vom laufenden Hoch faellt
    k1m = Kerzen("1m")
    rng = np.random.default_rng(11)
    for coin, d in k1m.d.items():
        t, h, l = d["t"], d["h"], d["l"]
        i0, i1 = np.searchsorted(t, ts_ms("2026-08-13T13:21:19Z")), np.searchsorted(t, ts_ms("2026-10-14T09:18:25Z"))
        starts = rng.integers(i0, i1 - 240, size=3000)
        for T in (60, 240):
            for dd in (0.85, 1.0, 1.274, 1.5, 2.0, 3.0):
                hit = 0
                for s in starts:
                    hh = np.maximum.accumulate(h[s:s + T])
                    if np.any(l[s:s + T] <= hh * (1 - dd / 100)):
                        hit += 1
                erg["rauschen"][f"{coin}|{T}min|{dd}"] = hit / len(starts)
    speichere("a5_halteband.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
