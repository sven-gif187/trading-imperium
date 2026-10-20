# -*- coding: utf-8 -*-
"""Prueft, ob die neuen Telemetrie-Felder im echten Betrieb ankommen.

Aufruf:  python telemetrie_pruefen.py

WOFUER
------
Schritt 3 hat 20 Spalten und eine Tabelle ergaenzt. Ob sie tatsaechlich
befuellt werden, zeigt sich erst im Betrieb - eine Spalte, die zwei
Wochen lang unbemerkt NULL bleibt, ist genau der Fehler, den das
Messfenster nicht ueberleben wuerde.

Dieses Skript liest NUR. Es aendert nichts.

WANN AUSFUEHREN
---------------
Nach dem naechsten Neustart, sobald der Bot ein paar Kaufpruefungen
gemacht hat (also nach etwa 10 Minuten). Danach gelegentlich.
"""
import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "data_store", "telemetrie.db")

# Spalte -> ab wann sie befuellt sein MUSS
NEUE_SPALTEN = [
    ("decision_id", "jede Entscheidung"),
    ("cycle_id", "jede Entscheidung"),
    ("git_commit", "jede Entscheidung"),
    ("regime", "jede Entscheidung"),
    ("fear_greed", "jede Entscheidung"),
    ("feature_snapshot_id", "jede Entscheidung"),
    ("kosten_erwartet_pct", "jede Entscheidung"),
    ("daten_alter_sec", "jede Entscheidung"),
    ("quellen_gesund", "jede Entscheidung"),
    ("spread_pct", "wenn Orderbuch abgefragt wurde"),
    ("agent_id", "wenn der Erzeuger es setzt"),
    ("model_version", "jede Entscheidung"),
    ("trailing_stop_pct", "wenn der Intent ihn traegt"),
    ("max_slippage_pct", "jede Entscheidung"),
    ("quantity_geplant", "wenn Menge geplant wurde"),
    ("risiko_pct", "wenn Einstieg UND Stop bekannt"),
    ("risiko_r_usd", "wenn zusaetzlich die Menge bekannt"),
    ("position_id", "nach dem Kauf (nachgetragen)"),
    ("r_multiple_netto", "erst beim VERKAUF"),
    ("take_profit", "NIE - es gibt bewusst keine Kursziele"),
    ("rr_geplant_netto", "NIE - Reserve, solange kein Kursziel"),
]


