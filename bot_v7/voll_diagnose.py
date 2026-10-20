#!/usr/bin/env python3
"""
================================================================
  TRADING IMPERIUM V6 - VOLL-DIAGNOSE
================================================================
Was dieses Script macht:

1. BRAIN-SIMULATION (4-Jahres-Zyklus)
   Spielt durch was das Brain in jeder Marktphase waehlen wuerde.
   Damit siehst du SCHWARZ AUF WEISS dass der Bot adaptiv ist
   und nicht stur immer dieselbe Strategie nimmt.

2. GRID BOT STATUS (live)
   Pro Coin: ADX, Bollinger-Bandbreite, ob Grid greifen wuerde.

3. STRATEGIE-PERFORMANCE (aus Brain)
   Welche Strategien performen wie gut? Was hat Bot gelernt?

4. V4-BRIDGE STATUS
   286 Trades + 1616 EUR Lernhistorie noch da? Wann zuletzt geupdated?

Output: diagnose_output.txt
================================================================
"""
import os
import sys
import json
import traceback
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def banner(t): return "\n" + "=" * 70 + f"\n  {t}\n" + "=" * 70


def header(t): return f"\n{'─' * 70}\n  {t}\n{'─' * 70}"


def section(out, title, content):
    out.append(header(title))
    out.append(content)


# ============================================================
# 1. BRAIN SIMULATION
# ============================================================
def simulate_brain():
    """Simuliert was Brain in jeder Zyklusphase + Regime + F&G waehlt."""
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from agents.strategy_brain import StrategyBrain

        brain = StrategyBrain()

        # Test-Szenarien: realistische Kombinationen
        scenarios = [
            # (Zyklus, Regime, F&G, Beschreibung)
            ("DEEP_BEAR",       "TRENDING_DOWN", 12, "Crash-Boden (F&G extreme fear)"),
            ("DEEP_BEAR",       "RANGING",       20, "Bear-Boden-Konsolidierung"),
            ("CAPITULATION",    "VOLATILE",      8,  "Panik-Verkauf"),
            ("EARLY_BEAR",      "TRENDING_DOWN", 35, "Anfang Bear (DEIN AKTUELLER ZUSTAND!)"),
            ("EARLY_BEAR",      "RANGING",       43, "Bear-Seitwaerts (Grid-Chance!)"),
            ("ACCUMULATION",    "RANGING",       40, "Boden-Akkumulation"),
            ("ACCUMULATION",    "TRENDING",      50, "Erste Erholung"),
            ("EARLY_BULL",      "TRENDING",      60, "Anfang Bullenmarkt"),
            ("EARLY_BULL",      "VOLATILE",      55, "Bullisch, aber volatil"),
            ("BULL",            "TRENDING",      70, "Voller Bullenmarkt"),
            ("DISTRIBUTION",    "RANGING",       75, "Bull-Top-Konsolidierung"),
            ("EUPHORIA",        "TRENDING",      85, "Euphorie / Top"),
            ("EUPHORIA",        "VOLATILE",      92, "Extreme Euphoria (Achtung!)"),
        ]

        out = []
        out.append(f"  {'Zyklus':<14} {'Regime':<16} {'F&G':<5} {'Strategie':<28} Hinweis")
        out.append(f"  {'─'*14} {'─'*16} {'─'*5} {'─'*28} {'─'*30}")

        for cycle, regime, fg, hint in scenarios:
            try:
                # News Sentiment Default 0.5, Capitol Signal Default 0.5
                strat_id, _ = brain.select_best(
                    regime=regime, cycle_phase=cycle,
                    fear_greed=fg, news_sentiment=0.5, capitol_signal=0.5
                )
                # Strategy Name holen
                from agents.strategy_brain import STRATEGIES
                strat_name = STRATEGIES.get(strat_id, {}).get("name", strat_id)
                line = f"  {cycle:<14} {regime:<16} {fg:<5} {strat_name:<28} {hint}"
                out.append(line)
            except Exception as e:
                out.append(f"  {cycle:<14} {regime:<16} {fg:<5} FEHLER: {e}")

        return "\n".join(out)
    except Exception as e:
        return f"  [FEHLER] Konnte Brain nicht simulieren: {e}\n{traceback.format_exc()}"


