# -*- coding: utf-8 -*-
"""Haette das Fraktal-Tor die Kaeufe vom 14.09.2026 verhindert?

DIE FRAGE
---------
Am 14.09. kaufte der Live-Bot viermal BTC nach Trendfolge und lag damit
am Hoch. Das Tor (features/fraktal_tor.py) soll genau das verhindern.
Ob es das TUT, ist eine Messung - keine Annahme.

Diese Datei stellt dem Tor dieselbe Lage noch einmal, mit den echten
Kerzen von damals, und fragt: erlaubt oder abgelehnt?

WAS DIESE MESSUNG NICHT BEANTWORTET
-----------------------------------
Sie sagt NICHT, ob das Tor Geld verdient. Vier Faelle sind vier Faelle.
Sie beantwortet nur die eine Frage, um die es hier geht: Greift die
Regel ueberhaupt an der Stelle, an der sie greifen soll?

Die Trivial-Latte gehoert trotzdem dazu (CLAUDE.md Abschnitt 7.2):
"gar nicht kaufen" ist die Alternative, gegen die sich alles messen
muss. Deshalb wird am Ende ausgewiesen, wie sich der Kurs nach den
Kaufzeitpunkten entwickelt hat.

KAUSALITAET
-----------
Das Tor bekommt AUSSCHLIESSLICH Kerzen, die zum Kaufzeitpunkt schon
abgeschlossen waren. Ohne diesen Schnitt saehe es Kerzen aus der
Zukunft und die Messung waere wertlos - der haeufigste Fehler in
Rueckrechnungen ueberhaupt.

Aufruf:  FRAKTAL_RUECKBLICK.bat  (Doppelklick)
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from features.fraktal_tor import FraktalTor, ZEITRAHMEN, KERZEN


# Die vier Kaeufe vom 14.09.2026, aus data_store/system.log und
# data_store/order_history.json. Zeiten sind UTC, wie sie im Log stehen.
KAEUFE = [
    ("2026-09-14T19:22:29Z", "BTC/USDC", 9, "MACD + EMA-Trend + ADX 35 + VWAP + Orderbook"),
    ("2026-09-14T19:24:34Z", "BTC/USDC", 8, "MACD + EMA-Trend + ADX 35 + VWAP"),
    ("2026-09-14T19:24:49Z", "BTC/USDC", 8, "MACD + EMA-Trend + ADX 35 + VWAP"),
    ("2026-09-14T19:24:27Z", "SOL/USDC", 7, "MACD + EMA-Trend + ADX 29 + VWAP"),
]


# Einmal geholte Rohkerzen je (Symbol, Zeitrahmen).
#
# Der erste Entwurf holte bei JEDEM der vier Kaeufe alle drei
# Zeitrahmen neu - rund zwanzig Abrufe, und ein Binance-Abruf dauert
# hier gemessen 8,6 Sekunden. Der Lauf brauchte damit ueber fuenf
# Minuten, und ein Werkzeug, das fuenf Minuten braucht, startet
# niemand zweimal.
#
# Die Rohkerzen sind fuer alle vier Kaeufe dieselben; nur der
# Kausalitaetsschnitt unterscheidet sich. Also einmal holen, je Kauf
# schneiden.
_ROH = {}
_EX = None


def _boerse():
    global _EX
    if _EX is None:
        import ccxt
        _EX = ccxt.binance({"enableRateLimit": True})
    return _EX


def hole_kerzen(symbol, tf, bis_ms, anzahl=KERZEN):
    """Echte Kerzen von Binance, NUR bis zum Zeitpunkt bis_ms.

    Binance ist die Kursquelle des Projekts (gehandelt wird bei Bybit
    EU). Oeffentlicher Abruf, keine Zugangsdaten noetig.
    """
    paar = symbol.replace("/USDC", "/USDT")     # Binance fuehrt USDT-Paare
    schluessel = (paar, tf)

    if schluessel not in _ROH:
        try:
            _ROH[schluessel] = _boerse().fetch_ohlcv(paar, tf,
                                                     limit=anzahl * 2)
        except Exception as e:
            print(f"      {tf}: Abruf fehlgeschlagen - {str(e)[:70]}")
            _ROH[schluessel] = None

    bars = _ROH[schluessel]
    if not bars:
        return None

    df = pd.DataFrame(bars, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    # KAUSALITAETSSCHNITT: nur Kerzen, die VOR dem Kaufzeitpunkt
    # abgeschlossen waren. Er passiert NACH dem Zwischenspeicher -
    # sonst waere der Speicher fuer den naechsten Kaufzeitpunkt falsch.
    df = df[df["ts"] < bis_ms]
    if len(df) < 25:
        return None
    return df.tail(anzahl).reset_index(drop=True)


class RueckblickAgent:
    """Gibt dem Tor die historischen Kerzen statt der aktuellen."""

    def __init__(self, symbol, bis_ms):
        self.symbol = symbol
        self.bis_ms = bis_ms
        self._speicher = {}

    def fetch_snapshot(self, symbol, tf="1h", limit=200):
        if tf not in self._speicher:
            self._speicher[tf] = hole_kerzen(symbol, tf, self.bis_ms, limit)
        df = self._speicher[tf]
        if df is None:
            return None

        class _S:
            pass
        s = _S()
        s._df = df
        return s


def main():
    print()
    print("=" * 74)
    print("  HAETTE DAS FRAKTAL-TOR DIE KAEUFE VOM 14.09. VERHINDERT?")
    print("=" * 74)
    print()
    print("  Kausalitaet: Das Tor sieht NUR Kerzen, die zum Kaufzeitpunkt")
    print("  bereits abgeschlossen waren.")
    print()

    abgelehnt = 0
    erlaubt = 0
    ungeprueft = 0
    zeilen = []

    for zeitpunkt, symbol, score, grund in KAEUFE:
        dt = datetime.strptime(zeitpunkt, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        bis_ms = int(dt.timestamp() * 1000)

        print("-" * 74)
        print(f"  {dt.strftime('%d.%m.%Y %H:%M:%S')} UTC   {symbol}"
              f"   Score {score}/10")
        print(f"  Der Bot kaufte wegen: {grund}")

        agent = RueckblickAgent(symbol, bis_ms)
        tor = FraktalTor(agent)

        # Der Preis zum Kaufzeitpunkt: Schluss der letzten Kerze davor.
        df1h = hole_kerzen(symbol, "1h", bis_ms)
        if df1h is None or df1h.empty:
            print("  KEINE KERZEN - nicht auswertbar")
            ungeprueft += 1
            continue
        preis = float(df1h["Close"].iloc[-1])

        urteil = tor.pruefe(symbol, preis)
        marke = "ERLAUBT " if urteil["erlaubt"] else "ABGELEHNT"
        if urteil["erlaubt"]:
            erlaubt += 1
        else:
            abgelehnt += 1

        print(f"  Preis damals: {preis:,.2f} $")
        print(f"  TOR-URTEIL:   {marke}")
        print(f"                {urteil['grund']}")

        zeilen.append((dt, symbol, score, preis, urteil["erlaubt"]))

    # ----------------------------------------------------------------
    print()
    print("=" * 74)
    print("  ERGEBNIS")
    print("=" * 74)
    gesamt = abgelehnt + erlaubt
    print(f"\n  Von {gesamt} auswertbaren Kaeufen haette das Tor")
    print(f"    {abgelehnt} abgelehnt")
    print(f"    {erlaubt} durchgelassen")
    if ungeprueft:
        print(f"    ({ungeprueft} nicht auswertbar)")

    # ---------------- Trivial-Latte ----------------
    print()
    print("  TRIVIAL-LATTE: was waere ohne jeden Kauf passiert?")
    print("  " + "-" * 70)
    print("  (CLAUDE.md 7.2 - 'gar nicht handeln' schlaegt viele Strategien)")
    print()

    nachlauf_speicher = {}
    for dt, symbol, score, preis, war_erlaubt in zeilen:
        bis_ms = int(dt.timestamp() * 1000)
        paar = symbol.replace("/USDC", "/USDT")
        if paar not in nachlauf_speicher:
            try:
                nachlauf_speicher[paar] = _boerse().fetch_ohlcv(
                    paar, "1h", since=bis_ms, limit=48)
            except Exception as e:
                print(f"    {symbol}: Nachlauf nicht abrufbar ({str(e)[:50]})")
                nachlauf_speicher[paar] = None
        nach = nachlauf_speicher[paar]
        if not nach:
            continue
        df = pd.DataFrame(nach, columns=["ts", "Open", "High", "Low",
                                         "Close", "Volume"])
        for stunden in (1, 4, 24):
            teil = df[df["ts"] <= bis_ms + stunden * 3600 * 1000]
            if teil.empty:
                continue
            spaeter = float(teil["Close"].iloc[-1])
            pct = (spaeter - preis) / preis * 100.0
            # Kosten je Runde, K-BASIS aus CLAUDE.md Abschnitt 8
            netto = pct - 0.505
            print(f"    {symbol} {dt.strftime('%H:%M')}  nach {stunden:>2} h: "
                  f"{pct:+6.3f} %   nach Kosten {netto:+6.3f} %"
                  f"   {'(Tor haette erlaubt)' if war_erlaubt else '(Tor haette abgelehnt)'}")
        print()

    print("=" * 74)
    print("  Diese Messung beantwortet EINE Frage: greift die Regel dort,")
    print("  wo sie greifen soll. Sie beweist keinen Vorteil - dafuer sind")
    print("  vier Faelle viel zu wenig.")
    print("=" * 74)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
