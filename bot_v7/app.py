"""
⚡ TRADING IMPERIUM V7 – Multi-Agent Trading System
====================================================
Modulare KI-Trading-Architektur mit:
- Event-Bus für Kommunikation zwischen Agents
- Risk-Agent mit Veto-Recht vor jeder Order
- Execution-Engine mit Retry, Circuit Breaker, Idempotenz
- ML Signal Agent + LLM Context Agent
- Persistenter State Store (überlebt Abstürze)
- Strukturiertes Logging mit Trace-IDs

Starten: python app.py
Dashboard: http://localhost:5000

V4 läuft parallel weiter für Paper Trading!
"""
import sys
import shutil
import os
import time
import threading
import signal
import traceback
from datetime import datetime, timezone

# Projekt-Root zum Python-Path hinzufuegen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === ALLE IMPORTS MIT FEHLERBEHANDLUNG ===
try:
    from config.settings import AppConfig, DATA_DIR
    from core.bus import EventBus
    from core.state_store import StateStore, TradeJournal
    from core.logger import log
    from core.scheduler import Scheduler
    from core.health import HealthMonitor
    from core.events import MarketSnapshot, DecisionIntent, ExecutionResult, Side, MarketRegime
    from core.events import EVENT_MARKET_UPDATE, EVENT_SIGNAL, EVENT_RISK_APPROVED, EVENT_RISK_REJECTED
    from core.events import EVENT_ERROR, EVENT_KILL_SWITCH, EVENT_ORDER_FILLED, EVENT_ORDER_FILLED
    from execution.engine import ExecutionEngine
    from risk.engine import RiskEngine
    from data.market_data import DataAgent
    from agents.signal_agent import SignalAgent
    from features.doc_agent import DocAgent
    from features.tickets_watcher import TicketsWatcher
    from features.impact_journal import ImpactJournal
    from features.bottom_detection import BottomDetector
    from portfolio.rebalancer import PortfolioRebalancer
    from features.bottom_detection import BottomDetector
    from portfolio.rebalancer import PortfolioRebalancer
    from agents.grid_bot import GridBot
    from agents.context_agent import LLMContextAgent
    from agents.strategy_brain import StrategyBrain
    from agents.cycle_theory import CycleTheory
    from agents.btc_accumulator import BTCAccumulator
    # === V4 BRIDGE (lernt aus echter V4-Performance) ===
    from agents.v4_strategies import V4StrategyEnsemble
    from models.v4_calibrator import V4Calibrator
    from models.brain_persistence import BrainPersistence
    from live.live_runner import LiveRunner
    from live.paper_runner import PaperRunner
    from live.state_recovery import StateRecovery
    from live.watchdog import Watchdog
    from features.indicators import calc_all_indicators
    from data.feature_store import FeatureStore
    from data.capitol_trades import CapitolTradesProvider
    from data.funding_rates import FundingRateMonitor
    from data.whale_alerts import WhaleAlertProvider
    from features.rsi_divergence import RSIDivergenceDetector
    from features.multi_timeframe import MultiTimeframeAggregator
    from features.regime_detection import RegimeDetector
    from data.reddit_sentiment import RedditSentimentProvider
    from data.sentiment_data import SentimentProvider
    from data.onchain_analytics import OnChainAnalytics
    from features.vwap_agent import VWAPAgent
    from execution.twap_executor import TWAPExecutor
    from agents.smart_entry import SmartEntryAgent
    from models.rl_feedback import RLFeedbackAgent
    from models.ensemble_signal import EnsembleSignal
    from agents.llm_local import LocalLLMAgent
    from agents.grid_trader import GridTrader
    from agents.dca_advanced import AdvancedDCA
    from risk.reentry_guard import ReentryGuard      # [E9-CHURN 29.07.]
    from data.orderbook_depth import OrderBookAnalyzer
    from config.versioning import ConfigVersioning
    from agents.arbitrage_agent import ArbitrageAgent
    from risk.adaptive_sizing import AdaptivePositionSizer
    from execution.multi_exchange import MultiExchangeManager
    from backtest.optimizer import BacktestOptimizer
    from ui.dashboard import WebDashboard
    from ui.ngrok_dashboard import NgrokDashboard
    from core.auto_restart import AutoRestartMonitor
    from data.websocket_stream import BinanceWebSocket
    from models.xgboost_model import XGBoostSignalModel
    from models.signal_model import SignalModel
    from models.train_pipeline import TrainPipeline
    from portfolio.agent import PortfolioAgent
    from reports.telegram import TelegramReporter
    # [GEFUNDENE-PROBLEME #14, 13.08.2026] WebhookServer-Import entfernt -
    # der TradingView-Webhook auf Port 5051 ist stillgelegt. Begruendung
    # im Kopf von ui/webhook_server.py und bei self.webhook = None.
    from models.auto_retrain import AutoRetrainer
    from execution.futures_trader import FuturesTrader
    from backtest.hyperopt import HyperOptimizer
    from agents.strategy_export import StrategyExporter
    from data.nupl_monitor import NUPLMonitor
    from data.dxy_monitor import DXYMonitor
    from reports.equity_tracker import EquityTracker
    from models.meta_voting import MetaVotingSystem
    from live.shadow_mode import ShadowModeManager
    from data.nupl_monitor import NUPLMonitor
except ImportError as e:
    print("=" * 60)
    print(f"IMPORT-FEHLER: {e}")
    print("=" * 60)
    print("\nFehlende Bibliothek installieren:")
    missing = str(e).replace("No module named ", "").strip("'\"")
    print(f"  pip install {missing}")
    print("\nAlle Befehle:")
    print("  pip install ccxt pandas pandas_ta numpy")
    print("  pip install customtkinter matplotlib mplfinance")
    print("  pip install psutil requests scikit-learn")
    print("  pip install websocket-client praw beautifulsoup4")
    traceback.print_exc()
    input("\nDruecke Enter zum Beenden...")
    sys.exit(1)
except Exception as e:
    print("=" * 60)
    print(f"FEHLER beim Laden: {e}")
    print("=" * 60)
    traceback.print_exc()
    # [13.08.2026] Hier stand "Loesung: Loesche den Ordner 'data_store'
    # und starte neu" - als pauschaler Rat fuer JEDEN Fehler beim Laden
    # der Module. Das ist an dieser Stelle besonders unsinnig: Wenn ein
    # IMPORT scheitert, hat das mit den gespeicherten Daten nichts zu tun.
    # data_store enthaelt Positionen, Kontostand, Journal und
    # telemetrie.db mit ueber 200.000 Zeilen - der Rat haette den
    # gesamten Bestand vernichtet, ohne das Problem zu beheben.
    # Dieselbe Zeile stand ein zweites Mal im __main__-Block, siehe dort.
    print("\nDas ist ein Fehler beim LADEN der Module - mit den")
    print("gespeicherten Daten hat er nichts zu tun.")
    print("Zuerst die Meldung oben lesen: meist ein fehlendes Paket")
    print("(pip install ...) oder ein Tippfehler im Code.")
    print("Den Ordner 'data_store' NICHT loeschen - darin liegen")
    print("Positionen, Kontostand, Journal und die Telemetrie-Datenbank.")
    input("\nDruecke Enter zum Beenden...")
    sys.exit(1)


# [GEFUNDENE-PROBLEME #4, 11.08.2026] Abstand zwischen zwei ML-Notizen je
# Coin. 3600 s = eine Kerze im 1h-Zeitrahmen. Siehe _ml_notizbuch().
ML_NOTIZ_ABSTAND_SEC = 3600


