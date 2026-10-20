#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  RUECKSCHLAEGE - wie tief faellt es, bevor es weitergeht?
================================================================
Angelegt 21.08.2026 auf Svens Frage: "wichtig ist zu wissen, wie
hat es sich in den letzten Jahren verhalten - um wie viel Prozent
hat er korrigiert, bevor es weiter nach oben ging?"

WARUM DAS DIE ENTSCHEIDENDE ZAHL IST
------------------------------------
Der Bot steigt aus, wenn der Kurs vom Hoechststand um X Prozent
faellt (Nachzieh-Stopp / Trailing-Stop). Heute ist X = 0,80 %.

Ob 0,80 % richtig ist, haengt an genau einer Frage: WIE TIEF sind
die Ruecksetzer (Pullbacks), nach denen es trotzdem weiter nach
oben ging? Ist ein normaler Ruecksetzer 2 %, dann wirft ein Stopp
bei 0,80 % den Bot bei jeder normalen Atmung aus dem Markt.

Das laesst sich messen. Nicht schaetzen, nicht aus einem Lehrbuch
abschreiben - an echten Kursen der letzten Jahre, getrennt nach
Marktphase.

DIE METHODE
-----------
1. Stundenkerzen ueber mehrere Jahre holen. Stunden, nicht Tage:
   die mittlere Haltedauer des Bots liegt bei 27,6 Stunden - eine
   Tages-Korrektur sieht er gar nicht.

2. Zu JEDEM Zeitpunkt die Marktphase bestimmen - aus dem Abstand
   zum bis dahin erreichten Hoechststand.

   ACHTUNG, hier steckt der haeufigste Messfehler: Wer das HEUTE
   bekannte Allzeithoch nimmt, benutzt Wissen aus der Zukunft
   (Look-ahead-Bias). Die Phase wird deshalb nur aus dem gebildet,
   was zu diesem Zeitpunkt schon bekannt war.

3. Ruecksetzer suchen: jede Bewegung vom laufenden Hoechststand
   nach unten und wieder hinauf.

4. Fuer jeden Ruecksetzer die entscheidende Frage beantworten:
   Ging es danach ueber das alte Hoch hinaus (UEBERLEBT) - oder
   war das Hoch der Wendepunkt (ENDE)?

   Nur die ueberlebten Ruecksetzer zaehlen fuer die Stopp-Weite.
   Sie sind die, bei denen ein Ausstieg ein Fehler war.

5. Verteilung je Marktphase ausgeben.

WAS DABEI HERAUSKOMMT
---------------------
Fuer jede Phase eine Zahl: "Ein Stopp von X % haette Y Prozent der
normalen Ruecksetzer ueberstanden." Damit laesst sich die Weite
begruenden statt raten.

WAS ES NICHT KANN
-----------------
* Es sagt nicht, wie viel Gewinn eine Weite bringt. Ein weiter
  Stopp ueberlebt mehr Ruecksetzer, gibt dafuer bei echten Wenden
  mehr zurueck. Beides gegeneinander rechnet ausstieg_vergleich.py.
* Vergangenheit ist keine Zusage. Was drei Jahre lang galt, kann
  im vierten anders sein.

AUFRUF
------
    python rueckschlaege.py                  BTC, 3 Jahre
    python rueckschlaege.py --muenze ETH/USDT
    python rueckschlaege.py --jahre 5
    python rueckschlaege.py --selbsttest
