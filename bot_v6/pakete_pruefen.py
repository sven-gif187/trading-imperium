#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAKETE PRUEFEN - misst, statt zu raten.

Angelegt 01.09.2026 beim Umzug auf den neuen Rechner.

WARUM ES DAS GIBT
-----------------
check_install.py heisst so, prueft aber etwas anderes: ob bestimmte
Code-Funktionen in app.py stehen (check_install.py:24-34). Welche
Pakete installiert sind, sieht es sich nirgends an. Fuer den Umzug
auf eine leere Maschine ist genau das die Frage.

WAS ES TUT - zwei getrennte Messungen
-------------------------------------
TEIL A  Jedes Paket aus requirements.txt wirklich importieren und die
        installierte Version gegen die gepinnte halten. Importieren,
        nicht nur nachsehen ob es da ist - xgboost etwa hat keinen
        sichtbaren import, wird aber zur Laufzeit gebraucht.

TEIL B  Alle .py des Projekts mit ast einlesen, die Top-Level-Importe
        einsammeln, Standardbibliothek und projekteigene Dateien
        abziehen - und den Rest gegen requirements.txt halten.
        Das findet Pakete, die der Code braucht und die Datei nicht
        nennt. Genau so wurde Befund 92 gefunden.

AENDERT NICHTS. Liest nur.

