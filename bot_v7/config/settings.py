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
    """Boersen-Konfiguration. API-Keys NIE hier - aus .env!

    [BEFUND 69, 14.09.2026] ZWEI BOERSEN, NICHT EINE
    -------------------------------------------------
    Bis hierher steuerte EIN Feld (`ccxt_id`) beides: woher die Kurse
    kommen UND wo gehandelt wird. Das ist falsch, und CLAUDE.md sagt es
    seit Wochen:

        "Datenquelle Binance (nur Kurse), gehandelt wird bei Bybit EU"

    Jetzt getrennt:

        ccxt_id           die DATENQUELLE fuer Kurse  -> binance
        handel_ccxt_id    das HANDELSZIEL             -> bybit
        handel_hostname   die Plattform darunter      -> bybit.eu

    WARUM DER HOSTNAME EIGENS DASTEHT: ccxt kennt nur EINE
    Bybit-Anbindung, und die zeigt fest auf `bybit.com`. Am 14.09.2026
    nachgemessen: `ccxt.bybit().hostname` ist `bybit.com`, eine eigene
    bybit.eu-Anbindung gibt es nicht. Bybit EU ist aber eine ANDERE
    Plattform - sie fuehrt EUR-Paare, die es auf bybit.com nicht gibt,
    und sie ist die MiCA-lizenzierte.

    Ohne diese Zeile landete eine Live-Order auf bybit.com. Mit ihr
    laedt ccxt 131 Maerkte von bybit.eu, darunter BTC/USDC, ETH/USDC und
    SOL/USDC - die drei, die der Bot handelt (geprueft am 14.09.).

    WARUM DAS DEN PAPIERHANDEL NICHT ANFASST: `ccxt_id` bleibt auf
    binance. Die Kurse kommen weiter von dort (data/market_data.py:17),
    am laufenden Papierhandel aendert sich nichts - Epoche E9 bleibt
    sauber.
    """
    name: str = "Binance"
    ccxt_id: str = "binance"            # DATENQUELLE fuer Kurse
    handel_ccxt_id: str = "bybit"       # HANDELSZIEL - hier fliesst Geld
    handel_hostname: str = "bybit.eu"   # die MiCA-Plattform, nicht bybit.com
    testnet: bool = False
    quote_currency: str = "USDC"
    timeout_connect: int = 3
    timeout_read: int = 10
    max_retries: int = 3
    # API-Keys werden zur Laufzeit aus .env gelesen
    api_key: str = ""
    api_secret: str = ""
    schluessel_quelle: str = ""         # welcher .env-Name gegriffen hat

    def load_api_keys(self):
        """Laedt API-Keys aus Umgebungsvariablen (.env).

        [BEFUND 69, 14.09.2026] Hier stand NUR `BINANCE_API_KEY`. Wer
        seine Bybit-Schluessel unter `BYBIT_API_KEY` eintrug, bekam eine
        Fehlermeldung ueber fehlende Schluessel - obwohl sie dastanden.

        Gelesen wird jetzt in dieser Reihenfolge:
          1. BYBIT_API_KEY / BYBIT_API_SECRET        die Zielboerse
          2. EXCHANGE_API_KEY / EXCHANGE_API_SECRET  boersenneutral
          3. BINANCE_API_KEY / BINANCE_API_SECRET    alter Name

        Der alte Name bleibt bewusst als letzter Rueckfall: ihn zu
        entfernen wuerde eine bestehende Einrichtung stillschweigend
        lahmlegen, und ein Schluessel, der ploetzlich nicht mehr
        gefunden wird, ist schwer zu suchen.
        """
        namen = (("BYBIT_API_KEY", "BYBIT_API_SECRET"),
                 ("EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"),
                 ("BINANCE_API_KEY", "BINANCE_API_SECRET"))
        for k_name, s_name in namen:
            if not self.api_key:
                self.api_key = os.environ.get(k_name, "")
            if not self.api_secret:
                self.api_secret = os.environ.get(s_name, "")
            if self.api_key and self.api_secret:
                self.schluessel_quelle = k_name.split("_")[0]
                break
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

    # [14.09.2026] Ab wie vielen Punkten der Bot kauft.
    #
    # Stand fest verdrahtet in agents/signal_agent.py. Vorgabe bleibt 3,
    # damit der Papier-Bot unveraendert weiterlaeuft - die Live-Instanz
    # setzt sie hoeher. Befund 103: Score 3-6 verliert (-0,540 %),
    # Score 7-10 gewinnt (+0,468 %), gemessen an 57 Verkaeufen.
    min_signal_score: int = 3

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

    # === [FRAKTAL-TOR 14.09.2026] Svens Verfahren am Handelspfad ===
    #
    # Der Anlass steht in features/fraktal_tor.py ausfuehrlich. Kurz:
    # Am 14.09. kaufte der Live-Bot viermal BTC nach Trendfolge
    # (MACD + EMA + ADX + VWAP), also NACH dem Anstieg. Svens Verfahren
    # kauft im Ruecksetzer - im Golden Pocket. Die dafuer gebaute Datei
    # features/fraktal_konfluenz.py war von keinem Handelspfad
    # importiert; sie rechnete, aber niemand fragte sie.
    #
    # true = das Tor kann Kaeufe VERHINDERN, die der Score erlauben
    #        wuerde. Das ist eine Verhaltensaenderung und braucht eine
    #        Epochengrenze (CLAUDE.md Abschnitt 5).
    # false = der Bot verhaelt sich exakt wie vorher.
    fraktal_tor_aktiv: bool = False

    # Schattenbetrieb: Das Tor rechnet und schreibt sein Urteil ins Log,
    # haelt aber keinen Kauf auf. So entsteht die Messung, BEVOR das
    # Verhalten sich aendert - CLAUDE.md Abschnitt 7.1, "nichts
    # anschliessen ohne Messung". Wirkt nur, wenn fraktal_tor_aktiv an ist.
    fraktal_tor_nur_messen: bool = False

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

    # === [14.09.2026] Befehls-Empfaenger schaltbar ===
    # Seit dem 14.09. laufen zwei Bots (Papier E9 im alten Ordner,
    # Echtgeld hier) mit demselben Telegram-Token - ueber die
    # Pruefsummen beider .env-Dateien nachgemessen, identisch.
    #
    # Telegram liefert eine Nachricht nur EINMAL aus. Zwei Prozesse am
    # selben Token heisst: Ein /notaus landet zufaellig beim falschen
    # Bot. Ausfuehrlich in reports/telegram.py, start_command_listener.
    #
    # Vorgabe AN - abschalten ist eine Entscheidung, kein Nebeneffekt.
    # Die eigentliche Loesung ist ein zweiter Bot-Token.
    befehle_aktiv: bool = True

    def load_from_env(self):
        if not self.token:
            self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not self.chat_id:
            self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        return bool(self.token and self.chat_id)


