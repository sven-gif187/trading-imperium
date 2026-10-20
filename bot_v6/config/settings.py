"""
Trading Imperium V6 - Zentrale Konfiguration
ALLE Werte sind prozentual oder relativ - skaliert von 300$ bis 100.000$.
Live/Paper Modus wird hier umgeschaltet.
"""
import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data_store")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


# ============================================================
# .env LADER (fuer API-Keys - NIE in Code!)
# ============================================================
def load_env():
    """Liest .env-Datei und schreibt in os.environ."""
    env_paths = [".env", os.path.join(BASE_DIR, ".env")]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if val:
                                os.environ[key] = val
                return True
            except Exception:
                pass
    return False


# Beim Import .env laden
load_env()


# ============================================================
# EXCHANGE CONFIG
# ============================================================
@dataclass
class ExchangeConfig:
    """Boersen-Konfiguration. API-Keys NIE hier - aus .env!"""
    name: str = "Binance"
    ccxt_id: str = "binance"
    testnet: bool = False
    quote_currency: str = "USDC"
    timeout_connect: int = 3
    timeout_read: int = 10
    max_retries: int = 3
    # API-Keys werden zur Laufzeit aus .env gelesen
    api_key: str = ""
    api_secret: str = ""

    def load_api_keys(self):
        """Laedt API-Keys aus Umgebungsvariablen (.env)."""
        if not self.api_key:
            self.api_key = os.environ.get("BINANCE_API_KEY", "")
        if not self.api_secret:
            self.api_secret = os.environ.get("BINANCE_API_SECRET", "")
        return bool(self.api_key and self.api_secret)


# ============================================================
# TRADING MODE - ALLES PROZENTUAL!
# ============================================================
@dataclass
class TradingMode:
    """Ein Trading-Modus mit PROZENTUALEN Werten.
    Skaliert automatisch mit Portfolio-Groesse.

    Beispiel mit position_size_pct=30:
      - 300$  Portfolio -> 90$  pro Trade
      - 1500$ Portfolio -> 450$ pro Trade
      - 5000$ Portfolio -> 1500$ pro Trade
    """
    name: str = "balanced"
    position_size_pct: float = 30.0           # % des Portfolios pro Trade
    max_positions: int = 3                     # Max gleichzeitige Trades
    cash_reserve_pct: float = 10.0            # % Cash-Reserve (immer halten)
    sector_limit_pct: float = 80.0            # % Max pro Sektor (100 = aus)
    max_coin_pct: float = 35.0                # % Max in einem einzelnen Coin
    # [BTC-ONLY 07.08.2026] Beschraenkt NEUE Kaeufe auf ein einzelnes Asset.
    # Leer = alle Coins erlaubt (Verhalten wie bisher, unveraendert).
    # "BTC"  = nur BTC-Paare duerfen neu gekauft werden.
    # WICHTIG: Wirkt ausschliesslich auf NEUE Kaeufe. Bereits offene Positionen
    # in anderen Coins behalten Stop-Loss und Trailing und werden ganz normal
    # zu Ende verwaltet - sonst entstuenden genau die Geisterpositionen, die
    # niemand mehr ueberwacht. Gleiches Prinzip wie beim Regime-Filter
    # (regime_filter.py:3 "blockt nur neue BUYs, fasst KEINE offene Position an").
    nur_asset: str = ""


@dataclass
class TradingModesConfig:
    """Drei vordefinierte Trading-Modi."""
    active_mode: str = "balanced"             # "all_in" | "balanced" | "diversified"

    # MODUS A: All-In - 1 grosser Trade
    all_in: TradingMode = field(default_factory=lambda: TradingMode(
        name="all_in",
        position_size_pct=95.0,
        max_positions=1,
        cash_reserve_pct=5.0,
        sector_limit_pct=100.0,
        max_coin_pct=100.0,
    ))

    # MODUS B: Balanced - 3 Trades
    balanced: TradingMode = field(default_factory=lambda: TradingMode(
        name="balanced",
        position_size_pct=30.0,
        max_positions=3,
        cash_reserve_pct=10.0,
        sector_limit_pct=80.0,
        max_coin_pct=35.0,
    ))

    # MODUS C: Diversified - 8-10 Trades
    diversified: TradingMode = field(default_factory=lambda: TradingMode(
        name="diversified",
        position_size_pct=10.0,
        max_positions=10,
        cash_reserve_pct=10.0,
        sector_limit_pct=40.0,
        max_coin_pct=15.0,
    ))

    # MODUS D: BTC-Only - nur Bitcoin akkumulieren
    # [BTC-ONLY 07.08.2026] Gleiche Groessen wie balanced, aber NEUE Kaeufe
    # ausschliesslich in BTC. max_coin_pct hochgesetzt, weil bei nur einem
    # Asset die 35-%-Coin-Grenze jeden zweiten Kauf blockieren wuerde.
    btc_only: TradingMode = field(default_factory=lambda: TradingMode(
        name="btc_only",
        position_size_pct=30.0,
        max_positions=3,
        cash_reserve_pct=10.0,
        sector_limit_pct=100.0,
        max_coin_pct=95.0,
        nur_asset="BTC",
    ))

    def get_active(self) -> TradingMode:
        """Gibt den aktiven Modus zurueck."""
        m = self.active_mode.lower()
        if m == "all_in":
            return self.all_in
        elif m == "diversified":
            return self.diversified
        elif m == "btc_only":
            return self.btc_only
        return self.balanced  # Default


