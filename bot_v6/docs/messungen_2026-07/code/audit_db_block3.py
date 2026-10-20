# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] DB-Teil der Freigaben 3.5 und 3.6 vom 04.08.2026.
"""
STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

3.5  TRIAL-ID-KOLLISION AUFLOESEN
     zeile_id 83/84 belegen T-034 und T-035 seit 31.07. als
     runde=2, VORREGISTRIERT, "Runde 2, Reserve". Die Nachtragsmessung
     vom 04.08. liegt mit runde=0 unter denselben IDs daneben.
     AUFLOESUNG: Die 48 Nachtragszeilen (hypothese='MS-NACHTRAG')
     bekommen das Suffix N -> T-034N .. T-041N. Damit hat jede ID genau
     eine Bedeutung. Die aelteren Vorregistrierungen bleiben unberuehrt -
     sie sind die im Register etablierte Vergabe, die Nachtragsmessung ist
     ausdruecklich "keine Runde 3" und gehoert nicht in die T-Serie der
     Runden.

3.6  LOOK-AHEAD-KORREKTURVERMERK
     Ein Befund in Tabelle 'befunde'. Der 45-Minuten-Look-ahead in
     zu_1h() betrifft E2 und G2 rueckwirkend. Verzerrung bis 4,77 pp,
     Richtung durchweg negativ - die Urteile werden bestaetigt, nicht
     entwertet.

Kein Schema geaendert, keine Tabelle/Spalte/Trigger/View/Index angelegt.
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "..", "..", "forschungsprogramm_2026-07",
                  "forschung.db")
QUELLE = "docs/messungen_2026-07/audit_v4_v6_block3.md"

LANGTEXT = (
    "messung_f2_ic.py:57-70 zu_1h() vergibt als Zeitstempel den "
    "STUNDENBEGINN H, als Preis aber den Close am STUNDENENDE H+60min. "
    "rennen() startet bei bisect_right(zeiten, H), also bei H+15min - die "
    "Viertelstunden H+15, H+30 und H+45 werden mitgerennt, obwohl der "
    "Signalpreis dort noch nicht bekannt ist. 45 Minuten Look-ahead. "
    "Betroffen sind alle Messungen auf dieser Zeitachse, also E2, G2 und "
    "die Nachtragsmessung T-034N..T-041N. GEMESSEN am Sensitivitaetslauf "
    "mit Start bei H+60min (messung_t034b_strategien.py, Spalte q_la): "
    "groesster Verzerrungsbetrag 4,77 pp (BOLLINGER_BOUNCE J1 "
    "+/-2,5%/72h: 49,33 % -> 44,56 %), Richtung der grossen Abweichungen "
    "durchweg NEGATIV. Der Look-ahead hat P(auf) also systematisch "
    "UEBERSCHAETZT. Ohne ihn fallen die Ergebnisse schlechter aus, nicht "
    "besser. Die negativen Urteile zu E2, G2 und zur Nachtragsmessung "
    "werden dadurch BESTAETIGT, nicht entwertet. Eine Neurechnung von E2 "
    "und G2 ist zur Absicherung der Urteile nicht erforderlich; sie waere "
    "nur noetig, wenn aus diesen Messungen ein POSITIVES Ergebnis "
    "abgeleitet werden sollte."
)


def main():
    schreiben = "--schreiben" in sys.argv
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    n_nachtrag = ro.execute(
        "select count(*) from trials where hypothese='MS-NACHTRAG'"
    ).fetchone()[0]
    n_kollision = ro.execute(
        "select count(*) from trials where trial_id in "
        "('T-034','T-035') and runde=2").fetchone()[0]
    ids = ro.execute(
        "select distinct trial_id from trials where hypothese='MS-NACHTRAG' "
        "order by trial_id").fetchall()
    n_befunde = ro.execute("select count(*) from befunde").fetchone()[0]
    schon_da = ro.execute(
        "select count(*) from befunde where kurztext like '%Look-ahead%'"
    ).fetchone()[0]
    ro.close()

    print("=" * 92)
    print(" 3.5  Trial-ID-Kollision")
    print("=" * 92)
    print(f"  Nachtragszeilen (hypothese='MS-NACHTRAG'): {n_nachtrag}")
    print(f"  IDs bisher: {[i[0] for i in ids]}")
    print(f"  Kollidierende Runde-2-Vorregistrierungen:  {n_kollision} "
          f"(T-034, T-035 - bleiben unberuehrt)")
    print(f"  Neue IDs:   {[i[0] + 'N' for i in ids]}")
    print("\n" + "=" * 92)
    print(" 3.6  Look-ahead-Korrekturvermerk")
    print("=" * 92)
    print(f"  Tabelle befunde: {n_befunde} Zeilen")
    print(f"  Bereits vorhandener Look-ahead-Befund: {schon_da}")
    if schon_da:
        print("  -> Es existiert bereits ein Eintrag. Kein zweiter.")

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    con = sqlite3.connect(DB)
    try:
        con.execute("BEGIN")
        # --- 3.5 ---
        cur = con.execute(
            "UPDATE trials SET trial_id = trial_id || 'N' "
            "WHERE hypothese='MS-NACHTRAG' AND trial_id NOT LIKE '%N'")
        geaendert = cur.rowcount
        # --- 3.6 ---
        eingefuegt = 0
        if not schon_da:
            con.execute(
                "INSERT INTO befunde (runde, kurztext, langtext, konfidenz, "
                "risiko_0_10, impact_0_10, prioritaet, trial_bezug, "
                "zeitstempel, quelle_md) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (0,
                 "45 Minuten Look-ahead in zu_1h() - betrifft E2, G2 und "
                 "T-034N..T-041N rueckwirkend",
                 LANGTEXT, "SICHER", 4, 5, "HOCH",
                 "E2, G2, T-034N..T-041N", jetzt, QUELLE))
            eingefuegt = 1
        # Verifikation im selben Transaktionsfenster
        rest = con.execute(
            "select count(*) from trials where hypothese='MS-NACHTRAG' "
            "and trial_id not like '%N'").fetchone()[0]
        doppelt = con.execute(
            "select count(*) from trials where trial_id in "
            "('T-034','T-035') group by trial_id").fetchall()
        if rest != 0 or geaendert != n_nachtrag:
            con.rollback()
            print(f"\nROLLBACK: erwartet {n_nachtrag} Aenderungen, "
                  f"gemessen {geaendert}, Rest ohne Suffix {rest}")
            return 4
        con.commit()
        print(f"\nCOMMIT. trials umbenannt: {geaendert} Zeilen. "
              f"befunde eingefuegt: {eingefuegt}")
    except Exception as ex:
        con.rollback()
        print("ROLLBACK wegen Fehler:", ex)
        return 5
    finally:
        con.close()

    ro = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                         uri=True)
    print("\nSELECT-Verifikation:")
    for tid, r, n in ro.execute(
            "select trial_id, runde, count(*) from trials where trial_id "
            "like 'T-03%' or trial_id like 'T-04%' group by trial_id, runde "
            "order by trial_id"):
        print(f"    {tid:<9s} runde={r} {n:3d} Zeilen")
    print(f"  befunde gesamt: "
          f"{ro.execute('select count(*) from befunde').fetchone()[0]}")
    for r in ro.execute("select befund_id, kurztext from befunde where "
                        "kurztext like '%Look-ahead%'"):
        print(f"    Befund {r[0]}: {r[1][:70]}")
    ro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