================================================================
"""
import os
import sys
import argparse
import statistics as st
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

NL = chr(10)

# Dieselben Grenzen wie im Bot (agents/cycle_theory.py:90) - damit die
# Ergebnisse auf die Phase passen, die der Bot selbst erkennt.
PHASEN = [(-5, "EUPHORIA"), (-20, "DISTRIBUTION"), (-35, "EARLY_BEAR"),
          (-50, "MID_BEAR"), (-70, "DEEP_BEAR"), (-80, "CAPITULATION")]


def phase_von(abstand_pct):
    """Marktphase aus dem Abstand zum Hoechststand."""
    for grenze, name in PHASEN:
        if abstand_pct > grenze:
            return name
    return "ACCUMULATION"


def kerzen(muenze="BTC/USDT", jahre=3, takt="1h"):
    """Stundenkerzen ueber mehrere Jahre, in 1000er-Bloecken."""
    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    ende = datetime.now(timezone.utc)
    seit = int((ende - timedelta(days=365 * jahre)).timestamp() * 1000)
    schritt = {"1h": 3600, "4h": 14400, "1d": 86400}[takt] * 1000
    raus, letzter = [], None
    while True:
        try:
            block = ex.fetch_ohlcv(muenze, takt, since=seit, limit=1000)
        except Exception as e:
            print("  Abruf abgebrochen: " + str(e)[:60])
            break
        if not block:
            break
        raus.extend(block)
        neu = block[-1][0]
        if letzter is not None and neu <= letzter:
            break
        letzter = neu
        seit = neu + schritt
        if len(block) < 1000:
            break
    raus.sort(key=lambda k: k[0])
    return raus


def ruecksetzer_finden(k, fenster_h=48, mindest_pct=0.3):
    """Ruecksetzer aus der Sicht EINER laufenden Position.

    [KORREKTUR 21.08.2026] Die erste Fassung hatte zwei Fehler, die der
    Selbsttest nicht abdeckte - er prueft die Mechanik, nicht die Frage.

      1. Sie zaehlte nur Ruecksetzer, die ein neues ALLZEITHOCH
         erreichten. In einem Baerenmarkt passiert das fast nie - dort
         fand sie also keine, obwohl es dort staendig welche gibt.
         Ergebnis: 135 Faelle in drei Jahren.
      2. Die Marktphase wurde aus dem Abstand des lokalen Hochs zum
         laufenden Hoechststand gebildet. Ein lokales Hoch IST aber der
         laufende Hoechststand - der Abstand war immer rund null, also
         landeten alle 135 Faelle in "EUPHORIA".

    Jetzt wird die Frage gestellt, um die es wirklich geht:

      "Ich bin eingestiegen. Der Kurs steht auf einem Hoch. Wie tief
       faellt er zurueck, bevor er dieses Hoch ueberschreitet - und
       schafft er es ueberhaupt, solange ich die Position halte?"

    Fuer jeden Zeitpunkt wird ein Fenster von `fenster_h` Stunden
    betrachtet (Vorgabe 48 - die mittlere Haltedauer des Bots liegt bei
    27,6 Stunden). Innerhalb des Fensters:

      * jedes neue Hoch setzt die Marke
      * der tiefste Punkt danach ist der Ruecksetzer
      * wird die Marke im Fenster wieder ueberboten -> UEBERLEBT
      * sonst -> das Hoch war der Wendepunkt, zaehlt NICHT mit

    Die Phase kommt vom KURS gegen das bis dahin bekannte Allzeithoch -
    nicht vom lokalen Hoch. Und nur aus Daten, die zu diesem Zeitpunkt
    schon da waren (kein Blick in die Zukunft).
    """
    raus = []
    n = len(k)
    lauf_ath = k[0][2]
    for i in range(n):
        lauf_ath = max(lauf_ath, k[i][2])
        # Nur an lokalen Hochs ansetzen - dort steht eine Position im
        # Gewinn, dort greift der Nachzieh-Stopp.
        if i == 0 or k[i][2] <= k[i - 1][2]:
            continue
        marke = k[i][2]
        tief = None
        for j in range(i + 1, min(n, i + fenster_h + 1)):
            if k[j][2] >= marke:
                if tief is not None:
                    tiefe = (marke - tief) / marke * 100
                    if tiefe >= mindest_pct:
                        raus.append(dict(
                            ts=k[i][0], tiefe=tiefe, dauer_h=j - i,
                            abstand_ath=(k[i][4] / lauf_ath - 1) * 100))
                break
            tief = k[j][3] if tief is None else min(tief, k[j][3])
    return raus


def bericht(muenze="BTC/USDT", jahre=3, takt="1h"):
    print("=" * 84)
    print("  WIE TIEF FAELLT ES, BEVOR ES WEITERGEHT?")
    print("  " + muenze + ", " + str(jahre) + " Jahre, " + takt + "-Kerzen")
    print("=" * 84)
    print(NL + "  Kerzen holen ...")
    k = kerzen(muenze, jahre, takt)
    if len(k) < 500:
        print("  Zu wenige Kerzen (" + str(len(k)) + ").")
        return 1
    von = datetime.fromtimestamp(k[0][0] / 1000, timezone.utc)
    bis = datetime.fromtimestamp(k[-1][0] / 1000, timezone.utc)
    print("  " + format(len(k), ",") + " Kerzen von "
          + format(von, "%d.%m.%Y") + " bis " + format(bis, "%d.%m.%Y"))

    rs = ruecksetzer_finden(k)
    print("  " + format(len(rs), ",") + " ueberlebte Ruecksetzer gefunden"
          + NL)

    # Nach Phase gruppieren
    gruppen = {}
    for r in rs:
        p = phase_von(r["abstand_ath"])
        gruppen.setdefault(p, []).append(r["tiefe"])

    print("  " + "Marktphase".ljust(16) + "Faelle".rjust(8)
          + "Median".rjust(9) + "75 %".rjust(9) + "90 %".rjust(9)
          + "95 %".rjust(9) + "   Stopp 0,80 % haette ...")
    print("  " + "-" * 82)
    for name in ("EUPHORIA", "DISTRIBUTION", "EARLY_BEAR", "MID_BEAR",
                 "DEEP_BEAR", "CAPITULATION", "ACCUMULATION"):
        v = sorted(gruppen.get(name, []))
        if len(v) < 20:
            continue
        def p(q):
            return v[min(len(v) - 1, int(len(v) * q))]
        ueberlebt = 100.0 * sum(1 for x in v if x < 0.80) / len(v)
        print("  " + name.ljust(16) + format(len(v), ",").rjust(8)
              + format(st.median(v), "8.2f") + "%"
              + format(p(0.75), "8.2f") + "%" + format(p(0.90), "8.2f") + "%"
              + format(p(0.95), "8.2f") + "%"
              + format(ueberlebt, "10.0f") + " % ueberstanden")

    alle = sorted(x["tiefe"] for x in rs)
    print("  " + "-" * 82)
    print("  " + "ZUSAMMEN".ljust(16) + format(len(alle), ",").rjust(8)
          + format(st.median(alle), "8.2f") + "%"
          + format(alle[int(len(alle) * 0.75)], "8.2f") + "%"
          + format(alle[int(len(alle) * 0.90)], "8.2f") + "%"
          + format(alle[int(len(alle) * 0.95)], "8.2f") + "%")

    print(NL + "  WAS DIE SPALTEN BEDEUTEN")
    print("    Median : die Haelfte aller Ruecksetzer war flacher als das.")
    print("    75/90/95 %: so tief ging es in 75, 90 bzw. 95 von 100 Faellen")
    print("    hoechstens - der Rest war tiefer.")
    print(NL + "  WIE MAN EINE STOPP-WEITE DARAUS ABLEITET")
    print("    Ein Stopp bei X ueberlebt alle Ruecksetzer, die flacher als X")
    print("    sind. Wer 90 von 100 normalen Ruecksetzern ueberstehen will,")
    print("    nimmt die Spalte '90 %' seiner Phase als Untergrenze.")
    print(NL + "  Alle Werte sind BRUTTO-Kursbewegung, ohne Kosten. Die Kosten")
    print("  (0,505 % je Runde) kommen beim Ausstieg obendrauf - ein Stopp,")
    print("  der bei 0,50 % ausloest, verliert also Geld, selbst wenn er")
    print("  'richtig' lag.")
    return 0


def selbsttest():
    """Findet die Suche das, was sie finden soll - und nichts anderes?"""
    fehler = 0
    print("=" * 70)
    print("SELBSTTEST")
    print("=" * 70)

    def bauen(werte):
        """Kerzen aus reinen Schlusskursen - Hoch und Tief gleich."""
        return [[i * 3600000, w, w, w, w, 1.0] for i, w in enumerate(werte)]

    print(NL + "  Erkennt sie einen ueberlebten Ruecksetzer?")
    # 100 -> 110 -> 105 (-4,5 %) -> 120: ueberlebt
    r = ruecksetzer_finden(bauen([100, 110, 105, 120]))
    ok = len(r) == 1 and abs(r[0]["tiefe"] - 4.545) < 0.1
    print("    " + ("OK  " if ok else "FEHL") + "  ein Ruecksetzer, Tiefe "
          + (format(r[0]["tiefe"], ".2f") + " %" if r else "keiner"))
    if not ok:
        fehler += 1

    print(NL + "  Zaehlt sie einen NICHT ueberlebten mit? (darf sie nicht)")
    # 100 -> 110 -> 90 und Ende: die Marke wird nie wieder erreicht
    r = ruecksetzer_finden(bauen([100, 110, 100, 90]))
    ok = len(r) == 0
    print("    " + ("OK  " if ok else "FEHL") + "  " + str(len(r))
          + " gezaehlt (erwartet 0)")
    if not ok:
        fehler += 1

    print(NL + "  Filtert sie Rauschen unter 0,3 %?")
    r = ruecksetzer_finden(bauen([100, 110, 109.9, 120]))
    ok = len(r) == 0
    print("    " + ("OK  " if ok else "FEHL") + "  " + str(len(r))
          + " gezaehlt (erwartet 0, Tiefe waere 0,09 %)")
    if not ok:
        fehler += 1

    print(NL + "  Trifft die Phasen-Einteilung die Grenzen?")
    for abstand, soll in ((-3, "EUPHORIA"), (-10, "DISTRIBUTION"),
                          (-30, "EARLY_BEAR"), (-43, "MID_BEAR"),
                          (-60, "DEEP_BEAR"), (-90, "ACCUMULATION")):
        ist = phase_von(abstand)
        ok = ist == soll
        print("    " + ("OK  " if ok else "FEHL") + "  " + str(abstand).rjust(4)
              + " %  ->  " + ist)
        if not ok:
            fehler += 1

    print(NL + "  Mehrere Ruecksetzer hintereinander?")
    r = ruecksetzer_finden(bauen([100, 110, 105, 120, 112, 130]))
    ok = len(r) == 2
    print("    " + ("OK  " if ok else "FEHL") + "  " + str(len(r))
          + " gefunden (erwartet 2)")
    if not ok:
        fehler += 1

    print(NL + ("SELBSTTEST BESTANDEN" if not fehler
                else str(fehler) + " FEHLER"))
    return 1 if fehler else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--muenze", default="BTC/USDT")
    p.add_argument("--jahre", type=int, default=3)
    p.add_argument("--takt", default="1h", choices=["1h", "4h", "1d"])
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    sys.exit(selbsttest() if a.selbsttest
             else bericht(a.muenze, a.jahre, a.takt))
