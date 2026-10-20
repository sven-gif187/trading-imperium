# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Backfill trades_journal aus trades_v5.json, 04.08.2026.
"""
Fuellt die Tabelle trades_journal in forschung.db aus
data_store/trades_v5.json neu auf - diesmal mit ALLEN vorhandenen Feldern.

STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

WARUM EIN ZWEITER LAUF: Der erste Backfill uebernahm nur Basisfelder.
Eine Feldzaehlung ueber alle 954 Journal-Eintraege zeigte, dass deutlich
mehr vorhanden ist:
    market_regime, fear_greed_at_entry, score, confidence,
    signal_reasons, active_strategy, latency_ms   je 81 Eintraege
    fee                                             373
    pnl_pct                                         199
    mfe_pct, mae_pct                                 20 (von 428 SELLs)
Diese Werte standen in der Quelle und fehlten in der Tabelle.

data_store/ wird ausschliesslich GELESEN.

PAARBILDUNG: Ein Trade ist ein BUY (plus alle Nachkaeufe auf denselben
Coin) bis zum naechsten SELL desselben Coins. Der SELL liefert Ergebnis,
MFE/MAE und Ausstiegsgrund; der erste BUY liefert Einstieg, Strategie,
Score und Marktkontext. Offene Positionen ohne SELL werden mit
geschlossen_at = NULL eingetragen.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
QUELLE = os.path.join(PROJEKT, "data_store", "trades_v5.json")
DB = os.path.join(HIER, "..", "..", "forschungsprogramm_2026-07",
                  "forschung.db")


def ts(x):
    return x.get("time") or x.get("_saved_at")


def minuten(a, b):
    try:
        d1 = datetime.fromisoformat(a)
        d2 = datetime.fromisoformat(b)
        return round((d2 - d1).total_seconds() / 60.0, 1)
    except Exception:
        return None


def baue_zeilen():
    trades = json.load(open(QUELLE, encoding="utf-8", errors="ignore"))
    trades.sort(key=lambda x: (ts(x) or "", x.get("_id") or 0))
    offen = {}
    zeilen = []
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in trades:
        typ = t.get("type")
        coin = t.get("coin") or t.get("symbol")
        if not coin:
            continue
        if typ in ("BUY", "DCA", "BTC_ACCUMULATE"):
            betrag = float(t.get("amount") or 0)
            if coin in offen:
                o = offen[coin]
                o["nachkaeufe"] += 1
                o["nachkauf_usd"] += betrag
                o["einsatz_usd"] += betrag
            else:
                offen[coin] = dict(
                    eroeffnet_at=ts(t), symbol=coin,
                    strategie_id=t.get("strategy") or t.get("active_strategy"),
                    setup_name=t.get("reason"),
                    score=t.get("score") if t.get("score") is not None
                    else t.get("signal_score"),
                    confidence=t.get("confidence"),
                    regime_1h=t.get("market_regime"),
                    fear_greed=t.get("fear_greed_at_entry"),
                    entry_fill=t.get("price"),
                    menge=t.get("qty"), einsatz_usd=betrag,
                    nachkaeufe=0, nachkauf_usd=0.0,
                    gebuehr_usd=float(t.get("fee") or 0),
                    notizen=None)
        elif typ in ("SELL", "MANUAL_SELL"):
            o = offen.pop(coin, None)
            if o is None:
                o = dict(eroeffnet_at=None, symbol=coin,
                         strategie_id=t.get("strategy"), setup_name=None,
                         score=None, confidence=None, regime_1h=None,
                         fear_greed=None, entry_fill=None, menge=None,
                         einsatz_usd=None, nachkaeufe=0, nachkauf_usd=0.0,
                         gebuehr_usd=0.0,
                         notizen="SELL ohne vorherigen BUY im Journal")
            geb = (o.get("gebuehr_usd") or 0) + float(t.get("fee") or 0)
            pnl = t.get("pnl")
            einsatz = o.get("einsatz_usd")
            r_mult = None
            if pnl is not None and einsatz:
                # R gemessen an der tatsaechlichen Kapitalbindung, nicht an
                # einem geplanten Stop - der steht im Journal nicht.
                try:
                    r_mult = round(float(pnl) / float(einsatz), 4)
                except Exception:
                    r_mult = None
            # eroeffnet_at ist NOT NULL. Bei SELLs ohne vorherigen BUY im
            # Journal (5 Faelle, Positionen aus der Zeit vor dem Journal)
            # wird der SELL-Zeitpunkt eingesetzt und in notizen vermerkt -
            # kein erfundener Einstiegszeitpunkt.
            _eroeffnet = o["eroeffnet_at"] or ts(t)
            zeilen.append((
                "v6_paper", _eroeffnet, ts(t), coin, "LONG",
                o["strategie_id"], None, o["setup_name"], o["score"],
                o["confidence"], None, None, o["regime_1h"], o["fear_greed"],
                None, None, None, o["entry_fill"], None, None, None,
                None, None, t.get("price"), t.get("reason"),
                o["menge"], o["einsatz_usd"], o["nachkaeufe"],
                round(o["nachkauf_usd"], 4), None, round(geb, 4),
                pnl, t.get("pnl_pct"), r_mult,
                t.get("mfe_pct"), t.get("mae_pct"),
                minuten(o["eroeffnet_at"], ts(t)) if o["eroeffnet_at"] else None,
                None, None, None, None, None,
                o.get("notizen") or "Backfill v2 aus trades_v5.json", jetzt))

    # offene Positionen
    for coin, o in offen.items():
        zeilen.append((
            "v6_paper", o["eroeffnet_at"], None, coin, "LONG",
            o["strategie_id"], None, o["setup_name"], o["score"],
            o["confidence"], None, None, o["regime_1h"], o["fear_greed"],
            None, None, None, o["entry_fill"], None, None, None,
            None, None, None, None,
            o["menge"], o["einsatz_usd"], o["nachkaeufe"],
            round(o["nachkauf_usd"], 4), None,
            round(o.get("gebuehr_usd") or 0, 4),
            None, None, None, None, None, None,
            None, None, None, None, None,
            "OFFEN - Backfill v2", jetzt))
    return zeilen


SPALTEN = ("quelle, eroeffnet_at, geschlossen_at, symbol, richtung, "
           "strategie_id, strategie_version, setup_name, score, confidence, "
           "regime_1d, regime_4h, regime_1h, fear_greed, key_level_typ, "
           "key_level_preis, entry_geplant, entry_fill, slippage_pct, "
           "stop_initial, stop_final, tp1, tp2, exit_fill, exit_grund, "
           "menge, einsatz_usd, nachkaeufe, nachkauf_usd, spread_pct_entry, "
           "gebuehr_usd, pnl_usd, pnl_pct, r_multiple, mfe_pct, mae_pct, "
           "haltedauer_min, regeln_erfuellt, regelverstoss, decision_id, "
           "cycle_id, feature_hash, notizen, eingetragen_at")


def main():
    schreiben = "--schreiben" in sys.argv
    zeilen = baue_zeilen()
    n_spalten = len(SPALTEN.split(","))
    print(f"Quelle: {QUELLE}")
    print(f"Gebaute Zeilen: {len(zeilen)}, je {len(zeilen[0])} Werte "
          f"(Spaltenliste: {n_spalten})")
    if len(zeilen[0]) != n_spalten:
        print("ABBRUCH: Spaltenzahl passt nicht.")
        return 3
    gefuellt = {}
    namen = [s.strip() for s in SPALTEN.split(",")]
    for z in zeilen:
        for k, v in zip(namen, z):
            if v is not None:
                gefuellt[k] = gefuellt.get(k, 0) + 1
    print("\nFuellgrad der neuen Zeilen:")
    for k in namen:
        print(f"  {k:20s} {gefuellt.get(k, 0):5d} / {len(zeilen)}")

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    con = sqlite3.connect(DB)
    try:
        vorher = con.execute("select count(*) from trades_journal").fetchone()[0]
        con.execute("BEGIN")
        # Alter Backfill wird ersetzt, nicht ergaenzt - sonst Dubletten.
        con.execute("DELETE FROM trades_journal WHERE quelle='v6_paper' "
                    "AND notizen LIKE 'Backfill%'")
        platz = ",".join("?" * n_spalten)
        con.executemany(f"INSERT INTO trades_journal ({SPALTEN}) "
                        f"VALUES ({platz})", zeilen)
        nachher = con.execute("select count(*) from trades_journal").fetchone()[0]
        # Ueber eingetragen_at zaehlen, nicht ueber notizen - einzelne
        # Zeilen tragen eine abweichende Notiz (z. B. "SELL ohne
        # vorherigen BUY im Journal").
        neu = con.execute("select count(*) from trades_journal where "
                          "eingetragen_at = ?",
                          (zeilen[0][-1],)).fetchone()[0]
        if neu != len(zeilen):
            con.rollback()
            print(f"ROLLBACK: erwartet {len(zeilen)} neue, gemessen {neu}")
            return 4
        con.commit()
        print(f"\nCOMMIT. trades_journal: {vorher} -> {nachher} Zeilen")
    except Exception as ex:
        con.rollback()
        print("ROLLBACK wegen Fehler:", ex)
        return 5
    finally:
        con.close()

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    n = ro.execute("select count(*) from trades_journal").fetchone()[0]
    print("\nSELECT-Verifikation:")
    for k in ("regime_1h", "fear_greed", "score", "mfe_pct", "mae_pct",
              "gebuehr_usd", "r_multiple", "pnl_usd", "nachkaeufe"):
        v = ro.execute(f"select count({k}) from trades_journal").fetchone()[0]
        print(f"  {k:14s} {v:5d} / {n}")
    print("  Strategien:",
          ro.execute("select strategie_id, count(*) from trades_journal "
                     "group by strategie_id order by 2 desc limit 5").fetchall())
    ro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
