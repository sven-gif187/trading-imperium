# -*- coding: utf-8 -*-
"""tagescheck.py - einmal am Tag das ganze System durchsehen.

[CLEANUP-KEEP]

Angelegt 28.09.2026 auf Svens Auftrag: "richte bitte eine automatische
ueberpruefung an damit er taeglich einmal das komplette system
ueberprueft nach bugs sucht und schaut ob auch wirklich alle daten
gesammelt werden - fuer v7 wie auch v6".

NUR LESEND. Startet nichts, beendet nichts, aendert keine Datenbank,
fasst keine Einstellung an. Es schreibt genau vier Dinge, alle eigene:

    data_store/tagescheck.log              ein Block je Lauf
    data_store/tagescheck_bericht.txt      der letzte Bericht, lesbar
    data_store/tagescheck_stand.json       Gedaechtnis fuer "schon gemeldet"
    tickets.txt                            nur bei einer NEUEN Abweichung

Damit ist es freeze-sicher: es aendert nichts am Verhalten des Bots und
braucht keine Epochengrenze.

WARUM ES DIESE DATEI GIBT, OBWOHL dauercheck.py SCHON EXISTIERT
---------------------------------------------------------------
dauercheck.py (18.08.2026) prueft den BETRIEB: laeuft der Bot, stehen
die Regel-Schalter, wachsen die Zaehler. Es lief bis zum 01.09.2026 als
geplante Aufgabe alle drei Stunden - dann kam der Umzug auf diesen
Rechner, und die Aufgabe blieb auf dem Laptop zurueck. Nachgesehen am
28.09.: in der Aufgabenplanung existiert kein "Dauercheck" mehr, und im
v7-Ordner gibt es nicht einmal eine dauercheck.log - dort hat es nie
gelaufen.

Genau dieser Ausfall ist der Grund fuer die Pruefung "Geplante
Aufgaben" weiter unten. Ein Waechter, der lautlos verschwinden kann,
ist kein Waechter.

Diese Datei ist der Rahmen um dauercheck.py: sie ruft es auf, ergaenzt
die Fragen, die es nicht stellt, und schreibt EINEN Bericht mit EINER
Stimme statt zwei Logs, die man nebeneinanderlegen muss.

WAS GEPRUEFT WIRD - und was jeweils als "richtig" gilt
------------------------------------------------------
Jede Pruefung nennt ihre Erwartung. Eine Pruefung ohne Erwartung ist
keine Pruefung, sondern eine Anzeige.

  A  Betrieb          die acht Pruefungen von dauercheck.py
  B  Sammler          sammler_pruefen.py - schreibt jeder Sammler das,
                      was die spaetere Auswertung braucht?
  C  Uebersetzbarkeit jede .py-Datei laesst sich uebersetzen. Eine
                      Datei, die seit einer Bearbeitung kaputt ist,
                      faellt sonst erst beim naechsten Start auf
  D  Datenbanken      sqlite quick_check ohne Befund
  E  Steuerzeichen    kein Zeichen unter 32 in .md/.txt/.json ausser
                      Tab, Zeilenumbruch, Wagenruecklauf
  F  Geplante Aufgaben jede Aufgabe dieses Ordners existiert, zeigt auf
                      vorhandene Dateien, ist nicht abgeschaltet und
                      lief innerhalb ihres Takts
  G  Selbstpruefung   diese Pruefung selbst ist eingerichtet und lief

DREI STUFEN, NICHT ZWEI
-----------------------
    OK         wie erwartet
    HINSEHEN   auffaellig, aber kein Ausfall - steht im Bericht,
               erzeugt KEIN Ticket
    FEHLER     Ausfall - erzeugt ein Ticket, aber nur beim ersten Mal

Die Trennung ist der Grund, warum diese Art Pruefung ueberhaupt
gelesen wird. Die erste Fassung von prozess_frische.py meldete jeden
Lauf, dauercheck.py meldete am ersten Abend dreimal Fehler, die keine
waren - danach liest niemand mehr hin. Gemeldet wird nur, was ABWEICHT,
und ein Zustandswechsel nur EINMAL.

Aufruf:
    python tagescheck.py                einmal pruefen
    python tagescheck.py --kurz         nur das Ergebnis in einer Zeile
    python tagescheck.py --einrichten   taegliche Aufgabe anlegen
    python tagescheck.py --pruefen      nachsehen, ob sie eingerichtet ist
    python tagescheck.py --entfernen    Aufgabe wieder loeschen
    python tagescheck.py --selbsttest   Gegentest in beide Richtungen

Rueckgabewert: 0 = kein Fehler, 1 = Fehler gefunden.
"""
import glob
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.path.join(HIER, "data_store")
LOG = os.path.join(DATEN, "tagescheck.log")
BERICHT = os.path.join(DATEN, "tagescheck_bericht.txt")
MERKER = os.path.join(DATEN, "tagescheck_stand.json")
GRUNDSTAND = os.path.join(DATEN, "tagescheck_aufgaben.json")
TICKETS = os.path.join(HIER, "tickets.txt")

OK = "OK"
HIN = "HINSEHEN"
FEHL = "FEHLER"

# Ordner, die beim Durchsuchen aussen bleiben - und warum:
#   __pycache__, .git, .venv   keine Quelltexte, die jemand pflegt
#   .claude                    enthaelt Arbeitskopien des ganzen Ordners
#                              (worktrees); ein Fund dort waere ein Fund
#                              in einer Kopie, nicht im Bot
#   v4_referenz                der V4-Referenzbot, bewusst eingefroren
AUS_ORDNER = {"__pycache__", ".git", ".claude", ".venv", "venv",
              "node_modules", "v4_referenz", "site-packages"}

# Dateien, die kaputt sein DUERFEN: sie sind als Beweisstueck einer
# frueheren Beschaedigung aufbewahrt. ENTWICKLERHANDBUCH_KORRUPT_
# 28072026.md enthaelt Nullbytes - absichtlich, sie zeigen den Schaden.
AUS_DATEI_MUSTER = ("korrupt", "_kaputt", "beschaedigt")

# Eine Datenbank im Modus "delete" sperrt waehrend der Pruefung ihre
# Schreiber aus. Gemessen am 28.09.2026: 30 MB = 2,5 s Sperre, der
# Vorgabe-Zeitausfall von sqlite3 liegt bei 5 s. Ab 40 MB wird es also
# knapp - dann lieber nicht pruefen als dem Sammler ins Handwerk
# pfuschen. WAL-Datenbanken sind davon nicht betroffen: dort lesen und
# schreiben zwei Seiten gleichzeitig (telemetrie.db, 676 MB in v6,
# 32 s Pruefzeit, ohne jede Sperre).
DB_SPERRGRENZE_MB = 40.0

