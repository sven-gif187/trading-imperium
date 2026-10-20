"""
Trading Imperium V6 - Portfolio Agent (100% prozentual)

Nutzt jetzt PortfolioManager als zentrale Quelle fuer:
- Cash-Reserve (% des Kapitals)
- Max Coin / Sektor (% des Kapitals)
- Korrelations-Limits (aus Config)

KEINE hardcoded USD-Werte mehr! Skaliert von 300$ bis 100k$ automatisch.
"""
from typing import Dict
from core.events import DecisionIntent, Side
from core.logger import log
from portfolio.rebalancer import Rebalancer
from portfolio.correlation_guard import CorrelationGuard, SECTORS


class PortfolioAgent:
    """Steuert Kapitalverteilung mit Anti-Klumpenrisiko.
    Alle Werte werden zur LAUFZEIT aus PortfolioManager geholt.
    """

    def __init__(self, config, portfolio_manager=None):
        self.config = config
        self.pm = portfolio_manager  # PortfolioManager fuer prozentuale Werte

        # Rebalancer (% basiert)
        self.rebalancer = Rebalancer(threshold_pct=5.0, min_trade_usd=10.0)

        # Korrelations-Limits aus aktivem Modus
        active_mode = config.get_active_mode()
        max_corr = max(active_mode.max_positions, 3)
        self.correlation_guard = CorrelationGuard(
            max_correlated_positions=max_corr,
            max_sector_coins=max_corr
        )

    def set_portfolio_manager(self, pm):
        """Spaetes Setzen des PortfolioManagers (zyklische Imports)."""
        self.pm = pm

    def check(self, intent, positions, total_equity, cycle_phase=""):
        """Prueft Trade gegen Portfolio-Regeln. ALLE Werte prozentual!

        Args:
            intent: DecisionIntent (BUY/SELL)
            positions: dict {symbol: {value: usd, ...}}
            total_equity: Aktuelles Gesamt-Kapital in USDC

        Returns: {ok: bool, reason: str, amount: float}
        """
        if intent.side != Side.BUY:
            return {"ok": True, "reason": "Sell erlaubt", "amount": intent.amount_usd}

        if total_equity <= 0:
            return {"ok": False, "reason": "Kein Kapital", "amount": 0}

        asset = intent.symbol.split("/")[0]
        amount = intent.amount_usd

        # Werte aus aktivem Modus holen (bei jedem Check frisch!)
        active_mode = self.config.get_active_mode()
        cash_reserve_pct = active_mode.cash_reserve_pct
        max_coin_pct = active_mode.max_coin_pct
        max_sector_pct = active_mode.sector_limit_pct

        # ============================================================
        # 1. CASH-RESERVE - dynamisch, basiert auf AKTUELLEM Cash
        # BUG-FIX 2025-04: Robust gegen falsche Werte, nutzt actual_cash
        # ============================================================
        invested = sum(p.get("value", 0) for p in positions.values())

        # Cash = total_equity - invested (so wie es WIRKLICH ist)
        # Wenn Aufrufer nicht alle Positionen mitschickt, kann actual_cash
        # falsch hoch sein - aber besser als negativ
        actual_cash = max(0, total_equity - invested)
        cash_after_trade = actual_cash - amount

        # Cash-Reserve: % des AKTUELLEN Gesamt-Kapitals (skaliert!)
        required_reserve = total_equity * cash_reserve_pct / 100.0

        # Mindest-Trade-Schwelle: 0.5% des Kapitals oder 5$
        min_trade_threshold = max(total_equity * 0.005, 5.0)

        # Wenn der Trade die Reserve unterschreiten wuerde
        if cash_after_trade < required_reserve:
            # Reduziere Trade auf max moeglichen Betrag
            max_ok = actual_cash - required_reserve

            # Wenn actual_cash bereits unter Reserve liegt -> kein Trade!
            if actual_cash < required_reserve:
                return {"ok": False,
                        "reason": f"Cash bereits unter Reserve: {actual_cash:.2f}$ < "
                                  f"{required_reserve:.2f}$ ({cash_reserve_pct}%)",
                        "amount": 0}

            if max_ok < min_trade_threshold:
                # Wirklich kein Geld mehr da
                return {"ok": False,
                        "reason": f"Cash-Reserve: nur {actual_cash:.2f}$ frei, "
                                  f"{required_reserve:.2f}$ ({cash_reserve_pct}%) sind Reserve",
                        "amount": 0}
            amount = min(amount, max_ok)
            log.info("PORTFOLIO", f"Sizing reduziert: {amount:.2f}$ "
                                  f"(Reserve: {required_reserve:.2f}$ = {cash_reserve_pct}%, "
                                  f"Cash: {actual_cash:.2f}$)")

        # ============================================================
        # 2. EINZELCOIN-LIMIT - prozentual!
        # ============================================================
        coin_val = positions.get(asset, {}).get("value", 0) + amount
        coin_pct = (coin_val / total_equity * 100) if total_equity > 0 else 0

        if coin_pct > max_coin_pct:
            max_coin_value = total_equity * max_coin_pct / 100.0
            allowed = max_coin_value - positions.get(asset, {}).get("value", 0)
            if allowed < min_trade_threshold:
                return {"ok": False,
                        "reason": f"{asset} schon {coin_pct:.0f}% (max {max_coin_pct}%)",
                        "amount": 0}
            amount = min(amount, allowed)

        # ============================================================
        # 3. SEKTOR-KORRELATION - prozentual!
        # ============================================================
        sector = SECTORS.get(asset, "other")
        sec_val = sum(p.get("value", 0)
                     for c, p in positions.items()
                     if SECTORS.get(c, "other") == sector)
        sec_pct = ((sec_val + amount) / total_equity * 100) if total_equity > 0 else 0

        if sec_pct > max_sector_pct:
            return {"ok": False,
                    "reason": f"Sektor '{sector}' schon {sec_pct:.0f}% (max {max_sector_pct}%)",
                    "amount": 0}

        # Korrelations-Check
        try:
            limit_check = self.correlation_guard.check(asset, positions)
            if not limit_check.get("ok", True):
                return {"ok": False,
                        "reason": limit_check.get("reason", "Korrelations-Limit"),
                        "amount": 0}
        except Exception:
            pass

        # ============================================================
        # OK - Trade approved
        # ============================================================
        return {
            "ok": True,
            "reason": "OK",
            "amount": amount,
            "stats": {
                "coin_pct": coin_pct,
                "sector_pct": sec_pct,
                "cash_pct": (cash_after_trade / total_equity * 100) if total_equity > 0 else 0,
            }
        }

    def get_status(self) -> Dict:
        """Status fuer Dashboard."""
        mode = self.config.get_active_mode()
        return {
            "mode": mode.name,
            "cash_reserve_pct": mode.cash_reserve_pct,
            "max_coin_pct": mode.max_coin_pct,
            "max_sector_pct": mode.sector_limit_pct,
            "max_positions": mode.max_positions,
        }
