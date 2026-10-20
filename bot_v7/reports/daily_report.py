"""
Trading Imperium V5 – Daily Report
Erstellt taeglich eine Zusammenfassung aller Aktivitaeten.
"""
import time
from datetime import datetime, timezone
from typing import Dict, List
from core.logger import log


class DailyReport:
    """Generiert taegliche Trading-Berichte."""

    def __init__(self):
        self.last_report_time = 0
        self.report_count = 0

    def generate(self, journal_stats, balance, btc_acc, risk_status, cycle_status) -> Dict:
        """Erstellt einen kompletten Tagesbericht."""
        usdc = balance.get("total", {}).get("USDC", 0) + balance.get("total", {}).get("USDT", 0)
        btc = balance.get("total", {}).get("BTC", 0)

        report = {
            "date": datetime.now().strftime("%d.%m.%Y"),
            "time": datetime.now().strftime("%H:%M"),
            "balance_usdc": round(usdc, 2),
            "balance_btc": round(btc, 8),
            "total_trades": journal_stats.get("total_trades", 0),
            "wins": journal_stats.get("wins", 0),
            "losses": journal_stats.get("losses", 0),
            "win_rate": journal_stats.get("win_rate", 0),
            "total_pnl": journal_stats.get("total_pnl", 0),
            "daily_loss": risk_status.get("kill_switch", {}).get("daily_loss", 0),
            "cycle_phase": cycle_status.get("phase", "?"),
            "btc_accumulated": btc_acc.get("total_btc", 0),
            "btc_invested": btc_acc.get("invested", 0),
        }
        self.last_report_time = time.time()
        self.report_count += 1
        return report

    def format_telegram(self, report) -> str:
        pnl = report["total_pnl"]
        emoji = "📈" if pnl >= 0 else "📉"
        return (f"{emoji} <b>TAGESBERICHT {report['date']}</b>\n"
                f"{'─' * 25}\n"
                f"💰 Balance: {report['balance_usdc']:.2f} USDC\n"
                f"₿ BTC: {report['balance_btc']:.8f}\n"
                f"📊 Trades: {report['total_trades']} ({report['wins']}W / {report['losses']}L)\n"
                f"🎯 Win-Rate: {report['win_rate']:.0f}%\n"
                f"💵 P&L: {pnl:+.2f}$\n"
                f"🔄 Zyklus: {report['cycle_phase']}\n"
                f"₿ Akkumuliert: {report['btc_accumulated']:.8f} BTC\n"
                f"{'─' * 25}\n"
                f"⏰ {report['time']} Uhr")

    def format_text(self, report) -> str:
        return (f"{'=' * 50}\n"
                f"  TAGESBERICHT {report['date']} {report['time']}\n"
                f"{'=' * 50}\n"
                f"  Balance:    {report['balance_usdc']:>10,.2f} USDC\n"
                f"  BTC:        {report['balance_btc']:>14.8f}\n"
                f"  Trades:     {report['total_trades']:>10}\n"
                f"  Win-Rate:   {report['win_rate']:>9.0f}%\n"
                f"  P&L:        {report['total_pnl']:>+10.2f}$\n"
                f"  Zyklus:     {report['cycle_phase']}\n"
                f"{'=' * 50}")

    def get_status(self):
        return {"last_report": self.last_report_time, "count": self.report_count}
