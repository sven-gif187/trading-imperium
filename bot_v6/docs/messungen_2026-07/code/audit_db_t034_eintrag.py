# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Eintrag der Nachtragsmessung T-034..T-041 in forschung.db.
"""
Traegt die 48 Zeilen aus messung_t034b_zwischenstand.jsonl in
docs/forschungsprogramm_2026-07/forschung.db, Tabelle trials, ein.

STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

TABELLENWAHL: trials ist die einzige Tabelle mit Trial-ID, Segment,
KI-Grenzen, Placebo-Perzentil, p-Wert, FDR-Spalte und Status-CHECK. Sie
ist eindeutig geeignet. Keine Schemaaenderung, kein neuer Index, kein
Trigger, keine neue Spalte.

ID-KOLLISION - BEWUSST NICHT AUFGELOEST:
  zeile_id 83 T-034 runde=2 VORREGISTRIERT "Runde 2, Reserve"
  zeile_id 84 T-035 runde=2 VORREGISTRIERT "Runde 2, Reserve"
Diese beiden Zeilen bleiben unveraendert. Die Nachtragsmessung wird mit
runde=0 eingetragen (0 ist im Bestand bereits fuer 15 Nicht-Runden-Zeilen
belegt) und ist damit von den Runde-2-Platzhaltern unterscheidbar. Ob die
Trial-IDs T-034..T-041 doppelt vergeben bleiben duerfen, ist eine
Registerfrage und wird NICHT vom Skript entschieden.

FELDBELEGUNG - Konvention, damit nichts stillschweigend umgedeutet wird:
  ev_je_runde   = P(auf) - Kostenschwelle in Prozentpunkten. Gleiche
                  Richtungssemantik wie EV (>0 = traegt), aber KEIN
                  Geldbetrag. Der rohe P(auf) steht in parameter und
                  begruendung.
  ki_unten/oben = Bootstrap-KI von P(auf), ebenfalls um die
                  Kostenschwelle verschoben.
  parameter     = JSON mit allen Rohwerten (n, q, lo, hi, plc, p95,
                  p_be, zens, sig, tage, q_ohne_lookahead).
  p_wert_fdr    = Benjamini-Hochberg-adjustierter q-Wert ueber alle
                  m=48 Tests, monoton von unten.
"""
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HIER, "..", "ausgaben",
                     "messung_t034b_zwischenstand.jsonl")
SKRIPT = os.path.join(HIER, "messung_t034b_strategien.py")
DB = os.path.join(HIER, "..", "..", "forschungsprogramm_2026-07",
                  "forschung.db")
ROH = "docs/messungen_2026-07/ausgaben/messung_t034b_strategien_out.txt"
QUELLE = "docs/messungen_2026-07/audit_multistrategy_block_1.md"

ZEITRAUM = {"J2": "2025-07-29..2026-07-29", "J1": "2024-07-29..2025-07-29"}
REGEL = {
    "RSI_OVERSOLD": "RSI-Oversold-Bounce (agents/v4_strategies.py:88-96)",
    "EMA_TREND": "EMA Triple Trend (agents/v4_strategies.py:102-111)",
    "MACD_CROSS": "MACD Crossover (agents/v4_strategies.py:113-125)",
    "TSI": "True Strength Index (agents/v4_strategies.py:161-171)",
    "BOLLINGER_BOUNCE": "Bollinger-Unterschreitung + RSI<40 "
                        "(agents/signal_agent.py:110-115)",
    "FIBONACCI_SUPPORT": "Fibonacci-Support 78,6/61,8/38,2 "
                         "(agents/v4_strategies.py:176-190)",
    "RSI_DIVERGENZ": "Bullische RSI-Divergenz "
                     "(features/rsi_divergence.py:67-90)",
    "MULTI_SIGNAL": "Additiver Score >= 3 (agents/signal_agent.py:78-169)",
}


def bh_adjustiert(ps):
    """Benjamini-Hochberg-q-Werte, monoton von unten."""
    m = len(ps)
    idx = sorted(range(m), key=lambda i: ps[i])
    q = [0.0] * m
    vorher = 1.0
    for rang in range(m - 1, -1, -1):
        i = idx[rang]
        w = min(1.0, ps[i] * m / (rang + 1))
        vorher = min(vorher, w)
        q[i] = vorher
    return q


