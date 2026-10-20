# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsdatenbank - Abfrage-Werkzeug, 30.07.2026.
"""
A6 - CLI fuer die Forschungsdatenbank. Reine Standardbibliothek.

AUFRUF (aus docs/forschungsprogramm_2026-07/code/):
    python db_frage.py                      # Hilfe + Uebersicht
    python db_frage.py status               # Programmstatus + Gates
    python db_frage.py trials [RUNDE]       # alle Trials einer Runde
    python db_frage.py confirmed            # alle CONFIRMED
    python db_frage.py trial T-024          # ein Trial im Detail
    python db_frage.py tot                  # alle toten Module
    python db_frage.py bugs                 # Module mit bekannten Bugs
    python db_frage.py luecken              # Datenquellen mit Luecken
    python db_frage.py quellen [TYP]        # Datenquellen
    python db_frage.py kosten               # Kostenszenarien
    python db_frage.py befunde              # Befunde nach Prioritaet
    python db_frage.py register             # Registerversionen
    python db_frage.py sql "SELECT ..."     # freie Leseabfrage (nur SELECT)

A5-VORRANG: Die .md-Dateien sind die verbindliche Fassung. Jede Ausgabe
nennt die Quelldatei; bei Widerspruch gilt die .md.
"""
import os
import sqlite3
import sys
import json

from db_schema import verbinde, DB


def tab(zeilen, kopf):
    if not zeilen:
        print("  (keine Treffer)")
        return
    br = [max(len(str(k)), max(len(str(z[i])) for z in zeilen))
          for i, k in enumerate(kopf)]
    br = [min(b, 62) for b in br]
    print("  " + " | ".join(str(k)[:b].ljust(b) for k, b in zip(kopf, br)))
    print("  " + "-+-".join("-" * b for b in br))
    for z in zeilen:
        print("  " + " | ".join(str(v)[:b].ljust(b)
                                for v, b in zip(z, br)))


def f(x, n=3):
    return "-" if x is None else f"{x:+.{n}f}"


