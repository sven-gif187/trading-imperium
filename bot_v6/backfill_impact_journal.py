# -*- coding: utf-8 -*-
"""
backfill_impact_journal.py - Geister-OPENs im Impact-Journal schliessen
========================================================================
Problem: Vor dem Journal-Fix (install_journal_fix.py) kamen Monitor-Exits
(STOP-LOSS, TREND-EXIT, TAKE-PROFIT, TRAILING-STOP-STUFE, Daily-Loss) nie
im Impact-Journal an. Folge: hunderte Eintraege stehen faelschlich auf OPEN
und der Lern-Datensatz kennt fast keine Verluste (Survivorship-Bias).

Loesung: Alle gefuellten SELLs aus order_history.json chronologisch
durchgehen. Jeder Sell verkauft die KOMPLETTE Position eines Coins
(so arbeitet der Monitor). Also werden pro Sell ALLE noch offenen
BUY-Eintraege dieses Coins, die VOR dem Sell liegen, geschlossen -
jeder mit seinem eigenen pnl_pct gegen seinen eigenen Entry-Preis.

Sicherheit:
  - Backup impact_journal.json.bak_backfill (nur beim ersten Lauf)
  - idempotent: backfilled-Eintraege werden nicht doppelt angefasst
  - bereits geschlossene Eintraege (WIN/LOSS) bleiben UNBERUEHRT
  - Eintraege ohne passenden Sell bleiben OPEN (echte offene Positionen)
  - Hinweis: pnl_usd ist ohne Gebuehren geschaetzt (amount_usd * pnl_pct)

ABLAUF: Bot KOMPLETT schliessen -> Skript ausfuehren -> Bot starten.
(Der Bot haelt das Journal im Speicher und wuerde es sonst ueberschreiben.)
"""
import os
import sys
import json
import shutil
from datetime import datetime, timezone


def find_file(base, name, prefer_dir="data_store"):
    pref = os.path.join(base, prefer_dir, name)
    if os.path.exists(pref):
        return pref
    direct = os.path.join(base, name)
    if os.path.exists(direct):
        return direct
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_archive"))]
        if name in files:
            return os.path.join(root, name)
    return None


def parse_iso(value):
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is not None:
            return dt.timestamp()
        return dt.replace(tzinfo=timezone.utc).astimezone().timestamp()
    except Exception:
        return None


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    print("Backfill - Impact-Journal aus order_history rekonstruieren")
    print(f"  Basis: {base}")
    print("-" * 60)

    ij_path = find_file(base, "impact_journal.json")
    oh_path = find_file(base, "order_history.json")
    if not ij_path or not oh_path:
        print("  FEHLER: impact_journal.json oder order_history.json fehlt.")
        sys.exit(1)
    print(f"  Impact-Journal: {ij_path}")
    print(f"  Order-History:  {oh_path}")

    with open(ij_path, "r", encoding="utf-8") as f:
        ij = json.load(f)
    entries = ij.get("entries", ij if isinstance(ij, list) else [])
    with open(oh_path, "r", encoding="utf-8") as f:
        oh = json.load(f)

    sells = [o for o in oh
             if o.get("side") == "SELL" and o.get("status") == "filled"
             and (o.get("fill_price") or 0) > 0]
    sells.sort(key=lambda o: o.get("created_at", 0))
    print(f"  {len(entries)} Journal-Eintraege | {len(sells)} gefuellte SELLs")

    # BUY-Eintraege mit Timestamp indizieren
    open_before = closed_before = 0
    for e in entries:
        if e.get("side") != "BUY":
            continue
        e["_ts"] = parse_iso(e.get("timestamp"))
        if e.get("status") == "OPEN":
            open_before += 1
        elif e.get("status") in ("WIN", "LOSS"):
            closed_before += 1
    print(f"  Vorher: {open_before} OPEN | {closed_before} geschlossen")

    backfilled = 0
    orphan_sells = 0
    per_reason = {}

    for sell in sells:
        sym = sell.get("symbol", "")
        s_ts = float(sell.get("created_at", 0))
        s_price = float(sell.get("fill_price", 0))
        reason = (sell.get("reason") or "?").strip()

        # Alle noch offenen BUYs dieses Coins VOR dem Sell schliessen (FIFO)
        candidates = [e for e in entries
                      if e.get("side") == "BUY" and e.get("status") == "OPEN"
                      and e.get("symbol") == sym
                      and e.get("_ts") is not None and e["_ts"] < s_ts]
        if not candidates:
            orphan_sells += 1
            continue
        candidates.sort(key=lambda e: e["_ts"])

        for e in candidates:
            entry_p = float(e.get("entry_price") or 0)
            if entry_p <= 0:
                continue
            pnl_pct = (s_price / entry_p - 1) * 100
            amount = float(e.get("amount_usd") or 0)
            pnl_usd = amount * pnl_pct / 100.0
            hold_min = (s_ts - e["_ts"]) / 60.0

            e["exit_price"] = round(s_price, 8)
            e["exit_time"] = datetime.fromtimestamp(s_ts).isoformat()
            e["pnl_usd"] = round(pnl_usd, 2)
            e["pnl_pct"] = round(pnl_pct, 3)
            e["hold_minutes"] = int(hold_min)
            e["sell_reason"] = reason + " [BACKFILL]"
            e["status"] = "WIN" if pnl_pct > 0 else "LOSS"
            e["backfilled"] = True
            backfilled += 1
            key = reason.split("(")[0].strip()[:24]
            per_reason[key] = per_reason.get(key, 0) + 1

    if backfilled == 0:
        print("  Nichts zu tun - keine offenen Eintraege passten zu Sells.")
        return

    # Aufraeumen + speichern
    for e in entries:
        e.pop("_ts", None)

    backup = ij_path + ".bak_backfill"
    if not os.path.exists(backup):
        shutil.copy2(ij_path, backup)

    if isinstance(ij, dict):
        ij["entries"] = entries
        ij["total_entries"] = len(entries)
        ij["saved_at"] = datetime.now().isoformat()
        payload = ij
    else:
        payload = entries

    tmp = ij_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    # Validierung vor dem Ersetzen
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, ij_path)

    open_after = sum(1 for e in entries
                     if e.get("side") == "BUY" and e.get("status") == "OPEN")
    wins = sum(1 for e in entries if e.get("status") == "WIN")
    losses = sum(1 for e in entries if e.get("status") == "LOSS")

    print("-" * 60)
    print(f"  {backfilled} Eintraege rueckwirkend geschlossen:")
    for r, n in sorted(per_reason.items(), key=lambda x: -x[1]):
        print(f"    {n:4d}x {r}")
    if orphan_sells:
        print(f"  {orphan_sells} Sells ohne offenen Journal-Eintrag (uebersprungen)")
    print(f"  Nachher: {open_after} OPEN | {wins} WIN / {losses} LOSS")
    print(f"  Backup: {os.path.basename(backup)}")
    print("  HINWEIS: pnl_usd im Backfill ohne Gebuehren geschaetzt.")
    print("Fertig. Jetzt situation_replay.py neu laufen lassen!")


if __name__ == "__main__":
    main()