# ============================================================
# RISK CONFIG - ALLES PROZENTUAL!
# ============================================================
@dataclass
class RiskConfig:
    """Risiko-Management - 100% prozentual."""
    # Tagesverlust-Limits (% des Tagesstart-Kapitals)
    max_daily_loss_pct: float = 10.0          # -10% Tagesverlust -> Bot pausiert
    max_drawdown_pct: float = 15.0            # Max Portfolio-Drawdown

    # Stop-Loss / Take-Profit (% vom Einstiegspreis)
    stop_loss_pct: float = 2.0                # -2% vom Entry -> SL (war 4%, zu weit)
    take_profit_pct: float = 1.5              # +1.5% vom Entry -> TP (war 8%, zu hoch)
    trailing_stop_pct: float = 1.5            # 1.5% unter Hoechststand

    # Positions-Management
    cooldown_after_losses: int = 3            # Pause nach X Verlusten
    kill_switch_enabled: bool = True

    # Live-Modus Sicherheits-Filter
    min_volume_24h_usd: float = 1_000_000     # Min 1M$ Volumen pro Coin
    max_spread_pct: float = 0.5               # Max 0.5% Spread

    # Backward-Kompatibilitaet (alte Code-Pfade)
    use_dynamic_sizing: bool = False
    max_open_positions: int = 3               # Spiegelt aktiven Modus (UI-Setting)
    max_exposure_per_coin_pct: float = 35.0
    max_daily_loss_usd: float = 50.0          # Alt - ersetzt durch max_daily_loss_pct

    # === [E9 29.07.2026] Tagesverlust-Waechter (portfolio/daily_loss.py) ===
    # MUSSTE hier als Feld stehen: AppConfig._from_dict uebernimmt aus
    # config.json ausschliesslich Schluessel, fuer die hasattr(section, k)
    # gilt. Ein blosser "daily_loss"-Block in der JSON wurde also stumm
    # verworfen - der Waechter lief unbemerkt weiter in der Vorgabe
    # "schatten" und hat NIE eingegriffen. Ausserdem haette AppConfig.save()
    # (asdict) den Block bei jedem UI-Speichern wieder aus der Datei entfernt.
    #   mode:      "aus" | "schatten" (rechnet nur) | "aktiv" (pausiert Kaeufe)
    #   limit_pct: Tagesverlust in % vom Tagesstart-Kapital
    # Wirkung ist AUSSCHLIESSLICH eine Kaufpause - nie ein Zwangsverkauf.
    daily_loss: dict = field(default_factory=lambda: {"mode": "schatten",
                                                      "limit_pct": 10.0})

    # === [E10-LIVE 29.07.2026] Sicherungen fuer den Echtgeld-Betrieb ===
    # Greifen AUSSCHLIESSLICH bei trading.mode == "live". Im Papierbetrieb
    # sind sie wirkungslos. Siehe execution/engine.py _live_sicherungen().
    #   live_require_gate  - Start nur, wenn go_live_check.py durchlaeuft.
    #                        Verhindert, dass eine unbedachte Config-Aenderung
    #                        echtes Geld an eine ungeprueften Strategie gibt.
    #   live_max_order_usd - harte Obergrenze je Einzelorder. Fangnetz gegen
    #                        Sizing-Fehler; das Sizing selbst rechnet prozentual.
    #   live_max_capital_usd - Obergrenze des Kapitals, das der Bot ueberhaupt
    #                        anfassen darf (0 = unbegrenzt). Liegt mehr auf dem
    #                        Konto, rechnet der Bot trotzdem nur mit diesem Wert.
    live_require_gate: bool = True
    live_max_order_usd: float = 50.0
    live_max_capital_usd: float = 0.0

    # Aliase fuer alte Feldnamen (strategy_export.py & co)
    @property
    def daily_loss_limit(self) -> float:
        """Alias fuer max_daily_loss_pct."""
        return self.max_daily_loss_pct

    @daily_loss_limit.setter
    def daily_loss_limit(self, value: float):
        self.max_daily_loss_pct = value

    @property
    def cooldown_after_loss(self) -> int:
        """Alias fuer cooldown_after_losses."""
        return self.cooldown_after_losses

    @cooldown_after_loss.setter
    def cooldown_after_loss(self, value: int):
        self.cooldown_after_losses = value


