# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit G1 vom 30.07.2026.
# Nicht archivieren - Verifikation des F2-Feature-Screens. Siehe ../README.md
"""
G1 - Sind die Indikatoren in messung_f2_ic.py richtig nachgebaut?

REFERENZ IST DER BOT SELBST. Dieses Skript importiert die
Projektimplementierungen (features/indicators.py, data/market_data.py,
agents/v4_strategies.py, features/vwap_agent.py, features/rsi_divergence.py)
und vergleicht sie numerisch mit dem F2-Nachbau auf identischen 1h-Balken.

ABWEICHUNG VON DER STDLIB-KONVENTION - BEGRUENDET
-------------------------------------------------
Die Messskripte E1-F3 nutzen ausschliesslich die Standardbibliothek.
G1 kann das nicht: die Referenz IST pandas/pandas_ta, weil der Bot damit
rechnet. G1 aendert nichts an der Reproduzierbarkeit von E1-F3; es prueft
sie. pandas 2.3.3 / pandas_ta (Version wird ausgegeben) / numpy 2.2.6.

LOGGER-HYGIENE
--------------
features/rsi_divergence.py loggt bei jedem Fund nach data_store/system.log
- die Logdatei des LAUFENDEN Bots. Vor jedem Aufruf werden die
Log-Methoden im MESSPROZESS durch No-Ops ersetzt (reiner In-Memory-Patch,
der Bot-Prozess ist nicht betroffen).

VERGLEICHSDESIGN
----------------
Teil 1  Vollserien-Features (vektorisierbar): Referenz auf der vollen
        1h-Serie, Vergleich ab Balken 200 (Einschwingzeit; davor
        unterscheiden sich Seed-Konventionen konstruktionsbedingt).
Teil 2  Fenster-Features (der Bot sieht live NUR ein 120-Balken-Fenster):
        Referenzaufruf je Fenster auf BTC/ETH/DOGE, jede 4. Stunde.
        Zusaetzlich Fenster-gegen-Vollserie fuer RSI/EMA/MACD/ADX/ATR/BB:
        das beziffert den Warmup-Effekt, den auch der Live-Bot hat.
Teil 3  Handrechnung RSI(14) nach Wilder, ausgeschrieben.
Teil 4  IC-Neuberechnung fuer jedes auffaellige Feature mit der
        PROJEKTIMPLEMENTIERUNG, beide Jahre, Urteil F2:
        BESTAETIGT / KORRIGIERT / WIDERLEGT.

Schwelle "auffaellig": Spearman < 0,99 oder Vorzeichenabweichung > 1 %.
"""
import sys
import math

import numpy as np
import pandas as pd
import pandas_ta as ta

from harness_ext import lade_jahr, COINS, STUNDE_MS
from messung_f_stat import spearman as sp_stdlib, mittel, bh_fdr, rho_p
import messung_f2_ic as f2

# ---- Projektimplementierungen (Referenz) ----
from core.logger import log as _projlog
for _m in ("info", "warn", "error", "signal", "trade", "debug"):
    if hasattr(_projlog, _m):
        setattr(_projlog, _m, lambda *a, **k: None)   # nur dieser Prozess

from features.indicators import (calc_stoch_rsi, calc_tsi, calc_obv,
                                 calc_adx as calc_adx_indicators)
from features.vwap_agent import VWAPAgent
from features.rsi_divergence import RSIDivergenceDetector
from agents.v4_strategies import calc_fibonacci_levels
from data.market_data import DataAgent

FENSTER = 120
EINSCHWING = 200
SCHRITT_FENSTER = 4          # jede 4. Stunde im Fenster-Vergleich
FENSTER_COINS = ["BTC/USDC", "ETH/USDC", "DOGE/USDC"]
AUFF_SPEARMAN = 0.99
AUFF_VORZ = 1.0              # %


# ===========================================================================
# Datenbasis: identische 1h-Balken wie in F2
# ===========================================================================
_DF_CACHE = {}
_REF_CACHE = {}


def df_1h(coin, marke):
    key = (coin, marke)
    if key in _DF_CACHE:
        return _DF_CACHE[key]
    ks15 = lade_jahr(marke)[0].get(coin)
    if not ks15:
        return None
    k1h = f2.zu_1h(ks15)
    vol = f2.lade_volumen_1h(coin, marke)
    d = pd.DataFrame(k1h, columns=["Date", "Open", "High", "Low", "Close"])
    d["Volume"] = [vol.get(t, 0.0) for t in d["Date"]]
    _DF_CACHE[key] = d
    return d


def referenz_voll_cached(coin, marke):
    key = (coin, marke)
    if key not in _REF_CACHE:
        d = df_1h(coin, marke)
        _REF_CACHE[key] = None if d is None else referenz_voll(d)
    return _REF_CACHE[key]


