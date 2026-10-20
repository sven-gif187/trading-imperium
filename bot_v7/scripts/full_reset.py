#!/usr/bin/env python3
"""
================================================================
  FULL PAPER RESET (v2 - komplett)
================================================================
Setzt den Bot WIRKLICH auf 0:
- USDC Balance = 1000$
- Alle Positionen weg
- Trade-Counter = 0
- Daily Loss Tracking = 0
- Realized P&L = 0
- Equity History zurueck

BLEIBT INTAKT (Lerngold):
- brain_performance.json
- v4_imported_trades.json
- v4_strategy_weights.json
- trade_journal.json

WICHTIG: Bot muss VORHER GESTOPPT sein!
================================================================
"""
import os
import sys
import json
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_STORE = os.path.join(PROJECT_ROOT, "data_store")

RESET_CASH = 1000.0


def banner(t): print("\n" + "=" * 64 + f"\n  {t}\n" + "=" * 64)
def ok(t):    print(f"  [OK] {t}")
def warn(t):  print(f"  [!]  {t}")
def err(t):   print(f"  [X]  {t}")
def info(t):  print(f"  [i]  {t}")


def reset_json(path, transform_func, label, ts):
    if not os.path.exists(path):
        info(f"{label}: nicht vorhanden - skip")
        return False
    try:
        backup = f"{path}.fullreset_backup_{ts}"
        shutil.copy2(path, backup)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_data = transform_func(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        ok(label)
        return True
    except Exception as e:
        err(f"{label}: {e}")
        return False


def delete_file(path, label):
    if os.path.exists(path):
        try:
            os.remove(path)
            ok(f"{label}: geloescht")
            return True
        except Exception as e:
            err(f"{label}: {e}")
            return False
    info(f"{label}: nicht vorhanden")
    return False


def main():
    banner("FULL PAPER RESET (v2)")
    print(f"  Project: {PROJECT_ROOT}")

    if not os.path.exists(DATA_STORE):
        err(f"data_store nicht gefunden: {DATA_STORE}")
        return 1

    warn("WICHTIG: Bot muss VORHER GESTOPPT sein! (Strg+C)")
    print()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    files_in_ds = os.listdir(DATA_STORE)

    protected = {
        "brain_performance.json", "v4_imported_trades.json",
        "v4_strategy_weights.json", "trade_journal.json",
        "ki_analyse_log.json", "v4_data",
    }

    print(f"  Files im data_store: {len(files_in_ds)}")
    print()

    # === bot_state.json ===
    bot_state = os.path.join(DATA_STORE, "bot_state.json")
    def reset_bot_state(data):
        data["paper_balances_backup"] = {"USDC": RESET_CASH}
        data["open_positions_backup"] = {}
        data["open_orders_backup"] = {}
        data["realized_pnl"] = 0.0
        data["trade_count"] = 0
        data["daily_pnl"] = 0.0
        data["daily_loss"] = 0.0
        data["last_reset"] = datetime.now().isoformat()
        return data
    reset_json(bot_state, reset_bot_state, "bot_state.json", ts)

    # === paper_balances.json ===
    paper_bal = os.path.join(DATA_STORE, "paper_balances.json")
    def reset_paper_bal(data):
        return {"USDC": RESET_CASH}
    reset_json(paper_bal, reset_paper_bal, "paper_balances.json", ts)

    # === paper_state.json ===
    paper_state = os.path.join(DATA_STORE, "paper_state.json")
    def reset_paper_state(data):
        if isinstance(data, dict):
            data["balances"] = {"USDC": RESET_CASH}
            data["positions"] = {}
            data["realized_pnl"] = 0.0
            data["trade_count"] = 0
        return data
    reset_json(paper_state, reset_paper_state, "paper_state.json", ts)

    # === equity_history.json ===
    eq_hist = os.path.join(DATA_STORE, "equity_history.json")
    def reset_eq(data):
        return [{
            "timestamp": datetime.now().isoformat(),
            "equity": RESET_CASH,
            "cash": RESET_CASH,
            "positions_value": 0,
        }]
    reset_json(eq_hist, reset_eq, "equity_history.json", ts)

    # === daily_pnl.json ===
    daily = os.path.join(DATA_STORE, "daily_pnl.json")
    def reset_daily(data):
        return {}
    reset_json(daily, reset_daily, "daily_pnl.json", ts)

    # === Files die geloescht werden ===
    for fname in ["open_orders.json", "pending_orders.json",
                  "execution_state.json", "shadow_state.json"]:
        delete_file(os.path.join(DATA_STORE, fname), fname)

    # === SCAN: weitere State-Dateien finden ===
    print()
    info("Scan nach weiteren State-Files...")
    found_extra = []
    for fname in files_in_ds:
        if fname in protected:
            continue
        if fname.endswith(".json"):
            lower = fname.lower()
            if any(k in lower for k in ["balance", "state", "position", "pnl",
                                          "equity", "history", "cash"]):
                # Pruefen ob schon behandelt
                handled = ["bot_state.json", "paper_balances.json", "paper_state.json",
                          "equity_history.json", "daily_pnl.json"]
                if fname not in handled and not fname.startswith("v4_"):
                    full = os.path.join(DATA_STORE, fname)
                    try:
                        shutil.copy2(full, f"{full}.fullreset_backup_{ts}")
                        found_extra.append(fname)
                    except Exception:
                        pass

    if found_extra:
        warn(f"Zusatzliche State-Dateien (Backup gemacht): {', '.join(found_extra)}")
        warn("Falls Balance noch falsch ist, sag mir den Inhalt von diesen Dateien.")

    print()
    banner("FERTIG!")
    print()
    print(f"  Cash:                 {RESET_CASH:.2f} USDC")
    print(f"  Positionen:           0")
    print(f"  Trade-Counter:        0")
    print(f"  Realized P&L:         0$")
    print(f"  Daily Loss Tracking:  0")
    print()
    print("  BLEIBT INTAKT:")
    print("    brain_performance.json, v4_*.json, trade_journal.json")
    print()
    print("  NAECHSTER SCHRITT:")
    print("    1. Bot KOMPLETT beendet sein")
    print("    2. python app.py")
    print()
    print(f"  Backups: data_store/*.fullreset_backup_{ts}")
    print()
    print("  WENN BOT IMMER NOCH MIT FALSCHEM CASH STARTET:")
    print("    dir data_store /a > files.txt")
    print("    Schicke mir files.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