# ============================================================
# TRADING CONFIG
# ============================================================
@dataclass
class TradingConfig:
    """Trading-Parameter."""
    mode: str = "paper"                       # "paper" oder "live"
    coins: List[str] = field(default_factory=lambda: [
        "BTC/USDC", "ETH/USDC", "SOL/USDC", "XRP/USDC",
        "ADA/USDC", "AVAX/USDC", "LINK/USDC", "DOT/USDC",
        "DOGE/USDC", "NEAR/USDC", "UNI/USDC", "ATOM/USDC",
    ])
    default_timeframe: str = "1h"
    candle_limit: int = 120
    loop_interval_seconds: int = 12

    # Paper Balance (NUR fuer Paper-Mode!)
    initial_paper_balance: float = 300.0      # Startwert fuer Paper-Trading

    # DCA (Sparplan)
    dca_enabled: bool = True
    dca_max_levels: int = 3
    dca_drop_pct: float = 2.0
    btc_dca_enabled: bool = False
    btc_dca_pct: float = 33.0
    btc_dca_interval_min: int = 60

    # === [E11-GRID 29.07.2026] Zweiter Einstiegspfad, schaltbar ===
    # false = Grid Bot wird gar nicht erst erzeugt (app.py). Waehrend des
    # Messfensters fuer die Live-Freigabe bewusst aus: er ist ein zweiter
    # Einstiegspfad neben DCA_FEAR_GREED, und eine Messung mit zwei
    # gleichzeitig laufenden Strategien laesst sich hinterher nicht
    # auseinanderrechnen. Nicht als schlecht bewertet - nur ungeprueft.
    grid_enabled: bool = False

    # Backward-Kompatibilitaet (alte UI/Code Pfade)
    # Diese werden vom UI gesetzt und ueberschreiben den aktiven Modus
    position_size_pct: float = 30.0           # % pro Trade (UI-Override)
    max_trades: int = 3                       # Max Trades (UI-Override)


# ============================================================
# WEITERE CONFIGS
# ============================================================
@dataclass
class RebalanceConfig:
    enabled: bool = False
    interval_min: int = 240
    btc_target_pct: float = 50.0
    eth_target_pct: float = 30.0
    other_target_pct: float = 20.0
    threshold_pct: float = 5.0


@dataclass
class AIConfig:
    enable_news: bool = True
    enable_llm_chat: bool = False
    news_interval_min: int = 30
    sentiment_weight: float = 0.3
    # OpenAI API (NIEMALS hier - aus .env laden!)
    openai_key: str = ""                      # Aus .env: OPENAI_API_KEY
    openai_model: str = "gpt-4o-mini"         # Default-Modell

    def load_from_env(self):
        """Laedt OPENAI_API_KEY aus Umgebungsvariablen (.env)."""
        if not self.openai_key:
            self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        return bool(self.openai_key)


@dataclass
class TelegramConfig:
    enabled: bool = False
    token: str = ""                           # Aus .env: TELEGRAM_BOT_TOKEN
    chat_id: str = ""                         # Aus .env: TELEGRAM_CHAT_ID
    notify_on_trade: bool = True
    notify_on_alert: bool = True

    def load_from_env(self):
        if not self.token:
            self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not self.chat_id:
            self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        return bool(self.token and self.chat_id)


@dataclass
class DashboardConfig:
    enabled: bool = True
    port: int = 5050
    host: str = "0.0.0.0"
    refresh_interval_sec: int = 8
    ngrok_token: str = ""
    ngrok_enabled: bool = False


