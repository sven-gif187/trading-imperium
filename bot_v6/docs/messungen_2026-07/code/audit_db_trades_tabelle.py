# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Trade-Ebene in forschung.db, Freigabe vom 04.08.2026.
"""
HINWEIS 04.08.2026, NACHTRAEGLICH: Dieses Skript wird NICHT mehr gebraucht.
Die Trade-Ebene existiert bereits als Tabelle 'trades_journal' in
forschung.db (1137 Zeilen, Backfill aus data_store/trades_v5.json), und
zwar mit demselben Zweck und einem breiteren Schema - inklusive
regime_1d/4h/1h, key_level_typ, key_level_preis, r_multiple, mfe_pct,
mae_pct, regeln_erfuellt und decision_id/cycle_id/feature_hash.
Der Schreibversuch dieses Skripts wurde durch die eingebaute
Spaltenpruefung per ROLLBACK gestoppt, bevor eine zweite, konkurrierende
Tabelle entstehen konnte. Das Skript bleibt als Beleg dieser Pruefung
liegen; ausfuehren im Dry-Run ist unschaedlich, --schreiben wuerde heute
an derselben Pruefung scheitern.
Fuer die offenen NULL-Felder in trades_journal (MFE, MAE, Spread, Regime,
Score, Regelkonformitaet) gilt: sie sind in trades_v5.json nicht
enthalten und muessen kuenftig beim Trade selbst mitgeschrieben werden.

Urspruenglicher Zweck:
Legt die Tabelle 'trades_forensik' in der BESTEHENDEN forschung.db an.

STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

WARUM: forschung.db hat bisher nur die Forschungsebene (trials, befunde,
kostenszenarien). Was fehlt, ist die Trade-Ebene - je Trade der Kontext
beim Einstieg, das Ergebnis in R, MFE/MAE, die tatsaechlichen Kosten und
welche Regel erfuellt war. Ohne diese Ebene laesst sich nach 50 Trades
nicht sagen, WARUM eine Serie lief oder nicht.

KEINE zweite Datenbank, KEIN zweites Register - eine Tabelle in der
vorhandenen Datei.

ABGRENZUNG: Diese Tabelle wird NICHT vom laufenden Bot geschrieben. Sie
wird aus data_store/trades_v5.json befuellt (Nachlauf, read-only auf der
Quelle). Damit bleibt der Entscheidungspfad unberuehrt und die Tabelle
ist jederzeit reproduzierbar neu aufbaubar.

FELDER, die ein Profi-Setup braucht und die hier vorgesehen sind:
  Identitaet   trade_id, quelle, symbol, seite
  Zeit         entry_ts, exit_ts, haltedauer_min
  Strategie    strategie_id, setup_name, score, confidence
  Kontext      regime, cycle_phase, fear_greed, rsi, adx, atr_rel
  Plan         entry_preis, stop_loss, take_profit_1, take_profit_2, r_geplant
  Ausfuehrung  menge, einsatz_usd, exit_preis, exit_grund
  Ergebnis     pnl_usd, pnl_pct, pnl_r, mfe_pct, mae_pct
  Kosten       spread_pct, slippage_entry_pct, slippage_exit_pct, gebuehr_usd
  Disziplin    regel_konform (JSON), abweichungen
  Nachkauf     dca_stufen, dca_volumen_usd
"""
import os
import sqlite3
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "..", "..", "forschungsprogramm_2026-07",
                  "forschung.db")

