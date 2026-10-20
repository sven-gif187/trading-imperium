# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A10 advocatus-diaboli · UNABHAENGIGE Nachrechnung des Strategie-Labors (K1/K2/M1/M3), eigener Code,
importiert NICHT labor/backtest.py. Regeln aus labor/STRATEGIE_LABOR.md (Svens Vorgabe):

  K1 je Coin und L in (5,10,20,30,60,90,150,250,360):
     Kauf:   Schluss(t) > hoechster Schluss der L Tage VOR t
     Stopp:  beim Kauf Mitte(max,min) der letzten L Schluesse inkl. t; danach max(Vortages-Stopp, Mitte)
     Raus:   Schluss(t) < Vortages-Stopp
     Groesse je Coin: min(1/N, aktiv/9 * 25 % / Jahresschwankung(90 Tage))     N = Coins mit >= 91 Schluessen
  K2 = K1, neue Kaeufe nur wenn BTC-Schluss > SMA200(BTC)
  Ausfuehrung zum Eroeffnungskurs t+1, Kosten K/2 je Seite, Kostenbremse "und" (>25 % UND >= 10 $),
  Start 500 $, ab dem 201. BTC-Tag (wie Labor).

Zusaetzlich (Fragen von A10, nicht im Labor gerechnet):
  R1 Robustheit auf dem 6-Coin-Universum (das Labor hat die Robustheit nur auf 12 Coins gerechnet)
  R2 rollierende 91-Tage-Fenster: Verteilung von Rendite und groesstem Rueckgang (S7: 3 Monate, Abbruch > 25 %)
  R3 Seit 2022: K2 gegen M3 auf denselben Tagen
  R4 Startbild Zielgewichte am letzten Tag

Nur lesen. Ausgabe: pruefstand/daten/a10_labor_k2.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path(__file__).resolve().parent.parent
DATEN = P / "labor" / "daten"
UNI6 = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"]
LB = (5, 10, 20, 30, 60, 90, 150, 250, 360)


def laden(coins):
    roh = {}
    for c in coins + (["BTC"] if "BTC" not in coins else []):
        with (DATEN / f"{c}_1d.csv").open(encoding="utf-8") as fh:
            roh[c] = {z["datum"]: (float(z["open"]), float(z["close"])) for z in csv.DictReader(fh)}
    tage = sorted(roh["BTC"])
    O = {c: np.array([roh[c].get(d, (np.nan, np.nan))[0] for d in tage]) for c in roh}
    C = {c: np.array([roh[c].get(d, (np.nan, np.nan))[1] for d in tage]) for c in roh}
    return tage, O, C


def ok_fenster(arr, i, n):
    return i - n + 1 >= 0 and not np.isnan(arr[i - n + 1:i + 1]).any()


def ziele_k(tage, C, coins, filt, zv=0.25, start_i=200):
    btc = C["BTC"]
    stopp = {(c, L): None for c in coins for L in LB}
    out = {}
    for i in range(start_i, len(tage) - 1):
        erlaubt = True
        if filt:
            erlaubt = ok_fenster(btc, i, 200) and btc[i] > btc[i - 199:i + 1].mean()
        N = sum(ok_fenster(C[c], i, 91) for c in coins)
        w = {}
        for c in coins:
            a = C[c]
            aktiv = 0
            for L in LB:
                if not ok_fenster(a, i, L + 1):
                    stopp[(c, L)] = None
                    continue
                mitte = (a[i - L + 1:i + 1].max() + a[i - L + 1:i + 1].min()) / 2
                s = stopp[(c, L)]
                if s is None:
                    if erlaubt and a[i] > a[i - L:i].max():
                        stopp[(c, L)] = mitte
                        aktiv += 1
                else:
                    if a[i] < s:
                        stopp[(c, L)] = None
                    else:
                        stopp[(c, L)] = max(s, mitte)
                        aktiv += 1
            if aktiv and ok_fenster(a, i, 91):
                r = np.diff(np.log(a[i - 90:i + 1]))
                vol = r.std(ddof=1) * math.sqrt(365)
                w[c] = min(1.0 / N, aktiv / len(LB) * zv / vol)
        out[i] = w
    return out


def ziele_m3(tage, C, start_i=200):
    btc = C["BTC"]
    return {i: {"BTC": 1.0 if (ok_fenster(btc, i, 200) and btc[i] > btc[i - 199:i + 1].mean()) else 0.0}
            for i in range(start_i, len(tage) - 1)}


def ziele_m1(tage, start_i=200):
    return {start_i: {"BTC": 1.0}}


