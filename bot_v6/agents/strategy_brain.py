"""
Trading Imperium V5 – Strategy Brain (Das Gehirn)
Wählt die beste Strategie basierend auf Marktregime, Zyklusphase,
News-Sentiment und historischer Performance. Genau wie V4's OfflineKI,
aber als eigener Agent mit klarer Schnittstelle.
"""
from typing import Dict, List, Tuple, Optional
from core.events import MarketRegime, CyclePhase, MarketSnapshot
from core.logger import log


# ================================================================
# ALLE 12 STRATEGIEN (identisch mit V4)
# ================================================================
STRATEGIES = {
    "RSI_OVERSOLD": {
        "name": "RSI Oversold Bounce", "typ": "mean_reversion",
        "best_regime": ["RANGING", "UNKNOWN"],
        "desc": "Kauft wenn RSI unter 35 (ueberverkauft)",
    },
    "BOLLINGER_BOUNCE": {
        "name": "Bollinger Band Bounce", "typ": "mean_reversion",
        "best_regime": ["RANGING"],
        "desc": "Kauft wenn Preis unter unterem Bollinger Band",
    },
    "RSI_DIVERGENZ": {
        "name": "RSI Divergenz", "typ": "reversal",
        "best_regime": ["RANGING", "TRENDING"],
        "desc": "Erkennt Divergenz zwischen Preis und RSI",
    },
    "MACD_CROSS": {
        "name": "MACD Crossover", "typ": "trend_following",
        "best_regime": ["TRENDING"],
        "desc": "MACD kreuzt Signal-Linie nach oben",
    },
    "EMA_TREND": {
        "name": "EMA Triple Trend", "typ": "trend_following",
        "best_regime": ["TRENDING"],
        "desc": "Preis ueber EMA20 ueber EMA50",
    },
    "ICHIMOKU": {
        "name": "Ichimoku Cloud", "typ": "trend_following",
        "best_regime": ["TRENDING"],
        "desc": "Preis ueber der Ichimoku-Wolke",
    },
    "MOMENTUM_BREAKOUT": {
        "name": "Momentum Breakout", "typ": "momentum",
        "best_regime": ["TRENDING", "VOLATILE"],
        "desc": "Volume-Spike + neues Hoch",
    },
    "TSI": {
        "name": "TSI (True Strength)", "typ": "momentum",
        "best_regime": ["TRENDING", "UNKNOWN"],
        "desc": "True Strength Index Signal",
    },
    "STOCHRSI_REVERSAL": {
        "name": "StochRSI Reversal", "typ": "momentum",
        "best_regime": ["RANGING", "UNKNOWN"],
        "desc": "StochRSI im ueberverkauften Bereich",
    },
    "MULTI_SIGNAL": {
        "name": "Multi-Signal Pro", "typ": "hybrid",
        "best_regime": ["TRENDING", "RANGING", "UNKNOWN"],
        "desc": "Kombiniert mehrere Signale (Score-System)",
    },
    "FIBONACCI_SUPPORT": {
        "name": "Fibonacci Support", "typ": "hybrid",
        "best_regime": ["RANGING", "TRENDING"],
        "desc": "Kauf an Fibonacci-Support-Levels",
    },
    "DCA_FEAR_GREED": {
        "name": "Fear & Greed DCA", "typ": "accumulation",
        "best_regime": ["RANGING", "VOLATILE", "UNKNOWN"],
        "desc": "Kauft bei extremer Angst (F&G < 20)",
    },
    "GRID_BOT": {
        "name": "Grid Bot (Bollinger)", "typ": "grid",
        "best_regime": ["RANGING"],
        "desc": "Bollinger-Grid - kauft an unteren Stufen, verkauft via Trailing-Stop",
    },
}


