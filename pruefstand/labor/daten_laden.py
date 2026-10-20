# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Strategie-Labor Stufe 1: Tageskerzen der 12 Bot-Coins laden und pruefen.

Quelle: Binance ueber ccxt, oeffentlich. Paare gegen USDT, weil USDC-Paare bei
Binance erst spaet starten (laengere Historie = mehr Marktphasen). Fuer Kurs-
bewegungen ist USDT ~ USDC (beide 1:1 an den Dollar). Abweichung: Grenze, benannt.
Die heute noch nicht abgeschlossene Tageskerze wird verworfen (kein Blick in die Zukunft).

Pruefungen je Coin: Startdatum, Tage, Luecken (fehlende Kalendertage), Doppelungen,
unplausible Kerzen (High < Low, Open/Close ausserhalb High/Low, Volumen 0) und
Ausreisser (Tagesrendite ueber +/-40 % - gemeldet, nicht geloescht).

Ergebnis: labor/daten/<COIN>_1d.csv und labor/daten/pruefbericht.json
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
DATEN = HIER / "daten"
COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE", "NEAR", "UNI", "ATOM"]
TAG_MS = 86_400_000


def laden(ex, coin: str) -> list[list]:
    sym = f"{coin}/USDT"
    seit = ex.parse8601("2017-01-01T00:00:00Z")
    alle = []
    while True:
        for versuch in range(4):
            try:
                teil = ex.fetch_ohlcv(sym, "1d", since=seit, limit=1000)
                break
            except Exception as e:
                if versuch == 3:
                    raise
                time.sleep(3 * (versuch + 1))
        if not teil:
            break
        alle += teil
        seit = teil[-1][0] + TAG_MS
        if len(teil) < 1000:
            break
    heute = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    return [k for k in alle if k[0] < heute]          # nur abgeschlossene Tage


def pruefen(coin: str, k: list[list]) -> dict:
    ts = [x[0] for x in k]
    doppelt = len(ts) - len(set(ts))
    luecken = [(datetime.fromtimestamp(a / 1000, timezone.utc).date().isoformat(), (b - a) // TAG_MS - 1)
               for a, b in zip(ts, ts[1:]) if b - a != TAG_MS]
    kaputt = [datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat() for x in k
              if x[2] < x[3] or not (x[3] <= x[1] <= x[2]) or not (x[3] <= x[4] <= x[2]) or x[5] <= 0]
    ausreisser = []
    for a, b in zip(k, k[1:]):
        r = b[4] / a[4] - 1
        if abs(r) > 0.40:
            ausreisser.append((datetime.fromtimestamp(b[0] / 1000, timezone.utc).date().isoformat(), round(r * 100, 1)))
    return {"coin": coin, "start": datetime.fromtimestamp(ts[0] / 1000, timezone.utc).date().isoformat(),
            "ende": datetime.fromtimestamp(ts[-1] / 1000, timezone.utc).date().isoformat(), "tage": len(k),
            "doppelt": doppelt, "luecken": luecken, "unplausibel": kaputt, "ausreisser_40pct": ausreisser}


if __name__ == "__main__":
    DATEN.mkdir(parents=True, exist_ok=True)
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 120000})
    ex.load_markets()
    bericht = {"quelle": "Binance via ccxt, Paare gegen USDT, 1d, nur abgeschlossene Tage",
               "geladen_utc": datetime.now(timezone.utc).isoformat(), "coins": []}
    for c in COINS:
        k = laden(ex, c)
        with (DATEN / f"{c}_1d.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts_ms", "datum", "open", "high", "low", "close", "volume"])
            for x in k:
                w.writerow([x[0], datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat(), *x[1:6]])
        p = pruefen(c, k)
        bericht["coins"].append(p)
        print(f"{c:5s} {p['start']} .. {p['ende']} | {p['tage']:5d} Tage | doppelt {p['doppelt']} | "
              f"Luecken {len(p['luecken'])} | unplausibel {len(p['unplausibel'])} | Ausreisser >40 % {len(p['ausreisser_40pct'])}",
              flush=True)
    (DATEN / "pruefbericht.json").write_text(json.dumps(bericht, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gespeichert:", DATEN)