class TradingImperiumV6:
    """Haupt-Anwendung – verbindet alle Module miteinander."""

    def __init__(self):
        print("=" * 60)
        print("⚡ TRADING IMPERIUM V7 – Multi-Agent Trading System")
        print("=" * 60)

        # 1. Konfiguration laden
        self.config = AppConfig.load()
        log.info("APP", f"Konfiguration geladen (Modus: {self.config.trading.mode})")
        log.info("APP", f"Daten-Verzeichnis: {DATA_DIR}")
        log.info("APP", f"Coins: {len(self.config.trading.coins)} ({self.config.trading.coins[0]}...)")

        # 2. Core-Systeme initialisieren
        self._coin_modes = {}  # Per-Coin Modus: SL, HOLD, TP
        self._last_latency = 0  # Letzte Exchange-Latenz in ms
        self._log_buffer = []  # Log-Buffer fuer Export
        self._recent_buys = {}  # coin -> timestamp (verhindert Doppelkaeufe)
        self._trade_lock = threading.Lock()  # Verhindert gleichzeitige Trades
        self.bus = EventBus()
        self.state = StateStore("bot_state")
        self.journal = TradeJournal("trades_v5")
        # [FIX 05.08.2026] Zwei Felder, die forschung.db/trades_journal
        # vorsieht und die bisher niemand erzeugt hat.
        self._cycle_id = 0          # zaehlt je Snapshot-Durchlauf hoch
        self._spread_cache = {}     # coin -> spread_pct aus dem Orderbuch
        self.health = HealthMonitor()
        self.scheduler = Scheduler()

        # 3. Agents initialisieren
        self.data_agent = DataAgent(self.config)
        self.signal_agent = SignalAgent(self.config)
        # === DOC-AGENT ===
        try:
            self.doc_agent = DocAgent()
            self.doc_agent.on_start(
                mode=self.config.trading.mode,
                balance=self.config.trading.initial_paper_balance)
            log.info("APP", "DocAgent initialisiert (schreibt ins ENTWICKLERHANDBUCH.md)")
        except Exception as _e:
            log.warn("APP", f"DocAgent Init-Fehler: {_e}")
            self.doc_agent = None
        # === TICKETS-WATCHER ===
        try:
            self.tickets_watcher = TicketsWatcher(self.doc_agent)
            log.info("APP", "TicketsWatcher initialisiert (tickets.txt wird alle 30s gefressen)")
        except Exception as _e:
            log.warn("APP", f"TicketsWatcher Init-Fehler: {_e}")
            self.tickets_watcher = None
        # === IMPACT-JOURNAL ===
        try:
            self.impact_journal = ImpactJournal()
            log.info("APP", "ImpactJournal initialisiert (Trade-Begruendungen)")
        except Exception as _e:
            log.warn("APP", f"ImpactJournal Init-Fehler: {_e}")
            self.impact_journal = None

        # === SPLIT-1: Reporting-Delegat (runtime/reporting.py) ===
        try:
            from runtime.reporting import Reporting
            self.reporting = Reporting(self)
            log.info("APP", "Reporting-Delegat aktiv (Split Schritt 1)")
        except Exception as _rep_e:
            self.reporting = None
            log.warn("APP", f"Reporting-Delegat fehlt: {str(_rep_e)[:60]}")

        # ================================================================
        # SICHERHEITSBAUTEILE - Startabbruch statt Weiterlaufen
        # [13.08.2026, MASTERPROMPT.md Abschnitt 3.5 "Kein stilles
        #  Scheitern": CRITICAL heisst Handel blockieren, nicht warnen.]
        #
        # Beide Bauteile wurden bisher nur geloggt, wenn sie fehlten - und
        # der Bot lief weiter. Beim Exit-Monitor bedeutete das: Handel ganz
        # OHNE Stop-Loss-Ueberwachung, erkennbar nur an einer einzigen
        # Zeile im Log, die niemand liest. _sl_tp_monitor() loggte dann
        # bei JEDEM Durchlauf "STOP-PRUEFUNG UEBERSPRUNGEN" und kehrte
        # zurueck - alle 30 Sekunden, folgenlos.
        #
        # Jetzt: Wer ohne diese Bauteile startet, startet gar nicht.
        # Lieber kein Handel als Handel ohne Sicherung.
        # ================================================================
        from core.exceptions import SicherheitsbauteilFehlt

        # SPLIT-2: State-Delegat (runtime/state_manager.py)
        try:
            from runtime.state_manager import StateManager
            self.state_manager = StateManager(self)
            log.info("APP", "State-Delegat aktiv (Split Schritt 2)")
        except Exception as _sm_e:
            self.state_manager = None
            log.error("APP", f"State-Delegat FEHLT - Startabbruch: {str(_sm_e)[:80]}")
            raise SicherheitsbauteilFehlt(
                bauteil="StateManager (runtime/state_manager.py)",
                ursache=f"{type(_sm_e).__name__}: {str(_sm_e)[:120]}",
                folge="Positionen und Kontostand wuerden nicht mehr "
                      "gespeichert; nach dem naechsten Neustart waere der "
                      "Zustand still veraltet oder verloren.") from _sm_e

        # SPLIT-3: Exit-Monitor-Delegat (runtime/exit_monitor.py)
        try:
            from runtime.exit_monitor import ExitMonitor
            self.exit_monitor = ExitMonitor(self)
            log.info("APP", "Exit-Monitor-Delegat aktiv (Split Schritt 3)")
        except Exception as _em_e:
            self.exit_monitor = None
            log.error("APP", f"Exit-Monitor FEHLT - Startabbruch: {str(_em_e)[:80]}")
            raise SicherheitsbauteilFehlt(
                bauteil="ExitMonitor (runtime/exit_monitor.py)",
                ursache=f"{type(_em_e).__name__}: {str(_em_e)[:120]}",
                folge="Kein Stop-Loss, kein Take-Profit, kein Trailing-Stop "
                      "und kein Trend-Ausstieg - offene Positionen liefen "
                      "voellig unbewacht.") from _em_e
        # === STEP 2: BOTTOM DETECTOR ===
        try:
            self.bottom_detector = BottomDetector(self.config)
            log.info("APP", "Bottom Detector initialisiert (F&G + Cycle + RSI)")
        except Exception as _e:
            log.warn("APP", f"Bottom Detector Init-Fehler: {_e}")
            self.bottom_detector = None
        # === STEP 2: PORTFOLIO REBALANCER (default OFF + dry-run) ===
        try:
            self.portfolio_rebalancer = PortfolioRebalancer(
                self.config, enabled=False, dry_run=True, threshold_pct=5.0)
            log.info("APP", "PortfolioRebalancer initialisiert (DISABLED, dry-run)")
        except Exception as _e:
            log.warn("APP", f"PortfolioRebalancer Init-Fehler: {_e}")
            self.portfolio_rebalancer = None
        # === STEP 2: BOTTOM + REBALANCER ===
        try:
            self.bottom_detector = BottomDetector(self.config)
            log.info("APP", "Bottom Detector initialisiert (F&G + Cycle + RSI)")
        except Exception as _e:
            log.warn("APP", f"Bottom Detector Init-Fehler: {_e}")
            self.bottom_detector = None
        try:
            # Default: DISABLED + DRY-RUN! Sicher!
            self.rebalancer = PortfolioRebalancer(
                self.config, enabled=False, dry_run=True, threshold_pct=5.0)
            log.info("APP", "Rebalancer initialisiert (DISABLED, dry-run)")
        except Exception as _e:
            log.warn("APP", f"Rebalancer Init-Fehler: {_e}")
            self.rebalancer = None
        # === GRID BOT ===
        # [E11-GRID 29.07.2026] Ueber config.trading.grid_enabled schaltbar.
        # ABGESCHALTET waehrend des Messfensters fuer die Live-Freigabe.
        # Grund: der Grid ist ein ZWEITER Einstiegspfad neben DCA_FEAR_GREED
        # (am 29.07. hat er ATOM gekauft). Laeuft er mit, misst das Gate eine
        # Mischung aus zwei Strategien in einem Topf, und am Ende ist nicht
        # zu trennen, welche den Erwartungswert traegt. Er ist NICHT als
        # schlecht bewertet - nur ungeprueft, und Messung braucht eine
        # Variable, nicht zwei.
        # WIEDER EINSCHALTEN: grid_enabled auf true in data_store/config.json,
        # dann bewusst als eigenes Messfenster fahren. Siehe Ticket E11-GRID.
        self.grid_bot = None
        if getattr(self.config.trading, "grid_enabled", False):
            try:
                self.grid_bot = GridBot(self.config)
                self.signal_agent.set_grid_bot(self.grid_bot)
                # Risk-Engine-Ref geben (fuer has_position Check)
                self.signal_agent._risk_engine_ref = self.risk_engine if hasattr(self, "risk_engine") else None
                log.info("APP", "Grid Bot initialisiert (Bollinger 8 Stufen, max 4 Coins)")
            except Exception as _e:
                log.warn("APP", f"Grid Bot Init-Fehler: {_e}")
        else:
            self.signal_agent._risk_engine_ref = self.risk_engine if hasattr(self, "risk_engine") else None
            log.warn("APP", "Grid Bot ABGESCHALTET (config.trading.grid_enabled=false) - "
                            "sauberes Messfenster fuer die Live-Freigabe")

        # === FRAKTAL-TOR (14.09.2026) ===
        # Svens Verfahren als Einstiegsfilter. Begruendung in
        # features/fraktal_tor.py, Schalter in config/settings.py.
        # Ohne Schalter wird es gar nicht erst erzeugt - dann verhaelt
        # sich der Bot exakt wie vorher.
        self.fraktal_tor = None
        if getattr(self.config.trading, "fraktal_tor_aktiv", False):
            try:
                from features.fraktal_tor import FraktalTor
                self.fraktal_tor = FraktalTor(self.data_agent, self.config)
                self.signal_agent.set_fraktal_tor(self.fraktal_tor)
                _modus = ("SCHATTEN (misst nur, haelt nichts auf)"
                          if getattr(self.config.trading,
                                     "fraktal_tor_nur_messen", False)
                          else "SCHARF (lehnt Kaeufe ab)")
                log.info("APP", f"Fraktal-Tor aktiv - {_modus}. "
                                f"Gekauft wird nur noch in Konfluenzzonen.")
            except Exception as _e:
                # Kein stilles Scheitern: Wenn das Tor angefordert war,
                # aber nicht gebaut werden konnte, muss das laut sein.
                # Sonst handelt der Bot nach Trendfolge weiter und
                # niemand merkt es (genau der Fall vom 14.09.).
                log.error("APP", f"FRAKTAL-TOR ANGEFORDERT, ABER NICHT "
                                 f"GEBAUT: {_e} - der Bot kauft weiter nach "
                                 f"Trendfolge!")
        else:
            log.warn("APP", "Fraktal-Tor AUS (config.trading.fraktal_tor_aktiv"
                            "=false) - Einstieg allein nach Score")
        # [FIX 04.08.2026] Der V4-Bridge-Block stand hier und begann mit
        # 'if hasattr(self, "v4_ensemble")'. self.v4_ensemble wird aber erst
        # weiter unten (:304) erzeugt - die Bedingung war in derselben
        # __init__ IMMER False, der gesamte Block wurde nie ausgefuehrt.
        # Folge: signal_agent.v4_ensemble und .v4_calibrator blieben None,
        # agents/signal_agent.py:151 war nie erfuellt, die V4-Bridge lief im
        # Signalpfad NIE. Deshalb trugen alle 523 BUYs im Journal
        # DCA_FEAR_GREED - 'strategy_id = v4_strategy_used or
        # self.current_strategy' (:182) fiel immer auf den Fallback zurueck.
        # Laufzeitbeleg vor dem Fix: 81 BUY-Signale nach dem Neustart,
        # KEINE einzige mit einem 'V4-...'-Grund.
        # Der Block ist jetzt nach die Erzeugung von strategy_brain (:291),
        # v4_ensemble (:304) und v4_calibrator (:306/312) verschoben.
        self.risk_engine = RiskEngine(self.config)
        # Grid Bot: Risk-Engine-Ref jetzt setzen
        if hasattr(self, 'signal_agent') and self.signal_agent:
            self.signal_agent._risk_engine_ref = self.risk_engine
        self.execution = ExecutionEngine(self.config)
        self.context_agent = LLMContextAgent(self.config)
        self.strategy_brain = StrategyBrain(self.config)
        self.cycle_theory = CycleTheory()
        self.btc_accumulator = BTCAccumulator(self.config)

        # === BALANCE REPORTER (zeigt echtes Vermoegen alle 30s) ===
        try:
            from core.balance_reporter import BalanceReporter
            self.balance_reporter = BalanceReporter(self, interval_sec=30)
        except Exception as _e:
            log.info('APP', f'BalanceReporter Init-Fehler: {_e}')
            self.balance_reporter = None

        # === V4 BRIDGE: V6 lernt aus echten V4-Trades ===
        self.v4_ensemble = V4StrategyEnsemble()
        try:
            self.v4_calibrator = V4Calibrator.load('v4_data/strategy_stats.json')
            top3 = [s for s, w in self.v4_calibrator.get_ranking()[:3]]
            log.info('APP', f'V4-Bridge aktiv: {len(self.v4_calibrator.weights)} Strategien kalibriert')
            log.info('APP', f'V4 Top-3: {top3}')
        except Exception as _e:
            log.info('APP', f'V4-Bridge: kein Calibrator-Cache ({_e})')
            self.v4_calibrator = V4Calibrator(stats={})

        # === V4-BRIDGE: Brain-Persistence Loader ===
        # [VERSCHOBEN 04.08.2026 von :270, siehe Begruendung dort]
        # Steht jetzt NACH strategy_brain (:291), v4_ensemble (:304) und
        # v4_calibrator (:306/312) - alle drei werden hier gebraucht.
        self.brain_persistence = BrainPersistence()
        initial_perf = self.brain_persistence.load_performance()
        if initial_perf:
            self.strategy_brain.performance = initial_perf
            _bp_total_trades = sum(p.get('trades', 0) for p in initial_perf.values())
            _bp_total_pnl = sum(p.get('total_pnl', 0) for p in initial_perf.values())
            log.info('BRAIN', f'V4-Performance geladen: {len(initial_perf)} Strategien, '
                              f'{_bp_total_trades} Trades, {_bp_total_pnl:+.2f} EUR')
        else:
            log.info('BRAIN', 'V4-Performance leer - starte ohne V4-Wissen')
        self.signal_agent.v4_ensemble = self.v4_ensemble
        self.signal_agent.v4_calibrator = self.v4_calibrator
        log.info('APP', 'V4-Bridge an SignalAgent angeschlossen '
                        f'(ensemble={self.signal_agent.v4_ensemble is not None}, '
                        f'calibrator={self.signal_agent.v4_calibrator is not None})')
        # === END V4-BRIDGE Brain-Persistence ===

        # ZENTRALE KAPITALVERWALTUNG (% basiert, skaliert mit Portfolio-Groesse)
        from portfolio.manager import PortfolioManager
        self.portfolio = PortfolioManager(self.config, self.execution)
        self.portfolio.set_data_agent(self.data_agent)

        # BUG-FIX: RiskEngine-Referenz an Execution + Portfolio fuer korrekte
        # Portfolio-Wert-Berechnung (offene Positionen einbeziehen!)
        self.execution._risk_engine_ref = self.risk_engine
        self.portfolio.set_risk_engine(self.risk_engine)

        # RiskEngine mit Portfolio Manager verbinden (fuer dynamische Limits!)
        self.risk_engine.set_portfolio_manager(self.portfolio)

        # [E10-KAPITAL 29.07.] BTC-Sparplan als Kapital-Topf anmelden.
        # Ohne diese Zeile fehlen seine 96.54 $ (20.7 % des Kapitals) in
        # get_total_capital() - und damit in Sizing, Exposure-Grenzen,
        # Drawdown-Guard und Tagesstart-Kapital. Siehe Modulkommentar in
        # portfolio/manager.py set_btc_accumulator().
        self.portfolio.set_btc_accumulator(self.btc_accumulator)

        # Portfolio Agent mit Manager verbinden
        self.portfolio_agent = PortfolioAgent(self.config, portfolio_manager=self.portfolio)
        self.telegram = TelegramReporter(self.config)
        # === TELEGRAM-V2: Befehls-Empfaenger starten ===
        try:
            self.telegram.start_command_listener(self)
        except Exception as _tg_e:
            log.warn("TELEGRAM", "Listener-Start fehlgeschlagen: " + str(_tg_e)[:80])
        # === WAECHTER-AGENT: zyklischer Buchhaltungs-Check ===
        try:
            from features.waechter import Waechter
            self.waechter = Waechter(self)
            self.waechter.start()
        except Exception as _wa_e:
            log.warn("WAECHTER", "Start fehlgeschlagen: " + str(_wa_e)[:80])

        # Live/Paper Runner
        if self.config.trading.mode == "live":
            self.runner = LiveRunner(self.config)
        else:
            self.runner = PaperRunner(self.config)

        # ML + Features
        self.regime_detector = RegimeDetector()
        self.feature_store = FeatureStore()
        self.capitol_trades = CapitolTradesProvider(cache_minutes=60)
        self.funding_rates = FundingRateMonitor(cache_minutes=15)
        self.whale_alerts = WhaleAlertProvider(min_value_usd=500000)
        self.rsi_divergence = RSIDivergenceDetector(lookback=30)
        self.multi_tf = MultiTimeframeAggregator()
        self.regime_detector = RegimeDetector()
        self.onchain = OnChainAnalytics(cache_minutes=30)
        self.vwap = VWAPAgent()
        self.twap = TWAPExecutor(min_split_usd=1000)  # Nur bei >1000$ splitten
        self.smart_entry = SmartEntryAgent()
        self.rl_feedback = RLFeedbackAgent()
        self.ensemble = EnsembleSignal()
        self.llm = LocalLLMAgent()
        self.grid_trader = GridTrader(grid_size_pct=1.0, num_grids=5, amount_per_grid=100)
        self.dca_advanced = AdvancedDCA(base_amount=100)
        # [E10-QUELLEN 29.07.] Gesundheitswaechter fuer externe Signalquellen.
        # Ausgefallene Quellen fallen aus der Gewichtung, statt mit einer
        # Ersatz-0.5 mitzuzaehlen (data/source_health.py).
        from data.source_health import SourceHealth
        self.source_health = SourceHealth(max_alter_min=30)
        # [E9-CHURN 29.07.] Wiedereinstiegs-Sperre. Vorher gab es NUR einen
        # Cooldown seit dem letzten KAUF - nach einem Exit war der laengst
        # abgelaufen, also kaufte der naechste Tick sofort teurer zurueck
        # (338 Faelle, 94 % davon zu hoeherem Preis). Details im Modulkopf.
        self.reentry_guard = ReentryGuard(
            sperr_minuten=90, preisfenster_stunden=6, mindest_abschlag_pct=1.0)
        self.orderbook = OrderBookAnalyzer()
        self.config_versioning = ConfigVersioning()
        self.arbitrage = ArbitrageAgent(min_spread_pct=0.3)
        self.multi_exchange = MultiExchangeManager()
        self.bt_optimizer = BacktestOptimizer()
        self.adaptive_sizer = AdaptivePositionSizer(base_pct=15.0)
        # [25.09.2026, Befund 111] Port aus der Konfiguration, nicht fest.
        # Vorher stand hier 5050 - und damit gewann auf diesem Rechner der
        # v6-Bot, der 5050 schon haelt. v7 meldete trotzdem "Dashboard
        # http://localhost:5050", der Browser zeigte v6-Daten.
        # Die eine Quelle: data_store/config.json -> dashboard.port
        self.dashboard = WebDashboard(self, port=self.config.dashboard.port)
        # [GEFUNDENE-PROBLEME #14, 13.08.2026] Webhook stillgelegt, siehe :99.
        self.webhook = None
        self.auto_retrainer = AutoRetrainer(interval_hours=168)
        self.futures = FuturesTrader(max_leverage=3)
        self.hyperopt = HyperOptimizer()
        self.strategy_export = StrategyExporter()
        self.nupl = NUPLMonitor(cache_minutes=60)
        self.dxy = DXYMonitor(cache_minutes=60)
        self.equity_tracker = EquityTracker()
        self.meta_voting = MetaVotingSystem()
        self.shadow_mode = ShadowModeManager()
        self._trade_markers = {}  # coin -> [(time_idx, price, "BUY"/"SELL")]
        self.ngrok = NgrokDashboard(local_port=self.config.dashboard.port,
                                    config=self.config)
        self.auto_restart = AutoRestartMonitor(timeout_sec=120)
        self.reddit_sentiment = RedditSentimentProvider(cache_minutes=30)
        self.sentiment_data = SentimentProvider(cache_minutes=30)
        self.websocket = BinanceWebSocket()
        # [GEFUNDENE-PROBLEME #11, 11.08.2026] Der gemeinsame Drei-Stufen-
        # Schalter (ACTIVE / SHADOW / OFF) wird endlich angeschlossen. Gebaut
        # und mit 30 Pruefungen getestet wurde er am 11.08. - benutzt hat ihn
        # bis heute keine einzige Regel ("NOCH KEINE REGEL ANGESCHLOSSEN - das
        # Geruest allein aendert nichts", ENTWICKLERHANDBUCH).
        #
        # Die Telemetrie wird nachgereicht, sobald sie existiert (weiter unten);
        # ohne sie kann der Schalter zwar entscheiden, aber nicht notieren.
        try:
            from core.regel_schalter import RegelSchalter
            self.regel_schalter = RegelSchalter()
        except Exception as _rs_err:
            self.regel_schalter = None
            log.warn("SCHALTER", f"Regel-Schalter nicht geladen: "
                                 f"{str(_rs_err)[:60]} - Regeln behalten ihr "
                                 f"bisheriges Verhalten")

        # [GEFUNDENE-PROBLEME #31, 12.08.2026] Waechter ueber dem Schalter.
        # Am 12.08. loeschte ein Speichervorgang in der Einstellungsmaske den
        # Block regel_modi - der Trend-Ausstieg war damit wieder scharf, und
        # gemerkt hat es niemand, weil nur eine Protokollzeile FEHLTE.
        # Der Waechter macht daraus einen lauten Alarm.
        try:
            from core.regel_waechter import RegelWaechter
            self.regel_waechter = (RegelWaechter(self.regel_schalter)
                                   if self.regel_schalter else None)
        except Exception as _rw_err:
            self.regel_waechter = None
            log.warn("REGEL-WAECHTER", f"nicht geladen: {str(_rw_err)[:60]}")

        self.xgboost_model = XGBoostSignalModel()
        # [GEFUNDENE-PROBLEME #4] Wann zuletzt eine ML-Notiz je Coin geschrieben
        # wurde - Bremse gegen 36.000 Zeilen am Tag, siehe _ml_notizbuch().
        self._ml_notiz_zuletzt = {}
        # [GEFUNDENE-PROBLEME #17] Dasselbe fuer die Ensemble-Notizen.
        self._ens_notiz_zuletzt = {}
        self.signal_model = SignalModel()
        self.train_pipeline = TrainPipeline(self.feature_store, self.signal_model, self.data_agent)
        self.watchdog = Watchdog(self.health)

        # Komponenten registrieren
        for comp in ["data", "signal", "risk", "execution", "context", "news", "sl_tp_monitor"]:
            self.health.register(comp)

        log.info("APP", "Core-Systeme initialisiert")
        log.info("APP", f"Trade-Journal: {self.journal.count()} bestehende Trades")

        # 3. Event-Subscriptions verdrahten
        self._setup_event_wiring()

        # 4. Scheduler-Tasks registrieren
        self._setup_tasks()

        # 5. Graceful Shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        self._running = False

    def _setup_event_wiring(self):
        """Verdrahtet alle Events zwischen den Modulen.

        Der Datenfluss ist:
        MarketData → SignalAgent → RiskAgent → ExecutionAgent → Journal
        """
        # Wenn neue Marktdaten kommen → Signal Agent analysiert
        self.bus.subscribe(EVENT_MARKET_UPDATE, self._on_market_update)

        # Wenn Signal erzeugt → Risk Agent prüft
        self.bus.subscribe(EVENT_SIGNAL, self._on_signal)

        # Wenn Risk genehmigt → Execution Agent führt aus
        self.bus.subscribe(EVENT_RISK_APPROVED, self._on_risk_approved)

        # Wenn Order gefüllt → Journal speichert
        self.bus.subscribe(EVENT_ORDER_FILLED, self._on_order_filled)

        # Kill-Switch
        self.bus.subscribe(EVENT_KILL_SWITCH, self._on_kill_switch)

        # Errors
        self.bus.subscribe(EVENT_ERROR, self._on_error)

        log.info("APP", "Event-Verdrahtung abgeschlossen (6 Event-Typen)")

    def _setup_tasks(self):
        """Registriert periodische Aufgaben."""
        cfg = self.config

        # ============================================================
        # KRITISCH: SL/TP MONITOR - Pruft offene Positionen alle 30s
        # mit ECHTEN Binance-Preisen (auch im Paper-Modus!)
        # ============================================================
        self.scheduler.add_task(
            "sl_tp_monitor", self._sl_tp_monitor,
            interval_sec=30)

        # Haupt-Trading-Loop
        self.scheduler.add_task(
            "trading_loop", self._trading_tick,
            interval_sec=cfg.trading.loop_interval_seconds)

        # [WARTE-AUFTRAEGE 11.09.2026] Liegende Limit-Kaeufe pruefen.
        # Eigene Aufgabe, gleicher Rhythmus - Begruendung an der Methode.
        # Kehrt sofort zurueck, solange der Schalter aus ist.
        self.scheduler.add_task(
            "warteauftraege", self._warteauftraege_takt,
            interval_sec=cfg.trading.loop_interval_seconds)

        # News + Kontext-Analyse
        self.scheduler.add_task(
            "news_analysis", self._news_tick,
            interval_sec=cfg.ai.news_interval_min * 60)

        # Tagesbericht (alle 24h)
        self.scheduler.add_task(
            "daily_report", self._daily_report,
            interval_sec=86400)

        # Wochenbericht (alle 7 Tage)
        self.scheduler.add_task(
            "weekly_report", self._weekly_report,
            interval_sec=604800)

        # [WAECHTER 06.08.2026] Signalpfad-Ueberwachung: meldet, wenn erzeugte
        # Kauf-Kandidaten die Risk-Pruefung nicht erreichen. Alle 5 Minuten.
        self.scheduler.add_task(
            "waechter_signalpfad", self._waechter_signalpfad,
            interval_sec=300)

        # [CHARTANALYSE-AGENT 07.08.2026] Haelt die Chartanalyse-Messung
        # selbsttaetig aktuell: einmal taeglich Backtest ueber frische Kurse,
        # Vergleich mit dem Vorlauf, Meldung bei auffaelliger Veraenderung.
        # Aendert KEINEN Parameter - er bringt die Messung auf Stand, nicht
        # das Ergebnis in Form. Laeuft im eigenen Thread (core/scheduler.py:86),
        # der Boersen-Abruf blockiert also weder Handel noch Stop-Ueberwachung.
        try:
            _ca_task = self.scheduler.add_task(
                "chartanalyse_agent", self._chartanalyse_agent_tick,
                interval_sec=86400)
            # Erster Lauf 5 Minuten nach dem Start, nicht sofort - beim
            # Hochfahren sind Datenagent und Netz noch beschaeftigt.
            _ca_task.last_run = time.time() - 86400 + 300
        except Exception as _ca_e:
            log.warn("APP", f"Chartanalyse-Agent nicht geplant: {str(_ca_e)[:60]}")

        # [REGIME-LERNEN 10.08.2026] Taeglich nachmessen, ob der Regime-Filter
        # in der aktuellen Marktlage nuetzt oder kostet - und die Schwelle
        # anpassen, wenn die Daten das eindeutig hergeben. Jede Entscheidung
        # samt Begruendung landet in telemetrie.db (Tabelle regime_lernen),
        # damit der Bot beim naechsten Baerenmarkt nachschlagen kann.
        # Sicherheitsgrenzen und Abschalter stehen in features/regime_adaptiv.py.
        try:
            _rl_task = self.scheduler.add_task(
                "regime_lernen", self._regime_lernen_tick,
                interval_sec=86400)
            # Erster Lauf 10 Minuten nach Start, nicht sofort.
            _rl_task.last_run = time.time() - 86400 + 600
        except Exception as _rl_e:
            log.warn("APP", f"Regime-Lernen nicht geplant: {str(_rl_e)[:60]}")

        # Heartbeat
        self.scheduler.add_task(
            "heartbeat", self._heartbeat,
            interval_sec=30)

        # Auto-Save
        self.scheduler.add_task(
            "auto_save", self._auto_save,
            interval_sec=30)

        # Health-Check
        self.scheduler.add_task(
            "health_check", self._health_check,
            interval_sec=60)

        # Fill Reconciler (alle 5 Minuten)
        self.scheduler.add_task(
            "reconcile", self._reconcile,
            interval_sec=300)

        # Idempotency Cleanup (alle Stunde)
        self.scheduler.add_task(
            "idemp_cleanup", lambda: self.execution.idempotency._cleanup(),
            interval_sec=3600)

        # === DOC-AGENT: Tagesbericht alle 24h ===
        if hasattr(self, 'doc_agent') and self.doc_agent:
            self.scheduler.add_task(
                "doc_agent_daily_report",
                self.doc_agent.write_daily_report,
                interval_sec=86400)

        # === TICKETS-WATCHER alle 30s ===
        if hasattr(self, 'tickets_watcher') and self.tickets_watcher:
            self.scheduler.add_task(
                "tickets_watcher",
                self.tickets_watcher.check,
                interval_sec=30)

        # === V4 AUTO-SYNC (alle 24h) - BUGFIX SINGLE-FIRE ===
        # Vorher: zwei Tasks - sind parallel gefeuert
        # Jetzt: nur EINE Task + Mutex-Check innerhalb _v4_auto_sync
        self.scheduler.add_task(
            "v4_auto_sync", self._v4_auto_sync,
            interval_sec=60)
        log.info("APP", "V4 Auto-Sync registriert (alle 24h, Single-Fire)")

        # Cache-Clear mit Daten-Export (alle 24h)
        self.scheduler.add_task(
            "cache_clear", self._cache_clear_with_export,
            interval_sec=86400)

        # Auto-Optimizer (alle 30 Min wenn aktiviert)
        self.auto_optimize_enabled = False
        self.scheduler.add_task(
            "auto_optimizer", self._auto_optimize,
            interval_sec=1800)

        # Shadow Mode Vergleich (alle 30 Min)
        self.scheduler.add_task(
            "shadow_compare", self._shadow_compare,
            interval_sec=1800)

        # Latenz-Monitoring (alle 5 Min)
        self.scheduler.add_task(
            "latency_check", self._check_latency,
            interval_sec=300)

        # Externe Signale im Hintergrund aktualisieren (nicht blockierend!)
        self.scheduler.add_task(
            "signal_update", self._update_external_signals,
            interval_sec=120)  # Alle 2 Minuten

        # Arbitrage-Scan (alle 5 Minuten)
        self.scheduler.add_task(
            "arbitrage_scan", lambda: self.arbitrage.scan(self.config.trading.coins[:5]),
            interval_sec=300)

        # [MARKTDATEN-HISTORIE 11.08.2026] Alle 15 Minuten ein Messpunkt.
        # bot_state.json kennt nur den AKTUELLEN Wert von Funding, Whale,
        # DXY, NUPL, Onchain und Fear&Greed - der alte wird ueberschrieben.
        # Ohne Zeitreihe ist nie lernbar, ob einer davon etwas vorhersagt.
        # 15 Minuten ergeben 96 Zeilen am Tag: fein genug fuer Tagesverlaeufe,
        # grob genug, dass die Datenbank nicht zulaeuft.
        # Reine Messung, kein Einfluss auf eine Handelsentscheidung.
        self.scheduler.add_task(
            "markt_historie", self._markt_schnappschuss,
            interval_sec=900)

        # [GEFUNDENE-PROBLEME #31] Regel-Schalter regelmaessig gegenpruefen.
        # Alle 5 Minuten, denn am 12.08. verschwand der Block MITTEN IM
        # BETRIEB (beim Speichern der Einstellungen) - eine Pruefung nur beim
        # Start haette das erst beim naechsten Neustart bemerkt, also
        # womoeglich Stunden spaeter.
        self.scheduler.add_task(
            "regel_waechter",
            lambda: (self.regel_waechter.pruefen()
                     if getattr(self, "regel_waechter", None) else None),
            interval_sec=300)

        # [VERFALL ABGESCHALTET 11.08.2026 - Freigabe des Eigentuemers]
        #
        # Hier lief stuendlich rl_feedback.decay_all(). Der Verfall zog jedes
        # gelernte Gewicht um 5 % je Stunde zurueck Richtung 1,0 (neutral).
        #
        # WARUM DAS FALSCH HERUM WAR
        # Bei rund zwei Verkaeufen am Tag baut das Modul etwa 10 % Abweichung
        # auf. Der Verfall loeschte am selben Tag rund 71 %. Es KONNTE per
        # Konstruktion nichts behalten.
        #
        # BELEG: DCA_FEAR_GREED stand am 27.07.2026 08:06 auf Gewicht 1,284.
        # Am 11.08.2026 stand es auf 1,01 - allein durch diesen Verfall
        # aufgezehrt, ohne einen einzigen Trade dazwischen (der Lernpfad war
        # in der Zeit ohnehin tot, siehe Lern-Fix B2 in exit_monitor.py).
        #
        # KEIN EINGRIFF IN DEN HANDEL: die Gewichte aus rl_feedback werden
        # nirgends gelesen - apply_to_scores(), get_best_strategy() und
        # get_weight() haben ausserhalb des Moduls null Aufrufer. Abgeschaltet
        # wird also nur das Loeschen, nicht eine Wirkung.
        #
        # Die Methode decay_all() bleibt bestehen; sie wird lediglich nicht
        # mehr im Takt gerufen. Rueckbau: diese vier Zeilen wieder einsetzen.
        #     self.scheduler.add_task(
        #         "rl_decay", self.rl_feedback.decay_all,
        #         interval_sec=3600)

        log.info("APP", f"Scheduler: {len(self.scheduler._tasks)} Tasks registriert")

    # ==========================================================
    # EVENT HANDLERS (werden später von echten Agents ersetzt)
    # ==========================================================
    def _on_market_update(self, event):
        """Markt-Update → Signal Agent analysiert → ggf. Intent erzeugen."""
        snapshot = event.data.get("payload")
        if not snapshot or not isinstance(snapshot, MarketSnapshot):
            return
        self.health.heartbeat("data")

        # 0. SMART ENTRY: Pruefen ob Pending-Entries kaufbereit sind
        symbol = snapshot.symbol
        if symbol in self.smart_entry.pending:
            self.smart_entry.check(symbol, snapshot.close,
                lambda intent: self.bus.publish(EVENT_SIGNAL, intent, source="smart_entry"))
            return  # Warte auf Entry, keine neue Analyse

        # 1. SELL-CHECK: Haben wir offene Positionen fuer diesen Coin?
        symbol = snapshot.symbol
        if symbol in self.risk_engine.open_positions and self.risk_engine.open_positions[symbol].get("active"):
            pos = self.risk_engine.open_positions[symbol]

            # BEREITS IM VERKAUF? Nicht nochmal verkaufen!
            if pos.get("_selling"):
                return

            # HOLD-Modus: Kein automatischer Verkauf!
            coin_mode = pos.get("mode", "SL")
            coin_mode = self._coin_modes.get(symbol, coin_mode)
            if coin_mode == "HOLD":
                return

            entry_price = pos.get("entry_price", 0)
            highest = pos.get("highest_price", entry_price)
            qty = pos.get("qty", 0)
            # Hoechstpreis updaten
            if snapshot.close > highest:
                pos["highest_price"] = snapshot.close
                highest = snapshot.close

            # === AUTO-DEFENSE HOOK STEP 1 ===
            sell_intent = None
            try:
                _all_positions = []
                for _sym, _pos in self.risk_engine.open_positions.items():
                    if not _pos.get("active"):
                        continue
                    _entry = _pos.get("entry_price", 0)
                    _snap = self.market_data.snapshots.get(_sym) if hasattr(self, "market_data") else None
                    _cur = _snap.close if _snap else 0
                    _qty = _pos.get("qty", 0)
                    if _entry > 0 and _cur > 0:
                        _all_positions.append({
                            "symbol": _sym, "entry_price": _entry,
                            "current_price": _cur, "qty": _qty,
                        })

                _regime = str(self.regime_detector.current_regime) if hasattr(self, "regime_detector") else "UNKNOWN"
                _mtf = "NEUTRAL"
                if hasattr(self, "mtf_analyzer"):
                    try:
                        _mtf_res = self.mtf_analyzer.analyze("BTC/USDC")
                        _mtf = _mtf_res.get("direction", "NEUTRAL") if isinstance(_mtf_res, dict) else "NEUTRAL"
                    except Exception:
                        pass

                _defense_sells = self.risk_engine.check_auto_defense_sells(
                    _all_positions, _regime, _mtf)

                for _ds in _defense_sells:
                    if _ds["symbol"] == symbol:
                        # [BUGFIX 06.08.2026] Hier stand:
                        #     from core.events import DecisionIntent, Side
                        # Beide Namen sind bereits global importiert (Zeile 37).
                        # Der lokale Import machte 'Side' und 'DecisionIntent' fuer
                        # die GESAMTE Funktion zu lokalen Variablen (Python-Regel:
                        # eine Zuweisung irgendwo im Funktionskoerper macht den
                        # Namen ueberall lokal). Diese Zeile liegt in einer fast
                        # nie durchlaufenen Verzweigung (Auto-Defense feuert nur
                        # bei TRENDING_DOWN + MTF BEARISH) - also war 'Side' bei
                        # Zeile 798 praktisch immer UNZUGEWIESEN:
                        #     UnboundLocalError: cannot access local variable 'Side'
                        # Folge: JEDER Kauf-Kandidat starb direkt nach seiner
                        # Erzeugung, noch vor der Risk-Pruefung. Der Event-Bus
                        # verschluckte die Exception, also fiel es monatelang
                        # nicht auf (14.986 Signale -> 0 Risk-Pruefungen).
                        sell_intent = DecisionIntent(
                            symbol=symbol, side=Side.SELL, confidence=0.95,
                            entry_price=snapshot.close, quantity=qty,
                            strategy_id="AUTO_DEFENSE",
                            entry_reason=f"Auto-Defense: PnL {_ds['pnl_pct']:+.2f}% in Bearish Market",
                            agent_id="auto_defense")
                        break
            except Exception as _e:
                try:
                    from core.logger import log as _log
                    _log.warn("AUTO-DEFENSE", f"Check-Fehler: {_e}")
                except Exception:
                    pass

            if sell_intent is None:
                sell_intent = self.signal_agent.check_sell(snapshot, entry_price, highest)

            # Take-Profit Check (einstellbar, funktioniert in SL + TP Modus)
            if not sell_intent and entry_price > 0:
                pnl_pct = ((snapshot.close / entry_price) - 1) * 100
                tp_pct = self.config.risk.take_profit_pct

                if coin_mode == "TP":
                    tp_threshold = tp_pct if tp_pct > 0 else 3.0
                    if pnl_pct >= tp_threshold:
                        sell_intent = DecisionIntent(
                            symbol=symbol, side=Side.SELL, confidence=0.9,
                            entry_price=snapshot.close, quantity=qty,
                            strategy_id="TAKE_PROFIT",
                            entry_reason=f"Take-Profit ({pnl_pct:+.1f}% >= {tp_threshold}%)",
                            agent_id="signal_agent")

                elif coin_mode == "SL" and tp_pct > 0:
                    if pnl_pct >= tp_pct:
                        sell_intent = DecisionIntent(
                            symbol=symbol, side=Side.SELL, confidence=0.9,
                            entry_price=snapshot.close, quantity=qty,
                            strategy_id="TAKE_PROFIT",
                            entry_reason=f"Take-Profit ({pnl_pct:+.1f}% >= {tp_pct}%)",
                            agent_id="signal_agent")

            if sell_intent:
                sell_intent.quantity = qty
                # SOFORT als "im Verkauf" markieren → verhindert Doppel-Sells!
                pos["_selling"] = True
                self.health.heartbeat("signal")
                log.signal("SIGNAL", f"SELL {symbol}: {sell_intent.entry_reason} (Qty: {qty:.6f})")
                self.bus.publish(EVENT_SIGNAL, sell_intent, source="signal_agent")
                return

        # 2. BUY-CHECK: Signal Agent analysiert
        balance = self.execution.get_balance()
        usdc = balance["total"].get("USDC", 0) + balance["total"].get("USDT", 0)
        fg = self.state.get("fear_greed", 50)  # Aus dem gecachten Wert

        # [FIX 05.08.2026] Positionsgroesse aus dem GESAMTKAPITAL, nicht aus
        # dem freien Cash.
        # BEFUND: Hier wurde bisher `usdc` uebergeben, und
        # agents/signal_agent.py:171 rechnet daraus
        # `pos_size = balance_usd * position_size_pct/100`. Damit schrumpfte
        # jede weitere Position, weil der Cash durch den vorigen Kauf schon
        # kleiner war. Bei 500 $ Start und 30 %:
        #     Kauf 1: 500 * 0,30 = 150,00 $  -> Rest 350,00
        #     Kauf 2: 350 * 0,30 = 105,00 $  -> Rest 245,00
        #     Kauf 3: 245 * 0,30 =  73,50 $  -> Rest 171,50
        # Gemessen am 05.08. um 04:05: Rest-USDC 169,32 $ - passt.
        # Die dritte Position war damit halb so gross wie die erste. Fuer die
        # Auswertung ist das toedlich: dieselbe Strategie bekommt je nach
        # Reihenfolge unterschiedliches Gewicht im P&L, ohne dass das
        # irgendwo vermerkt waere.
        # portfolio/manager.py:336-349 macht es richtig (get_total_capital),
        # dieser Pfad umging es. Jetzt bekommt der SignalAgent das
        # Gesamtkapital; die Cash-Deckung prueft weiterhin
        # execution/engine.py:269-271 vor jeder Order.
        # [FIX-2 05.08.2026] Kapitalbasis selbst bilden statt sie zu erfragen.
        # get_total_capital() lieferte hier weiterhin nur den Cash-Anteil,
        # waehrend der BalanceReporter zur selben Zeit 596,58 $ auswies
        # (USDC 169,32 + Positionen 330,24 + Sparplan 97,02, Log 04:44:20).
        # Gemessene Ordergroesse war 50,80 $ = exakt 30 % von 169,32 - die
        # Positionen fehlten also in der Basis. Statt der Ursache in
        # portfolio/manager.py weiter nachzugehen, wird die Basis hier
        # explizit und nachvollziehbar gebildet: Cash + bewertete offene
        # Positionen. Der Sparplan-BTC bleibt bewusst DRAUSSEN - er ist
        # langfristige Akkumulation und darf die Handelsgroesse nicht aufblaehen.
        _pos_wert = 0.0
        try:
            for _sym, _p in (self.risk_engine.open_positions or {}).items():
                if not isinstance(_p, dict) or not _p.get("active"):
                    continue
                _q = float(_p.get("qty") or 0)
                if _q <= 0:
                    continue
                _pr = 0.0
                try:
                    _pr = float((self.data_agent.price_cache or {}).get(_sym, 0) or 0)
                except Exception:
                    _pr = 0.0
                if _pr <= 0:
                    _pr = float(_p.get("entry_price") or 0)
                _pos_wert += _q * _pr
        except Exception as _e:
            log.warn("SIZING", f"Positionsbewertung fehlgeschlagen: {str(_e)[:60]}")

        _kapital = usdc + _pos_wert
        if _kapital <= 0:
            _kapital = usdc
        # Sichtbarkeit: ohne diese Zeile war nicht feststellbar, welche Basis
        # tatsaechlich verwendet wird.
        log.info("SIZING", f"Basis {_kapital:.2f}$ (Cash {usdc:.2f} + "
                           f"Positionen {_pos_wert:.2f}) -> "
                           f"{self.config.trading.position_size_pct:.0f}% = "
                           f"{_kapital * self.config.trading.position_size_pct / 100:.2f}$")

        intent = self.signal_agent.analyze(snapshot, _kapital, fg)

        # [FIX 05.08.2026] Deckel auf das tatsaechlich verfuegbare Cash.
        # Die Groesse kommt jetzt aus dem Gesamtkapital - das kann mehr sein
        # als frei liegt. Ohne Deckel liefe die Order in
        # execution/engine.py:270 auf "rejected: Balance", und zehn Rejects
        # in Folge schicken den Bot fuer 15 Minuten in den Schlafmodus
        # (features/safety.py, RejectionCounter max_in_row=10). Lieber kleiner
        # kaufen als den ganzen Bot anhalten.
        if intent is not None and intent.side == Side.BUY:
            try:
                _frei = usdc * 0.98          # Puffer fuer Gebuehr und Slippage
                if intent.amount_usd > _frei:
                    _vorher = intent.amount_usd
                    intent.amount_usd = _frei
                    log.info("SIZING", f"{intent.symbol}: Order von "
                                       f"{_vorher:.2f}$ auf {_frei:.2f}$ "
                                       f"gedeckelt (freies Cash {usdc:.2f}$)")
            except Exception as _e:
                log.warn("SIZING", f"Cash-Deckel fehlgeschlagen: {str(_e)[:60]}")

        # =============================================================
        # REGIME-FILTER: KEIN neuer Kauf bei bestaetigtem Abwaertstrend.
        # Blockt nur NEUE Kaeufe (intent=None). Offene Positionen + ihr
        # Stop-Loss bleiben UNBERUEHRT. Auto-Resume sobald Trend sich bessert.
        # Logik/Schwellen: regime_filter.py + config_regime_filter.json
        # =============================================================
        if intent and intent.side == Side.BUY:
            try:
                import regime_filter
                _regime = self.regime_detector.current_regime
                _cycle = self.state.get("cycle_phase", "UNKNOWN")
                _mtf = self.multi_tf.last_signals.get(symbol, {}).get("direction", "NEUTRAL")
                _ind = getattr(snapshot, "indicators", {}) or {}
                _block, _why = regime_filter.should_block_buy(
                    regime=_regime, cycle=_cycle, mtf_direction=_mtf,
                    indicators=_ind, price=snapshot.close)
                if regime_filter.diag_enabled():
                    _e20 = _ind.get("ema20"); _e50 = _ind.get("ema50")
                    _ema_keys = [k for k in _ind if "ema" in str(k).lower()]
                    log.warn("REGIME-DIAG", "%s: regime=%s cycle=%s mtf=%s ema20=%s ema50=%s close=%s keys=%s -> %s" % (symbol, _regime, _cycle, _mtf, _e20, _e50, getattr(snapshot, "close", None), _ema_keys, _why))
                if _block:
                    log.warn("REGIME", f"{symbol}: BUY blockiert (Regime-Filter) - {_why}")
                    # [LUECKE GESCHLOSSEN 06.08.2026] Diese Ablehnung MUSS ins
                    # Protokoll. Vorher starb der Kandidat hier und tauchte in
                    # telemetrie.db nie auf - SOL fehlte deshalb vollstaendig,
                    # obwohl es durchgehend blockiert wurde. Wer nur die
                    # Datenbank las, haette SOL fuer inaktiv gehalten.
                    self._telemetrie_schreiben(
                        intent, equity=_kapital, cycle=_cycle,
                        grund=f"Regime-Filter: {_why}")
                    intent = None
            except Exception as _e:
                log.warn("REGIME", f"Regime-Filter-Fehler ({_e}) - Kauf durchgelassen")

        # [CHURN-FIX 10.08.2026] Wiedereinstiegs-Sperre im SIGNAL-Pfad.
        #
        # PROBLEM: reentry_guard.darf_kaufen() wurde in dieser Datei nur an
        # EINER Stelle geprueft - Zeile ~2205 im DCA-Pfad. Der Signal-Pfad
        # fragte die Sperre nie. Aufgefallen ist das erst, nachdem der
        # Signal-Pfad ueberhaupt wieder lief: er war wochenlang durch den
        # UnboundLocalError in app.py:675 tot.
        #
        # BELEGE aus trades_v5.json - dreimal in drei Tagen verkauft und
        # Sekunden spaeter teurer zurueckgekauft:
        #   07.08. 16:02:19 SELL ETH @1914.60 -> 16:02:26 BUY @1917.70  (7s)
        #   07.08. 20:48:26 SELL BTC @64658.86 -> 20:48:30 BUY @64732.29 (4s, +74$)
        #   10.08. 01:22:32 SELL BTC @64837.57 -> 01:22:39 BUY @64925.31 (7s, +88$)
        # Die BTC-Menge sank dabei ueber die Rundlaeufe von 0.002779 auf
        # 0.002766 - jeder Churn frisst Bestand, genau gegen das Ziel
        # "Bitcoin akkumulieren".
        #
        # Das ist exakt das Muster, gegen das die Sperre am 29.07. gebaut
        # wurde (E9-CHURN, siehe Kommentar bei self.reentry_guard oben:
        # 338 Faelle, 94 % davon zu hoeherem Preis).
        #
        # Bewusst HIER platziert - gleiche Ebene wie Regime-Filter und
        # Modus-Sperre, vor dem Bus-Versand und mit Telemetrie-Eintrag.
        # Verkaeufe bleiben unberuehrt: dieser Block laeuft nur fuer BUY.
        if intent and intent.side == Side.BUY:
            try:
                _re_ok, _re_why = self.reentry_guard.darf_kaufen(
                    intent.symbol, snapshot.close)
                if not _re_ok:
                    log.info("CHURN", f"{symbol}: BUY gesperrt - "
                                      f"Wiedereinstiegs-Sperre: {_re_why}")
                    self._telemetrie_schreiben(
                        intent, equity=_kapital,
                        cycle=self.state.get("cycle_phase", "UNKNOWN"),
                        grund=f"Wiedereinstiegs-Sperre: {_re_why}")
                    intent = None
            except Exception as _re_err:
                # Wie beim Regime-Filter: ein Fehler in der Pruefung darf den
                # Handel nicht heimlich anhalten. Laut melden, durchlassen.
                log.warn("CHURN", f"Wiedereinstiegs-Pruefung fehlgeschlagen "
                                  f"({str(_re_err)[:60]}) - Kauf durchgelassen")

        # [BTC-ONLY 07.08.2026] Modus-Sperre fuer NEUE Kaeufe. Offene
        # Positionen in gesperrten Coins bleiben unberuehrt - siehe
        # _asset_erlaubt(). Auch dieser Block wird protokolliert, sonst
        # entstuende dieselbe Luecke wie beim Regime-Filter.
        if intent and intent.side == Side.BUY:
            _ok, _warum = self._asset_erlaubt(intent.symbol)
            if not _ok:
                log.info("MODUS", f"{symbol}: BUY gesperrt - {_warum}")
                self._telemetrie_schreiben(
                    intent, equity=_kapital,
                    cycle=self.state.get("cycle_phase", "UNKNOWN"),
                    grund=f"Modus-Sperre: {_warum}")
                intent = None

        # Shadow Mode: Lass Schatten-Strategien parallel pruefen
        if intent:
            self.shadow_mode.on_signal(symbol, intent.score, snapshot.close, usdc)
        # Shadow Sell-Check bei jedem Preis-Update
        self.shadow_mode.on_price_update(symbol, snapshot.close)

        if intent:
            # [WAECHTER 06.08.2026] Ab hier existiert ein Kauf-Kandidat. Dieser
            # Zaehler ist die WAHRHEIT darueber, wie viele erzeugt wurden -
            # Gegenstueck zu _sig_bei_risk in _on_signal.
            self._sig_erzeugt = getattr(self, "_sig_erzeugt", 0) + 1

            # [SICHTBARKEIT 06.08.2026] heartbeat war ungeschuetzt - eine
            # Exception hier haette den Kandidaten still getoetet.
            try:
                self.health.heartbeat("signal")
            except Exception as _hb_err:
                log.warn("SIGNAL", f"Heartbeat-Fehler: {str(_hb_err)[:60]}")
            try:
                explanation = self.context_agent.explain_trade(intent, snapshot)
                if explanation:
                    log.info("CONTEXT", f"{intent.symbol}: {explanation[:80]}")
            except Exception as _ctx_err:
                log.warn("CONTEXT", f"{intent.symbol}: Erklaerung fehlgeschlagen "
                                    f"({str(_ctx_err)[:60]})")

            # Smart Entry: Bei schnellem Pump auf Pullback warten
            # [SICHTBARKEIT 06.08.2026] Dieses return war der einzige Ausgang aus
            # _on_market_update, der einen fertigen Kandidaten OHNE Logzeile
            # zurueckhielt. Der Kandidat ist nicht verloren (er liegt in der
            # smart_entry-Warteschlange), aber er war unsichtbar. Jetzt nicht mehr.
            try:
                if (hasattr(snapshot, '_df') and snapshot._df is not None
                        and len(snapshot._df) > 5):
                    recent_pump = (snapshot.close / snapshot._df["Close"].iloc[-5] - 1) * 100
                    if recent_pump > 3.0:  # Nur bei >3% Pump warten
                        self.smart_entry.queue_entry(intent, snapshot.close)
                        self._sig_wartet = getattr(self, "_sig_wartet", 0) + 1
                        log.info("SIGNAL", f"{intent.symbol}: zurueckgestellt - "
                                           f"Pump +{recent_pump:.1f}% > 3.0%, "
                                           f"warte auf Rueckgang (Smart-Entry)")
                        # Auch die Zurueckstellung gehoert ins Protokoll - der
                        # Kandidat ist nicht abgelehnt, aber auch nicht gekauft.
                        self._telemetrie_schreiben(
                            intent, equity=_kapital,
                            cycle=self.state.get("cycle_phase", "UNKNOWN"),
                            grund=f"Smart-Entry: wartet auf Rueckgang "
                                  f"(Pump +{recent_pump:.1f}%)")
                        return  # Warte auf Pullback
            except Exception as _se_err:
                log.warn("SIGNAL", f"{intent.symbol}: Smart-Entry-Pruefung "
                                   f"fehlgeschlagen ({str(_se_err)[:60]}) - "
                                   f"Kandidat laeuft normal weiter")

            self.bus.publish(EVENT_SIGNAL, intent, source="signal_agent")

    def _on_signal(self, event):
        """Signal → Portfolio-Agent prüft Allokation → Risk-Agent prüft → genehmigt oder blockiert."""
        intent = event.data.get("payload")
        if not intent:
            return

        # Portfolio-Kontext
        # [E9-EQUITY 29.07.] total_equity war NUR das Cash. Die RiskEngine
        # rechnet damit Exposure-Grenzen und Sizing - mit 5 offenen Positionen
        # ist das Cash fast leer, also schrumpfte die Bezugsgroesse genau dann,
        # wenn das Risiko am hoechsten war. Jetzt: Cash + Positionswerte.
        try:
            _equity = self.portfolio.get_total_capital()
        except Exception:
            _equity = 0.0
        # [SICHTBARKEIT 06.08.2026] get_balance() und der ["total"]-Zugriff waren
        # ungeschuetzt. Eine Exception hier (Boerse langsam, Rate-Limit, Antwort
        # ohne "total") flog in den Event-Bus zurueck, wurde dort verschluckt
        # (bus.py) und der Kauf-Kandidat war weg - ohne Log, ohne Grund, ohne
        # Spur. Genau dieses Muster passt zum Befund vom 06.08.2026:
        # 14.986 erzeugte BUY-Signale, 0 Aufrufe von RiskEngine.check().
        # Jetzt: Fehler wird benannt, und der Kandidat laeuft mit Equity 0 in die
        # RiskEngine, die ihn dort SAUBER und PROTOKOLLIERT ablehnt
        # (risk/engine.py:141 "Exposure nicht pruefbar"). Lieber eine
        # dokumentierte Ablehnung als ein lautloses Verschwinden.
        usdc = 0.0
        try:
            balance = self.execution.get_balance()
            _total = (balance or {}).get("total", {}) or {}
            usdc = (_total.get("USDC", 0) or 0) + (_total.get("USDT", 0) or 0)
        except Exception as _bal_err:
            log.error("SIGNAL", f"{intent.symbol}: Kontostand nicht lesbar "
                                f"({type(_bal_err).__name__}: {str(_bal_err)[:80]}) "
                                f"- Kandidat geht mit Equity 0 in die Risk-Pruefung")

        portfolio = {"total_equity": _equity if _equity > 0 else usdc}
        cycle = self.state.get("cycle_phase", "UNKNOWN")

        # [WAECHTER 06.08.2026] Zaehlt, wie viele Kandidaten die Risk-Pruefung
        # tatsaechlich ERREICHEN. Gegenstueck zu _sig_erzeugt in
        # _on_market_update. Die Differenz beider Zaehler ist die Zahl der
        # unterwegs verschwundenen Kaufauftraege - siehe _waechter_signalpfad().
        self._sig_bei_risk = getattr(self, "_sig_bei_risk", 0) + 1

        # [CHURN-FIX 10.08.2026, zweite Stufe] Wiedereinstiegs-Sperre auch hier.
        #
        # Die erste Pruefung sitzt in _on_market_update, also im Signal-Pfad.
        # Sie greift aber NICHT fuer Kandidaten, die ueber app.py:634 aus der
        # Smart-Entry-Warteschlange kommen - die gehen direkt an den Bus. Ein
        # solcher Kandidat wurde zwar vor der Ruecklstellung geprueft, aber
        # zwischen Ruecklstellung und Freigabe koennen Minuten liegen, und in
        # der Zeit kann ein Exit passieren.
        #
        # _on_signal ist der gemeinsame Trichter ALLER Kaufwege. Die Pruefung
        # hier deckt damit auch den Smart-Entry-Pfad ab. Doppelt zu pruefen ist
        # hier bewusst in Kauf genommen: greift schon die erste Sperre, kommt
        # diese nie zum Zug - kostet also nichts. Umgeht ein Weg die erste,
        # faengt ihn diese. Bei Geld ist Guertel und Hosentraeger vertretbar.
        if intent.side == Side.BUY:
            try:
                _rk_ok, _rk_why = self.reentry_guard.darf_kaufen(
                    intent.symbol, intent.entry_price)
                if not _rk_ok:
                    log.info("CHURN", f"{intent.symbol}: BUY gesperrt (2. Stufe) - "
                                      f"Wiedereinstiegs-Sperre: {_rk_why}")
                    intent.risk_approved = False
                    intent.risk_reason = f"Wiedereinstiegs-Sperre: {_rk_why}"
                    self._telemetrie_schreiben(
                        intent, equity=portfolio.get("total_equity", 0) or 0,
                        cycle=cycle)
                    return
            except Exception as _rk_err:
                log.warn("CHURN", f"Wiedereinstiegs-Pruefung (2. Stufe) "
                                  f"fehlgeschlagen ({str(_rk_err)[:60]}) - "
                                  f"Kauf durchgelassen")

        # Risk Engine: Prüft den Intent
        checked = self.risk_engine.check(intent, portfolio, cycle)
        self.health.heartbeat("risk")

        # [TELEMETRIE 06.08.2026] Jede Kaufpruefung dauerhaft protokollieren -
        # mit ALLEN Ablehnungsgruenden, nicht nur dem ersten. Ohne das war
        # "warum hat er nicht gekauft" nur per Forensik im 20-MB-Log zu
        # beantworten. Absichtlich NACH der Pruefung und in eigenem try/except:
        # ein Protokollfehler darf den Handel nie anhalten.
        self._telemetrie_schreiben(
            checked, equity=portfolio.get("total_equity", 0) or 0, cycle=cycle)

        if checked.risk_approved:
            self.bus.publish(EVENT_RISK_APPROVED, checked, source="risk_engine")
        else:
            self.bus.publish(EVENT_RISK_REJECTED, {"intent": checked, "reason": checked.risk_reason},
                           source="risk_engine")

    def _on_risk_approved(self, event):
        """Risk genehmigt -> Portfolio-Agent prueft -> Execution Engine fuehrt aus."""
        intent = event.data.get("payload")
        if not intent:
            return

        # TRADE-LOCK: Verhindert gleichzeitige Ausfuehrung!
        if not self._trade_lock.acquire(blocking=False):
            log.warn("EXEC", f"Trade-Lock belegt, ueberspringe {intent.symbol}")
            if intent.side == Side.SELL and intent.symbol in self.risk_engine.open_positions:
                self.risk_engine.open_positions[intent.symbol]["_selling"] = False
            return

        try:
            self._execute_approved_trade(intent)
        finally:
            self._trade_lock.release()

    # ==================================================================
    # [WARTE-AUFTRAEGE 11.09.2026] Ein Takt der Warteschlange.
    # ------------------------------------------------------------------
    # Laeuft als eigene Scheduler-Aufgabe im selben Rhythmus wie der
    # Handelstakt (12 s). Bewusst NICHT in _trading_tick eingehaengt:
    # dieser Takt kehrt an mehreren Stellen frueh zurueck (Telegram-Pause,
    # Tagesverlust-Grenze), und ein liegender Warte-Auftrag muss auch dann
    # noch bedient oder verfallen werden. Sonst bliebe er bei der ersten
    # Pause fuer immer haengen.
    #
    # Die Sperre ist dieselbe wie beim Sofortkauf (_trade_lock). Ohne sie
    # koennte ein Warte-Auftrag genau dann gebucht werden, wenn nebenan ein
    # Kauf laeuft - und zwei Schreiber auf open_positions sind der Ursprung
    # der Buchhaltungs-Desyncs vom 05.08.
    # ==================================================================
    def _warteauftraege_takt(self):
        """Prueft die liegenden Warte-Auftraege gegen die aktuellen Kurse."""
        wsl = getattr(self.execution, "warteschlange", None)
        if wsl is None or not wsl.aktiv:
            return
        try:
            kurse = dict(self.data_agent.price_cache or {})
        except Exception as e:
            log.warn("PAPER", f"Warte-Auftraege: keine Kurse ({str(e)[:60]})")
            return
        if not kurse:
            # Kein Kurs heisst NICHT "verfallen lassen". Siehe Befund 95:
            # bei Netzausfall friert der Cache ein. Die Warteschlange
            # ueberspringt fehlende Symbole von sich aus.
            return

        if not self._trade_lock.acquire(blocking=False):
            return          # naechster Takt in 12 Sekunden, kein Verlust

        try:
            fertige = self.execution.warteauftraege_pruefen(kurse)
        except Exception as e:
            log.error("PAPER", f"Warte-Auftraege: Takt fehlgeschlagen: {e}")
            fertige = []
        finally:
            self._trade_lock.release()

        # Buchen AUSSERHALB der Sperre waere falsch - _buche_ergebnis
        # schreibt open_positions. Deshalb eine zweite Runde unter Sperre.
        for intent, result in fertige:
            if not self._trade_lock.acquire(blocking=True, timeout=10):
                log.error("PAPER", f"Warte-Auftrag {intent.symbol} gefuellt, "
                                   f"aber Sperre 10 s belegt - NICHT gebucht. "
                                   f"Der Bestand stimmt jetzt nicht mit dem "
                                   f"Register ueberein.")
                continue
            try:
                self._buche_ergebnis(intent, result)
            except Exception as e:
                log.error("PAPER", f"Warte-Auftrag {intent.symbol} nicht "
                                   f"gebucht: {e}")
            finally:
                self._trade_lock.release()

    def _mfe_mae(self, symbol, entry_price=0):
        """[13.08.2026] Bester und schlechtester Stand einer Position, in Prozent.

        mfe = maximum favorable excursion, der hoechste je erreichte Stand
        ueber dem Einstand. mae = das Gegenstueck nach unten.

        Zentral, weil ZWEI Stellen die Werte brauchen und sie sonst
        doppelt - und irgendwann unterschiedlich - gerechnet wuerden:
        _journal_add() fuer das Trade-Journal und _execute_approved_trade()
        fuer die Telemetrie-Datenbank.

        Die Werte haengen an der Position (highest_price / lowest_price
        werden im Exit-Monitor bei jedem Durchlauf mitgefuehrt) und sind
        nur so lange verfuegbar, wie die Position existiert - also VOR
        record_result() abrufen.

        Rueckgabe: (mfe_pct, mae_pct), beide koennen None sein.
        """
        try:
            pos = (self.risk_engine.open_positions or {}).get(symbol) or {}
            ep = pos.get("entry_price") or entry_price or 0
            if ep <= 0:
                return (None, None)
            mfe = mae = None
            hi = pos.get("highest_price") or 0
            if hi > 0:
                mfe = round((hi / ep - 1) * 100, 2)
            elif pos.get("hoechst_pnl_pct") is not None:
                mfe = round(float(pos["hoechst_pnl_pct"]), 2)
            lo = pos.get("lowest_price") or 0
            if lo > 0:
                mae = round((lo / ep - 1) * 100, 2)
            return (mfe, mae)
        except Exception:
            return (None, None)      # nie einen Trade wegen Statistik stoppen

    def _journal_add(self, entry: dict):
        """[FIX 04.08.2026] Zentrale Journal-Anreicherung fuer ALLE Schreibpfade.

        BEFUND, der dazu gefuehrt hat: Es gibt vier Stellen, die ins
        Trade-Journal schreiben - _execute_approved_trade (:1086),
        _record_twap_fill (:1187), der DCA-Pfad (:1882) und
        runtime/exit_monitor.py:244. Nur die erste ergaenzte den
        Marktkontext. Messung ueber data_store/trades_v5.json (954
        Eintraege): market_regime, fear_greed_at_entry, score, confidence,
        signal_reasons und active_strategy standen in genau 81 Eintraegen,
        mfe_pct/mae_pct in 20 von 428 SELLs. Dadurch blieben in
        forschung.db/trades_journal 24 von 45 Spalten leer, und die Frage
        "warum lief diese Serie" war nicht beantwortbar.

        Diese Methode ergaenzt fehlende Kontextfelder und laesst bereits
        gesetzte unangetastet. Sie darf NIE werfen - ein fehlendes
        Kontextfeld darf keinen Trade blockieren.
        """
        try:
            if entry.get("market_regime") is None:
                try:
                    _rd = getattr(self, "regime_detector", None)
                    entry["market_regime"] = (str(_rd.current_regime)
                                              if _rd is not None else "UNKNOWN")
                except Exception:
                    entry["market_regime"] = "UNKNOWN"
            if entry.get("fear_greed_at_entry") is None:
                try:
                    entry["fear_greed_at_entry"] = self.state.get("fear_greed", 50)
                except Exception:
                    entry["fear_greed_at_entry"] = None
            if entry.get("cycle_phase") is None:
                try:
                    _ct = getattr(self, "cycle_theory", None)
                    entry["cycle_phase"] = (_ct.current_phase
                                            if _ct is not None else None)
                except Exception:
                    entry["cycle_phase"] = None
            if entry.get("position_size_pct") is None:
                try:
                    entry["position_size_pct"] = float(
                        self.config.trading.position_size_pct)
                except Exception:
                    entry["position_size_pct"] = None
            if entry.get("schreibpfad") is None:
                entry["schreibpfad"] = "unbekannt"
            # [FIX 05.08.2026] cycle_id und spread_pct fuer JEDEN Schreibpfad.
            if entry.get("cycle_id") is None:
                entry["cycle_id"] = getattr(self, "_cycle_id", None)
            if entry.get("spread_pct_entry") is None:
                try:
                    _c = entry.get("coin") or entry.get("symbol")
                    entry["spread_pct_entry"] = (self._spread_cache or {}).get(_c)
                except Exception:
                    entry["spread_pct_entry"] = None
            # [FIX 13.08.2026] mfe_pct und mae_pct fuer JEDEN Verkaufspfad.
            #
            # BEFUND: Von 445 Verkaeufen im Journal trugen nur 37 einen
            # Hoechststand (mfe_pct) - 92 Prozent ohne. Grund: Der Wert
            # wurde ausschliesslich in runtime/exit_monitor.py:435 gesetzt,
            # also nur beim automatischen Ausstieg. Die drei anderen
            # Schreibpfade (siehe Kopf dieser Methode) gaben ihn nie mit.
            #
            # WARUM DAS ZAEHLT: mfe_pct ist der beste je erreichte Stand
            # einer Position. Ohne ihn ist die Frage "wie viel Gewinn geben
            # wir zurueck" nicht auswertbar - genau die Frage, um die es
            # bei der Gewinn-Ratsche geht (risk/exit_rules_schatten.py).
            # Ohne diesen Fix stuenden nach dem Messfenster wieder nur eine
            # Handvoll auswertbarer Trades zur Verfuegung.
            #
            # Die Werte haengen an der Position und sind beim Verkauf noch
            # da: highest_price und lowest_price werden im Exit-Monitor bei
            # jedem Durchlauf mitgefuehrt.
            if str(entry.get("type", "")).upper().startswith("SELL"):
                _mfe, _mae = self._mfe_mae(
                    entry.get("coin") or entry.get("symbol"),
                    entry.get("entry_price") or 0)
                if entry.get("mfe_pct") is None and _mfe is not None:
                    entry["mfe_pct"] = _mfe
                if entry.get("mae_pct") is None and _mae is not None:
                    entry["mae_pct"] = _mae
            # r_multiple: Ergebnis in Vielfachen des eingegangenen Risikos.
            # pnl_pct / Stopdistanz in Prozent. Nur wenn beide bekannt sind -
            # kein geschaetzter Nenner, lieber None als eine erfundene Zahl.
            if entry.get("r_multiple") is None:
                try:
                    _pp = entry.get("pnl_pct")
                    _sl = float(self.config.risk.stop_loss_pct or 0)
                    if _pp is not None and _sl > 0:
                        entry["r_multiple"] = round(float(_pp) / _sl, 4)
                except Exception:
                    entry["r_multiple"] = None
        except Exception as _e:
            try:
                log.warn("JOURNAL", f"Anreicherung fehlgeschlagen: {str(_e)[:80]}")
            except Exception:
                pass

        # [E12 PUFFER PFLICHTFELDER 15.10.2026] Befund 88: Kauf-Felder an den Verkauf weiterreichen.
        # stop_initial, trailing_stop_pct, decision_id, signal_score, signal_reasons und active_strategy stehen
        # am KAUF, aber nicht am VERKAUF - die Frage "welches Signal endet wie?" war nur ueber Umwege
        # beantwortbar. Positionen, die nach einem Neustart wiederhergestellt werden, verlieren zudem
        # entry_score/entry_strategie. Hier, wo ALLE Schreibwege durchlaufen, werden fehlende Felder eines
        # Verkaufs aus dem ersten Kauf der laufenden Runde ergaenzt (Kaeufe derselben Muenze seit dem letzten
        # Verkauf, wie pruefstand/skripte/runden_lib.py). Vorhandene Werte bleiben unangetastet.
        try:
            if str(entry.get("type", "")).upper().startswith("SELL"):
                _kf_felder = ("stop_initial", "trailing_stop_pct", "decision_id",
                              "signal_score", "signal_reasons", "active_strategy")
                _kf_leer = (None, "", [])
                if (any(entry.get(_f) in _kf_leer for _f in _kf_felder)
                        or entry.get("entry_score") is None or not entry.get("entry_strategie")):
                    _kf_coin = entry.get("coin") or entry.get("symbol")
                    _kf_kaeufe = []
                    for _t in reversed(self.journal.get_last(400)):
                        if (_t.get("coin") or _t.get("symbol")) != _kf_coin:
                            continue
                        _kf_typ = str(_t.get("type", "")).upper()
                        if _kf_typ.startswith("SELL"):
                            break
                        if _kf_typ == "BUY":
                            _kf_kaeufe.append(_t)
                    if _kf_kaeufe:
                        _kf_k = _kf_kaeufe[-1]          # erster Kauf der Runde
                        for _f in _kf_felder:
                            if entry.get(_f) in _kf_leer and _kf_k.get(_f) not in _kf_leer:
                                entry[_f] = _kf_k.get(_f)
                        if entry.get("entry_score") is None:
                            entry["entry_score"] = _kf_k.get("signal_score", _kf_k.get("score"))
                        if not entry.get("entry_strategie"):
                            entry["entry_strategie"] = (_kf_k.get("active_strategy")
                                                        or _kf_k.get("strategy") or "")
                        entry["felder_aus_kauf"] = {"kauf_id": _kf_k.get("_id"),
                                                    "kauf_zeit": _kf_k.get("time"),
                                                    "kaeufe": len(_kf_kaeufe)}
        except Exception as _kf_e:
            try:
                log.warn("JOURNAL", f"Kauf-Felder nicht uebernommen: {str(_kf_e)[:80]}")
            except Exception:
                pass

        _ergebnis = self.journal.add(entry)

        # [DOPPELVERKAUF-FIX 13.08.2026] Zustand SOFORT nach jedem Trade
        # sichern, nicht erst beim naechsten 30-Sekunden-Takt.
        #
        # Der Fix in stop() deckt nur das saubere Herunterfahren ab. Bei
        # einem Absturz, einem Stromausfall oder einem harten Abschiessen
        # des Prozesses laeuft stop() nie - und dann klafft dieselbe Luecke
        # von bis zu 30 Sekunden, in der eine verkaufte Position im
        # gespeicherten Stand noch als offen steht und beim naechsten Start
        # zurueckkehrt (siehe Begruendung in stop()).
        #
        # Diese Stelle ist bewusst gewaehlt: _journal_add() ist der einzige
        # Punkt, durch den ALLE VIER Schreibpfade laufen (siehe Kopf dieser
        # Methode). Jeder andere Ort haette wieder einen Pfad vergessen.
        #
        # Kosten: ein Speichervorgang je Trade statt alle 30 Sekunden - bei
        # rund zehn Trades am Tag vernachlaessigbar.
        try:
            if getattr(self, "state_manager", None) is not None:
                self.state_manager.auto_save()
        except Exception as _sv_e:
            log.warn("JOURNAL", f"Zustand nach dem Trade nicht gesichert "
                                f"({type(_sv_e).__name__}: {str(_sv_e)[:60]}) - "
                                f"bei einem Absturz koennte diese Position "
                                f"beim Neustart zurueckkehren")
        return _ergebnis

    def _execute_approved_trade(self, intent):
        """Fuehrt einen genehmigten Trade aus (unter Lock).

        WICHTIG fuer Live-Modus: Balance wird VOR JEDEM TRADE neu von Binance geholt!
        Sizing erfolgt prozentual auf Gesamt-Kapital (USDC + Coin-Werte).
        """
        # Portfolio-Agent: Klumpenrisiko pruefen (NUR fuer BUY!)
        if intent.side == Side.BUY:
            # AKTUELLES Kapital holen (Live: von Binance, Paper: aus Config)
            # Skaliert automatisch mit Portfolio-Groesse - 300$ ODER 5.000$ ODER 100.000$!
            capital = self.portfolio.get_total_capital()
            free_cash = self.portfolio.get_free_cash()

            if capital <= 0:
                log.warn("EXEC", f"Kein Kapital verfuegbar - skip {intent.symbol}")
                return

            # Positionen-Werte berechnen (aktueller Marktwert mit Fallbacks!)
            # BUG-FIX: Wenn price_cache leer -> nutze entry_price als Fallback
            # damit Positionen NIE als 0 zaehlen!
            positions = {}
            for sym, pos in self.risk_engine.open_positions.items():
                if not pos.get("active"):
                    continue
                asset = sym.split("/")[0]
                qty = pos.get("qty", 0)
                if qty <= 0:
                    continue
                # Mehrfach-Fallback fuer Preis
                price = self.data_agent.price_cache.get(sym, 0)
                if price <= 0:
                    price = pos.get("entry_price", 0)  # Fallback 1: Entry-Preis
                if price <= 0:
                    price = pos.get("highest_price", 0)  # Fallback 2: Hoechststand
                if price > 0:
                    positions[asset] = {"value": qty * price}

            cycle = self.state.get("cycle_phase", "UNKNOWN")

            # Portfolio-Check mit AKTUELLEM Gesamt-Kapital
            pf_check = self.portfolio_agent.check(intent, positions, capital, cycle)
            if not pf_check["ok"]:
                log.warn("PORTFOLIO", f"BLOCKED {intent.symbol}: {pf_check['reason']}")
                return

            if pf_check["amount"] != intent.amount_usd:
                log.info("PORTFOLIO", f"Betrag: {intent.amount_usd:.2f}$ -> {pf_check['amount']:.2f}$")
                intent.amount_usd = pf_check["amount"]

            # Spread- und Volumen-Check fuer Live-Modus
            if self.config.trading.mode == "live":
                try:
                    ticker = self.execution.exchange.fetch_ticker(intent.symbol) if hasattr(self.execution, 'exchange') and self.execution.exchange else None
                    if ticker:
                        if not self.portfolio.check_spread(ticker):
                            log.warn("LIVE-SAFETY", f"BLOCKED {intent.symbol}: Spread zu hoch")
                            return
                        if not self.portfolio.check_volume(ticker):
                            log.warn("LIVE-SAFETY", f"BLOCKED {intent.symbol}: Volumen zu niedrig")
                            return
                except Exception as e:
                    log.info("LIVE-SAFETY", f"Spread/Volume-Check uebersprungen: {e}")

            # Cash-Verfuegbarkeit pruefen (auch im Paper-Mode!)
            if intent.amount_usd > free_cash:
                # Auf verfuegbares Cash reduzieren (mit kleinem Puffer)
                buffer = free_cash * 0.98  # 2% Puffer fuer Fees/Slippage
                if buffer < 5:
                    log.warn("EXEC", f"BLOCKED {intent.symbol}: Cash zu niedrig ({free_cash:.2f}$)")
                    return
                log.info("EXEC", f"Sizing reduziert auf {buffer:.2f}$ (Cash: {free_cash:.2f}$)")
                intent.amount_usd = buffer

            # Fuer Folge-Logik: usdc = capital (war vorher nur free_cash)
            usdc = capital

        # Adaptive Position Sizing (KI) - NUR wenn dynamisches Sizing AN ist!
        if intent.side == Side.BUY:
            # NUPL Check: Euphorie = NICHT kaufen! (immer aktiv, egal ob dynamic)
            if self.nupl.should_block_buys():
                log.warn("NUPL", f"KAUFE NICHT: Euphorie-Zone (NUPL {self.nupl.current_nupl:.2f})")
                return

            # MANUELLES SIZING: User hat position_size_pct gesetzt -> kein Override!
            if not self.config.risk.use_dynamic_sizing:
                # PROZENTUAL aus aktivem Modus berechnen (skaliert mit Portfolio!)
                # all_in: 95% | balanced: 30% | diversified: 10%
                try:
                    # [KG1 KAUFGROESSE HANDELSGELD, 15.10.2026] Basis ist das Handelsgeld OHNE Sparplan-BTC
                    # (Entscheidung Sven KG1/KG1a). Vorher get_total_capital() mit Sparplan.
                    capital = self.portfolio.get_trading_capital()
                    target_amount = self.portfolio.get_position_size(capital)
                    mode_name = self.config.get_active_mode().name
                    if abs(intent.amount_usd - target_amount) > 1:
                        log.info("SIZING", f"[{mode_name}] {intent.amount_usd:.2f}$ -> {target_amount:.2f}$ "
                                           f"({self.config.get_active_mode().position_size_pct:.0f}% von {capital:.2f}$)")
                        intent.amount_usd = target_amount
                except Exception as e:
                    # Fallback zu altem Verhalten
                    target_amount = usdc * (self.config.trading.position_size_pct / 100)
                    if abs(intent.amount_usd - target_amount) > 1:
                        log.info("SIZING", f"Manuell (Fallback): {intent.amount_usd:.2f}$ -> {target_amount:.2f}$")
                        intent.amount_usd = target_amount

                # === SCHATTENMODUS ADAPTIVE SIZING [11.08.2026, freigegeben] ===
                # Rechnet mit, was adaptive_sizing getan HAETTE, und schreibt
                # nur mit. Es aendert keinen Cent - der Betrag steht oben
                # bereits fest und wird hier nirgends zurueckgeschrieben.
                #
                # Absichtlich NACH der echten Berechnung, damit echte und
                # hypothetische Groesse gegeneinander stehen. Vollstaendig
                # gekapselt: ein Fehler im Mitschreiben darf einen Kauf nie
                # verhindern - deshalb faengt der except-Block alles ab und
                # meldet es, statt still zu schlucken.
                try:
                    _fg = self.state.get("fear_greed", 50)
                    _dd = self.risk_engine.drawdown.current_drawdown_pct
                    _streak = self.risk_engine.consecutive_losses
                    _regime = self.regime_detector.current_regime
                    _schatten = self.adaptive_sizer.calculate(
                        usdc, confidence=intent.confidence,
                        win_rate=self.adaptive_sizer.get_win_rate(),
                        current_drawdown=_dd, streak=_streak,
                        regime=_regime, fear_greed=_fg)
                    _betrag = float(_schatten.get("amount", 0) or 0)
                    if abs(_betrag - intent.amount_usd) > 0.01:
                        log.info("SCHATTEN-SIZING",
                                 f"{intent.symbol}: echt {intent.amount_usd:.2f}$ | "
                                 f"haette {_betrag:.2f}$ "
                                 f"({_schatten.get('pct', 0):.1f}%) "
                                 f"{' | '.join(_schatten.get('reasons', [])[:2])}")
                    _tel = getattr(self, "telemetrie", None)
                    if _tel is None:
                        from core.telemetrie import Telemetrie
                        _tel = self.telemetrie = Telemetrie()
                    _tel.schatten_sizing(
                        symbol=intent.symbol, echt_usd=intent.amount_usd,
                        schatten_usd=_betrag, schatten_pct=_schatten.get("pct"),
                        gruende=" | ".join(_schatten.get("reasons", [])),
                        confidence=intent.confidence,
                        win_rate=self.adaptive_sizer.get_win_rate(),
                        drawdown_pct=_dd, verlustserie=_streak,
                        regime=str(_regime), fear_greed=_fg)
                except Exception as _sch_e:
                    log.warn("SCHATTEN-SIZING",
                             f"nicht mitgeschrieben: {str(_sch_e)[:80]}")
            else:
                # DYNAMIC SIZING: AdaptiveSizer + NUPL + DXY verwenden
                try:
                    fg = self.state.get("fear_greed", 50)
                    dd = self.risk_engine.drawdown.current_drawdown_pct
                    streak = self.risk_engine.consecutive_losses
                    regime = self.regime_detector.current_regime
                    adaptive = self.adaptive_sizer.calculate(
                        usdc, confidence=intent.confidence,
                        win_rate=self.adaptive_sizer.get_win_rate(),
                        current_drawdown=dd, streak=streak,
                        regime=regime, fear_greed=fg)
                    if adaptive["amount"] < intent.amount_usd:
                        log.info("ADAPTIVE", f"Sizing: {intent.amount_usd:.2f}$ -> {adaptive['amount']:.2f}$ "
                                             f"({adaptive['pct']:.1f}%) {' | '.join(adaptive['reasons'][:2])}")
                        intent.amount_usd = adaptive["amount"]
                except Exception:
                    pass

                # NUPL Multiplikator (Kapitulation = mehr, Gier = weniger)
                nupl_mult = self.nupl.get_buy_multiplier()
                if nupl_mult != 1.0:
                    intent.amount_usd *= nupl_mult
                    log.info("NUPL", f"Sizing x{nupl_mult:.1f} (Zone: {self.nupl.current_zone})")

                # DXY Multiplikator (steigender Dollar = weniger)
                dxy_mult = self.dxy.get_buy_multiplier()
                if dxy_mult != 1.0:
                    intent.amount_usd *= dxy_mult
                    log.info("DXY", f"Sizing x{dxy_mult:.1f} (Trend: {self.dxy.trend})")

        # === SIZING CAP FIX ===
        # Cap auf verfuegbares Cash - verhindert Order-Rejection.
        # Sizing rechnet 33% von Total-Equity, aber Order braucht
        # tatsaechliches Cash. Ohne Cap -> alle BUY-Orders rejected.
        if intent.side == Side.BUY:
            try:
                _bal = self.execution.get_balance()
                _free_cash = _bal["total"].get("USDC", 0) + _bal["total"].get("USDT", 0)
                # 95% des Cash zulassen (5% Buffer fuer Slippage/Fees)
                _max_allowed = _free_cash * 0.95
                if intent.amount_usd > _max_allowed:
                    if _max_allowed < 10.0:
                        # Zu wenig Cash fuer sinnvolle Order
                        log.info("SIZING-CAP", f"{intent.symbol}: Cash zu klein "
                                 f"({_free_cash:.2f}$) - Order skipped")
                        return
                    _original = intent.amount_usd
                    intent.amount_usd = _max_allowed
                    log.info("SIZING-CAP", f"{intent.symbol}: {_original:.2f}$ -> "
                             f"{intent.amount_usd:.2f}$ (Cash: {_free_cash:.2f}$)")
            except Exception as _e:
                log.warn("SIZING-CAP", f"Cap-Check Fehler: {_e}")

        # TWAP: Grosse Orders aufteilen (Paper + Live)
        if intent.side == Side.BUY and self.twap.should_split(intent.amount_usd):
            # Lambda closure: intent kopieren damit jeder TWAP seinen eigenen hat
            captured_intent = intent
            twap_id = self.twap.execute_twap(intent, self.execution,
                callback=lambda r, ci=captured_intent: self._record_twap_fill(ci, r))
            if twap_id:
                # Position SOFORT als aktiv markieren (verhindert DCA-Doppelkauf!)
                # [TOEPFE SCHRITT 1 - 07.08.2026] Kennung gleich beim Anlegen
                # vergeben. Diese Stelle legt die Position VOR record_result()
                # an; ohne Kennung hier wuerde sie erst der Waechter nachtragen.
                _twap_pos = {
                    "active": True, "entry_price": intent.entry_price,
                    "highest_price": intent.entry_price, "qty": 0,
                    "time": time.time(), "_twap_active": True}
                self.risk_engine.position_kennung_sicherstellen(
                    intent.symbol, _twap_pos,
                    strategie_id=getattr(intent, "strategy_id", "") or "")
                self.risk_engine.open_positions[intent.symbol] = _twap_pos
                log.info("TWAP", f"{intent.symbol}: {intent.amount_usd:.2f}$ in Teilen")
                self.health.heartbeat("execution")
                return

        # SELL GUARD: Letzte Pruefung vor Ausfuehrung
        if intent.side == Side.SELL:
            pos = self.risk_engine.open_positions.get(intent.symbol, {})
            if not pos.get("active"):
                log.warn("EXEC", f"SELL abgebrochen: {intent.symbol} nicht mehr aktiv (bereits verkauft?)")
                pos["_selling"] = False
                return
            # Menge aus Position nehmen (nicht aus Intent, falls veraltet)
            actual_qty = pos.get("qty", 0)
            if actual_qty > 0:
                intent.quantity = actual_qty

        result = self.execution.execute(intent)
        # [WARTE-AUFTRAEGE 11.09.2026] Das Buchen steht ab hier in einer
        # eigenen Methode, damit ein spaeter bedienter Warte-Auftrag
        # GENAU denselben Weg nimmt wie ein Sofortkauf - Journal,
        # Position, Telemetrie, Impact-Journal, Bus. Ein zweiter
        # Buchungsweg waere Befund 88 noch einmal: dort schrieben zwei
        # Verkaufswege verschiedene Felder, und es fiel drei Wochen
        # lang niemandem auf.
        return self._buche_ergebnis(intent, result)

    def _buche_ergebnis(self, intent, result):
        """Bucht ein fertiges Ausfuehrungsergebnis. Herausgeloest aus
        _execute_approved_trade, Inhalt unveraendert.

        Zwei Aufrufer: der Sofortkauf oben, und der bediente
        Warte-Auftrag in _warteauftraege_takt().
        """
        self.health.heartbeat("execution")

        if result.status == "filled":
            # Trade im Journal speichern
            # === PUNKT 5: Erweitere Trade-Entry mit Brain-Lerndaten ===
            try:
                _market_regime = "UNKNOWN"
                try:
                    if getattr(self, "regime_detector", None) is not None:
                        _market_regime = str(self.regime_detector.current_regime)
                except Exception:
                    _market_regime = "UNKNOWN"
                _fg_entry = self.state.get("fear_greed", 50)
                _signal_reasons = []
                if intent.entry_reason:
                    _signal_reasons = [r.strip() for r in intent.entry_reason.split("+")]
            except Exception:
                _market_regime = "UNKNOWN"
                _fg_entry = 50
                _signal_reasons = []

            trade_entry = {
                "type": intent.side.value,
                "coin": intent.symbol,
                "price": result.avg_fill_price,
                "qty": result.filled_qty,
                "amount": result.filled_cost,
                "pnl": None,
                "pnl_pct": None,
                "fee": round(result.fee or 0, 4),
                "strategy": intent.strategy_id,
                "reason": intent.entry_reason,
                "score": intent.score,
                "confidence": intent.confidence,
                "latency_ms": result.latency_ms,
                "time": datetime.now(timezone.utc).isoformat(),
                # --- Punkt 5 Felder ---
                "signal_score": intent.score,
                "signal_reasons": _signal_reasons,
                "active_strategy": intent.strategy_id,
                "market_regime": _market_regime,
                # [FIX 05.08.2026] Felder, die forschung.db/trades_journal
                # vorsieht, die aber bisher NIRGENDS erzeugt wurden. Ohne sie
                # blieben 24 von 45 Spalten leer und die Frage "warum lief
                # diese Serie" war nach 50 Trades nicht beantwortbar.
                # Alle Werte liegen im Intent bzw. im ExecutionResult bereits
                # vor - es fehlte nur die Uebernahme.
                "decision_id": intent.id,
                "strategie_version": intent.model_version,
                "entry_geplant": intent.entry_price,
                "stop_initial": intent.stop_loss,
                "tp1": intent.take_profit,
                "trailing_stop_pct": intent.trailing_stop_pct,
                "slippage_pct": getattr(result, "slippage_pct", None),
                "agent_id": intent.agent_id,
                "risk_reason": intent.risk_reason,
                "fear_greed_at_entry": _fg_entry,
            }

            # Bei SELL: P&L berechnen BEVOR Journal-Eintrag
            if intent.side == Side.SELL and intent.symbol in self.risk_engine.open_positions:
                pos = self.risk_engine.open_positions[intent.symbol]
                entry_p = pos.get("entry_price", 0)

                # [BEFUND 88, behoben 11.09.2026] Die zwei halben Schreibwege
                # angeglichen.
                #
                # Verkaeufe entstehen auf ZWEI Wegen: hier und in
                # runtime/exit_monitor.py:413. Der dortige schrieb seit dem
                # 10.08. entry_score, entry_strategie, position_id und
                # haltedauer_min mit - dieser nicht. Ergebnis: die Felder
                # standen nur bei 47,5 % der 120 Verkaeufe seit dem Umbau.
                #
                # Warum das mehr ist als Ordnungsliebe: Am 11.09. zeigte die
                # Auswertung, dass Signale ab Score 7 im Schnitt +0,468 %
                # bringen und darunter -0,540 % - ein Unterschied von einem
                # ganzen Prozentpunkt, der im Zufallstest (20.000 Mischungen)
                # nur in 1,18 % der Faelle zufaellig entsteht. Diese Rechnung
                # stand auf 57 statt 120 Faellen, WEIL die Haelfte der
                # Verkaeufe ueber diesen Weg lief und den Score verlor.
                #
                # Reines Aufschreiben: kein Handel aendert sich dadurch.
                trade_entry["entry_score"] = pos.get("entry_score")
                trade_entry["entry_strategie"] = pos.get("entry_strategie", "")
                trade_entry["position_id"] = pos.get("position_id", "")
                _eroeffnet = pos.get("eroeffnet_ts")
                trade_entry["haltedauer_min"] = (
                    round((datetime.now(timezone.utc).timestamp()
                           - float(_eroeffnet)) / 60, 1) if _eroeffnet else None)
                _hoch = pos.get("highest_price") or 0
                _tief = pos.get("lowest_price") or 0
                if entry_p > 0:
                    if _hoch > 0:
                        trade_entry["mfe_pct"] = round((_hoch / entry_p - 1) * 100, 2)
                    if _tief > 0:
                        trade_entry["mae_pct"] = round((_tief / entry_p - 1) * 100, 2)
                if entry_p > 0 and result.avg_fill_price > 0:
                    # [E9-FEE] gegen die ECHTE Kostenbasis rechnen (inkl. Kaufgebuehr).
                    # Alt: (Verkaufspreis - Einstand) * Menge - Verkaufsgebuehr.
                    # Da beim Kauf qty = (Betrag - Gebuehr)/Preis ist, fehlte die
                    # Kaufgebuehr komplett -> jeder Trade wurde um 0.1 % des
                    # Volumens zu gut gebucht (~19 $ ueber 944 Journal-Eintraege).
                    _qty_pos = pos.get("qty", 0) or result.filled_qty
                    _cb = pos.get("cost_basis", 0) or 0
                    if _cb > 0 and _qty_pos > 0:
                        _entry_cost = _cb * (result.filled_qty / _qty_pos)
                    else:
                        _entry_cost = result.filled_qty * entry_p * 1.001
                    pnl = (result.avg_fill_price * result.filled_qty) - _entry_cost - (result.fee or 0)
                    trade_entry["pnl"] = round(pnl, 2)
                    trade_entry["pnl_pct"] = round((result.avg_fill_price / entry_p - 1) * 100, 2)
                    self.adaptive_sizer.record_result(pnl)
                    # Meta-Voting: Bewerte welche Agenten richtig lagen
                    self.meta_voting.evaluate_trade(intent.symbol, pnl)
                    # Shadow Mode: Tracke aktive PnL zum Vergleich
                    self.shadow_mode.record_active_pnl(pnl)
                # FIX 6: pos["active"]=False uebergangsweise -
                # record_result() unten loescht die Position dann atomar
                pos["_selling"] = False
                # [E9-CHURN] Exit vermerken -> Wiedereinstiegs-Sperre greift
                try:
                    self.reentry_guard.notiere_exit(
                        intent.symbol, result.avg_fill_price, intent.strategy_id or "")
                except Exception as _rge:
                    log.warn("EXEC", f"Reentry-Guard: {str(_rge)[:60]}")
                log.trade("SELL", f"{intent.symbol}: P&L {trade_entry['pnl']:+.2f}$ "
                                  f"(Entry: {entry_p:,.2f}$ → Exit: {result.avg_fill_price:,.2f}$)")

                # [FIX 13.08.2026] Auch DIESER Verkaufspfad gehoert in die
                # Telemetrie-Datenbank.
                #
                # Bisher schrieb nur runtime/exit_monitor.py eine SOLD-Zeile
                # (ueber app._telemetrie_verkauf). Verkaeufe, die ueber den
                # EventBus hier ankommen, fehlten in evaluations komplett -
                # sie standen nur im Journal. Betrifft den Trend-Ausstieg
                # ueber den Bus, _sell_coin() im Cockpit und seit Punkt 32
                # auch den reparierten Hand-Verkauf.
                #
                # Folge ohne diesen Fix: Fuer diese Verkaeufe gaebe es kein
                # R-Vielfaches, weil das nur beim Schreiben der SOLD-Zeile
                # berechnet wird. Reines Aufschreiben, kein Eingriff.
                try:
                    _hd = None
                    _ts_auf = pos.get("eroeffnet_ts") or pos.get("time")
                    if _ts_auf:
                        _hd = round((time.time() - float(_ts_auf)) / 60, 1)
                    # Direkt aus der Position holen, NICHT aus trade_entry:
                    # _journal_add() laeuft erst weiter unten (:1721) und
                    # haette die Felder hier noch nicht ergaenzt. Beide
                    # Stellen benutzen dieselbe Methode, damit die Zahlen
                    # nicht auseinanderlaufen koennen.
                    _mfe, _mae = self._mfe_mae(intent.symbol, entry_p)
                    self._telemetrie_verkauf(
                        symbol=intent.symbol,
                        preis=result.avg_fill_price,
                        qty=result.filled_qty,
                        pnl_usd=trade_entry.get("pnl", 0),
                        pnl_pct=trade_entry.get("pnl_pct", 0),
                        grund=intent.entry_reason or "?",
                        strategie=intent.strategy_id or "",
                        fee=result.fee or 0,
                        mfe_pct=_mfe,
                        mae_pct=_mae,
                        haltedauer_min=_hd,
                        position_id=pos.get("position_id", ""),
                        equity=self.portfolio.get_total_capital()
                        if hasattr(self, "portfolio") else None)
                except Exception as _tvk_e:
                    log.warn("TELEMETRIE",
                             f"{intent.symbol}: Verkauf ueber den Bus nicht "
                             f"protokolliert ({type(_tvk_e).__name__}: "
                             f"{str(_tvk_e)[:60]})")

            # Journal: NUR EINMAL speichern!
            trade_entry["schreibpfad"] = "execute_approved_trade"
            self._journal_add(trade_entry)
            self.risk_engine.record_result(intent.symbol, trade_entry.get("pnl") or 0, intent.side)

            # === IMPACT-JOURNAL HOOK ===
            # Speichert Trade mit voller Begruendung fuer spaetere Analyse
            if hasattr(self, "impact_journal") and self.impact_journal is not None:
                try:
                    _cycle = str(self.state.get("cycle_phase", "UNKNOWN"))
                    # === SIT-MEM CONTEXT FIX: echte Indikatorwerte statt Nullen ===
                    # [FIX 05.08.2026] None statt 0.0 bei fehlendem Wert.
                    # RSI und ADX koennen den Wert 0 praktisch nicht annehmen
                    # (RSI liegt real bei 10-90, ADX bei 5-60). Eine 0 im
                    # Journal war deshalb keine Messung, sondern die Signatur
                    # eines fehlenden Werts - nur sah sie in jeder Auswertung
                    # wie ein echter Extremwert aus und zog jeden Mittelwert
                    # nach unten. None ist ehrlich und in SQL/pandas als
                    # fehlend erkennbar.
                    _ij_rsi = None; _ij_adx = None; _ij_mtf = None
                    try:
                        _ij_snap = self.data_agent._last_snapshots.get(intent.symbol)
                        if _ij_snap is not None:
                            _ij_ind = getattr(_ij_snap, "indicators", {}) or {}
                            _r = _ij_ind.get("rsi")
                            _a = _ij_ind.get("adx")
                            _ij_rsi = float(_r) if _r is not None else None
                            _ij_adx = float(_a) if _a is not None else None
                    except Exception:
                        pass
                    try:
                        _ij_mtf_d = self.multi_tf.last_signals.get(intent.symbol, {}) or {}
                        _ij_mtf = _ij_mtf_d.get("confluence",
                                                _ij_mtf_d.get("score"))
                    except Exception:
                        pass
                    _ij_context = {
                        "regime": _market_regime,
                        "cycle": _cycle,
                        "fear_greed": _fg_entry,
                        "rsi": round(_ij_rsi, 1),
                        "adx": round(_ij_adx, 1),
                        "mtf_confluence": _ij_mtf,
                    }
                    if intent.side == Side.BUY:
                        self.impact_journal.log_buy(
                            symbol=intent.symbol,
                            strategy=intent.strategy_id or "?",
                            score=intent.score or 0,
                            reasons=_signal_reasons,
                            context=_ij_context,
                            amount_usd=result.filled_cost,
                            price=result.avg_fill_price,
                        )
                    elif intent.side == Side.SELL:
                        _pnl_for_journal = trade_entry.get("pnl") or 0
                        self.impact_journal.log_sell(
                            symbol=intent.symbol,
                            exit_price=result.avg_fill_price,
                            pnl_usd=_pnl_for_journal,
                            reason=intent.entry_reason or "?",
                        )
                except Exception as _ij_err:
                    log.warn("APP", f"ImpactJournal Hook-Fehler: {str(_ij_err)[:80]}")
            # === ENDE IMPACT-JOURNAL HOOK ===

            # Trade-Marker fuer Charts (NUR EINMAL!)
            if intent.symbol not in self._trade_markers:
                self._trade_markers[intent.symbol] = []
            self._trade_markers[intent.symbol].append({
                "price": result.avg_fill_price,
                "side": intent.side.value,
                "time": time.time(),
            })
            if len(self._trade_markers[intent.symbol]) > 50:
                self._trade_markers[intent.symbol] = self._trade_markers[intent.symbol][-50:]

            # BUY: Position tracken
            if intent.side == Side.BUY and intent.symbol in self.risk_engine.open_positions:
                self.risk_engine.open_positions[intent.symbol]["entry_price"] = result.avg_fill_price
                self.risk_engine.open_positions[intent.symbol]["highest_price"] = result.avg_fill_price
                self.risk_engine.open_positions[intent.symbol]["lowest_price"] = result.avg_fill_price
                # ==========================================================
                # [15.09.2026] GEBUEHR IN COINS VON DER MENGE ABZIEHEN.
                #
                # Hier stand `= result.filled_qty` - die volle
                # Ausfuehrungsmenge der Boerse. Bybit zieht die
                # Spot-Kaufgebuehr aber IN DER GEKAUFTEN MUENZE ab:
                #
                #   fee = {'currency': 'ETH', 'cost': 1.05e-05, 'rate': 0.0025}
                #
                # Auf dem Konto landen also 0,25 % WENIGER, als hier
                # eingetragen wurde. Die Position fuehrte dauerhaft mehr,
                # als es gab.
                #
                # Am 15.09. um 13:39 wurde daraus ein Kapitalrisiko: Der
                # Stop-Loss fuer ETH loeste bei -2,15 % aus, der Verkauf
                # scheiterte mit "Insufficient balance" - und die Position
                # lief ungeschuetzt weiter, waehrend sie fiel.
                #
                #   Register 0,0042      ETH
                #   Boerse   0,0041895   ETH
                #   0,0042 x 0,25 % = 0,0000105   <- exakt die Differenz
                #
                # Warum es bei BTC gutging: Dort lag noch ein Restbestand
                # aus der vorigen Position, der die Gebuehr zufaellig
                # ausglich. Reiner Zufall, kein Schutz.
                #
                # Die Gebuehr wird NUR abgezogen, wenn sie in der
                # Basiswaehrung anfaellt. Zahlt die Boerse sie in USDC,
                # ist die Menge bereits richtig.
                _menge_netto = result.filled_qty
                try:
                    _fee_ccy = str(getattr(result, "fee_currency", "") or "").upper()
                    _basis = intent.symbol.split("/")[0].upper()
                    if _fee_ccy and _fee_ccy == _basis:
                        _fee_coins = float(getattr(result, "fee", 0) or 0)
                        if 0 < _fee_coins < result.filled_qty:
                            _menge_netto = result.filled_qty - _fee_coins
                            log.info("EXEC", f"{intent.symbol}: Gebuehr "
                                     f"{_fee_coins:.10f} {_basis} von der Menge "
                                     f"abgezogen ({result.filled_qty:.8f} -> "
                                     f"{_menge_netto:.8f}) - sonst fuehrt die "
                                     f"Position mehr, als auf dem Konto liegt")
                except Exception as _fe:
                    log.warn("EXEC", f"{intent.symbol}: Gebuehrenwaehrung nicht "
                                     f"pruefbar ({str(_fe)[:60]}) - Menge "
                                     f"unveraendert uebernommen")
                self.risk_engine.open_positions[intent.symbol]["qty"] = _menge_netto
                # [E9-KOSTENBASIS] echter Mittelabfluss inkl. Kaufgebuehr
                self.risk_engine.open_positions[intent.symbol]["cost_basis"] = \
                    (result.filled_cost or 0) + (result.fee or 0)
                self.risk_engine.open_positions[intent.symbol]["dca_levels"] = 1
                self.risk_engine.open_positions[intent.symbol]["hoechst_pnl_pct"] = 0.0
                self.risk_engine.open_positions[intent.symbol]["active"] = True
                self.risk_engine.open_positions[intent.symbol]["_selling"] = False
                # [SCORE-FIX 10.08.2026] Einstiegs-Score an der Position
                # festhalten. Ohne ihn schrieb der Exit-Monitor bei jedem
                # Verkauf hart score=10 und die Frage "enden schwache Signale
                # schlechter als starke?" war nicht auswertbar.
                self.risk_engine.open_positions[intent.symbol]["entry_score"] = \
                    getattr(intent, "score", None)
                self.risk_engine.open_positions[intent.symbol]["entry_strategie"] = \
                    getattr(intent, "strategy_id", "") or ""

                # === [15.09.2026] Die Kaufwelle an der Position festhalten ===
                #
                # Ohne diese vier Zeilen kann der Ausstieg keine
                # Fibonacci-Ziele rechnen: Die Ziele sind Verlaengerungen
                # GENAU DER Welle, in deren Ruecksetzer gekauft wurde, und
                # die kennt nur das Tor - im Moment des Kaufs.
                #
                # Das Handbuch fuehrte das bis heute als offenen Punkt
                # (6.10): "Das Swing-Tief der Kaufzone ist an der Position
                # nicht gespeichert - es entsteht erst, wenn dieser Weg
                # selbst kauft." Genau das passiert hier.
                #
                # Die Felder MUESSEN zusaetzlich in die Whitelist in
                # runtime/state_manager.py auto_save(). Diese Liste
                # entscheidet, was einen Neustart ueberlebt - Befund 88
                # war genau das: entry_score wurde geschrieben, stand
                # nicht in der Whitelist und war nach jedem Neustart weg.
                try:
                    _tor = getattr(self, "fraktal_tor", None)
                    _u = _tor.letztes_urteil(intent.symbol) if _tor else None
                    _w = (_u or {}).get("welle")
                    if _w:
                        _p = self.risk_engine.open_positions[intent.symbol]
                        _p["welle_hoch"] = _w.get("hoch")
                        _p["welle_tief"] = _w.get("tief")
                        _p["welle_zeitrahmen"] = _w.get("zeitrahmen", "")
                        from features.fraktal_ziele import beschreibung
                        log.info("FRAKTAL", f"{intent.symbol}: Kaufwelle "
                                 f"{_w.get('tief'):,.2f}-{_w.get('hoch'):,.2f} "
                                 f"({_w.get('zeitrahmen')}) gemerkt. Ziele: "
                                 f"{beschreibung(_w, result.avg_fill_price)}")
                    else:
                        # Kein stilles Scheitern: Ohne Welle greifen
                        # spaeter nur die alten Prozentmarken, und das
                        # muss im Log stehen - sonst sucht man den
                        # fehlenden Fibonacci-Ausstieg im Exit-Monitor.
                        log.warn("FRAKTAL", f"{intent.symbol}: keine Kaufwelle "
                                            f"vom Tor - Ausstieg laeuft nur "
                                            f"ueber Stop-Loss/Trailing")
                except Exception as _we:
                    log.warn("FRAKTAL", f"{intent.symbol}: Kaufwelle nicht "
                                        f"gemerkt ({str(_we)[:70]}) - Ausstieg "
                                        f"ohne Fibonacci-Ziele")

                # [SCHRITT 3, 13.08.2026] Die Kette Entscheidung -> Position
                # schliessen. Beim Protokollieren der Entscheidung gab es
                # noch keine Position; jetzt gibt es sie. Ohne diese
                # Verknuepfung findet der spaetere Verkauf seine
                # Einstiegszeile nicht - und damit fehlt das Risiko R, aus
                # dem sich das R-Vielfache errechnet.
                try:
                    _pid = self.risk_engine.open_positions[intent.symbol].get("position_id")
                    _eval_id = getattr(intent, "_evaluation_id", "")
                    if _pid and _eval_id:
                        _tel_v = getattr(self, "telemetrie", None)
                        if _tel_v is None:
                            from core.telemetrie import Telemetrie
                            _tel_v = self.telemetrie = Telemetrie()
                        _tel_v.position_verknuepfen(_eval_id, _pid)
                    elif _eval_id and not _pid:
                        log.warn("TELEMETRIE",
                                 f"{intent.symbol}: Position ohne position_id - "
                                 f"kein R-Vielfaches fuer diesen Trade "
                                 f"berechenbar")
                except Exception as _vk_e:
                    log.warn("TELEMETRIE",
                             f"{intent.symbol}: Entscheidung/Position nicht "
                             f"verknuepft ({type(_vk_e).__name__}: "
                             f"{str(_vk_e)[:60]})")

                # Meta-Voting: Agent-Vorhersagen speichern
                ext = self.signal_agent.external_scores or {}
                self.meta_voting.record_prediction(intent.symbol, {
                    "technical": "BUY",
                    "ensemble": "BUY" if ext.get("ensemble", 0.5) > 0.55 else "NEUTRAL",
                    "vwap": "BUY" if ext.get("vwap_bias") == "BULLISH" else "NEUTRAL",
                    "orderbook": "BUY" if ext.get("orderbook", 0) > 0.1 else "NEUTRAL",
                    "fear_greed": "BUY" if self.state.get("fear_greed", 50) < 30 else "NEUTRAL",
                    "regime": "BUY" if self.regime_detector.current_regime in ("TRENDING_UP",) else "NEUTRAL",
                    "funding": "BUY" if self.state.get("funding_score", 0.5) > 0.5 else "NEUTRAL",
                })

            self.bus.publish(EVENT_ORDER_FILLED, trade_entry, source="execution")
        elif result.status == "wartet":
            # [WARTE-AUFTRAEGE 11.09.2026] Kein Fehler, sondern der
            # Normalfall bei eingeschalteten Warte-Auftraegen: der Auftrag
            # liegt jetzt und wird bei jedem Takt geprueft. Ohne diesen
            # Zweig stuende bei jedem Kauf eine Warnung "Order nicht
            # gefuellt" im Log - und eine Warnung, die immer kommt, liest
            # nach drei Tagen niemand mehr.
            pass
        else:
            log.warn("EXEC", f"Order nicht gefuellt: {result.status} | {result.error or result.rejected_reason}")
            # Bei Fehler: _selling Flag zuruecksetzen
            if intent.side == Side.SELL and intent.symbol in self.risk_engine.open_positions:
                self.risk_engine.open_positions[intent.symbol]["_selling"] = False

    def _record_twap_fill(self, intent, result):
        """Callback fuer TWAP: Speichert jeden Teil-Trade im Journal + Position-Tracking."""
        if result.status == "filled":
            from datetime import datetime, timezone
            self._journal_add({
                "type": "BUY", "coin": intent.symbol,
                "price": result.avg_fill_price, "qty": result.filled_qty,
                "amount": result.filled_cost, "strategy": "TWAP_" + (intent.strategy_id or ""),
                "reason": "TWAP Teil", "fee": round(result.fee or 0, 4),
                # [GEFUNDENE-PROBLEME #24] Dritter und letzter Schreibpfad.
                "slippage_pct": getattr(result, "slippage_pct", None),
                "schreibpfad": "twap_fill",
                "score": intent.score, "confidence": intent.confidence,
                "active_strategy": intent.strategy_id,
                "pnl": None, "pnl_pct": None,
                "time": datetime.now(timezone.utc).isoformat()})
            # Position updaten: Qty addieren + Durchschnittspreis berechnen
            if intent.symbol in self.risk_engine.open_positions:
                pos = self.risk_engine.open_positions[intent.symbol]
                old_qty = pos.get("qty", 0)
                old_entry = pos.get("entry_price", result.avg_fill_price)
                new_qty = old_qty + result.filled_qty
                # Gewichteter Durchschnittspreis
                if new_qty > 0:
                    pos["entry_price"] = (old_entry * old_qty + result.avg_fill_price * result.filled_qty) / new_qty
                pos["qty"] = new_qty
                pos["highest_price"] = max(pos.get("highest_price", 0), result.avg_fill_price)
            # Trade-Marker
            if intent.symbol not in self._trade_markers:
                self._trade_markers[intent.symbol] = []
            self._trade_markers[intent.symbol].append({
                "price": result.avg_fill_price, "side": "BUY", "time": time.time()})
            self.health.heartbeat("execution")
            log.info("EXEC", f"TWAP BUY {intent.symbol}: {result.filled_qty:.6f} @ {result.avg_fill_price:,.2f}$")

    def _on_order_filled(self, event):
        """Trade gespeichert → Log + Telegram."""
        trade = event.data
        if isinstance(trade, dict):
            side = trade.get("type", "?")
            coin = trade.get("coin", "?").split("/")[0]
            qty = trade.get("qty", 0)
            price = trade.get("price", 0)
            amount = trade.get("amount", 0)
            log.trade("JOURNAL", f"{side} {coin}: {qty:.6f} @ {price:,.2f}$ = {amount:.2f}$")
            if "BUY" in side:
                self.telegram.on_buy(trade)
            elif side == "SELL":
                self.telegram.on_sell(trade)
                # [LERN-FIX B1 11.08.2026] Die beiden Lern-Aufrufe standen
                # INNERHALB von "if pnl > 0" und wurden bei Verlusten nie
                # ausgefuehrt. Der Bot lernte also ausschliesslich aus
                # Gewinnen - deshalb zeigt brain_performance.json Win-Raten
                # von 75 bis 83 Prozent: ein Zaehler, der Verluste nie
                # hochzaehlt, KANN nichts anderes liefern.
                #
                # Die Bedingung war urspruenglich nur fuer die
                # BTC-Umbuchung gedacht (Gewinne in Bitcoin umschichten);
                # die Lern-Aufrufe wurden spaeter faelschlich in denselben
                # Block gehaengt.
                #
                # Jetzt: Umbuchung bleibt an den Gewinn gebunden, Lernen
                # laeuft bei JEDEM Verkauf - auch bei Verlust und bei
                # genau null.
                pnl = trade.get("pnl", 0)
                if isinstance(pnl, (int, float)):
                    strategy = trade.get("strategy", "")
                    self.strategy_brain.record_trade_result(
                        strategy, pnl, quelle="order_filled", symbol=coin)
                    self.rl_feedback.record_trade(strategy, pnl)
                    if pnl > 0:
                        self.btc_accumulator.add_profit_for_conversion(pnl)

    def _on_kill_switch(self, event):
        """Kill-Switch – stoppt sofort alles + Telegram."""
        reason = event.data.get("reason", "Unbekannt")
        log.error("KILL", f"KILL-SWITCH: {reason}")
        self.telegram.on_kill_switch(reason)
        self.stop()

    def _on_error(self, event):
        """Fehler-Handler."""
        error = event.data.get("error", "Unbekannt")
        source = event.source
        log.error(source, f"Fehler: {error}")
        self.health.report_error(source, str(error))

    # ==========================================================
    # PERIODIC TASKS
    # ==========================================================
    def _close_all_positions_safety(self) -> int:
        """Notbremse: Schliesst alle offenen Positionen (z.B. bei Daily-Loss-Limit)."""
        from core.events import DecisionIntent, Side
        closed = 0
        for sym, pos in list(self.risk_engine.open_positions.items()):
            if not pos.get("active"):
                continue
            try:
                price = self.data_agent.price_cache.get(sym, 0)
                if price <= 0:
                    continue
                qty = pos.get("qty", 0)
                if qty <= 0:
                    continue
                intent = DecisionIntent(
                    symbol=sym, side=Side.SELL, confidence=1.0,
                    entry_price=price, quantity=qty,
                    strategy_id="DAILY_LOSS_SAFETY",
                    strategy_name="Daily Loss Notbremse",
                    entry_reason="Daily Loss Limit erreicht",
                    score=10, agent_id="safety")
                result = self.execution.execute(intent)
                if result.status == "filled":
                    closed += 1
                    # FIX 6: Atomar via record_result loeschen
                    self.risk_engine.record_result(sym, 0, Side.SELL)
                    # === SIT-MEM SAFETY FIX: Notverkauf ins Impact-Journal (echter PnL) ===
                    try:
                        _entry_p = pos.get("entry_price", 0) or 0
                        _pnl_safety = 0.0
                        if _entry_p > 0 and result.avg_fill_price > 0:
                            _pnl_safety = ((result.avg_fill_price - _entry_p)
                                           * result.filled_qty - (result.fee or 0))
                        if getattr(self, "impact_journal", None) is not None:
                            self.impact_journal.log_sell(
                                symbol=sym,
                                exit_price=result.avg_fill_price,
                                pnl_usd=round(_pnl_safety, 2),
                                reason="Daily-Loss Notverkauf",
                            )
                    except Exception as _ij_e:
                        log.warn("SAFETY", f"ImpactJournal SELL-Hook: {str(_ij_e)[:80]}")
                    log.info("SAFETY", f"Geschlossen: {sym} qty={qty:.6f}")
            except Exception as e:
                log.warn("SAFETY", f"Schliessen {sym} fehlgeschlagen: {e}")
        return closed

    # === SPLIT-3: Exit-Cluster umgezogen nach runtime/exit_monitor.py ===
    def _sl_tp_monitor(self):
        """SPLIT-3: siehe runtime/exit_monitor.py

        [13.08.2026] Der Fall exit_monitor is None kann seit dem
        Startabbruch in __init__ nicht mehr eintreten - fehlt das Bauteil,
        startet der Bot gar nicht erst. Die Pruefung bleibt als zweites
        Netz stehen, falls das Attribut spaeter zur Laufzeit verloren
        geht; sie ist jetzt aber ein echter Notfall und kein Alltag mehr.
        """
        if getattr(self, "exit_monitor", None) is None:
            log.error("MONITOR", "exit_monitor zur LAUFZEIT verloren - "
                                 "STOP-PRUEFUNG UEBERSPRUNGEN! Das darf nach "
                                 "dem Startabbruch nicht vorkommen; Bot "
                                 "sofort pruefen.")
            return
        return self.exit_monitor.sl_tp_monitor()

    def _fetch_current_price(self, symbol: str) -> float:
        """SPLIT-3: siehe runtime/exit_monitor.py"""
        if getattr(self, "exit_monitor", None) is None:
            log.error("MONITOR", f"exit_monitor fehlt - kein Preis fuer {symbol}!")
            return 0.0
        return self.exit_monitor.fetch_current_price(symbol)

    def _v4_auto_sync(self):
        # === BUGFIX V4-SYNC MUTEX (verhindert Doppel-Feuer) ===
        import time as _time_mod
        _now = _time_mod.time()
        if hasattr(self, "_last_v4_sync_time"):
            _delta = _now - self._last_v4_sync_time
            # Erster Sync nach 60s ok. Nach erstem Sync: nur alle 24h
            if _delta < 86400 and _delta > 90:
                return
        self._last_v4_sync_time = _now
        # Wenn das hier durch ist und Task war schon gemacht, dann muss interval auf 24h umgestellt werden
        try:
            if hasattr(self.scheduler, "tasks") and "v4_auto_sync" in self.scheduler.tasks:
                _task = self.scheduler.tasks["v4_auto_sync"]
                if hasattr(_task, "interval_sec"):
                    _task.interval_sec = 86400
                elif isinstance(_task, dict) and "interval_sec" in _task:
                    _task["interval_sec"] = 86400
        except Exception:
            pass
        # === ENDE BUGFIX ===
        """V4 AUTO-SYNC mit AUTO-DISCOVERY der besten V4-Datei.

        Durchsucht mehrere Pfade, waehlt die V4-Datei mit den meisten
        gueltigen SELL-Trades (=aktivste Quelle).
        """
        try:
            import json
            import os
            import glob
            from datetime import datetime
            from collections import defaultdict

            # === V4-Quelle: EINE feste Datei aus config_v4_sync.json ===
            # KEIN rekursiver Desktop-Scan mehr (zog sonst evtl. die falsche
            # Backup-Datei). enabled:false = reines V6-Lernen, kein V4-Merge.
            _here = os.path.dirname(os.path.abspath(__file__))
            _v4cfg = {"enabled": False,
                      "source_path": os.path.join("v4_data", "trades_log_v4.json")}
            try:
                _cfg_path = os.path.join(_here, "config_v4_sync.json")
                if os.path.exists(_cfg_path):
                    with open(_cfg_path, "r", encoding="utf-8") as _cf:
                        _v4cfg.update(json.load(_cf))
            except Exception:
                pass

            if not _v4cfg.get("enabled", False):
                log.info("V4-SYNC", "deaktiviert (config_v4_sync.json enabled=false) - reines V6-Lernen")
                return

            v4_file = _v4cfg.get("source_path") or ""
            if v4_file and not os.path.isabs(v4_file):
                v4_file = os.path.normpath(os.path.join(_here, v4_file))
            if not v4_file or not os.path.exists(v4_file):
                log.warn("V4-SYNC", "Quelle nicht gefunden (kein Scan): " + str(v4_file))
                return

            try:
                with open(v4_file, "r", encoding="utf-8") as _pf:
                    _probe = json.load(_pf)
                valid_sells = (sum(1 for t in _probe
                                   if isinstance(t, dict) and t.get("type") == "SELL" and "pnl" in t)
                               if isinstance(_probe, list) else 0)
            except Exception:
                valid_sells = 0
            if valid_sells == 0:
                log.info("V4-SYNC", "Quelle ohne gueltige SELL-Trades: " + v4_file)
                return

            log.info("V4-SYNC", "V4-Quelle (fix, " + str(valid_sells) + " SELL-Trades): " + v4_file)

            # === V4 Trades laden ===
            with open(v4_file, "r", encoding="utf-8") as f:
                v4_trades = json.load(f)

            STRAT_MAP = {
                "EMA_TREND": "EMA_TREND", "FIBONACCI_SUPPORT": "FIBONACCI_SUPPORT",
                "ICHIMOKU_CLOUD": "ICHIMOKU", "RSI_OVERSOLD": "RSI_OVERSOLD",
                "DCA_FEAR_GREED": "DCA_FEAR_GREED", "MACD_CROSS": "MACD_CROSS",
                "MACD_CROSSOVER": "MACD_CROSS", "MOMENTUM_BREAKOUT": "MOMENTUM_BREAKOUT",
                "STOCHRSI_REVERSAL": "STOCHRSI_REVERSAL", "STOCH_RSI": "STOCHRSI_REVERSAL",
                "BOLLINGER_BOUNCE": "BOLLINGER_BOUNCE", "BOLLINGER": "BOLLINGER_BOUNCE",
                "MULTI_SIGNAL": "MULTI_SIGNAL", "TSI": "TSI", "TSI_SIGNAL": "TSI",
                "RSI_DIVERGENZ": "RSI_DIVERGENZ", "RSI_DIVERGENCE": "RSI_DIVERGENZ",
            }

            # === Aggregieren ===
            stats = defaultdict(lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0,
                                          "last_time": "", "first_time": ""})
            for t in v4_trades:
                if t.get("type") != "SELL" or "pnl" not in t:
                    continue
                v4s = t.get("strategy", "")
                if not v4s or v4s.startswith("MANUELL"):
                    continue
                v6s = STRAT_MAP.get(v4s)
                if not v6s:
                    continue
                s = stats[v6s]
                s["trades"] += 1
                pnl = t.get("pnl", 0)
                if pnl > 0:
                    s["wins"] += 1
                s["total_pnl"] += pnl
                ts = t.get("time", "")
                if not s["first_time"] or ts < s["first_time"]:
                    s["first_time"] = ts
                if ts > s["last_time"]:
                    s["last_time"] = ts

            if not stats:
                log.info("V4-SYNC", "Keine relevanten V4-Trades nach Mapping")
                return

            # === V6 Brain laden ===
            brain_file = os.path.join("data_store", "brain_performance.json")
            v6_brain = {}
            original_data = {}
            structure_type = "flat"
            if os.path.exists(brain_file):
                with open(brain_file, "r", encoding="utf-8") as f:
                    original_data = json.load(f)
                if isinstance(original_data, dict) and "performance" in original_data:
                    v6_brain = original_data["performance"]
                    structure_type = "perf_nested"
                elif isinstance(original_data, dict) and "strategies" in original_data:
                    v6_brain = original_data["strategies"]
                    structure_type = "strat_nested"
                else:
                    v6_brain = original_data

            # === REPLACE V4 Baseline pro Strategie ===
            updated = 0
            new = 0
            for sid, v4 in stats.items():
                wr = (v4["wins"] / v4["trades"] * 100) if v4["trades"] > 0 else 0
                if sid in v6_brain:
                    cur = v6_brain[sid]
                    v6_own_trades = cur.get("trades", 0) - cur.get("v4_baseline_trades", 0)
                    v6_own_wins = cur.get("wins", 0) - cur.get("v4_baseline_wins", 0)
                    v6_own_pnl = cur.get("total_pnl", 0) - cur.get("v4_baseline_pnl", 0)

                    cur["trades"] = v6_own_trades + v4["trades"]
                    cur["wins"] = v6_own_wins + v4["wins"]
                    cur["total_pnl"] = v6_own_pnl + v4["total_pnl"]
                    cur["win_rate"] = (cur["wins"] / cur["trades"] * 100) if cur["trades"] > 0 else 0

                    cur["v4_baseline_trades"] = v4["trades"]
                    cur["v4_baseline_wins"] = v4["wins"]
                    cur["v4_baseline_pnl"] = v4["total_pnl"]
                    cur["last_v4_sync_trade_time"] = v4["last_time"]
                    cur["last_v4_sync"] = datetime.now().isoformat()
                    updated += 1
                else:
                    v6_brain[sid] = {
                        "trades": v4["trades"], "wins": v4["wins"],
                        "total_pnl": v4["total_pnl"], "win_rate": wr,
                        "v4_baseline_trades": v4["trades"],
                        "v4_baseline_wins": v4["wins"],
                        "v4_baseline_pnl": v4["total_pnl"],
                        "last_v4_sync_trade_time": v4["last_time"],
                        "last_v4_sync": datetime.now().isoformat(),
                    }
                    new += 1

            # === Speichern (BUGFIX: max 5 Backups behalten) ===
            if os.path.exists(brain_file):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Alte Backups aufraeumen - max 5 behalten
                import glob as _glob_mod
                _bk_pattern = brain_file + ".v4sync_backup_*"
                _existing = sorted(_glob_mod.glob(_bk_pattern))
                while len(_existing) >= 5:
                    try:
                        os.remove(_existing.pop(0))
                    except Exception:
                        break
                shutil.copy2(brain_file, brain_file + ".v4sync_backup_" + ts)

            if structure_type == "perf_nested":
                original_data["performance"] = v6_brain
                original_data["last_v4_sync"] = datetime.now().isoformat()
                out = original_data
            elif structure_type == "strat_nested":
                original_data["strategies"] = v6_brain
                original_data["last_v4_sync"] = datetime.now().isoformat()
                out = original_data
            else:
                out = v6_brain

            with open(brain_file, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)

            total_v4_trades = sum(s["trades"] for s in stats.values())
            total_v4_pnl = sum(s["total_pnl"] for s in stats.values())

            log.info("V4-SYNC",
                     "Sync OK: " + str(updated) + " updated, "
                     + str(new) + " neu, "
                     + str(total_v4_trades) + " V4-Trades, "
                     + str(round(total_v4_pnl, 2)) + "$ PnL gesamt")

        except Exception as e:
            log.warn("V4-SYNC", "Fehler beim Auto-Sync: " + str(e)[:150])

    def _technischer_wert(self, df):
        """[GEFUNDENE-PROBLEME #17] Technischer Wert einer Muenze als 0..1.

        Gibt (wert, teile) zurueck - oder (None, {}), wenn zu wenig Daten da
        sind. 0,5 heisst neutral, groesser 0,5 bullisch.

        WARUM DIESE DREI INDIKATOREN: Das Gewicht in ensemble_signal.py heisst
        woertlich "technical: 0.30  # RSI, MACD, Bollinger etc". Die Formel
        haelt sich an genau diese Vorgabe, statt etwas Eigenes zu erfinden.

        WICHTIG - das hier ist eine ERSTE, bewusst einfache Definition. Sie ist
        nicht gemessen, sondern gesetzt. Deshalb laeuft sie im Notizbuch-Modus:
        gerechnet und protokolliert, aber nicht am Steuer. Erst der Vergleich
        ueber mehrere Wochen sagt, ob sie taugt.

        Die drei Teile zaehlen gleich viel (je ein Drittel):
        - RSI    : 30 gilt als ueberverkauft (bullisch, 1,0), 70 als
                   ueberkauft (baerisch, 0,0), 50 als neutral (0,5).
        - MACD   : Histogramm ueber null heisst Aufwaertsschwung. Gemessen
                   wird relativ zum Preis, damit BTC und SOL vergleichbar sind.
        - Bollinger: Preis am unteren Band gilt als ueberverkauft (bullisch),
                   am oberen als ueberkauft.
        """
        try:
            import pandas as pd
            if df is None or len(df) < 20:
                return None, {}
            zeile = df.iloc[-1]

            def _zahl(name):
                try:
                    wert = zeile.get(name)
                    return None if wert is None or pd.isna(wert) else float(wert)
                except Exception:
                    return None

            teile = {}

            rsi = _zahl("RSI")
            if rsi is not None:
                # RSI 30 -> 1,0 | RSI 50 -> 0,5 | RSI 70 -> 0,0
                teile["rsi"] = min(max((70.0 - rsi) / 40.0, 0.0), 1.0)

            preis = _zahl("Close")
            macd_h = _zahl("MACD_hist")
            if macd_h is not None and preis:
                # Auf den Preis bezogen, sonst waere ein BTC-Histogramm
                # automatisch groesser als ein SOL-Histogramm. 0,5 % vom Preis
                # gilt als voller Ausschlag.
                teile["macd"] = min(max(0.5 + (macd_h / preis) / 0.01, 0.0), 1.0)

            bbl, bbu = _zahl("BBL_20_2.0"), _zahl("BBU_20_2.0")
            if preis and bbl and bbu and bbu > bbl:
                lage = (preis - bbl) / (bbu - bbl)   # 0 = unteres Band
                teile["bollinger"] = min(max(1.0 - lage, 0.0), 1.0)

            if not teile:
                return None, {}
            return sum(teile.values()) / len(teile), teile
        except Exception:
            return None, {}

    def _ensemble_notizbuch(self, coin, df, roh_scores, ensemble_jetzt):
        """[GEFUNDENE-PROBLEME #17] Was das Ensemble mit echtem technical taete.

        Heute steht raw_scores["technical"] fest auf 0,5 - der Kommentar
        "Wird pro Coin ueberschrieben" stimmt nicht, weil ensemble.calculate()
        einmal VOR der Muenz-Schleife laeuft. Da technical mit 30 von 73
        vergebenen Gewichtsprozenten das groesste Einzelgewicht hat, sind rund
        41 % des Ensemble-Werts eine Konstante.

        WARUM NICHT EINFACH REPARIEREN: Der Ensemble-Wert geht ab 0,65 als
        Bonus in den Kauf-Score ein (agents/signal_agent.py:135). Ein echter
        technical-Wert wuerde diesen Bonus zum Leben erwecken - Kaeufe wuerden
        also LEICHTER ausgeloest. Ob das besser ist, weiss niemand:
        signal_agent bewertet RSI, MACD und Bollinger bereits direkt mit
        eigenen Punkten, dieselben Indikatoren zaehlten dann doppelt.

        Deshalb erst messen: hier wird festgehalten, wie oft der Bonus
        ANDERS ausgefallen waere. Nach ein paar Wochen laesst sich sagen, ob
        sich das Reparieren ueberhaupt auf Entscheidungen auswirkt - und in
        welche Richtung. Auswertung: ensemble_notizbuch_auswertung.py.

        Wirft nie nach aussen.
        """
        try:
            jetzt = time.time()
            if jetzt - self._ens_notiz_zuletzt.get(coin, 0) < ML_NOTIZ_ABSTAND_SEC:
                return
            wert, teile = self._technischer_wert(df)
            if wert is None:
                return
            self._ens_notiz_zuletzt[coin] = jetzt

            mit_echt = self.ensemble.calculate(
                {**roh_scores, "technical": wert}).get("score", 0.5)

            def _bonus(score):
                return 2 if score > 0.75 else 1 if score > 0.65 else 0

            bonus_jetzt, bonus_echt = _bonus(ensemble_jetzt), _bonus(mit_echt)

            from core.telemetrie import Telemetrie
            tel = getattr(self, "telemetrie", None)
            if tel is None:
                tel = self.telemetrie = Telemetrie()
            tel.schatten_regel(
                regel="ensemble_technical", symbol=coin,
                haette=(f"technical {wert:.3f} -> Ensemble {mit_echt:.3f} "
                        f"(Bonus {bonus_echt}), heute {ensemble_jetzt:.3f} "
                        f"(Bonus {bonus_jetzt})"),
                grund=("BONUS WAERE ANDERS" if bonus_echt != bonus_jetzt
                       else "gleiche Entscheidung"),
                preis=self.data_agent.price_cache.get(coin, 0),
                zusatz=" ".join(f"{k}={v:.2f}" for k, v in teile.items()))
        except Exception as e:
            log.warn("ENS-NOTIZ", f"{coin}: {str(e)[:80]}")

    def _ml_notizbuch(self, coin, df, preis):
        """[GEFUNDENE-PROBLEME #4, 11.08.2026] ML-Vorhersage im NOTIZBUCH-Modus.

        Das XGBoost-Modell rechnet bei jedem Takt mit und wird protokolliert,
        entscheidet aber NICHTS. raw_scores["ml_model"] bleibt bewusst leer,
        der 20-%-Platz in ensemble_signal.py bleibt unbesetzt.

        WARUM nicht gleich scharf schalten: Die einzige vorhandene Messung
        (data_store/models/xgboost_meta.json) sagt Test-Treffer 71,4 % bei
        22,6 % positiver Klasse - "immer nein" waere mit 77,4 % besser. Dazu
        sind die Trainingsdaten nachweislich verdorben (models/auto_retrain.py
        klebt 5 Coins aneinander, danach laufen rolling()/shift() ueber die
        Coin-Grenzen). Ein Modell mit diesen Zahlen ans Steuer zu lassen waere
        geraten, nicht gemessen.

        Ausgewertet wird spaeter ueber die Tabelle schatten_regeln: zu jeder
        Notiz steht Zeit, Coin, Vorhersage und Preis. Der tatsaechliche
        Kursverlauf danach ergibt sich aus den spaeteren Notizen desselben
        Coins - damit laesst sich ohne Zusatzdaten nachrechnen, ob die
        Vorhersage Vorhersagekraft hatte.

        Wirft nie nach aussen: eine Notiz darf den Handel nie stoppen.
        """
        try:
            if not self.xgboost_model.is_trained:
                return

            # Drosseln: der Handelstakt laeuft alle 12 Sekunden, der Zeitrahmen
            # ist aber 1h - und das Modell sagt 5 Kerzen voraus. Ohne Bremse
            # entstuenden ~36.000 fast identische Zeilen am Tag, aus denen sich
            # nichts messen laesst (aufeinanderfolgende Notizen waeren nahezu
            # derselbe Datenpunkt). Eine Notiz je Coin und Stunde entspricht
            # genau einer Kerze.
            jetzt = time.time()
            letzte = self._ml_notiz_zuletzt.get(coin, 0)
            if jetzt - letzte < ML_NOTIZ_ABSTAND_SEC:
                return
            self._ml_notiz_zuletzt[coin] = jetzt
            # prepare_features() ist Pflicht: 8 der 13 Merkmale (returns,
            # volatility, volume_ratio, close_to_ema20, high_low_range,
            # rsi_slope, price_vs_bb, volume_trend) stehen NICHT im Snapshot,
            # sie werden erst hier berechnet. Ohne diesen Aufruf gingen sie
            # als 0 ins Modell - eine Vorhersage auf halben Daten.
            angereichert = self.xgboost_model.prepare_features(df)
            score, grund = self.xgboost_model.predict(angereichert)

            # Notbehelf erkennen: predict() weicht bei Problemen auf eine
            # simple RSI/ADX-Regel aus. Das ist KEINE ML-Vorhersage und darf
            # die Messung nicht verunreinigen.
            if grund.startswith("Fallback"):
                if not getattr(self, "_ml_notbehelf_gemeldet", False):
                    self._ml_notbehelf_gemeldet = True
                    log.warn("ML-NOTIZ", f"{coin}: Notbehelf statt Modell "
                                         f"({grund}) - nichts notiert")
                return

            from core.telemetrie import Telemetrie
            tel = getattr(self, "telemetrie", None)
            if tel is None:
                tel = self.telemetrie = Telemetrie()
            haette = ("KAUF-Signal" if score > 0.6 else
                      "VERKAUF-Signal" if score < 0.4 else "neutral")
            tel.schatten_regel(
                regel="ml_model", symbol=coin,
                haette=f"{haette} (Score {score:.3f})",
                grund=grund, preis=preis,
                zusatz=f"version={self.xgboost_model.version}")
        except Exception as e:
            log.warn("ML-NOTIZ", f"{coin}: {str(e)[:80]}")

    def _trading_tick(self):
        """Ein Durchlauf des Trading-Loops mit allen Agenten."""
        self.health.heartbeat("data")

        # TELEGRAM-PAUSE: Trading uebersprungen, Maschine bleibt am Leben.
        # /botstop setzt das Flag, /botstart hebt es auf. Kein Runterfahren.
        if getattr(self, "_trading_paused", False):
            return

        # Beim ersten Tick: Positionen wiederherstellen (braucht Preise!)
        if not hasattr(self, '_positions_restored'):
            self._positions_restored = True
            self._restore_positions()

        # DAILY LOSS CHECK: bei Tagesverlust-Limit NUR neue Kaeufe pausieren.
        # KEIN Zwangsverkauf - offene Positionen behalten ihren Einzel-Stop-Loss
        # (_sl_tp_monitor laeuft als eigener Task weiter). Das hat am 18.06. gefehlt.
        try:
            if self.portfolio.is_paused_by_daily_loss():
                if not getattr(self, '_daily_loss_notified', False):
                    log.warn("APP", "🛑 DAILY LOSS LIMIT - keine neuen Kaeufe heute. Offene Positionen laufen mit Stop-Loss weiter.")
                    self._daily_loss_notified = True
                    try:
                        self.telegram.send("🛑 DAILY LOSS LIMIT erreicht! Keine neuen Kaeufe mehr heute. Offene Positionen behalten ihren Stop-Loss.")
                    except Exception:
                        pass
                # Tick beenden - nur keine neuen Kaeufe (offene Positionen bleiben, Monitor laeuft separat)
                return
            else:
                self._daily_loss_notified = False
        except Exception as e:
            log.warn("APP", f"Daily-Loss-Check Fehler: {e}")

        coins = self.config.trading.coins[:12]  # Top 12 Coins
        tf = self.config.trading.default_timeframe

        # Zyklustheorie updaten
        btc_price = self.data_agent.price_cache.get("BTC/USDC", 0) or self.data_agent.price_cache.get("BTC/USDT", 0)
        self.cycle_theory.update(btc_price)
        cycle = self.cycle_theory.current_phase
        self.state.set("cycle_phase", cycle)

        # Fear & Greed
        fg = self.state.get("fear_greed", 50)
        news = self.state.get("news_sentiment", {})
        news_score = news.get("score", 0.5) if isinstance(news, dict) else 0.5

        # NUPL Monitor: Blockiert Kaeufe bei Euphorie
        nupl_data = self.nupl.calculate(btc_price)
        self.state.set("nupl", nupl_data.get("nupl", 0))
        self.state.set("nupl_zone", nupl_data.get("zone", "?"))
        if nupl_data.get("buy_blocked"):
            log.warn("NUPL", f"EUPHORIE ({nupl_data['nupl']:.2f}) - Keine Kaeufe!")

        # DXY Monitor: Reduziert Exposure bei steigendem Dollar
        dxy_data = self.dxy.fetch()
        self.state.set("dxy", dxy_data.get("dxy", 0))
        self.state.set("dxy_trend", dxy_data.get("trend", "NEUTRAL"))

        # Strategy Brain: Beste Strategie wählen
        regime = "UNKNOWN"
        for coin in coins[:1]:  # BTC als Regime-Indikator
            snap = self.data_agent.fetch_snapshot(coin, tf)
            if snap:
                # Erweiterte Regime Detection
                if hasattr(snap, '_df') and snap._df is not None:
                    regime, reg_conf = self.regime_detector.detect(snap._df)
                else:
                    regime = snap.regime.value
                # Multi-Timeframe fuer BTC
                if not self.multi_tf.client and self.data_agent.client:
                    self.multi_tf.set_client(self.data_agent.client)
                try:
                    mtf = self.multi_tf.analyze(coin)
                    if mtf.get("confluence", 0) >= 75:
                        log.info("MTF", f"BTC Confluence {mtf['confluence']:.0f}%: {mtf['direction']}")
                except Exception:
                    pass
                break

        # Externe Signale aus Cache lesen (NICHT blockierend!)
        # Diese werden im Hintergrund von _signal_updater aktualisiert
        cap_score = self.state.get("capitol_score", 0.5)
        fund_score = self.state.get("funding_score", 0.5)
        whale_score = self.state.get("whale_score", 0.5)
        reddit_score = self.state.get("reddit_score", 0.5)

        # Alle Signale gewichtet an Strategy Brain
        # [E10-QUELLEN] Nur ueber LEBENDE Quellen mitteln. Vorher ging eine
        # ausgefallene Quelle mit ihrer Ersatz-0.5 und vollem Gewicht ein
        # (Reddit allein 30 % dieses Wertes) und zog das Ergebnis konstant
        # Richtung neutral.
        extra_score = self.source_health.gewichteter_wert([
            ("capitol", cap_score, 0.2),
            ("funding", fund_score, 0.3),
            ("whale", whale_score, 0.2),
            ("reddit", reddit_score, 0.3),
        ])

        best_strat, reasoning = self.strategy_brain.select_best(
            regime=regime, cycle_phase=cycle, fear_greed=fg,
            news_sentiment=news_score, capitol_signal=extra_score)
        self.signal_agent.current_strategy = best_strat

        # === ENSEMBLE: Alle Signalquellen kombinieren ===
        onchain_score = self.state.get("onchain_score", 0.5)

        # Raw Scores fuer Ensemble
        raw_scores = {
            "technical": 0.5,  # Wird pro Coin ueberschrieben
            "fear_greed": (100 - fg) / 100 if fg < 50 else (100 - fg) / 100,
            "funding": fund_score,
            "onchain": onchain_score,
            "reddit": reddit_score,
            "capitol": cap_score,
            "whale": whale_score,
        }

        # [E10-QUELLEN] Tote Quellen aus dem Ensemble nehmen. EnsembleSignal
        # normiert ueber die vorhandenen Schluessel (total_weight waechst nur
        # fuer gefundene) - was hier herausfaellt, verteilt sein Gewicht
        # automatisch auf die lebenden Quellen. "technical" und "fear_greed"
        # kommen nicht aus dem Quellen-Monitor und bleiben immer drin.
        raw_scores = self.source_health.gesunde_auswahl(raw_scores)

        # Meta-Voting: Gewichte basierend auf Agent-Performance anpassen
        meta_ensemble_score = self.meta_voting.get_weighted_score(raw_scores)

        ensemble_result = self.ensemble.calculate(raw_scores)

        # [GEFUNDENE-PROBLEME #3] Meta-Voting-Wert tatsaechlich einfliessen
        # lassen statt ihn nur zu berechnen und zu verwerfen. 50/50-Mischung:
        # Typ-Gewichtung (ensemble) bleibt erhalten, Trefferquoten-Gewichtung
        # (meta_voting) kommt gleichwertig dazu.
        ensemble_result["typ_gewichtet_score"] = ensemble_result["score"]
        ensemble_result["meta_gewichtet_score"] = round(meta_ensemble_score, 3)
        ensemble_result["score"] = round(
            (ensemble_result["typ_gewichtet_score"] + meta_ensemble_score) / 2, 3)

        # Externe Scores fuer Signal Agent setzen
        self.signal_agent.set_external_scores({
            "ensemble": ensemble_result.get("score", 0.5),
            "vwap_bias": "NEUTRAL",  # Wird pro Coin aktualisiert
            "orderbook": 0,
        })

        # Orderbook Client setzen (einmalig)
        if not self.orderbook.client and self.data_agent.client:
            self.orderbook.set_client(self.data_agent.client)

        # Alle Coins durchgehen
        loaded_snapshots = 0
        for coin in coins:
            try:
                snapshot = self.data_agent.fetch_snapshot(coin, tf)
                if snapshot:
                    loaded_snapshots += 1
                    snapshot.cycle_phase = self.cycle_theory.current_phase
                    try:
                        if hasattr(snapshot, '_df') and snapshot._df is not None:
                            div = self.rsi_divergence.detect(snapshot._df)
                            if div.get("bullish"):
                                snapshot.rsi_divergence = "BULLISH"
                            # VWAP berechnen
                            vwap_data = self.vwap.calculate(snapshot._df, coin)
                            # Orderbook analysieren
                            ob_data = self.orderbook.analyze(coin)
                            # [FIX 05.08.2026] Spread je Coin merken.
                            # data/orderbook_depth.py:51/70 rechnet ihn ohnehin
                            # aus, er wurde bisher nur nie festgehalten. Ohne
                            # ihn bleibt spread_pct_entry in
                            # forschung.db/trades_journal leer - und damit die
                            # Frage unbeantwortbar, ob ein Trade an zu weitem
                            # Spread gescheitert ist. Kein zusaetzlicher
                            # API-Aufruf, nur ein Wert aus dem vorhandenen
                            # Ergebnis.
                            try:
                                _sp = ob_data.get("spread_pct")
                                if _sp is not None:
                                    self._spread_cache[coin] = float(_sp)
                            except Exception:
                                pass
                            # [GEFUNDENE-PROBLEME #4] ML-Modell im
                            # NOTIZBUCH-Modus: rechnet mit, entscheidet nicht.
                            # Siehe _ml_notizbuch() fuer die Begruendung.
                            self._ml_notizbuch(
                                coin, snapshot._df,
                                self.data_agent.price_cache.get(coin, 0))

                            # [GEFUNDENE-PROBLEME #17] Ebenfalls Notizbuch:
                            # was das Ensemble mit einem ECHTEN technical-Wert
                            # taete. Siehe _ensemble_notizbuch().
                            self._ensemble_notizbuch(
                                coin, snapshot._df, raw_scores,
                                ensemble_result.get("score", 0.5))

                            # Externe Scores pro Coin aktualisieren
                            self.signal_agent.set_external_scores({
                                "ensemble": ensemble_result.get("score", 0.5),
                                "vwap_bias": vwap_data.get("bias", "NEUTRAL"),
                                "orderbook": ob_data.get("imbalance", 0),
                            })
                    except Exception:
                        pass
                    self.bus.publish(EVENT_MARKET_UPDATE, snapshot, source="data_agent")
                time.sleep(0.5)
            except Exception as e:
                log.error("LOOP", f"{coin}: {str(e)[:60]}")

        # [FIX 05.08.2026] Zyklus zaehlen. forschung.db/trades_journal sieht
        # cycle_id vor, damit sich Trades desselben Entscheidungsdurchlaufs
        # zusammenfassen lassen - bisher gab es keinen Zaehler.
        self._cycle_id += 1

        if loaded_snapshots == 0:
            log.warn("LOOP", f"KEINE Snapshots! Client: {self.data_agent.client is not None}")
        else:
            log.info("LOOP", f"{loaded_snapshots}/{len(coins)} Snapshots OK")

        # ============================================================
        # DIREKT-KAUF: Fear & Greed DCA (wie V4!)
        # Wenn F&G < 25 -> direkt kaufen, kein Snapshot noetig
        # ============================================================
        # [25.09.2026, Epoche L7, Freigabe Sven: "Kaufweg 2 aus"]
        # Hier stand nur `if fg < 30:`. Dieser zweite Kaufweg lief damit
        # IMMER, wenn der Angst-und-Gier-Wert unter 30 lag - und zwar
        # ohne `trading.dca_enabled` zu lesen, obwohl der Schalter genau
        # dafuer da ist. Er stand die ganze Zeit auf false.
        #
        # Warum das mehr als ein Schoenheitsfehler war: Dieser Weg fuehrt
        # am Fraktal-Tor vorbei. Das Tor ist seit Epoche L2 der Kern von
        # Svens Verfahren - es soll Kaeufe ausserhalb einer Konfluenzzone
        # verhindern, und genau deshalb wurde es scharfgeschaltet. Ein
        # zweiter Weg, der daran vorbeikauft, hebt die Regel auf, ohne
        # dass es irgendwo auffaellt.
        if fg < 30 and self.config.trading.dca_enabled:  # DCA bei Fear
            # ============================================================
            # === DCA-FIX: Fester Betrag + Cooldown + Live-Cash-Check ===
            # ============================================================
            balance = self.execution.get_balance()
            usdc_avail = balance["total"].get("USDC", 0) + balance["total"].get("USDT", 0)

            # Equity-Basis: Cash + grober Positionswert (fuer Sizing)
            _pos_value = 0
            try:
                for _sym, _p in self.risk_engine.open_positions.items():
                    if _p.get("active"):
                        _pq = _p.get("qty", 0)
                        _pp = self.data_agent.price_cache.get(_sym, 0)
                        _pos_value += _pq * _pp
            except Exception:
                pass
            total_equity = usdc_avail + _pos_value

            # FESTER BETRAG pro Trade aus Config (position_size_pct vom Equity)
            pos_pct = getattr(self.config.trading, "position_size_pct", 15)
            # === REGIME-RISK: SL/Trail/Size an Marktphase anpassen ===
            _rr_regime = "UNKNOWN"
            try:
                if hasattr(self, "regime_detector") and self.regime_detector:
                    _rr_regime = str(self.regime_detector.current_regime)
            except Exception:
                pass
            _rr_dca_sl = self.config.risk.stop_loss_pct
            _rr_dca_trail = self.config.risk.trailing_stop_pct
            _rr_size_mult = 1.0
            try:
                from risk.regime_profiles import get_adjusted_risk
                _rr_dca_sl, _rr_dca_trail, _rr_size_mult = get_adjusted_risk(
                    cycle, _rr_regime,
                    self.config.risk.stop_loss_pct,
                    self.config.risk.trailing_stop_pct)
            except Exception:
                pass
            fixed_amount = round(total_equity * (pos_pct / 100.0) * _rr_size_mult, 2)
            # Sicherheits-Grenzen
            if fixed_amount < 10:
                fixed_amount = 10.0
            # Nie mehr als verfuegbares Cash
            if fixed_amount > usdc_avail:
                fixed_amount = usdc_avail

            open_count = sum(1 for p in self.risk_engine.open_positions.values() if p.get("active"))
            max_pos = self.config.risk.max_open_positions

            # MAX 2 neue Positionen pro DCA-Runde (verhindert Burst-Kauf)
            new_buys_this_round = 0
            max_new_per_round = 2

            # ================================================================
            # [E9-RISK 29.07.] RISIKO-TORE FUER DEN DCA-PFAD
            # Bis hierher lief DCA_FEAR_GREED voellig an der RiskEngine
            # vorbei: kein Kill-Switch, kein Schlafmodus, kein Drawdown-
            # Guard, kein Per-Coin-Exposure, kein Nachkauf-Limit. Und laut
            # Journal ist DCA_FEAR_GREED die EINZIGE Einstiegsstrategie
            # (521 von 521 Kaeufen) - der komplette Handel lief also ohne
            # jede Risikopruefung. Das wird hier nachgeholt.
            # ================================================================
            _dca_stop = ""
            try:
                if self.risk_engine.kill_switch.active:
                    _dca_stop = f"Kill-Switch: {self.risk_engine.kill_switch.trigger_reason}"
                elif self.risk_engine.is_in_sleep_mode():
                    _rest = int(self.risk_engine.sleep_mode_until - time.time())
                    _dca_stop = f"Schlafmodus (noch {_rest}s)"
                elif not self.risk_engine.drawdown.is_safe():
                    _dca_stop = (f"Drawdown {self.risk_engine.drawdown.current_drawdown_pct:.1f}%"
                                 f" >= {self.risk_engine.drawdown.max_drawdown_pct}%")
            except Exception as _ge:
                log.warn("DCA", f"Risiko-Tor-Pruefung fehlgeschlagen: {str(_ge)[:60]}")
            if _dca_stop:
                log.warn("DCA", f"Runde uebersprungen - {_dca_stop}")
                # [BEFUND 40] Auch die uebersprungene Runde gehoert ins
                # Protokoll - je Muenze eine Zeile, damit die Frage "warum
                # hat er nicht gekauft" spaeter beantwortbar ist.
                for _c in coins:
                    self._dca_telemetrie(
                        _c, self.data_agent.price_cache.get(_c, 0),
                        _dca_stop, equity=total_equity, cycle=str(cycle))
                return

            # Nachkauf-Obergrenze aus der Config (war nie verdrahtet)
            _max_levels = int(getattr(self.config.trading, "dca_max_levels", 3) or 3)
            _max_coin_pct = float(getattr(self.config.risk, "max_exposure_per_coin_pct", 25.0) or 25.0)

            # [BTC-ONLY 07.08.2026] Modus-Sperre auch im DCA-Pfad. Ohne das
            # wuerde der Nachkauf weiter ETH und SOL kaufen, waehrend der
            # Signal-Pfad schon auf BTC beschraenkt ist - der Modus waere
            # damit wirkungslos.
            # BESTANDSSCHUTZ: hier werden nur NEUE Kaeufe gefiltert. Offene
            # Positionen in gesperrten Coins behalten Stop-Loss und Trailing
            # und werden vom Exit-Monitor ganz normal zu Ende verwaltet.
            try:
                _gesperrt = [c for c in coins if not self._asset_erlaubt(c)[0]]
                if _gesperrt:
                    coins = [c for c in coins if c not in _gesperrt]
                    # Nur bei AENDERUNG melden - der DCA-Tick laeuft alle 12s,
                    # eine Meldung je Runde waere reines Log-Rauschen.
                    _merker = ",".join(_gesperrt)
                    if _merker != getattr(self, "_modus_sperre_gemeldet", None):
                        self._modus_sperre_gemeldet = _merker
                        log.info("DCA", f"Modus-Sperre aktiv: kein Nachkauf in "
                                        f"{_merker}. Offene Positionen dort "
                                        f"laufen normal weiter (Stop-Loss aktiv).")
            except Exception as _ms_err:
                log.warn("DCA", f"Modus-Filter fehlgeschlagen "
                                f"({str(_ms_err)[:60]}) - alle Coins erlaubt")

            if usdc_avail >= fixed_amount and fixed_amount >= 10:
                for coin in coins:
                    # STOP wenn genug neue Kaeufe in dieser Runde
                    if new_buys_this_round >= max_new_per_round:
                        break

                    # LIVE-CASH-CHECK vor JEDEM Kauf (verhindert Ueberziehung!)
                    _bal_now = self.execution.get_balance()
                    _cash_now = _bal_now["total"].get("USDC", 0) + _bal_now["total"].get("USDT", 0)
                    if _cash_now < fixed_amount:
                        break  # Nicht genug Cash - DCA-Runde fertig

                    # Coin gerade im Verkauf? Skip
                    if coin in self.risk_engine.open_positions and self.risk_engine.open_positions[coin].get("_selling"):
                        continue

                    price = self.data_agent.price_cache.get(coin, 0)
                    if price <= 0:
                        continue

                    # === COOLDOWN-CHECK via AdvancedDCA (15min-3h je nach F&G) ===
                    try:
                        _dca_dec = self.dca_advanced.should_dca(coin, fear_greed=fg, regime=str(cycle))
                        if not _dca_dec.get("execute", True):
                            continue  # Coin noch im Cooldown
                    except Exception:
                        pass  # Bei Fehler: trotzdem fortfahren

                    # Ist es ein Nachkauf einer bestehenden Position?
                    is_nachkauf = False
                    if coin in self.risk_engine.open_positions and self.risk_engine.open_positions[coin].get("active"):
                        pos = self.risk_engine.open_positions[coin]
                        entry = pos.get("entry_price", 0)
                        # Nur nachkaufen wenn Preis min 2% unter Entry (guenstiger)
                        if entry > 0 and price >= entry * 0.98:
                            continue

                        # [E9-RISK] Nachkauf-Leiter begrenzen (config dca_max_levels).
                        # Vorher unbegrenzt: da der Einstand beim Mitteln faellt,
                        # wird die naechste -2 %-Schwelle im Abwaertstrend immer
                        # leichter erreicht -> Martingale ohne Boden. Ergebnis
                        # im Depot: 651 ADA = 28 % des Kapitals in EINEM Coin.
                        _levels = int(pos.get("dca_levels", 1) or 1)
                        if _levels >= _max_levels:
                            log.info("DCA", f"{coin}: Nachkauf-Limit erreicht "
                                            f"({_levels}/{_max_levels}) - kein weiteres Mitteln")
                            continue

                        # [E9-RISK] Per-Coin-Exposure. Der DCA-Pfad hat
                        # max_exposure_per_coin_pct noch nie geprueft.
                        _cur_val = pos.get("qty", 0) * price
                        if total_equity > 0 and (_cur_val + fixed_amount) / total_equity * 100 > _max_coin_pct:
                            log.info("DCA", f"{coin}: Exposure-Limit "
                                            f"({(_cur_val + fixed_amount)/total_equity*100:.1f}% > {_max_coin_pct:.0f}%)"
                                            f" - kein Nachkauf")
                            continue
                        is_nachkauf = True
                    else:
                        # NEUE Position: nur wenn Platz da ist
                        if open_count >= max_pos:
                            self._dca_telemetrie(
                                coin, price,
                                f"Max Positionen: {open_count}/{max_pos}",
                                betrag=fixed_amount, equity=total_equity,
                                cycle=str(cycle))
                            continue
                        # [E9-CHURN] Wiedereinstiegs-Sperre. Genau hier entstand
                        # der Gebuehren-Kreisel: Position wird vom Exit-Monitor
                        # geloescht, der Kauf-Cooldown ist laengst abgelaufen,
                        # also kauft dieser Tick Sekunden spaeter teurer zurueck.
                        try:
                            _ok, _why = self.reentry_guard.darf_kaufen(coin, price)
                            if not _ok:
                                log.info("DCA", f"{coin}: {_why}")
                                self._dca_telemetrie(
                                    coin, price,
                                    f"Wiedereinstiegs-Sperre: {_why}",
                                    betrag=fixed_amount, equity=total_equity,
                                    cycle=str(cycle))
                                continue
                        except Exception as _rge:
                            log.warn("DCA", f"Reentry-Guard-Fehler ({str(_rge)[:50]}) - Kauf durchgelassen")

                    pos_size = fixed_amount

                    intent = DecisionIntent(
                        symbol=coin, side=Side.BUY, confidence=0.7,
                        entry_price=price, amount_usd=pos_size,
                        stop_loss=price * (1 - _rr_dca_sl / 100),
                        trailing_stop_pct=_rr_dca_trail,
                        strategy_id="DCA_FEAR_GREED", strategy_name="Fear & Greed DCA",
                        entry_reason=f"DCA ({fg})", score=5, agent_id="direct_dca")

                    # [BEFUND 40] Die ZUSAGE protokollieren - vor der
                    # Ausfuehrung, damit sie auch dann im Protokoll steht,
                    # wenn die Order danach scheitert. Genauso macht es der
                    # Signal-Pfad (app.py:1214, vor dem Bus-Ereignis).
                    self._dca_telemetrie(
                        coin, price, "OK", betrag=pos_size,
                        equity=total_equity, cycle=str(cycle), genehmigt=True)

                    result = self.execution.execute(intent)
                    if result.status == "filled":
                        # AdvancedDCA Cooldown setzen (verhindert Sofort-Wiederkauf!)
                        try:
                            self.dca_advanced.record_dca(coin, result.filled_cost,
                                                         result.avg_fill_price, result.filled_qty)
                        except Exception:
                            pass

                        if not is_nachkauf:
                            open_count += 1
                            new_buys_this_round += 1

                        # [E9-FEE] "fee" fehlte auf diesem Pfad komplett - alle
                        # 521 DCA-Kaeufe stehen ohne Gebuehr im Journal, deshalb
                        # wies die Auswertung nur 26.66 $ statt ~38.66 $ Gebuehren aus.
                        self._journal_add({"type": "BUY", "coin": coin, "price": result.avg_fill_price,
                            "qty": result.filled_qty, "amount": result.filled_cost,
                            "fee": round(result.fee or 0, 4),
                            # [GEFUNDENE-PROBLEME #24] Auch hier, aus genau dem
                            # Grund, der eine Zeile weiter oben steht: fehlt ein
                            # Feld auf EINEM Schreibpfad, ist die spaetere
                            # Auswertung schief, ohne dass es auffaellt. Bei
                            # 521 DCA-Kaeufen waere die Slippage-Messung sonst
                            # einseitig auf die Nicht-DCA-Trades gestuetzt.
                            "slippage_pct": getattr(result, "slippage_pct", None),
                            "schreibpfad": "dca_pfad",
                            "active_strategy": "DCA_FEAR_GREED",
                            "strategy": "DCA_FEAR_GREED", "reason": intent.entry_reason,
                            "time": datetime.now(timezone.utc).isoformat()})

                        # === IMPACT-JOURNAL HOOK fuer DCA-Trades ===
                        if hasattr(self, "impact_journal") and self.impact_journal is not None:
                            try:
                                self.impact_journal.log_buy(
                                    symbol=coin, strategy="DCA_FEAR_GREED", score=5,
                                    reasons=[f"DCA bei F&G {fg}", f"Cycle {cycle}", "Extreme Fear Kauf"],
                                    context={"regime": str(regime) if "regime" in dir() else "UNKNOWN",
                                             "cycle": str(cycle), "fear_greed": fg},
                                    amount_usd=result.filled_cost, price=result.avg_fill_price)
                            except Exception as _ije:
                                log.warn("APP", f"DCA Impact-Hook Fehler: {str(_ije)[:60]}")

                        # [E9-KOSTENBASIS] tatsaechlicher Mittelabfluss inkl. Kaufgebuehr.
                        _kosten = (result.filled_cost or 0) + (result.fee or 0)
                        if coin in self.risk_engine.open_positions and self.risk_engine.open_positions[coin].get("active"):
                            pos = self.risk_engine.open_positions[coin]
                            old_qty = pos.get("qty", 0)
                            old_entry = pos.get("entry_price", result.avg_fill_price)
                            new_qty = old_qty + result.filled_qty
                            if new_qty > 0:
                                pos["entry_price"] = (old_entry * old_qty + result.avg_fill_price * result.filled_qty) / new_qty
                            pos["qty"] = new_qty
                            pos["cost_basis"] = pos.get("cost_basis", old_qty * old_entry * 1.001) + _kosten
                            pos["dca_levels"] = int(pos.get("dca_levels", 1) or 1) + 1
                            # [E9-TRAILING-FIX] Hoechststaende MUESSEN beim Mitteln
                            # zurueckgesetzt werden. Sonst rechnet der Exit-Monitor
                            # "Fall vom Hoch" gegen ein Hoch, das zum ALTEN, hoeheren
                            # Einstand gehoerte: sobald die Position nach dem Nachkauf
                            # knapp ins Plus dreht, ist fall_from_high schon riesig und
                            # der Trailing-Stop feuert sofort. Genau der Mechanismus,
                            # der Gewinner bei ~+0.4 % gekappt hat.
                            pos["highest_price"] = max(result.avg_fill_price, price)
                            pos["lowest_price"] = min(pos.get("lowest_price", price), price)
                            pos["hoechst_pnl_pct"] = 0.0
                            log.info("DCA", f"{coin}: Nachkauf {pos['dca_levels']}/{_max_levels} | "
                                            f"neuer Einstand {pos['entry_price']:.6f} | "
                                            f"Hoechststand zurueckgesetzt")
                        else:
                            self.risk_engine.record_result(coin, 0, Side.BUY)
                            if coin in self.risk_engine.open_positions:
                                self.risk_engine.open_positions[coin]["entry_price"] = result.avg_fill_price
                                self.risk_engine.open_positions[coin]["highest_price"] = result.avg_fill_price
                                self.risk_engine.open_positions[coin]["lowest_price"] = result.avg_fill_price
                                self.risk_engine.open_positions[coin]["qty"] = result.filled_qty
                                self.risk_engine.open_positions[coin]["cost_basis"] = _kosten
                                self.risk_engine.open_positions[coin]["dca_levels"] = 1
                                self.risk_engine.open_positions[coin]["hoechst_pnl_pct"] = 0.0
                                self.risk_engine.open_positions[coin]["active"] = True
                                # [SCORE-FIX 10.08.2026] auch im DCA-Pfad, sonst
                                # fehlt der Score bei jedem Nachkauf-Einstieg.
                                #
                                # [BEFUND 41, behoben 12.09.2026] Hier stand:
                                #     getattr(_dca_intent, "score", None)
                                #         if "_dca_intent" in dir() else None
                                # `_dca_intent` wird im ganzen Projekt an keiner Stelle
                                # zugewiesen (nachgezaehlt: 0 Treffer). Die Bedingung war
                                # also immer falsch und der Score auf diesem Pfad IMMER
                                # leer - der Fix vom 10.08. griff nie. Belegt an den
                                # Daten: 0 von 220 Verkaeufen trugen einen Score.
                                #
                                # Die Variable heisst hier `intent`, oben in derselben
                                # Schleife gesetzt (mit score=5). Nachgesehen, dass sie an
                                # dieser Stelle existiert: zwischen ihrer Zuweisung und
                                # hier liegt genau ein execute(intent) und keine weitere
                                # Schleife.
                                #
                                # Reines Aufschreiben: `entry_score` wird von keiner
                                # Handelsregel gelesen, nur von Journal, Telemetrie und
                                # Export.
                                self.risk_engine.open_positions[coin]["entry_score"] = \
                                    getattr(intent, "score", None)
                                self.risk_engine.open_positions[coin]["entry_strategie"] = "DCA_FEAR_GREED"
                        log.trade("DCA", f"{coin}: {result.filled_qty:.6f} @ {result.avg_fill_price:,.2f}$ ({result.filled_cost:.2f}$)")
                    time.sleep(0.3)

                if new_buys_this_round > 0:
                    log.info("DCA", f"Runde: {new_buys_this_round} neue Position(en) a {fixed_amount:.2f}$ (max {max_new_per_round}/Runde, max {max_pos} gesamt)")

        # BTC Sparplan prüfen
        try:
            balance = self.execution.get_balance()
            usdc = balance["total"].get("USDC", 0) + balance["total"].get("USDT", 0)
            btc_price = self.data_agent.price_cache.get("BTC/USDC", 0) or self.data_agent.price_cache.get("BTC/USDT", 0)
            if btc_price > 0:
                sp = self.btc_accumulator.check_sparplan(usdc, btc_price, execution_engine=self.execution)
                if sp["executed"]:
                    self.telegram.send(f"₿ SPARPLAN: {sp['amount']:.2f}$ → {sp['btc_qty']:.8f} BTC @ {sp['btc_price']:,.2f}$")

                # Gewinne in BTC konvertieren
                pc = self.btc_accumulator.check_profit_conversion(btc_price, execution_engine=self.execution)
                if pc["executed"]:
                    self.telegram.send(f"₿ AUTO-BTC: {pc['amount']:.2f}$ → {pc['btc_qty']:.8f} BTC @ {pc['btc_price']:,.2f}$")
        except Exception as e:
            log.error("BTC-ACC", f"Sparplan: {str(e)[:60]}")

    def _news_tick(self):
        """Periodisch: News holen und Kontext-Analyse erstellen."""
        self.health.heartbeat("news")
        try:
            news = self.context_agent.news.fetch()
            fg = self.sentiment_data.get_fear_greed().get("value", 50)
            phase = self.state.get("cycle_phase", "UNKNOWN")
            log.info("NEWS", f"{news.get('label', '?')} (Score: {news.get('score', 0.5)}) | F&G: {fg}")
            self.state.set("fear_greed", fg)
            self.state.set("news_sentiment", news)
        except Exception as e:
            log.error("NEWS", f"Fehler: {str(e)[:60]}")

    def _update_external_signals(self):
        """Aktualisiert externe Signale im Hintergrund (nicht blockierend).

        [E10-QUELLEN 29.07.] Jede Quelle meldet jetzt zusaetzlich ihre
        Gesundheit an self.source_health. Vorher fiel eine ausgefallene
        Quelle still auf 0.5 zurueck und ging mit VOLLEM Gewicht ins
        Ensemble - eine tote Quelle hat das Signal also aktiv Richtung
        neutral gezogen, statt einfach zu fehlen. Siehe data/source_health.py.
        """
        def _hole(name, fn, state_key, hat_daten=None):
            """Holt einen Score, meldet Gesundheit, schreibt in den State."""
            try:
                sig = fn() or {}
            except Exception as e:
                self.source_health.melde(name, False, f"Fehler: {str(e)[:40]}")
                return
            if sig.get("error"):
                self.source_health.melde(name, False, str(sig["error"])[:40])
                return
            if hat_daten is not None:
                try:
                    if not hat_daten(sig):
                        self.source_health.melde(name, False, sig.get("details", "keine Daten"))
                        return
                except Exception:
                    pass
            self.source_health.melde(name, True, sig.get("label", ""))
            self.state.set(state_key, sig.get("score", 0.5))

        _hole("capitol", self.capitol_trades.get_signal, "capitol_score")
        _hole("funding", self.funding_rates.get_signal, "funding_score")
        _hole("whale", self.whale_alerts.get_signal, "whale_score")
        # Reddit meldet einen 403 nicht als Fehler, sondern liefert
        # {"score": 0.5, "posts": 0, "details": "Keine Reddit-Daten"}.
        # Genau daran erkennt man den Ausfall.
        _hole("reddit", self.reddit_sentiment.analyze_sentiment, "reddit_score",
              hat_daten=lambda s: int(s.get("posts", 1) or 0) > 0)
        _hole("onchain", self.onchain.get_signal, "onchain_score")

        try:
            _tote = self.source_health.tote()
            if _tote:
                log.warn("QUELLEN", self.source_health.status_zeile())
        except Exception:
            pass
        try:
            nupl = self.nupl.fetch()
            self.state.set("nupl", nupl.get("nupl", 0.5))
            self.state.set("nupl_zone", nupl.get("zone", "?"))
        except Exception:
            pass
        try:
            dxy = self.dxy.fetch()
            self.state.set("dxy", dxy.get("dxy", 100))
            self.state.set("dxy_trend", dxy.get("trend", "NEUTRAL"))
        except Exception:
            pass

    def _check_retrain(self):
        """Prueft ob Modell-Retraining noetig ist."""
        if self.auto_retrainer.should_retrain():
            self.auto_retrainer.retrain(
                self.data_agent, self.signal_model, self.xgboost_model,
                self.config.trading.coins[:5])

    def _cache_clear_with_export(self):
        """Exportiert alle Daten als TXT, dann cleart Cache. Nur nach 24h!"""
        if not hasattr(self, '_last_cache_clear'):
            self._last_cache_clear = time.time()  # Erst beim naechsten Mal
            return
        if (time.time() - self._last_cache_clear) < 82800:  # Min 23h
            return
        self._last_cache_clear = time.time()
        try:
            import os
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                f"auto_export_{ts}.txt")
            text = self.generate_analyse_export()
            text += f"\n\nLatenz: {self._last_latency}ms\n"
            text += f"Cache-Groesse: {len(self.data_agent.price_cache)} Preise\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            log.info("CACHE", f"Auto-Export gespeichert: {path}")
        except Exception as e:
            log.warn("CACHE", f"Export Fehler: {e}")
        # Cache leeren
        self.data_agent.price_cache.clear()
        self.data_agent._last_snapshots.clear()
        import gc; gc.collect()
        log.info("CACHE", "Cache gecleart + Garbage Collection")

    def _check_latency(self):
        """Prueft Latenz zum Exchange."""
        try:
            import time as _t
            start = _t.time()
            if self.data_agent.client:
                self.data_agent.client.fetch_ticker("BTC/USDC")
            latency = int((_t.time() - start) * 1000)
            self._last_latency = latency
            if latency > 500:
                log.warn("LATENZ", f"Hohe Latenz: {latency}ms (Ziel: <500ms)")
        except Exception:
            self._last_latency = -1

    def _shadow_compare(self):
        """Vergleicht Shadow-Strategien mit aktiver Strategie."""
        comparison = self.shadow_mode.get_comparison()
        log.info("SHADOW", f"\n{comparison}")
        best = self.shadow_mode.get_best_shadow()
        if best and best.total_pnl > self.shadow_mode.active_pnl + 50:
            log.warn("SHADOW", f"'{best.name}' ist {best.total_pnl - self.shadow_mode.active_pnl:.0f}$ besser! "
                               f"Parameter: SL={best.params['sl_pct']}% Trail={best.params['trail_pct']}%")
        # Meta-Voting Ranking loggen
        ranking = self.meta_voting.get_agent_ranking()
        if ranking:
            top3 = ", ".join(f"{a}:{w:.2f}" for a, w in ranking[:3])
            log.info("META", f"Top-Agenten: {top3}")

    def _auto_optimize(self):
        """Auto-Optimizer: sucht beste Parameter alle 30 Min (wenn aktiviert)."""
        if not self.auto_optimize_enabled:
            return
        if self.bt_optimizer.is_running:
            return
        try:
            from backtest.engine import BacktestEngine
            bt = BacktestEngine(self.config)
            coin = "BTC/USDC"
            snap = self.data_agent.fetch_snapshot(coin, "1h", 300)
            if not snap or not hasattr(snap, '_df') or snap._df is None:
                return
            df = snap._df
            if len(df) < 100:
                return

            result = self.bt_optimizer.grid_search(bt, df, coin=coin,
                sl_range=(3, 4, 5), trail_range=(1.0, 1.5, 2.0),
                pos_range=(15, 20, 25))

            if result.get("best"):
                best = result["best"]
                old_sl = self.config.risk.stop_loss_pct
                old_trail = self.config.risk.trailing_stop_pct
                self.config.risk.stop_loss_pct = best["sl"]
                self.config.risk.trailing_stop_pct = best["trail"]
                self.config.trading.position_size_pct = best["pos"]
                self.config.save()
                log.info("AUTO-OPT", f"Parameter optimiert: SL {old_sl}%→{best['sl']}% "
                                     f"Trail {old_trail}%→{best['trail']}% Pos {best['pos']}%")
        except Exception as e:
            log.warn("AUTO-OPT", f"Fehler: {str(e)[:40]}")

    # === SPLIT-1: Reporting-Cluster umgezogen nach runtime/reporting.py ===
    def generate_analyse_export(self) -> str:
        """SPLIT-1: siehe runtime/reporting.py"""
        if getattr(self, "reporting", None) is None:
            return "Reporting-Modul nicht geladen"
        return self.reporting.analyse_export()

    def _daily_report(self):
        """SPLIT-1: siehe runtime/reporting.py"""
        if getattr(self, "reporting", None) is not None:
            self.reporting.daily_report()

    def _weekly_report(self):
        """SPLIT-1: siehe runtime/reporting.py"""
        if getattr(self, "reporting", None) is not None:
            self.reporting.weekly_report()

    def _regime_lernen_tick(self):
        """[REGIME-LERNEN 10.08.2026] Taeglicher Lern-Lauf des Regime-Filters.

        Misst, was die geblockten Kaufgelegenheiten der letzten Tage gebracht
        haetten, und passt min_confirmations an - aber nur bei eindeutiger
        Datenlage und innerhalb harter Grenzen (2 bis 4, hoechstens eine Stufe
        je Lauf, danach 3 Tage Sperrfrist). Jede Entscheidung wird mit
        Begruendung und Marktphase gespeichert.

        Vollstaendig gekapselt: ein Fehler hier beruehrt den Handel nicht.
        """
        try:
            from features.regime_adaptiv import taeglicher_lauf
            e = taeglicher_lauf(app=self)
            log.info("REGIME-LERN", f"Lauf fertig: {e.get('entscheidung')} "
                                    f"({e.get('faelle')} Stunden gemessen, "
                                    f"{e.get('rendite', 0):+.2f} %)")
        except Exception as _e:
            log.warn("REGIME-LERN", f"Lauf fehlgeschlagen: {str(_e)[:100]}")

    def _chartanalyse_agent_tick(self):
        """[CHARTANALYSE-AGENT 07.08.2026] Taeglicher Messlauf der Chartanalyse.

        Reine Messung: der Agent rechnet den Backtest ueber frische Kurse neu
        und vergleicht mit dem Vorlauf. Er veraendert weder Parameter noch
        Handelsverhalten - ein Agent, der seine Schwellen nachzieht bis die
        Zahlen gefallen, erzeugt nur eine Illusion (Overfitting).

        Vollstaendig gekapselt: ein Fehler hier darf den Bot nicht beruehren.
        """
        try:
            from features.chartanalyse_agent import taeglicher_lauf
            erg = taeglicher_lauf(telegram=getattr(self, "telegram", None))
            n = len(erg.get("maerkte", []))
            meld = len(erg.get("meldungen", []))
            log.info("CHART-AGENT", f"Tageslauf fertig: {n} Maerkte gemessen, "
                                    f"{meld} Auffaelligkeit(en), "
                                    f"{len(erg.get('fehler', []))} Fehler")
        except Exception as _e:
            log.warn("CHART-AGENT", f"Tageslauf fehlgeschlagen: {str(_e)[:100]}")

    def _asset_erlaubt(self, symbol):
        """[BTC-ONLY 07.08.2026] Darf in diesem Coin NEU gekauft werden?

        Liest nur_asset aus dem aktiven Modus (config/settings.py TradingMode).
        Leer = alle Coins (Verhalten wie bisher). "BTC" = nur Bitcoin.

        BESTANDSSCHUTZ - der wichtigste Punkt an dieser Funktion:
        Sie wird AUSSCHLIESSLICH vor NEUEN Kaeufen gefragt. Offene Positionen
        in gesperrten Coins laufen vollstaendig normal weiter - Stop-Loss,
        Trailing-Stop und Verkauf bleiben unberuehrt, weil der Exit-Monitor
        (runtime/exit_monitor.py) und die SELL-Seite der RiskEngine
        (risk/engine.py:81 "SELLS IMMER genehmigen") diese Funktion nie
        aufrufen. Beim Umschalten auf BTC-Only werden ETH und SOL also
        ordentlich zu Ende verwaltet und nicht zu Geisterpositionen.

        Rueckgabe: (erlaubt: bool, grund: str)
        """
        try:
            modus = self.config.get_active_mode()
            nur = (getattr(modus, "nur_asset", "") or "").strip().upper()
            if not nur:
                return True, ""
            asset = symbol.split("/")[0].upper() if "/" in symbol else symbol.upper()
            if asset == nur:
                return True, ""
            return False, f"Modus {modus.name}: nur {nur} erlaubt, {asset} gesperrt"
        except Exception as _e:
            # Wie beim Regime-Filter: ein Fehler in der Pruefung darf den
            # Handel nicht heimlich anhalten. Laut melden, durchlassen.
            log.warn("MODUS", f"Asset-Pruefung fehlgeschlagen ({str(_e)[:60]}) "
                              f"- Kauf durchgelassen")
            return True, ""

    def _telemetrie_verkauf(self, **felder):
        """[VERKAUFS-LUECKE 10.08.2026] Bruecke fuer runtime/exit_monitor.py.

        Verkaeufe laufen dort bewusst am EventBus vorbei (Geschwindigkeit),
        deshalb erreichten sie die Telemetrie nie: 52.198 Kaufpruefungen
        standen null Verkaeufen gegenueber. Als am 07.08. SOL verkauft wurde,
        war der Grund hinterher nicht mehr feststellbar - system.log war
        bereits rotiert.

        Wirft nie nach aussen: Der Verkauf ist zum Aufrufzeitpunkt bereits
        ausgefuehrt, ein Protokollfehler darf daran nichts mehr aendern.
        """
        try:
            _tel = getattr(self, "telemetrie", None)
            if _tel is None:
                from core.telemetrie import Telemetrie
                _tel = self.telemetrie = Telemetrie()
            felder.setdefault("cycle_phase", self.state.get("cycle_phase", ""))
            return _tel.protokolliere_verkauf(**felder)
        except Exception as _tv_err:
            log.warn("TELEMETRIE", f"Verkauf nicht protokolliert: {str(_tv_err)[:80]}")
            return ""

    def _markt_schnappschuss(self):
        """[MARKTDATEN-HISTORIE 11.08.2026] Ein Messpunkt in die Telemetrie.

        Sammelt jedes Feld einzeln und gekapselt. Faellt eine Quelle aus,
        entsteht in dieser Spalte eine Luecke - nicht ein Loch in der ganzen
        Zeile und schon gar kein Fehler im Bot. Eine Zeitreihe mit ein paar
        leeren Feldern ist auswertbar; eine, die bei der ersten Stoerung
        abbricht, ist es nicht.

        Wirft nie nach aussen.
        """
        def _hol(pfad, standard=None):
            """Liest verschachtelt und still: _hol('regime_detector.current_regime')."""
            try:
                wert = self
                for teil in pfad.split("."):
                    wert = getattr(wert, teil)
                return wert() if callable(wert) else wert
            except Exception:
                return standard

        def _preis(symbol):
            try:
                p = self._fetch_current_price(symbol)
                return float(p) if p else None
            except Exception:
                return None

        try:
            # [GEFUNDENE-PROBLEME #19, 11.08.2026] Frueher stand hier
            # isinstance(..., dict). self.state ist aber ein StateStore-Objekt
            # (app.py:161), KEIN dict - die Pruefung schlug also immer fehl,
            # s wurde jedes Mal zum leeren {} und JEDER Sentiment-Wert landete
            # als NULL in der Datenbank. 19 Messpunkte lang enthielt die
            # Marktdaten-Zeitreihe nur Zeitstempel, Preise und Kontostand.
            # Die Werte selbst waren die ganze Zeit da (fear_greed 29,
            # nupl 0.2, dxy 99.82 ...) - sie wurden nur weggeworfen.
            # Jetzt wird auf die Faehigkeit geprueft (hat .get?), nicht auf
            # den Typ: das deckt dict UND StateStore ab.
            _quelle = getattr(self, "state", None)
            s = _quelle if hasattr(_quelle, "get") else {}
            cash = equity = None
            offene = None
            try:
                # Quelle ist execution.get_balance(), nicht portfolio - das
                # Portfolio hat gar keine solche Methode. Erst nachgesehen
                # (execution/engine.py:490), dann verdrahtet: sonst waere die
                # Cash-Spalte still fuer immer leer geblieben.
                # Struktur ist verschachtelt: {"total": {...}, "free": {...}}
                # (execution/engine.py:497), NICHT flach. Ein direkter
                # bal["USDC"] haette ein Dict statt einer Zahl geliefert.
                bal = self.execution.get_balance()
                if isinstance(bal, dict):
                    topf = bal.get("free") or bal.get("total") or {}
                    if isinstance(topf, dict):
                        cash = float(topf.get("USDC", 0) or 0)
            except Exception:
                pass
            try:
                equity = float(self.portfolio.get_total_capital())
            except Exception:
                pass
            try:
                offene = len(self.risk_engine.open_positions)
            except Exception:
                pass

            _tel = getattr(self, "telemetrie", None)
            if _tel is None:
                from core.telemetrie import Telemetrie
                _tel = self.telemetrie = Telemetrie()
            # [GEFUNDENE-PROBLEME #20, 11.08.2026] Tote Quellen als LUECKE
            # aufzeichnen, nicht als Messwert.
            #
            # Faellt eine Quelle aus, schreibt _update_external_signals() ihren
            # Wert NICHT neu - der alte bleibt im State stehen. Reddit liefert
            # seit dem 403 vom 29.07. gar nichts mehr, im State steht aber
            # weiterhin 0.5. Ohne diese Pruefung landete diese 0.5 stuendlich
            # in der Zeitreihe und waere spaeter nicht mehr von einer echten
            # neutralen Messung zu unterscheiden.
            #
            # Fuers Ensemble ist das laengst geloest (gesunde_auswahl wirft
            # tote Quellen raus, E10-QUELLEN 29.07.) - fuer die Messung war es
            # noch offen. Dieselbe Haltung wie im Test festgehalten:
            # "fehlende Werte sind NULL, nicht 0 (0 waere eine Luege)".
            def _wenn_lebt(quelle, schluessel):
                # [GEFUNDENE-PROBLEME #30] ZWEI Bedingungen, nicht eine:
                # die Quelle muss sich seit dem Start einmal gemeldet haben
                # UND aktuell gesund sein. Vorher wurde nur auf "gesund"
                # geprueft - und unbekannte Quellen gelten bewusst als gesund.
                # Nach jedem Neustart landete deshalb ein bis zwei Messpunkte
                # lang der ALTE Wert aus dem State in der Zeitreihe, obwohl
                # die Quelle noch gar nichts geliefert hatte.
                try:
                    if not self.source_health.hat_gemeldet(quelle):
                        return None
                    if not self.source_health.ist_gesund(quelle):
                        return None
                except Exception:
                    pass
                return s.get(schluessel)

            # ============================================================
            # [BEFUND 95, 12.09.2026] EINGEFRORENE KURSE NICHT MITSCHREIBEN
            # ------------------------------------------------------------
            # Faellt der Kursabruf aus, gibt fetch_current_price den ALTEN
            # Wert aus dem Cache zurueck - ohne Altersangabe, weil
            # data/market_data.py:11 keinen Zeitstempel fuehrt. Der alte
            # Wert landete dann im 15-Minuten-Takt in der Zeitreihe und sah
            # aus wie eine frische Messung. Gemessen: 129 von 2.162 Zeilen
            # (6,0 %) ueber 15 von 24 Tagen, laengste Serie 6 h 45 min.
            #
            # EINE LUECKE IST EHRLICH, EIN EINGEFRORENER WERT IST ES NICHT.
            # Die Luecke sieht man; den wiederholten Wert haelt jede
            # Auswertung fuer eine Messung.
            #
            # Erkannt wird das am Pruefmuster aus CLAUDE.md: Werte, die
            # identisch sein DUERFEN, aber nicht identisch sein SOLLTEN.
            # Drei Kurse zu zwei Zeitpunkten sind nie auf acht Stellen
            # gleich - wenn doch, hat sich nichts bewegt, weil nichts
            # abgerufen wurde.
            #
            # BEWUSST NICHT in fetch_current_price selbst: die Funktion
            # versorgt auch den Stop-Loss (runtime/exit_monitor.py:657).
            # Ihr bei altem Cache den Preis zu verweigern, waere eine
            # Verhaltensaenderung mit Kapitalrisiko - der Bot koennte dann
            # eine Position nicht mehr schliessen. Hier wird nur das
            # AUFSCHREIBEN abgesichert.
            # ============================================================
            _kurse_jetzt = (_preis("BTC/USDC"), _preis("ETH/USDC"),
                            _preis("SOL/USDC"))
            _alle_da = all(k is not None and k > 0 for k in _kurse_jetzt)
            _vorher = getattr(self, "_markt_kurse_vorher", None)
            if _alle_da and _vorher is not None and _kurse_jetzt == _vorher:
                self._markt_eingefroren = getattr(
                    self, "_markt_eingefroren", 0) + 1
                # Nur beim ersten Mal und dann alle vier Versuche melden -
                # eine Warnung, die alle 15 Minuten kommt, liest niemand.
                if self._markt_eingefroren in (1, 4) or                         self._markt_eingefroren % 8 == 0:
                    log.warn("TELEMETRIE",
                             "Kurse unveraendert seit dem letzten Schnappschuss "
                             "(%dx in Folge) - keine Zeile geschrieben. Lieber "
                             "eine Luecke als ein eingefrorener Wert "
                             "(Befund 95)." % self._markt_eingefroren)
                return
            if _alle_da:
                if getattr(self, "_markt_eingefroren", 0):
                    log.info("TELEMETRIE",
                             "Kurse bewegen sich wieder - %d Schnappschuesse "
                             "ausgelassen." % self._markt_eingefroren)
                self._markt_eingefroren = 0
                self._markt_kurse_vorher = _kurse_jetzt

            _tel.markt_schnappschuss(
                fear_greed=s.get("fear_greed"),
                nupl=s.get("nupl"), nupl_zone=s.get("nupl_zone"),
                dxy=s.get("dxy"), dxy_trend=s.get("dxy_trend"),
                funding_score=_wenn_lebt("funding", "funding_score"),
                whale_score=_wenn_lebt("whale", "whale_score"),
                onchain_score=_wenn_lebt("onchain", "onchain_score"),
                reddit_score=_wenn_lebt("reddit", "reddit_score"),
                capitol_score=_wenn_lebt("capitol", "capitol_score"),
                cycle_phase=s.get("cycle_phase"),
                regime=_hol("regime_detector.current_regime"),
                btc_preis=_kurse_jetzt[0], eth_preis=_kurse_jetzt[1],
                sol_preis=_kurse_jetzt[2],
                equity=equity, cash=cash, offene_pos=offene)
        except Exception as _mh_e:
            log.warn("MARKT-HISTORIE", f"Schnappschuss ausgefallen: {str(_mh_e)[:80]}")

    def _git_commit(self):
        """[SCHRITT 3, 13.08.2026] Der Codestand, einmal je Lauf ermittelt.

        WOFUER: Er beweist, dass waehrend des Messfensters nichts geaendert
        wurde. Ohne ihn ist jede Auswertung anfechtbar - "lief das die
        ganzen zwei Wochen wirklich mit demselben Code?" waere dann nur
        noch aus dem Gedaechtnis zu beantworten.

        Einmal ermittelt und gemerkt: ein Unterprozess je Entscheidung
        waere bei ~11.000 Entscheidungen am Tag absurd teuer.
        """
        if hasattr(self, "_git_commit_cache"):
            return self._git_commit_cache
        stand = ""
        try:
            import subprocess
            stand = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, timeout=5,
                cwd=os.path.dirname(os.path.abspath(__file__))
            ).stdout.decode("utf-8", "replace").strip()
        except Exception as _g_e:
            log.warn("TELEMETRIE", f"git_commit nicht ermittelbar "
                                   f"({type(_g_e).__name__}) - die Spalte "
                                   f"bleibt leer, Auswertung kann den "
                                   f"Codestand dann nicht belegen")
        self._git_commit_cache = stand
        if stand:
            log.info("TELEMETRIE", f"Codestand fuer die Telemetrie: {stand}")
        return stand

    def _feature_snapshot_id(self, symbol):
        """[SCHRITT 3, 13.08.2026] Merkmals-Schnappschuss holen oder anlegen.

        WOFUER: Ohne die Indikatorwerte des Entscheidungszeitpunkts ist
        eine Entscheidung hinterher nicht reproduzierbar und kein
        Neutraining moeglich. Kurse kann man nachladen, den Rechenstand
        des Bots nicht.

        QUELLE: snap._df, NICHT snapshot.indicators. Das Dict in
        data/market_data.py:76 enthaelt nur sieben Werte; EMA200,
        MACD-Histogramm und die Bollinger-Baender werden zwar berechnet,
        stehen aber ausschliesslich im angehaengten DataFrame.

        SPARSAMKEIT: Je Coin und Kerze wird nur EIN Schnappschuss
        geschrieben. Mehrere Entscheidungen im selben Takt teilen sich
        ihn - sonst entstuenden aus ~11.000 Entscheidungen am Tag ebenso
        viele fast identische Zeilen.
        """
        try:
            snap = getattr(self.data_agent, "_last_snapshots", {}).get(symbol)
            if snap is None:
                return ""
            df = getattr(snap, "_df", None)
            if df is None or len(df) == 0:
                return ""

            try:
                kerze = str(df.index[-1])
            except Exception:
                kerze = ""
            schluessel = (symbol, kerze)

            if not hasattr(self, "_feat_cache"):
                self._feat_cache = {}
            if schluessel in self._feat_cache:
                return self._feat_cache[schluessel]

            _tel = getattr(self, "telemetrie", None)
            if _tel is None:
                from core.telemetrie import Telemetrie
                _tel = self.telemetrie = Telemetrie()

            # [FIX 13.08.2026, beim Pruefen nach dem Neustart gefunden]
            # snap._df kommt aus data/market_data.py und enthaelt nur die
            # Indikatoren, die der Handelspfad braucht: RSI, EMA20, EMA50,
            # MACD, Bollinger, ADX, ATR. Es FEHLTEN EMA200, StochRSI, OBV,
            # VWAP, TSI und die abgeleiteten Merkmale (returns, volatility,
            # volume_ratio, high_low_range, close_to_ema20) - im ersten
            # geschriebenen Schnappschuss waren 12 Felder leer.
            #
            # calc_all_indicators() rechnet den vollen Satz. Der Aufruf
            # steht bewusst HIER und nicht in market_data.py: Dort waere er
            # im Handelspfad und wuerde bei jedem Kurs-Update Rechenzeit
            # kosten. Hier laeuft er nur einmal je Coin und Kerze (Cache
            # oben) und ausschliesslich fuer das Protokoll.
            #
            # Sven am 13.08. zum Umfang: "ich würde auch sagen alle".
            try:
                from features.indicators import calc_all_indicators
                df_voll = calc_all_indicators(df)
            except Exception as _ci_e:
                df_voll = df
                if not getattr(self, "_feat_voll_gemeldet", False):
                    self._feat_voll_gemeldet = True
                    log.warn("FEATURE-SNAPSHOT",
                             f"Vollsatz nicht berechenbar "
                             f"({type(_ci_e).__name__}: {str(_ci_e)[:60]}) - "
                             f"es werden nur die Handelspfad-Indikatoren "
                             f"protokolliert (einmalige Meldung)")

            fid = _tel.feature_snapshot(
                symbol, df=df_voll,
                timeframe=getattr(snap, "timeframe", ""),
                # Die letzte Kerze im laufenden Betrieb ist noch offen -
                # MASTERPROMPT.md Abschnitt C verlangt, dass das sichtbar
                # ist, statt sie stillschweigend als final zu behandeln.
                kerze_offen=True)

            # Cache klein halten: nur die jeweils letzte Kerze je Coin.
            self._feat_cache = {k: v for k, v in self._feat_cache.items()
                                if k[0] != symbol}
            self._feat_cache[schluessel] = fid
            return fid
        except Exception as _f_e:
            log.warn("FEATURE-SNAPSHOT",
                     f"{symbol}: nicht geschrieben "
                     f"({type(_f_e).__name__}: {str(_f_e)[:60]}) - diese "
                     f"Entscheidung ist spaeter nicht reproduzierbar")
            return ""

    def _telemetrie_kontext(self, intent):
        """[SCHRITT 3, 13.08.2026] Die Zusatzfelder fuer eine Entscheidung.

        Alles hier ist reines Aufschreiben - kein Wert beeinflusst den
        Handel. Faellt ein Einzelwert aus, bleibt genau seine Spalte leer
        und die Entscheidung wird trotzdem protokolliert.
        """
        symbol = getattr(intent, "symbol", "")
        kontext = {
            "git_commit": self._git_commit(),
            "cycle_id": getattr(self, "_cycle_id", 0),
            "feature_snapshot_id": self._feature_snapshot_id(symbol),
        }

        # Faellt ein Einzelwert aus, bleibt genau seine Spalte leer - aber
        # nicht stillschweigend: der Ausfall wird EINMAL gemeldet. Eine
        # Spalte, die zwei Wochen lang unbemerkt NULL bleibt, ist genau
        # der Fehler, den dieses ganze Vorhaben verhindern soll.
        if not hasattr(self, "_kontext_fehler_gemeldet"):
            self._kontext_fehler_gemeldet = set()

        def _weich(name, holen):
            try:
                kontext[name] = holen()
            except Exception as _e:
                if name not in self._kontext_fehler_gemeldet:
                    self._kontext_fehler_gemeldet.add(name)
                    log.warn("TELEMETRIE",
                             f"Kontextfeld '{name}' faellt aus "
                             f"({type(_e).__name__}: {str(_e)[:70]}) - die "
                             f"Spalte bleibt leer (einmalige Meldung)")

        _weich("regime", lambda: str(
            getattr(self.regime_detector, "current_regime", "") or ""))
        _weich("fear_greed", lambda: int(self.state.get("fear_greed", 50)))
        _weich("spread_pct", lambda: float(self._spread_cache.get(symbol, 0.0)))
        # [13.08.] source_health hat KEIN gesunde_quellen() - beim Testen
        # aufgefallen. Richtig ist status_zeile(), das lebende und
        # ausgefallene Quellen im Klartext liefert.
        _weich("quellen_gesund",
               lambda: self.source_health.status_zeile()[:200])

        # Erwartete Kosten einer Runde: Gebuehr ein + aus, dazu der
        # gemessene Schlupf je Muenze (Punkt 23) und der aktuelle Spread.
        def _kosten():
            gebuehr = 2 * 0.10
            schlupf = 2 * 0.06
            spread = float(self._spread_cache.get(symbol, 0.0) or 0.0)
            return round(gebuehr + schlupf + spread, 4)
        _weich("kosten_erwartet_pct", _kosten)

        # Alter der zugrunde liegenden Kerze in Sekunden.
        def _alter():
            snap = getattr(self.data_agent, "_last_snapshots", {}).get(symbol)
            ts = getattr(snap, "timestamp", None)
            if ts is None:
                return None
            return round((datetime.now(timezone.utc) - ts).total_seconds(), 1)
        _weich("daten_alter_sec", _alter)

        return kontext

    def _telemetrie_schreiben(self, intent, equity=0.0, cycle="", grund=None):
        """[TELEMETRIE 06.08.2026] Haelt EINE Kaufpruefung im Protokoll fest.

        Zentral, weil ein Kandidat an MEHREREN Stellen sterben kann und jede
        davon protokolliert gehoert. Erste Fassung schrieb nur an der
        Risk-Pruefung mit - dadurch fehlte SOL komplett in der Datenbank,
        weil der Regime-Filter frueher zuschlaegt (app.py _on_market_update).
        Eine Telemetrie mit Loechern ist keine Telemetrie.

        grund=None  -> Entscheidung aus intent.risk_approved/.risk_reason
        grund="..." -> erzwungene Ablehnung mit diesem Text (Regime, Smart-Entry)

        Wirft nie nach aussen: ein Protokollfehler darf den Handel nie anhalten.
        """
        try:
            _tel = getattr(self, "telemetrie", None)
            if _tel is None:
                from core.telemetrie import Telemetrie
                _tel = self.telemetrie = Telemetrie()
            if grund is not None:
                intent.risk_approved = False
                intent.risk_reason = grund
            _eid = _tel.protokolliere(
                intent, {"total_equity": equity}, cycle,
                offene_positionen=sum(
                    1 for p in self.risk_engine.open_positions.values()
                    if p.get("active")),
                config_version=getattr(self.config, "version", ""),
                # [SCHRITT 3, 13.08.2026] Codestand, Marktlage,
                # Merkmals-Schnappschuss und Kostenannahme mitschreiben.
                kontext=self._telemetrie_kontext(intent))
            # [SCHRITT 3] Kennung am intent merken. Entsteht spaeter eine
            # Position, wird sie in _execute_approved_trade nachgetragen -
            # erst diese Bruecke macht das R-Vielfache berechenbar.
            try:
                intent._evaluation_id = _eid
            except Exception:
                pass          # intent koennte slots haben; dann eben nicht
        except Exception as _tel_err:
            log.warn("TELEMETRIE", f"Protokoll fehlgeschlagen: {str(_tel_err)[:80]}")

    def _dca_telemetrie(self, coin, preis, grund, betrag=0.0, equity=0.0,
                        cycle="", score=5, genehmigt=False):
        """[BEFUND 40, 19.08.2026] Haelt eine DCA-Entscheidung im Protokoll fest.

        WARUM ES DIESE METHODE GIBT

        Der DCA-Pfad macht 538 von 547 Kaeufen - 98,4 %. Er lief bis heute
        vollstaendig an der Telemetrie vorbei:

            grep -n "risk_engine.check(" app.py     -> genau EIN Treffer (1206)
            grep -n "_telemetrie_schreiben(" app.py -> sechs Treffer, alle
                                                       zwischen 1010 und 1214

        Alle sechs liegen im Signal-Pfad. Im DCA-Block (2700-2996) stand
        keiner. Folge: Die 188.955 protokollierten Ablehnungen beschreiben
        ausschliesslich den Weg mit 1,6 % der Kaeufe. Vom Hauptweg gab es
        keine einzige aufgezeichnete Entscheidung - weder Zusage noch
        Ablehnung.

        Belegt durch zwei unabhaengige Quellen: telemetrie.db kennt seit dem
        06.08. genau neun angenommene Kaeufe, trades_v5.json genau neun
        Signal-Kaeufe - auf die Minute dieselben. Die vier DCA-Kaeufe im
        selben Zeitraum fehlen vollstaendig.

        WAS SIE AENDERT: nichts am Handel. Sie schreibt nur mit.

        Wirft nie nach aussen - ein Protokollfehler darf den Handel nie
        anhalten. Dasselbe Muster wie _telemetrie_schreiben().
        """
        try:
            from core.events import DecisionIntent, Side
            absicht = DecisionIntent(
                symbol=coin, side=Side.BUY, confidence=0.7,
                entry_price=preis or 0.0, amount_usd=betrag or 0.0,
                strategy_id="DCA_FEAR_GREED", strategy_name="Fear & Greed DCA",
                entry_reason="DCA-Pfad", score=score, agent_id="direct_dca")
            absicht.risk_approved = bool(genehmigt)
            absicht.risk_reason = grund
            self._telemetrie_schreiben(
                absicht, equity=equity, cycle=cycle,
                grund=None if genehmigt else grund)
            return absicht
        except Exception as _dt_e:
            log.warn("TELEMETRIE",
                     f"DCA-Protokoll fehlgeschlagen ({coin}): {str(_dt_e)[:70]}")
            return None

    def _waechter_signalpfad(self):
        """[WAECHTER 06.08.2026] Meldet verschwundene Kauf-Kandidaten.

        HINTERGRUND: Am 06.08.2026 zeigte data_store/system.log 14.986 erzeugte
        BUY-Signale und NULL Aufrufe von RiskEngine.check(). Die Kandidaten
        verschwanden zwischen _on_market_update und _on_signal, weil der
        Event-Bus Subscriber-Exceptions verschluckte (core/bus.py). Es gab
        keine Instanz, die das bemerkt haette - der Bot hielt sich fuer gesund.

        Dieser Waechter ist diese Instanz. Er aendert NICHTS am Handel; er
        vergleicht nur zwei Zaehler und schlaegt Alarm. Reine Diagnose (S1).

            _sig_erzeugt   - Kandidat existiert   (_on_market_update)
            _sig_wartet    - bewusst zurueckgestellt (Smart-Entry)
            _sig_bei_risk  - Risk-Pruefung erreicht (_on_signal)

        Erwartung:  erzeugt == wartet + bei_risk.
        Jede Luecke ist ein stiller Verlust und damit ein Befund.
        """
        # [TOEPFE SCHRITT 1 - 07.08.2026] Sicherheitsnetz: Positionen koennen
        # an mehreren Stellen entstehen (Signal-Pfad, DCA-Pfad, TWAP,
        # Wiederherstellung aus bot_state.json). Statt jede einzeln umzubauen
        # und dabei eine zu uebersehen, werden fehlende Kennungen hier zentral
        # nachgetragen. Reine Strukturarbeit, kein Handelseingriff.
        try:
            _ergaenzt = self.risk_engine.positions_kennungen_pruefen()
            if _ergaenzt:
                log.info("TOEPFE", f"{_ergaenzt} Position(en) nachtraeglich mit "
                                   f"Kennung versehen")
        except Exception as _pk_err:
            log.warn("TOEPFE", f"Kennungspruefung fehlgeschlagen: {str(_pk_err)[:60]}")

        erzeugt = getattr(self, "_sig_erzeugt", 0)
        wartet = getattr(self, "_sig_wartet", 0)
        bei_risk = getattr(self, "_sig_bei_risk", 0)

        if erzeugt == 0:
            return  # noch keine Kandidaten - nichts zu bewerten

        verloren = erzeugt - wartet - bei_risk
        quote = (bei_risk / erzeugt * 100) if erzeugt else 0.0

        if verloren <= 0:
            # Zaehler zuruecksetzen, sonst gilt eine laengst geschlossene
            # Luecke bei der naechsten Momentaufnahme als "zweites Mal".
            self._sig_verloren_vorher = 0
            log.info("WAECHTER", f"Signalpfad in Ordnung: {erzeugt} Kandidaten -> "
                                 f"{bei_risk} geprueft, {wartet} zurueckgestellt "
                                 f"({quote:.0f}% Durchsatz)")
            return

        # ==============================================================
        # [15.09.2026] ERGAENZUNG zum Waechter vom 06.08.
        #
        # Die drei Zaehler werden an verschiedenen Stellen des Pfades
        # hochgezaehlt. Liest der Waechter genau in dem Moment, in dem
        # ein Kandidat schon erzeugt, aber noch nicht bei der
        # Risk-Pruefung angekommen ist, fehlt genau EINER - und das ist
        # kein Verlust, sondern eine Momentaufnahme mitten im Vorgang.
        #
        # Am 15.09. im Log belegt. Die Zaehler sind KUMULATIV, deshalb
        # muesste eine echte Luecke bestehen bleiben:
        #
        #   12:14   486 -> 486 geprueft      in Ordnung
        #   12:19   1 von 538 fehlt          Warnung
        #   12:24   590 -> 590 geprueft      in Ordnung   <- Luecke zu
        #   12:29   1 von 636 fehlt          Warnung
        #   12:34   669 -> 669 geprueft      in Ordnung   <- Luecke zu
        #
        # Sie schliesst sich jedes Mal. Der Kandidat war nur unterwegs.
        #
        # Warum das repariert gehoert, obwohl nichts kaputt ist: Ein
        # Waechter, der regelmaessig falschen Alarm gibt, wird
        # ueberlesen - und dann faellt der echte Fall auch nicht mehr
        # auf. Eine Warnung, die man wegdruecken lernt, ist schlimmer
        # als keine.
        #
        # Deshalb: Erst melden, wenn die Luecke bei ZWEI
        # aufeinanderfolgenden Pruefungen besteht. Ein echter Verlust
        # bleibt bestehen (kumulative Zaehler), eine Momentaufnahme
        # nicht.
        # ==============================================================
        _vorher = getattr(self, "_sig_verloren_vorher", 0)
        self._sig_verloren_vorher = verloren

        if _vorher <= 0:
            # ERSTE Beobachtung einer Luecke. Genau so sieht eine
            # Momentaufnahme aus, deshalb hier noch keine Warnung -
            # sondern die naechste Pruefung abwarten. Ist der Kandidat
            # nur unterwegs, ist die Luecke in fuenf Minuten zu.
            log.info("WAECHTER",
                     f"Signalpfad: {verloren} Kandidat(en) noch unterwegs "
                     f"(erzeugt {erzeugt}, geprueft {bei_risk}). Kein Alarm - "
                     f"erst wenn die Luecke bei der naechsten Pruefung noch "
                     f"besteht, ist sie echt.")
            return

        anteil = verloren / erzeugt * 100
        stufe = log.error if anteil >= 20 else log.warn
        # Der Verweis auf bus_errors.log nur, wenn es die Datei gibt.
        # Stand dort frueher immer - und wer nachsah, fand nichts und
        # wusste nicht, ob das gut oder schlecht ist.
        _bf = os.path.join(DATA_DIR, "bus_errors.log")
        _hinweis = (f" Ursache steht in {_bf}" if os.path.exists(_bf)
                    else " (bus_errors.log existiert nicht - der Event-Bus"
                         " hat also nichts verschluckt)")
        stufe("WAECHTER",
              f"{verloren} von {erzeugt} Kauf-Kandidaten ({anteil:.0f}%) haben die "
              f"Risk-Pruefung NIE erreicht, und zwar bei zwei Pruefungen "
              f"hintereinander (vorher {_vorher}). Geprueft: {bei_risk}, "
              f"zurueckgestellt: {wartet}.{_hinweis}")

        try:
            bus_fehler = self.bus.get_stats().get("BUS_ERROR", 0)
            if bus_fehler:
                log.error("WAECHTER", f"Event-Bus meldet {bus_fehler} verschluckte "
                                      f"Subscriber-Fehler - das ist die "
                                      f"wahrscheinlichste Ursache.")
        except Exception:
            pass

        # Telegram nur bei massivem Verlust, und nur einmal je Vorfall -
        # der Waechter soll warnen, nicht spammen.
        if anteil >= 20 and not getattr(self, "_waechter_gemeldet", False):
            self._waechter_gemeldet = True
            try:
                if getattr(self, "telegram", None) is not None:
                    self.telegram.send(
                        f"⚠️ Signalpfad-Warnung\n\n{verloren} von {erzeugt} "
                        f"Kauf-Kandidaten ({anteil:.0f}%) erreichen die "
                        f"Risk-Pruefung nicht.\n\nDer Bot handelt deshalb "
                        f"weniger als er sollte. Details: bus_errors.log")
            except Exception as _tg_err:
                log.warn("WAECHTER", f"Telegram-Meldung fehlgeschlagen: "
                                     f"{str(_tg_err)[:60]}")

    def _heartbeat(self):
        """SPLIT-1: siehe runtime/reporting.py"""
        if getattr(self, "reporting", None) is not None:
            self.reporting.heartbeat()

    # === SPLIT-2: State-Cluster umgezogen nach runtime/state_manager.py ===
    def _auto_save(self):
        """SPLIT-2: siehe runtime/state_manager.py"""
        if getattr(self, "state_manager", None) is None:
            log.error("STATE", "state_manager fehlt - _auto_save uebersprungen!")
            return
        return self.state_manager.auto_save()

    def _restore_positions(self):
        """SPLIT-2: siehe runtime/state_manager.py"""
        if getattr(self, "state_manager", None) is None:
            log.error("STATE", "state_manager fehlt - _restore_positions uebersprungen!")
            return
        _ergebnis = self.state_manager.restore_positions()
        self._sync_paper_bestand()
        return _ergebnis

    def _sync_paper_bestand(self):
        """[FIX 05.08.2026] Paper-Bestand aus den wiederhergestellten
        Positionen auffuellen.

        BEFUND: execution/engine.py:36 setzt beim Start
        _paper_balances = {"USDC": initial_paper_balance} - also NUR USDC,
        keine Coin-Bestaende. bot_state.json fuehrt die offenen Positionen
        aber weiter. Nach jedem Neustart standen damit Positionen im State,
        denen auf der Paper-Boerse kein Bestand gegenueberstand.
        Folge, live beobachtet am 05.08.2026 01:58:02: ADA loeste den
        Trailing-Stop bei +19,37 % aus, der Verkauf scheiterte mit
        "SELL ADA/USDC abgelehnt - Bestand 0, angefordert 320.779720
        (Geister-Position?)", danach "REJECTION-LIMIT: 10 Rejects in Folge!
        Bot pausiert 15 Min". Das ist der Mechanismus hinter den 7.598
        Sleep-Mode-Zeilen im 24-Stunden-Log - ein Gewinn von +19 % war
        nicht realisierbar.
        live/state_recovery.py deckt diesen Fall nicht ab: es verlangt
        runner.connected und liest fetch_balance() von der Boerse, greift
        also nur im Live-Modus.
        """
        try:
            if not getattr(self.execution, "_paper_mode", False):
                return
            bal = self.execution._paper_balances
            ergaenzt = []
            for sym, pos in (self.risk_engine.open_positions or {}).items():
                if not isinstance(pos, dict) or not pos.get("active"):
                    continue
                qty = float(pos.get("qty") or 0)
                if qty <= 0:
                    continue
                asset = sym.split("/")[0]
                if bal.get(asset, 0) < qty:
                    bal[asset] = qty
                    ergaenzt.append(f"{asset}={qty:.6f}")
            if ergaenzt:
                log.info("EXEC", "Paper-Bestand aus State ergaenzt: "
                                 + ", ".join(ergaenzt))
        except Exception as _e:
            log.warn("EXEC", f"Paper-Bestand-Sync fehlgeschlagen: {str(_e)[:100]}")

    def _run_startup_diagnostic(self):
        """Selbsttest beim Start: Prueft alle Komponenten und loggt konkrete Fehler."""
        def test_data():
            assert self.data_agent is not None, "DataAgent nicht initialisiert"
            assert hasattr(self.data_agent, 'price_cache'), "price_cache fehlt"

        def test_signal():
            assert self.signal_agent is not None, "SignalAgent nicht initialisiert"
            assert hasattr(self.signal_agent, 'analyze'), "analyze() fehlt"

        def test_risk():
            assert self.risk_engine is not None, "RiskEngine nicht initialisiert"
            assert hasattr(self.risk_engine, 'check'), "check() fehlt"
            assert hasattr(self.risk_engine, 'open_positions'), "open_positions fehlt"

        def test_execution():
            assert self.execution is not None, "Execution Engine nicht initialisiert"
            bal = self.execution.get_balance()
            assert bal is not None, "get_balance() liefert None"
            assert "total" in bal, "Balance-Format falsch (kein 'total')"

        def test_context():
            assert self.context_agent is not None, "ContextAgent nicht initialisiert"

        def test_news():
            # News laeuft im Scheduler als _news_tick - nur pruefen ob LLM-Analyzer existiert
            assert self.llm is not None or self.scheduler is not None, "Kein News-System verfuegbar"

        def test_journal():
            """[E10-JOURNAL 29.07.] Aus 'Auto-Repair' wurde eine echte Pruefung.

            Vorher wurden hier fehlende Methoden zur Laufzeit angeflanscht.
            Der clear()-Ersatz griff dabei auf `trades` statt `_trades` zu und
            hat deshalb nichts geleert - der Reset-Knopf im UI tat seit jeher
            nur so, als wuerde er wirken. Alle drei Methoden stehen jetzt fest
            in core/state_store.py. Fehlt eine, ist das ein Fehler und kein
            Fall fuer eine stille Reparatur.
            """
            assert self.journal is not None, "Journal nicht initialisiert"
            for _m in ("add", "save", "clear", "get_last", "get_all", "get_stats"):
                assert hasattr(self.journal, _m), f"Journal.{_m}() fehlt"

        def test_state():
            assert self.state is not None, "StateStore nicht initialisiert"
            self.state.get("test_key")  # Lese-Test

        # Alle Tests ausfuehren
        tests = {
            "data": test_data,
            "signal": test_signal,
            "risk": test_risk,
            "execution": test_execution,
            "context": test_context,
            "news": test_news,
            "journal": test_journal,
            "state": test_state,
        }
        results = self.health.run_diagnostic(tests)

        # Heartbeat fuer alle bestandenen Tests
        for name in results["passed"]:
            self.health.heartbeat(name, status="ok")

        # Fehlgeschlagene loggen
        if results["failed"]:
            log.warn("APP", f"⚠️ {len(results['failed'])} Komponenten fehlerhaft: {list(results['failed'].keys())}")

    def _start_heartbeat_pulse(self):
        """Sendet zentral alle 30s Heartbeats fuer alle Komponenten.

        Jede Komponente wird kurz gepingt:
        - data: price_cache muss existieren
        - signal: signal_agent muss analyze() koennen
        - risk: open_positions Dict muss existieren
        - execution: get_balance() muss funktionieren
        - context: context_agent muss existieren
        - news: state hat news_sentiment ODER scheduler laeuft

        Bei Fehler wird report_error() mit konkreter Exception aufgerufen.
        """
        import threading

        def _pulse():
            # [PULSE-DIAGNOSE 07.08.2026] Der Puls setzte nachweislich keine
            # Heartbeats: im Log vom 07.08. stand "context: Kein Heartbeat seit
            # 21536s" bei 5h59m Uptime - also seit dem Start kein einziger.
            # data/signal/risk sahen nur deshalb gesund aus, weil sie im
            # laufenden Betrieb an anderer Stelle gesetzt werden.
            # Auffaellig ist die Reihenfolge: ab Punkt 4 (execution) ist alles
            # tot. get_balance() geht ans Netz - haengt der Aufruf ohne Timeout,
            # steht der ganze Thread und Punkt 5-7 werden nie erreicht.
            # Diese Zaehler zeigen, ob der Puls laeuft und wo er stehenbleibt.
            self._pulse_runden = 0
            self._pulse_letzter_punkt = "start"
            while self._running:
                try:
                    self._pulse_runden += 1
                    _rundenstart = time.time()
                    # 1. DATA: price_cache lebt?
                    try:
                        if hasattr(self.data_agent, 'price_cache'):
                            self.health.heartbeat("data", status="ok")
                        else:
                            raise AttributeError("price_cache fehlt")
                    except Exception as e:
                        self.health.report_error("data", str(e), exception=e)

                    # 2. SIGNAL: analyze() existiert?
                    try:
                        if hasattr(self.signal_agent, 'analyze'):
                            self.health.heartbeat("signal", status="ok")
                        else:
                            raise AttributeError("analyze() fehlt")
                    except Exception as e:
                        self.health.report_error("signal", str(e), exception=e)

                    # 3. RISK: open_positions Dict?
                    try:
                        if hasattr(self.risk_engine, 'open_positions') and isinstance(self.risk_engine.open_positions, dict):
                            self.health.heartbeat("risk", status="ok")
                        else:
                            raise AttributeError("open_positions fehlt oder kein Dict")
                    except Exception as e:
                        self.health.report_error("risk", str(e), exception=e)

                    # 4. EXECUTION: get_balance() funktioniert?
                    self._pulse_letzter_punkt = "4-execution (get_balance, Netz)"
                    try:
                        bal = self.execution.get_balance()
                        if bal is not None and "total" in bal:
                            self.health.heartbeat("execution", status="ok")
                        else:
                            raise ValueError("get_balance() liefert ungueltige Daten")
                    except Exception as e:
                        self.health.report_error("execution", str(e), exception=e)

                    # 5. CONTEXT: agent existiert?
                    self._pulse_letzter_punkt = "5-context"
                    try:
                        if self.context_agent is not None:
                            self.health.heartbeat("context", status="ok")
                        else:
                            raise AttributeError("context_agent ist None")
                    except Exception as e:
                        self.health.report_error("context", str(e), exception=e)

                    # 6. NEWS: state oder scheduler laeuft?
                    try:
                        # News ist OK wenn state existiert (news laeuft im scheduler)
                        if self.state is not None and self.scheduler is not None:
                            self.health.heartbeat("news", status="ok")
                        else:
                            raise AttributeError("state oder scheduler fehlt")
                    except Exception as e:
                        self.health.report_error("news", str(e), exception=e)

                    # 7. SL/TP MONITOR: laeuft alle 30s (Eigen-Heartbeat)
                    # Der Monitor pingt sich selbst beim Start - hier nur Fallback
                    self._pulse_letzter_punkt = "7-sl_tp_monitor"
                    try:
                        self.health.heartbeat("sl_tp_monitor", status="ok")
                    except Exception:
                        pass

                    # 8. AUTO-RESTART-MONITOR mitfuettern.
                    #
                    # [BEFUND 56, 19.08.2026] Dieser Puls fuetterte bisher NUR
                    # self.health. self.auto_restart kennt dieselben fuenf Namen,
                    # bekam aber nie ein Lebenszeichen: grep auf
                    # "auto_restart.heartbeat" fand null Treffer. Folge: Alle
                    # fuenf standen dauerhaft auf "frozen" mit roter Ampel -
                    # gemessen 7,1 Stunden nach dem Start, waehrend health im
                    # selben Augenblick "healthy: true" meldete.
                    #
                    # Gefaehrlich war es nie: app.py registriert ohne
                    # restart_fn, die Neustart-Bedingung im Monitor ist damit
                    # immer falsch ("restarts": 0 nach sieben Stunden). Aber
                    # eine Ampel, die immer rot ist, wird nach zwei Tagen nicht
                    # mehr gelesen - dieselbe Lektion wie bei prozess_frische.py
                    # (Handbuch 4.49) und dauercheck.py (4.57).
                    #
                    # Bewusst NICHT pauschal: gefuettert wird nur, was health
                    # gerade als "ok" fuehrt. Sonst meldete der Waechter
                    # Gesundheit, waehrend eine Komponente einen Fehler wirft -
                    # das waere schlimmer als der Dauer-Rotalarm.
                    self._pulse_letzter_punkt = "8-auto_restart"
                    try:
                        _ar = getattr(self, "auto_restart", None)
                        if _ar is not None:
                            for _name in ("data", "signal", "risk",
                                          "execution", "context"):
                                _k = self.health._components.get(_name) or {}
                                if _k.get("status") == "ok":
                                    _ar.heartbeat(_name)
                    except Exception as _ar_e:
                        log.warn("HEARTBEAT",
                                 f"auto_restart nicht gefuettert: "
                                 f"{str(_ar_e)[:70]}")

                    # [PULSE-DIAGNOSE 07.08.2026] Runde vollstaendig durch.
                    # Erste Runde und danach alle 20 Runden (=10 Min) melden,
                    # damit im Log belegbar ist, dass der Puls wirklich laeuft.
                    self._pulse_letzter_punkt = "fertig"
                    _dauer = time.time() - _rundenstart
                    if self._pulse_runden == 1 or self._pulse_runden % 20 == 0:
                        log.info("HEARTBEAT", f"Puls-Runde {self._pulse_runden} "
                                              f"komplett in {_dauer:.1f}s")
                    elif _dauer > 10:
                        log.warn("HEARTBEAT", f"Puls-Runde {self._pulse_runden} "
                                              f"war langsam: {_dauer:.1f}s")

                except Exception as e:
                    log.error("HEARTBEAT", f"Pulse-Fehler bei Punkt "
                                           f"{getattr(self, '_pulse_letzter_punkt', '?')}: "
                                           f"{type(e).__name__}: {e}")

                # Alle 30 Sekunden pulsen (Timeout ist 120s, also 4x Sicherheit)
                time.sleep(30)

        t = threading.Thread(target=_pulse, daemon=True, name="HeartbeatPulse")
        t.start()
        log.info("HEALTH", "💓 Heartbeat-Pulse gestartet (alle 30s)")

    def _health_check(self):
        """Überprüft die System-Gesundheit mit detaillierten Fehlermeldungen."""
        health = self.health.check_all()
        if not health["healthy"]:
            # Detaillierte Tot-Meldung mit konkretem Grund
            dead_with_reason = health.get("dead_with_reason", {})
            if dead_with_reason:
                for name, reason in dead_with_reason.items():
                    log.warn("HEALTH", f"❌ {name}: {reason[:120]}")
            else:
                dead = ", ".join(health["dead_components"])
                log.warn("HEALTH", f"Tote Komponenten: {dead}")

            # Permanently dead nach 3 Restarts -> kritischer Alert
            permanently_dead = health.get("permanently_dead", [])
            if permanently_dead:
                names = ", ".join(permanently_dead)
                log.error("HEALTH", f"🚨 KRITISCH: Komponenten sind nach 3 Restart-Versuchen tot: {names}")
                try:
                    self.telegram.send(f"🚨 Komponenten tot: {names}")
                except Exception:
                    pass

    def _reconcile(self):
        """Gleicht internen State mit Boerse ab."""
        try:
            issues = self.execution.reconcile()
            if issues:
                for issue in issues[:3]:
                    self.telegram.send(f"⚠️ Reconcile: {issue.get('type')} – {issue.get('symbol', '?')}")
        except Exception as e:
            log.error("RECONCILE", f"Fehler: {str(e)[:60]}")

    # ==========================================================
    # START / STOP
    # ==========================================================
    def start(self):
        """Startet das Trading-System."""
        if self._running:
            log.warn("APP", "System läuft bereits!")
            return

        self._running = True
        log.info("APP", "🚀 Trading Imperium V7 startet...")
        log.info("APP", f"   Modus: {self.config.trading.mode}")
        log.info("APP", f"   Coins: {len(self.config.trading.coins)}")
        log.info("APP", f"   Börse: {self.config.exchange.name}")

        # Runner initialisieren (Paper oder Live)
        if self.config.trading.mode == "live":
            key = self.config.exchange.api_key
            secret = self.config.exchange.api_secret
            if key and secret:
                try:
                    self.runner = LiveRunner(self.config)
                    success = self.runner.connect(key, secret, self.config.exchange.ccxt_id)
                    if success:
                        log.info("APP", "🔴 LIVE-MODUS aktiv!")
                        recovery = StateRecovery(self.runner, self.state, self.journal)
                        recovery.run()
                    else:
                        log.error("APP", "Live-Verbindung fehlgeschlagen → Paper")
                        self.runner = PaperRunner(self.config)
                except Exception as e:
                    log.error("APP", f"Live-Fehler: {e} → Paper")
                    self.runner = PaperRunner(self.config)
            else:
                log.warn("APP", "Keine API-Keys → Paper-Modus")
                self.runner = PaperRunner(self.config)
        else:
            self.runner = PaperRunner(self.config)
            log.info("APP", f"🟢 PAPER-MODUS (Balance: {self.config.trading.initial_paper_balance:,.0f} USDC)")

        # Scheduler starten
        self.scheduler.start()
        # Balance-Reporter mit-starten
        if hasattr(self, 'balance_reporter') and self.balance_reporter:
            self.balance_reporter.start()
        log.info("APP", "✅ Scheduler gestartet")

        # === SAMMLER MITSTARTEN [20.08.2026] ===
        #
        # Sven: "ohman das mit den ganzen befehlen wird mir echt viel und
        # bringt mich durcheinander, koenntest du das automatisieren?"
        #
        # Zwei Sammler muessen dauerhaft laufen, gehoeren aber nicht in den
        # Bot-Prozess (eigener Speicher, eigener Takt, duerfen abstuerzen
        # ohne den Bot mitzureissen). Bisher musste man sie von Hand
        # starten - und genau das ging schief: am 19.08. stand
        # positionsverlauf.py 28 Minuten still, weil er beim Bot-Neustart
        # mitgestorben war, und der Schatten-Sammler lief noch mit dem
        # Programmtext von vor der Reparatur.
        #
        # Ab jetzt startet der Bot sie mit. Nur, was NICHT schon laeuft -
        # geprueft an der Prozessliste, nicht geraten.
        #
        # REINES AUFSCHREIBEN. Beide Sammler handeln nicht, sie messen nur
        # (schatten_universum.py rechnet dieselbe Punktzahl wie der Bot,
        # positionsverlauf.py schreibt alle 5 Minuten den Stand offener
        # Positionen mit). Das Verhalten des Bots aendert sich dadurch
        # nicht - freeze-vertraeglich.
        try:
            import threading as _th

            def _sammler_sicherstellen():
                try:
                    import sammler_pruefen
                    sammler_pruefen.starten(
                        melden=lambda z: log.info("SAMMLER", z.strip()))
                except Exception as _se:
                    log.warn("SAMMLER", f"Start fehlgeschlagen: {str(_se)[:80]}")

            # In einem eigenen Faden, weil starten() 15 Sekunden wartet, um
            # nachzusehen, ob die Prozesse wirklich oben geblieben sind.
            # Der Bot soll darauf nicht warten muessen.
            _th.Thread(target=_sammler_sicherstellen, daemon=True,
                       name="sammler-start").start()
            log.info("SAMMLER", "Sammler werden geprueft und bei Bedarf gestartet")
        except Exception as _se:
            log.warn("SAMMLER", f"Sammler-Start nicht moeglich: {str(_se)[:80]}")

        # === CHART-AUTO-REFRESHER (Hintergrund, isoliert) === [CHART-REFRESH 21.07.]
        try:
            from features.chart_refresher import ChartRefresher
            self.chart_refresher = ChartRefresher()
            self.chart_refresher.start()
        except Exception as _cr_err:
            try:
                from chart_refresher import ChartRefresher
                self.chart_refresher = ChartRefresher()
                self.chart_refresher.start()
            except Exception as _cr_err2:
                log.warn("CHART-REFRESH", f"nicht gestartet: {str(_cr_err2)[:60]}")

        # SELBSTTEST: Alle kritischen Komponenten testen
        try:
            self._run_startup_diagnostic()
        except Exception as e:
            log.warn("APP", f"Selbsttest uebersprungen: {e}")

        # WebSocket starten (optional, fuer Echtzeit-Preise)
        try:
            # [PRICEFEED-FIX 10.07.] Preisversorgung = aktive Coins + Coins mit
            # offener Position. Vorher: coins[:10] -> Coin Nr. 11 fiel still raus,
            # pausierte Coins mit Restposition (XRP) hatten keinen Preisstrom
            # (Stop verglich gegen eingefrorenen Cache-Wert).
            _universe = list(self.config.trading.coins)
            try:
                for _sym, _pos in dict(getattr(self.risk_engine, "open_positions", {}) or {}).items():
                    if isinstance(_pos, dict) and _pos.get("active") and _sym not in _universe:
                        _universe.append(_sym)
            except Exception as _pf_e:
                log.warn("APP", f"WS-Universum: Register-Scan: {str(_pf_e)[:40]}")
            try:
                import json as _json
                _sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_store", "bot_state.json")
                if os.path.exists(_sp):
                    with open(_sp, encoding="utf-8") as _f:
                        _st = _json.load(_f)
                    for _src in (_st.get("open_positions") or {}, _st.get("open_positions_backup") or {}):
                        for _sym, _pos in _src.items():
                            if isinstance(_pos, dict) and _pos.get("active") and _sym not in _universe:
                                _universe.append(_sym)
            except Exception as _pf_e:
                log.warn("APP", f"WS-Universum: State-Scan: {str(_pf_e)[:40]}")
            _extra = len(_universe) - len(self.config.trading.coins)
            log.info("APP", f"WS-Universum: {len(_universe)} Coins "
                            f"({len(self.config.trading.coins)} aktiv + {_extra} Restposition(en))")
            coins_ws = [c.replace("/", "").lower() for c in _universe]
            if self.websocket.start(coins_ws):
                # WebSocket Preise in den DataAgent Cache schreiben
                def _ws_price_update(symbol, price, change, volume):
                    self.data_agent.price_cache[symbol] = price
                self.websocket.on_price_update(_ws_price_update)
                log.info("APP", f"✅ WebSocket gestartet ({len(coins_ws)} Coins)")
            else:
                log.info("APP", "WebSocket nicht verfuegbar (pip install websocket-client)")
        except Exception as e:
            log.info("APP", f"WebSocket optional: {str(e)[:40]}")

        # [GEFUNDENE-PROBLEME #11] Dem Regel-Schalter die Telemetrie geben und
        # melden, welche Regeln NICHT scharf sind. Wer eine Regel im
        # Schattenmodus laufen laesst, muss das beim Start sehen - sonst
        # wundert man sich Wochen spaeter, warum eine Regel nie ausloest.
        try:
            if getattr(self, "regel_schalter", None) is not None:
                from core.telemetrie import Telemetrie
                if getattr(self, "telemetrie", None) is None:
                    self.telemetrie = Telemetrie()
                self.regel_schalter.telemetrie = self.telemetrie
                for _zeile in (self.regel_schalter.startmeldung() or "").splitlines():
                    if _zeile.strip():
                        log.info("SCHALTER", _zeile.strip())

                # [GEFUNDENE-PROBLEME #31] Waechter sofort einmal laufen
                # lassen. Die Startmeldung oben SCHWEIGT, wenn alles auf
                # ACTIVE steht - und genau das ist der gefaehrliche Fall.
                # Ein fehlender Eintrag ist kein Alarm; der Waechter macht
                # daraus einen.
                if getattr(self, "regel_waechter", None) is not None:
                    self.regel_waechter.telegram = getattr(self, "telegram", None)
                    self.regel_waechter.pruefen()
        except Exception as _rs_err:
            log.warn("SCHALTER", f"Startmeldung: {str(_rs_err)[:60]}")

        # XGBoost Modell laden (wenn vorhanden)
        try:
            if self.xgboost_model.load():
                log.info("APP", f"✅ XGBoost Modell geladen: {self.xgboost_model.version}")
            else:
                log.info("APP", "XGBoost: Kein Modell vorhanden (wird beim Training erstellt)")
        except Exception:
            pass

        # Konfiguration speichern
        self.config.save()

        # Multi-Exchange Setup
        self.multi_exchange.add_public("binance")
        try:
            self.multi_exchange.add_public("bybit")
        except Exception:
            pass
        log.info("APP", f"Multi-Exchange: {', '.join(self.multi_exchange.get_exchanges())}")

        # Multi-Exchange mit Execution verbinden
        self.execution.set_multi_exchange(self.multi_exchange)

        # Futures Paper-Mode starten
        self.futures.connect(testnet=True)
        log.info("APP", f"Futures: {self.futures.get_status()['mode']} ({self.futures.max_leverage}x max)")

        # Offene Positionen wiederherstellen
        self._restore_positions()

        # SOFORT F&G laden (nicht 30 Min warten!)
        try:
            fg = self.sentiment_data.get_fear_greed().get("value", 50)
            self.state.set("fear_greed", fg)
            log.info("APP", f"Fear & Greed Index: {fg}")
        except Exception:
            log.info("APP", "F&G konnte nicht geladen werden (Default: 50)")

        # Web-Dashboard starten
        self.dashboard.start()

        # [GEFUNDENE-PROBLEME #14, 13.08.2026] Webhook wird nicht mehr
        # gestartet. Port 5051 lauschte auf 0.0.0.0 - also auf ALLEN
        # Netzwerkschnittstellen, im ganzen Heimnetz erreichbar, ohne
        # Passwort oder Token. Jeder POST auf /webhook erzeugte ein
        # Kaufsignal mit frei gesetztem score=7. Sven benutzt TradingView
        # nicht; damit faellt ein von aussen erreichbarer Kaufweg weg und
        # das Messfenster bleibt frei von TRADINGVIEW-Signalen.
        # WIEDER EINSCHALTEN: siehe Kopf von ui/webhook_server.py - dort
        # steht, was vorher repariert werden muss (127.0.0.1 + Token).

        # Auto-Retraining Scheduler (woechentlich)
        self.scheduler.add_task(
            "auto_retrain", self._check_retrain,
            interval_sec=3600)  # Stundlich pruefen ob Retraining noetig

        # ngrok Tunnel (optional, braucht pyngrok + Auth-Token)
        # Standardmaessig AUS um Spam zu vermeiden - nur AN wenn konfiguriert
        if getattr(self.config.dashboard, "ngrok_enabled", False):
            ngrok_url = self.ngrok.start()
            if ngrok_url:
                try:
                    self.telegram.send(f"🌐 Dashboard live: {ngrok_url}")
                except Exception:
                    pass
        else:
            log.info("NGROK", "Deaktiviert (config.dashboard.ngrok_enabled = False)")

        # Auto-Restart Monitor
        for comp in ["data", "signal", "risk", "execution", "context"]:
            self.auto_restart.register(comp)
        self.auto_restart.start()

        # ZENTRALER HEARTBEAT-PULSE: Sendet alle 30s Heartbeats fuer
        # alle Komponenten die sonst nur sporadisch aktiv sind
        self._start_heartbeat_pulse()

        print("\n" + "=" * 60)
        print("✅ TRADING IMPERIUM V7 LÄUFT")
        print(f"   Modus: {self.config.trading.mode}")
        print(f"   Coins: {len(self.config.trading.coins)}")
        print(f"   Dashboard: http://localhost:{self.config.dashboard.port}")
        print(f"   Daten: {DATA_DIR}")
        print("   Strg+C zum Beenden")
        print("=" * 60 + "\n")

    def stop(self):
        """Stoppt das System sauber."""
        if not self._running:
            return
        self._running = False
        log.info("APP", "System wird heruntergefahren...")
        self.scheduler.stop()
        self.watchdog.stop()

        # [DOPPELVERKAUF-FIX 13.08.2026] Vor dem Speichern den AKTUELLEN
        # Positionsstand einsammeln.
        #
        # BEFUND: Hier stand nur self.state.save(). Das schreibt aber nur
        # weg, was vorher in den State gelegt wurde - und die Positionsliste
        # (open_positions_backup) legt AUSSCHLIESSLICH
        # state_manager.auto_save() hinein, alle 30 Sekunden.
        #
        # Folge: Wurde zwischen der letzten Auto-Speicherung und dem
        # Beenden etwas verkauft, speicherte stop() den VERALTETEN Stand -
        # inklusive der gerade verkauften Position. Beim naechsten Start
        # holte restore_positions() sie zurueck, und die Ausstiegsregel
        # verkaufte sie ein zweites Mal.
        #
        # Nachgewiesen an SOL/USDC am 13.08.2026:
        #   11:14:55  Verkauf (BREAKEVEN-SPERRE), Position raus
        #   11:15:0x  Bot beendet -> alter Stand mit SOL gespeichert
        #   11:15:49  Neustart -> SOL wiederhergestellt
        #   11:36:02  zweiter Verkauf, SELBE position_id pos_SOL_d044b018,
        #             selbe Menge 1.4377682601826274, selbes mfe/mae
        # Erkennbar auch am Zykluszaehler: 2066 vor, 59 nach dem Neustart.
        #
        # Im Papiermodus kostet das nur falsche Zahlen. Live wuerde der Bot
        # Muenzen verkaufen, die er nicht mehr besitzt.
        try:
            if getattr(self, "state_manager", None) is not None:
                self.state_manager.auto_save()
        except Exception as _ss_e:
            log.error("APP", f"Zustand beim Herunterfahren nicht "
                             f"aktualisiert ({type(_ss_e).__name__}) - der "
                             f"naechste Start koennte einen veralteten "
                             f"Positionsstand laden!")

        self.state.save()
        self.bus.shutdown()
        log.info("APP", "✅ Sauber heruntergefahren.")

    def _shutdown_handler(self, signum, frame):
        """Behandelt Strg+C und SIGTERM."""
        print("\n⏹️ Shutdown-Signal empfangen...")
        self.stop()
        sys.exit(0)

    def run_forever(self):
        """Startet das System und wartet auf Shutdown."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _strategie_anzeigename(self):
        """[13.08.2026] Klarname der aktuellen Strategie fuer die Anzeige.

        current_strategy ist eine Kennung wie "MULTI_SIGNAL"; den lesbaren
        Namen haelt STRATEGIES in agents/strategy_brain.py. Die hasattr-
        Pruefung faengt den Fall ab, dass daraus spaeter ein Objekt wird.
        """
        s = getattr(self.strategy_brain, "current_strategy", None)
        if not s:
            return "-"
        if hasattr(s, "name"):
            return str(s.name)
        try:
            from agents.strategy_brain import STRATEGIES
            return str(STRATEGIES.get(s, {}).get("name") or s)
        except Exception:
            return str(s)

    def get_system_status(self) -> dict:
        """Gibt den kompletten System-Status zurueck (fuer Dashboard).

        [GEFUNDENE-PROBLEME #33, 13.08.2026] Diese Methode war ein einziges
        Dict-Literal mit 51 Methodenaufrufen. Ein Dict-Literal wird komplett
        ausgewertet, bevor es entsteht - EIN fehlgeschlagener Aufruf laesst
        also die GESAMTE Statusabfrage scheitern.

        Genau das passierte: 'order_manager': self.execution.order_manager
        .get_status() - diese Methode existiert nicht, OrderManager hat nur
        get_stats(). Die Zeile steht seit dem ersten Commit im Code. Folge:
        /api/status lieferte AUSNAHMSLOS HTTP 500, das Web-Dashboard auf
        Port 5050 hat also noch NIE Daten angezeigt. Aufgefallen ist es
        niemandem, weil das Tkinter-Cockpit die Objekte direkt liest und
        deshalb normal weiterlief - ein stiller Totalausfall.

        Jetzt: Die Modul-Statusfelder werden einzeln eingesammelt. Faellt
        eines aus, steht der Fehlertext IM FELD (sichtbar, nicht versteckt)
        und alle uebrigen 50 kommen trotzdem durch. Ein neuer fehlender
        Status legt damit nie wieder die ganze Anzeige lahm.

        Kein stiller Fallback: jedes ausgefallene Feld wird zusaetzlich
        einmalig als WARNING geloggt (einmalig, weil das Dashboard diese
        Methode im Sekundentakt abfragt und ein Log je Aufruf eine Flut
        erzeugen wuerde).

        Nebenbei mit repariert: Der Schluessel 'cycle' wurde zweimal
        gesetzt - einmal mit cycle_theory.get_status(), einmal mit
        cycle_theory.current_phase. Im Dict-Literal gewinnt der letzte
        Eintrag, der erste Aufruf war also immer schon wirkungslos. Er ist
        entfernt; 'cycle' bleibt current_phase wie bisher, damit sich fuer
        das Dashboard-Frontend nichts aendert.
        """
        # --- Direkte Werte: billig, koennen praktisch nicht scheitern ---
        status = {
            "version": self.config.version,
            "mode": self.config.trading.mode,
            "running": self._running,
            "runner_mode": ("live" if isinstance(self.runner, LiveRunner)
                            else "paper" if self.runner else "none"),
            "webhook": {"running": False, "stillgelegt_am": "2026-08-13",
                        "grund": "GEFUNDENE-PROBLEME #14"},
        }

        # --- Alles, was einen Aufruf braucht: einzeln, ausfallsicher ---
        felder = [
            ("uptime", self.health.get_uptime),
            ("health", self.health.check_all),
            ("scheduler", self.scheduler.get_status),
            ("events", self.bus.get_stats),
            ("recent_events", lambda: self.bus.get_recent_events(10)),
            ("journal_stats", self.journal.get_stats),
            ("recent_trades", lambda: self.journal.get_last(10)),
            ("alerts", lambda: self.health.get_alerts(5)),
            ("risk", self.risk_engine.get_status),
            ("signal", self.signal_agent.get_stats),
            ("brain", self.strategy_brain.get_status),
            ("btc_acc", self.btc_accumulator.get_status),
            ("ml_model", self.signal_model.get_status),
            ("watchdog", self.watchdog.get_status),
            # [#33] war get_status() - existiert nicht, richtig ist get_stats()
            ("order_manager", self.execution.order_manager.get_stats),
            ("reconciler", self.execution.fill_reconciler.get_status),
            ("context", self.context_agent.get_status),
            ("portfolio", self.portfolio_agent.get_status),
            ("balance", self.execution.get_balance),
            ("prices", lambda: self.data_agent.price_cache),
            # Phase 1 Signals
            ("funding_rates", self.funding_rates.get_status),
            ("whale_alerts", self.whale_alerts.get_status),
            ("reddit", self.reddit_sentiment.get_status),
            ("rsi_divergence", self.rsi_divergence.get_status),
            ("xgboost", self.xgboost_model.get_status),
            ("websocket", self.websocket.get_status),
            ("onchain", self.onchain.get_status),
            ("regime_detector", self.regime_detector.get_status),
            ("multi_tf", self.multi_tf.get_status),
            ("vwap", self.vwap.get_status),
            ("twap", self.twap.get_status),
            ("smart_entry", self.smart_entry.get_status),
            ("rl_feedback", self.rl_feedback.get_status),
            ("ensemble", self.ensemble.get_status),
            ("llm", self.llm.get_status),
            ("grid_trader", self.grid_trader.get_status),
            ("dca_advanced", self.dca_advanced.get_status),
            ("orderbook", self.orderbook.get_status),
            ("arbitrage", self.arbitrage.get_status),
            ("adaptive_sizer", self.adaptive_sizer.get_status),
            ("multi_exchange", self.multi_exchange.get_status),
            ("optimizer", self.bt_optimizer.get_status),
            ("ngrok", self.ngrok.get_status),
            ("auto_restart", self.auto_restart.get_all_status),
            ("auto_retrain", self.auto_retrainer.get_status),
            ("futures", self.futures.get_status),
            ("hyperopt", self.hyperopt.get_status),
            ("strategy_export", self.strategy_export.get_status),
            ("nupl", self.nupl.get_status),
            ("dxy", self.dxy.get_status),
            ("meta_voting", self.meta_voting.get_status),
            ("shadow_mode", self.shadow_mode.get_status),
            # V4 Bridge
            ("v4_ensemble", self.v4_ensemble.get_status),
            ("v4_calibrator", self.v4_calibrator.get_status),
            # Fuer Dashboard einfacher Zugriff
            # [FIX 13.08.2026] Hier stand current_strategy.name - aber
            # current_strategy ist ein STRING ("MULTI_SIGNAL",
            # agents/strategy_brain.py:88/245), kein Objekt. Der Zugriff
            # warf jedes Mal AttributeError.
            #
            # Das ist der Beleg dafuer, dass der Umbau von get_system_status
            # (Punkt 33) richtig war: Vorher haette dieser eine Fehler die
            # GESAMTE Statusabfrage zum Absturz gebracht, so wie es der
            # OrderManager-Tippfehler seit dem ersten Commit tat. Jetzt fiel
            # nur dieses Feld aus, mit lesbarem Fehlertext - gefunden am
            # 13.08. beim ersten erfolgreichen Aufruf von /api/status.
            #
            # Klarnamen aus STRATEGIES aufloesen; haelt auch, falls daraus
            # spaeter doch ein Objekt wird.
            ("strategy", self._strategie_anzeigename),
            ("regime", lambda: self.regime_detector.current_regime),
            ("cycle", lambda: self.cycle_theory.current_phase),
            ("fear_greed", lambda: self.state.get("fear_greed", 50)),
        ]

        if not hasattr(self, "_status_fehler_gemeldet"):
            self._status_fehler_gemeldet = set()

        for name, holen in felder:
            try:
                status[name] = holen()
            except Exception as _e:
                status[name] = {"fehler": f"{type(_e).__name__}: {str(_e)[:120]}"}
                if name not in self._status_fehler_gemeldet:
                    self._status_fehler_gemeldet.add(name)
                    log.warn("STATUS", f"Statusfeld '{name}' faellt aus: "
                                       f"{type(_e).__name__}: {str(_e)[:100]} "
                                       f"(einmalige Meldung, Feld zeigt den Fehler)")

        return status


# ==========================================================
# START
# ==========================================================
if __name__ == "__main__":
    import sys, traceback
    from core.exceptions import SicherheitsbauteilFehlt

    # ================================================================
    # [BEFUND 93, 13.09.2026] DOPPELSTART-SPERRE
    # ----------------------------------------------------------------
    # Hier stand bisher sofort TradingImperiumV6(), ohne nachzusehen, ob
    # schon einer laeuft. Zwei Sicherungen, die man dafuer haelt, greifen
    # nicht: die Sperrdatei in core/hintergrund.py schuetzt nur die
    # Hintergrundjobs, und die Portbelegung bremst nicht - mit netstat
    # nachgemessen hoert der Bot auf KEINEM Port. Damit laeuft auch die
    # Regel in CLAUDE.md ins Leere, vor jedem Neustart zu pruefen, wer
    # Port 5050 haelt: es haelt ihn niemand.
    # Am 01.09.2026 hing die Handelsschleife deshalb 37 Minuten.
    #
    # Der Grundsatz der Sperre ist IM ZWEIFEL STARTEN LASSEN - sie
    # blockiert nur, wenn die eingetragene Prozessnummer noch lebt UND
    # wirklich ein app.py ist. Herleitung in core/startsperre.py,
    # zehn Pruefungen in startsperre_test.py.
    #
    # Der Import ist abgesichert: faellt die Sperre selbst aus, startet
    # der Bot wie bisher. Ein Wachposten darf nie der Grund sein, warum
    # gar nichts mehr laeuft.
    # ================================================================
    try:
        from core.startsperre import pruefen_und_eintragen, freigeben
        if not pruefen_und_eintragen():
            input("Druecke Enter zum Beenden...")
            sys.exit(3)
        import atexit
        atexit.register(freigeben)
    except SystemExit:
        raise
    except Exception as _sperr_e:
        print("[STARTSPERRE] nicht verfuegbar (%s) - starte ohne sie."
              % str(_sperr_e)[:80])

    try:
        engine = TradingImperiumV6()
    except SicherheitsbauteilFehlt as e:
        # [13.08.2026] Eigener Zweig, damit dieser Abbruch nicht wie ein
        # gewoehnlicher Startfehler aussieht. Er ist gewollt: ein Bauteil,
        # ohne das nicht gehandelt werden darf, konnte nicht laden.
        print("\n" + "!" * 70)
        print("!!  START ABGEBROCHEN - SICHERHEITSBAUTEIL FEHLT")
        print("!" * 70)
        print(f"!!  Bauteil : {e.bauteil}")
        print(f"!!  Ursache : {e.ursache}")
        print(f"!!  Folge   : {e.folge}")
        print("!" * 70)
        print("!!  Der Bot startet ABSICHTLICH nicht. Handel ohne dieses")
        print("!!  Bauteil waere gefaehrlicher als kein Handel.")
        print("!!")
        print("!!  NICHT den Ordner data_store loeschen - der Zustand ist")
        print("!!  in Ordnung, es fehlt ein Programmteil. Zuerst die")
        print("!!  Ursache oben lesen; meist ein Import- oder Tippfehler")
        print("!!  in der genannten Datei.")
        print("!" * 70 + "\n")
        traceback.print_exc()
        input("Druecke Enter zum Beenden...")
        sys.exit(2)
    except Exception as e:
        print("=" * 60)
        print(f"FEHLER beim Start: {e}")
        print("=" * 60)
        traceback.print_exc()
        # [13.08.2026] Der pauschale Rat "Loesche den Ordner data_store"
        # stand hier fuer JEDEN Startfehler. data_store enthaelt den
        # kompletten Bot-Zustand: Positionen, Kontostand, Journal,
        # telemetrie.db mit inzwischen ueber 200.000 Zeilen. Bei einem
        # Import- oder Tippfehler haette dieser Rat den gesamten Bestand
        # vernichtet, ohne das Problem zu loesen.
        print("\nZuerst die Fehlermeldung oben lesen - meist ein fehlendes")
        print("Paket (pip install ...) oder ein Tippfehler im Code.")
        print("Den Ordner 'data_store' NICHT loeschen: darin liegen")
        print("Positionen, Kontostand, Journal und die Telemetrie-Datenbank.")
        print("Falls doch noetig, vorher eine Kopie anlegen.")
        input("Druecke Enter zum Beenden...")
        sys.exit(1)

    if "--headless" in sys.argv:
        engine.run_forever()
    else:
        try:
            from ui.main_window import MainWindow
            window = MainWindow(engine)
            window.mainloop()
        except ImportError as e:
            print(f"UI-Fehler: {e}")
            print("Installiere: pip install customtkinter matplotlib")
            engine.run_forever()
        except Exception as e:
            print(f"FEHLER: {e}")
            traceback.print_exc()
            input("Druecke Enter zum Beenden...")
