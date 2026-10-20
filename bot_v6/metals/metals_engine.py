#!/usr/bin/env python3
"""
================================================================
  EDELMETALL-ENGINE (Gold + Silber)  -  Multi-Indikator-Scoring
================================================================
Reine Datenlogik. Faesst den Bot NICHT an, handelt NICHT.

SCORING (wie das Crypto-Brain): 6 Indikatoren voten, Summe = Score
  - Trend (SMA 50/200)
  - RSI (Momentum)
  - MACD (Momentum / Trendwende)
  - Bollinger Bands (Volatilitaet / Mean-Reversion)
  - Gold-Silber-Ratio (Relativ-Wert - edelmetall-spezifisch!)
  - Support/Resistance (Struktur)

Score -> Signal (STARKER EINSTIEG / EINSTIEG / HALTEN / WARTEN)
Tracking speichert die Indikator-Werte mit (fuer Lernen Phase 2).

Eigene Datei (metals_journal.json) - kein Bot-State betroffen.
================================================================
"""
import os
import sys
import json
from datetime import datetime, timezone

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"FEHLER: {e}")
    print("Installieren mit:  pip install yfinance pandas numpy")
    sys.exit(1)


JOURNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "metals_journal.json")

METALLE = {
    "Gold":   "GC=F",
    "Silber": "SI=F",
}


# ----------------------------------------------------------------
# Indikatoren
# ----------------------------------------------------------------
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


def macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(close, period=20, n_std=2):
    ma = close.rolling(period).mean()
    sd = close.rolling(period).std()
    upper = ma + n_std * sd
    lower = ma - n_std * sd
    return upper, ma, lower


# ----------------------------------------------------------------
# Scoring: jeder Indikator votet (Punkte + Begruendung)
# ----------------------------------------------------------------
def _score_indicators(name, df, gs_ratio):
    close = df["Close"]
    price = float(close.iloc[-1])
    votes = []  # (Indikator, Punkte, Text)

    # 1. TREND (SMA 50/200)
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma50
    if sma50 > sma200:
        votes.append(("Trend", 2, "Aufwaertstrend (SMA50>200)"))
    else:
        votes.append(("Trend", -1, "Abwaertstrend (SMA50<200)"))

    # 2. RSI (Momentum)
    r = float(rsi(close).iloc[-1])
    if r < 30:
        votes.append(("RSI", 2, f"stark ueberverkauft ({r:.0f})"))
    elif r < 45:
        votes.append(("RSI", 1, f"guenstig ({r:.0f})"))
    elif r < 65:
        votes.append(("RSI", 0, f"neutral ({r:.0f})"))
    elif r < 70:
        votes.append(("RSI", -1, f"leicht ueberkauft ({r:.0f})"))
    else:
        votes.append(("RSI", -2, f"ueberkauft ({r:.0f})"))

    # 3. MACD (Momentum / Trendwende)
    macd_line, signal_line, hist = macd(close)
    m_now = float(macd_line.iloc[-1])
    s_now = float(signal_line.iloc[-1])
    h_now = float(hist.iloc[-1])
    h_prev = float(hist.iloc[-2]) if len(hist) > 1 else h_now
    if m_now > s_now and h_now > h_prev:
        votes.append(("MACD", 2, "bullishe Wende"))
    elif m_now > s_now:
        votes.append(("MACD", 1, "positiv"))
    else:
        votes.append(("MACD", -1, "negativ"))

    # 4. BOLLINGER (Volatilitaet / Mean-Reversion)
    upper, mid, lower = bollinger(close)
    u, m, l = float(upper.iloc[-1]), float(mid.iloc[-1]), float(lower.iloc[-1])
    if price <= l:
        votes.append(("Bollinger", 2, "am unteren Band (guenstig)"))
    elif price < m:
        votes.append(("Bollinger", 1, "unter Mittellinie"))
    elif price >= u:
        votes.append(("Bollinger", -2, "am oberen Band (teuer)"))
    else:
        votes.append(("Bollinger", 0, "ueber Mittellinie"))

    # 5. GOLD-SILBER-RATIO (Relativ-Wert)
    if gs_ratio is not None:
        if name == "Silber":
            if gs_ratio > 80:
                votes.append(("G/S-Ratio", 2, f"Silber billig (Ratio {gs_ratio:.0f})"))
            elif gs_ratio > 65:
                votes.append(("G/S-Ratio", 1, f"Silber eher billig (Ratio {gs_ratio:.0f})"))
            elif gs_ratio < 50:
                votes.append(("G/S-Ratio", -1, f"Silber teuer (Ratio {gs_ratio:.0f})"))
            else:
                votes.append(("G/S-Ratio", 0, f"Ratio neutral ({gs_ratio:.0f})"))
        else:  # Gold
            if gs_ratio < 50:
                votes.append(("G/S-Ratio", 2, f"Gold billig (Ratio {gs_ratio:.0f})"))
            elif gs_ratio < 60:
                votes.append(("G/S-Ratio", 1, f"Gold eher billig (Ratio {gs_ratio:.0f})"))
            elif gs_ratio > 80:
                votes.append(("G/S-Ratio", -1, f"Gold teuer (Ratio {gs_ratio:.0f})"))
            else:
                votes.append(("G/S-Ratio", 0, f"Ratio neutral ({gs_ratio:.0f})"))

    # 6. SUPPORT/RESISTANCE (Struktur)
    support = float(df["Low"].tail(20).min())
    resistance = float(df["High"].tail(20).max())
    if price <= support * 1.03:
        votes.append(("S/R", 1, "nahe Support"))
    elif price >= resistance * 0.97:
        votes.append(("S/R", -1, "nahe Widerstand"))
    else:
        votes.append(("S/R", 0, "mittig in der Range"))

    score = sum(v[1] for v in votes)
    return {
        "score": score, "votes": votes,
        "price": price, "rsi": r,
        "sma50": sma50, "sma200": sma200,
        "trend": "AUFWAERTS" if sma50 > sma200 else "ABWAERTS",
        "support": support, "resistance": resistance,
        "boll_upper": u, "boll_lower": l,
    }


