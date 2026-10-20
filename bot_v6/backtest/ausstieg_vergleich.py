# -*- coding: utf-8 -*-
"""
backtest/ausstieg_vergleich.py - Alt gegen Neu, dann Parametersuche  [E11 29.07.2026]
=====================================================================================
    python backtest/ausstieg_vergleich.py              # Alt gegen Neu
    python backtest/ausstieg_vergleich.py --suche      # + Parametersuche mit Walk-Forward

WARUM WALK-FORWARD
------------------
Eine Parametersuche findet IMMER etwas. Bei 60 Kombinationen ueber
denselben Datensatz ist die beste davon zu einem guten Teil Zufall -
sie hat die Eigenheiten genau dieser Kurshistorie auswendig gelernt.
Wer so ein Ergebnis live schaltet, handelt die Vergangenheit.

Deshalb wird der Zeitraum geteilt: auf dem ersten Teil (Training) wird
gesucht, auf dem zweiten (Test) wird das Gefundene EINMAL geprueft.
Nur was auf ungesehenen Daten haelt, zaehlt. Faellt das Testergebnis
deutlich hinter das Trainingsergebnis zurueck, war es Anpassung an
Rauschen - dann bleibt die einfachere Regel stehen.
"""
import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.ausstieg_backtest import (
    Lauf, ALTE_LEITER, NEUE_LEITER, lade_kerzen, lade_fear_greed, DATEN)
from risk import exit_rules

COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "AVAX/USDC",
         "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC", "UNI/USDC",
         "ATOM/USDC"]


def lade_alles(von_ms=None, bis_ms=None):
    daten, fehlend = {}, []
    for c in COINS:
        k = lade_kerzen(c)
        if not k:
            fehlend.append(c)
            continue
        if von_ms or bis_ms:
            k = [x for x in k
                 if (von_ms is None or x[0] >= von_ms) and (bis_ms is None or x[0] < bis_ms)]
        if k:
            daten[c] = k
    return daten, fehlend, lade_fear_greed()


def zeile(e):
    return (f"  {e['name']:<26s} {e['trades']:5d} {e['summe']:+9.2f}  "
            f"{e['mittel']:+7.4f}  {e['wr']:5.1f}  {e['rr']:5.2f}  "
            f"{e['profitfaktor']:5.2f}  {e['drawdown']:6.2f}  "
            f"{e['med_real']:+6.2f}  {e['giveback']:5.2f}  {e['groesster_gewinn']:+6.2f}")


def kopf():
    print(f"  {'Regel':<26s} {'Trades':>5s} {'Summe':>9s}  {'Mittel':>7s}  "
          f"{'WR%':>5s}  {'R/R':>5s}  {'PF':>5s}  {'MaxDD':>6s}  "
          f"{'Med%':>6s}  {'GBack':>5s}  {'Best%':>6s}")
    print("  " + "-" * 108)


def baue(leiter_fn, name, **kw):
    return Lauf(leiter_fn, name, **kw)


def vergleich_alt_neu(daten, fg):
    print("\n" + "=" * 112)
    print(" ALTE LEITER GEGEN NEUE RATSCHE - identische Kerzen, identische Einstiege")
    print("=" * 112)
    kopf()
    ergebnisse = []
    for fn, name, be in ((ALTE_LEITER, "ALT (inverse Leiter)", False),
                         (NEUE_LEITER, "NEU (Ratsche + BE)", True)):
        e = baue(fn, name, breakeven=be).laufe(daten, fg)
        ergebnisse.append(e)
        print(zeile(e))
    # Zwischenform: Ratsche ohne Breakeven-Sperre - trennt die beiden Effekte
    e = baue(NEUE_LEITER, "NEU ohne Breakeven", breakeven=False).laufe(daten, fg)
    ergebnisse.append(e)
    print(zeile(e))
    print("\n  Ausstiegsgruende:")
    for e in ergebnisse:
        print(f"    {e['name']:<26s} {e['gruende']}")
    return ergebnisse


# ---------------------------------------------------------------------------
# Parametersuche
# ---------------------------------------------------------------------------
def mit_leiter(leiter, trail_ab, be_ab, be_puffer):
    """Erzeugt eine Ausstiegsfunktion mit abweichenden Parametern."""
    def fn(pnl_pct, hoechst_pnl_pct, trail_pct, regime):
        return exit_rules.effektiver_trail(hoechst_pnl_pct, trail_pct, regime,
                                           trail_ab_pct=trail_ab)
    fn._leiter = leiter
    return fn


