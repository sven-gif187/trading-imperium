# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 ausstiegs-pruefer · Kerzen laden (nur oeffentliche Kursdaten, nur lesen).

Binance BTC/USDC, ETH/USDC, SOL/USDC ueber ccxt:
  - 1h-Kerzen ab 2026-06-01 (ATR-Vorlauf, Nachlauf 7 Tage)
  - 1m-Kerzen ab 2026-08-11 (Nachspielung der Ausstiege; der Bot prueft alle 30 s)
Ablage: pruefstand/daten/binance_<tf>_<COIN>_USDC.csv  (ts_ms,open,high,low,close,volume)
Vorhandene Dateien werden NICHT ueberschrieben, nur fehlende Zeit wird angehaengt.
Nur abgeschlossene Kerzen werden gespeichert (kein Blick in die Zukunft).
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timezone

import ccxt

DATEN = r"C:\Users\<BENUTZER>\Desktop\pruefstand\daten"
SYMBOLE = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]
PLAN = {"1h": datetime(2026, 6, 1, tzinfo=timezone.utc), "1m": datetime(2026, 8, 11, tzinfo=timezone.utc)}
TF_MS = {"1h": 3_600_000, "1m": 60_000}


def pfad(tf: str, sym: str) -> str:
    return os.path.join(DATEN, f"binance_{tf}_{sym.replace('/', '_')}.csv")


def letzte_zeit(p: str) -> int | None:
    if not os.path.exists(p):
        return None
    last = None
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0].isdigit():
                last = int(row[0])
    return last


def main() -> None:
    os.makedirs(DATEN, exist_ok=True)
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 120000})
    t0 = time.time()
    ex.load_markets()
    print(f"load_markets {time.time() - t0:.0f} s", flush=True)
    jetzt = ex.milliseconds()
    for tf in ("1h", "1m"):
        for sym in SYMBOLE:
            p = pfad(tf, sym)
            last = letzte_zeit(p)
            since = int(PLAN[tf].timestamp() * 1000) if last is None else last + TF_MS[tf]
            neu = []
            while since < jetzt - TF_MS[tf]:
                d = ex.fetch_ohlcv(sym, tf, since=since, limit=1000)
                if not d:
                    break
                for k in d:
                    if k[0] + TF_MS[tf] <= jetzt:          # nur abgeschlossene Kerzen
                        neu.append(k)
                nxt = d[-1][0] + TF_MS[tf]
                if nxt <= since:
                    break
                since = nxt
            schreib_kopf = not os.path.exists(p)
            tmp = p + ".tmp"
            # Anhaengen ueber Kopie, damit eine halbe Datei nie als fertig gilt
            alt = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                if schreib_kopf:
                    f.write("ts_ms,open,high,low,close,volume\n")
                else:
                    f.write(alt)
                w = csv.writer(f)
                for k in neu:
                    w.writerow([int(k[0]), k[1], k[2], k[3], k[4], k[5]])
            os.replace(tmp, p)
            if neu:
                a = datetime.fromtimestamp(neu[0][0] / 1000, timezone.utc).isoformat()
                b = datetime.fromtimestamp(neu[-1][0] / 1000, timezone.utc).isoformat()
                print(f"{tf} {sym}: +{len(neu)} Kerzen {a} .. {b}", flush=True)
            else:
                print(f"{tf} {sym}: nichts Neues", flush=True)
    print("fertig", flush=True)


if __name__ == "__main__":
    sys.exit(main())
