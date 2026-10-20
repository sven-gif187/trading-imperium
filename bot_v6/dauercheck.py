"""Dauercheck - prueft das System in festen Abstaenden und meldet nur Abweichungen.

NUR LESEND. Startet nichts, beendet nichts, aendert keine Datenbank.
Schreibt ausschliesslich sein eigenes Log und im Bedarfsfall ein Ticket.

WARUM ES DIESES SKRIPT GIBT
---------------------------
Sven fragte am 18.08.2026: "Kannst du regelmaessige Checks automatisch
durchfuehren, wenn ich dein Fenster auflasse - und wenn Fehler oder Bugs
auftauchen, klaeren?"

Die Antwort ist zweigeteilt:

  1. WAS EINE MASCHINE KANN - messen, vergleichen, Alarm schlagen.
     Das macht dieses Skript, und zwar unabhaengig davon, ob ein
     Chatfenster offen ist. Es laeuft ueber die Windows-Aufgabenplanung.

  2. WAS EINE MASCHINE NICHT KANN - einen Fund einordnen und
     entscheiden, was er bedeutet. Dafuer braucht es jemanden, der
     nachdenkt. Dieses Skript hinterlaesst deshalb einen ORDENTLICHEN
     BEFUND, mit dem sich sofort weiterarbeiten laesst - statt einer
     Zeile "Fehler aufgetreten".

Der Unterschied zu prozess_frische.py: Der prueft EINE Frage (laeuft
alter Programmtext?). Dieser hier prueft den ganzen Betrieb.

WAS GEPRUEFT WIRD - und was jeweils als "richtig" gilt
------------------------------------------------------
Jede Pruefung nennt ihre Erwartung. Eine Pruefung ohne Erwartung ist
keine Pruefung, sondern eine Anzeige.

  1. Bot laeuft            system.log juenger als 10 Minuten
  2. Regel-Schalter        alle acht wie hinterlegt (Freeze!)
  3. Sammler               Schatten-Universum und Capture juenger als 90 Min
  4. Prozess-Frische       kein Prozess mit veraltetem Programmtext
  5. Nachlauf-Rueckstand   weniger als 400 offene Eintraege
  6. Datenzuwachs          Schnappschuesse und Signale wachsen ueberhaupt
  7. Neue Handel           seit dem letzten Lauf, mit Ergebnis
  8. Plattenplatz          mehr als 10 GB frei

MELDEREGEL
----------
Gemeldet wird nur, was ABWEICHT - und ein Zustandswechsel nur EINMAL.
Sonst steht stuendlich dieselbe Zeile in tickets.txt, und nach zwei
Tagen liest sie niemand mehr. Das ist derselbe Gewoehnungseffekt, an
dem die erste Fassung von prozess_frische.py gescheitert ist.

Aufruf:
    python dauercheck.py            einmal pruefen
    python dauercheck.py --bericht  vollen Befund zeigen, auch wenn alles gut

Rueckgabewert: 0 = alles im Rahmen, 1 = Abweichung gefunden
"""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HIER, "data_store", "dauercheck.log")
MERKER = os.path.join(HIER, "data_store", "dauercheck_stand.json")
TICKETS = os.path.join(HIER, "tickets.txt")

SYSTEM_LOG = os.path.join(HIER, "data_store", "system.log")
SCHATTEN_LOG = os.path.join(HIER, "data_store", "schatten_universum.log")


def _capture_log():
    """Wo liegt das Log des Forschungs-Sammlers?

    [28.09.2026] Hier stand ein fester Pfad in den EIGENEN Ordner. In
    v7 gibt es diesen Ordner gar nicht - die Pruefung haette dort jeden
    Tag "Log fehlt" gemeldet, und das waere eine Abweichung, die keine
    ist.

    Der Grund: Den Forschungs-Sammler gibt es auf dem Rechner genau
    EINMAL, und er gehoert zu keinem Bot-Ordner. Er erfasst
    oeffentliche Marktdaten (Orderbuch, Ticker, Funding, OI) und
    kommt ohne Bot aus - nachgelesen in capture_daemon.py: "KEIN
    Import aus Bot-Modulen", "KEIN Zugriff auf data_store/". Die
    geplante Aufgabe ForschungCapture zeigt in den v6-Ordner, und das
    ist richtig so: seine Daten gelten fuer beide Baender.

    Gesucht wird deshalb zuerst im eigenen Ordner, danach in den
    Nachbarordnern gleicher Herkunft.
    """
    eigen = os.path.join(HIER, "docs", "forschungsprogramm_2026-07",
                         "capture", "capture.log")
    if os.path.exists(eigen):
        return eigen
    eltern = os.path.dirname(HIER)
    try:
        nachbarn = sorted(os.listdir(eltern))
    except OSError:
        return eigen
    for n in nachbarn:
        if not n.lower().startswith("trading_imperium"):
            continue
        p = os.path.join(eltern, n, "docs", "forschungsprogramm_2026-07",
                         "capture", "capture.log")
        if os.path.exists(p):
            return p
    return eigen


