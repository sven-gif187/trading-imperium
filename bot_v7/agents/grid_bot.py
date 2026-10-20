"""Grid Bot - Bollinger Band Grid Trader.

Funktioniert in Seitwaertsmaerkten (RANGING). Teilt die Bollinger-
Spanne in 8 Stufen. Kauft an unteren Stufen wenn Preis dort landet.
SELL laeuft ueber den bestehenden Trailing-Stop.

Self-Check: nur aktiv wenn ADX < 25 (Seitwaerts) UND Bandbreite > 2%.
"""
import time
import pandas as pd
from typing import Optional, Dict
from core.events import DecisionIntent, Side, MarketSnapshot
from core.logger import log


class GridBot:
    """Bollinger-Band-basierter Grid Trader fuer Seitwaertsphasen."""

    def __init__(self, config, num_levels: int = 8, max_capital_pct: float = 40.0,
                 cooldown_minutes: int = 60, max_grid_coins: int = 4,
                 max_adx: float = 25.0, min_band_width_pct: float = 2.0):
        self.config = config
        self.num_levels = num_levels
        self.max_capital_pct = max_capital_pct
        self.cooldown_minutes = cooldown_minutes
        self.max_grid_coins = max_grid_coins
        self.max_adx = max_adx
        self.min_band_width_pct = min_band_width_pct

        self._last_trade_time: Dict[str, float] = {}
        self._active_coins: set = set()

    def _get_bollinger(self, df) -> tuple:
        """Holt Bollinger Baender. Returns (lower, middle, upper)."""
        try:
            bbl = df.get("BBL_20_2.0")
            bbm = df.get("BBM_20_2.0")
            bbu = df.get("BBU_20_2.0")

            if bbl is None or bbm is None or bbu is None:
                # Manuell berechnen falls Spalten fehlen
                close = df["Close"]
                if len(close) < 20:
                    return 0.0, 0.0, 0.0
                bbm_val = close.rolling(20).mean().iloc[-1]
                std = close.rolling(20).std().iloc[-1]
                bbl_val = bbm_val - 2 * std
                bbu_val = bbm_val + 2 * std
            else:
                bbl_val = bbl.iloc[-1]
                bbm_val = bbm.iloc[-1]
                bbu_val = bbu.iloc[-1]

            if pd.isna(bbl_val) or pd.isna(bbm_val) or pd.isna(bbu_val):
                return 0.0, 0.0, 0.0

            return float(bbl_val), float(bbm_val), float(bbu_val)
        except Exception:
            return 0.0, 0.0, 0.0

    def _get_grid_levels(self, lower: float, upper: float) -> list:
        """Teilt Spanne in num_levels gleiche Stufen."""
        if lower >= upper or lower <= 0:
            return []
        step = (upper - lower) / self.num_levels
        return [lower + step * i for i in range(self.num_levels + 1)]

    def _in_cooldown(self, symbol: str) -> bool:
        last = self._last_trade_time.get(symbol, 0)
        elapsed_min = (time.time() - last) / 60.0
        return elapsed_min < self.cooldown_minutes

    def evaluate(self, snapshot, balance_usd: float = 0,
                 has_position: bool = False) -> Optional[DecisionIntent]:
        """Prueft ob Grid-BUY-Signal vorliegt. SELL ueber Trailing-Stop.

        Returns: DecisionIntent (BUY) oder None
        """
        if not snapshot or not hasattr(snapshot, "_df"):
            return None
        if has_position:
            return None  # Grid kauft nicht doppelt

        symbol = snapshot.symbol
        price = snapshot.close
        df = snapshot._df

        if df is None or len(df) < 20:
            return None

        # === SELF-CHECK 1: Ist Markt RANGING? ===
        adx = snapshot.indicators.get("adx", 100)
        if adx > self.max_adx:
            return None  # Trendmarkt -> nicht Grid-tauglich

        # === SELF-CHECK 2: Cooldown? ===
        if self._in_cooldown(symbol):
            return None

        # === SELF-CHECK 3: Max Grid-Coins erreicht? ===
        if symbol not in self._active_coins and len(self._active_coins) >= self.max_grid_coins:
            return None

        # === SELF-CHECK 4: Bollinger holen ===
        lower, middle, upper = self._get_bollinger(df)
        if lower <= 0 or middle <= 0 or upper <= 0:
            return None

        # === SELF-CHECK 5: Bandbreite >= Minimum? ===
        band_width_pct = ((upper - lower) / middle) * 100
        if band_width_pct < self.min_band_width_pct:
            return None  # Zu enge Range, kein Grid-Gewinn moeglich

        # === SELF-CHECK 6: Preis im unteren Halbraum? ===
        if price > middle:
            return None  # Nur an unteren Stufen kaufen

        # === GRID-LEVEL HIT? ===
        levels = self._get_grid_levels(lower, upper)
        if not levels:
            return None

        # Untere Stufen (von middle abwaerts)
        buy_levels = sorted([l for l in levels if l <= middle], reverse=True)
        # Toleranz: 0.5% um den Level
        tolerance = 0.005

        hit_level = None
        for lvl in buy_levels:
            if lvl <= 0:
                continue
            if abs(price - lvl) / lvl <= tolerance:
                hit_level = lvl
                break

        if hit_level is None:
            return None  # Kein Level getroffen

        # === BALANCE-CHECK ===
        if balance_usd < 10:
            return None

        # === SIZING ===
        # 40% Cap / 4 Coins / 8 Stufen = 1.25% pro Trade
        pos_pct = self.max_capital_pct / self.max_grid_coins / self.num_levels
        pos_size = balance_usd * (pos_pct / 100)
        pos_size = max(pos_size, 10.0)         # Mindestens 10$
        pos_size = min(pos_size, balance_usd * 0.5)  # Max 50% des Cash pro Trade

        # === INTENT ERSTELLEN ===
        self._last_trade_time[symbol] = time.time()
        self._active_coins.add(symbol)

        intent = DecisionIntent(
            symbol=symbol,
            side=Side.BUY,
            confidence=0.65,
            entry_price=price,
            amount_usd=pos_size,
            stop_loss=price * (1 - self.config.risk.stop_loss_pct / 100),
            trailing_stop_pct=self.config.risk.trailing_stop_pct,
            strategy_id="GRID_BOT",
            strategy_name="Grid Bot (Bollinger)",
            entry_reason=f"Grid-Level @ {hit_level:.4f}$ (Band: {lower:.4f}-{upper:.4f}, ADX {adx:.0f})",
            score=5,
            agent_id="grid_bot",
        )
        log.info("GRID", f"{symbol}: BUY {pos_size:.2f}$ @ {price:.4f}$ "
                         f"(Level {hit_level:.4f}$, Band {band_width_pct:.1f}%, ADX {adx:.0f})")
        return intent

    def on_position_closed(self, symbol: str):
        """Wird nach Verkauf aufgerufen damit Coin wieder frei wird."""
        self._active_coins.discard(symbol)

    def get_status(self) -> Dict:
        return {
            "active_coins": list(self._active_coins),
            "num_levels": self.num_levels,
            "max_capital_pct": self.max_capital_pct,
            "max_grid_coins": self.max_grid_coins,
            "cooldown_minutes": self.cooldown_minutes,
            "max_adx": self.max_adx,
            "min_band_width_pct": self.min_band_width_pct,
        }
