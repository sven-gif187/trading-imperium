# -*- coding: utf-8 -*-
"""Exportiert ALLE gemessenen Daten in eine Excel-Mappe.

Zusammengefuehrt werden saemtliche Quellen, die im Projekt Messwerte fuehren:

    data_store/trades_v5.json     Handelsjournal (Kaeufe, Verkaeufe, MFE/MAE)
    data_store/telemetrie.db      Kaufpruefungen, Blockgruende, Chartanalyse,
                                  Schatten-Exits
    docs/.../capture/             Live-Spreads der Boerse (Forschungs-Capture)
    data_store/bot_state.json     aktueller Zustand

Ergebnis: eine .xlsx mit einem Blatt je Thema. Ist openpyxl nicht vorhanden,
werden stattdessen CSV-Dateien in einen Ordner geschrieben - inhaltlich
identisch, nur ohne Formatierung.

Aufruf:  python datenexport.py
"""
import csv
import glob
import gzip
import io
import json
import os
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HIER, "data_store")
CAP = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
ZIEL_XLSX = os.path.join(HIER, f"BOT-DATEN_{STAMP}.xlsx")
ZIEL_CSV = os.path.join(HIER, f"BOT-DATEN_{STAMP}")

# [13.09.2026] Die Zahl steht jetzt an EINER Stelle: core/kosten.py.
# Hier stand 0.32 % - die alte Annahme aus der Zeit vor Bybit EU.
# Neun Dateien mit neun eigenen Kostenzahlen waren neun Gelegenheiten,
# eine davon zu vergessen; genau das war passiert. Diese Datei rechnet
# nur aus und handelt nicht - die Umstellung ist deshalb
# freeze-vertraeglich.
from core.kosten import K_BASIS_PCT
KOSTEN_PCT = K_BASIS_PCT


def lade_json(pfad, standard):
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return standard


def db():
    p = os.path.join(DS, "telemetrie.db")
    if not os.path.exists(p):
        return None
    try:
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    except Exception:
        return None


# ==================================================================
# Blaetter aufbauen - jedes liefert (Titel, Kopfzeile, Zeilen)
# ==================================================================
def blatt_uebersicht(trades, con):
    k = ["Kennzahl", "Wert", "Quelle"]
    z = []
    verk = [t for t in trades if str(t.get("type")).upper() == "SELL"
            and isinstance(t.get("pnl"), (int, float))]
    pnl = [float(t["pnl"]) for t in verk]
    gew = [x for x in pnl if x > 0]
    z.append(["Erstellt am", datetime.now().strftime("%d.%m.%Y %H:%M"), ""])
    z.append(["Journal-Eintraege", len(trades), "trades_v5.json"])
    z.append(["davon Verkaeufe mit P&L", len(verk), "trades_v5.json"])
    if verk:
        z.append(["Zeitraum von", str(trades[0].get("time"))[:10], ""])
        z.append(["Zeitraum bis", str(trades[-1].get("time"))[:10], ""])
        z.append(["Trefferquote %", round(len(gew) / len(verk) * 100, 2), ""])
        z.append(["P&L gesamt $", round(sum(pnl), 2), ""])
        z.append(["P&L je Verkauf $", round(sum(pnl) / len(verk), 4), ""])
        z.append(["groesster Gewinn $", round(max(pnl), 2), ""])
        z.append(["groesster Verlust $", round(min(pnl), 2), ""])
        z.append(["Gebuehren gesamt $",
                  round(sum(float(t.get("fee") or 0) for t in trades), 2), ""])
    if con:
        r = con.execute("SELECT COUNT(*), SUM(decision='APPROVED') "
                        "FROM evaluations").fetchone()
        z.append(["Kaufpruefungen", r[0], "telemetrie.db"])
        z.append(["davon genehmigt", r[1] or 0, "telemetrie.db"])
        for tab, name in (("chart_signale", "Chartanalyse-Signale"),
                          ("schatten_exits", "Schatten-Exits")):
            try:
                n = con.execute(f"SELECT COUNT(*) FROM {tab}").fetchone()[0]
                z.append([name, n, "telemetrie.db"])
            except Exception:
                pass
    z.append(["Handelskosten je Runde %", KOSTEN_PCT, "kosten_matrix_v4"])
    return "Uebersicht", k, z