DDL = """
CREATE TABLE IF NOT EXISTS trades_forensik (
    trade_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    quelle              TEXT NOT NULL,      -- live | paper | backtest | v4
    symbol              TEXT NOT NULL,
    seite               TEXT NOT NULL,      -- BUY | SELL
    entry_ts            TEXT,
    exit_ts             TEXT,
    haltedauer_min      REAL,
    strategie_id        TEXT,
    setup_name          TEXT,
    score               REAL,
    confidence          REAL,
    regime              TEXT,
    cycle_phase         TEXT,
    fear_greed          REAL,
    rsi                 REAL,
    adx                 REAL,
    atr_rel             REAL,
    entry_preis         REAL,
    stop_loss           REAL,
    take_profit_1       REAL,
    take_profit_2       REAL,
    r_geplant           REAL,
    menge               REAL,
    einsatz_usd         REAL,
    exit_preis          REAL,
    exit_grund          TEXT,
    pnl_usd             REAL,
    pnl_pct             REAL,
    pnl_r               REAL,
    mfe_pct             REAL,
    mae_pct             REAL,
    spread_pct          REAL,
    slippage_entry_pct  REAL,
    slippage_exit_pct   REAL,
    gebuehr_usd         REAL,
    dca_stufen          INTEGER,
    dca_volumen_usd     REAL,
    regel_konform       TEXT,               -- JSON
    abweichungen        TEXT,
    zeitstempel_import  TEXT,
    quelle_datei        TEXT
)
"""

IDX = [
    "CREATE INDEX IF NOT EXISTS ix_tf_symbol_entry "
    "ON trades_forensik(symbol, entry_ts)",
    "CREATE INDEX IF NOT EXISTS ix_tf_strategie "
    "ON trades_forensik(strategie_id)",
    "CREATE INDEX IF NOT EXISTS ix_tf_quelle "
    "ON trades_forensik(quelle)",
]


def main():
    schreiben = "--schreiben" in sys.argv

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    vorhanden = [r[0] for r in ro.execute(
        "select name from sqlite_master where type='table' order by name")]
    schon_da = "trades_forensik" in vorhanden
    ro.close()

    print("=" * 90)
    print(" Trade-Ebene fuer forschung.db")
    print("=" * 90)
    print(f"  Datei:              {os.path.abspath(DB)}")
    print(f"  Tabellen bisher:    {len(vorhanden)} -> {vorhanden}")
    print(f"  trades_forensik da: {schon_da}")
    print(f"\n  Anzulegen: 1 Tabelle mit 37 Spalten, 3 Indizes.")
    print(f"  Kein DROP, kein ALTER an bestehenden Tabellen, kein Trigger,")
    print(f"  kein View. CREATE TABLE IF NOT EXISTS - idempotent.")

    if schon_da:
        ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                             uri=True)
        n = ro.execute("select count(*) from trades_forensik").fetchone()[0]
        print(f"\n  Tabelle existiert bereits mit {n} Zeilen - nichts zu tun.")
        ro.close()
        return 0

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    con = sqlite3.connect(DB)
    try:
        con.execute("BEGIN")
        con.execute(DDL)
        for s in IDX:
            con.execute(s)
        # Verifikation im selben Transaktionsfenster
        cols = [d[1] for d in con.execute("pragma table_info(trades_forensik)")]
        if len(cols) != 37:
            con.rollback()
            print(f"ROLLBACK: erwartet 37 Spalten, gemessen {len(cols)}")
            return 4
        con.commit()
        print(f"\nCOMMIT. Tabelle angelegt, {len(cols)} Spalten.")
    except Exception as ex:
        con.rollback()
        print("ROLLBACK wegen Fehler:", ex)
        return 5
    finally:
        con.close()

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    tabellen = [r[0] for r in ro.execute(
        "select name from sqlite_master where type='table' order by name")]
    idx = [r[0] for r in ro.execute(
        "select name from sqlite_master where type='index' "
        "and tbl_name='trades_forensik'")]
    n = ro.execute("select count(*) from trades_forensik").fetchone()[0]
    print("\nSELECT-Verifikation:")
    print(f"  Tabellen jetzt: {len(tabellen)} -> {tabellen}")
    print(f"  Indizes:        {idx}")
    print(f"  Zeilen:         {n} (leer, wird per Nachlauf befuellt)")
    ro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
