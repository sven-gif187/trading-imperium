#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  SAMMLER-PRUEFUNG - ist bei jedem wirklich alles da?
================================================================
Angelegt 19.08.2026 auf Svens Auftrag: "mal wirklich fuer jeden
Sammler der momentan laeuft ueberpruefen, ob bei allen auch
wirklich alles da ist fuer die Auswertungen".

WARUM ES DIESES WERKZEUG BRAUCHT
--------------------------------
prozess_frische.py beantwortet nur: LAEUFT er noch, und mit
welchem Programmtext? Das ist die halbe Frage. Die andere Haelfte
ist: SCHREIBT er auch, was die spaetere Auswertung braucht?

Beide Ausfaelle sahen in diesem Projekt schon gleich aus:

  * positionsverlauf.py stand am 19.08. seit 21:58 still - der
    Prozess war weg, die Datenbank sah aber frisch aus, weil die
    letzte Zeile nur 20 Minuten alt war.
  * nachlauf.py lief durchgehend und schrieb Werte, von denen
    jeder dritte aus einer noch laufenden Kerze stammte
    (Befund 60). Laufen und richtig sammeln ist nicht dasselbe.

  > Ein Sammler, der laeuft, ist noch kein Sammler, der sammelt.

WAS GEPRUEFT WIRD - vier Fragen je Sammler
------------------------------------------
  1. LAEUFT er?        Prozess da, oder geplante Aufgabe, oder
                       Auftrag im Bot.
  2. SCHREIBT er?      Wie alt ist die letzte Zeile, gemessen am
                       erwarteten Takt?
  3. LUECKEN?          Groesste Pause der letzten sieben Tage.
                       Eine Luecke ist hinterher nicht nachtragbar.
  4. VOLLSTAENDIG?     Wie viel Prozent der Felder, die eine
                       Auswertung braucht, sind wirklich gefuellt?
                       Ein leeres Pflichtfeld macht die ganze
                       Zeile unbrauchbar.

BENUTZUNG - am einfachsten per Doppelklick
------------------------------------------
    SAMMLER_PRUEFEN.bat      die Ampel ansehen
    SAMMLER_NEUSTART.bat     nur wenn "mit altem Programmtext" gemeldet wird

Oder als Befehl:

    python sammler_pruefen.py              alles
    python sammler_pruefen.py --kurz       nur die Ampel
    python sammler_pruefen.py --starten    fehlende Dauerlaeufer starten
    python sammler_pruefen.py --neustart   beenden und frisch starten
    python sammler_pruefen.py --selbsttest Gegentest beide Richtungen

Der Bot ruft starten() beim Hochfahren selbst auf (app.py, direkt nach
dem Scheduler) - im Normalfall muss hier also gar nichts von Hand
gestartet werden.

