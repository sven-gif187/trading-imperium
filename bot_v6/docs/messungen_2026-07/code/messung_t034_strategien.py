# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] NACHTRAGSMESSUNG T-034ff zum Multi-Strategy-Bug, 04.08.2026.
"""
Tragen die strukturell blockierten Strategien aus strategy_brain.py einen
Richtungsvorteil? Trials T-034 bis T-041.

EINORDNUNG: NACHTRAGSMESSUNG zum Multi-Strategy-Bug, NICHT Runde 3. Das
Programm ist nach Regel 13 mit zwei negativen Gates beendet.

DATENBASIS: dieselben 15m-Kerzen wie E2/G2 (data_store/backtest), zu
1h aggregiert. Die Feature-Berechnung stammt aus messung_f2_ic.py und
wurde in G1 gegen die Projektimplementierung verifiziert (17 von 21
exakt, Spearman 1,0000). Damit ist keine Bedingung neu erfunden.

SIGNALBEDINGUNGEN - woertlich aus dem Projektcode, Fundstelle je Regel:
  RSI_OVERSOLD      agents/v4_strategies.py:88-96
  EMA_TREND         agents/v4_strategies.py:102-111
  MACD_CROSS        agents/v4_strategies.py:113-125
  TSI               agents/v4_strategies.py:161-171
  FIBONACCI_SUPPORT agents/v4_strategies.py:176-190 + :41-54
  BOLLINGER_BOUNCE  agents/signal_agent.py:110-115
  RSI_DIVERGENZ     features/rsi_divergence.py:67-90
  MULTI_SIGNAL      agents/signal_agent.py:78-146 (Score >= min_score 3)

AUSGESCHLOSSEN mit Begruendung:
  ICHIMOKU          v4_strategies.py:128 verlangt ICH_tenkan; weder
                    calc_all_indicators (features/indicators.py:9-43)
                    noch market_data.py:62-79 berechnen ICH_*. Es gibt
                    im Projekt KEINE Ichimoku-Implementierung. Selbst zu
                    rechnen hiesse die Bedingung erfinden.
  MOMENTUM_BREAKOUT v4_strategies.py:148 verlangt Vol_high; ebenfalls
                    nirgends im Projekt berechnet.
  STOCHRSI_REVERSAL Registry-Eintrag ohne Bedingung im Code. StochRSI
                    wird zwar berechnet (indicators.py:69), aber keine
                    Strategie wertet sie aus.
  DCA_FEAR_GREED    bereits in E2 gemessen (kein Richtungsvorteil).
  GRID_BOT          Range-Handel, kein Richtungssignal - anderer Typ.

TEST: identisch zu E2/G2. Barrieren +/-2,5%/72h, +/-5%/7d, +/-7%/14d,
First-Touch pessimistisch (Tief vor Hoch), beide Jahre getrennt,
phasengleiches Placebo (40 Ziehungen, nur Uhrzeit innerhalb der real
signalisierten Tage randomisiert), Block-Bootstrap 2000 ueber
Kalendertage, Seed 20260730.

KOSTENSCHWELLE coinweise aus 12_SPREAD-MESSUNG.md.
"""
import bisect
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_ext import lade_jahr, TAG_MS
import messung_f2_ic as F2

SEED = 20260730
BOOT = 2000
ZIEH = 40
STUNDE = 3_600_000
KOMBIS = [("+/-2,5%/72h", 2.5, 72), ("+/-5%/7d", 5.0, 168),
          ("+/-7%/14d", 7.0, 336)]
K_BASIS = {"BTC": 0.50, "ETH": 0.50, "SOL": 0.51, "DOGE": 0.51,
           "ADA": 0.56, "XRP": 0.57, "LINK": 0.62, "AVAX": 0.62,
           "UNI": 0.67, "NEAR": 0.68, "ATOM": 1.07, "DOT": 1.15}


# ---------------------------------------------------------------- Signale
def sig_rsi_oversold(F, i):
    r, a = F["rsi_14"][i], F["adx_14"][i]
    if r is None or a is None:
        return False
    return r < 30 or r < 35 or (r < 45 and a < 25) or (r < 48 and a < 20)


def sig_ema_trend(F, i, cl):
    e20, e50, a = F["p_vs_ema20"][i], F["p_vs_ema50"][i], F["adx_14"][i]
    if e20 is None or e50 is None or a is None:
        return False
    # price > ema20 > ema50 and adx > 20   ODER   price > ema50
    return ((e20 > 0 and e50 > 0 and F["ema20_vs_50"][i] is not None
             and F["ema20_vs_50"][i] > 0 and a > 20) or e50 > 0)


