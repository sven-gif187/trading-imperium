# -*- coding: utf-8 -*-
"""
A4: Ist der Papier-Kaufkurs realistisch, und was passiert in der ersten Stunde nach dem Kauf?
1-Minuten-Kerzen Binance (oeffentlich) von Kauf-15 min bis Kauf+75 min fuer jeden der 136 Kaeufe.
Cache: pruefstand/daten/a4_minuten_kaeufe.csv (wird bei vorhandener Datei nicht neu geladen).

Kennzahlen je Kauf:
  abw_letzter  = Kaufkurs(entry_geplant) / Schluss der letzten ABGESCHLOSSENEN Minute vor dem Kauf - 1
  abw_offen    = Kaufkurs / Eroeffnung der Kaufminute - 1
  r_5, r_15, r_30, r_60 = Schluss der Minute bei Kauf+X / Kaufkurs - 1   (ab tatsaechlichem Kaufkurs)
  m_60         = Schluss bei Kauf+60 / Schluss der letzten abgeschlossenen Minute vor dem Kauf - 1 (ab Marktkurs)
Zufall: mittlere 60-min-Rendite aller Laufzeit-Stunden derselben Muenze und Lage (Stundenkerzen) = Drift.
"""
import math
import sys
import time
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import DATEN, bootstrap_mittel  # noqa: E402
import json  # noqa: E402

df = pd.read_csv(DATEN / "a4_runden_v6_E7.csv", parse_dates=["kauf_zeit"])
roh = {r["time"]: r for r in json.loads(Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\data_store\trades_v5.json").read_text(encoding="utf-8"))}
CACHE = DATEN / "a4_minuten_kaeufe.csv"
if not CACHE.exists():
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 120000})
    ex.load_markets()
    teile = []
    for i, r in df.iterrows():
        since = int((r.kauf_zeit - pd.Timedelta(minutes=15)).timestamp() * 1000)
        k = ex.fetch_ohlcv(r.coin, "1m", since=since, limit=95)
        for x in k:
            teile.append({"kauf_t": r.kauf_t, "ts": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4]})
    pd.DataFrame(teile).to_csv(CACHE, index=False)
    print("geladen:", CACHE)
m = pd.read_csv(CACHE)
aus = []
for _, r in df.iterrows():
    k = roh[r.kauf_t]
    p = float(k.get("entry_geplant") or k["price"])
    p_fill = float(k["price"])
    g = m[m.kauf_t == r.kauf_t].set_index("ts").sort_index()
    t = int(r.kauf_zeit.timestamp() * 1000)
    min0 = t // 60000 * 60000                    # Beginn der Kaufminute
    letzte = g.loc[min0 - 60000, "c"] if (min0 - 60000) in g.index else np.nan
    offen = g.loc[min0, "o"] if min0 in g.index else np.nan
    z = {"kauf_t": r.kauf_t, "lage": r.lage, "kaufweg": r.kaufweg, "tag": r.tag, "muenze": r.muenze,
         "abw_letzter": (p / letzte - 1) * 100, "abw_offen": (p / offen - 1) * 100, "fill_vs_geplant": (p_fill / p - 1) * 100,
         "sek_in_minute": (t - min0) / 1000}
    for X in (5, 15, 30, 60):
        tx = min0 + X * 60000
        z[f"r_{X}"] = (g.loc[tx, "c"] / p - 1) * 100 if tx in g.index else np.nan
    z["m_60"] = (g.loc[min0 + 60 * 60000, "c"] / letzte - 1) * 100 if (min0 + 60 * 60000) in g.index else np.nan
    # Bis zur naechsten vollen Stunde (Einstieg der Hauptrechnung)
    voll = int(math.ceil(t / 3600000) * 3600000)
    z["bis_volle_stunde"] = (g.loc[voll - 60000, "c"] / p - 1) * 100 if (voll - 60000) in g.index else np.nan
    aus.append(z)
a = pd.DataFrame(aus)
print(f"n {len(a)} | Minutendaten vollstaendig: {a.r_60.notna().sum()}")
print(f"Kaufkurs gegen letzten Minutenschluss vor Kauf: Mittel {a.abw_letzter.mean():+.4f} %, Median {a.abw_letzter.median():+.4f} %, |Abw| Median {a.abw_letzter.abs().median():.4f} %")
print(f"Kaufkurs gegen Eroeffnung der Kaufminute:       Mittel {a.abw_offen.mean():+.4f} %, Median {a.abw_offen.median():+.4f} %")
print(f"Fill gegen entry_geplant (Papier-Schlupf):       Mittel {a.fill_vs_geplant.mean():+.4f} %")
E = {"n": len(a), "abw_letzter_mittel": round(a.abw_letzter.mean(), 4), "abw_letzter_median": round(a.abw_letzter.median(), 4),
     "abw_offen_mittel": round(a.abw_offen.mean(), 4), "pfad": {}}
for s in ("r_5", "r_15", "r_30", "r_60", "m_60", "bis_volle_stunde"):
    b = bootstrap_mittel(a[s], a.tag)
    E["pfad"][s] = {"mittel": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)], "median": round(a[s].median(), 3)}
    print(f"  {s:17s} Mittel {b[0]:+.3f} % [{b[1]:+.2f};{b[2]:+.2f}]  Median {a[s].median():+.3f} %")
for lage, g in a.groupby("lage"):
    b = bootstrap_mittel(g.r_60, g.tag)
    b2 = bootstrap_mittel(g.bis_volle_stunde, g.tag)
    E["pfad"][f"r_60_{lage}"] = {"mittel": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)]}
    E["pfad"][f"bis_volle_stunde_{lage}"] = {"mittel": round(b2[0], 3), "ci95": [round(b2[1], 3), round(b2[2], 3)]}
    print(f"  {lage}: r_60 {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] | bis volle Stunde {b2[0]:+.3f} [{b2[1]:+.2f};{b2[2]:+.2f}]")
for kw, g in a.groupby(a.kaufweg.where(a.kaufweg == "EMA_TREND", "NICHT_EMA")):
    b = bootstrap_mittel(g.r_60, g.tag)
    E["pfad"][f"r_60_{kw}"] = {"n": len(g), "mittel": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)]}
    print(f"  {kw}: n {len(g)} r_60 {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}]")
a.to_csv(DATEN / "a4_minuten_auswertung.csv", index=False)
(DATEN / "a4_minuten.json").write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