def blatt_trades(trades):
    k = ["Zeit", "Typ", "Coin", "Menge", "Preis", "Betrag", "PnL_USD",
         "PnL_Prozent", "Gebuehr", "Strategie", "Score", "MFE_Prozent",
         "MAE_Prozent", "Haltedauer_Min", "PositionID", "Grund"]
    z = []
    for t in trades:
        z.append([
            str(t.get("time", ""))[:19].replace("T", " "),
            t.get("type", ""), t.get("coin", ""),
            t.get("qty"), t.get("price"), t.get("amount"),
            t.get("pnl"), t.get("pnl_pct"), t.get("fee"),
            t.get("strategy", ""),
            t.get("entry_score", t.get("score")),
            t.get("mfe_pct"), t.get("mae_pct"), t.get("haltedauer_min"),
            t.get("position_id", ""),
            str(t.get("reason", ""))[:200],
        ])
    return "Trades", k, z


def blatt_je_coin(trades):
    k = ["Coin", "Kaeufe", "Verkaeufe", "Trefferquote_Prozent", "PnL_USD",
         "PnL_je_Verkauf", "Gebuehren_USD", "Volumen_USD", "letzter_Trade"]
    d = defaultdict(lambda: {"k": 0, "v": 0, "pnl": 0.0, "g": 0, "fee": 0.0,
                             "vol": 0.0, "letzt": ""})
    for t in trades:
        c = str(t.get("coin", "")).split("/")[0]
        if not c:
            continue
        x = d[c]
        x["fee"] += float(t.get("fee") or 0)
        x["vol"] += float(t.get("amount") or 0)
        zt = str(t.get("time", ""))[:10]
        if zt > x["letzt"]:
            x["letzt"] = zt
        if str(t.get("type")).upper() == "BUY":
            x["k"] += 1
        elif str(t.get("type")).upper() == "SELL":
            x["v"] += 1
            p = t.get("pnl")
            if isinstance(p, (int, float)):
                x["pnl"] += p
                if p > 0:
                    x["g"] += 1
    z = []
    for c, x in sorted(d.items(), key=lambda i: -i[1]["pnl"]):
        z.append([c, x["k"], x["v"],
                  round(x["g"] / x["v"] * 100, 2) if x["v"] else 0,
                  round(x["pnl"], 2),
                  round(x["pnl"] / x["v"], 4) if x["v"] else 0,
                  round(x["fee"], 2), round(x["vol"], 2), x["letzt"]])
    return "Je Coin", k, z


def blatt_ausstiege(trades):
    k = ["Ausstiegsgrund", "Faelle", "Trefferquote_Prozent", "PnL_USD",
         "PnL_je_Trade", "bester", "schlechtester"]
    d = defaultdict(list)
    for t in trades:
        if str(t.get("type")).upper() != "SELL":
            continue
        p = t.get("pnl")
        if isinstance(p, (int, float)):
            d[str(t.get("strategy") or "unbekannt")].append(float(p))
    z = []
    for s, p in sorted(d.items(), key=lambda i: -sum(i[1])):
        gew = sum(1 for x in p if x > 0)
        z.append([s, len(p), round(gew / len(p) * 100, 2), round(sum(p), 2),
                  round(sum(p) / len(p), 4), round(max(p), 2), round(min(p), 2)])
    return "Ausstiegsgruende", k, z


