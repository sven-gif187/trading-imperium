# -*- coding: utf-8 -*-
"""Vergleicht die Schatten-Ausstiegsregel mit der echten Leiter.

Aufruf:  python schatten_leiter_auswertung.py

WAS DAS BEANTWORTET
-------------------
Die Schatten-Regel (risk/exit_rules_schatten.py) notiert bei jeder
Position, wann SIE verkauft haette - verkauft aber nicht. Dieses Skript
holt sich dazu den TATSAECHLICHEN Ausgang aus dem Journal und rechnet
aus, welche der beiden Regeln mehr uebrig gelassen haette.

Ergebnis pro Trade in Prozentpunkten UND in Dollar, denn bei kleinem
Kapital ist der Prozentwert allein irrefuehrend: 0,35 % von 150 $ sind
vier Cent.

EHRLICHKEIT
-----------
Solange weniger als ~20 Vergleichspaare vorliegen, sagt das Ergebnis
nichts. Das Skript weist darauf hin, statt eine Zahl zu zeigen, die
nach Wahrheit aussieht.
"""
import json
import os
import sqlite3
import statistics as st

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_store")
DB = os.path.join(DATA, "telemetrie.db")
JOURNAL = os.path.join(DATA, "trades_v5.json")

MINDEST_PAARE = 20          # darunter keine Aussage
REGEL = "GEWINN_RATSCHE_25"


def journal_verkaeufe():
    """position_id -> tatsaechlicher Ausgang."""
    if not os.path.exists(JOURNAL):
        return {}
    try:
        with open(JOURNAL, encoding="utf-8") as f:
            j = json.load(f)
    except Exception as e:
        print(f"Journal nicht lesbar: {e}")
        return {}
    trades = j if isinstance(j, list) else j.get("trades", [])
    raus = {}
    for t in trades:
        if not str(t.get("type", "")).upper().startswith("SELL"):
            continue
        pid = t.get("position_id")
        if pid:
            raus[pid] = t
    return raus


def main():
    if not os.path.exists(DB):
        print(f"Keine Telemetrie-Datenbank unter {DB}")
        return

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    schatten = con.execute(
        "SELECT * FROM schatten_exits WHERE regel = ? ORDER BY ts_utc",
        (REGEL,)).fetchall()

    print("=" * 74)
    print(f"SCHATTEN-LEITER '{REGEL}' gegen die echte Ausstiegsleiter")
    print("=" * 74)
    print(f"\nSchatten-Ausloesungen aufgezeichnet: {len(schatten)}")

    if not schatten:
        print("\nNoch keine Ausloesung. Das ist zu erwarten, solange keine")
        print("Position ueber +1,0 % Hoechststand stand - die Regel ist")
        print("darunter absichtlich stumm.")
        return

    verkaeufe = journal_verkaeufe()
    print(f"Verkaeufe im Journal mit position_id  : {len(verkaeufe)}")

    paare, offen = [], []
    for s in schatten:
        pid = s["position_id"]
        echt = verkaeufe.get(pid) if pid else None
        if echt is None:
            offen.append(s)
            continue
        echt_pct = echt.get("pnl_pct")
        if not isinstance(echt_pct, (int, float)):
            offen.append(s)
            continue
        paare.append({
            "symbol": s["symbol"],
            "ts": s["ts_utc"][:16],
            "hoch": s["hoechst_pnl_pct"] or 0.0,
            "schatten_pct": s["pnl_pct"] or 0.0,
            "echt_pct": echt_pct,
            "echt_usd": echt.get("pnl", 0.0) or 0.0,
            "grund": str(echt.get("reason") or echt.get("exit_reason") or "")[:30],
        })

    print(f"Vergleichbare Paare (Schatten + Ausgang): {len(paare)}")
    if offen:
        print(f"Noch offen (Position laeuft oder ohne id): {len(offen)}")

    if not paare:
        print("\nNoch kein Paar vollstaendig. Sobald eine Position, bei der")
        print("die Schatten-Regel ausgeloest hat, tatsaechlich verkauft")
        print("wird, erscheint sie hier.")
        return

    print()
    print(f"{'Datum':17} {'Coin':10} {'Hoch':>7} {'Schatten':>9} "
          f"{'echt':>7} {'Diff Pp':>8} {'echt $':>8}  Grund")
    print("-" * 105)
    for p in paare:
        diff = p["schatten_pct"] - p["echt_pct"]
        print(f"{p['ts']:17} {p['symbol']:10} {p['hoch']:+7.2f} "
              f"{p['schatten_pct']:+9.2f} {p['echt_pct']:+7.2f} "
              f"{diff:+8.2f} {p['echt_usd']:+8.2f}  {p['grund']}")

    diffs = [p["schatten_pct"] - p["echt_pct"] for p in paare]
    besser = sum(1 for d in diffs if d > 0)

    print()
    print("-" * 74)
    print(f"Schatten-Regel waere besser gewesen in {besser} von {len(paare)} Faellen")
    print(f"Median-Unterschied : {st.median(diffs):+.2f} Prozentpunkte")
    print(f"Mittel-Unterschied : {st.mean(diffs):+.2f} Prozentpunkte")

    # In Dollar - der Wert, auf den es bei kleinem Kapital ankommt.
    usd = []
    for p in paare:
        if p["echt_pct"]:
            basis = abs(p["echt_usd"] / (p["echt_pct"] / 100))   # Positionswert
            usd.append(basis * (p["schatten_pct"] - p["echt_pct"]) / 100)
    if usd:
        print(f"Summe in Dollar    : {sum(usd):+.2f} $ "
              f"(positiv = Schatten-Regel haette mehr gebracht)")

    # Nach Gewinnhoehe getrennt - dort liegt der Kern der Frage.
    print()
    print("Nach Hoechststand getrennt:")
    for name, tief, hoch in (("bis  +3 %", 0, 3), ("+3 bis +8 %", 3, 8),
                             ("ueber +8 %", 8, 9999)):
        gruppe = [p for p in paare if tief <= p["hoch"] < hoch]
        if not gruppe:
            print(f"  {name:14}: keine Faelle")
            continue
        d = [p["schatten_pct"] - p["echt_pct"] for p in gruppe]
        print(f"  {name:14}: {len(gruppe):3} Faelle, Median "
              f"{st.median(d):+.2f} Pp, Schatten besser in "
              f"{sum(1 for x in d if x > 0)}")

    print()
    if len(paare) < MINDEST_PAARE:
        print(f"!! ACHTUNG: {len(paare)} Paare sind ZU WENIG fuer eine")
        print(f"!! Entscheidung. Aussagekraeftig ab etwa {MINDEST_PAARE}.")
        print("!! Die Zahlen oben sind ein Zwischenstand, kein Ergebnis.")
    else:
        print("Genug Paare fuer eine erste Einschaetzung. Vor einer")
        print("Regelaenderung zusaetzlich pruefen: verteilen sich die Faelle")
        print("ueber verschiedene Muenzen und Marktphasen, oder haengt das")
        print("Ergebnis an ein paar wenigen Ausreissern?")


if __name__ == "__main__":
    main()
