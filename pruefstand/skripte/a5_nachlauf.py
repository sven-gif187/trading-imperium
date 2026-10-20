# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 4 · Nachlauf: Kurs 1 h, 4 h, 24 h und 7 Tage nach jedem Verkauf, je Ausstiegsart und Marktlage.

Weg 1: Binance-1m-Kerzen (Schluss der Minute bei t+h) gegen den Verkaufskurs.
Weg 2: nachlauf.db des Bots (r1h/r4h/r24h; nur bis 27.09., danach Luecke) fuer dieselben Verkaeufe.
Gegen Drift: derselbe Horizont ab JEDER Minute derselben Muenze in derselben Marktlage (Zufalls-Latte).
Netto-Bedeutung: Nachlauf minus Drift > K heisst "Halten bis t+h waere nach Kosten besser gewesen"
(vereinfachte Sicht ohne den Weg dazwischen; die Nachspielung rechnet den Weg).
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from datetime import datetime

import numpy as np

from a5_basis import Kerzen, block_bootstrap, nl_verbindung, runden_e7, speichere, ts_ms

H = {"1h": 1, "4h": 4, "24h": 24, "7d": 168}


def art(r):
    return r["ausstieg"] if r["ausstieg"] in ("STOP_LOSS", "BREAKEVEN_LOCK", "TRAILING_STOP") else "SIGNAL"


def main():
    R = runden_e7()
    k1m = Kerzen("1m")
    erg = {"weg1": {}, "drift": {}, "weg2_abgleich": {}, "minus_drift": {}}
    # Drift-Latte je Muenze, Phase, Horizont (Mittel ueber alle Startminuten der Phase)
    grenzen = {"A_Aug": ("2026-08-13T13:21:19Z", "2026-09-01T00:00:00Z"), "B_SepOkt": ("2026-09-01T00:00:00Z", "2026-10-14T09:18:25Z")}
    drift = {}
    for coin, d in k1m.d.items():
        c, t = d["c"], d["t"]
        for ph, (a, b) in grenzen.items():
            i0, i1 = np.searchsorted(t, ts_ms(a)), np.searchsorted(t, ts_ms(b))
            for hn, h in H.items():
                j1 = min(i1, len(c) - h * 60)
                if j1 <= i0:
                    continue
                v = c[i0 + h * 60:j1 + h * 60] / c[i0:j1] * 100 - 100
                drift[(coin, ph, hn)] = float(v.mean())
    erg["drift"] = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in drift.items()}
    rows = []
    for r in R:
        x = {"art": art(r), "phase": r["phase"], "coin": r["coin"], "tag": r["tag"], "t": r["t"]}
        for hn, h in H.items():
            t2 = r["verkauf_ms"] + h * 3_600_000
            if t2 > k1m.ende(r["coin"]):
                x[hn] = None
                continue
            p = k1m.kurs_bei(r["coin"], t2)
            x[hn] = (p / r["verkauf_preis"] - 1) * 100
            x[hn + "_md"] = x[hn] - drift.get((r["coin"], r["phase"], hn), 0.0)
            # oertliche Latte: Mittel der h-Rendite ab jeder Minute im Fenster +-72 h um den Verkauf
            d = k1m.d[r["coin"]]
            a0 = np.searchsorted(d["t"], r["verkauf_ms"] - 72 * 3_600_000)
            a1 = min(np.searchsorted(d["t"], r["verkauf_ms"] + 72 * 3_600_000), len(d["c"]) - h * 60)
            x[hn + "_lok"] = x[hn] - float((d["c"][a0 + h * 60:a1 + h * 60] / d["c"][a0:a1] * 100 - 100).mean()) if a1 > a0 else None
        rows.append(x)
    for gruppe in ("art", "phase_art"):
        g = defaultdict(list)
        for x in rows:
            k = x["art"] if gruppe == "art" else f"{x['phase']}|{x['art']}"
            g[k].append(x)
        for k, xs in sorted(g.items()):
            e = {"n": len(xs)}
            for hn in H:
                v = [x[hn] for x in xs if x[hn] is not None]
                vm = [x[hn + "_md"] for x in xs if x.get(hn + "_md") is not None]
                if v:
                    p, lo, hi = block_bootstrap([x["tag"] for x in xs if x[hn] is not None], vm, "mittel")
                    vl = [x[hn + "_lok"] for x in xs if x.get(hn + "_lok") is not None]
                    pl, lol, hil = block_bootstrap([x["tag"] for x in xs if x.get(hn + "_lok") is not None], vl, "mittel")
                    e[hn] = {"n": len(v), "mittel": st.mean(v), "median": st.median(v),
                             "minus_drift": p, "minus_drift_ci95": [lo, hi],
                             "minus_oertlich": pl, "minus_oertlich_ci95": [lol, hil]}
            erg["weg1"][k] = e
    # Weg 2: nachlauf.db
    con = nl_verbindung()
    nl = con.execute("select ts_utc, muenze, preis, r1h, r4h, r24h, grund from nachlauf where art='exit'").fetchall()
    idx = defaultdict(list)
    for ts, m, p, r1, r4, r24, g in nl:
        idx[m].append((ts_ms(ts), p, r1, r4, r24, g))
    diffs = {"1h": [], "4h": [], "24h": []}
    treffer = 0
    for r, x in zip(R, rows):
        kand = [z for z in idx.get(r["coin"], []) if abs(z[0] - r["verkauf_ms"]) <= 120_000]
        if not kand:
            continue
        z = min(kand, key=lambda z: abs(z[0] - r["verkauf_ms"]))
        treffer += 1
        for hn, rv in (("1h", z[2]), ("4h", z[3]), ("24h", z[4])):
            if rv is not None and x[hn] is not None:
                # nachlauf.db misst gegen seinen eigenen Preis zum Zeitpunkt; auf Verkaufskurs umrechnen
                eigen = (z[1] * (1 + rv / 100) / r["verkauf_preis"] - 1) * 100
                diffs[hn].append(eigen - x[hn])
    erg["weg2_abgleich"] = {"verkaeufe_gefunden": treffer,
                            **{hn: {"n": len(v), "median_diff": st.median(v) if v else None,
                                    "mittel_abs_diff": st.mean(abs(a) for a in v) if v else None} for hn, v in diffs.items()}}
    erg["letzter_nachlauf_eintrag"] = con.execute("select max(ts_utc) from nachlauf where art='exit'").fetchone()[0]
    speichere("a5_nachlauf.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
