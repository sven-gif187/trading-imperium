# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] NACHTRAGSMESSUNG T-034ff zum Multi-Strategy-Bug, 04.08.2026.
"""
messung_t034b_strategien.py - Neulauf von T-034..T-041.

WARUM EIN NEUES SKRIPT
----------------------
messung_t034_strategien.py (04.08. 00:49) lieferte 5 von 48 Zeilen und war
danach tot (kein Prozess, Ausgabe endet 01:51). Zwei Gruende, beide behoben:

  (1) LAUFZEIT. Das Placebo rief rennen() ZIEH(40) x len(events) mal auf,
      bei EMA_TREND also 40 x 40799 = 1,63 Mio Rennen je Barriere. Der
      Bootstrap iterierte 2000 x len(tage) x eintraege_je_tag ~ 80 Mio mal.
      Hochrechnung: mehrere Tage Laufzeit fuer 48 Zeilen.
      FIX ohne Methodikaenderung: rennen() haengt ausschliesslich von
      (coin, 1h-Index, Barriere, Fenster) ab - Signal- UND Placebopfad
      benutzen denselben Ausdruck rennen(idx[s], zt[s], k1h[i][0],
      k1h[i][4], b, fh). Das Ergebnis wird daher EINMAL je (coin, barriere)
      fuer alle 1h-Indizes vorberechnet; Signal und Placebo sind danach
      Tabellenzugriffe. Der Bootstrap summiert je Kalendertag vorab
      (Summe, Anzahl) statt Einzelwerte zu durchlaufen - arithmetisch
      identisch, gleiche Zahl und Reihenfolge von randrange()-Aufrufen,
      also bitgleiche RNG-Sequenz.
      VERIFIKATION: die 5 Zeilen des Altlaufs muessen exakt reproduziert
      werden. Siehe Abschnitt REGRESSION am Ende der Ausgabe.

  (2) KEIN ZWISCHENSTAND. Jetzt wird jede fertige Zeile sofort als
      JSON-Zeile nach ../ausgaben/messung_t034b_zwischenstand.jsonl
      geschrieben und beim Neustart uebersprungen.

DREI KORREKTUREN AN DEN SIGNALBEDINGUNGEN (Belege im Kopf jeder Funktion)
-------------------------------------------------------------------------
Der Altlauf wich an drei Stellen vom Projektcode ab. Alle drei sind hier
woertlich nachgezogen, keine ist erfunden:

  FIBONACCI_SUPPORT  Alt: nur das 61,8%-Level, und der zweite Oder-Zweig
                     war eine Kopie des ersten (tote Bedingung).
                     v4_strategies.py:176-190 hat DREI Zweige (78,6% +
                     RSI<40, 61,8%, 38,2% + MACD bullisch). Ausserdem
                     Fenster 100 Kerzen (df.tail(100)), nicht 120.
  MULTI_SIGNAL       Alt: EMA-Punkt bei price>ema20 UND price>ema50.
                     signal_agent.py:97 verlangt price > ema20 > ema50.
  RSI_DIVERGENZ      Alt: letztes Swing-Tief gegen ALLE frueheren, ohne
                     Mindestabstand. rsi_divergence.py:105-115 vergleicht
                     AUFEINANDERFOLGENDE Paare und verlangt
                     price2 < price1*(1-min_swing_pct/100) mit
                     min_swing_pct=1.0 (:17) sowie rsi2 > rsi1+2 (:80).

RSI_OVERSOLD und EMA_TREND sind unveraendert - die 5 Altzeilen bleiben
damit gueltig und dienen als Regressionstest.

BEKANNTER MANGEL, NICHT BEHOBEN: LOOK-AHEAD VON 45 MINUTEN
----------------------------------------------------------
zu_1h() (messung_f2_ic.py:57-70) vergibt als Zeitstempel den STUNDENBEGINN
H, als Preis aber den Close am STUNDENENDE H+60min. rennen() startet bei
bisect_right(zeiten, H), also bei H+15min. Die Viertelstunden H+15, H+30,
H+45 werden mitgerennt, obwohl der Signalpreis dort noch nicht bekannt ist.
Das betrifft E2 und G2 gleichermassen. Der Hauptlauf behaelt die Konvention,
damit die Zahlen mit E2/G2 vergleichbar bleiben. Zusaetzlich wird je
Strategie und Barriere eine SENSITIVITAET mit Start bei H+60min gerechnet
(Punktschaetzer, ohne Bootstrap/Placebo) und getrennt ausgewiesen. Sie
geht NICHT in die BH-FDR-Korrektur ein - sonst waeren es Doppeltests.

TEST: Barrieren +/-2,5%/72h, +/-5%/7d, +/-7%/14d, First-Touch pessimistisch
(Tief vor Hoch innerhalb derselben Kerze), beide Jahre getrennt,
phasengleiches Placebo (40 Ziehungen, nur Uhrzeit innerhalb der real
signalisierten Kalendertage randomisiert), Block-Bootstrap 2000 ueber
Kalendertage, Seed 20260730. Kostenschwelle coinweise aus
12_SPREAD-MESSUNG.md, p_be = 0,5 + c/(2B).
"""
import bisect
import json
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_ext import lade_jahr, TAG_MS
import messung_f2_ic as F2

