# -*- coding: utf-8 -*-
"""A4 Gegenprobe Kursdaten: (1) Kaufkurse des Bots liegen in der Spanne der Binance-Stundenkerze?
(2) Binance-Schlusskurse gegen telemetrie.db markt_historie (v6, nur lesend, gezielt)."""
import sqlite3, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from runden_lib import lade, runden
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
D = Path(r"C:\Users\<BENUTZER>\Desktop\pruefstand\daten")
k = {c: pd.read_csv(D / f"binance_1h_{c}_USDC.csv") for c in ("BTC", "ETH", "SOL")}
for c in k:
    k[c]["t"] = pd.to_datetime(k[c]["open_utc"], utc=True)
    k[c] = k[c].set_index("t")

rows = lade(V6)
rd = runden(rows, "2026-08-13T13:21:19", "2026-10-14T09:18:25")
kt = {r["kauf_t"] for r in rd}
buys = [r for r in rows if str(r.get("type", "")).upper() == "BUY" and r["time"] in kt]
aus = []
for b in buys:
    c = b["coin"].split("/")[0]
    t = pd.Timestamp(b["time"]).floor("h")
    kz = k[c].loc[t]
    p = float(b.get("entry_geplant") or b["price"])
    aus.append({"coin": c, "in_spanne": kz["low"] * 0.999 <= p <= kz["high"] * 1.001,
                "abw_close_pct": (p / kz["close"] - 1) * 100, "slip": float(b.get("slippage_pct") or 0)})
a = pd.DataFrame(aus)
print("Kaufkurs (entry_geplant) in Kerzenspanne +-0,1 %:", a.in_spanne.sum(), "von", len(a))
print("Abweichung zum Kerzen-Schluss: Median %.3f %%, |Abw| Median %.3f %%" % (a.abw_close_pct.median(), a.abw_close_pct.abs().median()))
print("Bot-Schlupf je Kauf (slippage_pct): Mittel %.4f %%, Median %.4f %%" % (a.slip.mean(), a.slip.median()))

con = sqlite3.connect(f"file:{V6 / 'data_store' / 'telemetrie.db'}?mode=ro", uri=True)
tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("Tabellen:", tabs)
cols = [r[1] for r in con.execute("pragma table_info(markt_historie)")]
print("markt_historie Spalten:", cols)
print(con.execute("select * from markt_historie order by rowid desc limit 2").fetchall())
