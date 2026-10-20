# -*- coding: utf-8 -*-
"""Trading Imperium V6 - Telemetrie-Datenbank (Kaufpruefungs-Protokoll).

ZWECK
-----
Jede Kaufpruefung wird hier vollstaendig und dauerhaft festgehalten: mit allen
zutreffenden Ablehnungsgruenden (nicht nur dem ersten), mit Zeitpunkt, Preis,
Score und Kapitalstand. Danach beantwortet eine SQL-Abfrage in einer Sekunde,
wofuer am 06.08.2026 noch stundenlange Forensik in einer 20-MB-Logdatei noetig war.

WARUM ES DIESE DATEI GIBT
-------------------------
Am 06.08.2026 zeigte data_store/system.log 14.986 erzeugte BUY-Signale und NULL
Aufrufe von RiskEngine.check(). Die Ursache (app.py:675, UnboundLocalError durch
lokalen Import) war nur zu finden, weil der Event-Bus nachtraeglich zum Reden
gebracht wurde. Ohne Protokoll ist "warum hat er nicht gekauft" nicht
beantwortbar, sondern nur erratbar.

ABGRENZUNG - nicht verhandelbar
-------------------------------
Das ist NICHT docs/forschungsprogramm_2026-07/forschung.db. Jene Datenbank
gehoert ausschliesslich zum Forschungsprogramm und ist laut DATENBANK.md:8-13
bewusst vom laufenden Bot abgekoppelt. Diese hier ist die Betriebstelemetrie des
Live-Bots und liegt getrennt in data_store/telemetrie.db.

ROBUSTHEITSREGEL
----------------
Diese Datei darf den Bot NIEMALS anhalten. Jeder Schreibvorgang ist gekapselt;
schlaegt die Datenbank fehl, geht der Datensatz in eine Notfall-Datei
(telemetrie_ausfall.jsonl) und der Handel laeuft weiter. Ein Protokoll, das den
Betrieb gefaehrdet, waere schlimmer als kein Protokoll.
"""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

try:
    from config.settings import DATA_DIR
except Exception:                                    # Notfall-Pfad
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

