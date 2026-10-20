# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Trade-Ebene in forschung.db, Freigabe vom 04.08.2026.
"""
Legt die Tabelle trades_journal in der BESTEHENDEN forschung.db an und
befuellt sie aus den vorhandenen Journalen. Keine zweite Datenbank.

STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

WARUM: forschung.db hat bisher nur die Forschungsebene (trials, befunde,
kostenszenarien). Was fehlt, ist die Trade-Ebene - pro Trade der
Marktkontext beim Einstieg, Entry/Stop/Ziele, Ergebnis in R, MFE, MAE,
Kosten und welche Regel erfuellt war. Ohne diese Ebene laesst sich nach
20 Trades nicht sagen, WARUM etwas funktioniert hat.

TRENNUNG DER QUELLEN: Die Spalte 'quelle' trennt v6_live, v6_paper,
v4_import und backtest_*. Damit lassen sich Backtests verschiedener
Konfigurationen nebeneinander halten, ohne dass sich etwas vermischt -
jede Auswertung filtert auf ihre Quelle.

EHRLICH ZUM BACKFILL: Die Altjournale enthalten NICHT alle Felder. MFE,
MAE, Spread beim Einstieg, Regelkonformitaet und Marktregime fehlen dort
und bleiben NULL. Sie werden erst fuer neue Trades gefuellt. Ein NULL ist
ehrlicher als ein rekonstruierter Schaetzwert.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
DB = os.path.join(PROJEKT, "docs", "forschungsprogramm_2026-07",
                  "forschung.db")
J_V6 = os.path.join(PROJEKT, "data_store", "trades_v5.json")
J_V4 = os.path.join(PROJEKT, "v4_referenz", "trades_log_v4.json")

SCHEMA = """
CREATE TABLE trades_journal (
    trade_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quelle            TEXT NOT NULL,      -- v6_live | v6_paper | v4_import | backtest_<name>
    eroeffnet_at      TEXT NOT NULL,      -- ISO 8601 UTC
    geschlossen_at    TEXT,
    symbol            TEXT NOT NULL,
    richtung          TEXT DEFAULT 'LONG',
    -- Strategie und Setup
    strategie_id      TEXT,
    strategie_version TEXT,
    setup_name        TEXT,
    score             REAL,
    confidence        REAL,
    -- Marktkontext beim Einstieg
    regime_1d         TEXT,
    regime_4h         TEXT,
    regime_1h         TEXT,
    fear_greed        INTEGER,
    key_level_typ     TEXT,
    key_level_preis   REAL,
    -- Preise und Groessen
    entry_geplant     REAL,
    entry_fill        REAL,
    slippage_pct      REAL,
    stop_initial      REAL,
    stop_final        REAL,
    tp1               REAL,
    tp2               REAL,
    exit_fill         REAL,
    exit_grund        TEXT,
    menge             REAL,
    einsatz_usd       REAL,
    nachkaeufe        INTEGER DEFAULT 0,
    nachkauf_usd      REAL DEFAULT 0,
    -- Kosten
    spread_pct_entry  REAL,
    gebuehr_usd       REAL,
    -- Ergebnis
    pnl_usd           REAL,
    pnl_pct           REAL,
    r_multiple        REAL,
    mfe_pct           REAL,               -- maximale guenstige Bewegung
    mae_pct           REAL,               -- maximale adverse Bewegung
    haltedauer_min    REAL,
    -- Regelkonformitaet
    regeln_erfuellt   TEXT,               -- JSON
    regelverstoss     TEXT,
    -- Nachvollziehbarkeit
    decision_id       TEXT,
    cycle_id          TEXT,
    feature_hash      TEXT,
    notizen           TEXT,
    eingetragen_at    TEXT NOT NULL
)
"""

INDIZES = [
    "CREATE INDEX idx_tj_quelle_strat ON trades_journal (quelle, strategie_id)",
    "CREATE INDEX idx_tj_symbol_zeit ON trades_journal (symbol, eroeffnet_at)",
    "CREATE INDEX idx_tj_geschlossen ON trades_journal (geschlossen_at)",
]

SPALTEN = [
    "quelle", "eroeffnet_at", "geschlossen_at", "symbol", "richtung",
    "strategie_id", "setup_name", "score", "fear_greed",
    "entry_fill", "exit_fill", "exit_grund", "menge", "einsatz_usd",
    "nachkaeufe", "nachkauf_usd", "pnl_usd", "pnl_pct", "haltedauer_min",
    "notizen", "eingetragen_at",
]


def _zeit(x):
    return str(x or "")[:32]


def sammle(pfad, quelle, jetzt):
    """Positionen aus einem Journal rekonstruieren: Erstkauf bis Verkauf."""
    if not os.path.isfile(pfad):
        return [], f"Journal fehlt: {pfad}"
    trades = json.load(open(pfad, encoding="utf-8", errors="ignore"))
    trades.sort(key=lambda x: (str(x.get("time", "")), x.get("_id", 0)))
    offen, fertig, waisen = {}, [], 0
    for t in trades:
        typ = (t.get("type") or "").upper()
        coin = t.get("coin")
        if not coin:
            continue
        try:
            betrag = float(t.get("amount", 0) or 0)
            preis = float(t.get("price", 0) or 0)
            menge = float(t.get("qty", 0) or 0)
        except (TypeError, ValueError):
            continue
        if typ in ("BUY", "BTC_ACCUMULATE"):
            if coin in offen:
                offen[coin]["nachkaeufe"] += 1
                offen[coin]["nachkauf_usd"] += betrag
                offen[coin]["einsatz"] += betrag
                offen[coin]["menge"] += menge
            else:
                offen[coin] = dict(
                    zeit=_zeit(t.get("time")), strategie=t.get("strategy"),
                    setup=t.get("signal"), score=t.get("score"),
                    entry=preis, menge=menge, einsatz=betrag,
                    nachkaeufe=0, nachkauf_usd=0.0,
                    fg=t.get("fear_greed"))
        elif typ == "DCA":
            if coin in offen:
                offen[coin]["nachkaeufe"] += 1
                offen[coin]["nachkauf_usd"] += betrag
                offen[coin]["einsatz"] += betrag
                offen[coin]["menge"] += menge
            else:
                waisen += 1
        elif typ in ("SELL", "MANUAL_SELL"):
            p = offen.pop(coin, None)
            if p is None:
                waisen += 1
                continue
            pnl = t.get("pnl")
            pnl_pct = t.get("pnl_pct")
            halte = None
            try:
                a = datetime.fromisoformat(p["zeit"])
                b = datetime.fromisoformat(_zeit(t.get("time")))
                halte = round((b - a).total_seconds() / 60.0, 2)
            except (ValueError, TypeError):
                pass
            fertig.append((
                quelle, p["zeit"], _zeit(t.get("time")), coin, "LONG",
                p["strategie"] or t.get("strategy"), p["setup"],
                p["score"], p["fg"],
                p["entry"] or None, preis or None, t.get("reason"),
                p["menge"] or None, round(p["einsatz"], 4) or None,
                p["nachkaeufe"], round(p["nachkauf_usd"], 4),
                float(pnl) if pnl is not None else None,
                float(pnl_pct) if pnl_pct is not None else None,
                halte,
                "Backfill aus " + os.path.basename(pfad) +
                " - MFE/MAE/Spread/Regime/Regelkonformitaet nicht enthalten",
                jetzt))
    return fertig, (f"{len(fertig)} geschlossene Positionen, "
                    f"{len(offen)} noch offen, {waisen} Waisen")


def main():
    schreiben = "--schreiben" in sys.argv
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    da = ro.execute("select count(*) from sqlite_master where type='table' "
                    "and name='trades_journal'").fetchone()[0]
    tabellen = [r[0] for r in ro.execute(
        "select name from sqlite_master where type='table' order by name")]
    ro.close()

    print("=" * 92)
    print(" trades_journal - Trade-Ebene in der BESTEHENDEN forschung.db")
    print("=" * 92)
    print(f"  Datenbank: {DB}")
    print(f"  Tabellen bisher: {', '.join(tabellen)}")
    print(f"  trades_journal existiert bereits: {'JA' if da else 'nein'}")
    if da:
        print("\n  Tabelle ist schon da - kein zweites Anlegen.")

    v6, m6 = sammle(J_V6, "v6_paper", jetzt)
    v4, m4 = sammle(J_V4, "v4_import", jetzt)
    print(f"\n  Backfill v6_paper  (data_store/trades_v5.json): {m6}")
    print(f"  Backfill v4_import (v4_referenz/trades_log_v4.json): {m4}")
    print(f"  Zusammen: {len(v6) + len(v4)} Zeilen")
    print(f"\n  {len(SPALTEN)} von 44 Spalten werden befuellt. NULL bleiben:")
    print("    MFE, MAE, Spread bei Entry, Regime 1D/4H/1H, Key-Level,")
    print("    Stop, Take-Profit, R-Multiple, Slippage, Regelkonformitaet,")
    print("    decision_id, cycle_id, feature_hash.")
    print("    Diese Felder existieren in den Altjournalen nicht und werden")
    print("    erst fuer NEUE Trades gefuellt. NULL statt Schaetzwert.")

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    con = sqlite3.connect(DB)
    try:
        con.execute("BEGIN")
        if not da:
            con.execute(SCHEMA)
            for idx in INDIZES:
                con.execute(idx)
        platz = ",".join("?" * len(SPALTEN))
        con.executemany(
            f"INSERT INTO trades_journal ({','.join(SPALTEN)}) "
            f"VALUES ({platz})", v6 + v4)
        n = con.execute("select count(*) from trades_journal").fetchone()[0]
        if n < len(v6) + len(v4):
            con.rollback()
            print(f"\nROLLBACK: erwartet mindestens {len(v6)+len(v4)}, "
                  f"gemessen {n}")
            return 4
        con.commit()
        print(f"\nCOMMIT. trades_journal: {n} Zeilen")
    except Exception as ex:
        con.rollback()
        print("ROLLBACK wegen Fehler:", ex)
        return 5
    finally:
        con.close()

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    print("\nSELECT-Verifikation:")
    for q, n, pnl in ro.execute(
            "select quelle, count(*), round(sum(pnl_usd),2) "
            "from trades_journal group by quelle"):
        print(f"    {q:<12s} {n:5d} Trades, Summe pnl {pnl}$")
    print("\n  Top-Strategien nach Trades (v4_import):")
    for s, n, pnl in ro.execute(
            "select strategie_id, count(*), round(sum(pnl_usd),2) "
            "from trades_journal where quelle='v4_import' "
            "group by strategie_id order by count(*) desc limit 6"):
        print(f"    {str(s):<20s} {n:4d}  {pnl}$")
    print(f"\n  Spalten gesamt: "
          f"{len(list(ro.execute('pragma table_info(trades_journal)')))}")
    ro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
