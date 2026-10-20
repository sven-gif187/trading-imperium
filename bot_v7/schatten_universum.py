"""
schatten_universum.py — misst das Einstiegssignal auf 18 Münzen, ohne zu handeln
================================================================================

WARUM ES DIESES PROGRAMM GIBT

Der Bot handelt drei Münzen und macht dabei rund 2,9 Verkäufe am Tag. Das
Zwei-Wochen-Messfenster liefert damit etwa 40 Trades. Aufgeteilt nach Münze,
Marktphase und Ausstiegsart bleiben drei Fälle je Gruppe — damit lässt sich
nichts beweisen (die Streuung ist größer als jeder Effekt, den man sucht).

Dieses Programm löst das, ohne den Handel anzufassen: Es rechnet stündlich für
ACHTZEHN Münzen dieselbe Punktzahl aus wie der Bot und schreibt sie mit. Nach
zwei Wochen liegen mehrere tausend Beobachtungen vor statt 40.

[20.08.2026] Es waren zwölf; am 17.08. kamen sechs Nachzügler dazu (SUI, OP,
APT, ARB, INJ, RENDER). Diese Zeilen sagten trotzdem weiter "zwölf" — Sven
fiel es auf. Die verbindliche Zahl ist immer len(MUENZEN), nie ein Text.

WAS ES BEANTWORTET
    "Hat das Einstiegssignal auf Münze X nach echten Kosten einen Vorteil?"

WAS ES NICHT BEANTWORTET
    "Hätte das Portfolio mit Münze X mehr verdient?"

Der Unterschied ist wesentlich. Im Schatten gibt es keine Kapitalkonkurrenz:
In Wirklichkeit sind höchstens drei Positionen gleichzeitig offen, und wenn
das Geld in BTC steckt, kann ein DOGE-Signal nicht genommen werden. Der
Schatten nimmt jede Gelegenheit. Er überschätzt damit systematisch, wie oft
man zugegriffen hätte — aber er misst korrekt, OB das Signal auf dieser Münze
etwas taugt. Genau das ist die Frage, die über eine Universums-Erweiterung
entscheidet.

Die Portfolio-Sicht (mit Kapitalkonkurrenz, Nachkauf und Wiedereinstiegs-
Sperre) kommt in einem zweiten Schritt — sie rechnet auf DIESEN Daten und
wird gegen die echten Bot-Entscheidungen geeicht (siehe unten).

WARUM EIN EIGENES PROGRAMM UND NICHT IM BOT

Während des Messfensters darf am Bot nichts geändert werden. Neuer Code in
app.py könnte ihn im Fehlerfall stören. Dieses Programm läuft getrennt,
schreibt in eine EIGENE Datenbank und liest Marktdaten nur. Es kann den Bot
nicht beeinflussen — genau wie der Forschungs-Sammler.

WIE DIE SPÄTERE EICHUNG FUNKTIONIERT

Das Programm erfasst auch BTC, ETH und SOL — also genau die drei, die der Bot
wirklich handelt. Damit lässt sich später prüfen: Erzeugt der Schatten für
diese drei dieselben Signale wie der echte Bot? Wenn ja, darf man seinen
Zahlen für die übrigen fünfzehn trauen. Wenn nein, ist das Messgerät kaputt und
man merkt es, bevor man eine Entscheidung darauf baut.

AUFRUF
    python schatten_universum.py            einmal laufen
    python schatten_universum.py --dauer    alle 60 Minuten, bis Strg+C
    python schatten_universum.py --status   was bisher gesammelt wurde
"""
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

# [15.09.2026] Fuer die Fibonacci-Ziele der Kaufwelle.
#
# MUSS NACH sys.path.insert stehen: Wird das Programm aus einem
# anderen Verzeichnis gestartet (Aufgabenplanung, Verknuepfung), kennt
# Python den Projektordner vorher nicht und der Import scheitert -
# dann waeren die Ziel-Spalten still leer geblieben.
try:
    from features.fraktal_ziele import ziele_berechnen
except Exception as _zi:                               # pragma: no cover
    _ZIELE_FEHLER = str(_zi)[:80]

    def ziele_berechnen(_welle):
        return []
else:
    _ZIELE_FEHLER = ""

DB = os.path.join(HIER, "data_store", "schatten_universum.db")
LOG = os.path.join(HIER, "data_store", "schatten_universum.log")

