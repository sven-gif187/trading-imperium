#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZEILEN ZAEHLEN - der Beleg, dass Daten wirklich ankommen.

Angelegt 01.09.2026 beim Umzug auf den neuen Rechner.

WARUM
-----
"Der Prozess laeuft" ist kein Beleg dafuer, dass geschrieben wird.
Am 14.08.2026 stand ein Prozess in der Liste, das Log blieb leer,
und von aussen sah alles gut aus. Nur eine GEWACHSENE Tabelle
beweist, dass Daten ankommen.

BENUTZUNG
---------
    python zeilen_zaehlen.py --speichern vorher.json
    ... warten ...
    python zeilen_zaehlen.py --speichern nachher.json
    python zeilen_zaehlen.py --vergleich vorher.json nachher.json

OEFFNET JEDE DATENBANK NUR LESEND (mode=ro). Schreibt nie hinein.

docs/forschungsprogramm_2026-07/forschung.db wird bewusst NICHT
angefasst - sie ist abgekoppelt (PROJEKT-ENTSCHEIDUNGEN 13.08.2026).
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.path.join(HIER, "data_store")

# Abgekoppelt. Wird nicht gelesen und nicht geschrieben.
TABU = ("forschung.db",)


def datenbanken():
    raus = []
    for name in sorted(os.listdir(DATEN)):
        if not name.endswith(".db"):
            continue
        if any(t in name for t in TABU):
            continue
        raus.append(os.path.join(DATEN, name))
    return raus


def zaehle(pfad):
    """Tabellenname -> Zeilenzahl. Nur lesend."""
    uri = "file:" + pfad.replace("\\", "/").replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    ergebnis = {}
    fehler = None
    try:
        con = sqlite3.connect(uri, uri=True, timeout=20)
        try:
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name")
            for (tab,) in cur.fetchall():
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{tab}"')
                    ergebnis[tab] = cur.fetchone()[0]
                except sqlite3.Error as exc:
                    ergebnis[tab] = f"FEHLER: {exc}"
        finally:
            con.close()
    except sqlite3.Error as exc:
        fehler = str(exc)
    return ergebnis, fehler


def aufnehmen():
    stand = {
        "zeitpunkt": datetime.now(timezone.utc).isoformat(),
        "datenbanken": {},
    }
    for pfad in datenbanken():
        name = os.path.basename(pfad)
        tabellen, fehler = zaehle(pfad)
        stand["datenbanken"][name] = {
            "bytes": os.path.getsize(pfad),
            "tabellen": tabellen,
            "fehler": fehler,
        }
    return stand


def zeige(stand):
    print(f"Stand vom {stand['zeitpunkt']}")
    gesamt = 0
    for name, d in stand["datenbanken"].items():
        if d["fehler"]:
            print(f"\n  {name}  -- NICHT LESBAR: {d['fehler']}")
            continue
        summe = sum(v for v in d["tabellen"].values() if isinstance(v, int))
        gesamt += summe
        print(f"\n  {name}   ({d['bytes']:,} Bytes, {len(d['tabellen'])} Tabellen, "
              f"{summe:,} Zeilen)".replace(",", "."))
        for tab, n in sorted(d["tabellen"].items()):
            print(f"      {tab:<34} {n:>12}")
    print(f"\n  ZUSAMMEN: {gesamt:,} Zeilen".replace(",", "."))


def vergleiche(a, b):
    print("=" * 78)
    print(" WACHSTUM - nur gewachsene Tabellen beweisen, dass geschrieben wird")
    print("=" * 78)
    print(f"  vorher : {a['zeitpunkt']}")
    print(f"  nachher: {b['zeitpunkt']}")
    t1 = datetime.fromisoformat(a["zeitpunkt"])
    t2 = datetime.fromisoformat(b["zeitpunkt"])
    dauer = (t2 - t1).total_seconds()
    print(f"  Abstand: {dauer:.0f} Sekunden ({dauer/60:.1f} Minuten)")
    print()

    gewachsen = 0
    geschrumpft = 0
    gleich = 0
    zeilen = []
    for name in sorted(set(a["datenbanken"]) | set(b["datenbanken"])):
        da = a["datenbanken"].get(name, {}).get("tabellen", {})
        db_ = b["datenbanken"].get(name, {}).get("tabellen", {})
        for tab in sorted(set(da) | set(db_)):
            v1, v2 = da.get(tab), db_.get(tab)
            if not isinstance(v1, int) or not isinstance(v2, int):
                zeilen.append((name, tab, v1, v2, "?"))
                continue
            d = v2 - v1
            if d > 0:
                gewachsen += 1
                zeilen.append((name, tab, v1, v2, f"+{d}"))
            elif d < 0:
                geschrumpft += 1
                zeilen.append((name, tab, v1, v2, str(d)))
            else:
                gleich += 1

    if zeilen:
        print(f"  {'Datenbank':<26} {'Tabelle':<30} {'vorher':>10} {'nachher':>10}  Diff")
        print("  " + "-" * 88)
        for name, tab, v1, v2, d in zeilen:
            print(f"  {name:<26} {tab:<30} {str(v1):>10} {str(v2):>10}  {d}")
    print()
    print(f"  gewachsen: {gewachsen}    unveraendert: {gleich}    geschrumpft: {geschrumpft}")
    print()
    if gewachsen == 0:
        print("  URTEIL: KEIN Wachstum. Es kommen keine Daten an -")
        print("          egal, was die Prozessliste sagt.")
        return 1
    print(f"  URTEIL: {gewachsen} Tabelle(n) sind gewachsen. Es wird geschrieben.")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--speichern", metavar="DATEI")
    p.add_argument("--vergleich", nargs=2, metavar=("VORHER", "NACHHER"))
    a = p.parse_args()

    if a.vergleich:
        with open(a.vergleich[0], encoding="utf-8") as f:
            v = json.load(f)
        with open(a.vergleich[1], encoding="utf-8") as f:
            n = json.load(f)
        return vergleiche(v, n)

    stand = aufnehmen()
    zeige(stand)
    if a.speichern:
        with open(a.speichern, "w", encoding="utf-8") as f:
            json.dump(stand, f, indent=2)
        print(f"\n  Gespeichert: {a.speichern}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
