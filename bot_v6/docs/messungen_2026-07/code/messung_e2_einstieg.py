# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E2 Zusatz - EINSTIEGSQUALITAET UNABHAENGIG VON DER AUSSTIEGSREGEL.

Warum noetig: MFE/Trefferquote aus einem Backtest sind durch die
Ausstiegsregel abgeschnitten. Wer daraus auf "schlechter Einstieg"
schliesst, misst den Ausstieg mit. Hier wird deshalb jeder Kaufzeitpunkt
des Basislaufs genommen und der Kursverlauf DANACH ueber ein festes
Zeitfenster ausgewertet, ohne jede Ausstiegsregel.

Triple-Barrier (Lopez de Prado): von jedem Einstieg aus wird geprueft,
welche Schranke ZUERST beruehrt wird. Innerhalb einer 15m-Kerze gilt
dieselbe pessimistische Annahme wie im Harness (erst Tief, dann Hoch),
sonst waere das Rennen zugunsten der oberen Schranke verfaelscht.
"""
import sys
from harness_ext import (LaufMess, NEUE_LEITER, lade_jahr, kennzahlen,
                         median, STUNDE_MS)

FENSTER_H = (24, 72)
BARRIEREN = ((2.5, 2.5), (1.0, 2.5), (0.3, 2.5))   # (auf %, ab %)


def vorwaerts(kerzen_idx, symbol, t0, preis, stunden):
    """MFE/MAE in % ueber <stunden> nach t0, ohne Ausstiegsregel."""
    ks = kerzen_idx.get(symbol)
    if not ks or preis <= 0:
        return None, None
    t1 = t0 + stunden * STUNDE_MS
    hi_max, lo_min = None, None
    for k in ks:
        if k[0] <= t0:
            continue
        if k[0] > t1:
            break
        hi_max = k[2] if hi_max is None else max(hi_max, k[2])
        lo_min = k[3] if lo_min is None else min(lo_min, k[3])
    if hi_max is None:
        return None, None
    return (hi_max / preis - 1) * 100, (lo_min / preis - 1) * 100


def rennen(kerzen_idx, symbol, t0, preis, auf_pct, ab_pct, stunden=72):
    """Welche Schranke zuerst? 'auf' / 'ab' / 'keine'. Pessimistisch:
    innerhalb der Kerze zaehlt das Tief vor dem Hoch."""
    ks = kerzen_idx.get(symbol)
    if not ks or preis <= 0:
        return "keine"
    oben, unten = preis * (1 + auf_pct / 100), preis * (1 - ab_pct / 100)
    t1 = t0 + stunden * STUNDE_MS
    for k in ks:
        if k[0] <= t0:
            continue
        if k[0] > t1:
            break
        if k[3] <= unten:
            return "ab"
        if k[2] >= oben:
            return "auf"
    return "keine"


def main():
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        L = LaufMess(NEUE_LEITER, "basis", breakeven=True, stop_loss_pct=2.5)
        erg = L.laufe(daten, fg)
        ev = L.kauf_events

        print("\n" + "=" * 110)
        print(f" E2-ZUSATZ  Einstiegsqualitaet OHNE Ausstiegsregel  -  {jahr_bez}")
        print(f" Basislauf: {len(ev)} Kaeufe, {erg['trades']} geschlossene Positionen")
        print("=" * 110)

        for h in FENSTER_H:
            mfe, mae = [], []
            for s, t, p in ev:
                a, b = vorwaerts(idx, s, t, p, h)
                if a is not None:
                    mfe.append(a)
                    mae.append(b)
            n = len(mfe)
            if not n:
                continue
            print(f"\n  Fenster {h} h nach Einstieg  (n={n})")
            print(f"    Median MFE (bestes Hoch)      : {median(mfe):+7.2f} %")
            print(f"    Median MAE (tiefstes Tief)    : {median(mae):+7.2f} %")
            for schwelle in (0.3, 1.0, 2.5, 5.0):
                q = sum(1 for x in mfe if x >= schwelle) / n * 100
                print(f"    Anteil mit MFE >= {schwelle:4.1f} %        : {q:7.1f} %")
            for schwelle in (-2.5, -5.0):
                q = sum(1 for x in mae if x <= schwelle) / n * 100
                print(f"    Anteil mit MAE <= {schwelle:4.1f} %        : {q:7.1f} %")

        print(f"\n  Triple-Barrier-Rennen ab Einstieg (Fenster 72 h, Tief vor Hoch):")
        print(f"    {'Schranken auf/ab':<20s} {'auf zuerst':>11s} {'ab zuerst':>10s} "
              f"{'keine':>8s} | {'P(auf|entschieden)':>19s}")
        for auf, ab in BARRIEREN:
            z = {"auf": 0, "ab": 0, "keine": 0}
            for s, t, p in ev:
                z[rennen(idx, s, t, p, auf, ab, 72)] += 1
            ent = z["auf"] + z["ab"]
            print(f"    +{auf:.1f} % / -{ab:.1f} %{'':<7s} {z['auf']:11d} {z['ab']:10d} "
                  f"{z['keine']:8d} | {z['auf']/ent*100 if ent else 0:18.1f} %")
        sys.stdout.flush()

        print(f"\n  Giveback je Stop-Abstand (Median MFE der Position vs. Median realisiert):")
        print(f"    {'Variante':<15s} {'medMFE%':>8s} {'medReal%':>9s} {'Giveback%':>10s}")
        for sl in (2.0, 2.5, 3.0, 4.0, 5.0):
            Lx = LaufMess(NEUE_LEITER, "x", breakeven=True, stop_loss_pct=sl)
            e = Lx.laufe(daten, fg)
            print(f"    Stop {sl:4.1f} %{'':<4s} {e['med_mfe']:8.2f} {e['med_real']:9.2f} "
                  f"{e['giveback']:10.2f}")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
