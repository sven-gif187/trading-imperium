# -*- coding: utf-8 -*-
"""Test fuer die Marktdaten-Historie (Aufgabe 4, 11.08.2026).

Der Kern der Sache: eine Zeitreihe muss auch dann weiterlaufen, wenn
einzelne Quellen ausfallen. Eine Reihe mit ein paar leeren Feldern ist
auswertbar - eine, die bei der ersten Stoerung abbricht, ist es nicht.

Laeuft in einem Wegwerf-Ordner. Der Bot darf dabei laufen.

Aufruf:  python test_markt_historie.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from core.telemetrie import Telemetrie          # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print(("  OK   " if bedingung else "  FEHLT") + "  " + text)
    if not bedingung:
        fehler.append(text)


def main():
    ordner = tempfile.mkdtemp(prefix="markt_test_")
    try:
        db = os.path.join(ordner, "t.db")
        tel = Telemetrie(db_datei=db)

        print("\n1) Vollstaendiger Messpunkt")
        ok = tel.markt_schnappschuss(
            fear_greed=29, nupl=0.2, nupl_zone="HOFFNUNG", dxy=99.79,
            dxy_trend="NEUTRAL", funding_score=0.55, whale_score=0.5,
            onchain_score=0.65, reddit_score=0.5, capitol_score=0.5,
            cycle_phase="MID_BEAR", regime="RANGING", btc_preis=64007.7,
            eth_preis=1876.26, sol_preis=75.89, equity=496.42, cash=36.27,
            offene_pos=3)
        pruefe(ok is True, "Rueckgabe True")
        con = sqlite3.connect(db)
        z = con.execute("SELECT fear_greed,nupl,nupl_zone,dxy,cycle_phase,"
                        "btc_preis,equity,offene_pos FROM markt_historie").fetchone()
        con.close()
        pruefe(z[0] == 29 and z[1] == 0.2, "Fear&Greed und NUPL gespeichert")
        pruefe(z[2] == "HOFFNUNG" and z[4] == "MID_BEAR", "Textfelder gespeichert")
        pruefe(abs(z[5] - 64007.7) < 0.01 and abs(z[6] - 496.42) < 0.01,
               "Preis und Equity gespeichert")
        pruefe(z[7] == 3, "Anzahl offener Positionen gespeichert")

        print("\n2) Quelle ausgefallen -> Luecke, KEIN Abbruch")
        ok = tel.markt_schnappschuss(fear_greed=30, nupl=None, dxy=None,
                                     cycle_phase="MID_BEAR")
        pruefe(ok is True, "Zeile wird trotzdem geschrieben")
        con = sqlite3.connect(db)
        z = con.execute("SELECT fear_greed,nupl,dxy,whale_score FROM "
                        "markt_historie ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        pruefe(z[0] == 30, "vorhandener Wert steht drin")
        pruefe(z[1] is None and z[2] is None and z[3] is None,
               "fehlende Werte sind NULL, nicht 0 (0 waere eine Luege)")

        print("\n3) Unsinnige Werte werfen nichts nach aussen")
        pruefe(tel.markt_schnappschuss(fear_greed="dreissig", nupl="viel") is True,
               "Text statt Zahl -> kein Absturz")
        pruefe(tel.markt_schnappschuss() is True, "voellig leerer Aufruf -> kein Absturz")

        print("\n4) Zeitreihe: Reihenfolge und Zeitstempel")
        time.sleep(1.1)
        tel.markt_schnappschuss(fear_greed=31)
        con = sqlite3.connect(db)
        zeilen = con.execute("SELECT ts_utc,fear_greed FROM markt_historie "
                             "ORDER BY id").fetchall()
        con.close()
        pruefe(len(zeilen) == 5, f"{len(zeilen)} Messpunkte gesammelt")
        pruefe(zeilen[0][0] < zeilen[-1][0], "Zeitstempel laufen aufwaerts")
        pruefe(zeilen[-1][1] == 31, "letzter Messpunkt ist der neueste")

        print("\n5) Der Sammelpunkt in app.py ist verdrahtet")
        quelle = open(os.path.join(HIER, "app.py"), encoding="utf-8",
                      errors="replace").read()
        pruefe('"markt_historie", self._markt_schnappschuss' in quelle,
               "als Scheduler-Aufgabe eingetragen")
        pruefe("interval_sec=900" in quelle, "Takt 15 Minuten")
        pruefe("def _markt_schnappschuss" in quelle, "Methode vorhanden")
        # Die Cash-Quelle war beim ersten Anlauf falsch (portfolio statt
        # execution, und flach statt verschachtelt) - deshalb hier festgenagelt.
        pruefe("self.execution.get_balance()" in quelle,
               "Cash kommt aus execution.get_balance(), nicht aus portfolio")

    finally:
        shutil.rmtree(ordner, ignore_errors=True)

    print("\n" + "=" * 52)
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        for f in fehler:
            print("   -", f)
        return 1
    print("ALLE TESTS BESTANDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
