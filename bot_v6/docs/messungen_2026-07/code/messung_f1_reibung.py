# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit F1 vom 30.07.2026.
# Nicht archivieren - Beleg fuer die Kostenhuerden-Messung. Siehe ../README.md
"""
F1 - Wie hoch ist die Kostenhuerde wirklich?

a) Ordertypen: welche Order-Aufrufe stehen tatsaechlich im Code?
   Der Scan liest die Dateien zur Laufzeit und gibt Datei:Zeile aus -
   keine abgeschriebene Behauptung.
b) Gebuehren im Code und in config.json.
c) Break-even-Trefferquote P(auf) fuer verschiedene Reibungsniveaus,
   symmetrisches Barrierenrennen wie in E2 (+-2,5 %).
d) Horizont-Analyse: mediane absolute Bewegung je Haltedauer gegen die
   feste Rundenreibung, aus den vorhandenen 15m-Kerzen, beide Jahre.

WICHTIG ZUR DEUTUNG VON d)
--------------------------
"Bewegung traegt die Kosten" heisst NUR: die Kursbewegung ist gross genug,
dass Reibung sie nicht auffrisst. Es heisst NICHT, dass sich damit Geld
verdienen laesst - dafuer braucht es einen Richtungsvorteil, und den misst
E2 (Befund 9) als nicht vorhanden. d) begrenzt das Feld, es oeffnet keines.
"""
import os
import re
import sys
import json

from harness_ext import lade_jahr, COINS, PROJEKT
from messung_f_stat import median, quantil

REIBUNG_IST = 0.30        # % je Runde: 2 x 0,1 % Gebuehr + 2 x 0,05 % Slippage
BARRIERE = 2.5            # % Schranke des E2-Barrierentests
J2_KI_OBEN = 52.56        # % obere 95-%-KI-Grenze Jahr 2 (BEFUNDE.md, Befund 10)
J1_KI_OBEN = 57.69        # % obere 95-%-KI-Grenze Jahr 1

BALKEN_15M = {"1 h": 4, "4 h": 16, "24 h": 96, "72 h": 288, "7 d": 672}


# ===========================================================================
# F1a - Ordertypen aus dem Quelltext
# ===========================================================================
ORDER_MUSTER = re.compile(
    r"create_(market|limit)_(buy|sell)_order|create_order\s*\(|"
    r"postOnly|post_only|timeInForce")

SCAN_ORDNER = ["execution", "live", "agents", "portfolio", "risk", "core",
               "backtest", "features", "data", "models", "runtime", "ui"]
SCAN_DATEIEN = ["app.py", "cockpit_server.py"]


def _py_dateien():
    out = []
    for d in SCAN_DATEIEN:
        p = os.path.join(PROJEKT, d)
        if os.path.isfile(p):
            out.append(p)
    for o in SCAN_ORDNER:
        wurzel = os.path.join(PROJEKT, o)
        if not os.path.isdir(wurzel):
            continue
        for pfad, dirs, dateien in os.walk(wurzel):
            dirs[:] = [x for x in dirs
                       if x not in ("__pycache__",) and not x.startswith("_archive")]
            for f in sorted(dateien):
                if f.endswith(".py"):
                    out.append(os.path.join(pfad, f))
    return out


