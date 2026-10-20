# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 Punkt 5 · Gegenproben anderer Ausstiegsregeln auf DENSELBEN 136 E7-Einstiegen.

Motor: a5_motor.py (1m-Kerzen, Regel-Logik wie v6, RSI-Verkaufssignal nachgebildet; geeicht in a5_eichung.py).
Kapitalbindung: hoechstens 3 Positionen, je Muenze eine; ein echter Kauf entfaellt, solange die Nachspielung
die Muenze noch haelt. (Fruehere Ausstiege erzeugen KEINE neuen Kaeufe - das kann nur A4 beurteilen.)
Abschlag: jede nachgespielte Runde -0,15 Punkte (Skepsis-Regel 7).
Getrennt je Marktlage: A = Kauf 13.08.-31.08. (Anstieg), B = Kauf 01.09.-14.10.
Statistik: Block-Bootstrap nach Kauf-Kalendertag; Vergleich gegen Referenz als gepaarte Tagesdifferenz;
Bonferroni ueber alle Vergleiche (Varianten x Marktlagen).
Vorab festgelegte Varianten (vor dem ersten Lauf, nicht nachjustiert).
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict

import numpy as np

from a5_basis import (ABSCHLAG_NACHSPIELUNG, K_BITVAVO, K_BYBIT, Kerzen, atr_bei, atr_pct_1h,
                      block_bootstrap, iso, runden_e7, speichere, ts_ms)
from a5_motor import Regel, RSIStunde, spiele_alle

PHASEN = {"A_Aug": ("2026-08-01", "2026-09-01"), "B_SepOkt": ("2026-09-01", "2026-10-15"), "gesamt": ("2026-08-01", "2026-10-15")}
REFERENZ = "Bv_ist"


def atr_x_vorab(k1h) -> tuple[float, dict]:
    """x so, dass der mittlere ATR-Stopp VOR dem Fenster (15.06.-13.08.) 2,12 % betraegt (gleiches Risiko
    wie heute wirksam), nur anders auf Muenzen/Zeiten verteilt. Kein Blick in die Zukunft."""
    med = {}
    for coin in k1h.d:
        tg, ap = atr_pct_1h(k1h, coin)
        m = (tg >= ts_ms("2026-06-16T00:00:00Z")) & (tg < ts_ms("2026-08-13T13:21:19Z"))
        med[coin] = float(np.nanmedian(ap[m]))
    return 2.12 / float(np.mean(list(med.values()))), med


def auswerten(z: list[dict], von: str, bis: str, echt: bool = False) -> dict:
    zz = [x for x in z if von <= x["runde"]["kauf_t"][:10] < bis]
    if not zz:
        return {"n": 0}
    out = {"n": len(zz)}
    ab = 0.0 if echt else ABSCHLAG_NACHSPIELUNG
    for K in (K_BITVAVO, K_BYBIT):
        net = [x["kurs_pct"] - K - ab for x in zz]
        usd = [x["runde"]["kauf_nominal"] * v / 100 for x, v in zip(zz, net)]
        tage = [x["runde"]["kauf_t"][:10] for x in zz]
        p, lo, hi = block_bootstrap(tage, net, "mittel")
        out[f"K{K:.3f}"] = {"netto_usd": sum(usd), "je_runde_pct": st.mean(net), "ci95_je_runde": [lo, hi],
                            "treffer_pct": 100 * sum(v > 0 for v in net) / len(net),
                            "treffer_ohne_abschlag_pct": 100 * sum(v + ab > 0 for v in net) / len(net),
                            "avg_gewinn": st.mean([v for v in net if v > 0]) if any(v > 0 for v in net) else None,
                            "avg_verlust": st.mean([v for v in net if v <= 0]) if any(v <= 0 for v in net) else None}
    out["brutto_je_runde_pct"] = st.mean(x["kurs_pct"] for x in zz)
    out["arten"] = dict(Counter(x["art"] for x in zz))
    halte = [(x["aus_ms"] - x["runde"]["kauf_ms"]) / 3_600_000 for x in zz]
    out["haltedauer_median_h"] = st.median(halte)
    out["haltedauer_mittel_h"] = st.mean(halte)
    # Kapitalbindung: Positionsdauer auf das Phasenfenster beschnitten, je Kalenderstunde der Phase
    h0 = max(ts_ms(von + "T00:00:00Z"), ts_ms("2026-08-12T00:00:00Z"))
    h1 = min(ts_ms(bis + "T00:00:00Z"), ts_ms("2026-10-14T13:51:00Z"))
    alle = z
    gebunden = sum(x["runde"]["kauf_nominal"] * max(0, min(x["aus_ms"], h1) - max(x["runde"]["kauf_ms"], h0)) for x in alle)
    out["kapital_gebunden_mittel_usd"] = gebunden / (h1 - h0)
    out["offen_am_ende"] = sum(x.get("offen", False) for x in zz)
    return out


