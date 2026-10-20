"""Waechter fuer die Frische-Pruefung - laeuft von selbst, meldet sich nur bei Bedarf.

NUR LESEND, was den Bot angeht. Schreibt ausschliesslich ein eigenes
Log, eine eigene Merkdatei und im Bedarfsfall eine Zeile in tickets.txt.

WARUM ES DIESES SKRIPT GIBT
---------------------------
prozess_frische.py beantwortet die Frage "laeuft irgendwo noch alter
Programmtext?" - aber nur, wenn jemand sie stellt. Am 17.08.2026 hat
sie niemand gestellt, und die sechs neu ergaenzten Muenzen sammelten
einen ganzen Tag lang nichts (Handbuch 4.49).

> Eine Pruefung, die man von Hand aufrufen muss, wird genau dann
> vergessen, wenn sie gebraucht wird.

Dieser Waechter ruft sie selbst auf. Er wird von zwei Seiten
angestossen:

  1. stuendlich  ueber die Windows-Aufgabenplanung ("ProzessFrische")
  2. nach jedem Commit ueber .git/hooks/post-commit

WARUM ER NICHT BEI JEDEM LAUF SCHREIT
-------------------------------------
Er meldet nur den WECHSEL des Zustands: von "frisch" nach "Neustart
faellig". Solange sich nichts aendert, schreibt er still ins Log.
Sonst stuende stuendlich dieselbe Zeile in tickets.txt, und nach zwei
Tagen liest sie niemand mehr - derselbe Gewoehnungseffekt, an dem die
erste Fassung von prozess_frische.py schon einmal gescheitert ist.

Aufruf von Hand:  python prozess_frische_wacht.py
Rueckgabewert:    0 = alles frisch, 1 = Neustart faellig
"""
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HIER, "data_store", "prozess_frische.log")
MERKER = os.path.join(HIER, "data_store", "prozess_frische_stand.txt")
TICKETS = os.path.join(HIER, "tickets.txt")


def notiz(text):
    """Erst schreiben, dann anzeigen - und print NIE ungeschuetzt.

    Unter pythonw.exe (so laufen die Hintergrundjobs) ist sys.stdout
    None; ein blankes print() beendet dann das ganze Programm. Der
    Prozess stuende in der Liste und taete nichts. Diese Falle hat am
    14.08.2026 das Schatten-Universum lahmgelegt.
    """
    zeile = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {text}"
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except OSError:
        pass
    try:
        if sys.stdout is not None:
            print(zeile)
    except Exception:
        pass


def voriger_stand():
    try:
        with open(MERKER, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def stand_merken(wert):
    try:
        os.makedirs(os.path.dirname(MERKER), exist_ok=True)
        with open(MERKER, "w", encoding="utf-8") as f:
            f.write(wert)
    except OSError:
        pass


def ticket(text):
    """Eine Zeile in tickets.txt - der Bot traegt sie ins Handbuch ein."""
    try:
        with open(TICKETS, "a", encoding="utf-8") as f:
            f.write(f"\nBUG: {text}\n")
        return True
    except OSError:
        return False


def main():
    # Die Pruefung selbst liegt in prozess_frische.py und wird hier nur
    # aufgerufen - eine Kopie der Logik waere die naechste Fehlerquelle.
    sys.path.insert(0, HIER)
    try:
        import prozess_frische
    except Exception as e:
        notiz(f"FEHLER: prozess_frische.py nicht ladbar ({type(e).__name__}: {e})")
        return 2

    puffer = io.StringIO()
    try:
        with redirect_stdout(puffer):
            code = prozess_frische.main()
    except Exception as e:
        notiz(f"FEHLER beim Pruefen ({type(e).__name__}: {e})")
        return 2

    bericht = puffer.getvalue()
    faellig = code == 1

    # Welche Prozesse betroffen sind - fuer die Meldung.
    betroffen = [z.strip().rstrip(" (PID") for z in bericht.splitlines()
                 if z and not z.startswith((" ", "\t", "=", "-", "(")) and "(PID" in z]
    kurz = ", ".join(b.split(" (PID")[0] for b in betroffen) or "unbekannt"

    stand = "faellig" if faellig else "frisch"
    vorher = voriger_stand()

    if not faellig:
        notiz("alles frisch - kein Prozess laeuft mit altem Programmtext")
        stand_merken(stand)
        return 0

    notiz(f"NEUSTART FAELLIG: {kurz}")
    for zeile in bericht.splitlines():
        if "ACHTUNG" in zeile or zeile.strip().startswith(("18.", "17.", "16.")):
            notiz("  " + zeile.strip())

    # Nur beim WECHSEL ein Ticket - sonst stuende hier stuendlich dasselbe.
    if vorher != stand:
        if ticket(f"Frische-Pruefung: mindestens ein Prozess laeuft mit "
                  f"veraltetem Programmtext ({kurz}). Aenderung wirkt erst "
                  f"nach einem Neustart. Einzelheiten: "
                  f"python prozess_frische.py - Handbuch 4.49."):
            notiz("Ticket geschrieben (Zustandswechsel frisch -> faellig)")
    else:
        notiz("kein neues Ticket - Zustand unveraendert seit dem letzten Lauf")

    stand_merken(stand)
    return 1


if __name__ == "__main__":
    sys.exit(main())
