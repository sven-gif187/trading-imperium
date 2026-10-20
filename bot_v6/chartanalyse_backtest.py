# -*- coding: utf-8 -*-
"""Backtest der Chartanalyse - misst, ob die Signale ueberhaupt treffen.

AUFRUF
    python chartanalyse_backtest.py                    # BTC, 1h, 1000 Kerzen
    python chartanalyse_backtest.py BTC/USDC 4h 1500
    python chartanalyse_backtest.py --alle             # alle Coins x alle TF

WAS GEMESSEN WIRD
-----------------
Fuer jedes erkannte Einstiegssignal wird vorwaerts geprueft, was zuerst
eintrat: das vorgeschlagene Ziel oder der vorgeschlagene Stop. Daraus ergibt
sich die Trefferquote und der Erwartungswert je Signalart.

KAUSALITAET
-----------
Die Analyse bekommt in jedem Schritt NUR die Kerzen bis zum aktuellen Index
(df.iloc[:i+1]). Sie kann also nicht wissen, was danach passiert. Ohne diese
Trennung waere jedes Ergebnis wertlos - siehe den dokumentierten
Look-ahead-Befund in 02_EXPERIMENT-REGISTER_v2.0.md Nachtrag N1.

KOSTEN
------
Gerechnet wird mit den gemessenen Kosten aus dem Forschungsprogramm
(kosten_matrix_v3.py): 0,50 % je Runde fuer BTC/ETH als Grundfall. Ein Signal
mit Trefferquote 55 % kann nach Kosten trotzdem ein Verlustgeschaeft sein -
genau das soll hier sichtbar werden.

Dieses Skript handelt nicht. Es liest historische Kerzen und schreibt
Ergebnisse in data_store/telemetrie.db.
"""
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

