#!/usr/bin/env python3
"""Reset Paper-Trading State (Cash + Positions).

Brain-Daten bleiben intakt!
"""
import os
import sys
import json
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_STORE = os.path.join(PROJECT_ROOT, "data_store")
STATE_FILE = os.path.join(DATA_STORE, "bot_state.json")

RESET_CASH = 1000.0


def banner(t): print("\n" + "=" * 64 + f"\n  {t}\n" + "=" * 64)
def ok(t):    print(f"  [OK] {t}")
def err(t):   print(f"  [X]  {t}")


def main():
    banner("PAPER-RESET")

    if not os.path.exists(STATE_FILE):
        err(f"bot_state.json nicht gefunden")
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{STATE_FILE}.reset_backup_{ts}"
    shutil.copy2(STATE_FILE, backup)
    ok(f"Backup: {os.path.basename(backup)}")

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    if "paper_balances_backup" in state:
        old_total = sum(state["paper_balances_backup"].values())
        ok(f"Alte Balances Total: {old_total:.2f} USDC")
        state["paper_balances_backup"] = {"USDC": RESET_CASH}
        ok(f"Neue Balance: USDC = {RESET_CASH:.2f}")

    if "open_positions_backup" in state:
        old_pos = len(state["open_positions_backup"])
        state["open_positions_backup"] = {}
        ok(f"Positionen geloescht: {old_pos} -> 0")

    if "open_orders_backup" in state:
        state["open_orders_backup"] = {}

    if "realized_pnl" in state:
        old_pnl = state["realized_pnl"]
        state["realized_pnl"] = 0.0
        ok(f"Realized PnL: {old_pnl:+.2f} -> 0")

    state["last_reset"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    ok("bot_state.json gespeichert")

    banner("FERTIG!")
    print()
    print(f"  Cash: {RESET_CASH:.2f} USDC")
    print("  Positionen: alle geschlossen")
    print()
    print("  BLEIBT INTAKT (Lerngold):")
    print("    - brain_performance.json")
    print("    - v4_imported_trades.json")
    print("    - trade_journal.json")
    print()
    print("  JETZT:")
    print("    python app.py")
    print()
    print(f"  Backup: {os.path.basename(backup)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
