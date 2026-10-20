# -*- coding: utf-8 -*-
"""
A4: Zerfallskurve MINUTENGENAU ab dem Kaufzeitpunkt (Hauptmass), plus Pruefung der Papier-Fuellkurse.

Einstieg (realistisch, ohne Zukunftsblick): Schluss der letzten abgeschlossenen 1-min-Kerze vor dem Kauf.
Ausstieg: Schluss der 1-min-Kerze bei Kauf + H (H = 1, 4, 12, 24, 48, 72, 168 h).
Zufall: Laufzeit-Zufall wie in a4_analyse (mittlere H-Rendite aller Stunden derselben Muenze und Lage,
        in denen der Bot lief). Fuer Zufallseinstiege ist der Zeitpunkt in der Stunde egal (keine Bedingung).
Fuellpruefung: Kaufkurs (entry_geplant) unter dem Tief der Kaufminute UND der Minute davor = in echt unmoeglich.
Kursdaten: Binance-1m-Kerzen, die A5 abgelegt hat (pruefstand/daten/binance_1m_<MUENZE>_USDC.csv, 11.08. bis
14.10. 13:51 UTC, nur abgeschlossene Kerzen). Kein neuer Boersenabruf. Gegenprobe: a4_minuten_kaeufe.csv
(eigener Abruf A4 rund um jeden Kauf) muss an denselben Minuten denselben Schlusskurs zeigen.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import DATEN, HORIZONTE, K_ALT, K_NEU, block_von_tag, bootstrap_mittel, cluster_se_mittel  # noqa: E402

df = pd.read_csv(DATEN / "a4_runden_v6_E7.csv", parse_dates=["kauf_zeit"])
roh = {r["time"]: r for r in json.loads(Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\data_store\trades_v5.json").read_text(encoding="utf-8"))}
M = {}
for c in ("BTC", "ETH", "SOL"):
    x = pd.read_csv(DATEN / f"binance_1m_{c}_USDC.csv").set_index("ts_ms").sort_index()
    M[c] = x
print({c: (len(M[c]), str(pd.Timestamp(M[c].index.min(), unit="ms", tz="UTC")), str(pd.Timestamp(M[c].index.max(), unit="ms", tz="UTC"))) for c in M})

# Gegenprobe Datenquelle: eigener A4-Abruf gegen A5-Datei
eig = pd.read_csv(DATEN / "a4_minuten_kaeufe.csv")
eig["muenze"] = eig.kauf_t.map({r.kauf_t: r.muenze for r in df.itertuples()})
vgl = [(row.c, M[row.muenze].loc[row.ts, "close"]) for row in eig.itertuples() if row.ts in M[row.muenze].index]
abw = np.array([abs(a / b - 1) for a, b in vgl])
print(f"Gegenprobe 1m-Daten: {len(vgl)} gleiche Minuten, groesste Abweichung {abw.max() * 100:.5f} %")


def schluss(c, ts):
    return M[c].loc[ts, "close"] if ts in M[c].index else np.nan


zeilen = []
for _, r in df.iterrows():
    k = roh[r.kauf_t]
    p = float(k.get("entry_geplant") or k["price"])
    c = r.muenze
    min0 = int(r.kauf_zeit.timestamp() * 1000) // 60000 * 60000
    p_markt = schluss(c, min0 - 60000)              # letzter abgeschlossener Minutenschluss vor dem Kauf
    tief = min(M[c].loc[min0, "low"], M[c].loc[min0 - 60000, "low"])
    hoch = max(M[c].loc[min0, "high"], M[c].loc[min0 - 60000, "high"])
    z = {"kauf_t": r.kauf_t, "tag": r.tag, "lage": r.lage, "kaufweg": r.kaufweg, "muenze": r.muenze, "score": r.score,
         "kauf_nominal": r.kauf_nominal, "p_fill": p, "p_markt": p_markt, "brutto_pct": r.brutto_pct, "halte_h": r.halte_h,
         "netto_150_pct": r.netto_150_pct, "netto_505_pct": r.netto_505_pct, "ausstieg": r.ausstieg,
         "unter_tief": p < tief * (1 - 1e-5), "ueber_hoch": p > hoch * (1 + 1e-5), "abw_markt": (p / p_markt - 1) * 100}
    for H in HORIZONTE:
        z[f"m{H}"] = (schluss(c, min0 - 60000 + H * 3600000) / p_markt - 1) * 100   # Kurs genau H Stunden spaeter
        z[f"zr{H}"] = r[f"zr_f{H}"]
        z[f"xm{H}"] = z[f"m{H}"] - z[f"zr{H}"]
    zeilen.append(z)
a = pd.DataFrame(zeilen)
E = {}
u = a[a.unter_tief]
E["fuellung"] = {"n": len(a), "unter_minutentief": int(a.unter_tief.sum()), "ueber_minutenhoch": int(a.ueber_hoch.sum()),
                 "abw_markt_mittel_pct": round(a.abw_markt.mean(), 4), "abw_markt_median_pct": round(a.abw_markt.median(), 4),
                 "unter_tief_abw_mittel_pct": round(u.abw_markt.mean(), 3) if len(u) else None,
                 "vorteil_usd": round(float(((a.p_markt - a.p_fill) / a.p_fill * a.kauf_nominal).sum()), 2),
                 "vorteil_usd_nur_unter_tief": round(float(((u.p_markt - u.p_fill) / u.p_fill * u.kauf_nominal).sum()), 2)}
print("Fuellpruefung:", E["fuellung"])
print(a.sort_values("abw_markt").head(8)[["kauf_t", "muenze", "kaufweg", "abw_markt", "unter_tief"]].to_string())

BONF7 = 1 - 0.05 / 7
E["zerfall_minutengenau"] = {}
print("\nZerfall minutengenau ab Marktkurs vor dem Kauf (Laufzeit-Zufall abgezogen):")
print(f"{'H':>4} {'n':>4} {'Bot%':>7} {'Zuf%':>7} {'Vorspr':>7} {'95%':>15} {'Bonf7':>15} {'ClusterSE95':>15} {'-K150':>7} {'-K505':>7} {'(-K150)/Tag':>11}")
for name, sub in [("alle", a), ("A_Aug_Trend", a[a.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", a[a.lage == "B_SepOkt_seitwaerts"]),
                  ("EMA_TREND", a[a.kaufweg == "EMA_TREND"]), ("NICHT_EMA", a[a.kaufweg != "EMA_TREND"])]:
    E["zerfall_minutengenau"][name] = []
    print(f"-- {name}")
    for H in HORIZONTE:
        ok = sub[sub[f"xm{H}"].notna()]
        bl = block_von_tag(ok.tag, math.ceil(H / 24))
        b = bootstrap_mittel(ok[f"xm{H}"], bl)
        bb = bootstrap_mittel(ok[f"xm{H}"], bl, niveau=BONF7)
        cs = cluster_se_mittel(ok[f"xm{H}"], bl) if len(ok) > 2 else (np.nan,) * 4
        zz = {"H": H, "n": len(ok), "bot_pct": round(ok[f"m{H}"].mean(), 3), "zufall_pct": round(ok[f"zr{H}"].mean(), 3),
              "vorsprung": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)], "ci_bonf7": [round(bb[1], 3), round(bb[2], 3)],
              "ci95_cluster_se": [round(cs[1], 3), round(cs[2], 3)], "netto_150": round(b[0] - K_NEU, 3), "netto_505": round(b[0] - K_ALT, 3),
              "netto_150_je_tag": round((b[0] - K_NEU) * 24 / H, 3), "entscheidbar": len(ok) >= 30}
        E["zerfall_minutengenau"][name].append(zz)
        print(f"{H:>4} {len(ok):>4} {zz['bot_pct']:>+7.3f} {zz['zufall_pct']:>+7.3f} {b[0]:>+7.3f} [{b[1]:+.2f};{b[2]:+.2f}] "
              f"[{bb[1]:+.2f};{bb[2]:+.2f}] [{cs[1]:+.2f};{cs[2]:+.2f}] {b[0] - K_NEU:>+7.3f} {b[0] - K_ALT:>+7.3f} {zz['netto_150_je_tag']:>+11.3f}"
              f"{'' if len(ok) >= 30 else '  n<30'}")
# IC minutengenau (Score <-> Rendite ab Marktkurs)
from a4_basis import bootstrap_spearman  # noqa: E402
E["ic_minutengenau"] = []
print("\nIC Score <-> Rendite ab Marktkurs (minutengenau):")
for H in HORIZONTE:
    ok = a[a.score.notna() & a[f"m{H}"].notna()]
    r = bootstrap_spearman(ok.score, ok[f"m{H}"], block_von_tag(ok.tag, math.ceil(H / 24)))
    E["ic_minutengenau"].append({"H": H, "n": r[3], "ic": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)]})
    print(f"  H{H:>4} n {r[3]:3d} IC {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")
# ---------------------------------------------------------------- Kaufweg x Horizont minutengenau (alle Kaufwege, je Lage)
E["kaufweg_x_horizont_min"] = {}
print("\nKaufweg x Horizont minutengenau (Vorsprung gegen Laufzeit-Zufall, Prozentpunkte, n):")
gruppen = [(kw, g) for kw, g in a.groupby("kaufweg")] + [("NICHT_EMA", a[a.kaufweg != "EMA_TREND"]), ("ALLE", a)]
for lage_name in ("alle", "A_Aug_Trend", "B_SepOkt_seitwaerts"):
    for kw, g0 in gruppen:
        g = g0 if lage_name == "alle" else g0[g0.lage == lage_name]
        if len(g) == 0:
            continue
        zeilen_kw = []
        for H in HORIZONTE:
            ok = g[g[f"xm{H}"].notna()]
            b = bootstrap_mittel(ok[f"xm{H}"], block_von_tag(ok.tag, math.ceil(H / 24))) if len(ok) else (np.nan,) * 4
            zeilen_kw.append({"H": H, "n": len(ok), "vorsprung": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                              "netto_150": round(b[0] - K_NEU, 3), "netto_505": round(b[0] - K_ALT, 3)})
        E["kaufweg_x_horizont_min"][f"{lage_name}|{kw}"] = zeilen_kw
        print(f"  {lage_name:20s} {kw:18s} " + " ".join(f"{z['vorsprung']:+6.2f}({z['n']})" for z in zeilen_kw))

# ---------------------------------------------------------------- Vorlauf minutengenau (bis zur letzten Minute vor dem Kauf)
from a4_basis import kurse  # noqa: E402
for H in (24, 72):
    a[f"vm{H}"] = [(r.p_markt / schluss(r.muenze, int(pd.Timestamp(r.kauf_t).timestamp() * 1000) // 60000 * 60000 - 60000 - H * 3600000) - 1) * 100
                   for r in a.itertuples()]
rd = pd.read_csv(DATEN / "a4_runden_v6_E7.csv")
a["zr_v24"], a["zr_v72"] = rd["zr_v24"].values, rd["zr_v72"].values
E["vorlauf_min"] = {}
for H in (24, 72):
    x = a[f"vm{H}"] - a[f"zr_v{H}"]
    b = bootstrap_mittel(a[f"vm{H}"], block_von_tag(a.tag, math.ceil(H / 24)))
    bx = bootstrap_mittel(x, block_von_tag(a.tag, math.ceil(H / 24)))
    E["vorlauf_min"][f"{H}h"] = {"n": int(a[f"vm{H}"].notna().sum()), "bot": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                 "median": round(a[f"vm{H}"].median(), 3), "zufall_lauf": round(a[f"zr_v{H}"].mean(), 3),
                                 "ueber_zufall": round(bx[0], 3), "ci95_ueber": [round(bx[1], 3), round(bx[2], 3)],
                                 "anteil_nach_anstieg_pct": round(float((a[f"vm{H}"] > 0).mean() * 100), 1)}
    print(f"Vorlauf minutengenau {H}h: Bot {b[0]:+.2f} [{b[1]:+.2f};{b[2]:+.2f}] Median {a[f'vm{H}'].median():+.2f} | Laufzeit-Zufall "
          f"{a[f'zr_v{H}'].mean():+.2f} | ueber Zufall {bx[0]:+.2f} [{bx[1]:+.2f};{bx[2]:+.2f}] | nach Anstieg {(a[f'vm{H}'] > 0).mean() * 100:.0f} %")
# Vorlauf-Drittel -> Vorsprung minutengenau 4 h / 12 h und tatsaechliches Brutto
a["v_drittel"] = pd.qcut(a.vm24, 3, labels=["tief", "mittel", "hoch"])
E["vorlauf_drittel_min"] = {}
for k, g in a.groupby("v_drittel", observed=True):
    b4 = bootstrap_mittel(g.xm4, g.tag)
    b12 = bootstrap_mittel(g.xm12, g.tag)
    bb = bootstrap_mittel(g.brutto_pct, g.tag)
    E["vorlauf_drittel_min"][str(k)] = {"n": len(g), "v24_spanne": [round(g.vm24.min(), 2), round(g.vm24.max(), 2)],
                                        "vorsprung4": round(b4[0], 3), "ci95_4": [round(b4[1], 3), round(b4[2], 3)],
                                        "vorsprung12": round(b12[0], 3), "ci95_12": [round(b12[1], 3), round(b12[2], 3)],
                                        "brutto_pct": round(bb[0], 3), "ci95_brutto": [round(bb[1], 3), round(bb[2], 3)],
                                        "netto150_pct": round(g.netto_150_pct.mean(), 3), "stopps": int((g.ausstieg == "STOP_LOSS").sum())}
    print(f"  Drittel {k:6s} n {len(g)} v24 {g.vm24.min():+.2f}..{g.vm24.max():+.2f} | Vorspr4 {b4[0]:+.3f} [{b4[1]:+.2f};{b4[2]:+.2f}] | "
          f"Vorspr12 {b12[0]:+.3f} [{b12[1]:+.2f};{b12[2]:+.2f}] | brutto {bb[0]:+.3f} [{bb[1]:+.2f};{bb[2]:+.2f}] | Stopps {(g.ausstieg == 'STOP_LOSS').sum()}")

# ---------------------------------------------------------------- feste Haltedauer gegen tatsaechliche Ausstiege (gleiche Kaeufe)
E["fest_gegen_ist"] = {}
print("\nFeste Haltedauer (ab Marktkurs) gegen tatsaechlichen Ausstieg (ab Fuellkurs), gleiche Kaeufe:")
ist = bootstrap_mittel(a.brutto_pct, a.tag)
E["fest_gegen_ist"]["ist"] = {"brutto_pct": round(ist[0], 3), "ci95": [round(ist[1], 3), round(ist[2], 3)], "halte_h_mittel": round(a.halte_h.mean(), 1)}
print(f"  tatsaechlich: {ist[0]:+.3f} [{ist[1]:+.2f};{ist[2]:+.2f}] (Halte Mittel {a.halte_h.mean():.1f} h)")
for H in (4, 12, 24, 72):
    d = a[f"m{H}"] - a.brutto_pct
    b = bootstrap_mittel(d, block_von_tag(a.tag, math.ceil(H / 24)))
    E["fest_gegen_ist"][f"H{H}"] = {"fest_pct": round(a[f"m{H}"].mean(), 3), "fest_minus_ist": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                    "fest_minus_ist_minus_nachspiel_0_15": round(b[0] - 0.15, 3)}
    print(f"  fest {H:>3} h: {a[f'm{H}'].mean():+.3f} | fest - ist {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] | nach Nachspiel-Abschlag 0,15: {b[0] - 0.15:+.3f}")

# ---------------------------------------------------------------- Docht-Kaeufe (Kaufkurs deutlich unter letztem Minutenschluss)
doch = a[a.abw_markt < -0.3]
E["docht"] = {"schwelle_pct": -0.3, "n": len(doch), "kaufweg": doch.kaufweg.value_counts().to_dict(),
              "brutto_usd_diese_runden": round(float((doch.brutto_pct / 100 * doch.kauf_nominal).sum()), 2),
              "fuellvorteil_usd": round(float(((doch.p_markt - doch.p_fill) / doch.p_fill * doch.kauf_nominal).sum()), 2),
              "fuellvorteil_usd_alle": E["fuellung"]["vorteil_usd"]}
print("\nDocht-Kaeufe:", E["docht"])
for r in doch.itertuples():
    min0 = int(pd.Timestamp(r.kauf_t).timestamp() * 1000) // 60000 * 60000
    k0, k1 = M[r.muenze].loc[min0 - 60000], M[r.muenze].loc[min0]
    print(f"  {r.kauf_t[:19]} {r.muenze} {r.kaufweg:18s} Kauf {r.p_fill:.4f} | Minute davor O {k0.open} L {k0.low} C {k0.close} | Kaufminute O {k1.open} L {k1.low} C {k1.close}")

a.to_csv(DATEN / "a4_minuten_zerfall.csv", index=False)
(DATEN / "a4_minuten_zerfall.json").write_text(json.dumps(E, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("Geschrieben:", DATEN / "a4_minuten_zerfall.json")
