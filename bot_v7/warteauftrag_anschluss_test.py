# -*- coding: utf-8 -*-
"""Prueft den ANSCHLUSS der Live-Warte-Auftraege an execution/engine.py.

Die Maschine selbst ist in warteauftrag_live_test.py geprueft (31 Faelle).
Hier geht es um die Verdrahtung, und vor allem um die eine Frage, die
vor jeder Freigabe beantwortet sein muss:

    Aendert sich das Verhalten, solange `nur_paper` auf true steht?

Wenn ja, waere der Anschluss selbst schon eine Verhaltensaenderung - und
die braeuchte eine Epochengrenze, bevor auch nur ein Schalter umgelegt
wird. Deshalb wird beides geprueft: der Zweig muss AUS sein, wenn er aus
sein soll, und AN, wenn er an sein soll.

Aufruf:  python warteauftrag_anschluss_test.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QUELLE = io.open(os.path.join("execution", "engine.py"),
                 encoding="utf-8").read()

bestanden = 0
gefallen = 0


def pruefe(name, ist, soll):
    global bestanden, gefallen
    ok = ist == soll
    if ok:
        bestanden += 1
    else:
        gefallen += 1
    print(f"  [{'ok  ' if ok else 'FALSCH'}] {name}")
    if not ok:
        print(f"          erwartet: {soll!r}  bekommen: {ist!r}")


print("\n" + "=" * 72)
print("  ANSCHLUSS-TEST: Warte-Auftraege live an engine.py")
print("=" * 72)

# ------------------------------------------------ 1. Der Zweig ist verdrahtet
print("\n  1. Ist der Abzweig ueberhaupt da?")
pruefe("_warteauftrag_live_anlegen existiert",
       bool(re.search(r"def _warteauftrag_live_anlegen\(", QUELLE)), True)
pruefe("_warteauftraege_live_takt existiert",
       bool(re.search(r"def _warteauftraege_live_takt\(", QUELLE)), True)
pruefe("_execute_live ruft den Abzweig auf",
       bool(re.search(r"return self\._warteauftrag_live_anlegen\(", QUELLE)),
       True)
pruefe("warteauftraege_pruefen ruft den Live-Takt auf",
       bool(re.search(r"return self\._warteauftraege_live_takt\(\)", QUELLE)),
       True)

# --------------------------------------- 2. Der Schalter muss wirklich sperren
print("\n  2. Sperrt `nur_paper` den Zweig? (die entscheidende Frage)")
# Der Abzweig im Kaufweg
m = re.search(r"if \(intent\.side == Side\.BUY\s*\n\s*and self\.warteschlange "
              r"is not None\s*\n\s*and self\.warteschlange\.aktiv\s*\n"
              r"\s*and not self\.warteschlange\.einst\.get\(\"nur_paper\", True\)\)",
              QUELLE)
pruefe("Kaufweg prueft nur_paper, mit Vorgabe True", bool(m), True)
pruefe("Takt prueft nur_paper, mit Vorgabe True",
       bool(re.search(r'self\.warteschlange\.einst\.get\("nur_paper", True\)'
                      r'\s*:\s*\n\s*return \[\]', QUELLE)), True)

# Die Vorgabe in der Warteschlange selbst
W = io.open(os.path.join("execution", "warteauftraege.py"),
            encoding="utf-8").read()
pruefe("Vorgabe in warteauftraege.py steht auf True",
       bool(re.search(r'"nur_paper":\s*True', W)), True)

# ------------------------------------------------- 3. Nur Kaeufe, nie Verkaeufe
print("\n  3. Verkaeufe muessen Sofort-Auftraege bleiben")
pruefe("Abzweig greift nur bei Side.BUY",
       bool(re.search(r"if \(intent\.side == Side\.BUY", QUELLE)), True)
LIVE = io.open(os.path.join("execution", "warteauftraege_live.py"),
               encoding="utf-8").read()
pruefe("warteauftraege_live stellt nur 'buy'",
       len(re.findall(r'create_order\([^)]*"limit",\s*"buy"', LIVE)), 1)
pruefe("und kennt keinen Verkaufsweg",
       bool(re.search(r'"sell"', LIVE)), False)

# ----------------------------------------- 4. Kein stiller Rueckfall auf Market
print("\n  4. Scheitert der Warte-Auftrag, darf NICHT still sofort gekauft werden")
block = QUELLE[QUELLE.find("def _warteauftrag_live_anlegen"):]
block = block[:block.find("def _warteauftraege_live_takt")]
pruefe("bei Fehler wird abgelehnt, nicht ersetzt",
       bool(re.search(r'result\.status = "rejected"', block)), True)
pruefe("und es wird laut protokolliert",
       bool(re.search(r'log\.error\("WARTE-LIVE"', block)), True)

# ------------------------------- 5. 'unklar' darf nichts aufraeumen
print("\n  5. Bei unklarer Lage wird NICHTS aufgeraeumt")
takt = QUELLE[QUELLE.find("def _warteauftraege_live_takt"):]
takt = takt[:takt.find("def warteauftraege_pruefen")]
pruefe("'unklar' fuehrt zu continue, nicht zu abbrechen()",
       bool(re.search(r'if st\["zustand"\] == "unklar":\s*\n\s*continue', takt)),
       True)
pruefe("Menge 0 wird nicht gebucht",
       bool(re.search(r"if menge <= 0:", takt)), True)

# --------------------------- 6. Die WIRKLICHE Menge buchen, nicht die geplante
print("\n  6. Teilausfuehrung: gebucht wird, was wirklich kam")
pruefe("amount_usd aus Menge x Preis, nicht aus betrag_usd",
       bool(re.search(r"amount_usd=menge \* preis", takt)), True)
pruefe("filled_qty ist die gemeldete Menge",
       bool(re.search(r"result\.filled_qty = menge", takt)), True)

# ------------------------------------------- 7. Reihenfolge: Boerse zuerst
print("\n  7. Erst an die Boerse, dann in die eigene Liste")
i_stellen = block.find("_wl.stellen(")
i_anlegen = block.find("self.warteschlange.anlegen(")
pruefe("stellen() kommt vor anlegen()",
       i_stellen > 0 and i_anlegen > i_stellen, True)
pruefe("nimmt den Auftrag zurueck, wenn die Liste ihn ablehnt",
       bool(re.search(r"_wl\.zuruecknehmen\(exchange, oid", block)), True)

# ------------------------------------------ 8. Die Datei laedt ueberhaupt
print("\n  8. Laedt der geaenderte Code?")
try:
    import ast
    ast.parse(QUELLE)
    pruefe("engine.py ist syntaktisch gueltig", True, True)
except SyntaxError as e:
    pruefe(f"engine.py Syntax ({e})", False, True)
try:
    from execution import warteauftraege_live          # noqa: F401
    pruefe("warteauftraege_live laedt", True, True)
except Exception as e:
    pruefe(f"warteauftraege_live laedt ({e})", False, True)

print("\n" + "-" * 72)
print(f"  {bestanden} bestanden, {gefallen} gefallen")
if gefallen == 0:
    print("\n  Der Anschluss steht. Solange `nur_paper` auf true bleibt,")
    print("  ist der Zweig tot und das Verhalten unveraendert.")
else:
    print("\n  NICHT FREIGEBEN, solange etwas fehlschlaegt.")
print("=" * 72 + "\n")
sys.exit(1 if gefallen else 0)