# ----------------------------------------------------------------
# Analyse (gibt ein dict zurueck - UI-ready)
# ----------------------------------------------------------------
def analyze_metal(name, ticker, df=None, gs_ratio=None):
    if df is None:
        try:
            df = yf.Ticker(ticker).history(period="1y")
        except Exception as e:
            return {"name": name, "ticker": ticker, "error": str(e)}

    if df is None or df.empty or len(df) < 60:
        return {"name": name, "ticker": ticker,
                "error": f"zu wenig Daten ({0 if df is None else len(df)})"}

    sc = _score_indicators(name, df, gs_ratio)
    price = sc["price"]
    score = sc["score"]
    a = float(atr(df).iloc[-1])

    if score >= 6:
        signal = "STARKER EINSTIEG"
        reason = f"viele Indikatoren bullish (Score {score})"
    elif score >= 3:
        signal = "EINSTIEG"
        reason = f"ueberwiegend bullish (Score {score})"
    elif score >= 0:
        signal = "HALTEN"
        reason = f"gemischt (Score {score})"
    else:
        signal = "WARTEN"
        reason = f"ueberwiegend bearish (Score {score})"

    # STUFE-2: Trendfilter - kein Einstieg gegen bestaetigten Abwaertstrend
    # (SMA50<SMA200). Verhindert Dip-Kaeufe ins fallende Messer.
    if sc["trend"] == "ABWAERTS" and signal in ("EINSTIEG", "STARKER EINSTIEG"):
        signal = "WARTEN"
        reason = f"Abwaertstrend (SMA50<SMA200) - kein Einstieg trotz Score {score}"

    # STUFE-3: Richtung bestimmen. LONG kommt aus der Score-Logik oben.
    # Im bestaetigten Abwaertstrend ggf. SHORT statt nur WARTEN - aber nur
    # wenn der Kurs in eine Verkaufszone hochgelaufen ist (kein Short am
    # ueberverkauften Boden).
    direction = "LONG" if (signal.startswith("EINSTIEG") or signal.startswith("STARKER")) else None
    if sc["trend"] == "ABWAERTS":
        boll_mid = (sc["boll_lower"] + sc["boll_upper"]) / 2.0
        rallied = (price >= boll_mid) or (price >= sc["resistance"] * 0.97)
        if rallied and sc["rsi"] >= 50:
            signal = "SHORT EINSTIEG"
            reason = f"Abwaertstrend + Kurs in Verkaufszone (RSI {sc['rsi']:.0f}) - Short"
            direction = "SHORT"

    # Richtungsabhaengige SL/TP: SHORT spiegelt (Stop ueber, Ziel unter).
    if direction == "SHORT":
        stop_loss = price + 2 * a
        risk = stop_loss - price
        take_profit = price - 2 * risk
    else:
        stop_loss = price - 2 * a
        risk = price - stop_loss
        take_profit = price + 2 * risk

    return {
        "name": name, "ticker": ticker,
        "price": round(price, 2), "trend": sc["trend"],
        "rsi": round(sc["rsi"], 1), "atr": round(a, 2),
        "support": round(sc["support"], 2), "resistance": round(sc["resistance"], 2),
        "score": score, "votes": sc["votes"],
        "gs_ratio": round(gs_ratio, 1) if gs_ratio else None,
        "signal": signal, "reason": reason,
        "direction": direction,
        "entry": round(price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "is_entry": direction is not None,
        "df": df,
    }


def analyze_all():
    """Holt beide Metalle, berechnet Gold-Silber-Ratio, analysiert beide."""
    dfs = {}
    for name, ticker in METALLE.items():
        try:
            dfs[name] = yf.Ticker(ticker).history(period="1y")
        except Exception:
            dfs[name] = None

    gs_ratio = None
    try:
        gp = float(dfs["Gold"]["Close"].iloc[-1])
        sp = float(dfs["Silber"]["Close"].iloc[-1])
        if sp > 0:
            gs_ratio = gp / sp
    except Exception:
        gs_ratio = None

    analyses = [analyze_metal(n, t, df=dfs.get(n), gs_ratio=gs_ratio)
                for n, t in METALLE.items()]
    return analyses, gs_ratio


# ----------------------------------------------------------------
# Journal (eigene Datei)
# ----------------------------------------------------------------
def _load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return {"signals": []}
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"signals": []}


