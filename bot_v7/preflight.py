#!/usr/bin/env python3
"""Pre-Flight Check - Ist der Bot Live-Trading ready?"""
import os
import sys
import json
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data_store")

class C:
    R = "\033[0m"; B = "\033[1m"; G = "\033[92m"; RED = "\033[91m"
    Y = "\033[93m"; CY = "\033[96m"; GR = "\033[90m"

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        for a in dir(C):
            if not a.startswith("_"): setattr(C, a, "")


def check(name, passed, info=""):
    icon = f"{C.G}✓{C.R}" if passed else f"{C.RED}✗{C.R}"
    status = f"{C.G}OK{C.R}" if passed else f"{C.RED}FEHLT{C.R}"
    print(f"  {icon}  [{status}]  {C.B}{name}{C.R}")
    if info:
        print(f"        {C.GR}{info}{C.R}")
    return passed


def main():
    print(f"\n{C.CY}{C.B}{'='*70}")
    print(f"  PRE-FLIGHT CHECK - Bist du Live-Trading ready?")
    print(f"{'='*70}{C.R}\n")

    results = []

    # === 1. Paper-Bot Laufzeit ===
    print(f"\n{C.Y}{C.B}  1. PAPER-BOT LAUFZEIT (>= 14 Tage){C.R}")
    bot_state = os.path.join(DATA, "bot_state.json")
    days_running = 0
    if os.path.exists(bot_state):
        try:
            with open(bot_state) as f:
                state = json.load(f)
            equity_hist = state.get("equity_history", [])
            if equity_hist:
                first_ts = equity_hist[0].get("timestamp", "") if isinstance(equity_hist[0], dict) else ""
                if first_ts:
                    days_running = (datetime.now() - datetime.fromisoformat(first_ts)).days
        except Exception:
            pass
    results.append(check("Paper-Bot 14+ Tage stabil",
                         days_running >= 14,
                         f"Aktuell: {days_running} Tage gelaufen"))

    # === 2. Win-Rate >= 50% ===
    print(f"\n{C.Y}{C.B}  2. WIN-RATE >= 50%{C.R}")
    ij_path = os.path.join(DATA, "impact_journal.json")
    wr = 0
    closed = 0
    if os.path.exists(ij_path):
        try:
            with open(ij_path) as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else data
            wins = sum(1 for e in entries if e.get("status") == "WIN")
            losses = sum(1 for e in entries if e.get("status") == "LOSS")
            closed = wins + losses
            wr = (wins / closed * 100) if closed > 0 else 0
        except Exception:
            pass
    results.append(check(f"Win-Rate >= 50% (last {closed} trades)",
                         wr >= 50 and closed >= 20,
                         f"Aktuell: {wr:.1f}% bei {closed} abgeschlossenen Trades (mindestens 20 noetig)"))

    # === 3. Strategie-Diversitaet ===
    print(f"\n{C.Y}{C.B}  3. BRAIN HAT GELERNT (Diversitaet){C.R}")
    unique_strats = set()
    if os.path.exists(ij_path):
        try:
            with open(ij_path) as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else data
            unique_strats = set(e.get("strategy", "?") for e in entries if e.get("side") == "BUY")
        except Exception:
            pass
    results.append(check(f"Mindestens 3 verschiedene Strategien getriggert",
                         len(unique_strats) >= 3,
                         f"Aktuell: {len(unique_strats)} Strategie(n): {', '.join(list(unique_strats)[:5]) if unique_strats else 'keine'}"))

    # === 4. Live-Safety installiert ===
    print(f"\n{C.Y}{C.B}  4. LIVE-SAFETY MODULE{C.R}")
    safety_path = os.path.join(ROOT, "features", "safety.py")
    safety_ok = False
    if os.path.exists(safety_path):
        with open(safety_path) as f:
            content = f.read()
        safety_ok = all(x in content for x in ["CashReservation", "RateLimitTracker", "RejectionCounter"])
    results.append(check("features/safety.py mit 3 Klassen vorhanden",
                         safety_ok,
                         "CashReservation + RateLimitTracker + RejectionCounter"))

    # === 5. Impact-Journal Hooks ===
    print(f"\n{C.Y}{C.B}  5. IMPACT-JOURNAL HOOKS{C.R}")
    app_path = os.path.join(ROOT, "app.py")
    hooks_ok = False
    if os.path.exists(app_path):
        with open(app_path, encoding="utf-8") as f:
            content = f.read()
        hooks_ok = "IMPACT-JOURNAL HOOK" in content
    results.append(check("Hooks in app.py aktiv",
                         hooks_ok,
                         "Trades werden automatisch ins Journal geloggt"))

    # === 6. Brain-Tuning ===
    print(f"\n{C.Y}{C.B}  6. BRAIN-TUNING (Bottom-Bonus +3){C.R}")
    brain_path = os.path.join(ROOT, "agents", "strategy_brain.py")
    tuning_ok = False
    if os.path.exists(brain_path):
        with open(brain_path, encoding="utf-8") as f:
            content = f.read()
        tuning_ok = "TUNING: war +5" in content
    results.append(check("Brain-Tuning aktiv (mehr Strategie-Vielfalt)",
                         tuning_ok,
                         "Bottom-Bonus von +5 auf +3 reduziert"))

    # === 7. API-Keys vorhanden (Datei-Existenz, nicht Inhalt!) ===
    print(f"\n{C.Y}{C.B}  7. API-KEYS DATEI (Binance){C.R}")
    api_paths = [
        os.path.join(ROOT, "config", "api_keys.json"),
        os.path.join(ROOT, "config", "secrets.json"),
        os.path.join(ROOT, "api_keys.json"),
    ]
    api_exists = any(os.path.exists(p) for p in api_paths)
    api_found = next((p for p in api_paths if os.path.exists(p)), None)
    results.append(check("API-Keys-Datei vorhanden",
                         api_exists,
                         f"Gefunden: {os.path.basename(api_found)}" if api_found else "Noch nicht eingerichtet"))

    # === 8. Backup-Strategie ===
    print(f"\n{C.Y}{C.B}  8. BACKUP-STRATEGIE{C.R}")
    tickets_ok = os.path.exists(os.path.join(ROOT, "tickets.txt"))
    handbuch_ok = os.path.exists(os.path.join(ROOT, "ENTWICKLERHANDBUCH.md"))
    backup_ok = tickets_ok and handbuch_ok
    results.append(check("tickets.txt + ENTWICKLERHANDBUCH.md vorhanden",
                         backup_ok,
                         f"tickets: {'OK' if tickets_ok else 'FEHLT'} | handbuch: {'OK' if handbuch_ok else 'FEHLT'}"))

    # === SUMMARY ===
    passed = sum(results)
    total = len(results)
    pct = passed / total * 100

    print(f"\n{C.CY}{C.B}{'='*70}")
    print(f"  ERGEBNIS: {passed}/{total} Checks bestanden ({pct:.0f}%)")
    print(f"{'='*70}{C.R}\n")

    if passed == total:
        print(f"  {C.G}{C.B}✓ ALLE CHECKS BESTANDEN - DU BIST LIVE-READY!{C.R}\n")
        print(f"  {C.GR}Naechster Schritt: Config umschalten von paper auf live{C.R}")
        print(f"  {C.GR}WICHTIG: Mit MAX 50-100 USD anfangen!{C.R}")
    elif passed >= total - 2:
        print(f"  {C.Y}{C.B}⚠ FAST READY - 1-2 Punkte fehlen noch{C.R}\n")
        print(f"  {C.GR}Erledige die fehlenden Punkte, dann nochmal pruefen.{C.R}")
    else:
        print(f"  {C.RED}{C.B}✗ NOCH NICHT READY - {total-passed} Punkte fehlen{C.R}\n")
        print(f"  {C.GR}Erst die fehlenden Punkte erledigen, dann erneut pruefen.{C.R}")

    print(f"\n  {C.GR}Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.R}\n")


if __name__ == "__main__":
    main()