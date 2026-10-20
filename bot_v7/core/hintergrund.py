# -*- coding: utf-8 -*-
"""Trading Imperium V6 - Hintergrundjobs ohne sichtbares Fenster.

DAS PROBLEM
-----------
Beim Start des Forschungs-Capture und des taeglichen Sammlers poppte ein
schwarzes CMD-Fenster auf dem Bildschirm auf. Ursache war NICHT der
Python-Code (im ganzen Projekt gibt es genau einen subprocess-Aufruf,
execution/engine.py:67), sondern die Windows-Aufgabenplanung: beide
Aufgaben liefen mit Anmeldemodus "Nur interaktiv" (InteractiveToken) und
riefen eine .bat-Datei auf. Das Fenster gehoert dem cmd.exe um die .bat
herum - pythonw allein erzeugt keines.

DIE REGEL DAHINTER
------------------
Ein Fenster zu unterdruecken ist leicht. Die Gefahr ist, dass man ein
nerviges Fenster gegen einen blinden Fleck tauscht. Genau ein blinder
Fleck - verschluckte Fehler im Event-Bus - war am 06.08.2026 das
Ausgangsproblem des ganzen Projekts: der Bot meldete "Selbsttest 8/8 OK",
waehrend er 14.986 Auftraege verwarf.

Deshalb gilt hier:
  - stderr wird NIEMALS verworfen, immer ins Log geschrieben
  - jeder Job meldet Start, Ende, PID, Exit-Code, Laufzeit und
    Fehlerauszug in die Telemetrie-Tabelle `jobs`
  - Fehlschlaege landen zusaetzlich als Ticket in tickets.txt
  - keine leeren except-Bloecke

DOPPELSTART
-----------
Jeder Job haelt eine Sperrdatei mit der eigenen PID. Laeuft schon einer,
bricht der zweite sauber ab (Rueckgabe 0, Status UEBERSPRUNGEN) statt sich
mit dem ersten zu pruegeln. Genau das war am 07.08. die Ursache von
WinError 5: zwei Prozesse auf derselben Datei.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    from config.settings import DATA_DIR
except Exception:
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

PROJEKT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_ORDNER = os.path.join(DATA_DIR, "jobs")
TICKETS = os.path.join(PROJEKT, "tickets.txt")

# Ab dieser Groesse wird die Logdatei weggerollt. 2 MB reichen fuer
# mehrere Tage und bleiben mit einem Texteditor oeffenbar.
MAX_LOG_BYTES = 2 * 1024 * 1024
BEHALTE_ALTE = 5

# Nur auf Windows vorhanden. Sorgt dafuer, dass der Kindprozess KEIN
# Konsolenfenster bekommt - auch dann nicht, wenn der Elternprozess
# selbst keines hat (pythonw).
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _jetzt():
    return datetime.now(timezone.utc).isoformat()


def _rollen(pfad):
    """Rollt die Logdatei weg, wenn sie zu gross wird. Nie loeschen."""
    try:
        if os.path.exists(pfad) and os.path.getsize(pfad) > MAX_LOG_BYTES:
            for i in range(BEHALTE_ALTE - 1, 0, -1):
                alt, neu = f"{pfad}.{i}", f"{pfad}.{i + 1}"
                if os.path.exists(alt):
                    os.replace(alt, neu)
            os.replace(pfad, pfad + ".1")
    except Exception:
        pass          # ein Rollfehler darf den Job nicht verhindern


def _ticket(text):
    """Haelt einen Fehlschlag in tickets.txt fest. Fehler verschwinden nicht."""
    try:
        with open(TICKETS, "a", encoding="utf-8") as f:
            f.write("BUG: " + str(text).replace("\n", " ")[:900] + "\n")
        return True
    except Exception:
        return False


class Sperre:
    """Verhindert den doppelten Start desselben Jobs."""

    def __init__(self, name):
        self.pfad = os.path.join(LOG_ORDNER, f"{name}.pid")
        self.gehalten = False

    def __enter__(self):
        os.makedirs(LOG_ORDNER, exist_ok=True)
        if os.path.exists(self.pfad):
            try:
                with open(self.pfad, "r", encoding="utf-8") as f:
                    alte_pid = int((f.read() or "0").strip() or 0)
            except Exception:
                alte_pid = 0
            if alte_pid and _laeuft_noch(alte_pid):
                self.gehalten = False
                return self
            # Verwaiste Sperre eines abgestuerzten Laufs - darf nicht
            # dauerhaft blockieren.
            try:
                os.remove(self.pfad)
            except Exception:
                pass
        try:
            with open(self.pfad, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            self.gehalten = True
        except Exception:
            self.gehalten = False
        return self

    def __exit__(self, *a):
        if self.gehalten:
            try:
                os.remove(self.pfad)
            except Exception:
                pass
        return False


def _laeuft_noch(pid):
    """True, wenn ein Prozess mit dieser PID existiert.

    [BUGFIX 11.08.2026] Die erste Fassung nutzte text=True. Python
    dekodiert die Ausgabe dann mit cp1252 - tasklist antwortet auf einem
    deutschen Windows aber in cp850. Beim ersten Umlaut brach die
    Dekodierung ab:

        UnicodeDecodeError: 'charmap' codec can't decode byte 0x81

    Die Ausnahme fiel in einem Lesethread an, blieb also unauffaellig,
    und stdout kam leer zurueck. Ergebnis: die Funktion haette
    "Prozess laeuft nicht" gemeldet, obwohl er laeuft - und damit die
    Doppelstart-Sperre geoeffnet. Eine Schutzfunktion, die im Fehlerfall
    AUFMACHT statt zuzuhalten, ist schlimmer als keine: zwei Prozesse
    auf derselben Datei waren am 07.08. die Ursache von WinError 5.

    Jetzt werden Bytes gelesen und selbst dekodiert, Fehlzeichen ersetzt.
    """
    try:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"],
                           capture_output=True, timeout=15,
                           creationflags=CREATE_NO_WINDOW)
        ausgabe = (r.stdout or b"").decode("cp850", errors="replace")
        return str(pid) in ausgabe
    except Exception:
        return True       # im Zweifel als "laeuft" behandeln, nicht doppelt starten


def starte_still(job_name, argv, cwd=None, telemetrie=None, timeout=None,
                 ok_codes=(0,)):
    """Startet einen Job OHNE Fenster und protokolliert ihn vollstaendig.

    job_name  Name in Log und Telemetrie, z.B. "forschung_capture"
    argv      Liste, z.B. [sys.executable, "sammler.py"]
    cwd       Arbeitsverzeichnis (Vorgabe: Projektordner)
    telemetrie  optionales Telemetrie-Objekt; fehlt es, wird nur geloggt
    timeout   Sekunden bis zum Abbruch; None = unbegrenzt (Daemon)
    ok_codes  Exit-Codes, die KEIN Fehler sind (Vorgabe: nur 0)

    Rueckgabe: Exit-Code des Kindprozesses. 0 = in Ordnung.
               Bei bereits laufendem Job: 0 (uebersprungen, kein Fehler).

    ZU ok_codes - eine Lehre vom ersten Betriebstag
    -----------------------------------------------
    capture_daemon.py beendet sich mit Code 3, wenn bereits eine Instanz
    laeuft, und schreibt dazu selbst: "Das ist der Normalfall bei jedem
    Watchdog-Lauf." Die erste Fassung wertete jeden Code ungleich 0 als
    Fehler und legte ein Ticket an - bei einem 10-Minuten-Takt waeren das
    144 BUG-Tickets pro Tag gewesen.

    Das ist derselbe Fehler wie ein verschluckter Fehler, nur andersherum:
    ertraenkt man das Wichtige in Routine, sieht man es genauso wenig.
    Ein Wachhund, der bei jedem Blatt bellt, ist kein Wachhund.

    Der tatsaechliche Code wird trotzdem in der Spalte exit_code
    festgehalten - "3 = uebersprungen" bleibt also von "0 = gelaufen"
    unterscheidbar.
    """
    os.makedirs(LOG_ORDNER, exist_ok=True)
    logpfad = os.path.join(LOG_ORDNER, f"{job_name}.log")
    _rollen(logpfad)
    befehl = " ".join(str(a) for a in argv)

    with Sperre(job_name) as sperre:
        if not sperre.gehalten:
            with open(logpfad, "a", encoding="utf-8") as f:
                f.write(f"\n===== {_jetzt()} UEBERSPRUNGEN - laeuft bereits =====\n")
            if telemetrie is not None:
                zid = telemetrie.job_start(job_name, os.getpid(), logpfad, befehl)
                telemetrie.job_ende(zid, exit_code=0, status="UEBERSPRUNGEN",
                                    fehlerauszug="Doppelstart verhindert")
            return 0

        # Verwaiste Zeilen frueherer Laeufe schliessen, bevor eine neue
        # aufgemacht wird. Sonst behauptet die Tabelle, alte Jobs liefen noch.
        if telemetrie is not None:
            try:
                telemetrie.jobs_aufraeumen(_laeuft_noch)
            except Exception:
                pass

        beginn = time.time()
        zid = None
        proc = None
        try:
            with open(logpfad, "a", encoding="utf-8") as f:
                f.write(f"\n===== {_jetzt()} START =====\n")
                f.write(f"Befehl: {befehl}\n")
                f.flush()
                # stdout UND stderr in dieselbe Datei. stderr wird
                # ausdruecklich nicht verworfen.
                # [PUFFER-FIX 11.08.2026] PYTHONUNBUFFERED ist hier keine
                # Feinheit, sondern der Kern der Sache. Schreibt Python in
                # eine Datei statt auf ein Terminal, sammelt es die Ausgabe
                # blockweise und gibt sie erst beim Beenden heraus. Ein Job,
                # der HAENGT, beendet sich aber nie - seine Ausgabe geht beim
                # Abbruch restlos verloren.
                #
                # Genau das ist am 10.08. passiert: der Sammler blieb stehen
                # und hinterliess in sammler.log nur die Startzeile, keine
                # einzige Zeile Inhalt. Dadurch war nicht feststellbar, an
                # welchem Schritt er haengt - und der Ausfall fiel zwei Tage
                # lang niemandem auf.
                #
                # Unbuffered heisst: jede Zeile steht sofort in der Datei.
                # Beim naechsten Haenger sieht man den letzten erreichten
                # Schritt. Ein Log, das erst beim erfolgreichen Ende
                # erscheint, ist genau dann leer, wenn man es braucht.
                umgebung = dict(os.environ)
                umgebung["PYTHONUNBUFFERED"] = "1"
                proc = subprocess.Popen(
                    argv, cwd=cwd or PROJEKT, stdout=f, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW,
                    env=umgebung)
            if telemetrie is not None:
                zid = telemetrie.job_start(job_name, proc.pid, logpfad, befehl)
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            code = -1
            with open(logpfad, "a", encoding="utf-8") as f:
                f.write(f"===== {_jetzt()} ABBRUCH nach Zeitueberschreitung =====\n")
            if telemetrie is not None:
                telemetrie.job_ende(zid, exit_code=code, status="ABGEBROCHEN",
                                    fehlerauszug=f"Timeout nach {timeout}s")
            _ticket(f"Hintergrundjob {job_name} nach {timeout}s abgebrochen "
                    f"({_jetzt()}). Log: {logpfad}")
            return code
        except Exception as fehler:
            code = -2
            hinweis = f"{type(fehler).__name__}: {fehler}"
            try:
                with open(logpfad, "a", encoding="utf-8") as f:
                    f.write(f"===== {_jetzt()} START FEHLGESCHLAGEN: {hinweis} =====\n")
            except Exception:
                pass
            if telemetrie is not None:
                telemetrie.job_ende(zid, exit_code=code, fehlerauszug=hinweis)
            _ticket(f"Hintergrundjob {job_name} liess sich nicht starten: "
                    f"{hinweis} ({_jetzt()})")
            return code

        dauer = round(time.time() - beginn, 1)
        in_ordnung = code in tuple(ok_codes or (0,))
        auszug = "" if in_ordnung else _letzte_zeilen(logpfad, 25)
        with open(logpfad, "a", encoding="utf-8") as f:
            f.write(f"===== {_jetzt()} ENDE - Exit-Code {code}, {dauer}s"
                    f"{'' if in_ordnung else ' (FEHLER)'} =====\n")
        if telemetrie is not None:
            telemetrie.job_ende(zid, exit_code=code, fehlerauszug=auszug,
                                status="OK" if in_ordnung else "FEHLER")
        if not in_ordnung:
            _ticket(f"Hintergrundjob {job_name} endete mit Exit-Code {code} "
                    f"nach {dauer}s ({_jetzt()}). Log: {logpfad}")
        return code


def _letzte_zeilen(pfad, anzahl=25):
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-anzahl:])
    except Exception:
        return ""


def hole_telemetrie():
    """Telemetrie-Objekt, oder None. Ein DB-Fehler darf keinen Job stoppen."""
    try:
        sys.path.insert(0, PROJEKT)
        from core.telemetrie import Telemetrie
        return Telemetrie()
    except Exception:
        return None
