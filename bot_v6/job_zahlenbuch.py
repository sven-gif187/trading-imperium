# -*- coding: utf-8 -*-
"""Taeglicher Morgen-Lauf: Zahlenbuch als PDF + LAGE.md neu schreiben.
[CLEANUP-KEEP]

Wird von der Windows-Aufgabenplanung ("TI6-Zahlenbuch") per pythonw.exe
aufgerufen - also OHNE Fenster.

    pythonw.exe "<Projekt>\\job_zahlenbuch.py"

Von Hand testen (dann sieht man die Ausgabe):
    python job_zahlenbuch.py

WAS ER TUT
  1. ZAHLENBUCH_<datum>.pdf erzeugen (Belege des Vortags/Standes)
  2. LAGE.md neu schreiben (was laeuft, welche Daten es gibt)
  3. Beides in die Job-Telemetrie eintragen, damit ein Ausfall auffaellt

WICHTIG - KEIN UNGESCHUETZTES print()
Unter pythonw.exe ist sys.stdout None. Ein ungeschuetztes print() wirft dort
und beendet den Job, bevor er etwas tut. Genau dieser Fehler ist am
14.08.2026 beim Schatten-Universum passiert: der Prozess stand in der
Prozessliste, das Log blieb leer, und von aussen sah es aus, als liefe er.
Deshalb laeuft hier JEDE Ausgabe ueber melde().

Er liest nur und schreibt Berichte. Er aendert nichts am Bot.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HIER, "data_store", "zahlenbuch_job.log")


def melde(text):
    zeile = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {text}"
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except Exception:
        pass
    try:
        print(zeile)
    except Exception:
        pass          # pythonw: kein stdout - kein Grund abzubrechen


def starte(skript, beschreibung, *args):
    """Ruft ein Skript in einem eigenen Prozess auf.

    Bewusst als Unterprozess und nicht als Import: ein Fehler in einem
    Bericht darf den anderen nicht mitreissen.
    """
    start = time.time()
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HIER, skript), *args],
            cwd=HIER, capture_output=True, text=True, errors="replace",
            timeout=900)
        dauer = time.time() - start
        if r.returncode == 0:
            letzte = (r.stdout or "").strip().splitlines()
            melde(f"OK   {beschreibung} ({dauer:.0f}s) "
                  f"{letzte[-1] if letzte else ''}")
            return True
        melde(f"FEHLER {beschreibung}: Code {r.returncode} | "
              f"{(r.stderr or '')[-300:]}")
        return False
    except subprocess.TimeoutExpired:
        melde(f"FEHLER {beschreibung}: Zeitgrenze (15 min) ueberschritten")
        return False
    except Exception as e:
        melde(f"FEHLER {beschreibung}: {str(e)[:200]}")
        return False


def in_telemetrie(name, ok, dauer):
    """Job-Ergebnis in die Telemetrie, damit ein Ausfall auffaellt.

    Der Bot fuehrt eine jobs-Tabelle und meldet stille Ausfaelle. Ein
    Bericht, der wochenlang nicht mehr entsteht, faellt sonst niemandem auf.
    """
    try:
        sys.path.insert(0, HIER)
        from core.telemetrie import Telemetrie
        tel = Telemetrie()
        # [BEFUND 80, 26.08.2026] Der echte Startzeitpunkt wird
        # nachgereicht. Vorher standen job_start() und job_ende() hier
        # direkt hintereinander - beide NACH getaner Arbeit -, also war
        # start == ende und laufzeit_sek = 0,0. Der Parameter `dauer`
        # kam schon immer herein und wurde nur nie benutzt.
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        _start = (_dt.now(_tz.utc) - _td(seconds=float(dauer or 0))).isoformat()
        zid = tel.job_start(name, pid=os.getpid(), befehl="job_zahlenbuch.py",
                            start_utc=_start)
        tel.job_ende(zid, exit_code=0 if ok else 1,
                     fehlerauszug="" if ok else "siehe zahlenbuch_job.log")
    except Exception:
        pass


def main():
    start = time.time()
    melde("=" * 54)
    melde("Morgen-Lauf gestartet")

    ok1 = starte("zahlenbuch.py", "Zahlenbuch (PDF)")
    # [19.08.2026] Die Markdown-Fassung gehoert dazu, sonst altert sie still
    # neben einem frischen PDF - genau der Fehler, der beim Handbuch-PDF eine
    # Woche lang unbemerkt blieb (Handbuch 4.57).
    ok1b = starte("zahlenbuch.py", "Zahlenbuch (Markdown)", "--md")
    ok2 = starte("lage_erzeugen.py", "LAGE.md")

    dauer = time.time() - start
    melde(f"Fertig in {dauer:.0f}s | Zahlenbuch PDF {'OK' if ok1 else 'FEHLER'} | "
          f"MD {'OK' if ok1b else 'FEHLER'} | LAGE {'OK' if ok2 else 'FEHLER'}")
    alle = ok1 and ok1b and ok2
    in_telemetrie("zahlenbuch_morgen", alle, dauer)
    return 0 if alle else 1


if __name__ == "__main__":
    sys.exit(main())