def f1a():
    print("\n" + "=" * 100)
    print(" F1a  ORDERTYPEN - was ruft der Bot tatsaechlich auf?")
    print("=" * 100)
    treffer = {"market": [], "limit": [], "generisch": [], "flags": []}
    for pfad in _py_dateien():
        try:
            with open(pfad, encoding="utf-8", errors="replace") as f:
                zeilen = f.readlines()
        except OSError:
            continue
        rel = os.path.relpath(pfad, PROJEKT).replace("\\", "/")
        for nr, z in enumerate(zeilen, 1):
            if z.lstrip().startswith("#"):
                continue
            m = ORDER_MUSTER.search(z)
            if not m:
                continue
            eintrag = (rel, nr, z.strip()[:88])
            g = m.group(0)
            if "create_market" in g:
                treffer["market"].append(eintrag)
            elif "create_limit" in g:
                treffer["limit"].append(eintrag)
            elif "create_order" in g:
                treffer["generisch"].append(eintrag)
            else:
                treffer["flags"].append(eintrag)

    for name, titel in (("market", "MARKET-Orders"),
                        ("limit", "LIMIT-Orders"),
                        ("generisch", "create_order(...) generisch"),
                        ("flags", "postOnly / timeInForce")):
        lst = treffer[name]
        print(f"\n  {titel}: {len(lst)} Fundstellen")
        if not lst:
            print("    (keine)")
            continue
        for rel, nr, txt in lst:
            print(f"    {rel}:{nr}  {txt}")

    print("\n  ERGEBNIS F1a")
    print(f"    Market-Aufrufe : {len(treffer['market'])}")
    print(f"    Limit-Aufrufe  : {len(treffer['limit'])}")
    print(f"    Limit im Bot unterstuetzt: "
          f"{'JA' if treffer['limit'] or treffer['generisch'] else 'NEIN'}")
    sys.stdout.flush()
    return treffer


# ===========================================================================
# F1b - Gebuehren im Code und in config.json
# ===========================================================================
GEB_MUSTER = re.compile(
    r"fee_rate\s*=|GEBUEHR\s*=|SLIPPAGE\s*=|slippage_pct\s*=|"
    r"\"maker\"|'maker'|\"taker\"|'taker'|bnb_discount|base_bps\s*=")


def f1b():
    print("\n" + "=" * 100)
    print(" F1b  GEBUEHREN - was steht im Code, was in config.json?")
    print("=" * 100)
    print("\n  Fundstellen im Quelltext")
    for pfad in _py_dateien():
        try:
            with open(pfad, encoding="utf-8", errors="replace") as f:
                zeilen = f.readlines()
        except OSError:
            continue
        rel = os.path.relpath(pfad, PROJEKT).replace("\\", "/")
        for nr, z in enumerate(zeilen, 1):
            if z.lstrip().startswith("#"):
                continue
            if GEB_MUSTER.search(z):
                print(f"    {rel}:{nr}  {z.strip()[:88]}")

    print("\n  config.json - Suche nach Gebuehren-/Slippage-Schluesseln")
    cfg_pfad = os.path.join(PROJEKT, "data_store", "config.json")
    with open(cfg_pfad, encoding="utf-8") as f:
        cfg = json.load(f)

    gefunden = []

    def _lauf(d, pfad=""):
        if isinstance(d, dict):
            for k, v in d.items():
                p = f"{pfad}.{k}" if pfad else k
                if re.search(r"fee|gebuehr|maker|taker|slip|commission|cost",
                             k, re.I):
                    gefunden.append((p, v))
                _lauf(v, p)

    _lauf(cfg)
    if gefunden:
        for p, v in gefunden:
            print(f"    {p} = {v}")
    else:
        print("    KEIN einziger Gebuehren- oder Slippage-Schluessel vorhanden.")
    print(f"    (config.json Top-Level-Bloecke: {', '.join(cfg.keys())})")

    print("\n  ERGEBNIS F1b - die Reibung, wie sie im Code steht")
    print("    Paper-Pfad  (execution/engine.py:251)  Gebuehr 0,100 % je Seite")
    print("    Paper-Pfad  (execution/engine.py:243)  Slippage U(0,02;0,08) %"
          " je Seite, Erwartungswert 0,050 %")
    print("    Harness     (backtest/ausstieg_backtest.py:59/60) 0,100 % + 0,050 %")
    print("    Tabelle     (backtest/fees.py:9) binance maker 0,10 / taker 0,10")
    print("    -> Rundenreibung = 2 x (0,100 + 0,050) = 0,300 %  [deckt sich"
          " mit der bisher angenommenen Zahl]")
    sys.stdout.flush()


