# -*- coding: utf-8 -*-
"""
A4: Stundenkerzen BTC/USDC, ETH/USDC, SOL/USDC von Binance (oeffentlich, kein Schluessel).
Zeitraum ab 2026-06-15 00:00 UTC bis jetzt. Nur ABGESCHLOSSENE Kerzen werden gespeichert
(Kerzen-Ende <= Abrufzeit), damit kein Blick in die Zukunft entsteht.
Ziel: pruefstand/daten/binance_1h_<MUENZE>_USDC.csv  (ts_ms, open_utc, open, high, low, close, volume)
"""
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ZIEL = Path(r"C:\Users\<BENUTZER>\Desktop\pruefstand\daten")
ZIEL.mkdir(parents=True, exist_ok=True)
START = int(datetime(2026, 6, 15, tzinfo=timezone.utc).timestamp() * 1000)
H = 3600 * 1000

ex = ccxt.binance({"enableRateLimit": True, "timeout": 120000})
t0 = time.time()
ex.load_markets()
print(f"load_markets {time.time() - t0:.0f} s")
jetzt = ex.milliseconds()
for sym in ("BTC/USDC", "ETH/USDC", "SOL/USDC"):
    alle, since = {}, START
    while since < jetzt:
        teil = ex.fetch_ohlcv(sym, "1h", since=since, limit=1000)
        if not teil:
            break
        for k in teil:
            alle[k[0]] = k
        neu = teil[-1][0] + H
        if neu <= since:
            break
        since = neu
    zeilen = [alle[t] for t in sorted(alle) if t + H <= jetzt]  # nur abgeschlossene Kerzen
    # Luecken pruefen
    luecken = [(zeilen[i - 1][0], zeilen[i][0]) for i in range(1, len(zeilen)) if zeilen[i][0] - zeilen[i - 1][0] != H]
    datei = ZIEL / f"binance_1h_{sym.replace('/', '_')}.csv"
    with datei.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "open_utc", "open", "high", "low", "close", "volume"])
        for k in zeilen:
            w.writerow([k[0], datetime.fromtimestamp(k[0] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        k[1], k[2], k[3], k[4], k[5]])
    print(f"{sym}: {len(zeilen)} Kerzen {datetime.fromtimestamp(zeilen[0][0]/1000, timezone.utc)} .. "
          f"{datetime.fromtimestamp(zeilen[-1][0]/1000, timezone.utc)} | Luecken: {len(luecken)} {luecken[:5]} -> {datei.name}")
print("Abrufzeit UTC", datetime.fromtimestamp(jetzt / 1000, timezone.utc).isoformat())
