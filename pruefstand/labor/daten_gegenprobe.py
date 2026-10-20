# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Stufe 1, Gegenprobe: Binance-Tagesschluesse gegen OKX (zweite Quelle) und Ausreisser-Liste.
Gleiche Tageskerzen (UTC) muessen bis auf kleine Abweichungen gleich sein. Ausreisser > 40 %
werden mit der OKX-Kerze desselben Tages verglichen: gleiche Bewegung dort = echter Markt.
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATEN = Path(__file__).resolve().parent / "daten"
bericht = json.loads((DATEN / "pruefbericht.json").read_text(encoding="utf-8"))
okx = ccxt.okx({"enableRateLimit": True, "timeout": 60000})
okx.load_markets()


def binance(coin):
    with (DATEN / f"{coin}_1d.csv").open(encoding="utf-8") as f:
        return {r["datum"]: float(r["close"]) for r in csv.DictReader(f)}


def okx_tage(coin, seit_ms):
    out, seit = {}, seit_ms
    while True:
        k = okx.fetch_ohlcv(f"{coin}/USDT", "1d", since=seit, limit=300)
        if not k:
            break
        for x in k:
            out[datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat()] = (x[1], x[4])
        neu = k[-1][0] + 86_400_000
        if neu <= seit or len(k) < 100:
            break
        seit = neu
    return out


ergebnis = {}
for c in [x["coin"] for x in bericht["coins"]]:
    b = binance(c)
    o = okx_tage(c, okx.parse8601("2024-10-01T00:00:00Z"))
    gemeinsam = sorted(set(b) & set(o))
    abw = [abs(b[d] / o[d][1] - 1) * 100 for d in gemeinsam]
    abw.sort()
    med = abw[len(abw) // 2] if abw else None
    mx = abw[-1] if abw else None
    ausreisser = next(x for x in bericht["coins"] if x["coin"] == c)["ausreisser_40pct"]
    ergebnis[c] = {"tage_verglichen": len(gemeinsam), "median_abw_pct": med, "max_abw_pct": mx, "ausreisser": ausreisser}
    print(f"{c:5s} Binance vs OKX seit 10/2024: {len(gemeinsam)} Tage, Schluss-Abweichung Median {med:.4f} %, max {mx:.3f} % | "
          f"Ausreisser: {ausreisser}")
(DATEN / "gegenprobe_okx.json").write_text(json.dumps(ergebnis, indent=1), encoding="utf-8")
