#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROZESSLISTE - eine Quelle statt vier.

Angelegt 01.09.2026 beim Umzug auf den neuen Rechner.

WARUM ES DAS GIBT
-----------------
Vier laufende Dateien fragten die Prozessliste ueber `wmic` ab:

    sammler_pruefen.py:240     die Sammler-Aufsicht
    prozess_frische.py:94      "laeuft noch alter Programmtext?"
    lage_erzeugen.py:66        erzeugt LAGE.md
    schatten_starter.py:68     Schatten-Starter

Microsoft hat `wmic` aus Windows 11 entfernt. Auf dieser Maschine
(10.0.26200) gibt es weder den Befehl noch die Datei wmic.exe unter
System32/wbem/.
Der Aufruf wirft FileNotFoundError [WinError 2].

Das allein waere harmlos - schlimm war, was danach passierte:
sammler_pruefen._laufende_prozesse() fing die Ausnahme mit einem
pauschalen `except Exception` ab und gab "" zurueck. Eine leere
Prozessliste heisst dort "nichts laeuft". Folge:

  * die Ampel meldete jeden Sammler als FEHLT, obwohl alle liefen
    (nachgewiesen am 01.09.2026 um 21:48:42, waehrend die Prozesse
    11524 und 2076 nachweislich seit 21:48:26 liefen)
  * starten() prueft `if skript.lower() in prozesse` - bei leerem
    Text ist das immer falsch. Es haette bei JEDEM Lauf einen
    zweiten Sammler gestartet.

Jetzt kommt die Prozessliste aus psutil. Das steht ohnehin gepinnt
in requirements.txt (psutil==7.2.2) und wurde in
sammler_pruefen._fremder_ordner() schon benutzt - keine neue
Abhaengigkeit.

KEIN STILLES SCHEITERN
----------------------
Wenn auch psutil nicht kann, wird ProzesslisteFehler geworfen. Eine
faelschlich leere Liste ist schlimmer als ein lauter Abbruch: sie
sieht aus wie eine Antwort.
"""

from datetime import datetime, timezone


class ProzesslisteFehler(RuntimeError):
    """Die Prozessliste war nicht lesbar. Kein Ergebnis ist KEIN leeres Ergebnis."""


def _psutil():
    try:
        import psutil
    except Exception as exc:
        raise ProzesslisteFehler(
            f"psutil nicht ladbar ({type(exc).__name__}: {exc}). "
            f"Es steht in requirements.txt - nachinstallieren, nicht umgehen."
        ) from exc
    return psutil


def _ist_python(name):
    # deckt python.exe und pythonw.exe ab
    return "python" in (name or "").lower()


def befehlszeilen(nur_python=True):
    """Befehlszeilen aller laufenden Prozesse als Liste von Zeichenketten.

    nur_python=True liefert nur python.exe / pythonw.exe.
    Wirft ProzesslisteFehler, wenn die Liste gar nicht lesbar ist.
    """
    psutil = _psutil()
    raus = []
    gesehen = 0
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if nur_python and not _ist_python(p.info.get("name")):
                continue
            gesehen += 1
            teile = p.info.get("cmdline") or []
            if teile:
                raus.append(" ".join(str(x) for x in teile))
        except Exception:
            # Einzelner Prozess nicht lesbar (beendet, kein Zugriff) -
            # das ist normal und kein Grund, die ganze Liste zu verwerfen.
            continue
    if gesehen == 0 and not raus:
        # Nicht ein einziger Prozess sichtbar: das ist kein Messwert,
        # das ist ein defektes Messgeraet.
        raise ProzesslisteFehler(
            "psutil sah keinen einzigen Prozess - Liste unbrauchbar.")
    return raus


def python_prozesse():
    """[{'pid': int, 'start': datetime mit Zeitzone, 'aufruf': str}, ...]

    Gleiche Form, die prozess_frische.prozesse() vorher aus wmic baute.
    """
    psutil = _psutil()
    raus = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if not _ist_python(p.info.get("name")):
                continue
            teile = p.info.get("cmdline") or []
            if not teile:
                continue
            ct = p.info.get("create_time")
            if not ct:
                continue
            start = datetime.fromtimestamp(ct, tz=timezone.utc).astimezone()
            # [26.09.2026] Arbeitsverzeichnis dazu. Auf diesem Rechner
            # laufen zwei Bot-Ordner nebeneinander (v6(21) und v7); ueber
            # die Befehlszeile "app.py" sind sie nicht zu unterscheiden.
            # None = kein Zugriff, gilt als unbekannt.
            try:
                ordner = p.cwd()
            except Exception:
                ordner = None
            raus.append({
                "pid": int(p.info["pid"]),
                "start": start,
                "aufruf": " ".join(str(x) for x in teile),
                "ordner": ordner,
            })
        except Exception:
            continue
    return raus


def _selbsttest():
    """Gegentest in beide Richtungen: findet es den echten Fall - und
    meldet es nichts Falsches?"""
    import os
    import sys
    print("SELBSTTEST prozessliste.py")
    print("-" * 60)

    zeilen = befehlszeilen()
    print(f"  Python-Prozesse gefunden: {len(zeilen)}")

    # Richtung 1: Findet es den Prozess, in dem dieser Test selbst laeuft?
    ich = str(os.getpid())
    treffer = [d for d in python_prozesse() if d["pid"] == os.getpid()]
    if treffer:
        print(f"  [OK]   Findet den eigenen Prozess (PID {ich})")
        print(f"         Start: {treffer[0]['start']}")
    else:
        print(f"  [FEHL] Findet den eigenen Prozess NICHT (PID {ich})")
        return 1

    # Richtung 2: Meldet es etwas, das es nicht gibt?
    quatsch = "gibtesnichtxyz123.py"
    if any(quatsch in z.lower() for z in zeilen):
        print(f"  [FEHL] Meldet '{quatsch}' als laufend - das gibt es nicht")
        return 1
    print(f"  [OK]   Meldet '{quatsch}' NICHT als laufend")

    print("-" * 60)
    print("  Beide Richtungen bestanden.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_selbsttest())
