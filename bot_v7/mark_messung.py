# -*- coding: utf-8 -*-
"""mark_messung.py - halten Marks Fibonacci-Stufen, oder halten sie nicht?

DIE FRAGE
---------
`features/chartanalyse.py` baut Marks Verfahren nach: Fibonacci ueber die
Extreme des sichtbaren Fensters, neun Stufen einschliesslich der zwei
Wurzelverhaeltnisse 0,707 und 0,866. Dass die FORMEL stimmt, ist belegt -
`mark_gegenprobe.py` trifft 16 von ihm selbst beschriftete Stufen aus zwei
Maerkten auf den Cent.

Offen ist etwas anderes: Dreht der Kurs an diesen Stufen HAEUFIGER, als er
an einer beliebigen Linie im selben Abstand dreht?

WARUM DIE VORGAENGERMESSUNG NICHTS TAUGTE
------------------------------------------
`konfluenz_messung.py` (11.09.) sagte "kein Effekt". Das Urteil war wertlos,
aus zwei Gruenden, die beide erst beim Nachlesen von prognosen/MARK.md
auffielen:

1. **Sie benutzte diesen Code gar nicht**, sondern einen eigenen Nachbau -
   mit vier Stufen (`konfluenz_messung.py:59`) statt neun. Ausgerechnet
   0,707 und 0,866 fehlten, also genau die zwei, die Marks Verfahren
   ausmachen. Denselben Fehler hatte schon Befund 83 gemacht.

2. **Die Zufallslatte lag woanders als die echten Zonen.** Sie streute ueber
   plus/minus 4 %, die Fibonacci-Stufen lagen viel naeher am Kurs
   (727 Beruehrungen gegen 264). Verglichen wurde nah gegen fern, nicht
   Stufe gegen Zufall.

Beide Fehler sind hier vermieden: gerechnet wird mit `fibonacci_ziele()`
selbst, und die Zufallslinie wird auf DENSELBEN Abstand vom damaligen Kurs
gesetzt wie die Stufe, gegen die sie antritt.

WAS "HAELT" HEISST - und was es NICHT heisst
--------------------------------------------
Ein Kurs, der weiterfaellt, hat auch eine Schwankungsbreite. Die erste
Fassung der Vorgaengermessung nannte Hoch minus Tief im Fenster "gedreht" -
das war die Spanne, nicht die Umkehr. Deshalb hier scharf definiert:

  BERUEHRT   Das Tief einer Kerze erreicht die Stufe (von oben kommend).
  GEHALTEN   Danach steigt der Kurs innerhalb von FENSTER Kerzen um
             UMKEHR Prozent ueber die Stufe, OHNE vorher DURCHBRUCH
             Prozent darunter zu fallen.

Erst reagiert, dann gedreht. Wer nur "beruehrt" zaehlt, misst, wo der Kurs
war, nicht was er tat.

KAUSALITAET
-----------
`fibonacci_ziele()` bekommt in jedem Schritt nur Wendepunkte, die zu diesem
Zeitpunkt schon BESTAETIGT waren (`swing_punkte` gibt `bestaetigt_ab` mit).
Eine Stufe, deren Anker erst drei Kerzen spaeter erkennbar war, kann hier
nicht auftauchen.

AENDERT NICHTS. Liest gespeicherte Kerzen und rechnet.

    python mark_messung.py
"""
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd                                        # noqa: E402
from features.chartanalyse import swing_punkte, fibonacci_ziele   # noqa: E402

ORD = os.path.join(os.environ.get("TEMP", "."), "claude",
                   "C--Users-sven7-Desktop-trading-imperium-v6-21-",
                   "efb0dd76-0fbc-46d7-b8ff-7c7f12f375a5", "scratchpad")

MUENZEN = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
SICHT = 150            # Kerzen, die "im Bild" sind - Ankerfenster
SCHRITT = 8            # nur jede achte Kerze pruefen (Rechenzeit)
NAEHE = 0.10           # Prozent - so nah muss das Tief an die Stufe
FENSTER = 16           # Kerzen, in denen die Umkehr passieren muss
UMKEHR = 1.0           # Prozent ueber der Stufe = gehalten
DURCHBRUCH = 0.5       # Prozent darunter = nicht gehalten
VORLAUF = 200          # Kerzen Anlauf, bevor gemessen wird
random.seed(20260912)


def lade(sym):
    p = os.path.join(ORD, "kerzen_%s.json" % sym)
    if not os.path.exists(p):
        return None
    k = json.load(io.open(p, encoding="utf-8"))
    return pd.DataFrame({
        "High": [float(x[2]) for x in k],
        "Low": [float(x[3]) for x in k],
        "Close": [float(x[4]) for x in k],
    })


def haelt(df, i, linie):
    """Beruehrt der Kurs die Linie, und haelt sie dann?

    Rueckgabe: None = nie beruehrt, True = gehalten, False = durchbrochen.
    """
    lows = df["Low"].values
    highs = df["High"].values
    n = len(df)
    for j in range(i + 1, min(i + 1 + FENSTER, n)):
        # Beruehrung: Tief kommt bis auf NAEHE an die Linie heran
        if lows[j] <= linie * (1 + NAEHE / 100.0):
            # ab hier vorwaerts: erst UMKEHR oder erst DURCHBRUCH?
            for m in range(j, min(j + FENSTER, n)):
                if lows[m] <= linie * (1 - DURCHBRUCH / 100.0):
                    return False
                if highs[m] >= linie * (1 + UMKEHR / 100.0):
                    return True
            return False          # weder noch bis Fensterende
    return None


