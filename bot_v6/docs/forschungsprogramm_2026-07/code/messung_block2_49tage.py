# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Block 2 - der offene +31,44-$-Widerspruch, 03.08.2026.
"""
BLOCK 2 - Aufloesung des ungeklaerten Widerspruchs aus F1e.

FRAGE: Reibungsfrei haette der Bot im Live-Fenster (49 Tage) +31,44 $
gemacht, BTC-Halten +16,54 $. Im Zweijahres-Backtest verliert er
haushoch gegen Halten. Ist das (a) Rauschen oder (b) ein Modellfehler?

KEIN TRIAL: Es wird keine Handelsregel geprueft, sondern die Streuung
einer bereits gemessenen Groesse ueber gleich lange Fenster beschrieben.
Trial-Zaehler unveraendert.

METHODE
-------
Aus beiden Backtest-Jahren wird der unveraenderte Harness gefahren
(LaufMess, Stop 2,5 %, Breakeven, NEUE_LEITER - identisch zu E2/E5).
Fuer jeden Trade liegt aus harness_ext bereits vor:
    kosten      = tatsaechlich eingesetztes Kapital der Position
    brutto_pct  = Rendite OHNE Gebuehr und OHNE Slippage
                  (roh_ein = einstand/(1+SLIP), roh_aus = ausstieg/(1-SLIP))
Reibungsfreie P&L je Trade = kosten * brutto_pct / 100.

Rollierendes Fenster: 49 Kalendertage, Schrittweite 1 Tag. Einem Fenster
werden alle Trades zugerechnet, deren EINTRITT im Fenster liegt.
Zusaetzlich als Vergleichsmassstab: BTC-Halten ueber dasselbe Fenster,
gerechnet auf 500 $ Startkapital (wie der Bot).

ABGRENZUNG - was diese Messung NICHT kann
-----------------------------------------
Die Positionsgroesse im Harness haengt vom laufenden Eigenkapital ab.
Ein wirklich reibungsfreier Lauf haette andere Groessen und damit andere
Trades erzeugt. Diese Rechnung nimmt die Trades des Ist-Laufs und
entfernt nur die Reibung aus der Rendite. Das ist genau die Konvention,
mit der die +31,44 $ in F1e entstanden sind - der Vergleich ist also
konsistent, aber beide Zahlen teilen dieselbe Naeherung.
"""
import os
import sys
from datetime import datetime, timezone

from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, TAG_MS