@dataclass
class DashboardConfig:
    enabled: bool = True

    # === [25.09.2026] EIGENE ANSCHLUESSE FUER v7 (Befund 111) ===
    #
    # Vorher: port 5050, Cockpit fest 8110. Auf diesem Rechner laeuft der
    # v6-Papier-Bot daneben und haelt beide. Folge: v7 meldete "Dashboard
    # http://localhost:5050", der Browser zeigte aber v6-Daten - und der
    # Cockpit-Knopf pruefte nur, ob der Anschluss ANTWORTET, fand v6 und
    # oeffnete dessen Cockpit statt ein eigenes zu starten.
    #
    # Eine Anzeige, die die Zahlen eines anderen Bots zeigt und dabei
    # behauptet, die eigenen zu zeigen, ist schlimmer als keine Anzeige.
    #
    # Die Zahl stand an NEUN Stellen im Code. Jetzt ist sie hier und in
    # data_store/config.json - alles andere liest von hier.
    port: int = 5070              # Dashboard (Flask, im Bot-Prozess)
    cockpit_port: int = 8170      # Analyse-Cockpit (cockpit_server.py)

    # cockpit_port MUSS hier als Feld stehen, nicht nur in der JSON.
    # AppConfig._from_dict uebernimmt ausschliesslich Schluessel, fuer die
    # hasattr(section, k) gilt - ein blosser Block in config.json wird
    # STILL verworfen, und save() (asdict) wuerfe ihn beim naechsten
    # UI-Speichern wieder aus der Datei. Genau das ist dem Tagesverlust-
    # Waechter passiert, siehe den Kommentar bei RiskConfig.daily_loss.
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

        # ================================================================
        # [BEFUND 97, 12.09.2026] SICHERUNG UND WACHPOSTEN VOR DEM SCHREIBEN
        # ----------------------------------------------------------------
        # Am 12.08. verschwand beim Speichern der Telegram-Daten der Block
        # "regel_modi" (Befund 31). Die Reparatur darueber - fremde Bloecke
        # erhalten - hat gehalten, aber am 08.09. passierte es WIEDER, und
        # zwar anders: zwoelf Werte fielen gleichzeitig auf ihre
        # Vorgabewerte zurueck. trading.coins sprang von 3 auf 12,
        # take_profit_pct von 0,0 auf 1,5, stop_loss_pct von 2,5 auf 2,0,
        # initial_paper_balance von 500 auf 300 und so weiter.
        #
        # DIE URSACHE IST OFFEN. Am Code nachgesehen: es gibt im ganzen
        # Projekt keine Stelle, die eine frische AppConfig() baut und
        # speichert - nur die Tests tun das. Wer den Verlust ausloest, ist
        # damit nicht bestimmt.
        #
        # Deshalb steht hier ausdruecklich KEIN Fallback, der den Fehler
        # wegbuegelt. Es waere falsch, etwas zu reparieren, dessen Ursache
        # man nicht kennt. Stattdessen zwei Dinge, die beide nichts
        # verstecken:
        #
        #   1. Eine Sicherung der alten Datei, bevor sie ueberschrieben
        #      wird. Passiert es wieder, ist der letzte gute Stand da -
        #      am 08.09. musste er aus einem git-Commit vom 12.08. geholt
        #      werden, also vier Wochen alt.
        #   2. Ein lauter Hinweis, wenn viele Werte GLEICHZEITIG auf ihre
        #      Vorgabe zurueckfallen. Ein einzelner Wert ist eine
        #      Einstellung, zwoelf auf einmal sind ein Unfall.
        #
        # Das Speichern wird NICHT blockiert. Ein Wachposten, der den
        # Betrieb anhaelt, waere gefaehrlicher als das, was er verhindert.
        # ================================================================
        try:
            self._vor_dem_speichern_sichern(d)
        except Exception as _e:
            # Auch das Scheitern der Sicherung wird gesagt, nicht geschluckt.
            print("[CONFIG] Sicherung vor dem Speichern fehlgeschlagen: %s"
                  % str(_e)[:120])

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)

    # Wie viele Rueckfaelle auf Vorgabewerte gleichzeitig noch normal sind.
    # Einer ist eine Einstellung. Am 08.09. waren es zwoelf.
    RUECKFALL_ALARM = 4
    SICHERUNGEN_BEHALTEN = 12

    def _vor_dem_speichern_sichern(self, neu_d):
        """Legt den alten Stand weg und meldet Massen-Rueckfaelle.

        Gibt die Liste der verdaechtigen Felder zurueck - fuer den Test.
        """
        import glob
        import shutil
        from datetime import datetime

        if not os.path.exists(CONFIG_FILE):
            return []

        # --- 1. Sicherung mit Zeitstempel, rollierend ---------------
        ordner = os.path.dirname(os.path.abspath(CONFIG_FILE))
        stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
        ziel = os.path.join(ordner, "config.json.sicherung_%s" % stempel)
        shutil.copy2(CONFIG_FILE, ziel)

        alt_liste = sorted(glob.glob(os.path.join(
            ordner, "config.json.sicherung_*")))
        for weg in alt_liste[:-self.SICHERUNGEN_BEHALTEN]:
            try:
                os.remove(weg)
            except OSError:
                pass

        # --- 2. Wachposten: fallen viele Werte auf die Vorgabe? -----
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                alt_d = json.load(f)
        except Exception:
            return []          # kaputte Datei - nichts zu vergleichen

        vorgabe = asdict(AppConfig())
        verdaechtig = []
        for block, alt_werte in alt_d.items():
            if not isinstance(alt_werte, dict):
                continue
            neu_werte = neu_d.get(block)
            vorg_werte = vorgabe.get(block)
            if not isinstance(neu_werte, dict) or not isinstance(vorg_werte, dict):
                continue
            for feld, alt_wert in alt_werte.items():
                if feld not in neu_werte or feld not in vorg_werte:
                    continue
                neu_wert, vorg_wert = neu_werte[feld], vorg_werte[feld]
                # Verdaechtig ist NUR: war anders als die Vorgabe, ist
                # jetzt exakt die Vorgabe. Eine bewusste Aenderung auf
                # einen anderen Wert faellt nicht darunter.
                if alt_wert != vorg_wert and neu_wert == vorg_wert:
                    verdaechtig.append("%s.%s: %r -> %r"
                                       % (block, feld, alt_wert, neu_wert))

        # Verschwundene Bloecke sind der Fall von Befund 31.
        for block in alt_d:
            if block not in neu_d:
                verdaechtig.append("Block %s ist ganz verschwunden" % block)

        if len(verdaechtig) >= self.RUECKFALL_ALARM:
            print("")
            print("!" * 70)
            print("  [CONFIG-WACHPOSTEN] %d Werte fallen GLEICHZEITIG auf ihre"
                  % len(verdaechtig))
            print("  Vorgabe zurueck. Das ist Befund 97 - vermutlich kein")
            print("  gewolltes Speichern.")
            for z in verdaechtig[:15]:
                print("     %s" % z)
            if len(verdaechtig) > 15:
                print("     ... und %d weitere" % (len(verdaechtig) - 15))
            print("")
            print("  Der alte Stand liegt in:")
            print("     %s" % ziel)
            print("  Gespeichert wird trotzdem - ein Wachposten, der den")
            print("  Betrieb anhaelt, waere gefaehrlicher als der Fehler.")
            print("!" * 70)
            print("")
            try:
                from core.logger import log
                log.error("CONFIG", "Befund 97: %d Werte auf Vorgabe "
                                    "zurueckgefallen. Sicherung: %s"
                          % (len(verdaechtig), os.path.basename(ziel)))
            except Exception:
                pass

        return verdaechtig

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
