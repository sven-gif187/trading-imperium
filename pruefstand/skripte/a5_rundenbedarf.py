# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · Noetige Rundenzahl fuer die Vorschlaege (Vorab-Registrierung).

Gepaarte Tagesdifferenz (Variante minus Referenz Bv_ist, Netto-$ bei K 0,150) aus der Nachspielung:
  Tage_noetig(80 % Trennschaerfe, zweiseitig 5 %) = ((1,96 + 0,84) * sd_tag / effekt_tag)^2
  Runden_noetig = Tage_noetig * Runden_je_Tag (E7: 136 Runden / 39 Handelstage)
Fuer den Puffer (P1): Streuung der Nullsicherungs-Ausstiege um die Linie (sd aus a5_invarianten-Eichung).
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict

from a5_basis import K_BITVAVO, Kerzen, atr_bei, atr_pct_1h, runden_e7, speichere, ABSCHLAG_NACHSPIELUNG
from a5_explorativ import spiele_alle_band
from a5_motor import Regel, RSIStunde, spiele_alle


def tage_usd(z):
    d = defaultdict(float)
    for x in z:
        d[x["runde"]["kauf_t"][:10]] += x["runde"]["kauf_nominal"] * (x["kurs_pct"] - K_BITVAVO - ABSCHLAG_NACHSPIELUNG) / 100
    return d


def main():
    R = runden_e7()
    k1m, k1h = Kerzen("1m"), Kerzen("1h")
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    atr = {c: atr_pct_1h(k1h, c) for c in k1h.d}
    tage_alle = sorted({r["tag"] for r in R} | {r["kauf_t"][:10] for r in R})
    runden_je_tag = len(R) / len({r["tag"] for r in R})

    def trail_atr(r):
        tg, ap = atr[r["coin"]]
        return max(0.85, 2.0 * atr_bei(tg, ap, r["kauf_ms"]))

    ref_p = Regel("Bv_ist", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195)
    ref = spiele_alle(R, ref_p, k1m, rsis)
    ref6 = spiele_alle_band(R, ref_p, k1m, rsis, sperre_h=6)
    x_atr = 3.27   # aus a5_nachspielung (Eichung vor dem Fenster)

    def sl_atr(r):
        tg, ap = atr[r["coin"]]
        return float(min(6.0, max(1.0, x_atr * atr_bei(tg, ap, r["kauf_ms"]))))

    kand = {
        "P1_puffer025": (spiele_alle(R, Regel("p", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.25), k1m, rsis), ref),
        "ATR_Stopp": (spiele_alle(R, Regel("a", sl=None, sl_fn=sl_atr, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195), k1m, rsis), ref),
        "X1_trail_2ATR": (spiele_alle_band(R, Regel("x1", sl=2.12, start=1.21, trail=0.85, trail_fn=trail_atr, be_ab=1.0, puffer=0.195), k1m, rsis, sperre_h=6), ref6),
        "X2_band_24h": (spiele_alle_band(R, ref_p, k1m, rsis, sperre_h=24), ref6),
        "X3_beides": (spiele_alle_band(R, Regel("x3", sl=2.12, start=1.21, trail=0.85, trail_fn=trail_atr, be_ab=1.0, puffer=0.195), k1m, rsis, sperre_h=24), ref6),
        "weit_8_5_5": (spiele_alle(R, Regel("w", sl=8.0, start=5.0, trail=5.0, leiter=False, be_ab=None), k1m, rsis), ref),
    }
    erg = {"runden_je_handelstag": runden_je_tag, "kandidaten": {}}
    for name, (z, rz) in kand.items():
        a, b = tage_usd(z), tage_usd(rz)
        tage = sorted(set(a) | set(b))
        diff = [a.get(t, 0.0) - b.get(t, 0.0) for t in tage]
        eff = st.mean(diff)
        sd = st.pstdev(diff)
        n_tage = ((1.96 + 0.84) * sd / eff) ** 2 if eff != 0 else float("inf")
        erg["kandidaten"][name] = {"tage": len(tage), "effekt_je_tag_usd": eff, "sd_je_tag_usd": sd,
                                   "summe_usd": sum(diff), "tage_noetig_80pct": n_tage,
                                   "runden_noetig_80pct": n_tage * runden_je_tag}
    # P1 direkt: Nullsicherungs-Ausstiege, Abstand der echten Fuellung zur Linie
    be = [r for r in R if r["ausstieg"] == "BREAKEVEN_LOCK"]
    sd_be = st.pstdev([0.35 - r["kurs_pct"] for r in be])
    erg["P1_nullsicherungen_noetig"] = {"sd_pct": sd_be,
                                        "fuer_mittel_ge_0_bei_wahrem_plus_0.028": ((1.96 + 0.84) * sd_be / 0.028) ** 2,
                                        "fuer_95pct_bereich_ueber_minus_0.05": ((1.96) * sd_be / 0.078) ** 2}
    speichere("a5_rundenbedarf.json", erg)
    print(json.dumps(erg, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