# Ergebniscodes der Aufgabenplanung, die KEIN Fehler sind.
AUFGABE_CODES_GUT = {
    0: "letzter Lauf ohne Fehler",
    267009: "laeuft gerade",
    267011: "noch nie gelaufen",
    # 0x800710E0 - "der Bediener hat die Anforderung abgelehnt". Bei
    # einer Waechter-Aufgabe, deren Ziel dauerhaft laeuft, ist das der
    # Normalfall: der vorige Lauf war noch da, als der naechste Takt
    # kam, und die Aufgabenplanung hat den zweiten Start verweigert.
    # Nachgesehen am 28.09. an ForschungCapture (Takt 10 Minuten,
    # Daemon laeuft seit 28,8 Stunden durch): genau dieser Code.
    2147946720: "voriger Lauf lief noch, neuer Start abgelehnt - normal "
                "bei einem Waechter",
}

# Nach welchen Namen wird in der Aufgabenplanung gesucht.
#
# WARUM MUSTER UND NICHT ALLES
# Get-ScheduledTask ohne -TaskName liest erst alle Aufgaben des
# Rechners (hier ueber 200, samt Windows-Wartung und OneDrive) und
# wirft danach weg. Am 16.09.2026 gemessen: ueber drei Minuten, dreimal
# in den Zeitausfall gelaufen. Mit -TaskName filtert der Dienst selbst.
AUFGABEN_MUSTER = ["TI6-*", "TI7-*", "TI-*", "SchattenUniversum*",
                   "ForschungCapture*", "Tagescheck*", "Dauercheck*"]


# ----------------------------------------------------------------
#  Grundwerkzeug
# ----------------------------------------------------------------
def notiz(text, zeilen=None):
    """Erst schreiben, dann anzeigen - print nie ungeschuetzt.

    Unter pythonw.exe ist sys.stdout None; ein blankes print() beendet
    das Programm. Diese Falle hat am 14.08.2026 das Schatten-Universum
    lahmgelegt.
    """
    if zeilen is not None:
        zeilen.append(text)
    try:
        if sys.stdout is not None:
            print(text)
    except Exception:
        pass


def log_anhaengen(zeilen):
    marke = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write("\n===== " + marke + " =====\n")
            for z in zeilen:
                f.write(z + "\n")
    except OSError:
        pass


