# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · V1-Beleg: Was aendert die Regime-Skalierung (wirksam 2,12/0,85 gegen nominal 2,5/1,0) in Geld?
Gepaarte Tagesdifferenz nominal minus ist, je Regelwerk E7 und Bitvavo, mit Kapitalbindung und Abschlag.
"""
from __future__ import annotations

import json

from a5_basis import K_BITVAVO, K_BYBIT, Kerzen, runden_e7, speichere
from a5_motor import Regel, RSIStunde, spiele_alle
from a5_nachspielung import PHASEN, gepaart


def main():
    R = runden_e7()
    k1m, k1h = Kerzen("1m"), Kerzen("1h")
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    paare = {
        "E7": (Regel("n", sl=2.5, start=1.2, trail=1.0, be_ab=1.0, puffer=0.35),
               Regel("i", sl=2.12, start=1.2, trail=0.85, be_ab=1.0, puffer=0.35)),
        "Bitvavo": (Regel("n", sl=2.5, start=1.21, trail=1.0, be_ab=1.0, puffer=0.195),
                    Regel("i", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195)),
    }
    erg = {}
    for name, (pn, pi) in paare.items():
        zn, zi = spiele_alle(R, pn, k1m, rsis), spiele_alle(R, pi, k1m, rsis)
        erg[name] = {ph: {f"K{K:.3f}": gepaart(zn, zi, a, b, K, 0.05 / 6) for K in (K_BITVAVO, K_BYBIT)}
                     for ph, (a, b) in PHASEN.items()}
    speichere("a5_nominal_gegen_ist.json", erg)
    for name, e in erg.items():
        for ph, x in e.items():
            g = x["K0.150"]
            print(f"{name:8} {ph:9} nominal-ist K.150 {g['diff_usd']:+7.2f} [{g['ci95'][0]:+.1f};{g['ci95'][1]:+.1f}]  K.505 {x['K0.505']['diff_usd']:+7.2f} [{x['K0.505']['ci95'][0]:+.1f};{x['K0.505']['ci95'][1]:+.1f}]")


if __name__ == "__main__":
    main()