def sim(tage, O, C, ziele, k_runde, bremse=True, verz=0, start_i=200, ende_i=None):
    cs = k_runde / 200
    cash, qty = 500.0, {}
    eq, expo, kosten, runden = [], [], 0.0, 0
    ende_i = len(tage) - 1 if ende_i is None else ende_i
    for i in range(start_i, ende_i):
        j = i + 1
        z = ziele.get(i - verz)
        if z is not None:
            preis = {c: O[c][j] for c in O if not np.isnan(O[c][j])}
            eqo = cash + sum(q * preis[c] for c, q in qty.items() if c in preis)
            orders = []
            for c in set(z) | set(qty):
                if c not in preis:
                    continue
                vi = qty.get(c, 0.0) * preis[c]
                vs = max(0.0, z.get(c, 0.0)) * eqo
                d = vs - vi
                if vi <= 1e-9 and vs < 10:
                    continue
                if vs <= 1e-9 and vi > 0:
                    orders.append((c, -vi, True))
                    continue
                if vi <= 1e-9:
                    orders.append((c, d, False))
                    continue
                if bremse and not (abs(d) > 0.25 * vi and abs(d) >= 10):
                    continue
                orders.append((c, d, False))
            for c, d, voll in sorted(orders, key=lambda x: x[1]):
                p = preis[c]
                if d < 0:
                    menge = qty[c] if voll else min(qty[c], -d / p)
                    erl = menge * p
                    cash += erl * (1 - cs)
                    kosten += erl * cs
                    qty[c] -= menge
                    if qty[c] <= 1e-12 or voll:
                        del qty[c]
                        runden += 1
                else:
                    b = min(d, cash / (1 + cs))
                    if b < 1e-9:
                        continue
                    cash -= b * (1 + cs)
                    kosten += b * cs
                    qty[c] = qty.get(c, 0.0) + b / p
        wert = sum(q * (C[c][j] if not np.isnan(C[c][j]) else O[c][j]) for c, q in qty.items())
        eq.append(cash + wert)
        expo.append(wert / (cash + wert))
    return {"tage": tage[start_i + 1:ende_i + 1], "eq": np.array(eq), "expo": np.array(expo), "kosten": kosten,
            "runden": runden}


def kz(e, von=None, bis=None, start_wert=500.0):
    t = e["tage"]
    eq = e["eq"]
    vorher = np.concatenate([[start_wert], eq[:-1]])
    r = eq / vorher - 1
    m = np.array([(von is None or d >= von) and (bis is None or d <= bis) for d in t])
    r = r[m]
    if len(r) < 2:
        return {}
    w = np.prod(1 + r)
    cagr = w ** (365 / len(r)) - 1
    kurve = np.cumprod(1 + r)
    mdd = (kurve / np.maximum.accumulate(np.concatenate([[1.0], kurve]))[1:] - 1).min()
    sh = r.mean() / r.std(ddof=1) * math.sqrt(365)
    return {"jahr_pct": round(cagr * 100, 1), "gesamt_pct": round((w - 1) * 100, 1), "mdd_pct": round(min(0, mdd) * 100, 1),
            "sharpe": round(sh, 2), "investiert_pct": round(100 * e["expo"][m].mean(), 1)}


def rollierend(e, fenster=91, ab=None):
    """Alle Fenster von 91 Tagen: Rendite und groesster Rueckgang im Fenster."""
    eq = np.concatenate([[500.0], e["eq"]])
    t = ["start"] + e["tage"]
    ren, dd = [], []
    for a in range(0, len(eq) - fenster):
        if ab and t[a] < ab:
            continue
        seg = eq[a:a + fenster + 1]
        ren.append(seg[-1] / seg[0] - 1)
        dd.append((seg / np.maximum.accumulate(seg) - 1).min())
    ren, dd = np.array(ren), np.array(dd)
    return {"fenster": len(ren), "rendite_median_pct": round(100 * np.median(ren), 1),
            "rendite_p10_pct": round(100 * np.percentile(ren, 10), 1), "rendite_p90_pct": round(100 * np.percentile(ren, 90), 1),
            "anteil_rendite_negativ_pct": round(100 * (ren < 0).mean(), 1),
            "rueckgang_median_pct": round(100 * np.median(dd), 1), "rueckgang_p90_pct": round(100 * np.percentile(dd, 10), 1),
            "anteil_rueckgang_ueber_25_pct": round(100 * (dd < -0.25).mean(), 1),
            "anteil_rueckgang_ueber_15_pct": round(100 * (dd < -0.15).mean(), 1)}


