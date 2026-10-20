# -*- coding: utf-8 -*-
"""Pruefung der Signalpfad-Waechter-Logik (15.09.2026).

WORUM ES GEHT
-------------
Der Waechter meldete am 15.09. regelmaessig "1 von 538 Kauf-Kandidaten
haben die Risk-Pruefung NIE erreicht" - und fuenf Minuten spaeter war
wieder alles in Ordnung.

Die Zaehler sind KUMULATIV. Eine echte Luecke muesste also bestehen
bleiben. Sie schloss sich jedes Mal:

    12:14   486 -> 486 geprueft      in Ordnung
    12:19   1 von 538 fehlt          Warnung
    12:24   590 -> 590 geprueft      in Ordnung   <- Luecke zu
    12:29   1 von 636 fehlt          Warnung
    12:34   669 -> 669 geprueft      in Ordnung   <- Luecke zu

Es war also kein Verlust, sondern eine Momentaufnahme: ein Kandidat,
der beim Lesen gerade zwischen zwei Zaehlern unterwegs war.

BEIDE RICHTUNGEN
----------------
Die Reparatur unterdrueckt Fehlalarme. Damit besteht die Gefahr, dass
sie auch den ECHTEN Fall unterdrueckt - und ein Waechter, der nichts
mehr meldet, ist schlimmer als gar keiner. Deshalb steht zu jedem
"darf nicht warnen" ein "muss warnen" daneben.

Aufruf:  python waechter_signalpfad_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["TI_LOG_FILE"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data_store", "test.log")

BESTANDEN = []
DURCHGEFALLEN = []


def pruefe(name, bedingung, zusatz=""):
    if bedingung:
        BESTANDEN.append(name)
        print(f"    OK    {name}")
    else:
        DURCHGEFALLEN.append(name)
        print(f"    FEHLT {name}   {zusatz}")


class Waechter:
    """Bildet die Entscheidungslogik aus app.py _waechter_signalpfad nach.

    Bewusst nachgebaut statt app.py importiert: Der Import zieht den
    ganzen Bot hoch, inklusive Boersenverbindung. Geprueft wird die
    ENTSCHEIDUNG, und die steckt in diesen zwoelf Zeilen.

    Wer app.py aendert, muss diese Nachbildung mitaendern - deshalb
    steht die Fundstelle hier: app.py, Methode _waechter_signalpfad.
    """

    def __init__(self):
        self._sig_verloren_vorher = 0
        self.meldungen = []

    def pruefung(self, erzeugt, wartet, bei_risk):
        verloren = erzeugt - wartet - bei_risk

        if erzeugt == 0:
            return "nichts"

        if verloren <= 0:
            self._sig_verloren_vorher = 0
            self.meldungen.append("ordnung")
            return "ordnung"

        _vorher = self._sig_verloren_vorher
        self._sig_verloren_vorher = verloren

        if _vorher <= 0:
            self.meldungen.append("abwarten")
            return "abwarten"

        self.meldungen.append("ALARM")
        return "ALARM"


print()
print("=" * 72)
print("  SIGNALPFAD-WAECHTER - beide Richtungen")
print("=" * 72)

# ====================================================================
# RICHTUNG A: der echte Verlauf vom 15.09. darf NICHT alarmieren
# ====================================================================
print("\n  A) Der echte Verlauf vom 15.09. (Luecke schliesst sich)")
w = Waechter()
verlauf = [
    (486, 0, 486),    # in Ordnung
    (538, 0, 537),    # 1 unterwegs
    (590, 0, 590),    # wieder zu
    (636, 0, 635),    # 1 unterwegs
    (669, 0, 669),    # wieder zu
    (707, 0, 707),    # in Ordnung
]
for erzeugt, wartet, bei_risk in verlauf:
    ergebnis = w.pruefung(erzeugt, wartet, bei_risk)
    print(f"      {erzeugt:>4} erzeugt, {bei_risk:>4} geprueft  ->  {ergebnis}")

pruefe("kein Fehlalarm beim echten Verlauf",
       "ALARM" not in w.meldungen,
       f"Meldungen: {w.meldungen}")

# ====================================================================
# RICHTUNG B: ein ECHTER Verlust MUSS alarmieren
# ====================================================================
print("\n  B) Echter Verlust - Luecke bleibt bestehen und waechst")
w = Waechter()
verlauf = [
    (100, 0, 100),    # in Ordnung
    (150, 0, 145),    # 5 fehlen - erste Beobachtung
    (200, 0, 190),    # 10 fehlen - Luecke waechst  -> ALARM
]
for erzeugt, wartet, bei_risk in verlauf:
    ergebnis = w.pruefung(erzeugt, wartet, bei_risk)
    print(f"      {erzeugt:>4} erzeugt, {bei_risk:>4} geprueft  ->  {ergebnis}")

pruefe("echter Verlust wird gemeldet", "ALARM" in w.meldungen,
       "der Waechter schweigt bei einem echten Fehler!")

# ====================================================================
# RICHTUNG C: gleichbleibende Luecke - auch das ist echt
# ====================================================================
print("\n  C) Luecke bleibt gleich gross (Kandidat bleibt haengen)")
w = Waechter()
for erzeugt, wartet, bei_risk in [(100, 0, 100), (150, 0, 149), (200, 0, 199)]:
    ergebnis = w.pruefung(erzeugt, wartet, bei_risk)
    print(f"      {erzeugt:>4} erzeugt, {bei_risk:>4} geprueft  ->  {ergebnis}")

pruefe("dauerhaft haengender Kandidat wird gemeldet",
       "ALARM" in w.meldungen,
       "eine Luecke, die nicht zugeht, ist ein echter Verlust")

# ====================================================================
# RICHTUNG D: zurueckgestellte Kandidaten zaehlen nicht als verloren
# ====================================================================
print("\n  D) Zurueckgestellte Kandidaten (wartet) sind kein Verlust")
w = Waechter()
for erzeugt, wartet, bei_risk in [(100, 20, 80), (200, 30, 170)]:
    ergebnis = w.pruefung(erzeugt, wartet, bei_risk)
    print(f"      {erzeugt:>4} erzeugt, {wartet:>3} wartet, {bei_risk:>4} geprueft"
          f"  ->  {ergebnis}")

pruefe("Warteschlange loest keinen Alarm aus",
       "ALARM" not in w.meldungen, f"Meldungen: {w.meldungen}")

# ====================================================================
# RICHTUNG E: nach einer echten Luecke wieder Ruhe -> Zaehler zurueck
# ====================================================================
print("\n  E) Nach einem Alarm kehrt Ruhe ein - Zaehler muss zurueck")
w = Waechter()
w.pruefung(100, 0, 95)     # 5 fehlen, abwarten
w.pruefung(150, 0, 140)    # 10 fehlen, ALARM
w.pruefung(200, 0, 200)    # alles gut
letzte = w.pruefung(250, 0, 249)   # 1 unterwegs - darf NICHT alarmieren
print(f"      nach Ruhe, 1 unterwegs  ->  {letzte}")
pruefe("nach Ruhe faengt die Zaehlung von vorn an", letzte == "abwarten",
       "sonst gilt eine alte Luecke als 'zweites Mal'")

# ====================================================================
print()
print("=" * 72)
print(f"  ERGEBNIS: {len(BESTANDEN)} bestanden, {len(DURCHGEFALLEN)} durchgefallen")
print("=" * 72)
if DURCHGEFALLEN:
    print("\n  DURCHGEFALLEN:")
    for n in DURCHGEFALLEN:
        print(f"    - {n}")
    print()
    sys.exit(1)
print("\n  Alles in Ordnung.\n")
sys.exit(0)