def main():
    if not os.path.exists(DB):
        print(f"Keine Datenbank unter {DB}")
        return
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    vorhanden = {r[1] for r in con.execute("PRAGMA table_info(evaluations)")}
    tabellen = {r[0] for r in con.execute(
        "select name from sqlite_master where type='table'")}

    print("=" * 72)
    print("TELEMETRIE-PRUEFUNG (Schritt 3)")
    print("=" * 72)

    fehlend = [n for n, _ in NEUE_SPALTEN if n not in vorhanden]
    print(f"\nSpalten in evaluations : {len(vorhanden)}")
    print(f"Tabelle feature_snapshots vorhanden: "
          f"{'JA' if 'feature_snapshots' in tabellen else 'NEIN'}")
    if fehlend:
        print(f"\n!! FEHLENDE SPALTEN: {fehlend}")
        print("!! Der Bot lief noch nicht mit dem neuen Code - Neustart noetig.")
        return

    gesamt = con.execute("select count(*) from evaluations").fetchone()[0]
    # Nur Zeilen betrachten, die NACH der Erweiterung entstanden sind:
    # daran erkennbar, dass ueberhaupt eine der neuen Spalten gefuellt ist.
    neu = con.execute(
        "select count(*) from evaluations where decision_id is not null"
    ).fetchone()[0]
    print(f"\nZeilen gesamt          : {gesamt}")
    print(f"davon mit neuen Feldern: {neu}")

    if neu == 0:
        print("\nNoch keine Zeile mit den neuen Feldern.")
        print("Erwartet, solange der Bot noch mit dem alten Code laeuft.")
        print("Nach dem Neustart und ein paar Minuten Betrieb erneut pruefen.")
        return

    print(f"\n{'Spalte':22} {'gefuellt':>10} {'Anteil':>8}   erwartet ab")
    print("-" * 72)
    for name, wann in NEUE_SPALTEN:
        n = con.execute(
            f"select count(*) from evaluations "
            f"where decision_id is not null and {name} is not null"
        ).fetchone()[0]
        anteil = (n / neu * 100) if neu else 0
        print(f"{name:22} {n:>10} {anteil:>7.1f}%   {wann}")

    # Merkmals-Schnappschuesse
    fs = con.execute("select count(*) from feature_snapshots").fetchone()[0]
    print(f"\nMerkmals-Schnappschuesse: {fs}")
    if fs:
        r = con.execute(
            "select * from feature_snapshots order by ts_utc desc limit 1"
        ).fetchone()
        leer = [k for k in r.keys() if r[k] is None]
        print(f"  neuester: {r['symbol']} {r['ts_utc'][:19]} "
              f"(Schema {r['schema_version']})")
        print(f"  leere Felder darin: {leer if leer else 'keine'}")
        verwaist = con.execute(
            "select count(*) from evaluations "
            "where feature_snapshot_id is not null and feature_snapshot_id != '' "
            "and feature_snapshot_id not in "
            "(select feature_snapshot_id from feature_snapshots)"
        ).fetchone()[0]
        print(f"  Entscheidungen mit ungueltigem Verweis: {verwaist}"
              + ("  <- SOLLTE 0 SEIN" if verwaist else ""))

    # Die Kette Entscheidung -> Position -> Verkauf
    print("\nKette Entscheidung -> Position -> Verkauf:")
    for d in ("APPROVED", "SOLD"):
        r = con.execute(
            "select count(*) n, sum(position_id is not null and position_id != '') mit "
            "from evaluations where decision = ? and decision_id is not null",
            (d,)).fetchone()
        print(f"  {d:9}: {r['n']:5} Zeilen, mit position_id: {r['mit'] or 0}")
    rm = con.execute(
        "select count(*) from evaluations where r_multiple_netto is not null"
    ).fetchone()[0]
    print(f"  Verkaeufe mit R-Vielfachem: {rm}")
    if rm:
        w = con.execute(
            "select avg(r_multiple_netto) a, min(r_multiple_netto) mn, "
            "max(r_multiple_netto) mx from evaluations "
            "where r_multiple_netto is not null").fetchone()
        print(f"  Mittelwert {w['a']:+.2f}R  (von {w['mn']:+.2f}R bis {w['mx']:+.2f}R)")
        print("  Lesart: ueber 0 heisst, das eingegangene Risiko hat sich gelohnt.")