# ===========================================================================
# Referenz-Berechnung (Projektwege), volle Serie
# ===========================================================================
def referenz_voll(d):
    """Projektimplementierungen auf der vollen Serie. Gibt dict von Series."""
    c = d["Close"]
    R = {}
    rsi = ta.rsi(c, length=14)                        # market_data.py:62
    e20 = ta.ema(c, length=20)                        # market_data.py:63
    e50 = ta.ema(c, length=50)                        # market_data.py:64
    m = ta.macd(c)                                    # market_data.py:65
    bb = ta.bbands(c, length=20, std=2)               # market_data.py:67
    atr = ta.atr(d["High"], d["Low"], c, length=14)   # market_data.py:70
    adx_md = DataAgent._adx(None, d)                  # market_data.py:117
    adx_pt = ta.adx(d["High"], d["Low"], c, length=14)  # regime_detection.py:42

    R["rsi_14"] = rsi
    R["p_vs_ema20"] = c / e20 - 1.0
    R["p_vs_ema50"] = c / e50 - 1.0
    R["ema20_vs_50"] = e20 / e50 - 1.0
    if m is not None:
        R["macd_line"] = m.iloc[:, 0] / c             # F2-Skalierung /Close
        R["macd_hist"] = (m.iloc[:, 0] - m.iloc[:, 2]) / c
    if bb is not None:
        bbl, bbm_, bbu = bb.iloc[:, 0], bb.iloc[:, 1], bb.iloc[:, 2]
        R["bb_pos"] = (c - bbl) / (bbu - bbl)
        R["bb_width"] = (bbu - bbl) / bbm_
    R["atr_rel"] = atr / c
    R["adx_14"] = adx_md
    if adx_pt is not None:
        R["di_diff_wilder"] = adx_pt.iloc[:, 1] - adx_pt.iloc[:, 2]  # DMP-DMN
    R["stoch_rsi"] = calc_stoch_rsi(rsi)              # indicators.py:69
    tsi, tsi_sig = calc_tsi(c)                        # indicators.py:74
    R["tsi"] = tsi
    R["tsi_hist"] = tsi - tsi_sig
    R["volatilitaet"] = c.pct_change().rolling(14).std()   # indicators.py:36-37 (ddof=1)
    R["hl_range"] = (d["High"] - d["Low"]) / (c + 1e-10)   # indicators.py:39
    vs = d["Volume"].rolling(20).mean()               # indicators.py:37/signal_agent:125
    R["vol_ratio_20"] = d["Volume"] / (vs + 1e-10)
    R["hoch20_rel"] = c / d["High"].rolling(20).max() - 1.0  # v4:154 tail(20).max
    R["obv"] = calc_obv(d)                            # indicators.py:57
    # pump_5 nach app.py:747: close / Close.iloc[-5] - 1  ->  4 Balken zurueck
    R["pump_5_app"] = c / c.shift(4) - 1.0
    # Vektorisierte Aequivalente der Fenster-Features (fuer G1d):
    # fib nach v4:46-47: tail(100) High-max/Low-min DES UEBERGEBENEN df
    hi100 = d["High"].rolling(100).max()
    lo100 = d["Low"].rolling(100).min()
    fib618 = hi100 - (hi100 - lo100) * 0.618
    R["fib_dist_618_v4"] = (c - fib618) / c
    # VWAP nach vwap_agent auf 120er-Fenster = rollender 120-VWAP
    tp = (d["High"] + d["Low"] + c) / 3.0
    pv = (tp * d["Volume"]).rolling(FENSTER).sum()
    vv = d["Volume"].rolling(FENSTER).sum()
    R["vwap_rel_roll"] = c / (pv / vv) - 1.0
    return R