# ============================================================
# HAUPT-CONFIG
# ============================================================
@dataclass
class AppConfig:
    """Haupt-Konfiguration."""
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    modes: TradingModesConfig = field(default_factory=TradingModesConfig)
    rebalance: RebalanceConfig = field(default_factory=RebalanceConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    version: str = "6.1.0"

    def get_active_mode(self) -> TradingMode:
        """Shortcut: Gibt den aktiven Trading-Modus zurueck."""
        return self.modes.get_active()

    def save(self):
        d = asdict(self)
        # Secrets NIE in config.json schreiben (liegen in .env)
        try:
            if isinstance(d.get("exchange"), dict):
                d["exchange"]["api_key"] = ""
                d["exchange"]["api_secret"] = ""
            if isinstance(d.get("telegram"), dict):
                d["telegram"]["token"] = ""
            if isinstance(d.get("dashboard"), dict):
                d["dashboard"]["ngrok_token"] = ""
        except Exception:
            pass

        # [GEFUNDENE-PROBLEME #31, 12.08.2026] Unbekannte Bloecke ERHALTEN.
        #
        # asdict(self) baut die Datei komplett aus den bekannten Feldern neu
        # auf. Alles, was zusaetzlich in der config.json steht, fiel dabei
        # stillschweigend heraus.
        #
        # PASSIERT AM 12.08. UM 21:05: Sven speicherte in der Einstellungs-
        # maske seine Telegram-Daten. Dabei verschwand der Block "regel_modi"
        # - und weil der Drei-Stufen-Schalter bei fehlender Angabe bewusst auf
        # ACTIVE zurueckfaellt, war der Trend-Ausstieg wieder scharf. Eine
        # Regel, die in 46 gemessenen Faellen zu 0 % im Plus lag (-36,08 $),
        # haette also wieder verkauft - ausgeloest durch das Speichern einer
        # voellig unbeteiligten Einstellung.
        #
        # Jetzt werden fremde Schluessel aus der bestehenden Datei
        # uebernommen. Das schuetzt auch jede kuenftige Erweiterung, die
        # (noch) kein Dataclass-Feld hat.
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    vorhanden = json.load(f)
                if isinstance(vorhanden, dict):
                    for schluessel, wert in vorhanden.items():
                        if schluessel not in d:
                            d[schluessel] = wert
        except Exception:
            pass          # kaputte Datei -> lieber neu schreiben als abbrechen

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls) -> "AppConfig":
        """Laedt Config + API-Keys aus .env."""
        cfg = cls()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = cls._from_dict(data)
            except Exception as e:
                print(f"⚠️ Config-Load Fehler: {e} - nutze Defaults")

        # API-Keys aus .env laden (UEBERSCHREIBT was in config.json war!)
        cfg.exchange.load_api_keys()
        cfg.telegram.load_from_env()

        return cfg

    @classmethod
    def _from_dict(cls, data: Dict) -> "AppConfig":
        """Konvertiert Dict in AppConfig (mit Fallbacks fuer fehlende Felder)."""
        cfg = cls()

        def _set_section(section_name, dataclass_type):
            if section_name in data:
                section_data = data[section_name]
                if isinstance(section_data, dict):
                    section = getattr(cfg, section_name)
                    for k, v in section_data.items():
                        if hasattr(section, k):
                            try:
                                setattr(section, k, v)
                            except Exception:
                                pass

        _set_section("exchange", ExchangeConfig)
        _set_section("risk", RiskConfig)
        _set_section("trading", TradingConfig)
        _set_section("rebalance", RebalanceConfig)
        _set_section("ai", AIConfig)
        _set_section("telegram", TelegramConfig)
        _set_section("dashboard", DashboardConfig)

        # Modes hat verschachtelte Struktur
        if "modes" in data and isinstance(data["modes"], dict):
            modes_data = data["modes"]
            if "active_mode" in modes_data:
                cfg.modes.active_mode = modes_data["active_mode"]
            # [BTC-ONLY 07.08.2026] btc_only mit aufnehmen - fehlt der Name
            # hier, wird der Modus zwar angelegt, aber die Werte aus
            # config.json werden beim Start stillschweigend ignoriert.
            for mode_name in ["all_in", "balanced", "diversified", "btc_only"]:
                if mode_name in modes_data:
                    md = modes_data[mode_name]
                    target = getattr(cfg.modes, mode_name)
                    if isinstance(md, dict):
                        for k, v in md.items():
                            if hasattr(target, k):
                                setattr(target, k, v)

        return cfg
