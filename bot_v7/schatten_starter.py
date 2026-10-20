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

    [16.09.2026] WARUM DER PFAD NICHT MEHR VERDRAHTET IST
    ----------------------------------------------------
    Hier stand fest eingetragen:

        LOCALAPPDATA\\Microsoft\\WindowsApps\\
        PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\pythonw.exe

    Das gilt fuer DIESEN Rechner (Windows 10, Python 3.13). Sven zieht
    den Ordner auf seinen Rechner mit Windows 11 um; steht dort eine
    andere Python-Version, zeigt der Eintrag ins Leere. Der Starter
    meldet dann brav "pythonw nicht gefunden", die geplante Aufgabe
    meldet Erfolg - und die Datensammlung steht still. Genau der stille
    Ausfall, gegen den dieses Skript gebaut wurde.

    Die verlaesslichste Quelle ist der laufende Prozess selbst: laeuft
    dieses Skript bereits unter pythonw, ist die Frage beantwortet.
    Sonst wird der pythonw daneben genommen, danach die ueblichen
    Installationsorte von python.org.

    NICHT geprueft wird die DATEIGROESSE. Die Eintraege unter
    WindowsApps sind Verweise, keine Dateien - sie melden alle 0 Byte,
    die funktionierenden wie die Attrappen (am 16.09. nachgemessen).
    """
    eigen = sys.executable or ""
    if eigen.lower().endswith("pythonw.exe") and os.path.exists(eigen):
        return eigen

    kandidaten = []
    if eigen:
        kandidaten.append(os.path.join(os.path.dirname(eigen), "pythonw.exe"))
    lokal = os.environ.get("LOCALAPPDATA", "")
    if lokal:
        # Der Weg ueber den Windows Store, wie bisher - aber ohne feste
        # Versionsnummer: der passende Ordner wird gesucht, nicht geraten.
        laden = os.path.join(lokal, "Microsoft", "WindowsApps")
        try:
            # Der Punkt hinter "Python" ist wichtig: daneben liegt ein
            # Ordner "PythonSoftwareFoundation.PythonManager_...", der
            # kein pythonw.exe enthaelt. reverse=True nimmt die hoechste
            # Versionsnummer zuerst.
            for u in sorted(os.listdir(laden), reverse=True):
                if u.lower().startswith("pythonsoftwarefoundation.python."):
                    kandidaten.append(os.path.join(laden, u, "pythonw.exe"))
        except OSError:
            pass
        # Und der Weg ueber python.org.
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

    [16.09.2026] WARUM DER ORDNER MITGEPRUEFT WERDEN MUSS
    ----------------------------------------------------
    Seit dem 14.09. gibt es zwei Ordner: trading_imperium_v6(21) fuer
    den Papierhandel und trading_imperium_LIVE fuer echtes Geld. In
    beiden laeuft ein Schatten-Universum.

    Die alte Pruefung durchsuchte nur die Befehlszeile nach
    "schatten_universum" - und die sieht je nach Startart so aus:

        ...\\trading_imperium_v6(21)\\schatten_universum.py --dauer
        schatten_universum.py --dauer          <- relativ, kein Ordner!

    Der zweite Fall entsteht, wenn der Sammler aus seinem eigenen
    Ordner gestartet wird, also im Normalfall. Damit kann die alte
    Pruefung LIVE und Papier NICHT unterscheiden.

    Die Folge waere genau das Gegenteil dessen, wofuer dieses Skript
    gebaut wurde: Stirbt der LIVE-Sammler, sieht der Starter den
    Papier-Sammler, meldet "laeuft bereits" und startet nichts. Die
    Datensammlung stuende still, und im Log stuende, alles sei in
    Ordnung.

    psutil kennt das Arbeitsverzeichnis jedes Prozesses - damit ist
    die Frage eindeutig zu beantworten. Fehlt psutil, bleibt der alte
    Weg als Rueckfall; dann ist die Aussage unschaerfer, aber immer
    noch besser als gar keine.
    """
    try:
        import psutil
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cl = " ".join(p.info["cmdline"] or [])
                if "schatten_universum" not in cl or "starter" in cl:
                    continue
                # Der entscheidende Vergleich: eigener Ordner?
                if os.path.normcase(p.cwd()) == os.path.normcase(HIER):
                    return True
            except Exception:
                continue          # Prozess weg oder kein Zugriff
        return False
    except ImportError:
        pass

    # Rueckfall ohne psutil: Befehlszeile durchsuchen. Erkennt den
    # eigenen Ordner nur, wenn er im Pfad steht.
    try:
        roh = subprocess.run(
            ["wmic", "process", "where", "name like '%python%'",
             "get", "CommandLine"],
            capture_output=True, text=True, timeout=120).stdout
    except Exception as e:
        notiz(f"Prozessliste nicht lesbar ({type(e).__name__}) - "
              f"kein Start, um keinen zweiten zu erzeugen")
        return True          # im Zweifel NICHT starten
    notiz("psutil fehlt - pruefe nur die Befehlszeile, kann LIVE und "
          "Papier nicht sicher unterscheiden")
    return any("schatten_universum" in z and "starter" not in z
               for z in roh.splitlines())


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
