# -*- coding: utf-8 -*-
"""
A4 Diagnose der drei Abweichungen aus a4_gegenprobe.py (nur lesen):
 D1 Preisversatz markt_historie gegen Binance-Stundenkerzen (gleiche Zeitpunkte).
 D2 Verkauf: amount gegen qty*Kurs, Verkaufs-qty gegen Kauf-qty.
 D3 entry_strategie (Verkauf) gegen strategy (zugeordneter Kauf): Beispiele der Abweichungen.
"""
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import BIS, V6, VON, kurse  # noqa: E402

P = kurse()
con = sqlite3.connect(f"file:{V6 / 'data_store' / 'telemetrie.db'}?mode=ro", uri=True)
mh = pd.read_sql_query("select ts_utc, btc_preis, eth_preis, sol_preis from markt_historie where ts_utc >= '2026-08-10'", con)
mh["t"] = pd.to_datetime(mh["ts_utc"], utc=True, format="ISO8601")
print("D1 Versatz markt_historie / Binance-Schlusskurs (Probe innerhalb 2 min nach voller Stunde):")
aus = {}
for c, sp in {"BTC": "btc_preis", "ETH": "eth_preis", "SOL": "sol_preis"}.items():
    m = mh[["t", sp]].dropna().copy()
    m["h"] = m["t"].dt.floor("h")
    m = m[(m["t"] - m["h"]) <= pd.Timedelta(minutes=2)]
    m = m[m["h"].isin(P[c].index)]
    v = (m[sp].values / P[c].loc[m["h"]].values - 1) * 100
    aus[c] = {"n": len(v), "mittel_pct": round(float(np.mean(v)), 4), "median_pct": round(float(np.median(v)), 4)}
    print(f"  {c}: n {len(v)}  Mittel {np.mean(v):+.4f} %  Median {np.median(v):+.4f} %  (|Abw| Median {np.median(np.abs(v)):.4f} %)")

rows = sorted(json.loads((V6 / "data_store" / "trades_v5.json").read_text(encoding="utf-8")), key=lambda r: r["time"])
offen = defaultdict(list)
d2, d3 = [], []
for r in rows:
    typ = str(r.get("type", "")).upper()
    if typ == "BUY":
        offen[r["coin"]].append(r)
    elif typ == "SELL" and offen[r["coin"]]:
        kk = offen.pop(r["coin"])
        if not (VON <= r["time"] < BIS):
            continue
        k = kk[0]
        d2.append({"n_kauf": len(kk), "amt": float(r["amount"]), "qp": float(r["qty"]) * float(r["price"]),
                   "q_v": float(r["qty"]), "q_k": sum(float(x["qty"]) for x in kk), "nach": r.get("_nachgetragen")})
        if r.get("entry_strategie") is not None:
            d3.append({"verkauf": r["time"][:16], "coin": r["coin"], "kauf": k["time"][:16], "kauf_strategy": k.get("strategy"),
                       "entry_strategie": r.get("entry_strategie"), "kauf_score": k.get("signal_score"), "entry_score": r.get("entry_score"),
                       "kauf_active": k.get("active_strategy"), "ausstieg": r.get("strategy"), "position_id": r.get("position_id"),
                       "nachgetragen": r.get("_nachgetragen")})
d2 = pd.DataFrame(d2)
d2["diff"] = d2.qp - d2.amt
print(f"\nD2: {len(d2)} Runden | n_kauf>1: {(d2.n_kauf > 1).sum()} | Summe qty*Kurs - amount = {d2['diff'].sum():+.2f} $ | "
      f"Runden mit |diff|>0,01 $: {(d2['diff'].abs() > 0.01).sum()} | qty Verkauf != qty Kauf (>0,1 %): {((d2.q_v / d2.q_k - 1).abs() > 0.001).sum()}")
print(d2[d2['diff'].abs() > 0.01].head(12).to_string())
d3 = pd.DataFrame(d3)
ab = d3[d3.kauf_strategy != d3.entry_strategie]
print(f"\nD3: {len(d3)} Verkaeufe mit entry_strategie, davon {len(ab)} abweichend. Abweichende Beispiele:")
print(ab.head(15).to_string())
print("\nAbweichungen nach Ausstieg:", ab.ausstieg.value_counts().to_dict(), "| _nachgetragen:", ab.nachgetragen.value_counts(dropna=False).to_dict())
print("Paare (Kauf -> entry_strategie):", ab.groupby(["kauf_strategy", "entry_strategie"]).size().to_dict())
print("kauf_active == entry_strategie bei Abweichung:", int((ab.kauf_active == ab.entry_strategie).sum()))
