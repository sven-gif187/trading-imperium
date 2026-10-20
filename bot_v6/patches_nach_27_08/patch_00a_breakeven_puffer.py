#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  PATCH 00a - der Breakeven-Puffer deckt die Kosten nicht
================================================================
NICHT VOR DEM 28.08.2026 ANWENDEN. Verhaltensaenderung.

Angelegt 20.08.2026 auf Svens Frage: "damit haetten wir ja das
Problem mit der Stop-Loss-Problematik geloest, oder? Haben wir die
Loesung dafuer bereits?"

Antwort: die Loesung war erkannt und begruendet (Handbuch 4.34,
OFFEN.md Punkt 0) - aber als einzige der wichtigen Korrekturen
NICHT vorbereitet. Das holt dieser Patch nach.

DAS PROBLEM
-----------
risk/exit_rules.py:107

    BREAKEVEN_PUFFER_PCT = 0.35   # deckt 2x0.1 % Gebuehr + 2x0.06 % Slippage

Die Rechnung war zu ihrem Zeitpunkt richtig:

    Gebuehren  2 x 0.10 %  =  0.20 %
    Slippage   2 x 0.06 %  =  0.12 %
    ----------------------------------
    Kosten                 =  0.32 %

Seit E6_messfenster (13.08.) gilt der korrigierte Bybit-EU-Taker von
0,25 % je Seite. K-BASIS ist 0,505 % je Runde. Der Puffer wurde nicht
mitgezogen.

Folge - nachgerechnet:

    Puffer 0.350 %  ->  netto -0.155 %   VERLUST garantiert
    Puffer 0.550 %  ->  netto +0.045 %   deckt die Kosten

Die Sperre stellt also nicht die Null glatt, sondern einen kleinen
Verlust. Genau der Fehler, den der Fix vom 10.08. beheben sollte -
nur eine Etage hoeher.

DIE GEGENPROBE STAND SCHON IM CODE
----------------------------------
Im selben Kommentar steht seit dem 10.08. woertlich:

    "Gegenprobe nach ~10 weiteren BREAKEVEN_LOCK-Verkaeufen: der
     Durchschnitt muss bei oder ueber 0 $ liegen, sonst ist auch
     0.35 % noch zu niedrig."

Sie ist faellig und faellt durch:

    vor dem Fix  (Puffer 0.25 %)   6 Faelle   -0.138 $ im Schnitt
    nach dem Fix (Puffer 0.35 %)   4 Faelle   -0.594 $ im Schnitt

Wer den Puffer jetzt anhebt, tut genau das, was die damalige Notiz
fuer diesen Fall angeordnet hat. Es ist KEIN Schritt zurueck.

DER NEUE WERT
-------------
    0.505 %  K-BASIS (Bybit EU Taker 0,25 % je Seite)
  + 0.045 %  Marge, damit die Null nicht knapp verfehlt wird
  ---------
    0.550 %

Der Puffer wird nicht mehr verdrahtet, sondern aus K_BASIS_PCT
gerechnet - sonst veraltet er beim naechsten Gebuehrenwechsel wieder.
Dritter Fall desselben Musters nach den Epochen (4.92) und der
Muenzzahl (4.93).

WAS ER NICHT TUT
----------------
Er senkt NICHT die Schwelle BREAKEVEN_AB_PCT (1,0 %). Das waere die
naheliegende zweite Stellschraube - am 10.08. verfehlte ein Fall sie
um 0,02 Punkte (ETH, Hoch +0,98 %). Aber eine tiefere Schwelle
schliesst mehr Positionen bei +0,55 % und deckelt damit die Gewinner.
Ob sich das lohnt, ist eine MESSUNG, keine Meinung - dafuer sammelt
positionsverlauf.py. Erst rechnen, dann drehen.

ANWENDEN
--------
    python patches_nach_27_08/patch_00a_breakeven_puffer.py --pruefen
    python patches_nach_27_08/patch_00a_breakeven_puffer.py --anwenden
