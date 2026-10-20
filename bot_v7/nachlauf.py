"""
nachlauf.py — was WÄRE passiert? Kurs nach Ausstieg und nach Blockade
=====================================================================

WARUM ES DIESES PROGRAMM GIBT

Zwei Fragen des Projekts sind ohne diese Messung nicht beantwortbar:

1. **War der Stop-Loss richtig?** 68 Stop-Verkäufe kosteten −187,63 $ —
   mehr, als alle 169 Trailing-Gewinne einbrachten. Ob Aussitzen besser
   gewesen wäre, weiß niemand, weil nach dem Verkauf niemand mehr
   hinschaut.

2. **Waren die Blockaden richtig?** Rund 98.000 Kaufwünsche wurden
   abgelehnt. Ob das die richtigen 98.000 waren, ist unbekannt.

Beide Fragen brauchen dasselbe: den Kursverlauf NACH der Entscheidung.

WIE ES ARBEITET

Es merkt sich jeden Ausstieg und jede Blockade und trägt später nach,
wie der Kurs 1, 4, 24 und 48 Stunden danach stand. Daraus ergibt sich:

    "Der Stop bei −2 % war richtig"   → Kurs fiel weiter
    "Aussitzen wäre besser gewesen"   → Kurs erholte sich

Es HANDELT NICHT und ändert nichts am Bot. Es liest Kurse und schreibt
in eine eigene Tabelle.

WARUM IM SAMMLER UND NICHT ALS EIGENER DIENST

Der Rechner hat 3,9 GB Speicher und läuft am Anschlag. Ein weiterer
Dauerprozess wäre ein Risiko fürs Messfenster. Diese Messung hängt sich
deshalb an den stündlichen Lauf des Schatten-Universums an — der läuft
ohnehin und holt ohnehin Kurse.

AUFRUF
    python nachlauf.py            einmal nachtragen
    python nachlauf.py --status   was bisher gemessen wurde
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

DB = os.path.join(HIER, "data_store", "nachlauf.db")
JOURNAL = os.path.join(HIER, "data_store", "trades_v5.json")
TEL = os.path.join(HIER, "data_store", "telemetrie.db")

# Nach wie vielen Stunden nachgesehen wird
FENSTER = [1, 4, 24, 48]

# Wie viele Kerzen je Muenze geholt werden, um Kurse nachzutragen.
#
# [BEFUND 77, 26.08.2026] Hier stand fest verdrahtet 200. Bei
# Stundenkerzen sind das rund acht Tage. Alles Aeltere ist mit dem
# Kerzenfenster nicht mehr aufloesbar (siehe "if ziel < erste" weiter
# unten) - und wird dann von der letzten Zeile in kurse_nachtragen()
# als vollstaendig abgehakt, OHNE je einen Kurs bekommen zu haben.
#
# Aufgefallen beim Anschliessen der Notizbuecher: deren Eintraege
# reichen bis zum 11.08. zurueck, also 15 Tage. Mit 200 Kerzen waeren
# rund drei Viertel davon leer abgehakt worden - und ein leer
# abgehaktes Ereignis ist fuer immer verloren, weil vollstaendig=1
# es aus der Warteschlange nimmt.
#
# 600 Stundenkerzen sind 25 Tage. Das deckt den gesamten Bestand mit
# Rand. Kosten: ein Abruf je Muenze und Lauf statt eines kleineren -
# bei drei Muenzen im Stundentakt nicht messbar.
KERZEN = 600
_KERZE_H = 1          # Laenge einer Kerze in Stunden (tf="1h")

SCHEMA = """
CREATE TABLE IF NOT EXISTS nachlauf (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    art         TEXT NOT NULL,      -- 'exit' oder 'blockade'
    kennung     TEXT NOT NULL,      -- eindeutig je Ereignis
    ts_utc      TEXT NOT NULL,      -- Zeitpunkt der Entscheidung
    muenze      TEXT NOT NULL,
    preis       REAL NOT NULL,      -- Kurs zum Zeitpunkt
    grund       TEXT,               -- Exit-Grund bzw. Blockade-Grund
    pnl_pct     REAL,               -- nur bei Ausstieg
    p1h REAL, p4h REAL, p24h REAL, p48h REAL,
    r1h REAL, r4h REAL, r24h REAL, r48h REAL,   -- Rendite in %
    vollstaendig INTEGER DEFAULT 0,
    UNIQUE(art, kennung)
);
CREATE INDEX IF NOT EXISTS ix_nl_offen ON nachlauf(vollstaendig, ts_utc);
"""


def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(SCHEMA)
    return con


def ereignisse_aufnehmen(con):
    """Neue Ausstiege und Blockaden erfassen (noch ohne Nachlauf-Kurse)."""
    neu = 0
    # --- Ausstiege aus dem Journal ---------------------------------
    try:
        j = json.load(open(JOURNAL, encoding="utf-8"))
        j = j if isinstance(j, list) else j.get("trades", [])
        for t in j:
            if t.get("pnl") is None:
                continue
            ts = str(t.get("time") or "")
            if not ts:
                continue
            kennung = f"{ts}_{t.get('coin', '?')}"
            try:
                con.execute(
                    "INSERT OR IGNORE INTO nachlauf (art,kennung,ts_utc,muenze,"
                    "preis,grund,pnl_pct) VALUES ('exit',?,?,?,?,?,?)",
                    (kennung, ts, str(t.get("coin") or "?"),
                     float(t.get("price") or 0),
                     str(t.get("reason") or t.get("strategy") or "")[:60],
                     t.get("pnl_pct")))
                neu += con.total_changes and 1 or 0
            except Exception:
                pass
    except Exception:
        pass

    # --- Blockaden: nur eine Stichprobe, sonst laeuft die DB voll ---
    # 98.000 Ablehnungen sind zu 99 % dieselben Gruende im Endlostakt.
    # Eine Stichprobe je Stunde und Muenze reicht voellig.
    try:
        tel = sqlite3.connect(TEL)
        for eid, ts, sym, grund, preis in tel.execute(
                "SELECT evaluation_id, MIN(ts_utc), symbol, primary_reason, "
                "entry_price FROM evaluations WHERE decision='REJECTED' "
                "AND entry_price IS NOT NULL "
                "GROUP BY symbol, primary_reason, substr(ts_utc,1,13) "
                "ORDER BY ts_utc DESC LIMIT 400"):
            con.execute(
                "INSERT OR IGNORE INTO nachlauf (art,kennung,ts_utc,muenze,"
                "preis,grund) VALUES ('blockade',?,?,?,?,?)",
                (str(eid), ts, str(sym or "?"), float(preis or 0),
                 str(grund or "")[:60]))
        tel.close()
    except Exception:
        pass

    # --- Notizbuch-Eintraege: was eine Regel getan HAETTE ------------
    #
    # [BEFUND 77, 26.08.2026] Die Tabelle schatten_regeln haelt seit dem
    # 11.08. fest, was das KI-Modell und der Ensemble-Vergleich getan
    # haetten - aber ihre Ergebnisspalten pnl_pct und position_id waren
    # in 1.994 von 1.994 Zeilen LEER.
    #
    # Das ist kein Fehler der Schreibfunktion: core/telemetrie.py:677
    # nimmt pnl_pct entgegen, der Aufrufer kann ihn nur nicht kennen -
    # im Moment des Signals ist der Ausgang noch offen. Der Kommentar
    # dort sagt es selbst: "erst der spaetere Vergleich mit dem
    # tatsaechlichen Ausgang beantwortet, ob sie genuetzt haette".
    # Dieser spaetere Vergleich fehlte.
    #
    # Statt eine zweite Nachtrage-Mechanik zu bauen, haengen die Notizen
    # jetzt an der hier bereits laufenden: Ereignis eintragen, spaeter
    # r1h/r4h/r24h/r48h per UPDATE nachfuellen. Bewaehrt an 35.754
    # Zeilen. Genau so wurde am 20.08. schon die Art 'schatten'
    # nachgeruestet.
    #
    # HORIZONT: Sven hat am 26.08. 24 Stunden als Hauptmass gewaehlt.
    # Begruendung aus den Daten (29.807 vollstaendige Blockaden):
    #   1 h  Median +0,061 %  -  achtmal KLEINER als die Gebuehr 0,505 %
    #   24 h Median +2,104 %  -  Signal/Rauschen viermal besser
    # Bei einer Stunde bewegen sich nur 54,8 % der Faelle ueber die
    # Reibung hinaus; bei 24 h sind es 88,4 %. Alle vier Horizonte
    # werden weiter mitgeschrieben, 24 h ist nur das Urteilsmass.
    #
    # AENDERT KEIN BOT-VERHALTEN. Es entstehen nur zusaetzliche Zeilen
    # in nachlauf.db. Freeze-vertraeglich.
    #
    # WEITER AB DER LETZTEN: Ein "ORDER BY id DESC LIMIT 400" haette
    # bei jedem Lauf dieselben neuesten 400 gegriffen - die aelteren
    # waeren nie an die Reihe gekommen. Beim Test an einer Kopie fiel
    # genau das auf. Deshalb wird die hoechste bereits uebernommene
    # Nummer gelesen und dort weitergemacht.
    try:
        letzte = con.execute(
            "SELECT MAX(CAST(substr(kennung,2) AS INTEGER)) FROM nachlauf "
            "WHERE art='notiz'").fetchone()[0] or 0
    except Exception:
        letzte = 0
    try:
        tel = sqlite3.connect(TEL)
        for rid, ts, regel, sym, preis in tel.execute(
                "SELECT id, ts_utc, regel, symbol, preis "
                "FROM schatten_regeln WHERE preis IS NOT NULL AND preis > 0 "
                "AND id > ? ORDER BY id ASC LIMIT 600", (letzte,)):
            con.execute(
                "INSERT OR IGNORE INTO nachlauf (art,kennung,ts_utc,muenze,"
                "preis,grund) VALUES ('notiz',?,?,?,?,?)",
                ("n%s" % rid, ts, str(sym or "?"), float(preis or 0),
                 str(regel or "")[:60]))
        tel.close()
    except Exception:
        pass

    con.commit()
    return neu


def kurse_nachtragen(con, data_agent, tf="1h"):
    """Für fällige Ereignisse den Kurs nachtragen."""
    jetzt = datetime.now(timezone.utc)
    # ALTESTE zuerst. Mit DESC kamen immer nur die neuesten 60 dran;
    # da stuendlich neue dazukamen, erreichte kein Ereignis je seine
    # 24- und 48-Stunden-Marke (p24h/p48h blieben bei 0).
    #
    # [FUND 18.08.2026] "Aelteste zuerst" allein reicht nicht. Am 18.08.
    # standen 1.520 Ereignisse offen, davon 1.030 vom Vortag, die auf ihre
    # 24- und 48-Stunden-Marke warteten - also noch GAR NICHT faellig
    # waren. Die belegten das Fenster von 400 vollstaendig, und die
    # Ereignisse von heute kamen nie an die Reihe, obwohl ihr
    # 1-Stunden-Kurs laengst fertig war. Ergebnis: Der juengste
    # nachgetragene 1-Stunden-Kurs war 18 Stunden alt, das Log meldete
    # dabei brav "4 Kurse nachgetragen" - es sah nach Betrieb aus.
    #
    # Jetzt werden nur Ereignisse geholt, bei denen ueberhaupt etwas
    # FAELLIG ist. Wer noch wartet, verstopft die Schlange nicht mehr.
    #
    # Merke: Eine Warteschlange nach Alter abzuarbeiten ist richtig -
    # aber nur unter denen, die auch bereit sind. Sonst blockiert der
    # Kopf der Schlange alles dahinter.
    bedingungen = " OR ".join(
        f"(p{h}h IS NULL AND ts_utc <= ?)" for h in FENSTER)
    grenzen = [(jetzt - timedelta(hours=h)).isoformat() for h in FENSTER]
    offen = con.execute(
        "SELECT id, ts_utc, muenze, preis, p1h, p4h, p24h, p48h "
        f"FROM nachlauf WHERE vollstaendig=0 AND ({bedingungen}) "
        "ORDER BY ts_utc ASC LIMIT 400", grenzen).fetchall()
    if not offen:
        return 0

    # Kerzen je Münze einmal holen, nicht je Ereignis
    kerzen = {}
    getragen = 0
    for zid, ts, muenze, preis, p1, p4, p24, p48 in offen:
        try:
            zeit = datetime.fromisoformat(ts)
            if zeit.tzinfo is None:
                zeit = zeit.replace(tzinfo=timezone.utc)
        except Exception:
            con.execute("UPDATE nachlauf SET vollstaendig=1 WHERE id=?", (zid,))
            continue
        if not preis or preis <= 0:
            con.execute("UPDATE nachlauf SET vollstaendig=1 WHERE id=?", (zid,))
            continue

        if muenze not in kerzen:
            try:
                snap = data_agent.fetch_snapshot(muenze, tf, limit=KERZEN)
                kerzen[muenze] = getattr(snap, "_df", None)
            except Exception:
                kerzen[muenze] = None
        df = kerzen.get(muenze)
        if df is None or len(df) == 0:
            continue

        werte, fertig = {}, True
        for h, vorhanden in zip(FENSTER, (p1, p4, p24, p48)):
            if vorhanden is not None:
                continue
            ziel = zeit + timedelta(hours=h)
            if ziel > jetzt:
                fertig = False          # noch nicht faellig
                continue
            try:
                idx = df.index
                erste = idx[0].to_pydatetime().replace(tzinfo=timezone.utc)
                # Liegt der Zielzeitpunkt VOR der aeltesten geholten Kerze,
                # erfuellen ALLE Kerzen die Bedingung ">= ziel" - dann waere
                # treffer[0] immer dieselbe aelteste Kerze und alle vier
                # Fristen bekaemen denselben falschen Kurs. Solche Ereignisse
                # sind mit dem Kerzenfenster nicht mehr aufloesbar.
                if ziel < erste:
                    continue
                # naechste Kerze bei oder nach dem Zielzeitpunkt
                treffer = [i for i in range(len(idx))
                           if idx[i].to_pydatetime().replace(
                               tzinfo=timezone.utc) >= ziel]
                if not treffer:
                    continue
                # [FUND 19.08.2026] Die getroffene Kerze muss FERTIG sein.
                #
                # Eine Kerze traegt ihre OEFFNUNGS-Zeit als Stempel; die
                # 23:00-Kerze ist erst um 00:00 zu Ende. Wer sie um 23:30
                # ausliest, bekommt keinen Schlusskurs, sondern den gerade
                # laufenden Preis - eine Zahl, die sich noch bewegt, aber
                # dauerhaft als Messwert gespeichert wird.
                #
                # Gemessen beim Nachrechnen der bestehenden Werte:
                # 3.870 von 11.200 (34,6 %) stimmten mit KEINER fertigen
                # Kerze ueberein. Jeder dritte Messwert stammte aus einer
                # laufenden Kerze.
                #
                # Derselbe Fehlertyp wie bei den Merkmalen (Befund 39) und
                # beim KI-Modell auf df.iloc[-1]: die letzte Kerze ist noch
                # keine Kerze.
                _offen = idx[treffer[0]].to_pydatetime().replace(
                    tzinfo=timezone.utc)
                if _offen + timedelta(hours=_KERZE_H) > jetzt:
                    fertig = False       # laufende Kerze - naechste Runde
                    continue
                kurs = float(df["Close"].iloc[treffer[0]])
                werte[h] = kurs
            except Exception:
                continue

        if werte:
            sp, wt = [], []
            for h, kurs in werte.items():
                sp.append(f"p{h}h=?"); wt.append(kurs)
                sp.append(f"r{h}h=?"); wt.append((kurs / preis - 1) * 100)
            con.execute(f"UPDATE nachlauf SET {','.join(sp)} WHERE id=?",
                        (*wt, zid))
            getragen += 1
        if fertig and not werte:
            con.execute("UPDATE nachlauf SET vollstaendig=1 WHERE id=?", (zid,))
        elif zeit + timedelta(hours=max(FENSTER)) < jetzt:
            con.execute("UPDATE nachlauf SET vollstaendig=1 WHERE id=?", (zid,))
    con.commit()
    return getragen


def status():
    if not os.path.exists(DB):
        print("Noch nichts gemessen.")
        return 0
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM nachlauf").fetchone()[0]
    print(f"Ereignisse erfasst: {n}")
    for art in ("exit", "blockade"):
        k = con.execute("SELECT COUNT(*) FROM nachlauf WHERE art=?",
                        (art,)).fetchone()[0]
        m = con.execute("SELECT COUNT(*) FROM nachlauf WHERE art=? AND "
                        "r24h IS NOT NULL", (art,)).fetchone()[0]
        print(f"  {art:10} {k:5}  davon mit 24-h-Kurs: {m}")
    print()
    print("=== Ausstiege: wie ging es weiter? ===")
    for grund, k, r4, r24 in con.execute(
            "SELECT grund, COUNT(*), AVG(r4h), AVG(r24h) FROM nachlauf "
            "WHERE art='exit' AND r24h IS NOT NULL GROUP BY grund "
            "ORDER BY COUNT(*) DESC LIMIT 8"):
        print(f"  {str(grund)[:30]:32} n={k:3}  "
              f"nach 4h {r4:+6.2f}%  nach 24h {r24:+6.2f}%")
    con.close()
    return 0


def main():
    if "--status" in sys.argv:
        return status()
    from config.settings import AppConfig
    from data.market_data import DataAgent
    cfg = AppConfig.load()
    da = DataAgent(cfg)
    con = db()
    ereignisse_aufnehmen(con)
    n = kurse_nachtragen(con, da, cfg.trading.default_timeframe)
    ges = con.execute("SELECT COUNT(*) FROM nachlauf").fetchone()[0]
    con.close()
    try:
        print(f"Nachlauf: {ges} Ereignisse, {n} Kurse nachgetragen")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
