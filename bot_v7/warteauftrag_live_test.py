# -*- coding: utf-8 -*-
"""Gegentest fuer execution/warteauftraege_live.py - in beide Richtungen.

CLAUDE.md, Abschnitt 0: "Pruefwerkzeuge: Gegentest in BEIDE Richtungen -
meldet es nichts Falsches, UND findet es den echten Fall?"

Die Faelle hier sind nicht ausgedacht, sondern die drei Gefahren aus dem
Kopf von warteauftraege_live.py, dazu die Grenzfaelle, an denen dieses
Projekt schon einmal Geld verloren haette:

    Teilausfuehrung      15.09.2026: 0,0042 gebucht, 0,0041895 vorhanden -
                         der Stop-Loss konnte nicht verkaufen.
    Wettrennen           Befund 68: Abfrage in derselben Sekunde wie die
                         Ausfuehrung, als "fehlgeschlagen" gebucht.
    Boerse stumm         "unklar" darf NIE zu "weg" werden.

Aufruf:  python warteauftrag_live_test.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution import warteauftraege_live as wl


class Boerse:
    """Eine nachgebaute Boerse, die sich genau so verhaelt wie bestellt."""

    def __init__(self, id_="bybit", antworten=None, wirft_beim_stellen=None,
                 wirft_beim_stornieren=None, order_id="ORD-1"):
        self.id = id_
        self._antworten = list(antworten or [])
        self._wirft_stellen = wirft_beim_stellen
        self._wirft_storno = wirft_beim_stornieren
        self._order_id = order_id
        self.gestellt = []
        self.storniert = []
        self.abfragen = 0

    def create_order(self, symbol, typ, seite, menge, preis=None, params=None):
        if self._wirft_stellen:
            raise self._wirft_stellen
        self.gestellt.append({"symbol": symbol, "typ": typ, "seite": seite,
                              "menge": menge, "preis": preis,
                              "params": dict(params or {})})
        return {"id": self._order_id} if self._order_id else {}

    def fetch_order(self, oid, symbol):
        self.abfragen += 1
        if not self._antworten:
            raise RuntimeError("Boerse antwortet nicht")
        a = self._antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    def cancel_order(self, oid, symbol):
        if self._wirft_storno:
            raise self._wirft_storno
        self.storniert.append(oid)
        return {"id": oid, "status": "canceled"}


bestanden = 0
gefallen = 0


def pruefe(name, ist, soll):
    global bestanden, gefallen
    ok = ist == soll
    if ok:
        bestanden += 1
    else:
        gefallen += 1
    marke = "ok  " if ok else "FALSCH"
    print(f"  [{marke}] {name}")
    if not ok:
        print(f"          erwartet: {soll!r}")
        print(f"          bekommen: {ist!r}")


print("\n" + "=" * 72)
print("  GEGENTEST: Warte-Auftraege im Echtbetrieb")
print("=" * 72)

# ------------------------------------------------- 1. Stellen: der Normalfall
print("\n  1. Einen Auftrag stellen")
b = Boerse()
oid, fehler = wl.stellen(b, "ETH/USDC", 0.004, 2400.0, "TI-123")
pruefe("Order-ID kommt zurueck", oid, "ORD-1")
pruefe("kein Fehler", fehler, "")
pruefe("Ordertyp ist LIMIT, nicht market", b.gestellt[0]["typ"], "limit")
pruefe("Limitpreis wird mitgegeben", b.gestellt[0]["preis"], 2400.0)
pruefe("Bybit bekommt orderLinkId",
       b.gestellt[0]["params"].get("orderLinkId"), "TI-123")

b2 = Boerse(id_="binance")
wl.stellen(b2, "ETH/USDC", 0.004, 2400.0, "TI-123")
pruefe("Binance bekommt newClientOrderId",
       b2.gestellt[0]["params"].get("newClientOrderId"), "TI-123")

# --------------------------------------------- 2. Stellen: die Gegenrichtung
print("\n  2. Stellen schlaegt fehl - wird das gemeldet?")
b = Boerse(wirft_beim_stellen=RuntimeError("Insufficient balance"))
oid, fehler = wl.stellen(b, "ETH/USDC", 0.004, 2400.0)
pruefe("keine Order-ID bei Fehler", oid, "")
pruefe("Fehler wird durchgereicht", "Insufficient balance" in fehler, True)

b = Boerse(order_id="")
oid, fehler = wl.stellen(b, "ETH/USDC", 0.004, 2400.0)
pruefe("Antwort OHNE ID gilt als Fehler", oid, "")
pruefe("und sagt warum", "keine Order-ID" in fehler, True)

# -------------------------------------------------------- 3. Status erkennen
print("\n  3. Status: jeder Zustand muss richtig erkannt werden")
faelle = [
    ("offen", {"status": "open", "filled": 0.0, "remaining": 0.004}, "offen"),
    ("ganz gefuellt",
     {"status": "closed", "filled": 0.004, "remaining": 0.0,
      "average": 2399.5}, "gefuellt"),
    ("storniert, nichts gefuellt",
     {"status": "canceled", "filled": 0.0, "remaining": 0.004}, "weg"),
    ("TEILWEISE gefuellt, dann storniert",
     {"status": "canceled", "filled": 0.0018, "remaining": 0.0022,
      "average": 2399.0}, "teilweise"),
    ("teilweise, noch offen",
     {"status": "open", "filled": 0.0018, "remaining": 0.0022}, "teilweise"),
]
for name, antwort, soll in faelle:
    b = Boerse(antworten=[antwort])
    pruefe(name, wl.status(b, "ORD-1", "ETH/USDC")["zustand"], soll)

# Die Menge muss stimmen - hier lag am 15.09. das Kapitalrisiko.
b = Boerse(antworten=[{"status": "canceled", "filled": 0.0018,
                       "remaining": 0.0022, "average": 2399.0}])
s = wl.status(b, "ORD-1", "ETH/USDC")
pruefe("Teilmenge wird EXAKT gemeldet, nicht aufgerundet",
       s["menge"], 0.0018)

# --------------------------------------- 4. Boerse stumm: "unklar", nie "weg"
print("\n  4. Die Boerse antwortet nicht - der gefaehrlichste Fall")
b = Boerse(antworten=[])          # jede Abfrage wirft
s = wl.status(b, "ORD-1", "ETH/USDC")
pruefe("Zustand ist 'unklar'", s["zustand"], "unklar")
pruefe("und NICHT 'weg'", s["zustand"] == "weg", False)
pruefe("es wurde dreimal nachgefragt, nicht einmal", b.abfragen, 3)

# Einmal Fehler, dann Antwort: der Wiederholversuch muss greifen.
b = Boerse(antworten=[RuntimeError("timeout"),
                      {"status": "closed", "filled": 0.004,
                       "remaining": 0.0, "average": 2399.5}])
pruefe("nach einem Fehlversuch klappt es doch",
       wl.status(b, "ORD-1", "ETH/USDC")["zustand"], "gefuellt")

# ------------------------------------------------ 5. Das Wettrennen beim Storno
print("\n  5. Ruecknahme - das Wettrennen mit der Ausfuehrung")
b = Boerse(antworten=[{"status": "canceled", "filled": 0.0,
                       "remaining": 0.004}])
pruefe("normale Ruecknahme", wl.zuruecknehmen(b, "ORD-1", "ETH/USDC")["zustand"],
       "weg")

# Der Kern: cancel wirft, weil schon gefuellt. Der Status entscheidet.
b = Boerse(wirft_beim_stornieren=RuntimeError("order not found"),
           antworten=[{"status": "closed", "filled": 0.004,
                       "remaining": 0.0, "average": 2399.5}])
e = wl.zuruecknehmen(b, "ORD-1", "ETH/USDC")
pruefe("Storno scheitert, weil inzwischen GEFUELLT -> als gefuellt erkannt",
       e["zustand"], "gefuellt")
pruefe("und die Menge wird gemeldet, nicht verschluckt", e["menge"], 0.004)

b = Boerse(wirft_beim_stornieren=RuntimeError("already filled"),
           antworten=[{"status": "canceled", "filled": 0.0018,
                       "remaining": 0.0022, "average": 2399.0}])
e = wl.zuruecknehmen(b, "ORD-1", "ETH/USDC")
pruefe("Storno trifft TEILWEISE bedienten Auftrag", e["zustand"], "teilweise")
pruefe("Teilmenge geht nicht verloren", e["menge"], 0.0018)

# Storno klappt, aber danach ist die Boerse stumm -> nicht als erledigt buchen.
b = Boerse(antworten=[])
pruefe("Storno ok, aber Status unklar -> bleibt 'unklar'",
       wl.zuruecknehmen(b, "ORD-1", "ETH/USDC")["zustand"], "unklar")

# ------------------------------------------------------- 6. Gebundenes Geld
print("\n  6. Wieviel Geld haelt die Boerse fest?")
pruefe("nichts offen", wl.offene_summe_usd([]), 0.0)
pruefe("zwei Auftraege",
       wl.offene_summe_usd([{"betrag_usd": 10.0}, {"betrag_usd": 7.5}]), 17.5)
pruefe("kaputter Eintrag wirft nicht",
       wl.offene_summe_usd([{"betrag_usd": None}, {"betrag_usd": "x"},
                            {"betrag_usd": 5.0}]), 5.0)

# --------------------------------------------------- 7. Kein Verkauf per Limit
print("\n  7. Absicht: es gibt KEINEN Verkaufsweg")
pruefe("stellen() kennt nur 'buy'",
       "def verkaufen" in open(
           os.path.join("execution", "warteauftraege_live.py"),
           encoding="utf-8").read(), False)
b = Boerse()
wl.stellen(b, "ETH/USDC", 0.004, 2400.0)
pruefe("und stellt immer die Kaufseite", b.gestellt[0]["seite"], "buy")

print("\n" + "-" * 72)
print(f"  {bestanden} bestanden, {gefallen} gefallen")
if gefallen:
    print("\n  NICHT EINSETZEN, solange etwas fehlschlaegt.")
print("=" * 72 + "\n")
sys.exit(1 if gefallen else 0)
