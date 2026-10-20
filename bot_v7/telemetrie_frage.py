# -*- coding: utf-8 -*-
"""Fragt die Telemetrie-Datenbank ab: Warum hat der Bot gekauft - oder nicht?

Aufruf aus dem Hauptordner:
    python telemetrie_frage.py               # Uebersicht
    python telemetrie_frage.py gruende       # Ablehnungsgruende, haeufigste zuerst
    python telemetrie_frage.py kaeufe        # alle genehmigten Kaeufe
    python telemetrie_frage.py verlauf       # letzte 30 Pruefungen
    python telemetrie_frage.py coin BTC      # alles zu einem Coin
    python telemetrie_frage.py sql "SELECT ..."   # freie Leseabfrage

Nur lesend. Diese Datei aendert nie etwas an der Datenbank oder am Bot.
"""
import os
import sqlite3
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "telemetrie.db")


def verbinde():
    if not os.path.exists(DB):
        print(f"\n  Noch keine Telemetrie-Datenbank unter:\n  {DB}\n")
        print("  Sie entsteht automatisch, sobald der Bot laeuft und die erste")
        print("  Kaufpruefung durchfuehrt. Bot starten und ein paar Minuten warten.\n")
        sys.exit(1)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def linie(zeichen="=", n=86):
    print(zeichen * n)


def status(con):
    linie()
    print(" TELEMETRIE - UEBERSICHT")
    linie()
    r = con.execute(
        "SELECT COUNT(*) n, SUM(decision='APPROVED') ok, "
        "SUM(decision='REJECTED') nein, MIN(ts_utc) von, MAX(ts_utc) bis "
        "FROM evaluations").fetchone()
    if not r["n"]:
        print("\n  Noch keine Pruefungen aufgezeichnet.\n")
        return
    quote = r["ok"] / r["n"] * 100
    print(f"\n  Zeitraum        : {r['von'][:19]}  bis  {r['bis'][:19]}")
    print(f"  Pruefungen      : {r['n']}")
    print(f"  Genehmigt       : {r['ok']}  ({quote:.1f}%)")
    print(f"  Abgelehnt       : {r['nein']}")

    print("\n  Nach Art der Ablehnung:")
    for z in con.execute(
            "SELECT COALESCE(reject_art,'-') art, COUNT(*) n FROM evaluations "
            "WHERE decision='REJECTED' GROUP BY art ORDER BY n DESC"):
        hinweise = {
            "Kapazitaet": "  <- gesund: der Bot ist voll oder schon drin",
            "STOERUNG": "  <- ECHTE STOERUNG, hier lohnt ein Blick",
            "Marktfilter": "  <- gewollt: Abwaertstrend-Schutz greift",
            "Zurueckgestellt": "  <- wartet auf Rueckgang, nicht verloren",
        }
        print(f"    {z['art']:<16s} {z['n']:6d}{hinweise.get(z['art'], '')}")

    print("\n  Nach Coin:")
    for z in con.execute(
            "SELECT symbol, COUNT(*) n, SUM(decision='APPROVED') ok "
            "FROM evaluations GROUP BY symbol ORDER BY n DESC"):
        print(f"    {z['symbol']:<12s} {z['n']:6d} Pruefungen, {z['ok']:4d} gekauft")
    print()


def gruende(con):
    linie()
    print(" WARUM DER BOT NICHT GEKAUFT HAT - haeufigste Gruende zuerst")
    linie()
    zeilen = con.execute(
        "SELECT rule_name, COUNT(*) n, COUNT(DISTINCT evaluation_id) e, "
        "MAX(detail) beispiel FROM rule_evaluations WHERE result='BLOCK' "
        "GROUP BY rule_name ORDER BY n DESC").fetchall()
    if not zeilen:
        print("\n  Keine Ablehnungen aufgezeichnet.\n")
        return
    gesamt = con.execute(
        "SELECT COUNT(*) n FROM evaluations WHERE decision='REJECTED'").fetchone()["n"]
    print(f"\n  {'Regel':<26s} {'Faelle':>7s} {'Anteil':>8s}   Beispiel")
    print("  " + "-" * 82)
    for z in zeilen:
        anteil = z["e"] / gesamt * 100 if gesamt else 0
        print(f"  {z['rule_name']:<26s} {z['e']:7d} {anteil:7.1f}%   {z['beispiel'][:34]}")
    print(f"\n  WICHTIG: Die Summe kann ueber 100% liegen - eine Ablehnung kann")
    print(f"  mehrere Gruende gleichzeitig haben. Genau dafuer ist diese Tabelle da:")
    print(f"  frueher verdeckte der erste Grund alle weiteren.\n")