def blatt_monate(trades):
    k = ["Monat", "Verkaeufe", "Trefferquote_Prozent", "PnL_USD", "PnL_je_Verkauf"]
    d = defaultdict(list)
    for t in trades:
        if str(t.get("type")).upper() != "SELL":
            continue
        p = t.get("pnl")
        if isinstance(p, (int, float)):
            d[str(t.get("time", ""))[:7]].append(float(p))
    z = []
    for m in sorted(d):
        p = d[m]
        gew = sum(1 for x in p if x > 0)
        z.append([m, len(p), round(gew / len(p) * 100, 2), round(sum(p), 2),
                  round(sum(p) / len(p), 4)])
    return "Monate", k, z


def blatt_blockgruende(con):
    if not con:
        return None
    k = ["Blockgrund", "Faelle", "Anteil_Prozent"]
    ges = con.execute("SELECT COUNT(*) FROM evaluations "
                      "WHERE decision='REJECTED'").fetchone()[0] or 1
    z = [[r[0], r[1], round(r[1] / ges * 100, 2)] for r in con.execute(
        "SELECT rule_name, COUNT(DISTINCT evaluation_id) FROM rule_evaluations "
        "WHERE result='BLOCK' GROUP BY rule_name ORDER BY 2 DESC")]
    return "Blockgruende", k, z


def blatt_chartanalyse(con):
    if not con:
        return None
    k = ["Zeitrahmen", "Signalart", "Faelle", "Trefferquote_Prozent",
         "EV_brutto_Prozent", "EV_netto_Prozent"]
    z = [[r[0], r[1], r[2], round(r[3], 2), round(r[4], 4), round(r[5], 4)]
         for r in con.execute(
            "SELECT timeframe, signal, COUNT(*), "
            "100.0*SUM(ergebnis='ZIEL')/COUNT(*), AVG(rendite_pct), "
            "AVG(rendite_netto) FROM chart_signale GROUP BY timeframe, signal "
            "ORDER BY AVG(rendite_netto) DESC")]
    return "Chartanalyse", k, z


def blatt_schatten(con):
    if not con:
        return None
    try:
        k = ["Zeit", "PositionID", "Coin", "Regel", "PnL_Prozent",
             "Hoechststand_Prozent", "Preis", "Einstand", "Score", "Grund"]
        z = [[r[0][:19].replace("T", " "), r[1], r[2], r[3], r[4], r[5],
              r[6], r[7], r[8], r[9]] for r in con.execute(
            "SELECT ts_utc,position_id,symbol,regel,pnl_pct,hoechst_pnl_pct,"
            "preis,entry_price,entry_score,grund FROM schatten_exits "
            "ORDER BY ts_utc DESC")]
        return "Schatten-Exits", k, z
    except Exception:
        return None


def blatt_spreads():
    """Forschungs-Capture: Median-Spread je Coin ueber alle Tage."""
    tage = sorted(d for d in glob.glob(os.path.join(CAP, "20*"))
                  if os.path.isdir(d))
    if not tage:
        return None
    werte = defaultdict(list)
    for tag in tage:
        for p in glob.glob(os.path.join(tag, "ticker_*.csv.gz")):
            sym = os.path.basename(p)[len("ticker_"):-len(".csv.gz")]
            try:
                txt = gzip.open(p, "rt", encoding="utf-8").read()
                sp = [float(r["spread_bp"]) for r in
                      csv.DictReader(io.StringIO(txt)) if r.get("spread_bp")]
                if len(sp) >= 30:
                    werte[sym].extend(sp)
            except Exception:
                continue
    if not werte:
        return None
    k = ["Coin", "Messpunkte", "Median_bp", "p90_bp", "Slippage_je_Seite_Prozent",
         "K_BASIS_Prozent", "Breakeven_Quote_bei_5Prozent"]
    z = []
    for sym in sorted(werte, key=lambda s: st.median(werte[s])):
        w = werte[sym]
        med = st.median(w)
        q = st.quantiles(w, n=100)
        slip = med / 2 / 100
        kb = 2 * 0.25 + 2 * slip
        z.append([sym, len(w), round(med, 4), round(q[89], 4),
                  round(slip, 5), round(kb, 4),
                  round((0.5 + kb / (2 * 5.0)) * 100, 2)])
    return "Spreads (Capture)", k, z