def _save_journal(data):
    try:
        tmp = JOURNAL_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, JOURNAL_FILE)
    except Exception as e:
        print(f"  [WARN] Journal speichern fehlgeschlagen: {e}")


# ----------------------------------------------------------------
# Tracking
# ----------------------------------------------------------------
def _check_open_signal(sig, df):
    try:
        entry_dt = pd.to_datetime(sig["entry_date"]).date()
    except Exception:
        return None
    sl = sig["stop_loss"]
    tp = sig["take_profit"]
    entry = sig["entry_price"]
    direction = sig.get("direction", "LONG")  # STUFE-3: alte Signale = LONG
    for ts, row in df.iterrows():
        try:
            d = ts.date()
        except Exception:
            continue
        if d <= entry_dt:
            continue
        low = float(row["Low"])
        high = float(row["High"])
        if direction == "SHORT":
            # SHORT: Stop ueber Einstieg (Verlust bei Anstieg), Ziel darunter (Gewinn bei Fall)
            if high >= sl:
                return {"status": "LOSS", "close_date": str(d), "close_price": sl,
                        "pnl_pct": round((entry - sl) / entry * 100, 2)}
            if low <= tp:
                return {"status": "WIN", "close_date": str(d), "close_price": tp,
                        "pnl_pct": round((entry - tp) / entry * 100, 2)}
        else:
            if low <= sl:
                return {"status": "LOSS", "close_date": str(d), "close_price": sl,
                        "pnl_pct": round((sl / entry - 1) * 100, 2)}
            if high >= tp:
                return {"status": "WIN", "close_date": str(d), "close_price": tp,
                        "pnl_pct": round((tp / entry - 1) * 100, 2)}
    return None


def track_signals(analyses):
    journal = _load_journal()
    today = datetime.now(timezone.utc).date()
    df_by_name = {a["name"]: a.get("df") for a in analyses if "df" in a}

    for sig in journal["signals"]:
        if sig.get("status") != "OFFEN":
            continue
        df = df_by_name.get(sig["name"])
        if df is None:
            continue
        result = _check_open_signal(sig, df)
        if result:
            sig.update(result)

    neu = 0
    for a in analyses:
        if not a.get("is_entry"):
            continue
        has_open = any(s["name"] == a["name"] and s.get("status") == "OFFEN"
                       for s in journal["signals"])
        if has_open:
            continue
        votes_snapshot = {v[0]: v[1] for v in a.get("votes", [])}
        journal["signals"].append({
            "id": f"{a['name']}_{today}",
            "name": a["name"], "ticker": a["ticker"],
            "signal_type": a["signal"],
            "direction": a.get("direction", "LONG"),
            "score": a.get("score"),
            "indicators": votes_snapshot,
            "entry_date": str(today),
            "entry_price": a["entry"],
            "stop_loss": a["stop_loss"],
            "take_profit": a["take_profit"],
            "status": "OFFEN",
        })
        neu += 1

    _save_journal(journal)
    return journal, neu


