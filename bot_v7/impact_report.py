#!/usr/bin/env python3
"""Impact Journal Report Tool - zeigt schöne Übersicht."""
import os
import sys
import json
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JOURNAL_FILE = os.path.join(SCRIPT_DIR, "data_store", "impact_journal.json")


class C:
    R = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREY = "\033[90m"

if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        for attr in dir(C):
            if not attr.startswith("_") and isinstance(getattr(C, attr), str):
                setattr(C, attr, "")


def banner(text, color=C.CYAN):
    line = "=" * 72
    print(f"\n{color}{C.BOLD}{line}\n  {text}\n{line}{C.R}")


def section(text, color=C.YELLOW):
    print(f"\n{color}{C.BOLD}  {text}\n  {'-' * 70}{C.R}")


def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        print(f"{C.RED}Journal nicht gefunden: {JOURNAL_FILE}{C.R}")
        print(f"{C.GREY}Tipp: Lauf erst den Bot, damit Trades geloggt werden.{C.R}")
        return None
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "entries" in data:
            return data["entries"]
        return []
    except Exception as e:
        print(f"{C.RED}Fehler: {e}{C.R}")
        return None


def fmt_pnl(pnl):
    if pnl is None or pnl == 0:
        return f"{C.GREY}  +0.00${C.R}"
    if pnl > 0:
        return f"{C.GREEN}{C.BOLD}+{pnl:>7.2f}${C.R}"
    return f"{C.RED}{C.BOLD}{pnl:>8.2f}${C.R}"


def fmt_pct(pct):
    if pct is None:
        return f"{C.GREY}    --{C.R}"
    if pct > 0:
        return f"{C.GREEN}+{pct:>5.2f}%{C.R}"
    elif pct < 0:
        return f"{C.RED}{pct:>6.2f}%{C.R}"
    return f"{C.GREY} 0.00%{C.R}"


def fmt_status(status):
    if status == "WIN":
        return f"{C.GREEN}WIN {C.R}"
    elif status == "LOSS":
        return f"{C.RED}LOSS{C.R}"
    elif status == "OPEN":
        return f"{C.YELLOW}OPEN{C.R}"
    return f"{C.GREY}{status[:4]:<4}{C.R}"


def show_summary(entries):
    total = len([e for e in entries if e.get("side") == "BUY"])
    opens = sum(1 for e in entries if e.get("status") == "OPEN")
    wins = sum(1 for e in entries if e.get("status") == "WIN")
    losses = sum(1 for e in entries if e.get("status") == "LOSS")
    total_pnl = sum(e.get("pnl_usd", 0) or 0 for e in entries)
    closed = wins + losses
    banner("IMPACT JOURNAL REPORT")
    print(f"  {C.GREY}Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.R}\n")
    print(f"  Trades total:      {C.BOLD}{total:>4}{C.R}")
    print(f"  Open positions:    {C.YELLOW}{opens:>4}{C.R}")
    print(f"  Wins:              {C.GREEN}{wins:>4}{C.R}")
    print(f"  Losses:            {C.RED}{losses:>4}{C.R}")
    if closed > 0:
        wr = wins / closed * 100
        wr_color = C.GREEN if wr >= 60 else (C.YELLOW if wr >= 50 else C.RED)
        print(f"  Win-Rate:          {wr_color}{C.BOLD}{wr:>4.1f}%{C.R}")
    print(f"  Total P&L:        {fmt_pnl(total_pnl)}")


def show_strategies(entries):
    from collections import defaultdict
    stats = defaultdict(lambda: {"trades":0,"wins":0,"losses":0,"open":0,"total_pnl":0.0,"scores":[]})
    for e in entries:
        if e.get("side") != "BUY":
            continue
        strat = e.get("strategy", "?") or "?"
        stats[strat]["trades"] += 1
        stats[strat]["scores"].append(e.get("score", 0))
        status = e.get("status", "OPEN")
        if status == "WIN":
            stats[strat]["wins"] += 1
            stats[strat]["total_pnl"] += e.get("pnl_usd", 0) or 0
        elif status == "LOSS":
            stats[strat]["losses"] += 1
            stats[strat]["total_pnl"] += e.get("pnl_usd", 0) or 0
        elif status == "OPEN":
            stats[strat]["open"] += 1
    if not stats:
        return
    section("PERFORMANCE PRO STRATEGIE")
    print(f"  {C.BOLD}{'Strategy':<20} {'Trades':>7}  {'Win-Rate':>9}  {'P&L':>12}  {'Avg Score':>10}{C.R}")
    print(f"  {C.GREY}{'-' * 68}{C.R}")
    rows = sorted(stats.items(), key=lambda x: -x[1]["total_pnl"])
    for strat, s in rows:
        closed = s["wins"] + s["losses"]
        wr = (s["wins"] / closed * 100) if closed > 0 else None
        avg_score = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0
        wr_str = f"{wr:.1f}%" if wr is not None else "-"
        wr_col = C.GREEN if wr is not None and wr >= 60 else (C.YELLOW if wr is not None and wr >= 40 else (C.RED if wr is not None else C.GREY))
        print(f"  {strat:<20} {s['trades']:>7}  {wr_col}{wr_str:>9}{C.R}  {fmt_pnl(s['total_pnl'])}  {avg_score:>10.2f}")


