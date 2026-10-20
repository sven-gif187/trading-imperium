"""Startet das Schatten-Universum, falls es nicht laeuft. Sonst tut es nichts.

Gedacht fuer die Windows-Aufgabenplanung: einmal beim Hochfahren und
danach stuendlich. Damit kommt der Sammler nach einem Neustart von
selbst wieder hoch - und auch nach einem Absturz.

WARUM ES DIESES SKRIPT GIBT
---------------------------
Am 18.08.2026 fragte Sven nach einem Windows-Update: "Was bringt es,
wenn er jetzt anlaeuft, aber dann wieder abbricht?" Zu Recht. Bot und
Forschungs-Sammler kamen nach dem Neustart von selbst wieder - der eine,
weil Sven ihn startet, der andere ueber die Aufgabe ForschungCapture.
Nur das Schatten-Universum musste jedes Mal von Hand gestartet werden,
und niemand merkte es, wenn es fehlte.

ZWEI FALLEN, DIE HIER SCHON EINGEBAUT SIND
------------------------------------------
1. DER PROZESSNAME. schatten_universum_start.bat suchte nach
   "pythonw.exe". Der ueber den AppData-Pfad gestartete Prozess heisst
   aber "pythonw3.13.exe" - die Suche fand nichts, und der Sammler lief
   doppelt. Deshalb wird hier die BEFEHLSZEILE durchsucht, nicht der
   Programmname.

2. DIE ELTERNSCHAFT. Wer einen Dauerlaeufer mit "&" oder direktem
   Aufruf startet, macht ihn zum Kind der aufrufenden Konsole - er
   stirbt mit ihr. Deshalb DETACHED_PROCESS.

Beide Fehler sind mir am 18.08. selbst unterlaufen, siehe Handbuch 4.55.

Aufruf:  python schatten_starter.py
Rueckgabe: 0 = laeuft (schon oder jetzt), 1 = Start fehlgeschlagen
"""
import io
import os
import subprocess
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "schatten_universum.py")
LOG = os.path.join(HIER, "data_store", "schatten_starter.log")


def interpreter():
    """Der pythonw.exe, mit dem der Sammler gestartet wird.

    [14.10.2026] Uebernommen aus trading_imperium_v7/schatten_starter.py
    (dort am 16.09. gebaut). Hier stand fest verdrahtet:

        LOCALAPPDATA\\Microsoft\\WindowsApps\\
        PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\pythonw.exe

    Diesen Pfad gibt es auf dem Windows-11-Rechner NICHT (am 14.10.
    nachgesehen: Test-Path -> False). Python liegt dort unter
    AppData\\Local\\Python\\pythoncore-3.13-64. Der alte Starter haette
    also nur "pythonw nicht gefunden" gemeldet - stiller Ausfall.

    Reihenfolge: der laufende pythonw selbst, der pythonw daneben, dann
    die ueblichen Orte (Windows Store ohne feste Versionsnummer,
    python.org). Keine Dateigroessen-Pruefung: die WindowsApps-Eintraege
    sind Verweise und melden alle 0 Byte.
    """
    eigen = sys.executable or ""
    if eigen.lower().endswith("pythonw.exe") and os.path.exists(eigen):
        return eigen

    kandidaten = []
    if eigen:
        kandidaten.append(os.path.join(os.path.dirname(eigen), "pythonw.exe"))
    lokal = os.environ.get("LOCALAPPDATA", "")
    if lokal:
        laden = os.path.join(lokal, "Microsoft", "WindowsApps")
        try:
            for u in sorted(os.listdir(laden), reverse=True):
                if u.lower().startswith("pythonsoftwarefoundation.python."):
                    kandidaten.append(os.path.join(laden, u, "pythonw.exe"))
        except OSError:
            pass
        basis = os.path.join(lokal, "Programs", "Python")
        try:
            for u in sorted(os.listdir(basis), reverse=True):
                kandidaten.append(os.path.join(basis, u, "pythonw.exe"))
        except OSError:
            pass
    if eigen:
        kandidaten.append(eigen)      # letzter Ausweg: mit Konsolenfenster

    for k in kandidaten:
        if k and os.path.exists(k):
            return k
    return ""


PYTHONW = interpreter()


def notiz(text):
    zeile = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {text}"
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except OSError:
        pass
    try:
        if sys.stdout is not None:
            print(zeile)
    except Exception:
        pass


def laeuft_schon():
    """Laeuft der Sammler DIESES Ordners?

    [UMZUG 01.09.2026] Vorher wmic - in Windows 11 entfernt. Der
    Rueckfall "im Zweifel True" griff dann IMMER, also startete
    dieser Starter nie mehr etwas. Sicher, aber wirkungslos.
    Jetzt ueber prozessliste.py (psutil).

    [14.10.2026] DER ORDNER WIRD MITGEPRUEFT. Seit dem 21.09. laeuft
    im Ordner trading_imperium_v7 ein eigenes Schatten-Universum
    (Aufgabe SchattenUniversumLIVE). Die alte Pruefung suchte nur
    "schatten_universum" in der Befehlszeile und haette den v7-Sammler
    fuer den eigenen gehalten: "laeuft bereits", kein Start. Genau so
    stand der v6-Nachlauf vom 27.09. (Rechner-Neustart 14:32) bis zum
    14.10. still - 26 v6-Verkaeufe ohne Nachlauf, im v7-Nachlauf steht
    keiner davon. Gleiche Bauart wie prozess_frische.gehoert_hierher
    (26.09.) und v7/schatten_starter.py (16.09.).

    Das vorsichtige Verhalten bleibt: laesst sich die Liste nicht
    lesen, wird True gemeldet, damit kein zweiter Laeufer entsteht.
    """
    try:
        from prozessliste import python_prozesse
        prozesse = python_prozesse()
    except Exception as e:
        notiz(f"Prozessliste nicht lesbar ({type(e).__name__}) - "
              f"kein Start, um keinen zweiten zu erzeugen")
        return True          # im Zweifel NICHT starten
    hier = os.path.normcase(os.path.abspath(HIER))
    for p in prozesse:
        aufruf = p.get("aufruf") or ""
        if "schatten_universum" not in aufruf or "starter" in aufruf:
            continue
        ordner = p.get("ordner")
        if ordner is None:
            # Arbeitsverzeichnis nicht lesbar: im Zweifel als eigener
            # werten, damit kein zweiter Sammler entsteht.
            notiz(f"Ordner von PID {p.get('pid')} nicht lesbar - "
                  f"werte ihn vorsichtshalber als eigenen")
            return True
        if os.path.normcase(os.path.abspath(ordner)) == hier:
            return True
    return False


def main():
    if laeuft_schon():
        notiz("laeuft bereits - nichts zu tun")
        return 0

    if not PYTHONW or not os.path.exists(PYTHONW):
        notiz("kein Python-Interpreter gefunden - weder neben dem eigenen "
              "Prozess noch unter WindowsApps oder Programs\\Python. "
              "Der Sammler kann nicht gestartet werden.")
        return 1

    try:
        # DETACHED_PROCESS (0x8) + CREATE_NEW_PROCESS_GROUP (0x200):
        # der Sammler haengt danach an keiner Konsole mehr.
        subprocess.Popen([PYTHONW, ZIEL, "--dauer"], cwd=HIER,
                         creationflags=0x00000008 | 0x00000200,
                         close_fds=True)
        notiz("gestartet")
        return 0
    except Exception as e:
        notiz(f"Start fehlgeschlagen: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
