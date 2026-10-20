"""
P&L-Check: Wann und wo entstand das Minus?
Einfach ausfuehren:
  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\pnl_check.py"
Reine Analyse - aendert nichts.
"""
import os, json
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_journal():
    p = os.path.join(ROOT, "data_store", "trades_v5.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, list) and d:
                return d
        except Exception:
            pass
    return from_orders()


def from_orders():
    oh = os.path.join(ROOT, "data_store", "order_history.json")
    if not os.path.exists(oh):
        return []
    with open(oh, encoding="utf-8") as f:
        d = json.load(f)
    orders = d if isinstance(d, list) else d.get("orders", d.get("trades", []))
    orders = [o for o in orders if str(o.get("status", "filled")) == "filled"]
    orders.sort(key=lambda o: float(o.get("created_at", 0) or 0))
    lots, journal = {}, []
    for o in orders:
        sym = o.get("symbol", o.get("coin", "?"))
        side = str(o.get("side", o.get("type", ""))).upper()
        price = float(o.get("fill_price", o.get("price", 0)) or 0)
        qty = float(o.get("fill_qty", o.get("qty", 0)) or 0)
        fee = float(o.get("fee", 0) or 0)
        t = o.get("created_at", o.get("time", ""))
        try:
            tiso = datetime.fromtimestamp(float(t), timezone.utc).isoformat() if not isinstance(t, str) else t
        except Exception:
            tiso = str(t)
        if qty <= 0 or price <= 0:
            continue
        if "BUY" in side:
            cost_per = (price * qty + fee) / qty if qty else price
            lots.setdefault(sym, []).append([qty, cost_per])
        elif "SELL" in side:
            proceeds = price * qty - fee
            remaining, cost = qty, 0.0
            cl = lots.get(sym, [])
            while remaining > 1e-12 and cl:
                lq, lc = cl[0]
                take = min(remaining, lq)
                cost += take * lc
                lq -= take; remaining -= take
                if lq <= 1e-12: cl.pop(0)
                else: cl[0][0] = lq
            journal.append({"type": "SELL", "coin": sym, "time": tiso, "pnl": round(proceeds - cost, 4)})
    return journal


def day(t):
    s = str(t)
    return s[:10] if len(s) >= 10 else "?"


def main():
    trades = load_journal()
    sells = [t for t in trades if str(t.get("type", "")).upper() == "SELL"
             and isinstance(t.get("pnl"), (int, float))]
    if not sells:
        print("Keine abgeschlossenen Verkaeufe gefunden.")
        return
    per_day = defaultdict(lambda: {"pnl": 0.0, "n": 0, "w": 0})
    per_coin = defaultdict(lambda: {"pnl": 0.0, "n": 0, "w": 0})
    for s in sells:
        d = day(s.get("time", "")); c = str(s.get("coin", "?")).split("/")[0]; p = s["pnl"]
        per_day[d]["pnl"] += p; per_day[d]["n"] += 1; per_day[d]["w"] += 1 if p > 0 else 0
        per_coin[c]["pnl"] += p; per_coin[c]["n"] += 1; per_coin[c]["w"] += 1 if p > 0 else 0

    print("=" * 56)
    print("  P&L-ZEITSTRAHL  -  Wann/wo entstand das Minus?")
    print("=" * 56)
    print(f"\n  {len(sells)} abgeschlossene Verkaeufe\n")
    print("  PRO TAG (chronologisch + laufender Saldo):")
    print(f"  {'Datum':<12}{'P&L':>9}{'Saldo':>9}{'Trd':>5}{'WR':>5}")
    print("  " + "-" * 40)
    run = 0.0
    for d in sorted(per_day.keys()):
        v = per_day[d]; run += v["pnl"]
        wr = int(v["w"] / v["n"] * 100) if v["n"] else 0
        print(f"  {d:<12}{v['pnl']:>+9.2f}{run:>+9.2f}{v['n']:>5}{wr:>4}%")
    print("\n  PRO COIN (wer blutet zuerst):")
    print(f"  {'Coin':<8}{'P&L':>9}{'Trd':>5}{'WR':>5}")
    print("  " + "-" * 27)
    for c in sorted(per_coin.keys(), key=lambda x: per_coin[x]["pnl"]):
        v = per_coin[c]
        wr = int(v["w"] / v["n"] * 100) if v["n"] else 0
        print(f"  {c:<8}{v['pnl']:>+9.2f}{v['n']:>5}{wr:>4}%")
    total = sum(v["pnl"] for v in per_coin.values())
    print("  " + "-" * 27)
    print(f"  {'GESAMT':<8}{total:>+9.2f}")
    worst = min(per_day.items(), key=lambda x: x[1]["pnl"])
    best = max(per_day.items(), key=lambda x: x[1]["pnl"])
    print(f"\n  Schlechtester Tag: {worst[0]} ({worst[1]['pnl']:+.2f}$)")
    print(f"  Bester Tag:        {best[0]} ({best[1]['pnl']:+.2f}$)")
    print("\n  HINWEIS: Nur REALISIERTE Verkaeufe. Offene Positionen")
    print("  (unrealisiert) schwanken und sind hier nicht drin.")
    print()


if __name__ == "__main__":
    main()
