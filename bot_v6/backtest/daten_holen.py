# -*- coding: utf-8 -*-
"""
backtest/daten_holen.py - Historische Daten fuer den Backtest  [E11 29.07.2026]
==============================================================================
Holt einmalig, was der Backtest braucht, und legt es unter
data_store/backtest/ ab. Danach laeuft alles offline.

  1. 15-Minuten-Kerzen je Coin von Binance (oeffentlich, kein Schluessel noetig)
  2. Fear-&-Greed-Historie von alternative.me (taeglich, seit 2018)

WARUM 15 MINUTEN UND NICHT 1 STUNDE
-----------------------------------
Im Bestand lagen nur 1h-Kerzen (892 Stueck = 37 Tage). Fuer eine
Ausstiegsregel ist das aus zwei Gruenden untauglich:

  * Zu kurz. 37 Tage sind eine Marktphase, nicht ein Querschnitt.
  * Zu grob. Der Bot prueft seine Stops alle 30 Sekunden. Ob ein
    Trailing-Stop ausloest, entscheidet der Weg INNERHALB der Kerze.
    Bei 1h-Kerzen ist dieser Weg unbekannt - man wuerde die Regel
    gegen eine Aufloesung testen, in der sie gar nicht arbeitet.

15 Minuten ist der Kompromiss: fein genug, um den Kursverlauf brauchbar
abzubilden, grob genug, um ein Jahr Historie in vertretbarer Zeit zu laden.
Selbst damit bleibt eine Restunschaerfe - siehe die pessimistische
Reihenfolge-Annahme in backtest/ausstieg_backtest.py.

    python backtest/daten_holen.py            # 1 Jahr, alle Coins
    python backtest/daten_holen.py --tage 180
"""
import os
import sys
import csv
import json
import time
import argparse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(ROOT, "data_store", "backtest")

COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "AVAX/USDC",
         "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC", "UNI/USDC",
         "ATOM/USDC"]


def _kerzen(ex, symbol, timeframe, seit_ms, bis_ms):
    """Laedt Kerzen in 1000er-Bloecken bis bis_ms erreicht ist."""
    alle = []
    cursor = seit_ms
    schritt = {"15m": 900_000, "1h": 3_600_000, "5m": 300_000}[timeframe]
    while cursor < bis_ms:
        try:
            teil = ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
        except Exception as e:
            print(f"    Fehler bei {symbol} @ {cursor}: {str(e)[:60]} - warte 5s")
            time.sleep(5)
            continue
        if not teil:
            break
        alle.extend(teil)
        neu = teil[-1][0] + schritt
        if neu <= cursor:
            break
        cursor = neu
        sys.stdout.write(f"\r    {symbol} {timeframe}: {len(alle)} Kerzen")
        sys.stdout.flush()
    # Duplikate raus, nach Zeit sortieren
    gesehen, sauber = set(), []
    for k in sorted(alle, key=lambda x: x[0]):
        if k[0] not in gesehen and k[0] <= bis_ms:
            gesehen.add(k[0])
            sauber.append(k)
    return sauber


def hole_kerzen(tage, timeframe="15m", ende_vor_tagen=0, marke=""):
    """ende_vor_tagen: Zeitfenster um N Tage nach hinten verschieben.
    marke: Namenszusatz, damit mehrere Zeitraeume nebeneinander liegen."""
    import ccxt
    os.makedirs(ZIEL, exist_ok=True)
    ex = ccxt.binance({"enableRateLimit": True})
    bis = ex.milliseconds() - ende_vor_tagen * 86_400_000
    seit = bis - tage * 86_400_000

    for symbol in COINS:
        datei = os.path.join(ZIEL, symbol.replace("/", "") + f"_{timeframe}{marke}.csv")
        if os.path.exists(datei):
            with open(datei, encoding="utf-8") as f:
                vorhanden = sum(1 for _ in f) - 1
            print(f"  {symbol:12s} bereits vorhanden ({vorhanden} Kerzen) - uebersprungen")
            continue
        print(f"  {symbol:12s} laedt ...")
        try:
            k = _kerzen(ex, symbol, timeframe, seit, bis)
        except Exception as e:
            print(f"\r  {symbol:12s} FEHLGESCHLAGEN: {str(e)[:60]}")
            continue
        if not k:
            print(f"\r  {symbol:12s} keine Daten")
            continue
        with open(datei, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "open", "high", "low", "close", "volume"])
            w.writerows(k)
        von = time.strftime("%Y-%m-%d", time.gmtime(k[0][0] / 1000))
        bis_s = time.strftime("%Y-%m-%d", time.gmtime(k[-1][0] / 1000))
        print(f"\r  {symbol:12s} {len(k):6d} Kerzen  {von} .. {bis_s}          ")


def hole_fear_greed():
    """Taegliche F&G-Historie. Vorgabe des Bots: unter 30 wird gekauft."""
    os.makedirs(ZIEL, exist_ok=True)
    datei = os.path.join(ZIEL, "fear_greed.json")
    try:
        roh = urllib.request.urlopen(
            "https://api.alternative.me/fng/?limit=0&format=json", timeout=30).read()
        daten = json.loads(roh)["data"]
    except Exception as e:
        print(f"  Fear&Greed FEHLGESCHLAGEN: {str(e)[:60]}")
        return
    # {Datum (UTC) -> Wert}
    tabelle = {}
    for e in daten:
        try:
            tag = time.strftime("%Y-%m-%d", time.gmtime(int(e["timestamp"])))
            tabelle[tag] = int(e["value"])
        except Exception:
            continue
    with open(datei, "w", encoding="utf-8") as f:
        json.dump(tabelle, f, indent=1)
    tage = sorted(tabelle)
    print(f"  Fear&Greed   {len(tabelle):6d} Tage    {tage[0]} .. {tage[-1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tage", type=int, default=365)
    ap.add_argument("--timeframe", default="15m", choices=["5m", "15m", "1h"])
    ap.add_argument("--ende-vor-tagen", type=int, default=0,
                    help="Fenster um N Tage nach hinten verschieben (fuer aeltere Marktphasen)")
    ap.add_argument("--marke", default="", help="Namenszusatz, z.B. _bulle")
    a = ap.parse_args()
    print(f"Historische Daten -> {ZIEL}")
    print(f"Zeitraum: {a.tage} Tage, Aufloesung {a.timeframe}"
          f"{f', endet vor {a.ende_vor_tagen} Tagen' if a.ende_vor_tagen else ''}\n")
    hole_fear_greed()
    hole_kerzen(a.tage, a.timeframe, a.ende_vor_tagen, a.marke)
    print("\nFertig.")


if __name__ == "__main__":
    main()
