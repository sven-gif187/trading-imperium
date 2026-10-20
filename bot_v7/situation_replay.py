"""
Trading Imperium V6 - Situation-Memory Replay-Validierung
==========================================================
Beantwortet die Kernfrage BEVOR das Gedaechtnis je mitentscheiden darf:
"Haette das Situation-Memory die Trade-Ergebnisse vorhersagen koennen?"

Methode (streng ohne Lookahead):
  1. Alle abgeschlossenen Trades aus impact_journal.json chronologisch laden.
  2. Fuer jeden Trade: Memory NUR aus frueheren Trades befragen (before_ts).
  3. Vorhersage (Nachbar-Statistik) mit dem echten Outcome vergleichen.

Ausgabe: Trefferquote, Kalibrierung nach Konfidenz-Buckets, Strategie-Split,
und ein ehrlicher Bias-Hinweis (Impact-Journal erfasst Stop-Loss/Trend-Exits
derzeit NICHT vollstaendig -> Ergebnisse erst nach Journal-Fix belastbar).

Nutzung (aus dem V6-Projektordner):
    python situation_replay.py
    python situation_replay.py --journal data_store/impact_journal.json --k 5

Ziel-Pfad: Projektordner-Root (neben pnl_check.py / brain_view.py).
"""
import os
import sys
import json
import argparse
from collections import Counter, defaultdict

# Modul sowohl aus features/ als auch lokal auffindbar machen
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, "features")):
    if p not in sys.path:
        sys.path.insert(0, p)

from situation_memory import SituationMemory, _parse_ts  # noqa: E402


def find_journal(cli_path: str) -> str:
    if cli_path and os.path.exists(cli_path):
        return cli_path
    candidates = [
        os.path.join(_HERE, "data_store", "impact_journal.json"),
        os.path.join(_HERE, "impact_journal.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    print("FEHLER: impact_journal.json nicht gefunden. --journal PFAD angeben.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default="", help="Pfad zu impact_journal.json")
    ap.add_argument("--k", type=int, default=5, help="Anzahl Nachbarn")
    ap.add_argument("--min-n", type=int, default=3,
                    help="Mindest-Nachbarn fuer eine Vorhersage")
    args = ap.parse_args()

    path = find_journal(args.journal)
    print(f"Journal: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", data if isinstance(data, list) else [])

    closed = []
    for e in entries:
        if e.get("side") == "BUY" and e.get("status") in ("WIN", "LOSS") \
                and e.get("pnl_pct") is not None:
            ts = _parse_ts(e.get("timestamp"))
            if ts is not None:
                closed.append((ts, e))
    closed.sort(key=lambda x: x[0])
    print(f"Abgeschlossene Trades: {len(closed)}")
    if len(closed) < 20:
        print("Zu wenig Daten fuer eine sinnvolle Auswertung (<20).")
        sys.exit(0)

    # Memory einmal komplett befuellen; Lookahead wird per before_ts verhindert
    mem = SituationMemory(path=os.path.join(_HERE, "_replay_memory.json"),
                          autoload=False)
    for ts, e in closed:
        mem.add_situation(context=e.get("context") or {}, ts=ts,
                          symbol=e.get("symbol", ""),
                          strategy=e.get("strategy", ""),
                          pnl_pct=e.get("pnl_pct"),
                          sell_reason=e.get("sell_reason") or "",
                          status=e.get("status"))

    # --- Replay ---
    evaluated = skipped = 0
    hits = 0
    buckets = defaultdict(lambda: [0, 0])          # bucket -> [hits, n]
    strat = defaultdict(lambda: [0, 0])            # strategy -> [hits, n]
    pred_pnls, actual_pnls = [], []

    for ts, e in closed:
        ctx = e.get("context") or {}
        r = mem.query(ctx, k=args.k, before_ts=ts, min_neighbors=args.min_n)
        if not r["reliable"]:
            skipped += 1
            continue
        evaluated += 1
        pred_win = r["win_rate"] >= 0.5
        actual_win = float(e["pnl_pct"]) > 0
        hit = (pred_win == actual_win)
        hits += int(hit)

        wr = r["win_rate"]
        bucket = ("hoch (WR>=80%)" if wr >= 0.8 else
                  "mittel (50-80%)" if wr >= 0.5 else
                  "negativ (<50%)")
        buckets[bucket][0] += int(actual_win)
        buckets[bucket][1] += 1
        strat[e.get("strategy", "?")][0] += int(hit)
        strat[e.get("strategy", "?")][1] += 1
        pred_pnls.append(r["avg_pnl_pct"])
        actual_pnls.append(float(e["pnl_pct"]))

    # --- Report ---
    base_wr = sum(1 for _, e in closed if e["pnl_pct"] > 0) / len(closed)
    print("\n" + "=" * 62)
    print("SITUATION-MEMORY REPLAY-REPORT (Shadow-Validierung, kein Lookahead)")
    print("=" * 62)
    print(f"Bewertet: {evaluated} | Uebersprungen (zu wenig Nachbarn): {skipped}")
    if evaluated:
        print(f"Richtungs-Trefferquote (Win/Loss): {hits/evaluated*100:.1f}%")
    print(f"Baseline 'immer Win tippen':        {base_wr*100:.1f}%")
    print("-> Nur ein Vorsprung GEGENUEBER der Baseline zaehlt!")

    print("\nKalibrierung (vorhergesagte vs. echte Win-Rate):")
    for b in ("hoch (WR>=80%)", "mittel (50-80%)", "negativ (<50%)"):
        w, n = buckets[b]
        if n:
            print(f"  {b:18s}: echte WR {w/n*100:5.1f}%  (n={n})")

    print("\nTrefferquote je Strategie:")
    for s, (h, n) in sorted(strat.items(), key=lambda x: -x[1][1]):
        print(f"  {s:22s}: {h/n*100:5.1f}%  (n={n})")

    if len(pred_pnls) >= 10:
        corr = _pearson(pred_pnls, actual_pnls)
        print(f"\nKorrelation Nachbar-Oe-PnL% vs. echtes PnL%: {corr:+.3f}")
        print("(>= +0.2 waere ein erstes echtes Signal)")

    # --- Ehrlichkeits-Block ---
    reasons = Counter((e.get("sell_reason") or "?").split("(")[0].strip()
                      for _, e in closed)
    sl = sum(n for r, n in reasons.items() if "top-Loss" in r or "TOP-LOSS" in r)
    print("\n" + "!" * 62)
    print("BIAS-WARNUNG: Exit-Verteilung im Journal:")
    for r, n in reasons.most_common():
        print(f"  {n:4d}x {r}")
    if sl < len(closed) * 0.10:
        print("  -> Stop-Loss-Exits stark unterrepraesentiert!")
        print("  -> Impact-Journal log_sell() fehlt in SL/Trend-Exit-Pfaden.")
        print("  -> Report erst NACH dem Journal-Fix belastbar.")
    print("!" * 62)


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / (vx ** 0.5 * vy ** 0.5)


if __name__ == "__main__":
    main()