def gepaart(z: list[dict], ref: list[dict], von: str, bis: str, K: float, alpha: float) -> dict:
    """Tagesdifferenz (Kauftag) der Netto-$ Variante minus Referenz; Block-Bootstrap ueber Tage."""
    def tag_usd(zz):
        d = defaultdict(float)
        for x in zz:
            t = x["runde"]["kauf_t"][:10]
            if von <= t < bis:
                d[t] += x["runde"]["kauf_nominal"] * (x["kurs_pct"] - K - ABSCHLAG_NACHSPIELUNG) / 100
        return d
    a, b = tag_usd(z), tag_usd(ref)
    tage = sorted(set(a) | set(b))
    diff = [a.get(t, 0.0) - b.get(t, 0.0) for t in tage]
    p, lo, hi = block_bootstrap(tage, diff, "summe", alpha=alpha, B=20000)
    p95, lo95, hi95 = block_bootstrap(tage, diff, "summe", alpha=0.05, B=20000)
    return {"diff_usd": p, "ci95": [lo95, hi95], "ci_bonferroni": [lo, hi], "tage": len(tage),
            "belegt_besser": lo > 0, "belegt_schlechter": hi < 0}


def main():
    R = runden_e7()
    k1m, k1h = Kerzen("1m"), Kerzen("1h")
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    x_atr, med_atr = atr_x_vorab(k1h)
    atr_tab = {c: atr_pct_1h(k1h, c) for c in k1h.d}

    def sl_atr(r):
        tg, ap = atr_tab[r["coin"]]
        a = atr_bei(tg, ap, r["kauf_ms"])
        return float(min(6.0, max(1.0, x_atr * a)))

    V = {
        "E7_nominal": Regel("E7_nominal", sl=2.5, start=1.2, trail=1.0, be_ab=1.0, puffer=0.35),
        "E7_ist": Regel("E7_ist", sl=2.12, start=1.2, trail=0.85, be_ab=1.0, puffer=0.35),
        "E8_nominal": Regel("E8_nominal", sl=2.5, start=1.57, trail=1.0, be_ab=1.0, puffer=0.55),
        "E8_ist": Regel("E8_ist", sl=2.12, start=1.57, trail=0.85, be_ab=1.0, puffer=0.55),
        "Bv_nominal": Regel("Bv_nominal", sl=2.5, start=1.21, trail=1.0, be_ab=1.0, puffer=0.195),
        "Bv_ist": Regel("Bv_ist", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195),
        "Bv_ist_puffer025": Regel("Bv_ist_puffer025", sl=2.12, start=1.21, trail=0.85, be_ab=1.0, puffer=0.25),
        "Bv_ist_ohne_Null": Regel("Bv_ist_ohne_Null", sl=2.12, start=1.21, trail=0.85, be_ab=None),
        "mittel_4_3_3": Regel("mittel_4_3_3", sl=4.0, start=3.0, trail=3.0, leiter=False, be_ab=None),
        "weit_8_5_5": Regel("weit_8_5_5", sl=8.0, start=5.0, trail=5.0, leiter=False, be_ab=None),
        "ATR_Stopp": Regel("ATR_Stopp", sl=None, sl_fn=sl_atr, start=1.21, trail=0.85, be_ab=1.0, puffer=0.195),
    }
    m_vergleiche = (len(V) - 1) * 3
    alpha_b = 0.05 / m_vergleiche
    erg = {"atr_x": x_atr, "atr_median_vorab_pct": med_atr, "bonferroni_m": m_vergleiche, "alpha_bonferroni": alpha_b,
           "varianten": {}, "mit_bindung": {}, "ohne_bindung": {}, "gepaart": {}}
    # Markt je Phase (1h-Schluss)
    markt = {}
    for ph, (a, b) in PHASEN.items():
        mv = {}
        for coin in k1h.d:
            pa = k1h.kurs_bei(coin, ts_ms(max(a, "2026-08-13") + "T13:00:00Z"))
            pb = k1h.kurs_bei(coin, min(ts_ms(b + "T00:00:00Z"), k1h.ende(coin) - 1))
            mv[coin] = (pb / pa - 1) * 100
        markt[ph] = mv
    erg["markt_je_phase_pct"] = markt
    # echte Runden als Referenzzeile (Kasse, Gebuehr getauscht, ohne Abschlag)
    echt = [{"runde": r, "kurs_pct": r["kurs_pct"], "aus_ms": r["verkauf_ms"], "art": r["ausstieg"]} for r in R]
    erg["echt"] = {ph: auswerten(echt, a, b, echt=True) for ph, (a, b) in PHASEN.items()}

    ergebnisse = {}
    for name, p in V.items():
        z = spiele_alle(R, p, k1m, rsis, bindung=True)
        z0 = spiele_alle(R, p, k1m, rsis, bindung=False)
        ergebnisse[name] = z
        erg["varianten"][name] = {k: v for k, v in p.__dict__.items() if k not in ("sl_fn", "trail_fn", "extra")}
        erg["mit_bindung"][name] = {ph: auswerten(z, a, b) for ph, (a, b) in PHASEN.items()}
        erg["ohne_bindung"][name] = {ph: auswerten(z0, a, b) for ph, (a, b) in PHASEN.items()}
    for name, z in ergebnisse.items():
        if name == REFERENZ:
            continue
        erg["gepaart"][name] = {}
        for ph, (a, b) in PHASEN.items():
            erg["gepaart"][name][ph] = {f"K{K:.3f}": gepaart(z, ergebnisse[REFERENZ], a, b, K, alpha_b)
                                        for K in (K_BITVAVO, K_BYBIT)}
    # Zweiter Weg: gleiche Regeln auf 1h-Kerzen (wie Bericht-Gegenprobe), mit Bindung
    rsis_h = {c: RSIStunde(k1h, k1h, c) for c in k1h.d}
    erg["zweiter_weg_1h"] = {}
    for name in ("E7_ist", "E8_ist", "Bv_ist", "Bv_nominal", "mittel_4_3_3", "weit_8_5_5", "ATR_Stopp"):
        zh = spiele_alle(R, V[name], k1h, rsis_h, bindung=True)
        erg["zweiter_weg_1h"][name] = {ph: auswerten(zh, a, b) for ph, (a, b) in PHASEN.items()}
    # Empfindlichkeit: ohne RSI-Verkaufssignal (so rechnete die Bericht-Gegenprobe)
    erg["ohne_signal"] = {}
    for name in ("Bv_ist", "mittel_4_3_3", "weit_8_5_5"):
        q = Regel(**{**{k: v for k, v in V[name].__dict__.items()}, "signal": False})
        zs = spiele_alle(R, q, k1m, rsis, bindung=True)
        erg["ohne_signal"][name] = {ph: auswerten(zs, a, b) for ph, (a, b) in PHASEN.items()}
        erg["ohne_signal"][name]["gepaart_gegen_mit_signal"] = {
            ph: {f"K{K:.3f}": gepaart(zs, ergebnisse[name], a, b, K, 0.05 / 6) for K in (K_BITVAVO, K_BYBIT)}
            for ph, (a, b) in PHASEN.items()}
    # Runden-Detail fuer Gegenprobe (zweiter Weg) speichern
    detail = {}
    for name, z in ergebnisse.items():
        detail[name] = [{"kauf_t": x["runde"]["kauf_t"], "coin": x["runde"]["coin"], "aus": iso(x["aus_ms"]),
                         "art": x["art"], "kurs_pct": round(x["kurs_pct"], 4), "nominal": round(x["runde"]["kauf_nominal"], 2)}
                        for x in z]
    speichere("a5_nachspielung_detail.json", detail)
    speichere("a5_nachspielung.json", erg)
    # kurze Tabelle
    print(f"ATR-x {x_atr:.2f}  Median-ATR vorab {med_atr}")
    print("Markt", json.dumps(markt, default=float))
    for ph in PHASEN:
        print(f"\n== {ph}")
        e = erg["echt"][ph]
        print(f"  {'echt (Kasse)':20} n={e['n']:3} K.150 {e['K0.150']['netto_usd']:+8.2f}$ {e['K0.150']['je_runde_pct']:+.3f}%  "
              f"K.505 {e['K0.505']['netto_usd']:+8.2f}$  {e['arten']}")
        for name in V:
            e = erg["mit_bindung"][name][ph]
            g = erg["gepaart"].get(name, {}).get(ph, {}).get("K0.150")
            gs = f" diff {g['diff_usd']:+7.2f} [{g['ci95'][0]:+.1f};{g['ci95'][1]:+.1f}] B[{g['ci_bonferroni'][0]:+.1f};{g['ci_bonferroni'][1]:+.1f}]" if g else ""
            print(f"  {name:20} n={e['n']:3} K.150 {e['K0.150']['netto_usd']:+8.2f}$ {e['K0.150']['je_runde_pct']:+.3f}% "
                  f"[{e['K0.150']['ci95_je_runde'][0]:+.2f};{e['K0.150']['ci95_je_runde'][1]:+.2f}] T{e['K0.150']['treffer_pct']:.0f}% "
                  f"K.505 {e['K0.505']['netto_usd']:+8.2f}$ halte {e['haltedauer_median_h']:.1f}h kap {e['kapital_gebunden_mittel_usd']:.0f}$ "
                  f"offen {e['offen_am_ende']}{gs}  {e['arten']}")
        for name, e3 in erg["zweiter_weg_1h"].items():
            e = e3[ph]
            print(f"     1h {name:16} n={e['n']:3} K.150 {e['K0.150']['netto_usd']:+8.2f}$ {e['K0.150']['je_runde_pct']:+.3f}%  {e['arten']}")
        for name, e3 in erg["ohne_signal"].items():
            e = e3[ph]
            print(f"     ohneSig {name:13} n={e['n']:3} K.150 {e['K0.150']['netto_usd']:+8.2f}$ {e['K0.150']['je_runde_pct']:+.3f}% K.505 {e['K0.505']['netto_usd']:+8.2f}$ offen {e['offen_am_ende']} {e['arten']}")
            g = e3["gepaart_gegen_mit_signal"][ph]["K0.150"]
            print(f"        ohne minus mit Signal: {g['diff_usd']:+.2f} [{g['ci95'][0]:+.1f};{g['ci95'][1]:+.1f}] B6[{g['ci_bonferroni'][0]:+.1f};{g['ci_bonferroni'][1]:+.1f}]")


if __name__ == "__main__":
    main()