def main():
    schreiben = "--schreiben" in sys.argv
    if not os.path.isfile(JSONL):
        print("FEHLER: Zwischenstand fehlt:", JSONL)
        return 2
    zeilen = []
    with open(JSONL, encoding="utf-8") as f:
        for z in f:
            z = z.strip()
            if z:
                zeilen.append(json.loads(z))
    print(f"Zwischenstand: {len(zeilen)} Zeilen")
    if len(zeilen) != 48:
        print(f"ABBRUCH: erwartet 48 Zeilen, gefunden {len(zeilen)}. "
              f"Die Messung ist unvollstaendig - kein Eintrag.")
        return 3

    sha = hashlib.sha256(open(SKRIPT, "rb").read()).hexdigest()
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # p-Werte wie im Messskript (Normalapproximation des Bootstrap-KI)
    import math
    for e in zeilen:
        sd = (e["hi"] - e["lo"]) / 3.92 if e["hi"] > e["lo"] else 1.0
        z = (e["q"] - e["p_be"]) / sd if sd > 0 else 0.0
        e["p"] = 0.5 * math.erfc(z / math.sqrt(2))
    qs = bh_adjustiert([e["p"] for e in zeilen])
    for e, qq in zip(zeilen, qs):
        e["q_fdr"] = qq

    saetze = []
    for e in zeilen:
        vier = []
        if e["q"] <= e["p_be"]:
            vier.append("Punktschaetzer unter Kostenschwelle")
        if e["lo"] <= e["p_be"]:
            vier.append("KI-Untergrenze unter Kostenschwelle")
        if e["q"] <= e["p95"]:
            vier.append("Placebo nicht geschlagen")
        begr = (f"P(auf)={e['q']:.2f}% (n={e['n']}), "
                f"KI[{e['lo']:.2f};{e['hi']:.2f}], "
                f"Kostenschwelle {e['p_be']:.2f}%, "
                f"Abstand {e['q']-e['p_be']:+.2f}pp, "
                f"Placebo-Mittel {e['plc']:.2f}%/95.Perz {e['p95']:.2f}%. "
                f"FAIL: " + "; ".join(vier) + ". "
                f"NACHTRAGSMESSUNG zum Multi-Strategy-Bug, keine Runde 3.")
        saetze.append((
            e["trial"], 0, "MS-NACHTRAG", REGEL[e["name"]],
            "keine - Rekonstruktion der Projektimplementierung, "
            "kein Literaturtest",
            json.dumps(dict(strategie=e["name"], jahr=e["jahr"],
                            barriere=e["kombi"], n=e["n"], signale=e["sig"],
                            p_auf=round(e["q"], 4),
                            ki=[round(e["lo"], 4), round(e["hi"], 4)],
                            placebo_mittel=round(e["plc"], 4),
                            placebo_p95=round(e["p95"], 4),
                            kostenschwelle=round(e["p_be"], 4),
                            zensierung_pct=round(e["zens"], 4),
                            kalendertage=e["tage"],
                            p_auf_ohne_lookahead=round(e["q_la"], 4)),
                       ensure_ascii=False),
            "11er-Portfolio USDC", ZEITRAUM[e["jahr"]], "GESAMT", "K-BASIS",
            round(e["q"] - e["p_be"], 4),
            round(e["lo"] - e["p_be"], 4), round(e["hi"] - e["p_be"], 4),
            round(e["p95"], 4), round(e["p"], 6), round(e["q_fdr"], 6),
            "REJECTED", begr, jetzt, ROH, sha, QUELLE))

    print(f"Vorbereitet: {len(saetze)} INSERT-Saetze, alle status=REJECTED, "
          f"runde=0, segment=GESAMT")
    print(f"Skript-SHA256: {sha}")
    print("\nBeispielsatz (erster):")
    for k, v in zip(("trial_id", "runde", "hypothese", "regel_name",
                     "literatur_quelle", "parameter", "asset",
                     "datenzeitraum", "segment", "kostenszenario",
                     "ev_je_runde", "ki_unten", "ki_oben",
                     "placebo_perzentil", "p_wert", "p_wert_fdr", "status",
                     "begruendung", "zeitstempel", "pfad_rohausgabe",
                     "skript_sha256", "quelle_md"), saetze[0]):
        print(f"  {k:18s} {str(v)[:110]}")

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    con = sqlite3.connect(DB)
    try:
        vorher = con.execute("select count(*) from trials").fetchone()[0]
        con.execute("BEGIN")
        con.executemany(
            "INSERT INTO trials (trial_id,runde,hypothese,regel_name,"
            "literatur_quelle,parameter,asset,datenzeitraum,segment,"
            "kostenszenario,ev_je_runde,ki_unten,ki_oben,placebo_perzentil,"
            "p_wert,p_wert_fdr,status,begruendung,zeitstempel,"
            "pfad_rohausgabe,skript_sha256,quelle_md) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", saetze)
        nachher = con.execute("select count(*) from trials").fetchone()[0]
        neu = con.execute(
            "select count(*) from trials where hypothese='MS-NACHTRAG' "
            "and zeitstempel=?", (jetzt,)).fetchone()[0]
        if nachher - vorher != len(saetze) or neu != len(saetze):
            con.rollback()
            print(f"ROLLBACK: erwartet +{len(saetze)}, "
                  f"gemessen +{nachher-vorher} (neu={neu})")
            return 4
        con.commit()
        print(f"\nCOMMIT. trials: {vorher} -> {nachher} Zeilen")
    except Exception as ex:
        con.rollback()
        print("ROLLBACK wegen Fehler:", ex)
        return 5
    finally:
        con.close()

    # Verifikation in getrennter, nur lesender Verbindung
    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    n = ro.execute("select count(*) from trials where hypothese="
                   "'MS-NACHTRAG'").fetchone()[0]
    print(f"SELECT-Verifikation: {n} Zeilen mit hypothese='MS-NACHTRAG'")
    for r in ro.execute(
            "select trial_id, datenzeitraum, ev_je_runde, status from trials "
            "where hypothese='MS-NACHTRAG' order by ev_je_runde desc limit 3"):
        print("   ", r)
    ro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
