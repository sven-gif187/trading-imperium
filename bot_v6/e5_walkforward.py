# -*- coding: utf-8 -*-
"""
e5_walkforward.py - E5-Vorbereitung: Trailing-Kandidaten OHNE Overfitting
==========================================================================
Beantwortet VOR dem E5-Start zwei Fragen, sauber getrennt:

  FRAGE 1 (E5, global): Welches Trailing haette auf den ECHTEN V6-Entries
    am besten funktioniert - und haelt der Sieger auch out-of-sample?
    Methode Walk-Forward: Configs werden auf den ersten 60% der Entries
    (chronologisch) gerankt (In-Sample). Der Champion muss sich dann auf
    den letzten 40% (Out-of-Sample) beweisen. Grosser IS/OOS-Abstand
    = Overfitting-Warnung.

  FRAGE 2 (E6-Vorschau, pro Coin): Welcher Stop-Loss passt zu welchem
    Coin? (Grid 2.0/2.5/3.0/4.0 mit dem Champion-Trailing, volle Daten,
    nur als Vorschau markiert - Entscheidung faellt in E6.)

Simulation je Entry (1h-Candles aus data_store/charts/):
  - Stop-Loss: Low beruehrt Entry*(1-Stop%) -> Exit zum Stop-Preis
    (Stop wird IN der Kerze VOR dem Trailing geprueft = pessimistisch)
  - Trailing: aktiv ab Hoch >= Entry*(1+Aktivierung%); Exit wenn Preis
    Trail% unter dem Hoch seit Entry faellt
  - Stufen-Leiter: Trail% wird enger, je hoeher der Gewinn
  - Max-Haltezeit 14 Tage, sonst Exit zum letzten Close
  - Gebuehren 0.1% je Seite (netto = brutto - 0.2%)

GRENZEN (ehrlich): Approximation des Bot-Monitors - keine Phasen-
Multiplikatoren, keine ADX-Anpassung, kein RSI/Trend-Exit. Es vergleicht
Konfigurationen RELATIV zueinander auf identischen Entries; absolute
$-Werte weichen vom echten Bot ab.

Nutzung (V6-Hauptordner, Bot darf laufen - liest nur):
    python e5_walkforward.py
Braucht: data_store/order_history.json + data_store/charts/*_1h.csv
"""
import os
import csv
import json
import sys
from collections import defaultdict

FEE_PCT = 0.2          # round-trip netto-Abzug
MAX_HOLD_H = 14 * 24   # 14 Tage
IS_SPLIT = 0.6         # 60% In-Sample / 40% Out-of-Sample

# Kandidaten: (Name, stop_pct, aktivierung_pct, leiter)
# leiter = Liste (ab_gewinn_pct, trail_pct), absteigend angewandt
CONFIGS = [
    ("IST: Stop2.5/Trail1.0",   2.5, 1.0, [(0.0, 1.0)]),
    ("Trail 1.25",              2.5, 1.0, [(0.0, 1.25)]),
    ("Trail 1.5",               2.5, 1.0, [(0.0, 1.5)]),
    ("Trail 2.0",               2.5, 1.0, [(0.0, 2.0)]),
    ("Leiter A (1.5->1.0->0.6)", 2.5, 1.0, [(4.0, 0.6), (2.0, 1.0), (0.0, 1.5)]),
    ("Leiter B (2.0->1.0)",     2.5, 1.5, [(3.0, 1.0), (0.0, 2.0)]),
]


def find_base():
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(here, "data_store", "order_history.json")):
        return here
    print("FEHLER: data_store/order_history.json nicht gefunden - Skript in den V6-Hauptordner legen.")
    sys.exit(1)


def load_candles(base, symbol):
    """Laedt 1h-Kerzen. Cache liegt teils als USDT-Paar vor (Preis-Proxy
    fuer USDC, beides Dollar-Stablecoins) -> Fallback-Kette."""
    safe = symbol.replace("/", "")
    candidates = [safe, safe.replace("USDC", "USDT"), safe.replace("USDT", "USDC")]
    path = None
    for c in candidates:
        p = os.path.join(base, "data_store", "charts", f"{c}_1h.csv")
        if os.path.exists(p):
            path = p
            break
    if path is None:
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["open_time"]) / 1000, float(r["high"]),
                         float(r["low"]), float(r["close"])))
    rows.sort()
    return rows


def simulate(entry_price, candles, start_idx, stop_pct, act_pct, ladder):
    """Simuliert einen Trade. Rueckgabe: (netto_pnl_pct, exit_grund)."""
    stop_price = entry_price * (1 - stop_pct / 100)
    high = entry_price
    trailing_on = False
    for i in range(start_idx, min(start_idx + MAX_HOLD_H, len(candles))):
        _, h, l, c = candles[i]
        # 1) Stop zuerst (pessimistisch)
        if l <= stop_price:
            return (stop_price / entry_price - 1) * 100 - FEE_PCT, "STOP"
        # 2) Hoch aktualisieren, Trailing aktivieren
        if h > high:
            high = h
        gain_pct = (high / entry_price - 1) * 100
        if not trailing_on and gain_pct >= act_pct:
            trailing_on = True
        # 3) Trailing-Exit (Trail% je nach Leiter-Stufe)
        if trailing_on:
            trail = next(t for g, t in ladder if gain_pct >= g)
            trail_price = high * (1 - trail / 100)
            if l <= trail_price and trail_price > stop_price:
                return (trail_price / entry_price - 1) * 100 - FEE_PCT, "TRAIL"
    # 4) Zeit-Exit
    last_close = candles[min(start_idx + MAX_HOLD_H, len(candles)) - 1][3]
    return (last_close / entry_price - 1) * 100 - FEE_PCT, "ZEIT"


