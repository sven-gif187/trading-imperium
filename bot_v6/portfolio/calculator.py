"""
Trading Imperium V6 - Portfolio Calculator
=============================================
DAS HERZSTUECK: Berechnet ALLES prozentual zum aktuellen Kapital.
Funktioniert IDENTISCH fuer Paper UND Live - einziger Unterschied:
- Paper: balance kommt aus PaperExchange (config.initial_paper_balance)
- Live:  balance kommt LIVE von Binance (echte Balance)

REGEL: Es gibt KEINEN einzigen hardcoded USDC-Betrag im Sizing!
Alle Limits sind Prozente und werden zur Laufzeit berechnet.
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from core.logger import log


@dataclass
class PortfolioSnapshot:
    """Aktueller Portfolio-Zustand (jeder Trade ruft das frisch ab)."""
    total_value_usd: float = 0.0
    cash_usd: float = 0.0
    invested_usd: float = 0.0
    open_positions_count: int = 0
    daily_start_value: float = 0.0
    daily_pnl_usd: float = 0.0
    daily_pnl_pct: float = 0.0
    timestamp: float = 0.0


@dataclass
class TradeSizing:
    """Berechnete Sizing-Werte fuer einen Trade."""
    allowed: bool = False
    reason: str = ""
    amount_usd: float = 0.0
    amount_pct: float = 0.0
    cash_after_trade: float = 0.0
    cash_reserve_required: float = 0.0
    can_open_more_positions: bool = True


class PortfolioCalculator:
    """ZENTRALE Sizing-Engine - rein prozentual.

    Verwendung:
        calc = PortfolioCalculator(config, execution)
        snapshot = calc.get_snapshot(open_positions, prices)
        sizing = calc.calculate_trade_size(snapshot, symbol, open_positions, prices)
        if sizing.allowed:
            execute_trade(symbol, sizing.amount_usd)
    """

    def __init__(self, config, execution_engine, sectors_map=None):
        self.config = config
        self.execution = execution_engine
        self.sectors_map = sectors_map or {}
        self._daily_start_value = None
        self._daily_start_date = None
        self._daily_paused = False

    def get_snapshot(self, open_positions: Dict, prices: Dict) -> PortfolioSnapshot:
        """Live Portfolio-Snapshot (Cash + Positionen).
        LIVE: holt echte Binance-Balance, PAPER: holt Paper-Balance.
        """
        try:
            balance = self.execution.get_balance()
            cash = float(balance.get("total", {}).get("USDC", 0)) + \
                   float(balance.get("total", {}).get("USDT", 0))
        except Exception as e:
            log.warn("PORTFOLIO", f"Balance-Abruf fehlgeschlagen: {e}")
            cash = 0.0

        invested = 0.0
        active_count = 0
        for symbol, pos in open_positions.items():
            if not pos.get("active"):
                continue
            qty = pos.get("qty", 0)
            price = prices.get(symbol, 0)
            if qty > 0 and price > 0:
                invested += qty * price
                active_count += 1

        total = cash + invested

        # Daily-Start tracken
        today = time.strftime("%Y-%m-%d")
        if self._daily_start_date != today:
            self._daily_start_date = today
            self._daily_start_value = total
            self._daily_paused = False
            log.info("PORTFOLIO", f"Tages-Start: {total:.2f}$")
        elif self._daily_start_value is None:
            self._daily_start_value = total

        daily_pnl_usd = total - self._daily_start_value
        daily_pnl_pct = (daily_pnl_usd / self._daily_start_value * 100) if self._daily_start_value > 0 else 0

        return PortfolioSnapshot(
            total_value_usd=total, cash_usd=cash, invested_usd=invested,
            open_positions_count=active_count,
            daily_start_value=self._daily_start_value,
            daily_pnl_usd=daily_pnl_usd, daily_pnl_pct=daily_pnl_pct,
            timestamp=time.time(),
        )

    def calculate_trade_size(self, snapshot: PortfolioSnapshot, symbol: str,
                            open_positions: Optional[Dict] = None,
                            prices: Optional[Dict] = None) -> TradeSizing:
        """Komplette Sizing-Logik - rein prozentual."""
        mode = self.config.get_active_mode()
        total = snapshot.total_value_usd

        # Daily-Loss-Limit
        if self._daily_paused:
            return TradeSizing(allowed=False,
                reason=f"Daily-Loss-Limit aktiv ({snapshot.daily_pnl_pct:.1f}%)")

        if snapshot.daily_pnl_pct <= -self.config.risk.max_daily_loss_pct:
            self._daily_paused = True
            log.error("PORTFOLIO", f"🚨 DAILY-LOSS-LIMIT! "
                      f"{snapshot.daily_pnl_pct:.1f}% <= -{self.config.risk.max_daily_loss_pct}%")
            return TradeSizing(allowed=False,
                reason=f"Daily-Loss-Limit erreicht ({snapshot.daily_pnl_pct:.1f}%)")

        if total <= 0:
            return TradeSizing(allowed=False, reason="Kein Kapital")

        if snapshot.open_positions_count >= mode.max_positions:
            return TradeSizing(allowed=False,
                reason=f"Max Positionen: {snapshot.open_positions_count}/{mode.max_positions}",
                can_open_more_positions=False)

        # Sizing prozentual
        target_amount = total * (mode.position_size_pct / 100.0)
        cash_reserve_required = total * (mode.cash_reserve_pct / 100.0)
        cash_after_trade = snapshot.cash_usd - target_amount

        if cash_after_trade < cash_reserve_required:
            max_allowed = snapshot.cash_usd - cash_reserve_required
            if max_allowed < total * 0.01:
                return TradeSizing(allowed=False,
                    reason=f"Cash-Reserve verletzt (Cash: {snapshot.cash_usd:.2f}$, Reserve: {cash_reserve_required:.2f}$)",
                    cash_after_trade=cash_after_trade,
                    cash_reserve_required=cash_reserve_required)
            target_amount = max_allowed
            log.info("PORTFOLIO", f"Sizing reduziert: {target_amount:.2f}$ wegen Cash-Reserve")

        # Sektor-Limit
        if mode.sector_limit_pct < 100.0 and open_positions and prices:
            asset = symbol.split("/")[0]
            sector = self.sectors_map.get(asset, "other")
            sector_value = sum(
                pos.get("qty", 0) * prices.get(sym, 0)
                for sym, pos in open_positions.items()
                if pos.get("active") and self.sectors_map.get(sym.split("/")[0], "other") == sector
            )
            sector_pct_after = (sector_value + target_amount) / total * 100
            if sector_pct_after > mode.sector_limit_pct:
                allowed_sector = total * (mode.sector_limit_pct / 100.0) - sector_value
                if allowed_sector < total * 0.01:
                    return TradeSizing(allowed=False,
                        reason=f"Sektor '{sector}' bereits {sector_value/total*100:.0f}% (max {mode.sector_limit_pct}%)")
                target_amount = min(target_amount, allowed_sector)

        # Coin-Limit
        if open_positions and prices:
            asset = symbol.split("/")[0]
            existing = 0.0
            for sym, pos in open_positions.items():
                if pos.get("active") and sym.split("/")[0] == asset:
                    existing += pos.get("qty", 0) * prices.get(sym, 0)
            coin_pct_after = (existing + target_amount) / total * 100
            if coin_pct_after > mode.max_coin_pct:
                allowed_coin = total * (mode.max_coin_pct / 100.0) - existing
                if allowed_coin < total * 0.01:
                    return TradeSizing(allowed=False,
                        reason=f"Coin {asset} bereits {existing/total*100:.0f}% (max {mode.max_coin_pct}%)")
                target_amount = min(target_amount, allowed_coin)

        amount_pct = (target_amount / total * 100) if total > 0 else 0
        return TradeSizing(
            allowed=True, reason="OK", amount_usd=target_amount, amount_pct=amount_pct,
            cash_after_trade=snapshot.cash_usd - target_amount,
            cash_reserve_required=cash_reserve_required,
            can_open_more_positions=(snapshot.open_positions_count + 1 < mode.max_positions),
        )

    # === STOP-LOSS / TAKE-PROFIT - PROZENTUAL ===
    def calculate_stop_loss(self, entry_price: float) -> float:
        return entry_price * (1 - self.config.risk.stop_loss_pct / 100.0)

    def calculate_take_profit(self, entry_price: float) -> float:
        if self.config.risk.take_profit_pct <= 0:
            return 0.0
        return entry_price * (1 + self.config.risk.take_profit_pct / 100.0)

    def calculate_trailing_stop(self, highest_price: float) -> float:
        return highest_price * (1 - self.config.risk.trailing_stop_pct / 100.0)

    def should_trigger_sl(self, current_price: float, entry_price: float) -> bool:
        return current_price <= self.calculate_stop_loss(entry_price)

    def should_trigger_tp(self, current_price: float, entry_price: float) -> bool:
        tp = self.calculate_take_profit(entry_price)
        return tp > 0 and current_price >= tp

    def should_trigger_trailing(self, current_price: float, highest_price: float) -> bool:
        return current_price <= self.calculate_trailing_stop(highest_price)

    # === DAILY-LOSS / LIVE/PAPER ===
    def is_daily_paused(self) -> bool:
        return self._daily_paused

    def force_daily_reset(self):
        self._daily_start_value = None
        self._daily_start_date = None
        self._daily_paused = False
        log.info("PORTFOLIO", "Daily-Tracker zurueckgesetzt")

    def is_live_mode(self) -> bool:
        return self.config.trading.mode == "live"

    def is_paper_mode(self) -> bool:
        return self.config.trading.mode == "paper"

    def check_live_safety(self, symbol: str, ticker: Optional[Dict] = None) -> Tuple[bool, str]:
        """LIVE-ONLY: Spread + Volume Filter."""
        if not self.is_live_mode():
            return True, "Paper-Modus"

        if ticker is None:
            return False, "Kein Ticker"

        bid = float(ticker.get("bid", 0))
        ask = float(ticker.get("ask", 0))
        if bid > 0 and ask > 0:
            spread_pct = (ask - bid) / bid * 100
            if spread_pct > self.config.risk.max_spread_pct:
                return False, f"Spread zu hoch: {spread_pct:.2f}%"

        volume_24h = float(ticker.get("quoteVolume", 0))
        if volume_24h < self.config.risk.min_volume_24h_usd:
            return False, f"Volumen zu niedrig: {volume_24h:,.0f}$"

        return True, "OK"

    def get_status(self, snapshot: Optional[PortfolioSnapshot] = None) -> Dict:
        mode = self.config.get_active_mode()
        return {
            "mode": self.config.trading.mode,
            "active_strategy": mode.name,
            "position_size_pct": mode.position_size_pct,
            "max_positions": mode.max_positions,
            "cash_reserve_pct": mode.cash_reserve_pct,
            "sector_limit_pct": mode.sector_limit_pct,
            "max_coin_pct": mode.max_coin_pct,
            "stop_loss_pct": self.config.risk.stop_loss_pct,
            "take_profit_pct": self.config.risk.take_profit_pct,
            "trailing_stop_pct": self.config.risk.trailing_stop_pct,
            "daily_loss_limit_pct": self.config.risk.max_daily_loss_pct,
            "daily_paused": self._daily_paused,
            "snapshot": {
                "total": snapshot.total_value_usd if snapshot else 0,
                "cash": snapshot.cash_usd if snapshot else 0,
                "invested": snapshot.invested_usd if snapshot else 0,
                "positions": snapshot.open_positions_count if snapshot else 0,
                "daily_pnl_pct": snapshot.daily_pnl_pct if snapshot else 0,
            } if snapshot else {},
        }