def kaeufe(con):
    linie()
    print(" GENEHMIGTE KAEUFE")
    linie()
    zeilen = con.execute(
        "SELECT ts_utc, symbol, amount_usd, entry_price, score, entry_reason "
        "FROM evaluations WHERE decision='APPROVED' ORDER BY ts_utc DESC "
        "LIMIT 40").fetchall()
    if not zeilen:
        print("\n  Noch kein genehmigter Kauf aufgezeichnet.\n")
        return
    print()
    for z in zeilen:
        print(f"  {z['ts_utc'][:19]}  {z['symbol']:<11s} "
              f"{z['amount_usd'] or 0:8.2f}$ @ {z['entry_price'] or 0:11.2f}$  "
              f"Score {z['score'] or 0}/10")
        if z["entry_reason"]:
            print(f"      {z['entry_reason'][:76]}")
    print()


def verkaeufe(con):
    """[VERKAUFS-LUECKE 10.08.2026] Zeigt, WARUM verkauft wurde - und was es brachte."""
    linie()
    print(" VERKAEUFE - warum ist der Bot ausgestiegen?")
    linie()
    try:
        zeilen = con.execute(
            "SELECT ts_utc, symbol, pnl_usd, pnl_pct, qty, entry_price, "
            "strategy_id, primary_reason, haltedauer_min, mfe_pct, mae_pct "
            "FROM evaluations WHERE decision='SOLD' ORDER BY ts_utc DESC "
            "LIMIT 40").fetchall()
    except Exception:
        print("\n  Die Verkaufsspalten fehlen noch - Bot einmal neu starten,\n"
              "  dann werden sie automatisch angelegt.\n")
        return
    if not zeilen:
        print("\n  Noch kein Verkauf aufgezeichnet.")
        print("  Die Aufzeichnung startet mit dem naechsten Bot-Neustart;")
        # Verkaeufe vor dem 10.08.2026 sind nicht rekonstruierbar - sie
        # liefen an der Telemetrie vorbei und system.log ist rotiert.
        print("  Verkaeufe von VOR dem 10.08.2026 sind nicht nachtraeglich")
        print("  rekonstruierbar (liefen an der Telemetrie vorbei).\n")
        return
    print()
    for z in zeilen:
        zeichen = "+" if (z["pnl_usd"] or 0) >= 0 else "-"
        dauer = f"{z['haltedauer_min']/60:.1f}h" if z["haltedauer_min"] else "?"
        print(f"  {z['ts_utc'][:16]}  {z['symbol']:<11s} [{zeichen}] "
              f"{z['pnl_usd'] or 0:+8.2f}$ ({z['pnl_pct'] or 0:+6.2f}%)  "
              f"gehalten {dauer}")
        print(f"      {z['strategy_id']:<16s} {(z['primary_reason'] or '')[:56]}")
        if z["mfe_pct"] is not None:
            print(f"      War im Hoch {z['mfe_pct']:+.2f}%, im Tief {z['mae_pct']:+.2f}%")
    r = con.execute(
        "SELECT COUNT(*), SUM(pnl_usd), AVG(pnl_pct), SUM(pnl_usd>0) "
        "FROM evaluations WHERE decision='SOLD'").fetchone()
    if r and r[0]:
        print(f"\n  Gesamt: {r[0]} Verkaeufe, Summe {r[1] or 0:+.2f}$, "
              f"Schnitt {r[2] or 0:+.2f}%, davon {r[3] or 0} im Plus")
        print("\n  MFE/MAE lesen: 'War im Hoch +2,1%' bei einem Verkauf mit")
        print("  -0,3% heisst - der Gewinn war da und wurde nicht mitgenommen.")
    print()


def verlauf(con):
    linie()
    print(" LETZTE 30 PRUEFUNGEN")
    linie()
    print()
    for z in con.execute(
            "SELECT ts_utc, symbol, decision, reject_art, grund_anzahl, "
            "primary_reason, score FROM evaluations ORDER BY ts_utc DESC LIMIT 30"):
        zeichen = "OK  " if z["decision"] == "APPROVED" else "NEIN"
        extra = f" (+{z['grund_anzahl']-1} weitere)" if (z["grund_anzahl"] or 0) > 1 else ""
        grund = z["primary_reason"] or "genehmigt"
        print(f"  {z['ts_utc'][11:19]}  [{zeichen}] {z['symbol']:<11s} "
              f"Score {z['score'] or 0}/10  {grund[:40]}{extra}")
    print()


