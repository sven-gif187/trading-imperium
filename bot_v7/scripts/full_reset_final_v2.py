#!/usr/bin/env python3
"""
================================================================
  FULL RESET FINAL v2 (mit Marker)
================================================================
Wie v1, aber zusaetzlich:
- Setzt eine Marker-Datei .reset_marker im data_store
- Bot erkennt Marker beim Start und ignoriert State-Backups
- Marker wird beim ersten Bot-Start geloescht

EFFEKT: Reset = wirklich Reset. Bot kann den State nicht
nachtraeglich ueberschreiben bevor wir's checken konnten.

WICHTIG: Bot muss VORHER gestoppt sein!
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


def backup_file(path, ts):
    if os.path.exists(path):
        try:
            shutil.copy2(path, f"{path}.finalreset_{ts}")
            return True
        except Exception:
            pass
    return False


def main():
    banner("FULL RESET FINAL v2 (mit Marker)")
    print(f"  Data Store: {DATA_STORE}")

    if not os.path.exists(DATA_STORE):
        err(f"data_store nicht gefunden: {DATA_STORE}")
        return 1

    warn("WICHTIG: Bot muss VORHER GESTOPPT sein!")
    print()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # === trades_v5.json ===
    p = os.path.join(DATA_STORE, "trades_v5.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_count = len(old) if isinstance(old, list) else "?"
            with open(p, "w", encoding="utf-8") as f:
                json.dump([], f)
            ok(f"trades_v5.json geleert ({old_count} -> 0 Trades)")
        except Exception as e:
            err(f"trades_v5.json: {e}")

    # === order_history.json ===
    p = os.path.join(DATA_STORE, "order_history.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_count = len(old) if isinstance(old, list) else "?"
            with open(p, "w", encoding="utf-8") as f:
                json.dump([], f)
            ok(f"order_history.json geleert ({old_count} -> 0 Orders)")
        except Exception as e:
            err(f"order_history.json: {e}")

    # === bot_state.json ===
    p = os.path.join(DATA_STORE, "bot_state.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict):
                if "equity_history" in state:
                    state["equity_history"] = []
                for key in ["realized_pnl", "trade_count", "total_trades",
                            "daily_pnl", "daily_loss", "pnl"]:
                    if key in state:
                        state[key] = 0
                for key in ["paper_balances_backup", "paper_balances"]:
                    if key in state:
                        state[key] = {"USDC": RESET_CASH}
                for key in ["open_positions_backup", "open_orders_backup",
                            "open_positions", "positions"]:
                    if key in state:
                        state[key] = {}
                state["_last_reset"] = datetime.now().isoformat()
            with open(p, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            ok("bot_state.json: equity_history + counter geleert")
        except Exception as e:
            err(f"bot_state.json: {e}")

    # === bot_state.json.bak ===
    p = os.path.join(DATA_STORE, "bot_state.json.bak")
    if os.path.exists(p):
        try:
            os.remove(p)
            ok("bot_state.json.bak geloescht")
        except Exception:
            pass

    # === equity_history.json ===
    p = os.path.join(DATA_STORE, "equity_history.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump([], f)
            ok("equity_history.json geleert")
        except Exception:
            pass

    # === idempotency_keys ===
    p = os.path.join(DATA_STORE, "idempotency_keys.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                old = json.load(f)
            empty = [] if isinstance(old, list) else {}
            with open(p, "w", encoding="utf-8") as f:
                json.dump(empty, f)
            ok("idempotency_keys.json geleert")
        except Exception:
            pass

    # === agent_votes.json ===
    p = os.path.join(DATA_STORE, "agent_votes.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                old = json.load(f)
            empty = [] if isinstance(old, list) else {}
            with open(p, "w", encoding="utf-8") as f:
                json.dump(empty, f)
            ok("agent_votes.json geleert")
        except Exception:
            pass

    # === DER MARKER ===
    marker_path = os.path.join(DATA_STORE, ".reset_marker")
    try:
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())
        ok(f".reset_marker gesetzt - Bot startet GARANTIERT frisch")
    except Exception as e:
        err(f".reset_marker: {e}")
        return 1

    print()
    banner("FERTIG!")
    print()
    print(f"  Cash:               {RESET_CASH:.2f} USDC")
    print(f"  Trades:             0")
    print(f"  Order-History:      0")
    print(f"  Realized P&L:       0")
    print(f"  Equity History:     leer")
    print(f"  RESET-MARKER:       GESETZT")
    print()
    print("  BLEIBT INTAKT (Lerngold):")
    print("    brain_performance.json")
    print("    v4_imported_*.json")
    print("    v4_strategy_weights.json")
    print("    trade_journal.json")
    print()
    print("  WICHTIG: install_bugfixes.py muss installiert sein")
    print("  damit der Marker beim Bot-Start auch erkannt wird!")
    print()
    print("  NAECHSTER SCHRITT:")
    print("    python app.py")
    print()
    print("  IM LOG SOLLTE STEHEN:")
    print("    [APP] RESET-MARKER erkannt - frischer Start mit 1000.00 USDC")
    print()
    print(f"  Backups: data_store/*.finalreset_{ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