SEED = 20260730
BOOT = 2000
ZIEH = 40
STUNDE = 3_600_000
START = 210                 # Warmlauf, wie im Altlauf
KOMBIS = [("+/-2,5%/72h", 2.5, 72), ("+/-5%/7d", 5.0, 168),
          ("+/-7%/14d", 7.0, 336)]
K_BASIS = {"BTC": 0.50, "ETH": 0.50, "SOL": 0.51, "DOGE": 0.51,
           "ADA": 0.56, "XRP": 0.57, "LINK": 0.62, "AVAX": 0.62,
           "UNI": 0.67, "NEAR": 0.68, "ATOM": 1.07, "DOT": 1.15}

AUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "ausgaben")
ZWISCHEN = os.path.join(AUS, "messung_t034b_zwischenstand.jsonl")


# ======================================================== Signalbedingungen
def sig_rsi_oversold(F, i, X):
    """v4_strategies.py:88-96 _rsi_oversold. UNVERAENDERT ggue. Altlauf."""
    r, a = F["rsi_14"][i], F["adx_14"][i]
    if r is None or a is None:
        return False
    return r < 30 or r < 35 or (r < 45 and a < 25) or (r < 48 and a < 20)


def sig_ema_trend(F, i, X):
    """v4_strategies.py:102-111 _ema_trend. UNVERAENDERT ggue. Altlauf.
    price>ema20>ema50 and adx>20   ODER   price>ema50."""
    e20, e50, a = F["p_vs_ema20"][i], F["p_vs_ema50"][i], F["adx_14"][i]
    if e20 is None or e50 is None or a is None:
        return False
    e2050 = F["ema20_vs_50"][i]
    return ((e20 > 0 and e50 > 0 and e2050 is not None and e2050 > 0
             and a > 20) or e50 > 0)


def sig_macd_cross(F, i, X):
    """v4_strategies.py:113-125 _macd_cross. macd_hist>0 ist aequivalent zu
    MACD>MACD_signal (macd_hist = (MACD-Signal)/Close, f2_ic.py:474)."""
    h, hp, a = F["macd_hist"][i], F["macd_hist"][i - 1], F["adx_14"][i]
    if h is None or hp is None or a is None:
        return False
    return (h > 0 and hp <= 0) or (h > 0 and a > 20)


def sig_tsi(F, i, X):
    """v4_strategies.py:161-171 _tsi_signal. tsi_hist = TSI - TSI_signal."""
    t, th, thp = F["tsi"][i], F["tsi_hist"][i], F["tsi_hist"][i - 1]
    if t is None or th is None or thp is None:
        return False
    return (th > 0 and thp <= 0 and t < 10) or (th > 0 and t > 0)


def sig_bollinger(F, i, X):
    """signal_agent.py:110-115. price < BBL und RSI < 40.
    bb_pos = (c-BBL)/(BBU-BBL) < 0  <=>  price < BBL (f2_ic.py:486)."""
    b, r = F["bb_pos"][i], F["rsi_14"][i]
    if b is None or r is None:
        return False
    return b < 0 and r < 40


def sig_fib(F, i, X):
    """v4_strategies.py:176-190 _fibonacci_support, KORRIGIERT.
    Drei Zweige, Fenster 100 Kerzen (calc_fibonacci_levels, :44-45)."""
    d786, d618, d382 = X["fib786"][i], X["fib618"][i], X["fib382"][i]
    if d618 is None:
        return False
    r, h = F["rsi_14"][i], F["macd_hist"][i]
    if d786 is not None and abs(d786) < 0.005 and r is not None and r < 40:
        return True
    if abs(d618) < 0.005:
        return True
    if d382 is not None and abs(d382) < 0.005 and h is not None and h > 0:
        return True
    return False


def sig_rsi_div(F, i, X):
    """rsi_divergence.py:67-90 + :105-115, KORRIGIERT (siehe Kopf)."""
    return X["div"][i] > 0


