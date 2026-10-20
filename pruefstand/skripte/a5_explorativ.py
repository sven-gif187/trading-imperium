# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · EXPLORATIVE Nachspielungen (nach Sichtung von Rauschen/Rueckkauf/Nachlauf gewaehlt).
Ergebnisse sind KEIN Beleg, nur Groessenordnung fuer eine Vorab-Registrierung (Gefahr der Ueberanpassung).

X1  Nachzieh-Abstand je Muenze = 2 x ATR(14,1h) beim Kauf (aus dem Rauschband heraus), Rest wie Bv_ist
X2  Halteband nach Ausstieg: Rueckkauf derselben Muenze binnen 24 h nur, wenn Kaufkurs <= Verkaufskurs - 1 %
    (heute: 6 h), Ausstiege wie Bv_ist
X3  X1 + X2
Referenz: Bv_ist (2,12 / 1,21 / 0,85, Puffer 0,195). Kapitalbindung, -0,15 Abschlag, Block-Bootstrap, Bonferroni.
"""
from __future__ import annotations

import json

from a5_basis import K_BITVAVO, K_BYBIT, Kerzen, atr_bei, atr_pct_1h, runden_e7, speichere
from a5_motor import Regel, RSIStunde, spiele
from a5_nachspielung import PHASEN, auswerten, gepaart


def spiele_alle_band(R, p, k1m, rsis, sperre_h=None, abschlag_pct=1.0):
    aus, belegt, letzter = [], {}, {}
    for r in sorted(R, key=lambda x: x["kauf_ms"]):
        offen = [c for c, bis in belegt.items() if bis > r["kauf_ms"]]
        if r["coin"] in offen or len(offen) >= 3:
            continue
        if sperre_h is not None and r["coin"] in letzter:
            t_aus, p_aus = letzter[r["coin"]]
            if r["kauf_ms"] - t_aus < sperre_h * 3_600_000 and r["einstieg_preis"] > p_aus * (1 - abschlag_pct / 100):
                continue
        z = spiele(r, p, k1m, rsis.get(r["coin"]))
        z["kurs_pct"] = (z["preis"] / r["einstieg_preis"] - 1) * 100
        z["runde"] = r
        belegt[r["coin"]] = z["aus_ms"]
        letzter[r["coin"]] = (z["aus_ms"], z["preis"])
        aus.append(z)
    return aus


def main():
    R = runden_e7()
    k1m, k1h = Kerzen("1m"), Kerzen("1h")
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    atr = {c: atr_pct_1h(k1h, c) for c in k1h.d}

    def trail_atr(r):
        tg, ap = atr[r["coin"]]
        return max(0.85, 2.0 * atr_bei(tg, ap, r["kauf_ms"]))

    ref_p = Regel("Bv_ist", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195)
    x1 = Regel("X1_trail_2ATR", sl=2.12, start=1.21, trail=0.85, trail_fn=trail_atr, be_ab=1.0, puffer=0.195)
    ref = spiele_alle_band(R, ref_p, k1m, rsis, sperre_h=6)        # heutige Sperre 6 h nachgebildet
    V = {"X1_trail_2ATR": spiele_alle_band(R, x1, k1m, rsis, sperre_h=6),
         "X2_band_24h": spiele_alle_band(R, ref_p, k1m, rsis, sperre_h=24),
         "X3_beides": spiele_alle_band(R, x1, k1m, rsis, sperre_h=24)}
    m = len(V) * len(PHASEN)
    erg = {"bonferroni_m": m, "referenz_mit_sperre6h": {ph: auswerten(ref, a, b) for ph, (a, b) in PHASEN.items()}, "varianten": {}}
    for name, z in V.items():
        erg["varianten"][name] = {ph: {"werte": auswerten(z, a, b),
                                       "gegen_ref": {f"K{K:.3f}": gepaart(z, ref, a, b, K, 0.05 / m) for K in (K_BITVAVO, K_BYBIT)}}
                                  for ph, (a, b) in PHASEN.items()}
    speichere("a5_explorativ.json", erg)
    for ph in PHASEN:
        e = erg["referenz_mit_sperre6h"][ph]
        print(f"== {ph}  Ref n={e['n']} K.150 {e['K0.150']['netto_usd']:+.2f}$ K.505 {e['K0.505']['netto_usd']:+.2f}$ halte {e['haltedauer_median_h']:.1f}h")
        for name in V:
            w = erg["varianten"][name][ph]["werte"]
            g = erg["varianten"][name][ph]["gegen_ref"]
            print(f"  {name:14} n={w['n']:3} K.150 {w['K0.150']['netto_usd']:+8.2f}$ K.505 {w['K0.505']['netto_usd']:+8.2f}$ halte {w['haltedauer_median_h']:.1f}h "
                  f"diff K.150 {g['K0.150']['diff_usd']:+.2f} [{g['K0.150']['ci95'][0]:+.1f};{g['K0.150']['ci95'][1]:+.1f}] B[{g['K0.150']['ci_bonferroni'][0]:+.1f};{g['K0.150']['ci_bonferroni'][1]:+.1f}] "
                  f"| K.505 {g['K0.505']['diff_usd']:+.2f} [{g['K0.505']['ci95'][0]:+.1f};{g['K0.505']['ci95'][1]:+.1f}]  {w['arten']}")


if __name__ == "__main__":
    main()
