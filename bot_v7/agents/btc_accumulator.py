"""
Trading Imperium V5 – BTC Akkumulation
Auto-BTC aus Gewinnen + DCA-Sparplan mit 1/3-Regel.
Ziel: Langfristig BTC aufbauen, egal was der Markt macht.
"""
import time
import json
import os
from typing import Dict, List
from datetime import datetime, timezone
from core.logger import log
from config.settings import DATA_DIR


ACCUMULATOR_FILE = os.path.join(DATA_DIR, "btc_accumulator.json")


def _taker_pct():
    """Die Boersengebuehr je Seite, in Prozent - aus EINER Quelle.

    [17.09.2026] An zwei Stellen dieser Datei stand `* 0.001`, also
    0,1 %. Bybit EU nimmt 0,25 % je Seite; die Annahme war 60 % zu
    niedrig. Sie stammt aus der Zeit vor der Boersenwahl und ist
    derselbe Fehler, der laut Handbuch 4.53 noch an weiteren Stellen
    im Projekt steckt.

    Der Wert wird NICHT hier hineingeschrieben, sondern aus
    core/kosten.py geholt. Eine Zahl, die an drei Stellen steht, geht
    irgendwann an einer davon falsch aus - genau so ist dieser Fehler
    entstanden.

    Faellt der Import aus, wird bewusst der TEURERE Wert genommen: wer
    zu hohe Kosten annimmt, kauft etwas zu wenig. Wer zu niedrige
    annimmt, bucht mehr, als er bezahlt hat - und das faellt erst beim
    Kontoabgleich auf.
    """
    try:
        from core.kosten import TAKER_PCT
        return float(TAKER_PCT)
    except Exception:
        return 0.25


