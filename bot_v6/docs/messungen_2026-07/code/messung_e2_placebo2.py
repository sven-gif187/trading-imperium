# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E2 Placebo II - waehlt der F&G-Einstieg eine RICHTUNG oder nur VOLATILITAET?

Placebo I zeigte: MFE ueber Zufallsniveau, symmetrisches Barrierenrennen
aber auf Zufallsniveau. Beides zusammen ist nur widerspruchsfrei, wenn auch
die Abwaertsseite (MAE) ueber Zufallsniveau liegt. Genau das wird hier
gemessen statt gefolgert.

Schnell durch Vorab-Praefixe: statt je Einstieg die Kerzenliste von vorn zu
durchlaufen, wird per bisect eingestiegen und ein Sliding-Window-Maximum
ueber ein FESTES Fenster (96 bzw. 288 Kerzen) gebildet.
"""
import bisect
import random
import sys
from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, median

ZIEHUNGEN = 20
SEED = 20260730
FENSTER = ((24, 96), (72, 288))


def mfe_mae(ks, zeiten, t0, preis, n_kerzen):
    i = bisect.bisect_right(zeiten, t0)
    j = min(i + n_kerzen, len(ks))
    if i >= j or preis <= 0:
        return None, None
    hi = max(ks[x][2] for x in range(i, j))
    lo = min(ks[x][3] for x in range(i, j))
    return (hi / preis - 1) * 100, (lo / preis - 1) * 100


def auswerten(idx, zeiten_idx, events, n_kerzen):
    mfe, mae = [], []
    for s, t, p in events:
        ks = idx.get(s)
        if not ks:
            continue
        a, b = mfe_mae(ks, zeiten_idx[s], t, p, n_kerzen)
        if a is not None:
            mfe.append(a)
            mae.append(b)
    n = len(mfe) or 1
    return {
        "n": len(mfe),
        "medMFE": median(mfe), "medMAE": median(mae),
        "MFE>=2.5": sum(1 for x in mfe if x >= 2.5) / n * 100,
        "MAE<=-2.5": sum(1 for x in mae if x <= -2.5) / n * 100,
        "MFE>=5": sum(1 for x in mfe if x >= 5.0) / n * 100,
        "MAE<=-5": sum(1 for x in mae if x <= -5.0) / n * 100,
    }


def main():
    rnd = random.Random(SEED)
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        zeiten_idx = {s: [k[0] for k in ks] for s, ks in idx.items()}
        L = LaufMess(NEUE_LEITER, "basis", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        echt = L.kauf_events
        je_coin = {}
        for s, t, p in echt:
            je_coin[s] = je_coin.get(s, 0) + 1

        zieh = []
        for _ in range(ZIEHUNGEN):
            ev = []
            for s, anzahl in je_coin.items():
                ks = idx[s]
                grenze = len(ks) - 289
                if grenze <= 1:
                    continue
                for _i in range(anzahl):
                    k = ks[rnd.randrange(grenze)]
                    ev.append((s, k[0], k[4]))
            zieh.append(ev)

        print("\n" + "=" * 104)
        print(f" E2-PLACEBO II  Richtung oder Volatilitaet?  -  {jahr_bez}")
        print(f" {len(echt)} echte Kaeufe gegen {ZIEHUNGEN} Zufallsziehungen, Seed {SEED}")
        print("=" * 104)
        for h, nk in FENSTER:
            e = auswerten(idx, zeiten_idx, echt, nk)
            zs = [auswerten(idx, zeiten_idx, ev, nk) for ev in zieh]
            print(f"\n  Fenster {h} h   (echt n={e['n']})")
            print(f"    {'Mass':<14s} {'ECHT':>8s} | {'Zufall Mit':>10s} {'min':>7s} "
                  f"{'max':>7s} | {'Urteil':>18s}")
            for key in ("medMFE", "medMAE", "MFE>=2.5", "MAE<=-2.5", "MFE>=5", "MAE<=-5"):
                w = [z[key] for z in zs]
                m = sum(w) / len(w)
                drin = min(w) <= e[key] <= max(w)
                print(f"    {key:<14s} {e[key]:8.2f} | {m:10.2f} {min(w):7.2f} "
                      f"{max(w):7.2f} | {'in Streuung' if drin else 'AUSSERHALB':>18s}")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
