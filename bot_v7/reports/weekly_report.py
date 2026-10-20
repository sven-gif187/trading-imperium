"""
Trading Imperium V5 – Weekly Report
Wochenbericht mit Performance-Vergleich und Strategie-Ranking.
"""
import time
from datetime import datetime
from typing import Dict, List
from core.logger import log


class WeeklyReport:
    """Generiert woechentliche Trading-Berichte."""

    def __init__(self):
        self.weekly_trades = []
        self.weekly_pnl = []
        self.last_report_time = 0
        self.report_count = 0

    def add_trade(self, trade):
        self.weekly_trades.append(trade)

    def add_pnl(self, pnl):
        self.weekly_pnl.append(pnl)

    def generate(self, balance, btc_acc, strategy_brain) -> Dict:
        sells = [t for t in self.weekly_trades if t.get("type") in ("SELL", "sell")]
        total_pnl = sum(t.get("pnl", 0) for t in sells if isinstance(t.get("pnl"), (int, float)))
        wins = sum(1 for t in sells if t.get("pnl", 0) > 0)
        wr = (wins / len(sells) * 100) if sells else 0
        usdc = balance.get("total", {}).get("USDC", 0) + balance.get("total", {}).get("USDT", 0)

        # Strategie-Ranking
        ranking = strategy_brain.get_ranking() if strategy_brain else []

        report = {
            "week": datetime.now().strftime("KW %V"),
            "date_range": f"{datetime.now().strftime('%d.%m.%Y')}",
            "total_trades": len(self.weekly_trades),
            "sells": len(sells),
            "wins": wins, "losses": len(sells) - wins,
            "win_rate": round(wr, 1),
            "total_pnl": round(total_pnl, 2),
            "balance_usdc": round(usdc, 2),
            "btc_total": btc_acc.get("total_btc", 0),
            "best_strategies": ranking[:3],
        }
        self.last_report_time = time.time()
        self.report_count += 1
        return report

    def format_telegram(self, report) -> str:
        pnl = report["total_pnl"]
        emoji = "📈" if pnl >= 0 else "📉"
        msg = (f"{emoji} <b>WOCHENBERICHT {report['week']}</b>\n"
               f"{'═' * 25}\n"
               f"💰 Balance: {report['balance_usdc']:.2f} USDC\n"
               f"₿ BTC: {report['btc_total']:.8f}\n"
               f"📊 Trades: {report['total_trades']} ({report['wins']}W/{report['losses']}L)\n"
               f"🎯 Win-Rate: {report['win_rate']:.0f}%\n"
               f"💵 Wochen-P&L: {pnl:+.2f}$\n")
        if report.get("best_strategies"):
            msg += f"{'─' * 25}\n🏆 Top Strategien:\n"
            for i, s in enumerate(report["best_strategies"][:3]):
                medal = ["🥇", "🥈", "🥉"][i]
                msg += f"  {medal} {s.get('name', '?')}: {s.get('total_pnl', 0):+.2f}$\n"
        msg += f"{'═' * 25}\n⏰ {report['date_range']}"
        return msg

    def reset(self):
        self.weekly_trades = []
        self.weekly_pnl = []

    def get_status(self):
        return {"trades_this_week": len(self.weekly_trades), "count": self.report_count}
