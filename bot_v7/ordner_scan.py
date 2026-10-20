# -*- coding: utf-8 -*-
"""Geht den Ordner Datei fuer Datei durch - nach Mustern, die hier schon geschadet haben.

WOZU
----
Sven am 17.09.2026: *"bitte scanne den bot weiterhin und schaue ordner
fuer ordner ob alles passt"*.

Dieses Werkzeug sucht NICHT nach allem, was falsch sein koennte - das
waere eine Liste ohne Ende, und eine Liste ohne Ende wird nicht gelesen.
Es sucht nach **genau den Mustern, die in diesem Projekt bereits einen
Schaden verursacht haben.** Jede Regel unten hat eine Fundstelle in der
Projektgeschichte.

DIE REGELN - und was sie gekostet haben
---------------------------------------
1. VERDRAHTETE GEBUEHR
   agents/btc_accumulator.py:131 und :167 rechneten mit 0,1 % statt
   0,25 % (17.09.2026). Die Annahme stammt aus der Zeit vor der
   Boersenwahl. Laut Handbuch 4.53 steckt sie noch an weiteren Stellen.
   Eine zu niedrige Gebuehr bucht mehr, als bezahlt wurde - das faellt
   erst beim Kontoabgleich auf.

2. STILLER SCHLUCKER
   `except: pass` ohne Protokoll. Am 06.08.2026 war genau das die
   Ursache des ganzen Projekts: nicht der Fehler war das Problem,
   sondern dass er unsichtbar blieb. In runtime/exit_monitor.py stand
   an einer solchen Stelle ein `pass`, und die Trend-Ausstiegsregel
   traf nie zu, ohne dass es jemand erfuhr.

3. PAPIER-PFAD IM ECHTBETRIEB
   `_paper_balances` und Verwandtes. Der Bot laeuft seit dem 14.09. im
   Modus `live`. Code, der auf Papier-Guthaben zugreift, rechnet dann
   gegen eine Groesse, die es nicht mehr gibt.

4. ZWEITE WAHRHEIT
   Dieselbe Zahl an mehreren Stellen. Befund 90: ein festes Datum in
   DAUERREGELN.txt sagte, der Freeze sei vorbei, waehrend das Fenster
   laengst verlaengert war. Zwei Wahrheiten gehen irgendwann an einer
   davon falsch aus.

5. FREMDER ORDNER
   Seit dem 14.09. gibt es zwei Ordner. check_punkt_a.py:9 pruefte die
   Einstellungen des PAPIER-Bots und gab das Ergebnis aus, als waere es
   das des Live-Bots (17.09.).

Reine Leseoperation. Aendert nichts, startet nichts.

Aufruf:
    python ordner_scan.py              alle Ordner
    python ordner_scan.py risk core    nur diese
"""
import io
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))

# Ordner, die bewusst nicht geprueft werden.
AUS = {"archiv", ".git", "__pycache__", "v4_referenz", "v4_data",
       "zahlenbuecher", "docs", "aufgabenplanung_backup", "node_modules",
       "uebergabe-dust", "assets", "prognosen", "reports", ".claude"}

# Dateien, die ueber diese Muster SCHREIBEN - sie wuerden sich selbst melden.
SELBST = {"ordner_scan.py", "umzug_pruefen.py", "schon_bekannt.py",
          "kosten.py", "kosten_matrix_v4.py"}


def regeln():
    """Jede Regel: (Kuerzel, Muster, Erklaerung, Schwere)."""
    return [
        ("GEBUEHR",
         re.compile(r"[*]\s*0\.001\b|[*]\s*0\.0032\b|=\s*0\.0010?\b.*fee|"
                    r"fee\s*=\s*[^#\n]*0\.001\b|0\.32\s*[/%]"),
         "Gebuehr verdrahtet - Bybit EU nimmt 0,25 % je Seite",
         "hoch"),
        ("SCHLUCKER",
         re.compile(r"except[^:]*:\s*$"),
         "except ohne Protokoll - Fehler bleibt unsichtbar",
         "mittel"),
        ("PAPIERPFAD",
         re.compile(r"_paper_balances|simulate_fill|fake_fill"),
         "Papier-Pfad, obwohl der Bot im Modus 'live' laeuft",
         "hoch"),
        ("FREMDORDNER",
         re.compile(r"trading_imperium_v6\(21\)"),
         "zeigt auf den PAPIER-Ordner",
         "hoch"),
    ]


