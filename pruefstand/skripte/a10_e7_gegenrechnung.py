# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A10 advocatus-diaboli · unabhaengige Gegenrechnung der E7-Zahlen (v6), OHNE runden_lib und OHNE a4/a5-Module.

1  Kasse E7: eigene FIFO-Paarung direkt aus trades_v5.json (qty x Kurs, Gebuehr nur aus Feld fee)
   Soll laut Auftrag: 136 Runden, brutto +75,51 $, Gebuehren 109,62 $, netto -34,11 $
   Zusatz: Teilverkaeufe? Mehrfachkaeufe?
2  Rueckkauf (A5 Abschnitt 6): naechster Kauf derselben Muenze nach dem Verkauf
   Soll A5: 117 von 136 binnen 24 h, Median 6,0 h, "Durchhalten besser um" +0,39 % (K 0,150)
3  Feste Haltedauer 12 h (A4 V1): Kurs 12 h nach dem Kauf ab letztem Minutenschluss
   Soll A4: Bot 12 h +0,753 %, fest 12 h gegen Ist +0,42 Punkte
   Zusatz: Wie viele 12-h-Fenster ueberlappen mit dem naechsten Kauf derselben Muenze?
4  A5 explorativ X1-X3: Zerlegung des gepaarten Vorteils in Brutto-Kurseffekt, Kostenersparnis
   und Nachspiel-Abschlag (aus a5_explorativ.json, nur gelesen)

