# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit F2 vom 30.07.2026.
# Nicht archivieren - Beleg fuer den Feature-Screen. Siehe ../README.md
"""
F2 - Traegt eines der vorhandenen Features ueberhaupt Information?

a) Inventar: welche Features berechnet das System, welche sind aus den
   Backtest-Daten rekonstruierbar, welche nur live verfuegbar.
b) Spearman-Rangkorrelation (Information Coefficient) gegen die
   Forward-Rendite ueber 1 h / 4 h / 24 h, je Coin und gepoolt,
   beide Jahre GETRENNT.
c) Benjamini-Hochberg-FDR ueber die gesamte Testfamilie.
d) Stabilitaet: gleiches Vorzeichen in BEIDEN Jahren?
e) Oekonomische Schwelle: welcher IC waere noetig, damit ein Feature die
   Reibung traegt.

ZEITBASIS
---------
Der Bot rechnet auf 1h-Kerzen (config.json trading.default_timeframe = "1h")
mit einem Fenster von 120 Balken (candle_limit = 120). Alle Features werden
hier auf aus den 15m-Kerzen aggregierten 1h-Balken berechnet, mit Fenstern
<= 120 - damit sind sie mit dem, was der Bot live sieht, vergleichbar.
Indikatoren, die mehr als 120 Balken brauchen (EMA200), kann der Bot
strukturell nicht berechnen und werden als nicht pruefbar gefuehrt.

KEIN LOOK-AHEAD
---------------
Jedes Feature zum Balken t verwendet ausschliesslich Balken <= t.
Die Forward-Rendite ist Close(t+h)/Close(t) - 1, also strikt danach.

WARUM DIE ROHEN p-WERTE NICHTS TAUGEN
-------------------------------------
Bei h > 1 ueberlappen sich benachbarte Forward-Renditen; zusaetzlich sind
die 11 Coins mit rho = 0,72-0,75 gekoppelt (E5, Befund 16: N_eff = 1,23-1,42).
Ein t-Test auf n = 11 x 8760 Beobachtungen behauptet eine Praezision, die
die Daten nicht haben. Ausgegeben werden daher BEIDE Varianten:
  p_roh  - naiv auf allen Beobachtungen (wie beauftragt)
  p_eff  - auf n_eff = (Balken/h) x N_eff, N_eff = 1,3 aus E5
BH-FDR laeuft ueber beide Familien getrennt.
"""
import sys
import math

from harness_ext import lade_jahr, COINS, STUNDE_MS, TAG_MS
from messung_f_stat import (spearman, rho_p, bh_fdr, median, mittel,
                            ic_zu_trefferquote, trefferquote_zu_ic)

FENSTER = 120          # candle_limit aus config.json
N_EFF_COINS = 1.3      # E5, Befund 16 (gemessen 1,23-1,42)
REIBUNG = 0.30         # % je Runde
HORIZONTE = [("1 h", 1), ("4 h", 4), ("24 h", 24)]