def show_open(entries):
    open_pos = [e for e in entries if e.get("status") == "OPEN"]
    if not open_pos:
        return
    section(f"OFFENE POSITIONEN ({len(open_pos)})", color=C.YELLOW)
    for e in open_pos:
        sym = e.get("symbol", "?")[:12]
        strat = (e.get("strategy", "?") or "?")[:18]
        score = e.get("score", 0) or 0
        amt = e.get("amount_usd", 0) or 0
        entry_price = e.get("entry_price", 0) or 0
        ctx = e.get("context", {})
        fg = ctx.get("fear_greed", 0)
        regime = (ctx.get("regime", "?") or "?")[:15]
        print(f"  {sym:<12} {strat:<18}  Score:{score:>2}  Entry {entry_price:>10.4f}$  ({amt:>6.2f}$)  {C.GREY}F&G {fg}, {regime}{C.R}")


def show_best_worst(entries, n=5):
    closed = [e for e in entries if e.get("status") in ("WIN", "LOSS") and e.get("pnl_usd") is not None]
    if not closed:
        return
    best = sorted(closed, key=lambda x: -(x.get("pnl_usd") or 0))[:n]
    worst = sorted(closed, key=lambda x: (x.get("pnl_usd") or 0))[:n]
    if best:
        section(f"TOP {n} GEWINNER", color=C.GREEN)
        for e in best:
            print(f"  {(e.get('symbol','?'))[:12]:<12} {(e.get('strategy','?'))[:18]:<18}  {fmt_pnl(e.get('pnl_usd',0))}  {fmt_pct(e.get('pnl_pct',0))}  {(e.get('hold_minutes',0) or 0):>5}min")
    if worst:
        section(f"TOP {n} VERLIERER", color=C.RED)
        for e in worst:
            print(f"  {(e.get('symbol','?'))[:12]:<12} {(e.get('strategy','?'))[:18]:<18}  {fmt_pnl(e.get('pnl_usd',0))}  {fmt_pct(e.get('pnl_pct',0))}  {(e.get('hold_minutes',0) or 0):>5}min")


def show_recent(entries, n=10):
    section(f"LETZTE {n} TRADES")
    recent = entries[-n:] if len(entries) > n else entries
    for e in reversed(recent):
        ts = e.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts).strftime("%H:%M:%S")
        except Exception:
            ts = ts[:8]
        side = e.get("side", "?")
        side_col = C.GREEN if side == "BUY" else (C.RED if side == "SELL" else C.GREY)
        status = e.get("status", "OPEN")
        pnl_str = ""
        if e.get("pnl_usd") is not None:
            pnl_str = f" | {fmt_pnl(e.get('pnl_usd', 0))}"
        reasons = e.get("reasons", []) or []
        reason_text = ", ".join(reasons[:2])[:50] if reasons else ""
        print(f"  {C.GREY}{ts}{C.R} {side_col}{side:<4}{C.R} {(e.get('symbol','?'))[:10]:<10} {(e.get('strategy','?') or '?')[:18]:<18} Score:{(e.get('score',0) or 0):>2}  {fmt_status(status)}{pnl_str}")
        if reason_text:
            print(f"           {C.GREY}{reason_text}{C.R}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--strategy", type=str, default=None)
    parser.add_argument("--no-recent", action="store_true")
    parser.add_argument("--no-best", action="store_true")
    args = parser.parse_args()

    entries = load_journal()
    if entries is None:
        return 1
    if not entries:
        print(f"\n  {C.YELLOW}Journal ist leer - noch keine Trades aufgezeichnet.{C.R}")
        print(f"  {C.GREY}Wenn der Bot trading macht, kommen die Eintraege rein.{C.R}\n")
        return 0
    if args.strategy:
        entries = [e for e in entries if e.get("strategy") == args.strategy]
        if not entries:
            print(f"  {C.YELLOW}Keine Trades mit Strategie '{args.strategy}'.{C.R}")
            return 0

    show_summary(entries)
    show_strategies(entries)
    show_open(entries)
    if not args.no_best:
        show_best_worst(entries, n=5)
    if not args.no_recent:
        show_recent(entries, n=args.top)
    print(f"\n  {C.GREY}Letzter Update: {datetime.now().strftime('%H:%M:%S')}{C.R}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())