# F2-Schluessel -> (Referenzschluessel, Quelle der Referenz)
PAARE = [
    ("rsi_14",       "rsi_14",          "ta.rsi | market_data.py:62"),
    ("p_vs_ema20",   "p_vs_ema20",      "ta.ema(20) | market_data.py:63"),
    ("p_vs_ema50",   "p_vs_ema50",      "ta.ema(50) | market_data.py:64"),
    ("ema20_vs_50",  "ema20_vs_50",     "ta.ema | market_data.py:63-64"),
    ("macd_line",    "macd_line",       "ta.macd | market_data.py:65"),
    ("macd_hist",    "macd_hist",       "ta.macd | market_data.py:65-66"),
    ("bb_pos",       "bb_pos",          "ta.bbands | market_data.py:67"),
    ("bb_width",     "bb_width",        "ta.bbands | market_data.py:67"),
    ("atr_rel",      "atr_rel",         "ta.atr | market_data.py:70"),
    ("adx_14",       "adx_14",          "DataAgent._adx | market_data.py:117"),
    ("di_diff",      "di_diff_wilder",  "ta.adx DMP-DMN | regime_detection.py:42"),
    ("stoch_rsi",    "stoch_rsi",       "calc_stoch_rsi | indicators.py:69"),
    ("tsi",          "tsi",             "calc_tsi | indicators.py:74"),
    ("tsi_hist",     "tsi_hist",        "calc_tsi | indicators.py:74"),
    ("volatilitaet", "volatilitaet",    "rolling.std ddof=1 | indicators.py:36"),
    ("hl_range",     "hl_range",        "indicators.py:39"),
    ("vol_ratio_20", "vol_ratio_20",    "signal_agent.py:125-126"),
    ("hoch20_rel",   "hoch20_rel",      "tail(20).max | v4_strategies.py:154"),
    ("pump_5",       "pump_5_app",      "iloc[-5] | app.py:747"),
    ("fib_dist_618", "fib_dist_618_v4", "tail(100) | v4_strategies.py:46-47"),
    ("vwap_rel",     "vwap_rel_roll",   "VWAPAgent (120er-Fenster) | vwap_agent.py:29-34"),
]
# Ohne numerischen Referenzpfad:
OHNE_REFERENZ = [
    ("fear_greed",  "identische Quelle (fear_greed.json Tageswert) - kein Numerikvergleich noetig"),
    ("fg_delta",    "Ableitung derselben Tageswerte - keine Projektreferenz, eigene Konstruktion"),
    ("obv_steig",   "OBV-Steigung ist EIGENE Konstruktion; Projekt kennt nur OBV selbst "
                    "(indicators.py:57). OBV wird verglichen, die Steigung nicht."),
    ("rsi_div_bull", "nur fensterweise pruefbar -> Teil 2"),
]


def vergleiche(nachbau, referenz, ab=EINSCHWING):
    """(pearson, spearman, maxabs, meanabs, vorzeichen%_anteil, n)"""
    a, b = [], []
    n_ges = min(len(nachbau), len(referenz))
    for i in range(ab, n_ges):
        x = nachbau[i]
        y = referenz.iloc[i] if hasattr(referenz, "iloc") else referenz[i]
        if x is None or y is None:
            continue
        try:
            y = float(y)
        except (TypeError, ValueError):
            continue
        if math.isnan(y) or math.isinf(y):
            continue
        a.append(float(x))
        b.append(y)
    if len(a) < 100:
        return None
    aa, bb_ = np.asarray(a), np.asarray(b)
    pe = float(np.corrcoef(aa, bb_)[0, 1])
    from scipy.stats import spearmanr
    spr = float(spearmanr(aa, bb_).statistic)
    diff = np.abs(aa - bb_)
    vz = float(np.mean(np.sign(aa) != np.sign(bb_)) * 100.0)
    return pe, spr, float(diff.max()), float(diff.mean()), vz, len(a)


