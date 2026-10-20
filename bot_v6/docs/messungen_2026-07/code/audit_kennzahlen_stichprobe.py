# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Audit: Kennzahlen ohne Mindeststichprobe, 05.08.2026.
"""
Read-only. Sucht Stellen, an denen eine Kennzahl berechnet und ausgegeben
wird, ohne dass die Stichprobe geprueft wird.

WARUM DAS ZAEHLT
----------------
Eine Win-Rate von 100 % aus zwei Trades ist keine Kennzahl, sondern eine
Zufallszahl mit drei Nachkommastellen. Sie steht aber im Bericht wie ein
Messwert und wird gelesen wie einer. Aus der eigenen Messreihe: bei n=30
ist das 95-%-Konfidenzintervall einer Trefferquote rund +/-18
Prozentpunkte breit - bei n=20.129 waren es +/-4.

GESUCHT WIRD
  A  Quote = a / b ohne vorherige Pruefung von b
  B  Mittelwert ueber eine Liste ohne Laengenpruefung
  C  Ausgabe einer Quote in einem Log-/Reportstring
  D  Vorhandene Mindestpruefungen (zum Gegenlesen - was gibt es schon?)
"""
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))

PFADE = ["app.py", "cockpit_server.py", "reports", "core", "features",
         "portfolio", "risk", "runtime", "models", "agents"]

# Kennzahl-Namen, die auf eine Quote hindeuten
KENN = (r"win_rate|winrate|wr\b|trefferquote|hit_rate|profit_factor|"
        r"avg_win|avg_loss|avg_pnl|roi|sharpe|sortino|r_multiple|rr\b|"
        r"erfolgsquote|quote")

MUSTER = [
    ("A", "Quote ohne Nenner-Pruefung",
     re.compile(rf"({KENN})\s*=\s*[\w\.\[\]\(\)]+\s*/\s*[\w\.\[\]\(\)]+"
                r"(?!\s*if)", re.I)),
    ("B", "Mittelwert ohne Laengenpruefung",
     re.compile(r"=\s*sum\s*\([^)]+\)\s*/\s*len\s*\([^)]+\)(?!\s*if)")),
    ("C", "Quote im Ausgabe-String",
     re.compile(rf"f['\"][^'\"]*\{{[^}}]*({KENN})[^}}]*\}}", re.I)),
    ("D", "vorhandene Mindeststichprobe",
     re.compile(r"(len\s*\([^)]+\)|n|trades|count)\s*[<>]=?\s*"
                r"(\d+)\s*[:\)]|min_trades|MIN_TRADES|min_sample")),
]


def dateien():
    for p in PFADE:
        voll = os.path.join(PROJEKT, p)
        if os.path.isfile(voll):
            yield voll
        elif os.path.isdir(voll):
            for w, dirs, fs in os.walk(voll):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for f in fs:
                    if f.endswith(".py") and ".bak" not in f:
                        yield os.path.join(w, f)


def main():
    treffer = {(k, n): [] for k, n, _ in MUSTER}
    for pfad in dateien():
        try:
            txt = open(pfad, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        rel = os.path.relpath(pfad, PROJEKT)
        zeilen = txt.splitlines()
        for kat, name, rx in MUSTER:
            for m in rx.finditer(txt):
                nr = txt[:m.start()].count("\n") + 1
                z = zeilen[nr - 1].strip() if nr <= len(zeilen) else ""
                if z.startswith("#") or z.startswith('"""') or z.startswith("*"):
                    continue
                treffer[(kat, name)].append((rel, nr, z[:110]))

    print("=" * 100)
    print(" AUDIT: KENNZAHLEN OHNE MINDESTSTICHPROBE")
    print("=" * 100)
    for (kat, name), liste in sorted(treffer.items()):
        if not liste:
            continue
        print(f"\n{'-' * 100}")
        print(f" [{kat}] {name}  -  {len(liste)} Fundstellen")
        print(f"{'-' * 100}")
        nach = {}
        for rel, nr, z in liste:
            nach.setdefault(rel, []).append((nr, z))
        for rel in sorted(nach, key=lambda x: -len(nach[x]))[:8]:
            print(f"\n  {rel}  ({len(nach[rel])}x)")
            for nr, z in nach[rel][:5]:
                print(f"    :{nr:<5d} {z}")
            if len(nach[rel]) > 5:
                print(f"    ... und {len(nach[rel]) - 5} weitere")
    print(f"\n{'=' * 100}")
    print(" Kategorie D zeigt, wo bereits eine Mindestpruefung existiert -")
    print(" zum Gegenlesen, nicht als Mangel.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