CAPTURE_LOG = _capture_log()
TELEMETRIE = os.path.join(HIER, "data_store", "telemetrie.db")
NACHLAUF = os.path.join(HIER, "data_store", "nachlauf.db")

# Zwischenablage fuer den Stillstandszaehler - pruefungen() gibt ihn
# ueber diese Liste an main() zurueck, ohne die Schnittstelle zu aendern.
STILLSTAND = [{}]

# Wie alt darf der juengste nachgetragene 1-Stunden-Kurs sein?
# Nachgerechnet statt geraten: Der Kurs entsteht 1 h nach dem Ereignis,
# der Nachtrag laeuft stuendlich (also bis zu 1 h Wartezeit), dazu ein
# Puffer fuer langsame Laeufe und Neustarts. Macht 4 Stunden.
# Dritte Fassung dieser Grenze an einem Abend - die ersten beiden waren
# 400 offene Eintraege (falsche Groesse) und 3 Stunden (zu knapp
# gerechnet). Steht hier, damit die naechste Aenderung nicht wieder
# geraten wird.
NACHLAUF_ALTER_H = 4
STILLSTAND_GRENZE = 4      # so viele Laeufe darf ein Zaehler stillstehen


def notiz(text):
    """Erst schreiben, dann anzeigen - print nie ungeschuetzt.

    Unter pythonw.exe ist sys.stdout None; ein blankes print() beendet
    das Programm. Diese Falle hat am 14.08.2026 das Schatten-Universum
    lahmgelegt.
    """
    zeile = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {text}"
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except OSError:
        pass
    try:
        if sys.stdout is not None:
            print(zeile)
    except Exception:
        pass


def alter_minuten(pfad):
    try:
        m = datetime.fromtimestamp(os.path.getmtime(pfad), timezone.utc)
        return (datetime.now(timezone.utc) - m).total_seconds() / 60
    except OSError:
        return None


def zaehle(db, tabelle):
    try:
        con = sqlite3.connect(db)
        return con.execute(f"select count(*) from {tabelle}").fetchone()[0]
    except Exception:
        return None


