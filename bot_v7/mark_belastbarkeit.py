# -*- coding: utf-8 -*-
"""mark_belastbarkeit.py - sind die +2,1 Prozentpunkte echt oder Rauschen?

WOZU
----
`mark_messung.py` findet, dass Marks Fibonacci-Stufen in 25,9 % der Faelle
halten gegen 23,8 % bei einer Zufallslinie im selben Abstand - ein Vorsprung
von 2,1 Prozentpunkten ueber 6.971 Faelle.

**6.971 ist nicht die Zahl, die zaehlt.** Zwei Gruende:

1. **Mehrere Stufen je Zeitpunkt.** An einem Zeitpunkt werden bis zu sieben
   Stufen geprueft. Sie haengen alle am selben Kursverlauf - faellt der Kurs
   durch, faellt er meist durch mehrere.

2. **Ueberlappende Fenster.** Gemessen wird alle 8 Kerzen, das Urteilsfenster
   ist 16 Kerzen lang. Benachbarte Messungen sehen dieselben Kerzen.

Die Regel aus CLAUDE.md dazu: *"Immer fragen, wie viele davon UNABHAENGIG
sind."* Diese Datei beantwortet genau das - mit einem BLOCK-Bootstrap: es
werden nicht Einzelfaelle gezogen, sondern ganze Zeitbloecke. Was innerhalb
eines Blocks zusammenhaengt, bleibt zusammen.

Dazu ein Mischungstest: Wenn man die Etiketten "Stufe" und "Zufall"
zufaellig vertauscht - wie oft entsteht dann ein Vorsprung von 2,1 Punkten
von allein?

AENDERT NICHTS. Rechnet auf gespeicherten Kerzen.

    python mark_belastbarkeit.py
"""
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd                                              # noqa: E402
from features.chartanalyse import swing_punkte, fibonacci_ziele  # noqa: E402

ORD = os.path.join(os.environ.get("TEMP", "."), "claude",
                   "C--Users-sven7-Desktop-trading-imperium-v6-21-",
                   "efb0dd76-0fbc-46d7-b8ff-7c7f12f375a5", "scratchpad")

MUENZEN = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
SICHT, SCHRITT, NAEHE = 150, 8, 0.10
FENSTER, UMKEHR, DURCHBRUCH, VORLAUF = 16, 1.0, 0.5, 200
BLOCK = 96          # Kerzen je Block = 1 Tag. Innerhalb eines Tages haengt
                    # alles zusammen, ueber Tage hinweg kaum noch.
ZIEHUNGEN = 5000
random.seed(20260912)


def lade(sym):
    p = os.path.join(ORD, "kerzen_%s.json" % sym)
    if not os.path.exists(p):
        return None
    k = json.load(io.open(p, encoding="utf-8"))
    return pd.DataFrame({"High": [float(x[2]) for x in k],
                         "Low": [float(x[3]) for x in k],
                         "Close": [float(x[4]) for x in k]})


def haelt(lows, highs, n, i, linie):
    for j in range(i + 1, min(i + 1 + FENSTER, n)):
        if lows[j] <= linie * (1 + NAEHE / 100.0):
            for m in range(j, min(j + FENSTER, n)):
                if lows[m] <= linie * (1 - DURCHBRUCH / 100.0):
                    return False
                if highs[m] >= linie * (1 + UMKEHR / 100.0):
                    return True
            return False
    return None