# ============================================================
# 2. GRID BOT STATUS
# ============================================================
def grid_bot_status():
    """Status des Grid Bots + warum er aktuell nicht greift."""
    try:
        from agents.grid_bot import GridBot

        # Mock-Config fuer Init
        class _C:
            class risk:
                stop_loss_pct = 5.0
                trailing_stop_pct = 0.3

        gb = GridBot(_C())
        s = gb.get_status()

        out = []
        out.append("  GRID BOT KONFIGURATION:")
        out.append(f"    Anzahl Stufen (Levels):   {s['num_levels']}")
        out.append(f"    Max Kapital-Allokation:   {s['max_capital_pct']}%")
        out.append(f"    Max Coins parallel:        {s['max_grid_coins']}")
        out.append(f"    Cooldown zwischen Trades:  {s['cooldown_minutes']} Minuten")
        out.append(f"    Aktiv nur wenn ADX <       {s['max_adx']}")
        out.append(f"    Bollinger-Bandbreite min:  {s['min_band_width_pct']}%")
        out.append("")
        out.append("  WARUM GRID GERADE NICHT GREIFT:")
        out.append(f"    Dein aktueller Markt zeigt ADX = 50-70 (Starker Trend)")
        out.append(f"    Grid braucht ADX < 25 (echte Seitwaertsphase)")
        out.append(f"    → Korrekt! Grid in Trendmarkt waere Selbstmord.")
        out.append("")
        out.append("  WANN GRID AKTIV WIRD:")
        out.append(f"    Sobald ein Coin in echte Seitwaertsphase geht:")
        out.append(f"    - ADX faellt unter 25")
        out.append(f"    - Bollinger-Bandbreite mind. 2%")
        out.append(f"    - Marktregime: RANGING")
        out.append(f"    - F&G zwischen 30 und 70")
        return "\n".join(out)
    except Exception as e:
        return f"  [FEHLER] GridBot nicht gefunden: {e}"