class StrategyBrain:
    """Das Gehirn: Wählt die beste Strategie basierend auf Marktlage."""

    def __init__(self, config=None):
        self.current_strategy = "MULTI_SIGNAL"
        self.performance: Dict[str, Dict] = {}
        # === V4 BRAIN PERSISTENCE Auto-Load ===
        try:
            from models.brain_persistence import BrainPersistence
            loaded = BrainPersistence().load_performance()
            if loaded:
                self.performance = loaded
                from core.logger import log as _log
                _trades = sum(p.get("trades", 0) for p in loaded.values())
                _v6 = sum(p.get("v6_trades_added", 0) for p in loaded.values())
                _pnl = sum(p.get("total_pnl", 0) for p in loaded.values())
                _log.info("BRAIN", f"V4-Wissen geladen: {len(loaded)} Strategien, {_trades} Trades ({_v6} V6-Trades dazu), {_pnl:+.0f} EUR Lerngrundlage")
        except Exception as _e:
            try:
                from core.logger import log as _log
                _log.info("BRAIN", f"V4-Wissen Load-Fehler: {_e}")
            except Exception:
                pass
        self.reasoning_log: List[Dict] = []
        # === PHASE-MEMORY: Phasen-Gedaechtnis laden ===
        try:
            from features.phase_memory import PhaseMemory
            self.phase_memory = PhaseMemory()
            log.info("BRAIN", "Phase-Memory aktiv (lernt aus Impact-Journal)")
        except Exception:
            self.phase_memory = None

    def select_best(self, regime: str = "UNKNOWN", cycle_phase: str = "",
                    fear_greed: int = 50, news_sentiment: float = 0.5,
                    capitol_signal: float = 0.5, df=None) -> Tuple[str, str]:
        """
        Wählt die beste Strategie. Returns (strategy_id, reasoning).
        """
        scores = {}
        _phase_info = {}  # PHASE-MEMORY: sammelt Phasen-Anpassungen

        for sid, s in STRATEGIES.items():
            score = 0.0

            # 1. Regime-Match (0-3 Punkte)
            if regime in s.get("best_regime", []):
                score += 3.0
            elif regime == "UNKNOWN":
                score += 1.0

            # 2. Zyklusphase (0-2 Punkte)
            if cycle_phase in ("DEEP_BEAR", "CAPITULATION"):
                if s["typ"] == "accumulation":
                    score += 2.0  # DCA dominiert im Bärenmarkt
                elif s["typ"] in ("trend_following", "momentum"):
                    score -= 1.0  # Trend-Strategien schlecht im Bärenmarkt
            elif cycle_phase in ("ACCUMULATION",):
                if s["typ"] in ("mean_reversion", "hybrid"):
                    score += 1.5
            elif cycle_phase == "EUPHORIA":
                if s["typ"] == "momentum":
                    score += 1.0  # Momentum in Euphorie
                elif s["typ"] == "accumulation":
                    score -= 1.0

            # 3. Fear & Greed (0-2 Punkte)
            if fear_greed < 20:
                if sid == "DCA_FEAR_GREED":
                    score += 2.0
                elif s["typ"] == "mean_reversion":
                    score += 1.0
            elif fear_greed > 75:
                if s["typ"] == "momentum":
                    score += 0.5

            # === STEP 2: BOTTOM BONUS ===
            # Wenn Bottom-Signal aktiv (extra Parameter via select_best Kontext),
            # DCA bekommt MASSIVEN Bonus - auch in TRENDING_DOWN!
            if hasattr(self, "_bottom_signal_active") and self._bottom_signal_active:
                if sid == "DCA_FEAR_GREED":
                    score += 3.0  # TUNING: war +5, jetzt +3 fuer mehr Strategie-Vielfalt
                elif s["typ"] in ("trend_following", "momentum"):
                    score -= 1.5  # TUNING: war -2, jetzt -1.5 (mildere Strafe)

            # 4. Historische Performance (0-2 Punkte)
            perf = self.performance.get(sid, {})
            wr = perf.get("win_rate", 0)
            trades = perf.get("trades", 0)
            if trades >= 3 and wr > 60:
                score += 2.0
            elif trades >= 3 and wr > 40:
                score += 1.0
            elif trades >= 3 and wr < 30:
                score -= 1.0

            # === PHASE-MEMORY: Phasen-spezifische Performance ===
            if getattr(self, "phase_memory", None) is not None:
                try:
                    _padj, _pinf = self.phase_memory.get_score_adjustment(
                        regime, cycle_phase, sid)
                    if _padj != 0:
                        score += _padj
                        _phase_info[sid] = (_padj, _pinf)
                except Exception:
                    pass

            # 4b. GRID-Bot Bonus: idealerweise in Seitwaerts + neutralem F&G
            # STEP 1: Bonus von +2 auf +4 erhoeht damit Grid wirklich gewinnt
            if sid == "GRID_BOT":
                if regime == "RANGING" and 30 <= fear_greed <= 70:
                    score += 4.0  # STEP 1 (war +2)
                elif regime != "RANGING":
                    score -= 2.0  # Grid taugt nicht im Trend

            # 5. News-Sentiment (0-1 Punkt)
            if news_sentiment < 0.3 and s["typ"] == "accumulation":
                score += 1.0
            elif news_sentiment > 0.7 and s["typ"] == "trend_following":
                score += 0.5

            # 6. Capitol Trades Signal (Politiker-Insider, 0-1.5 Punkte)
            if capitol_signal > 0.65 and s["typ"] in ("trend_following", "momentum"):
                score += 1.5  # Politiker kaufen -> Trend/Momentum bevorzugen
            elif capitol_signal < 0.35 and s["typ"] == "accumulation":
                score += 1.0  # Politiker verkaufen -> vorsichtig, DCA

            scores[sid] = max(score, 0)

        # Beste Strategie wählen
        best_id = max(scores, key=scores.get)
        best_score = scores[best_id]
        best_name = STRATEGIES[best_id]["name"]

        # === PHASE-MEMORY: Logging ===
        if best_id in _phase_info:
            _padj, _pinf = _phase_info[best_id]
            if _padj > 0:
                log.info("PHASE-MEMORY",
                         f"({_pinf.get('win_rate', 0):.0f}%): {cycle_phase} + {regime} "
                         f"-> {best_name} bevorzugt (+{_padj:.0f})")
        for _sid, (_padj, _pinf) in _phase_info.items():
            if _padj <= -5:
                log.info("PHASE-MEMORY",
                         f"{STRATEGIES.get(_sid, {}).get('name', _sid)} in {cycle_phase} "
                         f"gesperrt ({_pinf.get('win_rate', 0):.0f}% Win-Rate)")

        # Zweitbeste für Reasoning
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        second = sorted_scores[1] if len(sorted_scores) > 1 else (best_id, 0)
        second_name = STRATEGIES.get(second[0], {}).get("name", "?")

        # Reasoning
        regime_text = {
            "TRENDING": "Trendmarkt", "RANGING": "Seitwärtsmarkt",
            "VOLATILE": "Volatiler Markt", "UNKNOWN": "Übergangsphase"
        }.get(regime, regime)

        reasoning = (f"Strategie '{best_name}' gewählt. "
                    f"Regime: {regime_text} | Zyklus: {cycle_phase} | F&G: {fear_greed}. "
                    f"Zweitbeste: {second_name} (Score: {second[1]:.1f})")

        self.current_strategy = best_id
        self.reasoning_log.append({
            "strategy": best_id, "score": best_score,
            "regime": regime, "reasoning": reasoning,
        })
        if len(self.reasoning_log) > 100:
            self.reasoning_log = self.reasoning_log[-100:]

        log.info("BRAIN", reasoning)
        return best_id, reasoning

    def record_trade_result_with_context(self, strategy_id: str, pnl: float,
                                          score: int = 0, market_regime: str = "UNKNOWN",
                                          fear_greed: int = 50):
        """Erweitertes Tracking mit Kontext (Punkt 5).
        Speichert nicht nur PnL sondern auch unter welchen Bedingungen.
        """
        # Standard Tracking
        self.record_trade_result(strategy_id, pnl)

        # Kontext-Tracking
        if not hasattr(self, "context_log"):
            self.context_log = []
        self.context_log.append({
            "strategy": strategy_id,
            "pnl": pnl,
            "score": score,
            "market_regime": market_regime,
            "fear_greed": fear_greed,
            "won": pnl > 0,
        })
        # Max 500 Eintraege
        if len(self.context_log) > 500:
            self.context_log = self.context_log[-500:]

        # Auch speichern via Persistence (falls vorhanden)
        try:
            from models.brain_persistence import BrainPersistence
            bp = BrainPersistence()
            if hasattr(bp, "save_context_log"):
                bp.save_context_log(self.context_log)
        except Exception:
            pass

    def get_strategy_context_stats(self, strategy_id: str) -> dict:
        """Gibt detaillierte Stats fuer eine Strategie unter welchen Bedingungen sie funktioniert."""
        if not hasattr(self, "context_log"):
            return {}
        entries = [e for e in self.context_log if e["strategy"] == strategy_id]
        if not entries:
            return {}

        # Aufgesplittet nach Markt-Regime
        by_regime = {}
        for e in entries:
            r = e["market_regime"]
            if r not in by_regime:
                by_regime[r] = {"trades": 0, "wins": 0, "pnl": 0}
            by_regime[r]["trades"] += 1
            if e["won"]:
                by_regime[r]["wins"] += 1
            by_regime[r]["pnl"] += e["pnl"]

        return {
            "total_context_trades": len(entries),
            "by_regime": by_regime,
            "best_score_range": _find_best_score_range(entries),
        }

    def record_trade_result(self, strategy_id: str, pnl: float,
                            quelle: str = "", symbol: str = "",
                            position_id: str = ""):
        """Zeichnet ein Trade-Ergebnis auf für Performance-Tracking.

        [SAUBERER V6-ZAEHLER 11.08.2026 - Variante C]
        Diese Methode ist der einzige gemeinsame Punkt beider Verkaufswege
        (app.py:1655 ueber ORDER_FILLED und runtime/exit_monitor.py:435
        direkt). Deshalb haengt der neue, V4-freie Zaehler genau hier -
        einmal eingehaengt, deckt er beide Wege ab.

        Die drei neuen Parameter haben Vorgabewerte, damit alle bestehenden
        Aufrufe unveraendert gueltig bleiben.
        """
        if strategy_id not in self.performance:
            self.performance[strategy_id] = {"trades": 0, "wins": 0, "total_pnl": 0, "win_rate": 0}
        p = self.performance[strategy_id]
        p["trades"] += 1
        if pnl > 0:
            p["wins"] += 1
        p["total_pnl"] += pnl
        p["win_rate"] = (p["wins"] / p["trades"] * 100) if p["trades"] > 0 else 0
        p["v6_trades_added"] = p.get("v6_trades_added", 0) + 1
        try:
            from models.brain_persistence import BrainPersistence
            BrainPersistence().save_performance(self.performance)
        except Exception:
            pass

        # --- Sauberer V6-Zaehler, getrennte Datei, kein Einfluss auf den
        # Score. Vollstaendig gekapselt: faellt er aus, bleibt oben alles
        # unveraendert. Siehe models/lern_journal_v6.py fuer die Begruendung.
        try:
            from models.lern_journal_v6 import hole_journal
            _j = hole_journal()
            if _j is not None:
                _j.buchen(strategy_id, pnl, quelle=quelle, symbol=symbol,
                          position_id=position_id)
        except Exception:
            pass

    def get_ranking(self) -> List[Dict]:
        """Gibt Strategie-Ranking zurück."""
        ranking = []
        for sid, s in STRATEGIES.items():
            perf = self.performance.get(sid, {})
            ranking.append({
                "id": sid, "name": s["name"], "typ": s["typ"],
                "trades": perf.get("trades", 0), "win_rate": perf.get("win_rate", 0),
                "total_pnl": perf.get("total_pnl", 0),
            })
        return sorted(ranking, key=lambda x: x["total_pnl"], reverse=True)

    def set_bottom_signal(self, active: bool):
        """STEP 2: Setzt Bottom-Signal aus BottomDetector."""
        old = getattr(self, "_bottom_signal_active", False)
        self._bottom_signal_active = active
        if active and not old:
            log.info("BRAIN", "Bottom-Signal AKTIV - DCA wird priorisiert")
        elif not active and old:
            log.info("BRAIN", "Bottom-Signal beendet - normales Brain")

    def get_status(self) -> Dict:
        return {
            "current": self.current_strategy,
            "name": STRATEGIES.get(self.current_strategy, {}).get("name", "?"),
            "strategies_count": len(STRATEGIES),
            "with_data": sum(1 for p in self.performance.values() if p.get("trades", 0) > 0),
        }
