# -*- coding: utf-8 -*-
"""
A4 einstiegs-pruefer · Hauptrechnung Punkte 1-8 (v6, Epoche E7, Verkaeufe 13.08. 13:21:19 bis 14.10. 09:18:25 UTC).
Ausgabe: Tabellen auf der Konsole + pruefstand/daten/a4_ergebnisse.json
Aufruf: python a4_analyse.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import (BIS, DATEN, GRENZE_LAGE, HORIZONTE, K_ALT, K_NEU, V6, V7, block_von_tag,  # noqa: E402
                      bootstrap_mittel, bootstrap_spearman, kurse, marktlage, rendite, runden_mit_kauf,
                      vorwaerts, zufall_stunden)

E = {}          # Ergebnisse fuer JSON
P = kurse()
df = vorwaerts(runden_mit_kauf(), P)
N = len(df)
print(f"Runden {N} | brutto {df.brutto.sum():+.2f} $ | netto K0,150 {df.netto_150.sum():+.2f} $ | "
      f"netto K0,505 {df.netto_505.sum():+.2f} $ | Kasse (gebucht 0,25 %/Seite) {df.netto.sum():+.2f} $")
E["kontrolle"] = {"runden": N, "brutto_usd": round(df.brutto.sum(), 2), "netto_150_usd": round(df.netto_150.sum(), 2),
                  "netto_505_usd": round(df.netto_505.sum(), 2), "netto_kasse_usd": round(df.netto.sum(), 2),
                  "kaeufe_erster": str(df.kauf_zeit.min()), "kaeufe_letzter": str(df.kauf_zeit.max())}

# ---------------------------------------------------------------- Zufallsstunden im selben Zeitraum
start = df.kauf_zeit.min().floor("h")
ende = pd.Timestamp(BIS + "Z")
Z = zufall_stunden(P, start, ende)
# Marktbewegung je Lage (Korb, gleichgewichtet) zur Begruendung der Lage-Grenze
lage_markt = {}
for lage, (a, b) in {"A_Aug_Trend": (start, GRENZE_LAGE), "B_SepOkt_seitwaerts": (GRENZE_LAGE, ende.floor("h"))}.items():
    lage_markt[lage] = {c: round(rendite(P[c], a, b), 2) for c in P}
    lage_markt[lage]["tage"] = round((b - a).total_seconds() / 86400, 1)
    lage_markt[lage]["korb"] = round(np.mean([lage_markt[lage][c] for c in P]), 2)
print("Markt je Lage (%):", lage_markt)
E["markt_je_lage_pct"] = lage_markt

# Vergleichswerte je Kauf: (a) Muenze + Lage (Zeitraum), (b) Muenze + Kalendertag
spalten = [f"f{H}" for H in HORIZONTE] + ["v24", "v72"]
base_lage = Z.groupby(["muenze", "lage"])[spalten].mean()
base_tag = Z.groupby(["muenze", "tag"])[spalten].mean()
# (c) Laufzeit-Zufall: nur Stunden, in denen der Bot lief (Kaufbewertungen in telemetrie evaluations).
#     Eintritt = naechste volle Stunde nach der Bewertungsstunde (wie beim Bot).
_ev = pd.read_csv(DATEN / "a4_eval_stunden_v6.csv")
_lauf = set(zip(_ev["symbol"].str.split("/").str[0], pd.to_datetime(_ev["stunde_utc"], utc=True) + pd.Timedelta(hours=1)))
Z["laeuft"] = [(c, h) in _lauf for c, h in zip(Z.muenze, Z.h)]
print(f"Zufallsstunden gesamt {len(Z)}, davon Bot lief {int(Z.laeuft.sum())}")
base_lauf = Z[Z.laeuft].groupby(["muenze", "lage"])[spalten].mean()
for s in spalten:
    df[f"zr_{s}"] = [base_lauf.loc[(c, l), s] for c, l in zip(df.muenze, df.lage)]
    df[f"xr_{s}"] = df[s] - df[f"zr_{s}"]      # Vorsprung gegen Zufall (Laufzeit)
for s in spalten:
    df[f"zl_{s}"] = [base_lage.loc[(c, l), s] for c, l in zip(df.muenze, df.lage)]
    df[f"zt_{s}"] = [base_tag.loc[(c, t), s] if (c, t) in base_tag.index else np.nan for c, t in zip(df.muenze, df.tag)]
    df[f"xl_{s}"] = df[s] - df[f"zl_{s}"]      # Vorsprung gegen Zufall (Zeitraum)
    df[f"xt_{s}"] = df[s] - df[f"zt_{s}"]      # Vorsprung gegen Zufall (gleicher Tag)

BONF7 = 1 - 0.05 / 7


def bl(H, sub):
    return block_von_tag(sub["tag"], math.ceil(H / 24))


def zeile_horizont(sub: pd.DataFrame, H: int) -> dict:
    s = f"f{H}"
    ok = sub[~sub[s].isna()]
    n = len(ok)
    m_bot = ok[s].mean() if n else np.nan
    m_z = ok[f"zl_{s}"].mean() if n else np.nan
    xl = bootstrap_mittel(ok[f"xl_{s}"], bl(H, ok)) if n else (np.nan,) * 4
    xlb = bootstrap_mittel(ok[f"xl_{s}"], bl(H, ok), niveau=BONF7) if n else (np.nan,) * 4
    xt = bootstrap_mittel(ok[f"xt_{s}"], bl(H, ok)) if n else (np.nan,) * 4
    xr = bootstrap_mittel(ok[f"xr_{s}"], bl(H, ok)) if n else (np.nan,) * 4
    xrb = bootstrap_mittel(ok[f"xr_{s}"], bl(H, ok), niveau=BONF7) if n else (np.nan,) * 4
    xtb = bootstrap_mittel(ok[f"xt_{s}"], bl(H, ok), niveau=BONF7) if n else (np.nan,) * 4
    r = {"H": H, "n": n, "bloecke": xl[3], "bot_pct": m_bot, "zufall_pct": m_z,
         "vorsprung_pct": xl[0], "ci95": [xl[1], xl[2]], "ci_bonf7": [xlb[1], xlb[2]],
         "vorsprung_tag_pct": xt[0], "ci95_tag": [xt[1], xt[2]], "ci_bonf7_tag": [xtb[1], xtb[2]],
         "zufall_lauf_pct": ok[f"zr_{s}"].mean() if n else np.nan,
         "vorsprung_lauf_pct": xr[0], "ci95_lauf": [xr[1], xr[2]], "ci_bonf7_lauf": [xrb[1], xrb[2]],
         "netto_vorsprung_lauf_150": xr[0] - K_NEU, "netto_vorsprung_tag_150": xt[0] - K_NEU,
         "netto_vorsprung_150": xl[0] - K_NEU, "netto_vorsprung_505": xl[0] - K_ALT,
         "netto_abs_150": m_bot - K_NEU, "netto_abs_505": m_bot - K_ALT,
         "netto_vorsprung_150_je_tag": (xl[0] - K_NEU) * 24 / H, "netto_vorsprung_505_je_tag": (xl[0] - K_ALT) * 24 / H,
         "entscheidbar": n >= 30}
    return {k: (round(v, 3) if isinstance(v, float) else ([round(x, 3) for x in v] if isinstance(v, list) else v))
            for k, v in r.items()}


def drucke_horizonte(titel, zeilen):
    print(f"\n== {titel}")
    print(f"{'H':>4} {'n':>4} {'Bl':>3} {'Bot%':>7} {'Zuf%':>7} {'Vorspr':>7} {'95%-Bereich':>17} {'Bonf(7)':>17} "
          f"{'TagVor':>7} {'-K150':>7} {'-K505':>7} {'abs-150':>7} {'(-150)/Tag':>9}")
    for z in zeilen:
        print(f"{z['H']:>4} {z['n']:>4} {z['bloecke']:>3} {z['bot_pct']:>7.3f} {z['zufall_pct']:>7.3f} {z['vorsprung_pct']:>7.3f} "
              f"[{z['ci95'][0]:>6.2f};{z['ci95'][1]:>6.2f}] [{z['ci_bonf7'][0]:>6.2f};{z['ci_bonf7'][1]:>6.2f}] "
              f"{z['vorsprung_tag_pct']:>7.3f} {z['netto_vorsprung_150']:>7.3f} {z['netto_vorsprung_505']:>7.3f} "
              f"{z['netto_abs_150']:>7.3f} {z['netto_vorsprung_150_je_tag']:>9.3f}{'' if z['entscheidbar'] else '  n<30'}")
    print("     Laufzeit-Zufall: " + " | ".join(f"H{z['H']} {z['vorsprung_lauf_pct']:+.3f} [{z['ci95_lauf'][0]:+.2f};{z['ci95_lauf'][1]:+.2f}]" for z in zeilen))
    print("     Tages-Zufall:    " + " | ".join(f"H{z['H']} {z['vorsprung_tag_pct']:+.3f} [{z['ci95_tag'][0]:+.2f};{z['ci95_tag'][1]:+.2f}]" for z in zeilen))


# ---------------------------------------------------------------- 1+2 Trivial-Latte und Zerfallskurve
E["zerfall"] = {}
for name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]),
                  ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"]),
                  ("regime_RANGING", df[df.regime == "RANGING"]), ("regime_TRENDING_UP", df[df.regime == "TRENDING_UP"])]:
    zeilen = [zeile_horizont(sub, H) for H in HORIZONTE]
    E["zerfall"][name] = zeilen
    drucke_horizonte(f"Trivial-Latte / Zerfall · {name} ({len(sub)} Kaeufe)", zeilen)

# Wiederholung der Berichtszahl (Monat statt Lage), 24 h
print("\n== Bericht-Wiederholung 24 h je Kaufmonat (Zufall = gleiche Muenze, gleicher Monat)")
Z["monat"] = Z["h"].dt.strftime("%Y-%m")
df["monat"] = df["kauf_zeit"].dt.strftime("%Y-%m")
bm = Z.groupby(["muenze", "monat"])["f24"].mean()
df["x_monat_f24"] = df["f24"] - [bm.loc[(c, m)] for c, m in zip(df.muenze, df.monat)]
E["monat_24h"] = {}
for m, g in df.groupby("monat"):
    r = bootstrap_mittel(g["x_monat_f24"], g["tag"])
    E["monat_24h"][m] = {"n": int(g["f24"].notna().sum()), "vorsprung": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)]}
    print(f"{m}: n {g['f24'].notna().sum():3d}  Vorsprung {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")

# ---------------------------------------------------------------- 3 IC je Horizont (Score <-> Vorwaertsrendite)
print("\n== IC (Rangkorrelation Score <-> Rendite) je Horizont, 95 %-Bereich Block-Bootstrap")
E["ic_runden"] = {}
for name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"])]:
    E["ic_runden"][name] = []
    for H in HORIZONTE:
        ok = sub[sub[f"f{H}"].notna() & sub.score.notna()]
        r = bootstrap_spearman(ok.score, ok[f"xt_f{H}"], bl(H, ok))
        r2 = bootstrap_spearman(ok.score, ok[f"f{H}"], bl(H, ok))
        E["ic_runden"][name].append({"H": H, "n": r[3], "ic_vorsprung_tag": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)],
                                     "ic_roh": round(r2[0], 3), "ci95_roh": [round(r2[1], 3), round(r2[2], 3)]})
        print(f"{name:20s} H{H:>4} n {r[3]:3d}  IC(Vorsprung) {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]  IC(roh) {r2[0]:+.3f} [{r2[1]:+.2f};{r2[2]:+.2f}]")
ok = df[df.score.notna()]
r = bootstrap_spearman(ok.score, ok.brutto_pct, ok.tag)
E["ic_runden_tatsaechlich"] = {"n": r[3], "ic": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)]}
print(f"IC Score <-> tatsaechliches Brutto je Runde: {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}] n {r[3]}")

# IC auf allen bewerteten Kaufkandidaten (telemetrie evaluations, Muenze x Stunde)
ev = pd.read_csv(DATEN / "a4_eval_stunden_v6.csv")
ev["muenze"] = ev["symbol"].str.split("/").str[0]
ev["stunde"] = pd.to_datetime(ev["stunde_utc"], utc=True)
ev = ev[(ev.stunde >= start) & ev.max_score.notna()].copy()
ev["kauf_zeit"] = ev["stunde"] + pd.Timedelta(minutes=59, seconds=59)    # Score erst am Stundenende bekannt
ev = vorwaerts(ev, P)
ev["tag"] = ev["stunde"].dt.strftime("%Y-%m-%d")
ev["lage"] = ev["stunde"].map(marktlage)
for H in HORIZONTE:
    ev[f"xt_f{H}"] = ev[f"f{H}"] - [base_tag.loc[(c, t), f"f{H}"] if (c, t) in base_tag.index else np.nan
                                     for c, t in zip(ev.muenze, ev.tag)]
print(f"\n== IC auf Kaufkandidaten (evaluations, {len(ev)} Muenze-Stunden, davon {int((ev.n_genehmigt > 0).sum())} mit Kauf)")
E["ic_kandidaten"] = {}
for name, sub in [("alle", ev), ("A_Aug_Trend", ev[ev.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", ev[ev.lage == "B_SepOkt_seitwaerts"])]:
    E["ic_kandidaten"][name] = []
    for H in HORIZONTE:
        ok = sub[sub[f"xt_f{H}"].notna()]
        r = bootstrap_spearman(ok.max_score, ok[f"xt_f{H}"], bl(H, ok), n=2000)
        r2 = bootstrap_spearman(ok.max_score, ok[f"f{H}"], bl(H, ok), n=2000)
        E["ic_kandidaten"][name].append({"H": H, "n": r[3], "ic": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)],
                                         "ic_roh": round(r2[0], 3), "ci95_roh": [round(r2[1], 3), round(r2[2], 3)]})
        print(f"{name:20s} H{H:>4} n {r[3]:4d}  IC(Tag) {r[0]:+.3f} [{r[1]:+.3f};{r[2]:+.3f}]  IC(roh) {r2[0]:+.3f} [{r2[1]:+.3f};{r2[2]:+.3f}]")
print("Vorsprung (gleicher Tag) 24 h je Score der Kandidaten-Stunde:")
E["kandidaten_score_24h"] = {}
ev["sk"] = pd.cut(ev.max_score, [-99, 3, 5, 7, 8, 99], labels=["<=3", "4-5", "6-7", "8", ">=9"])
for k, g in ev.groupby("sk", observed=True):
    r = bootstrap_mittel(g["xt_f24"], block_von_tag(g["tag"], 1))
    E["kandidaten_score_24h"][str(k)] = {"n": int(g["xt_f24"].notna().sum()), "vorsprung": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)]}
    print(f"  Score {k:>4}: n {g['xt_f24'].notna().sum():4d}  {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")
for H in HORIZONTE:
    ev[f"xr_f{H}"] = ev[f"f{H}"] - [base_lauf.loc[(c, l), f"f{H}"] for c, l in zip(ev.muenze, ev.lage)]
print("Gekauft vs. nur abgelehnt (roh minus Laufzeit-Mittel je Muenze und Lage):")
E["kandidaten_gekauft_vs_abgelehnt_lauf"] = {}
for H in (1, 4, 12, 24, 72):
    for lab, g in (("gekauft", ev[ev.n_genehmigt > 0]), ("abgelehnt", ev[ev.n_genehmigt == 0])):
        r = bootstrap_mittel(g[f"xr_f{H}"], block_von_tag(g["tag"], math.ceil(H / 24)))
        E["kandidaten_gekauft_vs_abgelehnt_lauf"][f"{lab}_{H}h"] = {"n": int(g[f"xr_f{H}"].notna().sum()), "vorsprung": round(r[0], 3),
                                                                   "ci95": [round(r[1], 3), round(r[2], 3)]}
        print(f"  H{H:>3} {lab:9s} n {g[f'xr_f{H}'].notna().sum():4d}  {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")
print("Kandidaten je Score (roh minus Laufzeit-Mittel), 4 h und 24 h:")
E["kandidaten_score_lauf"] = {}
for k, g in ev.groupby("sk", observed=True):
    r4 = bootstrap_mittel(g["xr_f4"], block_von_tag(g["tag"], 1))
    r24 = bootstrap_mittel(g["xr_f24"], block_von_tag(g["tag"], 1))
    E["kandidaten_score_lauf"][str(k)] = {"n": int(g["xr_f24"].notna().sum()), "v4": round(r4[0], 3), "ci95_v4": [round(r4[1], 3), round(r4[2], 3)],
                                          "v24": round(r24[0], 3), "ci95_v24": [round(r24[1], 3), round(r24[2], 3)]}
    print(f"  Score {k:>4}: n {g['xr_f24'].notna().sum():4d}  4h {r4[0]:+.3f} [{r4[1]:+.2f};{r4[2]:+.2f}]  24h {r24[0]:+.3f} [{r24[1]:+.2f};{r24[2]:+.2f}]")
print("Gekauft vs. nur abgelehnt (Vorsprung gleicher Tag):")
E["kandidaten_gekauft_vs_abgelehnt"] = {}
for H in (4, 24, 72):
    for lab, g in (("gekauft", ev[ev.n_genehmigt > 0]), ("abgelehnt", ev[ev.n_genehmigt == 0])):
        r = bootstrap_mittel(g[f"xt_f{H}"], block_von_tag(g["tag"], math.ceil(H / 24)))
        E["kandidaten_gekauft_vs_abgelehnt"][f"{lab}_{H}h"] = {"n": int(g[f"xt_f{H}"].notna().sum()), "vorsprung": round(r[0], 3),
                                                              "ci95": [round(r[1], 3), round(r[2], 3)]}
        print(f"  H{H:>3} {lab:9s} n {g[f'xt_f{H}'].notna().sum():4d}  {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")

# ---------------------------------------------------------------- 4 Vorlauf
print("\n== Vorlauf vor dem Kauf (bis zur letzten abgeschlossenen Kerze)")
E["vorlauf"] = {}
for name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"])]:
    E["vorlauf"][name] = {}
    for H in (24, 72):
        r = bootstrap_mittel(sub[f"v{H}"], block_von_tag(sub["tag"], math.ceil(H / 24)))
        x = bootstrap_mittel(sub[f"xl_v{H}"], block_von_tag(sub["tag"], math.ceil(H / 24)))
        xt = bootstrap_mittel(sub[f"xt_v{H}"], block_von_tag(sub["tag"], math.ceil(H / 24)))
        xr = bootstrap_mittel(sub[f"xr_v{H}"], block_von_tag(sub["tag"], math.ceil(H / 24)))
        anteil_r = float((Z[Z.laeuft & Z.lage.isin(sub.lage.unique())][f"v{H}"] > 0).mean() * 100)
        anteil = float((sub[f"v{H}"] > 0).mean() * 100)
        anteil_z = float((Z[Z.lage.isin(sub.lage.unique())][f"v{H}"] > 0).mean() * 100)
        E["vorlauf"][name][f"{H}h"] = {"n": len(sub), "bot": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)],
                                       "zufall": round(sub[f"zl_v{H}"].mean(), 3), "ueber_zufall": round(x[0], 3),
                                       "ci95_ueber_zufall": [round(x[1], 3), round(x[2], 3)], "ueber_zufall_tag": round(xt[0], 3),
                                       "anteil_kauf_nach_anstieg_pct": round(anteil, 1), "anteil_zufall_pct": round(anteil_z, 1),
                                       "zufall_lauf": round(sub[f"zr_v{H}"].mean(), 3), "ueber_zufall_lauf": round(xr[0], 3),
                                       "ci95_ueber_zufall_lauf": [round(xr[1], 3), round(xr[2], 3)], "anteil_zufall_lauf_pct": round(anteil_r, 1)}
        print(f"{name:20s} {H}h vorher: Bot {r[0]:+.2f} % [{r[1]:+.2f};{r[2]:+.2f}] | Zufall {sub[f'zl_v{H}'].mean():+.2f} | "
              f"ueber Zufall {x[0]:+.2f} [{x[1]:+.2f};{x[2]:+.2f}] (Tag {xt[0]:+.2f}) | Laufzeit-Zufall {sub[f'zr_v{H}'].mean():+.2f}, ueber {xr[0]:+.2f} [{xr[1]:+.2f};{xr[2]:+.2f}] | "
              f"Kauf nach Anstieg {anteil:.0f} % (Zufall {anteil_z:.0f} %, Laufzeit {anteil_r:.0f} %)")
# Hilft oder schadet der Vorlauf? Drittel nach 24-h-Vorlauf
print("Vorlauf-Drittel -> Brutto je Runde und 24-h-Vorsprung:")
df["v24_drittel"] = pd.qcut(df["v24"], 3, labels=["tief", "mittel", "hoch"])
E["vorlauf_drittel"] = {}
for k, g in df.groupby("v24_drittel", observed=True):
    b = bootstrap_mittel(g.brutto_pct, g.tag)
    x = bootstrap_mittel(g.xt_f24, g.tag)
    xr = bootstrap_mittel(g.xr_f24, g.tag)
    xr4 = bootstrap_mittel(g.xr_f4, g.tag)
    E["vorlauf_drittel"][str(k)] = {"vorsprung24_lauf": round(xr[0], 3), "ci95_vorsprung24_lauf": [round(xr[1], 3), round(xr[2], 3)],
                                    "vorsprung4_lauf": round(xr4[0], 3), "ci95_vorsprung4_lauf": [round(xr4[1], 3), round(xr4[2], 3)],
                                    "netto150_usd": round(g.netto_150.sum(), 2), "netto505_usd": round(g.netto_505.sum(), 2),"n": len(g), "v24_spanne": [round(g.v24.min(), 2), round(g.v24.max(), 2)],
                                    "brutto_pct": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                    "netto150_pct": round(g.netto_150_pct.mean(), 3), "vorsprung24_tag": round(x[0], 3),
                                    "ci95_vorsprung24": [round(x[1], 3), round(x[2], 3)], "stopps": int((g.ausstieg == "STOP_LOSS").sum())}
    print(f"  {k:6s} n {len(g):3d} v24 {g.v24.min():+.2f}..{g.v24.max():+.2f} | brutto {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] | "
          f"netto150 {g.netto_150_pct.mean():+.3f} ({g.netto_150.sum():+.2f} $) | Vorsprung24 Tag {x[0]:+.3f} [{x[1]:+.2f};{x[2]:+.2f}] Lauf {xr[0]:+.3f} [{xr[1]:+.2f};{xr[2]:+.2f}] "
          f"| Vorspr4 Lauf {xr4[0]:+.3f} | Stopps {(g.ausstieg == 'STOP_LOSS').sum()}")
r = bootstrap_spearman(df.v24, df.brutto_pct, df.tag)
E["vorlauf_ic_brutto"] = {"ic": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)], "n": r[3]}
print(f"Rangkorrelation Vorlauf24 <-> Brutto je Runde: {r[0]:+.3f} [{r[1]:+.2f};{r[2]:+.2f}]")


# ---------------------------------------------------------------- 5 Kaufwege
def kaufweg_zeile(g: pd.DataFrame) -> dict:
    b = bootstrap_mittel(g.brutto_pct, g.tag)
    n150 = bootstrap_mittel(g.netto_150_pct, g.tag)
    n505 = bootstrap_mittel(g.netto_505_pct, g.tag)
    return {"runden": len(g), "tage": g.tag.nunique(), "brutto_usd": round(g.brutto.sum(), 2),
            "brutto_pct": round(b[0], 3), "ci95_brutto": [round(b[1], 3), round(b[2], 3)],
            "kosten_150_usd": round(g.kosten_150.sum(), 2), "netto_150_usd": round(g.netto_150.sum(), 2),
            "netto_150_pct": round(n150[0], 3), "ci95_netto_150": [round(n150[1], 3), round(n150[2], 3)],
            "kosten_505_usd": round(g.kosten_505.sum(), 2), "netto_505_usd": round(g.netto_505.sum(), 2),
            "netto_505_pct": round(n505[0], 3), "ci95_netto_505": [round(n505[1], 3), round(n505[2], 3)],
            "netto_kasse_usd": round(g.netto.sum(), 2),
            "treffer_150_pct": round((g.netto_150 > 0).mean() * 100, 1), "treffer_505_pct": round((g.netto_505 > 0).mean() * 100, 1),
            "stopps": int((g.ausstieg == "STOP_LOSS").sum()), "nullsicherung": int((g.ausstieg == "BREAKEVEN_LOCK").sum()),
            "nachzieh": int((g.ausstieg == "TRAILING_STOP").sum()), "halte_h_median": round(g.halte_h.median(), 1),
            "score_median": None if g.score.isna().all() else float(g.score.median()),
            "entscheidbar": len(g) >= 30}


print("\n== Kaufwege (Runden, brutto, Kosten, netto bei beiden K, Stopps)")
E["kaufweg"] = {}
for lage_name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"])]:
    E["kaufweg"][lage_name] = {}
    gruppen = list(sub.groupby("kaufweg")) + [("NICHT_EMA (alle anderen)", sub[sub.kaufweg != "EMA_TREND"]), ("SUMME", sub)]
    print(f"-- {lage_name}")
    print(f"{'Kaufweg':26s} {'n':>3} {'brutto$':>8} {'br%/R':>7} {'95%':>15} {'K150$':>6} {'net150$':>8} {'n150%':>7} "
          f"{'K505$':>6} {'net505$':>8} {'Kasse$':>7} {'Stopp':>5} {'Null':>4} {'Halte':>5}")
    for kw, g in sorted(gruppen, key=lambda x: -len(x[1])):
        z = kaufweg_zeile(g)
        E["kaufweg"][lage_name][kw] = z
        print(f"{kw:26s} {z['runden']:>3} {z['brutto_usd']:>+8.2f} {z['brutto_pct']:>+7.3f} [{z['ci95_brutto'][0]:>+5.2f};{z['ci95_brutto'][1]:>+5.2f}] "
              f"{z['kosten_150_usd']:>6.2f} {z['netto_150_usd']:>+8.2f} {z['netto_150_pct']:>+7.3f} {z['kosten_505_usd']:>6.2f} "
              f"{z['netto_505_usd']:>+8.2f} {z['netto_kasse_usd']:>+7.2f} {z['stopps']:>5} {z['nullsicherung']:>4} {z['halte_h_median']:>5}"
              f"{'' if z['entscheidbar'] else '  n<30'}")
# Kaufweg x Horizont (Vorsprung gegen Zufall, Zeitraum-Basis)
print("\n== Kaufweg x Horizont: Vorsprung gegen Zufall in Prozentpunkten (n in Klammern); Bonferroni m=14 fuer EMA/NICHT_EMA")
E["kaufweg_x_horizont"] = {}
BONF14 = 1 - 0.05 / 14
for kw, g in sorted(list(df.groupby("kaufweg")) + [("NICHT_EMA (alle anderen)", df[df.kaufweg != "EMA_TREND"]), ("ALLE", df)],
                    key=lambda x: -len(x[1])):
    E["kaufweg_x_horizont"][kw] = []
    teile = []
    for H in HORIZONTE:
        ok = g[g[f"f{H}"].notna()]
        r = bootstrap_mittel(ok[f"xl_f{H}"], bl(H, ok)) if len(ok) else (np.nan,) * 4
        rb = bootstrap_mittel(ok[f"xl_f{H}"], bl(H, ok), niveau=BONF14) if len(ok) else (np.nan,) * 4
        rr = bootstrap_mittel(ok[f"xr_f{H}"], bl(H, ok)) if len(ok) else (np.nan,) * 4
        rrb = bootstrap_mittel(ok[f"xr_f{H}"], bl(H, ok), niveau=BONF14) if len(ok) else (np.nan,) * 4
        rt = bootstrap_mittel(ok[f"xt_f{H}"], bl(H, ok)) if len(ok) else (np.nan,) * 4
        E["kaufweg_x_horizont"][kw].append({"H": H, "n": len(ok), "vorsprung": round(r[0], 3), "ci95": [round(r[1], 3), round(r[2], 3)],
                                             "vorsprung_lauf": round(rr[0], 3), "ci95_lauf": [round(rr[1], 3), round(rr[2], 3)], "ci_bonf14_lauf": [round(rrb[1], 3), round(rrb[2], 3)],
                                             "netto_lauf_150": round(rr[0] - K_NEU, 3), "netto_lauf_505": round(rr[0] - K_ALT, 3),
                                             "vorsprung_tag": round(rt[0], 3), "ci95_tag": [round(rt[1], 3), round(rt[2], 3)],
                                             "ci_bonf14": [round(rb[1], 3), round(rb[2], 3)],
                                             "netto_150": round(r[0] - K_NEU, 3), "netto_505": round(r[0] - K_ALT, 3)})
        teile.append(f"{r[0]:+6.2f}/{rr[0]:+5.2f}/{rt[0]:+5.2f}({len(ok)})")
    print(f"{kw:26s} " + " ".join(teile))

print("Kaufweg x Horizont je Lage (Laufzeit-Zufall):")
E["kaufweg_x_horizont_lage"] = {}
for lage_name in ("A_Aug_Trend", "B_SepOkt_seitwaerts"):
    sub = df[df.lage == lage_name]
    for kw, g in [("EMA_TREND", sub[sub.kaufweg == "EMA_TREND"]), ("NICHT_EMA", sub[sub.kaufweg != "EMA_TREND"]), ("ALLE", sub)]:
        zeilen = []
        for H in HORIZONTE:
            ok = g[g[f"f{H}"].notna()]
            rr = bootstrap_mittel(ok[f"xr_f{H}"], bl(H, ok))
            zeilen.append({"H": H, "n": len(ok), "vorsprung_lauf": round(rr[0], 3), "ci95_lauf": [round(rr[1], 3), round(rr[2], 3)]})
        E["kaufweg_x_horizont_lage"][f"{lage_name}|{kw}"] = zeilen
        print(f"  {lage_name:20s} {kw:10s} " + " ".join(f"{z['vorsprung_lauf']:+6.2f}({z['n']})" for z in zeilen))

# ---------------------------------------------------------------- 6 Koennen gegen Drift
print("\n== Koennen gegen Drift (tatsaechliches Brutto je Runde minus Marktdrift waehrend der Haltedauer)")
mu_lage = Z.groupby(["muenze", "lage"])["f1"].mean()           # mittlere Stundenrendite je Muenze und Lage
mu_lauf = Z[Z.laeuft].groupby(["muenze", "lage"])["f1"].mean()  # nur Stunden, in denen der Bot lief
df["drift_lauf"] = [mu_lauf.loc[(c, l)] * h for c, l, h in zip(df.muenze, df.lage, df.halte_h)]
df["koennen_lauf"] = df.brutto_pct - df.drift_lauf
df["drift_lage"] = [mu_lage.loc[(c, l)] * h for c, l, h in zip(df.muenze, df.lage, df.halte_h)]
# Zweiter Weg: Zufallskauf derselben Muenze am selben Tag mit gleicher (gerundeter) Haltedauer
drift_tag = []
for c, t, h in zip(df.muenze, df.tag, df.halte_h):
    Hh = max(1, int(round(h)))
    stunden = [x for x in P[c].index if x.strftime("%Y-%m-%d") == t]
    w = [rendite(P[c], s, s + pd.Timedelta(hours=Hh)) for s in stunden]
    w = [x for x in w if not np.isnan(x)]
    drift_tag.append(np.mean(w) if w else np.nan)
df["drift_tag"] = drift_tag
df["koennen_lage"] = df.brutto_pct - df.drift_lage
df["koennen_tag"] = df.brutto_pct - df.drift_tag
E["koennen"] = {}
for name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"]),
                  ("EMA_TREND", df[df.kaufweg == "EMA_TREND"]), ("NICHT_EMA", df[df.kaufweg != "EMA_TREND"])]:
    b = bootstrap_mittel(sub.brutto_pct, sub.tag)
    kl = bootstrap_mittel(sub.koennen_lage, sub.tag)
    kt = bootstrap_mittel(sub.koennen_tag, sub.tag)
    kr = bootstrap_mittel(sub.koennen_lauf, sub.tag)
    E["koennen"][name] = {"drift_lauf_pct": round(sub.drift_lauf.mean(), 3), "koennen_lauf_pct": round(kr[0], 3),
                          "ci95_koennen_lauf": [round(kr[1], 3), round(kr[2], 3)], "koennen_lauf_minus_K150": round(kr[0] - K_NEU, 3),
                          "koennen_lauf_minus_K505": round(kr[0] - K_ALT, 3),"n": len(sub), "brutto_pct": round(b[0], 3), "drift_lage_pct": round(sub.drift_lage.mean(), 3),
                          "drift_tag_pct": round(sub.drift_tag.mean(), 3), "koennen_lage_pct": round(kl[0], 3),
                          "ci95_koennen_lage": [round(kl[1], 3), round(kl[2], 3)], "koennen_tag_pct": round(kt[0], 3),
                          "ci95_koennen_tag": [round(kt[1], 3), round(kt[2], 3)],
                          "koennen_minus_K150": round(kl[0] - K_NEU, 3), "koennen_minus_K505": round(kl[0] - K_ALT, 3),
                          "halte_h_mittel": round(sub.halte_h.mean(), 2)}
    print(f"{name:20s} n {len(sub):3d} brutto {b[0]:+.3f} | Drift(Lage) {sub.drift_lage.mean():+.3f} | Koennen {kl[0]:+.3f} "
          f"[{kl[1]:+.2f};{kl[2]:+.2f}] | Drift(Tag) {sub.drift_tag.mean():+.3f} -> Koennen {kt[0]:+.3f} [{kt[1]:+.2f};{kt[2]:+.2f}] "
          f"| Drift(Lauf) {sub.drift_lauf.mean():+.3f} -> Koennen {kr[0]:+.3f} [{kr[1]:+.2f};{kr[2]:+.2f}] | Halte {sub.halte_h.mean():.1f} h")

# ---------------------------------------------------------------- 7 Score-Eichung
print("\n== Score-Eichung (Ergebnis je Score-Stufe)")
df["score_stufe"] = pd.cut(df.score, [-99, 5, 7, 8, 99], labels=["3-5", "6-7", "8", "9-10"])
E["score"] = {}
BONF4 = 1 - 0.05 / 4
for lage_name, sub in [("alle", df), ("A_Aug_Trend", df[df.lage == "A_Aug_Trend"]), ("B_SepOkt_seitwaerts", df[df.lage == "B_SepOkt_seitwaerts"])]:
    E["score"][lage_name] = {}
    print(f"-- {lage_name}")
    for k, g in sub.groupby("score_stufe", observed=True):
        b = bootstrap_mittel(g.brutto_pct, g.tag)
        bb = bootstrap_mittel(g.brutto_pct, g.tag, niveau=BONF4)
        x = bootstrap_mittel(g.xt_f24, g.tag)
        kw = g.kaufweg.value_counts().to_dict()
        E["score"][lage_name][str(k)] = {"n": len(g), "brutto_pct": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                         "ci_bonf4": [round(bb[1], 3), round(bb[2], 3)], "brutto_usd": round(g.brutto.sum(), 2),
                                         "netto_150_usd": round(g.netto_150.sum(), 2), "netto_505_usd": round(g.netto_505.sum(), 2),
                                         "netto_150_pct": round(g.netto_150_pct.mean(), 3), "netto_505_pct": round(g.netto_505_pct.mean(), 3),
                                         "treffer_150_pct": round((g.netto_150 > 0).mean() * 100, 1),
                                         "stopps": int((g.ausstieg == "STOP_LOSS").sum()), "vorsprung24_tag": round(x[0], 3),
                                         "kaufwege": kw, "entscheidbar": len(g) >= 30}
        print(f"  Score {k:5s} n {len(g):3d} brutto {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] ({g.brutto.sum():+.2f} $) | netto150 "
              f"{g.netto_150.sum():+.2f} $ | netto505 {g.netto_505.sum():+.2f} $ | Treffer150 {(g.netto_150 > 0).mean() * 100:.0f} % | "
              f"Stopps {(g.ausstieg == 'STOP_LOSS').sum()} | Vorspr24 {x[0]:+.3f} | {kw}")
    ohne = sub[sub.score.isna()]
    if len(ohne):
        E["score"][lage_name]["ohne_score"] = {"n": len(ohne), "brutto_usd": round(ohne.brutto.sum(), 2), "kaufwege": ohne.kaufweg.value_counts().to_dict()}
# Score innerhalb EMA_TREND (Kaufweg-Mischung als Stoergroesse ausschalten)
print("Score innerhalb EMA_TREND:")
E["score_ema"] = {}
for k, g in df[df.kaufweg == "EMA_TREND"].groupby("score_stufe", observed=True):
    b = bootstrap_mittel(g.brutto_pct, g.tag)
    E["score_ema"][str(k)] = {"n": len(g), "brutto_pct": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                              "netto_150_usd": round(g.netto_150.sum(), 2)}
    print(f"  Score {k:5s} n {len(g):3d} brutto {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] netto150 {g.netto_150.sum():+.2f} $")

# ---------------------------------------------------------------- 8 market_regime-Feld
print("\n== market_regime-Feld der Kaeufe")
E["regime"] = {}
for rg, g in df.groupby("regime"):
    z = kaufweg_zeile(g)
    x = bootstrap_mittel(g.xl_f24, g.tag)
    z["vorsprung24"] = round(x[0], 3)
    z["ci95_vorsprung24"] = [round(x[1], 3), round(x[2], 3)]
    z["lage_A"] = int((g.lage == "A_Aug_Trend").sum())
    E["regime"][rg] = z
    print(f"{rg:12s} n {z['runden']:3d} brutto {z['brutto_pct']:+.3f} [{z['ci95_brutto'][0]:+.2f};{z['ci95_brutto'][1]:+.2f}] "
          f"netto150 {z['netto_150_usd']:+.2f} $ netto505 {z['netto_505_usd']:+.2f} $ Stopps {z['stopps']} | Vorspr24 {x[0]:+.3f} "
          f"[{x[1]:+.2f};{x[2]:+.2f}] | davon Aug {z['lage_A']}")
print("Kaufweg x market_regime-Feld:")
E["kaufweg_x_regime"] = {}
for (kw, rg), g in df.groupby(["kaufweg", "regime"]):
    if len(g) < 3:
        continue
    b = bootstrap_mittel(g.brutto_pct, g.tag)
    E["kaufweg_x_regime"][f"{kw}|{rg}"] = {"n": len(g), "brutto_pct": round(b[0], 3), "ci95": [round(b[1], 3), round(b[2], 3)],
                                           "brutto_usd": round(g.brutto.sum(), 2), "netto_150_usd": round(g.netto_150.sum(), 2),
                                           "netto_505_usd": round(g.netto_505.sum(), 2), "stopps": int((g.ausstieg == "STOP_LOSS").sum()),
                                           "davon_aug": int((g.lage == "A_Aug_Trend").sum())}
    print(f"  {kw:18s} {rg:12s} n {len(g):3d} brutto {b[0]:+.3f} [{b[1]:+.2f};{b[2]:+.2f}] netto150 {g.netto_150.sum():+.2f} $ "
          f"netto505 {g.netto_505.sum():+.2f} $ Stopps {(g.ausstieg == 'STOP_LOSS').sum()} (Aug {(g.lage == 'A_Aug_Trend').sum()})")
print("Kreuztabelle Lage x Regime:")
print(pd.crosstab(df.lage, df.regime))
E["kreuz_lage_regime"] = pd.crosstab(df.lage, df.regime).to_dict()
print("Kreuztabelle Kaufweg x Lage:")
print(pd.crosstab(df.kaufweg, df.lage))
E["kreuz_kaufweg_lage"] = pd.crosstab(df.kaufweg, df.lage).to_dict()

# ---------------------------------------------------------------- v7 (nur Anzeige, NICHT gemischt)
try:
    d7 = vorwaerts(runden_mit_kauf(V7, "2026-09-25T21:56:26", "2026-10-14T09:51:17"), P)
    for H in (4, 24):
        d7[f"xt_f{H}"] = d7[f"f{H}"] - [base_tag.loc[(c, t), f"f{H}"] if (c, t) in base_tag.index else np.nan
                                        for c, t in zip(d7.muenze, d7.tag)]
    E["v7"] = {"runden": len(d7), "brutto_usd": round(d7.brutto.sum(), 2), "netto_150_usd": round(d7.netto_150.sum(), 2),
               "netto_505_usd": round(d7.netto_505.sum(), 2), "kaufwege": d7.kaufweg.value_counts().to_dict(),
               "vorsprung4_tag": round(d7.xt_f4.mean(), 3), "vorsprung24_tag": round(d7.xt_f24.mean(), 3),
               "n24": int(d7.f24.notna().sum()), "v24_vorlauf": round(d7.v24.mean(), 3), "entscheidbar": False}
    print("\n== v7 (L7, getrennt, n<30):", E["v7"])
except Exception as ex:  # noqa: BLE001
    E["v7"] = {"fehler": str(ex)}
    print("v7 nicht auswertbar:", ex)

# ---------------------------------------------------------------- Ablage
df.to_csv(DATEN / "a4_runden_v6_E7.csv", index=False)
(DATEN / "a4_ergebnisse.json").write_text(json.dumps(E, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("\nGeschrieben:", DATEN / "a4_ergebnisse.json", "und", DATEN / "a4_runden_v6_E7.csv")
