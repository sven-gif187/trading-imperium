"""
STOP-LOSS-EDGE-ANALYSE  -  Baustein 4
======================================
Findet pro Coin den besten Stop-Loss-Wert, indem die echten Trades
gegen die echten Kerzendaten (Tiefkurse!) durchgerechnet werden.

Vorbild: Freqtrade 'Edge Positioning'. Fuer jeden Kauf wird im
Chart nachgeschaut, wie tief der Kurs danach fiel, und simuliert,
ob ein Stop bei X% ausgeloest haette - und mit welchem Ergebnis.

Reine Analyse, KEIN Trading-Eingriff. Liefert einen Vorschlag an
den Menschen, kein automatischer Eingriff.
"""
import os
import json

import pandas as pd

STOPS = [0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.08]


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_trades(root):
    path = os.path.join(root, "data_store", "trades_v5.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d if isinstance(d, list) else d.get("trades", [])


def _pair_trades(trades, base):
    """Bildet Kauf->Verkauf-Paare fuer einen Coin (FIFO, vereinfacht)."""
    relevant = []
    for t in trades:
        sym = str(t.get("symbol", t.get("coin", "")))
        if not sym.upper().startswith(base):
            continue
        ts = t.get("time", t.get("timestamp", ""))
        try:
            when = pd.to_datetime(ts, utc=True)
        except Exception:
            continue
        relevant.append({
            "time": when,
            "price": float(t.get("price", 0) or 0),
            "qty": float(t.get("qty", 0) or 0),
            "side": "BUY" if "BUY" in str(t.get("side", t.get("type", ""))).upper() else "SELL",
            "pnl": float(t.get("pnl") or 0),
        })
    relevant.sort(key=lambda x: x["time"])
    # FIFO-Paarung: jeder Verkauf schliesst den aeltesten offenen Kauf
    open_buys = []
    pairs = []
    for t in relevant:
        if t["side"] == "BUY":
            open_buys.append(t)
        elif open_buys:
            buy = open_buys.pop(0)
            pairs.append((buy, t))
    return pairs


def analyse_coin(symbol, chart_data, trades, root):
    base = symbol.split("/")[0].upper()
    pairs = _pair_trades(trades, base)
    if not pairs:
        return None

    # Kerzen laden (1h, genug Historie)
    try:
        rows = chart_data.load(symbol, interval="1h", days=90)
    except Exception:
        rows = []
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.sort_values("t").reset_index(drop=True)

    def lowest_between(t_start, t_end):
        seg = df[(df["t"] >= t_start) & (df["t"] <= t_end)]
        if seg.empty:
            return None
        return float(seg["low"].min())

    results = {}
    for stop in STOPS:
        total = 0.0
        wins = 0
        losses = 0
        for buy, sell in pairs:
            entry = buy["price"]
            qty = buy["qty"]
            if entry <= 0 or qty <= 0:
                continue
            stop_price = entry * (1 - stop)
            low = lowest_between(buy["time"], sell["time"])
            if low is not None and low <= stop_price:
                # Stop haette ausgeloest: Verlust = stop% des Einsatzes
                pnl = -(entry * qty) * stop
            else:
                # Stop nicht ausgeloest: realer Trade-Ausgang
                pnl = sell["price"] * qty - entry * qty
            total += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
        n = wins + losses
        results[stop] = {
            "total_pnl": round(total, 2),
            "win_rate": round(wins / n * 100, 1) if n else 0,
            "trades": n,
            "expectancy": round(total / n, 3) if n else 0,
        }
    # Bester Stop = hoechste Expectancy
    best = max(results, key=lambda s: results[s]["expectancy"])
    return {"symbol": symbol, "pairs": len(pairs), "results": results, "best": best}


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
        r = analyse_coin(s, cd, trades, root)
        if r:
            out.append(r)
    return out


def format_report(results, current_stop=0.032):
    """Erzeugt einen lesbaren Text-Report."""
    if not results:
        return "Keine Trade-Paare gefunden - der Bot braucht erst mehr abgeschlossene Trades."
    lines = []
    lines.append("STOP-LOSS-EDGE-ANALYSE  (Vorbild Freqtrade Edge)")
    lines.append("=" * 60)
    lines.append(f"Aktueller Stop-Loss im Bot: {current_stop*100:.1f}%")
    lines.append("Pro Coin: welcher Stop haette die beste Expectancy gehabt?")
    lines.append("(Expectancy = erwarteter Gewinn pro Trade)")
    lines.append("")
    for r in sorted(results, key=lambda x: -x["results"][x["best"]]["expectancy"]):
        best = r["best"]
        b = r["results"][best]
        cur = r["results"].get(round(current_stop, 3))
        cur_txt = ""
        if cur:
            cur_txt = f" | aktuell {current_stop*100:.1f}%: Exp {cur['expectancy']:+.3f}$"
        flag = ""
        if cur and b["expectancy"] > cur["expectancy"] + 0.02:
            flag = "  <== anderer Stop waere besser!"
        lines.append(f"{r['symbol']:<10} {r['pairs']:>2} Trades | bester Stop "
                     f"{best*100:.1f}% (Exp {b['expectancy']:+.3f}$, WR {b['win_rate']}%)"
                     f"{cur_txt}{flag}")
    lines.append("")
    lines.append("WICHTIG: Naeherung auf 1h-Kerzen - grobe Richtung, kein exakter")
    lines.append("Backtest. Entscheidung erst bei der Auswertung, mit mehr Daten.")
    return "\n".join(lines)


if __name__ == "__main__":
    res = run()
    print(format_report(res))