DB_DATEI = os.path.join(DATA_DIR, "telemetrie.db")
AUSFALL_DATEI = os.path.join(DATA_DIR, "telemetrie_ausfall.jsonl")

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id   TEXT PRIMARY KEY,
    ts_utc          TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,
    decision        TEXT NOT NULL,   -- APPROVED | REJECTED
    reject_art      TEXT,            -- Kapazitaet | STOERUNG | NULL
    primary_reason  TEXT,
    grund_anzahl    INTEGER NOT NULL DEFAULT 0,
    score           INTEGER,
    confidence      REAL,
    entry_price     REAL,
    amount_usd      REAL,
    stop_loss       REAL,
    strategy_id     TEXT,
    entry_reason    TEXT,
    total_equity    REAL,
    cycle_phase     TEXT,
    offene_positionen INTEGER,
    config_version  TEXT
);
CREATE TABLE IF NOT EXISTS rule_evaluations (
    evaluation_id TEXT NOT NULL,
    rule_name     TEXT NOT NULL,
    result        TEXT NOT NULL,     -- BLOCK | PASS | NOT_EVALUATED
    detail        TEXT,
    ts_utc        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schatten_exits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    position_id   TEXT,
    symbol        TEXT NOT NULL,
    regel         TEXT NOT NULL,   -- welche Regel haette ausgeloest
    grund         TEXT,
    preis         REAL,            -- Kurs im Moment des Schatten-Signals
    pnl_pct       REAL,            -- Stand der Position zu diesem Zeitpunkt
    hoechst_pnl_pct REAL,
    entry_price   REAL,
    entry_score   INTEGER
);
CREATE TABLE IF NOT EXISTS schatten_regeln (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    regel         TEXT NOT NULL,   -- trend_exit | baerenmarkt | ...
    symbol        TEXT,
    haette        TEXT,            -- was die Regel getan haette
    grund         TEXT,
    preis         REAL,
    pnl_pct       REAL,
    position_id   TEXT,
    zusatz        TEXT
);
CREATE INDEX IF NOT EXISTS ix_schregel_regel ON schatten_regeln(regel);
CREATE INDEX IF NOT EXISTS ix_schregel_ts    ON schatten_regeln(ts_utc);
CREATE TABLE IF NOT EXISTS markt_historie (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    fear_greed    INTEGER,
    nupl          REAL,
    nupl_zone     TEXT,
    dxy           REAL,
    dxy_trend     TEXT,
    funding_score REAL,
    whale_score   REAL,
    onchain_score REAL,
    reddit_score  REAL,
    capitol_score REAL,
    cycle_phase   TEXT,
    regime        TEXT,
    btc_preis     REAL,
    eth_preis     REAL,
    sol_preis     REAL,
    equity        REAL,
    cash          REAL,
    offene_pos    INTEGER
);
CREATE INDEX IF NOT EXISTS ix_markt_ts ON markt_historie(ts_utc);
CREATE TABLE IF NOT EXISTS schatten_sizing (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    echt_usd      REAL,            -- was der Bot wirklich gekauft hat
    schatten_usd  REAL,            -- was adaptive_sizing getan HAETTE
    differenz_usd REAL,            -- schatten minus echt (negativ = kleiner)
    schatten_pct  REAL,
    gruende       TEXT,
    confidence    REAL,
    win_rate      REAL,
    drawdown_pct  REAL,
    verlustserie  INTEGER,
    regime        TEXT,
    fear_greed    INTEGER
);
CREATE INDEX IF NOT EXISTS ix_schsiz_ts  ON schatten_sizing(ts_utc);
CREATE INDEX IF NOT EXISTS ix_schsiz_sym ON schatten_sizing(symbol);
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name      TEXT NOT NULL,
    pid           INTEGER,
    start_utc     TEXT NOT NULL,
    ende_utc      TEXT,
    laufzeit_sek  REAL,
    exit_code     INTEGER,          -- NULL = laeuft noch
    status        TEXT NOT NULL,    -- LAEUFT | OK | FEHLER | ABGEBROCHEN
    logpfad       TEXT,
    fehlerauszug  TEXT,
    befehl        TEXT
);
CREATE INDEX IF NOT EXISTS ix_jobs_name ON jobs(job_name, start_utc);
CREATE INDEX IF NOT EXISTS ix_jobs_stat ON jobs(status);
CREATE TABLE IF NOT EXISTS lern_ereignisse (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    strategie     TEXT NOT NULL,
    pnl_usd       REAL NOT NULL,
    gewonnen      INTEGER NOT NULL,   -- 1 = Gewinn, 0 = Verlust oder exakt 0
    quelle        TEXT,               -- exit_monitor | order_filled | ...
    symbol        TEXT,
    position_id   TEXT
);
CREATE INDEX IF NOT EXISTS ix_lern_strat ON lern_ereignisse(strategie);
CREATE INDEX IF NOT EXISTS ix_lern_ts    ON lern_ereignisse(ts_utc);
CREATE INDEX IF NOT EXISTS ix_schatten_pos  ON schatten_exits(position_id);
CREATE INDEX IF NOT EXISTS ix_schatten_regel ON schatten_exits(regel);
CREATE INDEX IF NOT EXISTS ix_eval_ts     ON evaluations(ts_utc);
CREATE INDEX IF NOT EXISTS ix_eval_sym    ON evaluations(symbol, ts_utc);
CREATE INDEX IF NOT EXISTS ix_eval_dec    ON evaluations(decision);
CREATE INDEX IF NOT EXISTS ix_rule_eval   ON rule_evaluations(evaluation_id);
CREATE INDEX IF NOT EXISTS ix_rule_name   ON rule_evaluations(rule_name);
"""

# [VERKAUFS-LUECKE 10.08.2026] Zusatzspalten fuer die Verkaufsseite.
#
# BEFUND: Die DB enthielt 52.198 Kaufpruefungen und NULL Verkaeufe. Grund:
# Verkaeufe laufen ueber runtime/exit_monitor.py und werden dort bewusst
# SOFORT ausgefuehrt statt ueber den EventBus (exit_monitor.py:216
# "nicht ueber EventBus, das koennte verzoegern"). Damit lief die gesamte
# Verkaufsseite an der Telemetrie vorbei.
#
# Folge im Alltag: Als am 07.08. SOL verkauft wurde, war der Grund
# hinterher nicht mehr feststellbar - system.log war bereits rotiert.
# Genau das soll die Telemetrie verhindern.
#
# Diese Spalten werden per ALTER TABLE nachgeruestet, damit bestehende
# Datenbanken nicht neu angelegt werden muessen (die 52k Kaufzeilen
# bleiben erhalten).
ZUSATZSPALTEN = (
    ("pnl_usd", "REAL"),          # realisierter Gewinn/Verlust in USD
    ("pnl_pct", "REAL"),          # dasselbe in Prozent
    ("qty", "REAL"),              # verkaufte Menge
    ("fee", "REAL"),              # Gebuehr des Verkaufs
    ("mfe_pct", "REAL"),          # hoechster Stand ueber Einstand (max favorable)
    ("mae_pct", "REAL"),          # tiefster Stand unter Einstand (max adverse)
    ("haltedauer_min", "REAL"),   # wie lange die Position offen war
    ("position_id", "TEXT"),      # Bruecke zu den Toepfen (Schritt 1)

    # ================================================================
    # SCHRITT 3 des Messfenster-Plans, 13.08.2026
    # (Begruendung je Spalte in SCHRITT3-DATENBANK-PLAN.md)
    #
    # Leitsatz: Ein Feld, das im Messfenster nicht mitgeschrieben wird,
    # ist hinterher NICHT nachruestbar - der Marktzustand von damals ist
    # weg. Kosten einer ueberfluessigen Spalte: ein paar Bytes. Kosten
    # einer fehlenden: das Messfenster nochmal fahren, zwei Wochen.
    # ================================================================

    # --- Gruppe A: lag schon im intent vor, wurde nur nie geschrieben ---
    ("decision_id", "TEXT"),      # intent.id - die Bruecke Entscheidung->Order->Fill
    ("cycle_id", "INTEGER"),      # welcher Analyse-Durchlauf (app._cycle_id)
    ("take_profit", "REAL"),      # bleibt NULL: wird nirgends gesetzt (bewusst,
                                  # Sven 13.08.: "hab ich bewusst kein TP")
    ("trailing_stop_pct", "REAL"),# der tatsaechliche Ausstiegsmechanismus
    ("max_slippage_pct", "REAL"), # angenommener Schlupf - Vergleich zum gemessenen
    ("quantity_geplant", "REAL"), # geplante Menge; gegen qty = Teilfuellungen
    ("agent_id", "TEXT"),         # wer hat das Signal erzeugt
    ("model_version", "TEXT"),    # Pflicht laut MASTERPROMPT.md Abschnitt J
    ("spread_pct", "REAL"),       # aus app._spread_cache - wurde befuellt, nie gespeichert

    # --- Gruppe B: vorhanden, musste durchgereicht werden ---
    ("git_commit", "TEXT"),       # BEWEIST, dass im Messfenster nichts geaendert wurde
    ("regime", "TEXT"),           # Auswertung nach Marktregime ist ausdrueckliches Ziel
    ("fear_greed", "INTEGER"),    # steht in markt_historie, fehlte am Einzelfall
    ("daten_alter_sec", "REAL"),  # wie alt war die Kerze? erklaert spaetere Ausreisser
    ("quellen_gesund", "TEXT"),   # welche externen Quellen lebten zur Entscheidungszeit

    # --- Gruppe C: Risiko-Kennzahlen (Basis fuer das R-Vielfache) ---
    # RR-Netto ist in diesem Bot nicht berechenbar - ohne Kursziel fehlt
    # der Zaehler. Stattdessen das R-Vielfache: R = Einstieg - Stop (ist
    # bekannt), Ergebnis = Gewinn / R. Siehe SCHRITT3-DATENBANK-PLAN.md.
    ("risiko_r_usd", "REAL"),     # (entry - stop) * menge = 1R in Dollar
    ("risiko_pct", "REAL"),       # (entry - stop) / entry * 100 = Stop-Abstand
    ("kosten_erwartet_pct", "REAL"),  # Gebuehr ein+aus + Spread + Schlupf
    ("r_multiple_netto", "REAL"), # beim Verkauf: (pnl - Kosten) / risiko_r_usd
    ("rr_geplant_netto", "REAL"), # bleibt NULL solange es keine Kursziele gibt -
                                  # die Spalte ist die Reserve, falls doch welche kommen

    # --- Gruppe D: Verweis auf den Merkmals-Schnappschuss ---
    ("feature_snapshot_id", "TEXT"),
)

# Tabelle fuer die Merkmals-Schnappschuesse (Gruppe D).
#
# WARUM EIGENE TABELLE: Ein Schnappschuss hat rund 20 Zahlen. Als Spalten
# in evaluations waere die Tabelle unlesbar, und mehrere Entscheidungen
# koennen aus demselben Schnappschuss entstehen.
#
# WARUM AUS snap._df UND NICHT AUS snapshot.indicators: Das Dict in
# data/market_data.py:76 enthaelt nur SIEBEN Werte (rsi, ema20, ema50,
# macd, macd_signal, adx, atr). Berechnet werden aber auch EMA200,
# MACD-Histogramm und die kompletten Bollinger-Baender - die stehen
# ausschliesslich im angehaengten DataFrame (snap._df, market_data.py:80)
# und gingen bisher verloren. Sven am 13.08. auf die Frage nach dem
# Umfang: "ich würde auch sagen alle".
SCHEMA_FEATURES = """
CREATE TABLE IF NOT EXISTS feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY,
    ts_utc          TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    timeframe       TEXT,
    kerze_zeit      TEXT,        -- Zeitstempel der verwendeten Kerze
    kerze_offen     INTEGER,     -- 1 = Kerze noch nicht geschlossen
    schema_version  TEXT,        -- steigt, wenn sich der Satz aendert
    -- Preis / Kerze
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    volume          REAL,
    -- Klassische Indikatoren
    rsi             REAL,
    stoch_rsi       REAL,
    macd            REAL,
    macd_signal     REAL,
    macd_hist       REAL,
    ema20           REAL,
    ema50           REAL,
    ema200          REAL,
    atr             REAL,
    adx             REAL,
    bb_unten        REAL,
    bb_mitte        REAL,
    bb_oben         REAL,
    bb_breite       REAL,
    bb_lage         REAL,        -- wo im Band liegt der Kurs (0..1)
    obv             REAL,
    vwap            REAL,
    tsi             REAL,
    tsi_signal      REAL,
    -- Abgeleitete Merkmale
    returns         REAL,
    volatility      REAL,
    volume_sma      REAL,
    volume_ratio    REAL,
    high_low_range  REAL,
    close_to_ema20  REAL,
    -- Alles Uebrige unveraendert als JSON, damit nichts verloren geht,
    -- wenn calc_all_indicators spaeter neue Spalten liefert.
    rest_json       TEXT
);
CREATE INDEX IF NOT EXISTS idx_feat_symbol_ts
    ON feature_snapshots (symbol, ts_utc);