def pruefungen():
    """Liefert (name, ok, befund) je Pruefung."""
    e = []

    # --- 1. Bot
    a = alter_minuten(SYSTEM_LOG)
    e.append(("Bot", a is not None and a < 10,
              f"system.log {a:.0f} Min alt" if a is not None
              else "system.log nicht lesbar"))

    # --- 2. Regel-Schalter (Freeze)
    try:
        r = subprocess.run([sys.executable, "regel_waechter_bestaetigen.py"],
                           cwd=HIER, capture_output=True, text=True, timeout=120)
        sauber = "nichts zu bestaetigen" in r.stdout
        e.append(("Regel-Schalter", sauber,
                  "alle wie hinterlegt" if sauber
                  else "ABWEICHUNG - moeglicher Freeze-Bruch!"))
    except Exception as ex:
        e.append(("Regel-Schalter", False, f"nicht pruefbar ({type(ex).__name__})"))

    # --- 3. Sammler
    for name, pfad in (("Schatten-Universum", SCHATTEN_LOG),
                       ("Forschungs-Sammler", CAPTURE_LOG)):
        a = alter_minuten(pfad)
        e.append((name, a is not None and a < 90,
                  f"Log {a:.0f} Min alt" if a is not None else "Log fehlt"))

    # --- 4. Programmtext-Frische
    try:
        r = subprocess.run([sys.executable, "prozess_frische.py"],
                           cwd=HIER, capture_output=True, text=True, timeout=300)
        frisch = r.returncode == 0
        e.append(("Programmtext", frisch,
                  "alle Prozesse aktuell" if frisch
                  else "NEUSTART FAELLIG - Aenderung wirkt nicht"))
    except Exception as ex:
        e.append(("Programmtext", False, f"nicht pruefbar ({type(ex).__name__})"))

    # --- 5. Nachlauf: kommen die Kurse nach?
    #
    # [KORREKTUR 18.08.2026, noch am selben Abend] Die erste Fassung
    # zaehlte die OFFENEN Eintraege und schlug ab 400 Alarm. Das war die
    # falsche Erwartung: Ein Eintrag bleibt bis zu 48 Stunden offen, weil
    # er auf seine 48-Stunden-Marke wartet - voellig richtig so. Bei drei
    # Muenzen im Stundentakt sind ueber 400 offene Eintraege der
    # NORMALFALL, und die Pruefung meldete beim ersten Lauf Alarm, obwohl
    # der Rueckstand langst behoben war.
    #
    # Gemessen wird jetzt, worauf es ankommt: Wie alt ist der juengste
    # nachgetragene 1-Stunden-Kurs? Steht der still, steht der Nachtrag -
    # und genau das war der Fehler von heute Abend (Handbuch 4.55).
    #
    # [ZWEITE KORREKTUR, 20 Minuten spaeter] Auch das war noch zu streng:
    # Steht der Bot still - etwa fuer ein Windows-Update - entstehen keine
    # neuen Blockaden, und der juengste 1-Stunden-Kurs altert
    # zwangslaeufig. Die Pruefung schlug dadurch Alarm, waehrend Sven
    # gerade den Rechner neu startete. Ein Wartungsfenster ist kein
    # Fehler. Deshalb gilt diese Pruefung nur, wenn der Bot laeuft.
    bot_laeuft = e[0][1] if e else False
    try:
        con = sqlite3.connect(NACHLAUF)
        juengster = con.execute(
            "select max(ts_utc) from nachlauf where p1h is not null").fetchone()[0]
        offen = con.execute(
            "select count(*) from nachlauf where vollstaendig=0").fetchone()[0]
        if not bot_laeuft:
            e.append(("Nachlauf", True,
                      "nicht bewertbar - der Bot laeuft nicht, es entstehen "
                      "keine neuen Ereignisse"))
        elif not juengster:
            e.append(("Nachlauf", False, "kein einziger 1-h-Kurs vorhanden"))
        else:
            alt = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(juengster)).total_seconds() / 3600
            e.append(("Nachlauf", alt < NACHLAUF_ALTER_H,
                      f"juengster 1-h-Kurs {alt:.1f} h alt "
                      f"(Grenze {NACHLAUF_ALTER_H} h), {offen} Eintraege offen"))
    except Exception as ex:
        e.append(("Nachlauf", False, f"nicht lesbar ({type(ex).__name__})"))

    # --- 6. Wachsen die Daten ueberhaupt?
    stand = {}
    for kurz, db, tab in (("Schnappschuesse", TELEMETRIE, "feature_snapshots"),
                          ("Kaufpruefungen", TELEMETRIE, "evaluations"),
                          ("Schatten-Signale",
                           os.path.join(HIER, "data_store",
                                        "schatten_universum.db"), "signale")):
        stand[kurz] = zaehle(db, tab)
    # [KORREKTUR 18.08.2026] Die erste Fassung verlangte Wachstum bei
    # JEDEM Lauf. Falsche Erwartung: Schatten-Signale entstehen nur, wenn
    # die Punktzahl passt - null Signale in drei Stunden sind voellig
    # normal. Die Pruefung meldete deshalb sofort Alarm ohne Anlass.
    #
    # Jetzt zwei getrennte Fragen:
    #   - Ist ein Zaehler GESCHRUMPFT? Das waere Datenverlust: sofort melden.
    #   - Steht er ueber mehrere Laeufe still? Erst nach vier Laeufen
    #     (12 Stunden) melden - dann ist es kein Zufall mehr.
    vorheriger = voriger_stand()
    vorher = vorheriger.get("zaehler", {})
    stillstand = dict(vorheriger.get("stillstand", {}))
    for kurz, wert in stand.items():
        frueher = vorher.get(kurz)
        if wert is None:
            e.append((kurz, False, "Tabelle nicht lesbar"))
        elif frueher is None:
            stillstand[kurz] = 0
            e.append((kurz, True, f"{wert} (erster Lauf, kein Vergleich)"))
        elif wert < frueher:
            stillstand[kurz] = 0
            e.append((kurz, False,
                      f"{wert} - GESCHRUMPFT um {frueher-wert}! Datenverlust?"))
        elif wert > frueher:
            stillstand[kurz] = 0
            e.append((kurz, True, f"{wert} (+{wert-frueher} seit dem letzten Lauf)"))
        else:
            stillstand[kurz] = stillstand.get(kurz, 0) + 1
            n = stillstand[kurz]
            e.append((kurz, n < STILLSTAND_GRENZE,
                      f"{wert} (unveraendert seit {n} Laeufen"
                      + (", das ist zu lange)" if n >= STILLSTAND_GRENZE
                         else ")")))
    STILLSTAND[0] = stillstand

    # --- 7. Handbuch-PDF aktuell?
    # [18.08.2026] Sven fiel auf, dass BOT-HANDBUCH.pdf vom 11.08. war -
    # eine Woche alt, die Kapitel 4.20 bis 4.56 fehlten. Es gab nie einen
    # Generator; das PDF wurde einmal von Hand erzeugt. Seither gibt es
    # handbuch_pdf.py, und diese Pruefung merkt, wenn es wieder hinterher
    # haengt. Eine Aufgabe, an die man denken muss, wird vergessen.
    try:
        md = os.path.join(HIER, "BOT-HANDBUCH.md")
        pdf = os.path.join(HIER, "BOT-HANDBUCH.pdf")
        if os.path.exists(md) and os.path.exists(pdf):
            diff = (os.path.getmtime(md) - os.path.getmtime(pdf)) / 3600
            e.append(("Handbuch-PDF", diff < 24,
                      "aktuell" if diff < 24
                      else f"{diff:.0f} h aelter als das Handbuch - "
                           f"python handbuch_pdf.py"))
        else:
            e.append(("Handbuch-PDF", False, "Datei fehlt"))
    except Exception:
        e.append(("Handbuch-PDF", True, "nicht pruefbar"))

    # --- 8. Plattenplatz
    try:
        frei = shutil.disk_usage(HIER).free / 1e9
        e.append(("Plattenplatz", frei > 10, f"{frei:.1f} GB frei"))
    except Exception:
        e.append(("Plattenplatz", True, "nicht pruefbar"))

    return e, stand