def sig_multi(F, i, X):
    """signal_agent.py:78-146, Score >= min_score 3 (:169-170), KORRIGIERT
    beim EMA-Punkt (:97 verlangt price > ema20 > ema50).
    Nur die aus Kerzendaten rekonstruierbaren Komponenten - Ensemble,
    Orderbuch, VWAP-Bias und V4-Bridge (:131-160) fehlen und wuerden den
    Score ausschliesslich ERHOEHEN. Der Test ist damit konservativ."""
    r, a = F["rsi_14"][i], F["adx_14"][i]
    if r is None:
        return False
    s = 0
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
    e20, e50, e2050 = (F["p_vs_ema20"][i], F["p_vs_ema50"][i],
                       F["ema20_vs_50"][i])
    if (e20 is not None and e50 is not None and e2050 is not None
            and e20 > 0 and e50 > 0 and e2050 > 0):
        s += 1
    if a is not None and a > 25:
        s += 1
    fg = X["fg"][i]
    if fg < 15:
        s += 3
    elif fg < 25:
        s += 2
    elif fg < 35:
        s += 1
    b = F["bb_pos"][i]
    if b is not None and b < 0 and r < 40:
        s += 2
    if X["div"][i] > 0:
        s += 2
    vr = F["vol_ratio_20"][i]
    if vr is not None and vr > 2 and r < 60:
        s += 1
    return s >= 3


STRATEGIEN = [
    ("T-034", "RSI_OVERSOLD", "v4_strategies.py:88-96", sig_rsi_oversold),
    ("T-035", "EMA_TREND", "v4_strategies.py:102-111", sig_ema_trend),
    ("T-036", "MACD_CROSS", "v4_strategies.py:113-125", sig_macd_cross),
    ("T-037", "TSI", "v4_strategies.py:161-171", sig_tsi),
    ("T-038", "BOLLINGER_BOUNCE", "signal_agent.py:110-115", sig_bollinger),
    ("T-039", "FIBONACCI_SUPPORT", "v4_strategies.py:176-190", sig_fib),
    ("T-040", "RSI_DIVERGENZ", "rsi_divergence.py:67-90", sig_rsi_div),
    ("T-041", "MULTI_SIGNAL", "signal_agent.py:78-146", sig_multi),
]

# Signalfamilien fuer 1.7: mehrere Varianten desselben Rohindikators sind
# KEINE unabhaengige Bestaetigung.
FAMILIE = {
    "RSI_OVERSOLD": "RSI", "RSI_DIVERGENZ": "RSI", "BOLLINGER_BOUNCE": "RSI",
    "MULTI_SIGNAL": "RSI", "EMA_TREND": "TREND", "MACD_CROSS": "TREND",
    "TSI": "TREND", "FIBONACCI_SUPPORT": "PREIS",
}


# ============================================================ Zusatzfeatures
def fib_distanzen(k1h, cl, fenster=100):
    """calc_fibonacci_levels (v4_strategies.py:41-54) je Balken.
    high = max(High) und low = min(Low) der letzten <fenster> Kerzen
    INKLUSIVE der aktuellen - genau wie df.tail(100)."""
    hi = [k[2] for k in k1h]
    lo = [k[3] for k in k1h]
    hmax = F2.rollend_max(hi, fenster)
    lmin = F2.rollend_min(lo, fenster)
    m = len(cl)
    out = {"fib786": [None] * m, "fib618": [None] * m, "fib382": [None] * m}
    for i in range(m):
        if hmax[i] is None or lmin[i] is None or i < 19:   # len(df)<20 -> Fallback
            continue
        c = cl[i]
        n = max(c, 1e-9)
        d = hmax[i] - lmin[i]
        out["fib786"][i] = (c - (hmax[i] - d * 0.786)) / n
        out["fib618"][i] = (c - (hmax[i] - d * 0.618)) / n
        out["fib382"][i] = (c - (hmax[i] - d * 0.382)) / n
    return out


