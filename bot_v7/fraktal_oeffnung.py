# -*- coding: utf-8 -*-
"""Wie oft geht das Fraktal-Tor ueberhaupt auf?

DIE FRAGE, DIE UEBER ALLES ANDERE ENTSCHEIDET
---------------------------------------------
Ein Tor, das jeden Kauf ablehnt, besteht jede Pruefung auf "haelt den
Fehler vom 14.09. auf" - und ist trotzdem wertlos. Es handelt dann
nicht weniger falsch, sondern gar nicht.

Die Rueckmessung (fraktal_rueckblick.py) zeigt, dass das Tor die vier
Kaeufe vom 14.09. abgelehnt haette. Das ist die halbe Antwort. Die
andere Haelfte: Laesst es irgendwann irgendetwas durch?

Diese Datei geht die letzten Wochen Stunde fuer Stunde durch und
zaehlt, wie oft der Preis in einer Kaufzone stand.

WAS DABEI HERAUSKOMMEN MUSS
---------------------------
    unter  1 %   das Tor ist praktisch zu - der Bot handelt nie
    1 - 15 %     ein enges Tor, wie beabsichtigt
    ueber 40 %   das Tor filtert kaum noch etwas

KAUSALITAET
-----------
Fuer jeden Zeitpunkt sieht das Tor NUR Kerzen, die davor
abgeschlossen waren. Ohne diesen Schnitt saehe es die Zukunft und die
Zahl waere wertlos.

Aufruf:  FRAKTAL_OEFFNUNG.bat  (Doppelklick)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from features.fraktal_tor import (FraktalTor, MIN_ZONEN_SCORE,
                                  MIN_WELLE_PCT, MIN_RUECKSETZER,
                                  WELLEN_JE_ZEITRAHMEN, NAEHE_PCT)

SYMBOLE = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]
ZEITRAHMEN = ("1h", "4h", "1d")

# Wie viele Stunden zurueck geprueft wird. 720 = 30 Tage.
STUNDEN = 720

_ROH = {}
_EX = None


def boerse():
    global _EX
    if _EX is None:
        import ccxt
        _EX = ccxt.binance({"enableRateLimit": True})
    return _EX


def roh(paar, tf, limit):
    schluessel = (paar, tf)
    if schluessel not in _ROH:
        try:
            _ROH[schluessel] = boerse().fetch_ohlcv(paar, tf, limit=limit)
        except Exception as e:
            print(f"    {paar} {tf}: Abruf fehlgeschlagen - {str(e)[:60]}")
            _ROH[schluessel] = None
    return _ROH[schluessel]


class ZeitpunktAgent:
    """Gibt dem Tor die Kerzen, wie sie zu EINEM Zeitpunkt aussahen."""

    def __init__(self, rahmen, bis_ms):
        self.rahmen = rahmen
        self.bis_ms = bis_ms

    def fetch_snapshot(self, symbol, tf="1h", limit=200):
        df = self.rahmen.get(tf)
        if df is None:
            return None
        teil = df[df["ts"] < self.bis_ms].tail(limit)
        if len(teil) < 25:
            return None

        class _S:
            pass
        s = _S()
        s._df = teil.reset_index(drop=True)
        return s


def main():
    print()
    print("=" * 74)
    print("  WIE OFT GEHT DAS FRAKTAL-TOR AUF?")
    print("=" * 74)
    print()
    print(f"  Einstellungen: Mindestscore {MIN_ZONEN_SCORE}, Welle ab "
          f"{MIN_WELLE_PCT} %, Ruecksetzer ab {MIN_RUECKSETZER},")
    print(f"  Naehe {NAEHE_PCT} %, {WELLEN_JE_ZEITRAHMEN} Wellen je Zeitrahmen,"
          f" nur Aufwaertswellen")
    print(f"  Zeitraum: die letzten {STUNDEN} Stunden ({STUNDEN // 24} Tage)")
    print()

    gesamt_offen = 0
    gesamt_geprueft = 0

    for symbol in SYMBOLE:
        paar = symbol.replace("/USDC", "/USDT")
        rahmen = {}
        for tf in ZEITRAHMEN:
            # Genug Vorlauf, damit auch am fruehesten Pruefzeitpunkt
            # noch 200 Kerzen davorliegen.
            limit = {"1h": 1000, "4h": 500, "1d": 400}[tf]
            bars = roh(paar, tf, limit)
            if not bars:
                continue
            rahmen[tf] = pd.DataFrame(
                bars, columns=["ts", "Open", "High", "Low", "Close", "Volume"])

        if len(rahmen) < 2:
            print(f"  {symbol}: zu wenige Zeitrahmen - uebersprungen")
            continue

        stunden_df = rahmen.get("1h")
        if stunden_df is None or stunden_df.empty:
            continue

        pruefpunkte = stunden_df.tail(STUNDEN)
        offen = 0
        geprueft = 0
        golden = 0
        beispiele = []

        for _, kerze in pruefpunkte.iterrows():
            bis_ms = int(kerze["ts"])
            preis = float(kerze["Close"])
            tor = FraktalTor(ZeitpunktAgent(rahmen, bis_ms))
            try:
                u = tor.pruefe(symbol, preis)
            except Exception:
                continue
            geprueft += 1
            if u["erlaubt"]:
                offen += 1
                if u["zone"] and u["zone"].get("golden_pocket"):
                    golden += 1
                if len(beispiele) < 3:
                    beispiele.append(
                        (pd.to_datetime(bis_ms, unit="ms"), preis, u["grund"]))

        gesamt_offen += offen
        gesamt_geprueft += geprueft
        quote = offen / geprueft * 100 if geprueft else 0

        print("-" * 74)
        print(f"  {symbol}")
        print(f"    {geprueft} Stunden geprueft, davon Tor OFFEN in "
              f"{offen}  ->  {quote:.1f} %")
        if offen:
            print(f"    davon im Golden Pocket: {golden} "
                  f"({golden / offen * 100:.0f} % der offenen Stunden)")
            print("    Beispiele:")
            for zeit, p, grund in beispiele:
                print(f"      {zeit:%d.%m. %H:%M}  {p:>10,.2f} $  {grund[:70]}")
        else:
            print("    NIE OFFEN - mit diesen Einstellungen handelt der Bot nicht.")
        print()

    # ----------------------------------------------------------------
    print("=" * 74)
    quote = gesamt_offen / gesamt_geprueft * 100 if gesamt_geprueft else 0
    print(f"  GESAMT: {gesamt_offen} von {gesamt_geprueft} Stunden offen"
          f"  ->  {quote:.1f} %")
    print()
    if quote < 1:
        print("  URTEIL: Das Tor ist praktisch ZU. Der Bot wuerde so gut wie")
        print("          nie kaufen. Das ist kein Filter, das ist ein Riegel.")
    elif quote < 15:
        print("  URTEIL: Enges Tor - so ist es gemeint. Der Bot wartet auf")
        print("          den Ruecksetzer, statt am Hoch zu kaufen.")
    elif quote < 40:
        print("  URTEIL: Offenes Tor. Es filtert, aber nicht scharf.")
    else:
        print("  URTEIL: Das Tor laesst fast alles durch und filtert kaum.")
    print()
    print("  ACHTUNG: Diese Zahl sagt, WIE OFT gekauft werden duerfte -")
    print("  nicht, ob es sich lohnt. Das entscheidet erst der laufende")
    print("  Betrieb oder ein Backtest mit Kontrollgruppe (Stufe 3).")
    print("=" * 74)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