def sig_macd_cross(F, i):
    h, hp, a = F["macd_hist"][i], F["macd_hist"][i - 1], F["adx_14"][i]
    if h is None or hp is None or a is None:
        return False
    return (h > 0 and hp <= 0) or (h > 0 and a > 20)


def sig_tsi(F, i):
    t, th, thp = F["tsi"][i], F["tsi_hist"][i], F["tsi_hist"][i - 1]
    if t is None or th is None or thp is None:
        return False
    return (th > 0 and thp <= 0 and t < 10) or (th > 0 and t > 0)


def sig_bollinger(F, i):
    b, r = F["bb_pos"][i], F["rsi_14"][i]
    if b is None or r is None:
        return False
    return b < 0 and r < 40          # price < BBL und RSI < 40


def sig_fib(F, i, cl):
    d, r, h = F["fib_dist_618"][i], F["rsi_14"][i], F["macd_hist"][i]
    if d is None or r is None:
        return False
    return abs(d) < 0.005 or (h is not None and h > 0 and abs(d) < 0.005)


def sig_rsi_div(F, i):
    v = F["rsi_div_bull"][i]
    return v is not None and v > 0


def sig_multi(F, i, fg):
    """signal_agent.py:78-146, Score >= 3. Nur die Komponenten, die aus
    Kerzendaten rekonstruierbar sind - externe Quellen (Ensemble,
    Orderbuch, VWAP-Bias, V4-Bridge) fehlen und wuerden den Score nur
    ERHOEHEN. Der Test ist damit konservativ."""
    s = 0
    r, a = F["rsi_14"][i], F["adx_14"][i]
    if r is None:
        return False
    if r < 30:
        s += 3
    elif r < 35:
        s += 2
    elif r < 45:
        s += 1
    h = F["macd_hist"][i]
    if h is not None:
        ml = F["macd_line"][i]
        if h > 0 and ml is not None and ml < 0:
            s += 2
        elif h > 0:
            s += 1
    e20, e50 = F["p_vs_ema20"][i], F["p_vs_ema50"][i]
    if e20 is not None and e50 is not None and e20 > 0 and e50 > 0:
        s += 1
    if a is not None and a > 25:
        s += 1
    if fg < 15:
        s += 3
    elif fg < 25:
        s += 2
    elif fg < 35:
        s += 1
    b = F["bb_pos"][i]
    if b is not None and b < 0 and r < 40:
        s += 2
    if F["rsi_div_bull"][i]:
        s += 2
    vr = F["vol_ratio_20"][i]
    if vr is not None and vr > 2 and r < 60:
        s += 1
    return s >= 3


STRATEGIEN = [
    ("T-034", "RSI_OVERSOLD", "v4_strategies.py:88-96",
     lambda F, i, cl, fg: sig_rsi_oversold(F, i)),
    ("T-035", "EMA_TREND", "v4_strategies.py:102-111",
     lambda F, i, cl, fg: sig_ema_trend(F, i, cl)),
    ("T-036", "MACD_CROSS", "v4_strategies.py:113-125",
     lambda F, i, cl, fg: sig_macd_cross(F, i)),
    ("T-037", "TSI", "v4_strategies.py:161-171",
     lambda F, i, cl, fg: sig_tsi(F, i)),
    ("T-038", "BOLLINGER_BOUNCE", "signal_agent.py:110-115",
     lambda F, i, cl, fg: sig_bollinger(F, i)),
    ("T-039", "FIBONACCI_SUPPORT", "v4_strategies.py:176-190",
     lambda F, i, cl, fg: sig_fib(F, i, cl)),
    ("T-040", "RSI_DIVERGENZ", "rsi_divergence.py:67-90",
     lambda F, i, cl, fg: sig_rsi_div(F, i)),
    ("T-041", "MULTI_SIGNAL", "signal_agent.py:78-146",
     lambda F, i, cl, fg: sig_multi(F, i, fg)),
]


# ---------------------------------------------------------------- Rennen
def rennen(ks, zeiten, t0, preis, b, fenster_h):
    if preis <= 0:
        return "keine"
    i = bisect.bisect_right(zeiten, t0)
    j = min(i + fenster_h * 4, len(ks))       # 15m-Kerzen
    oben, unten = preis * (1 + b / 100), preis * (1 - b / 100)
    for x in range(i, j):
        if ks[x][3] <= unten:
            return "ab"
        if ks[x][2] >= oben:
            return "auf"
    return "keine"