# ===========================================================================
# Teil 2: Fenster-Features
# ===========================================================================
def fenster_vergleich(d, F_nachbau):
    """Referenz je 120er-Fenster (wie der Live-Bot) gegen F2-Nachbau.
    Gibt dict feature -> (liste_nachbau, liste_referenz)."""
    vwap_agent = VWAPAgent()
    det = RSIDivergenceDetector()          # lookback=30, min_swing_pct=1.0
    rsi_voll = ta.rsi(d["Close"], length=14)   # fuer detect braucht df RSI-Spalte
    out = {k: ([], []) for k in ("vwap_rel", "vwap_rel_exakt", "fib_dist_618",
                                 "rsi_div_bull", "pump_5")}
    warmup = {k: ([], []) for k in ("rsi_14", "p_vs_ema20", "p_vs_ema50",
                                    "macd_hist", "adx_14", "atr_rel", "bb_pos")}
    R_voll = referenz_voll(d)
    m = len(d)
    for ende in range(max(FENSTER, EINSCHWING), m, SCHRITT_FENSTER):
        w = d.iloc[ende - FENSTER + 1: ende + 1].copy()
        w.reset_index(drop=True, inplace=True)
        c_now = float(w["Close"].iloc[-1])
        i = ende

        # --- VWAPAgent (kumulativ ueber das Fenster) ---
        # Zwei Referenzen: (a) das Rueckgabefeld "vwap" - vwap_agent.py:64
        # rundet es auf 2 Dezimalen, was Kleinpreis-Coins (DOGE ~0,1 $)
        # zerschiesst; (b) die WOERTLICHE Agentenformel (Zeile 29-34) ohne
        # die Ausgaberundung. Die Bias-Entscheidung des Agenten rechnet
        # VOR der Rundung (Zeile 37-47), (b) ist also die
        # entscheidungsrelevante Groesse.
        try:
            v = vwap_agent.calculate(w, "?")
            vr = c_now / v["vwap"] - 1.0 if v.get("vwap") else None
        except Exception:
            vr = None
        tpw = (w["High"] + w["Low"] + w["Close"]) / 3.0
        cv = float(w["Volume"].sum())
        vr_ex = (c_now / (float((tpw * w["Volume"]).sum()) / cv) - 1.0
                 if cv > 0 else None)
        if F_nachbau["vwap_rel"][i] is not None:
            if vr is not None:
                out["vwap_rel"][0].append(F_nachbau["vwap_rel"][i])
                out["vwap_rel"][1].append(vr)
            if vr_ex is not None:
                out["vwap_rel_exakt"][0].append(F_nachbau["vwap_rel"][i])
                out["vwap_rel_exakt"][1].append(vr_ex)

        # --- Fibonacci 61,8 (v4: tail(100) des Fensters) ---
        fibs = calc_fibonacci_levels(w)
        fd = (c_now - fibs["61.8"]) / c_now
        if F_nachbau["fib_dist_618"][i] is not None:
            out["fib_dist_618"][0].append(F_nachbau["fib_dist_618"][i])
            out["fib_dist_618"][1].append(fd)

        # --- RSI-Divergenz (Projektdetektor auf dem Fenster) ---
        w2 = w.copy()
        w2["RSI"] = rsi_voll.iloc[ende - FENSTER + 1: ende + 1].values
        try:
            div = det.detect(w2)
            db = 1.0 if div.get("bullish") else 0.0
        except Exception:
            db = None
        if db is not None and F_nachbau["rsi_div_bull"][i] is not None:
            out["rsi_div_bull"][0].append(F_nachbau["rsi_div_bull"][i])
            out["rsi_div_bull"][1].append(db)

        # --- pump_5 (app.py:747 woertlich: close / iloc[-5] - 1) ---
        p5 = c_now / float(w["Close"].iloc[-5]) - 1.0
        if F_nachbau["pump_5"][i] is not None:
            out["pump_5"][0].append(F_nachbau["pump_5"][i])
            out["pump_5"][1].append(p5)

        # --- Warmup-Effekt: Fensterwert gegen Vollserienwert (Referenz je) ---
        wr = ta.rsi(w["Close"], length=14)
        we20 = ta.ema(w["Close"], length=20)
        we50 = ta.ema(w["Close"], length=50)
        wm = ta.macd(w["Close"])
        wbb = ta.bbands(w["Close"], length=20, std=2)
        watr = ta.atr(w["High"], w["Low"], w["Close"], length=14)
        wadx = DataAgent._adx(None, w)
        paare = {
            "rsi_14": (wr.iloc[-1] if wr is not None else None,
                       R_voll["rsi_14"].iloc[i]),
            "p_vs_ema20": (c_now / we20.iloc[-1] - 1 if we20 is not None else None,
                           R_voll["p_vs_ema20"].iloc[i]),
            "p_vs_ema50": (c_now / we50.iloc[-1] - 1 if we50 is not None else None,
                           R_voll["p_vs_ema50"].iloc[i]),
            "macd_hist": ((wm.iloc[-1, 0] - wm.iloc[-1, 2]) / c_now
                          if wm is not None else None,
                          R_voll["macd_hist"].iloc[i]),
            "adx_14": (wadx.iloc[-1] if wadx is not None else None,
                       R_voll["adx_14"].iloc[i]),
            "atr_rel": (watr.iloc[-1] / c_now if watr is not None else None,
                        R_voll["atr_rel"].iloc[i]),
            "bb_pos": ((c_now - wbb.iloc[-1, 0]) / (wbb.iloc[-1, 2] - wbb.iloc[-1, 0])
                       if wbb is not None else None,
                       R_voll["bb_pos"].iloc[i]),
        }
        for k, (a, b) in paare.items():
            try:
                if a is not None and not math.isnan(float(a)) \
                        and not math.isnan(float(b)):
                    warmup[k][0].append(float(a))
                    warmup[k][1].append(float(b))
            except (TypeError, ValueError):
                continue
    return out, warmup