def main(argv):
    if not os.path.exists(DB):
        print(f"FEHLER: {DB} fehlt. Erst 'python db_schema.py' und "
              f"'python db_fill_migration.py' ausfuehren.")
        return 1
    con = verbinde()
    cmd = argv[1] if len(argv) > 1 else ""
    arg = argv[2] if len(argv) > 2 else None

    if cmd == "status":
        print("\n PROGRAMMSTATUS")
        for r in con.execute("SELECT * FROM programm_status ORDER BY gate_nummer"):
            print(f"  Gate {r['gate_nummer']}: {r['ergebnis']} "
                  f"({r['datum']})\n    {r['begruendung']}\n"
                  f"    Verdict: {r['verdict_pfad']}")
        print("\n TRIALS NACH STATUS")
        tab([(r[0], r[1]) for r in con.execute(
            "SELECT status, COUNT(DISTINCT trial_id) FROM trials "
            "GROUP BY status ORDER BY 2 DESC")], ["Status", "Trials"])
        print("\n REGISTERVERSIONEN")
        tab([(r[0], r[1], (r[2] or "")[:16]) for r in con.execute(
            "SELECT version, datum, sha256 FROM register_versionen "
            "ORDER BY version")], ["Version", "Datum", "SHA256 (gekuerzt)"])

    elif cmd == "trials":
        w = "WHERE runde=?" if arg else ""
        p = (int(arg),) if arg else ()
        tab([(r[0], r[1], r[2] or "-", r[3] or "-", f(r[4]), r[5], r[6][:40])
             for r in con.execute(
                 "SELECT trial_id,hypothese,regel_name,asset,ev_je_runde,"
                 "status,begruendung FROM trials "
                 f"{w} AND segment='GESAMT' AND (kostenszenario='K-BASIS' "
                 "OR kostenszenario IS NULL)".replace("WHERE runde=? AND",
                                                      "WHERE runde=? AND")
                 if arg else
                 "SELECT trial_id,hypothese,regel_name,asset,ev_je_runde,"
                 "status,begruendung FROM trials WHERE segment='GESAMT' "
                 "AND (kostenszenario='K-BASIS' OR kostenszenario IS NULL) "
                 "ORDER BY trial_id", p)],
            ["Trial", "Hyp", "Regel", "Asset", "EV/Runde", "Status", "Grund"])

    elif cmd == "confirmed":
        z = [(r[0], r[1], r[2], f(r[3]), r[4]) for r in con.execute(
            "SELECT trial_id,hypothese,asset,ev_je_runde,begruendung "
            "FROM trials WHERE status='CONFIRMED' AND segment='GESAMT'")]
        tab(z, ["Trial", "Hyp", "Asset", "EV/Runde", "Grund"])
        if not z:
            print("  -> Kein einziger CONFIRMED-Trial. Gate 1 ist NEGATIV.")

    elif cmd == "trial" and arg:
        for r in con.execute(
                "SELECT * FROM trials WHERE trial_id=? ORDER BY segment,"
                "kostenszenario", (arg,)):
            print(f"\n  {r['trial_id']} | {r['hypothese']} | "
                  f"{r['asset'] or '-'} | Segment {r['segment']} | "
                  f"{r['kostenszenario'] or '-'}")
            print(f"    EV/Runde {f(r['ev_je_runde'])}  "
                  f"KI [{f(r['ki_unten'])} ; {f(r['ki_oben'])}]  "
                  f"Placebo {f(r['placebo_perzentil'],1)}  p={f(r['p_wert'],4)}")
            print(f"    Status {r['status']} | {r['begruendung']}")
            print(f"    Regel: {r['regel_name'] or '-'}")
            print(f"    Quelle: {r['literatur_quelle'] or '-'}")
            print(f"    Roh: {r['pfad_rohausgabe'] or '-'} | md: {r['quelle_md']}")

    elif cmd == "tot":
        z = [(r[0], r[1], (r[2] or "")[:58]) for r in con.execute(
            "SELECT pfad,zeilen,zweck FROM bot_architektur "
            "WHERE status='TOT' ORDER BY zeilen DESC")]
        tab(z, ["Pfad", "Zeilen", "Zweck"])
        ges = con.execute("SELECT COUNT(*), SUM(zeilen) FROM bot_architektur "
                          "WHERE status='TOT'").fetchone()
        alle = con.execute("SELECT COUNT(*) FROM bot_architektur").fetchone()[0]
        print(f"\n  {ges[0]} von {alle} Modulen tot "
              f"({ges[0]/alle*100:.0f} %), {ges[1]} Zeilen.")
        print("  TOT = von keinem Projektmodul importiert und kein "
              "Einstiegspunkt (AST-Importgraph ab app.py).")

    elif cmd == "bugs":
        for r in con.execute(
                "SELECT pfad,status,bekannte_bugs FROM bot_architektur "
                "WHERE bekannte_bugs != '[]' ORDER BY pfad"):
            print(f"\n  {r['pfad']}  [{r['status']}]")
            for b in json.loads(r["bekannte_bugs"]):
                print(f"    - {b}")

    elif cmd == "luecken":
        gefunden = False
        for r in con.execute(
                "SELECT name,typ,anzahl_zeilen,luecken FROM datenquellen "
                "ORDER BY name"):
            lk = json.loads(r["luecken"] or "[]")
            if lk:
                gefunden = True
                print(f"  {r['name']:<28s} {r['anzahl_zeilen']:6d} Zeilen, "
                      f"{len(lk)} Luecke(n): {lk[:3]}")
        if not gefunden:
            print("  Keine Luecken in 28 Datenquellen "
                  "(Toleranz 60 s auf das Sollintervall).")

    elif cmd == "quellen":
        w, p = ("WHERE typ=?", (arg,)) if arg else ("", ())
        tab([(r[0], r[1], r[2] or "-", r[3], r[4], r[5], r[6]) for r in
             con.execute("SELECT name,typ,coin,intervall,erster_datenpunkt,"
                         f"letzter_datenpunkt,anzahl_zeilen FROM datenquellen "
                         f"{w} ORDER BY typ,name", p)],
            ["Datei", "Typ", "Coin", "Iv", "von", "bis", "Zeilen"])

    elif cmd == "kosten":
        tab([(r[0], f(r[1], 3), f(r[2], 3), f(r[3], 3), f(r[4], 3), r[5], r[6][:40])
             for r in con.execute(
                 "SELECT name,maker_pct,taker_pct,slippage_pct,roundtrip_pct,"
                 "konfidenz,quelle FROM kostenszenarien ORDER BY roundtrip_pct")],
            ["Szenario", "Maker%", "Taker%", "Slip%", "Runde%", "Konfidenz", "Quelle"])

    elif cmd == "befunde":
        for r in con.execute(
                "SELECT prioritaet,kurztext,langtext,konfidenz,risiko_0_10,"
                "impact_0_10,trial_bezug FROM befunde ORDER BY "
                "CASE prioritaet WHEN 'KRITISCH' THEN 1 WHEN 'HOCH' THEN 2 "
                "WHEN 'MITTEL' THEN 3 ELSE 4 END, impact_0_10 DESC"):
            print(f"\n  [{r['prioritaet']}] {r['kurztext']}  "
                  f"[{r['konfidenz']}] R{r['risiko_0_10']}/I{r['impact_0_10']}"
                  f"  {r['trial_bezug'] or ''}")
            print(f"    {r['langtext']}")

    elif cmd == "register":
        for r in con.execute("SELECT * FROM register_versionen ORDER BY version"):
            print(f"\n  {r['version']}  {r['datum']}  {r['sha256'][:32]}...")
            print(f"    {r['aenderung']}")
            print(f"    {r['quelle_md']}")

    elif cmd == "sql" and arg:
        if not arg.strip().lower().startswith("select"):
            print("  Nur SELECT erlaubt (Leseabfrage).")
            return 1
        try:
            cur = con.execute(arg)
            tab([tuple(r) for r in cur.fetchall()],
                [d[0] for d in cur.description])
        except sqlite3.Error as e:
            print(f"  SQL-Fehler: {e}")
            return 1

    else:
        print(__doc__)
        print("  BESTAND:")
        for t in ("trials", "datenquellen", "kostenszenarien", "befunde",
                  "register_versionen", "programm_status", "bot_architektur"):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"    {t:<20s} {n:5d}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
