# -*- coding: utf-8 -*-
"""Testfaelle fuer die Schatten-Ausstiegsregel (risk/exit_rules_schatten.py).

Aufruf:  python test_schatten_leiter.py

Prueft Normalfall, Grenzfaelle und Fehlerfaelle. Die Regel greift nicht
in den Handel ein - trotzdem muss sie stimmen, sonst misst das
Messfenster Unsinn und niemand merkt es.
"""
from risk.exit_rules_schatten import (
    schwelle, loest_aus, grund_text, beschreibung,
    GEWINN_ANTEIL, MINDEST_RUECKGABE_PCT, AKTIV_AB_PCT,
    KOSTEN_PCT, KOSTEN_MARGE_PCT)

_fehler = []


def pruefe(name, ist, soll):
    ok = ist == soll
    if not ok:
        _fehler.append(f"{name}: war {ist!r}, erwartet {soll!r}")
    print(f"  {'OK  ' if ok else 'FEHL'} {name}: {ist}"
          + ("" if ok else f"   ERWARTET {soll}"))


print("=" * 66)
print("SCHATTEN-LEITER - Testfaelle")
print("=" * 66)

print("\n--- NORMALFALL: Svens Ausgangsfrage (+20 %) ---")
aktiv, aus, rueck = schwelle(20.0)
pruefe("Hoch +20% ist aktiv", aktiv, True)
pruefe("Hoch +20% -> Ausstieg bei %", aus, 15.0)
pruefe("Hoch +20% -> Spielraum Pp", rueck, 5.0)
pruefe("bei +16% weiter halten", loest_aus(16.0, 20.0), False)
pruefe("bei +15% ausloesen (Gleichstand)", loest_aus(15.0, 20.0), True)
pruefe("bei +14% ausloesen", loest_aus(14.0, 20.0), True)

print("\n--- GRENZFALL: Untergrenze schuetzt vor Rauschen ---")
# 25 % von 1,5 waeren 0,375 Pp - zu eng, MINDEST_RUECKGABE_PCT greift.
aktiv, aus, rueck = schwelle(1.5)
pruefe("Hoch +1.5% -> Spielraum min. 0.5 statt 0.375", rueck, 0.5)
pruefe("Hoch +1.5% -> Ausstieg bei %", aus, 1.0)
# Ab hier rechnet wieder der Prozentsatz, nicht die Untergrenze.
pruefe("Hoch +4.0% -> Prozentsatz gewinnt (1.0 Pp)", schwelle(4.0)[2], 1.0)
pruefe("Umschlagpunkt: Hoch +2.0% -> genau 0.5 Pp", schwelle(2.0)[2], 0.5)

print("\n--- GRENZFALL: Aktivierungsschwelle ---")
pruefe("Hoch +0.9% nicht aktiv", schwelle(0.9)[0], False)
pruefe("Hoch +0.9% loest nie aus", loest_aus(0.1, 0.9), False)
pruefe("Hoch +1.0% aktiv (Gleichstand)", schwelle(1.0)[0], True)
pruefe("Hoch +1.0% -> Ausstieg bei %", schwelle(1.0)[1], 0.5)

print("\n--- GRENZFALL: Kostenboden ---")
# Bei Standardwerten greift er NICHT: der niedrigste Ausstieg ist
# AKTIV_AB_PCT - MINDEST_RUECKGABE_PCT = 0.5 und liegt ueber dem Boden.
boden = KOSTEN_PCT + KOSTEN_MARGE_PCT
tiefster = AKTIV_AB_PCT - MINDEST_RUECKGABE_PCT
pruefe("Boden greift bei Standardwerten nicht", tiefster >= boden, True)
# Mit abgesenkter Aktivierungsschwelle muss er greifen.
aktiv, aus, rueck = schwelle(0.6, aktiv_ab_pct=0.5)
pruefe("abgesenkt (ab 0.5%): Ausstieg nicht unter Boden", aus, round(boden, 3))
pruefe("abgesenkt: Spielraum entsprechend gekuerzt", rueck, round(0.6 - boden, 3))

print("\n--- FEHLERFALL: unbrauchbare Eingaben ---")
pruefe("None", schwelle(None), (False, 0.0, 0.0))
pruefe("Text", schwelle("abc"), (False, 0.0, 0.0))
pruefe("leerer String", schwelle(""), (False, 0.0, 0.0))
pruefe("loest_aus mit None als Gewinn", loest_aus(None, 20.0), False)
pruefe("negativer Hoechststand", schwelle(-5.0)[0], False)
pruefe("Hoechststand genau 0", schwelle(0.0)[0], False)

print("\n--- RATSCHE: haengt am Hoechststand, nie am aktuellen Stand ---")
# Gleicher Hoechststand -> gleiche Schwelle, egal wie tief es gefallen ist.
s_hoch = schwelle(20.0)[1]
pruefe("Schwelle unabhaengig vom aktuellen Gewinn", schwelle(20.0)[1], s_hoch)
pruefe("hoeherer Hoechststand -> hoehere Schwelle",
       schwelle(25.0)[1] > schwelle(20.0)[1], True)
pruefe("Schwelle waechst monoton",
       all(schwelle(h)[1] <= schwelle(h + 0.5)[1] for h in
           [x / 2 for x in range(2, 60)]), True)

print("\n--- VERGLEICH mit der heutigen Leiter (nur Anzeige) ---")
LEITER = ((1.2, 1.0), (3.0, 1.3), (5.0, 1.7), (8.0, 2.2))
print(f"  {'Hoch':>7} {'heute':>9} {'Schatten':>10}   besser")
for hoch in (1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 15.0, 23.0):
    f = LEITER[0][1]
    for s, ff in LEITER:
        if hoch >= s:
            f = ff
    heute = ((1 + hoch / 100) * (1 - (1.0 * f) / 100) - 1) * 100
    neu = schwelle(hoch)[1]
    print(f"  {hoch:>6.1f}% {heute:>8.2f}% {neu:>9.2f}%   "
          f"{'Schatten' if neu > heute else 'heutige'}")

print("\n" + "=" * 66)
print(beschreibung())
print("Beispiel:", grund_text(14.8, 20.0))
print("=" * 66)
if _fehler:
    print(f"\nFEHLGESCHLAGEN: {len(_fehler)}")
    for f in _fehler:
        print("  -", f)
    raise SystemExit(1)
print("\nAlle Testfaelle bestanden.")
