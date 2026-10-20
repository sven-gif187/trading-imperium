# -*- coding: utf-8 -*-
"""schreibwege_test.py - schreiben beide Verkaufswege dieselben Felder?

BEFUND 88
---------
Verkaeufe entstehen auf ZWEI Wegen:

  A) runtime/exit_monitor.py:413   Stop-Loss, Trailing, Trend-Ausstieg
  B) app.py:1658                   der allgemeine Ausfuehrungspfad

Weg A schrieb seit dem 10.08.2026 entry_score, entry_strategie,
position_id, haltedauer_min, mfe_pct und mae_pct mit. Weg B nicht.
Ergebnis: Die Felder standen nur bei 47,5 % der 120 Verkaeufe seit dem
Umbau - und jede Auswertung, die sie braucht, lief auf der halben
Datenmenge.

WARUM DAS ZAEHLT
----------------
Am 11.09.2026 zeigte die Auswertung: Signale ab Score 7 bringen im Schnitt
+0,468 %, darunter -0,540 %. Ein ganzer Prozentpunkt Unterschied, im
Zufallstest ueber 20.000 Mischungen nur in 1,18 % der Faelle zufaellig.
Diese Rechnung stand auf 57 statt 120 Faellen - genau wegen dieser Luecke.

Behoben am 11.09.2026 in app.py, direkt nach `pos = ...` im SELL-Zweig.

DIESER TEST prueft beide Richtungen:
  1. Findet er die Luecke, wenn ein Feld fehlt?   (Gegenprobe)
  2. Schweigt er, wenn alles da ist?

AENDERT NICHTS. Liest nur den Quelltext und das Journal.
"""
import io
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))

# Die Felder, die BEIDE Wege schreiben muessen, damit eine Auswertung
# ueber alle Verkaeufe moeglich ist.
PFLICHT = ["entry_score", "entry_strategie", "position_id",
           "haltedauer_min", "mfe_pct", "mae_pct"]


def schreibt(pfad, von, bis, felder):
    """Welche der Felder kommen im Quelltext zwischen zwei Zeilen vor?"""
    z = io.open(os.path.join(HIER, pfad), encoding="utf-8").read().split("\n")
    text = "\n".join(z[von - 1:bis])
    return {f: bool(re.search(r'["\']%s["\']' % f, text)) for f in felder}


def block_finden(pfad, marke, laenge=60):
    z = io.open(os.path.join(HIER, pfad), encoding="utf-8").read().split("\n")
    for i, x in enumerate(z):
        if marke in x:
            return i + 1, min(i + laenge, len(z))
    return None, None


def main():
    print("=" * 70)
    print("  SCHREIBWEGE - schreiben beide Verkaufswege dieselben Felder?")
    print("=" * 70)

    a_von, a_bis = block_finden("runtime/exit_monitor.py", '"type": "SELL", "coin": sym')
    b_von, b_bis = block_finden("app.py", "Bei SELL: P&L berechnen BEVOR Journal-Eintrag")
    if not a_von or not b_von:
        print("\n  Ein Weg wurde im Quelltext nicht gefunden - Test nicht durchfuehrbar.")
        return 2

    a = schreibt("runtime/exit_monitor.py", a_von, a_bis, PFLICHT)
    b = schreibt("app.py", b_von, b_bis, PFLICHT)

    print("\n  Feld                 Weg A (exit_monitor)   Weg B (app.py)")
    print("  " + "-" * 62)
    fehlt = []
    for f in PFLICHT:
        ja_a = "ja " if a[f] else "NEIN"
        ja_b = "ja " if b[f] else "NEIN"
        if not (a[f] and b[f]):
            fehlt.append(f)
        print("  %-20s %-22s %s%s"
              % (f, ja_a, ja_b, "   <== LUECKE" if not (a[f] and b[f]) else ""))

    print("\n" + "-" * 70)
    if fehlt:
        print("  DURCHGEFALLEN: %d Feld(er) fehlen auf einem Weg: %s"
              % (len(fehlt), ", ".join(fehlt)))
        ergebnis = 1
    else:
        print("  BESTANDEN: Beide Wege schreiben alle %d Pflichtfelder." % len(PFLICHT))
        ergebnis = 0

    # --- Gegenprobe: wuerde der Test eine echte Luecke finden? ---
    probe = schreibt("app.py", b_von, b_bis, ["gibt_es_nicht_xyz"])
    print("\n  Gegenprobe - ein erfundenes Feld:")
    print("    gibt_es_nicht_xyz    %s"
          % ("faelschlich gefunden - TEST TAUGT NICHTS"
             if probe["gibt_es_nicht_xyz"] else "nicht gefunden, richtig"))

    # --- Und was steht im Journal? ---
    p = os.path.join(HIER, "data_store", "trades_v5.json")
    if os.path.exists(p):
        t = json.loads(io.open(p, encoding="utf-8").read())
        t = t if isinstance(t, list) else t.get("trades", [])
        s = [x for x in t if x.get("type") == "SELL"
             and str(x.get("time", "")) >= "2026-07-29T19:00"]
        if s:
            print("\n  Stand im Journal (%d Verkaeufe seit dem Umbau):" % len(s))
            for f in PFLICHT:
                da = sum(1 for x in s if x.get(f) not in (None, "", 0))
                print("    %-20s %5.1f %%" % (f, 100.0 * da / len(s)))
            print("\n  Alte Verkaeufe bleiben unvollstaendig - die Reparatur")
            print("  wirkt erst auf NEUE. Ab dem naechsten Bot-Start steigt")
            print("  der Anteil, das ist der Beleg dafuer, dass sie greift.")
    print("-" * 70)
    return ergebnis


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
