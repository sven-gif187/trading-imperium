"""
lage_erzeugen.py — schreibt LAGE.md: was gerade läuft und welche Daten es gibt
==============================================================================

WARUM ES DIESES PROGRAMM GIBT

Sven dokumentiert seit Monaten alles: BOT-HANDBUCH.md, ENTWICKLERHANDBUCH.md,
GEFUNDENE-PROBLEME.md, ARCHITEKTUR.md, INVENTAR.md, Tickets. Trotzdem geht in
jeder neuen Sitzung Wissen verloren.

Der Grund ist nicht fehlende Dokumentation, sondern eine fehlende EINGANGSTÜR.
Wer neu dazukommt (Mensch wie Assistent), muss sich den aktuellen Zustand aus
mehreren tausend Zeilen zusammensuchen — und sucht dabei zwangsläufig am
Falschen vorbei. Konkreter Fall vom 14.08.: Der Forschungs-Sammler erfasst
seit Wochen die beobachteten Münzen mit Orderbuch, Ticker und Spread. Das stand in
05_LIVE-CAPTURE-SPEZIFIKATION.md — gefunden wurde es erst durch Zufall.

Dieses Programm erzeugt EINE kurze Seite, die sich NICHT aus Erinnerung
speist, sondern aus dem tatsächlichen Zustand der Festplatte: laufende
Prozesse, vorhandene Datenbanken mit Zeilenzahlen, Epochen, Regel-Schalter,
Messreihen. Sie ist damit per Konstruktion aktuell.

REGEL: LAGE.md wird NICHT von Hand gepflegt. Wer etwas ändert, ändert den
Bot — und der nächste Lauf schreibt es von selbst auf.

Es liest nur. Es ändert nichts am Bot.

AUFRUF
    python lage_erzeugen.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "LAGE.md")


def zahl(con, tabelle, wo=""):
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabelle} {wo}").fetchone()[0]
    except Exception:
        return None


def groesse(pfad):
    try:
        b = os.path.getsize(pfad)
        for e in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.0f} {e}"
            b /= 1024
        return f"{b:.1f} TB"
    except Exception:
        return "—"


def laeuft(muster):
    """Läuft ein Prozess, dessen Befehlszeile das Muster enthält?

    [21.09.2026] `wmic` gibt es seit Windows 11 24H2 nicht mehr. Der
    Aufruf warf FileNotFoundError, und LAGE.md zeigte unter "Was
    läuft?" nur noch Striche. Deshalb zuerst psutil.
    """
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil is not None:
        try:
            for p in psutil.process_iter(["cmdline"]):
                try:
                    cl = " ".join(p.info["cmdline"] or [])
                except Exception:
                    continue      # Prozess weg oder kein Zugriff
                if muster.lower() in cl.lower():
                    return True
            return False
        except Exception:
            return None

    try:
        out = subprocess.run(
            ["wmic", "process", "get", "CommandLine"],
            capture_output=True, text=True, errors="replace", timeout=25).stdout
        return any(muster.lower() in z.lower() for z in out.splitlines())
    except Exception:
        return None


def main():
    t = []
    jetzt = datetime.now(timezone.utc)
    t += [
        "# LAGE — was gerade läuft",
        "",
        f"**Automatisch erzeugt {jetzt.strftime('%d.%m.%Y %H:%M')} UTC mit "
        f"`lage_erzeugen.py`. Nicht von Hand ändern.**",
        "",
        "Diese Seite ist die Eingangstür ins Projekt. Sie beantwortet drei",
        "Fragen: Was läuft? Welche Daten existieren? Was ist gerade eingefroren?",
        "",
        "Für das *Warum* siehe `BOT-HANDBUCH.md`, für offene Punkte",
        "`GEFUNDENE-PROBLEME.md`, für die Chronik `ENTWICKLERHANDBUCH.md`.",
        "", "---", "",
        "## Laufende Prozesse", "",
        "| Was | Status |", "|---|---|",
    ]
    for name, muster in [("Bot (`app.py`)", "app.py"),
                         ("Forschungs-Sammler", "job_forschung_capture"),
                         ("Täglicher Sammler", "job_sammler"),
                         ("Schatten-Universum", "schatten_universum")]:
        z = laeuft(muster)
        t.append(f"| {name} | {'läuft' if z else ('läuft nicht' if z is False else '?')} |")

    # ---------------- Konfiguration ----------------
    t += ["", "## Konfiguration", "", "| | |", "|---|---|"]
    try:
        cfg = json.load(open(os.path.join(HIER, "data_store", "config.json"),
                             encoding="utf-8"))
        tr = cfg.get("trading", {})
        t += [
            f"| Modus | {tr.get('mode')} |",
            f"| Münzen | {', '.join(tr.get('coins') or [])} |",
            f"| Zeitrahmen | {tr.get('default_timeframe')} |",
            f"| Takt | {tr.get('loop_interval_seconds')} s |",
            f"| Aktiver Modus | {(cfg.get('modes') or {}).get('active_mode')} |",
        ]
        rm = cfg.get("regel_modi")
        if rm:
            nicht = [f"`{k}`={v}" for k, v in rm.items() if v != "ACTIVE"]
            t.append(f"| Regel-Schalter | {', '.join(nicht) if nicht else 'alle ACTIVE'} |")
        else:
            t.append("| Regel-Schalter | **BLOCK FEHLT — alle fallen auf ACTIVE!** |")
    except Exception as e:
        t.append(f"| Fehler | {str(e)[:60]} |")

    # ---------------- Epochen ----------------
    t += ["", "## Epochen (Regelwerks-Abschnitte)", "",
          "Auswertungen dürfen **nur innerhalb** einer Epoche verglichen werden.",
          "", "| Epoche | ab (UTC) |", "|---|---|"]
    try:
        eps = json.load(open(os.path.join(HIER, "config_epochs.json"),
                             encoding="utf-8"))["epochs"]
        for e in sorted(eps, key=lambda x: x["start"]):
            t.append(f"| `{e['id']}` | {e['start'][:16]} |")
        t += ["", f"**Aktuelle Epoche: `{sorted(eps, key=lambda x: x['start'])[-1]['id']}`**"]
    except Exception as e:
        t.append(f"| Fehler | {str(e)[:60]} |")

    # ---------------- Daten ----------------
    t += ["", "## Vorhandene Daten", "", "| Quelle | Umfang |", "|---|---|"]

    tel = os.path.join(HIER, "data_store", "telemetrie.db")
    if os.path.exists(tel):
        con = sqlite3.connect(tel)
        for tab, bez in [("evaluations", "Kaufprüfungen"),
                         ("markt_historie", "Marktdaten-Zeitreihe"),
                         ("schatten_regeln", "Schatten-Notizen"),
                         ("schatten_exits", "Schatten-Ausstiege"),
                         ("lern_ereignisse", "Lern-Ereignisse"),
                         ("jobs", "Hintergrund-Läufe")]:
            n = zahl(con, tab)
            if n is not None:
                t.append(f"| `telemetrie.db` → {bez} | {n} Zeilen |")
        for regel in ("ml_model", "ensemble_technical"):
            n = zahl(con, "schatten_regeln", f"WHERE regel='{regel}'")
            if n:
                t.append(f"| … davon `{regel}` | {n} |")
        con.close()

    su = os.path.join(HIER, "data_store", "schatten_universum.db")
    if os.path.exists(su):
        con = sqlite3.connect(su)
        n = zahl(con, "signale")
        m = con.execute("SELECT COUNT(DISTINCT muenze) FROM signale").fetchone()[0] if n else 0
        t.append(f"| `schatten_universum.db` | {n} Signale auf {m} Münzen |")
        con.close()

    nl = os.path.join(HIER, "data_store", "nachlauf.db")
    if os.path.exists(nl):
        con = sqlite3.connect(nl)
        try:
            n = zahl(con, "nachlauf")
            # Nur die 24-Stunden-Spalte melden: sie ist der Engpass. Die
            # 1- und 4-Stunden-Werte fuellen sich schnell, die eigentliche
            # Frage (war der Stop zu eng?) haengt an 24 und 48 Stunden.
            f24 = con.execute(
                "SELECT COUNT(r24h) FROM nachlauf WHERE art='exit'").fetchone()[0]
            ex = con.execute(
                "SELECT COUNT(*) FROM nachlauf WHERE art='exit'").fetchone()[0]
            t.append(f"| `nachlauf.db` | {n} Ereignisse, davon {ex} Ausstiege "
                     f"({f24} mit 24-h-Kurs) |")
        except Exception:
            pass
        con.close()

    try:
        j = json.load(open(os.path.join(HIER, "data_store", "trades_v5.json"),
                           encoding="utf-8"))
        j = j if isinstance(j, list) else j.get("trades", [])
        verk = [x for x in j if x.get("pnl") is not None]
        t.append(f"| `trades_v5.json` | {len(j)} Einträge, {len(verk)} Verkäufe |")
    except Exception:
        pass

    cap = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")
    if os.path.isdir(cap):
        tage = sorted(d for d in os.listdir(cap) if d.startswith("20"))
        if tage:
            letzter = os.path.join(cap, tage[-1])
            dateien = len(os.listdir(letzter))
            muenzen = len({f.split("_")[1].split("USD")[0]
                           for f in os.listdir(letzter) if "_" in f and "USD" in f})
            t.append(f"| Forschungs-Sammler | {len(tage)} Tage, zuletzt {tage[-1]} "
                     f"({dateien} Dateien, {muenzen} Münzen) |")
            t += ["", f"**Der Sammler erfasst je Münze:** Orderbuch, Ticker "
                  f"(mit `spread_bp`), Trades, Funding, offene Positionen — "
                  f"alle ~60 Sekunden."]

    # ---------------- Messwerkzeuge ----------------
    t += ["", "## Messwerkzeuge (alle nur lesend)", "",
          "| Aufruf | beantwortet |", "|---|---|"]
    for datei, frage in [
            ("epoch_report.py", "Ergebnis je Regelwerks-Epoche"),
            ("ml_notizbuch_auswertung.py", "Hat das KI-Modell Vorhersagekraft?"),
            ("ensemble_notizbuch_auswertung.py", "Würde ein echter technical-Wert Käufe ändern?"),
            ("schatten_universum.py --status", "Was auf allen beobachteten Münzen gesammelt wurde"),
            ("telemetrie_pruefen.py", "Doppelverkäufe, Positionsabgleich"),
            ("regel_waechter_bestaetigen.py", "Stehen die Regel-Schalter wie hinterlegt?"),
            ("stoploss_analyse.py", "Warum laufen Positionen ins Minus?"),
            ("lage_erzeugen.py", "Diese Seite neu schreiben")]:
        if os.path.exists(os.path.join(HIER, datei.split()[0])):
            t.append(f"| `python {datei}` | {frage} |")

    # ---------------- Sicherung ----------------
    t += ["", "## Sicherung", "", "| | |", "|---|---|"]
    g = os.path.join(HIER, ".git")
    if os.path.isdir(g):
        try:
            log = subprocess.run(["git", "log", "-1", "--format=%h %ci %s"],
                                 cwd=HIER, capture_output=True, text=True,
                                 errors="replace", timeout=20).stdout.strip()
            t.append(f"| Git | letzter Stand: {log[:80]} |")
        except Exception:
            t.append("| Git | vorhanden |")
    sich = r"C:\Users\<BENUTZER>\OneDrive\trading_imperium_sicherung"
    if os.path.isdir(sich):
        try:
            n = sum(len(f) for _, _, f in os.walk(sich))
            mt = time.strftime("%d.%m. %H:%M",
                               time.localtime(os.path.getmtime(sich)))
            t.append(f"| OneDrive-Kopie | {n} Dateien, zuletzt {mt} |")
        except Exception:
            pass
    t += ["", "Sicherung erneuern: `python sicherung.py <Ziel>`"]

    t += ["", "---", "",
          "*Diese Seite wird von `lage_erzeugen.py` erzeugt. Änderungen von "
          "Hand gehen beim nächsten Lauf verloren.*", ""]

    with open(ZIEL, "w", encoding="utf-8") as f:
        f.write("\n".join(t))
    print(f"Geschrieben: {os.path.basename(ZIEL)} ({groesse(ZIEL)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
