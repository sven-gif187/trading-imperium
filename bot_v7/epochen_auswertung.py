# -*- coding: utf-8 -*-
"""Teilt die Telemetrie-Datenbank nach Epochen auf.

WOZU
----
CLAUDE.md Abschnitt 5: *"Jede Verhaltensaenderung braucht eine
Epochengrenze, sonst sind alle Vorher-Nachher-Vergleiche wertlos."*

Die Grenzen stehen in config_epochs.json. Die Messdaten stehen in
data_store/telemetrie.db. Zwischen beiden fehlte die Verbindung: Die
Tabellen tragen einen Zeitstempel (ts_utc), aber keine Epoche - wer
etwas auswerten wollte, musste die Grenzen von Hand heraussuchen und
in ein SQL einsetzen.

Genau so rechnet irgendwann jemand zwei Epochen in einen Topf. Und
weil die Epochen sich gerade schnell abloesen (L1 ohne Fraktal-Tor,
L2 mit Tor, L3 mit Tor und Fibonacci-Ausstieg), waere das hier
besonders leicht passiert.

Das vorhandene epoch_report.py macht dasselbe fuer die JSON-Journale.
Diese Datei ist sein Gegenstueck fuer die Datenbank - und benutzt
dieselbe Quelle (epochs.py), damit es nie zwei Wahrheiten gibt.

WAS DABEI AUFFIEL
-----------------
epochs.py stuerzte ab, sobald eine Epoche ein leeres `start`-Feld
hatte - und L1_echtgeld_start trug den Vermerk "Startzeit wird beim
ersten Lauf eingetragen", eingetragen wurde sie nie. Damit ging JEDES
Werkzeug nicht, das Epochen benutzt. Am 15.09. behoben.

Aufruf:  EPOCHEN_AUSWERTUNG.bat  (Doppelklick)
         python epochen_auswertung.py --tabelle evaluations
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import epochs  # noqa: E402

DB = os.path.join("data_store", "telemetrie.db")

# Tabellen mit Zeitstempel, die sich lohnen. Die Spalte heisst in
# allen ts_utc - geprueft, nicht angenommen.
TABELLEN = ("evaluations", "rule_evaluations", "schatten_exits",
            "schatten_regeln", "schatten_sizing", "lern_ereignisse",
            "markt_historie", "feature_snapshots", "chart_signale")


def zeitspalte(c, tabelle):
    """Findet die Zeitspalte einer Tabelle. None, wenn es keine gibt."""
    try:
        spalten = [r[1] for r in c.execute(f'PRAGMA table_info("{tabelle}")')]
    except Exception:
        return None
    for bevorzugt in ("ts_utc", "ts", "zeit", "datum"):
        if bevorzugt in spalten:
            return bevorzugt
    for s in spalten:
        if any(k in s.lower() for k in ("ts", "zeit", "time", "datum")):
            return s
    return None


def normiere(ts):
    """Bringt einen Zeitstempel auf das Format der Datenbank.

    ZWINGEND NOETIG, und der Grund ist gemein:
    Verglichen wird in SQL als TEXT. Die Epochengrenzen stehen in
    config_epochs.json als "2026-09-15 07:26:43" (mit Leerzeichen),
    die Datenbank schreibt "2026-09-15T05:32:44.123+00:00" (ISO, mit T).

    Im Zeichenvergleich ist "T" (0x54) GROESSER als " " (0x20). Damit
    galt jeder Zeitstempel nach Mitternacht als spaeter als eine
    Grenze desselben Tages - egal wie frueh er war.

    Der erste Lauf dieses Werkzeugs zeigte es sofort: L1 lief zwoelf
    Stunden und bekam 5 Zeilen, L3 lief drei Stunden und bekam 2.882.

    Die Summenprobe unten haette das NICHT gefunden - die Summe stimmt
    ja, die Zeilen sind nur im falschen Fach. Deshalb prueft dieses
    Werkzeug zusaetzlich einen bekannten Einzelfall (siehe
    `probe_einzelfall`). Genau das verlangt CLAUDE.md Abschnitt 0:
    gegen einen von Hand nachgerechneten Einzelfall, nicht gegen eine
    Anzahl.
    """
    s = (ts or "").strip()
    if not s:
        return None
    # "2026-09-15 07:26:43" -> "2026-09-15T07:26:43"
    if len(s) > 10 and s[10] == " ":
        s = s[:10] + "T" + s[11:]
    return s


def grenzen():
    """Die Epochen als Liste (id, start_iso, ende_iso oder None).

    Das Ende einer Epoche ist der Anfang der naechsten - so entstehen
    luecken- und ueberschneidungsfreie Faecher.
    """
    eps = epochs.load_epochs()
    raus = []
    for i, e in enumerate(eps):
        start = normiere(e.get("start"))
        ende = None
        if i + 1 < len(eps):
            ende = normiere(eps[i + 1].get("start"))
        raus.append((e.get("id", f"epoche_{i}"), start, ende,
                     e.get("label", "")))
    return raus


def probe_einzelfall(c):
    """Gegenprobe an einem bekannten Fall, nicht an einer Summe.

    Die aelteste Zeile der Datenbank MUSS in die aelteste Epoche
    fallen - das laesst sich ohne Rechnung entscheiden. Faellt sie
    woandershin, stimmt die Zuordnung nicht, und keine Zahl dieses
    Werkzeugs ist zu gebrauchen.
    """
    try:
        aeltester = c.execute(
            "SELECT MIN(ts_utc) FROM evaluations").fetchone()[0]
    except Exception:
        return True, "keine evaluations-Tabelle - Probe uebersprungen"
    if not aeltester:
        return True, "keine Daten - Probe uebersprungen"

    ep = grenzen()
    if not ep:
        return False, "keine Epochen"

    # In welches Fach faellt die aelteste Zeile?
    treffer = None
    for eid, start, ende, _ in ep:
        if start and aeltester < start:
            continue
        if ende and aeltester >= ende:
            continue
        treffer = eid
        break

    erwartet = ep[0][0]
    ok = treffer == erwartet
    text = (f"aelteste Zeile {aeltester[:19]} faellt in {treffer}, "
            f"erwartet {erwartet}")
    return ok, text


def zaehle(c, tabelle, spalte, start, ende, bedingung=""):
    """Zeilen einer Tabelle im Zeitfenster [start, ende)."""
    wo = []
    werte = []
    if start:
        wo.append(f'"{spalte}" >= ?')
        werte.append(start)
    if ende:
        wo.append(f'"{spalte}" < ?')
        werte.append(ende)
    if bedingung:
        wo.append(bedingung)
    sql = f'SELECT COUNT(*) FROM "{tabelle}"'
    if wo:
        sql += " WHERE " + " AND ".join(wo)
    try:
        return c.execute(sql, werte).fetchone()[0]
    except Exception:
        return None


def main():
    nur = None
    if "--tabelle" in sys.argv:
        i = sys.argv.index("--tabelle")
        if i + 1 < len(sys.argv):
            nur = sys.argv[i + 1]

    print()
    print("=" * 76)
    print("  TELEMETRIE NACH EPOCHEN")
    print("=" * 76)

    if not os.path.exists(DB):
        print(f"\n  {DB} nicht gefunden.\n")
        return 1

    ep = grenzen()
    if not ep:
        print("\n  Keine Epochen in config_epochs.json.\n")
        return 1

    print("\n  Epochen aus config_epochs.json:")
    for eid, start, ende, label in ep:
        s = start or "(kein Startdatum - gilt als aelteste)"
        print(f"    {eid:24} ab {s}")
        if label:
            print(f"    {'':24}    {label}")
    print()

    c = sqlite3.connect(DB)

    # === GEGENPROBE VOR ALLEM ANDEREN ===
    # Stimmt die Zuordnung nicht, sind alle Zahlen darunter wertlos -
    # dann lieber gar nichts ausgeben als etwas Falsches.
    ok, text = probe_einzelfall(c)
    print(f"  GEGENPROBE (Einzelfall): {text}")
    if not ok:
        print()
        print("  !! ZUORDNUNG STIMMT NICHT - keine Zahlen ausgegeben. !!")
        print("     Haeufigste Ursache: Zeitformat. Die Grenzen in")
        print("     config_epochs.json und die Zeitstempel in der")
        print("     Datenbank muessen dasselbe Format haben.")
        print()
        return 1
    print()

    tabellen = [nur] if nur else list(TABELLEN)

    for tabelle in tabellen:
        spalte = zeitspalte(c, tabelle)
        if spalte is None:
            continue
        gesamt = zaehle(c, tabelle, spalte, None, None)
        if not gesamt:
            continue

        print("-" * 76)
        print(f"  {tabelle}   ({gesamt} Zeilen, Zeitspalte {spalte})")

        summe = 0
        for eid, start, ende, _ in ep:
            n = zaehle(c, tabelle, spalte, start, ende)
            if n is None:
                continue
            summe += n
            anteil = n / gesamt * 100 if gesamt else 0
            balken = "#" * int(anteil / 2.5)
            print(f"    {eid:24} {n:>7}  {anteil:>5.1f} %  {balken}")

            # Bei Entscheidungen zusaetzlich die Genehmigungsquote -
            # das ist die Zahl, an der man eine Epoche erkennt.
            if tabelle == "evaluations":
                ap = zaehle(c, tabelle, spalte, start, ende,
                            "decision='APPROVED'")
                if ap is not None and n:
                    print(f"    {'':24} davon genehmigt: {ap}"
                          f" ({ap / n * 100:.2f} %)")

        # GEGENPROBE (CLAUDE.md Abschnitt 0): Die Faecher muessen die
        # Tabelle vollstaendig abdecken. Fehlt etwas, liegen Zeilen
        # ausserhalb aller Epochen - und wuerden bei jeder Auswertung
        # stillschweigend fehlen.
        if summe != gesamt:
            print(f"    GEGENPROBE FEHLGESCHLAGEN: {summe} in Epochen,"
                  f" aber {gesamt} in der Tabelle"
                  f"  ({gesamt - summe} Zeilen ausserhalb!)")
        else:
            print(f"    Gegenprobe: {summe} = {gesamt}, keine Zeile faellt"
                  f" durchs Raster")
        print()

    print("=" * 76)
    print("  Diese Zahlen NIE epochenuebergreifend vergleichen - genau")
    print("  dafuer gibt es die Grenzen.")
    print("=" * 76)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