# ===========================================================================
# F1c - Break-even-Trefferquote
# ===========================================================================
def p_break_even(reibung_pct, barriere_pct):
    """Symmetrisches Barrierenrennen: p*B - (1-p)*B - c = 0 -> p = 0,5 + c/(2B)."""
    return 0.5 + reibung_pct / (2.0 * barriere_pct)


def f1c():
    print("\n" + "=" * 100)
    print(" F1c  BREAK-EVEN-TREFFERQUOTE P(auf) je Reibungsniveau")
    print("=" * 100)
    print("\n  Modell: symmetrisches First-Touch-Rennen wie E2, Schranken"
          f" +-{BARRIERE:.1f} %.")
    print("    Gewinn je Treffer  = +B, Verlust je Fehltreffer = -B,"
          " Reibung c je Runde.")
    print("    Break-even: p*B - (1-p)*B = c   ->   p = 0,5 + c/(2B)")
    print("\n  Vergleichswerte aus E2 (BEFUNDE.md, Befund 9/10):")
    print("    gemessen J2 47,66 %   |   95-%-KI-Obergrenze J2 52,56 %")
    print("    gemessen J1 50,69 %   |   95-%-KI-Obergrenze J1 57,69 %")

    stufen = [0.30, 0.20, 0.15, 0.10, 0.05, 0.00]
    print(f"\n    {'Reibung/Runde':>14s} {'P(auf) noetig':>14s} "
          f"{'Luecke zu 47,66%':>17s} {'J2-Obergr. reicht?':>19s} "
          f"{'J1-Obergr. reicht?':>19s}")
    print("    " + "-" * 90)
    for c in stufen:
        p = p_break_even(c, BARRIERE) * 100
        luecke = p - 47.66
        j2 = "JA" if J2_KI_OBEN >= p else "nein"
        j1 = "JA" if J1_KI_OBEN >= p else "nein"
        marke = "  <- Ist" if abs(c - REIBUNG_IST) < 1e-9 else ""
        print(f"    {c:13.2f}% {p:13.2f}% {luecke:+16.2f}pp "
              f"{j2:>19s} {j1:>19s}{marke}")

    # Umkehrung: welche Reibung machte die KI-Obergrenzen break-even?
    c_j2 = (J2_KI_OBEN / 100 - 0.5) * 2 * BARRIERE
    c_j1 = (J1_KI_OBEN / 100 - 0.5) * 2 * BARRIERE
    c_pkt = (47.66 / 100 - 0.5) * 2 * BARRIERE
    print("\n  UMKEHRUNG - welche Reibung waere noetig, damit der gemessene"
          " Wert traegt?")
    print(f"    J2 Punktschaetzer 47,66 %  -> c = {c_pkt:+.4f} %"
          "   (negativ: es muesste eine Praemie GEZAHLT werden)")
    print(f"    J2 KI-Obergrenze  52,56 %  -> c = {c_j2:.4f} %")
    print(f"    J1 KI-Obergrenze  57,69 %  -> c = {c_j1:.4f} %")

    print("\n  ERREICHBARE UNTERGRENZEN nach den Zahlen im Projekt")
    fuss = [
        ("Ist (Market, Standardgebuehr)", 2 * (0.100 + 0.050), "engine.py:243/251"),
        ("Market + BNB-Rabatt 0,075 %", 2 * (0.075 + 0.050), "fees.py:9 bnb_discount"),
        ("Limit/Maker, Gebuehr unveraendert 0,10 %", 2 * (0.100 + 0.000),
         "fees.py:9 maker == taker"),
        ("Limit/Maker + BNB-Rabatt", 2 * (0.075 + 0.000), "fees.py:9 kombiniert"),
    ]
    print(f"    {'Szenario':<44s} {'c/Runde':>9s} {'P(auf) noetig':>14s} "
          f"{'>52,56%?':>10s}  Beleg")
    print("    " + "-" * 100)
    for name, c, beleg in fuss:
        p = p_break_even(c, BARRIERE) * 100
        print(f"    {name:<44s} {c:8.3f}% {p:13.2f}% "
              f"{('reicht' if J2_KI_OBEN >= p else 'REICHT NICHT'):>10s}  {beleg}")
    sys.stdout.flush()


