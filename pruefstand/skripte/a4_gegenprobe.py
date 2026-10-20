# -*- coding: utf-8 -*-
"""
A4 Gegenprobe: jede wichtige Zahl aus a4_analyse.py auf einem ZWEITEN Weg.

G1  Vorwaertsrendite aus anderer Kursquelle: v6 telemetrie.db markt_historie (15-min-Kurse, nur lesend),
    Einstieg = tatsaechlicher Kaufkurs ohne Schlupf (entry_geplant), Zufall = alle 15-min-Proben derselben
    Muenze und Lage, waehrend der Bot lief (markt_historie wird nur geschrieben, wenn der Bot laeuft).
G2  Trivial-Latte mit eigenem numpy-Code (searchsorted), unabhaengig von a4_basis.rendite.
G3  Kaufweg-Zuordnung: Verkaufsfeld entry_strategie gegen FIFO-Zuordnung von runden_lib; brutto je Kaufweg
    mit eigener FIFO-Paarung direkt aus trades_v5.json.
G4  IC mit scipy.stats.spearmanr (statt Rang-Pearson von pandas), dazu Fisher-z-Bereich (naiv, zu eng).
G5  Cluster-robuster Standardfehler (Cluster = Kauftag) statt Bootstrap fuer die Kernmittel.
G6  Placebo: Ist der Vergleich "Zufall am selben Tag" fuer Kaeufe nach einem Anstieg verzerrt?
    Stundenrenditen je Muenze zufaellig gemischt (kein Gedaechtnis), Schein-Kaeufe nach starkem 24-h-Anstieg,
    dann Vorsprung gegen Tages- und gegen Zeitraum-Zufall. Unverzerrt waere beides ~0.
G7  Vorlauf mit tatsaechlichem Kaufkurs (statt Kerzenschluss), Mittel und Median.
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import (BIS, DATEN, GRENZE_LAGE, HORIZONTE, V6, VON, block_von_tag, bootstrap_mittel,  # noqa: E402
                      cluster_se_mittel, kurse, marktlage, runden_mit_kauf)

G = {}
df = pd.read_csv(DATEN / "a4_runden_v6_E7.csv", parse_dates=["kauf_zeit", "verkauf_zeit"])
print("Runden aus Hauptrechnung:", len(df))

# ---------------------------------------------------------------- G1 markt_historie
con = sqlite3.connect(f"file:{V6 / 'data_store' / 'telemetrie.db'}?mode=ro", uri=True)
mh = pd.read_sql_query("select ts_utc, btc_preis, eth_preis, sol_preis from markt_historie where ts_utc >= '2026-08-10' order by ts_utc", con)
mh["t"] = pd.to_datetime(mh["ts_utc"], utc=True, format="ISO8601")
mh = mh.set_index("t")
print(f"markt_historie: {len(mh)} Proben {mh.index.min()} .. {mh.index.max()}")
spalte = {"BTC": "btc_preis", "ETH": "eth_preis", "SOL": "sol_preis"}
roh = {r["time"]: r for r in json.loads((V6 / "data_store" / "trades_v5.json").read_text(encoding="utf-8"))}


def preis_nach(c: str, t: pd.Timestamp, tol_min: int = 30) -> float:
    s = mh[spalte[c]]
    i = s.index.searchsorted(t)
    if i >= len(s) or (s.index[i] - t) > pd.Timedelta(minutes=tol_min):
        return np.nan
    return float(s.iloc[i])


H1 = [1, 4, 12, 24]
for H in H1:
    w = []
    for _, r in df.iterrows():
        k = roh[r["kauf_t"]]
        p0 = float(k.get("entry_geplant") or k["price"])
        p1 = preis_nach(r["muenze"], r["kauf_zeit"] + pd.Timedelta(hours=H))
        w.append((p1 / p0 - 1) * 100 if p0 and not np.isnan(p1) else np.nan)
    df[f"g_f{H}"] = w
# Zufall: alle Proben, waehrend der Bot lief (je Muenze und Lage)
zuf = []
for c, sp in spalte.items():
    s = mh[sp]
    s = s[(s.index >= df.kauf_zeit.min().floor("h")) & (s.index < pd.Timestamp(BIS + "Z"))]
    for H in H1:
        idx = s.index.searchsorted(s.index + pd.Timedelta(hours=H))
        ok = idx < len(s)
        ziel_t = np.where(ok, s.index.values[np.minimum(idx, len(s) - 1)], np.datetime64("NaT"))
        abst = (pd.to_datetime(ziel_t, utc=True) - (s.index + pd.Timedelta(hours=H))).total_seconds() / 60
        f = np.where(ok & (abst <= 30), s.values[np.minimum(idx, len(s) - 1)] / s.values - 1, np.nan) * 100
        zuf.append(pd.DataFrame({"muenze": c, "H": H, "t": s.index, "f": f}))
zuf = pd.concat(zuf)
zuf["lage"] = zuf["t"].map(marktlage)
bz = zuf.groupby(["muenze", "lage", "H"])["f"].mean()
G["G1_markt_historie"] = {}
print("\nG1 (markt_historie, Einstieg = Kaufkurs) gegen Hauptrechnung (Binance-Stundenkerzen, Laufzeit-Zufall):")
haupt = json.loads((DATEN / "a4_ergebnisse.json").read_text(encoding="utf-8"))
for H in H1:
    x = df[f"g_f{H}"] - [bz.loc[(c, l, H)] for c, l in zip(df.muenze, df.lage)]
    b = bootstrap_mittel(x, block_von_tag(df.tag, math.ceil(H / 24)))
    hz = next(z for z in haupt["zerfall"]["alle"] if z["H"] == H)
    G["G1_markt_historie"][f"H{H}"] = {"n": int(x.notna().sum()), "bot_pct": round(df[f"g_f{H}"].mean(), 3),
                                       "vorsprung": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                       "haupt_bot_pct": hz["bot_pct"], "haupt_vorsprung_lauf": hz["vorsprung_lauf_pct"]}
    print(f"  H{H:>3}: n {x.notna().sum():3d}  Bot {df[f'g_f{H}'].mean():+.3f} (Haupt {hz['bot_pct']:+.3f})  "
          f"Vorsprung {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] (Haupt Laufzeit {hz['vorsprung_lauf_pct']:+.3f})")

# ---------------------------------------------------------------- G2 eigener numpy-Code, Binance-Kerzen
P = kurse()
arr = {c: (P[c].index.values.astype("datetime64[s]").astype(np.int64), P[c].values) for c in P}


def p_at(c, ts):
    t, v = arr[c]
    i = np.searchsorted(t, ts)
    return v[i] if i < len(t) and t[i] == ts else np.nan


lauf = pd.read_csv(DATEN / "a4_eval_stunden_v6.csv")
lauf_set = defaultdict(set)
for sym, h in zip(lauf.symbol, lauf.stunde_utc):
    lauf_set[sym.split("/")[0]].add(int(pd.Timestamp(h).timestamp()) + 3600)
G["G2_numpy"] = {}
print("\nG2 (eigener numpy-Code, Laufzeit-Zufall):")
for H in HORIZONTE:
    bot, zr = [], []
    for c, kt, lage in zip(df.muenze, df.kauf_zeit, df.lage):
        t0 = int(math.ceil(kt.timestamp() / 3600) * 3600)
        a, b = p_at(c, t0), p_at(c, t0 + H * 3600)
        bot.append((b / a - 1) * 100 if not (np.isnan(a) or np.isnan(b)) else np.nan)
    bot = np.array(bot)
    basis = {}
    for c in arr:
        for lage in ("A_Aug_Trend", "B_SepOkt_seitwaerts"):
            ws = []
            for ts in lauf_set[c]:
                if marktlage(pd.Timestamp(ts, unit="s", tz="UTC")) != lage:
                    continue
                a, b = p_at(c, ts), p_at(c, ts + H * 3600)
                if not (np.isnan(a) or np.isnan(b)):
                    ws.append((b / a - 1) * 100)
            basis[(c, lage)] = np.mean(ws)
    x = bot - np.array([basis[(c, l)] for c, l in zip(df.muenze, df.lage)])
    hz = next(z for z in haupt["zerfall"]["alle"] if z["H"] == H)
    G["G2_numpy"][f"H{H}"] = {"bot_pct": round(float(np.nanmean(bot)), 3), "vorsprung_lauf": round(float(np.nanmean(x)), 3),
                              "haupt": hz["vorsprung_lauf_pct"]}
    print(f"  H{H:>3}: Bot {np.nanmean(bot):+.3f} (Haupt {hz['bot_pct']:+.3f}) | Vorsprung {np.nanmean(x):+.3f} (Haupt {hz['vorsprung_lauf_pct']:+.3f})")

# ---------------------------------------------------------------- G3 Kaufweg-Zuordnung und brutto
rows = sorted(roh.values(), key=lambda r: r["time"])
offen = defaultdict(list)
paare = []
for r in rows:
    typ = str(r.get("type", "")).upper()
    if typ == "BUY":
        offen[r["coin"]].append(r)
    elif typ == "SELL" and offen[r["coin"]]:
        kk = offen.pop(r["coin"])
        if VON <= r["time"] < BIS:
            br = float(r["qty"]) * float(r["price"]) - sum(float(k["qty"]) * float(k["price"]) for k in kk)
            paare.append({"kaufweg": kk[0].get("strategy"), "entry_strategie": r.get("entry_strategie"), "brutto": br,
                          "entry_score": r.get("entry_score"), "kauf_score": kk[0].get("signal_score")})
pa = pd.DataFrame(paare)
mit = pa[pa.entry_strategie.notna()]
G["G3"] = {"paare": len(pa), "mit_entry_strategie": len(mit), "gleich": int((mit.kaufweg == mit.entry_strategie).sum()),
           "score_gleich": int((mit.entry_score == mit.kauf_score).sum()),
           "brutto_je_kaufweg": pa.groupby("kaufweg")["brutto"].sum().round(2).to_dict()}
print(f"\nG3: {len(pa)} Paare, entry_strategie vorhanden {len(mit)}, gleich FIFO-Kaufweg {G['G3']['gleich']}, Score gleich {G['G3']['score_gleich']}")
print("  brutto je Kaufweg (qty*Kurs, eigene FIFO):", G["G3"]["brutto_je_kaufweg"])
print("  Hauptrechnung:", {k: v["brutto_usd"] for k, v in haupt["kaufweg"]["alle"].items()})

# ---------------------------------------------------------------- G4 IC mit scipy
G["G4_ic_scipy"] = {}
print("\nG4 IC Score <-> Vorwaertsrendite (scipy.spearmanr, Fisher-z naiv):")
for H in HORIZONTE:
    ok = df[df.score.notna() & df[f"f{H}"].notna()]
    rho, p = stats.spearmanr(ok.score, ok[f"f{H}"])
    z, se = np.arctanh(rho), 1 / math.sqrt(len(ok) - 3)
    hz = next(z_ for z_ in haupt["ic_runden"]["alle"] if z_["H"] == H)
    G["G4_ic_scipy"][f"H{H}"] = {"rho": round(float(rho), 3), "p": round(float(p), 4),
                                 "fisher95": [round(float(np.tanh(z - 1.96 * se)), 3), round(float(np.tanh(z + 1.96 * se)), 3)],
                                 "haupt_ic_roh": hz["ic_roh"]}
    print(f"  H{H:>3}: rho {rho:+.3f} p {p:.3f} Fisher [{np.tanh(z - 1.96 * se):+.2f};{np.tanh(z + 1.96 * se):+.2f}] (Haupt {hz['ic_roh']:+.3f})")
rho, p = stats.spearmanr(df.dropna(subset=["score"]).score, df.dropna(subset=["score"]).brutto_pct)
G["G4_ic_brutto"] = {"rho": round(float(rho), 3), "p": round(float(p), 4)}
print(f"  Score <-> Brutto je Runde: rho {rho:+.3f} p {p:.3f}")

# ---------------------------------------------------------------- G5 Cluster-SE statt Bootstrap
G["G5_cluster_se"] = {}
print("\nG5 Cluster-robuster 95 %-Bereich (Cluster = Kauftag bzw. Mehrtagesblock):")
for name, w, b in [("brutto_pct_alle", df.brutto_pct, df.tag),
                   ("brutto_pct_EMA", df[df.kaufweg == "EMA_TREND"].brutto_pct, df[df.kaufweg == "EMA_TREND"].tag),
                   ("brutto_pct_NICHT_EMA", df[df.kaufweg != "EMA_TREND"].brutto_pct, df[df.kaufweg != "EMA_TREND"].tag),
                   ("koennen_lauf_alle", df.koennen_lauf, df.tag),
                   ("vorlauf24_ueber_lauf", df.xr_v24, df.tag)] + \
                  [(f"vorsprung_lauf_H{H}", df[f"xr_f{H}"], block_von_tag(df.tag, math.ceil(H / 24))) for H in HORIZONTE]:
    m, lo, hi, g = cluster_se_mittel(w, b)
    G["G5_cluster_se"][name] = {"mittel": round(m, 3), "ci95": [round(lo, 3), round(hi, 3)], "cluster": g}
    print(f"  {name:24s} {m:+.3f} [{lo:+.2f};{hi:+.2f}] Cluster {g}")

# ---------------------------------------------------------------- G6 Placebo fuer den Tagesvergleich
rng = np.random.default_rng(5)
ergebnisse = {"tag": [], "zeitraum": []}
for rep in range(200):
    xs_tag, xs_zr = [], []
    for c in P:
        s = P[c][(P[c].index >= pd.Timestamp("2026-08-10", tz="UTC")) & (P[c].index < pd.Timestamp("2026-10-14", tz="UTC"))]
        r = np.diff(np.log(s.values))
        r = rng.permutation(r)
        p = np.exp(np.concatenate([[0], np.cumsum(r)]))
        n = len(p)
        v24 = np.full(n, np.nan)
        f24 = np.full(n, np.nan)
        v24[24:] = (p[24:] / p[:-24] - 1) * 100
        f24[:-24] = (p[24:] / p[:-24] - 1) * 100
        tag = np.arange(n) // 24
        ok = ~np.isnan(f24)
        tagmittel = pd.Series(f24[ok]).groupby(tag[ok]).mean()
        schwelle = np.nanquantile(v24, 2 / 3)               # oberes Drittel = "nach Anstieg"
        wahl = np.where(ok & (v24 > schwelle))[0]
        wahl = rng.choice(wahl, size=min(46, len(wahl)), replace=False)
        xs_tag += list(f24[wahl] - tagmittel.loc[tag[wahl]].values)
        xs_zr += list(f24[wahl] - np.nanmean(f24))
    ergebnisse["tag"].append(np.mean(xs_tag))
    ergebnisse["zeitraum"].append(np.mean(xs_zr))
G["G6_placebo"] = {k: {"mittel": round(float(np.mean(v)), 3), "bereich_2_5_97_5": [round(float(np.quantile(v, 0.025)), 3), round(float(np.quantile(v, 0.975)), 3)]}
                   for k, v in ergebnisse.items()}
print("\nG6 Placebo (gemischte Stundenrenditen, Kauf nach starkem 24-h-Anstieg, 24-h-Vorsprung):", G["G6_placebo"])

# ---------------------------------------------------------------- G7 Vorlauf mit Kaufkurs
w = []
for _, r in df.iterrows():
    k = roh[r["kauf_t"]]
    p0 = float(k.get("entry_geplant") or k["price"])
    t = r["kauf_zeit"] - pd.Timedelta(hours=24)
    p_alt = preis_nach(r["muenze"], t, tol_min=20)
    w.append((p0 / p_alt - 1) * 100 if not np.isnan(p_alt) else np.nan)
w = pd.Series(w)
G["G7_vorlauf_kaufkurs"] = {"n": int(w.notna().sum()), "mittel": round(w.mean(), 3), "median": round(w.median(), 3),
                            "haupt_mittel": round(df.v24.mean(), 3), "haupt_median": round(df.v24.median(), 3),
                            "anteil_kurs_24h_vorher_tiefer_pct": round(float((w > 0).mean() * 100), 1)}
print("\nG7 Vorlauf 24 h mit Kaufkurs (markt_historie):", G["G7_vorlauf_kaufkurs"])

(DATEN / "a4_gegenprobe.json").write_text(json.dumps(G, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("\nGeschrieben:", DATEN / "a4_gegenprobe.json")
