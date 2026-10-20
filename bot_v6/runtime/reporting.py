# -*- coding: utf-8 -*-
"""
runtime/reporting.py - SPLIT SCHRITT 1 (Bauplan: SPLIT_BAUPLAN.md)
===================================================================
Reporting-Cluster, wortwoertlich umgezogen aus app.py (Z. 2105-2190,
Stand 04.07.): Analyse-Export, Tages-/Wochenbericht, Heartbeat.
Aenderung gemaess Umzugsregel 4: self.X -> self.app.X. Sonst NICHTS.

Delegaten-Muster: haelt KEINEN eigenen Zustand (Umzugsregel/Falle 4),
alles haengt an self.app.
"""
from datetime import datetime

from core.logger import log


class Reporting:
    def __init__(self, app):
        self.app = app

    def analyse_export(self) -> str:
        """Erstellt einen Analyse-Export wie V4."""
        stats = self.app.journal.get_stats()
        balance = self.app.execution.get_balance()
        usdc = balance["total"].get("USDC", 0) + balance["total"].get("USDT", 0)
        btc_acc = self.app.btc_accumulator.get_status()
        brain = self.app.strategy_brain.get_status()
        cycle = self.app.cycle_theory.get_status()
        risk = self.app.risk_engine.get_status()

        lines = [
            "=" * 80,
            "⚡ TRADING IMPERIUM V6 – ANALYSE EXPORT",
            f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            "=" * 80,
            "",
            "📊 SESSION-ÜBERSICHT",
            "-" * 40,
            f"Session P&L:        {stats.get('total_pnl', 0):+.2f} USDC",
            f"USDC Balance:       {usdc:,.2f}",
            f"BTC akkumuliert:    {btc_acc.get('total_btc', 0):.8f}",
            f"Trades gesamt:      {stats.get('total_trades', 0)}",
            f"Win-Rate:           {stats.get('win_rate', 0):.1f}%",
            "",
            "🧠 AKTIVE KI-STRATEGIE",
            "-" * 40,
            f"Strategie:          {brain.get('name', '?')}",
            f"Zyklus:             {cycle.get('phase', '?')} | {cycle.get('mode', '?')}",
            f"F&G:                {self.app.state.get('fear_greed', '?')}",
            "",
            "📈 STRATEGIE-PERFORMANCE",
            "-" * 80,
            f"{'Strategie':<25}{'Trades':>8}{'Wins':>8}{'Win-Rate':>10}{'Gesamt PnL':>12}",
            "-" * 80,
        ]

        for s_id, s_data in stats.get("strategies", {}).items():
            wr = (s_data["wins"] / s_data["trades"] * 100) if s_data["trades"] > 0 else 0
            active = " ◀ AKTIV" if s_id == brain.get("strategy_id", "") else ""
            lines.append(f"{s_id:<25}{s_data['trades']:>8}{s_data['wins']:>8}{wr:>9.1f}%{s_data['pnl']:>+11.2f}{active}")

        lines.extend(["", "📋 TRADE-HISTORY (letzte 50)", "-" * 100,
            f"{'Zeit':<22}{'Typ':<8}{'Coin':<12}{'Menge':>12}{'Preis':>12}{'P&L':>10}{'Strategie':<15}",
            "-" * 100])

        for t in self.app.journal.get_all()[-50:]:
            ts = str(t.get("time", ""))[:19]
            typ = t.get("type", "?")
            coin = str(t.get("coin", "?")).split("/")[0]
            qty = t.get("qty", 0)
            price = t.get("price", 0)
            pnl = t.get("pnl", "")
            pnl_s = f"{pnl:+.2f}" if isinstance(pnl, (int, float)) and pnl else ""
            strat = str(t.get("strategy", ""))[:14]
            lines.append(f"{ts:<22}{typ:<8}{coin:<12}{qty:>12.6f}{price:>11,.2f}${pnl_s:>10}{strat:<15}")

        lines.extend(["", "=" * 80, "Ende der Analyse. Viel Erfolg beim Trading!"])
        return "\n".join(lines)

    def daily_report(self):
        """Sendet Tagesbericht per Telegram."""
        try:
            stats = self.app.journal.get_stats()
            balance = self.app.execution.get_balance()
            self.app.telegram.send_daily_report(stats, balance)
        except Exception as e:
            log.error("REPORT", f"Tagesbericht: {str(e)[:60]}")

    def weekly_report(self):
        """Sendet Wochenbericht per Telegram."""
        try:
            stats = self.app.journal.get_stats()
            balance = self.app.execution.get_balance()
            self.app.telegram.send_weekly_report(stats, balance)
        except Exception as e:
            log.error("REPORT", f"Wochenbericht: {str(e)[:60]}")

    def heartbeat(self):
        """System-Heartbeat."""
        stats = self.app.journal.get_stats()
        health = self.app.health.check_all()
        uptime = self.app.health.get_uptime()
        log.info("HEART", f"💓 Uptime: {uptime} | Trades: {stats['total_trades']} | "
                          f"P&L: {stats['total_pnl']:+.2f}$ | "
                          f"System: {'✅' if len(health.get('dead_components', [])) <= 1 else '❌'}")
