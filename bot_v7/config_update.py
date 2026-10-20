#!/usr/bin/env python3
"""
================================================================
  CONFIG UPDATE - Sizing fuer 100$ pro Trade
================================================================
Setzt in data_store/config.json:
  - initial_paper_balance: 500.0  (Startkapital)
  - position_size_pct: 20          (20% = 100$ pro Trade)
  - max_open_positions: 5          (max 5 Positionen)
  - balanced mode: 20% / 5 Positionen (passend)

So bekommst du: 500$ Einsatz, ~100$ pro Trade, max 5 Positionen.

ALLE anderen Config-Werte bleiben unveraendert.
================================================================
"""
import os
import sys
import json
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
# config.json kann in data_store/ oder im Root liegen
_candidates = [
    os.path.join(ROOT, "data_store", "config.json"),
    os.path.join(ROOT, "config.json"),
    os.path.join(ROOT, "config", "config.json"),
]
CONFIG = next((p for p in _candidates if os.path.exists(p)), _candidates[0])


def banner(t): print("\n" + "=" * 64 + f"\n  {t}\n" + "=" * 64)
def ok(t):    print(f"  [OK] {t}")
def err(t):   print(f"  [X]  {t}")
def info(t):  print(f"  [i]  {t}")


# === HIER kannst du die Werte anpassen wenn du willst ===
NEW_BALANCE = 500.0
NEW_POSITION_PCT = 20      # 20% von 500 = 100$ pro Trade
NEW_MAX_POSITIONS = 4 


def main():
    banner("CONFIG UPDATE - Sizing fuer 100$ pro Trade")

    if not os.path.exists(CONFIG):
        err(f"config.json nicht gefunden!")
        info(f"Gesucht in: {', '.join(_candidates)}")
        return 1

    ok(f"Config gefunden: {CONFIG}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = CONFIG + f".sizing_backup_{ts}"
    shutil.copy2(CONFIG, backup)
    ok(f"Backup: {os.path.basename(backup)}")

    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    print()
    print("  AENDERUNGEN:")

    # trading.initial_paper_balance
    old = cfg.get("trading", {}).get("initial_paper_balance", "?")
    cfg.setdefault("trading", {})["initial_paper_balance"] = NEW_BALANCE
    print(f"    initial_paper_balance: {old} -> {NEW_BALANCE}")

    # trading.position_size_pct
    old = cfg.get("trading", {}).get("position_size_pct", "?")
    cfg["trading"]["position_size_pct"] = NEW_POSITION_PCT
    print(f"    position_size_pct:     {old} -> {NEW_POSITION_PCT}")

    # risk.max_open_positions
    old = cfg.get("risk", {}).get("max_open_positions", "?")
    cfg.setdefault("risk", {})["max_open_positions"] = NEW_MAX_POSITIONS
    print(f"    max_open_positions:    {old} -> {NEW_MAX_POSITIONS}")

    # modes.balanced anpassen (wird als aktiver Modus genutzt)
    if "modes" in cfg and "balanced" in cfg["modes"]:
        old_p = cfg["modes"]["balanced"].get("position_size_pct", "?")
        old_m = cfg["modes"]["balanced"].get("max_positions", "?")
        cfg["modes"]["balanced"]["position_size_pct"] = float(NEW_POSITION_PCT)
        cfg["modes"]["balanced"]["max_positions"] = NEW_MAX_POSITIONS
        print(f"    balanced.position_size_pct: {old_p} -> {NEW_POSITION_PCT}")
        print(f"    balanced.max_positions:     {old_m} -> {NEW_MAX_POSITIONS}")

    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print()
    ok("config.json gespeichert")

    banner("FERTIG!")
    print()
    print(f"  NEUE EINSTELLUNGEN:")
    print(f"    Startkapital:   {NEW_BALANCE}$ (Paper)")
    print(f"    Pro Trade:      {NEW_POSITION_PCT}% = {NEW_BALANCE * NEW_POSITION_PCT / 100:.0f}$")
    print(f"    Max Positionen: {NEW_MAX_POSITIONS}")
    print()
    print(f"  Bei {NEW_MAX_POSITIONS} Positionen voll investiert:")
    print(f"    {NEW_MAX_POSITIONS} x {NEW_BALANCE * NEW_POSITION_PCT / 100:.0f}$ = {NEW_MAX_POSITIONS * NEW_BALANCE * NEW_POSITION_PCT / 100:.0f}$")
    print(f"    (von {NEW_BALANCE}$ Kapital)")
    print()
    print("  NAECHSTER SCHRITT:")
    print("    1. Bot stoppen")
    print("    2. python scripts\\\\full_reset_final_v3.py")
    print("    3. python app.py")
    print()
    print(f"  Backup: {os.path.basename(backup)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
