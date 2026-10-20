"""
Trading Imperium V5 – Indikator-Bibliothek
Alle technischen Indikatoren an einem Ort.
"""
import pandas as pd
import pandas_ta as ta
import numpy as np

def calc_all_indicators(df):
    """Berechnet alle Indikatoren auf einem DataFrame."""
    d = df.copy()
    d["RSI"] = ta.rsi(d["Close"], length=14)
    d["EMA20"] = ta.ema(d["Close"], length=20)
    d["EMA50"] = ta.ema(d["Close"], length=50)
    d["EMA200"] = ta.ema(d["Close"], length=200)
    d["ATR"] = ta.atr(d["High"], d["Low"], d["Close"], length=14)

    macd = ta.macd(d["Close"])
    if macd is not None:
        d["MACD"] = macd.iloc[:, 0]
        d["MACD_signal"] = macd.iloc[:, 2]
        d["MACD_hist"] = macd.iloc[:, 1]

    bb = ta.bbands(d["Close"], length=20, std=2)
    if bb is not None:
        for c in bb.columns: d[c] = bb[c]

    d["ADX"] = calc_adx(d)
    d["OBV"] = calc_obv(d)
    d["VWAP"] = calc_vwap(d)
    d["StochRSI"] = calc_stoch_rsi(d.get("RSI", pd.Series()))
    tsi, tsi_sig = calc_tsi(d["Close"])
    d["TSI"] = tsi; d["TSI_signal"] = tsi_sig

    # Zusätzliche Features für ML
    d["returns"] = d["Close"].pct_change()
    d["volatility"] = d["returns"].rolling(14).std()
    d["volume_sma"] = d["Volume"].rolling(20).mean()
    d["volume_ratio"] = d["Volume"] / (d["volume_sma"] + 1e-10)
    d["high_low_range"] = (d["High"] - d["Low"]) / (d["Close"] + 1e-10)
    d["close_to_ema20"] = (d["Close"] - d["EMA20"]) / (d["EMA20"] + 1e-10)

    return d

def calc_adx(df, period=14):
    try:
        h, l, c = df["High"], df["Low"], df["Close"]
        pdm = h.diff().clip(lower=0); mdm = (-l.diff()).clip(lower=0)
        tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        pdi = 100 * (pdm.rolling(period).mean() / atr)
        mdi = 100 * (mdm.rolling(period).mean() / atr)
        dx = (pdi - mdi).abs() / (pdi + mdi + 1e-10) * 100
        return dx.rolling(period).mean()
    except: return pd.Series([20]*len(df), index=df.index)

def calc_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i-1]: obv.append(obv[-1] + df["Volume"].iloc[i])
        elif df["Close"].iloc[i] < df["Close"].iloc[i-1]: obv.append(obv[-1] - df["Volume"].iloc[i])
        else: obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

def calc_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

def calc_stoch_rsi(rsi, period=14):
    if len(rsi) < period: return pd.Series([50]*len(rsi))
    mn = rsi.rolling(period).min(); mx = rsi.rolling(period).max()
    return ((rsi - mn) / (mx - mn + 1e-10)) * 100

def calc_tsi(close, long=25, short=13, signal=7):
    diff = close.diff()
    smooth1 = diff.ewm(span=long).mean().ewm(span=short).mean()
    smooth2 = diff.abs().ewm(span=long).mean().ewm(span=short).mean()
    tsi = 100 * (smooth1 / (smooth2 + 1e-10))
    sig = tsi.ewm(span=signal).mean()
    return tsi, sig