FENSTER_TAGE = 49
LIVE_WERT = 31.44
LIVE_HALTEN = 16.54
START = 500.0


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def perz(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main():
    print("=" * 100)
    print(" BLOCK 2 - IST +31,44 $ UEBER 49 TAGE AUSSERGEWOEHNLICH?")
    print(" Kein Trial. Deskriptive Streuungsmessung.")
    print("=" * 100)

    alle_werte = []
    for jahr, marke in (("Jahr 2  2025-07..2026-07", ""),
                        ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        L = LaufMess(NEUE_LEITER, "block2", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)

        # reibungsfreie P&L je Trade, am Eintrittstag verbucht
        je_tag = {}
        for t in L.trades:
            tag = t["eintritt"] // TAG_MS
            je_tag.setdefault(tag, 0.0)
            je_tag[tag] += t["kosten"] * t["brutto_pct"] / 100.0

        btc = sorted(daten["BTC/USDC"])
        btc_tag = {}
        for k in btc:
            btc_tag.setdefault(k[0] // TAG_MS, k[4])

        tage = sorted(set(list(je_tag) + list(btc_tag)))
        t0, t1 = min(tage), max(tage)

        fenster, halten = [], []
        start = t0
        while start + FENSTER_TAGE <= t1:
            ende = start + FENSTER_TAGE
            s = sum(v for tg, v in je_tag.items() if start <= tg < ende)
            fenster.append(s)
            # BTC-Halten auf 500 $ ueber dasselbe Fenster
            p_a = next((btc_tag[x] for x in range(start, ende) if x in btc_tag),
                       None)
            p_e = next((btc_tag[x] for x in range(ende, start, -1)
                        if x in btc_tag), None)
            if p_a and p_e:
                halten.append(START * (p_e / p_a - 1))
            start += 1

        alle_werte.extend(fenster)
        n = len(fenster)
        drunter = sum(1 for x in fenster if x < LIVE_WERT)
        print(f"\n  {jahr}")
        print(f"    {n} rollierende 49-Tage-Fenster, {len(L.trades)} Trades")
        print(f"    reibungsfreie P&L je Fenster:")
        print(f"      Minimum   {min(fenster):+9.2f} $")
        print(f"      5.  Perz. {perz(fenster,0.05):+9.2f} $")
        print(f"      25. Perz. {perz(fenster,0.25):+9.2f} $")
        print(f"      Median    {median(fenster):+9.2f} $")
        print(f"      75. Perz. {perz(fenster,0.75):+9.2f} $")
        print(f"      95. Perz. {perz(fenster,0.95):+9.2f} $")
        print(f"      Maximum   {max(fenster):+9.2f} $")
        print(f"      Mittelwert{sum(fenster)/n:+9.2f} $")
        print(f"    Anteil Fenster mit positiver reibungsfreier P&L: "
              f"{sum(1 for x in fenster if x > 0)/n*100:.1f} %")
        print(f"    >>> LIVE-WERT +{LIVE_WERT:.2f} $ liegt im "
              f"{drunter/n*100:.1f}. Perzentil "
              f"({'INNERHALB' if min(fenster) <= LIVE_WERT <= max(fenster) else 'AUSSERHALB'} "
              f"der Spannweite)")
        if halten:
            print(f"    BTC-Halten ueber dieselben Fenster: Median "
                  f"{median(halten):+.2f} $, Spanne {min(halten):+.2f} bis "
                  f"{max(halten):+.2f} $")
            print(f"      Live-Halten-Wert +{LIVE_HALTEN:.2f} $ liegt im "
                  f"{sum(1 for x in halten if x < LIVE_HALTEN)/len(halten)*100:.1f}. "
                  f"Perzentil")
        sys.stdout.flush()

    # ---- Nachtrag: nur Fenster MIT Handelstaetigkeit ----
    print("\n" + "=" * 100)
    print(" NACHTRAG - nur Fenster MIT Trades (die Nullfenster verzerren)")
    print("=" * 100)
    print("\n  Viele Fenster enthalten gar keine Eintritte (F&G-Filter,")
    print("  in J1 nur 43 Einstiegstage). Sie stehen mit exakt 0,00 $ in der")
    print("  Verteilung und ziehen Median und Perzentile kuenstlich zur Null.")
    print("  Das Live-Fenster hatte unstrittig Handelstaetigkeit - der faire")
    print("  Vergleich ist deshalb die bedingte Verteilung.\n")
    for jahr, marke in (("Jahr 2", ""), ("Jahr 1", "_v1")):
        daten, fg = lade_jahr(marke)
        L = LaufMess(NEUE_LEITER, "b2b", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        je_tag, cnt = {}, {}
        for t in L.trades:
            tg = t["eintritt"] // TAG_MS
            je_tag[tg] = je_tag.get(tg, 0.0) + t["kosten"] * t["brutto_pct"] / 100.0
            cnt[tg] = cnt.get(tg, 0) + 1
        tage = sorted(set(list(je_tag) + [k[0] // TAG_MS
                                          for k in daten["BTC/USDC"]]))
        t0, t1 = min(tage), max(tage)
        mit = []
        start = t0
        while start + FENSTER_TAGE <= t1:
            ende = start + FENSTER_TAGE
            ntr = sum(v for tg, v in cnt.items() if start <= tg < ende)
            if ntr > 0:
                mit.append((sum(v for tg, v in je_tag.items()
                                if start <= tg < ende), ntr))
            start += 1
        if not mit:
            continue
        w = [x[0] for x in mit]
        tr = [x[1] for x in mit]
        d = sum(1 for x in w if x < LIVE_WERT)
        print(f"  {jahr}: {len(w)} Fenster mit Trades "
              f"(Median {median(tr):.0f} Trades je Fenster)")
        print(f"    Spanne {min(w):+.2f} bis {max(w):+.2f} $, "
              f"Median {median(w):+.2f} $")
        print(f"    Anteil >= +{LIVE_WERT:.2f} $: {(len(w)-d)/len(w)*100:.1f} % "
              f"-> Live-Wert im {d/len(w)*100:.1f}. Perzentil")

    n = len(alle_werte)
    drunter = sum(1 for x in alle_werte if x < LIVE_WERT)
    print("\n" + "=" * 100)
    print(" BEIDE JAHRE ZUSAMMEN")
    print("=" * 100)
    print(f"\n  {n} Fenster gesamt")
    print(f"  Spanne {min(alle_werte):+.2f} $ bis {max(alle_werte):+.2f} $")
    print(f"  Median {median(alle_werte):+.2f} $, "
          f"Mittelwert {sum(alle_werte)/n:+.2f} $")
    print(f"  Anteil Fenster >= +{LIVE_WERT:.2f} $: "
          f"{(n-drunter)/n*100:.1f} %")
    print(f"\n  >>> +{LIVE_WERT:.2f} $ liegt im {drunter/n*100:.1f}. Perzentil "
          f"der Backtest-Verteilung.")
    innen = min(alle_werte) <= LIVE_WERT <= max(alle_werte)
    print(f"  >>> {'INNERHALB' if innen else 'AUSSERHALB'} der Spannweite.")
    print(f"\n  URTEIL: " + (
        "Erklaerung (a) traegt - 49 Tage sind Rauschen. Der Live-Wert liegt "
        "\n          bequem in der Streuung gleich langer Backtest-Fenster."
        if innen and 5 <= drunter / n * 100 <= 95 else
        "Erklaerung (a) traegt NICHT allein - der Live-Wert liegt am Rand "
        "\n          oder ausserhalb. Modellunterschiede pruefen."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