# Die Münzen, die der Forschungs-Sammler ohnehin schon erfasst.
# [20.08.2026] Hier stand "Die zwölf Münzen" - seit dem 17.08. sind
# es achtzehn. Ein Kommentar, der eine Anzahl nennt, veraltet mit der
# ersten Ergänzung. Wer die Zahl braucht: len(MUENZEN).
# Damit lässt sich der live gemessene Spread aus seinen Ticker-Dateien
# direkt danebenlegen, statt mit Annahmen zu rechnen.
MUENZEN = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "DOGE/USDC", "ADA/USDC",
           "XRP/USDC", "LINK/USDC", "AVAX/USDC", "UNI/USDC", "NEAR/USDC",
           "ATOM/USDC", "DOT/USDC",
           # [17.08.2026] Sechs Nachzuegler aus dem V4-Vorgaenger, die hier
           # nie gemessen wurden - Sven fiel auf, dass V4 Muenzen handelte,
           # die V6 gar nicht kennt, darunter KI-Werte. Erste Stichprobe der
           # Spanne bei Bybit: SUI 1,48 bp und OP 2,37 bp sind BILLIGER als
           # ADA, AVAX und alles darunter. Die Empfehlung "DOGE ist der beste
           # Erweiterungskandidat" (Handbuch 4.20) galt also fuer ein
           # unvollstaendiges Feld.
           # Sie werden hier NUR beobachtet, nicht gehandelt.
           "SUI/USDC", "OP/USDC", "APT/USDC", "ARB/USDC",
           "INJ/USDC", "RENDER/USDC"]

# Die drei, die der Bot wirklich handelt — für die spätere Eichung.
ECHTE = {"BTC/USDC", "ETH/USDC", "SOL/USDC"}