def perz(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def bootstrap(aus, rnd):
    nach = {}
    for tag, w in aus:
        nach.setdefault(tag, []).append(w)
    tage = list(nach)
    qs = []
    for _ in range(BOOT):
        a = g = 0
        for _i in range(len(tage)):
            for w in nach[tage[rnd.randrange(len(tage))]]:
                a += w
                g += 1
        if g:
            qs.append(a / g * 100)
    return perz(qs, 0.025), perz(qs, 0.975), len(tage)


def main():
    print("=" * 104)
    print(" NACHTRAGSMESSUNG T-034..T-041 - tragen die blockierten")
    print(" Strategien einen Richtungsvorteil?  Seed", SEED)
    print(" KEINE Runde 3. Programm nach Regel 13 beendet.")
    print("=" * 104)

    ergebnis = []
    for jahr, marke in (("J2", ""), ("J1", "_v1")):
        daten, fg_tab = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        zt = {s: [k[0] for k in ks] for s, ks in idx.items()}
        # Features je Coin auf 1h
        feats, stunden = {}, {}
        for coin, ks15 in daten.items():
            k1h = F2.zu_1h(ks15)
            vol = F2.lade_volumen_1h(coin, marke)
            F, _cl = F2.features_je_coin(k1h, vol, fg_tab)
            feats[coin] = (F, k1h)
            stunden[coin] = [k[0] for k in k1h]
        print(f"\n  {jahr}: {len(daten)} Coins, "
              f"{len(next(iter(feats.values()))[1])} 1h-Balken je Coin")

        for tnr, name, quelle, fn in STRATEGIEN:
            events = []
            for coin, (F, k1h) in feats.items():
                fgs = F["fear_greed"]
                for i in range(210, len(k1h) - 1):
                    fg = fgs[i] if fgs[i] is not None else 50
                    try:
                        if fn(F, i, k1h[i][4], fg):
                            events.append((coin, k1h[i][0], k1h[i][4]))
                    except (TypeError, IndexError):
                        continue
            if not events:
                print(f"    {tnr} {name:<18s} KEINE SIGNALE")
                continue
            e_tage = {t // TAG_MS for _c, t, _p in events}
            for kbez, b, fh in KOMBIS:
                rnd = random.Random(SEED)
                auf = ab = keine = 0
                aus = []
                for s, t, p in events:
                    r = rennen(idx[s], zt[s], t, p, b, fh)
                    if r == "auf":
                        auf += 1
                        aus.append((t // TAG_MS, 1))
                    elif r == "ab":
                        ab += 1
                        aus.append((t // TAG_MS, 0))
                    else:
                        keine += 1
                n = auf + ab
                if n < 30:
                    print(f"    {tnr} {name:<18s} {kbez:<12s} "
                          f"n={n} < 30 -> INCONCLUSIVE")
                    continue
                q = auf / n * 100
                lo, hi, ntg = bootstrap(aus, rnd)
                # phasengleiches Placebo
                tag_idx = {}
                for coin, (F, k1h) in feats.items():
                    d = {}
                    for i, k in enumerate(k1h):
                        d.setdefault(k[0] // TAG_MS, []).append(i)
                    tag_idx[coin] = d
                pl = []
                for _z in range(ZIEH):
                    a2 = b2 = 0
                    for s, t, _p in events:
                        kand = tag_idx[s].get(t // TAG_MS)
                        if not kand:
                            continue
                        i2 = kand[rnd.randrange(len(kand))]
                        k1h = feats[s][1]
                        r = rennen(idx[s], zt[s], k1h[i2][0], k1h[i2][4], b, fh)
                        if r == "auf":
                            a2 += 1
                        elif r == "ab":
                            b2 += 1
                    if a2 + b2:
                        pl.append(a2 / (a2 + b2) * 100)
                p95 = perz(pl, 0.95)
                pm = sum(pl) / len(pl) if pl else 0.0
                # Kostenschwelle: gewichteter Mittelwert ueber die Coins
                cs = [K_BASIS.get(s.split("/")[0], 0.60) for s, _t, _p in events]
                c = sum(cs) / len(cs)
                p_be = (0.5 + c / (2 * b)) * 100
                ergebnis.append(dict(
                    trial=tnr, name=name, jahr=jahr, kombi=kbez, n=n,
                    q=q, lo=lo, hi=hi, plc=pm, p95=p95, p_be=p_be,
                    zens=keine / (n + keine) * 100, tage=len(e_tage),
                    sig=len(events)))
                print(f"    {tnr} {name:<18s} {kbez:<12s} n={n:5d} "
                      f"P(auf)={q:5.2f}% KI[{lo:5.2f};{hi:5.2f}] "
                      f"Plc={pm:5.2f} Schwelle={p_be:5.2f}% "
                      f"{'UEBER' if q > p_be else 'unter'}")
                sys.stdout.flush()

    # ---------------- Auswertung ----------------
    print("\n" + "=" * 104)
    print(" VORZEICHENSTABILITAET (P(auf) - 50 in beiden Jahren)")
    print("=" * 104)
    from collections import defaultdict
    nach = defaultdict(dict)
    for e in ergebnis:
        nach[(e["name"], e["kombi"])][e["jahr"]] = e["q"] - 50
    print(f"\n    {'Strategie':<18s} {'Kombi':<12s} {'J2':>8s} {'J1':>8s} {'stabil':>8s}")
    stabil = []
    for (nm, kb), v in sorted(nach.items()):
        if "J1" in v and "J2" in v:
            s = (v["J2"] > 0) == (v["J1"] > 0)
            if s:
                stabil.append((nm, kb))
            print(f"    {nm:<18s} {kb:<12s} {v['J2']:+7.2f} {v['J1']:+7.2f} "
                  f"{'JA' if s else 'nein':>8s}")

    print("\n" + "=" * 104)
    print(" BH-FDR ueber alle Tests (q=0,10)")
    print("=" * 104)
    # einseitiger p-Wert: Anteil Bootstrap-Ziehungen <= Schwelle, genaehert
    # ueber die Normalapproximation des KI
    import math
    for e in ergebnis:
        sd = (e["hi"] - e["lo"]) / 3.92 if e["hi"] > e["lo"] else 1.0
        z = (e["q"] - e["p_be"]) / sd if sd > 0 else 0.0
        e["p"] = 0.5 * math.erfc(z / math.sqrt(2))
    m = len(ergebnis)
    srt = sorted(ergebnis, key=lambda x: x["p"])
    kmax = 0
    for k, e in enumerate(srt, 1):
        if e["p"] <= k * 0.10 / m:
            kmax = k
    schwelle = srt[kmax - 1]["p"] if kmax else 0.0
    print(f"\n  m={m} Tests, Schwelle p <= {schwelle:.4f} (k={kmax})")
    print(f"  Zufallserwartung bei p<0,05 ohne Korrektur: {m*0.05:.1f} Treffer")
    print(f"\n    {'Trial':<7s} {'Strategie':<18s} {'Jahr':<4s} {'Kombi':<12s} "
          f"{'P(auf)':>7s} {'Schwelle':>8s} {'p roh':>8s} {'FDR':>5s}")
    print("    " + "-" * 82)
    treffer = []
    for e in srt[:14]:
        sig = kmax > 0 and e["p"] <= schwelle
        if sig:
            treffer.append(e)
        print(f"    {e['trial']:<7s} {e['name']:<18s} {e['jahr']:<4s} "
              f"{e['kombi']:<12s} {e['q']:6.2f}% {e['p_be']:7.2f}% "
              f"{e['p']:8.4f} {'JA' if sig else 'nein':>5s}")

    print("\n" + "=" * 104)
    print(" URTEIL")
    print("=" * 104)
    ueber = [e for e in ergebnis if e["q"] > e["p_be"]]
    ueber_ki = [e for e in ueber if e["lo"] > e["p_be"]]
    ueber_plc = [e for e in ueber_ki if e["q"] > e["p95"]]
    stab_namen = {nm for nm, _kb in stabil}
    final = [e for e in ueber_plc if e["name"] in stab_namen]
    print(f"\n  Tests gesamt:                              {len(ergebnis)}")
    print(f"  Punktschaetzer ueber Kostenschwelle:       {len(ueber)}")
    print(f"  davon KI-Untergrenze ueber Schwelle:       {len(ueber_ki)}")
    print(f"  davon Placebo geschlagen (>95. Perzentil): {len(ueber_plc)}")
    print(f"  davon vorzeichenstabil in beiden Jahren:   {len(final)}")
    print(f"  davon FDR-signifikant:                     "
          f"{len([e for e in final if kmax>0 and e['p']<=schwelle])}")
    if final:
        for e in final:
            print(f"    -> {e['trial']} {e['name']} {e['jahr']} {e['kombi']}")
    else:
        print("\n  KEINE Strategie erfuellt alle vier Bedingungen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