def stats(pnls):
    if not pnls:
        return None
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(pnls), "sum": sum(pnls), "avg": sum(pnls) / len(pnls),
        "wr": len(wins) / len(pnls) * 100,
        "rr": abs(aw / al) if al else 0.0,
    }


def main():
    base = find_base()
    with open(os.path.join(base, "data_store", "order_history.json"),
              encoding="utf-8") as f:
        oh = json.load(f)
    buys = [o for o in oh if o.get("side") == "BUY"
            and o.get("status") == "filled" and (o.get("fill_price") or 0) > 0]
    buys.sort(key=lambda o: o.get("created_at", 0))
    print(f"Gefuellte BUYs: {len(buys)}")

    candle_cache = {}
    entries = []   # (created_at, symbol, entry_price, start_idx)
    skipped = 0
    for b in buys:
        sym = b["symbol"]
        if sym not in candle_cache:
            candle_cache[sym] = load_candles(base, sym)
        candles = candle_cache[sym]
        if not candles:
            skipped += 1
            continue
        t0 = float(b["created_at"])
        idx = next((i for i, (t, *_ ) in enumerate(candles) if t >= t0), None)
        if idx is None or idx >= len(candles) - 5:
            skipped += 1
            continue
        if candles[idx][0] - t0 > 7200:  # Entry liegt VOR Cache-Beginn -> unsimulierbar
            skipped += 1
            continue
        entries.append((t0, sym, float(b["fill_price"]), idx))
    print(f"Simulierbar: {len(entries)} | uebersprungen (kein Cache/zu neu): {skipped}")
    if len(entries) < 40:
        print("Zu wenig simulierbare Entries (<40) - Cache pruefen (Charts-Tab oeffnen laedt Kerzen).")
        sys.exit(0)

    split = int(len(entries) * IS_SPLIT)
    is_set, oos_set = entries[:split], entries[split:]

    def run(config, subset):
        _, stop, act, ladder = config
        pnls = []
        by_coin = defaultdict(list)
        reasons = defaultdict(int)
        for _, sym, ep, idx in subset:
            p, why = simulate(ep, candle_cache[sym], idx, stop, act, ladder)
            pnls.append(p)
            by_coin[sym].append(p)
            reasons[why] += 1
        return pnls, by_coin, reasons

    # ===== FRAGE 1: Walk-Forward =====
    print("\n" + "=" * 74)
    print(f"FRAGE 1 - TRAILING-KANDIDATEN (Walk-Forward: {split} IS / {len(oos_set)} OOS)")
    print("=" * 74)
    print(f"{'Config':26s} | {'IS Oe%':>7s} {'IS WR':>6s} {'IS R/R':>6s} | "
          f"{'OOS Oe%':>7s} {'OOS WR':>6s} {'OOS R/R':>7s}")
    results = []
    for cfg in CONFIGS:
        is_p, _, _ = run(cfg, is_set)
        oos_p, _, _ = run(cfg, oos_set)
        s1, s2 = stats(is_p), stats(oos_p)
        results.append((cfg, s1, s2))
        print(f"{cfg[0]:26s} | {s1['avg']:+7.3f} {s1['wr']:5.1f}% {s1['rr']:6.2f} | "
              f"{s2['avg']:+7.3f} {s2['wr']:5.1f}% {s2['rr']:7.2f}")

    champ = max(results, key=lambda r: r[1]["avg"])
    oos_rank = sorted(results, key=lambda r: -r[2]["avg"])
    champ_oos_platz = next(i for i, r in enumerate(oos_rank, 1) if r[0] is champ[0])
    print("-" * 74)
    print(f"IS-Champion: {champ[0][0]}  ->  OOS-Platz {champ_oos_platz}/{len(CONFIGS)}")
    if champ_oos_platz <= 2 and champ[2]["avg"] >= champ[1]["avg"] * 0.5:
        print("BEWERTUNG: Champion haelt out-of-sample -> valider E5-Kandidat.")
    elif champ_oos_platz <= 3:
        print("BEWERTUNG: Champion nur mittel stabil -> E5 nur mit dem Config,")
        print("           das IS UND OOS in den Top 3 liegt (Robustheit vor Maximum).")
    else:
        print("BEWERTUNG: Champion kollabiert OOS -> OVERFITTING-Warnung,")
        print("           E5 NICHT auf diese Optimierung stuetzen.")

    # ===== FRAGE 2: Coin-Stop-Vorschau (E6) =====
    print("\n" + "=" * 74)
    print("FRAGE 2 - COIN-STOP-VORSCHAU fuer E6 (volle Daten, NUR VORSCHAU)")
    print("=" * 74)
    _, _, act, ladder = champ[0]
    per_coin_n = defaultdict(int)
    for _, sym, _, _ in entries:
        per_coin_n[sym] += 1
    header = f"{'Coin':10s} (n)  |" + "".join(f"  Stop {s:.1f}%" for s in (2.0, 2.5, 3.0, 4.0))
    print(header)
    for sym in sorted(per_coin_n, key=lambda s: -per_coin_n[s]):
        subset = [e for e in entries if e[1] == sym]
        line = f"{sym.split('/')[0]:10s} ({per_coin_n[sym]:3d}) |"
        for s in (2.0, 2.5, 3.0, 4.0):
            pnls, _, _ = run(("", s, act, ladder), subset)
            st = stats(pnls)
            line += f"  {st['avg']:+7.3f}%"
        marke = "  << n<10, nur Rauschen" if per_coin_n[sym] < 10 else ""
        print(line + marke)
    print("-" * 74)
    print("Oe Netto-PnL% pro Trade je Stop (mit Champion-Trailing).")
    print("E6-Entscheidung erst in der Epoche selbst - das hier ist die Datenbasis.")


if __name__ == "__main__":
    main()
