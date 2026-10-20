# -*- coding: utf-8 -*-
"""warteauftrag_maschine_test.py - der Warte-Auftrag durch die ECHTE Maschine.

WOZU
----
`warteauftrag_test.py` prueft die Warteschlange fuer sich allein. Das
beantwortet aber nicht die Frage, auf die es ankommt: Tut die
Ausfuehrungsmaschine (`execution/engine.py`) mit einem Warte-Auftrag
wirklich das Richtige - richtiger Preis, richtige Gebuehr, richtiger
Bestand, und kein Bestand, solange er nur wartet?

Dieses Programm baut eine eigene ExecutionEngine mit eigenen Papier-
Bestaenden und rechnet einen vollstaendigen Vorgang durch. Vorbild:
gebuehren_test.py.

Die sieben Pruefungen:

  1  Schalter aus              kauft sofort, Taker 0,25 %, wie bisher
  2  Schalter an, Kauf         legt einen Auftrag hin, KEIN Bestand
  3  Kurs bleibt oben          nichts passiert, Auftrag wartet
  4  Kurs faellt aufs Limit    gefuellt, Maker 0,10 %, Bestand da
  5  Der Fuellpreis            ist der Limitpreis, ohne Schlupf
  6  Kurs faellt NICHT         Auftrag verfaellt, kein Bestand, Geld ganz
  7  Verkauf                   bleibt IMMER Sofort-Auftrag

AENDERT NICHTS AM LAUFENDEN BOT. Eigene Maschine, eigene Bestaende,
eigene Warteschlangen-Datei im Temp-Ordner.

    python warteauftrag_maschine_test.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig                      # noqa: E402
from core.events import DecisionIntent, Side               # noqa: E402
from execution.engine import ExecutionEngine               # noqa: E402
from execution.warteauftraege import Warteschlange         # noqa: E402

EINSATZ = 200.0
KURS = 100.0
STUNDE = 3600.0
T0 = 1789000000.0


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, nummer, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("  %d  %-40s ok   %s" % (nummer, was, zusatz))
        else:
            self.fehler.append((nummer, was, zusatz))
            print("  %d  %-40s FEHL %s" % (nummer, was, zusatz))


def maschine(ordner, aktiv, name):
    """Eine frische Engine mit eigener Warteschlange."""
    cfg = AppConfig()
    cfg.trading.mode = "paper"
    eng = ExecutionEngine(cfg)
    eng._paper_balances = {"USDC": 10000.0}
    eng._paper_entries = {}
    eng.warteschlange = Warteschlange(
        pfad=os.path.join(ordner, "%s.json" % name),
        einstellungen={"aktiv": aktiv, "abstand_pct": 0.10,
                       "gueltig_kerzen": 4, "kerze_minuten": 15},
        jetzt=T0)
    return eng


def kaufauftrag(symbol="TEST/USDC"):
    return DecisionIntent(symbol=symbol, side=Side.BUY,
                          amount_usd=EINSATZ, entry_price=KURS,
                          strategy_id="PRUEFUNG", score=8)


def main():
    print("=" * 76)
    print("  WARTE-AUFTRAG durch die echte Maschine")
    print("=" * 76)
    print()

    ordner = tempfile.mkdtemp(prefix="warteauftrag_masch_")
    p = Pruefung()
    try:
        # --- 1  Schalter aus: alles wie bisher -------------------------
        eng = maschine(ordner, False, "aus")
        r = eng.execute(kaufauftrag())
        taker_erwartet = EINSATZ * 0.0025
        p.sage(1, "Schalter aus: kauft sofort",
               r.status == "filled" and abs(r.fee - taker_erwartet) < 0.001,
               "Gebuehr %.4f $ (Taker, erwartet %.4f)" % (r.fee, taker_erwartet))

        # --- 2  Schalter an: legt hin, kauft nicht ---------------------
        eng = maschine(ordner, True, "an")
        vorher_usdc = eng._paper_balances.get("USDC", 0)
        r = eng.execute(kaufauftrag())
        bestand = eng._paper_balances.get("TEST", 0)
        p.sage(2, "Schalter an: legt einen Auftrag hin",
               r.status == "wartet" and bestand == 0
               and eng._paper_balances.get("USDC", 0) == vorher_usdc,
               "Limit %.4f $, kein Bestand, Kasse unberuehrt" % r.avg_fill_price)

        limit_erwartet = KURS * 0.999
        p.sage(3, "Limitpreis 0,10 % unter 100,00 $",
               abs(r.avg_fill_price - limit_erwartet) < 1e-6,
               "%.4f $ (erwartet %.4f)" % (r.avg_fill_price, limit_erwartet))

        # --- 4  Kurs bleibt oben: nichts passiert ----------------------
        fertige = eng.warteauftraege_pruefen({"TEST/USDC": 99.95})
        p.sage(4, "Kurs 99,95 $ liegt ueber dem Limit",
               not fertige and "TEST/USDC" in eng.warteschlange.offene(),
               "wartet weiter")

        # --- 5  Kurs faellt: gefuellt, Maker ---------------------------
        fertige = eng.warteauftraege_pruefen({"TEST/USDC": 99.90})
        if not fertige:
            p.sage(5, "Kurs auf dem Limit: gefuellt", False, "nichts gefuellt")
        else:
            intent, res = fertige[0]
            maker_erwartet = EINSATZ * 0.0010
            bestand = eng._paper_balances.get("TEST", 0)
            p.sage(5, "Kurs auf dem Limit: gefuellt",
                   res.status == "filled" and bestand > 0,
                   "Bestand %.6f" % bestand)
            p.sage(6, "Gebuehr ist Maker, nicht Taker",
                   abs(res.fee - maker_erwartet) < 0.001,
                   "%.4f $ (Maker, erwartet %.4f; Taker waere %.4f)"
                   % (res.fee, maker_erwartet, taker_erwartet))
            p.sage(7, "Fuellpreis ist der Limitpreis, ohne Schlupf",
                   abs(res.avg_fill_price - limit_erwartet) < 1e-6
                   and abs(res.slippage_pct) < 1e-9,
                   "%.4f $, Schlupf %.4f %%" % (res.avg_fill_price, res.slippage_pct))
            # Kostenbasis wie in gebuehren_test.py
            basis = (res.filled_cost or 0) + (res.fee or 0)
            p.sage(8, "Kostenbasis ist der echte Mittelabfluss",
                   abs(basis - EINSATZ) < 0.01,
                   "%.4f $ (Einsatz %.2f, Abweichung %+.4f)"
                   % (basis, EINSATZ, basis - EINSATZ))
            p.sage(9, "Die Angaben vom Kauf kommen mit",
                   intent.strategy_id == "PRUEFUNG" and intent.score == 8,
                   "strategy_id=%s score=%d" % (intent.strategy_id, intent.score))

        # --- 10  Kurs faellt nicht: verfaellt --------------------------
        eng2 = maschine(ordner, True, "verfall")
        r = eng2.execute(kaufauftrag())
        kasse_vorher = eng2._paper_balances.get("USDC", 0)
        # Die Frist von Hand vorziehen, statt eine Stunde zu warten
        eng2.warteschlange.auftraege["TEST/USDC"]["verfaellt_ts"] = T0
        fertige = eng2.warteauftraege_pruefen({"TEST/USDC": 100.00})
        p.sage(10, "Frist abgelaufen: verfaellt",
               not fertige and not eng2.warteschlange.offene()
               and eng2._paper_balances.get("TEST", 0) == 0
               and eng2._paper_balances.get("USDC", 0) == kasse_vorher,
               "kein Bestand, Kasse %.2f $ unberuehrt"
               % eng2._paper_balances.get("USDC", 0))

        # --- 11  Verkauf bleibt sofort ---------------------------------
        eng3 = maschine(ordner, True, "verkauf")
        eng3._paper_balances = {"USDC": 1000.0, "TEST": 2.0}
        eng3._paper_entries = {"TEST/USDC": 100.0}
        verkauf = DecisionIntent(symbol="TEST/USDC", side=Side.SELL,
                                 quantity=2.0, entry_price=110.0)
        rv = eng3.execute(verkauf)
        p.sage(11, "Verkauf bleibt IMMER Sofort-Auftrag",
               rv.status == "filled" and not eng3.warteschlange.offene(),
               "sofort gefuellt, keine Warteschlange")

        # --- Gegentest -------------------------------------------------
        print()
        print("  Gegentest - waere der Unterschied ueberhaupt sichtbar?")
        print("    Taker (Sofortkauf)  %.4f $ auf %.2f $ Einsatz" % (taker_erwartet, EINSATZ))
        print("    Maker (Warte)       %.4f $" % (EINSATZ * 0.0010))
        unterschied = taker_erwartet - EINSATZ * 0.0010
        print("    Unterschied         %.4f $ = %.3f Prozentpunkte je Seite"
              % (unterschied, 100.0 * unterschied / EINSATZ))
        if unterschied <= 0:
            print("    Kein Unterschied - dann prueft Nummer 6 nichts.")
            p.fehler.append((0, "Gegentest", "Maker = Taker"))
        else:
            print("    Ein vertauschter Satz waere in Nummer 6 aufgefallen.")

    finally:
        shutil.rmtree(ordner, ignore_errors=True)

    print()
    print("-" * 76)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d Pruefungen"
              % (len(p.fehler), p.ok + len(p.fehler)))
        for nummer, was, zusatz in p.fehler:
            print("    %s  %s  %s" % (nummer, was, zusatz))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Der Schalter steht in data_store/config.json auf aktiv=false.")
    print("  Einschalten ist eine VERHALTENSAENDERUNG und braucht vorher")
    print("  eine Epochengrenze in config_epochs.json - sonst sind alle")
    print("  Vorher-Nachher-Vergleiche ueber die Grenze hinweg wertlos.")
    print("-" * 76)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