def get_stats(journal):
    sigs = journal["signals"]
    closed = [s for s in sigs if s.get("status") in ("WIN", "LOSS")]
    wins = [s for s in closed if s["status"] == "WIN"]
    losses = [s for s in closed if s["status"] == "LOSS"]
    open_sigs = [s for s in sigs if s.get("status") == "OFFEN"]
    total_pnl = sum(s.get("pnl_pct", 0) for s in closed)
    win_rate = (len(wins) / len(closed) * 100) if closed else 0
    return {
        "total": len(sigs), "open": len(open_sigs), "closed": len(closed),
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(win_rate, 1), "total_pnl_pct": round(total_pnl, 2),
        "open_signals": open_sigs, "closed_signals": closed,
    }


def export_csv(journal):
    """Schreibt alle Signale in eine CSV (zum Recherchieren in Excel)."""
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "metals_signals_log.csv")
    try:
        import csv
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Metall", "Signal-Typ", "Score", "Einstieg-Datum",
                        "Einstieg-Preis", "Stop-Loss", "Take-Profit", "Status",
                        "Schluss-Datum", "Schluss-Preis", "Ergebnis %", "Indikatoren"])
            for s in journal["signals"]:
                ind = s.get("indicators", {})
                ind_txt = " ".join(f"{k}:{v:+d}" for k, v in ind.items()) if ind else ""
                w.writerow([
                    s.get("name", ""), s.get("signal_type", ""), s.get("score", ""),
                    s.get("entry_date", ""), s.get("entry_price", ""),
                    s.get("stop_loss", ""), s.get("take_profit", ""),
                    s.get("status", ""), s.get("close_date", ""),
                    s.get("close_price", ""), s.get("pnl_pct", ""), ind_txt,
                ])
        return csv_file
    except Exception as e:
        print(f"  [WARN] CSV-Export fehlgeschlagen: {e}")
        return None


# ----------------------------------------------------------------
# Konsolen-Report (zum Testen)
# ----------------------------------------------------------------
def main():
    print("=" * 64)
    print("  EDELMETALL-ENGINE  -  Multi-Indikator-Scoring")
    print("=" * 64)

    analyses, gs_ratio = analyze_all()
    if gs_ratio:
        print(f"\n  Gold-Silber-Ratio: {gs_ratio:.1f}")

    for a in analyses:
        print(f"\n  {a['name']} ({a['ticker']})")
        if a.get("error"):
            print(f"    Fehler: {a['error']}")
            continue
        print(f"    Kurs {a['price']:,.2f}$ | Trend {a['trend']} | RSI {a['rsi']:.0f}")
        print(f"    Indikatoren:")
        for ind, pts, txt in a["votes"]:
            print(f"      {ind:<11} {pts:+d}  {txt}")
        print(f"    => SCORE {a['score']}  =>  {a['signal']}")
        if a["is_entry"]:
            print(f"       Einstieg ~{a['entry']:,.2f}$ | "
                  f"SL {a['stop_loss']:,.2f}$ | TP {a['take_profit']:,.2f}$")

    journal, neu = track_signals(analyses)
    if neu:
        print(f"\n  [TRACKING] {neu} neues Signal aufgenommen")
    csv_path = export_csv(journal)
    if csv_path:
        print(f"  [CSV] {os.path.basename(csv_path)}")

    stats = get_stats(journal)
    print("\n" + "=" * 64)
    print("  SIGNAL-PERFORMANCE")
    print("=" * 64)
    print(f"  gesamt {stats['total']} (offen {stats['open']}, "
          f"geschlossen {stats['closed']})")
    if stats["closed"]:
        print(f"  Trefferquote {stats['win_rate']:.0f}% | "
              f"{stats['wins']}W/{stats['losses']}L | "
              f"Summe {stats['total_pnl_pct']:+.2f}%")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