def blatt_positionen():
    s = lade_json(os.path.join(DS, "bot_state.json"), {})
    pos = s.get("open_positions_backup") or {}
    k = ["Coin", "Menge", "Einstand", "Hoechstkurs", "Kostenbasis",
         "DCA_Stufe", "PositionID", "Topf", "Score"]
    z = []
    for sym, p in pos.items():
        if isinstance(p, dict):
            z.append([sym, p.get("qty"), p.get("entry_price"),
                      p.get("highest_price"), p.get("cost_basis"),
                      p.get("dca_levels"), p.get("position_id", ""),
                      p.get("topf", ""), p.get("entry_score")])
    return "Offene Positionen", k, z


# ==================================================================
def schreibe_xlsx(blaetter):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    kopf_fill = PatternFill("solid", fgColor="1F3864")
    kopf_font = Font(color="FFFFFF", bold=True)

    for titel, kopf, zeilen in blaetter:
        ws = wb.create_sheet(titel[:31])
        ws.append(kopf)
        for c in range(1, len(kopf) + 1):
            z = ws.cell(row=1, column=c)
            z.fill = kopf_fill
            z.font = kopf_font
            z.alignment = Alignment(horizontal="center")
        for r in zeilen:
            ws.append(r)
        ws.freeze_panes = "A2"
        if zeilen:
            ws.auto_filter.ref = (f"A1:{get_column_letter(len(kopf))}"
                                  f"{len(zeilen) + 1}")
        for c in range(1, len(kopf) + 1):
            breit = len(str(kopf[c - 1]))
            for r in zeilen[:200]:
                if c - 1 < len(r) and r[c - 1] is not None:
                    breit = max(breit, len(str(r[c - 1])))
            ws.column_dimensions[get_column_letter(c)].width = min(breit + 3, 55)
    wb.save(ZIEL_XLSX)
    return ZIEL_XLSX


def schreibe_csv(blaetter):
    os.makedirs(ZIEL_CSV, exist_ok=True)
    for titel, kopf, zeilen in blaetter:
        name = titel.replace(" ", "_").replace("(", "").replace(")", "")
        with open(os.path.join(ZIEL_CSV, f"{name}.csv"), "w",
                  newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(kopf)
            w.writerows(zeilen)
    return ZIEL_CSV


def main():
    trades = lade_json(os.path.join(DS, "trades_v5.json"), [])
    if not isinstance(trades, list):
        trades = []
    con = db()

    print("=" * 74)
    print(" DATENEXPORT - alle gemessenen Daten in eine Datei")
    print("=" * 74)

    roh = [blatt_uebersicht(trades, con), blatt_trades(trades),
           blatt_je_coin(trades), blatt_ausstiege(trades), blatt_monate(trades),
           blatt_blockgruende(con), blatt_chartanalyse(con), blatt_schatten(con),
           blatt_spreads(), blatt_positionen()]
    blaetter = [b for b in roh if b and b[2]]

    print()
    for titel, kopf, zeilen in blaetter:
        print(f"  {titel:<22s} {len(zeilen):7d} Zeilen, {len(kopf)} Spalten")
    leer = [b[0] for b in roh if b and not b[2]]
    if leer:
        print(f"\n  Ohne Daten (uebersprungen): {', '.join(leer)}")

    if con:
        con.close()

    try:
        pfad = schreibe_xlsx(blaetter)
        print(f"\n  FERTIG: {pfad}")
        print(f"  {len(blaetter)} Tabellenblaetter, Filter und fixierte Kopfzeile.")
    except ImportError:
        pfad = schreibe_csv(blaetter)
        print(f"\n  openpyxl fehlt - stattdessen CSV geschrieben:")
        print(f"  {pfad}")
        print(f"  Fuer Excel-Ausgabe:  pip install openpyxl")
    except Exception as e:
        pfad = schreibe_csv(blaetter)
        print(f"\n  Excel fehlgeschlagen ({type(e).__name__}: {e})")
        print(f"  CSV geschrieben: {pfad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
