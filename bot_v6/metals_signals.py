#!/usr/bin/env python3
"""
EDELMETALL-SIGNALE (Gold + Silber Analyse)
Reines Anschau-Tool. Handelt NICHT. Holt echte Gold/Silber-Preise
und zeigt Einstieg, Stop-Loss und Take-Profit fuer deine Trades.
"""
import sys

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"FEHLER: {e}")
    print("Installieren mit:  pip install yfinance pandas numpy")
    sys.exit(1)


METALLE = {
    "Gold":   "GC=F",
    "Silber": "SI=F",
}


def rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss.replace(0, 0.0001)
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyse(name, ticker):
    print("\n" + "=" * 60)
    print(f"  {name}  ({ticker})")
    print("=" * 60)

    try:
        df = yf.Ticker(ticker).history(period="1y")
    except Exception as e:
        print(f"  Fehler beim Laden: {e}")
        return

    if df is None or df.empty or len(df) < 60:
        print(f"  Zu wenig Daten")
        return

    close = df["Close"]
    price = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma50
    r = float(rsi(close).iloc[-1])
    a = float(atr(df).iloc[-1])
    support = float(df["Low"].tail(20).min())
    resistance = float(df["High"].tail(20).max())

    if sma50 > sma200:
        trend = "AUFWAERTS"
        trend_txt = "langfristig steigend (SMA50 ueber SMA200)"
    else:
        trend = "ABWAERTS"
        trend_txt = "langfristig fallend (SMA50 unter SMA200)"

    if r < 30:
        rsi_lage = "STARK UEBERVERKAUFT"
    elif r < 45:
        rsi_lage = "ueberverkauft / guenstig"
    elif r < 65:
        rsi_lage = "neutral"
    elif r < 70:
        rsi_lage = "leicht ueberkauft"
    else:
        rsi_lage = "STARK UEBERKAUFT"

    if r < 30:
        signal = "STARKER EINSTIEG"
        begruendung = "stark ueberverkauft - oft ein guter Boden"
    elif trend == "AUFWAERTS" and r < 45:
        signal = "EINSTIEG (Pullback)"
        begruendung = "Ruecksetzer im Aufwaertstrend - klassische Kaufzone"
    elif trend == "AUFWAERTS" and r < 65:
        signal = "HALTEN / NACHKAUFEN"
        begruendung = "Aufwaertstrend intakt, aber kein guenstiger Punkt"
    elif r > 70:
        signal = "WARTEN (ueberkauft)"
        begruendung = "ueberkauft - kein Einstieg, eher Gewinne sichern"
    else:
        signal = "WARTEN"
        begruendung = "kein klares Signal - abwarten"

    stop_loss = price - 2 * a
    sl_support = support * 0.99
    risiko = price - stop_loss
    take_profit = price + 2 * risiko

    print(f"  Aktueller Kurs:   {price:,.2f} $")
    print(f"  Trend:            {trend}  ({trend_txt})")
    print(f"  RSI (14):         {r:.0f}  ({rsi_lage})")
    print(f"  Volatilitaet ATR: {a:,.2f} $  (Tagesschwankung)")
    print(f"  Support (20T):    {support:,.2f} $")
    print(f"  Widerstand (20T): {resistance:,.2f} $")
    print()
    print(f"  >>> SIGNAL: {signal}")
    print(f"      {begruendung}")
    print()
    if signal.startswith("STARKER EINSTIEG") or signal.startswith("EINSTIEG"):
        print(f"  WENN DU JETZT KAUFST:")
        print(f"    Einstieg:     ~{price:,.2f} $")
        print(f"    Stop-Loss:     {stop_loss:,.2f} $   (-{risiko:,.2f}$ / -{risiko/price*100:.1f}%)")
        print(f"    Take-Profit:   {take_profit:,.2f} $   (+{2*risiko:,.2f}$ / +{2*risiko/price*100:.1f}%)")
        print(f"    (Chance-Risiko-Verhaeltnis 2:1)")
    else:
        print(f"  FALLS du spaeter einsteigst, als Orientierung:")
        print(f"    Stop-Loss-Idee: {stop_loss:,.2f} $  (2x ATR unter Kurs)")
        print(f"    oder knapp unter Support: {sl_support:,.2f} $")


def main():
    print("=" * 60)
    print("  EDELMETALL-SIGNALE  -  Gold & Silber")
    print("  (reines Analyse-Tool, kein Handel)")
    print("=" * 60)
    for name, ticker in METALLE.items():
        analyse(name, ticker)
    print("\n" + "=" * 60)
    print("  Hinweis: Orientierungs-Signale auf Tagesbasis,")
    print("  keine Anlageberatung. Du entscheidest selbst.")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())