Nur lesen. Ausgabe: pruefstand/daten/a10_e7_gegenrechnung.json
"""
from __future__ import annotations

import bisect
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path(__file__).resolve().parent.parent
BOT = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
VON, BIS = "2026-08-13T13:21:19", "2026-10-14T09:18:25"
K = 0.150


def f(x):
    try:
        return float(x or 0.0)
    except (TypeError, ValueError):
        return 0.0


def ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


# ------------------------------------------------------------------ 1 Kasse
rows = json.loads((BOT / "data_store" / "trades_v5.json").read_text(encoding="utf-8"))
rows.sort(key=lambda r: r["time"])
offen = defaultdict(list)
runden, teilverkauf, ohne_kauf = [], 0, 0
for r in rows:
    typ = str(r.get("type", "")).upper()
    coin = r["coin"]
    if typ == "BUY":
        offen[coin].append(r)
    elif typ == "SELL":
        if not offen[coin]:
            ohne_kauf += 1
            continue
        kaeufe = offen.pop(coin)
        q_kauf = sum(f(k["qty"]) for k in kaeufe)
        q_verk = f(r["qty"])
        if abs(q_kauf - q_verk) > 1e-6 * max(q_kauf, 1e-12) * 100:
            teilverkauf += 1 if VON <= r["time"][:19] < BIS else 0
        if not (VON <= r["time"][:19] < BIS):
            continue
        kauf_nom = sum(f(k["qty"]) * f(k["price"]) for k in kaeufe)
        verk_nom = q_verk * f(r["price"])
        fee_k = sum(f(k["fee"]) for k in kaeufe)
        fee_v = f(r["fee"])
        runden.append({"coin": coin.split("/")[0], "kauf_t": kaeufe[0]["time"], "verk_t": r["time"],
                       "kauf_ms": ms(kaeufe[0]["time"]), "verk_ms": ms(r["time"]),
                       "kauf_preis": f(kaeufe[0]["price"]), "verk_preis": f(r["price"]),
                       "n_kaeufe": len(kaeufe), "q_kauf": q_kauf, "q_verk": q_verk,
                       "kauf_nom": kauf_nom, "verk_nom": verk_nom, "fee": fee_k + fee_v,
                       "brutto": verk_nom - kauf_nom, "ausstieg": r.get("strategy")})
brutto = sum(x["brutto"] for x in runden)
fees = sum(x["fee"] for x in runden)
volumen = sum(x["kauf_nom"] + x["verk_nom"] for x in runden)
kasse = {"runden": len(runden), "brutto_usd": round(brutto, 2), "gebuehren_usd": round(fees, 2),
         "netto_usd": round(brutto - fees, 2), "volumen_usd": round(volumen, 1),
         "netto_K0150_usd": round(brutto - K / 200 * volumen, 2),
         "brutto_pct_ungewichtet": round(st.mean(100 * (x["verk_preis"] / x["kauf_preis"] - 1) for x in runden), 3),
         "brutto_pct_gewichtet": round(100 * brutto / sum(x["kauf_nom"] for x in runden), 3),
         "runden_mit_mehreren_kaeufen": sum(x["n_kaeufe"] > 1 for x in runden),
         "teilverkaeufe_im_fenster": teilverkauf, "verkaeufe_ohne_offenen_kauf_gesamt": ohne_kauf}
print("1 KASSE E7 (eigene FIFO):", kasse)

# ------------------------------------------------------------------ 2 Rueckkauf
kaeufe_je = defaultdict(list)
for r in rows:
    if str(r.get("type", "")).upper() == "BUY":
        kaeufe_je[r["coin"].split("/")[0]].append((ms(r["time"]), f(r["price"])))
for c in kaeufe_je:
    kaeufe_je[c].sort()
rk = []
for x in runden:
    lst = kaeufe_je[x["coin"]]
    i = bisect.bisect_right(lst, (x["verk_ms"], float("inf")))
    if i < len(lst):
        t2, p2 = lst[i]
        rk.append({"dt_h": (t2 - x["verk_ms"]) / 3.6e6, "preis_rel_pct": 100 * (p2 / x["verk_preis"] - 1)})
r24 = [y for y in rk if y["dt_h"] <= 24]
r6 = [y for y in rk if y["dt_h"] <= 6]
rueckkauf = {"mit_folgekauf": len(rk), "binnen_24h": len(r24), "binnen_6h": len(r6),
             "median_abstand_h_24": round(st.median(y["dt_h"] for y in r24), 2),
             "durchhalten_besser_24h_pct_K0150": round(st.mean(y["preis_rel_pct"] for y in r24) + K, 3),
             "preis_rel_24h_pct": round(st.mean(y["preis_rel_pct"] for y in r24), 3),
             "teurer_zurueck_24h": sum(y["preis_rel_pct"] > 0 for y in r24),
             "durchhalten_besser_6h_pct_K0150": round(st.mean(y["preis_rel_pct"] for y in r6) + K, 3),
             "durchhalten_besser_6_24h_pct_K0150": round(st.mean(y["preis_rel_pct"] for y in r24 if y["dt_h"] > 6) + K, 3),
             "n_6_24h": sum(1 for y in r24 if y["dt_h"] > 6)}
print("2 RUECKKAUF:", rueckkauf)


# ------------------------------------------------------------------ 3 fest 12 h, Ueberlappung
def lade_1m(coin):
    t, c = [], []
    with (P / "daten" / f"binance_1m_{coin}_USDC.csv").open(encoding="utf-8") as fh:
        for z in csv.DictReader(fh):
            t.append(int(z["ts_ms"]))
            c.append(float(z["close"]))
    return t, c


K1M = {c: lade_1m(c) for c in ("BTC", "ETH", "SOL")}


def kurs_vor(coin, t_ms):
    """Schluss der letzten abgeschlossenen Minute vor t_ms (Minute endet bei ts+60s <= t_ms)."""
    t, c = K1M[coin]
    i = bisect.bisect_right(t, t_ms - 60_000) - 1
    return c[i] if i >= 0 else None


f12, diff12, ueberlapp12, ueberlapp24 = [], [], 0, 0
for x in runden:
    p0 = kurs_vor(x["coin"], x["kauf_ms"])
    p1 = kurs_vor(x["coin"], x["kauf_ms"] + 12 * 3_600_000)
    if p0 and p1:
        r12 = 100 * (p1 / p0 - 1)
        f12.append(r12)
        diff12.append(r12 - 100 * (x["verk_preis"] / x["kauf_preis"] - 1))
    lst = kaeufe_je[x["coin"]]
    i = bisect.bisect_right(lst, (x["kauf_ms"], float("inf")))
    if i < len(lst):
        if lst[i][0] - x["kauf_ms"] < 12 * 3_600_000:
            ueberlapp12 += 1
        if lst[i][0] - x["kauf_ms"] < 24 * 3_600_000:
            ueberlapp24 += 1
fest12 = {"n": len(f12), "bot_12h_pct": round(st.mean(f12), 3), "fest12_minus_ist_pct": round(st.mean(diff12), 3),
          "naechster_kauf_gleiche_muenze_binnen_12h_nach_kauf": ueberlapp12,
          "naechster_kauf_gleiche_muenze_binnen_24h_nach_kauf": ueberlapp24}
print("3 FEST 12 H:", fest12)

# ------------------------------------------------------------------ 4 A5 X1-X3 zerlegen
d = json.loads((P / "daten" / "a5_explorativ.json").read_text(encoding="utf-8"))


def zerlege(w):
    n150, n505 = w["K0.150"]["netto_usd"], w["K0.505"]["netto_usd"]
    nom = (n150 - n505) / (0.505 - 0.150) * 100             # Summe Kaufnominal
    brutto_usd = n150 + (0.150 + 0.15) / 100 * nom          # netto = brutto - (K + Abschlag) * nom
    return nom, brutto_usd


ref = d["referenz_mit_sperre6h"]["gesamt"]
nom_r, br_r = zerlege(ref)
zerlegung = {"referenz": {"n": ref["n"], "nominal_usd": round(nom_r, 0), "brutto_usd": round(br_r, 2)}}
for name, v in d["varianten"].items():
    w = v["gesamt"]["werte"]
    nom, br = zerlege(w)
    dn = nom_r - nom
    zerlegung[name] = {"n": w["n"], "nominal_usd": round(nom, 0),
                       "gepaart_K0150_laut_A5": round(v["gesamt"]["gegen_ref"]["K0.150"]["diff_usd"], 2),
                       "davon_brutto_kurseffekt": round(br - br_r, 2),
                       "davon_echte_kostenersparnis_K0150": round(0.0015 * dn, 2),
                       "davon_nachspiel_abschlag_weniger_runden": round(0.0015 * dn, 2),
                       "ohne_abschlag_artefakt_K0150": round(v["gesamt"]["gegen_ref"]["K0.150"]["diff_usd"] - 0.0015 * dn, 2)}
print("4 ZERLEGUNG A5 X1-X3:", json.dumps(zerlegung, indent=1))

# ------------------------------------------------------------------ 5 Fuellvorteil (A4 8.3)
fv = []
for x in runden:
    p0 = kurs_vor(x["coin"], x["kauf_ms"])
    if p0:
        q = x["kauf_nom"] / x["kauf_preis"]
        fv.append(((p0 - x["kauf_preis"]) * q, 100 * (x["kauf_preis"] / p0 - 1), x))
docht = [y for y in fv if y[1] < -0.3]
fuell = {"fuellvorteil_alle_usd": round(sum(y[0] for y in fv), 2), "n": len(fv),
         "kaeufe_mehr_als_0_3pct_unter_minutenschluss": len(docht),
         "fuellvorteil_docht_usd": round(sum(y[0] for y in docht), 2),
         "brutto_docht_runden_usd": round(sum(y[2]["brutto"] for y in docht), 2),
         "netto_K0150_ohne_fuellvorteil_usd": round(brutto - sum(y[0] for y in fv) - K / 200 * volumen, 2)}
print("5 FUELLVORTEIL:", fuell)

out = {"kasse_e7": kasse, "rueckkauf": rueckkauf, "fest_12h": fest12, "a5_explorativ_zerlegung": zerlegung,
       "fuellvorteil": fuell}
(P / "daten" / "a10_e7_gegenrechnung.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print("gespeichert: daten/a10_e7_gegenrechnung.json")
