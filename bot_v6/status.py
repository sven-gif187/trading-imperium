#!/usr/bin/env python3
"""Status Tool - Schnelle Bot-Uebersicht in einem Befehl."""
import os
import sys
import json
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data_store")

class C:
    R = "\033[0m"; B = "\033[1m"; G = "\033[92m"; RED = "\033[91m"
    Y = "\033[93m"; CY = "\033[96m"; GR = "\033[90m"; BLUE = "\033[94m"

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        for a in dir(C):
            if not a.startswith("_"): setattr(C, a, "")


def fmt_pnl(p):
    if p is None or p == 0:
        return f"{C.GR} +0.00${C.R}"
    if p > 0:
        return f"{C.G}{C.B}+{p:.2f}${C.R}"
    return f"{C.RED}{C.B}{p:.2f}${C.R}"


def main():
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()

    print(f"\n{C.CY}{C.B}{'='*60}")
    print(f"  TRADING IMPERIUM V6 - STATUS")
    print(f"{'='*60}{C.R}")
    print(f"  {C.GR}{now.strftime('%Y-%m-%d %H:%M:%S')}{C.R}\n")

    # === BOT-STATUS (an Hand letzter State-Update) ===
    bot_state_path = os.path.join(DATA, "bot_state.json")
    cash = 0; total = 0; positions = []
    last_update = "?"
    running = False
    if os.path.exists(bot_state_path):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(bot_state_path))
            last_update = mtime.strftime("%H:%M:%S")
            # < 5 Min Update = Bot laeuft
            running = (now - mtime).total_seconds() < 300
            with open(bot_state_path) as f:
                state = json.load(f)
            pb = state.get("paper_balances", {})
            cash = pb.get("USDC", 0) + pb.get("USDT", 0)
            for k, v in pb.items():
                if k not in ("USDC", "USDT") and v > 0:
                    positions.append(k)
        except Exception:
            pass

    print(f"{C.Y}{C.B}  BOT-STATUS{C.R}")
    if running:
        print(f"    Status:     {C.G}{C.B}LAEUFT{C.R}  (letztes Update: {last_update})")
    else:
        print(f"    Status:     {C.RED}{C.B}STOPP{C.R}  (letztes Update: {last_update})")
    print(f"    Cash:       {C.B}{cash:.2f} USDC{C.R}")
    print(f"    Positionen: {C.B}{len(positions)}{C.R} ({', '.join(positions[:6])})")

    # === TRADES HEUTE ===
    print(f"\n{C.Y}{C.B}  HEUTE{C.R}")
    ij_path = os.path.join(DATA, "impact_journal.json")
    trades_today = 0
    wins_today = 0
    losses_today = 0
    pnl_today = 0.0
    strats_today = set()
    if os.path.exists(ij_path):
        try:
            with open(ij_path) as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else data
            for e in entries:
                ts = e.get("timestamp", "")
                if ts >= today_start:
                    if e.get("side") == "BUY":
                        trades_today += 1
                        strats_today.add(e.get("strategy", "?"))
                    if e.get("status") == "WIN":
                        wins_today += 1
                        pnl_today += e.get("pnl_usd", 0) or 0
                    elif e.get("status") == "LOSS":
                        losses_today += 1
                        pnl_today += e.get("pnl_usd", 0) or 0
        except Exception:
            pass
    print(f"    Trades:      {C.B}{trades_today}{C.R}")
    print(f"    Wins/Losses: {C.G}{wins_today}{C.R} / {C.RED}{losses_today}{C.R}")
    print(f"    P&L heute:  {fmt_pnl(pnl_today)}")
    print(f"    Strategien:  {len(strats_today)} aktiv ({', '.join(list(strats_today)[:3]) if strats_today else '-'})")

    # === GESAMT ===
    print(f"\n{C.Y}{C.B}  GESAMT (seit Reset){C.R}")
    if os.path.exists(ij_path):
        try:
            with open(ij_path) as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else data
            total_trades = len([e for e in entries if e.get("side") == "BUY"])
            total_wins = sum(1 for e in entries if e.get("status") == "WIN")
            total_losses = sum(1 for e in entries if e.get("status") == "LOSS")
            total_pnl = sum(e.get("pnl_usd", 0) or 0 for e in entries)
            closed = total_wins + total_losses
            wr = (total_wins / closed * 100) if closed > 0 else 0
            print(f"    Trades total: {C.B}{total_trades}{C.R} ({closed} closed, {total_trades - closed} open)")
            print(f"    Win-Rate:     {C.G if wr >= 60 else (C.Y if wr >= 40 else C.RED)}{wr:.1f}%{C.R}")
            print(f"    Total P&L:   {fmt_pnl(total_pnl)}")
        except Exception:
            print(f"    (Kein Impact-Journal Daten)")

    # === V4-SYNC STATUS ===
    print(f"\n{C.Y}{C.B}  V4-LERNHISTORIE{C.R}")
    brain_path = os.path.join(DATA, "brain_performance.json")
    v4_trades = 0
    strategies_with_data = 0
    if os.path.exists(brain_path):
        try:
            with open(brain_path) as f:
                bp = json.load(f)
            for sid, perf in bp.items():
                t = perf.get("trades", 0)
                if t > 0:
                    strategies_with_data += 1
                    v4_trades += t
        except Exception:
            pass
    print(f"    Trade-Wissen: {C.B}{v4_trades}{C.R} Trades (aus V4+V6)")
    print(f"    Strategien mit Daten: {C.B}{strategies_with_data}{C.R} / 13")

    print(f"\n{C.GR}  Tipp: python impact_report.py fuer Details, python preflight.py fuer Live-Check{C.R}\n")


if __name__ == "__main__":
    main()