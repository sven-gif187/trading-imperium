"""
Impact Journal - Trade-Begruendungs-System.
Speichert pro Trade: Strategie, Score, Reasons, Markt-Kontext, P&L.
"""
import os
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a, **kw): pass
        def warn(self, *a, **kw): pass
    log = _Log()


class ImpactJournal:
    def __init__(self, journal_path: Optional[str] = None):
        if journal_path is None:
            journal_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data_store",
                "impact_journal.json"
            )
        self.journal_path = journal_path
        self._lock = threading.RLock()
        self._entries: List[Dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._entries = data
                elif isinstance(data, dict) and "entries" in data:
                    self._entries = data["entries"]
            except Exception as e:
                log.warn("JOURNAL", f"Lade-Fehler: {str(e)[:80]}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
            with open(self.journal_path, "w", encoding="utf-8") as f:
                json.dump({
                    "saved_at": datetime.now().isoformat(),
                    "total_entries": len(self._entries),
                    "entries": self._entries,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warn("JOURNAL", f"Speicher-Fehler: {str(e)[:80]}")

    def log_buy(self, symbol: str, strategy: str, score: int,
                reasons: List[str], context: Dict,
                amount_usd: float, price: float):
        with self._lock:
            entry = {
                "id": f"trade_{len(self._entries)+1}_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol, "side": "BUY",
                "strategy": strategy, "score": score, "reasons": reasons,
                "context": {
                    "regime": context.get("regime", "?"),
                    "cycle": context.get("cycle", "?"),
                    "fear_greed": context.get("fear_greed", 0),
                    "nupl": context.get("nupl", 0),
                    "rsi": context.get("rsi", 0),
                    "adx": context.get("adx", 0),
                    "mtf_confluence": context.get("mtf_confluence", 0),
                },
                "entry_price": price, "amount_usd": amount_usd,
                "exit_price": None, "exit_time": None,
                "pnl_usd": None, "pnl_pct": None,
                "hold_minutes": None, "sell_reason": None,
                "status": "OPEN",
            }
            self._entries.append(entry)
            self._save()

    def log_sell(self, symbol: str, exit_price: float, pnl_usd: float, reason: str = ""):
        with self._lock:
            target = None
            for e in reversed(self._entries):
                if e.get("symbol") == symbol and e.get("status") == "OPEN" and e.get("side") == "BUY":
                    target = e
                    break
            if not target:
                self._entries.append({
                    "id": f"trade_{len(self._entries)+1}_{int(datetime.now().timestamp())}",
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol, "side": "SELL",
                    "exit_price": exit_price, "pnl_usd": pnl_usd,
                    "sell_reason": reason, "status": "ORPHAN_SELL",
                })
                self._save()
                return
            entry_price = target.get("entry_price", 0)
            entry_time = target.get("timestamp", "")
            try:
                buy_ts = datetime.fromisoformat(entry_time)
                hold_min = int((datetime.now() - buy_ts).total_seconds() / 60)
            except Exception:
                hold_min = 0
            pnl_pct = ((exit_price / entry_price) - 1) * 100 if entry_price > 0 else 0
            target["exit_price"] = exit_price
            target["exit_time"] = datetime.now().isoformat()
            target["pnl_usd"] = round(pnl_usd, 4)
            target["pnl_pct"] = round(pnl_pct, 3)
            target["hold_minutes"] = hold_min
            target["sell_reason"] = reason
            target["status"] = "WIN" if pnl_usd > 0 else "LOSS"
            self._save()

    def get_recent(self, n: int = 20) -> List[Dict]:
        with self._lock:
            return list(self._entries[-n:])

    def get_open_positions(self) -> List[Dict]:
        with self._lock:
            return [e for e in self._entries if e.get("status") == "OPEN"]

    def get_strategy_stats(self) -> Dict:
        with self._lock:
            stats = defaultdict(lambda: {"trades":0,"wins":0,"losses":0,"total_pnl":0.0,"scores":[]})
            for e in self._entries:
                if e.get("side") != "BUY":
                    continue
                strat = e.get("strategy", "?")
                stats[strat]["trades"] += 1
                stats[strat]["scores"].append(e.get("score", 0))
                if e.get("status") == "WIN":
                    stats[strat]["wins"] += 1
                    stats[strat]["total_pnl"] += e.get("pnl_usd", 0)
                elif e.get("status") == "LOSS":
                    stats[strat]["losses"] += 1
                    stats[strat]["total_pnl"] += e.get("pnl_usd", 0)
            result = {}
            for strat, s in stats.items():
                closed = s["wins"] + s["losses"]
                wr = (s["wins"] / closed * 100) if closed > 0 else None
                result[strat] = {
                    "trades": s["trades"], "wins": s["wins"], "losses": s["losses"],
                    "open": s["trades"] - closed,
                    "win_rate": round(wr, 1) if wr is not None else None,
                    "total_pnl": round(s["total_pnl"], 2),
                    "avg_score": round(sum(s["scores"]) / len(s["scores"]), 2) if s["scores"] else 0,
                }
            return result

    def get_best_setups(self, n: int = 5) -> List[Dict]:
        with self._lock:
            closed = [e for e in self._entries if e.get("status") in ("WIN", "LOSS")]
            return sorted(closed, key=lambda x: x.get("pnl_usd", 0), reverse=True)[:n]

    def get_worst_setups(self, n: int = 5) -> List[Dict]:
        with self._lock:
            closed = [e for e in self._entries if e.get("status") in ("WIN", "LOSS")]
            return sorted(closed, key=lambda x: x.get("pnl_usd", 0))[:n]

    def get_summary(self) -> Dict:
        with self._lock:
            total = len(self._entries)
            opens = sum(1 for e in self._entries if e.get("status") == "OPEN")
            wins = sum(1 for e in self._entries if e.get("status") == "WIN")
            losses = sum(1 for e in self._entries if e.get("status") == "LOSS")
            total_pnl = sum(e.get("pnl_usd", 0) or 0 for e in self._entries)
            closed = wins + losses
            return {
                "total_trades": total, "open": opens,
                "wins": wins, "losses": losses,
                "win_rate": round(wins / closed * 100, 1) if closed > 0 else 0,
                "total_pnl_usd": round(total_pnl, 2),
            }