# Gemessene Median-Spreads (Basispunkte) als Rückfall, falls für eine Münze
# gerade kein Live-Wert vorliegt. Quelle: 12_SPREAD-MESSUNG.md.
SPREAD_RUECKFALL = {
    "ETH": 0.054, "BTC": 0.118, "SOL": 1.366, "DOGE": 1.441, "ADA": 5.954,
    "XRP": 6.591, "LINK": 12.105, "AVAX": 12.372, "UNI": 16.519,
    "NEAR": 18.276, "ATOM": 56.887, "DOT": 65.232,
    # [17.08.2026] Die sechs Neuen. ACHTUNG: Das ist EINE Stichprobe vom
    # 17.08. bei Bybit, kein Median ueber Tage wie die Werte oben. Sie
    # taugen als Rueckfall, aber NICHT fuer einen Vergleich - dafuer muss
    # das Schatten-Universum sie erst ueber mehrere Tage messen.
    "SUI": 1.48, "OP": 2.37, "APT": 3.84, "ARB": 4.01,
    "INJ": 4.88, "RENDER": 7.93,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS signale (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc          TEXT NOT NULL,
    muenze          TEXT NOT NULL,
    im_echtbetrieb  INTEGER NOT NULL,   -- 1 = Bot handelt diese Münze auch
    score           REAL,
    confidence      REAL,
    preis           REAL,
    betrag_usd      REAL,
    strategie       TEXT,
    begruendung     TEXT,
    stop_loss       REAL,
    -- Marktzustand zum Signalzeitpunkt
    rsi             REAL,
    adx             REAL,
    macd_hist       REAL,
    atr             REAL,
    regime          TEXT,
    zyklus          TEXT,
    fear_greed      INTEGER,
    -- Kosten zum Signalzeitpunkt
    spread_bp       REAL,
    spread_quelle   TEXT,               -- 'live' oder 'rueckfall'
    kosten_runde    REAL,               -- Anteil, z.B. 0.0051
    lauf_id         TEXT,
    -- =================================================================
    -- [15.09.2026] Das Fraktal-Tor, auf allen 18 Münzen mitgemessen.
    --
    -- Seit dem 15.09. kauft der Bot nur noch in Fibonacci-Konfluenz-
    -- zonen (features/fraktal_tor.py). Auf drei Münzen mit ein paar
    -- Trades im Monat lässt sich nicht feststellen, ob das trägt -
    -- genau das Problem, gegen das dieses Programm gebaut wurde.
    --
    -- WICHTIG FÜR DIE AUSWERTUNG: Das Tor wird hier NEBEN dem Signal
    -- ausgewertet, nicht davor. Hinge es im Signalweg, kämen die
    -- abgelehnten Fälle gar nicht erst in die Datenbank - und
    -- ausgerechnet die braucht man, um zu vergleichen.
    --
    --     tor_erlaubt = 1  ->  der Bot hätte gekauft
    --     tor_erlaubt = 0  ->  der Score reichte, das Tor sagte nein
    --
    -- Die Frage, die sich damit beantworten lässt: Liefen die
    -- erlaubten Fälle besser als die abgelehnten? Ohne beide Gruppen
    -- ist sie nicht zu stellen.
    -- =================================================================
    tor_erlaubt     INTEGER,            -- 1 = Kauf erlaubt, 0 = abgelehnt
    tor_grund       TEXT,
    zone_unten      REAL,
    zone_oben       REAL,
    zone_score      INTEGER,
    zone_quellen    INTEGER,            -- unabhängige Beobachtungen
    zone_zeitrahmen TEXT,               -- z.B. "1d+4h"
    zone_golden     INTEGER,            -- 1 = Golden Pocket getroffen
    abstand_pct     REAL,               -- wie weit neben der Zone
    -- Die Kaufwelle und ihre Fibonacci-Ziele. Damit lässt sich später
    -- messen, ob ein Ziel erreicht wurde, bevor der Stop-Loss griff.
    welle_hoch      REAL,
    welle_tief      REAL,
    ziel_1000       REAL,
    ziel_1272       REAL,
    ziel_1618       REAL
);
CREATE INDEX IF NOT EXISTS ix_sig_ts     ON signale(ts_utc);
CREATE INDEX IF NOT EXISTS ix_sig_muenze ON signale(muenze);

CREATE TABLE IF NOT EXISTS laeufe (
    lauf_id         TEXT PRIMARY KEY,
    ts_utc          TEXT NOT NULL,
    muenzen_geprueft INTEGER,
    signale_erzeugt  INTEGER,
    dauer_sek       REAL,
    fehler          TEXT
);

-- =====================================================================
-- [15.09.2026] Das Tor auf JEDER Münze, in JEDEM Lauf.
--
-- WARUM EINE ZWEITE TABELLE
-- `signale` enthält nur, was die Kaufschwelle erreicht hat - im
-- Live-Betrieb Score 7 von 10. Das ist selten: Bei 18 Münzen stündlich
-- sind das wenige Zeilen am Tag, und davon lässt das Tor noch einen
-- Teil durch. Für eine Messung ist das zu dünn, und genau die
-- Fallzahl war der Grund, dieses Programm überhaupt zu bauen.
--
-- Diese Tabelle schreibt bei JEDEM Lauf für JEDE Münze eine Zeile -
-- 18 x 24 = 432 am Tag, unabhängig vom Score. Damit lässt sich
-- beantworten:
--
--   * Wie oft ist das Tor überhaupt offen, je Münze?
--   * Fallen Tor und Score zusammen, oder sind es zwei Welten?
--   * Wie liefen die Fälle, in denen das Tor offen war, der Score
--     aber fehlte? (Die sieht man in `signale` nie.)
--
-- `signale` bleibt unverändert - es beantwortet weiter seine eigene
-- Frage. Zwei Tabellen, zwei Fragen, keine vermischt.
-- =====================================================================
CREATE TABLE IF NOT EXISTS tor_beobachtungen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc          TEXT NOT NULL,
    lauf_id         TEXT,
    muenze          TEXT NOT NULL,
    im_echtbetrieb  INTEGER NOT NULL,
    preis           REAL,
    tor_erlaubt     INTEGER,            -- 1 = Preis in einer Kaufzone
    tor_grund       TEXT,
    zone_unten      REAL,
    zone_oben       REAL,
    zone_score      INTEGER,
    zone_quellen    INTEGER,
    zone_zeitrahmen TEXT,
    zone_golden     INTEGER,
    abstand_pct     REAL,
    welle_hoch      REAL,
    welle_tief      REAL,
    ziel_1000       REAL,
    ziel_1272       REAL,
    ziel_1618       REAL,
    -- Hätte der Score allein gekauft? So lässt sich trennen, was das
    -- Tor beiträgt und was schon der Score leistet.
    score           REAL,
    score_reichte   INTEGER             -- 1 = analyze() gab ein Signal
);
CREATE INDEX IF NOT EXISTS ix_tor_ts     ON tor_beobachtungen(ts_utc);
CREATE INDEX IF NOT EXISTS ix_tor_muenze ON tor_beobachtungen(muenze);
"""


def notiz(text):
    """Schreibt ins Log - und NUR wenn moeglich zusaetzlich auf den Bildschirm.

    [FEHLER 14.08.2026] Hier stand print() ungeschuetzt vor dem Schreiben.
    Unter pythonw.exe (fensterlos, so laufen alle Hintergrund-Jobs) ist
    sys.stdout aber None - print() wirft dann AttributeError und beendet das
    ganze Programm. Der Prozess stand in der Prozessliste, tat aber nichts.
    Das Log blieb leer, und von aussen sah es aus, als liefe er.

    Merke: In einem Programm, das auch fensterlos laufen soll, darf KEIN
    ungeschuetztes print() stehen. Erst schreiben, dann anzeigen.
    """
    zeile = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {text}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except Exception:
        pass
    try:
        print(zeile)
    except Exception:
        pass          # pythonw: kein stdout - kein Grund abzubrechen


# [15.09.2026] Die Spalten des Fraktal-Tors. Stehen zusaetzlich hier,
# weil CREATE TABLE IF NOT EXISTS eine SCHON VORHANDENE Tabelle nicht
# anfasst - wer eine aeltere Datenbank hat, bekaeme sonst beim ersten
# INSERT einen "no such column"-Fehler und der ganze Lauf faellt aus.
NACHRUESTEN = [
    ("tor_erlaubt", "INTEGER"), ("tor_grund", "TEXT"),
    ("zone_unten", "REAL"), ("zone_oben", "REAL"),
    ("zone_score", "INTEGER"), ("zone_quellen", "INTEGER"),
    ("zone_zeitrahmen", "TEXT"), ("zone_golden", "INTEGER"),
    ("abstand_pct", "REAL"),
    ("welle_hoch", "REAL"), ("welle_tief", "REAL"),
    ("ziel_1000", "REAL"), ("ziel_1272", "REAL"), ("ziel_1618", "REAL"),
]


def db_oeffnen():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(SCHEMA)

    # Fehlende Spalten nachtragen. Kein try/except um alles herum -
    # nur der eine erwartete Fall (Spalte gibt es schon) wird
    # geschluckt, alles andere soll laut sein.
    vorhanden = {r[1] for r in con.execute("PRAGMA table_info(signale)")}
    neu = 0
    for name, typ in NACHRUESTEN:
        if name in vorhanden:
            continue
        con.execute(f"ALTER TABLE signale ADD COLUMN {name} {typ}")
        neu += 1
    if neu:
        con.commit()
        notiz(f"Datenbank erweitert: {neu} Spalte(n) fuer das Fraktal-Tor "
              f"nachgetragen")
    return con


def live_spread(basis):
    """Letzter gemessener Spread aus den Ticker-Dateien des Forschungs-Sammlers.

    Der Sammler schreibt alle 60-90 Sekunden bid/ask/spread_bp je Münze. Diese
    Zahl ist der Momentwert des Marktes - viel besser als eine Annahme. Fehlt
    sie, wird der gemessene Median vom 31.07. genommen und als solcher
    gekennzeichnet, damit später niemand die beiden verwechselt.
    """
    ordner = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for tag in (heute,):
        for quote in ("USDC", "USDT"):
            pfad = os.path.join(ordner, tag, f"ticker_{basis}{quote}.csv")
            if not os.path.exists(pfad):
                continue
            try:
                with open(pfad, "r", encoding="utf-8", errors="replace") as f:
                    zeilen = f.readlines()
                if len(zeilen) < 2:
                    continue
                kopf = zeilen[0].strip().split(",")
                if "spread_bp" not in kopf:
                    continue
                i = kopf.index("spread_bp")
                letzte = zeilen[-1].strip().split(",")
                wert = float(letzte[i])
                # Unsinnige Werte verwerfen statt sie mitzuschleppen
                if 0 < wert < 1000:
                    return wert, "live"
            except Exception:
                continue
    return SPREAD_RUECKFALL.get(basis), "rueckfall"


def kosten_je_runde(spread_bp):
    """Gesamtreibung einer Kauf-Verkauf-Runde als Anteil.

    Zwei Taker-Gebühren (Bybit EU, 0,25 % je Seite) plus zweimal den halben
    Spread - eine Market-Order zahlt gegenüber der Mitte immer die Hälfte des
    Abstands zwischen Kauf- und Verkaufsangebot.
    """
    if spread_bp is None:
        return None
    return 2 * 0.0025 + 2 * (spread_bp / 2.0 / 10000.0)


def _regime_von(schnappschuss, zusatz):
    """Marktzustand dieser Muenze - TRENDING / RANGING / UNKNOWN.

    [FUND 19.08.2026] Die Spalte `regime` war in ALLEN 697 Zeilen leer.
    Ursache war eine Auslassung: `zusatz` wird mit
    {"fear_greed": 50, "regime": None, "zyklus": None} angelegt, danach
    holt der Code fear_greed und zyklus aus dem Bot-Zustand - regime
    nicht. Es blieb also fuer immer None, und niemand hat es bemerkt,
    weil die Zeile ansonsten vollstaendig aussah.

    Der Wert war die ganze Zeit da: DataAgent legt ihn beim Holen der
    Kerzen in den Schnappschuss (market_data.py, aus dem ADX).

    Und er ist PRO MUENZE richtig, nicht global - ein Wert aus `zusatz`
    waere fuer alle achtzehn Muenzen derselbe gewesen, obwohl BTC im Trend
    laufen kann, waehrend SOL seitwaerts geht.
    """
    r = getattr(schnappschuss, "regime", None)
    if r is not None:
        r = getattr(r, "value", r)        # Enum oder schon Text
        if r:
            return str(r)
    return zusatz.get("regime")


def tor_urteil(tor, muenze, preis):
    """Fragt das Fraktal-Tor und packt die Antwort in ein flaches dict.

    Eine Funktion fuer beide Tabellen: `signale` und
    `tor_beobachtungen` schreiben dieselben Felder. Zwei getrennte
    Rechnungen waeren zwei Gelegenheiten, verschiedene Zahlen zu
    bekommen.

    Gibt ein leeres dict zurueck, wenn kein Tor da ist oder es
    scheitert - dann bleiben die Spalten NULL. Wichtig: NULL heisst
    "nicht beurteilt", 0 heisst "abgelehnt". Wer das verwechselt,
    zaehlt Ausfaelle als Ablehnungen.
    """
    if tor is None or not preis or preis <= 0:
        return {}
    u = tor.pruefe(muenze, preis)
    z = u.get("zone") or {}
    w = u.get("welle") or {}
    nach_r = {round(x["verhaeltnis"], 3): x["preis"]
              for x in (ziele_berechnen(w) if w else [])}
    return {
        "erlaubt": 1 if u.get("erlaubt") else 0,
        "grund": str(u.get("grund", ""))[:300],
        "unten": z.get("unten"), "oben": z.get("oben"),
        "score": z.get("score"), "quellen": z.get("quellen"),
        "zeitrahmen": "+".join(z.get("zeitrahmen") or []),
        "golden": 1 if z.get("golden_pocket") else 0,
        "abstand": u.get("abstand"),
        "w_hoch": w.get("hoch"), "w_tief": w.get("tief"),
        "z1": nach_r.get(1.0), "z2": nach_r.get(1.272),
        "z3": nach_r.get(1.618),
    }


def ein_lauf(con, cfg, data_agent, signal_agent, zusatz, tor=None):
    lauf_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    start = time.time()
    geprueft = erzeugt = beobachtet = 0
    tor_ja = tor_nein = 0
    fehler = []

    for muenze in MUENZEN:
        try:
            schnappschuss = data_agent.fetch_snapshot(
                muenze, cfg.trading.default_timeframe, limit=200)
            if schnappschuss is None:
                fehler.append(f"{muenze}: keine Daten")
                continue
            geprueft += 1

            schnappschuss.cycle_phase = zusatz.get("zyklus") or ""
            absicht = signal_agent.analyze(
                schnappschuss,
                balance_usd=zusatz.get("balance", 500.0),
                fear_greed=zusatz.get("fear_greed", 50))

            # === [15.09.2026] Das Tor VOR dem Score-Filter auswerten ===
            #
            # Muss hier stehen, nicht weiter unten: Unterhalb der
            # Kaufschwelle bricht die Schleife gleich ab, und dann
            # gaebe es fuer diese Muenze gar keine Tor-Beobachtung.
            # Genau die fehlenden Faelle sind aber interessant - "Tor
            # offen, Score zu niedrig" sieht man sonst nie.
            _preis = 0.0
            try:
                _preis = float(getattr(schnappschuss, "close", 0) or 0)
            except Exception:
                _preis = 0.0
            try:
                t = tor_urteil(tor, muenze, _preis)
            except Exception as _te:
                # NULL statt 0 - ein Ausfall ist keine Ablehnung.
                t = {}
                fehler.append(f"{muenze}: Tor {str(_te)[:40]}")

            con.execute(
                "INSERT INTO tor_beobachtungen (ts_utc,lauf_id,muenze,"
                "im_echtbetrieb,preis,tor_erlaubt,tor_grund,zone_unten,"
                "zone_oben,zone_score,zone_quellen,zone_zeitrahmen,"
                "zone_golden,abstand_pct,welle_hoch,welle_tief,"
                "ziel_1000,ziel_1272,ziel_1618,score,score_reichte) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), lauf_id, muenze,
                 1 if muenze in ECHTE else 0, _preis,
                 t.get("erlaubt"), t.get("grund"),
                 t.get("unten"), t.get("oben"), t.get("score"),
                 t.get("quellen"), t.get("zeitrahmen"), t.get("golden"),
                 t.get("abstand"), t.get("w_hoch"), t.get("w_tief"),
                 t.get("z1"), t.get("z2"), t.get("z3"),
                 getattr(absicht, "score", None) if absicht else None,
                 1 if absicht is not None else 0))
            beobachtet += 1
            if t.get("erlaubt"):
                tor_ja += 1
            elif t.get("erlaubt") == 0:
                tor_nein += 1

            # analyze() liefert nur oberhalb der Kaufschwelle etwas zurück.
            # Genau das ist die interessante Menge: Signale, bei denen der Bot
            # tatsächlich kaufen wollte. Alles darunter handelt er ohnehin nie.
            if absicht is None:
                continue

            basis = muenze.split("/")[0].upper()
            sp, quelle = live_spread(basis)
            ind = getattr(schnappschuss, "indicators", {}) or {}

            # Das Tor-Urteil von oben wird hier WIEDERVERWENDET.
            # Es ein zweites Mal zu berechnen waere eine zweite
            # Gelegenheit, eine andere Zahl zu bekommen - der erste
            # Entwurf tat genau das und rechnete dabei mit einem
            # anderen Preis (entry_price statt Schlusskurs).
            con.execute(
                "INSERT INTO signale (ts_utc,muenze,im_echtbetrieb,score,"
                "confidence,preis,betrag_usd,strategie,begruendung,stop_loss,"
                "rsi,adx,macd_hist,atr,regime,zyklus,fear_greed,spread_bp,"
                "spread_quelle,kosten_runde,lauf_id,"
                "tor_erlaubt,tor_grund,zone_unten,zone_oben,zone_score,"
                "zone_quellen,zone_zeitrahmen,zone_golden,abstand_pct,"
                "welle_hoch,welle_tief,ziel_1000,ziel_1272,ziel_1618) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
                "?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(),
                 muenze, 1 if muenze in ECHTE else 0,
                 getattr(absicht, "score", None),
                 getattr(absicht, "confidence", None),
                 getattr(absicht, "entry_price", None),
                 getattr(absicht, "amount_usd", None),
                 getattr(absicht, "strategy_id", None),
                 str(getattr(absicht, "entry_reason", ""))[:300],
                 getattr(absicht, "stop_loss", None),
                 ind.get("rsi"), ind.get("adx"),
                 ind.get("macd_hist") or ind.get("macd"),
                 ind.get("atr"),
                 _regime_von(schnappschuss, zusatz), zusatz.get("zyklus"),
                 zusatz.get("fear_greed"),
                 sp, quelle, kosten_je_runde(sp), lauf_id,
                 t.get("erlaubt"), t.get("grund"),
                 t.get("unten"), t.get("oben"), t.get("score"),
                 t.get("quellen"), t.get("zeitrahmen"), t.get("golden"),
                 t.get("abstand"),
                 t.get("w_hoch"), t.get("w_tief"),
                 t.get("z1"), t.get("z2"), t.get("z3")))
            erzeugt += 1
            if t.get("erlaubt"):
                tor_ja += 1
            elif t.get("erlaubt") == 0:
                tor_nein += 1

        except Exception as e:
            fehler.append(f"{muenze}: {str(e)[:60]}")
        time.sleep(0.4)          # freundlich zur Börsen-Schnittstelle

    con.execute(
        "INSERT OR REPLACE INTO laeufe (lauf_id,ts_utc,muenzen_geprueft,"
        "signale_erzeugt,dauer_sek,fehler) VALUES (?,?,?,?,?,?)",
        (lauf_id, datetime.now(timezone.utc).isoformat(), geprueft, erzeugt,
         round(time.time() - start, 1), "; ".join(fehler)[:400] or None))
    con.commit()

    _tor_text = ""
    if tor is not None and (tor_ja or tor_nein):
        _tor_text = (f" | Tor: {tor_ja} erlaubt, {tor_nein} abgelehnt"
                     f" ({tor_ja / (tor_ja + tor_nein) * 100:.0f} % durch)")
    notiz(f"Lauf {lauf_id}: {geprueft}/{len(MUENZEN)} Münzen, "
          f"{erzeugt} Signale, {beobachtet} Tor-Beobachtungen, "
          f"{time.time()-start:.0f}s{_tor_text}"
          + (f" | Fehler: {'; '.join(fehler)[:120]}" if fehler else ""))
    return erzeugt


def status():
    if not os.path.exists(DB):
        print("Noch nichts gesammelt.")
        return 0
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM signale").fetchone()[0]
    # [15.09.2026] Hier stand ein `return 0`, wenn `signale` leer war.
    # Das ist der Normalfall: Bei Schwelle 7 von 10 vergehen Stunden
    # ohne ein einziges Signal - und dann wurde auch der Tor-Teil
    # nicht mehr angezeigt, obwohl dort 18 Beobachtungen je Lauf
    # stehen. Der erste Lauf sah deshalb aus, als haette er nichts
    # getan, waehrend er 7 erlaubte und 11 abgelehnte Faelle
    # geschrieben hatte.
    if n:
        r = con.execute("SELECT MIN(ts_utc), MAX(ts_utc) FROM signale").fetchone()
        print(f"Signale gesamt : {n}")
        print(f"Zeitraum       : {r[0][:16]} bis {r[1][:16]} (UTC)")
        print()
    else:
        print("Signale        : noch keine (Score hat die Kaufschwelle")
        print("                 noch nicht erreicht - das ist normal)")
        print()
    # Die Muenzen-Tabelle nur, wenn es ueberhaupt Signale gibt -
    # sonst stuenden hier eine Trennlinie und eine Legende ueber
    # nichts.
    if n:
        print(f"{'Münze':12} {'Signale':>8} {'Ø Score':>8} {'Ø Spread bp':>12} "
              f"{'Kosten/Runde':>13}")
        print("-" * 58)
        for m, k, sc, sp, ko in con.execute(
                "SELECT muenze, COUNT(*), AVG(score), AVG(spread_bp), "
                "AVG(kosten_runde) FROM signale GROUP BY muenze "
                "ORDER BY COUNT(*) DESC"):
            marke = " *" if m in ECHTE else ""
            print(f"{m:12} {k:>8} {sc or 0:>8.1f} {sp or 0:>12.2f} "
                  f"{(ko or 0):>12.3%}{marke}")
        print()
        print("* = Münze, die der Bot wirklich handelt (für die Eichung)")
        q = con.execute("SELECT spread_quelle, COUNT(*) FROM signale "
                        "GROUP BY spread_quelle").fetchall()
        print("Spread-Quelle  :", ", ".join(f"{a}={b}" for a, b in q))

    # === [15.09.2026] Das Fraktal-Tor ===
    #
    # Gelesen aus `tor_beobachtungen`, NICHT aus `signale`: Dort steht
    # nur, was die Kaufschwelle erreicht hat (live Score 7 von 10), und
    # das sind wenige Zeilen am Tag. Die Tor-Tabelle hat eine Zeile je
    # Muenze und Lauf - 18 x 24 = 432 taeglich.
    try:
        n_tor = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                            "WHERE tor_erlaubt IS NOT NULL").fetchone()[0]
    except sqlite3.OperationalError:
        n_tor = 0                    # alte Datenbank ohne die Tabelle
    print()
    if not n_tor:
        print("FRAKTAL-TOR: noch keine Beobachtungen.")
        return 0

    ja = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                     "WHERE tor_erlaubt=1").fetchone()[0]
    gp = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                     "WHERE tor_erlaubt=1 AND zone_golden=1").fetchone()[0]
    ausfall = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                          "WHERE tor_erlaubt IS NULL").fetchone()[0]

    print("FRAKTAL-TOR  (eine Zeile je Muenze und Lauf)")
    print("-" * 58)
    print(f"  beurteilt      : {n_tor}")
    print(f"  Tor offen      : {ja}  ({ja / n_tor * 100:.1f} %)")
    print(f"  Tor zu         : {n_tor - ja}  ({(n_tor - ja) / n_tor * 100:.1f} %)")
    if ja:
        print(f"  davon Golden Pocket: {gp} ({gp / ja * 100:.0f} %)")
    if ausfall:
        # NULL heisst "nicht beurteilt", nicht "abgelehnt". Wer das
        # verwechselt, zaehlt Ausfaelle als Ablehnungen.
        print(f"  NICHT beurteilt: {ausfall}  (Tor-Ausfall, zaehlt nirgends mit)")

    print()
    print(f"  {'Muenze':12} {'geprueft':>9} {'offen':>7} {'Quote':>8} {'GP':>5}")
    for m, k, j, g in con.execute(
            "SELECT muenze, COUNT(*), "
            "SUM(CASE WHEN tor_erlaubt=1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN tor_erlaubt=1 AND zone_golden=1 THEN 1 ELSE 0 END) "
            "FROM tor_beobachtungen WHERE tor_erlaubt IS NOT NULL "
            "GROUP BY muenze ORDER BY 3 DESC, 2 DESC"):
        marke = " *" if m in ECHTE else ""
        print(f"  {m:12} {k:>9} {j or 0:>7} {(j or 0) / k * 100:>7.1f} % "
              f"{g or 0:>4}{marke}")

    # Wie oft fielen Score UND Tor zusammen? Das ist die Zahl, die
    # sagt, ob das Tor ueberhaupt etwas Eigenes beitraegt.
    beides = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                         "WHERE tor_erlaubt=1 AND score_reichte=1").fetchone()[0]
    nur_score = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                            "WHERE tor_erlaubt=0 AND score_reichte=1").fetchone()[0]
    nur_tor = con.execute("SELECT COUNT(*) FROM tor_beobachtungen "
                          "WHERE tor_erlaubt=1 AND score_reichte=0").fetchone()[0]
    print()
    print("  SCORE UND TOR ZUSAMMEN")
    print(f"    beides ja        : {beides}   <- hier haette der Bot gekauft")
    print(f"    Score ja, Tor nein: {nur_score}   <- vom Tor verhindert")
    print(f"    Tor ja, Score nein: {nur_tor}   <- Preis gut, Lage zu schwach")
    print()
    print("  ACHTUNG: Diese Quoten sagen, wie OFT das Tor aufgeht -")
    print("  nicht, ob sich das lohnt. Dafuer muss der Nachlauf gemessen")
    print("  werden: Lief der erlaubte Fall besser als der abgelehnte?")
    print("  Genau dafuer stehen beide Gruppen in der Tabelle.")
    return 0


def main():
    if "--status" in sys.argv:
        return status()

    from config.settings import AppConfig
    from data.market_data import DataAgent
    from agents.signal_agent import SignalAgent

    cfg = AppConfig.load()
    data_agent = DataAgent(cfg)
    signal_agent = SignalAgent(cfg)

    # === [15.09.2026] Das Fraktal-Tor mitmessen ===
    #
    # Es wird NICHT an den signal_agent gehaengt (set_fraktal_tor),
    # sondern eigenstaendig geführt - siehe die lange Begruendung in
    # ein_lauf(). Kurz: Im Signalweg wuerde es die abgelehnten Faelle
    # wegfiltern, und genau die braucht die Auswertung.
    #
    # Es bekommt seinen EIGENEN DataAgent-Verweis, teilt sich aber den
    # Kerzen-Cache nicht mit dem Bot - das ist ein getrennter Prozess.
    # Bei stuendlichem Lauf sind das 18 Muenzen x 3 Zeitrahmen = 54
    # Abrufe; der Cache im Tor faengt Wiederholungen innerhalb eines
    # Laufs ab.
    tor = None
    try:
        from features.fraktal_tor import FraktalTor
        tor = FraktalTor(data_agent, cfg)
        notiz("Fraktal-Tor wird mitgemessen (nicht scharf - es filtert "
              "hier nichts, es urteilt nur)")
    except Exception as e:
        # Laut, nicht still: Ohne Tor fehlt genau die Spalte, wegen der
        # dieses Programm erweitert wurde.
        notiz(f"WARNUNG: Fraktal-Tor nicht ladbar ({str(e)[:80]}) - "
              f"die Tor-Spalten bleiben leer!")

    # Marktumfeld einmal je Lauf lesen - dieselben Werte, die der Bot nutzt.
    zusatz = {"fear_greed": 50, "regime": None, "zyklus": None, "balance": 500.0}
    try:
        from core.state_store import StateStore
        st = StateStore("bot_state")
        zusatz["fear_greed"] = st.get("fear_greed", 50)
        zusatz["zyklus"] = st.get("cycle_phase")
    except Exception:
        pass

    con = db_oeffnen()
    notiz(f"Start | {len(MUENZEN)} Münzen | Zeitrahmen "
          f"{cfg.trading.default_timeframe} | DB {os.path.basename(DB)}")

    if "--dauer" not in sys.argv:
        ein_lauf(con, cfg, data_agent, signal_agent, zusatz, tor)
        con.close()
        return 0

    notiz("Dauerbetrieb: alle 60 Minuten. Beenden mit Strg+C.")
    letzter_bericht = None
    try:
        while True:
            try:
                from core.state_store import StateStore
                st = StateStore("bot_state")
                zusatz["fear_greed"] = st.get("fear_greed", 50)
                zusatz["zyklus"] = st.get("cycle_phase")
            except Exception:
                pass
            ein_lauf(con, cfg, data_agent, signal_agent, zusatz, tor)

            # [14.08.2026] Nachlauf-Messung anhaengen: Kurs 1/4/24/48 h nach
            # jedem Ausstieg und jeder Blockade. Beantwortet als Einziges die
            # 187-Dollar-Frage (war der Stop richtig, oder haette Aussitzen
            # geholfen) und ob die 98.000 Ablehnungen die richtigen waren.
            # Haengt hier mit dran, statt ein eigener Dauerprozess zu sein -
            # der Rechner hat nur 3,9 GB und laeuft am Anschlag.
            try:
                import nachlauf
                ncon = nachlauf.db()
                nachlauf.ereignisse_aufnehmen(ncon)

                # [20.08.2026] Die eigenen Signale gehoeren mit in die
                # Nachlauf-Messung.
                #
                # Sven: "wichtig, dass alle Instrumente sich automatisch in
                # einem Intervall wiederholen, damit wir nichts vergessen."
                #
                # Genau hier ist die richtige Stelle: dieser Lauf erzeugt die
                # Signale UND misst danach ohnehin schon Ausstiege und
                # Blockaden nach. Ein eigener Zeitplan waere eine zweite
                # Stelle, die ausfallen kann - und eine mehr, an die niemand
                # denkt (vgl. positionsverlauf.py, der am 19.08. 28 Minuten
                # stillstand, weil ihn nur eine Hand gestartet hatte).
                #
                # Reines Aufschreiben. Beantwortet Befund 64: haette ein Kauf
                # in Gier-Phasen nach Kosten getragen?
                try:
                    import schatten_nachlauf
                    schatten_nachlauf.uebertragen(schreiben=True, still=True)
                except Exception as _sn:
                    notiz(f"Schatten-Nachlauf uebersprungen: {str(_sn)[:80]}")

                k = nachlauf.kurse_nachtragen(
                    ncon, data_agent, cfg.trading.default_timeframe)
                ges = ncon.execute("SELECT COUNT(*) FROM nachlauf").fetchone()[0]
                ncon.close()
                notiz(f"Nachlauf: {ges} Ereignisse, {k} Kurse nachgetragen")
            except Exception as e:
                notiz(f"Nachlauf uebersprungen: {str(e)[:90]}")

            # [14.08.2026] Zahlenbuch einmal taeglich. Bewusst HIER und nicht
            # in der Aufgabenplanung: die hat am 14.08. dreimal Erfolg
            # gemeldet und nichts ausgefuehrt (WindowsApps-Verweis, 0 Bytes).
            # Dieser Prozess laeuft nachweislich - also erledigt er es mit.
            heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if letzter_bericht != heute:
                letzter_bericht = heute
                try:
                    import subprocess
                    r = subprocess.run(
                        [sys.executable, os.path.join(HIER, "job_zahlenbuch.py")],
                        cwd=HIER, capture_output=True, text=True,
                        errors="replace", timeout=900)
                    notiz(f"Tagesbericht: "
                          f"{'OK' if r.returncode == 0 else 'FEHLER ' + str(r.returncode)}")
                except Exception as e:
                    notiz(f"Tagesbericht fehlgeschlagen: {str(e)[:90]}")

            time.sleep(3600)
    except KeyboardInterrupt:
        notiz("Beendet.")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    # [STILLER AUSFALL 14.08.2026] Ohne diesen Mantel scheitert der Lauf unter
    # der Windows-Aufgabenplanung lautlos: main() macht die Importe (ccxt,
    # config, DataAgent) VOR dem ersten Log-Eintrag. Schlaegt dort etwas fehl -
    # anderer Suchpfad, fehlende Umgebungsvariable, Netzfehler beim Import -
    # gibt es weder Prozess noch Protokollzeile. Genau das ist um 07:02 Uhr
    # passiert: Aufgabe "gelaufen", Log unveraendert, nichts gesammelt.
    #
    # Ein Fehler, der sich nicht meldet, ist schlimmer als einer, der abstuerzt.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
                        f"ABSTURZ beim Start:\n")
                traceback.print_exc(file=f)
                f.write("\n")
        except Exception:
            pass
        sys.exit(1)
