# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E2 - Stop-Abstand gegen Einstiegsqualitaet.

Variiert AUSSCHLIESSLICH den Stop-Abstand. Alles andere (Einstiege, Trailing,
Breakeven, Nachkauf, Sperre, Gebuehren, Slippage) bleibt wie im Harness.
Beide Jahre getrennt.

SPALTEN-KENNZEICHNUNG
  [V]  vergleichbar zwischen Varianten (Verhaeltnis-/Ereigniszahlen)
  [!]  NICHT auf Live uebertragbar (absolute $-Betraege; der Harness hat
       eine um Faktor ~8 zu niedrige Nachkaufrate, siehe E1)
"""
import sys
from harness_ext import (LaufMess, NEUE_LEITER, lade_jahr, atr_1h_ohne_lookahead,
                         kennzahlen, stop_anteil_am_verlust, rueckkehr_nach_stop,
                         kapitalbindung, median, COINS)
from backtest.ausstieg_backtest import Lauf

VARIANTEN = [
    ("Stop 2,0 %",     dict(stop_loss_pct=2.0, stop_mode="pct")),
    ("Stop 2,5 % IST", dict(stop_loss_pct=2.5, stop_mode="pct")),
    ("Stop 3,0 %",     dict(stop_loss_pct=3.0, stop_mode="pct")),
    ("Stop 4,0 %",     dict(stop_loss_pct=4.0, stop_mode="pct")),
    ("Stop 5,0 %",     dict(stop_loss_pct=5.0, stop_mode="pct")),
    ("ATR(14,1h) 1,5x", dict(stop_loss_pct=2.5, stop_mode="atr", atr_mult=1.5)),
    ("ATR(14,1h) 2,0x", dict(stop_loss_pct=2.5, stop_mode="atr", atr_mult=2.0)),
]

JAHRE = [("Jahr 2  2025-07..2026-07", ""), ("Jahr 1  2024-07..2025-07", "_v1")]


def kontrolle(daten, fg):
    """Beweis, dass LaufMess bei stop_mode='pct' identisch zum Original ist."""
    o = Lauf(NEUE_LEITER, "orig", breakeven=True)
    o.laufe(daten, fg)
    m = LaufMess(NEUE_LEITER, "mess", breakeven=True, stop_mode="pct")
    m.laufe(daten, fg)
    gleich = (len(o.trades) == len(m.trades)
              and abs(sum(t["pnl"] for t in o.trades)
                      - sum(t["pnl"] for t in m.trades)) < 1e-9)
    print(f"KONTROLLE Original vs. Instrumentierung: Trades {len(o.trades)} / "
          f"{len(m.trades)}, Summe {sum(t['pnl'] for t in o.trades):+.4f} / "
          f"{sum(t['pnl'] for t in m.trades):+.4f}  ->  "
          f"{'IDENTISCH' if gleich else 'ABWEICHUNG !!!'}")
    return gleich


def main():
    for jahr_bez, marke in JAHRE:
        daten, fg = lade_jahr(marke)
        atr_tab = {s: atr_1h_ohne_lookahead(ks) for s, ks in daten.items()}
        print("\n" + "=" * 132)
        print(f" E2  {jahr_bez}   ({len(daten)} Coins)")
        print("=" * 132)
        if marke == "":
            kontrolle(daten, fg)
        print(f"  {'Variante':<17s} {'Stop~':>6s} {'Trad':>5s} {'WR%':>5s} "
              f"{'R/R':>5s} {'BE-RR':>6s} {'EV(R)':>6s} | {'NettoP&L$':>10s} "
              f"{'EV$/Tr':>7s} | {'Stop%Tr':>7s} {'Stop%Verl':>9s} | "
              f"{'24h-zurueck':>11s} | {'Halt_h':>7s} {'Bind%':>6s} {'OffPos':>6s}")
        print("  " + "-" * 128)
        print(f"  {'':<17s} {'[V]':>6s} {'[V]':>5s} {'[V]':>5s} {'[V]':>5s} "
              f"{'[V]':>6s} {'[V]':>6s} | {'[!]':>10s} {'[!]':>7s} | "
              f"{'[V]':>7s} {'[V]':>9s} | {'[V]':>11s} | {'[V]':>7s} {'[V]':>6s} {'[V]':>6s}")
        print("  " + "-" * 128)

        for bez, kw in VARIANTEN:
            L = LaufMess(NEUE_LEITER, bez, breakeven=True, atr_tab=atr_tab, **kw)
            L.laufe(daten, fg)
            k = kennzahlen(L.trades)
            s_tr, s_verl, verl_ges, stop_verl = stop_anteil_am_verlust(L.trades)
            n_stop, zurueck, z_pct = rueckkehr_nach_stop(L.trades, daten, 24)
            bind, offpos = kapitalbindung(L)
            stop_med = median(L.stop_pcts)
            be = k["be_rr"]
            print(f"  {bez:<17s} {stop_med:6.2f} {k['n']:5d} {k['wr']:5.1f} "
                  f"{k['rr']:5.2f} {be:6.2f} {k['ev_r']:+6.3f} | {k['summe']:+10.2f} "
                  f"{k['ev']:+7.3f} | {s_tr:7.1f} {s_verl:9.1f} | "
                  f"{zurueck:4d}/{n_stop:<4d}{z_pct:4.0f}% | {k['halte']:7.1f} "
                  f"{bind:6.1f} {offpos:6.2f}")
            if kw["stop_mode"] == "atr":
                q = sorted(L.stop_pcts)
                print(f"  {'':<17s} ATR-Stops: p10={q[len(q)//10]:.2f}% "
                      f"p50={stop_med:.2f}% p90={q[len(q)*9//10]:.2f}% "
                      f"| Fallback-Kaeufe ohne ATR: {L.atr_fallback}")
            sys.stdout.flush()

        # Verlust-Umverteilung: wohin wandert der Verlust?
        print("\n  Verlust-Zerlegung nach Ausstiegsgrund (Summe der NEGATIVEN Trades, $ [!]):")
        print(f"  {'Variante':<17s} {'VerlustGes':>11s} {'STOP_LOSS':>11s} "
              f"{'TRAILING':>11s} {'BREAKEVEN':>11s} | {'GewinnGes':>11s}")
        for bez, kw in VARIANTEN:
            L = LaufMess(NEUE_LEITER, bez, breakeven=True, atr_tab=atr_tab, **kw)
            L.laufe(daten, fg)
            neg = {}
            for t in L.trades:
                if t["pnl"] <= 0:
                    neg[t["grund"]] = neg.get(t["grund"], 0.0) + t["pnl"]
            gew = sum(t["pnl"] for t in L.trades if t["pnl"] > 0)
            print(f"  {bez:<17s} {sum(neg.values()):+11.2f} "
                  f"{neg.get('STOP_LOSS', 0.0):+11.2f} {neg.get('TRAILING', 0.0):+11.2f} "
                  f"{neg.get('BREAKEVEN', 0.0):+11.2f} | {gew:+11.2f}")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