def main():
    out = {}
    tage, O, C = laden(UNI6)
    print(f"Daten {tage[0]} .. {tage[-1]}, Start Rueckrechnung {tage[200]} (Labor: 2018-03-05)")
    PER = {"P1": ("2018-03-05", "2020-12-31"), "P2": ("2021-01-01", "2021-12-31"), "P3": ("2022-01-01", "2026-12-31"),
           "Fenster_Bot": ("2026-08-13", "2026-10-13")}

    zk2 = ziele_k(tage, C, UNI6, True)
    zk1 = ziele_k(tage, C, UNI6, False)
    zm3 = ziele_m3(tage, C)
    zm1 = ziele_m1(tage)
    basis = {}
    for name, z, br in (("K2", zk2, True), ("K1", zk1, True), ("M3", zm3, False), ("M1", zm1, False)):
        e = sim(tage, O, C, z, 0.15, bremse=br)
        basis[name] = e
        g = kz(e)
        zeile = {"gesamt": g, "runden_je_monat": round(e["runden"] / (len(e["eq"]) / 30.44), 2), "kosten_usd": round(e["kosten"], 2)}
        for p, (a, b) in PER.items():
            zeile[p] = kz(e, a, b)
        out[f"basis_6coins_{name}_K0.15"] = zeile
        print(f"{name}: {g} | Runden/Mon {zeile['runden_je_monat']} | P1 {zeile['P1'].get('jahr_pct')} P2 {zeile['P2'].get('jahr_pct')} "
              f"P3 {zeile['P3'].get('jahr_pct')} (Sharpe {zeile['P3'].get('sharpe')}, MaxDD {zeile['P3'].get('mdd_pct')}) | "
              f"13.08.-13.10. {zeile['Fenster_Bot'].get('gesamt_pct')} %")
    print("Labor (stufe5c): K2 57,3 % / -35,9 % / 1,35 ; K1 59,3 % / -47,1 % / 1,34 ; M3 27,2 / -63,9 / 0,78 ; M1 25,9 / -76,6 / 0,69")

    # R1 Robustheit auf 6 Coins
    rob = {}
    for label, coins in (("ohne SOL", [c for c in UNI6 if c != "SOL"]), ("ohne DOGE", [c for c in UNI6 if c != "DOGE"]),
                         ("ohne XRP", [c for c in UNI6 if c != "XRP"]), ("nur BTC ETH SOL", ["BTC", "ETH", "SOL"]),
                         ("nur BTC ETH", ["BTC", "ETH"])):
        z = ziele_k(tage, C, coins, True)
        O2 = {c: O[c] for c in coins}
        e = sim(tage, O2, C, z, 0.15)
        rob[label] = {"gesamt": kz(e), "P3": kz(e, *PER["P3"])}
        print(f"K2 {label:16s}: {rob[label]['gesamt']} | P3 {rob[label]['P3']}")
    e = sim(tage, O, C, zk2, 0.15, verz=1)
    rob["Ausfuehrung +1 Tag"] = {"gesamt": kz(e), "P3": kz(e, *PER["P3"])}
    print(f"K2 +1 Tag         : {rob['Ausfuehrung +1 Tag']}")
    for k in (0.30, 0.50, 1.00):
        e = sim(tage, O, C, zk2, k)
        rob[f"Kosten {k}"] = {"gesamt": kz(e), "P3": kz(e, *PER["P3"])}
        print(f"K2 Kosten {k:.2f}     : {rob[f'Kosten {k}']}")
    out["robustheit_K2_6coins"] = rob

    # Start ab anderem Tag (Startzeitpunkt-Abhaengigkeit des Drawdowns)
    for s_label, s_tag in (("Start 2019-01-01", "2019-01-01"), ("Start 2021-11-10 (Hoch)", "2021-11-10"), ("Start 2022-01-01", "2022-01-01")):
        si = tage.index(s_tag)
        for name, z in (("K2", zk2), ("M3", zm3), ("M1", {si: {"BTC": 1.0}})):
            zz = {i: w for i, w in z.items() if i >= si} if name != "M1" else z
            e = sim(tage, O, C, zz, 0.15, bremse=(name == "K2"), start_i=si)
            out.setdefault("startpunkt", {})[f"{s_label} {name}"] = kz(e)
            print(f"{s_label} {name}: {kz(e)}")

    # R2 rollierende 91-Tage-Fenster
    roll = {}
    for name in ("K2", "M3", "M1"):
        roll[name] = {"alle": rollierend(basis[name]), "ab_2022": rollierend(basis[name], ab="2022-01-01")}
        print(f"91-Tage {name}: alle {roll[name]['alle']}\n            ab 2022 {roll[name]['ab_2022']}")
    # K2 minus M3 je 91-Tage-Fenster ab 2022
    eqk = np.concatenate([[500.0], basis["K2"]["eq"]])
    eqm = np.concatenate([[500.0], basis["M3"]["eq"]])
    t = ["start"] + basis["K2"]["tage"]
    diffs = [(eqk[a + 91] / eqk[a]) - (eqm[a + 91] / eqm[a]) for a in range(len(eqk) - 91) if t[a] >= "2022-01-01"]
    diffs = np.array(diffs)
    roll["K2_minus_M3_ab_2022"] = {"median_pct": round(100 * np.median(diffs), 2), "anteil_K2_besser_pct": round(100 * (diffs > 0).mean(), 1)}
    print("K2 minus M3 je 91 Tage ab 2022:", roll["K2_minus_M3_ab_2022"])
    out["rollierend_91_tage"] = roll

    # R4 Startbild: Zielgewichte nach dem letzten Schluss
    letzter = max(zk2)
    out["startbild_letzter_schluss"] = {"tag": tage[letzter], "K2": {c: round(100 * w, 1) for c, w in zk2[letzter].items()},
                                        "summe_pct": round(100 * sum(zk2[letzter].values()), 1)}
    print("Startbild", out["startbild_letzter_schluss"])
    (P / "daten" / "a10_labor_k2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gespeichert: daten/a10_labor_k2.json")


if __name__ == "__main__":
    main()
