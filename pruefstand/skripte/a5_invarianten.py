# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 2 · Kosten-Invarianten I1-I3 (MASTERPROMPT 3.9) fuer E7, E8 und Bitvavo-Regeln,
gegen K = 0,505 (Bybit) und K = 0,150 (Bitvavo), mit nominellem UND wirksamem Abstand
(risk/regime_profiles.py skaliert: EARLY_BEAR/RANGING 0,85; TRENDING 0,98; TRENDING_UP 0,98 x 1,3 = 1,274).

I1  puffer        >= K + marge
I2  trail_start   >= h_trailing(K, abstand) + marge,  h = ((1+K/100)/(1-abstand/100) - 1)*100
I3  ziel_abstand  >= 3*K  und  >= 1,5 * stopp       (ziel_abstand: hier Nachzieh-Start und Ø Gewinnerbewegung)

Eichung der Marge an den Daten: Unterschiessen der echten Ausloesung gegenueber der Regel-Linie
(Takt 30 s + Kurssprung) aus den 21 Nullsicherungen und 61 Nachzieh-Ausstiegen von E7.
"""
from __future__ import annotations

import json
import re
import statistics as st

import numpy as np

from a5_basis import K_BITVAVO, K_BYBIT, runden_e7, speichere


def h_trailing(K, a):
    return ((1 + K / 100) / (1 - a / 100) - 1) * 100


def main():
    R = runden_e7()
    erg = {}
    # ---- Eichung: Ausloesung (Bot-pnl_pct im Grund) gegen Linie, und Fuellung gegen Ausloesung
    be = [r for r in R if r["ausstieg"] == "BREAKEVEN_LOCK"]
    lag = []
    for r in be:
        m = re.search(r"jetzt ([+-][0-9.]+)%", r["grund"])
        lag.append(0.35 - float(m.group(1)))
    fill = [r["kurs_pct"] - r["pnl_pct_bot"] for r in be]
    gesamt = [0.35 - r["kurs_pct"] for r in be]
    erg["eichung_nullsicherung"] = {
        "n": len(be),
        "verzug_ausloesung_mittel": st.mean(lag), "verzug_ausloesung_p90": float(np.quantile(lag, 0.9)),
        "fuellung_minus_ausloesung_mittel": st.mean(fill),
        "puffer_minus_kurs_mittel": st.mean(gesamt), "puffer_minus_kurs_median": st.median(gesamt),
        "puffer_minus_kurs_p90": float(np.quantile(gesamt, 0.9)), "puffer_minus_kurs_p95": float(np.quantile(gesamt, 0.95)),
        "max": max(gesamt),
    }
    tr = []
    for r in R:
        if r["ausstieg"] != "TRAILING_STOP":
            continue
        m = re.search(r"Fall ([0-9.]+)% >= ([0-9.]+)%", r["grund"])
        if m:
            tr.append(float(m.group(1)) - float(m.group(2)))
    erg["eichung_nachzieh_ueberschuss_fall"] = {"n": len(tr), "mittel": st.mean(tr), "median": st.median(tr),
                                               "p90": float(np.quantile(tr, 0.9)), "p95": float(np.quantile(tr, 0.95))}
    marge_daten = round(float(np.quantile(gesamt, 0.9)), 2)
    erg["marge_vorschlag"] = {"masterprompt": 0.10, "aus_daten_p90": marge_daten,
                              "heute_im_code": 0.045}

    # ---- Wirksame Abstaende
    abst = {"nominal_1.0": 1.0, "wirksam_RANGING_0.85": 0.85, "wirksam_TRENDING_0.98": 0.98,
            "wirksam_TRENDING_UP_1.274": 1.274}
    stopps = {"nominal_2.5": 2.5, "wirksam_RANGING_2.12": 2.12, "wirksam_TRENDING_2.23": 2.23}
    regeln = {"E7": {"puffer": 0.35, "start": 1.2}, "E8": {"puffer": 0.55, "start": 1.57},
              "Bitvavo": {"puffer": 0.195, "start": 1.21}}
    # Ø Gewinner-Bewegung brutto je K (aus den echten Runden)
    gew_bew = {}
    for K in (K_BYBIT, K_BITVAVO):
        g = [r["kurs_pct"] for r in R if r["brutto_pct"] - K > 0]
        v = [r["kurs_pct"] for r in R if r["brutto_pct"] - K <= 0]
        gew_bew[K] = (st.mean(g), st.mean(v))
    tab = []
    for rn, rg in regeln.items():
        for K in (K_BYBIT, K_BITVAVO):
            for marge_name, marge in (("0,10", 0.10), ("Daten_p90", marge_daten)):
                z = {"regel": rn, "K": K, "marge": marge_name, "puffer": rg["puffer"], "start": rg["start"]}
                z["I1_soll"] = round(K + marge, 3)
                z["I1_ok"] = rg["puffer"] >= K + marge - 1e-9
                z["I1_netto_erwartet_nullsicherung"] = round(rg["puffer"] - erg["eichung_nullsicherung"]["puffer_minus_kurs_mittel"] - K, 3)
                for an, a in abst.items():
                    soll = h_trailing(K, a) + marge
                    z[f"I2_{an}_soll"] = round(soll, 3)
                    z[f"I2_{an}_ok"] = rg["start"] >= soll - 1e-9
                # I3 mit Nachzieh-Start als Ziel und mit Ø Gewinnerbewegung als Ziel
                gb, vb = gew_bew[K]
                z["I3_ziel_start_ge_3K"] = rg["start"] >= 3 * K
                z["I3_gewinnerbewegung"] = round(gb, 3)
                z["I3_verliererbewegung"] = round(vb, 3)
                z["I3_gewinner_ge_3K"] = gb >= 3 * K
                for sn, s in stopps.items():
                    z[f"I3_ziel_start_ge_1.5_stopp_{sn}"] = rg["start"] >= 1.5 * s
                    z[f"I3_gewinner_ge_1.5_stopp_{sn}"] = gb >= 1.5 * s
                tab.append(z)
    erg["tabelle"] = tab
    # Schutzwirkung: Solange I1 gilt und trail_start >= BREAKEVEN_AB (1,0), kann ein Nachzieh-Ausstieg
    # nicht unter dem Puffer enden (die Nullsicherung loest zuerst aus). Beleg in den Daten:
    tr_unter = [r for r in R if r["ausstieg"] == "TRAILING_STOP" and r["kurs_pct"] < 0.35]
    erg["nachzieh_unter_puffer_E7"] = {"n": len(tr_unter),
                                       "faelle": [(r["t"][:16], r["coin"], round(r["kurs_pct"], 3), r["grund"]) for r in tr_unter]}
    speichere("a5_invarianten.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