OHNE Schalter ist es eine reine Leseoperation. --starten und
--neustart greifen ein: sie starten Prozesse, --neustart beendet
vorher die laufenden. Der Bot selbst beendet NIE etwas.
================================================================
"""
import os
import sys
import sqlite3
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)

GRUEN, GELB, ROT, GRAU = "OK", "PRUEFEN", "FEHLT", "-"


# ----------------------------------------------------------------
#  Die Sammler. Eine Zeile je Sammler, alles Uebrige ist Mechanik.
#
#  takt_min      erwarteter Abstand zweier Zeilen in Minuten
#  pflicht       Felder, ohne die eine Auswertung nicht geht
#  wofuer        welche Auswertung darauf steht
# ----------------------------------------------------------------
SAMMLER = [
    {
        "name": "Bot-Entscheidungen",
        "prozess": "app.py",
        "db": "data_store/telemetrie.db",
        "tabelle": "evaluations",
        "zeit": "ts_utc",
        "takt_min": 1,
        "pflicht": ["symbol", "decision", "entry_price", "total_equity",
                    "regime", "cycle_phase", "git_commit"],
        "wofuer": "Erwartungswert, Ablehnungsgruende, Zielgroessen",
    },
    {
        "name": "Merkmals-Schnappschuss",
        "prozess": "app.py",
        "db": "data_store/telemetrie.db",
        "tabelle": "feature_snapshots",
        "zeit": "ts_utc",
        "takt_min": 60,
        "pflicht": ["rsi", "macd_hist", "adx", "atr", "ema20", "ema50",
                    "ema200", "volume_ratio", "bb_breite"],
        "wofuer": "KI-Modell, Merkmalsauswertung",
    },
    {
        "name": "Marktlage stuendlich",
        "prozess": "app.py",
        "db": "data_store/telemetrie.db",
        "tabelle": "markt_historie",
        "zeit": "ts_utc",
        "takt_min": 60,
        "pflicht": ["fear_greed", "regime", "cycle_phase", "btc_preis",
                    "equity"],
        # [Befund 95] Drei Kurse gleichzeitig auf den Cent gleich gibt es
        # nicht. Steht das trotzdem da, wurde ein alter Wert weitergereicht.
        "nie_gleich": ["btc_preis", "eth_preis", "sol_preis"],
        "wofuer": "Regime-Auswertung, Zyklus-Reiter",
    },
    {
        # [19.08.2026] Geprueft wird chart_LAEUFE, nicht chart_signale.
        # Der Sammler rechnet je Lauf 800 Kerzen durch und schreibt dabei
        # 400 bis 500 Signale auf einmal - in chart_signale sehen die
        # Pausen zwischen zwei Laeufen deshalb aus wie Ausfaelle. Der
        # Herzschlag ist der Lauf, nicht das Signal.
        # Und er laeuft NICHT im Bot mit: chart_laeufe schreibt
        # chartanalyse_backtest.py - ein Skript, das Sven von Hand
        # startet. Deshalb "manuell": eine Luecke ist hier kein Ausfall,
        # sondern heisst nur, dass es an dem Tag niemand gestartet hat.
        "name": "Chartanalyse-Laeufe",
        "prozess": "chartanalyse_backtest.py",
        "manuell": True,
        "db": "data_store/telemetrie.db",
        "tabelle": "chart_laeufe",
        "zeit": "ts_utc",
        "takt_min": None,
        "pflicht": ["kerzen", "signale", "quote_pct", "ev_netto_pct",
                    "kosten_pct"],
        "wofuer": "Trefferquote der Chartanalyse (Analyse-Reiter)",
    },
    {
        "name": "Schatten-Ausstiege",
        "prozess": "app.py",
        "db": "data_store/telemetrie.db",
        "tabelle": "schatten_exits",
        "zeit": "ts_utc",
        "takt_min": None,           # ereignisgetrieben, kein Takt
        "pflicht": ["regel", "preis", "pnl_pct", "hoechst_pnl_pct"],
        "wofuer": "Ausstieg bei -1 % gegen Aussitzen",
    },
    {
        "name": "Nachlauf nach Ausstieg",
        "prozess": "app.py",
        "db": "data_store/nachlauf.db",
        "tabelle": "nachlauf",
        "zeit": "ts_utc",
        "takt_min": None,
        "pflicht": ["preis", "grund"],
        "spaeter": ["r1h", "r4h", "r24h", "r48h"],
        "wofuer": "War der Ausstieg zu frueh? (Befund 59/60)",
    },
    {
        "name": "Positionsverlauf",
        "prozess": "positionsverlauf.py",
        "db": "data_store/positionsverlauf.db",
        "tabelle": "verlauf",
        "zeit": "ts_utc",
        "takt_min": 5,
        "pflicht": ["preis", "pnl_pct", "hoch_seit", "tief_seit", "atr",
                    "rsi", "adx", "regime"],
        "wofuer": "Ausstiegsregeln gegeneinander rechnen",
    },
    {
        # [24.08.2026] Der Takt wird gegen `laeufe` gemessen, nicht gegen
        # `signale`. Das ist derselbe Denkfehler wie bei den Hintergrund-
        # Auftraegen eine Zeile weiter unten, nur andersherum:
        #
        #   `signale` bekommt nur dann eine Zeile, wenn ein Signal GEFUNDEN
        #   wurde. Findet der Markt stundenlang nichts, sieht das aus wie
        #   ein Sammler, der ausgefallen ist - obwohl er jede Stunde
        #   pflichtbewusst 18 Muenzen geprueft hat.
        #
        # Gemeldet wurde am 24.08. dauerhaft "Luecke 11,0 h - PRUEFEN".
        # Nachgerechnet: in `signale` gibt es diese Luecke wirklich
        # (22.08. 08:03 -> 19:01). In `laeufe` gibt es im selben Zeitraum
        # keine einzige Luecke ueber drei Stunden. Der Sammler lief.
        #
        #   > Nicht "wann kam zuletzt ein Ergebnis", sondern
        #   > "wann hat er zuletzt GEARBEITET".
        #
        # `tabelle` bleibt `signale` - daran haengen die Pflichtfelder und
        # die Zeilenzahl, und die gehoeren dorthin.
        "name": "Schatten-Universum",
        "prozess": "schatten_universum.py",
        "db": "data_store/schatten_universum.db",
        "tabelle": "signale",
        "zeit": "ts_utc",
        "takt_tabelle": "laeufe",
        "takt_zeit": "ts_utc",
        "takt_min": 60,
        "pflicht": ["score", "preis", "strategie", "rsi", "adx", "regime",
                    "kosten_runde"],
        "wofuer": "Welche Muenze ihre Reibung verdient",
    },
    {
        # [20.08.2026] KEIN Takt. Die jobs-Tabelle ist ereignisgetrieben,
        # und der Forschungs-Capture ist ein DAUERLAEUFER: solange die eine
        # Instanz laeuft, melden die 10-Minuten-Starts nur "Doppelstart
        # verhindert" - und wenn gar keiner startet, weil der Daemon
        # durchlaeuft, entsteht eine Luecke ganz ohne Ausfall.
        #
        # Am 18.08. sah das nach 11,1 Stunden Stillstand aus. Nachgesehen:
        # der Capture hat an dem Tag 15 MB geschrieben. Die Luecke war das
        # Gegenteil eines Problems - ein Prozess, der durchlief.
        #
        # Die richtige Frage ist nicht "wie lange war Pause", sondern
        # "ist zuletzt einer GESCHEITERT".
        "name": "Hintergrund-Auftraege",
        "prozess": "app.py",
        "db": "data_store/telemetrie.db",
        "tabelle": "jobs",
        "zeit": "start_utc",
        "takt_min": None,
        "fehlerstatus": ("status", ("FEHLER", "ABGEBROCHEN")),
        "pflicht": ["job_name", "status"],
        "wofuer": "Ist ein Hintergrundjob still gescheitert?",
    },
]


# ----------------------------------------------------------------
#  Mechanik
# ----------------------------------------------------------------
def _laufende_prozesse():
    """Befehlszeilen aller laufenden Python-Prozesse.

    [21.09.2026] Lief bis zum Umzug ueber `wmic`. Das gibt es seit
    Windows 11 24H2 nicht mehr; der Aufruf warf FileNotFoundError, das
    `except` lieferte "" - und damit meldete JEDE Prozesspruefung
    dieses Werkzeugs "laeuft nicht". Ein stiller Fehlalarm, und zwar
    in die beruhigende Richtung. Deshalb zuerst psutil.
    """
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil is not None:
        zeilen = []
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                if "python" not in (p.info["name"] or "").lower():
                    continue
                zeilen.append(" ".join(p.info["cmdline"] or []))
            except Exception:
                continue          # Prozess weg oder kein Zugriff
        return "\n".join(zeilen).lower()

    try:
        out = subprocess.run(
            ["wmic", "process", "where",
             "name like '%python%'", "get", "CommandLine"],
            capture_output=True, text=True, timeout=25)
        return (out.stdout or "").lower()
    except Exception:
        return ""


def _fremder_ordner(skript):
    """Laeuft dieser Sammler aus einem ANDEREN Ordner als diesem hier?

    [24.08.2026] Der teuerste blinde Fleck dieses Werkzeugs, gefunden,
    nachdem er zugeschlagen hatte.

    Am 24.08. um 20:00 startete Sven `SAMMLER_NEUSTART.bat` - aber die
    Kopie aus `.claude/worktrees/...`, einem Arbeitsordner, den eine
    frueherer Sitzung stehen gelassen hatte. Jede .bat beginnt mit
    `cd /d "%~dp0"`, also wechselte sie in IHREN Ordner. Dort steht ein
    zweiter, leerer `data_store`. Die echten Sammler wurden dabei
    beendet, die Kopien schrieben 40 Minuten lang ins Nichts.

    Diese Pruefung meldete waehrenddessen "Positionsverlauf - OK,
    laeuft". Sie hatte recht: ein Prozess dieses Namens LIEF. Sie sah
    nur nicht nach, wohin er schreibt.

      > Ein Sammler, der laeuft, ist noch kein Sammler, der HIER sammelt.

    Bewusst nur eine zusaetzliche Warnung: die vorhandene Erkennung
    bleibt unveraendert. Wuerde man sie schaerfen, koennte sie einen
    laufenden Sammler uebersehen und ihn ein zweites Mal starten - das
    waere schlimmer als der blinde Fleck.

    Rueckgabe: Liste der fremden Ordner (leer = alles in Ordnung).
    """
    fremd = []
    try:
        import psutil
    except Exception:
        return fremd
    hier = os.path.normcase(os.path.abspath(HIER))
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "python" not in (p.info["name"] or "").lower():
                continue
            teile = [str(x) for x in (p.info["cmdline"] or [])]
            treffer = [x for x in teile if skript.lower() in x.lower()]
            if not treffer:
                continue
            # Steht ein Pfad in der Befehlszeile, gilt der. Sonst der
            # Arbeitsordner des Prozesses.
            ordner = os.path.dirname(os.path.abspath(treffer[0]))
            if not os.path.dirname(treffer[0]):
                try:
                    ordner = p.cwd()
                except Exception:
                    continue
            if os.path.normcase(ordner) != hier:
                fremd.append(ordner)
        except Exception:
            continue
    return fremd


def _zeit(s):
    if not s:
        return None
    try:
        z = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return z if z.tzinfo else z.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _oeffne(pfad):
    voll = os.path.join(HIER, pfad)
    if not os.path.exists(voll):
        return None
    try:
        return sqlite3.connect("file:" + voll.replace("\\", "/")
                               + "?mode=ro", uri=True, timeout=10)
    except Exception:
        return None


def _bot_lief(von, bis):
    """Hat der Bot zwischen diesen beiden Zeitpunkten gearbeitet?

    Der Herzschlag ist die Tabelle `evaluations`: der Bot schreibt dort
    im Sekundentakt. Steht in einem Zeitraum nichts drin, lief er nicht -
    dann war der Rechner aus, und eine Luecke in irgendeinem Sammler ist
    kein Ausfall dieses Sammlers.

    Geprueft wird mit Abstand zu den Raendern (je 5 Minuten), sonst
    zaehlt der letzte Eintrag VOR der Pause selbst als Beweis, dass der
    Bot lief - er ist ja die Untergrenze der Luecke.
    """
    try:
        con = _oeffne("data_store/telemetrie.db")
        if con is None:
            return True                       # im Zweifel als Ausfall werten
        a = (von + timedelta(minutes=5)).isoformat()
        b = (bis - timedelta(minutes=5)).isoformat()
        if a >= b:
            return False
        n = con.execute("SELECT COUNT(*) FROM evaluations "
                        "WHERE ts_utc > ? AND ts_utc < ?", (a, b)).fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return True


def pruefe(s, prozesse, jetzt=None):
    """Vier Fragen fuer einen Sammler. Gibt ein Ergebnis-Dict zurueck."""
    jetzt = jetzt or datetime.now(timezone.utc)
    e = {"name": s["name"], "wofuer": s["wofuer"], "laeuft": None,
         "letzte": None, "alter_min": None, "luecke_min": None,
         "zeilen": 0, "leer": [], "wdh": None, "ampel": GRAU, "hinweis": "",
         "veraltet": None, "bot_aus": 0.0}

    e["laeuft"] = s["prozess"].lower() in prozesse
    # [20.08.2026] Der haeufigste Stolperstein gehoert in den BERICHT, nicht
    # nur in den Start-Aufruf. Sven liess am 20.08. um 02:01 die Pruefung
    # laufen, sah ueberall gruen - und der Schatten-Sammler arbeitete
    # trotzdem seit vier Stunden mit dem Programmtext von vor der Reparatur.
    # Eine Warnung, die nur dort steht, wo man nicht hinsieht, ist keine.
    if e["laeuft"] and s["prozess"] != "app.py":
        e["veraltet"] = _veraltet(s["prozess"])

    con = _oeffne(s["db"])
    if con is None:
        e["ampel"] = ROT
        e["hinweis"] = "Datenbank fehlt: " + s["db"]
        return e
    t, z = s["tabelle"], s["zeit"]
    # [24.08.2026] `tabelle` beantwortet "was wurde gesammelt", `takt_tabelle`
    # beantwortet "wann wurde zuletzt gearbeitet". Bei den meisten Sammlern
    # ist das dieselbe Tabelle - jede Arbeit erzeugt eine Zeile. Beim
    # Schatten-Universum nicht: dort entsteht eine Zeile nur bei einem
    # Treffer. Ohne diese Trennung meldet ein ereignisloser Markt einen
    # Ausfall. Fehlt die Angabe, bleibt alles wie vorher.
    tt = s.get("takt_tabelle", t)
    tz = s.get("takt_zeit", z)
    try:
        e["zeilen"] = con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
        letzte = con.execute("SELECT MAX(" + tz + ") FROM " + tt).fetchone()[0]
    except Exception as ex:
        e["ampel"] = ROT
        e["hinweis"] = "Tabelle nicht lesbar: " + str(ex)[:50]
        return e

    zl = _zeit(letzte)
    e["letzte"] = letzte
    if zl:
        e["alter_min"] = (jetzt - zl).total_seconds() / 60.0

    # Groesste Pause der letzten sieben Tage - und die Frage dahinter:
    # war das ein AUSFALL des Sammlers, oder war einfach der Rechner aus?
    #
    # [20.08.2026] Vorher stand bei Bot-Entscheidungen dauerhaft "Luecke
    # 2,8 h - PRUEFEN". Die Luecke war echt, aber sie war der Nacht vom
    # 18.08. geschuldet, in der der Rechner aus war. Sie wird nie wieder
    # verschwinden, solange sie im Sieben-Tage-Fenster liegt.
    #
    #   > Eine Ampel, die dauerhaft gelb steht und nicht gruen werden KANN,
    #   > bringt einem bei, sie zu ignorieren.
    #
    # Deshalb wird jede Luecke gegen den Herzschlag des Bots gehalten
    # (evaluations). Schrieb der Bot in dieser Zeit auch nichts, war der
    # Rechner aus - das ist kein Ausfall des Sammlers. Nur eine Luecke, in
    # der der Bot NACHWEISLICH lief, ist eine, die man ihm ankreiden kann.
    if s.get("takt_min"):
        try:
            seit = (jetzt - timedelta(days=7)).isoformat()
            stempel = [_zeit(r[0]) for r in con.execute(
                "SELECT " + tz + " FROM " + tt + " WHERE " + tz + " >= ? "
                "ORDER BY " + tz, (seit,))]
            stempel = [x for x in stempel if x]
            luecke = 0.0
            erklaert = 0.0
            for i in range(1, len(stempel)):
                d = (stempel[i] - stempel[i - 1]).total_seconds() / 60.0
                if d <= s["takt_min"] * 6:
                    continue
                if _bot_lief(stempel[i - 1], stempel[i]):
                    luecke = max(luecke, d)          # echter Ausfall
                else:
                    erklaert = max(erklaert, d)      # Rechner war aus
            e["luecke_min"] = luecke
            e["bot_aus"] = erklaert
        except Exception:
            pass

    # Vollstaendigkeit der Pflichtfelder, gemessen an den letzten 500 Zeilen
    for feld in s["pflicht"]:
        try:
            leer = con.execute(
                "SELECT SUM(CASE WHEN " + feld + " IS NULL THEN 1 ELSE 0 END), "
                "COUNT(*) FROM (SELECT " + feld + " FROM " + t
                + " ORDER BY " + z + " DESC LIMIT 500)").fetchone()
            if leer and leer[1]:
                anteil = 100.0 * (leer[0] or 0) / leer[1]
                if anteil > 0.5:
                    e["leer"].append((feld, anteil))
        except Exception:
            e["leer"].append((feld, -1.0))       # Spalte gibt es gar nicht
    # [03.09.2026 - Befund 95] Eingefrorene Werte finden.
    #
    # Eine Luecke ist sichtbar. Ein alter Wert, der als frischer eingetragen
    # wird, sieht aus wie eine Messung. Am 02.09. schrieb markt_historie
    # waehrend eines Netzausfalls sechsmal hintereinander dieselben drei
    # Kurse - im vollkommen normalen 15-Minuten-Takt. Die Pruefung hier
    # meldete "OK", weil sie Zeilenzahl, Abstand und leere Felder ansah,
    # aber nie die Werte.
    #
    # Geprueft wird das Muster aus CLAUDE.md Abschnitt 0: Werte, die
    # identisch sein DUERFEN, aber nicht identisch sein SOLLTEN. Deshalb
    # muessen ALLE genannten Spalten gleichzeitig gleich sein - ein
    # einzelner Kurs kann zufaellig zweimal denselben Stand haben, drei
    # verschiedene Muenzen auf den Cent nicht.
    if s.get("nie_gleich"):
        sp = ", ".join(s["nie_gleich"])
        try:
            r = list(con.execute(
                "SELECT " + sp + " FROM (SELECT " + sp + ", " + z
                + " FROM " + t + " ORDER BY " + z + " DESC LIMIT 500)"
                " ORDER BY " + z))
            anz, lauf, laengste = 0, 0, 0
            vor = None
            for zeile in r:
                if vor is not None and zeile == vor and any(
                        x is not None for x in zeile):
                    anz += 1
                    lauf += 1
                    laengste = max(laengste, lauf)
                else:
                    lauf = 0
                vor = zeile
            if anz:
                e["wdh"] = (anz, len(r), laengste)
        except Exception:
            pass                       # Spalte fehlt - kein Grund fuer Alarm

    # Gescheiterte Auftraege der letzten 24 Stunden
    e["gescheitert"] = []
    if s.get("fehlerstatus"):
        spalte, schlecht = s["fehlerstatus"]
        try:
            seit = (jetzt - timedelta(hours=24)).isoformat()
            e["gescheitert"] = con.execute(
                "SELECT job_name, " + spalte + ", COUNT(*) FROM " + t
                + " WHERE " + z + " >= ? AND " + spalte + " IN ("
                + ",".join("?" * len(schlecht)) + ") GROUP BY 1,2",
                (seit,) + tuple(schlecht)).fetchall()
        except Exception:
            pass
    con.close()

    # Ampel
    gruende = []
    if e.get("gescheitert"):
        gruende.append(str(sum(x[2] for x in e["gescheitert"]))
                       + " gescheiterte Auftraege (24 h)")
    if s.get("takt_min"):
        if e["alter_min"] is None or e["alter_min"] > s["takt_min"] * 6:
            gruende.append("schreibt nicht mehr")
        if e["luecke_min"] and e["luecke_min"] > s["takt_min"] * 6:
            gruende.append("Luecke " + format(e["luecke_min"] / 60.0, ".1f") + " h")
    if not e["laeuft"] and s["prozess"] != "app.py" and not s.get("manuell"):
        gruende.append("Prozess laeuft nicht")
    # [24.08.2026] siehe _fremder_ordner(): ein Sammler kann laufen und
    # trotzdem in einen anderen data_store schreiben.
    if s["prozess"] != "app.py" and not s.get("manuell"):
        e["fremd"] = _fremder_ordner(s["prozess"])
        if e["fremd"]:
            gruende.append("laeuft aus FREMDEM Ordner: " + e["fremd"][0])
    if e["veraltet"]:
        gruende.append("ALTER PROGRAMMTEXT -> SAMMLER_NEUSTART.bat")
    if e["leer"]:
        gruende.append(str(len(e["leer"])) + " Feld(er) leer")
    if e["wdh"]:
        gruende.append(str(e["wdh"][0]) + " eingefrorene Zeile(n)")
    if not e["zeilen"]:
        gruende.append("keine Zeilen")

    if not gruende:
        e["ampel"] = GRUEN
    elif any(g.startswith(("schreibt", "keine", "Prozess", "laeuft aus"))
             for g in gruende):
        e["ampel"] = ROT
    else:
        e["ampel"] = GELB
    e["hinweis"] = ", ".join(gruende)
    return e


def bericht(kurz=False):
    jetzt = datetime.now(timezone.utc)
    prozesse = _laufende_prozesse()
    print("=" * 88)
    print("  SAMMLER-PRUEFUNG  -  schreibt jeder das, was die Auswertung braucht?")
    print("  Stand " + format(jetzt, "%d.%m.%Y %H:%M") + " UTC")
    print("=" * 88)
    print(NL + "  " + "Sammler".ljust(24) + "Zeilen".rjust(9)
          + "letzte".rjust(10) + "Luecke".rjust(9) + "   Status")
    print("  " + "-" * 84)

    erg = [pruefe(s, prozesse, jetzt) for s in SAMMLER]
    for e in erg:
        alt = ("-" if e["alter_min"] is None
               else (format(e["alter_min"], ".0f") + "m" if e["alter_min"] < 90
                     else format(e["alter_min"] / 60.0, ".1f") + "h"))
        lue = ("-" if not e["luecke_min"]
               else (format(e["luecke_min"], ".0f") + "m" if e["luecke_min"] < 90
                     else format(e["luecke_min"] / 60.0, ".1f") + "h"))
        print("  " + e["name"].ljust(24) + format(e["zeilen"], ",").rjust(9)
              + alt.rjust(10) + lue.rjust(9) + "   " + e["ampel"]
              + ("  (" + e["hinweis"] + ")" if e["hinweis"] else ""))

    if not kurz:
        print(NL + "=" * 88)
        print("  WOFUER JEDER GEBRAUCHT WIRD - und was fehlt")
        print("=" * 88)
        for e, s in zip(erg, SAMMLER):
            print(NL + "  " + e["name"] + "   [" + e["ampel"] + "]")
            print("    braucht man fuer : " + e["wofuer"])
            if s.get("manuell"):
                print("    Prozess          : " + s["prozess"]
                      + "  (startest DU von Hand - kein Dauerlaeufer)")
            else:
                print("    Prozess          : " + s["prozess"]
                      + ("  (laeuft)" if e["laeuft"] else "  (laeuft NICHT)"))
            print("    letzte Zeile     : " + str(e["letzte"])[:19])
            if e.get("veraltet"):
                from datetime import datetime as _d
                print("    ACHTUNG          : laeuft mit ALTEM Programmtext - "
                      "gestartet "
                      + _d.fromtimestamp(e["veraltet"][1]).strftime("%d.%m. %H:%M")
                      + ", Datei geaendert "
                      + _d.fromtimestamp(e["veraltet"][2]).strftime("%d.%m. %H:%M"))
                print("                       -> SAMMLER_NEUSTART.bat "
                      "doppelklicken")
            for jn, st, n in (e.get("gescheitert") or []):
                print("    GESCHEITERT      : " + str(jn) + "  " + str(st)
                      + "  " + str(n) + "x in 24 h")
            if e.get("bot_aus"):
                print("    Pause ohne Schuld: "
                      + format(e["bot_aus"] / 60.0, ".1f")
                      + " h, aber der Bot lief da auch nicht (Rechner aus)")
            if e["wdh"]:
                anz, ges, laengste = e["wdh"]
                print("    EINGEFROREN      : " + str(anz) + " von "
                      + str(ges) + " Zeilen gleich wie die Vorzeile ("
                      + format(100.0 * anz / ges, ".1f") + " %)")
                print("                       laengste Serie " + str(laengste)
                      + " Zeilen - alte Werte als frische eingetragen"
                      " (Befund 95)")
            if e["leer"]:
                for feld, anteil in e["leer"]:
                    if anteil < 0:
                        print("    LEER             : " + feld
                              + " - Spalte gibt es nicht")
                    else:
                        print("    LEER             : " + feld + " zu "
                              + format(anteil, ".0f") + " % ohne Wert")
            if s.get("spaeter"):
                print("    (Nachlauf-Felder werden erst spaeter gefuellt -"
                      " siehe nachlauf_rueckwirkend.py --stand)")

    # --- Buecher: Markdown und PDF muessen zusammen aktuell sein ---
    #
    # [20.08.2026] Sven: "sowohl das Bothandbuch als PDF und als Markdown,
    # genauso mit dem Zahlenbuch". Das Risiko ist nicht, dass eine Fassung
    # fehlt - es ist, dass sie AUSEINANDERLAUFEN. Wer das PDF liest,
    # waehrend das Markdown drei Abschnitte weiter ist, liest einen alten
    # Stand, ohne es zu merken. Deshalb steht es hier, wo Sven ohnehin
    # hinsieht, statt in einem Zettel, den man befolgen muesste.
    print(NL + "  " + "Buch".ljust(24) + "Markdown".rjust(12)
          + "PDF".rjust(12) + "   Stand")
    print("  " + "-" * 60)
    for md, pdf, wie in (("BOT-HANDBUCH.md", "BOT-HANDBUCH.pdf",
                          "python handbuch_pdf.py"),
                         ("ZAHLENBUCH.md", "ZAHLENBUCH.pdf",
                          "python zahlenbuch.py")):
        a = os.path.join(HIER, md)
        b = os.path.join(HIER, pdf)
        if not (os.path.exists(a) and os.path.exists(b)):
            print("  " + md.replace(".md", "").ljust(24)
                  + "eine Fassung FEHLT")
            continue
        ta, tb = os.path.getmtime(a), os.path.getmtime(b)
        gleich = abs(ta - tb) < 900          # 15 Minuten Toleranz
        print("  " + md.replace(".md", "").ljust(24)
              + datetime.fromtimestamp(ta).strftime("%d.%m %H:%M").rjust(12)
              + datetime.fromtimestamp(tb).strftime("%d.%m %H:%M").rjust(12)
              + "   " + (GRUEN if gleich else GELB
                         + "  -> " + wie))

    rot = sum(1 for e in erg if e["ampel"] == ROT)
    gelb = sum(1 for e in erg if e["ampel"] == GELB)
    print(NL + "=" * 88)
    if rot:
        print("  " + str(rot) + " Sammler sammeln NICHT. Was jetzt fehlt, fehlt")
        print("  hinterher fuer immer - eine Luecke laesst sich nicht nachtragen.")
    elif gelb:
        print("  Alle sammeln, aber " + str(gelb) + " mit Luecken oder leeren Feldern.")
    else:
        print("  Alle Sammler sammeln vollstaendig.")
    print("=" * 88)
    return 1 if rot else 0


# ----------------------------------------------------------------
#  Gegentest in beide Richtungen
# ----------------------------------------------------------------
def selbsttest():
    """Findet die Pruefung einen echten Ausfall - und meldet sie
    nichts Falsches, wenn alles in Ordnung ist?"""
    import tempfile
    fehler = 0
    jetzt = datetime.now(timezone.utc)
    print("=" * 74)
    print("SELBSTTEST - findet die Pruefung, was sie finden soll?")
    print("=" * 74)

    ordner = tempfile.mkdtemp()
    pfad = os.path.join(ordner, "test.db")
    con = sqlite3.connect(pfad)
    con.execute("CREATE TABLE t (ts_utc TEXT, wert REAL, pflichtfeld REAL)")

    def fuelle(zeilen):
        con.execute("DELETE FROM t")
        con.executemany("INSERT INTO t VALUES (?,?,?)", zeilen)
        con.commit()

    global HIER
    alt_hier = HIER
    HIER = ordner
    vorlage = {"name": "Test", "prozess": "gibtsnicht.py", "db": "test.db",
               "tabelle": "t", "zeit": "ts_utc", "takt_min": 5,
               "pflicht": ["pflichtfeld"], "wofuer": "Test"}

    faelle = [
        ("alles in Ordnung",
         [((jetzt - timedelta(minutes=5 * i)).isoformat(), 1.0, 1.0)
          for i in range(20)],
         {"leer": 0, "luecke_klein": True}),
        ("ein Pflichtfeld leer",
         [((jetzt - timedelta(minutes=5 * i)).isoformat(), 1.0,
           None if i % 2 else 1.0) for i in range(20)],
         {"leer": 1, "luecke_klein": True}),
        ("eine Luecke von sechs Stunden",
         [(jetzt.isoformat(), 1.0, 1.0),
          ((jetzt - timedelta(hours=6)).isoformat(), 1.0, 1.0),
          ((jetzt - timedelta(hours=6, minutes=5)).isoformat(), 1.0, 1.0)],
         {"leer": 0, "luecke_klein": False}),
        ("schreibt seit zwei Tagen nicht",
         [((jetzt - timedelta(days=2, minutes=5 * i)).isoformat(), 1.0, 1.0)
          for i in range(20)],
         {"leer": 0, "tot": True}),
        # [Befund 95] Beide Richtungen. Der erste Fall MUSS anschlagen,
        # der zweite darf es NICHT - sonst haette man ein Werkzeug, das
        # entweder blind ist oder immer schreit.
        ("eingefrorene Werte - MUSS anschlagen",
         [((jetzt - timedelta(minutes=5 * i)).isoformat(), 7.0, 7.0)
          for i in range(20)],
         {"leer": 0, "luecke_klein": True, "nie_gleich": ["wert", "pflichtfeld"],
          "wdh_min": 19, "wdh_lauf": 19}),
        ("wechselnde Werte - darf NICHT anschlagen",
         [((jetzt - timedelta(minutes=5 * i)).isoformat(),
           7.0 + i, 7.0 + i * 2) for i in range(20)],
         {"leer": 0, "luecke_klein": True, "nie_gleich": ["wert", "pflichtfeld"],
          "wdh_min": 0}),
        # Der heikle Fall: EINE Spalte wiederholt sich, die andere nicht.
        # Das ist Zufall und kein Einfrieren - es darf nicht melden.
        ("nur eine Spalte gleich - darf NICHT anschlagen",
         [((jetzt - timedelta(minutes=5 * i)).isoformat(), 7.0, 7.0 + i)
          for i in range(20)],
         {"leer": 0, "luecke_klein": True, "nie_gleich": ["wert", "pflichtfeld"],
          "wdh_min": 0}),
    ]
    # Der Prozess gilt in diesen Faellen als laufend - sonst wuerde jeder
    # Fall allein daran schon rot, und der GRUENE Weg bliebe ungeprueft.
    # Genau so entsteht ein Test, der immer besteht und nichts aussagt.
    laeuft_angeblich = "gibtsnicht.py"
    for name, zeilen, soll in faelle:
        fuelle(zeilen)
        v = dict(vorlage)
        if soll.get("nie_gleich"):
            v["nie_gleich"] = soll["nie_gleich"]
        e = pruefe(v, laeuft_angeblich, jetzt)
        ok = True
        if len(e["leer"]) != soll["leer"]:
            ok = False
        if "wdh_min" in soll:
            gefunden = e["wdh"][0] if e["wdh"] else 0
            if soll["wdh_min"] == 0 and gefunden:
                ok = False
            if soll["wdh_min"] and gefunden < soll["wdh_min"]:
                ok = False
        if soll.get("wdh_lauf") and (not e["wdh"]
                                     or e["wdh"][2] < soll["wdh_lauf"]):
            ok = False
        if soll.get("tot") and e["ampel"] != ROT:
            ok = False
        if soll.get("luecke_klein") is False and (e["luecke_min"] or 0) < 300:
            ok = False
        if soll.get("luecke_klein") is True and (e["luecke_min"] or 0) > 30:
            ok = False
        # Der erste Fall MUSS gruen sein - sonst prueft der Test nur, dass
        # alles rot wird.
        if name == "alles in Ordnung" and e["ampel"] != GRUEN:
            ok = False
        print("  " + ("OK  " if ok else "FEHL") + "  " + name.ljust(34)
              + "Ampel " + e["ampel"] + "   " + e["hinweis"][:40])
        if not ok:
            fehler += 1

    # Andere Richtung: meldet sie etwas, wo nichts ist?
    print(NL + "  Andere Richtung - erfundene Datenbank:")
    e = pruefe(dict(vorlage, db="gibt_es_nicht.db"), laeuft_angeblich, jetzt)
    ok = e["ampel"] == ROT and "fehlt" in e["hinweis"]
    print("    " + ("OK  " if ok else "FEHL") + "  fehlende Datenbank -> "
          + e["ampel"] + "  " + e["hinweis"][:40])
    if not ok:
        fehler += 1
    e = pruefe(dict(vorlage, tabelle="gibt_es_nicht"), laeuft_angeblich, jetzt)
    ok = e["ampel"] == ROT
    print("    " + ("OK  " if ok else "FEHL") + "  fehlende Tabelle   -> "
          + e["ampel"])
    if not ok:
        fehler += 1

    con.close()
    HIER = alt_hier
    # [20.08.2026] Diese Pruefung MUSS nach dem Zuruecksetzen von HIER
    # stehen. Vorher zeigte HIER auf den Testordner - _bot_lief fand dort
    # keine telemetrie.db, fiel in seinen Sicherheitszweig ("im Zweifel
    # Ausfall") und meldete "Bot lief", obwohl er nicht lief.
    #
    # Der Test schlug fehl und hatte trotzdem recht: nicht die Einordnung
    # war falsch, sondern der Test hatte sich selbst den Boden weggezogen.
    # Genau dafuer ist ein Gegentest da.
    # Die Einordnung der Luecken - gegen zwei BEKANNTE Zeitraeume
    print(NL + "  Luecken einordnen (lief der Bot da ueberhaupt?):")
    from datetime import datetime as _d
    faelle2 = [
        ("18.08. 07:02-09:51 (Rechner war aus)",
         _d(2026, 8, 18, 7, 2, tzinfo=timezone.utc),
         _d(2026, 8, 18, 9, 51, tzinfo=timezone.utc), False),
        ("letzte Stunde (Bot laeuft)",
         jetzt - timedelta(hours=1), jetzt, True),
    ]
    for name, a, b, soll in faelle2:
        ist = _bot_lief(a, b)
        ok = ist == soll
        print("    " + ("OK  " if ok else "FEHL") + "  " + name.ljust(38)
              + ("Bot lief" if ist else "Bot lief nicht"))
        if not ok:
            fehler += 1


    print(NL + ("SELBSTTEST BESTANDEN" if not fehler
                else str(fehler) + " FEHLER"))
    return 1 if fehler else 0


# ----------------------------------------------------------------
#  Die Dauerlaeufer starten, die nach einem Neustart fehlen
# ----------------------------------------------------------------
#
# [19.08.2026] Sven: "Muss ich alle 31 py-Dateien bei jedem neuen
# Botstart selbst aktivieren?"
#
# Nein - genau ZWEI muessen dauerhaft laufen. Die anderen sind
# Werkzeuge, die man aufruft, wenn man eine Antwort braucht. Damit
# man sich das nicht merken muss, macht dieser Aufruf es selbst:
#
#     python sammler_pruefen.py --starten
#
# Er startet nur, was nicht schon laeuft, und sieht danach nach, ob
# wirklich etwas passiert ist.
DAUERLAEUFER = [
    ("Schatten-Universum", "schatten_universum.py", ["--dauer"]),
    ("Positionsverlauf", "positionsverlauf.py", []),
]


def _veraltet(skript):
    """Laeuft dieser Sammler noch mit einem aelteren Programmtext?

    [20.08.2026] Der haeufigste Stolperstein in diesem Projekt: der
    Prozess laeuft, die Ampel ist gruen - und er arbeitet trotzdem mit
    dem Code von vor der Reparatur. Am 19.08. schrieb der Schatten-
    Sammler deshalb nach der Regime-Reparatur weiter leere Felder.

    Gibt (PID, Startzeit, Aenderungszeit) zurueck, wenn die Datei NACH
    dem Start geaendert wurde - sonst None.
    """
    try:
        import psutil
    except Exception:
        return None
    pfad = os.path.join(HIER, skript)
    if not os.path.exists(pfad):
        return None
    geaendert = os.path.getmtime(pfad)
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if "python" not in (p.info["name"] or "").lower():
                continue
            if not any(skript in str(x) for x in (p.info["cmdline"] or [])):
                continue
            if geaendert > p.info["create_time"]:
                return (p.info["pid"], p.info["create_time"], geaendert)
        except Exception:
            continue
    return None


def _beenden(skript, sag):
    """Beendet die Prozesse dieses Sammlers. Nur auf ausdruecklichen
    Wunsch (--neustart) - der Bot tut das nie von selbst."""
    try:
        import psutil
    except Exception:
        sag("  psutil fehlt - kann nicht beenden")
        return 0
    weg = 0
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "python" not in (p.info["name"] or "").lower():
                continue
            if not any(skript in str(x) for x in (p.info["cmdline"] or [])):
                continue
            p.terminate()
            try:
                p.wait(timeout=8)
            except Exception:
                p.kill()
            weg += 1
        except Exception:
            continue
    return weg


def neustart():
    """Beendet die Dauerlaeufer und startet sie frisch.

    Gedacht fuer genau einen Fall: an einem Sammler wurde etwas
    repariert, und er laeuft noch mit dem alten Programmtext.
    """
    import time
    print("=" * 74)
    print("DAUERLAEUFER NEU STARTEN")
    print("=" * 74)
    beendet = []
    for name, skript, _a in DAUERLAEUFER:
        weg = _beenden(skript, print)
        print(NL + "  " + name.ljust(22)
              + (str(weg) + " Prozess(e) beendet" if weg else "lief nicht"))
        if weg:
            beendet.append((name, skript))

    # [FIX 20.08.2026] Warten, bis sie WIRKLICH aus der Prozessliste weg sind.
    #
    # Sven: "beim zweiten Mal sagt er 2 Prozesse beendet, aber startet sie
    # nicht". Genau das war es: terminate() bittet den Prozess zu gehen, er
    # braucht dafuer einen Moment. starten() fragt danach die Prozessliste ab,
    # sieht den Sterbenden noch, sagt "laeuft schon - nichts zu tun" und
    # startet nichts. Danach war gar keiner mehr da.
    #
    # Dass es beim ERSTEN Mal ging, machte es tueckisch: es hing daran, wie
    # schnell Windows den Eintrag raeumt.
    #
    # Deshalb wird jetzt nachgesehen statt gewartet-und-gehofft.
    if beendet:
        print(NL + "  Warten, bis sie wirklich aus der Prozessliste sind ...")
        for versuch in range(20):                      # bis zu 10 Sekunden
            liste = _laufende_prozesse()
            uebrig = [n for n, s in beendet if s.lower() in liste]
            if not uebrig:
                print("    alle weg nach " + format(versuch * 0.5, ".1f") + " s")
                break
            time.sleep(0.5)
        else:
            print("    ACHTUNG: noch in der Liste: " + ", ".join(uebrig))
            print("    Sie werden trotzdem gestartet - notfalls Rechner neu"
                  " starten.")
    print()
    return starten(trotzdem={s for _n, s in beendet})


def _laeuft_hier(skript):
    """[SAMMLER EIGENER ORDNER 14.10.2026] Laeuft `skript` aus GENAU diesem Ordner (HIER)?

    Massgeblich ist der Pfad des Skripts in der Befehlszeile, ersatzweise der
    Arbeitsordner des Prozesses. Ein gleichnamiger Sammler aus einem anderen
    Bot-Ordner zaehlt NICHT.
    """
    import psutil
    hier = os.path.normcase(os.path.abspath(HIER))
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "python" not in (p.info["name"] or "").lower():
                continue
            teile = [str(x) for x in (p.info["cmdline"] or [])]
            treffer = [t for t in teile if t.lower().endswith(skript.lower())]
            if not treffer:
                continue
            ordner = os.path.dirname(os.path.abspath(treffer[0]))
            if not os.path.isabs(treffer[0]) or os.path.dirname(treffer[0]) == "":
                ordner = p.cwd()
            if os.path.normcase(os.path.abspath(ordner)) == hier:
                return True
        except Exception:
            continue
    return False


def starten(melden=None, trotzdem=()):
    """Startet die Dauerlaeufer, die gerade nicht laufen.

    melden: Funktion fuer eine Zeile Text. Ohne Angabe wird gedruckt -
    der Bot uebergibt hier sein Log, damit die Meldungen dort landen,
    wo Sven ohnehin hinsieht, statt in einer Konsole, die keiner liest.
    """
    import subprocess
    import time

    sag = melden or (lambda z: print(z))
    prozesse = _laufende_prozesse()
    if melden is None:
        print("=" * 74)
        print("DAUERLAEUFER - starten, was nach dem Neustart fehlt")
        print("=" * 74)
    gestartet = []
    for name, skript, args in DAUERLAEUFER:
        # `trotzdem` kommt vom Neustart: diese Sammler wurden gerade
        # beendet. Steht einer dann noch in der Prozessliste, ist das ein
        # Nachhall, kein laufender Sammler - er wird gestartet.
        # [SAMMLER EIGENER ORDNER 14.10.2026] Vorher: skript.lower() in prozesse - zaehlte auch Sammler aus
        # FREMDEN Ordnern (v6 hielt v7 seit 02.10. vom Positionsverlauf ab).
        if _laeuft_hier(skript) and skript not in trotzdem:
            alt_stand = _veraltet(skript)
            if alt_stand:
                from datetime import datetime as _dt
                sag("  " + name.ljust(22) + "laeuft - ABER mit altem "
                    "Programmtext!")
                sag("      gestartet " + _dt.fromtimestamp(
                    alt_stand[1]).strftime("%d.%m. %H:%M") + ", Datei geaendert "
                    + _dt.fromtimestamp(alt_stand[2]).strftime("%d.%m. %H:%M"))
                sag("      -> SAMMLER_NEUSTART.bat doppelklicken")
            else:
                sag("  " + name.ljust(22) + "laeuft schon - nichts zu tun")
            continue
        pfad = os.path.join(HIER, skript)
        if not os.path.exists(pfad):
            sag("  " + name.ljust(22) + "FEHLT: " + skript)
            continue
        try:
            subprocess.Popen([sys.executable, pfad] + args, cwd=HIER,
                             creationflags=getattr(subprocess,
                                                   "CREATE_NO_WINDOW", 0),
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            sag("  " + name.ljust(22) + "gestartet ...")
            gestartet.append((name, skript))
        except Exception as e:
            sag("  " + name.ljust(22) + "START FEHLGESCHLAGEN: " + str(e)[:50])

    if not gestartet:
        sag("  Alles lief bereits.")
        return 0

    # Nachsehen, ob wirklich etwas passiert ist - kein stilles Scheitern.
    # Zaehlen reicht nicht: der Start kann melden "ok" und der Prozess
    # zwei Sekunden spaeter an einem Importfehler sterben.
    sag("  Nachsehen, ob sie wirklich laufen (15 Sekunden) ...")
    time.sleep(15)
    jetzt = _laufende_prozesse()
    fehler = 0
    for name, skript in gestartet:
        da = skript.lower() in jetzt
        sag("    " + ("OK  " if da else "FEHL") + "  " + name.ljust(22)
            + ("laeuft" if da else "ist wieder weg - von Hand starten und "
                                   "die Meldung lesen: python " + skript))
        if not da:
            fehler += 1
    return 1 if fehler else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Prueft alle Sammler")
    p.add_argument("--kurz", action="store_true", help="nur die Ampel")
    p.add_argument("--starten", action="store_true",
                   help="fehlende Dauerlaeufer starten")
    p.add_argument("--neustart", action="store_true",
                   help="Dauerlaeufer beenden und frisch starten")
    p.add_argument("--selbsttest", action="store_true",
                   help="Gegentest in beide Richtungen")
    a = p.parse_args()
    if a.selbsttest:
        sys.exit(selbsttest())
    if a.neustart:
        rc = neustart()
        print()
        # [20.08.2026] Sven: "Pruefer 1 war detaillierter, richte mir den
        # neuen ebenfalls so an, damit man sieht, welcher Waechter fuer was
        # da ist." Also auch hier die lange Fassung - sie sagt zu jedem
        # Sammler, WOFUER er gebraucht wird. Nach einem Neustart ist das
        # der Moment, in dem man genau das wissen will.
        sys.exit(bericht(kurz=False) or rc)
    if a.starten:
        rc = starten()
        print()
        sys.exit(bericht(kurz=False) or rc)
    sys.exit(bericht(kurz=a.kurz))
