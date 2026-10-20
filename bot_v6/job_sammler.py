# -*- coding: utf-8 -*-
"""Starter fuer den taeglichen Sammler - OHNE Fenster, MIT Status.

[CLEANUP-KEEP]

Wird von der Windows-Aufgabenplanung ("TI6-Sammler") per pythonw.exe
aufgerufen. Ersetzt sammler_taeglich.bat.

Die .bat brauchte cmd.exe nur fuer die Log-Umleitung (>>). Genau dieses
cmd.exe war das sichtbare Fenster. Die Umleitung uebernimmt jetzt
core/hintergrund.py - inklusive Rollen der Logdatei und Eintrag in die
Telemetrie-Tabelle `jobs`.

Aufruf durch die Aufgabenplanung:
    pythonw.exe "<Projekt>\\job_sammler.py"

Von Hand testen:
    python job_sammler.py

Faesst den Bot NICHT an. Schreibt nur in die Sammel-Dateien und ins Log.
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from core.hintergrund import starte_still, hole_telemetrie   # noqa: E402

SAMMLER = os.path.join(HIER, "sammler.py")


def main():
    if not os.path.isfile(SAMMLER):
        print("FEHLER: sammler.py nicht gefunden:", SAMMLER)
        return 2
    return starte_still(
        job_name="sammler_taeglich",
        argv=[sys.executable, SAMMLER],
        cwd=HIER,
        telemetrie=hole_telemetrie(),
        # [MESSUNG 11.08.2026] Gemessene Laufzeiten aus data_store/sammler.log:
        # 07.08. 35s, 08.08. 26s, 09.08. 53s; frisch nachgemessen 38,8s und
        # 68s. Die erste Fassung stand auf 3600s - fuer einen Job, der unter
        # einer Minute braucht, ist das kein Wachhund, sondern ein Freibrief.
        # Am 11.08. lief er dadurch 60,6 Minuten, bevor der Abbruch griff.
        # 600s laesst reichlich Luft fuer eine langsame Leitung und schlaegt
        # trotzdem in Minuten statt in einer Stunde an.
        timeout=600,
    )


if __name__ == "__main__":
    sys.exit(main())