# ===========================================================================
# Teil 3: Handrechnung RSI(14)
# ===========================================================================
def handrechnung_rsi(d):
    print("\n" + "=" * 112)
    print(" G1c-HAND  RSI(14) nach Wilder - ausgeschriebener Rechenweg, BTC 1h, Balken 0-16")
    print("=" * 112)
    c = [float(x) for x in d["Close"].iloc[:17]]
    print("\n  Rechenweg:")
    print("    delta_i = Close_i - Close_(i-1);  Gewinn = max(delta,0), Verlust = max(-delta,0)")
    print("    Seed (Balken 14): avgGain = Mittel(Gewinn_1..14), avgLoss = Mittel(Verlust_1..14)")
    print("    danach Wilder:    avg = (avg_vorher * 13 + wert_i) / 14")
    print("    RSI = 100 - 100/(1 + avgGain/avgLoss)")
    print(f"\n    {'i':>3s} {'Close':>12s} {'delta':>10s} {'Gewinn':>9s} {'Verlust':>9s}")
    g, v = [], []
    for i in range(1, 15):
        dl = c[i] - c[i - 1]
        g.append(max(dl, 0.0))
        v.append(max(-dl, 0.0))
        print(f"    {i:3d} {c[i]:12.2f} {dl:+10.2f} {g[-1]:9.2f} {v[-1]:9.2f}")
    ag, av = sum(g) / 14, sum(v) / 14
    rsi14 = 100 - 100 / (1 + ag / av) if av > 0 else 100.0
    print(f"\n    Seed:  avgGain = {ag:.4f}   avgLoss = {av:.4f}   "
          f"RSI(Balken 14) = {rsi14:.4f}")
    # zwei Wilder-Schritte
    werte = {14: rsi14}
    for i in (15, 16):
        dl = c[i] - c[i - 1]
        ag = (ag * 13 + max(dl, 0.0)) / 14
        av = (av * 13 + max(-dl, 0.0)) / 14
        werte[i] = 100 - 100 / (1 + ag / av) if av > 0 else 100.0
        print(f"    Balken {i}: delta {dl:+.2f} -> avgGain {ag:.4f}, "
              f"avgLoss {av:.4f} -> RSI = {werte[i]:.4f}")
    r_ta = ta.rsi(d["Close"], length=14)
    F, _ = f2.features_je_coin(
        [(int(t), float(o), float(h), float(l), float(cl))
         for t, o, h, l, cl in d[["Date", "Open", "High", "Low", "Close"]].values],
        {int(t): float(v_) for t, v_ in d[["Date", "Volume"]].values}, {})
    print(f"\n    {'Balken':>7s} {'Hand':>10s} {'pandas_ta':>10s} {'F2-Nachbau':>11s}")
    for i in (14, 15, 16):
        print(f"    {i:7d} {werte[i]:10.4f} {float(r_ta.iloc[i]):10.4f} "
              f"{F['rsi_14'][i]:11.4f}")
    print("    Hand und F2-Nachbau muessen exakt uebereinstimmen (gleiche")
    print("    Rekursion); pandas_ta weicht frueh ab, weil sein RMA als")
    print("    ewm(alpha=1/14) mit adjust=True startet und erst asymptotisch")
    print("    in die Wilder-Rekursion uebergeht.")
    sys.stdout.flush()


# ===========================================================================
# Teil 4: IC-Neuberechnung mit Projektimplementierung
# ===========================================================================
def ic_projekt(feature_ref, horizonte=(1, 4, 24)):
    """IC (Mittel der coinweisen Spearman) mit der REFERENZ-Serie, beide Jahre."""
    erg = {}
    for jahr, marke in (("J2", ""), ("J1", "_v1")):
        for h in horizonte:
            rhos = []
            for coin in COINS:
                d = df_1h(coin, marke)
                R = referenz_voll_cached(coin, marke)
                if d is None or R is None:
                    continue
                ref = R[feature_ref]
                cl = d["Close"]
                fw = cl.shift(-h) / cl - 1.0
                mask = ref.notna() & fw.notna()
                if int(mask.sum()) < 200:
                    continue
                from scipy.stats import spearmanr
                rho = float(spearmanr(ref[mask].values, fw[mask].values).statistic)
                rhos.append(rho)
            if rhos:
                erg[(jahr, h)] = sum(rhos) / len(rhos)
    return erg


