# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · Eichung des Nachspiel-Motors: Wie gut trifft die Nachspielung die ECHTEN 136 E7-Ausstiege?

Gespielt wird die tatsaechlich wirksame E7-Regel (Log/Verkaufsgruende): Verlustbremse und Abstand
werden in v6 von risk/regime_profiles.py skaliert (Zyklus EARLY_BEAR: SL x0,85, Trail x0,85;
Regime TRENDING: SL x1,05, Trail x1,15; VOLATILE: SL x0,85, Trail x0,9; TRENDING_UP zusaetzlich
TREND_BONUS x1,3 auf den Abstand). Zwei Fassungen:
  ist_fest   : 2,12 / ab 1,2 / 0,85, Nullsicherung 1,0 -> 0,35 (Fall EARLY_BEAR/RANGING, 25 von 33 Stopps)
  ist_regime : wie oben, aber SL/Trail je Runde aus market_regime + cycle_phase des Verkaufssatzes
Ohne Kapitalbindung (gleiche 136 Einstiege). Gemessen: Treffer der Ausstiegsart, Zeitabstand,
Kurs-% Nachspielung minus echt (= Verzerrung der Nachspielung, Masterprompt nimmt 0,15 an).
Dazu: Pruefung der RSI-Signal-Nachbildung gegen die 21 echten Signal-Verkaeufe.
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict

import numpy as np

from a5_basis import Kerzen, block_bootstrap, runden_e7, speichere
from a5_motor import Regel, RSIStunde, spiele

CYC = {"EARLY_BEAR": (0.85, 0.85), "MID_BEAR": (0.80, 0.80)}
REG = {"RANGING": (1.0, 1.0, 1.0), "TRENDING_UP": (1.05, 1.15, 1.3), "TRENDING_DOWN": (1.05, 1.15, 1.0),
       "VOLATILE": (0.85, 0.90, 1.0)}


def sl_regime(r):
    c = CYC.get(r["zyklus"], (1.0, 1.0))
    g = REG.get(r["regime"], (1.0, 1.0, 1.0))
    return round(max(1.5, min(6.0, 2.5 * c[0] * g[0])), 2)


def trail_regime(r):
    c = CYC.get(r["zyklus"], (1.0, 1.0))
    g = REG.get(r["regime"], (1.0, 1.0, 1.0))
    return round(max(0.5, min(4.0, 1.0 * c[1] * g[1])), 2) * g[2]


def art_echt(r):
    return r["ausstieg"] if r["ausstieg"] in ("STOP_LOSS", "BREAKEVEN_LOCK", "TRAILING_STOP") else "SIGNAL"


