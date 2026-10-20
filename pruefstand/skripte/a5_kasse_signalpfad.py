# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · Nebenbefund Kasse: Verkaufsgebuehr auf dem Schreibpfad execute_approved_trade doppelt abgezogen?

Weg 1: Verhaeltnis amount / (qty * price) je Schreibpfad im Verkaufssatz.
Weg 2: Netto aus Kursbewegung minus beide Gebuehren (unabhaengig von 'amount') gegen runden_lib.
Code-Beleg (nur gelesen): execution/engine.py:437-451  revenue = qty*price; fee = revenue*fee_rate;
net = revenue - fee; USDC += net; result.filled_cost = net  -> amount (Signalpfad) ist schon netto.
"""
from __future__ import annotations

import json
import statistics as st

from a5_basis import V6, VON, BIS, lade, runden_e7, speichere


def main():
    rows = lade(V6)
    S = [r for r in rows if str(r.get("type", "")).upper() == "SELL" and VON <= r["time"] < BIS]
    erg = {"weg1": {}}
    for pfad in sorted({s.get("schreibpfad") for s in S}):
        ss = [s for s in S if s.get("schreibpfad") == pfad]
        q = [(float(s["amount"]) / (float(s["qty"]) * float(s["price"])) - 1) * 100 for s in ss]
        erg["weg1"][pfad] = {"n": len(ss), "amount_zu_qty_mal_kurs_pct": st.mean(q), "min": min(q), "max": max(q)}
    R = runden_e7()
    lib = sum(r["netto"] for r in R)
    korr = sum(r["kauf_nominal"] * r["kurs_pct"] / 100 - r["kauf_fee"] - r["verkauf_fee"] for r in R)
    sig = [r for r in R if r["ausstieg"] not in ("STOP_LOSS", "BREAKEVEN_LOCK", "TRAILING_STOP")]
    erg["weg2"] = {
        "netto_runden_lib_usd": lib,
        "netto_kurs_minus_gebuehren_usd": korr,
        "differenz_usd": korr - lib,
        "summe_verkaufsgebuehr_signalrunden_usd": sum(r["verkauf_fee"] for r in sig),
        "brutto_runden_lib_usd": sum(r["brutto"] for r in R),
        "brutto_kurs_usd": sum(r["kauf_nominal"] * r["kurs_pct"] / 100 for r in R),
        "vorsprung_je_runde_lib_pct": st.mean(r["brutto_pct_lib"] for r in R),
        "vorsprung_je_runde_kurs_pct": st.mean(r["kurs_pct"] for r in R),
        "signal_runden_netto_lib_usd": sum(r["netto"] for r in sig),
        "signal_runden_netto_korr_usd": sum(r["kauf_nominal"] * r["kurs_pct"] / 100 - r["kauf_fee"] - r["verkauf_fee"] for r in sig),
    }
    speichere("a5_kasse_signalpfad.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
