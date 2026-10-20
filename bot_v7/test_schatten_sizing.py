# -*- coding: utf-8 -*-
"""Test fuer den Schattenmodus der Positionsgroesse (11.08.2026).

Die wichtigste Pruefung steht in Abschnitt 3: der Schattenblock in app.py
darf den Kaufbetrag NIE veraendern. Das wird hier nicht geglaubt, sondern
am Quelltext nachgesehen.

Laeuft in einem Wegwerf-Ordner. Der Bot darf dabei laufen.

Aufruf:  python test_schatten_sizing.py
"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from core.telemetrie import Telemetrie          # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print(("  OK   " if bedingung else "  FEHLT") + "  " + text)
    if not bedingung:
        fehler.append(text)


def main():
    ordner = tempfile.mkdtemp(prefix="schatten_test_")
    try:
        db = os.path.join(ordner, "t.db")
        tel = Telemetrie(db_datei=db)

        print("\n1) Schattenzeile wird geschrieben")
        ok = tel.schatten_sizing(
            symbol="BTC/USDC", echt_usd=148.44, schatten_usd=96.20,
            schatten_pct=19.4, gruende="Verlustserie 2 | Drawdown -3.1%",
            confidence=0.62, win_rate=44.0, drawdown_pct=-3.1,
            verlustserie=2, regime="RANGING", fear_greed=29)
        pruefe(ok is True, "Rueckgabe True")
        con = sqlite3.connect(db)
        z = con.execute("SELECT symbol,echt_usd,schatten_usd,differenz_usd,"
                        "verlustserie,regime,fear_greed FROM schatten_sizing").fetchone()
        con.close()
        pruefe(z is not None, "Zeile in schatten_sizing vorhanden")
        pruefe(z[0] == "BTC/USDC", "Symbol gespeichert")
        pruefe(abs(z[3] - (-52.24)) < 0.001,
               f"Differenz automatisch berechnet ({z[3]} = 96.20 - 148.44)")
        pruefe(z[4] == 2 and z[5] == "RANGING" and z[6] == 29,
               "Begleitumstaende gespeichert (Verlustserie, Regime, F&G)")

        print("\n2) Kaputte Eingaben werfen nichts nach aussen")
        pruefe(tel.schatten_sizing(symbol=None, echt_usd="keine Zahl") is True,
               "unsinnige Werte -> kein Absturz")

        print("\n3) Der Schattenblock in app.py aendert NIE den Betrag")
        quelle = open(os.path.join(HIER, "app.py"), encoding="utf-8",
                      errors="replace").read()
        start = quelle.find("SCHATTENMODUS ADAPTIVE SIZING")
        ende = quelle.find("nicht mitgeschrieben", start)
        pruefe(start > 0 and ende > start, "Schattenblock gefunden")
        block = quelle[start:ende]
        zuweisungen = re.findall(r"intent\.amount_usd\s*(?![=!<>])=(?!=)", block)
        pruefe(not zuweisungen,
               f"keine Zuweisung an intent.amount_usd im Block ({len(zuweisungen)} gefunden)")
        pruefe("intent.amount_usd" in block, "Betrag wird gelesen (Vergleich/Protokoll)")

        print("\n4) Der stuendliche RL-Verfall ist nicht mehr eingeplant")
        aktive = [z for z in quelle.splitlines()
                  if "rl_decay" in z and not z.strip().startswith("#")]
        pruefe(not aktive, f"keine aktive rl_decay-Zeile mehr ({len(aktive)} gefunden)")
        pruefe("VERFALL ABGESCHALTET" in quelle, "Abschaltung ist begruendet dokumentiert")
        pruefe("#         \"rl_decay\"" in quelle or '#         "rl_decay"' in quelle,
               "Rueckbauweg steht als Kommentar daneben")

        print("\n5) situation_memory ist als nicht verdrahtet gekennzeichnet")
        kopf = open(os.path.join(HIER, "features", "situation_memory.py"),
                    encoding="utf-8", errors="replace").read(1400)
        pruefe("NICHT VERDRAHTET" in kopf, "Warnhinweis im Dateikopf")
        pruefe("situation_replay.py" in kopf, "einziger Nutzer benannt")

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
