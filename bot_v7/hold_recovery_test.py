# -*- coding: utf-8 -*-
"""hold_recovery_test.py - haelt die Hold/Recovery-Regel, was sie verspricht?

WOZU
----
Diese Regel entscheidet im Schattenbetrieb, ob eine Verlustposition
ausgesessen oder geschlossen wuerde. Sie handelt nicht - aber was sie
misst, soll spaeter eine Entscheidung tragen. Also muss sie stimmen.

Geprueft wird in BEIDE Richtungen, und besonders scharf die Reihenfolge:
Die Notbremse muss VOR der Struktur greifen. Waere es andersherum, liefe
eine Position bei -20 % weiter, solange die Struktur formal haelt - und
genau das soll die Notbremse verhindern.

AENDERT NICHTS.

    python hold_recovery_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.kosten import K_BASIS_PCT                            # noqa: E402
from risk.hold_recovery import (                               # noqa: E402
    NOTBREMSE_PCT, RECOVERY_AB_PCT, bewerte, grund_text,
    haette_gehalten, netto, struktur_gebrochen)


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("    %-50s ok   %s" % (was, zusatz))
        else:
            self.fehler.append((was, zusatz))
            print("    %-50s FEHL %s" % (was, zusatz))


def main():
    print("=" * 78)
    print("  HOLD/RECOVERY - Zustaende, Notbremse, Reihenfolge")
    print("=" * 78)
    p = Pruefung()

    print()
    print("  DIE FUENF ZUSTAENDE")
    print("  " + "-" * 68)
    # Einstand 100, Swing-Tief bei 95 -> Struktur bricht unter 94,715
    TIEF = 95.0

    e = bewerte(2.0, preis=102.0, swing_tief=TIEF)
    p.sage("Im Plus -> NORMAL", e["zustand"] == "NORMAL" and not e["verkauft"],
           e["zustand"])

    e = bewerte(-1.5, preis=98.5, swing_tief=TIEF)
    p.sage("Im Minus, Struktur haelt -> RECOVERY",
           e["zustand"] == "RECOVERY" and not e["verkauft"],
           "%s, wird ausgesessen" % e["zustand"])

    e = bewerte(1.2, preis=101.2, swing_tief=TIEF, tiefster_pnl_pct=-3.0)
    p.sage("Zurueck ueber null -> ERHOLT",
           e["zustand"] == "ERHOLT" and not e["verkauft"],
           "tiefster Stand war -3,0 %")

    e = bewerte(-6.0, preis=94.0, swing_tief=TIEF)
    p.sage("Kurs unter dem Swing-Tief -> INVALIDIERT",
           e["zustand"] == "INVALIDIERT" and e["verkauft"],
           "94,0 unter 95,0 minus Puffer")

    e = bewerte(-16.0, preis=84.0, swing_tief=TIEF)
    p.sage("Tiefer als -15 %% -> NOTBREMSE",
           e["zustand"] == "NOTBREMSE" and e["verkauft"], e["zustand"])

    print()
    print("  DIE REIHENFOLGE - der schaerfste Test")
    print("  " + "-" * 68)
    # Struktur HAELT (Kurs weit ueber dem Tief), aber -16 % erreicht.
    # Das geht nur, wenn der Einstand hoch ueber dem Swing-Tief lag.
    e = bewerte(-16.0, preis=200.0, swing_tief=100.0)
    p.sage("Notbremse greift, obwohl die Struktur haelt",
           e["zustand"] == "NOTBREMSE" and e["verkauft"],
           "Kurs 200 weit ueber Tief 100 - trotzdem Schluss")
    p.sage("      ... und die Struktur ist wirklich heil",
           not struktur_gebrochen(200.0, 100.0),
           "sonst waere der Test wertlos")

    print()
    print("  DIE NOTBREMSE HAENGT AM TIEFSTEN STAND, nicht am jetzigen")
    print("  " + "-" * 68)
    e = bewerte(-2.0, preis=98.0, swing_tief=TIEF, tiefster_pnl_pct=-16.0)
    p.sage("War schon bei -16 %, steht jetzt bei -2 %",
           e["zustand"] == "NOTBREMSE",
           "greift trotzdem - sonst waere sie umgehbar")

    print()
    print("  STRUKTUR-PRUEFUNG")
    print("  " + "-" * 68)
    # Puffer 0,3 % -> Bruch erst unter 95 * 0,997 = 94,715
    p.sage("Genau auf dem Tief: kein Bruch",
           not struktur_gebrochen(95.0, 95.0), "95,0")
    p.sage("Knapp darunter, im Puffer: kein Bruch",
           not struktur_gebrochen(94.8, 95.0), "94,8 > 94,715")
    p.sage("Unter dem Puffer: Bruch",
           struktur_gebrochen(94.7, 95.0), "94,7 < 94,715")
    p.sage("Ohne Swing-Tief kein Bruch",
           not struktur_gebrochen(50.0, None), "unbekannte Struktur haelt")

    print()
    print("  KOSTEN")
    print("  " + "-" * 68)
    p.sage("Erholung auf +0,3 %% ist netto ein VERLUST",
           netto(0.3) < 0,
           "+0,300 brutto = %+.3f netto bei %.3f %% Kosten"
           % (netto(0.3), K_BASIS_PCT))
    p.sage("Erst ueber %.3f %% ist es ein Gewinn" % K_BASIS_PCT,
           netto(K_BASIS_PCT + 0.01) > 0, "")

    print()
    print("  GEGENTEST - wuerde eine kaputte Regel auffallen?")
    print("  " + "-" * 68)
    # Eine Regel ohne Notbremse
    ohne = bewerte(-16.0, preis=200.0, swing_tief=100.0,
                   notbremse_pct=-999.0)
    p.sage("Ohne Notbremse laeuft die Position weiter",
           ohne["zustand"] == "RECOVERY" and not ohne["verkauft"],
           "-> bei -16 %% immer noch RECOVERY. Genau das verhindert")
    print("        die Notbremse, und genau das prueft der Test oben.")

    # haette_gehalten als Umkehrung
    p.sage("haette_gehalten ist die Umkehrung von verkauft",
           haette_gehalten(-1.5, 98.5, TIEF)
           and not haette_gehalten(-16.0, 84.0, TIEF), "")

    # Unsinnige Eingaben
    p.sage("Text statt Zahl stuerzt nicht ab",
           bewerte("keine Zahl")["zustand"] == "NORMAL", "")

    print()
    print("  Ein Beispiel, wie es im Protokoll steht:")
    print("    %s" % grund_text(-1.5, 98.5, TIEF))
    print("    %s" % grund_text(-16.0, 84.0, TIEF))

    print()
    print("-" * 78)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d" % (len(p.fehler), p.ok + len(p.fehler)))
        for was, z in p.fehler:
            print("    %s  %s" % (was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Was das NICHT sagt: ob Aussitzen Geld bringt. Die Regel")
    print("  rechnet richtig - ob sie recht hat, misst der Schattenbetrieb")
    print("  und hold_recovery_rueckblick.py.")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