def voriger_stand():
    try:
        with io.open(MERKER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def stand_merken(daten):
    try:
        with io.open(MERKER, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=1)
    except OSError:
        pass


def ticket(text):
    try:
        with io.open(TICKETS, "a", encoding="utf-8") as f:
            f.write(f"\nBUG: {text}\n")
        return True
    except OSError:
        return False


def main():
    voll = "--bericht" in sys.argv
    # [28.09.2026] --kein-ticket: aufgerufen aus tagescheck.py, das den
    # gemeinsamen Bericht und das Ticket schreibt. Zwei Werkzeuge, die
    # denselben Fund melden, ergeben zwei Tickets fuer eine Sache.
    stumm = "--kein-ticket" in sys.argv
    ergebnisse, zaehler = pruefungen()
    schlecht = [(n, b) for n, ok, b in ergebnisse if not ok]

    if voll or schlecht:
        notiz("--- Dauercheck ---")
        for name, ok, befund in ergebnisse:
            if voll or not ok:
                notiz(f"  {'OK  ' if ok else 'FEHL'} {name:20} {befund}")

    alt = voriger_stand()
    vorige_fehler = set(alt.get("fehler", []))
    jetzige_fehler = {n for n, _ in schlecht}

    if not schlecht:
        if vorige_fehler:
            notiz("wieder in Ordnung: " + ", ".join(sorted(vorige_fehler)))
        elif not voll:
            notiz("alles im Rahmen")
        stand_merken({"fehler": [], "zaehler": zaehler,
                      "stillstand": STILLSTAND[0],
                      "zuletzt": datetime.now(timezone.utc).isoformat()})
        return 0

    # Nur NEUE Abweichungen melden - Wiederholung waere Gewoehnung.
    neu = jetzige_fehler - vorige_fehler
    notiz(f"ABWEICHUNG: {', '.join(sorted(jetzige_fehler))}")
    if neu and stumm:
        notiz("kein Ticket - --kein-ticket, der Aufrufer meldet selbst")
    elif neu:
        text = "; ".join(f"{n}: {b}" for n, b in schlecht if n in neu)
        if ticket(f"Dauercheck {datetime.now(timezone.utc):%d.%m. %H:%M} UTC - "
                  f"{text}. Einzelheiten: data_store/dauercheck.log"):
            notiz(f"Ticket geschrieben fuer: {', '.join(sorted(neu))}")
    else:
        notiz("kein neues Ticket - dieselbe Abweichung wie beim letzten Lauf")

    stand_merken({"fehler": sorted(jetzige_fehler), "zaehler": zaehler,
                  "stillstand": STILLSTAND[0],
                  "zuletzt": datetime.now(timezone.utc).isoformat()})
    return 1


if __name__ == "__main__":
    sys.exit(main())