# ===========================================================================
# F1d - Horizont-Analyse
# ===========================================================================
def bewegungen(kerzen, h_balken):
    """Absolute Close-zu-Close-Bewegung in % ueber h Balken, ueberlappend."""
    out = []
    n = len(kerzen)
    for i in range(0, n - h_balken):
        a = kerzen[i][4]
        b = kerzen[i + h_balken][4]
        if a > 0:
            out.append(abs(b / a - 1.0) * 100.0)
    return out


def f1d():
    print("\n" + "=" * 100)
    print(" F1d  HORIZONT - mediane absolute Bewegung gegen feste Rundenreibung")
    print("=" * 100)
    print(f"\n  Reibung je Runde: {REIBUNG_IST:.2f} % (fix, unabhaengig vom"
          " Horizont).")
    print("  |Bewegung| = |Close(t+h)/Close(t) - 1|, ueberlappende Fenster auf"
          " 15m-Kerzen.")
    print("  Quote = Median(|Bewegung|) / Reibung. Quote > 1 heisst: die"
          " typische Bewegung")
    print("  ist groesser als die Kosten - es heisst NICHT, dass sie in die"
          " richtige Richtung geht.")

    for jahr, marke in (("Jahr 2  2025-07..2026-07", ""),
                        ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, _fg = lade_jahr(marke)
        print(f"\n  {jahr}")
        print(f"    {'Coin':<10s}" + "".join(f"{k:>12s}" for k in BALKEN_15M))
        print("    " + "-" * (10 + 12 * len(BALKEN_15M)))
        gepoolt = {k: [] for k in BALKEN_15M}
        for coin in COINS:
            ks = daten.get(coin)
            if not ks:
                continue
            zeile = f"    {coin.split('/')[0]:<10s}"
            for name, hb in BALKEN_15M.items():
                bw = bewegungen(ks, hb)
                gepoolt[name].extend(bw)
                zeile += f"{median(bw):11.2f}%"
            print(zeile)
        print("    " + "-" * (10 + 12 * len(BALKEN_15M)))

        print(f"\n    {'Horizont':<10s} {'Median|Bew|':>12s} {'Quote':>8s} "
              f"{'P25':>9s} {'P75':>9s} {'Anteil >0,30%':>14s} "
              f"{'noetige P(auf)':>15s}")
        print("    " + "-" * 84)
        for name, hb in BALKEN_15M.items():
            bw = gepoolt[name]
            med = median(bw)
            q25, q75 = quantil(bw, 0.25), quantil(bw, 0.75)
            anteil = sum(1 for x in bw if x > REIBUNG_IST) / len(bw) * 100
            # Break-even fuer ein Rennen mit Schranke = Median-Bewegung
            p_noetig = p_break_even(REIBUNG_IST, med) * 100 if med > 0 else 100.0
            print(f"    {name:<10s} {med:11.2f}% {med / REIBUNG_IST:8.2f} "
                  f"{q25:8.2f}% {q75:8.2f}% {anteil:13.1f}% {p_noetig:14.2f}%")
        sys.stdout.flush()

    print("\n  LESART")
    print("    Die letzte Spalte beantwortet F1d direkt: haelt man eine Position")
    print("    so lange, dass die typische Bewegung dem Median entspricht, und")
    print("    setzt die Schranken auf diesen Median, dann braucht es diese")
    print("    Trefferquote, um die 0,30 % Reibung zu decken. Je laenger der")
    print("    Horizont, desto naeher rueckt sie an 50 %.")


def main():
    print("=" * 100)
    print(" MESSUNG F1 - DIE HUERDE: wie hoch muss sie wirklich sein?")
    print(" Stand 30.07.2026 - Datenbasis wie PRUEFSUMMEN.txt")
    print("=" * 100)
    f1a()
    f1b()
    f1c()
    f1d()
    print("\n" + "=" * 100)
    print(" ENDE F1")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
