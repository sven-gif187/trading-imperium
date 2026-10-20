#!/usr/bin/env python3
# brain_view.py   (READ-ONLY - aendert nie etwas)
# ---------------------------------------------------------------------------
# Zeigt drei Blicke nebeneinander:
#   1) V6-EIGEN     - echte realisierte P&L aus trades_v5.json (Ground Truth),
#                     aufgeschluesselt nach Exit-Typ + R/R-Kennzahl.
#   2) BRAIN        - was brain_performance.json fuer Entscheidungen nutzt,
#                     inkl. wie viel davon V4-Warmstart ist.
#   3) V4 (optional)- realisierte P&L aus einer V4-Datei, fuer die spaetere
#                     Gesamt-Auswertung. Nur wenn du eine Datei uebergibst.
#
# Aufruf:
#   python "...\brain_view.py"
#       -> V6-EIGEN + BRAIN  (reiner V6-Blick)
#   python "...\brain_view.py" trades_log_v4.json
#       -> zusaetzlich der V4-Block + kombinierter Track-Record
#   python "...\brain_view.py" "C:\pfad\zu\meinen_v4_trades.json"
# ---------------------------------------------------------------------------
import os, sys, json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def money(x, w=9):
    return "%+*.2f" % (w, x)


def find_perf(brain):
    """Robust gegen die bekannten brain_performance.json-Varianten."""
    if not isinstance(brain, dict):
        return {}
    for key in ("performance", "strategies", "strategy_performance"):
        if isinstance(brain.get(key), dict):
            return brain[key]
    flat = {k: v for k, v in brain.items()
            if isinstance(v, dict) and ("trades" in v or "total_pnl" in v)}
    return flat


def agg_sells(trades):
    """SELLs nach 'strategy' aggregieren -> {strat:[n,wins,pnl]} + Win/Loss-Listen."""
    by = defaultdict(lambda: [0, 0, 0.0])
    wins_pnl, loss_pnl = [], []
    for t in trades or []:
        if not isinstance(t, dict) or t.get("type") != "SELL":
            continue
        pnl = t.get("pnl")
        if pnl is None:
            continue
        s = t.get("strategy") or "?"
        by[s][0] += 1
        by[s][1] += 1 if pnl > 0 else 0
        by[s][2] += pnl
        if pnl > 0:
            wins_pnl.append(pnl)
        elif pnl < 0:
            loss_pnl.append(pnl)
    return by, wins_pnl, loss_pnl


def print_sell_table(by):
    print("  %-20s %6s %7s %12s %10s" % ("Strategie/Exit", "Sells", "WR", "P&L", "O/Trade"))
    print("  " + "-" * 60)
    tot_n = tot_w = 0
    tot_p = 0.0
    for s, (n, w, p) in sorted(by.items(), key=lambda x: -x[1][2]):
        wr = (w / n * 100) if n else 0
        avg = (p / n) if n else 0
        print("  %-20s %6d %6.1f%% %12s %10s" % (s, n, wr, money(p, 10), money(avg, 8)))
        tot_n += n
        tot_w += w
        tot_p += p
    wr = (tot_w / tot_n * 100) if tot_n else 0
    print("  " + "-" * 60)
    print("  %-20s %6d %6.1f%% %12s" % ("GESAMT", tot_n, wr, money(tot_p, 10)))
    return tot_p


def section_v6():
    print("=" * 66)
    print("1) V6-EIGEN  -  realisierte P&L aus trades_v5.json (Ground Truth)")
    print("=" * 66)
    trades = load_json(os.path.join(HERE, "trades_v5.json"))
    if trades is None:
        print("  trades_v5.json nicht lesbar - uebersprungen.\n")
        return None
    by, wins, losses = agg_sells(trades)
    if not by:
        print("  Keine SELL-Trades mit P&L gefunden.\n")
        return 0.0
    total = print_sell_table(by)

    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    rr = (avg_win / abs(avg_loss)) if avg_loss else 0.0
    print()
    print("  R/R-CHECK (die Hauptbaustelle):")
    print("    Gewinn-Trades : %3d  |  O Gewinn  %s" % (len(wins), money(avg_win, 7)))
    print("    Verlust-Trades: %3d  |  O Verlust %s" % (len(losses), money(avg_loss, 7)))
    if rr:
        urteil = "schlecht (<1 = Verluste groesser als Gewinne)" if rr < 1 else "ok"
        print("    R/R = %.2f   %s" % (rr, urteil))
    print()
    return total