DB = os.path.join(HIER, "data_store", "telemetrie.db")
KOSTEN_PCT = 0.50          # je Runde, gemessen (K-BASIS BTC/ETH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_signale (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lauf_id       TEXT NOT NULL,
    ts_utc        TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    timeframe     TEXT NOT NULL,
    kerze_zeit    TEXT,
    kerzen_index  INTEGER,
    signal        TEXT NOT NULL,
    guete         REAL,
    preis         REAL,
    stop          REAL,
    ziel          REAL,
    rr            REAL,
    trend         TEXT,
    formationen   TEXT,
    begruendung   TEXT,
    ergebnis      TEXT,          -- ZIEL | STOP | OFFEN
    balken_bis    INTEGER,       -- wie viele Kerzen bis zum Ergebnis
    rendite_pct   REAL,          -- brutto
    rendite_netto REAL           -- nach Kosten
);
CREATE TABLE IF NOT EXISTS chart_laeufe (
    lauf_id       TEXT PRIMARY KEY,
    ts_utc        TEXT NOT NULL,
    symbol        TEXT,
    timeframe     TEXT,
    kerzen        INTEGER,
    signale       INTEGER,
    treffer       INTEGER,
    quote_pct     REAL,
    ev_netto_pct  REAL,
    kosten_pct    REAL,
    parameter     TEXT
);
CREATE INDEX IF NOT EXISTS ix_sig_lauf ON chart_signale(lauf_id);
CREATE INDEX IF NOT EXISTS ix_sig_art  ON chart_signale(signal, ergebnis);
"""


def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=10.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def hole_kerzen(symbol: str, timeframe: str, anzahl: int):
    """Holt historische Kerzen ueber ccxt (dieselbe Boerse wie der Bot)."""
    import ccxt
    import pandas as pd
    boerse = ccxt.binance({"enableRateLimit": True})
    alle = []
    seit = None
    rest = anzahl
    while rest > 0:
        teil = boerse.fetch_ohlcv(symbol, timeframe,
                                  since=seit, limit=min(1000, rest))
        if not teil:
            break
        alle = teil + alle if seit is None and alle else alle + teil
        rest -= len(teil)
        if len(teil) < 1000:
            break
        seit = teil[-1][0] + 1
        time.sleep(boerse.rateLimit / 1000.0)
    if not alle:
        return None
    df = pd.DataFrame(alle, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df["zeit"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.tail(anzahl).reset_index(drop=True)


def vorwaerts_pruefen(df, start: int, stop: float, ziel: float, max_balken=100):
    """Was kam zuerst - Ziel oder Stop? Konservativ: Stop gewinnt Gleichstand.

    Wenn in einer Kerze beide Marken liegen, wird STOP gewertet. Alles andere
    waere geschoenigt: ohne Tick-Daten weiss man nicht, was zuerst kam, und im
    Zweifel gegen sich selbst zu rechnen ist die einzige ehrliche Variante.
    """
    ende = min(len(df), start + 1 + max_balken)
    for i in range(start + 1, ende):
        hoch = float(df["High"].iloc[i])
        tief = float(df["Low"].iloc[i])
        if tief <= stop:
            return "STOP", i - start
        if hoch >= ziel:
            return "ZIEL", i - start
    return "OFFEN", ende - start - 1


def lauf(symbol="BTC/USDC", timeframe="1h", kerzen=1000, min_guete=0.35):
    from features.chartanalyse import analysiere

    print(f"\n  Lade {kerzen} Kerzen {symbol} {timeframe} ...")
    df = hole_kerzen(symbol, timeframe, kerzen)
    if df is None or len(df) < 100:
        print("  Zu wenig Daten.")
        return None
    print(f"  {len(df)} Kerzen von {df['zeit'].iloc[0]} bis {df['zeit'].iloc[-1]}")

    lauf_id = f"{symbol.replace('/','')}_{timeframe}_{int(time.time())}"
    jetzt = datetime.now(timezone.utc).isoformat()[:19]
    zeilen = []
    start = 60                       # Vorlauf, damit Zonen entstehen koennen

    for i in range(start, len(df) - 1):
        # KAUSAL: nur Kerzen bis einschliesslich i
        teil = df.iloc[:i + 1]
        erg = analysiere(teil, symbol, timeframe)
        if erg is None or erg.einstieg_signal == "KEIN":
            continue
        if erg.einstieg_guete < min_guete:
            continue
        if not (erg.vorschlag_stop and erg.vorschlag_ziel):
            continue
        if erg.vorschlag_ziel <= erg.preis or erg.vorschlag_stop >= erg.preis:
            continue

        ergebnis, balken = vorwaerts_pruefen(
            df, i, erg.vorschlag_stop, erg.vorschlag_ziel)
        if ergebnis == "ZIEL":
            brutto = (erg.vorschlag_ziel / erg.preis - 1) * 100
        elif ergebnis == "STOP":
            brutto = (erg.vorschlag_stop / erg.preis - 1) * 100
        else:
            brutto = (float(df["Close"].iloc[min(i + 100, len(df) - 1)])
                      / erg.preis - 1) * 100
        netto = brutto - KOSTEN_PCT

        zeilen.append((
            lauf_id, jetzt, symbol, timeframe,
            str(df["zeit"].iloc[i]), i, erg.einstieg_signal,
            erg.einstieg_guete, erg.preis, erg.vorschlag_stop,
            erg.vorschlag_ziel, erg.rr_verhaeltnis, erg.trend,
            ",".join(f.name for f in erg.formationen),
            erg.begruendung[:300], ergebnis, balken,
            round(brutto, 4), round(netto, 4)))

    if not zeilen:
        print("  Keine Signale gefunden.")
        return None

    con = db()
    con.executemany(
        "INSERT INTO chart_signale (lauf_id,ts_utc,symbol,timeframe,kerze_zeit,"
        "kerzen_index,signal,guete,preis,stop,ziel,rr,trend,formationen,"
        "begruendung,ergebnis,balken_bis,rendite_pct,rendite_netto) "
        "VALUES (" + ",".join("?" * 19) + ")", zeilen)

    treffer = sum(1 for z in zeilen if z[15] == "ZIEL")
    quote = treffer / len(zeilen) * 100
    ev = sum(z[18] for z in zeilen) / len(zeilen)
    con.execute(
        "INSERT OR REPLACE INTO chart_laeufe (lauf_id,ts_utc,symbol,timeframe,"
        "kerzen,signale,treffer,quote_pct,ev_netto_pct,kosten_pct,parameter) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (lauf_id, jetzt, symbol, timeframe, len(df), len(zeilen), treffer,
         round(quote, 2), round(ev, 4), KOSTEN_PCT,
         f"min_guete={min_guete}, swing_weite=3, max_balken=100"))
    con.commit()
    con.close()

    bericht(zeilen, symbol, timeframe, quote, ev)
    return lauf_id


def bericht(zeilen, symbol, timeframe, quote, ev):
    print("\n" + "=" * 84)
    print(f" ERGEBNIS {symbol} {timeframe}")
    print("=" * 84)
    print(f"\n  Signale gesamt : {len(zeilen)}")
    print(f"  Trefferquote   : {quote:.1f}%")
    print(f"  EV brutto      : {sum(z[17] for z in zeilen)/len(zeilen):+.3f}% je Signal")
    print(f"  EV NETTO       : {ev:+.3f}% je Signal  (nach {KOSTEN_PCT}% Kosten)")

    print(f"\n  Nach Signalart:")
    print(f"    {'Art':<16s} {'n':>5s} {'Treffer':>8s} {'Quote':>7s} "
          f"{'EV netto':>10s}")
    print("    " + "-" * 50)
    for art in sorted({z[6] for z in zeilen}):
        g = [z for z in zeilen if z[6] == art]
        t = sum(1 for z in g if z[15] == "ZIEL")
        print(f"    {art:<16s} {len(g):5d} {t:8d} {t/len(g)*100:6.1f}% "
              f"{sum(z[18] for z in g)/len(g):+9.3f}%")

    print(f"\n  URTEIL: ", end="")
    if ev > 0.1:
        print("POSITIV nach Kosten - naeher ansehen lohnt sich.")
    elif ev > -0.1:
        print("NEUTRAL - im Rauschen, kein belastbarer Vorteil.")
    else:
        print("NEGATIV nach Kosten - so nicht einbauen.")
    print("  Achtung: ein einzelner Lauf ist noch kein Beweis. Erst ueber")
    print("  mehrere Coins, Zeitrahmen und Marktphasen wird daraus ein Befund.")
    print("=" * 84)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--alle" in sys.argv:
        for sym in ("BTC/USDC", "ETH/USDC", "SOL/USDC"):
            for tf in ("1h", "4h"):
                try:
                    lauf(sym, tf, 1000)
                except Exception as e:
                    print(f"  {sym} {tf}: Fehler {e}")
        return 0
    sym = args[0] if args else "BTC/USDC"
    tf = args[1] if len(args) > 1 else "1h"
    n = int(args[2]) if len(args) > 2 else 1000
    lauf(sym, tf, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
