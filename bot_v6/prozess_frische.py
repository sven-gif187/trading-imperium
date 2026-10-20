"""Frische-Pruefung: laeuft irgendwo noch alter Programmtext?

NUR LESEND. Startet nichts, beendet nichts, aendert keine Datei.

WARUM ES DIESES SKRIPT GIBT
---------------------------
Am 17.08.2026 wurden sechs Muenzen ergaenzt (SUI, OP, APT, ARB, INJ,
RENDER) - in der Datei. Die beiden Sammler liefen aber seit dem 14.08.
ununterbrochen weiter und arbeiteten die ganze Zeit mit der alten
Liste. Python liest den Programmtext NUR BEIM START; eine Aenderung an
der Datei erreicht einen laufenden Prozess nie.

Im Log stand jede Stunde brav "12/12 Muenzen". Die Uebergabe an den
naechsten Chat behauptete "jetzt 18 Muenzen". Beides sah nach Erfolg
aus, und einen ganzen Tag lang sammelten die sechs neuen Muenzen
nichts. Gemerkt hat es niemand, weil niemand die beiden Zahlen
nebeneinandergelegt hat.

Die Frage, die dieses Skript beantwortet:
    "Wenn ich heute etwas geaendert habe - wirkt es ueberhaupt?"

WIE ENTSCHIEDEN WIRD, WELCHE DATEI ZAEHLT
-----------------------------------------
Zwei Anlaeufe waren zu grob und meldeten Fehlalarm - beide stehen hier
als Warnung, weil der zweite genau so aussah wie eine Loesung:

1. "jede geaenderte .py-Datei zaehlt". Meldete sofort Auswertungs-
   skripte, die kein laufender Prozess je laedt.
2. "eine Datei im Hauptordner zaehlt, wenn sie irgendwo importiert
   wird". Hielt genau so lange, bis ein zweites Werkzeug
   prozess_frische.py selbst importierte - schon galt es fuer jeden
   Prozess als wichtig.

Richtig ist nur der genaue Weg: Fuer jeden Prozess wird von seiner
Startdatei aus die IMPORTKETTE verfolgt - was importiert sie, was
importieren diese Dateien, und so weiter. Nur was in dieser Kette
liegt, kann der Prozess geladen haben. Alles andere ist ihm egal.

    Eine Warnlampe, die grundlos leuchtet, schaut sich nach drei Tagen
    niemand mehr an. Ein Pruefwerkzeug mit Fehlalarmen ist schlimmer
    als keines - es erzeugt Gewoehnung.

Aufruf:  python prozess_frische.py
Rueckgabewert: 0 = alles frisch, 1 = mindestens ein Neustart faellig

Automatisch laeuft die Pruefung ueber prozess_frische_wacht.py
(stuendlich per Aufgabenplanung und nach jedem Commit).
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))

# Ordner, die nicht zaehlen: Vorgaenger-Code, Sicherungskopien,
# uebersetzter Zwischencode, Datenordner.
IGNORIEREN = ("v4_referenz", "__pycache__", ".git", "backup", "zahlenbuecher")

# Welcher Prozess gilt als welcher Job - erkannt am Aufruf.
# Zweiter Eintrag: die Startdatei, von der aus die Importkette laeuft.
JOBS = [
    ("app.py",                "Bot",                "app.py"),
    ("schatten_universum.py", "Schatten-Universum", "schatten_universum.py"),
    ("capture_daemon.py",     "Forschungs-Sammler",
     os.path.join("docs", "forschungsprogramm_2026-07", "capture",
                  "capture_daemon.py")),
    ("job_forschung_capture", "Forschungs-Sammler (Starter)",
     "job_forschung_capture.py"),
    ("sammler.py",            "Taeglicher Sammler", "sammler.py"),
    # [19.08.2026] Neuer Sammler fuer die Ausstiegsanalyse. Gehoert hierher,
    # weil er dieselbe Falle hat wie die anderen: er laeuft tagelang durch,
    # und eine Codeaenderung wirkt erst nach einem Neustart.
    ("positionsverlauf.py",   "Positionsverlauf",   "positionsverlauf.py"),
]

IMPORT_MUSTER = re.compile(
    r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))",
    re.M)


def prozesse():
    """Alle laufenden Python-Prozesse mit Startzeit und Aufruf.

    [UMZUG 01.09.2026] Hier stand ein wmic-Aufruf. wmic ist aus
    Windows 11 entfernt (hier 10.0.26200) - der Aufruf warf
    FileNotFoundError, und dieses Werkzeug meldete danach bei JEDEM
    Lauf "Prozessliste nicht lesbar". Ehrlich, aber unbrauchbar.
    Jetzt ueber prozessliste.py (psutil, gepinnt in requirements.txt).

    Das laute Scheitern bleibt: kann die Liste gar nicht gelesen
    werden, wird das gesagt und [] zurueckgegeben - nicht so getan,
    als liefe nichts.
    """
    try:
        from prozessliste import python_prozesse
        return python_prozesse()
    except Exception as e:
        print(f"Prozessliste nicht lesbar ({type(e).__name__}). "
              f"Ohne sie kann ich nichts pruefen.")
        return []


def _module_einer_datei(pfad):
    try:
        with open(pfad, encoding="utf-8", errors="ignore") as f:
            inhalt = f.read()
    except OSError:
        return []
    namen = []
    for a, b in IMPORT_MUSTER.findall(inhalt):
        namen.append(a or b)
    return namen


def _aufloesen(modul, von_ordner):
    """Modulname -> moegliche Dateien im Projekt (leer = Fremdbibliothek)."""
    teile = modul.split(".")
    treffer = []
    for wurzel in (HIER, von_ordner):
        treffer.append(os.path.join(wurzel, *teile) + ".py")
        treffer.append(os.path.join(wurzel, *teile, "__init__.py"))
        # from paket.modul import X  ->  auch das Paket selbst mitnehmen
        if len(teile) > 1:
            treffer.append(os.path.join(wurzel, teile[0], "__init__.py"))
            treffer.append(os.path.join(wurzel, teile[0]) + ".py")
    return [t for t in treffer if os.path.isfile(t)]


def importkette(startdatei):
    """Alle Projektdateien, die dieser Prozess geladen haben kann."""
    start = os.path.join(HIER, startdatei)
    if not os.path.isfile(start):
        return set()
    offen, kette = [start], set()
    while offen:
        pfad = os.path.normpath(offen.pop())
        if pfad in kette or any(i in pfad for i in IGNORIEREN):
            continue
        kette.add(pfad)
        ordner = os.path.dirname(pfad)
        for modul in _module_einer_datei(pfad):
            for kandidat in _aufloesen(modul, ordner):
                if kandidat not in kette:
                    offen.append(kandidat)
    return kette


def geaendert_seit(zeitpunkt, kette):
    """Dateien aus der Importkette, die nach diesem Zeitpunkt geaendert wurden."""
    treffer = []
    for pfad in kette:
        try:
            m = datetime.fromtimestamp(os.path.getmtime(pfad), timezone.utc)
        except OSError:
            continue
        if m > zeitpunkt:
            treffer.append((os.path.relpath(pfad, HIER), m))
    return sorted(treffer, key=lambda x: x[1], reverse=True)


_FREMDE_KOPIEN = (os.path.normcase(os.path.join(".claude", "worktrees")),
                  os.path.normcase("v4_referenz"))


def gehoert_hierher(ordner, hier=HIER):
    """Laeuft ein Prozess mit diesem Arbeitsverzeichnis aus DIESEM Projekt?

    Ja: der Projektordner selbst und seine Unterordner.
    Nein: jeder andere Ordner, und Unterordner mit eigenen Projektkopien
    (.claude/worktrees, v4_referenz). Begruendung in main().
    None (Verzeichnis nicht lesbar) zaehlt als ja - lieber einmal zu viel
    melden als einen Prozess uebersehen.
    """
    if ordner is None:
        return True
    _hier = os.path.normcase(os.path.abspath(hier))
    o = os.path.normcase(os.path.abspath(ordner))
    if o == _hier:
        return True
    if not o.startswith(_hier + os.sep):
        return False                     # anderer Ordner
    rest = o[len(_hier) + 1:]            # Weg innerhalb des Projekts
    return not any(rest.startswith(k) for k in _FREMDE_KOPIEN)


def main():
    laufende = prozesse()
    # NUR Prozesse aus DIESEM Ordner.
    #
    # [26.09.2026, uebernommen aus v7 vom 21.09.] Auf diesem Rechner laufen
    # zwei Bot-Ordner nebeneinander. Die Zuordnung unten geht allein ueber
    # die Befehlszeile: "app.py" passt auf beide. Am 26.09. meldete diese
    # Pruefung deshalb den v7-Bot (PID 12420) als "NEUSTART FAELLIG" - sie
    # hatte ihn gegen die Dateien DIESES Ordners verglichen.
    # ordner None = unbekannt -> bleibt drin, lieber einmal zu viel melden.
    # Unterordner gehoeren dazu: der Forschungs-Sammler laeuft in
    # docs/forschungsprogramm_2026-07/capture. Die erste v7-Fassung (nur
    # "gleich HIER") verlor ihn - im Gegentest am 26.09. aufgefallen.
    # AUSGENOMMEN sind Unterordner mit eigenen Projektkopien: eine Kopie
    # unter .claude/worktrees ist eine eigene Instanz mit eigenem data_store
    # (Befund 73: am 24.08. lief so eine Kopie 40 Minuten ins Leere), und
    # v4_referenz ist der V4-Referenzbot. Beide gegen die Dateien dieses
    # Ordners zu vergleichen waere derselbe Zuordnungsfehler eine Ebene
    # tiefer. Fassung abgestimmt mit der v7-Sitzung am 26.09.
    laufende = [p for p in laufende if gehoert_hierher(p.get("ordner"))]
    if not laufende:
        print("Keine laufenden Python-Prozesse gefunden.")
        return 1

    jetzt = datetime.now(timezone.utc)
    print("=" * 66)
    print("FRISCHE-PRUEFUNG - laeuft irgendwo noch alter Programmtext?")
    print(f"Stand {jetzt.strftime('%d.%m.%Y %H:%M')} UTC")
    print("=" * 66)

    neustart_faellig = False
    gesehen = set()

    for muster, name, startdatei in JOBS:
        passende = [p for p in laufende if muster in p["aufruf"]]
        if not passende:
            print(f"\n{name}: LAEUFT NICHT")
            continue

        # Der Windows-Startwrapper erzeugt immer ein Elternprozess-Paar,
        # das wie zwei Instanzen aussieht (Uebergabe 13.08.). Fuer die
        # Frische zaehlt der aelteste - er hat den Text zuerst geladen.
        passende = sorted(passende, key=lambda x: x["start"])
        mehrfach = len(passende) > 1
        p = passende[0]
        if p["pid"] in gesehen:
            continue
        gesehen.add(p["pid"])

        alter = (jetzt - p["start"]).total_seconds() / 3600
        start_utc = p["start"].astimezone(timezone.utc).strftime("%d.%m. %H:%M")
        print(f"\n{name} (PID {p['pid']}"
              + (f", + {len(passende)-1} Wrapper-Prozess" if mehrfach else "")
              + ")")
        print(f"  gestartet {start_utc} UTC - laeuft seit {alter:.1f} Stunden")

        kette = importkette(startdatei)
        if not kette:
            print(f"  Startdatei {startdatei} nicht gefunden - nicht pruefbar.")
            continue
        print(f"  Importkette: {len(kette)} Dateien")

        neuer = geaendert_seit(p["start"], kette)
        if not neuer:
            print("  Programmtext unveraendert seit dem Start - frisch.")
            continue
        neustart_faellig = True
        print(f"  ACHTUNG: {len(neuer)} Datei(en) NACH dem Start geaendert -")
        print("  dieser Prozess arbeitet noch mit dem alten Stand:")
        for pfad, m in neuer[:8]:
            print(f"    {m.strftime('%d.%m. %H:%M')}  {pfad}")
        if len(neuer) > 8:
            print(f"    ... und {len(neuer)-8} weitere")
        print("  -> NEUSTART FAELLIG, sonst wirkt die Aenderung nicht.")

    print()
    print("-" * 66)
    if neustart_faellig:
        print("ERGEBNIS: Mindestens ein Prozess laeuft mit veraltetem Text.")
        print("Waehrend eines Freeze gilt: Sammler und Auswertung duerfen")
        print("neu gestartet werden, der Bot NICHT ohne Freigabe - ein")
        print("Neustart des Bots setzt Regeln neu und bricht das Messfenster.")
    else:
        print("ERGEBNIS: Alle Prozesse laufen mit dem aktuellen Stand.")
    return 1 if neustart_faellig else 0


if __name__ == "__main__":
    sys.exit(main())
