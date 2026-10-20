# -*- coding: utf-8 -*-
"""
cleanup_daily_loss.py - P5 abschliessen: verwaiste Module markieren
====================================================================
Der Audit meldete "Daily-Loss doppelt/gefaehrlich". Analyse 09.07 ergab:
Die REAL laufende Logik in portfolio/manager.py ist bereits sauber
(echter Tagesreset, echter Tagesverlust, KEIN Zwangsverkauf, fuer
Datensammlung bewusst deaktiviert). Die zwei Module daily_loss_guard.py
und daily_loss_guardian.py werden NIRGENDS importiert (verifiziert) -
sie sind toter Code, der nur Verwirrung stiftet.

Dieses Skript benennt die zwei Dateien in *.py.UNUSED um (loescht NICHT).
So sind sie aus dem Import-Weg, bleiben aber als Referenz erhalten.
Idempotent, meldet was es tut. AENDERT NUR Dateinamen, keinen Code.

ABLAUF: Bot darf laufen (die Dateien werden ja eh nicht genutzt).
Zur Sicherheit trotzdem: bei geschlossenem Bot ausfuehren.
"""
import os
import sys

TARGETS = ["daily_loss_guard.py", "daily_loss_guardian.py"]


def find(base, name):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_archive", "backup"))]
        if name in files:
            return os.path.join(root, name)
    return None


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    print("P5 - Verwaiste Daily-Loss-Module markieren")
    print("-" * 52)
    done = 0
    for name in TARGETS:
        path = find(base, name)
        if not path:
            # evtl. schon markiert?
            unused = find(base, name + ".UNUSED")
            if unused:
                print(f"  {name}: bereits als .UNUSED markiert")
            else:
                print(f"  {name}: nicht gefunden (evtl. schon aufgeraeumt)")
            continue
        target = path + ".UNUSED"
        if os.path.exists(target):
            print(f"  {name}: .UNUSED existiert schon - lasse Original liegen")
            continue
        os.rename(path, target)
        print(f"  {name} -> {os.path.basename(target)}")
        done += 1
    print("-" * 52)
    if done:
        print(f"  {done} Modul(e) markiert. Kein Code geloescht.")
        print("  Die aktive Daily-Loss-Logik in portfolio/manager.py bleibt.")
    else:
        print("  Nichts zu tun.")
    print("Fertig.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FEHLER: {e}")
    input("\nEnter zum Schliessen...")