# ===========================================================================
# 15m -> 1h
# ===========================================================================
def zu_1h(kerzen15):
    """[(t, o, h, l, c, v)] auf volle Stunden. Volumen fehlt in lade_kerzen,
    wird daher separat gelesen - hier nur OHLC + Zeit."""
    stunden = {}
    for t, o, hi, lo, cl in kerzen15:
        H = (t // STUNDE_MS) * STUNDE_MS
        s = stunden.get(H)
        if s is None:
            stunden[H] = [o, hi, lo, cl]
        else:
            s[1] = max(s[1], hi)
            s[2] = min(s[2], lo)
            s[3] = cl
    return [(H, o, hi, lo, cl) for H, (o, hi, lo, cl) in sorted(stunden.items())]


def lade_volumen_1h(symbol, marke):
    """Volumen je Stunde direkt aus der CSV (lade_kerzen laesst es weg)."""
    import csv
    import os
    from harness_ext import PROJEKT
    p = os.path.join(PROJEKT, "data_store", "backtest",
                     symbol.replace("/", "") + f"_15m{marke}.csv")
    vol = {}
    if not os.path.exists(p):
        return vol
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                H = (int(r["zeit"]) // STUNDE_MS) * STUNDE_MS
                vol[H] = vol.get(H, 0.0) + float(r["volume"])
            except (KeyError, TypeError, ValueError):
                continue
    return vol


# ===========================================================================
# Indikatoren - Nachbau der im Bot verwendeten Implementierungen
# ===========================================================================
def _rma(werte, n):
    """Wilder-Glaettung, wie pandas_ta sie fuer RSI/ATR benutzt."""
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    s = sum(werte[:n]) / n
    out[n - 1] = s
    for i in range(n, len(werte)):
        s = (s * (n - 1) + werte[i]) / n
        out[i] = s
    return out


def _ema(werte, n):
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    a = 2.0 / (n + 1.0)
    s = sum(werte[:n]) / n
    out[n - 1] = s
    for i in range(n, len(werte)):
        s = werte[i] * a + s * (1 - a)
        out[i] = s
    return out


def _sma(werte, n):
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    s = sum(werte[:n])
    out[n - 1] = s / n
    for i in range(n, len(werte)):
        s += werte[i] - werte[i - n]
        out[i] = s / n
    return out


def rsi(close, n=14):
    """RSI mit Wilder-Glaettung (pandas_ta.rsi)."""
    gew, ver = [0.0], [0.0]
    for i in range(1, len(close)):
        d = close[i] - close[i - 1]
        gew.append(max(d, 0.0))
        ver.append(max(-d, 0.0))
    ag, av = _rma(gew[1:], n), _rma(ver[1:], n)
    out = [None] * len(close)
    for i in range(len(ag)):
        if ag[i] is None:
            continue
        if av[i] == 0:
            out[i + 1] = 100.0
        else:
            rs = ag[i] / av[i]
            out[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return out


def adx_bot(hi, lo, cl, n=14):
    """Nachbau von data/market_data.py::_adx (einfache rollende Mittel,
    NICHT Wilder). Gibt (adx, pdi, mdi) zurueck."""
    m = len(cl)
    pdm, mdm, tr = [0.0] * m, [0.0] * m, [0.0] * m
    for i in range(1, m):
        up = hi[i] - hi[i - 1]
        dn = lo[i - 1] - lo[i]
        pdm[i] = max(up, 0.0)
        mdm[i] = max(dn, 0.0)
        tr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
    atr = _sma(tr, n)
    spdm, smdm = _sma(pdm, n), _sma(mdm, n)
    pdi, mdi, dx = [None] * m, [None] * m, [None] * m
    for i in range(m):
        if atr[i] is None or atr[i] <= 0:
            continue
        pdi[i] = 100.0 * spdm[i] / atr[i]
        mdi[i] = 100.0 * smdm[i] / atr[i]
        dx[i] = abs(pdi[i] - mdi[i]) / (pdi[i] + mdi[i] + 1e-10) * 100.0
    dxv = [x if x is not None else 0.0 for x in dx]
    adx = _sma(dxv, n)
    for i in range(m):
        if dx[i] is None:
            adx[i] = None
    return adx, pdi, mdi


def atr_wilder(hi, lo, cl, n=14):
    m = len(cl)
    tr = [0.0] * m
    for i in range(1, m):
        tr[i] = max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
    return _rma(tr, n)


def bbands(close, n=20, k=2.0):
    """SMA +- k*Standardabweichung (ddof=0, wie pandas_ta)."""
    m = len(close)
    mid = _sma(close, n)
    unten, oben = [None] * m, [None] * m
    s = s2 = 0.0
    for i in range(m):
        s += close[i]
        s2 += close[i] * close[i]
        if i >= n:
            s -= close[i - n]
            s2 -= close[i - n] * close[i - n]
        if i >= n - 1:
            mu = s / n
            var = max(s2 / n - mu * mu, 0.0)
            sd = math.sqrt(var)
            unten[i] = mu - k * sd
            oben[i] = mu + k * sd
    return unten, mid, oben


def rollend_max(werte, n):
    """Gleitendes Maximum ueber n Balken (inkl. aktuellem)."""
    from collections import deque
    out = [None] * len(werte)
    dq = deque()
    for i, v in enumerate(werte):
        while dq and werte[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        while dq[0] <= i - n:
            dq.popleft()
        if i >= n - 1:
            out[i] = werte[dq[0]]
    return out


def rollend_min(werte, n):
    from collections import deque
    out = [None] * len(werte)
    dq = deque()
    for i, v in enumerate(werte):
        while dq and werte[dq[-1]] >= v:
            dq.pop()
        dq.append(i)
        while dq[0] <= i - n:
            dq.popleft()
        if i >= n - 1:
            out[i] = werte[dq[0]]
    return out


def rollend_vwap(hi, lo, cl, vol, n):
    """VWAP ueber das rollende Fenster - entspricht dem kumulierten VWAP,
    den features/vwap_agent.py auf den 120 geholten Balken rechnet."""
    m = len(cl)
    out = [None] * m
    stp = stpv = 0.0
    sv = 0.0
    tp = [(hi[i] + lo[i] + cl[i]) / 3.0 for i in range(m)]
    for i in range(m):
        stpv += tp[i] * vol[i]
        sv += vol[i]
        if i >= n:
            stpv -= tp[i - n] * vol[i - n]
            sv -= vol[i - n]
        if i >= n - 1 and sv > 0:
            out[i] = stpv / sv
    return out


def rsi_divergenz_bull(close, rsiw, lookback=30, fenster=5):
    """Nachbau von features/rsi_divergence.py: bullische Divergenz.

    Swing-Tief: lokales Minimum ueber +-fenster. Bullisch, wenn das letzte
    Swing-Tief tiefer liegt als ein frueheres im Lookback, der RSI dort
    aber hoeher steht. Ergebnis 1/0 je Balken; nur abgeschlossene Balken.
    """
    m = len(close)
    out = [0.0] * m
    tiefs = []          # (index, preis, rsi)
    for i in range(fenster, m - fenster):
        f = close[i]
        if all(close[j] >= f for j in range(i - fenster, i + fenster + 1)):
            if rsiw[i] is not None:
                tiefs.append((i, f, rsiw[i]))
    # Fuer jeden Balken t: liegt eine Divergenz in den letzten `lookback`
    # Balken vor? Nur Swing-Tiefs verwenden, die bei t bereits bestaetigt
    # sind (Index + fenster <= t).
    zeiger = 0
    aktiv = []
    for t in range(m):
        while zeiger < len(tiefs) and tiefs[zeiger][0] + fenster <= t:
            aktiv.append(tiefs[zeiger])
            zeiger += 1
        rel = [x for x in aktiv if x[0] > t - lookback]
        if len(rel) >= 2:
            letzt = rel[-1]
            for frueh in rel[:-1]:
                if letzt[1] < frueh[1] and letzt[2] > frueh[2]:
                    out[t] = 1.0
                    break
    return out


def obv_steigung(close, vol, n=20):
    m = len(close)
    obv = [0.0] * m
    for i in range(1, m):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + vol[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - vol[i]
        else:
            obv[i] = obv[i - 1]
    svol = _sma(vol, n)
    out = [None] * m
    for i in range(n, m):
        if svol[i] and svol[i] > 0:
            out[i] = (obv[i] - obv[i - n]) / (svol[i] * n)
    return out


def stoch_rsi(rsiw, n=14):
    werte = [x if x is not None else 50.0 for x in rsiw]
    mn, mx = rollend_min(werte, n), rollend_max(werte, n)
    out = [None] * len(werte)
    for i in range(len(werte)):
        if mn[i] is None or rsiw[i] is None:
            continue
        out[i] = (werte[i] - mn[i]) / (mx[i] - mn[i] + 1e-10) * 100.0
    return out


def tsi_paar(close, lang=25, kurz=13, sig=7):
    """features/indicators.py::calc_tsi - ewm ohne SMA-Seed (pandas .ewm)."""
    m = len(close)
    diff = [0.0] + [close[i] - close[i - 1] for i in range(1, m)]
    absd = [abs(x) for x in diff]

    def ewm(xs, span):
        a = 2.0 / (span + 1.0)
        out = [xs[0]]
        for i in range(1, len(xs)):
            out.append(xs[i] * a + out[-1] * (1 - a))
        return out

    s1 = ewm(ewm(diff, lang), kurz)
    s2 = ewm(ewm(absd, lang), kurz)
    tsi = [100.0 * s1[i] / (s2[i] + 1e-10) for i in range(m)]
    return tsi, ewm(tsi, sig)


def rollende_std(werte, n):
    m = len(werte)
    out = [None] * m
    s = s2 = 0.0
    for i in range(m):
        s += werte[i]
        s2 += werte[i] * werte[i]
        if i >= n:
            s -= werte[i - n]
            s2 -= werte[i - n] * werte[i - n]
        if i >= n - 1:
            mu = s / n
            out[i] = math.sqrt(max(s2 / n - mu * mu, 0.0))
    return out


# ===========================================================================
# Feature-Inventar
# ===========================================================================
# (schluessel, Anzeigename, Quelle, Status)
#   A = aktiv im Entscheidungspfad
#   B = im Projekt berechenbar, aber im Entscheidungspfad NICHT verdrahtet
#   T = toter Pfad: der Code liest eine Spalte, die nie erzeugt wird
INVENTAR = [
    ("rsi_14",        "RSI(14)",                "agents/signal_agent.py:71",   "A"),
    ("macd_hist",     "MACD - Signal",          "agents/signal_agent.py:82",   "A"),
    ("macd_line",     "MACD-Linie",             "data/market_data.py:65",      "A"),
    ("p_vs_ema20",    "Close/EMA20 - 1",        "agents/signal_agent.py:95",   "A"),
    ("p_vs_ema50",    "Close/EMA50 - 1",        "agents/v4_strategies.py:105", "A"),
    ("ema20_vs_50",   "EMA20/EMA50 - 1",        "agents/signal_agent.py:95",   "A"),
    ("adx_14",        "ADX(14)",                "agents/signal_agent.py:100",  "A"),
    ("atr_rel",       "ATR(14)/Close",          "data/market_data.py:70",      "A"),
    ("bb_pos",        "Lage in den BBaendern",  "agents/signal_agent.py:113",  "A"),
    ("bb_width",      "BBand-Breite",           "data/market_data.py:67",      "A"),
    ("fear_greed",    "Fear & Greed (Tag)",     "agents/signal_agent.py:104",  "A"),
    ("fg_delta",      "F&G Tagesaenderung",     "abgeleitet aus fear_greed",   "A"),
    ("vol_ratio_20",  "Volumen/SMA20",          "agents/signal_agent.py:126",  "A"),
    ("rsi_div_bull",  "RSI-Divergenz bullisch", "features/rsi_divergence.py:24", "A"),
    ("vwap_rel",      "Close/VWAP(120) - 1",    "features/vwap_agent.py:29",   "A"),
    ("di_diff",       "+DI - -DI",              "features/regime_detection.py:42", "A"),
    ("fib_dist_618",  "Abstand zu Fib 61,8 %",  "agents/v4_strategies.py:186", "A"),
    ("pump_5",        "Close/Close[-5] - 1",    "app.py:747",                  "A"),
    ("hoch20_rel",    "Close/Hoch(20) - 1",     "agents/v4_strategies.py:154", "T"),
    ("stoch_rsi",     "StochRSI(14)",           "features/indicators.py:69",   "B"),
    ("tsi",           "TSI",                    "features/indicators.py:74",   "T"),
    ("tsi_hist",      "TSI - TSI_signal",       "features/indicators.py:74",   "T"),
    ("obv_steig",     "OBV-Steigung(20)",       "features/indicators.py:57",   "B"),
    ("volatilitaet",  "Vola(14) der Renditen",  "features/indicators.py:36",   "B"),
    ("hl_range",      "(High-Low)/Close",       "features/indicators.py:39",   "B"),
]

NICHT_PRUEFBAR = [
    ("orderbook_imbalance", "data/orderbook_depth.py / app.py:1658",
     "Orderbuch-Tiefe wird live abgefragt, nicht archiviert"),
    ("whale_score", "data/whale_alerts.py / app.py:1584",
     "Whale-Alerts nur live, kein Verlauf im Projekt"),
    ("reddit_score", "data/reddit_sentiment.py / app.py:1585",
     "Reddit-Sentiment nur live"),
    ("capitol_score", "data/capitol_trades.py / app.py:1582",
     "Capitol-Trades nur live"),
    ("funding_score", "data/funding_rates.py / app.py:1583",
     "Funding-Rates nur live, keine Historie abgelegt"),
    ("onchain_score", "data/onchain_analytics.py / app.py:1605",
     "On-Chain/NUPL nur live"),
    ("news_sentiment", "data/news_data.py / app.py:1600",
     "News-Score nur live"),
    ("dxy_filter", "data/dxy_filter.py",
     "DXY-Reihe nicht im Projekt abgelegt"),
    ("ensemble", "models/ensemble_signal.py / app.py:1629",
     "Aggregat der obigen Quellen - erbt deren Nichtpruefbarkeit"),
    ("mtf_score", "features/multi_timeframe.py:39",
     "braucht 5m-Kerzen; im Projekt liegen nur 15m"),
    ("ema200", "features/indicators.py:14",
     "braucht 200 Balken, der Bot holt 120 (config.json candle_limit)"),
    ("ichimoku", "agents/v4_strategies.py:127",
     "TOTER PFAD: Spalten ICH_* werden nirgends erzeugt"),
    ("vol_high_gate", "agents/v4_strategies.py:148",
     "TOTER PFAD: Spalte Vol_high wird nirgends erzeugt"),
]


def features_je_coin(kerzen1h, vol1h, fg_tab):
    """Alle rekonstruierbaren Features fuer eine Coin-Zeitreihe."""
    t = [k[0] for k in kerzen1h]
    o = [k[1] for k in kerzen1h]
    hi = [k[2] for k in kerzen1h]
    lo = [k[3] for k in kerzen1h]
    cl = [k[4] for k in kerzen1h]
    vol = [vol1h.get(x, 0.0) for x in t]
    m = len(cl)

    r = rsi(cl, 14)
    e20, e50 = _ema(cl, 20), _ema(cl, 50)
    e12, e26 = _ema(cl, 12), _ema(cl, 26)
    macd = [None if (e12[i] is None or e26[i] is None) else e12[i] - e26[i]
            for i in range(m)]
    macd_gef = [x if x is not None else 0.0 for x in macd]
    macd_sig = _ema(macd_gef, 9)
    bbl, bbm, bbu = bbands(cl, 20, 2.0)
    adx, pdi, mdi = adx_bot(hi, lo, cl, 14)
    atr = atr_wilder(hi, lo, cl, 14)
    vsma = _sma(vol, 20)
    vwap = rollend_vwap(hi, lo, cl, vol, FENSTER)
    div = rsi_divergenz_bull(cl, r, 30, 5)
    obv_s = obv_steigung(cl, vol, 20)
    srsi = stoch_rsi(r, 14)
    tsi, tsis = tsi_paar(cl)
    rend = [0.0] + [(cl[i] / cl[i - 1] - 1.0) if cl[i - 1] > 0 else 0.0
                    for i in range(1, m)]
    volat = rollende_std(rend, 14)
    hoch20 = rollend_max(hi, 20)
    hoch120 = rollend_max(hi, FENSTER)
    tief120 = rollend_min(lo, FENSTER)

    from datetime import datetime, timezone
    fg = []
    fgd = []
    for x in t:
        d = datetime.fromtimestamp(x / 1000, timezone.utc)
        tag = d.strftime("%Y-%m-%d")
        vorher = datetime.fromtimestamp(x / 1000 - 86400, timezone.utc).strftime("%Y-%m-%d")
        a = fg_tab.get(tag)
        b = fg_tab.get(vorher)
        fg.append(float(a) if a is not None else None)
        fgd.append(float(a) - float(b) if (a is not None and b is not None) else None)

    F = {k: [None] * m for k, _n, _q, _s in INVENTAR}
    for i in range(m):
        c = cl[i]
        F["rsi_14"][i] = r[i]
        if macd[i] is not None and macd_sig[i] is not None:
            F["macd_hist"][i] = (macd[i] - macd_sig[i]) / c if c > 0 else None
            F["macd_line"][i] = macd[i] / c if c > 0 else None
        if e20[i]:
            F["p_vs_ema20"][i] = c / e20[i] - 1.0
        if e50[i]:
            F["p_vs_ema50"][i] = c / e50[i] - 1.0
        if e20[i] and e50[i]:
            F["ema20_vs_50"][i] = e20[i] / e50[i] - 1.0
        F["adx_14"][i] = adx[i]
        if atr[i] is not None and c > 0:
            F["atr_rel"][i] = atr[i] / c
        if bbl[i] is not None and bbu[i] is not None and bbu[i] > bbl[i]:
            F["bb_pos"][i] = (c - bbl[i]) / (bbu[i] - bbl[i])
            F["bb_width"][i] = (bbu[i] - bbl[i]) / bbm[i] if bbm[i] else None
        F["fear_greed"][i] = fg[i]
        F["fg_delta"][i] = fgd[i]
        if vsma[i] and vsma[i] > 0:
            F["vol_ratio_20"][i] = vol[i] / vsma[i]
        F["rsi_div_bull"][i] = div[i]
        if vwap[i]:
            F["vwap_rel"][i] = c / vwap[i] - 1.0
        if pdi[i] is not None and mdi[i] is not None:
            F["di_diff"][i] = pdi[i] - mdi[i]
        if hoch120[i] is not None and tief120[i] is not None:
            spanne = hoch120[i] - tief120[i]
            if spanne > 0:
                fib618 = hoch120[i] - 0.618 * spanne
                F["fib_dist_618"][i] = (c - fib618) / c
        if i >= 5 and cl[i - 5] > 0:
            F["pump_5"][i] = c / cl[i - 5] - 1.0
        if hoch20[i]:
            F["hoch20_rel"][i] = c / hoch20[i] - 1.0
        F["stoch_rsi"][i] = srsi[i]
        F["tsi"][i] = tsi[i]
        F["tsi_hist"][i] = tsi[i] - tsis[i]
        F["obv_steig"][i] = obv_s[i]
        F["volatilitaet"][i] = volat[i]
        if c > 0:
            F["hl_range"][i] = (hi[i] - lo[i]) / c
    return F, cl


def forward(cl, h):
    m = len(cl)
    out = [None] * m
    for i in range(m - h):
        if cl[i] > 0:
            out[i] = cl[i + h] / cl[i] - 1.0
    return out


# ===========================================================================
def jahr_messen(marke):
    daten, fg_tab = lade_jahr(marke)
    je_coin = {}
    for coin in COINS:
        ks15 = daten.get(coin)
        if not ks15:
            continue
        k1h = zu_1h(ks15)
        vol = lade_volumen_1h(coin, marke)
        F, cl = features_je_coin(k1h, vol, fg_tab)
        fw = {name: forward(cl, h) for name, h in HORIZONTE}
        je_coin[coin] = (F, fw, len(cl))
    return je_coin


def ic_tabelle(je_coin):
    """{(feature, horizont): {"coins": {coin: (rho,n)}, "mittel": rho,
                              "n_balken": int}}"""
    erg = {}
    for schluessel, _n, _q, _s in INVENTAR:
        for hname, h in HORIZONTE:
            pro_coin = {}
            for coin, (F, fw, m) in je_coin.items():
                xs, ys = [], []
                fv, rv = F[schluessel], fw[hname]
                for i in range(m):
                    a, b = fv[i], rv[i]
                    if a is None or b is None:
                        continue
                    xs.append(a)
                    ys.append(b)
                if len(xs) < 200:
                    continue
                # konstante Features (z. B. Divergenz durchgehend 0) ueberspringen
                if xs[0] == xs[-1] and len(set(xs[:5000])) < 2:
                    continue
                rho, n = spearman(xs, ys)
                pro_coin[coin] = (rho, n)
            if not pro_coin:
                continue
            werte = [v[0] for v in pro_coin.values()]
            n_balken = median([v[1] for v in pro_coin.values()])
            erg[(schluessel, hname)] = {
                "coins": pro_coin,
                "mittel": mittel(werte),
                "n_balken": n_balken,
                "n_gesamt": sum(v[1] for v in pro_coin.values()),
                "positiv": sum(1 for w in werte if w > 0),
                "anzahl": len(werte),
            }
    return erg


def p_werte(erg):
    for (f, hname), d in erg.items():
        h = dict(HORIZONTE)[hname]
        d["p_roh"] = rho_p(d["mittel"], d["n_gesamt"])
        n_eff = (d["n_balken"] / h) * N_EFF_COINS
        d["n_eff"] = n_eff
        d["p_eff"] = rho_p(d["mittel"], n_eff)
    schluessel = sorted(erg.keys())
    q_roh = bh_fdr([erg[k]["p_roh"] for k in schluessel])
    q_eff = bh_fdr([erg[k]["p_eff"] for k in schluessel])
    for k, a, b in zip(schluessel, q_roh, q_eff):
        erg[k]["q_roh"] = a
        erg[k]["q_eff"] = b
    return erg


# ===========================================================================
def f2a():
    print("\n" + "=" * 112)
    print(" F2a  INVENTAR - was rechnet das System, was ist rekonstruierbar?")
    print("=" * 112)
    print("\n  REKONSTRUIERBAR aus data_store/backtest (15m-Kerzen + F&G)")
    print(f"    {'#':>3s} {'Feature':<24s} {'Quelle':<40s} {'Status':<8s}")
    print("    " + "-" * 82)
    for i, (k, name, quelle, status) in enumerate(INVENTAR, 1):
        s = {"A": "aktiv", "B": "n.verdr.", "T": "tot"}[status]
        print(f"    {i:3d} {name:<24s} {quelle:<40s} {s:<8s}")
    print("\n    aktiv       = steht im Kauf-Entscheidungspfad")
    print("    n.verdr.    = wird im Projekt berechnet, aber von keiner")
    print("                  Kaufregel gelesen (features/indicators.py::")
    print("                  calc_all_indicators ist in app.py:64 importiert")
    print("                  und wird NIRGENDS aufgerufen)")
    print("    tot         = die Regel liest eine DataFrame-Spalte, die der")
    print("                  Snapshot nie enthaelt -> Regel feuert nie")

    print("\n  NICHT PRUEFBAR (nur live / nicht archiviert / toter Pfad)")
    print(f"    {'Feature':<22s} {'Quelle':<44s} Grund")
    print("    " + "-" * 104)
    for k, quelle, grund in NICHT_PRUEFBAR:
        print(f"    {k:<22s} {quelle:<44s} {grund}")
    print(f"\n    Rekonstruierbar: {len(INVENTAR)}   "
          f"Nicht pruefbar: {len(NICHT_PRUEFBAR)}")
    sys.stdout.flush()


def f2bc(erg, jahr):
    print("\n" + "=" * 112)
    print(f" F2b/c  INFORMATION COEFFICIENT + BH-FDR  -  {jahr}")
    print("=" * 112)
    print("\n  IC = Mittel der 11 coinweisen Spearman-Korrelationen"
          " (Feature(t) gegen Rendite t->t+h).")
    print("  p_roh  auf allen Beobachtungen | p_eff auf n_eff ="
          " (Balken/h) x 1,3 (E5 Befund 16)")
    print("  q_*    = Benjamini-Hochberg ueber ALLE"
          f" {len(erg)} Tests dieses Jahres")
    print(f"\n    {'Feature':<24s} {'Hor':>5s} {'IC':>8s} {'+/11':>5s} "
          f"{'n_eff':>8s} {'p_roh':>10s} {'q_roh':>9s} {'p_eff':>9s} "
          f"{'q_eff':>9s} {'sig':>5s}")
    print("    " + "-" * 106)
    reihen = sorted(erg.items(), key=lambda kv: -abs(kv[1]["mittel"]))
    for (f, hname), d in reihen:
        name = next(n for k, n, _q, _s in INVENTAR if k == f)
        sig = ""
        if d["q_eff"] < 0.05:
            sig = "**"
        elif d["q_roh"] < 0.05:
            sig = "(*)"
        print(f"    {name:<24s} {hname:>5s} {d['mittel']:+8.4f} "
              f"{d['positiv']:2d}/{d['anzahl']:<2d} {d['n_eff']:8.0f} "
              f"{d['p_roh']:10.3e} {d['q_roh']:9.4f} {d['p_eff']:9.4f} "
              f"{d['q_eff']:9.4f} {sig:>5s}")
    n_roh = sum(1 for _k, d in erg.items() if d["q_roh"] < 0.05)
    n_eff = sum(1 for _k, d in erg.items() if d["q_eff"] < 0.05)
    n_p05 = sum(1 for _k, d in erg.items() if d["p_roh"] < 0.05)
    print("    " + "-" * 106)
    print(f"    Tests: {len(erg)} | p_roh < 0,05: {n_p05} | "
          f"BH-FDR q_roh < 0,05: {n_roh} | BH-FDR q_eff < 0,05: {n_eff}")
    print(f"    Bei reinem Zufall zu erwarten (p<0,05): "
          f"{len(erg) * 0.05:.1f} Treffer")
    print("    ** = haelt auch der effektiven Stichprobe stand")
    print("    (*) = nur mit der naiven Stichprobe signifikant -> Artefakt")
    sys.stdout.flush()
    return n_roh, n_eff, n_p05


def f2d(e2, e1):
    print("\n" + "=" * 112)
    print(" F2d  STABILITAET - gleiches Vorzeichen in BEIDEN Jahren?")
    print("=" * 112)
    print(f"\n    {'Feature':<24s} {'Hor':>5s} {'IC J2':>9s} {'IC J1':>9s} "
          f"{'Vorz.':>7s} {'|IC| min':>9s} {'q_eff J2':>9s} {'q_eff J1':>9s}")
    print("    " + "-" * 90)
    stabil = []
    streng = []
    gemeinsam = sorted(set(e2.keys()) & set(e1.keys()),
                       key=lambda k: -min(abs(e2[k]["mittel"]),
                                          abs(e1[k]["mittel"])))
    for k in gemeinsam:
        f, hname = k
        name = next(n for kk, n, _q, _s in INVENTAR if kk == f)
        a, b = e2[k]["mittel"], e1[k]["mittel"]
        gleich = (a > 0) == (b > 0)
        mini = min(abs(a), abs(b))
        beide_fdr = e2[k]["q_eff"] < 0.05 and e1[k]["q_eff"] < 0.05
        if gleich:
            stabil.append((mini, k, a, b))
            if beide_fdr:
                streng.append((mini, k, a, b))
        print(f"    {name:<24s} {hname:>5s} {a:+9.4f} {b:+9.4f} "
              f"{('gleich' if gleich else 'WECHSEL'):>7s} {mini:9.4f} "
              f"{e2[k]['q_eff']:9.4f} {e1[k]['q_eff']:9.4f}"
              f"{'   <== haelt beides' if (gleich and beide_fdr) else ''}")
    print("    " + "-" * 90)
    print(f"    Vorzeichen gleich: {len(stabil)} von {len(gemeinsam)} "
          f"({len(stabil) / len(gemeinsam) * 100:.0f} %)")
    print("    Erwartung bei reinem Zufall: 50 %")
    print(f"    Davon zusaetzlich in BEIDEN Jahren mit q_eff < 0,05:"
          f" {len(streng)}")
    for _m, (f, hname), a, b in sorted(streng, reverse=True):
        name = next(n for kk, n, _q, _s in INVENTAR if kk == f)
        print(f"      {name:<24s} {hname:>5s}  IC {a:+.4f} / {b:+.4f}")
    print("\n    ACHTUNG zur 75-%-Quote: die 75 Tests sind nicht unabhaengig.")
    print("    Viele Features messen dieselbe Groesse (Close/EMA20,")
    print("    Close/EMA50, Lage im BBand, StochRSI, VWAP-Abstand sind alle")
    print("    Varianten von 'Kurs relativ zum juengsten Mittel'). Eine")
    print("    Vorzeichenkonstanz von 75 % beweist daher KEINE 56 unabhaengigen")
    print("    stabilen Befunde, sondern im Kern eine Handvoll.")
    stabil.sort(reverse=True)
    streng.sort(reverse=True)
    sys.stdout.flush()
    return stabil, streng


def f2e(stabil, streng, je_coin_j2, je_coin_j1):
    print("\n" + "=" * 112)
    print(" F2e  OEKONOMISCHE SCHWELLE - traegt der IC die Reibung?")
    print("=" * 112)
    ziel = 0.56
    ic_noetig = trefferquote_zu_ic(ziel)
    print(f"\n  Noetige Trefferquote im +-2,5-%-Barrierentest bei 0,30 %"
          f" Reibung: {ziel * 100:.0f} % (F1c)")
    print(f"  Zugehoeriger Spearman-IC unter bivariat-normaler Naeherung:"
          f" {ic_noetig:.4f}")
    print("  Naeherung, keine Messung: sie bildet das Vorzeichen einer"
          " Rendite ueber FESTEN")
    print("  Horizont ab, nicht das First-Touch-Rennen aus E2. Sie taugt als"
          " Groessenordnung.")
    print(f"\n  Untergrenze Reibung nach F1c (Limit + BNB) 0,15 %"
          f" -> P(auf) 53 % -> IC {trefferquote_zu_ic(0.53):.4f}")

    print("\n  AUSWAHL: die drei staerksten Features, die (i) in beiden Jahren")
    print("  dasselbe Vorzeichen haben UND (ii) in beiden Jahren die BH-FDR")
    print("  auf der effektiven Stichprobe ueberstehen. Nur diese sind")
    print("  ueberhaupt Kandidaten - alles andere ist nach F2c/F2d Rauschen.")
    top = streng[:3] if len(streng) >= 3 else stabil[:3]
    if len(streng) < 3:
        print("  (weniger als 3 Kandidaten - ersatzweise die staerksten"
              " vorzeichenstabilen)")
    print(f"\n    {'Feature':<24s} {'Hor':>5s} {'IC J2':>9s} {'IC J1':>9s} "
          f"{'impl. Treffer J2':>17s} {'reicht fuer 56 %?':>18s}")
    print("    " + "-" * 90)
    for mini, (f, hname), a, b in top:
        name = next(n for kk, n, _q, _s in INVENTAR if kk == f)
        tq = ic_zu_trefferquote(abs(a)) * 100
        print(f"    {name:<24s} {hname:>5s} {a:+9.4f} {b:+9.4f} "
              f"{tq:16.2f}% {('JA' if tq >= 56 else 'NEIN'):>18s}")
    print("    'impl. Treffer' auf |IC| gerechnet - das Vorzeichen sagt nur,")
    print("    in welche Richtung man handeln muesste, nicht wie stark.")
    print("\n    KOSTENVERGLEICH AM PASSENDEN HORIZONT (F1d)")
    for _m, (f, hname), a, _b in top:
        h = dict(HORIZONTE)[hname]
        med = {1: 0.35, 4: 0.71, 24: 2.03}[h]      # J2, gepoolt, aus F1d
        noetig = (0.5 + REIBUNG / (2 * med)) * 100
        tq = ic_zu_trefferquote(abs(a)) * 100
        name = next(n for kk, n, _q, _s in INVENTAR if kk == f)
        print(f"      {name:<24s} {hname:>4s}: Median|Bewegung| {med:.2f} %"
              f" -> noetige Trefferquote {noetig:.1f} %,"
              f" erreichbar laut IC {tq:.1f} %  -> "
              f"{'traegt' if tq >= noetig else 'TRAEGT NICHT'}")

    print("\n  DIREKTE MESSUNG statt Naeherung - Quintilanalyse am"
          " jeweiligen Horizont, je Coin normiert")
    print("    Oberstes/unterstes Fuenftel nach Feature; mittlere Rendite")
    print("    und Vorzeichen-Trefferquote im jeweiligen Horizont.")
    for jahr, jc in (("Jahr 2", je_coin_j2), ("Jahr 1", je_coin_j1)):
        print(f"\n    {jahr}")
        print(f"      {'Feature':<20s} {'Hor':>4s} {'Q5 E[r]':>9s} {'Q5 Tr%':>8s} "
              f"{'Q1 E[r]':>9s} {'Q1 Tr%':>8s} {'Spread':>9s} "
              f"{'Spread-Reibung':>15s}")
        print("      " + "-" * 88)
        for mini, (f, hname), _a, _b in top:
            name = next(n for kk, n, _q, _s in INVENTAR if kk == f)
            q5r, q5t, q1r, q1t = quintile(jc, f, hname)
            spread = q5r - q1r
            print(f"      {name[:20]:<20s} {hname:>4s} {q5r:+8.3f}% {q5t:7.1f}% "
                  f"{q1r:+8.3f}% {q1t:7.1f}% {spread:+8.3f}% "
                  f"{spread - REIBUNG:+14.3f}%")
    print("\n    Spread-Reibung > 0 waere die Mindestbedingung dafuer, dass"
          " ein Long/Short-")
    print("    Paar aus den Extremquintilen die Kosten deckt. Der Bot kann"
          " ohnehin nur Long.")
    sys.stdout.flush()


def quintile(je_coin, feature, hname):
    """Renditen im obersten/untersten Feature-Fuenftel, je Coin normiert."""
    q5, q1 = [], []
    for coin, (F, fw, m) in je_coin.items():
        paare = [(F[feature][i], fw[hname][i]) for i in range(m)
                 if F[feature][i] is not None and fw[hname][i] is not None]
        if len(paare) < 500:
            continue
        paare.sort(key=lambda x: x[0])
        n = len(paare)
        g = n // 5
        q1.extend(y * 100 for _x, y in paare[:g])
        q5.extend(y * 100 for _x, y in paare[-g:])
    if not q5 or not q1:
        return 0.0, 0.0, 0.0, 0.0
    return (mittel(q5), sum(1 for y in q5 if y > 0) / len(q5) * 100,
            mittel(q1), sum(1 for y in q1 if y > 0) / len(q1) * 100)


def main():
    print("=" * 112)
    print(" MESSUNG F2 - FEATURE-SCREEN: sitzt irgendwo Information?")
    print(" Stand 30.07.2026 - Datenbasis wie PRUEFSUMMEN.txt")
    print("=" * 112)
    f2a()

    print("\n  ... berechne Features Jahr 2 ...")
    sys.stdout.flush()
    jc2 = jahr_messen("")
    e2 = p_werte(ic_tabelle(jc2))
    f2bc(e2, "Jahr 2  2025-07..2026-07")

    print("\n  ... berechne Features Jahr 1 ...")
    sys.stdout.flush()
    jc1 = jahr_messen("_v1")
    e1 = p_werte(ic_tabelle(jc1))
    f2bc(e1, "Jahr 1  2024-07..2025-07")

    stabil, streng = f2d(e2, e1)
    f2e(stabil, streng, jc2, jc1)

    print("\n" + "=" * 112)
    print(" ENDE F2")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    sys.exit(main())
