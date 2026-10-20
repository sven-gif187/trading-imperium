# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 1 · MFE/MAE je Runde (hoechster/tiefster Zwischenstand), Rueckgabe, Verlierer mit Vorlauf ins Plus.

Drei Wege fuer MFE/MAE:
  (a) Bot-Feld mfe_pct/mae_pct im Verkaufssatz (30-s-Takt, letzter Kurs)
  (b) 1m-Kerzen Binance zwischen Kauf und Verkauf (Hoch/Tief inkl. Dochte)
  (c) positionsverlauf.db (5-min-Takt, ab 19.08.)
Rueckgabe = MFE - mitgenommene Kursbewegung (Verkaufskurs/Einstiegskurs - 1).
Gewinner/Verlierer je Kostenlatte K (0,505 und 0,150).
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict

import numpy as np

from a5_basis import (K_BITVAVO, K_BYBIT, Kerzen, pv_verbindung, runden_e7, speichere)


def main():
    R = runden_e7()
    k1m = Kerzen("1m")
    con = pv_verbindung()
    for r in R:
        d = k1m.d[r["coin"]]
        i = k1m.ab(r["coin"], r["kauf_ms"] + 60_000 - (r["kauf_ms"] % 60_000))   # erste volle Minute nach Kauf
        j = k1m.ab(r["coin"], r["verkauf_ms"] - (r["verkauf_ms"] % 60_000))      # Minute des Verkaufs (exklusiv)
        if j > i:
            r["mfe_kerze"] = (d["h"][i:j].max() / r["einstieg_preis"] - 1) * 100
            r["mae_kerze"] = (d["l"][i:j].min() / r["einstieg_preis"] - 1) * 100
        else:
            r["mfe_kerze"] = r["mae_kerze"] = None
        pv = None
        if r["position_id"]:
            pv = con.execute("select max(mfe_pct), min(mae_pct), count(*) from verlauf where pos_id=?",
                             (r["position_id"],)).fetchone()
        r["mfe_pv"], r["mae_pv"], r["n_pv"] = (pv if pv and pv[2] else (None, None, 0))

    erg = {"n": len(R)}
    # --- Abgleich der drei Wege
    def diffs(a, b):
        x = [r[a] - r[b] for r in R if r.get(a) is not None and r.get(b) is not None]
        return {"n": len(x), "median": st.median(x), "mittel": st.mean(x)} if x else None
    erg["abgleich"] = {
        "mfe_kerze_minus_bot": diffs("mfe_kerze", "mfe_bot"),
        "mae_kerze_minus_bot": diffs("mae_kerze", "mae_bot"),
        "mfe_pv_minus_bot": diffs("mfe_pv", "mfe_bot"),
        "kurs_pct_minus_pnl_pct_bot": diffs("kurs_pct", "pnl_pct_bot"),
    }

    for K in (K_BYBIT, K_BITVAVO):
        key = f"K_{K:.3f}"
        e = {}
        gew = [r for r in R if r["brutto_pct"] - K > 0]
        ver = [r for r in R if r["brutto_pct"] - K <= 0]
        e["gewinner"] = len(gew)
        e["verlierer"] = len(ver)
        e["treffer_pct"] = 100 * len(gew) / len(R)
        e["avg_gewinn_netto"] = st.mean(r["brutto_pct"] - K for r in gew)
        e["avg_verlust_netto"] = st.mean(r["brutto_pct"] - K for r in ver)
        e["noetige_trefferquote"] = 100 * -e["avg_verlust_netto"] / (e["avg_gewinn_netto"] - e["avg_verlust_netto"])
        e["netto_usd"] = sum(r["kauf_nominal"] * (r["brutto_pct"] - K) / 100 for r in R)
        for quelle in ("bot", "kerze"):
            g = [r for r in gew if r[f"mfe_{quelle}"] is not None]
            e[f"gewinner_mfe_{quelle}"] = st.mean(r[f"mfe_{quelle}"] for r in g)
            e[f"gewinner_mitgenommen_kurs"] = st.mean(r["kurs_pct"] for r in g)
            e[f"gewinner_rueckgabe_{quelle}"] = st.mean(r[f"mfe_{quelle}"] - r["kurs_pct"] for r in g)
            v = [r for r in ver if r[f"mfe_{quelle}"] is not None]
            for s in (0.5, 1.0):
                x = [r for r in v if r[f"mfe_{quelle}"] >= s]
                e[f"verlierer_mfe_ge_{s}_{quelle}"] = {"n": len(x), "von": len(v),
                                                        "netto_usd": sum(r["kauf_nominal"] * (r["brutto_pct"] - K) / 100 for r in x)}
        erg[key] = e

    # --- je Ausstiegsart (Bot-MFE)
    ja = defaultdict(list)
    for r in R:
        art = r["ausstieg"] if r["ausstieg"] in ("STOP_LOSS", "BREAKEVEN_LOCK", "TRAILING_STOP") else "SIGNAL"
        ja[art].append(r)
    erg["je_ausstieg"] = {}
    for art, rr in ja.items():
        erg["je_ausstieg"][art] = {
            "n": len(rr),
            "mfe_bot_mittel": st.mean(r["mfe_bot"] for r in rr),
            "mfe_bot_median": st.median(r["mfe_bot"] for r in rr),
            "mae_bot_mittel": st.mean(r["mae_bot"] for r in rr),
            "kurs_pct_mittel": st.mean(r["kurs_pct"] for r in rr),
            "rueckgabe_mittel": st.mean(r["mfe_bot"] - r["kurs_pct"] for r in rr),
            "netto_usd_K0505": sum(r["kauf_nominal"] * (r["brutto_pct"] - K_BYBIT) / 100 for r in rr),
            "netto_usd_K0150": sum(r["kauf_nominal"] * (r["brutto_pct"] - K_BITVAVO) / 100 for r in rr),
            "im_plus_K0505": sum(r["brutto_pct"] > K_BYBIT for r in rr),
            "im_plus_K0150": sum(r["brutto_pct"] > K_BITVAVO for r in rr),
        }
    # --- MFE-Verteilung: wie viele Runden erreichen welche Schwelle (Bot / Kerze)
    erg["mfe_schwellen"] = {}
    for s in (0.5, 1.0, 1.21, 1.57, 2.0, 3.0, 5.0, 8.0):
        erg["mfe_schwellen"][str(s)] = {
            "bot": sum(r["mfe_bot"] >= s for r in R),
            "kerze": sum((r["mfe_kerze"] or -9) >= s for r in R),
        }
    # --- MAE der spaeteren Gewinner (wie tief tauchen Gewinner vorher?)
    for K in (K_BYBIT, K_BITVAVO):
        g = [r["mae_bot"] for r in R if r["brutto_pct"] - K > 0]
        erg[f"K_{K:.3f}"]["gewinner_mae_quantile"] = {q: float(np.quantile(g, q)) for q in (0.1, 0.25, 0.5)}
    # --- je Phase
    erg["je_phase"] = {}
    for ph in ("A_Aug", "B_SepOkt"):
        rr = [r for r in R if r["phase"] == ph]
        v = [r for r in rr if r["brutto_pct"] - K_BYBIT <= 0]
        erg["je_phase"][ph] = {
            "n": len(rr),
            "mfe_bot_mittel": st.mean(r["mfe_bot"] for r in rr),
            "kurs_pct_mittel": st.mean(r["kurs_pct"] for r in rr),
            "verlierer_K0505": len(v),
            "verlierer_mfe_ge_0.5": sum(r["mfe_bot"] >= 0.5 for r in v),
            "verlierer_mfe_ge_1.0": sum(r["mfe_bot"] >= 1.0 for r in v),
        }
    speichere("a5_mfe_mae.json", erg)
    speichere("a5_runden_angereichert.json", R)
    import json
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
