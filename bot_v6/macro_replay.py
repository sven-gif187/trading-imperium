# -*- coding: utf-8 -*-
"""
macro_replay.py - Beweis-Schritt fuer die Zyklus-These
=======================================================
Frage: Sagt "aehnliche Makro-Situation in der Vergangenheit" den
Forward-Return voraus? (Kern der 4-Jahres-Zyklus-Hypothese)

Methode (streng ohne Lookahead):
  1. situation_history.json laden (aus history_harvester.py).
  2. Fuer jeden Tag ab Warmup: k aehnlichste FRUEHERE Tage suchen.
     WICHTIG: Mindestabstand (--gap, Standard 30 Tage), sonst matcht
     das Gedaechtnis nur "gestern" und misst Trivial-Persistenz
     statt Zyklus-Wiederholung.
  3. Vorhersage = Oe Forward-Return der Nachbarn; Vergleich mit echtem
     Forward-Return: Korrelation, Richtungs-Trefferquote vs Baseline,
     und die Geld-Frage: Top-20%-Vorhersagen vs Flop-20%-Vorhersagen.

Nutzung (V6-Hauptordner):
    python macro_replay.py
    python macro_replay.py --k 20 --gap 30 --horizon fwd_30d
"""
import os
import sys
import json
import math
import argparse
from datetime import datetime

# Numerische Makro-Features: (key, normierung, gewicht)
FEATURES = [
    ("mayer",        1.0, 1.5),
    ("drawdown_ath", 60.0, 1.5),
    ("ret_30d",      40.0, 1.0),
    ("ret_90d",      80.0, 1.0),
    ("vol30",         4.0, 0.75),
    ("rsi",         100.0, 0.75),
    ("fear_greed",  100.0, 1.0),
]
W_TREND = 1.0  # kategorisch: sma_trend


def distance(f1, f2):
    total = 0.0
    wsum = 0.0
    for key, norm, w in FEATURES:
        v1, v2 = f1.get(key), f2.get(key)
        if v1 is None or v2 is None:
            continue
        d = (float(v1) - float(v2)) / norm
        total += w * d * d
        wsum += w
    t1, t2 = f1.get("sma_trend"), f2.get("sma_trend")
    if t1 and t2:
        total += W_TREND * (0.0 if t1 == t2 else 1.0)
        wsum += W_TREND
    if wsum <= 0:
        return None
    return math.sqrt(total / wsum)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / (vx ** 0.5 * vy ** 0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", default="")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--gap", type=int, default=30,
                    help="Mindestabstand der Nachbarn in Tagen")
    ap.add_argument("--warmup", type=int, default=365,
                    help="erste N Tage nur als Gedaechtnis, nicht bewertet")
    ap.add_argument("--horizon", default="fwd_30d",
                    choices=["fwd_7d", "fwd_30d", "fwd_90d"])
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    path = args.history or os.path.join(base, "data_store", "situation_history.json")
    if not os.path.exists(path):
        print(f"FEHLER: {path} nicht gefunden. Erst history_harvester.py laufen lassen.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    days = data.get("days", [])
    days = [d for d in days if d.get("outcome", {}).get(args.horizon) is not None]
    print(f"Historie: {path}")
    print(f"{len(days)} Tage mit {args.horizon}-Outcome | k={args.k} | "
          f"Gap={args.gap}d | Warmup={args.warmup}d")

    preds, actuals, dates, phases = [], [], [], []
    for i in range(args.warmup, len(days)):
        target = days[i]
        cutoff = i - args.gap
        if cutoff <= 0:
            continue
        cands = []
        tf = target["features"]
        for j in range(cutoff):
            d = distance(tf, days[j]["features"])
            if d is not None:
                cands.append((d, days[j]["outcome"][args.horizon]))
        if len(cands) < args.k:
            continue
        cands.sort(key=lambda x: x[0])
        neigh = [o for _, o in cands[:args.k]]
        preds.append(sum(neigh) / len(neigh))
        actuals.append(target["outcome"][args.horizon])
        dates.append(target["date"])
        phases.append(target.get("phase", "?"))

    n = len(preds)
    if n < 100:
        print("Zu wenig bewertbare Tage.")
        sys.exit(0)

    # --- Kernmetriken ---
    base_up = sum(1 for a in actuals if a > 0) / n
    hit = sum(1 for p, a in zip(preds, actuals)
              if (p > 0) == (a > 0)) / n
    corr = pearson(preds, actuals)

    # --- Die Geld-Frage: Top vs Flop der Vorhersagen ---
    order = sorted(range(n), key=lambda i: preds[i])
    q = max(1, n // 5)
    flop = [actuals[i] for i in order[:q]]
    top = [actuals[i] for i in order[-q:]]
    flop_avg = sum(flop) / len(flop)
    top_avg = sum(top) / len(top)

    print("\n" + "=" * 62)
    print(f"MAKRO-REPLAY ({args.horizon}, kein Lookahead, Gap {args.gap}d)")
    print("=" * 62)
    print(f"Bewertete Tage:              {n}")
    print(f"Richtungs-Trefferquote:      {hit*100:.1f}%")
    print(f"Baseline 'immer aufwaerts':  {base_up*100:.1f}%")
    print(f"Korrelation Pred vs Real:    {corr:+.3f}   (>= +0.2 = echtes Signal)")
    print("\nDie Geld-Frage (je Top/Flop-20% der Vorhersagen):")
    print(f"  Top-Vorhersagen    -> echter Oe Return: {top_avg:+6.2f}%")
    print(f"  Flop-Vorhersagen   -> echter Oe Return: {flop_avg:+6.2f}%")
    print(f"  Spread (Top-Flop):                      {top_avg-flop_avg:+6.2f}%")
    print("  -> Positiver Spread = Gedaechtnis trennt gute von schlechten Lagen.")

    # --- Aufschluesselung nach Phase ---
    print("\nTrefferquote je (heutiger) Phase:")
    from collections import defaultdict
    ph = defaultdict(lambda: [0, 0, 0.0])
    for p, a, phz in zip(preds, actuals, phases):
        ph[phz][0] += int((p > 0) == (a > 0))
        ph[phz][1] += 1
        ph[phz][2] += a
    for phz, (h, m, s) in sorted(ph.items(), key=lambda x: -x[1][1]):
        print(f"  {phz:14s}: {h/m*100:5.1f}%  (n={m}, Oe real {s/m:+.1f}%)")

    # --- Beispiel: aktuellste Situation ---
    last = days[-1]
    cands = []
    for j in range(len(days) - args.gap):
        d = distance(last["features"], days[j]["features"])
        if d is not None:
            cands.append((d, days[j]))
    cands.sort(key=lambda x: x[0])
    print(f"\nAktuellste Situation ({last['date']}, Phase {last.get('phase')}):")
    print("  Aehnlichste historische Tage:")
    for d, day in cands[:5]:
        o = day["outcome"].get(args.horizon)
        print(f"    {day['date']}  Phase {day.get('phase', '?'):14s} "
              f"-> {args.horizon} {o:+.1f}%  (Dist {d:.3f})")


if __name__ == "__main__":
    main()
