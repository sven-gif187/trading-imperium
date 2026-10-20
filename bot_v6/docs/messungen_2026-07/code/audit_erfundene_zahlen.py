# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Audit: wo erfindet der Bot Zahlen statt zu messen? 05.08.2026.
"""
Read-only. Sucht Stellen, an denen ein FEHLENDER Messwert stillschweigend
durch eine erfundene Zahl ersetzt wird - und diese Zahl dann eine
Entscheidung trifft oder in einem Bericht als Messwert erscheint.

WARUM DAS GEFAEHRLICH IST
-------------------------
Ein Fallback wie `_safe_get(df, 'RSI', 50)` sieht harmlos aus. Fehlt der
RSI aber wirklich, entscheidet der Bot mit einer Zahl, die niemand
gemessen hat - und im Log steht "RSI=50" wie ein echter Wert. Der
Unterschied zwischen "RSI ist 50" und "RSI ist unbekannt" ist der
Unterschied zwischen einer Messung und einer Erfindung.

KATEGORIEN
  A  Fallback im ENTSCHEIDUNGSPFAD  - trifft Kaufs-/Verkaufsentscheidungen
  B  Fallback im BERICHT            - erscheint als Kennzahl
  C  Division/Statistik ohne Daten  - 0/0 wird zu 0 oder 100 %
  D  Hardcodierter Wert             - Konstante, die wie eine Messung aussieht

Das Skript bewertet NICHT automatisch, es sammelt Fundstellen mit Kontext.
Die Einordnung steht im Bericht.
"""
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))

# Verzeichnisse, die den laufenden Bot ausmachen. v4_referenz und die
# Messskripte sind bewusst NICHT dabei - dort sind Annahmen dokumentiert.
PFADE = ["app.py", "agents", "risk", "portfolio", "execution", "runtime",
         "features", "models", "data", "core"]

MUSTER = [
    # _safe_get(df, 'RSI', 50) - Indikator-Fallback
    ("A", "Indikator-Fallback",
     re.compile(r"_safe_get\s*\(\s*[^,]+,\s*['\"](\w+)['\"]\s*,\s*([\d.]+)\s*\)")),
    # ind.get("rsi", 50)
    ("A", "Indikator aus dict mit Default",
     re.compile(r"\.get\s*\(\s*['\"](rsi|adx|macd|ema\d*|atr|volume|bb\w*|"
                r"stoch\w*|tsi|obv|vwap)\w*['\"]\s*,\s*([\d.]+)\s*\)")),
    # fear_greed default
    ("A", "Fear&Greed-Default",
     re.compile(r"fear_greed\w*\s*[=:]\s*(\d+)\b|"
                r"\.get\s*\(\s*['\"]fear_greed['\"]\s*,\s*(\d+)\s*\)")),
    # Gewicht-Default
    ("A", "Gewicht-Default",
     re.compile(r"weights\.get\s*\([^,]+,\s*([\d.]+)\s*\)")),
    # or 0 / or 50 direkt vor einer Rechnung
    ("B", "or-Fallback auf Zahl",
     re.compile(r"=\s*[\w\.\[\]\(\)\"']+\s+or\s+([1-9][\d.]*)\b")),
    # except -> return Zahl
    ("C", "except mit Zahl-Rueckgabe",
     re.compile(r"except[^\n]*:\s*\n\s*return\s+([\d.]+)\s*$", re.M)),
    # Division mit Ersatzwert
    ("C", "Division mit Ersatznenner",
     re.compile(r"/\s*max\s*\(\s*[^,]+,\s*([\d.e-]+)\s*\)")),
    ("C", "if x else Zahl (Division geschuetzt)",
     re.compile(r"if\s+\w+\s*>\s*0\s+else\s+([\d.]+)")),
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
    treffer = {}
    for kat, name, _rx in MUSTER:
        treffer[(kat, name)] = []

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
                zeile = zeilen[nr - 1].strip() if nr <= len(zeilen) else ""
                # Kommentare und Docstrings ueberspringen
                if zeile.startswith("#") or zeile.startswith('"'):
                    continue
                treffer[(kat, name)].append((rel, nr, zeile[:105]))

    print("=" * 100)
    print(" AUDIT: WO ERFINDET DER BOT ZAHLEN?")
    print("=" * 100)
    print(f"  Durchsucht: {PFADE}")
    print(f"  Ausgenommen: v4_referenz, docs, tests, .bak-Dateien")

    gesamt = 0
    for (kat, name), liste in sorted(treffer.items()):
        if not liste:
            continue
        gesamt += len(liste)
        print(f"\n{'-' * 100}")
        print(f" [{kat}] {name}  -  {len(liste)} Fundstellen")
        print(f"{'-' * 100}")
        # nach Datei gruppieren, damit Haeufungen sichtbar werden
        nach_datei = {}
        for rel, nr, z in liste:
            nach_datei.setdefault(rel, []).append((nr, z))
        for rel in sorted(nach_datei, key=lambda x: -len(nach_datei[x])):
            eintraege = nach_datei[rel]
            print(f"\n  {rel}  ({len(eintraege)}x)")
            for nr, z in eintraege[:6]:
                print(f"    :{nr:<5d} {z}")
            if len(eintraege) > 6:
                print(f"    ... und {len(eintraege) - 6} weitere")

    print(f"\n{'=' * 100}")
    print(f" GESAMT: {gesamt} Fundstellen")
    print(f"{'=' * 100}")
    print("""
  LESART: Nicht jede Fundstelle ist ein Fehler. Entscheidend ist:
    - Trifft der Ersatzwert eine ENTSCHEIDUNG?          -> gefaehrlich
    - Erscheint er als KENNZAHL in einem Bericht?       -> gefaehrlich
    - Ist er dokumentiert und bewusst konservativ?      -> in Ordnung
    - Schuetzt er nur vor Division durch Null?          -> meist harmlos
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
