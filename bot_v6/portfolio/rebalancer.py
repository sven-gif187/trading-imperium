"""
Trading Imperium - Portfolio Rebalancer

ZWEI KLASSEN:
1. Rebalancer (ALT - bleibt, wird von portfolio/agent.py importiert)
2. PortfolioRebalancer (NEU - Step 2, 55/15/10/10/10 Auto-Allokation)
"""
import time
from typing import Dict, List, Tuple, Optional
from core.logger import log


class Rebalancer:
    """Gleicht Portfolio an Ziel-Allokation an. (ALT - bleibt fuer Kompatibilitaet)"""

    def __init__(self, threshold_pct=5.0, min_trade_usd=10.0):
        self.threshold_pct = threshold_pct
        self.min_trade_usd = min_trade_usd
        self.last_rebalance = 0
        self.rebalance_count = 0

    def calculate_trades(self, positions, total_equity, target_alloc, prices):
        if total_equity <= 0:
            return []
        trades = []
        current = {}
        for asset, pos in positions.items():
            val = pos.get("value", 0)
            pct = (val / total_equity * 100) if total_equity > 0 else 0
            current[asset] = {"value": val, "pct": round(pct, 1)}

        invested = sum(p.get("value", 0) for p in positions.values())
        cash_pct = ((total_equity - invested) / total_equity * 100) if total_equity > 0 else 100

        for asset, target_pct in target_alloc.items():
            if asset == "cash" or asset == "alts":
                continue
            curr_pct = current.get(asset, {}).get("pct", 0)
            diff = target_pct - curr_pct
            if abs(diff) < self.threshold_pct:
                continue
            amount_usd = abs(diff / 100 * total_equity)
            if amount_usd < self.min_trade_usd:
                continue
            if diff > 0:
                trades.append({
                    "action": "BUY", "asset": asset,
                    "symbol": asset + "/USDC",
                    "amount_usd": round(amount_usd, 2),
                    "current_pct": curr_pct, "target_pct": target_pct,
                    "reason": "Rebalance " + str(round(curr_pct, 1)) + "% -> " + str(target_pct) + "%",
                })
            else:
                price = prices.get(asset + "/USDC", 0) or prices.get(asset + "/USDT", 0)
                qty = amount_usd / price if price > 0 else 0
                trades.append({
                    "action": "SELL", "asset": asset,
                    "symbol": asset + "/USDC",
                    "amount_usd": round(amount_usd, 2),
                    "qty": round(qty, 6),
                    "current_pct": curr_pct, "target_pct": target_pct,
                    "reason": "Rebalance " + str(round(curr_pct, 1)) + "% -> " + str(target_pct) + "%",
                })

        if trades:
            self.last_rebalance = time.time()
            self.rebalance_count += 1
            log.info("REBALANCE", str(len(trades)) + " Trades vorgeschlagen")
            for t in trades:
                log.info("REBALANCE",
                         "  " + t["action"] + " " + t["asset"] + ": "
                         + str(t["amount_usd"]) + "$ (" + t["reason"] + ")")
        return trades

    def should_rebalance(self, interval_hours=24):
        return (time.time() - self.last_rebalance) > (interval_hours * 3600)

    def get_deviation_report(self, positions, total_equity, target_alloc):
        report = {}
        for asset, target_pct in target_alloc.items():
            if asset in ("cash", "alts"):
                continue
            val = positions.get(asset, {}).get("value", 0)
            curr_pct = (val / total_equity * 100) if total_equity > 0 else 0
            diff = curr_pct - target_pct
            report[asset] = {
                "current_pct": round(curr_pct, 1),
                "target_pct": target_pct,
                "diff": round(diff, 1),
                "status": "OK" if abs(diff) < self.threshold_pct else ("OVER" if diff > 0 else "UNDER"),
            }
        return report

    def get_status(self):
        return {
            "last_rebalance": self.last_rebalance,
            "count": self.rebalance_count,
            "threshold": self.threshold_pct,
            "min_trade": self.min_trade_usd,
        }


