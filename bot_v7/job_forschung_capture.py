# -*- coding: utf-8 -*-
"""Starter fuer den Forschungs-Capture - OHNE Fenster, MIT Status.

[CLEANUP-KEEP]

Wird von der Windows-Aufgabenplanung ("ForschungCapture") per pythonw.exe
aufgerufen. Ersetzt capture_start.bat, weil das cmd.exe um die .bat herum
das sichtbare Fenster erzeugte.

Aufruf durch die Aufgabenplanung:
    pythonw.exe "<Projekt>\\job_forschung_capture.py"

Von Hand testen (dann sieht man die Ausgabe):
    python job_forschung_capture.py

Dieser Starter blockiert absichtlich, solange der Daemon laeuft. Genau das
brauchte die Korrektur vom 04.08.2026: mit "start /b" war die .bat sofort
fertig, die Aufgabenplanung hielt den Task fuer beendet und raeumte den
Prozessbaum ab - der Daemon starb jedes Mal nach wenigen Minuten.

Kein Trading, keine Schluessel, kein Zugriff auf data_store des Bots.
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from core.hintergrund import starte_still, hole_telemetrie   # noqa: E402

CAPTURE = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")
DAEMON = os.path.join(CAPTURE, "capture_daemon.py")


def main():
    if not os.path.isfile(DAEMON):
        print("FEHLER: capture_daemon.py nicht gefunden:", DAEMON)
        return 2
    return starte_still(
        job_name="forschung_capture",
        argv=[sys.executable, DAEMON],
        cwd=CAPTURE,
        telemetrie=hole_telemetrie(),
        timeout=None,          # Daemon, laeuft dauerhaft
        # Code 3 = "eine andere Instanz haelt die Sperre"
        # (capture_daemon.py:122). Das ist bei einem 10-Minuten-Takt der
        # Normalfall und KEIN Fehler - sonst entstuenden 144 BUG-Tickets
        # pro Tag und das Wichtige ginge darin unter. Der Code bleibt in
        # der Spalte exit_code sichtbar, "3 = uebersprungen" ist also
        # weiterhin von "0 = gelaufen" unterscheidbar.
        ok_codes=(0, 3),
    )


if __name__ == "__main__":
    sys.exit(main())
