# -*- coding: utf-8 -*-
"""befund68_test.py - kann eine Wiederholung noch zweimal kaufen?

WOZU
----
Befund 68 ist als **KRITISCH FUER LIVE** eingestuft: `_execute_live` rief
`create_market_buy_order(symbol, menge)` ohne Kennung auf, und darueber
liegt `self.retry.execute()`. Ging die Antwort der Boerse verloren, sendete
der Wiederholungsversuch die Order ein zweites Mal - und die Boerse sah
zwei unabhaengige Auftraege.

Der IdempotencyGuard schuetzt davor NICHT. Er prueft, ob `execute()`
zweimal aufgerufen wird; die Wiederholung passiert INNERHALB eines Aufrufs.

Am 14.09.2026 repariert. Dieser Test prueft alle drei Punkte an einer
NACHGEBAUTEN Boerse - keine Verbindung, kein Konto, kein Geld.

Die wichtigste Pruefung ist Nummer 5: Sendet die Wiederholung DIESELBE
Kennung? Eine Kennung, die sich bei jedem Versuch aendert, ist wertlos -
die Boerse wuerde beide Auftraege annehmen.

AENDERT NICHTS.

    python befund68_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig                      # noqa: E402
from core.events import DecisionIntent, ExecutionResult, Side   # noqa: E402
from execution.engine import ExecutionEngine               # noqa: E402


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("    %-50s ok   %s" % (was, zusatz))
        else:
            self.fehler.append((was, zusatz))
            print("    %-50s FEHL %s" % (was, zusatz))


class FalscheBoerse:
    """Eine Boerse, die nur mitschreibt. Sendet nichts.

    `scheitert_mal` laesst die ersten N Versuche fehlschlagen - so wie eine
    Zeitueberschreitung. Damit wird die Wiederholung ausgeloest, um die es
    in Befund 68 geht.
    """

    def __init__(self, boersen_id="bybit", min_kosten=5.0, scheitert_mal=0):
        self.id = boersen_id
        self.auftraege = []            # jeder Sendeversuch landet hier
        self.abgefragt = []
        self.scheitert_mal = scheitert_mal
        self.markets = {
            "BTC/USDT": {"limits": {"cost": {"min": min_kosten},
                                    "amount": {"min": 0.000001}},
                         "precision": {"amount": 0.000001}}}

    def amount_to_precision(self, symbol, menge):
        return round(float(menge), 6)

    def create_order(self, symbol, art, seite, menge, preis=None, params=None):
        self.auftraege.append({"symbol": symbol, "art": art, "seite": seite,
                               "menge": menge, "params": dict(params or {})})
        if len(self.auftraege) <= self.scheitert_mal:
            raise TimeoutError("Zeitueberschreitung (nachgestellt)")
        return {"id": "ORD-1", "filled": menge, "average": 100.0,
                "cost": menge * 100.0, "status": "closed",
                "fee": {"cost": 0.25}}

    def fetch_order(self, order_id, symbol=None):
        self.abgefragt.append(order_id)
        return {"id": order_id, "status": "closed", "filled": 1.0,
                "average": 100.0, "cost": 100.0}

    # Der Rest, damit die Engine nicht stolpert
    def fetch_balance(self):
        return {"total": {"USDT": 1000.0}}


def eigene_warteschlange(eng):
    """Die Warteschlange auf eine Wegwerfdatei umbiegen.

    [14.09.2026] OHNE DAS SCHREIBT DER TEST IN DEN LAUFENDEN BOT.
    Beim ersten Lauf ist genau das passiert: Der Papierkauf am Ende legte
    einen Warte-Auftrag fuer TEST/USDC an - und der landete in
    data_store/warteauftraege.json, also in der echten Warteschlange des
    laufenden Papierhandels. Beim zweiten Lauf lag er noch dort, ein
    zweiter Auftrag auf dasselbe Symbol wird abgelehnt, und der Test fiel
    durch.

    Der Test hatte also recht - nur nicht ueber den Code, sondern ueber
    sich selbst. Ein Test, der in Produktivdateien schreibt, ist kein
    Test, sondern ein Eingriff.
    """
    import tempfile
    from execution.warteauftraege import Warteschlange
    try:
        eng.warteschlange = Warteschlange(
            pfad=os.path.join(tempfile.mkdtemp(prefix="befund68_"),
                              "warteauftraege.json"),
            einstellungen={"aktiv": False})
    except Exception:
        eng.warteschlange = None
    return eng


def maschine(boerse):
    cfg = AppConfig()
    cfg.trading.mode = "live"          # nur fuer den Pfad, es wird nichts gesendet
    eng = ExecutionEngine(cfg)
    eng._paper_mode = False
    eng.exchange = boerse
    eng.multi_exchange = None
    return eigene_warteschlange(eng)


def auftrag(betrag=100.0, symbol="BTC/USDT"):
    return DecisionIntent(symbol=symbol, side=Side.BUY, amount_usd=betrag,
                          entry_price=100.0, strategy_id="TEST")


def ergebnis(intent, kennung="TI5_abc12345_BTCUSDT_1789000000"):
    r = ExecutionResult(intent_id=intent.id, symbol=intent.symbol,
                        side=intent.side)
    r.client_order_id = kennung
    return r


def main():
    print("=" * 80)
    print("  BEFUND 68 - kann eine Wiederholung noch zweimal kaufen?")
    print("=" * 80)
    p = Pruefung()

    print()
    print("  PUNKT 1 - DIE KENNUNG GEHT MIT, und zwar unter dem")
    print("            richtigen Namen je Boerse")
    print("  " + "-" * 70)

    for boersen_id, feld in (("bybit", "orderLinkId"),
                             ("binance", "newClientOrderId"),
                             ("kraken", "clientOrderId")):
        b = FalscheBoerse(boersen_id)
        eng = maschine(b)
        i = auftrag()
        eng._execute_live(i, ergebnis(i))
        gesendet = b.auftraege[0]["params"] if b.auftraege else {}
        p.sage("%-8s sendet %s" % (boersen_id, feld),
               feld in gesendet and gesendet[feld].startswith("TI5_"),
               "%s" % (list(gesendet.keys()) or "NICHTS"))

    print()
    print("  PUNKT 2 - MINDESTBETRAG")
    print("  " + "-" * 70)

    b = FalscheBoerse("bybit", min_kosten=5.0)
    eng = maschine(b)
    i = auftrag(betrag=3.0)                 # unter 5 USDT
    r = eng._execute_live(i, ergebnis(i))
    p.sage("Order unter dem Mindestbetrag wird abgelehnt",
           r.status == "rejected" and not b.auftraege,
           "und GAR NICHT gesendet (%d Versuche)" % len(b.auftraege))
    p.sage("      ... mit nachvollziehbarem Grund",
           "Mindestbetrag" in (r.rejected_reason or ""),
           (r.rejected_reason or "")[:44])

    b = FalscheBoerse("bybit", min_kosten=5.0)
    eng = maschine(b)
    i = auftrag(betrag=100.0)
    eng._execute_live(i, ergebnis(i))
    p.sage("Order darueber geht raus",
           len(b.auftraege) == 1, "1 Versuch")

    print()
    print("  PUNKT 1b - DER KERN: dieselbe Kennung bei WIEDERHOLUNG")
    print("  " + "-" * 70)

    # Die ersten zwei Versuche scheitern - die Wiederholung greift
    b = FalscheBoerse("bybit", scheitert_mal=2)
    eng = maschine(b)
    i = auftrag()
    eng._execute_live(i, ergebnis(i))
    kennungen = {a["params"].get("orderLinkId") for a in b.auftraege}
    p.sage("Nach zwei Fehlversuchen wurde wiederholt",
           len(b.auftraege) >= 2, "%d Sendeversuche" % len(b.auftraege))
    p.sage("ALLE Versuche tragen DIESELBE Kennung",
           len(kennungen) == 1 and None not in kennungen,
           "%d verschiedene - bei mehr als einer waere der Schutz wertlos"
           % len(kennungen))

    print()
    print("  PUNKT 3 - NACHFRAGEN STATT RATEN")
    print("  " + "-" * 70)

    class OhneFuellung(FalscheBoerse):
        def create_order(self, symbol, art, seite, menge, preis=None, params=None):
            self.auftraege.append({"symbol": symbol, "params": dict(params or {})})
            return {"id": "ORD-9", "status": "open"}        # kein `filled`

    b = OhneFuellung("bybit")
    eng = maschine(b)
    i = auftrag()
    eng._execute_live(i, ergebnis(i))
    p.sage("Unklare Antwort -> die Boerse wird gefragt",
           b.abgefragt == ["ORD-9"], "fetch_order(%s)" % (b.abgefragt or "nie"))

    b = FalscheBoerse("bybit")            # antwortet sauber mit filled
    eng = maschine(b)
    i = auftrag()
    eng._execute_live(i, ergebnis(i))
    p.sage("Klare Antwort -> NICHT nochmal gefragt",
           not b.abgefragt,
           "spart Rate-Limit (%d Abfragen)" % len(b.abgefragt))

    print()
    print("  DER PAPIERPFAD BLEIBT UNBERUEHRT")
    print("  " + "-" * 70)
    cfg = AppConfig()
    cfg.trading.mode = "paper"
    eng = eigene_warteschlange(ExecutionEngine(cfg))
    eng._paper_balances = {"USDC": 1000.0}
    eng._paper_entries = {}
    r = eng.execute(DecisionIntent(symbol="TEST/USDC", side=Side.BUY,
                                   amount_usd=200.0, entry_price=100.0))
    p.sage("Papierkauf laeuft wie bisher",
           r.status == "filled",
           "Status %s - eigene Warteschlange, keine Boerse" % r.status)

    print()
    print("  GEGENTEST")
    print("  " + "-" * 70)
    print("    Der alte Code rief create_market_buy_order(symbol, menge)")
    print("    auf - ohne params. Pruefung 1 bis 3 haetten dann NICHTS")
    print("    im Parameterfeld gefunden und FEHL gemeldet.")
    print("    Und Pruefung 1b faende zwei verschiedene Kennungen, wenn")
    print("    die Kennung im Wiederholungsversuch neu erzeugt wuerde -")
    print("    genau der Fehler, den man beim Bauen leicht macht.")

    print()
    print("-" * 80)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d" % (len(p.fehler), p.ok + len(p.fehler)))
        for was, z in p.fehler:
            print("    %s  %s" % (was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Was das NICHT beweist: dass eine echte Boerse die Kennung")
    print("  auch auswertet. Das zeigt erst die Testnetz-Probe mit")
    print("  Schluesseln - dort wird dieselbe Order zweimal gesendet und")
    print("  nachgesehen, ob nur EINE ankommt.")
    print("-" * 80)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
