# -*- coding: utf-8 -*-
"""Test fuer den Dreifach-Schalter (Aufgabe 3, 11.08.2026).

Die wichtigste Pruefung ist Abschnitt 2: JEDER Fehlerfall muss bei ACTIVE
landen. Ein Tippfehler in der Konfiguration darf niemals versehentlich eine
Regel abschalten - im Zweifel gilt das heutige Verhalten.

Laeuft in einem Wegwerf-Ordner. Der Bot darf dabei laufen.

Aufruf:  python test_regel_schalter.py
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from core.regel_schalter import (RegelSchalter, ACTIVE, SHADOW, OFF,   # noqa: E402
                                 BEKANNTE_REGELN)
from core.telemetrie import Telemetrie                                 # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print(("  OK   " if bedingung else "  FEHLT") + "  " + text)
    if not bedingung:
        fehler.append(text)


def schreibe_config(ordner, inhalt):
    pfad = os.path.join(ordner, "config.json")
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(inhalt, f)
    return pfad


def main():
    ordner = tempfile.mkdtemp(prefix="schalter_test_")
    try:
        db = os.path.join(ordner, "t.db")
        tel = Telemetrie(db_datei=db)

        print("\n1) Ohne Konfiguration steht alles auf ACTIVE")
        s = RegelSchalter(telemetrie=tel,
                          config_datei=os.path.join(ordner, "gibtsnicht.json"))
        pruefe(all(s.modus(r) == ACTIVE for r in BEKANNTE_REGELN),
               f"alle {len(BEKANNTE_REGELN)} Regeln auf ACTIVE")
        pruefe(s.wirkt("trend_exit") is True, "wirkt() = True")
        pruefe(s.startmeldung() == "", "Startmeldung schweigt, wenn alles scharf ist")

        print("\n2) JEDER Fehlerfall landet bei ACTIVE (die Kernpruefung)")
        for beschreibung, inhalt in (
                ("Tippfehler im Zustand", {"regel_modi": {"trend_exit": "SHADOOW"}}),
                ("Zustand leer", {"regel_modi": {"trend_exit": ""}}),
                ("Zahl statt Text", {"regel_modi": {"trend_exit": 0}}),
                ("null", {"regel_modi": {"trend_exit": None}}),
                ("Block ist kein Dict", {"regel_modi": "aus"}),
                ("Block fehlt ganz", {"andere_sachen": 1})):
            p = schreibe_config(ordner, inhalt)
            s2 = RegelSchalter(telemetrie=tel, config_datei=p)
            pruefe(s2.modus("trend_exit") == ACTIVE, f"{beschreibung} -> ACTIVE")
        with open(os.path.join(ordner, "config.json"), "w", encoding="utf-8") as f:
            f.write("{kaputt,,,")
        s2 = RegelSchalter(telemetrie=tel,
                           config_datei=os.path.join(ordner, "config.json"))
        pruefe(s2.modus("trend_exit") == ACTIVE, "unlesbare Datei -> ACTIVE")

        print("\n3) Gross- und Kleinschreibung, Leerzeichen")
        p = schreibe_config(ordner, {"regel_modi": {"trend_exit": " shadow ",
                                                    "baerenmarkt": "Off"}})
        s3 = RegelSchalter(telemetrie=tel, config_datei=p)
        pruefe(s3.modus("trend_exit") == SHADOW, "' shadow ' wird erkannt")
        pruefe(s3.modus("baerenmarkt") == OFF, "'Off' wird erkannt")

        print("\n4) wirkt() und schreibt_mit()")
        pruefe(s3.wirkt("trend_exit") is False, "SHADOW -> wirkt False")
        pruefe(s3.schreibt_mit("trend_exit") is True, "SHADOW -> schreibt mit")
        pruefe(s3.wirkt("baerenmarkt") is False, "OFF -> wirkt False")
        pruefe(s3.schreibt_mit("baerenmarkt") is False, "OFF -> schreibt NICHT mit")
        pruefe(s3.wirkt("smart_entry") is True, "nicht genannte Regel -> ACTIVE")

        print("\n5) Notiert wird ausschliesslich im Zustand SHADOW")
        pruefe(s3.notieren("trend_exit", symbol="BTC/USDC",
                           haette="verkauft", grund="MTF baerisch",
                           preis=63750.0, pnl_pct=-1.2) is True, "SHADOW notiert")
        pruefe(s3.notieren("baerenmarkt", symbol="SOL/USDC",
                           haette="blockiert") is False, "OFF notiert nicht")
        pruefe(s3.notieren("smart_entry", symbol="ETH/USDC",
                           haette="verzoegert") is False, "ACTIVE notiert nicht")
        con = sqlite3.connect(db)
        zeilen = con.execute("SELECT regel,symbol,haette,grund,preis,pnl_pct "
                             "FROM schatten_regeln").fetchall()
        con.close()
        pruefe(len(zeilen) == 1, f"genau 1 Zeile in der Datenbank ({len(zeilen)})")
        pruefe(zeilen[0][0] == "trend_exit" and zeilen[0][1] == "BTC/USDC",
               "Regel und Symbol gespeichert")
        pruefe(abs(zeilen[0][5] - (-1.2)) < 0.001, "PnL gespeichert")

        print("\n6) Unbekannte Eintraege werden gemeldet, nicht verschluckt")
        p = schreibe_config(ordner, {"regel_modi": {"gibtsgarnicht": "SHADOW",
                                                    "trend_exit": "QUATSCH"}})
        s4 = RegelSchalter(telemetrie=tel, config_datei=p)
        st = s4.status()
        pruefe("gibtsgarnicht" in st["unbekannte_eintraege"],
               "unbekannte Regel taucht im Status auf")
        pruefe(any("QUATSCH" in e for e in st["unbekannte_eintraege"]),
               "unsinniger Zustand taucht im Status auf")
        pruefe(s4.modus("trend_exit") == ACTIVE, "trotzdem ACTIVE")

        print("\n7) Startmeldung nennt jede nicht scharfe Regel")
        meldung = s3.startmeldung()
        pruefe("trend_exit=SHADOW" in meldung, "SHADOW steht in der Meldung")
        pruefe("baerenmarkt=OFF" in meldung, "OFF steht in der Meldung")

        print("\n8) Kaputte Telemetrie stoppt nichts")
        class KaputteDB:
            def schatten_regel(self, **kw):
                raise RuntimeError("DB weg")
        s5 = RegelSchalter(telemetrie=KaputteDB(),
                           config_datei=schreibe_config(
                               ordner, {"regel_modi": {"trend_exit": "SHADOW"}}))
        pruefe(s5.notieren("trend_exit", symbol="X") is False,
               "meldet False statt abzustuerzen")
        pruefe(s5.wirkt("trend_exit") is False, "Schalter funktioniert weiter")

        print("\n9) Neu laden ohne Neustart")
        p = schreibe_config(ordner, {"regel_modi": {"trend_exit": "SHADOW"}})
        s6 = RegelSchalter(telemetrie=tel, config_datei=p)
        pruefe(s6.modus("trend_exit") == SHADOW, "vorher SHADOW")
        schreibe_config(ordner, {"regel_modi": {"trend_exit": "ACTIVE"}})
        s6.neu_laden()
        pruefe(s6.modus("trend_exit") == ACTIVE, "nach neu_laden() ACTIVE")

    finally:
        shutil.rmtree(ordner, ignore_errors=True)

    print("\n" + "=" * 52)
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        for f in fehler:
            print("   -", f)
        return 1
    print("ALLE TESTS BESTANDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
