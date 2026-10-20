# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E2 Placebo - hat der F&G-Einstieg ueberhaupt einen Vorteil gegenueber
einem ZUFAELLIGEN Einstieg in dieselben Coins?

Die Barriere-Quoten aus e2_einstieg.py (89,9 % bei +0,3/-2,5) sehen nach
Geometrie aus, nicht nach Signal: bei einem driftfreien Random Walk trifft
der Kurs die obere Schranke mit Wahrscheinlichkeit ab/(auf+ab).
    +0,3/-2,5 -> 89,3 %   +1,0/-2,5 -> 71,4 %   +2,5/-2,5 -> 50,0 %

Statt diese Formel zu zitieren wird hier gemessen: dieselbe Zahl Einstiege
je Coin, aber zu gleichverteilt gezogenen Zeitpunkten (mehrere Ziehungen,
fester Seed). Liegt das echte Signal innerhalb der Streuung der Ziehungen,
hat der Einstieg keinen messbaren Vorteil.
"""
import random
import sys
from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, median, STUNDE_MS
from messung_e2_einstieg import rennen, vorwaerts

ZIEHUNGEN = 20
SEED = 20260730
BARRIEREN = ((2.5, 2.5), (1.0, 2.5), (0.3, 2.5))


def quoten(idx, events, auf, ab, stunden=72):
    z = {"auf": 0, "ab": 0, "keine": 0}
    for s, t, p in events:
        z[rennen(idx, s, t, p, auf, ab, stunden)] += 1
    ent = z["auf"] + z["ab"]
    return z["auf"] / ent * 100 if ent else 0.0


def mfe_quote(idx, events, schwelle, stunden=24):
    tref, n = 0, 0
    for s, t, p in events:
        a, _b = vorwaerts(idx, s, t, p, stunden)
        if a is None:
            continue
        n += 1
        if a >= schwelle:
            tref += 1
    return tref / n * 100 if n else 0.0


def main():
    rnd = random.Random(SEED)
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        L = LaufMess(NEUE_LEITER, "basis", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        echt = L.kauf_events
        je_coin = {}
        for s, t, p in echt:
            je_coin[s] = je_coin.get(s, 0) + 1

        print("\n" + "=" * 112)
        print(f" E2-PLACEBO  echter F&G-Einstieg gegen Zufallseinstieg  -  {jahr_bez}")
        print(f" {len(echt)} echte Kaeufe, {ZIEHUNGEN} Zufallsziehungen gleicher "
              f"Groesse je Coin, Seed {SEED}")
        print("=" * 112)

        # Zufallsziehungen vorbereiten (nur Kerzen, die 72h Vorlauf lassen)
        zieh = []
        for _ in range(ZIEHUNGEN):
            ev = []
            for s, anzahl in je_coin.items():
                ks = idx[s]
                obergrenze = len(ks) - 289          # 72h = 288 Kerzen
                if obergrenze <= 1:
                    continue
                for _i in range(anzahl):
                    k = ks[rnd.randrange(obergrenze)]
                    ev.append((s, k[0], k[4]))
            zieh.append(ev)

        print(f"  {'Mass':<26s} {'ECHT':>8s} | {'Zufall Mittel':>13s} "
              f"{'min':>7s} {'max':>7s} | {'Urteil':>22s}")
        print("  " + "-" * 100)

        for auf, ab in BARRIEREN:
            e = quoten(idx, echt, auf, ab)
            zs = [quoten(idx, ev, auf, ab) for ev in zieh]
            m = sum(zs) / len(zs)
            drin = min(zs) <= e <= max(zs)
            print(f"  {'P(auf) ' + f'+{auf}/-{ab} %':<26s} {e:8.1f} | {m:13.1f} "
                  f"{min(zs):7.1f} {max(zs):7.1f} | "
                  f"{'in Zufallsstreuung' if drin else 'AUSSERHALB':>22s}")
            sys.stdout.flush()

        for schwelle in (0.3, 1.0, 2.5):
            e = mfe_quote(idx, echt, schwelle)
            zs = [mfe_quote(idx, ev, schwelle) for ev in zieh]
            m = sum(zs) / len(zs)
            drin = min(zs) <= e <= max(zs)
            print(f"  {'MFE24h >= ' + f'{schwelle} %':<26s} {e:8.1f} | {m:13.1f} "
                  f"{min(zs):7.1f} {max(zs):7.1f} | "
                  f"{'in Zufallsstreuung' if drin else 'AUSSERHALB':>22s}")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