def sicher_schreiben(pfad, text):
    """Erst daneben, dann umlegen - eine halbe Datei gibt es nicht."""
    tmp = pfad + ".tmp"
    try:
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def voriger_stand():
    try:
        with io.open(MERKER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def zeile(bereich, name, stufe, befund, erwartung=""):
    return {"bereich": bereich, "name": name, "stufe": stufe,
            "befund": befund, "erwartung": erwartung}


def _python(*teile):
    """Ein Unterprogramm dieses Ordners aufrufen. (rc, ausgabe)."""
    try:
        f = subprocess.run([sys.executable] + list(teile), cwd=HIER,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        return f.returncode, (f.stdout or "") + (f.stderr or "")
    except subprocess.TimeoutExpired:
        return None, "Zeitausfall nach 600 s"
    except Exception as ex:
        return None, "%s: %s" % (type(ex).__name__, ex)


def ps(befehl, zeit=300):
    try:
        f = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=zeit)
        return f.returncode, (f.stdout or "") + (f.stderr or "")
    except Exception as ex:
        return 1, "%s: %s" % (type(ex).__name__, ex)


# ----------------------------------------------------------------
#  A - Betrieb: die acht Pruefungen von dauercheck.py
# ----------------------------------------------------------------
def betrieb():
    """Ruft dauercheck.py auf, statt seine acht Pruefungen nachzubauen.

    Mit --kein-ticket, damit nicht zwei Werkzeuge dasselbe melden. Der
    Bericht hier hat EINE Stimme; das Ticket schreibt diese Datei.
    """
    pfad = os.path.join(HIER, "dauercheck.py")
    if not os.path.exists(pfad):
        return [zeile("Betrieb", "dauercheck.py", FEHL, "Datei fehlt",
                      "liegt im Ordner")]
    rc, aus = _python("dauercheck.py", "--bericht", "--kein-ticket")
    if rc is None:
        return [zeile("Betrieb", "dauercheck.py", FEHL, aus,
                      "laeuft durch")]

    erg = []
    for roh in aus.splitlines():
        # notiz() setzt "[<zeitstempel>] " davor - abschneiden.
        z = roh.split("] ", 1)[1] if "] " in roh else roh
        kopf = z[2:6]
        if kopf not in ("OK  ", "FEHL"):
            continue
        rest = z[7:]
        erg.append(zeile("Betrieb", rest[:20].strip(),
                         OK if kopf == "OK  " else FEHL,
                         rest[20:].strip()))
    if not erg:
        return [zeile("Betrieb", "dauercheck.py", FEHL,
                      "keine auswertbare Zeile zurueck (rc=%s)" % rc,
                      "gibt je Pruefung eine Zeile aus")]
    return erg


# ----------------------------------------------------------------
#  B - Sammler: schreibt jeder, was die Auswertung braucht?
# ----------------------------------------------------------------
def sammler():
    """sammler_pruefen.py --kurz auswerten.

    Dessen Ausgabe wird NICHT nach Spalten zerlegt, sondern die Zeilen
    mit FEHLT oder PRUEFEN werden woertlich uebernommen. Eine Tabelle
    nachzuparsen bricht beim naechsten Umbau; ein Zitat nicht.
    """
    pfad = os.path.join(HIER, "sammler_pruefen.py")
    if not os.path.exists(pfad):
        return [zeile("Sammler", "sammler_pruefen.py", FEHL, "Datei fehlt",
                      "liegt im Ordner")]
    rc, aus = _python("sammler_pruefen.py", "--kurz")
    if rc is None:
        return [zeile("Sammler", "sammler_pruefen.py", FEHL, aus,
                      "laeuft durch")]

    erg = []
    for roh in aus.splitlines():
        z = " ".join(roh.split())
        if not z or z.startswith("=") or z.startswith("-"):
            continue
        if "FEHLT" in z:
            erg.append(zeile("Sammler", z.split()[0], FEHL, z,
                             "sammelt und schreibt"))
        elif "PRUEFEN" in z:
            erg.append(zeile("Sammler", z.split()[0], HIN, z,
                             "sammelt ohne Luecke"))
    if not erg:
        erg.append(zeile("Sammler", "alle", OK,
                         "alle Sammler sammeln vollstaendig",
                         "sammelt und schreibt"))
    elif rc == 0 and not any(e["stufe"] == FEHL for e in erg):
        erg.insert(0, zeile("Sammler", "Ampel", OK,
                            "kein Sammler steht still",
                            "kein roter Sammler"))
    return erg


# ----------------------------------------------------------------
#  C - laesst sich jede Datei noch uebersetzen?
# ----------------------------------------------------------------
def uebersetzbarkeit(basis=None):
    """Jede .py-Datei wird uebersetzt, ohne sie auszufuehren.

    Erwartung: alle. Eine Datei, die nach einer Bearbeitung nicht mehr
    uebersetzbar ist, faellt sonst erst beim naechsten Start auf - und
    wenn sie nur beim Auswerten gebraucht wird, erst Wochen spaeter.

    compile() schreibt nichts auf die Platte (kein __pycache__) und
    fuehrt keine Zeile aus.
    """
    basis = basis or HIER
    anzahl = 0
    kaputt = []
    for wurzel, ordner, dateien in os.walk(basis):
        ordner[:] = [o for o in ordner
                     if o not in AUS_ORDNER and not o.startswith(".")]
        for d in dateien:
            if not d.endswith(".py"):
                continue
            p = os.path.join(wurzel, d)
            anzahl += 1
            try:
                compile(io.open(p, "rb").read(), p, "exec")
            except SyntaxError as ex:
                kaputt.append("%s Zeile %s: %s"
                              % (os.path.relpath(p, basis), ex.lineno,
                                 ex.msg))
            except Exception as ex:
                kaputt.append("%s %s: %s"
                              % (os.path.relpath(p, basis),
                                 type(ex).__name__, ex))
    erw = "alle .py uebersetzbar"
    if kaputt:
        return [zeile("Uebersetzbar", "Quelltexte", FEHL,
                      "%d von %d nicht uebersetzbar: %s"
                      % (len(kaputt), anzahl, "; ".join(kaputt[:5])), erw)]
    return [zeile("Uebersetzbar", "Quelltexte", OK,
                  "%d Dateien, alle in Ordnung" % anzahl, erw)]


# ----------------------------------------------------------------
#  D - sind die Datenbanken unbeschaedigt?
# ----------------------------------------------------------------
def datenbanken(ordner=None):
    """sqlite quick_check je Datenbank. Erwartung: 'ok'.

    Geoeffnet wird ausdruecklich nur lesend (mode=ro). Grosse Dateien
    im Modus 'delete' werden uebersprungen - siehe DB_SPERRGRENZE_MB.
    """
    ordner = ordner or DATEN
    erg = []
    dateien = sorted(glob.glob(os.path.join(ordner, "*.db")))
    if not dateien:
        return [zeile("Datenbank", "(keine)", HIN,
                      "keine .db in %s" % ordner, "mindestens eine")]
    for p in dateien:
        name = os.path.basename(p)
        mb = os.path.getsize(p) / 1048576.0
        con = None
        try:
            uri = "file:%s?mode=ro" % p.replace("\\", "/")
            con = sqlite3.connect(uri, uri=True, timeout=5)
            modus = con.execute("pragma journal_mode").fetchone()[0]
            if modus.lower() != "wal" and mb > DB_SPERRGRENZE_MB:
                erg.append(zeile(
                    "Datenbank", name, HIN,
                    "%.0f MB im Modus %s - nicht geprueft, die Pruefung "
                    "wuerde den Schreiber zu lange sperren"
                    % (mb, modus), "quick_check = ok"))
                continue
            t0 = time.time()
            wert = con.execute("pragma quick_check(1)").fetchone()[0]
            dauer = time.time() - t0
            erg.append(zeile("Datenbank", name,
                             OK if wert == "ok" else FEHL,
                             "%s (%.1f MB, %.1f s)" % (wert, mb, dauer),
                             "quick_check = ok"))
        except Exception as ex:
            erg.append(zeile("Datenbank", name, FEHL,
                             "%s: %s" % (type(ex).__name__, ex),
                             "quick_check = ok"))
        finally:
            # [28.09.2026, vom eigenen Selbsttest gefunden] Ohne finally
            # blieb die Verbindung offen, wenn quick_check scheitert -
            # also genau im Fehlerfall. Windows gibt die Datei dann nicht
            # mehr frei. Eine Pruefung, die im Fehlerfall eine Datei
            # festhaelt, ist schlimmer als keine.
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
    return erg


# ----------------------------------------------------------------
#  E - Steuerzeichen in Textdateien
# ----------------------------------------------------------------
def steuerzeichen(basis=None):
    """Kein Zeichen unter 32 ausser Tab (9), LF (10), CR (13).

    WARUM DIESE PRUEFUNG
    Am 25./26.09.2026 sind bei der Arbeit an diesem Projekt dreimal
    Steuerzeichen in Dateien gelangt: ein Rueckschritt (\\b) in ein
    Ticket, ein Seitenvorschub (\\f) an Position 684049 des
    ENTWICKLERHANDBUCHs - der eine Pfadangabe zerstoerte - und ein
    echter Zeilenumbruch, wo \\n stehen sollte, der sammler_pruefen.py
    unuebersetzbar machte. Alle drei sind unsichtbar, wenn man die
    Datei ansieht. Genau deshalb muss eine Maschine danach suchen.
    """
    basis = basis or HIER
    erlaubt = {9, 10, 13}
    anzahl = 0
    treffer = []
    for wurzel, ordner, dateien in os.walk(basis):
        ordner[:] = [o for o in ordner
                     if o not in AUS_ORDNER and not o.startswith(".")]
        for d in dateien:
            if not d.endswith((".md", ".txt", ".json")):
                continue
            klein = d.lower()
            if any(m in klein for m in AUS_DATEI_MUSTER):
                continue
            p = os.path.join(wurzel, d)
            try:
                inhalt = io.open(p, "rb").read()
            except OSError:
                continue
            anzahl += 1
            schlecht = sorted({b for b in set(inhalt)
                               if b < 32 and b not in erlaubt})
            if schlecht:
                treffer.append("%s: %s"
                               % (os.path.relpath(p, basis),
                                  ", ".join("Zeichen %d" % b
                                            for b in schlecht)))
    erw = "kein Steuerzeichen ausser Tab und Zeilenumbruch"
    if treffer:
        return [zeile("Steuerzeichen", "Textdateien", FEHL,
                      "%d von %d betroffen: %s"
                      % (len(treffer), anzahl, "; ".join(treffer[:5])),
                      erw)]
    return [zeile("Steuerzeichen", "Textdateien", OK,
                  "%d Dateien, alle sauber" % anzahl, erw)]


# ----------------------------------------------------------------
#  F - geplante Aufgaben
# ----------------------------------------------------------------
PS_AUFGABEN = (
    "$ErrorActionPreference='SilentlyContinue'; $aus = @(); "
    "foreach ($t in (Get-ScheduledTask -TaskName %s -EA 0)) { "
    "$i = $t | Get-ScheduledTaskInfo; "
    "$l = ''; if ($i.LastRunTime) "
    "{ $l = $i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss') } "
    "$n = ''; if ($i.NextRunTime) "
    "{ $n = $i.NextRunTime.ToString('yyyy-MM-dd HH:mm:ss') } "
    "$ex = @(); $ar = @(); $wd = @(); "
    "foreach ($a in $t.Actions) { $ex += [string]$a.Execute; "
    "$ar += [string]$a.Arguments; $wd += [string]$a.WorkingDirectory } "
    "$ty = @(); $rp = @(); "
    "foreach ($g in $t.Triggers) { $ty += [string]$g.CimClass.CimClassName; "
    "$rp += [string]$g.Repetition.Interval } "
    "$aus += [PSCustomObject]@{ name=[string]$t.TaskName; "
    "zustand=[string]$t.State; letzte=$l; "
    "ergebnis=[string]$i.LastTaskResult; naechste=$n; "
    "exe=$ex; args=$ar; cwd=$wd; art=$ty; takt=$rp } } "
    "$boot = ''; try { $boot = (Get-CimInstance Win32_OperatingSystem)."
    "LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss') } catch { } "
    "ConvertTo-Json -InputObject "
    "([PSCustomObject]@{ boot=$boot; aufgaben=@($aus) }) "
    "-Depth 4 -Compress")


def aufgaben_holen():
    """Fragt die Aufgabenplanung ab. (fehler_text, boot, liste)."""
    muster = ",".join("'" + m + "'" for m in AUFGABEN_MUSTER)
    rc, aus = ps(PS_AUFGABEN % muster, zeit=300)
    roh = aus.strip()
    anfang = roh.find("{")
    if anfang < 0:
        return ("Aufgabenplanung nicht abfragbar: %s"
                % " ".join(roh.split())[:160], "", [])
    try:
        daten = json.loads(roh[anfang:])
    except Exception as ex:
        return ("Antwort der Aufgabenplanung unlesbar (%s)"
                % type(ex).__name__, "", [])
    liste = daten.get("aufgaben") or []
    if isinstance(liste, dict):
        liste = [liste]
    return "", daten.get("boot") or "", liste


def _als_liste(wert):
    if wert is None:
        return []
    if isinstance(wert, list):
        return [str(x) for x in wert if x is not None]
    return [str(wert)]


def _gehoert_hierher(a, basis):
    """Zeigt diese Aufgabe in den geprueften Ordner?

    Verglichen wird der Ordnerpfad in Programm, Argumenten und
    Arbeitsordner. Er steht in mindestens einem davon - bei TI6-Sammler
    nur im Arbeitsordner, bei SchattenUniversumLIVE nur im Argument.
    """
    ziel = basis.replace("\\", "/").lower()
    for wert in (_als_liste(a.get("exe")) + _als_liste(a.get("args"))
                 + _als_liste(a.get("cwd"))):
        if ziel in wert.replace("\\", "/").lower():
            return True
    return False


def _erwartetes_alter_h(a):
    """Wie alt darf der letzte Lauf hoechstens sein? None = nicht
    bewertbar (Anmeldung, Hochfahren - die laufen nicht nach Uhr)."""
    for t in _als_liste(a.get("takt")):
        m = re.match(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?$", t or "")
        if m and any(m.groups()):
            std = (int(m.group(1) or 0) * 24 + int(m.group(2) or 0)
                   + int(m.group(3) or 0) / 60.0)
            if std > 0:
                return max(std * 4, 1.0)
    arten = " ".join(_als_liste(a.get("art")))
    if "Daily" in arten:
        return 48.0
    if "Weekly" in arten:
        return 14 * 24.0
    if "Monthly" in arten:
        return 70 * 24.0
    return None


def _zeit(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def aufgaben_pruefen(liste, boot, basis=None, jetzt=None,
                     erwartete_namen=None):
    """Bewertet die Aufgaben dieses Ordners.

    Alle Zeitangaben sind ORTSZEIT - die Aufgabenplanung liefert
    Ortszeit, deshalb wird hier bewusst mit datetime.now() ohne
    Zeitzone verglichen und nicht mit UTC. (Am 26.09.2026 ist genau
    diese Verwechslung einmal in einen falschen Alarm gelaufen:
    "kein Lebenszeichen seit zwei Stunden", tatsaechlich 0,8 Sekunden.)
    """
    basis = basis or HIER
    jetzt = jetzt or datetime.now()
    erg = []
    hoch = _zeit(boot)
    an_seit_h = (jetzt - hoch).total_seconds() / 3600.0 if hoch else None

    meine = [a for a in liste if _gehoert_hierher(a, basis)]
    namen = sorted(a.get("name", "?") for a in meine)

    if not meine:
        erg.append(zeile("Aufgaben", "(keine)", HIN,
                         "keine geplante Aufgabe zeigt in diesen Ordner",
                         "mindestens die taegliche Pruefung"))

    for a in sorted(meine, key=lambda x: str(x.get("name", ""))):
        name = str(a.get("name", "?"))
        stufe, teile = OK, []

        zustand = str(a.get("zustand", "?"))
        if zustand == "Disabled":
            stufe = FEHL
            teile.append("ABGESCHALTET")
        else:
            teile.append(zustand)

        # Zeigt sie auf Dateien, die es gibt? Genau das ging beim
        # Umzug schief: der Pfad des Laptops blieb stehen, die Aufgabe
        # meldete Erfolg und tat nichts.
        for wert in _als_liste(a.get("exe")):
            if wert and not os.path.exists(wert):
                stufe = FEHL
                teile.append("Programm fehlt: " + wert)
        for wert in _als_liste(a.get("args")):
            for stueck in re.findall(r'"([^"]+)"', wert) or [wert.strip()]:
                if not stueck or not re.search(
                        r"\.(py|bat|cmd|exe|ps1)$", stueck, re.I):
                    continue
                pfad = stueck if os.path.isabs(stueck) else os.path.join(
                    (_als_liste(a.get("cwd")) or [basis])[0] or basis,
                    stueck)
                if not os.path.exists(pfad):
                    stufe = FEHL
                    teile.append("Datei fehlt: " + stueck)

        code = a.get("ergebnis")
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = None
        if code is None:
            teile.append("Ergebnis unbekannt")
        elif code in AUFGABE_CODES_GUT:
            teile.append(AUFGABE_CODES_GUT[code])
        else:
            stufe = FEHL
            teile.append("letzter Lauf endete mit 0x%08X" % (code & 0xFFFFFFFF))

        grenze = _erwartetes_alter_h(a)
        letzte = _zeit(str(a.get("letzte") or ""))
        if grenze is None:
            teile.append("laeuft nicht nach Uhr")
        elif letzte is None or letzte.year < 2000 or code == 267011:
            # [28.09.2026, beim ersten echten Lauf gefunden] Eine gerade
            # angelegte Aufgabe traegt als letzten Lauf den 30.11.1999.
            # Die Altersrechnung meldete daraufhin "letzter Lauf vor
            # 235198 Stunden" - ein Fehlalarm am Tag der Einrichtung,
            # also genau dort, wo man dem Werkzeug noch nicht traut.
            teile.append("noch nie gelaufen - erster Lauf steht aus")
        else:
            alt = (jetzt - letzte).total_seconds() / 3600.0
            if an_seit_h is not None and an_seit_h < grenze:
                teile.append("letzter Lauf vor %.1f h - nicht bewertbar, "
                             "der Rechner ist erst seit %.1f h an"
                             % (alt, an_seit_h))
            elif alt > grenze:
                stufe = FEHL
                teile.append("letzter Lauf vor %.1f h, erlaubt sind %.0f h"
                             % (alt, grenze))
            else:
                teile.append("letzter Lauf vor %.1f h" % alt)

        erg.append(zeile("Aufgaben", name, stufe, "; ".join(teile),
                         "vorhanden, aktiv, Dateien da, im Takt gelaufen"))

    # Ist eine Aufgabe verschwunden, die schon einmal da war?
    if erwartete_namen is None:
        erwartete_namen = grundstand_lesen()
    fehlt = [n for n in erwartete_namen if n not in namen]
    if fehlt:
        erg.append(zeile("Aufgaben", "Grundstand", FEHL,
                         "nicht mehr vorhanden: " + ", ".join(fehlt),
                         "alle einmal erfassten Aufgaben sind noch da"))
    elif erwartete_namen:
        erg.append(zeile("Aufgaben", "Grundstand", OK,
                         "%d erfasste Aufgabe(n), alle noch da"
                         % len(erwartete_namen),
                         "alle einmal erfassten Aufgaben sind noch da"))
    return erg, namen


def grundstand_lesen():
    try:
        with io.open(GRUNDSTAND, encoding="utf-8") as f:
            return list(json.load(f).get("erwartet") or [])
    except Exception:
        return []


def grundstand_schreiben(namen, grund):
    sicher_schreiben(GRUNDSTAND, json.dumps(
        {"erwartet": sorted(namen), "grund": grund,
         "geschrieben": datetime.now(timezone.utc).isoformat(
             timespec="seconds")},
        indent=1, ensure_ascii=False))


# ----------------------------------------------------------------
#  G - Selbstpruefung
# ----------------------------------------------------------------
def aufgaben_name():
    """Der Aufgabenname folgt dem Ordner, damit v6 und v7 sich nie in
    die Quere kommen."""
    kurz = os.path.basename(HIER).lower()
    if "v7" in kurz:
        return "TI7-Tagescheck"
    if "v6" in kurz:
        return "TI6-Tagescheck"
    rest = re.sub(r"[^a-z0-9]", "", kurz)[:12] or "ordner"
    return "TI-Tagescheck-" + rest


def startzeit():
    """v6 und v7 laufen versetzt - zwei gleichzeitige Pruefungen
    wuerden sich um dieselbe Datenbank streiten. TI6-Sammler laeuft um
    06:00, deshalb beide danach."""
    kurz = os.path.basename(HIER).lower()
    if "v6" in kurz:
        return "07:15"
    if "v7" in kurz:
        return "07:30"
    return "07:45"


def selbst(liste):
    name = aufgaben_name()
    erw = "diese Pruefung ist als taegliche Aufgabe eingerichtet"
    da = [a for a in liste if str(a.get("name", "")) == name]
    if not da:
        return [zeile("Selbst", name, FEHL,
                      "nicht eingerichtet - python tagescheck.py "
                      "--einrichten", erw)]
    return [zeile("Selbst", name, OK, "eingerichtet", erw)]


# ----------------------------------------------------------------
#  Bericht
# ----------------------------------------------------------------
def bericht_bauen(erg, hinweise):
    jetzt = datetime.now()
    b = []
    b.append("=" * 78)
    b.append("  TAGESCHECK   %s" % os.path.basename(HIER))
    b.append("  %s Ortszeit" % jetzt.strftime("%d.%m.%Y %H:%M"))
    b.append("=" * 78)
    n_fehl = sum(1 for e in erg if e["stufe"] == FEHL)
    n_hin = sum(1 for e in erg if e["stufe"] == HIN)
    n_ok = sum(1 for e in erg if e["stufe"] == OK)
    b.append("")
    b.append("  ERGEBNIS: %d Fehler, %d zum Hinsehen, %d in Ordnung"
             % (n_fehl, n_hin, n_ok))
    b.append("")

    for stufe, titel in ((FEHL, "FEHLER - hier stimmt etwas nicht"),
                         (HIN, "HINSEHEN - auffaellig, aber kein Ausfall"),
                         (OK, "IN ORDNUNG")):
        gruppe = [e for e in erg if e["stufe"] == stufe]
        if not gruppe:
            continue
        b.append("  " + titel)
        b.append("  " + "-" * 74)
        for e in gruppe:
            b.append("  %-14s %-22s %s"
                     % (e["bereich"], e["name"][:22], e["befund"]))
            if stufe == FEHL and e["erwartung"]:
                b.append("  %-14s %-22s   erwartet: %s"
                         % ("", "", e["erwartung"]))
        b.append("")

    if hinweise:
        b.append("  ANMERKUNGEN")
        b.append("  " + "-" * 74)
        for h in hinweise:
            b.append("  " + h)
        b.append("")

    b.append("  WAS DIESE PRUEFUNG NICHT BEANTWORTET")
    b.append("  " + "-" * 74)
    b.append("  Ob der Bot GUT handelt. Sie prueft, ob er laeuft, ob")
    b.append("  gesammelt wird und ob nichts kaputt ist - nicht, ob die")
    b.append("  Zahlen gefallen. Dafuer sind die Auswertungen da.")
    b.append("")
    b.append("  Vollstaendige Laufliste: data_store/tagescheck.log")
    b.append("=" * 78)
    return "\n".join(b) + "\n"


def ticket_schreiben(text):
    try:
        with io.open(TICKETS, "a", encoding="utf-8") as f:
            f.write("\nBUG: " + text + "\n")
        return True
    except OSError:
        return False


# ----------------------------------------------------------------
#  Hauptlauf
# ----------------------------------------------------------------
def lauf(kurz=False):
    zeilen = []
    hinweise = []
    erg = []

    fehler_text, boot, liste = aufgaben_holen()
    if fehler_text:
        erg.append(zeile("Aufgaben", "Abfrage", FEHL, fehler_text,
                         "Aufgabenplanung antwortet"))
        liste, boot = [], ""

    erg += betrieb()
    erg += sammler()
    erg += uebersetzbarkeit()
    erg += datenbanken()
    erg += steuerzeichen()
    if not fehler_text:
        teil, namen = aufgaben_pruefen(liste, boot)
        erg += teil
        erg += selbst(liste)
        if not grundstand_lesen() and namen:
            grundstand_schreiben(namen, "beim ersten Lauf aufgenommen")
            hinweise.append("Grundstand der geplanten Aufgaben zum ersten "
                            "Mal aufgenommen: " + ", ".join(namen)
                            + ". Verschwindet eine davon, wird das ab "
                            "morgen gemeldet.")

    text = bericht_bauen(erg, hinweise)
    sicher_schreiben(BERICHT, text)

    n_fehl = sum(1 for e in erg if e["stufe"] == FEHL)
    n_hin = sum(1 for e in erg if e["stufe"] == HIN)
    kopfzeile = ("TAGESCHECK %s: %d Fehler, %d zum Hinsehen, %d in Ordnung"
                 % (os.path.basename(HIER), n_fehl, n_hin,
                    sum(1 for e in erg if e["stufe"] == OK)))

    if kurz:
        notiz(kopfzeile, zeilen)
        for e in erg:
            if e["stufe"] == FEHL:
                notiz("  FEHLER  %s / %s: %s"
                      % (e["bereich"], e["name"], e["befund"]), zeilen)
    else:
        for z in text.splitlines():
            notiz(z, zeilen)

    log_anhaengen([kopfzeile] + [
        "  %-8s %-14s %-22s %s" % (e["stufe"], e["bereich"], e["name"],
                                   e["befund"]) for e in erg])

    # --- Ticket nur fuer NEUE Fehler ---
    alt = voriger_stand()
    vorher = set(alt.get("fehler") or [])
    jetzt_fehler = {"%s/%s" % (e["bereich"], e["name"])
                    for e in erg if e["stufe"] == FEHL}
    neu = jetzt_fehler - vorher
    weg = vorher - jetzt_fehler

    if weg:
        notiz("  wieder in Ordnung: " + ", ".join(sorted(weg)), zeilen)
    if neu:
        texte = "; ".join("%s/%s: %s" % (e["bereich"], e["name"], e["befund"])
                          for e in erg
                          if e["stufe"] == FEHL
                          and "%s/%s" % (e["bereich"], e["name"]) in neu)
        if ticket_schreiben(
                "Tagescheck %s %s - %s. Ganzer Bericht: "
                "data_store/tagescheck_bericht.txt"
                % (os.path.basename(HIER),
                   datetime.now().strftime("%d.%m. %H:%M"), texte[:1200])):
            notiz("  Ticket geschrieben fuer: " + ", ".join(sorted(neu)),
                  zeilen)
    elif jetzt_fehler:
        notiz("  kein neues Ticket - dieselben Fehler wie beim letzten Lauf",
              zeilen)

    sicher_schreiben(MERKER, json.dumps(
        {"fehler": sorted(jetzt_fehler),
         "hinsehen": sorted("%s/%s" % (e["bereich"], e["name"])
                            for e in erg if e["stufe"] == HIN),
         "zuletzt": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        indent=1, ensure_ascii=False))
    return 1 if n_fehl else 0


# ----------------------------------------------------------------
#  Einrichten / Pruefen / Entfernen
# ----------------------------------------------------------------
def python_pfad():
    """Ein Interpreter, der in einer geplanten Aufgabe wirklich laeuft.

    Die Reihenfolge ist Absicht: erst der laufende Prozess - der stimmt
    auf JEDEM Rechner, auch nach einem Umzug. Ein fest eingetragener
    Pfad zeigt nach dem Umzug ins Leere, die Aufgabe meldet Erfolg und
    tut nichts. Genau so ist der Dauercheck am 01.09. verschwunden.
    """
    eigen = sys.executable or ""
    if not eigen:
        return None, "sys.executable ist leer"
    ordner = os.path.dirname(eigen)
    for k in (os.path.join(ordner, "pythonw.exe"), eigen):
        if not os.path.exists(k):
            continue
        marke = os.path.join(DATEN, "_probelauf_tagescheck.txt")
        try:
            if os.path.exists(marke):
                os.remove(marke)
            subprocess.run([k, "-c", "open(" + repr(marke) + ",'w')"
                                     ".write('da')"],
                           capture_output=True, timeout=60)
            gut = os.path.exists(marke)
            if gut:
                os.remove(marke)
        except Exception:
            gut = False
        if gut:
            zusatz = "" if k.lower().endswith("pythonw.exe") else \
                "  (python.exe - bei jedem Lauf blitzt ein Fenster auf)"
            return k, zusatz
    return None, "kein Interpreter hat den Probelauf bestanden"


def einrichten():
    name = aufgaben_name()
    uhr = startzeit()
    pyw, hinweis = python_pfad()
    print()
    print("=" * 78)
    print("  TAEGLICHE PRUEFUNG EINRICHTEN  -  %s" % os.path.basename(HIER))
    print("=" * 78)
    if pyw is None:
        print("\n  ABBRUCH: %s" % hinweis)
        print("  Es wird bewusst NICHTS angelegt - eine Aufgabe, die")
        print("  Erfolg meldet und ins Leere zeigt, ist schlimmer als")
        print("  keine.")
        return 1
    print("\n  Interpreter : %s%s" % (pyw, hinweis))
    print("  Aufgabe     : %s" % name)
    print("  Taeglich um : %s Ortszeit" % uhr)
    print("  Ordner      : %s" % HIER)
    print("\n  Nachholen   : ja - war der Rechner aus, laeuft sie beim")
    print("                naechsten Anmelden nach (StartWhenAvailable).")

    skript = os.path.join(HIER, "tagescheck.py")
    befehl = (
        "$ErrorActionPreference='Stop'; "
        "$exe = '" + pyw + "'; $arg = '\"" + skript + "\"'; "
        "$wer = $env:COMPUTERNAME + '\\' + $env:USERNAME; "
        "$a = New-ScheduledTaskAction -Execute $exe -Argument $arg "
        "-WorkingDirectory '" + HIER + "'; "
        # RunLevel Limited: ausdruecklich OHNE erhoehte Rechte. Genau
        # das macht das Anlegen ohne Adminrechte moeglich (16.09.2026).
        "$p = New-ScheduledTaskPrincipal -UserId $wer "
        "-LogonType Interactive -RunLevel Limited; "
        "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -StartWhenAvailable "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 30); "
        "try { $t = New-ScheduledTaskTrigger -Daily -At '" + uhr + "'; "
        "Register-ScheduledTask -TaskName '" + name + "' -Action $a "
        "-Trigger $t -Principal $p -Settings $s -Force | Out-Null; "
        "'ANGELEGT' } catch { 'FEHLER ' + $_.Exception.Message }; "
        "'--- STAND ---'; "
        "Get-ScheduledTask -TaskName '" + name + "' -EA 0 | "
        "ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
        "\"$($_.TaskName) | $($_.State) | naechster Lauf "
        "$($i.NextRunTime)\" }")

    rc, aus = ps(befehl, zeit=300)
    kopf, _, schwanz = aus.partition("--- STAND ---")
    print()
    for z in kopf.splitlines():
        z = z.strip()
        if z == "ANGELEGT":
            print("    [ok]      Aufgabe angelegt")
        elif z:
            print("    [FEHLER]  %s" % " ".join(z.split())[:160])

    # Gegenprobe: nicht der Rueckgabewert zaehlt, sondern was da ist.
    print("\n  Gegenprobe - was die Aufgabenplanung jetzt fuehrt")
    print("  " + "-" * 74)
    zeilen = [z.strip() for z in schwanz.splitlines() if z.strip()]
    if not zeilen:
        print("    (nichts - die Aufgabe wurde NICHT angelegt)")
        return 1
    for z in zeilen:
        print("    " + z)

    # Grundstand aufnehmen, damit ab morgen auffaellt, wenn eine
    # Aufgabe dieses Ordners verschwindet.
    fehler_text, boot, liste = aufgaben_holen()
    if not fehler_text:
        namen = sorted(a.get("name", "?") for a in liste
                       if _gehoert_hierher(a, HIER))
        grundstand_schreiben(namen, "beim Einrichten aufgenommen")
        print("\n  Grundstand aufgenommen: %s" % (", ".join(namen) or "-"))
        print("  Verschwindet eine davon, meldet es die Pruefung.")

    print("\n" + "=" * 78)
    print("  Sofort einmal laufen lassen:  python tagescheck.py")
    print("  Wieder entfernen:             python tagescheck.py --entfernen")
    print("=" * 78 + "\n")
    return 0


def pruefen():
    name = aufgaben_name()
    fehler_text, boot, liste = aufgaben_holen()
    print()
    if fehler_text:
        print("  " + fehler_text)
        return 1
    meine = [a for a in liste if _gehoert_hierher(a, HIER)]
    print("  Aufgaben, die in %s zeigen" % os.path.basename(HIER))
    print("  " + "-" * 74)
    if not meine:
        print("    (keine)")
    for a in sorted(meine, key=lambda x: str(x.get("name", ""))):
        print("    %-34s %-9s letzter Lauf %s"
              % (a.get("name"), a.get("zustand"), a.get("letzte") or "nie"))
    print()
    print("  Taegliche Pruefung (%s): %s" % (
        name, "eingerichtet" if any(str(a.get("name")) == name
                                    for a in liste) else "FEHLT"))
    print("  Rechner an seit: %s" % (boot or "unbekannt"))
    print()
    return 0


def entfernen():
    name = aufgaben_name()
    rc, aus = ps("Unregister-ScheduledTask -TaskName '" + name + "' "
                 "-Confirm:$false -ErrorAction Stop; 'weg'")
    print("\n  %s: %s\n" % (name, "entfernt" if "weg" in aus
                            else "nicht vorhanden"))
    return 0


# ----------------------------------------------------------------
#  Gegentest in beide Richtungen
# ----------------------------------------------------------------
def selbsttest():
    """Meldet die Pruefung nichts Falsches - UND findet sie den echten
    Fall? Getestet werden die ECHTEN Funktionen mit untergeschobenen
    Daten, nicht nachgebaute Kopien.

    Diese Unterscheidung steht hier, weil sie am 26.09.2026 einmal
    schieflief: ein "Gegentest ueber acht Faelle" hatte die Logik
    nachgebaut statt sie aufzurufen - er prueft dann sich selbst.
    """
    import tempfile
    fehler = 0
    print("=" * 78)
    print("  SELBSTTEST - findet die Pruefung, was sie finden soll?")
    print("=" * 78)

    def urteil(was, bedingung):
        nonlocal fehler
        print("  %-58s %s" % (was, "ok" if bedingung else "FEHLGESCHLAGEN"))
        if not bedingung:
            fehler += 1

    with tempfile.TemporaryDirectory() as tmp:
        # --- C: Uebersetzbarkeit ---
        io.open(os.path.join(tmp, "gut.py"), "w",
                encoding="utf-8").write("x = 1\n")
        r = uebersetzbarkeit(tmp)
        urteil("Uebersetzbarkeit: saubere Datei bleibt unbeanstandet",
               r[0]["stufe"] == OK)
        io.open(os.path.join(tmp, "kaputt.py"), "w",
                encoding="utf-8").write("def f(:\n")
        r = uebersetzbarkeit(tmp)
        urteil("Uebersetzbarkeit: kaputte Datei wird gefunden",
               r[0]["stufe"] == FEHL and "kaputt.py" in r[0]["befund"])

        # --- E: Steuerzeichen ---
        io.open(os.path.join(tmp, "sauber.md"), "w",
                encoding="utf-8").write("Zeile\tmit Tab\n")
        r = steuerzeichen(tmp)
        urteil("Steuerzeichen: Tab und Umbruch sind erlaubt",
               r[0]["stufe"] == OK)
        io.open(os.path.join(tmp, "krank.md"), "wb").write(
            b"vorher\x0cnachher")
        r = steuerzeichen(tmp)
        urteil("Steuerzeichen: Seitenvorschub wird gefunden",
               r[0]["stufe"] == FEHL and "krank.md" in r[0]["befund"])
        io.open(os.path.join(tmp, "alt_KORRUPT_x.md"), "wb").write(b"a\x00b")
        r = steuerzeichen(tmp)
        urteil("Steuerzeichen: KORRUPT-Beweisstueck wird uebergangen",
               "alt_KORRUPT_x.md" not in r[0]["befund"])

        # --- D: Datenbanken ---
        dbo = os.path.join(tmp, "db")
        os.makedirs(dbo)
        con = sqlite3.connect(os.path.join(dbo, "heil.db"))
        con.execute("create table t (a int)")
        con.execute("insert into t values (1)")
        con.commit()
        con.close()
        r = datenbanken(dbo)
        urteil("Datenbank: heile Datei gilt als ok",
               len(r) == 1 and r[0]["stufe"] == OK)
        io.open(os.path.join(dbo, "muell.db"), "wb").write(b"kein sqlite" * 40)
        r = datenbanken(dbo)
        schlecht = [e for e in r if e["name"] == "muell.db"]
        urteil("Datenbank: Muelldatei wird beanstandet",
               bool(schlecht) and schlecht[0]["stufe"] == FEHL)
        urteil("Datenbank: die heile Datei bleibt daneben unbeanstandet",
               any(e["name"] == "heil.db" and e["stufe"] == OK for e in r))

        # --- F: Aufgaben ---
        echt = os.path.join(tmp, "ziel.py")
        io.open(echt, "w", encoding="utf-8").write("x = 1\n")
        jetzt = datetime(2026, 9, 28, 12, 0, 0)
        boot = "2026-09-20 08:00:00"          # lange an, also bewertbar
        gut = {"name": "TEST-Gut", "zustand": "Ready",
               "letzte": "2026-09-28 07:30:00", "ergebnis": "0",
               "exe": [sys.executable], "args": ['"' + echt + '"'],
               "cwd": [tmp], "art": ["MSFT_TaskDailyTrigger"], "takt": [""]}
        r, namen = aufgaben_pruefen([gut], boot, basis=tmp, jetzt=jetzt,
                                    erwartete_namen=["TEST-Gut"])
        urteil("Aufgabe: heile Aufgabe bleibt unbeanstandet",
               all(e["stufe"] == OK for e in r))

        # Der Pfad muss auf .py enden - sonst greift die Pruefung gar
        # nicht, und der Test haette sich selbst bestaetigt. (Beim
        # ersten Lauf stand hier "...ziel.py_nichtda": die Endung war
        # weg, die Pruefung sah kein Skript, und der Gegentest fiel
        # durch. Genau dafuer ist er da.)
        weg = dict(gut, name="TEST-Weg",
                   args=['"' + os.path.join(tmp, "gibtesnicht.py") + '"'])
        r, _ = aufgaben_pruefen([weg], boot, basis=tmp, jetzt=jetzt,
                                erwartete_namen=[])
        urteil("Aufgabe: fehlende Zieldatei wird gefunden",
               r[0]["stufe"] == FEHL and "Datei fehlt" in r[0]["befund"])

        alt = dict(gut, name="TEST-Alt", letzte="2026-09-20 07:30:00")
        r, _ = aufgaben_pruefen([alt], boot, basis=tmp, jetzt=jetzt,
                                erwartete_namen=[])
        urteil("Aufgabe: seit Tagen nicht gelaufen wird gefunden",
               r[0]["stufe"] == FEHL and "erlaubt" in r[0]["befund"])

        r, _ = aufgaben_pruefen([alt], "2026-09-28 11:00:00", basis=tmp,
                                jetzt=jetzt, erwartete_namen=[])
        urteil("Aufgabe: frisch hochgefahren ist KEIN Fehler",
               r[0]["stufe"] == OK and "nicht bewertbar" in r[0]["befund"])

        aus = dict(gut, name="TEST-Aus", zustand="Disabled")
        r, _ = aufgaben_pruefen([aus], boot, basis=tmp, jetzt=jetzt,
                                erwartete_namen=[])
        urteil("Aufgabe: abgeschaltete Aufgabe wird gefunden",
               r[0]["stufe"] == FEHL and "ABGESCHALTET" in r[0]["befund"])

        waechter = dict(gut, name="TEST-Waechter", ergebnis="2147946720",
                        art=["MSFT_TaskTimeTrigger"], takt=["PT15M"],
                        letzte="2026-09-28 11:50:00")
        r, _ = aufgaben_pruefen([waechter], boot, basis=tmp, jetzt=jetzt,
                                erwartete_namen=[])
        urteil("Aufgabe: 0x800710E0 bei einem Waechter ist kein Fehler",
               r[0]["stufe"] == OK)

        r, _ = aufgaben_pruefen([], boot, basis=tmp, jetzt=jetzt,
                                erwartete_namen=["TEST-Gut"])
        urteil("Aufgabe: verschwundene Aufgabe wird gemeldet",
               any(e["name"] == "Grundstand" and e["stufe"] == FEHL
                   for e in r))

        fremd = dict(gut, name="TEST-Fremd", exe=[sys.executable],
                     args=['"C:\\woanders\\x.py"'], cwd=["C:\\woanders"])
        r, namen = aufgaben_pruefen([fremd], boot, basis=tmp, jetzt=jetzt,
                                    erwartete_namen=[])
        urteil("Aufgabe: fremder Ordner wird nicht mitgezaehlt",
               namen == [] and any(e["name"] == "(keine)" for e in r))

    print("=" * 78)
    if fehler:
        print("  %d Gegentest(s) fehlgeschlagen - die Pruefung ist nicht "
              "verlaesslich." % fehler)
    else:
        print("  Alle Gegentests bestanden, in beide Richtungen.")
    print("=" * 78)
    return 1 if fehler else 0


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if arg in ("--einrichten", "-e"):
        return einrichten()
    if arg in ("--pruefen", "-p"):
        return pruefen()
    if arg == "--entfernen":
        return entfernen()
    if arg == "--selbsttest":
        return selbsttest()
    if arg in ("--hilfe", "-h", "--help", "/?"):
        print(__doc__)
        return 0
    return lauf(kurz=arg in ("--kurz", "-k"))


if __name__ == "__main__":
    sys.exit(main())
