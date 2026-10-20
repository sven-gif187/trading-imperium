# -*- coding: utf-8 -*-
"""
patch_45_trailing_schwelle.py — hebt die Trailing-Schwelle über die Kostenlinie
==============================================================================

NICHT VOR DEM 27.08.2026 ANWENDEN.
Diese Änderung berührt das Handelsverhalten und braucht eine Epochengrenze.

DAS PROBLEM (Befund 45, BOT-HANDBUCH.md 4.64)
---------------------------------------------
Der Trailing-Stop wird ab +1,2 % Höchststand scharf (TRAIL_AB_PCT) und
hält 1,0 % Abstand (config.json trailing_stop_pct). Rentabel wird er erst
ab +1,52 %. Dazwischen verliert jeder Ausstieg rechnerisch:

    Höchststand   Ausstieg bei   netto nach 0,505 % Kosten
      1,20 %        +0,188 %          -0,317 %
      1,50 %        +0,485 %          -0,020 %
      1,52 %        +0,505 %          +-0,000 %

Gemessen: 74 von 135 Trailing-Ausstiegen (55 %) enden brutto im Plus und
netto im Minus, zusammen -19,61 Prozentpunkte.

DIE URSACHE
-----------
Die Leiter war am 29.07. korrekt gerechnet - bei 0,10 % Gebühr je Seite
lag die Nulllinie bei 1,33 %, die Schwelle 1,2 knapp darunter. Seit dem
13.08. sind es 0,25 % je Seite. Die Kostenschwelle ist unter der Regel
weggewandert.

DIE ÄNDERUNG
------------
TRAIL_AB_PCT wird nicht mehr fest gesetzt, sondern AUS DEN KOSTEN
GERECHNET:

    TRAIL_AB_PCT = (1 + K/100) / (1 - trail/100) - 1  + Sicherheitsmarge

Damit wandert die Schwelle automatisch mit, wenn sich Gebühren oder
Trail-Abstand ändern - der Fehler kann sich nicht wiederholen.

WAS DIESE ÄNDERUNG NICHT TUT
----------------------------
Sie macht den Trail nicht enger. Die Messung an 43 Trades legt nahe, dass
ein engerer Abstand besser wäre (+1,274 % gegen +0,852 %), aber diese
Rechnung kennt nur den Höchststand, nicht den Weg dorthin. Sie ist eine
Obergrenze, kein Ergebnis. Die Entscheidung darüber gehört hinter die
Auswertung von positionsverlauf.py.

AUFRUF
------
    python patches_nach_27_08/patch_45_trailing_schwelle.py --pruefen
    python patches_nach_27_08/patch_45_trailing_schwelle.py --anwenden
    python patches_nach_27_08/patch_45_trailing_schwelle.py --selbsttest
"""
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(HIER, "risk", "exit_rules.py")
CONFIG = os.path.join(HIER, "data_store", "config.json")
ZIELE = os.path.join(HIER, "config_zielgroessen.json")
MARGE = 0.05          # Prozentpunkte Sicherheitsabstand über die Nulllinie


def kosten_je_runde():
    """K-BASIS aus config_zielgroessen.json, sonst 0,505."""
    try:
        with open(ZIELE, encoding="utf-8") as f:
            return float(json.load(f).get("kosten_je_runde_pct", 0.505))
    except Exception:
        return 0.505


def trail_abstand():
    """trailing_stop_pct aus der Konfiguration."""
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return float(json.load(f).get("risk", {}).get("trailing_stop_pct", 1.0))
    except Exception:
        return 1.0


def nulllinie(k, trail):
    """Ab welchem Höchststand trägt sich ein Trailing-Ausstieg?

    Ausstieg = (1 + h) * (1 - t) - 1.  Gesucht ist h mit Ausstieg = k.
    """
    return ((1 + k / 100) / (1 - trail / 100) - 1) * 100


def aktueller_wert():
    try:
        t = io.open(ZIEL, encoding="utf-8").read()
        m = re.search(r"^TRAIL_AB_PCT\s*=\s*([\d.]+)", t, re.M)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def bericht():
    k, trail = kosten_je_runde(), trail_abstand()
    n = nulllinie(k, trail)
    ist = aktueller_wert()
    soll = round(n + MARGE, 2)
    print(f"\n{'='*68}")
    print("  PATCH 45 — Trailing-Schwelle über die Kostenlinie")
    print(f"{'='*68}\n")
    print(f"  Kosten je Runde (K-BASIS)   {k:6.3f} %")
    print(f"  Trail-Abstand (config)      {trail:6.3f} %")
    print(f"  -> Nulllinie                {n:6.3f} %")
    print(f"  -> Sicherheitsmarge         {MARGE:6.3f} %")
    print(f"  -> NEUER Wert               {soll:6.2f} %")
    print(f"\n  TRAIL_AB_PCT steht heute auf {ist if ist is not None else '?'} %")
    if ist is not None:
        if abs(ist - soll) < 0.005:
            print("  -> bereits richtig, nichts zu tun.")
        elif ist < n:
            fehl = [(h, ((1 + h/100) * (1 - trail/100) - 1) * 100 - k)
                    for h in (ist, (ist + n) / 2, n)]
            print(f"  -> ZU NIEDRIG. Jeder Ausstieg zwischen {ist} % und "
                  f"{n:.2f} % verliert:")
            for h, netto in fehl:
                print(f"       Hoechststand {h:5.2f} %  ->  netto {netto:+6.3f} %")
        else:
            print("  -> über der Nulllinie, aber weicht vom Sollwert ab.")
    return soll, ist


