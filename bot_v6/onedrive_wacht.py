# -*- coding: utf-8 -*-
"""
onedrive_wacht.py - passt auf, dass das Projekt nicht wieder in die Cloud rutscht
=================================================================================
WARUM ES DIESE DATEI GIBT

Am 03.09.2026 lag das Projekt auf dem Desktop, und der Desktop war nach
C:\\Users\\<Benutzer>\\OneDrive\\Desktop umgeleitet. OneDrive hat damit in
den laufenden Projektordner hineinsynchronisiert. Die Folgen:

  * 6318 Konfliktkopien, 1,6 GB "- Kopie"-Muell im Projekt
  * Um 16:04 wurde per Doppelklick ein ZWEITER Bot aus dem OneDrive-Ordner
    gestartet, waehrend der erste noch lief. Port 5050 kann nur einer
    halten - fuenf Stunden lang zwei getrennte Datenbestaende, die
    danach von Hand zusammengefuehrt werden mussten.
  * Sieben Stunden Telemetrie vom 02./03.09. sind dabei endgueltig
    verloren. Die gibt es nicht wieder.

Am 05.09.2026 wurde die OneDrive-Sicherung fuer den Desktop abgeschaltet
und das Projekt auf den nun wieder lokalen Desktop gelegt.

    DAS PROBLEM IST DAMIT BEHOBEN - ABER NICHT DAUERHAFT GESICHERT.

OneDrive schaltet die Ordnersicherung gerne von selbst wieder ein: nach
einem Windows-Update, nach einer Neuanmeldung, oder wenn jemand eine der
Nachfragen ("Ihre Dateien sichern?") wegklickt. Passiert das, liegt das
Projekt ohne jede Warnung wieder in der Cloud und das Theater vom
03.09. faengt von vorne an.

Dieser Waechter prueft genau das - und zwar so, dass man es nicht
uebersieht: er schreibt ein Ticket in tickets.txt, das der Bot selbst
ins ENTWICKLERHANDBUCH uebernimmt.

Aufruf:
    python onedrive_wacht.py           prueft und meldet
    python onedrive_wacht.py --leise   nur Rueckgabewert, keine Ausgabe

Rueckgabewert: 0 = alles in Ordnung, 1 = Projekt ist in Gefahr.
"""
import os
import sys
import time

PROJEKT = os.path.dirname(os.path.abspath(__file__))
TICKETS = os.path.join(PROJEKT, "tickets.txt")


def desktop_pfad():
    """Liest aus der Registry, wohin Windows den Desktop zeigen laesst."""
    try:
        import winreg
        schluessel = (r"Software\Microsoft\Windows\CurrentVersion"
                      r"\Explorer\User Shell Folders")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, schluessel) as k:
            roh, _ = winreg.QueryValueEx(k, "Desktop")
        return os.path.expandvars(roh)
    except Exception:
        return None


def liegt_in_onedrive(pfad):
    """Wahr, wenn der Pfad unterhalb eines OneDrive-Ordners liegt."""
    if not pfad:
        return False
    teile = os.path.normpath(pfad).lower().split(os.sep)
    return any(t.startswith("onedrive") for t in teile)


def pruefen():
    """Gibt eine Liste von Befunden zurueck. Leer = alles in Ordnung."""
    befunde = []

    d = desktop_pfad()
    if d is None:
        befunde.append("Der Desktop-Pfad war nicht aus der Registry lesbar - "
                       "die Pruefung konnte NICHT stattfinden.")
    elif liegt_in_onedrive(d):
        befunde.append(f"Der Desktop ist wieder nach OneDrive umgeleitet: {d}. "
                       "Damit synchronisiert OneDrive alles, was dort liegt.")

    if liegt_in_onedrive(PROJEKT):
        befunde.append(f"DER PROJEKTORDNER SELBST LIEGT IN ONEDRIVE: {PROJEKT}. "
                       "Das ist der Zustand, der am 03.09.2026 zu zwei "
                       "parallel laufenden Bots und sieben verlorenen "
                       "Stunden Telemetrie gefuehrt hat.")

    # Konfliktkopien zaehlen - aber nur FRISCHE. Aus der Aufraeumaktion
    # vom 03.09.2026 liegen zwei alte Reste im Projekt (_- Kopie.env,
    # _- Kopie.gitignore). Die duerfen keinen Daueralarm ausloesen, sonst
    # gewoehnt man sich an die Meldung und uebersieht den echten Fall.
    frisch_ab = time.time() - 3 * 24 * 3600
    kopien = []
    try:
        for name in os.listdir(PROJEKT):
            if " - Kopie" not in name and "-Kopie" not in name:
                continue
            try:
                if os.path.getmtime(os.path.join(PROJEKT, name)) < frisch_ab:
                    continue
            except OSError:
                continue
            kopien.append(name)
            if len(kopien) >= 5:
                break
    except Exception:
        pass
    if kopien:
        befunde.append("Es sind in den letzten drei Tagen neue Konfliktkopien "
                       "im Projekt aufgetaucht (z.B. " + ", ".join(kopien[:3]) +
                       ") - ein sicheres Zeichen, dass OneDrive mitschreibt.")

    return befunde


def ticket_schreiben(befunde):
    try:
        teile = ["BUG: ONEDRIVE GREIFT WIEDER AUF DAS PROJEKT ZU - "
                 f"automatisch gemeldet vom OneDrive-Waechter am "
                 f"{time.strftime('%d.%m.%Y %H:%M')}."]
        teile.extend(befunde)
        teile.append("Sofort pruefen: OneDrive-Einstellungen -> Synchronisierung "
                     "und Sicherung -> Sicherung verwalten -> Desktop AUSschalten. "
                     "Solange das offen ist, NICHT zwei Bots starten.")
        with open(TICKETS, "a", encoding="utf-8") as f:
            f.write("\n\n" + " ".join(teile) + "\n")
        return True
    except Exception as e:
        print(f"  Ticket konnte nicht geschrieben werden: {str(e)[:80]}")
        return False


def main():
    leise = "--leise" in sys.argv
    befunde = pruefen()

    if not befunde:
        if not leise:
            print("=" * 62)
            print("ONEDRIVE-WAECHTER - alles in Ordnung")
            print("=" * 62)
            print(f"  Desktop  : {desktop_pfad()}")
            print(f"  Projekt  : {PROJEKT}")
            print("  Weder der Desktop noch der Projektordner liegen in OneDrive.")
        return 0

    if not leise:
        print("=" * 62)
        print("ONEDRIVE-WAECHTER - ACHTUNG")
        print("=" * 62)
        for b in befunde:
            print(f"  - {b}")
        print()
        print("  So wird es abgestellt:")
        print("    OneDrive-Symbol (unten rechts) -> Zahnrad -> Einstellungen")
        print("    -> Synchronisierung und Sicherung -> Sicherung verwalten")
        print("    -> Schalter bei 'Desktop' AUSschalten")
        print()
        print("  Bis dahin NICHT aus zwei Ordnern gleichzeitig starten.")

    ticket_schreiben(befunde)
    return 1


if __name__ == "__main__":
    sys.exit(main())
