#!/usr/bin/env python3
"""
================================================================
  V4-BRIDGE DIAGNOSE
================================================================
Prueft was von der V4-Bridge in V6 wirklich aktiv ist.
Liest nur Files - kein Bot-Restart noetig!
================================================================
"""
import os
import json

OK = "[OK]"
FAIL = "[X] "
WARN = "[!] "


def banner(text):
    print("\n" + "=" * 64)
    print(f"  {text}")
    print("=" * 64)


def check(label, condition, detail=""):
    sym = OK if condition else FAIL
    line = f"  {sym} {label}"
    if detail:
        line += f"  -> {detail}"
    print(line)
    return condition


def main():
    banner("V4-BRIDGE DIAGNOSE - Trading Imperium V6")
    print(f"  Verzeichnis: {os.getcwd()}")

    score = {"ok": 0, "fail": 0, "warn": 0}

    # ============================================================
    # 1. FILES VORHANDEN?
    # ============================================================
    banner("1. BRIDGE-DATEIEN")
    files_to_check = [
        ("agents/v4_strategies.py",          "V4 Strategien-Modul"),
        ("models/v4_calibrator.py",          "V4 Performance-Calibrator"),
        ("models/brain_persistence.py",       "Brain Persistence (Lern-Speicher)"),
        ("data/v4_importer.py",              "V4 Daten-Importer"),
        ("v4_data/strategy_stats.json",      "V4 Performance-Daten"),
    ]
    for path, label in files_to_check:
        if check(f"{label} ({path})", os.path.exists(path)):
            score["ok"] += 1
        else:
            score["fail"] += 1

    # ============================================================
    # 2. APP.PY GEPATCHT?
    # ============================================================
    banner("2. APP.PY PATCHES")
    if os.path.exists("app.py"):
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        patches_app = [
            ("V4StrategyEnsemble Import",    "from agents.v4_strategies import V4StrategyEnsemble"),
            ("V4Calibrator Import",          "from models.v4_calibrator import V4Calibrator"),
            ("BrainPersistence Import",      "from models.brain_persistence import BrainPersistence"),
            ("V4-Ensemble initialisiert",    "self.v4_ensemble = V4StrategyEnsemble()"),
            ("V4-Calibrator geladen",        "V4Calibrator.load("),
            ("Brain Persistence aktiv",       "self.brain_persistence = BrainPersistence()"),
            ("Initial Performance geladen",  "initial_perf = self.brain_persistence.load_performance()"),
            ("Brain-Performance gesetzt",    "self.strategy_brain.performance = initial_perf"),
            ("SignalAgent V4-Injection",     "self.signal_agent.v4_ensemble = self.v4_ensemble"),
        ]
        for label, marker in patches_app:
            if check(label, marker in content):
                score["ok"] += 1
            else:
                score["fail"] += 1
    else:
        check("app.py existiert", False)
        score["fail"] += 1

    # ============================================================
    # 3. SIGNAL_AGENT.PY GEPATCHT?
    # ============================================================
    banner("3. SIGNAL_AGENT.PY PATCHES")
    if os.path.exists("agents/signal_agent.py"):
        with open("agents/signal_agent.py", "r", encoding="utf-8") as f:
            content = f.read()
        patches_signal = [
            ("v4_ensemble Attribut",          "self.v4_ensemble = None"),
            ("v4_calibrator Attribut",         "self.v4_calibrator = None"),
            ("V4 Bridge im analyze()",        "v4_ensemble.evaluate_buy"),
            ("V4 STARK Score-Boost",           "STARK"),
        ]
        for label, marker in patches_signal:
            if check(label, marker in content):
                score["ok"] += 1
            else:
                score["fail"] += 1
    else:
        check("agents/signal_agent.py existiert", False)
        score["fail"] += 1

    # ============================================================
    # 4. STRATEGY_BRAIN.PY GEPATCHT?
    # ============================================================
    banner("4. STRATEGY_BRAIN.PY PATCHES (Persistenz)")
    if os.path.exists("agents/strategy_brain.py"):
        with open("agents/strategy_brain.py", "r", encoding="utf-8") as f:
            content = f.read()
        patches_brain = [
            ("BrainPersistence Auto-Save",    "BrainPersistence().save_performance"),
            ("V6-Trade Counter",              "v6_trades_added"),
        ]
        for label, marker in patches_brain:
            if check(label, marker in content):
                score["ok"] += 1
            else:
                score["fail"] += 1
    else:
        check("agents/strategy_brain.py existiert", False)
        score["fail"] += 1

    # ============================================================
    # 5. DATA STORE - WIRD WIRKLICH GESPEICHERT?
    # ============================================================
    banner("5. DATA STORE - LIVE-LERNEN AKTIV?")
    bp_file = "data_store/brain_performance.json"
    if check(f"Brain-Performance gespeichert ({bp_file})", os.path.exists(bp_file)):
        score["ok"] += 1
        try:
            with open(bp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            perf = data.get("performance", {})
            saved_at = data.get("saved_at", "?")
            total_trades = sum(p.get("trades", 0) for p in perf.values())
            v6_added = sum(p.get("v6_trades_added", 0) for p in perf.values())
            v4_baseline = total_trades - v6_added
            total_pnl = sum(p.get("total_pnl", 0) for p in perf.values())

            print(f"      Gespeichert am:    {saved_at}")
            print(f"      Strategien:        {len(perf)}")
            print(f"      Trades total:      {total_trades}")
            print(f"        davon V4-Basis:  {v4_baseline}")
            print(f"        davon V6 dazu:   {v6_added}  {'(=> V6 lernt aktiv!)' if v6_added > 0 else '(noch keine V6-Trades closed)'}")
            print(f"      Total PnL:         {total_pnl:+.2f} EUR")

            if perf:
                print(f"\n      Top-3 Strategien:")
                top = sorted(perf.items(), key=lambda x: x[1].get("total_pnl", 0), reverse=True)[:3]
                for sid, p in top:
                    extra = f" (+{p.get('v6_trades_added', 0)} V6)" if p.get('v6_trades_added', 0) > 0 else ""
                    print(f"        {sid:<22} {p.get('trades', 0)} trades, "
                          f"{p.get('total_pnl', 0):+.0f} EUR{extra}")
        except Exception as e:
            print(f"      Fehler beim Lesen: {e}")
            score["warn"] += 1
    else:
        score["fail"] += 1

    # V4 Calibrator Cache
    weights_file = "data_store/v4_strategy_weights.json"
    if check(f"V4-Gewichte gecached ({weights_file})", os.path.exists(weights_file)):
        score["ok"] += 1
        try:
            with open(weights_file, "r", encoding="utf-8") as f:
                w = json.load(f)
            weights = w.get("weights", {})
            top_weights = sorted(weights.items(), key=lambda x: -x[1])[:3]
            for sid, weight in top_weights:
                print(f"        {sid:<22} weight={weight:.2f}")
        except Exception:
            pass
    else:
        score["fail"] += 1

    # V4-Imported Trades
    trades_file = "data_store/v4_imported_trades.json"
    if check(f"V4-Trades importiert ({trades_file})", os.path.exists(trades_file)):
        score["ok"] += 1
        try:
            with open(trades_file, "r", encoding="utf-8") as f:
                trades = json.load(f)
            print(f"      {len(trades)} V4-Trades als Lerngrundlage")
        except Exception:
            pass

    # ============================================================
    # GESAMTBEWERTUNG
    # ============================================================
    banner("GESAMTBEWERTUNG")
    total = score["ok"] + score["fail"] + score["warn"]
    pct = (score["ok"] / total * 100) if total > 0 else 0
    print(f"  Checks bestanden: {score['ok']}/{total} ({pct:.0f}%)")
    print(f"    OK:    {score['ok']}")
    print(f"    Fehler: {score['fail']}")
    if score["warn"]:
        print(f"    Warn:  {score['warn']}")

    print()
    if score["fail"] == 0:
        print("  STATUS: V4-BRIDGE VOLL AKTIV!")
        print("  -> Bot lernt aus V4-Wissen + sammelt eigene Daten")
    elif score["fail"] <= 3:
        print("  STATUS: V4-BRIDGE TEILWEISE AKTIV")
        print("  -> Einige Patches fehlen - kann ich nachpatchen")
    else:
        print("  STATUS: V4-BRIDGE NICHT AKTIV")
        print("  -> Patches haben nicht gegriffen - braucht Reparatur")

    print()
    print("  Schick diesen Output als Screenshot an Claude.")
    return 0


if __name__ == "__main__":
    main()
