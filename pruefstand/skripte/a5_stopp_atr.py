# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 3 · Verlustbremse je Muenze gegen ihre Schwankung (ATR 14 auf 1h-Kerzen).

- Stopp-Quote je Muenze (E7, 136 Runden), Netto der Stopps je K.
- ATR% beim Kauf: Weg 1 = eigene Rechnung (Wilder, 1h Binance, nur abgeschlossene Kerzen),
                  Weg 2 = positionsverlauf.db (Spalte atr_pct, erste Zeile je Position, Bot-Rechnung).
- Stopp-Abstand in ATR-Einheiten je Muenze (wirksam 2,12 %).
- Wie tief tauchen spaetere Gewinner (MAE) in ATR-Einheiten? -> Vorschlag Stopp = x * ATR.
  Eichung nur auf August (Phase A), Pruefung auf September/Oktober (Phase B): kein Blick in die Zukunft.
- Typische Stundenspanne (Hoch-Tief)/Schluss je Muenze im Fenster.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict

import numpy as np

from a5_basis import K_BITVAVO, K_BYBIT, Kerzen, atr_bei, atr_pct_1h, pv_verbindung, runden_e7, speichere, ts_ms


def main():
    R = runden_e7()
    k1h = Kerzen("1h")
    con = pv_verbindung()
    atr = {c: atr_pct_1h(k1h, c) for c in k1h.d}
    for r in R:
        tg, ap = atr[r["coin"]]
        r["atr_kauf"] = atr_bei(tg, ap, r["kauf_ms"])
        row = None
        if r["position_id"]:
            row = con.execute("select atr_pct, ts_utc from verlauf where pos_id=? order by ts_utc limit 1",
                              (r["position_id"],)).fetchone()
        r["atr_kauf_pv"] = row[0] if row else None
    erg = {"je_muenze": {}}
    for coin in ("BTC/USDC", "ETH/USDC", "SOL/USDC"):
        rr = [r for r in R if r["coin"] == coin]
        sl = [r for r in rr if r["ausstieg"] == "STOP_LOSS"]
        d = k1h.d[coin]
        m = (d["t"] >= ts_ms("2026-08-13T13:00:00Z")) & (d["t"] < ts_ms("2026-10-14T09:00:00Z"))
        spanne = (d["h"][m] - d["l"][m]) / d["c"][m] * 100
        tg, ap = atr[coin]
        mm = (tg >= ts_ms("2026-08-13T13:00:00Z")) & (tg < ts_ms("2026-10-14T09:00:00Z"))
        a_kauf = [r["atr_kauf"] for r in rr]
        a_pv = [(r["atr_kauf"], r["atr_kauf_pv"]) for r in rr if r["atr_kauf_pv"]]
        e = {
            "runden": len(rr), "stopps": len(sl), "stopp_quote_pct": 100 * len(sl) / len(rr),
            "stopps_netto_usd_K0505": sum(r["kauf_nominal"] * (r["brutto_pct"] - K_BYBIT) / 100 for r in sl),
            "stopps_netto_usd_K0150": sum(r["kauf_nominal"] * (r["brutto_pct"] - K_BITVAVO) / 100 for r in sl),
            "runden_netto_usd_K0150": sum(r["kauf_nominal"] * (r["brutto_pct"] - K_BITVAVO) / 100 for r in rr),
            "stundenspanne_median_pct": float(np.median(spanne)),
            "atr_fenster_median_pct": float(np.nanmedian(ap[mm])),
            "atr_beim_kauf_median_pct": float(np.median(a_kauf)),
            "atr_beim_kauf_pv_median_pct": float(np.median([b for _, b in a_pv])) if a_pv else None,
            "atr_weg1_minus_weg2_median": float(np.median([a - b for a, b in a_pv])) if a_pv else None,
            "stopp_212_in_atr": 2.12 / float(np.median(a_kauf)),
            "stopp_25_in_atr": 2.5 / float(np.median(a_kauf)),
        }
        # Gewinner (K 0,15) - MAE in ATR-Einheiten
        g = [r for r in rr if r["brutto_pct"] - K_BITVAVO > 0]
        mae_atr = [-r["mae_bot"] / r["atr_kauf"] for r in g if r["mae_bot"] is not None]
        e["gewinner_n"] = len(g)
        e["gewinner_mae_atr_quantile"] = {q: float(np.quantile(mae_atr, q)) for q in (0.5, 0.75, 0.9, 0.95)} if mae_atr else None
        e["stopp_mae_atr_median"] = float(np.median([-r["mae_bot"] / r["atr_kauf"] for r in sl])) if sl else None
        erg["je_muenze"][coin] = e
    # Eichung x auf Phase A, Pruefung Phase B: Anteil Gewinner, deren MAE den Stopp x*ATR beruehrt haette
    A = [r for r in R if r["phase"] == "A_Aug" and r["brutto_pct"] - K_BITVAVO > 0]
    B = [r for r in R if r["phase"] == "B_SepOkt"]
    mae_A = np.array([-r["mae_bot"] / r["atr_kauf"] for r in A])
    x90 = float(np.quantile(mae_A, 0.9))
    erg["eichung_A"] = {"gewinner_n": len(A), "x_90pct_gewinner_ueberleben": x90}
    # in B: wie viele Runden haetten mit x90*ATR statt 2,12 % den Stopp beruehrt (aus Bot-MAE)?
    def beruehrt(r, s):
        return r["mae_bot"] is not None and -r["mae_bot"] >= s
    zeilen = []
    for name, sfn in (("fest_2.12", lambda r: 2.12), ("fest_2.5", lambda r: 2.5), ("ATR_x90A", lambda r: x90 * r["atr_kauf"])):
        for coin in ("BTC/USDC", "ETH/USDC", "SOL/USDC", "alle"):
            rr = [r for r in B if coin == "alle" or r["coin"] == coin]
            gew = [r for r in rr if r["brutto_pct"] - K_BITVAVO > 0]
            zeilen.append({"regel": name, "coin": coin, "runden_B": len(rr),
                           "stopp_mittel_pct": st.mean(sfn(r) for r in rr),
                           "beruehrt_alle": sum(beruehrt(r, sfn(r)) for r in rr),
                           "beruehrt_gewinner": sum(beruehrt(r, sfn(r)) for r in gew), "gewinner": len(gew)})
    erg["pruefung_B_beruehrung"] = zeilen
    erg["hinweis"] = ("Beruehrung aus Bot-MAE bis zum ECHTEN Ausstieg; nach dem echten Ausstieg unbekannt. "
                      "Wirkung auf Netto nur aus der Nachspielung (a5_nachspielung.py, Variante ATR_Stopp).")
    speichere("a5_stopp_atr.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
