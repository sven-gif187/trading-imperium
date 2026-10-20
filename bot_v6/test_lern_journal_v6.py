# -*- coding: utf-8 -*-
"""Test fuer den sauberen V6-Lernzaehler (Variante C, 11.08.2026).

Laeuft vollstaendig in einem Wegwerf-Ordner. Ruehrt data_store/ NICHT an -
der Bot darf waehrenddessen laufen.

Aufruf:  python test_lern_journal_v6.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.lern_journal_v6 import LernJournalV6          # noqa: E402
from core.telemetrie import Telemetrie                    # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print(("  OK   " if bedingung else "  FEHLT") + "  " + text)
    if not bedingung:
        fehler.append(text)


def main():
    ordner = tempfile.mkdtemp(prefix="lernjournal_test_")
    datei = os.path.join(ordner, "brain_performance_v6.json")
    db = os.path.join(ordner, "t.db")
    try:
        tel = Telemetrie(db_datei=db)
        j = LernJournalV6(datei=datei, telemetrie=tel, aktiv=True)

        print("\n1) Verluste werden gezaehlt (das war Bug B1)")
        j.buchen("TEST_STRAT", -1.23, quelle="exit_monitor", symbol="BTC/USDC")
        j.buchen("TEST_STRAT", +2.00, quelle="exit_monitor", symbol="BTC/USDC")
        j.buchen("TEST_STRAT", 0.0, quelle="order_filled", symbol="ETH/USDC")
        p = j.performance["TEST_STRAT"]
        pruefe(p["trades"] == 3, "3 Faelle gezaehlt")
        pruefe(p["wins"] == 1, "1 Gewinn (0.0 zaehlt NICHT als Gewinn)")
        pruefe(p["losses"] == 2, "2 Nicht-Gewinne")
        pruefe(abs(p["total_pnl"] - 0.77) < 1e-9, "Summe P&L = +0.77")
        pruefe(abs(p["win_rate"] - 33.33) < 0.01, "Trefferquote 33,33 %")
        pruefe(p["quellen"] == {"exit_monitor": 2, "order_filled": 1},
               "Herkunft je Weg festgehalten")

        print("\n2) Datei ist da, gueltiges JSON, kein V4 drin")
        pruefe(os.path.exists(datei), "Datei geschrieben")
        with open(datei, "r", encoding="utf-8") as f:
            roh = f.read()
        d = json.loads(roh)
        pruefe(d["total_trades"] == 3, "Gesamtzahl stimmt")
        pruefe("v4_bootstrap" not in roh, "keine V4-Altdaten enthalten")
        pruefe("\x00" not in roh, "keine Nullbytes")

        print("\n3) Neustart verliert nichts")
        j2 = LernJournalV6(datei=datei, telemetrie=None, aktiv=True)
        pruefe(j2.performance["TEST_STRAT"]["trades"] == 3, "Stand ueberlebt Neustart")

        print("\n4) Mindestdatenmenge sperrt duenne Zahlen")
        pruefe(not j2.ist_belastbar("TEST_STRAT"), "3 Faelle gelten NICHT als belastbar")
        for _ in range(20):
            j2.buchen("TEST_STRAT", 1.0, quelle="test")
        pruefe(j2.ist_belastbar("TEST_STRAT"), "23 Faelle gelten als belastbar")

        print("\n5) Rohspur in der Datenbank")
        import sqlite3
        con = sqlite3.connect(db)
        n = con.execute("select count(*) from lern_ereignisse").fetchone()[0]
        verl = con.execute("select count(*) from lern_ereignisse "
                           "where gewonnen=0").fetchone()[0]
        con.close()
        pruefe(n == 3, "3 Einzelfaelle in lern_ereignisse (nur j hatte die DB)")
        pruefe(verl == 2, "davon 2 als Nicht-Gewinn markiert")

        print("\n6) Kaputte Eingaben duerfen nichts umwerfen")
        pruefe(j.buchen("X", "keine Zahl") is False, "Text als P&L -> False, kein Absturz")
        pruefe(j.buchen(None, None) is False, "None -> False, kein Absturz")
        pruefe(j.performance.get("X") is None, "nichts Halbes gebucht")

        print("\n7) Abschalter wirkt")
        j3 = LernJournalV6(datei=os.path.join(ordner, "aus.json"),
                           telemetrie=None, aktiv=False)
        pruefe(j3.buchen("A", 1.0) is False, "abgeschaltet -> bucht nicht")
        pruefe(not os.path.exists(os.path.join(ordner, "aus.json")),
               "abgeschaltet -> legt keine Datei an")

        print("\n8) DB-Ausfall darf den Zaehler nicht stoppen")
        class KaputteDB:
            def lern_ereignis(self, **kw):
                raise RuntimeError("DB weg")
        j4 = LernJournalV6(datei=os.path.join(ordner, "b.json"),
                           telemetrie=KaputteDB(), aktiv=True)
        pruefe(j4.buchen("B", -5.0) is True, "JSON-Buchung gelingt trotz DB-Fehler")
        pruefe(j4.performance["B"]["losses"] == 1, "Verlust trotzdem gezaehlt")

        print("\n9) Status-Auskunft")
        s = j2.status()
        pruefe(s["faelle_gesamt"] == 23, "Statuszahl stimmt")
        pruefe(s["verluste"] == 2, "Verluste im Status sichtbar")
        pruefe("TEST_STRAT" in s["belastbare_strategien"], "belastbare Strategie gelistet")

    finally:
        shutil.rmtree(ordner, ignore_errors=True)

    print("\n" + "=" * 52)
    if fehler:
        print("FEHLGESCHLAGEN: %d von vielen" % len(fehler))
        for f in fehler:
            print("   -", f)
        return 1
    print("ALLE TESTS BESTANDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
