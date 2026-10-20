#!/usr/bin/env python3
"""
================================================================
  FULL RESET FINAL v3 (mit Impact-Journal Cleanup)
================================================================
Wie v2, aber zusaetzlich:
- Leert auch impact_journal.json (NEU)
- Setzt .reset_marker fuer garantierten Fresh-Start

LEERT:
- trades_v5.json (Trade-Counter + History)
- order_history.json (Order-Tracking)
- bot_state.json (Equity-History + Counter)
- equity_history.json
- agent_votes.json
- idempotency_keys.json
- impact_journal.json (NEU!)

BLEIBT INTAKT (Lerngold):
- brain_performance.json (Strategie-Lernhistorie!)
- v4_imported_trades.json (V4-Daten)
- v4_imported_equity.json
- v4_imported_state.json
- v4_strategy_weights.json
- trade_journal.json (Langzeit-Historie)

WICHTIG: Bot muss VORHER gestoppt sein!
================================================================
"""
import os
import sys
import json
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "scripts" else SCRIPT_DIR
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
            shutil.copy2(path, f"{path}.finalreset_v3_{ts}")
            return True
        except Exception:
            pass
    return False


def main():
    banner("FULL RESET FINAL v3 (mit Impact-Journal)")
    print(f"  Project: {PROJECT_ROOT}")
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

    # === bot_state.json.bak loeschen ===
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

    # === NEU v3: impact_journal.json ===
    p = os.path.join(DATA_STORE, "impact_journal.json")
    if os.path.exists(p):
        backup_file(p, ts)
        try:
            with open(p, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_count = len(old.get("entries", [])) if isinstance(old, dict) else (len(old) if isinstance(old, list) else 0)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"saved_at": datetime.now().isoformat(),
                          "total_entries": 0, "entries": []}, f, indent=2)
            ok(f"impact_journal.json geleert ({old_count} -> 0 Trade-Begruendungen)")
        except Exception as e:
            err(f"impact_journal.json: {e}")
    else:
        info("impact_journal.json existiert noch nicht (wird beim ersten Trade erstellt)")

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
    print(f"  Cash:               {RESET_CASH:.2f} USDC (oder initial_paper_balance aus config)")
    print(f"  Trades:             0")
    print(f"  Order-History:      0")
    print(f"  Realized P&L:       0")
    print(f"  Equity History:     leer")
    print(f"  Impact-Journal:     leer")
    print(f"  RESET-MARKER:       GESETZT")
    print()
    print("  BLEIBT INTAKT (Lerngold):")
    print("    brain_performance.json (Strategie-Lernhistorie)")
    print("    v4_imported_*.json (V4 Trade-Wissen)")
    print("    v4_strategy_weights.json (Brain-Gewichtungen)")
    print("    trade_journal.json (Langzeit-Historie)")
    print()
    print("  NAECHSTER SCHRITT:")
    print("    python app.py")
    print()
    print("  IM LOG SOLLTE STEHEN:")
    print("    [APP] RESET-MARKER erkannt - frischer Start mit X USDC")
    print("    [APP] DocAgent initialisiert")
    print("    [APP] TicketsWatcher initialisiert")
    print("    [APP] ImpactJournal initialisiert")
    print()
    print(f"  Backups: data_store/*.finalreset_v3_{ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