class BTCAccumulator:
    """BTC-Akkumulation: Sparplan + Auto-Konvertierung aus Gewinnen."""

    def __init__(self, config):
        self.config = config
        self.total_btc = 0.0
        self.total_invested_usd = 0.0
        self.buy_history = []
        self.sparplan_active = config.trading.btc_dca_enabled
        self.sparplan_pct = config.trading.btc_dca_pct        # 33% = 1/3 Regel
        self.sparplan_interval = config.trading.btc_dca_interval_min * 60  # Sekunden
        self.last_sparplan_time = 0
        self.unrealized_profit_for_btc = 0.0  # Gewinne die noch nicht in BTC konvertiert wurden
        self._load()

    def _load(self):
        """Lädt gespeicherte Akkumulations-Daten."""
        if not os.path.exists(ACCUMULATOR_FILE):
            return
        try:
            with open(ACCUMULATOR_FILE, "r") as f:
                data = json.load(f)
            self.total_btc = data.get("total_btc", 0)
            self.total_invested_usd = data.get("total_invested_usd", 0)
            self.buy_history = data.get("buy_history", [])
            self.last_sparplan_time = data.get("last_sparplan_time", 0)
            self.unrealized_profit_for_btc = data.get("unrealized_profit", 0)
            log.info("BTC-ACC", f"Geladen: {self.total_btc:.8f} BTC ({self.total_invested_usd:.2f}$ investiert)")
        except Exception as e:
            log.warn("BTC-ACC", f"Laden fehlgeschlagen: {e}")

    def _save(self):
        """Speichert Akkumulations-Daten."""
        try:
            data = {
                "total_btc": self.total_btc,
                "total_invested_usd": self.total_invested_usd,
                "buy_history": self.buy_history[-500:],
                "last_sparplan_time": self.last_sparplan_time,
                "unrealized_profit": self.unrealized_profit_for_btc,
            }
            tmp = ACCUMULATOR_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=1, default=str)
            os.replace(tmp, ACCUMULATOR_FILE)
        except Exception as e:
            log.warn("BTC-ACC", f"Speichern fehlgeschlagen: {e}")

    def record_purchase(self, usd_spent: float, btc_qty: float, btc_price: float, source: str = "SPARPLAN"):
        """Zeichnet einen BTC-Kauf auf."""
        self.total_btc += btc_qty
        self.total_invested_usd += usd_spent
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "usd_spent": round(usd_spent, 2),
            "btc_qty": round(btc_qty, 8),
            "btc_price": round(btc_price, 2),
            "source": source,
            "total_btc_after": round(self.total_btc, 8),
        }
        self.buy_history.append(entry)
        self._save()
        log.trade("BTC-ACC", f"₿ {source}: {usd_spent:.2f}$ → {btc_qty:.8f} BTC @ {btc_price:,.2f}$")
        return entry

    def add_profit_for_conversion(self, profit_usd: float):
        """Fügt Gewinn hinzu der in BTC konvertiert werden soll."""
        if profit_usd > 0:
            self.unrealized_profit_for_btc += profit_usd
            self._save()

    def reset(self):
        """Setzt die komplette BTC-Akkumulation zurueck (fuer Reset-Script)."""
        self.total_btc = 0.0
        self.total_invested_usd = 0.0
        self.buy_history = []
        self.last_sparplan_time = 0
        self.unrealized_profit_for_btc = 0.0
        self._save()
        log.info("BTC-ACC", "Akkumulator komplett zurueckgesetzt")

    def check_sparplan(self, usdc_balance: float, btc_price: float,
                       execution_engine=None) -> Dict:
        """
        Prüft ob ein Sparplan-Kauf fällig ist.
        Returns: {"executed": bool, "amount": float, "btc_qty": float}
        """
        if not self.sparplan_active:
            return {"executed": False, "reason": "Sparplan deaktiviert"}

        now = time.time()
        if (now - self.last_sparplan_time) < self.sparplan_interval:
            remaining = int(self.sparplan_interval - (now - self.last_sparplan_time))
            return {"executed": False, "reason": f"Nächster Kauf in {remaining // 60}m"}

        # 1/3 Regel: Kaufe sparplan_pct% des verfügbaren USDC
        buy_amount = usdc_balance * (self.sparplan_pct / 100)

        if buy_amount < 5:
            return {"executed": False, "reason": f"Zu wenig USDC ({usdc_balance:.2f}$)"}

        if btc_price <= 0:
            return {"executed": False, "reason": "Kein BTC-Preis"}

        # === BUG-FIX: USDC-Check + Abzug (sonst doppelt gezaehlt) ===
        if execution_engine is not None:
            _pbal = getattr(execution_engine, "_paper_balances", {}) or {}
            _free = _pbal.get("USDC", 0) + _pbal.get("USDT", 0)
            if _free < buy_amount:
                return {"executed": False, "reason": f"Zu wenig freies USDC ({_free:.2f}$)"}
            _pbal["USDC"] = _pbal.get("USDC", 0) - buy_amount
            execution_engine._paper_balances = _pbal

        # [17.09.2026] Hier stand fest verdrahtet 0.001, also 0,1 %.
        # Bybit EU nimmt 0,25 % je Seite (CLAUDE.md Abschnitt 8). Der
        # Sparplan haette also 0,15 Prozentpunkte zu wenig abgezogen und
        # entsprechend zuviel BTC gebucht.
        #
        # WIRKUNG BISHER: keine. Der Sparplan hat in keinem der beiden
        # Journale je gekauft (0 von 8 live, 0 von 554 Papier) - der Pfad
        # ist tot. Deshalb ist das hier kein Kapitalrisiko, sondern eine
        # Zeitbombe fuer den Tag, an dem er eingeschaltet wird.
        fee = buy_amount * (_taker_pct() / 100.0)
        btc_qty = (buy_amount - fee) / btc_price
        self.last_sparplan_time = now
        self.record_purchase(buy_amount, btc_qty, btc_price, "SPARPLAN")

        return {
            "executed": True,
            "amount": round(buy_amount, 2),
            "btc_qty": round(btc_qty, 8),
            "btc_price": round(btc_price, 2),
            "fee": round(fee, 4),
        }

    def check_profit_conversion(self, btc_price: float, min_amount: float = 3.0,
                                execution_engine=None) -> Dict:
        """
        Konvertiert angesammelte Gewinne in BTC.
        Returns: {"executed": bool, "amount": float, "btc_qty": float}
        """
        if self.unrealized_profit_for_btc < min_amount:
            return {"executed": False, "reason": f"Zu wenig Gewinn ({self.unrealized_profit_for_btc:.2f}$)"}

        if btc_price <= 0:
            return {"executed": False, "reason": "Kein BTC-Preis"}

        amount = self.unrealized_profit_for_btc

        # === BUG-FIX: USDC-Check + Abzug (sonst doppelt gezaehlt) ===
        if execution_engine is not None:
            _pbal = getattr(execution_engine, "_paper_balances", {}) or {}
            _free = _pbal.get("USDC", 0) + _pbal.get("USDT", 0)
            if _free < amount:
                return {"executed": False, "reason": f"Zu wenig freies USDC ({_free:.2f}$ < {amount:.2f}$)"}
            _pbal["USDC"] = _pbal.get("USDC", 0) - amount
            execution_engine._paper_balances = _pbal

        # [17.09.2026] Zweite Stelle, gleicher Fehler wie oben in
        # check_sparplan. Eine Konstante, die an zwei Stellen steht, geht
        # irgendwann an einer davon falsch aus - deshalb beide ueber
        # _taker_pct().
        fee = amount * (_taker_pct() / 100.0)
        btc_qty = (amount - fee) / btc_price
        self.unrealized_profit_for_btc = 0
        self.record_purchase(amount, btc_qty, btc_price, "AUTO-BTC")

        return {
            "executed": True,
            "amount": round(amount, 2),
            "btc_qty": round(btc_qty, 8),
            "btc_price": round(btc_price, 2),
            "fee": round(fee, 4),
        }

    def get_avg_price(self) -> float:
        """Durchschnittlicher Kaufpreis."""
        if self.total_btc <= 0:
            return 0
        return round(self.total_invested_usd / self.total_btc, 2)

    def get_pnl(self, current_btc_price: float) -> Dict:
        """Berechnet P&L der BTC-Akkumulation."""
        current_value = self.total_btc * current_btc_price
        pnl = current_value - self.total_invested_usd
        pnl_pct = ((current_value / self.total_invested_usd) - 1) * 100 if self.total_invested_usd > 0 else 0
        return {
            "total_btc": round(self.total_btc, 8),
            "invested": round(self.total_invested_usd, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "avg_price": self.get_avg_price(),
            "purchases": len(self.buy_history),
        }

    def get_history_text(self) -> str:
        """Formatierte Kauf-Historie."""
        if not self.buy_history:
            return "Noch keine BTC-Käufe."
        lines = [f"{'Zeit':<22}{'Betrag':>10}{'BTC':>14}{'Preis':>12}{'Quelle':<12}",
                 "─" * 70]
        for b in self.buy_history[-30:]:
            ts = b.get("time", "")[:19].replace("T", " ")
            lines.append(f"{ts:<22}{b['usd_spent']:>9.2f}${b['btc_qty']:>14.8f}{b['btc_price']:>11,.2f}${b['source']:<12}")
        lines.append("─" * 70)
        pnl = self.get_pnl(self.buy_history[-1]["btc_price"] if self.buy_history else 0)
        lines.append(f"GESAMT: {pnl['total_btc']:.8f} BTC | {pnl['invested']:.2f}$ investiert | "
                    f"Ø {pnl['avg_price']:,.2f}$/BTC | {pnl['purchases']} Käufe")
        return "\n".join(lines)

    def get_status(self) -> Dict:
        return {
            "total_btc": round(self.total_btc, 8),
            "invested": round(self.total_invested_usd, 2),
            "avg_price": self.get_avg_price(),
            "purchases": len(self.buy_history),
            "sparplan_active": self.sparplan_active,
            "sparplan_pct": self.sparplan_pct,
            "unrealized_profit": round(self.unrealized_profit_for_btc, 2),
        }
