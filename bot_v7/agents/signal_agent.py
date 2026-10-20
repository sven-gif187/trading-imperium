"""Trading Imperium V5 – Signal Agent: Generiert Trade-Signale."""
import pandas as pd
from typing import Optional, List, Dict
from core.events import DecisionIntent, Side, MarketSnapshot
from core.logger import log

STRATEGIES = {
    "RSI_OVERSOLD": {"name":"RSI Oversold","typ":"mean_reversion"},
    "BOLLINGER_BOUNCE": {"name":"Bollinger Bounce","typ":"mean_reversion"},
    "MACD_CROSS": {"name":"MACD Crossover","typ":"trend"},
    "EMA_TREND": {"name":"EMA Triple","typ":"trend"},
    "MOMENTUM_BREAKOUT": {"name":"Momentum Breakout","typ":"momentum"},
    "STOCHRSI_REVERSAL": {"name":"StochRSI Reversal","typ":"momentum"},
    "MULTI_SIGNAL": {"name":"Multi-Signal Pro","typ":"hybrid"},
    "FIBONACCI_SUPPORT": {"name":"Fibonacci Support","typ":"hybrid"},
    "DCA_FEAR_GREED": {"name":"Fear & Greed DCA","typ":"accumulation"},
}

class SignalAgent:
    """Analysiert MarketSnapshots und erzeugt DecisionIntents."""

    def __init__(self, config):
        self.config = config
        self.v4_ensemble = None
        self.v4_calibrator = None
        self.current_strategy = "MULTI_SIGNAL"
        self.performance = {}
        self.external_scores = {}  # Wird von app.py gesetzt (ensemble, vwap, orderbook...)
        # === GRID BOT HOOK ===
        # Wird von app.py via set_grid_bot() injiziert
        self.grid_bot = None
        # === FRAKTAL-TOR ===
        # Wird von app.py via set_fraktal_tor() injiziert. Bleibt None,
        # wenn der Schalter aus ist - dann verhaelt sich der Bot exakt
        # wie vorher.
        self.fraktal_tor = None

    def set_grid_bot(self, grid_bot):
        """Injiziert den Grid Bot Agent."""
        self.grid_bot = grid_bot

    def set_fraktal_tor(self, tor):
        """Injiziert das Fraktal-Tor (features/fraktal_tor.py)."""
        self.fraktal_tor = tor

    def set_external_scores(self, scores: dict):
        """Setzt externe Signal-Scores (Ensemble, VWAP, Orderbook etc)."""
        self.external_scores = scores

    def analyze(self, snapshot: MarketSnapshot, balance_usd: float = 0, fear_greed: int = 50) -> Optional[DecisionIntent]:
        """Analysiert einen Snapshot und gibt ggf. einen Kauf-Intent zurueck."""
        if not snapshot or not hasattr(snapshot, '_df'):
            return None

        df = snapshot._df
        if df is None or len(df) < 30:
            return None

        # === GRID BOT HOOK ===
        # Vor der Multi-Signal-Logik pruefen ob Grid greift.
        # Grid Bot prueft selbst (ADX, Bandbreite, Cooldown etc).
        # Bei keinem Grid-Signal: None -> faellt durch zur normalen Logik.
        if self.grid_bot is not None:
            try:
                # Check ob Coin schon eine Position hat (kein doppelter Grid-Buy)
                has_pos = False
                _re = getattr(self, "_risk_engine_ref", None)
                if _re is not None:
                    _p = _re.open_positions.get(snapshot.symbol, {})
                    has_pos = bool(_p.get("active") and _p.get("qty", 0) > 0)

                grid_intent = self.grid_bot.evaluate(
                    snapshot, balance_usd=balance_usd, has_position=has_pos)
                if grid_intent is not None:
                    return grid_intent
            except Exception as _e:
                log.warn("GRID", f"Grid-Eval Fehler: {_e}")

        ind = snapshot.indicators
        rsi = ind.get("rsi", 50)
        adx = ind.get("adx", 20)
        macd = ind.get("macd", 0)
        macd_sig = ind.get("macd_signal", 0)
        price = snapshot.close

        # Multi-Signal Scoring (wie V4)
        score = 0
        reasons = []

        # RSI Oversold
        if rsi < 30:
            score += 3; reasons.append(f"RSI stark oversold ({rsi:.0f})")
        elif rsi < 35:
            score += 2; reasons.append(f"RSI oversold ({rsi:.0f})")
        elif rsi < 45:
            score += 1; reasons.append(f"RSI niedrig ({rsi:.0f})")

        # MACD Cross
        if macd > macd_sig and macd < 0:
            score += 2; reasons.append("MACD bullish cross")
        elif macd > macd_sig:
            score += 1; reasons.append("MACD positiv")

        # EMA Trend
        ema20 = ind.get("ema20", 0)
        ema50 = ind.get("ema50", 0)
        if price > ema20 > ema50 and ema20 > 0:
            score += 1; reasons.append("EMA-Trend up")

        # ADX Trend-Staerke
        if adx > 25:
            score += 1; reasons.append(f"Starker Trend (ADX {adx:.0f})")

        # Fear & Greed (wie V4 - Haupttreiber!)
        if fear_greed < 15:
            score += 3; reasons.append(f"EXTREME FEAR ({fear_greed})")
        elif fear_greed < 25:
            score += 2; reasons.append(f"Extreme Fear ({fear_greed})")
        elif fear_greed < 35:
            score += 1; reasons.append(f"Fear ({fear_greed})")

        # Bollinger Band
        bbl = df.get("BBL_20_2.0")
        if bbl is not None and len(bbl) > 0:
            last_bbl = bbl.iloc[-1]
            if not pd.isna(last_bbl) and price < last_bbl and rsi < 40:
                score += 2; reasons.append("Unter Bollinger Band")

        # RSI Divergenz (Phase 1 Feature)
        if hasattr(snapshot, 'rsi_divergence') and snapshot.rsi_divergence == "BULLISH":
            score += 2; reasons.append("Bullische RSI-Divergenz!")

        # Volume Spike (wie V4 Momentum Breakout)
        if len(df) > 20:
            vol_avg = df["Volume"].tail(20).mean()
            vol_now = df["Volume"].iloc[-1]
            if vol_now > vol_avg * 2 and rsi < 60:
                score += 1; reasons.append(f"Volume-Spike ({vol_now/vol_avg:.1f}x)")

        # === ENSEMBLE: Externe Signale einbeziehen ===
        ext = self.external_scores
        if ext:
            ensemble_score = ext.get("ensemble", 0.5)
            if ensemble_score > 0.75:
                score += 2; reasons.append(f"Ensemble STARK bullisch ({ensemble_score:.2f})")
            elif ensemble_score > 0.65:
                score += 1; reasons.append(f"Ensemble bullisch ({ensemble_score:.2f})")

            vwap_bias = ext.get("vwap_bias", "NEUTRAL")
            if vwap_bias == "BULLISH":
                score += 1; reasons.append("Ueber VWAP")

            ob_score = ext.get("orderbook", 0)
            if ob_score > 0.15:
                score += 1; reasons.append(f"Orderbook Kaufdruck ({ob_score:+.2f})")

        # === V4-BRIDGE Score-Boost ===
        v4_strategy_used = None
        v4_calibrated = 0.0
        if self.v4_ensemble is not None and self.v4_calibrator is not None:
            try:
                v4_calibrated, v4_reason, v4_strategy_used = self.v4_ensemble.evaluate_buy(
                    df=df, price=price, fear_greed=fear_greed,
                    calibrator=self.v4_calibrator)
                if v4_calibrated >= 0.7:
                    score += 4
                    reasons.append(f'V4-{v4_strategy_used} STARK ({v4_calibrated:.2f})')
                elif v4_calibrated >= 0.5:
                    score += 3
                    reasons.append(f'V4-{v4_strategy_used} ({v4_calibrated:.2f})')
                elif v4_calibrated >= 0.3:
                    score += 2
                    reasons.append(f'V4-{v4_strategy_used} schwach')
            except Exception:
                pass

        # Minimum Score fuer Kauf
        #
        # [14.09.2026] Stand hier fest auf 3. Jetzt aus der Konfiguration
        # lesbar, Vorgabe bleibt 3 - der Papier-Bot handelt also unveraendert
        # weiter und Epoche E9 bleibt sauber.
        #
        # WARUM DAS EINSTELLBAR SEIN MUSS: Befund 103 hat am 11.09. an
        # 57 Verkaeufen gemessen, wo die Trennlinie liegt:
        #
        #     Score 3-6   n=23   -0,540 %   60,9 % Treffer
        #     Score 7-10  n=34   +0,468 %   79,4 % Treffer
        #
        # Ein Unterschied von 1,008 Prozentpunkten; im Zufallstest ueber
        # 20.000 Mischungen entsteht er nur in 1,18 % der Faelle von allein.
        # Bei einer Schwelle von 3 kauft der Bot also auch die Gruppe, die
        # nachweislich verliert.
        #
        # Die Schwelle 7 stammt aus denselben Daten, an denen sie gemessen
        # wurde - das ist Ueberanpassung, solange sie sich nicht vorwaerts
        # bestaetigt. Deshalb bleibt die Vorgabe bei 3 und die Live-Instanz
        # setzt sie bewusst hoeher: dort zaehlt echtes Geld, und die
        # Messung laeuft nebenan im Papier-Bot weiter.
        min_score = int(getattr(self.config.trading, "min_signal_score", 3) or 3)
        if score >= min_score and balance_usd > 10:
            # ========================================================
            # FRAKTAL-TOR  (14.09.2026)
            # ========================================================
            # Hier und nur hier greift Svens Verfahren in den Handel ein.
            #
            # Der Score oben sagt "die Lage ist guenstig". Er sagt NICHT,
            # dass der PREIS guenstig ist - im Gegenteil: MACD positiv,
            # EMA-Trend up, ADX hoch und ueber VWAP heissen zusammen,
            # dass der Kurs bereits gelaufen ist. Am 14.09. kam so
            # Score 9/10 zustande, und der Bot kaufte am Hoch.
            #
            # Das Tor darf nur ABLEHNEN, nie erlauben. Damit bleibt die
            # an 57 Verkaeufen gemessene Schwelle (Befund 103) das, was
            # sie war, und der Vergleich zum Papier-Bot haelt.
            if self.fraktal_tor is not None:
                nur_messen = bool(getattr(self.config.trading,
                                          "fraktal_tor_nur_messen", False))
                try:
                    urteil = self.fraktal_tor.pruefe(snapshot.symbol, price)
                except Exception as _fe:
                    # Kein stilles Scheitern (CLAUDE.md 7.4): Faellt das
                    # Tor aus, wird NICHT gekauft. Ein Tor, das bei
                    # Fehlern durchlaesst, ist kein Tor.
                    log.error("FRAKTAL", f"{snapshot.symbol}: Tor-Fehler, "
                                         f"Kauf abgelehnt: {str(_fe)[:120]}")
                    return None

                if not urteil["erlaubt"]:
                    if nur_messen:
                        log.info("FRAKTAL", f"{snapshot.symbol}: Tor wuerde "
                                            f"ablehnen (Score {score}) - "
                                            f"{urteil['grund']} [NUR MESSEN, "
                                            f"Kauf laeuft durch]")
                    else:
                        log.info("FRAKTAL", f"{snapshot.symbol}: Kauf "
                                            f"abgelehnt trotz Score {score} - "
                                            f"{urteil['grund']}")
                        return None
                else:
                    log.signal("FRAKTAL", f"{snapshot.symbol}: Einstiegspreis "
                                          f"bestaetigt - {urteil['grund']}")
                    reasons.append("Fraktal-Konfluenz")

            pos_size = balance_usd * (self.config.trading.position_size_pct / 100)
            confidence = min(score / 10, 1.0)

            intent = DecisionIntent(
                symbol=snapshot.symbol,
                side=Side.BUY,
                confidence=confidence,
                entry_price=price,
                amount_usd=pos_size,
                stop_loss=price * (1 - self.config.risk.stop_loss_pct / 100),
                trailing_stop_pct=self.config.risk.trailing_stop_pct,
                strategy_id=v4_strategy_used or self.current_strategy,
                strategy_name="Multi-Signal V5",
                entry_reason=" + ".join(reasons),
                score=score,
                agent_id="signal_agent",
            )
            log.signal("SIGNAL", f"{snapshot.symbol}: Score {score}/10 ({confidence:.0%}) -> BUY {pos_size:.2f}$ | {' + '.join(reasons)}")
            return intent

        return None

    def check_sell(self, snapshot: MarketSnapshot, entry_price: float, highest_price: float) -> Optional[DecisionIntent]:
        """Prüft ob eine Position verkauft werden soll."""
        if not snapshot:
            return None

        price = snapshot.close
        ind = snapshot.indicators
        rsi = ind.get("rsi", 50)

        if entry_price <= 0:
            return None

        pnl_pct = ((price / entry_price) - 1) * 100
        fall_from_high = ((highest_price - price) / highest_price * 100) if highest_price > 0 else 0

        reason = ""
        should_sell = False

        # [EXIT-EINHEIT 14.07.] Stop hier ist nur noch NOTAUS-NETZ:
        # Der Monitor (runtime/exit_monitor.py) ist die EINE Exit-Autoritaet
        # (phasen-angepasst + Per-Coin-Override aus risk/coin_stops.py).
        # Dieses Netz greift erst 0.5% HINTER dem effektiven Stop.
        # Wenn es feuert, hat der Monitor versagt -> Alarm im Verkaufsgrund.
        from risk.coin_stops import effective_stop
        _netz = effective_stop(snapshot.symbol, self.config.risk.stop_loss_pct) + 0.5
        if pnl_pct <= -_netz:
            should_sell = True
            reason = f"NOTAUS-NETZ Stop ({pnl_pct:.1f}% <= -{_netz:.1f}%) - MONITOR PRUEFEN!"

        # [EXIT-EINHEIT 14.07.] Agent-Trailing DEAKTIVIERT: Doppel-Pfad zum
        # Monitor-Stufen-Trailing (feuerte mit anderen Parametern zuerst,
        # umging E6-B und haette E7 ausgehebelt). Monitor trailt exklusiv.

        # RSI überkauft
        elif rsi > 80 and pnl_pct > 1.0:
            should_sell = True
            reason = f"RSI overbought ({rsi:.0f}), P&L {pnl_pct:+.1f}%"

        if should_sell:
            intent = DecisionIntent(
                symbol=snapshot.symbol,
                side=Side.SELL,
                confidence=0.8,
                entry_price=price,
                strategy_id=self.current_strategy,
                entry_reason=reason,
                agent_id="signal_agent",
            )
            log.signal("SIGNAL", f"{snapshot.symbol}: SELL -> {reason}")
            return intent

        return None

    def get_stats(self):
        return {"strategy": self.current_strategy, "performance": self.performance}