def section_brain():
    print("=" * 66)
    print("2) BRAIN  -  brain_performance.json: wie viel davon ist V4-Warmstart?")
    print("=" * 66)
    brain = load_json(os.path.join(HERE, "brain_performance.json"))
    if brain is None:
        print("  brain_performance.json nicht lesbar - uebersprungen.\n")
        return
    perf = find_perf(brain)
    if not perf:
        print("  Keine Strategie-Daten im Brain gefunden.\n")
        return
    saved = brain.get("saved_at", "?")
    print("  Stand: %s" % saved)
    print("  %-20s %14s %20s %9s" % ("Entry-Strategie", "Brain-Gesamt", "davon V4-Warmstart", "V6 dazu"))
    print("  " + "-" * 64)
    g_pnl = 0.0
    v4_pnl = 0.0
    v4_tr = 0
    v6_tr = 0
    rows = []
    for name, v in perf.items():
        if not isinstance(v, dict):
            continue
        tp = float(v.get("total_pnl", 0) or 0)
        vb_pnl = float(v.get("v4_baseline_pnl", 0) or 0)
        vb_tr = int(v.get("v4_baseline_trades", 0) or 0)
        v6a = int(v.get("v6_trades_added", 0) or 0)
        rows.append((tp, name, vb_pnl, vb_tr, v6a))
        g_pnl += tp
        v4_pnl += vb_pnl
        v4_tr += vb_tr
        v6_tr += v6a
    for tp, name, vb_pnl, vb_tr, v6a in sorted(rows, key=lambda x: -x[0]):
        v4str = ("%s (%d Tr)" % (money(vb_pnl, 8), vb_tr)) if (vb_pnl or vb_tr) else "-"
        print("  %-20s %14s %20s %6d Tr" % (name[:20], money(tp, 12), v4str, v6a))
    print("  " + "-" * 64)
    print("  %-20s %14s %20s %6d Tr" % ("GESAMT", money(g_pnl, 12),
                                        "%s (%d Tr)" % (money(v4_pnl, 8), v4_tr), v6_tr))
    print()
    anteil = (v4_pnl / g_pnl * 100) if g_pnl else 0
    print("  -> Vom Brain-Gedaechtnis sind %s / %d Trades getrackter V4-Warmstart"
          % (money(v4_pnl, 1), v4_tr))
    print("     (ca. %.0f%% der Gesamt-P&L im Brain). V4-SYNC ist AUS -> es kommt" % anteil)
    print("     nichts Neues dazu, aber dieser Anteil bleibt eingebacken bis zum Scrub.")
    print("  HINWEIS: Eine saubere V6-/V4-Aufteilung der P&L ist NICHT moeglich -")
    print("           das Brain speichert nur V4-Baseline + V6-Anzahl, kein V6-P&L.")
    print("           Der echte V6-Wert steht in Block 1 (aus dem Journal).")
    print()


def section_v4(path, v6_total):
    full = path if os.path.isabs(path) else os.path.join(HERE, path)
    print("=" * 66)
    print("3) V4-AUSWERTUNG  -  %s" % os.path.basename(full))
    print("=" * 66)
    trades = load_json(full)
    if trades is None:
        print("  Datei nicht lesbar: %s\n" % full)
        return
    by, wins, losses = agg_sells(trades)
    if not by:
        print("  Keine SELL-Trades mit P&L in der V4-Datei.\n")
        return
    v4_total = print_sell_table(by)
    print()
    if v6_total is not None:
        print("  KOMBINIERTER TRACK-RECORD (V6 + V4):")
        print("    V6-EIGEN : %s" % money(v6_total, 9))
        print("    V4       : %s" % money(v4_total, 9))
        print("    -------------------------")
        print("    GESAMT   : %s" % money(v6_total + v4_total, 9))
        print("  (Hinweis: V6 ist nach Exit-Typ getaggt, V4 nach Entry-Strategie -")
        print("   die Summe stimmt, die Strategie-Spalten sind aber nicht 1:1 vergleichbar.)")
    print()


def main():
    args = [a for a in sys.argv[1:] if a not in ("--v4",)]
    print()
    v6_total = section_v6()
    section_brain()
    if args:
        section_v4(args[0], v6_total)
    else:
        print("(Tipp: V4-Daten fuer die spaetere Gesamt-Auswertung mit reinnehmen:")
        print("  python \"%s\" trades_log_v4.json )" % os.path.join(HERE, "brain_view.py"))
        print()


if __name__ == "__main__":
    main()
