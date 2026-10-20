#!/usr/bin/env python3
"""
MIGRATE V4 -> V6
================
Ein-Klick Migration: importiert alle V4-Daten in V6 und kalibriert das System.

Verwendung:
    1. Lege deine V4 JSON-Dateien in:  trading_imperium_v6/v4_data/
       - strategy_stats.json
       - trades_log_v4.json
       - equity_history.json
       - imperium_state.json  (API-Keys werden automatisch entfernt!)
       - evolution_data.json   (optional)

    2. Aus dem V6-Hauptverzeichnis:
       python scripts/migrate_v4_to_v6.py

    3. Dann V6 starten:
       python app.py

V6 nutzt automatisch die V4-Erkenntnisse:
    - Calibrator gewichtet Strategien nach echter V4-Performance
    - Verlierer-Strategien (STOCHRSI, MANUELL, EMA_TREND) sind gesperrt
    - Trade-History ist als Lerngrundlage importiert
"""

import os
import sys
import json
from datetime import datetime

# Pfad-Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Pfade
V4_DATA_DIR = os.path.join(PROJECT_ROOT, "v4_data")
V6_DATA_DIR = os.path.join(PROJECT_ROOT, "data_store")


def banner(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def main():
    banner("MIGRATE V4 -> V6")
    print(f"V4-Daten:    {V4_DATA_DIR}")
    print(f"V6-Daten:    {V6_DATA_DIR}")

    if not os.path.exists(V4_DATA_DIR):
        print(f"\nFEHLER: V4-Daten-Ordner nicht gefunden: {V4_DATA_DIR}")
        print("Erstelle den Ordner und lege deine V4 JSON-Dateien dort ab.")
        return 1

    # Welche Files sind vorhanden?
    expected = ["strategy_stats.json", "trades_log_v4.json",
                "equity_history.json", "imperium_state.json"]
    found = [f for f in expected if os.path.exists(os.path.join(V4_DATA_DIR, f))]
    missing = [f for f in expected if f not in found]

    print(f"\nGefundene V4-Dateien ({len(found)}/{len(expected)}):")
    for f in found:
        print(f"  OK  {f}")
    for f in missing:
        print(f"  --  {f} (fehlt - optional)")

    if not found:
        print("\nKeine V4-Dateien gefunden. Abbruch.")
        return 1

    # === SCHRITT 1: V4-Daten importieren ===
    banner("SCHRITT 1: V4-Daten importieren")
    try:
        from data.v4_importer import import_all, get_import_summary
        counts = import_all(V4_DATA_DIR, V6_DATA_DIR)
        print(f"  Trades importiert:     {counts['trades']}")
        print(f"  Equity-Punkte:         {counts['equity_points']}")
        print(f"  BTC-Kaeufe (Sparplan): {counts['btc_buys']}")
        print(f"  Settings (bereinigt):  {counts['settings']}")

        summary = get_import_summary(V6_DATA_DIR)
        if summary.get("available"):
            print(f"\n  Total importiert:      {summary['total_trades']} Trades")
            print(f"  Davon abgeschlossen:   {summary['completed_trades']}")
            print(f"  Gesamt-PnL:            {summary['total_pnl']:+.2f} EUR")
    except Exception as e:
        print(f"FEHLER beim Import: {e}")
        import traceback; traceback.print_exc()
        return 1

    # === SCHRITT 2: Calibrator initialisieren ===
    banner("SCHRITT 2: Performance-Calibrator initialisieren")
    try:
        from models.v4_calibrator import V4Calibrator
        stats_path = os.path.join(V4_DATA_DIR, "strategy_stats.json")
        cal = V4Calibrator.load(stats_path)
        print(cal.report())

        # In V6 data_store als Cache schreiben (V6 laedt das beim Start)
        cal_cache_path = os.path.join(V6_DATA_DIR, "v4_strategy_weights.json")
        os.makedirs(V6_DATA_DIR, exist_ok=True)
        with open(cal_cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": "v4_calibrator_1.0",
                "computed_at": datetime.now().astimezone().isoformat(),
                "weights": cal.weights,
                "blocked": [s for s, w in cal.weights.items() if w == 0.0],
                "source_stats": cal.stats,
            }, f, indent=2)
        print(f"\n  Gewichte gecached: {cal_cache_path}")
    except Exception as e:
        print(f"FEHLER beim Calibrator: {e}")
        import traceback; traceback.print_exc()
        return 1

    # === SCHRITT 3: V4 Strategien-Ensemble testen ===
    banner("SCHRITT 3: V4-Strategien-Ensemble testen")
    try:
        from agents.v4_strategies import V4StrategyEnsemble, V4_STRATEGIES
        ens = V4StrategyEnsemble()
        print(f"  Ensemble geladen: {len(V4_STRATEGIES)} Strategien")
        for sid in V4_STRATEGIES:
            w = cal.get_weight(sid)
            mark = "[OK]" if w > 0.5 else "[GEDAEMPFT]" if w > 0 else "[GESPERRT]"
            print(f"    {sid:<22} weight={w:.2f}  {mark}")
    except Exception as e:
        print(f"FEHLER beim Strategien-Test: {e}")
        return 1

    # === ZUSAMMENFASSUNG ===
    banner("MIGRATION ABGESCHLOSSEN")
    print("Naechste Schritte:")
    print("  1. Pruefe ob app.py den V4-Calibrator + V4-Ensemble laedt")
    print("     (siehe docs/INTEGRATION_GUIDE.md)")
    print("  2. Starte V6 im Demo-Modus:  python app.py")
    print("  3. Im Dashboard: Tab 'Agents' - dort sollten die V4-Gewichte sichtbar sein")
    print("\nViel Erfolg!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
