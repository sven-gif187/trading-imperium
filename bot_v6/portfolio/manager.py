"""
Trading Imperium V6 - Portfolio Manager (zentrale Kapitalverwaltung)

ALLES PROZENTUAL - skaliert automatisch von 300$ bis 100.000$.

Features:
- get_total_capital(): Holt aktuelle Balance (Paper ODER Live)
- get_position_size(): Prozentual basierend auf aktivem Modus
- get_cash_reserve(): Prozentual basierend auf aktivem Modus
- check_daily_loss_limit(): Stoppt Bot bei -10% Tagesverlust
- get_max_positions(): Aus aktivem Modus

Beispiel:
    pm = PortfolioManager(config, execution_engine)
    capital = pm.get_total_capital()           # 300$ Paper oder 1.500$ Live
    size = pm.get_position_size(capital)       # 30% von capital = 90$ bzw 450$
    reserve = pm.get_cash_reserve(capital)     # 10% von capital = 30$ bzw 150$
"""
import time
from typing import Dict, Optional
from datetime import datetime, timezone
from core.logger import log


class PortfolioManager:
    """Zentrale Kapitalverwaltung - 100% prozentual.

    Lebt im Hauptsystem als self.portfolio und wird von:
    - SignalAgent (Position-Sizing)
    - RiskEngine (Limits)
    - PortfolioAgent (Cash-Reserve)
    - ExecutionEngine (Balance-Check)
    aufgerufen statt hardcodete Werte zu verwenden.
    """

    def __init__(self, config, execution_engine):
        self.config = config
        self.execution = execution_engine

        # Tagesstart-Kapital fuer Daily-Loss-Limit
        self._day_start_capital = 0.0
        self._day_start_date = ""
        self._daily_loss_active = False  # True = Bot pausiert

        # Initial setzen
        self._update_day_start()

    # ============================================================
    # KERN-FUNKTION: Aktuelles Kapital holen (Paper ODER Live!)
    # ============================================================
    def _kapital_deckel(self, wert: float) -> float:
        """[E10-LIVE 29.07.] Begrenzt das Kapital, mit dem der Bot rechnet.

        Nur im Live-Modus und nur wenn risk.live_max_capital_usd > 0.
        Zweck: auf dem Boersenkonto liegt oft mehr als der Bot verwalten
        soll. Ohne Deckel skaliert das prozentuale Sizing automatisch auf
        den GESAMTEN Kontostand hoch - wer 5.000 $ liegen hat, handelt bei
        20 % also mit 1.000 $ je Position, ohne das je entschieden zu haben.
        """
        try:
            if str(getattr(self.config.trading, "mode", "paper")).lower() != "live":
                return wert
            deckel = float(getattr(self.config.risk, "live_max_capital_usd", 0) or 0)
            if deckel > 0 and wert > deckel:
                return deckel
        except Exception:
            pass
        return wert

    def get_total_capital(self) -> float:
        """Gibt das aktuelle Gesamt-Kapital zurueck (USDC + Coin-Werte).

        BUG-FIX: Garantiert dass offene Positionen IMMER mitgerechnet werden.
        Auch wenn price_cache leer ist, wird Entry-Preis als Fallback genutzt.

        Berechnung: Cash + sum(qty * current_price) fuer alle Coins
        """
        try:
            balance = self.execution.get_balance()
            if not balance or "total" not in balance:
                return self._get_capital_from_positions()

            total = balance["total"]
            usdc = total.get("USDC", 0) + total.get("USDT", 0)

            # Coins zu USDC-Wert umrechnen mit ROBUSTER Preis-Logik
            coin_value = 0.0
            for asset, qty in total.items():
                if asset in ("USDC", "USDT") or qty <= 0:
                    continue
                # Preis holen mit Mehrfach-Fallback
                price = self._get_robust_price(asset)
                if price > 0:
                    coin_value += qty * price

            # KRITISCH: Wenn coin_value=0 aber risk_engine sagt Positionen sind offen,
            # dann nutze Risk-Engine Entry-Preise (sonst falscher Verlust!)
            if coin_value == 0:
                position_value = self._get_position_values_from_risk()
                if position_value > 0:
                    log.info("PORTFOLIO",
                             f"Positions-Werte aus Risk-Engine: {position_value:.2f}$ "
                             f"(price_cache war leer)")
                    coin_value = position_value

            balance_based_total = usdc + coin_value

            # === CAPITAL ANOMALY FIX ===
            # (Sparplan-BTC wird weiter unten auf beide Zweige addiert.)
            # Zweite Quelle: Risk-Engine direkt bewerten.
            # Wenn das paper_balances dict asymmetrisch zur Risk-Engine ist,
            # liefert balance_based einen zu niedrigen Wert. Daher: max() nehmen.
            risk_based_positions = self._get_position_values_from_risk()
            risk_based_total = usdc + risk_based_positions

            # [E10-KAPITAL] Sparplan-BTC gehoert zum Kapital (siehe
            # set_btc_accumulator). Wird auf BEIDE Zweige addiert, damit der
            # Anomalie-Vergleich unten weiter Aepfel mit Aepfeln vergleicht.
            acc_value = self.get_btc_accumulator_value()
            balance_based_total += acc_value
            risk_based_total += acc_value

            # 20% Toleranz: ab da gilt's als Anomalie
            if risk_based_total > balance_based_total * 1.2 and risk_based_total > 0:
                # Anomalie-Warnung gedrosselt (max 1x pro 60 Sekunden)
                _now = time.time()
                _last = getattr(self, "_anomaly_last_log", 0)
                if (_now - _last) > 60:
                    self._anomaly_last_log = _now
                    log.info("PORTFOLIO",
                             f"Capital-Sync: balance={balance_based_total:.2f}$ vs "
                             f"risk={risk_based_total:.2f}$ - nutze risk_based")
                return self._kapital_deckel(risk_based_total)

            return self._kapital_deckel(balance_based_total)
        except Exception as e:
            log.warn("PORTFOLIO", f"get_total_capital Fehler: {e}")
            return self._get_capital_from_positions()

    def _get_robust_price(self, asset: str) -> float:
        """Holt Preis mit MEHRFACH-Fallback fuer einen Asset.

        Reihenfolge:
        1. data_agent.price_cache (BTC/USDC oder BTC/USDT)
        2. multi_exchange Ticker
        3. risk_engine entry_price (letzter Fallback - besser als 0!)
        """
        # 1. PRIMAER: aus data_agent.price_cache
        if hasattr(self, '_data_agent') and self._data_agent:
            try:
                cache = getattr(self._data_agent, 'price_cache', {}) or {}
                for sym in [f"{asset}/USDC", f"{asset}/USDT"]:
                    price = cache.get(sym, 0)
                    if price and price > 0:
                        return float(price)
            except Exception:
                pass

        # 2. FALLBACK: multi_exchange
        try:
            for sym in [f"{asset}/USDC", f"{asset}/USDT"]:
                if hasattr(self.execution, 'multi_exchange') and self.execution.multi_exchange:
                    try:
                        ticker = self.execution.multi_exchange.get_ticker(sym)
                        if ticker and "last" in ticker:
                            return float(ticker["last"])
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. LETZTER FALLBACK: Entry-Preis aus Risk-Engine
        # (besser als 0 -> sonst zaehlt offene Position als 'verloren')
        try:
            risk_engine = getattr(self, '_risk_engine', None)
            if risk_engine is not None:
                for sym in [f"{asset}/USDC", f"{asset}/USDT"]:
                    pos = risk_engine.open_positions.get(sym, {})
                    if pos.get("active") and pos.get("entry_price", 0) > 0:
                        return float(pos["entry_price"])
        except Exception:
            pass

        return 0.0

    def _get_capital_from_positions(self) -> float:
        """Fallback: Berechnet Kapital nur aus Cash + Risk-Engine Positionen.
        Wird genutzt wenn Balance-API fehlschlaegt.
        """
        try:
            balance = self.execution.get_balance()
            usdc = 0.0
            if balance and "total" in balance:
                total = balance["total"]
                usdc = total.get("USDC", 0) + total.get("USDT", 0)

            position_value = self._get_position_values_from_risk()
            # [E10-KAPITAL] auch im Notfall-Pfad den Sparplan mitzaehlen
            return usdc + position_value + self.get_btc_accumulator_value()
        except Exception:
            return 0.0

    def _get_position_values_from_risk(self) -> float:
        """Holt Position-Werte aus Risk-Engine open_positions.

        Berechnung: qty * current_price fuer jede aktive Position.
        Falls aktueller Preis fehlt: nutze entry_price als Fallback.
        """
        total = 0.0
        try:
            # Bevorzugt: direkte Referenz, sonst execution-Fallback
            risk_engine = getattr(self, '_risk_engine', None) or \
                          getattr(self.execution, '_risk_engine_ref', None)
            if risk_engine is None:
                return 0.0

            for sym, pos in risk_engine.open_positions.items():
                if not pos.get("active"):
                    continue
                qty = pos.get("qty", 0)
                if qty <= 0:
                    continue

                # Aktuellen Preis holen
                price = 0.0
                if hasattr(self, '_data_agent') and self._data_agent:
                    price = self._data_agent.price_cache.get(sym, 0) or 0

                # Fallback: entry_price (besser als 0)
                if price <= 0:
                    price = pos.get("entry_price", 0)

                if price > 0:
                    total += qty * price
        except Exception:
            pass
        return total

    def get_free_cash(self) -> float:
        """Verfuegbares USDC/USDT Cash (nicht in Coins gebunden)."""
        try:
            balance = self.execution.get_balance()
            if not balance:
                return 0.0
            free = balance.get("free", balance.get("total", {}))
            return free.get("USDC", 0) + free.get("USDT", 0)
        except Exception:
            return 0.0

    def _get_price_for_asset(self, asset: str) -> float:
        """Findet Preis fuer einen Coin (BTC -> BTC/USDC).

        BUG-FIX: Nutzt jetzt PRIMAER data_agent.price_cache,
        statt nur multi_exchange (das oft nicht aktiv ist).
        """
        # 1. PRIMAER: aus data_agent.price_cache (immer aktuell, immer da)
        if hasattr(self, '_data_agent') and self._data_agent:
            try:
                cache = self._data_agent.price_cache
                for sym in [f"{asset}/USDC", f"{asset}/USDT"]:
                    price = cache.get(sym, 0)
                    if price > 0:
                        return float(price)
            except Exception:
                pass

        # 2. FALLBACK: multi_exchange
        try:
            for sym in [f"{asset}/USDC", f"{asset}/USDT"]:
                if hasattr(self.execution, 'multi_exchange') and self.execution.multi_exchange:
                    try:
                        ticker = self.execution.multi_exchange.get_ticker(sym)
                        if ticker and "last" in ticker:
                            return float(ticker["last"])
                    except Exception:
                        pass
        except Exception:
            pass

        return 0.0

    def set_data_agent(self, data_agent):
        """Setzt Referenz zum DataAgent fuer Preis-Cache."""
        self._data_agent = data_agent

    def set_risk_engine(self, risk_engine):
        """Setzt Referenz zur RiskEngine fuer offene Positionen."""
        self._risk_engine = risk_engine

    # ================================================================
    # [E10-KAPITAL 29.07.2026] BTC-SPARPLAN SICHTBAR MACHEN
    # ----------------------------------------------------------------
    # BTCAccumulator.check_sparplan()/check_profit_conversion() ziehen
    # USDC direkt aus execution._paper_balances ab, buchen die gekaufte
    # BTC-Menge aber NUR in die eigene Datei btc_accumulator.json.
    # Sie taucht damit weder in get_balance() noch irgendwo sonst auf.
    #
    # Gemessener Stand 29.07.: 0.00151268 BTC aus 27 Kaeufen fuer
    # 96.01 $ -> aktueller Wert 96.54 $ = 20.7 % des echten Kapitals.
    # Folge: der Bot meldete 370.60 $ (-25.9 %), tatsaechlich waren es
    # 467.14 $ (-6.6 %). Auf dieser zu kleinen Bezugsgroesse rechneten
    # Positionsgroesse, Exposure-Grenzen, Drawdown-Guard und das
    # Tagesstart-Kapital des Daily-Loss-Waechters.
    #
    # Bewusst NICHT in _paper_balances einbuchen: restore_positions()
    # rekonstruiert Positionen aus dem Bestand (qty = bal["BTC"]) und
    # wuerde den Sparplan dann als handelbare Position vereinnahmen und
    # beim naechsten Stop-Loss mitverkaufen. Der Sparplan ist ein
    # Langfrist-Topf und bleibt getrennt - aber er wird gezaehlt.
    # ================================================================
    def set_btc_accumulator(self, accumulator):
        """Setzt Referenz zum BTC-Sparplan (Langfrist-Topf)."""
        self._btc_accumulator = accumulator

    def get_btc_accumulator_value(self) -> float:
        """Aktueller USD-Wert des BTC-Sparplans. 0.0 wenn nicht verdrahtet."""
        acc = getattr(self, "_btc_accumulator", None)
        if acc is None:
            return 0.0
        try:
            menge = float(getattr(acc, "total_btc", 0) or 0)
            if menge <= 0:
                return 0.0
            preis = self._get_robust_price("BTC")
            if preis <= 0:
                # Kein Preis -> Einstand als Untergrenze, besser als 0
                preis_ersatz = float(getattr(acc, "total_invested_usd", 0) or 0)
                return preis_ersatz
            return menge * preis
        except Exception:
            return 0.0

    def get_trading_capital(self) -> float:
        """Kapital fuer die KAUFGROESSE: Handelsgeld (USDC + offene Positionen) OHNE Sparplan-BTC.

        [KG1 KAUFGROESSE HANDELSGELD, 15.10.2026] Entscheidung Sven KG1/KG1a (pruefstand/entscheidungen.md).
        get_total_capital() zaehlt den Sparplan seit E10-KAPITAL (29.07.) mit. Fuer Drawdown-Guard,
        Tagesverlust und Anzeige bleibt das so. Die Kaufgroesse darf ihn aber nicht mitzaehlen:
        v7 setzte am 15.10. dadurch 95 % der Handelskasse in eine einzige Muenze.
        Im Papiermodus ist das exakt Handelsgeld; im Live-Modus wirkt der Kapital-Deckel
        (_kapital_deckel) schon auf die Summe MIT Sparplan - dann ist der Wert eher zu klein, nie zu gross.
        """
        gesamt = self.get_total_capital()
        try:
            sparplan = float(self.get_btc_accumulator_value() or 0.0)
        except Exception:
            sparplan = 0.0
        return max(gesamt - max(sparplan, 0.0), 0.0)

    # ============================================================
    # POSITION SIZING - 100% prozentual
    # ============================================================
    def get_position_size(self, capital: Optional[float] = None) -> float:
        """Gibt empfohlene Position-Groesse in USDC zurueck.

        Berechnet aus aktivem Modus * aktuellem Kapital.
        - all_in:       95% des Kapitals
        - balanced:     30% des Kapitals
        - diversified:  10% des Kapitals
        """
        if capital is None:
            capital = self.get_total_capital()

        mode = self.config.get_active_mode()
        size = capital * (mode.position_size_pct / 100.0)
        return max(size, 5.0)  # Minimum 5$ damit Trades nicht zu klein werden

    def get_cash_reserve(self, capital: Optional[float] = None) -> float:
        """Gibt zu haltende Cash-Reserve in USDC zurueck.
        Prozentual aus aktivem Modus berechnet.
        """
        if capital is None:
            capital = self.get_total_capital()
        mode = self.config.get_active_mode()
        return capital * (mode.cash_reserve_pct / 100.0)

    def get_max_positions(self) -> int:
        """Max gleichzeitige Positionen aus aktivem Modus."""
        return self.config.get_active_mode().max_positions

    def get_max_coin_pct(self) -> float:
        """Max % des Kapitals in einem Coin (aus aktivem Modus)."""
        return self.config.get_active_mode().max_coin_pct

    def get_sector_limit_pct(self) -> float:
        """Max % des Kapitals in einem Sektor (aus aktivem Modus)."""
        return self.config.get_active_mode().sector_limit_pct

    # ============================================================
    # SL / TP - prozentual vom Einstiegspreis
    # ============================================================
    def get_stop_loss_price(self, entry_price: float, side: str = "BUY") -> float:
        """Stop-Loss als Preis (Entry - X%)."""
        sl_pct = self.config.risk.stop_loss_pct / 100.0
        if side == "BUY":
            return entry_price * (1 - sl_pct)
        else:
            return entry_price * (1 + sl_pct)

    def get_take_profit_price(self, entry_price: float, side: str = "BUY") -> float:
        """Take-Profit als Preis (Entry + X%). 0 = aus."""
        tp_pct = self.config.risk.take_profit_pct
        if tp_pct <= 0:
            return 0.0  # Kein TP
        if side == "BUY":
            return entry_price * (1 + tp_pct / 100.0)
        else:
            return entry_price * (1 - tp_pct / 100.0)

    def get_trailing_stop_pct(self) -> float:
        """Trailing-Stop in Prozent (z.B. 1.5)."""
        return self.config.risk.trailing_stop_pct

    # ============================================================
    # DAILY LOSS LIMIT (-10% pausiert Bot bis nächster Tag)
    # ============================================================
    def _update_day_start(self):
        """Aktualisiert Tagesstart-Kapital wenn neuer Tag."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._day_start_date:
            self._day_start_date = today
            self._day_start_capital = self.get_total_capital()
            self._daily_loss_active = False
            log.info("PORTFOLIO", f"📅 Neuer Tag - Startkapital: {self._day_start_capital:.2f}$")

    def check_daily_loss_limit(self) -> Dict:
        """Prueft ob Tagesverlust-Limit erreicht.

        Returns: {
            "limit_reached": bool,
            "loss_pct": float,
            "current": float,
            "start": float,
            "reason": str
        }
        """
        self._update_day_start()

        if self._day_start_capital <= 0:
            return {"limit_reached": False, "loss_pct": 0, "reason": "Kein Startkapital"}

        # get_total_capital() macht jetzt den max(balance, risk) Check selbst,
        # daher hier kein doppelter Workaround mehr noetig.
        current = self.get_total_capital()

        # Wenn current = 0 aber Positionen offen sind -> Sicherheits-Skip
        if current == 0 and len(getattr(self, '_risk_engine', {}) and self._risk_engine.open_positions or {}) > 0:
            log.warn("PORTFOLIO", "Capital=0 aber Positionen offen - Daily-Loss Check uebersprungen")
            return {"limit_reached": False, "loss_pct": 0, "reason": "Capital-Sync ausstehend"}

        loss_pct = ((self._day_start_capital - current) / self._day_start_capital) * 100

        max_loss_pct = self.config.risk.max_daily_loss_pct  # z.B. 10.0

        result = {
            "limit_reached": loss_pct >= max_loss_pct,
            "loss_pct": loss_pct,
            "current": current,
            "start": self._day_start_capital,
            "reason": "",
        }

        if result["limit_reached"]:
            result["reason"] = f"Tagesverlust {loss_pct:.1f}% >= Limit {max_loss_pct}%"
            if not self._daily_loss_active:
                self._daily_loss_active = True
                log.error("PORTFOLIO", f"🛑 DAILY LOSS LIMIT! "
                                       f"Verlust: {loss_pct:.2f}% (Limit: {max_loss_pct}%)")
                log.error("PORTFOLIO", f"   Start: {self._day_start_capital:.2f}$ -> "
                                       f"Aktuell: {current:.2f}$")

        return result

    def _p5_waechter(self):
        """[DAILY-LOSS P5] Neuer Waechter - eine Wahrheit, nur Kaufpause."""
        w = getattr(self, "_p5_dl", None)
        if w is None:
            from portfolio.daily_loss import DailyLoss
            w = DailyLoss(config=self.config,
                          equity_getter=self.get_total_capital)
            self._p5_dl = w
        return w

    def daily_loss_status(self) -> dict:
        """[DAILY-LOSS P5] Voller Tagesstand (fuer UI/Terminal-Tab)."""
        try:
            return self._p5_waechter().pruefe()
        except Exception as _e:
            log.warn("DAILY-LOSS", f"Statusabfrage fehlgeschlagen: {str(_e)[:60]}")
            return {}

    def is_paused_by_daily_loss(self) -> bool:
        """[DAILY-LOSS P5] Delegiert an das neue Modul.
        Modus 'schatten' -> immer False (nur Protokoll).
        Modus 'aktiv'    -> True bei Limit: NUR Kaufpause.
        Verkauft niemals etwas."""
        try:
            return self._p5_waechter().kaeufe_pausiert()
        except Exception as _e:
            log.warn("DAILY-LOSS", f"Pruefung fehlgeschlagen, keine Pause: {str(_e)[:60]}")
            return False

    def _alt_is_paused_by_daily_loss(self) -> bool:
        """True wenn Bot wegen Daily-Loss pausiert.
        DATENSAMMEL-PHASE: temporaer deaktiviert (immer False), damit der Bot
        durchlaeuft und ueber alle Marktlagen Daten sammelt. Einzel-Stop-Loss
        pro Position bleibt aktiv. VOR LIVE wieder scharf schalten (dann mit
        echtem Tagesverlust statt Abstand zum Startkapital)."""
        if getattr(self, "_daily_loss_disabled", True):
            return False
        self.check_daily_loss_limit()
        return self._daily_loss_active

    def reset_daily_loss(self):
        """Manuelles Reset des Daily-Loss-Schutzes (z.B. neuer Tag)."""
        self._day_start_capital = self.get_total_capital()
        self._day_start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._daily_loss_active = False
        log.info("PORTFOLIO", f"Daily-Loss reset. Startkapital: {self._day_start_capital:.2f}$")

    # ============================================================
    # LIVE-MODE SAFETY CHECKS
    # ============================================================
    def check_spread(self, ticker: dict) -> bool:
        """True wenn Spread im erlaubten Bereich. ticker = {bid, ask}."""
        try:
            bid = ticker.get("bid", 0)
            ask = ticker.get("ask", 0)
            if bid <= 0 or ask <= 0:
                return False
            spread_pct = ((ask - bid) / bid) * 100
            max_spread = self.config.risk.max_spread_pct
            if spread_pct > max_spread:
                log.warn("PORTFOLIO", f"Spread zu hoch: {spread_pct:.2f}% > {max_spread}%")
                return False
            return True
        except Exception:
            return True  # Bei Fehler: nicht blockieren

    def check_volume(self, ticker: dict) -> bool:
        """True wenn 24h-Volumen ausreichend."""
        try:
            volume_24h = ticker.get("quoteVolume", 0)  # USDC-Volumen
            min_vol = self.config.risk.min_volume_24h_usd
            if volume_24h < min_vol:
                log.warn("PORTFOLIO", f"Volumen zu niedrig: {volume_24h:,.0f}$ < {min_vol:,.0f}$")
                return False
            return True
        except Exception:
            return True

    # ============================================================
    # STATUS / DEBUGGING
    # ============================================================
    def get_status(self) -> Dict:
        """Status fuer Dashboard / Debugging."""
        capital = self.get_total_capital()
        mode = self.config.get_active_mode()
        return {
            "mode": mode.name,
            "current_capital": round(capital, 2),
            "day_start_capital": round(self._day_start_capital, 2),
            "position_size_usd": round(self.get_position_size(capital), 2),
            "cash_reserve_usd": round(self.get_cash_reserve(capital), 2),
            "max_positions": mode.max_positions,
            "position_size_pct": mode.position_size_pct,
            "cash_reserve_pct": mode.cash_reserve_pct,
            "sector_limit_pct": mode.sector_limit_pct,
            "max_coin_pct": mode.max_coin_pct,
            "stop_loss_pct": self.config.risk.stop_loss_pct,
            "take_profit_pct": self.config.risk.take_profit_pct,
            "trailing_stop_pct": self.config.risk.trailing_stop_pct,
            "daily_loss_active": self._daily_loss_active,
            "trading_mode": self.config.trading.mode,  # paper/live
        }
