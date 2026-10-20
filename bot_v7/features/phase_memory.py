"""
Trading Imperium V6 - Phase Memory (Das Phasen-Gedaechtnis)
============================================================
Lernt aus der Trade-Historie WELCHE Strategie in WELCHER Marktphase
(Regime + Cycle) historisch funktioniert hat.
Liest direkt aus dem Impact-Journal (data_store/impact_journal.json).
"""
import os
import json


class PhaseMemory:
    """Phasen-Gedaechtnis: lernt aus Impact-Journal welche Strategie wo gewinnt."""

    MIN_TRADES_BONUS = 4
    MIN_TRADES_BLOCK = 5
    WR_STRONG = 70.0
    WR_GOOD = 55.0
    WR_WEAK = 35.0

    def __init__(self, journal_path=None):
        if journal_path is None:
            journal_path = os.path.join("data_store", "impact_journal.json")
        self.journal_path = journal_path
        self._cache = None
        self._cache_mtime = 0

    def _read_field(self, entry, *names):
        if isinstance(entry, dict):
            for n in names:
                if n in entry and entry[n] not in (None, ""):
                    return entry[n]
            ctx = entry.get("context", {})
            if isinstance(ctx, dict):
                for n in names:
                    if n in ctx and ctx[n] not in (None, ""):
                        return ctx[n]
        return None

    def _load_stats(self):
        try:
            mtime = os.path.getmtime(self.journal_path)
        except OSError:
            return {}
        if self._cache is not None and mtime == self._cache_mtime:
            return self._cache

        try:
            with open(self.journal_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}

        entries = data.get("entries", data) if isinstance(data, dict) else data
        if not isinstance(entries, list):
            return {}

        stats = {}
        for e in entries:
            if not isinstance(e, dict):
                continue
            status = str(self._read_field(e, "status") or "").upper()
            pnl_raw = self._read_field(e, "pnl_usd", "pnl", "realized_pnl", "pnl_pct")

            if status == "OPEN":
                continue
            is_closed = status in ("WIN", "LOSS", "CLOSED") or pnl_raw is not None
            if not is_closed:
                continue

            if status == "WIN":
                won = True
            elif status == "LOSS":
                won = False
            elif pnl_raw is not None:
                try:
                    won = float(pnl_raw) > 0
                except (ValueError, TypeError):
                    continue
            else:
                continue

            regime = str(self._read_field(e, "regime", "market_regime",
                                          "market_regime_at_entry") or "UNKNOWN").upper()
            cycle = str(self._read_field(e, "cycle", "cycle_phase",
                                         "cycle_at_entry") or "UNKNOWN").upper()
            strat = self._read_field(e, "strategy", "strategy_id") or "?"

            try:
                pnl_val = float(pnl_raw) if pnl_raw is not None else (1.0 if won else -1.0)
            except (ValueError, TypeError):
                pnl_val = 1.0 if won else -1.0

            key = (regime, cycle, strat)
            if key not in stats:
                stats[key] = {"trades": 0, "wins": 0, "pnl": 0.0}
            stats[key]["trades"] += 1
            if won:
                stats[key]["wins"] += 1
            stats[key]["pnl"] += pnl_val

        for v in stats.values():
            v["win_rate"] = (v["wins"] / v["trades"] * 100) if v["trades"] > 0 else 0.0

        self._cache = stats
        self._cache_mtime = mtime
        return stats

    def get_score_adjustment(self, regime, cycle, strategy):
        """Returns (score_adjustment, info_dict)."""
        stats = self._load_stats()
        key = (str(regime).upper(), str(cycle).upper(), strategy)
        s = stats.get(key)
        if not s or s["trades"] < self.MIN_TRADES_BONUS:
            return 0.0, {}

        wr = s["win_rate"]
        info = {"win_rate": wr, "trades": s["trades"], "pnl": s["pnl"]}

        if s["trades"] >= self.MIN_TRADES_BLOCK and wr < self.WR_WEAK and s["pnl"] < 0:
            return -10.0, info
        if s["trades"] >= self.MIN_TRADES_BLOCK and wr >= self.WR_STRONG:
            return 2.0, info
        if s["trades"] >= self.MIN_TRADES_BONUS and wr >= self.WR_GOOD:
            return 1.0, info
        return 0.0, info

    def get_status(self):
        stats = self._load_stats()
        return {
            "phase_combos": len(stats),
            "total_closed": sum(v["trades"] for v in stats.values()),
        }

    def get_phase_overview(self, regime, cycle):
        stats = self._load_stats()
        rk, ck = str(regime).upper(), str(cycle).upper()
        out = []
        for (r, c, strat), v in stats.items():
            if r == rk and c == ck:
                out.append({"strategy": strat, "trades": v["trades"],
                            "win_rate": v["win_rate"], "pnl": v["pnl"]})
        return sorted(out, key=lambda x: x["win_rate"], reverse=True)