def ist_kommentar(z, imdoc):
    n = z.strip()
    return imdoc or n.startswith("#") or n.startswith('"""') or \
        n.startswith("'''") or n.startswith("REM ")


def pruefe_datei(pfad, rs):
    treffer = []
    try:
        text = io.open(pfad, encoding="utf-8", errors="ignore").read()
    except OSError:
        return treffer
    imdoc = False
    zeilen = text.splitlines()
    for nr, z in enumerate(zeilen, 1):
        if z.count('"""') % 2:
            imdoc = not imdoc
            continue
        if ist_kommentar(z, imdoc):
            continue
        for kuerzel, muster, erklaerung, schwere in rs:
            if not muster.search(z):
                continue
            if kuerzel == "SCHLUCKER":
                # Nur melden, wenn die NAECHSTE Zeile ein nacktes pass ist.
                naechste = zeilen[nr].strip() if nr < len(zeilen) else ""
                if naechste != "pass":
                    continue
            treffer.append((nr, kuerzel, erklaerung, schwere, z.strip()[:72]))
    return treffer


def main():
    nur = [a.lower() for a in sys.argv[1:]]
    rs = regeln()

    # Sammeln: je Ordner eine Liste von Treffern.
    nach_ordner = {}
    dateien_gesamt = 0
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner if o not in AUS]
        rel = os.path.relpath(wurzel, HIER)
        kopf = "." if rel == "." else rel.split(os.sep)[0]
        if nur and kopf.lower() not in nur:
            continue
        for d in sorted(dateien):
            if not d.endswith(".py") or d in SELBST or d.startswith("ZZ_"):
                continue
            dateien_gesamt += 1
            t = pruefe_datei(os.path.join(wurzel, d), rs)
            if t:
                nach_ordner.setdefault(kopf, []).append(
                    (os.path.relpath(os.path.join(wurzel, d), HIER), t))

    print("\n" + "=" * 76)
    print("  ORDNER-SCAN - nur Muster, die hier schon geschadet haben")
    print("=" * 76)
    print(f"\n  {dateien_gesamt} Python-Dateien geprueft, "
          f"{len(nach_ordner)} Ordner mit Treffern.\n")

    gesamt = {"hoch": 0, "mittel": 0}
    for kopf in sorted(nach_ordner):
        eintraege = nach_ordner[kopf]
        anzahl = sum(len(t) for _, t in eintraege)
        name = "(Hauptordner)" if kopf == "." else kopf + "/"
        print(f"  {name:<22} {anzahl:>3} Treffer in "
              f"{len(eintraege)} Datei(en)")
        for datei, t in eintraege:
            for nr, kuerzel, erklaerung, schwere, text in t:
                gesamt[schwere] = gesamt.get(schwere, 0) + 1
                marke = "!!" if schwere == "hoch" else " ."
                print(f"    {marke} {datei}:{nr}  [{kuerzel}]")
                print(f"         {text}")
                print(f"         -> {erklaerung}")
        print()

    print("  " + "-" * 72)
    print(f"  {gesamt.get('hoch', 0)} schwer · {gesamt.get('mittel', 0)} leicht")
    print("\n  PFLICHT vor dem Melden als Befund (CLAUDE.md):")
    print("     python schon_bekannt.py <datei.py:zeile>")
    print("  Meldet es BEKANNT, ist es eine Ergaenzung, kein Fund.")
    print("=" * 76 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