def coin(con, name):
    name = name.upper()
    linie()
    print(f" ALLES ZU {name}")
    linie()
    r = con.execute(
        "SELECT COUNT(*) n, SUM(decision='APPROVED') ok FROM evaluations "
        "WHERE symbol LIKE ?", (f"%{name}%",)).fetchone()
    print(f"\n  {r['n']} Pruefungen, davon {r['ok'] or 0} gekauft\n")
    for z in con.execute(
            "SELECT r.rule_name, COUNT(*) n FROM rule_evaluations r "
            "JOIN evaluations e ON e.evaluation_id=r.evaluation_id "
            "WHERE e.symbol LIKE ? GROUP BY r.rule_name ORDER BY n DESC",
            (f"%{name}%",)):
        print(f"    {z['rule_name']:<26s} {z['n']:6d}x")
    print()


def markt(con):
    """[MARKTDATEN-HISTORIE 11.08.2026] Zeigt die Zeitreihe der Marktwerte.

    Beantwortet zwei Fragen auf einen Blick: Wie lang ist die Reihe schon,
    und welche Quellen liefern ueberhaupt Daten? Eine Spalte, die dauerhaft
    leer bleibt, ist ein kaputter Anschluss - nicht ein ruhiger Markt.
    """
    print()
    linie()
    print("  MARKTDATEN-HISTORIE - was wurde wann gemessen")
    linie()
    try:
        n, von, bis = con.execute(
            "SELECT COUNT(*), MIN(ts_utc), MAX(ts_utc) FROM markt_historie").fetchone()
    except Exception:
        print("\n  Noch keine Tabelle - der Bot muss einmal mit dem neuen")
        print("  Stand gelaufen sein.\n")
        return
    if not n:
        print("\n  Noch keine Messpunkte. Der erste kommt 15 Minuten nach")
        print("  dem naechsten Bot-Start.\n")
        return
    print(f"\n  Messpunkte: {n}   von {str(von)[:16]}   bis {str(bis)[:16]}")
    tage = n * 15 / 60 / 24
    print(f"  Abgedeckt: rund {tage:.1f} Tage (ein Punkt alle 15 Minuten)")

    print("\n  Belegung je Quelle (leer = Anschluss pruefen):")
    spalten = ("fear_greed", "nupl", "dxy", "funding_score", "whale_score",
               "onchain_score", "reddit_score", "capitol_score",
               "btc_preis", "eth_preis", "sol_preis", "equity", "cash")
    for s in spalten:
        try:
            gefuellt = con.execute(
                f"SELECT COUNT({s}) FROM markt_historie").fetchone()[0]
        except Exception:
            continue
        anteil = 100 * gefuellt / n if n else 0
        marke = "ok " if anteil > 90 else ("teils" if anteil > 0 else "LEER")
        print(f"    {s:16s} {gefuellt:6d} von {n:6d}  ({anteil:5.1f} %)  {marke}")

    print("\n  Letzte 8 Messpunkte:")
    print(f"    {'Zeit':17s} {'F&G':>4s} {'NUPL':>6s} {'DXY':>7s} "
          f"{'BTC':>10s} {'Equity':>9s}  Phase")
    for z in con.execute(
            "SELECT ts_utc,fear_greed,nupl,dxy,btc_preis,equity,cycle_phase "
            "FROM markt_historie ORDER BY id DESC LIMIT 8"):
        def _f(w, breite, nach=2):
            return f"{w:{breite}.{nach}f}" if isinstance(w, (int, float)) else f"{'-':>{breite}}"
        print(f"    {str(z[0])[:16]:17s} {z[1] if z[1] is not None else '-':>4} "
              f"{_f(z[2], 6, 3)} {_f(z[3], 7)} {_f(z[4], 10)} {_f(z[5], 9)}  "
              f"{z[6] or '-'}")
    print()


def frei(con, abfrage):
    if not abfrage.strip().lower().startswith("select"):
        print("\n  Nur SELECT-Abfragen erlaubt.\n")
        return
    for z in con.execute(abfrage):
        print("  " + " | ".join(str(w) for w in z))


def main():
    args = sys.argv[1:]
    con = verbinde()
    try:
        if not args or args[0] == "status":
            status(con)
        elif args[0] == "gruende":
            gruende(con)
        elif args[0] == "kaeufe":
            kaeufe(con)
        elif args[0] in ("verkaeufe", "verkauf"):
            verkaeufe(con)
        elif args[0] == "verlauf":
            verlauf(con)
        elif args[0] in ("markt", "historie"):
            markt(con)
        elif args[0] == "coin" and len(args) > 1:
            coin(con, args[1])
        elif args[0] == "sql" and len(args) > 1:
            frei(con, args[1])
        else:
            print(__doc__)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