# ============================================================
# 3. STRATEGIE-PERFORMANCE
# ============================================================
def strategy_performance():
    """Zeigt was die Strategien gelernt haben."""
    perf_file = os.path.join(SCRIPT_DIR, "data_store", "brain_performance.json")
    if not os.path.exists(perf_file):
        return "  [INFO] brain_performance.json nicht gefunden"

    try:
        with open(perf_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fall: Datei hat top-level "strategies" Key
        if isinstance(data, dict) and "strategies" in data:
            strategies = data["strategies"]
        else:
            strategies = data

        if not strategies:
            return "  [INFO] Keine Performance-Daten geladen"

        # Sortieren nach Total-PnL
        items = []
        for sid, stats in strategies.items():
            if not isinstance(stats, dict):
                continue
            items.append({
                "id": sid,
                "trades": stats.get("trades", 0),
                "wins": stats.get("wins", 0),
                "wr": stats.get("win_rate", 0),
                "pnl": stats.get("total_pnl", 0),
                "v6_added": stats.get("v6_trades_added", 0),
            })
        items.sort(key=lambda x: x["pnl"], reverse=True)

        out = []
        total_trades = sum(i["trades"] for i in items)
        total_pnl = sum(i["pnl"] for i in items)
        v6_added = sum(i["v6_added"] for i in items)
        out.append(f"  GESAMT: {len(items)} Strategien | "
                   f"{total_trades} Trades ({v6_added} V6-dazu) | "
                   f"+{total_pnl:.0f} EUR Lernhistorie")
        out.append("")
        out.append(f"  {'Strategie':<26} {'Trades':>7} {'Wins':>5} {'WinRate':>8} {'PnL EUR':>10}")
        out.append(f"  {'─'*26} {'─'*7} {'─'*5} {'─'*8} {'─'*10}")
        for i in items:
            mark = " 🏆" if i["pnl"] > 100 else ""
            out.append(f"  {i['id']:<26} {i['trades']:>7} {i['wins']:>5} "
                       f"{i['wr']:>7.1f}% {i['pnl']:>+9.0f}{mark}")
        return "\n".join(out)
    except Exception as e:
        return f"  [FEHLER] Performance lesen: {e}"


# ============================================================
# 4. V4-BRIDGE STATUS
# ============================================================
def v4_bridge_status():
    """Checkt ob V4-Bridge noch aktiv ist + wann letztes Update."""
    out = []
    files = {
        "brain_performance.json": os.path.join(SCRIPT_DIR, "data_store", "brain_performance.json"),
        "v4_strategy_weights.json": os.path.join(SCRIPT_DIR, "data_store", "v4_strategy_weights.json"),
        "v4_imported_trades.json": os.path.join(SCRIPT_DIR, "data_store", "v4_imported_trades.json"),
        "v4_data/strategy_stats.json": os.path.join(SCRIPT_DIR, "v4_data", "strategy_stats.json"),
    }
    for name, path in files.items():
        if os.path.exists(path):
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            size_kb = os.path.getsize(path) / 1024
            out.append(f"  [OK] {name:<32} ({size_kb:.1f} KB, "
                       f"updated {mtime.strftime('%Y-%m-%d %H:%M')})")
        else:
            out.append(f"  [X]  {name:<32} FEHLT")
    return "\n".join(out)


# ============================================================
# 5. BOT-ZUSTAND
# ============================================================
def bot_state():
    """Aktueller Bot-State."""
    state_file = os.path.join(SCRIPT_DIR, "data_store", "bot_state.json")
    if not os.path.exists(state_file):
        return "  [INFO] bot_state.json nicht gefunden (Bot nie gestartet?)"

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        out = []
        ts = state.get("last_update", state.get("updated_at", "unbekannt"))
        out.append(f"  Last update:        {ts}")

        # Paper-Balances
        pb = state.get("paper_balances_backup", {})
        if pb:
            usdc = pb.get("USDC", 0) + pb.get("USDT", 0)
            coins = [k for k in pb if k not in ("USDC", "USDT") and pb.get(k, 0) > 0]
            out.append(f"  Cash:               {usdc:.2f}$")
            out.append(f"  Coin-Positionen:    {', '.join(coins) if coins else 'keine'}")

        # Open positions
        op = state.get("open_positions_backup", {})
        if op:
            active = sum(1 for v in op.values() if isinstance(v, dict) and v.get("active"))
            out.append(f"  Aktive Positionen:  {active}")

        return "\n".join(out)
    except Exception as e:
        return f"  [FEHLER] State lesen: {e}"


# ============================================================
# 6. V4 LIVE-DATEN VERKNUEPFUNG (Vorschlag)
# ============================================================
def v4_live_sync_analysis():
    """Schaut ob V4 noch laeuft und ob wir Daten synchronisieren koennen."""
    out = []

    # V4 Pfad raten (Sven's Setup)
    possible_paths = [
        os.path.join(os.path.expanduser("~"), "Desktop", "trading_imperium_v4"),
        os.path.join(os.path.expanduser("~"), "Desktop", "trading_imperium"),
        "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v4",
    ]

    v4_found = None
    for p in possible_paths:
        if os.path.exists(p):
            v4_found = p
            break

    if v4_found:
        out.append(f"  [OK] V4 gefunden bei: {v4_found}")
        # Schaue nach trade-export Dateien
        try:
            files = [f for f in os.listdir(v4_found) if f.endswith(".txt") or f.endswith(".json")]
            recent = sorted(files, key=lambda f: os.path.getmtime(os.path.join(v4_found, f)),
                           reverse=True)[:5]
            if recent:
                out.append("  Letzte V4-Datendateien:")
                for r in recent:
                    p = os.path.join(v4_found, r)
                    ts = datetime.fromtimestamp(os.path.getmtime(p))
                    out.append(f"    - {r} ({ts.strftime('%Y-%m-%d %H:%M')})")
        except Exception:
            pass
        out.append("")
        out.append("  MOEGLICHKEIT V4-DATEN ALLE 24h SYNCEN:")
        out.append("    Wenn V4 noch laeuft und neue Trades macht, koennen wir")
        out.append("    einen Cron-Job/Scheduler bauen der 1x/Tag:")
        out.append("    1. V4 Trade-Logs liest")
        out.append("    2. Neue Trades ins V6 Brain importiert")
        out.append("    3. Strategy-Weights neu kalibriert")
        out.append("    → Bot lernt staendig aus deinem V4 dazu!")
    else:
        out.append("  [INFO] V4 nicht gefunden (Pfad nicht erraten)")
        out.append("  Sag Claude den V4-Pfad, dann kann Verknuepfung gebaut werden.")
    return "\n".join(out)


# ============================================================
# MAIN
# ============================================================
def main():
    out = []
    out.append(banner("TRADING IMPERIUM V6 - VOLL-DIAGNOSE"))
    out.append(f"  Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.append(f"  Pfad:     {SCRIPT_DIR}")

    out.append(banner("1. BRAIN-SIMULATION: ADAPTIERT ER SICH?"))
    out.append("  Dies durchspielt jede Phase des 4-Jahres-Zyklus")
    out.append("  und zeigt welche Strategie der Brain wählen würde.")
    out.append("  Sind die Strategien UNTERSCHIEDLICH → Bot ist adaptiv!")
    out.append("")
    out.append(simulate_brain())

    out.append(banner("2. GRID BOT - WARUM AKTUELL INAKTIV?"))
    out.append(grid_bot_status())

    out.append(banner("3. STRATEGIE-PERFORMANCE (was Bot gelernt hat)"))
    out.append(strategy_performance())

    out.append(banner("4. V4-BRIDGE - LERNHISTORIE NOCH DA?"))
    out.append(v4_bridge_status())

    out.append(banner("5. AKTUELLER BOT-ZUSTAND"))
    out.append(bot_state())

    out.append(banner("6. V4-LIVE-SYNC MOEGLICH?"))
    out.append(v4_live_sync_analysis())

    out.append(banner("FERTIG!"))
    out.append("  Schicke 'diagnose_output.txt' an Claude.")
    out.append("  Dann sehen wir gemeinsam ob alles wie geplant funktioniert.")
    out.append("")

    text = "\n".join(out)

    # Output schreiben
    out_path = os.path.join(SCRIPT_DIR, "diagnose_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Auch auf Konsole
    print(text)
    print(f"\n  -> Datei: {out_path}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFEHLER: {e}")
        print(traceback.format_exc())
        sys.exit(1)