def sammle(df):
    """Gibt je Block (echt_treffer, echt_n, zufall_treffer, zufall_n)."""
    lows, highs, closes = df["Low"].values, df["High"].values, df["Close"].values
    n = len(df)
    hochs, tiefs = swing_punkte(df, weite=3)
    bloecke = {}
    i = VORLAUF
    while i < n - 2 * FENSTER - 1:
        b = i // BLOCK
        if b not in bloecke:
            bloecke[b] = [0, 0, 0, 0]
        fib = fibonacci_ziele(df, hochs, tiefs, i, mit_vor=False, rueckblick=SICHT)
        if fib and fib.get("stufen"):
            kurs = float(closes[i])
            for verhaeltnis, preis, art in fib["stufen"]:
                if art == "anker" or preis <= 0 or preis >= kurs:
                    continue
                abstand = (kurs - preis) / kurs
                if abstand > 0.10:
                    continue
                e = haelt(lows, highs, n, i, preis)
                if e is not None:
                    bloecke[b][1] += 1
                    bloecke[b][0] += 1 if e else 0
                    stoerung = random.uniform(-0.25, 0.25) / 100.0
                    zufall = kurs * (1 - abstand + stoerung)
                    z = haelt(lows, highs, n, i, zufall) if zufall > 0 else None
                    if z is not None:
                        bloecke[b][3] += 1
                        bloecke[b][2] += 1 if z else 0
        i += SCHRITT
    return [tuple(v) for v in bloecke.values() if v[1] > 0]


def vorsprung(bloecke):
    et = sum(b[0] for b in bloecke); en = sum(b[1] for b in bloecke)
    zt = sum(b[2] for b in bloecke); zn = sum(b[3] for b in bloecke)
    if not en or not zn:
        return 0.0
    return 100.0 * et / en - 100.0 * zt / zn


def main():
    print("=" * 80)
    print("  MARKS STUFEN - wie belastbar sind die 2,1 Prozentpunkte?")
    print("=" * 80)

    if any(lade(s) is None for s in MUENZEN):
        print("\n  Kerzendateien fehlen.")
        return 2

    alle = []
    print()
    print("  %-8s %8s %10s %12s" % ("Muenze", "Bloecke", "Faelle", "Vorsprung"))
    print("  " + "-" * 44)
    for sym in MUENZEN:
        b = sammle(lade(sym))
        alle.extend(b)
        print("  %-8s %8d %10d %+11.1f" % (sym.replace("USDT", ""), len(b),
                                           sum(x[1] for x in b), vorsprung(b)))
    print("  " + "-" * 44)
    n_faelle = sum(x[1] for x in alle)
    echt = vorsprung(alle)
    print("  %-8s %8d %10d %+11.1f" % ("zusammen", len(alle), n_faelle, echt))

    print()
    print("  Ein Block ist %d Kerzen = 1 Tag. %d Faelle verteilen sich auf"
          % (BLOCK, n_faelle))
    print("  %d Bloecke - im Schnitt %.1f Faelle je Block, die miteinander"
          % (len(alle), n_faelle / max(len(alle), 1)))
    print("  zusammenhaengen. Die wirkliche Stichprobe sind die BLOECKE.")

    # ---------------------------------------------------- Block-Bootstrap
    print()
    print("  Block-Bootstrap: %d mal so viele Bloecke mit Zuruecklegen ziehen"
          % ZIEHUNGEN)
    werte = []
    N = len(alle)
    for _ in range(ZIEHUNGEN):
        stichprobe = [alle[random.randrange(N)] for _ in range(N)]
        werte.append(vorsprung(stichprobe))
    werte.sort()
    lo = werte[int(0.025 * ZIEHUNGEN)]
    hi = werte[int(0.975 * ZIEHUNGEN)]
    print("    Vertrauensintervall: %+.2f bis %+.2f Prozentpunkte" % (lo, hi))
    ueber_null = lo > 0
    print("    -> %s" % ("ganz ueber Null" if ueber_null
                         else "enthaelt die Null"))

    # ---------------------------------------------------- Mischungstest
    print()
    print("  Mischungstest: Etiketten 'Stufe' und 'Zufall' je Block tauschen")
    zufaellig_groesser = 0
    for _ in range(ZIEHUNGEN):
        gemischt = []
        for b in alle:
            if random.random() < 0.5:
                gemischt.append((b[2], b[3], b[0], b[1]))   # getauscht
            else:
                gemischt.append(b)
        if vorsprung(gemischt) >= echt:
            zufaellig_groesser += 1
    p = 100.0 * zufaellig_groesser / ZIEHUNGEN
    print("    So gross oder groesser entsteht der Vorsprung zufaellig in")
    print("    %.2f %% der Mischungen." % p)

    # ------------------------------------------------ in die Datenbank
    # Der Analyse-Reiter liest von hier. Reines Aufschreiben - der Reiter
    # bleibt Beobachtungsdeck und loest keinen Handel aus.
    _schreibe(echt, lo, hi, p, n_faelle, len(alle))

    print()
    print("-" * 80)
    if ueber_null and p < 5.0:
        print("  BELASTBAR: %+.1f Prozentpunkte, Vertrauensintervall %+.2f bis %+.2f,"
              % (echt, lo, hi))
        print("  zufaellig in %.2f %% der Mischungen. Marks Stufen halten besser" % p)
        print("  als eine Zufallslinie im selben Abstand.")
    elif ueber_null:
        print("  UNEINDEUTIG: Das Vertrauensintervall liegt zwar ueber Null")
        print("  (%+.2f bis %+.2f), aber der Mischungstest gibt %.2f %% -" % (lo, hi, p))
        print("  das ist zu haeufig, um es Zufall auszuschliessen.")
    else:
        print("  NICHT ENTSCHEIDBAR: Das Vertrauensintervall %+.2f bis %+.2f" % (lo, hi))
        print("  enthaelt die Null. Ueber Bloecke gerechnet traegt der")
        print("  Vorsprung von %+.1f Punkten nicht." % echt)
    print()
    print("  UND UNABHAENGIG DAVON: Eine Stufe, die haelt, ist noch kein")
    print("  Gewinn. Der Kurs muss danach weit genug laufen, um 0,505 %")
    print("  Kosten je Runde zu decken. Diese Messung sagt nichts darueber.")
    print("-" * 80)
    return 0




