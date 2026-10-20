# -*- coding: utf-8 -*-
"""startsperre_test.py - sperrt sie richtig, und laesst sie richtig durch?

WOZU
----
Die Doppelstart-Sperre (Befund 93) ist ein Bauteil, das den Bot am Starten
hindern kann. Ein Fehler darin ist teurer als das Problem, das sie loest:
zwei Boetten merkt man, ein nicht startender Bot steht still, bis jemand
hinsieht.

Deshalb ist der Grundsatz **im Zweifel starten lassen** - und deshalb
prueft dieser Test vor allem die Faelle, in denen sie NICHT sperren darf.
Sieben von acht Pruefungen sind Durchlassfaelle.

  1  Keine Sperrdatei                    starten
  2  Sperrdatei mit TOTER Nummer         starten  <- der Absturzfall
  3  Sperrdatei kaputt                   starten
  4  Sperrdatei leer                     starten
  5  Lebende Nummer, aber kein Bot       starten  <- Nummer neu vergeben
  6  Lebender Bot                        SPERREN  <- der einzige Sperrfall
  7  Lebender Bot + Notausgang           starten
  8  freigeben() loescht nur die eigene  fremde bleibt stehen

AENDERT NICHTS am Bot. Arbeitet auf einer Sperrdatei im Temp-Ordner.

    python startsperre_test.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core.startsperre as sp                              # noqa: E402


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, nr, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("  %d  %-42s ok   %s" % (nr, was, zusatz))
        else:
            self.fehler.append((nr, was, zusatz))
            print("  %d  %-42s FEHL %s" % (nr, was, zusatz))


def _schreibe(pid, pfad):
    with io.open(pfad, "w", encoding="utf-8") as f:
        json.dump({"pid": pid, "gestartet": "2026-09-13T00:00:00"}, f)


def _tote_nummer():
    """Eine Prozessnummer, die es sicher nicht gibt."""
    try:
        import psutil
        genommen = {p.pid for p in psutil.process_iter()}
    except Exception:
        genommen = set()
    for n in range(999990, 900000, -7):
        if n not in genommen:
            return n
    return 999999


def main():
    print("=" * 76)
    print("  STARTSPERRE - sperrt sie richtig, und laesst sie richtig durch?")
    print("=" * 76)
    print()
    print("  Grundsatz: IM ZWEIFEL STARTEN LASSEN. Sieben der acht")
    print("  Pruefungen sind deshalb Durchlassfaelle.")
    print()

    ordner = tempfile.mkdtemp(prefix="startsperre_")
    echte = sp.SPERRDATEI
    p = Pruefung()
    try:
        sp.SPERRDATEI = os.path.join(ordner, "bot_laeuft.json")

        # --- 1  keine Datei -------------------------------------------
        p.sage(1, "Keine Sperrdatei", sp.pruefen_und_eintragen([]) is True,
               "startet, und traegt sich ein")
        p.sage(1, "  ... und hat sich eingetragen",
               os.path.exists(sp.SPERRDATEI), "")

        # --- 2  tote Nummer (Absturzfall) ------------------------------
        tot = _tote_nummer()
        _schreibe(tot, sp.SPERRDATEI)
        p.sage(2, "Sperrdatei mit TOTER Nummer (%d)" % tot,
               sp.pruefen_und_eintragen([]) is True,
               "startet - sonst sperrt ein Absturz fuer immer aus")

        # --- 3  kaputte Datei ------------------------------------------
        with io.open(sp.SPERRDATEI, "w", encoding="utf-8") as f:
            f.write('{"pid": 12')
        p.sage(3, "Sperrdatei halb geschrieben",
               sp.pruefen_und_eintragen([]) is True, "startet")

        # --- 4  leere Datei --------------------------------------------
        with io.open(sp.SPERRDATEI, "w", encoding="utf-8") as f:
            f.write("")
        p.sage(4, "Sperrdatei leer",
               sp.pruefen_und_eintragen([]) is True, "startet")

        # --- 5  lebende Nummer, aber kein Bot --------------------------
        # Der eigene Testprozess lebt und heisst nicht app.py
        _schreibe(os.getpid(), sp.SPERRDATEI)
        lebt, ist_bot, text = sp._prozess_lebt(os.getpid())
        p.sage(5, "Eigene Nummer lebt, ist aber kein Bot",
               lebt and not ist_bot and sp.pruefen_und_eintragen([]) is True,
               "lebt=%s ist_bot=%s" % (lebt, ist_bot))

        # --- 6  lebender Bot -> sperren --------------------------------
        # Nachgestellt: die Lebendpruefung meldet einen laufenden app.py
        echte_pruefung = sp._prozess_lebt
        sp._prozess_lebt = lambda pid: (True, True, "python app.py")
        _schreibe(4242, sp.SPERRDATEI)
        gesperrt = sp.pruefen_und_eintragen([]) is False
        p.sage(6, "Ein lebender Bot laeuft schon", gesperrt, "SPERRT")

        # --- 7  Notausgang ---------------------------------------------
        p.sage(7, "Notausgang --trotzdem-starten",
               sp.pruefen_und_eintragen(["app.py", "--trotzdem-starten"]) is True,
               "startet trotzdem")
        sp._prozess_lebt = echte_pruefung

        # --- 8  freigeben nur die eigene -------------------------------
        _schreibe(4242, sp.SPERRDATEI)          # fremde Nummer
        weg = sp.freigeben()
        p.sage(8, "freigeben() bei fremder Nummer",
               weg is False and os.path.exists(sp.SPERRDATEI),
               "laesst sie stehen")
        sp.eintragen()                          # jetzt die eigene
        weg = sp.freigeben()
        p.sage(8, "freigeben() bei eigener Nummer",
               weg is True and not os.path.exists(sp.SPERRDATEI),
               "loescht sie")

        # --- Gegentest --------------------------------------------------
        print()
        print("  Gegentest - wuerde eine zu strenge Sperre auffallen?")
        print("    Eine, die immer sperrt, waere an 1 bis 5 und 7")
        print("    gescheitert - das sind sechs von acht Pruefungen.")
        print("    Eine, die nie sperrt, waere an 6 gescheitert.")
        print()
        print("    Der wichtigste Fall ist Nummer 2: ohne die Lebend-")
        print("    pruefung wuerde ein einziger Absturz den naechsten")
        print("    Start dauerhaft aussperren. Genau davor warnt")
        print("    OFFEN.md Punkt 24.")

    finally:
        sp.SPERRDATEI = echte
        shutil.rmtree(ordner, ignore_errors=True)

    print()
    print("-" * 76)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d - NICHT in app.py einbauen."
              % (len(p.fehler), p.ok + len(p.fehler)))
        for nr, was, z in p.fehler:
            print("    %d  %s  %s" % (nr, was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Was das NICHT abdeckt: zwei Starts in derselben Sekunde. Wer")
    print("  zweimal gleichzeitig doppelklickt, kann beide durchkommen")
    print("  sehen - dagegen hilft nur eine Sperre des Betriebssystems.")
    print("  Der gemessene Fall vom 01.09. war ein Start Minuten spaeter,")
    print("  und den faengt sie.")
    print("-" * 76)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