"""

# Steigt, wenn sich der Satz der Merkmale aendert. Alte Zeilen behalten
# ihre Version - so ist spaeter erkennbar, dass sie mit einer anderen
# Formel entstanden sind (MASTERPROMPT.md, Abschnitt D).
FEATURE_SCHEMA_VERSION = "1.0"

# DataFrame-Spalte -> Tabellenspalte. Was hier nicht steht, landet in
# rest_json. Bollinger-Spalten heissen bei pandas_ta z.B. BBL_20_2.0 -
# deshalb wird unten zusaetzlich nach Praefix gesucht.
FEATURE_MAPPING = {
    "Open": "open", "High": "high", "Low": "low",
    "Close": "close", "Volume": "volume",
    "RSI": "rsi", "StochRSI": "stoch_rsi",
    "MACD": "macd", "MACD_signal": "macd_signal", "MACD_hist": "macd_hist",
    "EMA20": "ema20", "EMA50": "ema50", "EMA200": "ema200",
    "ATR": "atr", "ADX": "adx",
    "OBV": "obv", "VWAP": "vwap",
    "TSI": "tsi", "TSI_signal": "tsi_signal",
    "returns": "returns", "volatility": "volatility",
    "volume_sma": "volume_sma", "volume_ratio": "volume_ratio",
    "high_low_range": "high_low_range", "close_to_ema20": "close_to_ema20",
}

# Bollinger: pandas_ta haengt die Parameter an den Namen (BBL_20_2.0).
FEATURE_BB_PRAEFIX = {
    "BBL": "bb_unten", "BBM": "bb_mitte", "BBU": "bb_oben",
    "BBB": "bb_breite", "BBP": "bb_lage",
}

# Ablehnungsgruende auf stabile Regelnamen abbilden. Der Bot formuliert sie als
# Fliesstext mit Zahlen drin ("Max Positionen: 3/3") - fuer Auswertungen braucht
# es einen Namen, der sich nicht aendert, wenn sich die Zahl aendert.
_REGELN = (
    ("Max Positionen", "MAX_POSITIONEN"),
    ("Bereits in Position", "BEREITS_IN_POSITION"),
    ("Schlafmodus", "SCHLAFMODUS"),
    ("Kill-Switch", "KILL_SWITCH"),
    ("Drawdown", "DRAWDOWN_GUARD"),
    ("Exposure nicht pruefbar", "KAPITALBASIS_UNBEKANNT"),
    ("Cooldown", "COOLDOWN_NACH_VERLUST"),
    ("Baerenmarkt", "BAERENMARKT_NUR_BTC_ETH"),
    ("Sektor", "SEKTOR_LIMIT"),
    ("Exposure", "COIN_EXPOSURE_LIMIT"),
    # [LUECKE GESCHLOSSEN 06.08.2026] Der Regime-Filter blockiert in
    # app.py _on_market_update, also VOR der Risk-Pruefung. Diese Faelle
    # fehlten komplett in der Datenbank - SOL tauchte deshalb ueberhaupt
    # nicht auf, obwohl es dauernd blockiert wurde.
    ("Regime-Filter", "REGIME_FILTER"),
    ("Smart-Entry", "SMART_ENTRY_WARTET"),
    ("Modus-Sperre", "MODUS_SPERRE"),
    ("Wiedereinstiegs-Sperre", "WIEDEREINSTIEGS_SPERRE"),
)

# Ablehnungen, die eine echte Stoerung anzeigen (alles andere ist Kapazitaet
# oder gewollte Marktfilterung).
_STOERUNGSMUSTER = ("Exposure nicht pruefbar", "Drawdown", "Kill-Switch")
_MARKTFILTER = ("Regime-Filter",)


def regelname(grundtext: str) -> str:
    """Ordnet einem Grundtext einen stabilen Regelnamen zu.

    "Max Positionen: 3/3" und "Max Positionen: 5/5" sind dieselbe Regel -
    ohne diese Abbildung waere jede Zahlaenderung ein neuer Gruppenschluessel
    und keine Auswertung ueber Zeit moeglich.
    """
    text = (grundtext or "").lower()
    for muster, name in _REGELN:
        if muster.lower() in text:
            return name
    return "SONSTIGE"


class Telemetrie:
    """Schreibt Kaufpruefungen in die Datenbank. Fehlertolerant per Design."""

    def __init__(self, db_datei: str = DB_DATEI):
        self.db_datei = db_datei
        self._lock = threading.Lock()
        self.geschrieben = 0
        self.ausgefallen = 0
        self.aktiv = False
        try:
            os.makedirs(os.path.dirname(self.db_datei), exist_ok=True)
            with self._verbinde() as con:
                con.executescript(SCHEMA)
                # [SCHRITT 3, 13.08.2026] Merkmals-Schnappschuesse.
                con.executescript(SCHEMA_FEATURES)
                self._migriere(con)
            self.aktiv = True
        except Exception:
            self.aktiv = False          # Bot laeuft trotzdem weiter

    def _migriere(self, con):
        """Ruestet fehlende Spalten nach - idempotent, gefahrlos wiederholbar.

        SQLite kennt kein 'ADD COLUMN IF NOT EXISTS'. Deshalb wird erst
        gelesen, welche Spalten existieren, und nur wirklich Fehlendes
        ergaenzt. Bestehende Daten bleiben unangetastet: ALTER TABLE ADD
        COLUMN schreibt in SQLite keine Zeilen um, die neuen Felder sind
        bei Altzeilen einfach NULL.
        """
        try:
            vorhanden = {r[1] for r in con.execute("PRAGMA table_info(evaluations)")}
            for name, typ in ZUSATZSPALTEN:
                if name not in vorhanden:
                    con.execute(f"ALTER TABLE evaluations ADD COLUMN {name} {typ}")
        except Exception:
            pass          # Migration darf den Bot nie anhalten

    def _verbinde(self):
        con = sqlite3.connect(self.db_datei, timeout=5.0)
        con.execute("PRAGMA journal_mode=WAL")       # nebenlaeufig lesbar
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    def protokolliere(self, intent, portfolio=None, cycle_phase="",
                      offene_positionen=None, config_version="", kontext=None):
        """Haelt EINE Kaufpruefung fest. Wirft niemals nach aussen.

        kontext : optionales Dict mit Zusatzfeldern (Gruppe B/C aus
                  SCHRITT3-DATENBANK-PLAN.md) - git_commit, regime,
                  fear_greed, spread_pct, cycle_id, feature_snapshot_id,
                  daten_alter_sec, quellen_gesund, kosten_erwartet_pct.
                  Unbekannte Schluessel werden still verworfen, damit ein
                  Tippfehler im Aufrufer nie den INSERT sprengt.

        Rueckgabe: evaluation_id (auch wenn nur die Notfall-Datei beschrieben
        werden konnte) oder "" wenn gar nichts ging.
        """
        try:
            datensatz = self._baue_datensatz(
                intent, portfolio, cycle_phase, offene_positionen,
                config_version, kontext)
        except Exception:
            return ""

        try:
            with self._lock:
                with self._verbinde() as con:
                    # [SCHRITT 3, 13.08.2026] INSERT aus den Schluesseln
                    # gebaut statt fest verdrahtet.
                    #
                    # Vorher standen hier 19 Spaltennamen und 19 Fragezeichen,
                    # passend zu einem 19-stelligen Tupel aus
                    # _baue_datensatz(). Mit den neuen Feldern waeren daraus
                    # 39 Positionen geworden - und eine Verwechslung waere
                    # STILL: der Wert landete in der falschen Spalte, die
                    # Datenbank meldet nichts, und die Auswertung nach dem
                    # Messfenster waere falsch, ohne dass es jemand sieht.
                    # Ueber Namen kann das nicht passieren.
                    felder = datensatz["felder"]
                    spalten = ",".join(felder.keys())
                    platz = ",".join("?" * len(felder))
                    con.execute(
                        f"INSERT OR REPLACE INTO evaluations ({spalten}) "
                        f"VALUES ({platz})",
                        tuple(felder.values()))
                    if datensatz["regeln"]:
                        con.executemany(
                            "INSERT INTO rule_evaluations (evaluation_id,rule_name,"
                            "result,detail,ts_utc) VALUES (?,?,?,?,?)",
                            datensatz["regeln"])
            self.geschrieben += 1
            return datensatz["id"]
        except Exception as fehler:
            self._notfall(datensatz, fehler)
            return datensatz["id"]

    def position_verknuepfen(self, evaluation_id, position_id):
        """[SCHRITT 3, 13.08.2026] Traegt die position_id am Einstieg nach.

        WARUM NACHTRAEGLICH: Die Entscheidung wird protokolliert, BEVOR
        die Order laeuft - zu dem Zeitpunkt existiert noch keine Position
        und damit keine position_id. Erst wenn der Kauf gefuellt ist,
        entsteht sie (risk/engine.py:122).

        WARUM UEBERHAUPT: Ohne diese Bruecke findet der Verkauf seine
        Einstiegszeile nicht - und ohne die gibt es kein R-Vielfaches,
        weil das Risiko R = (Einstieg - Stop) * Menge dort steht.
        Gemessen am 13.08.: 7 APPROVED-Zeilen, davon 0 mit position_id;
        8 SOLD-Zeilen, alle 8 mit. Die Kette war also an genau dieser
        Stelle unterbrochen.

        Wirft nie nach aussen.
        """
        if not evaluation_id or not position_id:
            return False
        try:
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "UPDATE evaluations SET position_id = ? "
                        "WHERE evaluation_id = ?",
                        (str(position_id), str(evaluation_id)))
            return True
        except Exception:
            return False

    def protokolliere_verkauf(self, symbol, preis, qty, pnl_usd, pnl_pct,
                              grund, strategie="", fee=0.0, mfe_pct=None,
                              mae_pct=None, haltedauer_min=None,
                              position_id="", cycle_phase="", equity=None):
        """[VERKAUFS-LUECKE 10.08.2026] Haelt EINEN Verkauf im Protokoll fest.

        Eigene Methode statt protokolliere(), weil ein Verkauf voellig andere
        Daten hat: Es gibt keine Ablehnungsgruende und keine Risk-Pruefung,
        dafuer ein Ergebnis (pnl), eine Haltedauer und MFE/MAE.

        decision='SOLD' unterscheidet die Zeile klar von APPROVED/REJECTED.
        Damit bleiben alle bestehenden Abfragen unveraendert gueltig - wer
        nach decision='APPROVED' filtert, bekommt weiterhin nur Kaeufe.

        Wirft nie nach aussen. Ein Protokollfehler darf keinen Verkauf
        gefaehrden - der ist zu diesem Zeitpunkt bereits ausgefuehrt.
        """
        try:
            eid = uuid.uuid4().hex
            jetzt = datetime.now(timezone.utc).isoformat()
            felder = {
                "evaluation_id": eid, "ts_utc": jetzt,
                "symbol": str(symbol or ""), "side": "SELL",
                "decision": "SOLD", "primary_reason": str(grund or "")[:300],
                "grund_anzahl": 0,
                "entry_price": _zahl(preis, float),
                "strategy_id": str(strategie or ""),
                "entry_reason": str(grund or "")[:400],
                "total_equity": _zahl(equity, float),
                "cycle_phase": str(cycle_phase or ""),
                "pnl_usd": _zahl(pnl_usd, float),
                "pnl_pct": _zahl(pnl_pct, float),
                "qty": _zahl(qty, float), "fee": _zahl(fee, float),
                "mfe_pct": _zahl(mfe_pct, float),
                "mae_pct": _zahl(mae_pct, float),
                "haltedauer_min": _zahl(haltedauer_min, float),
                "position_id": str(position_id or ""),
            }

            # [SCHRITT 3, 13.08.2026] Das R-VIELFACHE.
            #
            # RR-Netto ist in diesem Bot nicht berechenbar: take_profit
            # wird nirgends gesetzt (bewusst - der Ausstieg ist
            # regelbasiert), und ohne Kursziel fehlt dem klassischen
            # Chance-Risiko-Verhaeltnis der Zaehler.
            #
            # Das R-Vielfache braucht kein Ziel. Das Risiko einer Position
            # steht beim EINSTIEG fest: R = (Einstieg - Stop) * Menge.
            # Genau das hat _baue_datensatz() als risiko_r_usd gespeichert.
            # Hier wird es ueber die position_id wieder eingesammelt:
            #
            #     R-Vielfaches = (Gewinn - Kosten) / R
            #
            # "+2,5R" heisst: der Trade brachte zweieinhalb mal so viel
            # ein, wie beim Stop verloren gegangen waere. Ueber viele
            # Trades beantwortet der Mittelwert die Frage, die RR-Netto
            # beantworten sollte - lohnt das eingegangene Risiko?
            risiko = None
            if position_id:
                try:
                    with self._verbinde() as con:
                        treffer = con.execute(
                            "SELECT risiko_r_usd FROM evaluations "
                            "WHERE position_id = ? AND decision = 'APPROVED' "
                            "AND risiko_r_usd IS NOT NULL "
                            "ORDER BY ts_utc LIMIT 1", (str(position_id),)
                        ).fetchone()
                    if treffer and treffer[0]:
                        risiko = float(treffer[0])
                except Exception:
                    risiko = None

            if risiko and risiko > 0:
                _pnl = _zahl(pnl_usd, float) or 0.0
                _fee = _zahl(fee, float) or 0.0
                # fee ist die Verkaufsgebuehr; die Kaufgebuehr steckt
                # bereits in der cost_basis, mit der pnl_usd gerechnet
                # wurde (siehe app.py, E9-FEE). Nicht doppelt abziehen.
                felder["r_multiple_netto"] = round((_pnl - _fee) / risiko, 4)
                felder["risiko_r_usd"] = round(risiko, 6)

            namen = ",".join(felder.keys())
            platz = ",".join("?" * len(felder))
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        f"INSERT INTO evaluations ({namen}) VALUES ({platz})",
                        tuple(felder.values()))
            self.geschrieben += 1
            return eid
        except Exception as fehler:
            # Notfall-Datei, damit der Verkauf auch bei DB-Ausfall belegbar bleibt
            try:
                with open(AUSFALL_DATEI, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "typ": "VERKAUF", "symbol": str(symbol),
                        "preis": str(preis), "qty": str(qty),
                        "pnl_usd": str(pnl_usd), "grund": str(grund),
                        "db_fehler": f"{type(fehler).__name__}: {fehler}",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            self.ausgefallen += 1
            return ""

    def job_start(self, job_name, pid=None, logpfad="", befehl="",
                  start_utc=None):
        """[HINTERGRUNDJOBS 11.08.2026] Vermerkt den Start eines Jobs.

        Rueckgabe: die Zeilen-id fuer job_ende(), oder None.

        WARUM ES DAS GIBT
        -----------------
        Ein Fenster zu unterdruecken ist einfach. Die Gefahr dabei ist, dass
        man ein nerviges Fenster gegen einen blinden Fleck tauscht - und
        genau ein blinder Fleck (verschluckte Fehler im Event-Bus) war am
        06.08.2026 das Ausgangsproblem des ganzen Projekts. Deshalb gilt:
        kein unsichtbarer Prozess ohne beobachtbaren Status.
        """
        try:
            with self._lock:
                with self._verbinde() as con:
                    cur = con.execute(
                        "INSERT INTO jobs (job_name,pid,start_utc,status,"
                        "logpfad,befehl) VALUES (?,?,?,'LAEUFT',?,?)",
                        (str(job_name or "?")[:60],
                         int(pid) if pid else None,
                         # [BEFUND 80, 26.08.2026] Bisher stand hier fest
                         # datetime.now(). Wer job_start() und job_ende()
                         # NACH getaner Arbeit hintereinander ruft - so
                         # macht es job_zahlenbuch.py - bekommt dadurch
                         # start == ende und laufzeit_sek = 0,0.
                         # Gemessen: 42 von 43 Laeufen bei
                         # zahlenbuch_morgen, 1.722 von 2.036 bei
                         # forschung_capture. Die Spalte sah aus, als
                         # habe der Job keine Zeit gebraucht, statt zu
                         # sagen "nicht gemessen".
                         #
                         # Der Vorgabewert None erhaelt das bisherige
                         # Verhalten fuer alle bestehenden Aufrufer -
                         # auch fuer den laufenden Bot, der diese Datei
                         # erst bei einem Neustart neu liest.
                         (start_utc or
                          datetime.now(timezone.utc).isoformat()),
                         str(logpfad or "")[:300], str(befehl or "")[:400]))
                    return cur.lastrowid
        except Exception:
            self.ausgefallen += 1
            return None

    def job_ende(self, zeilen_id, exit_code=None, fehlerauszug="",
                 status=None):
        """Schliesst einen Job ab: Endzeit, Laufzeit, Exit-Code, Fehlerauszug."""
        if zeilen_id is None:
            return False
        try:
            jetzt = datetime.now(timezone.utc)
            if status is None:
                status = "OK" if exit_code == 0 else "FEHLER"
            with self._lock:
                with self._verbinde() as con:
                    row = con.execute("SELECT start_utc FROM jobs WHERE id=?",
                                      (zeilen_id,)).fetchone()
                    dauer = None
                    if row:
                        try:
                            dauer = round((jetzt - datetime.fromisoformat(
                                row[0])).total_seconds(), 1)
                        except Exception:
                            dauer = None
                    con.execute(
                        "UPDATE jobs SET ende_utc=?,laufzeit_sek=?,exit_code=?,"
                        "status=?,fehlerauszug=? WHERE id=?",
                        (jetzt.isoformat(), dauer,
                         int(exit_code) if exit_code is not None else None,
                         status, str(fehlerauszug or "")[:2000], zeilen_id))
            return True
        except Exception:
            self.ausgefallen += 1
            return False

    def schatten_regel(self, regel="", symbol="", haette="", grund="",
                       preis=None, pnl_pct=None, position_id="", zusatz=""):
        """[AUFGABE 3, 11.08.2026] Haelt fest, was eine Regel getan HAETTE.

        Gegenstueck zu core/regel_schalter.py. Die Regel handelt dabei
        nicht - erst der spaetere Vergleich mit dem tatsaechlichen Ausgang
        beantwortet, ob sie genuetzt haette.

        Wirft nie nach aussen.
        """
        try:
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "INSERT INTO schatten_regeln (ts_utc,regel,symbol,"
                        "haette,grund,preis,pnl_pct,position_id,zusatz) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(),
                         str(regel or "")[:40], str(symbol or "")[:40],
                         str(haette or "")[:200], str(grund or "")[:300],
                         _zahl(preis, float), _zahl(pnl_pct, float),
                         str(position_id or "")[:60], str(zusatz or "")[:200]))
            self.geschrieben += 1
            return True
        except Exception:
            self.ausgefallen += 1
            return False

    def markt_schnappschuss(self, **felder):
        """[MARKTDATEN-HISTORIE 11.08.2026] Haelt EINEN Messpunkt fest.

        WARUM DAS DER WICHTIGSTE FEHLENDE BAUSTEIN WAR
        ----------------------------------------------
        bot_state.json speichert von Funding, Whale, DXY, NUPL, Onchain und
        Fear&Greed immer nur den AKTUELLEN Wert - der alte wird bei jedem
        Speichern ueberschrieben. Damit laesst sich die entscheidende Frage
        gar nicht stellen: sagt einer dieser Werte irgendetwas vorher?

        Ohne Zeitreihe ist jede Antwort darauf Meinung. Mit Zeitreihe wird
        sie in ein paar Wochen eine Rechnung: Wert von damals gegen das,
        was danach tatsaechlich passiert ist.

        Der Wert steigt mit der Zeit - deshalb faengt das Sammeln JETZT an
        und nicht dann, wenn die Auswertung gebraucht wird.

        Wirft nie nach aussen.
        """
        spalten = ("fear_greed", "nupl", "nupl_zone", "dxy", "dxy_trend",
                   "funding_score", "whale_score", "onchain_score",
                   "reddit_score", "capitol_score", "cycle_phase", "regime",
                   "btc_preis", "eth_preis", "sol_preis", "equity", "cash",
                   "offene_pos")
        text_spalten = {"nupl_zone", "dxy_trend", "cycle_phase", "regime"}
        ganzzahl = {"fear_greed", "offene_pos"}
        try:
            werte = [datetime.now(timezone.utc).isoformat()]
            for name in spalten:
                roh = felder.get(name)
                if name in text_spalten:
                    werte.append(str(roh)[:40] if roh is not None else None)
                elif name in ganzzahl:
                    werte.append(_zahl(roh, int))
                else:
                    werte.append(_zahl(roh, float))
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "INSERT INTO markt_historie (ts_utc," +
                        ",".join(spalten) + ") VALUES (" +
                        ",".join("?" * (len(spalten) + 1)) + ")", werte)
            self.geschrieben += 1
            return True
        except Exception:
            self.ausgefallen += 1
            return False

    def schatten_sizing(self, symbol="", echt_usd=None, schatten_usd=None,
                        schatten_pct=None, gruende="", confidence=None,
                        win_rate=None, drawdown_pct=None, verlustserie=None,
                        regime="", fear_greed=None):
        """[SCHATTENMODUS SIZING 11.08.2026] Haelt fest, was adaptive_sizing
        getan HAETTE - ohne dass es etwas tut.

        risk/adaptive_sizing.py ist vollstaendig verdrahtet, aber ueber
        use_dynamic_sizing=False abgeschaltet (config/settings.py:186). Es
        koennte Ordergroessen ausschliesslich VERKLEINERN, nie vergroessern.
        Ob das genuetzt haette, ist ohne Messung nicht zu beantworten -
        und Einschalten ohne Messung waere genau der Fehler, den das
        Projekt sich verboten hat.

        Diese Zeile aendert KEINEN Cent. Sie notiert nur den Unterschied
        zwischen echter und hypothetischer Ordergroesse. Ueber Symbol und
        Zeitpunkt laesst sich spaeter im Journal nachsehen, wie der Trade
        tatsaechlich ausging - erst dieser Vergleich beantwortet die Frage.

        Wirft nie nach aussen.
        """
        try:
            echt = _zahl(echt_usd, float)
            schatten = _zahl(schatten_usd, float)
            diff = None
            if echt is not None and schatten is not None:
                diff = round(schatten - echt, 4)
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "INSERT INTO schatten_sizing (ts_utc,symbol,echt_usd,"
                        "schatten_usd,differenz_usd,schatten_pct,gruende,"
                        "confidence,win_rate,drawdown_pct,verlustserie,regime,"
                        "fear_greed) VALUES (" + ",".join("?" * 13) + ")",
                        (datetime.now(timezone.utc).isoformat(),
                         str(symbol or "")[:40], echt, schatten, diff,
                         _zahl(schatten_pct, float), str(gruende or "")[:300],
                         _zahl(confidence, float), _zahl(win_rate, float),
                         _zahl(drawdown_pct, float),
                         _zahl(verlustserie, int), str(regime or "")[:40],
                         _zahl(fear_greed, int)))
            self.geschrieben += 1
            return True
        except Exception:
            self.ausgefallen += 1
            return False

    def jobs_aufraeumen(self, pid_lebt=None):
        """Setzt verwaiste 'LAEUFT'-Zeilen auf ABGEBROCHEN. Gibt die Anzahl zurueck.

        [LUECKE 11.08.2026] Wird ein Job von aussen abgeschossen oder faellt
        der Rechner aus, bleibt seine Zeile fuer immer auf 'LAEUFT' stehen.
        Die Tabelle behauptet dann, alles laufe - genau die Schoenfaerberei,
        gegen die sie gebaut wurde. Belegt am 11.08.: forschung_capture
        PID 6560 stand auf LAEUFT, obwohl der Prozess laengst weg war.

        pid_lebt: Funktion(pid) -> bool. Fehlt sie, wird tasklist gefragt.
        """
        try:
            if pid_lebt is None:
                from core.hintergrund import _laeuft_noch as pid_lebt
        except Exception:
            return 0
        try:
            with self._verbinde() as con:
                offen = con.execute(
                    "SELECT id, pid FROM jobs WHERE status='LAEUFT'").fetchall()
            tot = [zid for zid, pid in offen if not pid or not pid_lebt(pid)]
            for zid in tot:
                self.job_ende(zid, exit_code=None, status="ABGEBROCHEN",
                              fehlerauszug="Verwaiste Zeile: Prozess existiert "
                                           "nicht mehr, nachtraeglich geschlossen")
            return len(tot)
        except Exception:
            return 0

    def job_gesundheit(self, job_name=None):
        """Ampel je Job: letzter Lauf, letzter Erfolg, Fehlerzahl."""
        try:
            with self._verbinde() as con:
                wo = "WHERE job_name=?" if job_name else ""
                arg = (job_name,) if job_name else ()
                zeilen = con.execute(
                    "SELECT job_name, MAX(start_utc), "
                    "  MAX(CASE WHEN status='OK' THEN start_utc END), "
                    "  SUM(CASE WHEN status='FEHLER' THEN 1 ELSE 0 END), "
                    "  COUNT(*) "
                    f"FROM jobs {wo} GROUP BY job_name", arg).fetchall()
            return [{"job": z[0], "letzter_lauf": z[1], "letzter_erfolg": z[2],
                     "fehler": z[3], "laeufe": z[4]} for z in zeilen]
        except Exception:
            return []

    def lern_ereignis(self, strategie="", pnl_usd=0.0, quelle="",
                      symbol="", position_id=""):
        """[SAUBERER V6-ZAEHLER 11.08.2026] Haelt EIN Lern-Ereignis fest.

        Eine Zeile je Verkauf, aus dem gelernt wurde - Gewinn UND Verlust.
        Das ist die Rohspur unter data_store/brain_performance_v6.json: die
        JSON-Datei traegt nur Summen, hier steht jeder Einzelfall mit
        Zeitpunkt und Herkunft.

        WARUM GETRENNT VON brain_performance.json
        -----------------------------------------
        Die alte Datei ist mit V4-Altdaten vorbefuellt (source: v4_bootstrap,
        siehe ENTWICKLERHANDBUCH.md:1419, Beschluss vom 27.07.2026). Ihre
        Trefferquoten von 75-91 % stammen groesstenteils NICHT aus V6.
        Wer neue, ehrliche V6-Ergebnisse dort hineinschreibt, erzeugt eine
        Mischzahl, die weder V4 noch V6 ist. Deshalb zaehlt V6 ab jetzt
        daneben mit - die alte Datei bleibt als Beweisstueck unberuehrt.

        Wirft nie nach aussen. Ein Protokollfehler darf einen bereits
        ausgefuehrten Verkauf nie gefaehrden.
        """
        try:
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "INSERT INTO lern_ereignisse (ts_utc,strategie,pnl_usd,"
                        "gewonnen,quelle,symbol,position_id) VALUES (?,?,?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(),
                         str(strategie or "")[:80],
                         float(pnl_usd or 0.0),
                         1 if float(pnl_usd or 0.0) > 0 else 0,
                         str(quelle or "")[:40],
                         str(symbol or "")[:40],
                         str(position_id or "")[:60]))
            self.geschrieben += 1
            return True
        except Exception as fehler:
            try:
                with open(AUSFALL_DATEI, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "typ": "LERN_EREIGNIS", "strategie": str(strategie),
                        "pnl_usd": str(pnl_usd), "quelle": str(quelle),
                        "db_fehler": f"{type(fehler).__name__}: {fehler}",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            self.ausgefallen += 1
            return False

    def schatten_exit(self, position_id="", symbol="", regel="", grund="",
                      preis=0.0, pnl_pct=0.0, hoechst_pnl_pct=0.0,
                      entry_price=0.0, entry_score=None):
        """[SCHATTENMODUS 10.08.2026] Haelt fest, was eine Regel getan HAETTE.

        Die Regel verkauft dabei NICHT - die Position laeuft weiter. Ueber
        position_id laesst sich spaeter im Journal nachsehen, wie sie
        tatsaechlich ausging. Erst dieser Vergleich beantwortet, ob der
        fruehe Ausstieg besser gewesen waere als das Aussitzen.

        Wirft nie nach aussen.
        """
        try:
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        "INSERT INTO schatten_exits (ts_utc,position_id,symbol,"
                        "regel,grund,preis,pnl_pct,hoechst_pnl_pct,entry_price,"
                        "entry_score) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(),
                         str(position_id or ""), str(symbol or ""),
                         str(regel or ""), str(grund or "")[:300],
                         _zahl(preis, float), _zahl(pnl_pct, float),
                         _zahl(hoechst_pnl_pct, float),
                         _zahl(entry_price, float), _zahl(entry_score, int)))
            return True
        except Exception:
            return False

    def feature_snapshot(self, symbol, df=None, zeile=None, timeframe="",
                         kerze_offen=None):
        """[SCHRITT 3, 13.08.2026] Haelt fest, MIT WELCHEN ZAHLEN entschieden wurde.

        Ohne diesen Schnappschuss ist eine Entscheidung im Nachhinein
        plausibel, aber nicht beweisbar reproduzierbar - und ein
        Neutraining der KI unmoeglich. Kursdaten kann man nachladen, den
        Rechenstand des Bots von damals nicht.

        symbol : z.B. "BTC/USDC"
        df     : DataFrame aus calc_all_indicators bzw. snap._df; es wird
                 die LETZTE Zeile verwendet
        zeile  : alternativ direkt ein Dict {Spaltenname: Wert}
        kerze_offen : True, wenn die Kerze noch laeuft (dann ist der Wert
                 vorlaeufig - MASTERPROMPT.md Abschnitt C verbietet, eine
                 offene Kerze als finale Grundlage zu behandeln)

        Rueckgabe: feature_snapshot_id oder "" bei Fehlschlag.
        Wirft nie nach aussen.
        """
        try:
            werte = dict(zeile) if zeile else {}
            kerze_zeit = ""
            if not werte and df is not None:
                letzte = df.iloc[-1]
                werte = {k: letzte[k] for k in df.columns}
                try:
                    kerze_zeit = str(df.index[-1])
                except Exception:
                    kerze_zeit = ""

            if not werte:
                return ""

            fid = uuid.uuid4().hex
            spalten = {
                "feature_snapshot_id": fid,
                "ts_utc": datetime.now(timezone.utc).isoformat(),
                "symbol": str(symbol or ""),
                "timeframe": str(timeframe or ""),
                "kerze_zeit": kerze_zeit,
                "kerze_offen": None if kerze_offen is None else int(bool(kerze_offen)),
                "schema_version": FEATURE_SCHEMA_VERSION,
            }

            rest = {}
            for name, wert in werte.items():
                ziel = FEATURE_MAPPING.get(name)
                if ziel is None:
                    # Bollinger heissen bei pandas_ta BBL_20_2.0 usw.
                    for praefix, bb_ziel in FEATURE_BB_PRAEFIX.items():
                        if str(name).upper().startswith(praefix):
                            ziel = bb_ziel
                            break
                if ziel:
                    spalten[ziel] = _zahl(wert, float)
                else:
                    # Nichts wegwerfen: was heute unbekannt ist, kann
                    # morgen wichtig sein. Kostet ein paar Bytes.
                    try:
                        rest[str(name)] = (None if wert is None
                                           else float(wert))
                    except (TypeError, ValueError):
                        rest[str(name)] = str(wert)[:80]

            if rest:
                spalten["rest_json"] = json.dumps(rest, ensure_ascii=False,
                                                  default=str)[:4000]

            namen = ",".join(spalten.keys())
            platz = ",".join("?" * len(spalten))
            with self._lock:
                with self._verbinde() as con:
                    con.execute(
                        f"INSERT OR REPLACE INTO feature_snapshots ({namen}) "
                        f"VALUES ({platz})", tuple(spalten.values()))
            return fid
        except Exception:
            return ""

    def _baue_datensatz(self, intent, portfolio, cycle_phase,
                        offene_positionen, config_version, kontext=None):
        eid = uuid.uuid4().hex
        jetzt = datetime.now(timezone.utc).isoformat()
        portfolio = portfolio or {}

        genehmigt = bool(getattr(intent, "risk_approved", False))
        grundtext = getattr(intent, "risk_reason", "") or ""
        # Die RiskEngine verbindet mehrere Gruende mit " | " - hier wieder trennen,
        # damit KEIN Grund von einem anderen verdeckt wird.
        gruende = [g.strip() for g in grundtext.split("|") if g.strip()]
        if genehmigt:
            gruende = []

        art = None
        if not genehmigt:
            if any(s in grundtext for s in _STOERUNGSMUSTER):
                art = "STOERUNG"          # hier lohnt ein Blick
            elif any(s in grundtext for s in _MARKTFILTER):
                art = "Marktfilter"       # gewollt: Abwaertstrend-Schutz
            elif "Smart-Entry" in grundtext:
                art = "Zurueckgestellt"   # wartet auf Rueckgang, nicht verloren
            else:
                art = "Kapazitaet"        # bin voll / hab ich schon

        seite = getattr(intent, "side", "")
        seite = getattr(seite, "value", str(seite))

        entry = _zahl(getattr(intent, "entry_price", None), float)
        stop = _zahl(getattr(intent, "stop_loss", None), float)
        menge = _zahl(getattr(intent, "quantity", None), float)

        felder = {
            "evaluation_id": eid,
            "ts_utc": jetzt,
            "symbol": str(getattr(intent, "symbol", "")),
            "side": seite,
            "decision": "APPROVED" if genehmigt else "REJECTED",
            "reject_art": art,
            "primary_reason": gruende[0] if gruende else None,
            "grund_anzahl": len(gruende),
            "score": _zahl(getattr(intent, "score", None), int),
            "confidence": _zahl(getattr(intent, "confidence", None), float),
            "entry_price": entry,
            "amount_usd": _zahl(getattr(intent, "amount_usd", None), float),
            "stop_loss": stop,
            "strategy_id": str(getattr(intent, "strategy_id", "") or ""),
            "entry_reason": str(getattr(intent, "entry_reason", "") or "")[:400],
            "total_equity": _zahl(portfolio.get("total_equity"), float),
            "cycle_phase": str(cycle_phase or ""),
            "offene_positionen": _zahl(offene_positionen, int),
            "config_version": str(config_version or ""),

            # --- Gruppe A: lag im intent, wurde nie geschrieben ---
            "decision_id": str(getattr(intent, "id", "") or ""),
            "take_profit": _zahl(getattr(intent, "take_profit", None), float),
            "trailing_stop_pct": _zahl(getattr(intent, "trailing_stop_pct", None), float),
            "max_slippage_pct": _zahl(getattr(intent, "max_slippage_pct", None), float),
            "quantity_geplant": menge,
            "agent_id": str(getattr(intent, "agent_id", "") or ""),
            "model_version": str(getattr(intent, "model_version", "") or ""),
        }

        # --- Gruppe B + C: vom Aufrufer durchgereicht ---
        # kontext kommt aus app._telemetrie_schreiben(). Unbekannte
        # Schluessel werden verworfen statt den INSERT zu sprengen: eine
        # Telemetrie darf den Bot nie anhalten.
        erlaubt = {name for name, _typ in ZUSATZSPALTEN}
        for schluessel, wert in (kontext or {}).items():
            if schluessel in erlaubt:
                felder[schluessel] = wert

        # --- Gruppe C: Risiko-Kennzahlen, hier zentral gerechnet ---
        # Zentral, damit dieselbe Formel gilt, egal welcher der sieben
        # Aufrufer von _telemetrie_schreiben() gerade dran ist.
        if entry and stop and entry > 0 and stop > 0 and entry > stop:
            felder["risiko_pct"] = round((entry - stop) / entry * 100, 4)
            # [FIX 13.08.2026, beim Pruefen nach dem Neustart gefunden]
            # Hier stand nur "if menge:" - und intent.quantity ist beim
            # KAUFSIGNAL immer 0.0. Die Stueckzahl steht erst fest, wenn
            # die Order laeuft; geplant wird in Dollar (amount_usd).
            # Folge: risiko_r_usd blieb bei 126 von 126 Entscheidungen
            # leer - und ohne diesen Wert gibt es kein R-Vielfaches, weil
            # der Verkauf ihn als Nenner braucht. Das Feature waere zwei
            # Wochen lang still ins Leere gelaufen.
            #
            # Ersatzweg: Stueckzahl = geplanter Betrag / Einstiegskurs.
            betrag = _zahl(getattr(intent, "amount_usd", None), float)
            if not menge and betrag and entry:
                menge = betrag / entry
            if menge:
                felder["risiko_r_usd"] = round((entry - stop) * menge, 6)

        regeln = [(eid, regelname(g), "BLOCK", g[:300], jetzt) for g in gruende]
        return {"id": eid, "felder": felder, "regeln": regeln}

    def _notfall(self, datensatz, fehler):
        """DB kaputt -> Datensatz trotzdem retten. Nie den Bot anhalten."""
        self.ausgefallen += 1
        try:
            with open(AUSFALL_DATEI, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "evaluation_id": datensatz["id"],
                    # [SCHRITT 3, 13.08.2026] war "zeile" als Liste von
                    # Werten ohne Spaltennamen - beim Zurueckspielen aus
                    # der Notfalldatei haette man raten muessen, welcher
                    # Wert wohin gehoert. Jetzt mit Namen.
                    "felder": {k: (None if v is None else str(v))
                               for k, v in datensatz["felder"].items()},
                    "regeln": [list(map(str, r)) for r in datensatz["regeln"]],
                    "db_fehler": f"{type(fehler).__name__}: {fehler}",
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def status(self):
        return {"aktiv": self.aktiv, "datei": self.db_datei,
                "geschrieben": self.geschrieben, "ausgefallen": self.ausgefallen}


def _zahl(wert, typ):
    try:
        if wert is None:
            return None
        return typ(wert)
    except Exception:
        return None
