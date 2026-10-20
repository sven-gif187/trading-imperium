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
    lauf_id         TEXT
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


def db_oeffnen():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(SCHEMA)
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


def ein_lauf(con, cfg, data_agent, signal_agent, zusatz):
    lauf_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    start = time.time()
    geprueft = erzeugt = 0
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

            # analyze() liefert nur oberhalb der Kaufschwelle etwas zurück.
            # Genau das ist die interessante Menge: Signale, bei denen der Bot
            # tatsächlich kaufen wollte. Alles darunter handelt er ohnehin nie.
            if absicht is None:
                continue

            basis = muenze.split("/")[0].upper()
            sp, quelle = live_spread(basis)
            ind = getattr(schnappschuss, "indicators", {}) or {}

            con.execute(
                "INSERT INTO signale (ts_utc,muenze,im_echtbetrieb,score,"
                "confidence,preis,betrag_usd,strategie,begruendung,stop_loss,"
                "rsi,adx,macd_hist,atr,regime,zyklus,fear_greed,spread_bp,"
                "spread_quelle,kosten_runde,lauf_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                 sp, quelle, kosten_je_runde(sp), lauf_id))
            erzeugt += 1

        except Exception as e:
            fehler.append(f"{muenze}: {str(e)[:60]}")
        time.sleep(0.4)          # freundlich zur Börsen-Schnittstelle

    con.execute(
        "INSERT OR REPLACE INTO laeufe (lauf_id,ts_utc,muenzen_geprueft,"
        "signale_erzeugt,dauer_sek,fehler) VALUES (?,?,?,?,?,?)",
        (lauf_id, datetime.now(timezone.utc).isoformat(), geprueft, erzeugt,
         round(time.time() - start, 1), "; ".join(fehler)[:400] or None))
    con.commit()

    notiz(f"Lauf {lauf_id}: {geprueft}/{len(MUENZEN)} Münzen, "
          f"{erzeugt} Signale, {time.time()-start:.0f}s"
          + (f" | Fehler: {'; '.join(fehler)[:120]}" if fehler else ""))
    return erzeugt


def status():
    if not os.path.exists(DB):
        print("Noch nichts gesammelt.")
        return 0
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM signale").fetchone()[0]
    if not n:
        print("Datenbank angelegt, noch keine Signale.")
        return 0
    r = con.execute("SELECT MIN(ts_utc), MAX(ts_utc) FROM signale").fetchone()
    print(f"Signale gesamt : {n}")
    print(f"Zeitraum       : {r[0][:16]} bis {r[1][:16]} (UTC)")
    print()
    print(f"{'Münze':12} {'Signale':>8} {'Ø Score':>8} {'Ø Spread bp':>12} "
          f"{'Kosten/Runde':>13}")
    print("-" * 58)
    for m, k, s, sp, ko in con.execute(
            "SELECT muenze, COUNT(*), AVG(score), AVG(spread_bp), "
            "AVG(kosten_runde) FROM signale GROUP BY muenze "
            "ORDER BY COUNT(*) DESC"):
        marke = " *" if m in ECHTE else ""
        print(f"{m:12} {k:>8} {s or 0:>8.1f} {sp or 0:>12.2f} "
              f"{(ko or 0):>12.3%}{marke}")
    print()
    print("* = Münze, die der Bot wirklich handelt (für die Eichung)")
    q = con.execute("SELECT spread_quelle, COUNT(*) FROM signale "
                    "GROUP BY spread_quelle").fetchall()
    print("Spread-Quelle  :", ", ".join(f"{a}={b}" for a, b in q))
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
        ein_lauf(con, cfg, data_agent, signal_agent, zusatz)
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
            ein_lauf(con, cfg, data_agent, signal_agent, zusatz)

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
