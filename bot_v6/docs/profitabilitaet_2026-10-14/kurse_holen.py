# Stundenkerzen BTC/ETH/SOL von Binance (oeffentliche Kursdaten, nur lesen).
import json, os, time, urllib.request
from datetime import datetime, timezone
HIER = os.path.dirname(os.path.abspath(__file__))
START = int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp() * 1000)
ENDE = int(time.time() * 1000)
aus = {}
for sym in ("BTCUSDC", "ETHUSDC", "SOLUSDC"):
    zeilen = []
    t = START
    while t < ENDE:
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&startTime={t}&limit=1000"
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.loads(r.read())
        if not d:
            break
        zeilen += [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in d]
        t = d[-1][0] + 3600_000
    aus[sym] = zeilen
    print(sym, len(zeilen), datetime.fromtimestamp(zeilen[0][0]/1000, timezone.utc), datetime.fromtimestamp(zeilen[-1][0]/1000, timezone.utc), "erster close", zeilen[0][4], "letzter close", zeilen[-1][4])
json.dump(aus, open(os.path.join(HIER, "kurse_1h.json"), "w"))
