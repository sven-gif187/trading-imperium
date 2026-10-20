"""
STRATEGIE-LABOR  -  Was-waere-wenn-Analyse
==========================================
Rechnet auf den echten Kerzendaten durch, welche Stop-Loss- und
Trailing-Kombination in der aktuellen Marktphase pro Coin am besten
gewesen waere. REINE ANALYSE - kein Trading-Eingriff, aendert nichts
am Bot. Liefert nur einen Bericht zum Anschauen.

Vorbild: Freqtrade Hyperopt (vereinfacht, auf 1h-Kerzen).
"""
import os
import json
import pandas as pd

STOPS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.08]
TRAILS = [0.0, 0.01, 0.015, 0.02, 0.03]   # 0.0 = kein Trailing


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_trades(root):
    p = os.path.join(root, "data_store", "trades_v5.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    return d if isinstance(d, list) else d.get("trades", [])


def _pairs(trades, base):
    rel = []
    for t in trades:
        sym = str(t.get("symbol", t.get("coin", "")))
        if not sym.upper().startswith(base):
            continue
        ts = t.get("time", t.get("timestamp", ""))
        try:
            when = pd.to_datetime(ts, utc=True)
        except Exception:
            continue
        rel.append({
            "time": when,
            "price": float(t.get("price", 0) or 0),
            "qty": float(t.get("qty", 0) or 0),
            "side": "BUY" if "BUY" in str(t.get("side", t.get("type", ""))).upper() else "SELL",
        })
    rel.sort(key=lambda x: x["time"])
    open_b, pairs = [], []
    for t in rel:
        if t["side"] == "BUY":
            open_b.append(t)
        elif open_b:
            pairs.append((open_b.pop(0), t))
    return pairs


def _simulate(pairs, df, stop, trail):
    """Simuliert Stop + Trailing auf den Kerzen. Gibt Gesamt-P&L zurueck."""
    total = 0.0
    wins = 0
    n = 0
    for buy, sell in pairs:
        entry = buy["price"]
        qty = buy["qty"]
        if entry <= 0 or qty <= 0:
            continue
        seg = df[(df["t"] >= buy["time"]) & (df["t"] <= sell["time"])]
        if seg.empty:
            # kein Kerzen-Fenster: realer Ausgang
            pnl = (sell["price"] - entry) * qty
        else:
            exit_price = None
            highest = entry
            stop_price = entry * (1 - stop)
            for _, k in seg.iterrows():
                low = float(k["low"]); high = float(k["high"])
                # Stop-Loss zuerst pruefen (konservativ)
                if low <= stop_price:
                    exit_price = stop_price
                    break
                # Trailing nachziehen
                if trail > 0:
                    if high > highest:
                        highest = high
                        new_stop = highest * (1 - trail)
                        if new_stop > stop_price:
                            stop_price = new_stop
            if exit_price is None:
                exit_price = sell["price"]   # regulaerer Verkauf
            pnl = (exit_price - entry) * qty
        total += pnl
        n += 1
        if pnl > 0:
            wins += 1
    return total, wins, n


def analyse(symbol, chart_data, trades, root):
    base = symbol.split("/")[0].upper()
    pairs = _pairs(trades, base)
    if not pairs:
        return None
    try:
        rows = chart_data.load(symbol, interval="1h", days=90)
    except Exception:
        rows = []
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.sort_values("t").reset_index(drop=True)

    best = None
    grid = []
    for stop in STOPS:
        for trail in TRAILS:
            total, wins, n = _simulate(pairs, df, stop, trail)
            if n == 0:
                continue
            row = {"stop": stop, "trail": trail, "pnl": round(total, 2),
                   "wr": round(wins / n * 100, 1), "n": n}
            grid.append(row)
            if best is None or row["pnl"] > best["pnl"]:
                best = row
    return {"symbol": symbol, "pairs": len(pairs), "best": best, "grid": grid}


def run(symbols=None, root=None):
    root = root or _root()
    from features.chart_data import ChartData
    cd = ChartData(root)
    trades = _load_trades(root)
    if symbols is None:
        symbols = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "XRP/USDC", "ADA/USDC",
                   "AVAX/USDC", "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC",
                   "UNI/USDC", "ATOM/USDC"]
    out = []
    for s in symbols:
        r = analyse(s, cd, trades, root)
        if r and r["best"]:
            out.append(r)
    return out


def format_report(results, cur_stop=0.04, cur_trail=0.01):
    if not results:
        return ("Noch nicht genug abgeschlossene Trades pro Coin fuer eine\n"
                "verlaessliche Analyse. Bot weiter sammeln lassen.")
    lines = []
    lines.append("STRATEGIE-LABOR  -  Was waere optimal gewesen?")
    lines.append("=" * 62)
    lines.append(f"Aktuell im Bot:  Stop {cur_stop*100:.1f}%  |  Trailing {cur_trail*100:.1f}%")
    lines.append("Pro Coin: beste Stop+Trail-Kombi auf echten 1h-Kerzen")
    lines.append("")
    total_best = 0.0
    for r in sorted(results, key=lambda x: -x["best"]["pnl"]):
        b = r["best"]
        total_best += b["pnl"]
        # aktueller Vergleich
        cur = next((g for g in r["grid"]
                    if abs(g["stop"] - cur_stop) < 0.001 and abs(g["trail"] - cur_trail) < 0.001), None)
        cur_txt = f"  (aktuell waere {cur['pnl']:+.2f}$)" if cur else ""
        lines.append(f"{r['symbol']:<10} {r['pairs']:>2} Tr | BEST: Stop {b['stop']*100:.0f}% "
                     f"Trail {b['trail']*100:.1f}% -> {b['pnl']:+.2f}$ (WR {b['wr']}%)" + cur_txt)
    lines.append("")
    lines.append(f"Summe beste Kombis: {total_best:+.2f}$")
    lines.append("")
    lines.append("WICHTIG (Sensei): Das ist eine RUECKRECHNUNG auf vergangenen")
    lines.append("Kerzen (Naeherung, 1h). Sie zeigt die Richtung, ist KEINE")
    lines.append("Garantie fuer die Zukunft. Umsetzung erst zur Auswertung,")
    lines.append("mit mehr Daten - nicht jetzt im Affekt am Bot drehen!")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(run()))