# ============================================================
# STEP 2 - NEUE KLASSE: PortfolioRebalancer
# ============================================================
class PortfolioRebalancer:
    """STEP 2: Auto-Rebalancer mit fester 55/15/10/10/10 Ziel-Allokation."""

    DEFAULT_ALLOCATION = {
        "BTC/USDC":  55.0,
        "ETH/USDC":  15.0,
        "SOL/USDC":  10.0,
        "XRP/USDC":  10.0,
        "ADA/USDC":   3.3,
        "AVAX/USDC":  3.3,
        "LINK/USDC":  3.4,
    }

    def __init__(self, config=None, enabled=False, dry_run=True, threshold_pct=5.0):
        self.config = config
        self.enabled = enabled
        self.dry_run = dry_run
        self.threshold_pct = threshold_pct
        self.allocation = dict(self.DEFAULT_ALLOCATION)
        self.last_rebalance_time = 0
        self.min_interval_sec = 6 * 3600
        self.last_dry_run_log = 0

    def set_allocation(self, allocation):
        total = sum(allocation.values())
        if abs(total - 100.0) > 1.0:
            log.warn("REBAL", "Allokation summiert nicht 100% (" + str(round(total, 1)) + "%) - ignoriert")
            return
        self.allocation = dict(allocation)
        log.info("REBAL", "Allokation gesetzt")

    def enable(self, dry_run=True):
        self.enabled = True
        self.dry_run = dry_run
        mode = "TROCKENLAUF" if dry_run else "LIVE"
        log.info("REBAL", "Rebalancer AKTIVIERT (" + mode + ")")

    def disable(self):
        self.enabled = False
        log.info("REBAL", "Rebalancer deaktiviert")

    def _compute_current_allocation(self, positions_with_values, cash_usd):
        total = sum(positions_with_values.values()) + cash_usd
        if total <= 0:
            return {}
        result = {}
        for sym, val in positions_with_values.items():
            result[sym] = (val / total) * 100
        result["CASH"] = (cash_usd / total) * 100
        return result

    def check_needs_rebalance(self, positions_with_values, cash_usd):
        current = self._compute_current_allocation(positions_with_values, cash_usd)
        deviations = {}
        max_dev = 0
        max_dev_coin = ""
        for sym, target_pct in self.allocation.items():
            actual_pct = current.get(sym, 0)
            dev = abs(actual_pct - target_pct)
            deviations[sym] = {"target": target_pct, "actual": actual_pct, "deviation": dev}
            if dev > max_dev:
                max_dev = dev
                max_dev_coin = sym
        if max_dev > self.threshold_pct:
            return True, max_dev_coin + ": " + str(round(max_dev, 1)) + "% Abweichung", {
                "current": current, "deviations": deviations,
            }
        return False, "Alle Coins unter Threshold", {
            "current": current, "deviations": deviations,
        }

    def compute_orders(self, positions_with_values, cash_usd, prices):
        total = sum(positions_with_values.values()) + cash_usd
        if total <= 0:
            return []
        orders = []
        for sym, target_pct in self.allocation.items():
            target_usd = total * (target_pct / 100)
            current_usd = positions_with_values.get(sym, 0)
            diff_usd = target_usd - current_usd
            if abs(diff_usd) < 10.0:
                continue
            price = prices.get(sym, 0)
            if price <= 0:
                continue
            if diff_usd > 0:
                qty = diff_usd / price
                orders.append({
                    "symbol": sym, "side": "BUY",
                    "amount_usd": diff_usd, "qty": qty, "price": price,
                })
            else:
                qty = abs(diff_usd) / price
                orders.append({
                    "symbol": sym, "side": "SELL",
                    "amount_usd": abs(diff_usd), "qty": qty, "price": price,
                })
        orders.sort(key=lambda o: 0 if o["side"] == "SELL" else 1)
        return orders

    def can_rebalance_now(self, cycle_phase="UNKNOWN", is_bottom=False):
        if not self.enabled:
            return False, "Rebalancer nicht aktiviert"
        elapsed = time.time() - self.last_rebalance_time
        if elapsed < self.min_interval_sec:
            return False, "Cooldown aktiv"
        phase_str = str(cycle_phase).upper()
        if phase_str not in ("ACCUMULATION",) and not is_bottom:
            return False, "Phase " + phase_str
        return True, "OK"

    def execute(self, positions_with_values, cash_usd, prices,
                cycle_phase="UNKNOWN", is_bottom=False):
        can_rebal, reason = self.can_rebalance_now(cycle_phase, is_bottom)
        if not can_rebal:
            return None
        needs, _why, _details = self.check_needs_rebalance(positions_with_values, cash_usd)
        if not needs:
            return None
        orders = self.compute_orders(positions_with_values, cash_usd, prices)
        if not orders:
            return None
        if self.dry_run:
            now = time.time()
            if now - self.last_dry_run_log < 600:
                return None
            self.last_dry_run_log = now
            log.info("REBAL-DRY", "=== REBALANCE-TROCKENLAUF ===")
            log.info("REBAL-DRY", "Grund: " + _why)
            for o in orders:
                log.info("REBAL-DRY",
                         "WUERDE " + o["side"] + " " + o["symbol"]
                         + ": " + str(round(o["amount_usd"], 2)) + "$")
            log.info("REBAL-DRY", "=== Ende Trockenlauf - keine echten Trades ===")
            return None
        log.info("REBAL", "REBALANCE wird ausgefuehrt: " + _why)
        self.last_rebalance_time = time.time()
        return orders

    def get_status(self):
        return {
            "enabled": self.enabled,
            "dry_run": self.dry_run,
            "threshold_pct": self.threshold_pct,
            "allocation": dict(self.allocation),
            "last_rebalance_time": self.last_rebalance_time,
            "min_interval_sec": self.min_interval_sec,
        }
