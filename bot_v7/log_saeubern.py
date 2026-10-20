# -*- coding: utf-8 -*-
"""Entfernt Testmeldungen aus data_store/system.log.

WOZU
----
In der Nacht zum 15.09.2026 lief fraktal_tor_test.py mehrfach und
schrieb dabei seine Attrappen-Meldungen in das ECHTE Log des
Echtgeld-Bots: erfundene Kaeufe auf TEST/USDC, dazu RESTORE-Zeilen aus
den Attrappen-Faellen. Im Log stehen sie zwischen den echten Zeilen und
sind auf den ersten Blick nicht davon zu unterscheiden.

Die URSACHE ist behoben (core/logger.py liest jetzt TI_LOG_FILE, und
fraktal_tor_test.py lenkt sein Log nach data_store/test.log um). Diese
Datei raeumt nur noch auf, was vorher schon drinsteht.

WIE TEST UND ECHT UNTERSCHIEDEN WERDEN
--------------------------------------
Nicht nach Zeitraum - am 14.09. um 20:22 lief der echte Bot noch, seine
Zeilen stehen also mitten zwischen den Testzeilen. Unterschieden wird
an den WERTEN, und die sind eindeutig verschieden:

    Test  (Attrappe)   0.00041000 BTC   Einstand 79,170.00 $
    Echt  (15.09.)     0.00040997 BTC   Einstand 79,202.74 $

Dazu kommt: Die Bestandsuebernahme gab es am 14.09. im laufenden Bot
noch gar nicht - sie wurde erst in dieser Nacht gebaut. Jede
RESTORE-Zeile mit Datum 14.09. kann deshalb nur aus einem Testlauf
stammen.

SICHERHEIT
----------
- Vorher wird eine Sicherung gelegt.
- Der Bot darf weiterlaufen: core/logger.py oeffnet die Datei bei jedem
  Schreiben neu im Anhaengen-Modus (Zeile 62) und haelt keinen
  Dateizeiger. Was er waehrend des Laufs anhaengt, wird hier erkannt
  und unveraendert wieder angehaengt.
- Es wird NUR geloescht, was mindestens ein Testmuster trifft UND vom
  14.09. stammt. Im Zweifel bleibt eine Zeile stehen.

Aufruf:  LOG_SAEUBERN.bat  (Doppelklick)
"""
import datetime
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG = os.path.join("data_store", "system.log")

# Ein Muster allein reicht nicht - die Zeile muss ZUSAETZLICH vom
# 14.09. sein. Sonst wuerde die echte Uebernahme vom 15.09. mitgehen.
TEST_MUSTER = (
    "TEST/USDC",
    "0.00041000 BTC",                    # Attrappenmenge
    "79,170.00$",                        # Attrappen-Einstand
    "0.00000010 unter Mindestmenge",     # Staub-Testfall
    "Keine uebernahmefaehigen Live-Bestaende",
    "Live-Bestaende uebernommen",
)
NUR_AN_DIESEM_TAG = "[2026-09-14T"

# Sicherheitsnetz: Was so aussieht wie die ECHTE Uebernahme, bleibt
# immer stehen - egal was sonst zutrifft.
NIE_LOESCHEN = ("0.00040997", "79,202.74")


def ist_testzeile(zeile):
    if not zeile.startswith(NUR_AN_DIESEM_TAG):
        return False
    if any(s in zeile for s in NIE_LOESCHEN):
        return False
    return any(m in zeile for m in TEST_MUSTER)


def main():
    print()
    print("=" * 72)
    print("  LOG SAEUBERN - Testmeldungen aus system.log entfernen")
    print("=" * 72)
    print()

    if not os.path.exists(LOG):
        print(f"  FEHLER: {LOG} nicht gefunden.")
        return 1

    # Groesse merken. Alles, was der laufende Bot waehrend der Arbeit
    # anhaengt, liegt hinter dieser Marke und wird unangetastet
    # wieder angehaengt.
    marke = os.path.getsize(LOG)

    stempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sicherung = f"{LOG}.vor_saeuberung_{stempel}"
    shutil.copy(LOG, sicherung)
    print(f"  Sicherung: {os.path.basename(sicherung)}")

    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        inhalt = f.read(marke)

    zeilen = inhalt.splitlines(keepends=True)
    behalten = []
    entfernt = []
    for z in zeilen:
        if ist_testzeile(z):
            entfernt.append(z)
        else:
            behalten.append(z)

    if not entfernt:
        print("\n  Keine Testmeldungen gefunden. Nichts zu tun.")
        os.remove(sicherung)
        print(f"  (Sicherung wieder geloescht - sie war ueberfluessig)")
        return 0

    print(f"\n  Gefunden: {len(entfernt)} Testzeilen von {len(zeilen)} gesamt")
    print("\n  Was entfernt wird (erste acht):")
    for z in entfernt[:8]:
        print(f"    {z.rstrip()[:96]}")
    if len(entfernt) > 8:
        print(f"    ... und {len(entfernt) - 8} weitere")

    # Was der Bot waehrenddessen angehaengt hat
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        f.seek(marke)
        nachschub = f.read()

    with open(LOG, "w", encoding="utf-8") as f:
        f.writelines(behalten)
        if nachschub:
            f.write(nachschub)

    neu = len(behalten) + (nachschub.count("\n") if nachschub else 0)
    print()
    print(f"  Log neu geschrieben: {neu} Zeilen")
    if nachschub:
        print(f"  ({nachschub.count(chr(10))} Zeilen, die der Bot waehrend der"
              f" Arbeit geschrieben hat, wurden uebernommen)")

    # ---------------- Gegenprobe (CLAUDE.md Abschnitt 0) ----------------
    print()
    print("  GEGENPROBE:")
    with open(LOG, encoding="utf-8", errors="replace") as f:
        jetzt = f.read()

    rest_test = sum(1 for z in jetzt.splitlines() if ist_testzeile(z))
    echt_da = "0.00040997 BTC UEBERNOMMEN" in jetzt

    print(f"    Testzeilen noch im Log : {rest_test}"
          f"   {'OK' if rest_test == 0 else '<- FEHLER!'}")
    print(f"    Echte Uebernahme noch da: {'ja' if echt_da else 'NEIN'}"
          f"   {'OK' if echt_da else '<- FEHLER, Sicherung zurueckspielen!'}")

    if rest_test or not echt_da:
        print()
        print("  ETWAS STIMMT NICHT. Die Sicherung liegt hier:")
        print(f"    {sicherung}")
        return 1

    print()
    print("=" * 72)
    print("  Fertig. Der Bot lief dabei ungestoert weiter.")
    print("=" * 72)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
