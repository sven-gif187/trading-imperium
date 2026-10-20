# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A10 advocatus-diaboli · Zusatzpruefungen (nur lesen).

Z1 A4-V1 realistisch: feste Haltedauer 12 h auf den echten E7-Kaeufen, ABER
   - je Muenze hoechstens eine Position, hoechstens 3 gleichzeitig (Kauf entfaellt, solange gehalten)
   - Notstopp 2,12 % (wirksame Verlustbremse) auf 1m-Tief
   Vergleich gepaart mit dem Ist der GLEICHEN aufgenommenen Kaeufe, je Marktlage, K 0,150.
Z2 A5-Nachspielung: Anteil des Nachspiel-Abschlags am gepaarten Vorteil von mittel/weit (a5_nachspielung.json)
Z3 Labor: wann lagen die groessten Rueckgaenge von K2 und M3? Abstand BTC zur 200-Tage-Linie heute.
   Belichtungs-Latte: 35 % BTC + 65 % Bargeld, monatlich ausgeglichen (gleiche mittlere Investitionsquote wie K2).
   K2 gegen M3 je 91 Tage ab 2022: besser / gleich / schlechter.
Ausgabe: pruefstand/daten/a10_zusatz.json
"""
from __future__ import annotations

import bisect
import csv
import json
import math
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import a10_labor_k2 as lk  # eigener Code (A10), nicht labor/backtest.py  # noqa: E402

K = 0.150
out = {}


def ms(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00").replace(" ", "T")).timestamp() * 1000)


# ------------------------------------------------------------------ Z1
def lade_1m(coin):
    t, lo, c = [], [], []
    with (P / "daten" / f"binance_1m_{coin}_USDC.csv").open(encoding="utf-8") as fh:
        for z in csv.DictReader(fh):
            t.append(int(z["ts_ms"]))
            lo.append(float(z["low"]))
            c.append(float(z["close"]))
    return np.array(t), np.array(lo), np.array(c)


K1M = {c: lade_1m(c) for c in ("BTC", "ETH", "SOL")}
runden = []
with (P / "daten" / "a4_runden_v6_E7.csv").open(encoding="utf-8") as fh:
    for z in csv.DictReader(fh):
        runden.append({"coin": z["muenze"], "kauf_ms": ms(z["kauf_t"]), "verk_ms": ms(z["t"]),
                       "kaufpreis": float(z["kaufpreis"]), "nominal": float(z["kauf_nominal"]),
                       "ist_pct": float(z["brutto_pct"]), "lage": z["lage"]})
runden.sort(key=lambda r: r["kauf_ms"])


def fest(r, stunden, stopp):
    t, lo, c = K1M[r["coin"]]
    i0 = bisect.bisect_right(t, r["kauf_ms"] - 60_000)        # erste Minute, die nach dem Kauf beginnt
    i1 = bisect.bisect_right(t, r["kauf_ms"] + stunden * 3_600_000 - 60_000)
    e = r["kaufpreis"]
    if stopp is not None:
        lv = e * (1 - stopp / 100)
        hit = np.nonzero(lo[i0:i1] <= lv)[0]
        if len(hit):
            return -stopp, int(t[i0 + hit[0]]) + 60_000
    return 100 * (c[i1 - 1] / e - 1), r["kauf_ms"] + stunden * 3_600_000


def spiel(stunden, stopp, bindung):
    belegt, aus = {}, []
    for r in runden:
        if bindung:
            offen = [k for k, bis in belegt.items() if bis > r["kauf_ms"]]
            if r["coin"] in offen or len(offen) >= 3:
                continue
        pct, ende = fest(r, stunden, stopp)
        belegt[r["coin"]] = ende
        aus.append((r, pct))
    return aus


def zusammenfassen(aus, label):
    res = {}
    for lage in ("alle", "A_Aug_Trend", "B_SepOkt"):
        zz = [(r, p) for r, p in aus if lage == "alle" or r["lage"].startswith(lage[:1])]
        if not zz:
            continue
        d = [p - r["ist_pct"] for r, p in zz]
        usd_var = sum(r["nominal"] * (p - K) / 100 for r, p in zz)
        usd_ist_gleiche = sum(r["nominal"] * (r["ist_pct"] - K) / 100 for r, _ in zz)
        # Tagesblock-Bootstrap der Differenz je Runde
        tage = {}
        for (r, p), x in zip(zz, d):
            tage.setdefault(r["kauf_ms"] // 86_400_000, []).append(x)
        bl = list(tage.values())
        rng = np.random.default_rng(7)
        boot = []
        for _ in range(5000):
            w = [bl[i] for i in rng.integers(0, len(bl), len(bl))]
            flat = [x for b in w for x in b]
            boot.append(st.mean(flat))
        res[lage] = {"n": len(zz), "var_minus_ist_je_runde_pct": round(st.mean(d), 3),
                     "ci95": [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
                     "netto_K0150_variante_usd": round(usd_var, 2), "netto_K0150_ist_gleiche_kaeufe_usd": round(usd_ist_gleiche, 2),
                     "stopps": sum(1 for _, p in zz if p <= -2.11)}
    print(label, json.dumps(res))
    return res


z1 = {"fest12_ohne_stopp_ohne_bindung": zusammenfassen(spiel(12, None, False), "12h ohne Stopp, ohne Bindung"),
      "fest12_notstopp_ohne_bindung": zusammenfassen(spiel(12, 2.12, False), "12h Notstopp, ohne Bindung"),
      "fest12_notstopp_mit_bindung": zusammenfassen(spiel(12, 2.12, True), "12h Notstopp, mit Bindung"),
      "fest24_notstopp_mit_bindung": zusammenfassen(spiel(24, 2.12, True), "24h Notstopp, mit Bindung")}
ist_alle = sum(r["nominal"] * (r["ist_pct"] - K) / 100 for r in runden)
z1["ist_alle_136_K0150_usd"] = round(ist_alle, 2)
print("Ist alle 136 (Kursbewegung, K 0,150):", round(ist_alle, 2))
out["Z1_a4_v1_realistisch"] = z1

# ------------------------------------------------------------------ Z2
d = json.loads((P / "daten" / "a5_nachspielung.json").read_text(encoding="utf-8"))
mb = d["mit_bindung"]


def nom(w):
    return (w["K0.150"]["netto_usd"] - w["K0.505"]["netto_usd"]) / 0.355 * 100


z2 = {}
nr = nom(mb["Bv_ist"]["gesamt"])
for v in ("mittel_4_3_3", "weit_8_5_5", "ATR_Stopp", "E7_ist", "Bv_nominal"):
    nv = nom(mb[v]["gesamt"])
    g = d["gepaart"][v]["gesamt"]["K0.150"]["diff_usd"]
    z2[v] = {"n": mb[v]["gesamt"]["n"], "gepaart_K0150": round(g, 2), "abschlag_anteil_usd": round(0.0015 * (nr - nv), 2),
             "kostenersparnis_usd": round(0.0015 * (nr - nv), 2), "brutto_kurseffekt_usd": round(g - 0.003 * (nr - nv), 2)}
print("Z2", json.dumps(z2))
out["Z2_a5_abschlag"] = z2

# ------------------------------------------------------------------ Z3 Labor
tage, O, C = lk.laden(lk.UNI6)
zk2 = lk.ziele_k(tage, C, lk.UNI6, True)
zm3 = lk.ziele_m3(tage, C)
ek2 = lk.sim(tage, O, C, zk2, 0.15)
em3 = lk.sim(tage, O, C, zm3, 0.15, bremse=False)


def tiefster(e):
    eq = e["eq"]
    hoch = np.maximum.accumulate(eq)
    dd = eq / hoch - 1
    i = int(np.argmin(dd))
    j = int(np.argmax(eq[:i + 1]))
    return {"hoch_am": e["tage"][j], "tief_am": e["tage"][i], "rueckgang_pct": round(100 * dd[i], 1)}


z3 = {"K2_groesster_rueckgang": tiefster(ek2), "M3_groesster_rueckgang": tiefster(em3)}
btc = C["BTC"]
sma = btc[-200:].mean()
z3["btc_schluss_letzter_tag"] = {"tag": tage[-1], "schluss": float(btc[-1]), "sma200": round(float(sma), 1),
                                 "abstand_pct": round(100 * (btc[-1] / sma - 1), 2)}
# Belichtungs-Latte 35 % BTC, monatlich
zb = {}
for i in range(200, len(tage) - 1):
    if i == 200 or tage[i + 1][:7] != tage[i][:7]:
        zb[i] = {"BTC": 0.35}
eb = lk.sim(tage, O, C, zb, 0.15, bremse=False)
z3["latte_35pct_BTC"] = {"gesamt": lk.kz(eb), "P3": lk.kz(eb, "2022-01-01", "2026-12-31")}
# Korb 6 mit 35 % investiert, monatlich
zk = {}
for i in range(200, len(tage) - 1):
    if i == 200 or tage[i + 1][:7] != tage[i][:7]:
        da = [c for c in lk.UNI6 if not np.isnan(C[c][i])]
        zk[i] = {c: 0.35 / len(da) for c in da}
ek = lk.sim(tage, O, C, zk, 0.15, bremse=False)
z3["latte_35pct_Korb6"] = {"gesamt": lk.kz(ek), "P3": lk.kz(ek, "2022-01-01", "2026-12-31")}
# K2 gegen M3 je 91 Tage ab 2022
a2 = np.concatenate([[500.0], ek2["eq"]])
a3 = np.concatenate([[500.0], em3["eq"]])
t = ["start"] + ek2["tage"]
diff = np.array([(a2[a + 91] / a2[a]) - (a3[a + 91] / a3[a]) for a in range(len(a2) - 91) if t[a] >= "2022-01-01"])
z3["K2_gegen_M3_91_tage_ab_2022"] = {"fenster": len(diff), "K2_besser_pct": round(100 * (diff > 1e-9).mean(), 1),
                                     "gleich_pct": round(100 * (abs(diff) <= 1e-9).mean(), 1),
                                     "K2_schlechter_pct": round(100 * (diff < -1e-9).mean(), 1),
                                     "mittel_pp": round(100 * diff.mean(), 2)}
# Kalenderjahre K2 gegen M3
jahre = {}
for j in range(2018, 2027):
    a, b = f"{j}-01-01", f"{j}-12-31"
    jahre[str(j)] = {"K2": lk.kz(ek2, a, b).get("gesamt_pct"), "M3": lk.kz(em3, a, b).get("gesamt_pct")}
z3["jahre_K2_M3_gesamt_pct"] = jahre
print("Z3", json.dumps(z3, default=float, indent=1))
out["Z3_labor"] = z3

(P / "daten" / "a10_zusatz.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print("gespeichert: daten/a10_zusatz.json")