def _schreibe(vorsprung_pp, lo, hi, p_wert, faelle, bloecke):
    """Legt das Ergebnis in telemetrie.db ab, fuer den Analyse-Reiter.

    Eigene Tabelle, kein Anfassen bestehender. Faellt das Schreiben aus,
    ist das kein Grund, die Messung zu verwerfen - aber es wird gesagt.
    """
    import sqlite3
    import datetime
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data_store", "telemetrie.db")
    try:
        con = sqlite3.connect(pfad, timeout=20)
        con.execute("""CREATE TABLE IF NOT EXISTS fib_messung (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc      TEXT,
            vorsprung_pp REAL,
            ki_unten    REAL,
            ki_oben     REAL,
            p_prozent   REAL,
            faelle      INTEGER,
            bloecke     INTEGER,
            naehe_pct   REAL,
            umkehr_pct  REAL,
            durchbruch_pct REAL,
            fenster     INTEGER)""")
        con.execute("INSERT INTO fib_messung (ts_utc,vorsprung_pp,ki_unten,"
                    "ki_oben,p_prozent,faelle,bloecke,naehe_pct,umkehr_pct,"
                    "durchbruch_pct,fenster) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (datetime.datetime.now(datetime.timezone.utc).isoformat(
                        timespec="seconds"),
                     round(vorsprung_pp, 3), round(lo, 3), round(hi, 3),
                     round(p_wert, 3), faelle, bloecke,
                     NAEHE, UMKEHR, DURCHBRUCH, FENSTER))
        con.commit()
        con.close()
        print()
        print("  In telemetrie.db abgelegt (Tabelle fib_messung) - der")
        print("  Analyse-Reiter zeigt es beim naechsten Aufruf an.")
    except Exception as e:
        print()
        print("  NICHT in die Datenbank geschrieben: %s" % str(e)[:80])
        print("  (Die Messung oben gilt trotzdem - nur der Reiter sieht sie nicht.)")


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
