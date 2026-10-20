"""
V4 DATA IMPORTER
================
Importiert V4 Trade-History und Equity-Daten ins V6 Format.

Wandelt:
  trades_log_v4.json   -> V6 TradeJournal-Eintraege
  equity_history.json  -> V6 EquityTracker-Daten
  imperium_state.json  -> BTC Accumulator State + Settings
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("v4_importer")


def load_v4_trades(path: str) -> List[Dict]:
    """Liest trades_log_v4.json und normalisiert ins V6-Format."""
    if not os.path.exists(path):
        logger.warning(f"V4 trades nicht gefunden: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    normalized = []
    for t in raw:
        # V4 Felder: type, coin, price, qty, pnl, pnl_pct, reason, strategy, time
        try:
            normalized.append({
                "ts": t.get("time"),
                "side": (t.get("type") or "").upper(),     # BUY / SELL
                "symbol": t.get("coin"),
                "price": float(t.get("price", 0)),
                "qty": float(t.get("qty", 0)),
                "pnl": float(t.get("pnl", 0) or 0),
                "pnl_pct": float(t.get("pnl_pct", 0) or 0),
                "strategy": t.get("strategy", "UNKNOWN"),
                "reason": t.get("reason", ""),
                "source": "v4_import",
            })
        except (TypeError, ValueError) as e:
            logger.warning(f"Skip ungueltiger Trade: {e}")
            continue
    return normalized


def load_v4_equity(path: str) -> List[Tuple[str, float]]:
    """Liest equity_history.json. Gibt Liste [(timestamp, value), ...] zurueck."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    result = []
    for e in raw:
        try:
            result.append((e.get("t"), float(e.get("v", 0))))
        except (TypeError, ValueError):
            continue
    return result


def load_v4_state(path: str) -> Dict:
    """Liest imperium_state.json (BTC Accumulator + Settings)."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_v6_trade_journal(trades: List[Dict], output_path: str):
    """
    Schreibt V6 TradeJournal-Format.
    V6 erwartet eine Liste von Dicts in data_store/trades_v5.json (oder aehnlich).

    Falls dein V6 ein anderes Format nutzt, hier anpassen.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"{len(trades)} V4-Trades nach {output_path} geschrieben")


def import_all(v4_data_dir: str, v6_data_dir: str) -> Dict[str, int]:
    """
    Importiert ALLES aus V4 nach V6.
    Returns: Dict mit Anzahl importierter Items pro Kategorie.
    """
    counts = {"trades": 0, "equity_points": 0, "btc_buys": 0, "settings": 0}

    # 1. Trades
    trades = load_v4_trades(os.path.join(v4_data_dir, "trades_log_v4.json"))
    if trades:
        write_v6_trade_journal(trades, os.path.join(v6_data_dir, "v4_imported_trades.json"))
        counts["trades"] = len(trades)

    # 2. Equity-Verlauf
    equity = load_v4_equity(os.path.join(v4_data_dir, "equity_history.json"))
    if equity:
        out = os.path.join(v6_data_dir, "v4_imported_equity.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump([{"t": t, "v": v} for t, v in equity], f, default=str)
        counts["equity_points"] = len(equity)

    # 3. State (BTC Accumulator etc.) - Sicherheits-Bereinigung!
    state = load_v4_state(os.path.join(v4_data_dir, "imperium_state.json"))
    if state:
        # API-Keys herausstrippen!
        clean_state = dict(state)
        if "settings" in clean_state:
            sett = dict(clean_state["settings"])
            for sensitive in ("binance_key", "binance_secret", "telegram_token",
                              "telegram_chat", "openai_key"):
                sett.pop(sensitive, None)
            clean_state["settings"] = sett
            counts["settings"] = len(sett)

        # BTC Accumulator
        btc_acc = state.get("btc_accumulator", {})
        if "buy_history" in btc_acc:
            counts["btc_buys"] = len(btc_acc["buy_history"])

        out = os.path.join(v6_data_dir, "v4_imported_state.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(clean_state, f, indent=2, ensure_ascii=False, default=str)

    return counts


def get_import_summary(v6_data_dir: str) -> Dict:
    """Liest die importierten Daten und gibt eine Zusammenfassung zurueck."""
    summary = {"available": False}
    trades_path = os.path.join(v6_data_dir, "v4_imported_trades.json")
    if not os.path.exists(trades_path):
        return summary
    with open(trades_path, "r", encoding="utf-8") as f:
        trades = json.load(f)
    sells = [t for t in trades if t.get("side") == "SELL"]
    total_pnl = sum(t.get("pnl", 0) for t in sells)
    by_strategy: Dict[str, Dict] = {}
    for t in sells:
        s = t.get("strategy", "UNKNOWN")
        if s not in by_strategy:
            by_strategy[s] = {"trades": 0, "pnl": 0.0, "wins": 0}
        by_strategy[s]["trades"] += 1
        by_strategy[s]["pnl"] += t.get("pnl", 0)
        if t.get("pnl", 0) > 0:
            by_strategy[s]["wins"] += 1
    summary.update({
        "available": True,
        "total_trades": len(trades),
        "completed_trades": len(sells),
        "total_pnl": round(total_pnl, 2),
        "by_strategy": by_strategy,
    })
    return summary