def divergenz_projekttreu(cl, rsiw, lookback=30, fenster=5, min_swing=1.0):
    """rsi_divergence.py: _find_swing_lows(:120-126) + _check_bullish
    (:105-115). Swing-Tief erst <fenster> Balken spaeter bestaetigt -
    kein Look-ahead."""
    m = len(cl)
    out = [0.0] * m
    tiefs = []
    for i in range(fenster, m - fenster):
        f = cl[i]
        if f == min(cl[i - fenster:i + fenster + 1]) and rsiw[i] is not None:
            tiefs.append((i, f, rsiw[i]))
    zeiger, aktiv = 0, []
    for t in range(m):
        while zeiger < len(tiefs) and tiefs[zeiger][0] + fenster <= t:
            aktiv.append(tiefs[zeiger])
            zeiger += 1
        rel = [x for x in aktiv if x[0] > t - lookback]
        for j in range(len(rel) - 1):
            _i1, p1, r1 = rel[j]
            _i2, p2, r2 = rel[j + 1]
            if p2 < p1 * (1 - min_swing / 100.0) and r2 > r1 + 2:
                out[t] = 1.0
                break
    return out


# ================================================================= Rennen
def tabelle(hi15, lo15, zeiten, k1h, b, fenster_h, versatz=0):
    """First-Touch je 1h-Index. 1=auf, 0=ab, -1=keine.
    versatz=0 reproduziert rennen() aus dem Altlauf bitgenau.
    versatz=STUNDE-1 startet erst am Stundenende (Look-ahead-Sensitivitaet)."""
    n15 = len(zeiten)
    out = [-1] * len(k1h)
    for i in range(len(k1h)):
        preis = k1h[i][4]
        if preis <= 0:
            continue
        s = bisect.bisect_right(zeiten, k1h[i][0] + versatz)
        e = s + fenster_h * 4
        if e > n15:
            e = n15
        oben = preis * (1 + b / 100.0)
        unten = preis * (1 - b / 100.0)
        r = -1
        for x in range(s, e):
            if lo15[x] <= unten:
                r = 0
                break
            if hi15[x] >= oben:
                r = 1
                break
        out[i] = r
    return out