Exit-Code 0 = alles vollstaendig, 1 = mindestens eine Luecke.
"""

import ast
import os
import sys
import importlib
import importlib.metadata as md

HIER = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HIER, "requirements.txt")

# Ordner, die nicht zum laufenden Bot gehoeren.
AUS = {"__pycache__", ".git", ".claude", "_archive_20260812_144758",
       "archiv", "v4_referenz", "v4_data", "uebergabe-dust",
       "patches_nach_27_08", "node_modules", ".venv", "venv"}

# Paketname auf der Platte  ->  Name, unter dem man ihn importiert.
# Nur die Faelle, wo beides auseinanderfaellt.
IMPORTNAME = {
    "websocket-client": "websocket",
    "pandas-ta": "pandas_ta",
    "scikit-learn": "sklearn",
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
    "Flask": "flask",
    "python-dateutil": "dateutil",
    "PyYAML": "yaml",
}


def pins():
    """requirements.txt lesen -> [(Paketname, gepinnte Version)]."""
    raus = []
    if not os.path.exists(REQ):
        return raus
    with open(REQ, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.split("#", 1)[0].strip()
            if not zeile:
                continue
            if "==" in zeile:
                name, ver = zeile.split("==", 1)
                raus.append((name.strip(), ver.strip()))
            else:
                raus.append((zeile.strip(), ""))
    return raus


def teil_a():
    print("=" * 74)
    print(" TEIL A - Ist installiert, was requirements.txt verlangt?")
    print("=" * 74)
    liste = pins()
    if not liste:
        print("  requirements.txt nicht lesbar oder leer.")
        return 1, []

    fehlend = []
    abweichend = []
    print(f"  {'Paket':<22} {'gepinnt':<12} {'installiert':<12} Import")
    print("  " + "-" * 70)
    for name, pin in liste:
        imp = IMPORTNAME.get(name, name.replace("-", "_"))
        try:
            importlib.import_module(imp)
            geladen = True
            fehler = ""
        except Exception as exc:
            geladen = False
            fehler = f"{type(exc).__name__}: {exc}"[:34]
        try:
            ist = md.version(name)
        except Exception:
            ist = "-"
        marke = "ok" if geladen else "FEHLT"
        if geladen and pin and ist != "-" and ist != pin:
            marke = "ANDERE VERSION"
            abweichend.append((name, pin, ist))
        if not geladen:
            fehlend.append((name, fehler))
        print(f"  {name:<22} {pin or '-':<12} {ist:<12} {marke}")
        if fehler:
            print(f"  {'':<22} -> {fehler}")

    print()
    print(f"  {len(liste)} Zeilen geprueft, {len(fehlend)} nicht ladbar, "
          f"{len(abweichend)} mit abweichender Version.")
    return (1 if (fehlend or abweichend) else 0), [n for n, _ in liste]


def eigene_module():
    """Alles, was im Projekt selbst liegt - das sind keine Fremdpakete."""
    eigen = set()
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner if o not in AUS and not o.startswith(".")]
        for o in ordner:
            eigen.add(o)
        for d in dateien:
            if d.endswith(".py"):
                eigen.add(d[:-3])
    return eigen


def teil_b(bekannte_pins):
    print()
    print("=" * 74)
    print(" TEIL B - Braucht der Code etwas, das requirements.txt nicht nennt?")
    print("=" * 74)

    eigen = eigene_module()
    standard = set(sys.stdlib_module_names)
    erlaubt = set()
    for n in bekannte_pins:
        erlaubt.add(IMPORTNAME.get(n, n.replace("-", "_")).lower())
        erlaubt.add(n.lower().replace("-", "_"))

    gefunden = {}
    unlesbar = []
    dateien = 0
    for wurzel, ordner, namen in os.walk(HIER):
        ordner[:] = [o for o in ordner if o not in AUS and not o.startswith(".")]
        for n in namen:
            if not n.endswith(".py"):
                continue
            pfad = os.path.join(wurzel, n)
            dateien += 1
            try:
                with open(pfad, encoding="utf-8") as f:
                    baum = ast.parse(f.read(), filename=pfad)
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                unlesbar.append((os.path.relpath(pfad, HIER), type(exc).__name__))
                continue
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Import):
                    for a in knoten.names:
                        gefunden.setdefault(a.name.split(".")[0], set()).add(
                            os.path.relpath(pfad, HIER))
                elif isinstance(knoten, ast.ImportFrom):
                    if knoten.level == 0 and knoten.module:
                        gefunden.setdefault(knoten.module.split(".")[0], set()).add(
                            os.path.relpath(pfad, HIER))

    offen = {}
    for modul, wo in gefunden.items():
        if modul in standard or modul in eigen:
            continue
        if modul.lower() in erlaubt:
            continue
        offen[modul] = wo

    print(f"  {dateien} Python-Dateien mit ast gelesen, "
          f"{len(unlesbar)} nicht parsebar.")
    for pfad, art in unlesbar[:10]:
        print(f"    nicht parsebar: {pfad}  ({art})")
    print()

    if not offen:
        print("  Keine Luecke: jeder Fremd-Import ist in requirements.txt gedeckt.")
        return 0

    print("  LUECKE - diese Module werden importiert, stehen aber nicht")
    print("  in requirements.txt:")
    print()
    for modul in sorted(offen):
        wo = sorted(offen[modul])
        try:
            importlib.import_module(modul)
            zustand = "installiert"
        except Exception:
            zustand = "NICHT installiert"
        print(f"    {modul:<24} {zustand:<18} {len(wo)} Datei(en)")
        for w in wo[:4]:
            print(f"      <- {w}")
        if len(wo) > 4:
            print(f"      <- ... und {len(wo) - 4} weitere")
    return 1


def main():
    print()
    print("PAKETE PRUEFEN")
    print("Projekt :", HIER)
    print("Python  :", sys.version.split()[0], "-", sys.executable)
    print()
    rc_a, namen = teil_a()
    rc_b = teil_b(namen)
    print()
    print("=" * 74)
    if rc_a == 0 and rc_b == 0:
        print(" ERGEBNIS: vollstaendig. Nichts fehlt, nichts weicht ab.")
    else:
        print(" ERGEBNIS: NICHT vollstaendig - siehe oben.")
        print(" Nichts eigenmaechtig nachinstallieren. Erst Sven vorlegen.")
    print("=" * 74)
    return 0 if (rc_a == 0 and rc_b == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