def main():
    R = runden_e7()
    k1m, k1h = Kerzen("1m"), Kerzen("1h")
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    erg = {}

    # --- RSI-Nachbildung: wann waere das Signal erstmals gefallen (zwischen Kauf und echtem Ausstieg + 1 h)?
    rs = {"signal_echt_n": 0, "signal_getroffen_15min": 0, "signal_getroffen_60min": 0,
          "fruehe_fehlsignale_bei_nicht_signal": 0, "nicht_signal_n": 0, "abstaende_min": []}
    for r in R:
        d = k1m.d[r["coin"]]
        i0 = k1m.ab(r["coin"], r["kauf_ms"] - r["kauf_ms"] % 60_000 + 60_000)
        j1 = k1m.ab(r["coin"], r["verkauf_ms"] + 3_600_000)
        e = r["einstieg_preis"]
        rr = rsis[r["coin"]].rsi_min
        hit = None
        for j in range(i0, j1):
            if rr[j] > 80 and (d["c"][j] / e - 1) * 100 > 1.0:
                hit = int(d["t"][j]) + 60_000
                break
        if art_echt(r) == "SIGNAL":
            rs["signal_echt_n"] += 1
            if hit is not None:
                ab = (hit - r["verkauf_ms"]) / 60_000
                rs["abstaende_min"].append(round(ab, 1))
                rs["signal_getroffen_15min"] += abs(ab) <= 15
                rs["signal_getroffen_60min"] += abs(ab) <= 60
        else:
            rs["nicht_signal_n"] += 1
            if hit is not None and hit < r["verkauf_ms"] - 60_000:
                rs["fruehe_fehlsignale_bei_nicht_signal"] += 1
    erg["rsi_nachbildung"] = rs

    fassungen = {
        "ist_fest_mit_signal": Regel("ist_fest", sl=2.12, start=1.2, trail=0.85, be_ab=1.0, puffer=0.35, signal=True),
        "ist_fest_ohne_signal": Regel("ist_fest", sl=2.12, start=1.2, trail=0.85, be_ab=1.0, puffer=0.35, signal=False),
        "ist_regime_mit_signal": Regel("ist_regime", sl=None, sl_fn=sl_regime, trail_fn=trail_regime,
                                       start=1.2, be_ab=1.0, puffer=0.35, signal=True),
        "nominal_2.5_1.2_1.0": Regel("nominal", sl=2.5, start=1.2, trail=1.0, be_ab=1.0, puffer=0.35, signal=True),
    }
    for name, p in fassungen.items():
        z = []
        for r in R:
            x = spiele(r, p, k1m, rsis[r["coin"]])
            x["kurs_pct"] = (x["preis"] / r["einstieg_preis"] - 1) * 100
            z.append((r, x))
        diff = [x["kurs_pct"] - r["kurs_pct"] for r, x in z]
        gleich = sum(x["art"] == art_echt(r) for r, x in z)
        zeit = [abs(x["aus_ms"] - r["verkauf_ms"]) / 60_000 for r, x in z]
        je = defaultdict(list)
        for r, x in z:
            je[art_echt(r)].append(x["kurs_pct"] - r["kurs_pct"])
        verw = Counter((art_echt(r), x["art"]) for r, x in z)
        pkt, lo, hi = block_bootstrap([r["tag"] for r, _ in z], diff, "mittel")
        erg[name] = {
            "art_gleich": gleich, "n": len(z),
            "zeit_abstand_median_min": st.median(zeit),
            "zeit_abstand_le_10min": sum(v <= 10 for v in zeit),
            "kurs_diff_mittel": st.mean(diff), "kurs_diff_median": st.median(diff),
            "kurs_diff_95": [lo, hi],
            "kurs_diff_je_echter_art": {k: {"n": len(v), "mittel": st.mean(v), "median": st.median(v)} for k, v in je.items()},
            "verwechslung_echt_zu_nachgespielt": {f"{a}->{b}": n for (a, b), n in sorted(verw.items())},
        }
        # nur Runden mit gleicher Ausstiegsart: reine Ausfuehrungs-Verzerrung
        same = [x["kurs_pct"] - r["kurs_pct"] for r, x in z if x["art"] == art_echt(r)]
        erg[name]["kurs_diff_bei_gleicher_art_mittel"] = st.mean(same) if same else None
    # Ueberschiessen der echten Ausstiege gegen die Regel-Linie (Takt 30 s + Kursspruenge)
    ueb = defaultdict(list)
    for r in R:
        a = art_echt(r)
        if a == "STOP_LOSS":
            import re
            m = re.search(r"<= -([0-9.]+)%", r["grund"])
            if m:
                ueb[a].append(r["kurs_pct"] + float(m.group(1)))
        elif a == "BREAKEVEN_LOCK":
            ueb[a].append(r["kurs_pct"] - 0.35)
        elif a == "TRAILING_STOP":
            import re
            m = re.search(r">= ([0-9.]+)%", r["grund"])
            if m and r["mfe_bot"] is not None:
                lvl = ((1 + r["mfe_bot"] / 100) * (1 - float(m.group(1)) / 100) - 1) * 100
                ueb[a].append(r["kurs_pct"] - lvl)
    erg["echt_minus_regel_linie"] = {k: {"n": len(v), "mittel": st.mean(v), "median": st.median(v),
                                         "p05": float(np.quantile(v, 0.05)), "p95": float(np.quantile(v, 0.95))}
                                     for k, v in ueb.items()}
    speichere("a5_eichung.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