def perz(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def bootstrap(aus, rnd):
    """Block-Bootstrap ueber Kalendertage. Arithmetisch identisch zum
    Altlauf, aber je Tag vorsummiert; gleiche RNG-Sequenz."""
    summe, anzahl = {}, {}
    for tag, w in aus:
        summe[tag] = summe.get(tag, 0) + w
        anzahl[tag] = anzahl.get(tag, 0) + 1
    tage = list(summe)
    nt = len(tage)
    rr = rnd.randrange
    qs = []
    for _ in range(BOOT):
        a = g = 0
        for _i in range(nt):
            d = tage[rr(nt)]
            a += summe[d]
            g += anzahl[d]
        if g:
            qs.append(a / g * 100)
    return perz(qs, 0.025), perz(qs, 0.975), nt


# ================================================================== Lauf
def lade_zwischenstand():
    fertig = {}
    if os.path.exists(ZWISCHEN):
        with open(ZWISCHEN, encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    e = json.loads(zeile)
                except ValueError:
                    continue
                fertig[(e["name"], e["jahr"], e["kombi"])] = e
    return fertig


def persistiere(e):
    with open(ZWISCHEN, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.flush()


def baue_jahr(marke):
    daten, fg_tab = lade_jahr(marke)
    idx = {s: sorted(ks) for s, ks in daten.items()}
    paket = {}
    for coin in daten:                      # Reihenfolge wie im Altlauf
        ks = idx[coin]
        k1h = F2.zu_1h(daten[coin])
        vol = F2.lade_volumen_1h(coin, marke)
        F, cl = F2.features_je_coin(k1h, vol, fg_tab)
        X = fib_distanzen(k1h, cl)
        X["div"] = divergenz_projekttreu(cl, F["rsi_14"])
        X["fg"] = [x if x is not None else 50 for x in F["fear_greed"]]
        paket[coin] = dict(
            F=F, X=X, k1h=k1h,
            zeiten=[k[0] for k in ks],
            hi15=[k[2] for k in ks], lo15=[k[3] for k in ks])
    return paket


def main():
    ausgabe = []

    def p(*a):
        z = " ".join(str(x) for x in a)
        print(z)
        sys.stdout.flush()
        ausgabe.append(z)

    p("=" * 104)
    p(" NACHTRAGSMESSUNG T-034..T-041 (Neulauf b) - tragen die blockierten")
    p(" Strategien einen Richtungsvorteil?  Seed", SEED)
    p(" KEINE Runde 3. Programm nach Regel 13 beendet.")
    p("=" * 104)

    fertig = lade_zwischenstand()
    if fertig:
        p(f"\n  Zwischenstand: {len(fertig)} Zeilen bereits gerechnet, "
          f"werden uebersprungen.")
    ergebnis = list(fertig.values())
    konfluenz = {}

    for jahr, marke in (("J2", ""), ("J1", "_v1")):
        offen = [(t, n, q, f) for t, n, q, f in STRATEGIEN
                 if any((n, jahr, kb) not in fertig for kb, _b, _f in KOMBIS)]
        if not offen:
            p(f"\n  {jahr}: vollstaendig aus Zwischenstand.")
            continue
        paket = baue_jahr(marke)
        n1h = len(next(iter(paket.values()))["k1h"])
        p(f"\n  {jahr}: {len(paket)} Coins, {n1h} 1h-Balken je Coin")

        # --- First-Touch-Tabellen: einmal je (Barriere, Coin) ---
        TAB, TAB_LA = {}, {}
        for kbez, b, fh in KOMBIS:
            TAB[kbez] = {}
            TAB_LA[kbez] = {}
            for coin, d in paket.items():
                TAB[kbez][coin] = tabelle(d["hi15"], d["lo15"], d["zeiten"],
                                          d["k1h"], b, fh, 0)
                TAB_LA[kbez][coin] = tabelle(d["hi15"], d["lo15"], d["zeiten"],
                                             d["k1h"], b, fh, STUNDE - 1)
            p(f"    Tabelle {kbez:<12s} fertig")

        # --- Tagesindex fuer das phasengleiche Placebo ---
        tag_idx = {}
        for coin, d in paket.items():
            dd = {}
            for i, k in enumerate(d["k1h"]):
                dd.setdefault(k[0] // TAG_MS, []).append(i)
            tag_idx[coin] = dd

        # --- Signale je Strategie ---
        sig_idx = {}
        for tnr, name, _quelle, fn in STRATEGIEN:
            events = []
            for coin, d in paket.items():
                F, X, k1h = d["F"], d["X"], d["k1h"]
                for i in range(START, len(k1h) - 1):
                    try:
                        if fn(F, i, X):
                            events.append((coin, i))
                    except (TypeError, IndexError):
                        continue
            sig_idx[name] = events
            if not events:
                p(f"    {tnr} {name:<18s} KEINE SIGNALE")

        konfluenz[jahr] = _konfluenz(paket, sig_idx, TAB, p, jahr)

        # --- Auswertung je Strategie x Barriere ---
        for tnr, name, _quelle, _fn in STRATEGIEN:
            events = sig_idx[name]
            if not events:
                continue
            for kbez, b, fh in KOMBIS:
                if (name, jahr, kbez) in fertig:
                    continue
                rnd = random.Random(SEED)
                auf = ab = keine = 0
                aus = []
                for coin, i in events:
                    r = TAB[kbez][coin][i]
                    t_tag = paket[coin]["k1h"][i][0] // TAG_MS
                    if r == 1:
                        auf += 1
                        aus.append((t_tag, 1))
                    elif r == 0:
                        ab += 1
                        aus.append((t_tag, 0))
                    else:
                        keine += 1
                n = auf + ab
                if n < 30:
                    p(f"    {tnr} {name:<18s} {kbez:<12s} n={n} < 30 "
                      f"-> INCONCLUSIVE")
                    continue
                q = auf / n * 100
                lo, hi, ntg = bootstrap(aus, rnd)
                # phasengleiches Placebo - gleiche Reihenfolge wie Altlauf
                pl = []
                for _z in range(ZIEH):
                    a2 = b2 = 0
                    for coin, i in events:
                        kand = tag_idx[coin].get(
                            paket[coin]["k1h"][i][0] // TAG_MS)
                        if not kand:
                            continue
                        i2 = kand[rnd.randrange(len(kand))]
                        r = TAB[kbez][coin][i2]
                        if r == 1:
                            a2 += 1
                        elif r == 0:
                            b2 += 1
                    if a2 + b2:
                        pl.append(a2 / (a2 + b2) * 100)
                p95 = perz(pl, 0.95)
                pm = sum(pl) / len(pl) if pl else 0.0
                # Look-ahead-Sensitivitaet, nur Punktschaetzer
                a3 = b3 = 0
                for coin, i in events:
                    r = TAB_LA[kbez][coin][i]
                    if r == 1:
                        a3 += 1
                    elif r == 0:
                        b3 += 1
                q_la = a3 / (a3 + b3) * 100 if a3 + b3 else 0.0
                cs = [K_BASIS.get(c.split("/")[0], 0.60) for c, _i in events]
                c = sum(cs) / len(cs)
                p_be = (0.5 + c / (2 * b)) * 100
                e = dict(trial=tnr, name=name, jahr=jahr, kombi=kbez, n=n,
                         q=q, lo=lo, hi=hi, plc=pm, p95=p95, p_be=p_be,
                         q_la=q_la, n_la=a3 + b3,
                         zens=keine / (n + keine) * 100, tage=ntg,
                         sig=len(events))
                ergebnis.append(e)
                persistiere(e)
                p(f"    {tnr} {name:<18s} {kbez:<12s} n={n:5d} "
                  f"P(auf)={q:5.2f}% KI[{lo:5.2f};{hi:5.2f}] "
                  f"Plc={pm:5.2f} Schwelle={p_be:5.2f}% "
                  f"{'UEBER' if q > p_be else 'unter'}  "
                  f"[oL {q_la:5.2f}%]")

    _auswertung(ergebnis, konfluenz, p)
    with open(os.path.join(AUS, "messung_t034b_strategien_out.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(ausgabe) + "\n")
    return 0


# ============================================================== Konfluenz
def _konfluenz(paket, sig_idx, TAB, p, jahr):
    """1.7 rein deskriptiv. Keine Gewichtung, keine Schwellensuche."""
    p("\n  " + "-" * 100)
    p(f"  KONFLUENZ {jahr} - deskriptiv, keine Optimierung")
    p("  " + "-" * 100)
    namen = [n for _t, n, _q, _f in STRATEGIEN if sig_idx.get(n)]
    mengen = {n: set(sig_idx[n]) for n in namen}
    # paarweise Ueberlappung (Jaccard) - Unabhaengigkeit belegen statt annehmen
    p(f"    Paarweise Jaccard-Ueberlappung der Signalmengen "
      f"(gleicher Coin, gleiche Stunde):")
    p(f"      {'Paar':<42s} {'Jaccard':>8s} {'Familie':>10s}")
    for a in range(len(namen)):
        for b in range(a + 1, len(namen)):
            na, nb = namen[a], namen[b]
            sa, sb = mengen[na], mengen[nb]
            j = len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0
            if j >= 0.20:
                gl = "GLEICH" if FAMILIE[na] == FAMILIE[nb] else "getrennt"
                p(f"      {na + ' / ' + nb:<42s} {j:8.3f} {gl:>10s}")
    # Wieviele Strategien feuern gleichzeitig?
    zaehler = defaultdict(int)
    fam_zaehler = defaultdict(int)
    alle = set()
    for n in namen:
        alle |= mengen[n]
    for schluessel in alle:
        k = sum(1 for n in namen if schluessel in mengen[n])
        zaehler[k] += 1
        fam = {FAMILIE[n] for n in namen if schluessel in mengen[n]}
        fam_zaehler[len(fam)] += 1
    p(f"\n    Zeitpunkte mit mindestens einem Signal: {len(alle)}")
    p(f"      {'k Strategien':<14s} {'Zeitpunkte':>12s} {'Anteil':>8s} "
      f"{'k Familien':>12s} {'Zeitpunkte':>12s}")
    for k in sorted(zaehler):
        p(f"      {k:<14d} {zaehler[k]:12d} {zaehler[k]/len(alle)*100:7.2f}% "
          f"{k if k in fam_zaehler else '':>12} "
          f"{fam_zaehler.get(k, 0):12d}")
    # Traegt Uebereinstimmung mehr als das staerkste Einzelsignal?
    p(f"\n    P(auf) nach Zahl gleichzeitig feuernder UNABHAENGIGER Familien")
    p(f"      (Barriere +/-2,5%/72h; RSI-Familie zaehlt einmal, "
      f"TREND-Familie einmal, PREIS einmal)")
    p(f"      {'Familien':<10s} {'n':>8s} {'P(auf)':>8s}")
    kb = KOMBIS[0][0]
    nach_fam = defaultdict(lambda: [0, 0])
    for schluessel in alle:
        coin, i = schluessel
        fam = {FAMILIE[n] for n in namen if schluessel in mengen[n]}
        r = TAB[kb][coin][i]
        if r < 0:
            continue
        nach_fam[len(fam)][0] += r
        nach_fam[len(fam)][1] += 1
    for k in sorted(nach_fam):
        a, g = nach_fam[k]
        p(f"      {k:<10d} {g:8d} {a/g*100:7.2f}%" if g else "")
    return {"paare": {f"{a}|{b}": len(mengen[a] & mengen[b])
                      for a in namen for b in namen if a < b},
            "familien": {str(k): list(v) for k, v in nach_fam.items()}}


# ============================================================== Auswertung
def _auswertung(ergebnis, konfluenz, p):
    p("\n" + "=" * 104)
    p(" VORZEICHENSTABILITAET (P(auf) - 50 in beiden Jahren)")
    p("=" * 104)
    nach = defaultdict(dict)
    for e in ergebnis:
        nach[(e["name"], e["kombi"])][e["jahr"]] = e["q"] - 50
    p(f"\n    {'Strategie':<18s} {'Kombi':<12s} {'J2':>8s} {'J1':>8s} "
      f"{'stabil':>8s}")
    stabil = []
    for (nm, kb), v in sorted(nach.items()):
        if "J1" in v and "J2" in v:
            s = (v["J2"] > 0) == (v["J1"] > 0)
            if s:
                stabil.append((nm, kb))
            p(f"    {nm:<18s} {kb:<12s} {v['J2']:+7.2f} {v['J1']:+7.2f} "
              f"{'JA' if s else 'nein':>8s}")

    p("\n" + "=" * 104)
    p(" BH-FDR ueber alle Tests (q=0,10), einseitig H0: P(auf) <= Schwelle")
    p("=" * 104)
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
    p(f"\n  m={m} Tests, BH-Schwelle p <= {schwelle:.4f} (k={kmax})")
    p(f"  Zufallserwartung bei p<0,05 OHNE Korrektur: {m*0.05:.1f} Treffer")
    p(f"  Zufallserwartung bei p<0,10 OHNE Korrektur: {m*0.10:.1f} Treffer")
    p(f"\n    {'Trial':<7s} {'Strategie':<18s} {'Jahr':<4s} {'Kombi':<12s} "
      f"{'P(auf)':>7s} {'Schwelle':>9s} {'Abstand':>8s} {'p roh':>8s} "
      f"{'FDR':>5s}")
    p("    " + "-" * 92)
    for e in srt:
        sig = kmax > 0 and e["p"] <= schwelle
        p(f"    {e['trial']:<7s} {e['name']:<18s} {e['jahr']:<4s} "
          f"{e['kombi']:<12s} {e['q']:6.2f}% {e['p_be']:8.2f}% "
          f"{e['q']-e['p_be']:+7.2f}pp {e['p']:8.4f} "
          f"{'JA' if sig else 'nein':>5s}")

    p("\n" + "=" * 104)
    p(" LOOK-AHEAD-SENSITIVITAET (Start erst am Stundenende, +45 min)")
    p("=" * 104)
    p(f"\n    {'Strategie':<18s} {'Jahr':<4s} {'Kombi':<12s} "
      f"{'P(auf)':>8s} {'ohne LA':>8s} {'Delta':>8s}")
    dmax = 0.0
    for e in sorted(ergebnis, key=lambda x: (x["name"], x["jahr"],
                                             x["kombi"])):
        d = e["q_la"] - e["q"]
        dmax = max(dmax, abs(d))
        p(f"    {e['name']:<18s} {e['jahr']:<4s} {e['kombi']:<12s} "
          f"{e['q']:7.2f}% {e['q_la']:7.2f}% {d:+7.2f}pp")
    p(f"\n  Groesster Betrag der Verzerrung: {dmax:.2f} pp")

    p("\n" + "=" * 104)
    p(" URTEILSTABELLE JE STRATEGIE (1.8)")
    p("=" * 104)
    stab_namen = {nm for nm, _kb in stabil}
    p(f"\n    {'Strategie':<18s} {'beste Luecke':>13s} {'Kombi/Jahr':<22s} "
      f"{'Placebo':>9s} {'stabil':>7s} {'Urteil':<16s}")
    urteile = {}
    for _t, name, _q, _f in STRATEGIEN:
        es = [e for e in ergebnis if e["name"] == name]
        if not es:
            urteile[name] = "NICHT TESTBAR"
            p(f"    {name:<18s} {'-':>13s} {'-':<22s} {'-':>9s} {'-':>7s} "
              f"{'NICHT TESTBAR':<16s}")
            continue
        best = max(es, key=lambda x: x["q"] - x["p_be"])
        luecke = best["q"] - best["p_be"]
        vier = (luecke > 0 and best["lo"] > best["p_be"]
                and best["q"] > best["p95"] and name in stab_namen)
        urteil = "TRAEGT" if vier else "TRAEGT NICHT"
        urteile[name] = urteil
        p(f"    {name:<18s} {luecke:+12.2f}pp "
          f"{best['kombi'] + ' / ' + best['jahr']:<22s} "
          f"{best['q']-best['plc']:+8.2f}pp "
          f"{'JA' if name in stab_namen else 'nein':>7s} {urteil:<16s}")
    for name in ("ICHIMOKU", "MOMENTUM_BREAKOUT", "STOCHRSI_REVERSAL"):
        p(f"    {name:<18s} {'-':>13s} {'-':<22s} {'-':>9s} {'-':>7s} "
          f"{'NICHT TESTBAR':<16s}")

    p("\n" + "=" * 104)
    p(" URTEIL 1.9 - vier Bedingungen, alle vier")
    p("=" * 104)
    ueber = [e for e in ergebnis if e["q"] > e["p_be"]]
    ueber_ki = [e for e in ueber if e["lo"] > e["p_be"]]
    ueber_plc = [e for e in ueber_ki if e["q"] > e["p95"]]
    final = [e for e in ueber_plc if e["name"] in stab_namen]
    p(f"\n  Tests gesamt:                              {len(ergebnis)}")
    p(f"  1) Punktschaetzer ueber Kostenschwelle:    {len(ueber)}")
    p(f"  2) davon KI-Untergrenze ueber Schwelle:    {len(ueber_ki)}")
    p(f"  3) davon Placebo geschlagen (>95. Perz.):  {len(ueber_plc)}")
    p(f"  4) davon vorzeichenstabil in beiden Jahren:{len(final)}")
    p(f"  davon FDR-signifikant:                     "
      f"{len([e for e in final if kmax > 0 and e['p'] <= schwelle])}")
    if ergebnis:
        beste = max(ergebnis, key=lambda x: x["q"] - x["p_be"])
        p(f"\n  Kleinste gemessene Luecke zur Kostenschwelle: "
          f"{beste['p_be']-beste['q']:.2f} pp "
          f"({beste['name']} {beste['jahr']} {beste['kombi']}: "
          f"{beste['q']:.2f}% gegen {beste['p_be']:.2f}%)")
        naeh = max(ergebnis, key=lambda x: x["hi"] - x["p_be"])
        p(f"  Naechste KI-Obergrenze an ihrer Schwelle:    "
          f"{naeh['p_be']-naeh['hi']:.2f} pp "
          f"({naeh['name']} {naeh['jahr']} {naeh['kombi']})")
    if final:
        p("\n  ARCHITEKTURREPARATUR: JA")
        for e in final:
            p(f"    -> {e['trial']} {e['name']} {e['jahr']} {e['kombi']}")
    else:
        p("\n  KEINE Strategie erfuellt alle vier Bedingungen.")
        p("  ARCHITEKTURREPARATUR ZUM FREILEGEN DIESER STRATEGIEN: NEIN")

    p("\n" + "=" * 104)
    p(" REGRESSION gegen den Altlauf (messung_t034_strategien_out.txt)")
    p("=" * 104)
    alt = [("RSI_OVERSOLD", "J2", "+/-2,5%/72h", 20129, 49.09, 45.19, 52.96,
            37.07, 63.51),
           ("RSI_OVERSOLD", "J2", "+/-5%/7d", 19079, 46.05, 41.09, 51.15,
            37.40, 56.76),
           ("RSI_OVERSOLD", "J2", "+/-7%/14d", 19004, 46.15, 40.84, 51.58,
            40.04, 54.83),
           ("EMA_TREND", "J2", "+/-2,5%/72h", 40799, 46.28, 42.75, 49.83,
            54.43, 63.26),
           ("EMA_TREND", "J2", "+/-5%/7d", 38489, 45.27, 41.02, 49.90,
            50.78, 56.63)]
    ok = fehl = 0
    for nm, jr, kb, n0, q0, lo0, hi0, pl0, be0 in alt:
        tr = [e for e in ergebnis if e["name"] == nm and e["jahr"] == jr
              and e["kombi"] == kb]
        if not tr:
            p(f"    {nm:<18s} {kb:<12s} nicht im Ergebnis")
            fehl += 1
            continue
        e = tr[0]
        d = (e["n"] == n0 and abs(e["q"] - q0) < 0.005
             and abs(e["lo"] - lo0) < 0.005 and abs(e["hi"] - hi0) < 0.005
             and abs(e["plc"] - pl0) < 0.005
             and abs(e["p_be"] - be0) < 0.005)
        ok += d
        fehl += (not d)
        p(f"    {nm:<18s} {kb:<12s} n {e['n']}/{n0} q {e['q']:.2f}/{q0} "
          f"KI[{e['lo']:.2f};{e['hi']:.2f}]/[{lo0};{hi0}] "
          f"Plc {e['plc']:.2f}/{pl0} -> "
          f"{'BITGLEICH' if d else 'ABWEICHUNG'}")
    p(f"\n  {ok} von {len(alt)} Altzeilen bitgleich reproduziert, "
      f"{fehl} Abweichungen.")
    return urteile


if __name__ == "__main__":
    sys.exit(main())
