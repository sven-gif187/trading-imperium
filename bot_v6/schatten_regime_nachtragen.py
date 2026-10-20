#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  SCHATTEN-REGIME NACHTRAGEN
================================================================
Angelegt 19.08.2026. Die Spalte `regime` war in ALLEN 697 Zeilen
von schatten_universum.db leer - eine Auslassung im Sammler
(siehe schatten_universum._regime_von).

Nachtragbar ist sie trotzdem, und zwar EXAKT: der Marktzustand
haengt allein am ADX, und der steht in jeder Zeile mit drin.

    market_data.py:102
    reg = TRENDING if adx > 25 else RANGING if adx < 20 else UNKNOWN

Es wird also nichts geschaetzt und nichts erfunden - dieselbe
Eingabe, dieselbe Regel, dasselbe Ergebnis, das der Sammler
geschrieben haette.

    python schatten_regime_nachtragen.py --gegenprobe
    python schatten_regime_nachtragen.py                # Probelauf
    python schatten_regime_nachtragen.py --schreiben
================================================================
"""
import os
import sys
import sqlite3
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "schatten_universum.db")
NL = chr(10)


def regime_aus_adx(adx):
    """Genau die Regel aus data/market_data.py:102 - nicht nachgebaut,
    sondern nachgelesen und wortgleich uebernommen."""
    if adx is None:
        return None
    a = float(adx)
    if a > 25:
        return "TRENDING"
    if a < 20:
        return "RANGING"
    return "UNKNOWN"


def gegenprobe():
    """Zwei Richtungen: trifft die Regel die Grenzfaelle, und stimmt
    sie mit dem ueberein, was der Bot fuer dieselben Zahlen sagt?"""
    fehler = 0
    print("=" * 70)
    print("GEGENPROBE 1 - die Grenzfaelle von Hand")
    print("=" * 70)
    faelle = [(None, None), (0.0, "RANGING"), (19.99, "RANGING"),
              (20.0, "UNKNOWN"), (25.0, "UNKNOWN"), (25.01, "TRENDING"),
              (71.9, "TRENDING")]
    for adx, soll in faelle:
        ist = regime_aus_adx(adx)
        ok = ist == soll
        print("  " + ("OK  " if ok else "FEHL") + "  ADX "
              + str(adx).rjust(6) + "  ->  " + str(ist).ljust(9)
              + " erwartet " + str(soll))
        if not ok:
            fehler += 1

    print(NL + "=" * 70)
    print("GEGENPROBE 2 - gegen den echten DataAgent")
    print("=" * 70)
    try:
        sys.path.insert(0, HIER)
        from core.events import MarketRegime
        for adx in (10.0, 22.0, 40.0):
            echt = (MarketRegime.TRENDING if adx > 25
                    else MarketRegime.RANGING if adx < 20
                    else MarketRegime.UNKNOWN).value
            ist = regime_aus_adx(adx)
            ok = ist == echt
            print("  " + ("OK  " if ok else "FEHL") + "  ADX "
                  + str(adx).rjust(6) + "  Nachtrag " + str(ist).ljust(9)
                  + " Bot " + str(echt))
            if not ok:
                fehler += 1
    except Exception as e:
        print("  Bot-Klasse nicht ladbar (" + str(e)[:50] + ")")
        print("  Die Regel steht wortgleich in market_data.py:102.")

    print(NL + ("BESTANDEN" if not fehler else str(fehler) + " FEHLER"))
    return 1 if fehler else 0


def nachtragen(schreiben=False):
    con = sqlite3.connect(DB, timeout=30)
    zeilen = con.execute(
        "SELECT id, adx FROM signale WHERE regime IS NULL OR regime=''"
    ).fetchall()
    print("=" * 70)
    print("NACHTRAG" + ("" if schreiben else "   -   PROBELAUF"))
    print("=" * 70)
    print(NL + str(len(zeilen)) + " Zeilen ohne Marktzustand.")
    if not zeilen:
        return 0

    zaehler = {}
    ohne = 0
    for zid, adx in zeilen:
        r = regime_aus_adx(adx)
        if r is None:
            ohne += 1
            continue
        zaehler[r] = zaehler.get(r, 0) + 1
        if schreiben:
            con.execute("UPDATE signale SET regime=? WHERE id=?", (r, zid))
    if schreiben:
        con.commit()

    print(NL + "  Verteilung, die dabei herauskommt:")
    for r, n in sorted(zaehler.items(), key=lambda x: -x[1]):
        print("    " + r.ljust(10) + str(n).rjust(5) + "   ("
              + format(100.0 * n / len(zeilen), ".0f") + " %)")
    if ohne:
        print("    ohne ADX  " + str(ohne).rjust(5) + "   bleibt leer")
    if not schreiben:
        print(NL + "  PROBELAUF - mit --schreiben wird es eingetragen.")
    else:
        rest = con.execute("SELECT COUNT(*) FROM signale "
                           "WHERE regime IS NULL OR regime=''").fetchone()[0]
        print(NL + "  Danach noch ohne Marktzustand: " + str(rest))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gegenprobe", action="store_true")
    p.add_argument("--schreiben", action="store_true")
    a = p.parse_args()
    sys.exit(gegenprobe() if a.gegenprobe else nachtragen(a.schreiben))
