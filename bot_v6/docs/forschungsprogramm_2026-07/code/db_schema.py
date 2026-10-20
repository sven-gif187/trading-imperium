# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsdatenbank - Schema, 30.07.2026. Siehe ../DATENBANK.md
"""
Schema der Forschungs- und Dokumentationsdatenbank (Teil A des Auftrags
vom 30.07.2026).

GRENZE - NICHT VERHANDELBAR
---------------------------
Diese Datenbank gehoert AUSSCHLIESSLICH zum Forschungsprogramm. Sie
liegt unter docs/, sie liest NICHTS aus data_store/ und schreibt NICHTS
dorthin, und sie wird vom laufenden Bot nicht angebunden. Eine Umstellung
des Bots auf SQLite ist eine offene, separate Grundsatzentscheidung
(ENTWICKLERHANDBUCH.md:1205) und wird hier NICHT vorweggenommen.

VORRANG (A5): Die .md-Dateien bleiben die verbindliche Fassung. Diese
Datenbank ergaenzt sie um Abfragbarkeit. Bei Widerspruch gilt die .md.
Jede Zeile fuehrt deshalb eine Quellreferenz auf die .md.

Reine Standardbibliothek (sqlite3). Aufruf:
    python db_schema.py            # legt forschung.db an (idempotent)
    python db_schema.py --neu      # loescht und legt neu an
"""
import os
import sqlite3
import sys

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASIS, "forschung.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

-- Trials: eine Zeile je (Trial x Segment x Kostenszenario). Aggregatzeilen
-- (Gesamtzeitraum) tragen segment='GESAMT'.
CREATE TABLE IF NOT EXISTS trials (
    zeile_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trial_id          TEXT NOT NULL,
    runde             INTEGER NOT NULL,
    hypothese         TEXT NOT NULL,
    regel_name        TEXT,
    literatur_quelle  TEXT,
    parameter         TEXT,               -- JSON
    asset             TEXT,
    datenzeitraum     TEXT,
    segment           TEXT NOT NULL,      -- GESAMT | S-A | S-B | S-C
    kostenszenario    TEXT,               -- K-MAKER | K-BASIS | K-KONSERVATIV
    ev_je_runde       REAL,
    ki_unten          REAL,
    ki_oben           REAL,
    placebo_perzentil REAL,
    p_wert            REAL,
    p_wert_fdr        REAL,
    status            TEXT CHECK (status IN
                        ('CONFIRMED','REJECTED','INCONCLUSIVE',
                         'NICHT_AUSGEFUEHRT','VORREGISTRIERT')),
    begruendung       TEXT,
    zeitstempel       TEXT,
    pfad_rohausgabe   TEXT,
    skript_sha256     TEXT,
    quelle_md         TEXT NOT NULL       -- A5: verbindliche Fassung
);

CREATE TABLE IF NOT EXISTS datenquellen (
    quelle_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    url               TEXT,
    typ               TEXT,               -- klines | funding | makro | universum
    coin              TEXT,
    intervall         TEXT,
    erster_datenpunkt TEXT,
    letzter_datenpunkt TEXT,
    anzahl_zeilen     INTEGER,
    luecken           TEXT,               -- JSON
    sha256            TEXT,
    abrufdatum        TEXT,
    lizenzstatus      TEXT,
    quelle_md         TEXT
);

CREATE TABLE IF NOT EXISTS kostenszenarien (
    szenario_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    boerse            TEXT,
    maker_pct         REAL,
    taker_pct         REAL,
    slippage_pct      REAL,
    roundtrip_pct     REAL,
    quelle            TEXT,
    verifiziert_am    TEXT,
    konfidenz         TEXT,               -- SICHER | WAHRSCHEINLICH | UNGEKLAERT
    quelle_md         TEXT
);

CREATE TABLE IF NOT EXISTS bot_architektur (
    modul_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pfad              TEXT NOT NULL UNIQUE,
    zeilen            INTEGER,
    zweck             TEXT,
    abhaengigkeiten   TEXT,               -- JSON: Liste interner Importe
    importiert_von    TEXT,               -- JSON: Liste der Importeure
    status            TEXT CHECK (status IN
                        ('AKTIV','TOT','DEAKTIVIERT','UNGEPRUEFT')),
    status_belege     TEXT,
    bekannte_bugs     TEXT,               -- JSON
    letzte_pruefung   TEXT,
    anmerkung         TEXT
);

CREATE TABLE IF NOT EXISTS befunde (
    befund_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    runde             INTEGER,
    kurztext          TEXT NOT NULL,
    langtext          TEXT,
    konfidenz         TEXT,               -- SICHER | WAHRSCHEINLICH | VERMUTUNG
    risiko_0_10       INTEGER,
    impact_0_10       INTEGER,
    prioritaet        TEXT,
    trial_bezug       TEXT,
    widerlegt_befund_id INTEGER REFERENCES befunde(befund_id),
    zeitstempel       TEXT,
    quelle_md         TEXT
);

CREATE TABLE IF NOT EXISTS register_versionen (
    version           TEXT PRIMARY KEY,
    datum             TEXT,
    sha256            TEXT,
    aenderung         TEXT,
    gueltig_ab        TEXT,
    gueltig_bis       TEXT,
    quelle_md         TEXT
);

CREATE TABLE IF NOT EXISTS programm_status (
    gate_nummer       INTEGER PRIMARY KEY,
    ergebnis          TEXT,               -- NEGATIV | POSITIV | OFFEN
    datum             TEXT,
    begruendung       TEXT,
    verdict_pfad      TEXT
);

CREATE INDEX IF NOT EXISTS ix_trials_id     ON trials(trial_id);
CREATE INDEX IF NOT EXISTS ix_trials_runde  ON trials(runde);
CREATE INDEX IF NOT EXISTS ix_trials_status ON trials(status);
CREATE INDEX IF NOT EXISTS ix_arch_status   ON bot_architektur(status);
CREATE INDEX IF NOT EXISTS ix_quellen_typ   ON datenquellen(typ);
"""


def verbinde(pfad=DB):
    con = sqlite3.connect(pfad)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def anlegen(neu=False):
    if neu and os.path.exists(DB):
        os.remove(DB)
        print(f"  geloescht: {DB}")
    con = verbinde()
    con.executescript(SCHEMA)
    con.commit()
    tabellen = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    print(f"  Datenbank: {DB}")
    print(f"  Tabellen ({len(tabellen)}): {', '.join(tabellen)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(anlegen(neu="--neu" in sys.argv))