def doppelverkaeufe():
    """[13.08.2026] Sucht dieselbe Position zweimal verkauft.

    ANLASS: Sven fand am 13.08. im Verlauf zwei SOL-Verkaeufe mit
    identischer Menge, 21 Minuten auseinander, beide BREAKEVEN-SPERRE.
    Beide trugen dieselbe position_id (pos_SOL_d044b018). Ursache war die
    Zustandssicherung: Sie wurde nur alle 30 Sekunden geschrieben, und
    stop() aktualisierte die Positionsliste vorher nicht. Wer in diesem
    Fenster neu startete, bekam die eben verkaufte Position zurueck.

    Diese Pruefung ist der Nachweis, dass es nicht wieder passiert.
    Erkennungsmerkmal ist die position_id: dieselbe Kennung darf nur EIN
    Mal verkauft werden. Mehrere Verkaeufe desselben Coins sind dagegen
    voellig normal - der Bot haelt nacheinander mehrere Positionen.
    """
    print("\n" + "=" * 72)
    print("DOPPELVERKAUFS-PRUEFUNG")
    print("=" * 72)
    journal = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "data_store", "trades_v5.json")
    if not os.path.exists(journal):
        print("Kein Journal gefunden.")
        return
    import json
    from collections import defaultdict
    try:
        with open(journal, encoding="utf-8") as f:
            j = json.load(f)
    except Exception as e:
        print(f"Journal nicht lesbar: {e}")
        return
    trades = j if isinstance(j, list) else j.get("trades", [])
    nach_id = defaultdict(list)
    ohne_id = 0
    for t in trades:
        if not str(t.get("type", "")).upper().startswith("SELL"):
            continue
        pid = t.get("position_id")
        if pid:
            nach_id[pid].append(t)
        else:
            ohne_id += 1

    doppelt = {k: v for k, v in nach_id.items() if len(v) > 1}
    print(f"\nVerkaeufe mit Positions-Kennung: {sum(len(v) for v in nach_id.values())}")
    print(f"Verkaeufe ohne Kennung (aeltere) : {ohne_id}")
    print(f"Positionen mehr als einmal verkauft: {len(doppelt)}")

    if not doppelt:
        print("\n  Keine Doppelverkaeufe. Gut.")
        return

    print()
    for pid, liste in sorted(doppelt.items(),
                             key=lambda x: str(x[1][0].get("time", ""))):
        print(f"  {pid}  ({len(liste)} Verkaeufe)")
        for t in liste:
            print(f"     {str(t.get('time',''))[:19]}  {t.get('qty',0):.8f}  "
                  f"{t.get('pnl',0):+7.2f}$  {str(t.get('reason',''))[:40]}")
    print("\n  !! Jede Zeile hier ist eine Position, die mehrfach verkauft")
    print("  !! wurde. Im Papiermodus verfaelscht das die Zahlen, live")
    print("  !! wuerde der Bot Muenzen verkaufen, die er nicht hat.")


def zustand_gegen_bestand():
    """[13.08.2026] Vergleicht die gespeicherte Positionsliste mit dem Bestand.

    Weicht beides ab, steht im gespeicherten Zustand eine Position, die es
    real nicht mehr gibt (oder umgekehrt). Genau dieser Zustand fuehrte am
    13.08. zum SOL-Doppelverkauf.
    """
    print("\n" + "=" * 72)
    print("ZUSTAND GEGEN BESTAND")
    print("=" * 72)
    import json
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data_store", "bot_state.json")
    try:
        with open(pfad, encoding="utf-8") as f:
            s = json.load(f)
    except Exception as e:
        print(f"bot_state.json nicht lesbar: {e}")
        return
    bak = s.get("open_positions_backup") or {}
    pb = s.get("paper_balances_backup") or {}
    if not bak:
        print("\n  Keine gespeicherten Positionen.")
    fehler = 0
    for sym, p in bak.items():
        asset = sym.split("/")[0]
        bestand = float(pb.get(asset, 0) or 0)
        qty = float(p.get("qty", 0) or 0)
        passt = qty > 0 and abs(bestand - qty) <= qty * 0.01
        if not passt:
            fehler += 1
        print(f"  {sym:10} gespeichert {qty:.8f} | Bestand {bestand:.8f}  "
              f"{'passt' if passt else '<-- WEICHT AB'}")
    # Umgekehrt: Bestand ohne gespeicherte Position
    for asset, menge in pb.items():
        if asset in ("USDC", "USDT", "EUR", "USD") or not menge:
            continue
        if not any(s0.split("/")[0] == asset for s0 in bak):
            fehler += 1
            print(f"  {asset:10} Bestand {float(menge):.8f} OHNE gespeicherte "
                  f"Position  <-- unbewacht, kein Stop-Loss")
    print(f"\n  Abweichungen: {fehler}")


if __name__ == "__main__":
    main()
    doppelverkaeufe()
    zustand_gegen_bestand()