def main():
    print("=" * 112)
    print(" MESSUNG G1 - SIND DIE F2-INDIKATOREN RICHTIG NACHGEBAUT?")
    print(f" pandas {pd.__version__} | numpy {np.__version__} | "
          f"pandas_ta {getattr(ta, 'version', getattr(ta, '__version__', '?'))}")
    print(" Referenz: die Projektimplementierungen selbst. Datenbasis wie F2")
    print(" (1h-Aggregate der gepruef ten 15m-CSVs).")
    print("=" * 112)

    # ---------------- G1a ----------------
    print("\n" + "=" * 112)
    print(" G1a  BEKANNTE ABWEICHUNGEN Nachbau vs. Projekt (vor jeder Zahl)")
    print("=" * 112)
    for txt in [
        "1. pump_5: app.py:747 rechnet close/Close.iloc[-5]-1 = 4 Balken",
        "   zurueck. F2-Nachbau: cl[i]/cl[i-5] = 5 Balken zurueck. OFF-BY-ONE.",
        "2. fib_dist_618: v4_strategies.py:46-47 nimmt tail(100) des",
        "   uebergebenen df. F2-Nachbau: rollende 120. FENSTERLAENGE 100 vs 120.",
        "3. rsi_div_bull: rsi_divergence.py:80-84 verlangt price2 <",
        "   price1*(1-1%) UND rsi2 > rsi1+2 und vergleicht NUR BENACHBARTE",
        "   Swing-Tiefs. F2-Nachbau: beliebige Paare, ohne Mindestschwung,",
        "   ohne RSI-Marge. LOGIK DEUTLICH VERSCHIEDEN.",
        "4. di_diff: F2 zitierte regime_detection.py:42 (ta.adx, Wilder),",
        "   nachgebaut wurde aber die SMA-Variante aus market_data.py:117.",
        "   FALSCHE PROJEKTVARIANTE ALS VORBILD.",
        "5. volatilitaet: indicators.py:36 rolling.std mit ddof=1;",
        "   F2-Nachbau ddof=0. Konstanter Faktor sqrt(13/14) - rangneutral.",
        "6. tsi: calc_tsi nutzt pandas ewm(span).mean() mit adjust=True;",
        "   F2-Nachbau rekursiv (adjust=False). Einschwingunterschied.",
        "7. EMA/MACD/RSI/ATR: pandas_ta-Seeds vs. SMA-Seed-Rekursion des",
        "   Nachbaus - erwartet klein, wird gemessen.",
        "8. obv_steig: eigene Konstruktion ohne Projektreferenz; nur OBV",
        "   selbst ist vergleichbar.",
        "9. Der Live-Bot rechnet ALLES auf einem 120-Balken-Fenster",
        "   (candle_limit); F2 rechnete auf der vollen Serie. Der",
        "   Warmup-Effekt wird in Teil 2 separat beziffert.",
    ]:
        print("  " + txt)

    # ---------------- G1b Vollserie ----------------
    print("\n" + "=" * 112)
    print(" G1b  VOLLSERIEN-ABGLEICH  -  11 Coins, Jahr 2, ab Balken 200")
    print("      (aggregiert: n-gewichtetes Mittel der Coin-Kennzahlen; 'max' = Maximum ueber Coins)")
    print("=" * 112)
    agg = {}
    for coin in COINS:
        d = df_1h(coin, "")
        if d is None:
            continue
        k1h = [(int(t), float(o), float(h), float(l), float(c))
               for t, o, h, l, c in d[["Date", "Open", "High", "Low", "Close"]].values]
        vol = {int(t): float(v) for t, v in d[["Date", "Volume"]].values}
        F, _cl = f2.features_je_coin(k1h, vol, lade_jahr("")[1])
        R = referenz_voll(d)
        for f2k, refk, quelle in PAARE:
            r = vergleiche(F[f2k], R[refk])
            if r is None:
                continue
            agg.setdefault((f2k, refk, quelle), []).append(r)
        # OBV separat
        r = vergleiche(
            f2.obv_steigung([k[4] for k in k1h], [vol.get(k[0], 0.0) for k in k1h], 20),
            R["obv"])
        # (Steigung vs. OBV ist NICHT vergleichbar - nur zur Doku nicht aggregiert)
    print(f"\n    {'F2-Feature':<14s} {'Referenz (Datei:Zeile)':<40s} "
          f"{'Pearson':>8s} {'Spearman':>9s} {'maxAbs':>10s} {'meanAbs':>10s} "
          f"{'Vorz%':>7s} {'Urteil':>10s}")
    print("    " + "-" * 112)
    auffaellig = []
    for (f2k, refk, quelle), rs in agg.items():
        n_sum = sum(r[5] for r in rs)
        pe = sum(r[0] * r[5] for r in rs) / n_sum
        spr = sum(r[1] * r[5] for r in rs) / n_sum
        mx = max(r[2] for r in rs)
        me = sum(r[3] * r[5] for r in rs) / n_sum
        vz = sum(r[4] * r[5] for r in rs) / n_sum
        auff = spr < AUFF_SPEARMAN or vz > AUFF_VORZ
        if auff:
            auffaellig.append((f2k, refk, spr, vz))
        print(f"    {f2k:<14s} {quelle:<40s} {pe:8.4f} {spr:9.4f} "
              f"{mx:10.2e} {me:10.2e} {vz:6.2f}% "
              f"{'AUFFAELLIG' if auff else 'ok':>10s}")
    print("\n  Ohne numerischen Referenzpfad:")
    for k, grund in OHNE_REFERENZ:
        print(f"    {k:<14s} {grund}")
    sys.stdout.flush()

    # ---------------- G1b Fenster ----------------
    print("\n" + "=" * 112)
    print(f" G1b-FENSTER  120-Balken-Fenster wie der Live-Bot  -  "
          f"{'/'.join(c.split('/')[0] for c in FENSTER_COINS)}, Jahr 2, "
          f"jede {SCHRITT_FENSTER}. Stunde")
    print("=" * 112)
    fen_agg = {}
    fen_coin = {}
    warm_agg = {}
    for coin in FENSTER_COINS:
        d = df_1h(coin, "")
        k1h = [(int(t), float(o), float(h), float(l), float(c))
               for t, o, h, l, c in d[["Date", "Open", "High", "Low", "Close"]].values]
        vol = {int(t): float(v) for t, v in d[["Date", "Volume"]].values}
        F, _ = f2.features_je_coin(k1h, vol, lade_jahr("")[1])
        out, warmup = fenster_vergleich(d, F)
        for k, (a, b) in out.items():
            fen_agg.setdefault(k, ([], []))
            fen_agg[k][0].extend(a)
            fen_agg[k][1].extend(b)
            fen_coin.setdefault(k, {})[coin] = (list(a), list(b))
        for k, (a, b) in warmup.items():
            warm_agg.setdefault(k, ([], []))
            warm_agg[k][0].extend(a)
            warm_agg[k][1].extend(b)

    print(f"\n    NACHBAU gegen PROJEKT-FENSTERAUFRUF")
    print(f"    {'Feature':<14s} {'n':>6s} {'Pearson':>8s} {'Spearman':>9s} "
          f"{'maxAbs':>10s} {'Vorz%/Diskr%':>13s} {'Urteil':>10s}")
    print("    " + "-" * 78)
    from scipy.stats import spearmanr
    for k, (a, b) in fen_agg.items():
        aa, bb_ = np.asarray(a), np.asarray(b)
        if k == "rsi_div_bull":
            # binaer: Uebereinstimmungsrate + Kontingenz
            gleich = float(np.mean(aa == bb_) * 100)
            beide1 = int(np.sum((aa == 1) & (bb_ == 1)))
            nur_nb = int(np.sum((aa == 1) & (bb_ == 0)))
            nur_pr = int(np.sum((aa == 0) & (bb_ == 1)))
            auff = (100 - gleich) > AUFF_VORZ
            print(f"    {k:<14s} {len(aa):6d} {'-':>8s} {'-':>9s} {'-':>10s} "
                  f"{100 - gleich:12.2f}% {'AUFFAELLIG' if auff else 'ok':>10s}")
            print(f"      Kontingenz: beide=1: {beide1} | nur Nachbau=1: {nur_nb} "
                  f"| nur Projekt=1: {nur_pr}")
            if auff:
                auffaellig.append((k, "rsi_divergence.detect", 0.0, 100 - gleich))
            continue
        pe = float(np.corrcoef(aa, bb_)[0, 1])
        spr = float(spearmanr(aa, bb_).statistic)
        vz = float(np.mean(np.sign(aa) != np.sign(bb_)) * 100)
        auff = spr < AUFF_SPEARMAN or vz > AUFF_VORZ
        if auff and k not in [x[0] for x in auffaellig]:
            auffaellig.append((k, "Fensteraufruf", spr, vz))
        print(f"    {k:<14s} {len(aa):6d} {pe:8.4f} {spr:9.4f} "
              f"{np.abs(aa - bb_).max():10.2e} {vz:12.2f}% "
              f"{'AUFFAELLIG' if auff else 'ok':>10s}")

    # vwap_rel je Coin: trennt Rundungsartefakt von echter Abweichung
    print("\n    vwap_rel AUFGESCHLUESSELT (Rundung in vwap_agent.py:64)")
    print(f"    {'Coin':<10s} {'Referenz':<26s} {'n':>6s} {'Spearman':>9s} "
          f"{'Vorz%':>7s}")
    print("    " + "-" * 62)
    for k, bez in (("vwap_rel", "Rueckgabefeld (gerundet)"),
                   ("vwap_rel_exakt", "Agentenformel (ungerundet)")):
        for coin in FENSTER_COINS:
            a, b = fen_coin.get(k, {}).get(coin, ([], []))
            if len(a) < 100:
                continue
            aa, bb2 = np.asarray(a), np.asarray(b)
            spr = float(spearmanr(aa, bb2).statistic)
            vz = float(np.mean(np.sign(aa) != np.sign(bb2)) * 100)
            print(f"    {coin.split('/')[0]:<10s} {bez:<26s} {len(a):6d} "
                  f"{spr:9.4f} {vz:6.2f}%")

    print(f"\n    WARMUP-EFFEKT: 120er-Fensterwert gegen Vollserienwert"
          f" (beides Projektweg)")
    print(f"    {'Feature':<14s} {'n':>6s} {'Pearson':>8s} {'Spearman':>9s} "
          f"{'maxAbs':>10s} {'meanAbs':>10s}")
    print("    " + "-" * 62)
    for k, (a, b) in warm_agg.items():
        aa, bb_ = np.asarray(a), np.asarray(b)
        pe = float(np.corrcoef(aa, bb_)[0, 1])
        spr = float(spearmanr(aa, bb_).statistic)
        print(f"    {k:<14s} {len(aa):6d} {pe:8.4f} {spr:9.4f} "
              f"{np.abs(aa - bb_).max():10.2e} {np.abs(aa - bb_).mean():10.2e}")
    print("    Spearman hier misst, wie stark die RANGordnung leidet, wenn")
    print("    man - wie der Live-Bot - nur 120 Balken Geschichte hat.")
    sys.stdout.flush()

    # ---------------- G1c Hand ----------------
    handrechnung_rsi(df_1h("BTC/USDC", ""))

    # ---------------- G1d ----------------
    print("\n" + "=" * 112)
    print(" G1d  IC-NEUBERECHNUNG mit der PROJEKTIMPLEMENTIERUNG"
          " (nur auffaellige Features)")
    print("=" * 112)
    print(f"\n  Auffaellig aus G1b: "
          f"{', '.join(sorted(set(x[0] for x in auffaellig))) or 'KEINES'}")
    neu = {}
    for f2k in sorted(set(x[0] for x in auffaellig)):
        refk = dict((a, b) for a, b, _q in PAARE).get(f2k)
        if refk is None:
            print(f"    {f2k}: kein vektorisierbarer Referenzpfad -> siehe"
                  " Fenstermessung; IC-Neuberechnung nicht moeglich:"
                  " NICHT ENTSCHEIDBAR")
            continue
        neu[f2k] = ic_projekt(refk)
    if neu:
        print(f"\n    {'Feature':<14s} {'Hor':>4s} {'IC J2 alt':>10s} "
              f"{'IC J2 NEU':>10s} {'IC J1 alt':>10s} {'IC J1 NEU':>10s}")
        print("    " + "-" * 66)
        alt = {
            # aus ausgaben/messung_f2_ic_out.txt
            ("pump_5", 1): (-0.0278, -0.0358),
            ("pump_5", 4): (-0.0234, -0.0118),
            ("pump_5", 24): (-0.0249, -0.0151),
            ("fib_dist_618", 1): (-0.0321, -0.0157),
            ("fib_dist_618", 4): (-0.0541, -0.0205),
            ("fib_dist_618", 24): (-0.0901, -0.0296),
            ("di_diff", 1): (-0.0184, -0.0096),
            ("di_diff", 4): (-0.0192, +0.0050),
            ("di_diff", 24): (-0.0135, -0.0012),
            ("vwap_rel", 1): (-0.0321, -0.0172),
            ("vwap_rel", 4): (-0.0580, -0.0217),
            ("vwap_rel", 24): (-0.0937, -0.0279),
            ("tsi", 1): (-0.0250, -0.0030),
            ("tsi", 4): (-0.0408, +0.0003),
            ("tsi", 24): (-0.0450, +0.0328),
            ("tsi_hist", 1): (-0.0186, -0.0191),
            ("tsi_hist", 4): (-0.0181, -0.0026),
            ("tsi_hist", 24): (-0.0087, -0.0170),
            ("rsi_14", 1): (-0.0331, -0.0232),
            ("rsi_14", 4): (-0.0390, -0.0087),
            ("rsi_14", 24): (-0.0457, +0.0152),
            ("stoch_rsi", 1): (-0.0257, -0.0328),
            ("stoch_rsi", 4): (-0.0102, -0.0068),
            ("stoch_rsi", 24): (-0.0086, -0.0127),
            ("bb_pos", 1): (-0.0314, -0.0272),
            ("bb_pos", 4): (-0.0315, -0.0058),
            ("bb_pos", 24): (-0.0327, -0.0060),
            ("p_vs_ema20", 1): (-0.0329, -0.0325),
            ("p_vs_ema20", 4): (-0.0370, -0.0196),
            ("p_vs_ema20", 24): (-0.0427, -0.0081),
        }
        for f2k, erg in neu.items():
            for h in (1, 4, 24):
                a2, a1 = alt.get((f2k, h), (float("nan"), float("nan")))
                n2 = erg.get(("J2", h), float("nan"))
                n1 = erg.get(("J1", h), float("nan"))
                print(f"    {f2k:<14s} {h:3d}h {a2:+10.4f} {n2:+10.4f} "
                      f"{a1:+10.4f} {n1:+10.4f}")
    print("\n  Bewertungsmassstab fuer das F2-Urteil: aendert sich fuer ein")
    print("  auffaelliges Feature |IC| auf >= 0,090 (oekonomische Schwelle der")
    print("  Reibungs-Untergrenze) oder kippt ein stabiler Befund das")
    print("  Vorzeichen, ist F2 zu KORRIGIEREN. Sonst BESTAETIGT.")
    print("\n" + "=" * 112)
    print(" ENDE G1")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    sys.exit(main())
