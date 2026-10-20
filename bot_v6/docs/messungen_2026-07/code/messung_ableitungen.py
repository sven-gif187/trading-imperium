# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
Abgeleitete Kennzahlen, damit im Bericht keine Kopfrechnung als Messung auftritt.

1) E2b - Umverteilung des Verlusts: Zahl der Stop-Ausstiege und mittlerer
   Verlust JE Stop-Ausstieg, je Stop-Abstand. Antwortet auf die Frage, ob
   ein weiterer Stop den Verlust verschiebt oder nur umpackt.
2) E5d - effektive Zahl unabhaengiger Positionen bei gemessener
   Durchschnittskorrelation: N_eff = N / (1 + (N-1)*rho).
"""
import sys
from harness_ext import (LaufMess, NEUE_LEITER, lade_jahr, atr_1h_ohne_lookahead,
                         kennzahlen, stop_anteil_am_verlust)

STOPS = (2.0, 2.5, 3.0, 4.0, 5.0)


def main():
    print("=" * 104)
    print(" E2b  Verlust-Umverteilung: weniger Stops, aber groessere - Netto-Wirkung?")
    print("=" * 104)
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        print(f"\n  {jahr_bez}")
        print(f"    {'Stop':<8s} {'nStops':>7s} {'SummeStopVerl$':>15s} "
              f"{'je Stop$':>9s} {'nStops rel':>11s} {'jeStop rel':>11s} "
              f"{'EV(R)':>8s} {'dEV(R) vs 2,0%':>15s}")
        basis_ev = None
        basis_n = basis_je = None
        for sl in STOPS:
            L = LaufMess(NEUE_LEITER, "x", breakeven=True, stop_loss_pct=sl)
            L.laufe(daten, fg)
            k = kennzahlen(L.trades)
            stop_tr = [t for t in L.trades if t["grund"] == "STOP_LOSS" and t["pnl"] <= 0]
            n = len(stop_tr)
            s = sum(t["pnl"] for t in stop_tr)
            je = s / n if n else 0.0
            if basis_ev is None:
                basis_ev, basis_n, basis_je = k["ev_r"], n, je
            print(f"    {sl:5.1f} % {n:7d} {s:15.2f} {je:9.3f} "
                  f"{n/basis_n:10.2f}x {je/basis_je:10.2f}x "
                  f"{k['ev_r']:+8.3f} {k['ev_r']-basis_ev:+15.3f}")
            sys.stdout.flush()

    print("\n" + "=" * 104)
    print(" E5d  Effektive Zahl unabhaengiger Positionen  N_eff = N / (1 + (N-1)*rho)")
    print("=" * 104)
    messungen = [
        ("Jahr 2  alle Tage",          11, 0.753),
        ("Jahr 2  BTC unter 50T-SMA",  11, 0.755),
        ("Jahr 2  BTC ueber 50T-SMA",  11, 0.728),
        ("Jahr 1  alle Tage",          11, 0.721),
        ("Jahr 1  BTC unter 50T-SMA",  11, 0.796),
        ("Jahr 1  BTC ueber 50T-SMA",  11, 0.674),
    ]
    print(f"    {'Teilmenge':<28s} {'N':>3s} {'rho':>6s} {'N_eff':>7s}")
    for bez, N, rho in messungen:
        print(f"    {bez:<28s} {N:3d} {rho:6.3f} {N/(1+(N-1)*rho):7.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