def suche(daten, fg, trainings_anteil=0.6):
    zeiten = sorted({k[0] for ks in daten.values() for k in ks})
    grenze = zeiten[int(len(zeiten) * trainings_anteil)]
    d_tr = {s: [k for k in ks if k[0] < grenze] for s, ks in daten.items()}
    d_te = {s: [k for k in ks if k[0] >= grenze] for s, ks in daten.items()}
    v = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    print("\n" + "=" * 112)
    print(" PARAMETERSUCHE MIT WALK-FORWARD")
    print(f" Training: {v(zeiten[0])} .. {v(grenze)}   |   Test: {v(grenze)} .. {v(zeiten[-1])}")
    print("=" * 112)

    original = exit_rules.LEITER
    kandidaten = []
    # Leitern: von "flach wie alt" bis "sehr weit"
    leitern = {
        "alt-artig 1.0/0.7/0.5": ((1.2, 1.0), (3.0, 0.7), (5.0, 0.5)),
        "flach 1.0":             ((1.2, 1.0),),
        "sanft 1.0/1.15/1.3":    ((1.2, 1.0), (3.0, 1.15), (5.0, 1.3)),
        "aktuell 1.0/1.3/1.7":   ((1.2, 1.0), (3.0, 1.3), (5.0, 1.7), (8.0, 2.2)),
        "weit 1.2/1.8/2.5":      ((1.2, 1.2), (3.0, 1.8), (5.0, 2.5), (8.0, 3.0)),
        "sehr weit 1.5/2.5/3.5": ((1.2, 1.5), (3.0, 2.5), (5.0, 3.5), (8.0, 4.5)),
    }
    for lname, leiter in leitern.items():
        for trail_ab in (0.8, 1.2, 2.0):
            for be in (None, (1.0, 0.25), (1.5, 0.5)):
                kandidaten.append((lname, leiter, trail_ab, be))

    def fahre(kand, d):
        lname, leiter, trail_ab, be = kand
        exit_rules.LEITER = leiter
        if be:
            exit_rules.BREAKEVEN_AB_PCT, exit_rules.BREAKEVEN_PUFFER_PCT = be
        fn = lambda p, h, t, r: exit_rules.effektiver_trail(h, t, r, trail_ab_pct=trail_ab)
        return Lauf(fn, "x", breakeven=bool(be)).laufe(d, fg)

    print(f"\n  {len(kandidaten)} Kombinationen auf dem TRAININGS-Zeitraum ...\n")
    tr = []
    for i, k in enumerate(kandidaten):
        e = fahre(k, d_tr)
        tr.append((e["summe"], e, k))
        sys.stdout.write(f"\r    {i+1}/{len(kandidaten)}")
        sys.stdout.flush()
    exit_rules.LEITER = original
    tr.sort(key=lambda x: -x[0])

    print("\n\n  Beste 8 im TRAINING:")
    print(f"  {'#':>2s}  {'Leiter':<24s} {'TrailAb':>7s} {'Breakeven':>10s} "
          f"{'Trades':>6s} {'Summe':>9s} {'R/R':>5s} {'MaxDD':>6s}")
    print("  " + "-" * 84)
    for i, (s, e, k) in enumerate(tr[:8]):
        lname, _, ta, be = k
        print(f"  {i+1:2d}  {lname:<24s} {ta:7.1f} "
              f"{('aus' if not be else f'{be[0]}/{be[1]}'):>10s} "
              f"{e['trades']:6d} {s:+9.2f} {e['rr']:5.2f} {e['drawdown']:6.2f}")

    print("\n  Dieselben 8 auf dem UNGESEHENEN TEST-Zeitraum:")
    print(f"  {'#':>2s}  {'Leiter':<24s} {'TrailAb':>7s} {'Breakeven':>10s} "
          f"{'Trades':>6s} {'Summe':>9s} {'R/R':>5s} {'MaxDD':>6s}")
    print("  " + "-" * 84)
    te = []
    for i, (s, _e, k) in enumerate(tr[:8]):
        e = fahre(k, d_te)
        te.append((e["summe"], e, k))
        lname, _, ta, be = k
        print(f"  {i+1:2d}  {lname:<24s} {ta:7.1f} "
              f"{('aus' if not be else f'{be[0]}/{be[1]}'):>10s} "
              f"{e['trades']:6d} {e['summe']:+9.2f} {e['rr']:5.2f} {e['drawdown']:6.2f}")
    exit_rules.LEITER = original

    # Referenz: die aktuell eingebaute Regel auf demselben Test-Zeitraum
    ist = Lauf(NEUE_LEITER, "aktuell eingebaut", breakeven=True).laufe(d_te, fg)
    alt = Lauf(ALTE_LEITER, "alt", breakeven=False).laufe(d_te, fg)
    print(f"\n  Referenz auf demselben Test-Zeitraum:")
    print(f"      aktuell eingebaut  {ist['trades']:6d} {ist['summe']:+9.2f} "
          f"{ist['rr']:5.2f} {ist['drawdown']:6.2f}")
    print(f"      alte Leiter        {alt['trades']:6d} {alt['summe']:+9.2f} "
          f"{alt['rr']:5.2f} {alt['drawdown']:6.2f}")
    return tr, te, ist, alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suche", action="store_true")
    a = ap.parse_args()

    daten, fehlend, fg = lade_alles()
    if not daten:
        print(f"Keine Kerzen in {DATEN}. Erst laufen lassen:")
        print("  python backtest/daten_holen.py")
        return 1
    zeiten = sorted({k[0] for ks in daten.values() for k in ks})
    v = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    print(f"Daten: {len(daten)} Coins, {len(zeiten)} Zeitpunkte, "
          f"{v(zeiten[0])} .. {v(zeiten[-1])}, F&G {len(fg)} Tage")
    if fehlend:
        print(f"Fehlend: {', '.join(fehlend)}")

    vergleich_alt_neu(daten, fg)
    if a.suche:
        suche(daten, fg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