================================================================
"""
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(HIER, "risk", "exit_rules.py")

ANKER = ("BREAKEVEN_PUFFER_PCT = 0.35   "
         "# deckt 2x0.1 % Gebuehr + 2x0.06 % Slippage")

ERSATZ = '''# [PATCH 00a, ab 28.08.2026] Der Puffer wird gerechnet, nicht gesetzt.
#
# Vorher: 0.35 %, hergeleitet aus 2x0.10 % Gebuehr + 2x0.06 % Slippage.
# Diese Herleitung war am 10.08. richtig. Seit der Gebuehrenkorrektur
# (Bybit EU, 0,25 % je Seite) liegen die echten Kosten bei 0,505 % je
# Runde - der Puffer blieb stehen und garantierte damit einen kleinen
# VERLUST statt die Null zu sichern:
#
#     0.350 % - 0.505 % = -0.155 %
#
# Die im alten Kommentar verlangte Gegenprobe ist faellig und faellt
# durch: die vier BREAKEVEN_LOCK-Verkaeufe nach dem Fix liegen bei
# -0,594 $ im Schnitt, schlechter als die sechs davor.
#
# Jetzt aus der Konstante gerechnet, damit er beim naechsten
# Gebuehrenwechsel nicht wieder haengenbleibt.
K_BASIS_PCT = 0.505           # Bybit EU Taker 0,25 % je Seite, CLAUDE.md 8
BREAKEVEN_MARGE_PCT = 0.045   # damit die Null nicht knapp verfehlt wird
BREAKEVEN_PUFFER_PCT = round(K_BASIS_PCT + BREAKEVEN_MARGE_PCT, 3)   # 0.55'''


def pruefen():
    print("=" * 70)
    print("PATCH 00a - Breakeven-Puffer auf Kostendeckung")
    print("=" * 70)
    fehler = 0
    if not os.path.exists(ZIEL):
        print("  FEHLT: " + ZIEL)
        return 1
    t = open(ZIEL, encoding="utf-8").read()

    n = t.count(ANKER)
    print("\n  Anker genau einmal vorhanden : "
          + ("ja" if n == 1 else "NEIN (" + str(n) + "x)"))
    if n != 1:
        fehler += 1
    schon = "K_BASIS_PCT" in t
    print("  Patch schon angewendet       : " + ("JA" if schon else "nein"))
    if schon:
        return 1

    print("\n  Nachrechnung:")
    K = 0.505
    for p, wie in ((0.35, "bisher"), (0.55, "neu")):
        print("    Puffer " + format(p, ".3f") + " %  ->  netto "
              + format(p - K, "+.3f") + " %   "
              + ("VERLUST garantiert" if p - K < 0 else "deckt die Kosten")
              + "   (" + wie + ")")

    # Gegenprobe: aendert der Patch WIRKLICH nur diese eine Zahl?
    neu = t.replace(ANKER, ERSATZ, 1)
    a = [z for z in t.split("\n") if z.strip()]
    b = [z for z in neu.split("\n") if z.strip()]
    weg = [z for z in a if z not in b]
    print("\n  Zeilen, die verschwinden: " + str(len(weg)))
    for z in weg:
        print("    - " + z.strip()[:66])
    if len(weg) != 1:
        print("  ACHTUNG: es sollte genau eine sein.")
        fehler += 1

    print("\n  " + ("BEREIT - mit --anwenden einspielen" if not fehler
                    else str(fehler) + " Problem(e), NICHT anwenden"))
    return 1 if fehler else 0


def anwenden():
    if pruefen():
        return 1
    t = open(ZIEL, encoding="utf-8").read()
    open(ZIEL + ".bak_vor_patch00a", "w", encoding="utf-8").write(t)
    open(ZIEL, "w", encoding="utf-8").write(t.replace(ANKER, ERSATZ, 1))
    print("\n  Angewendet. Sicherung: exit_rules.py.bak_vor_patch00a")
    print("  JETZT: Epochengrenze E8 eintragen, dann Bot neu starten.")
    print("  DANACH: nach ~10 BREAKEVEN_LOCK-Verkaeufen nachmessen -")
    print("  der Durchschnitt muss bei oder ueber 0 $ liegen.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--anwenden", action="store_true")
    a = p.parse_args()
    sys.exit(anwenden() if a.anwenden else pruefen())