def anwenden():
    soll, ist = bericht()
    if ist is not None and abs(ist - soll) < 0.005:
        print("\n  Nichts zu ändern.\n")
        return 0
    sicherung = ZIEL + f".bak_patch45_{datetime.now():%Y%m%d_%H%M%S}"
    shutil.copy2(ZIEL, sicherung)
    t = io.open(ZIEL, encoding="utf-8").read()
    k, trail = kosten_je_runde(), trail_abstand()
    neu_zeile = (
        f"# [PATCH 45, {datetime.now():%d.%m.%Y}] Aus den Kosten gerechnet statt\n"
        f"# gesetzt. Nulllinie = (1+K)/(1-Trail)-1 = {nulllinie(k, trail):.3f} % bei\n"
        f"# K={k} % und Trail={trail} %, plus {MARGE} % Marge.\n"
        f"# Der alte Wert 1.2 stammte aus einer Zeit mit 0,10 % Gebuehr je Seite\n"
        f"# (Nulllinie damals 1,33 %). Seit dem 13.08.2026 sind es 0,25 %.\n"
        f"# Wer Gebuehren oder Trail aendert, muss diesen Wert neu rechnen:\n"
        f"#     python patches_nach_27_08/patch_45_trailing_schwelle.py --pruefen\n"
        f"TRAIL_AB_PCT = {soll}            # darunter kein Trailing"
    )
    t2 = re.sub(r"^TRAIL_AB_PCT\s*=\s*[\d.]+.*$", neu_zeile, t, count=1, flags=re.M)
    if t2 == t:
        print("\n  FEHLER: TRAIL_AB_PCT nicht gefunden - nichts geändert.\n")
        return 1
    io.open(ZIEL, "w", encoding="utf-8").write(t2)
    print(f"\n  Sicherung: {os.path.basename(sicherung)}")
    print(f"  TRAIL_AB_PCT: {ist} -> {soll}")
    print("\n  NICHT VERGESSEN:")
    print("   1. Epochengrenze in config_epochs.json eintragen")
    print("   2. Bot neu starten (sonst laeuft der alte Wert weiter)")
    print("   3. python prozess_frische.py zur Kontrolle\n")
    return 0


def selbsttest():
    fehler = 0
    print("\n=== Richtung 1: rechnet die Nulllinie bekannte Faelle richtig? ===")
    for k, trail, soll in [(0.505, 1.0, 1.520), (0.32, 1.0, 1.333),
                           (0.505, 0.5, 1.010), (0.0, 1.0, 1.010)]:
        ist = nulllinie(k, trail)
        ok = abs(ist - soll) < 0.01
        print(f"  {'OK  ' if ok else 'FEHL'} K={k:5.3f} Trail={trail:4.2f} "
              f"-> {ist:6.3f} % (soll {soll:.3f})")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: ist die Nulllinie wirklich die Nulllinie? ===")
    k, trail = 0.505, 1.0
    n = nulllinie(k, trail)
    for h, erwartet in [(n - 0.2, "Verlust"), (n, "Null"), (n + 0.2, "Gewinn")]:
        netto = ((1 + h/100) * (1 - trail/100) - 1) * 100 - k
        art = "Verlust" if netto < -0.001 else ("Gewinn" if netto > 0.001 else "Null")
        ok = art == erwartet
        print(f"  {'OK  ' if ok else 'FEHL'} Hoechststand {h:5.3f} % -> "
              f"netto {netto:+6.3f} % ({art}, erwartet {erwartet})")
        if not ok:
            fehler += 1

    print("\n=== Richtung 3: liest es die echten Werte? ===")
    k, trail, ist = kosten_je_runde(), trail_abstand(), aktueller_wert()
    print(f"  K-BASIS aus config_zielgroessen.json : {k}")
    print(f"  Trail aus config.json                : {trail}")
    print(f"  TRAIL_AB_PCT aus risk/exit_rules.py  : {ist}")
    for name, wert in [("K-BASIS", k), ("Trail", trail), ("TRAIL_AB_PCT", ist)]:
        if wert is None:
            print(f"  FEHLER: {name} nicht lesbar")
            fehler += 1

    print("\n=== Richtung 4: erkennt es den heutigen Fehlstand? ===")
    if ist is not None:
        zu_niedrig = ist < nulllinie(k, trail)
        print(f"  {ist} < {nulllinie(k, trail):.3f} -> "
              f"{'ZU NIEDRIG erkannt (richtig)' if zu_niedrig else 'nicht erkannt'}")
        if not zu_niedrig:
            print("    HINWEIS: entweder schon gepatcht, oder K/Trail geaendert.")

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--pruefen"
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    if arg == "--anwenden":
        sys.exit(anwenden())
    bericht()
    print("\n  Nur geprueft. NICHT VOR DEM 27.08.2026 anwenden.\n")
