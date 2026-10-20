# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · Eichung von I3 (Ziel/Stopp) an den Daten: feste Klammer (Ziel T, Stopp S) auf den 136 E7-Einstiegen,
1m-Kerzen, hoechstens 7 Tage, ohne Kapitalbindung (beschreibend). Beruehren T und S dieselbe Minute,
zaehlt der Stopp (vorsichtig). Netto = Ergebnis - K - 0,15 (Nachspiel-Abschlag).
Frage: Wie oft erreicht ein Einstieg T vor S (Trefferquote), gegen die noetige Quote (S+K)/(T+S)?
DESKRIPTIV: 28 Zellen x 3 Lagen -> kein Einzelwert ist ein Beleg.
"""
from __future__ import annotations

import json
import statistics as st

import numpy as np

from a5_basis import ABSCHLAG_NACHSPIELUNG, K_BITVAVO, K_BYBIT, Kerzen, block_bootstrap, runden_e7, speichere

TS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)
SS = (1.5, 2.12, 3.0, 4.0)


def klammer(r, k1m, T, S, max_min=7 * 1440):
    d = k1m.d[r["coin"]]
    e = r["einstieg_preis"]
    i0 = int(np.searchsorted(d["t"], r["kauf_ms"] - r["kauf_ms"] % 60_000 + 60_000))
    i1 = min(len(d["t"]), i0 + max_min)
    hi, lo = d["h"][i0:i1], d["l"][i0:i1]
    up = np.nonzero(hi >= e * (1 + T / 100))[0]
    dn = np.nonzero(lo <= e * (1 - S / 100))[0]
    a = up[0] if len(up) else 10**9
    b = dn[0] if len(dn) else 10**9
    if b <= a and b < 10**9:
        return -S, "S"
    if a < 10**9:
        return T, "T"
    return (d["c"][i1 - 1] / e - 1) * 100, "Zeit"


def main():
    R = runden_e7()
    k1m = Kerzen("1m")
    erg = {"zellen": []}
    for S in SS:
        for T in TS:
            res = [(r, *klammer(r, k1m, T, S)) for r in R]
            for ph in ("A_Aug", "B_SepOkt", "gesamt"):
                rr = [x for x in res if ph == "gesamt" or x[0]["phase"] == ph]
                n = len(rr)
                p_t = sum(x[2] == "T" for x in rr) / n
                z = {"S": S, "T": T, "phase": ph, "n": n, "treffer_T": p_t,
                     "zeit": sum(x[2] == "Zeit" for x in rr)}
                for K in (K_BITVAVO, K_BYBIT):
                    net = [x[1] - K - ABSCHLAG_NACHSPIELUNG for x in rr]
                    p, lo, hi = block_bootstrap([x[0]["tag"] for x in rr], net, "mittel")
                    z[f"K{K:.3f}"] = {"netto_je_runde": p, "ci95": [lo, hi],
                                      "noetige_quote": (S + K + ABSCHLAG_NACHSPIELUNG) / (T + S)}
                erg["zellen"].append(z)
    speichere("a5_ziel_stopp.json", erg)
    for ph in ("A_Aug", "B_SepOkt", "gesamt"):
        print("==", ph)
        for z in erg["zellen"]:
            if z["phase"] != ph:
                continue
            k = z["K0.150"]
            print(f"  S {z['S']:4} T {z['T']:3}  T zuerst {100*z['treffer_T']:5.1f}% (noetig {100*k['noetige_quote']:5.1f}%) Zeit {z['zeit']:2} "
                  f"netto K.15 {k['netto_je_runde']:+.3f} [{k['ci95'][0]:+.2f};{k['ci95'][1]:+.2f}]  K.505 {z['K0.505']['netto_je_runde']:+.3f}")


if __name__ == "__main__":
    main()