def messe(df, sym):
    treffer_echt = [0, 0]        # [gehalten, gesamt]
    treffer_zufall = [0, 0]
    abstaende = []

    hochs, tiefs = swing_punkte(df, weite=3)
    n = len(df)
    i = VORLAUF
    while i < n - 2 * FENSTER - 1:
        fib = fibonacci_ziele(df, hochs, tiefs, i, mit_vor=False,
                              rueckblick=SICHT)
        if fib and fib.get("stufen"):
            kurs = float(df["Close"].values[i])
            for verhaeltnis, preis, art in fib["stufen"]:
                if art == "anker":
                    continue                      # 0 und 1 sind die Anker selbst
                if preis <= 0 or preis >= kurs:
                    continue                      # nur Stufen UNTER dem Kurs
                abstand = (kurs - preis) / kurs   # relativ, fuer die Latte
                if abstand > 0.10:
                    continue                      # ueber 10 % weg: unerreichbar

                e = haelt(df, i, preis)
                if e is not None:
                    treffer_echt[1] += 1
                    treffer_echt[0] += 1 if e else 0
                    abstaende.append(abstand)

                    # ZUFALLSLATTE im GLEICHEN Abstand - das ist der Punkt.
                    # Die Vorgaengermessung streute frei und verglich damit
                    # nah gegen fern.
                    stoerung = random.uniform(-0.25, 0.25) / 100.0
                    zufall = kurs * (1 - abstand + stoerung)
                    if zufall > 0:
                        z = haelt(df, i, zufall)
                        if z is not None:
                            treffer_zufall[1] += 1
                            treffer_zufall[0] += 1 if z else 0
        i += SCHRITT

    return treffer_echt, treffer_zufall, abstaende


def quote(t):
    return 100.0 * t[0] / t[1] if t[1] else 0.0


def main():
    print("=" * 84)
    print("  MARKS FIBONACCI-STUFEN - halten sie besser als eine Zufallslinie?")
    print("  Gerechnet mit features/chartanalyse.py selbst, nicht mit einem Nachbau")
    print("=" * 84)

    fehlt = [s for s in MUENZEN if lade(s) is None]
    if fehlt:
        print("\n  Kerzendateien fehlen: %s" % ", ".join(fehlt))
        return 2

    print()
    print("  Beruehrung: Tief kommt auf %.2f %% an die Stufe" % NAEHE)
    print("  Gehalten:   danach %+.1f %% darueber, bevor %.1f %% darunter"
          % (UMKEHR, DURCHBRUCH))
    print("  Fenster:    %d Kerzen (15 min) = %d Stunden"
          % (FENSTER, FENSTER // 4))
    print()
    print("  %-8s %10s %14s %14s %12s" % ("Muenze", "Faelle", "Marks Stufen",
                                          "Zufallslinie", "Unterschied"))
    print("  " + "-" * 64)

    gesamt_e, gesamt_z = [0, 0], [0, 0]
    for sym in MUENZEN:
        df = lade(sym)
        e, z, ab = messe(df, sym)
        gesamt_e[0] += e[0]; gesamt_e[1] += e[1]
        gesamt_z[0] += z[0]; gesamt_z[1] += z[1]
        d = quote(e) - quote(z)
        print("  %-8s %10d %13.1f %% %13.1f %% %+11.1f" %
              (sym.replace("USDT", ""), e[1], quote(e), quote(z), d))
        if ab:
            print("           mittlerer Abstand zum Kurs: %.2f %%"
                  % (100.0 * sum(ab) / len(ab)))

    print("  " + "-" * 64)
    d = quote(gesamt_e) - quote(gesamt_z)
    print("  %-8s %10d %13.1f %% %13.1f %% %+11.1f" %
          ("zusammen", gesamt_e[1], quote(gesamt_e), quote(gesamt_z), d))

    print()
    print("  Die Zufallslinie liegt im GLEICHEN Abstand vom Kurs wie die")
    print("  Stufe, gegen die sie antritt (plus/minus 0,25 %% Streuung). Ohne")
    print("  das haette man nah gegen fern verglichen - der Fehler, an dem")
    print("  die Messung vom 11.09. gescheitert ist.")

    # ------------------------------------------------------------ Urteil
    print()
    print("-" * 84)
    if gesamt_e[1] < 30:
        print("  NICHT ENTSCHEIDBAR: nur %d Faelle." % gesamt_e[1])
        return 0
    print("  Marks Stufen halten in %.1f %% der Faelle (%d von %d)."
          % (quote(gesamt_e), gesamt_e[0], gesamt_e[1]))
    print("  Eine Zufallslinie im selben Abstand: %.1f %% (%d von %d)."
          % (quote(gesamt_z), gesamt_z[0], gesamt_z[1]))
    print()
    print("  Unterschied: %+.1f Prozentpunkte" % d)
    print()
    print("  Was das NICHT beantwortet: ob sich daraus ein Handel bauen")
    print("  laesst. Eine Stufe, die haelt, ist noch kein Gewinn - der")
    print("  Kurs muss danach weit genug laufen, um 0,505 %% Kosten zu")
    print("  decken. Das ist die naechste Frage, nicht diese.")
    print("-" * 84)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
