# -*- coding: utf-8 -*-
"""Laeuft dieser Ordner auf DIESEM Rechner? - vor und nach einem Umzug.

WOZU
----
Sven am 16.09.2026: *"der laptop hier laeuft auf windows 10 aber mein
rechner zuhause auf 11 also mach einen vermerk rein das wenn ich den live
ordner auf meinen pc rueber ziehe das er das weiss"*.

Ein Vermerk in einer Datei wird gelesen, wenn man ihn sucht - also nie.
Deshalb ist der Vermerk hier ein WERKZEUG: es sagt nicht, woran man denken
soll, sondern was gerade nicht stimmt.

Aufruf nach dem Umzug, als erster Schritt:

    python umzug_pruefen.py

WAS ES PRUEFT - und warum genau das
-----------------------------------
Jede Zeile hier steht fuer einen Fehler, der schon einmal passiert ist.
Alle haben dieselbe Bauart: **sie melden Erfolg und tun nichts.**

  1. Betriebssystem     Windows 10 (Laptop) gegen 11 (Rechner zuhause).
                        Nur zur Einordnung, beides geht.
  2. Python             Der Aufruf `python` ist unter Windows haeufig eine
                        Attrappe, die den Microsoft Store oeffnet. In einer
                        geplanten Aufgabe scheitert sie STILL (14.08.2026).
                        Geprueft wird deshalb durch Probelauf.
  3. Pakete             requirements.txt altert still: am 02.09. fehlten
                        reportlab und openpyxl. Auf der Maschine, auf der
                        entwickelt wird, merkt das niemand.
  4. Geplante Aufgaben  Eine importierte Aufgaben-XML traegt die
                        Benutzerkennung (SID) des ALTEN Rechners. Sie sieht
                        aus, als liefe sie, und tut nichts. Ausserdem: zeigt
                        die Aufgabe ueberhaupt auf DIESEN Ordner? Seit dem
                        14.09. gibt es zwei, Papier und Live.
  5. Feste Pfade        Dateien, die den alten Benutzernamen oder den
                        anderen Projektordner tragen.
  6. Haken (hooks)      .claude/settings.json verweist absolut. Stimmt der
                        Pfad nicht, arbeitet Claude ohne die Projektregeln -
                        und ohne Schreibschutz.
  7. Daten und .env     Sind die Datenbanken mitgekommen? Liegt die .env da?
                        Der INHALT wird nie gelesen (CLAUDE.md).

Reine Leseoperation. Aendert nichts, startet nichts.
"""
import io
import json
import os
import platform
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))

# Die zwanzig Fremdpakete aus Handbuch 10.11, dort ueber alle 313 Dateien
# mit `ast` erhoben - nicht von Hand zusammengeschrieben.
PAKETE = ("ccxt", "yfinance", "websocket", "requests", "pandas", "numpy",
          "pandas_ta", "sklearn", "xgboost", "matplotlib", "mplfinance",
          "customtkinter", "PIL", "praw", "bs4", "flask", "pyngrok",
          "psutil", "reportlab", "openpyxl")

# Was ohne Daten nicht sinnvoll startet.
DATEN = ("data_store/config.json",
         "data_store/trades_v5.json",
         "data_store/telemetrie.db",
         "data_store/schatten_universum.db",
         "config_epochs.json")

ok_zahl = 0
warn_zahl = 0
fehl_zahl = 0


def zeile(stufe, text, zusatz=""):
    global ok_zahl, warn_zahl, fehl_zahl
    marke = {"ok": "[ok]   ", "warn": "[!]    ", "fehl": "[FEHLT]"}[stufe]
    if stufe == "ok":
        ok_zahl += 1
    elif stufe == "warn":
        warn_zahl += 1
    else:
        fehl_zahl += 1
    print(f"  {marke} {text}")
    if zusatz:
        for z in str(zusatz).splitlines():
            print(f"          {z}")


def titel(t):
    print(f"\n  {t}")
    print("  " + "-" * 68)


# ---------------------------------------------------------------- 1. System
def pruefe_system():
    titel("1. Rechner und Betriebssystem")
    art = platform.system()
    fassung = platform.release()
    bau = platform.version().split(".")[-1] if "." in platform.version() else "?"
    # Windows 11 meldet sich als "10" mit Baunummer ab 22000. Das ist keine
    # Macke dieses Skripts, sondern von Windows selbst.
    try:
        echt = "11" if int(bau) >= 22000 else fassung
    except ValueError:
        echt = fassung
    zeile("ok", f"{art} {echt}  (Baunummer {bau})")
    zeile("ok", f"Rechnername: {platform.node()}")
    zeile("ok", f"Ordner: {HIER}")
    if "LIVE" not in HIER:
        zeile("warn", "Der Ordnername enthaelt kein 'LIVE'.",
              "Wurde hier der Papier-Ordner kopiert? Beide sehen gleich aus,\n"
              "aber nur einer handelt mit echtem Geld.")


# ---------------------------------------------------------------- 2. Python
def pruefe_python():
    titel("2. Python - und ob es in einer geplanten Aufgabe laeuft")
    zeile("ok", f"Version {sys.version.split()[0]}")
    zeile("ok", f"Interpreter: {sys.executable}")

    try:
        from schatten_starter import interpreter
    except Exception as e:
        zeile("fehl", f"schatten_starter.py nicht ladbar: {type(e).__name__}",
              str(e)[:120])
        return
    pyw = interpreter()
    if not pyw:
        zeile("fehl", "Kein pythonw.exe gefunden.",
              "Ohne ihn startet der Schatten-Sammler nicht, und bei jedem\n"
              "Lauf wuerde sonst ein Konsolenfenster aufpoppen.")
        return

    # DER PROBELAUF. Nicht exists(), nicht getsize() - beides fuehrt bei
    # den Store-Verweisen in die Irre: sie melden alle 0 Byte, die
    # funktionierenden wie die Attrappen (16.09.2026 nachgemessen).
    import tempfile
    marke = os.path.join(tempfile.gettempdir(), f"ti_umzug_{os.getpid()}.txt")
    try:
        subprocess.run([pyw, "-c", f"open(r'{marke}','w').write('da')"],
                       capture_output=True, timeout=90)
        gut = os.path.exists(marke)
        if gut:
            os.remove(marke)
    except Exception as e:
        gut = False
        zeile("fehl", f"Probelauf nicht moeglich: {type(e).__name__}")
        return
    if gut:
        zeile("ok", "pythonw besteht den Probelauf", pyw)
    else:
        zeile("fehl", "pythonw laeuft NICHT - nur ein Verweis, keine Datei.",
              f"{pyw}\n"
              "Abhilfe: Python von python.org installieren und die\n"
              "App-Ausfuehrungsaliase in den Windows-Einstellungen abschalten.")


# ---------------------------------------------------------------- 3. Pakete
def pruefe_pakete():
    titel("3. Die zwanzig Fremdpakete")
    fehlen = []
    for p in PAKETE:
        try:
            __import__(p)
        except Exception:
            fehlen.append(p)
    if not fehlen:
        zeile("ok", f"alle {len(PAKETE)} Pakete geladen")
    else:
        zeile("fehl", f"{len(fehlen)} von {len(PAKETE)} fehlen: "
                      f"{', '.join(fehlen)}",
              "Nachinstallieren:  pip install -r requirements.txt")


# ------------------------------------------------------- 4. Geplante Aufgaben
def pruefe_aufgaben():
    titel("4. Geplante Aufgaben - zeigen sie auf DIESEN Ordner?")
    befehl = (
        "Get-ScheduledTask -TaskName 'SchattenUniversum*' -EA 0 | "
        "ForEach-Object { $z = ($_.Actions | ForEach-Object { "
        "$_.Arguments + '|' + $_.Execute }) -join ' ' ; "
        "\"$($_.TaskName)`t$($_.State)`t$z\" }")
    try:
        f = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
            capture_output=True, text=True, timeout=300)
        roh = (f.stdout or "")
    except Exception as e:
        zeile("warn", f"Aufgabenplanung nicht lesbar ({type(e).__name__})",
              "Auf einem ausgelasteten Rechner dauert die Abfrage lange.\n"
              "Spaeter nochmal versuchen.")
        return

    zeilen = [z for z in roh.splitlines() if "\t" in z]
    if not zeilen:
        zeile("fehl", "Keine Aufgabe 'SchattenUniversum*' eingerichtet.",
              "Einrichten mit:  python autostart_einrichten.py")
        return

    fuer_uns = 0
    for z in zeilen:
        t = z.split("\t")
        name, zustand, ziel = t[0], t[1], (t[2] if len(t) > 2 else "")
        arg, _, exe = ziel.partition("|")
        # Der Ordner im Argument entscheidet, nicht der Name der Aufgabe.
        meiner = os.path.normcase(HIER) in os.path.normcase(arg)
        if meiner:
            fuer_uns += 1
            # Zeigt sie auf einen Interpreter, den es hier gibt?
            if exe.strip() and not os.path.exists(exe.strip().strip('"')):
                zeile("fehl", f"{name}: Interpreter existiert nicht",
                      f"{exe.strip()}\n"
                      "Die Aufgabe meldet Erfolg und tut nichts. Neu anlegen:\n"
                      "  python autostart_einrichten.py")
            else:
                zeile("ok", f"{name} ({zustand}) - zeigt hierher")
        else:
            wo = "Papier-Ordner" if "v6(21)" in arg else "einen anderen Ordner"
            zeile("ok", f"{name} ({zustand}) - zeigt auf {wo}, nicht unsere")
    if fuer_uns == 0:
        zeile("fehl", "Keine der Aufgaben zeigt auf DIESEN Ordner.",
              "Nach einem Umzug ist das der Normalfall - die alten Aufgaben\n"
              "tragen die Kennung des alten Rechners. Neu anlegen:\n"
              "  python autostart_einrichten.py")


# ----------------------------------------------------------- 5. Feste Pfade
def pruefe_feste_pfade():
    titel("5. Fest eingetragene Pfade auf den alten Rechner")
    benutzer = os.environ.get("USERNAME", "")
    treffer = []
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner
                     if o not in ("archiv", ".git", "__pycache__", "docs",
                                  "zahlenbuecher", "aufgabenplanung_backup")]
        for d in dateien:
            if not d.endswith((".py", ".bat")) or d.startswith("ZZ_"):
                continue
            # Diese Datei sucht nach dem Wort "Users" - also findet sie
            # sich selbst. Ein Pruefwerkzeug, das sich selbst meldet,
            # bringt dem Leser bei, die Meldung zu ueberlesen.
            if os.path.abspath(os.path.join(wurzel, d)) == os.path.abspath(__file__):
                continue
            p = os.path.join(wurzel, d)
            try:
                text = io.open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for nr, z in enumerate(text.splitlines(), 1):
                nackt = z.strip()
                if nackt.startswith(("#", "REM ", "rem ")) or '"""' in z:
                    continue
                if "Users\\" in z or "Users/" in z:
                    # Ein anderer Benutzername als der eigene ist der Fund.
                    if benutzer and benutzer not in z:
                        treffer.append((os.path.relpath(p, HIER), nr,
                                        nackt[:80], "fremder Benutzer"))
                    elif "v6(21)" in z:
                        treffer.append((os.path.relpath(p, HIER), nr,
                                        nackt[:80], "zeigt auf Papier-Ordner"))
    if not treffer:
        zeile("ok", "keine fremden Pfade in ausgefuehrten Zeilen")
        return
    for datei, nr, text, warum in treffer[:12]:
        zeile("warn", f"{datei}:{nr} - {warum}", text)
    if len(treffer) > 12:
        print(f"          ... und {len(treffer) - 12} weitere")


# ----------------------------------------------------------------- 6. Haken
def _haken_pfade(daten):
    """Alle Dateipfade, die in settings.json auf .claude zeigen.

    [21.09.2026] Vorher wurde settings.json ZEILENWEISE zerlegt und aus
    jedem Stueck `s.split(" ")[-1]` genommen - also das letzte durch
    Leerzeichen getrennte Wort. Das ging genau so lange gut, wie im
    Pfad kein Leerzeichen stand.

    Auf dem Laptop hiess der Benutzer `sven7`. Auf diesem Rechner heisst
    er `Sven <NACHNAME>`. Aus
        C:/Users/<BENUTZER>/Desktop/.../sitzungsstart.py
    wurde dabei
        <NACHNAME>/Desktop/.../sitzungsstart.py
    - ein Pfad, den es nicht gibt. Die Pruefung meldete daraufhin drei
    tote Haken, obwohl alle drei Dateien da waren und funktionierten.

    Ein Fehlalarm ausgerechnet in der Pruefung, die vor stillen Fehlern
    warnen soll. Deshalb jetzt ueber den geparsten JSON-Baum statt ueber
    Textzeilen: ein String, der `.claude` enthaelt, IST der Pfad.

    Die alte Zerlegung bleibt als zweiter Versuch - fuer Eintraege der
    Bauart `python "C:\\...\\haken.py"`, wo Befehl und Pfad in einem
    String stehen.
    """
    gefunden = []

    def sammeln(knoten):
        if isinstance(knoten, dict):
            for w in knoten.values():
                sammeln(w)
        elif isinstance(knoten, (list, tuple)):
            for w in knoten:
                sammeln(w)
        elif isinstance(knoten, str):
            if ".claude" in knoten and ("/" in knoten or "\\" in knoten):
                gefunden.append(knoten)

    sammeln(daten)

    pfade = []
    for roh in gefunden:
        kandidat = roh.strip().strip('"')
        if os.path.exists(kandidat):          # der Normalfall: reiner Pfad
            pfade.append(kandidat)
            continue
        # Befehl und Pfad in einem String? Erst in Anfuehrungszeichen
        # suchen, dann als letztes Wort - wie frueher.
        zerlegt = [t for t in kandidat.split('"') if ".claude" in t]
        zerlegt.append(kandidat.split(" ")[-1])
        for t in zerlegt:
            t = t.strip()
            if t and os.path.exists(t):
                kandidat = t
                break
        pfade.append(kandidat)
    return pfade


def pruefe_haken():
    titel("6. Die Haken (hooks) fuer Claude")
    p = os.path.join(HIER, ".claude", "settings.json")
    if not os.path.exists(p):
        zeile("warn", ".claude/settings.json fehlt",
              "Claude arbeitet dann ohne die Projektregeln.")
        return
    try:
        roh = io.open(p, encoding="utf-8").read()
        json.loads(roh)
    except Exception as e:
        zeile("fehl", f"settings.json nicht lesbar: {type(e).__name__}")
        return
    kaputt = []
    for pfad in _haken_pfade(json.loads(roh)):
        if not os.path.exists(pfad):
            kaputt.append(pfad)
    if kaputt:
        for k in kaputt[:6]:
            zeile("fehl", "Haken zeigt ins Leere", k)
        print("          Die Haken brechen STILL - man merkt es nicht.")
    else:
        zeile("ok", "settings.json lesbar, keine toten Pfade gefunden")


# --------------------------------------------------------- 7. Daten und .env
def pruefe_daten():
    titel("7. Daten, Schluessel, Datenbanken")
    for rel in DATEN:
        p = os.path.join(HIER, rel.replace("/", os.sep))
        if os.path.exists(p):
            mb = os.path.getsize(p) / 1024 / 1024
            zeile("ok", f"{rel}  ({mb:.1f} MB)")
        else:
            zeile("fehl", f"{rel} fehlt")
    env = os.path.join(HIER, ".env")
    if os.path.exists(env):
        # NUR die Existenz. Der Inhalt wird nie gelesen - CLAUDE.md.
        zeile("ok", ".env vorhanden (Inhalt wird nicht gelesen)")
    else:
        zeile("fehl", ".env fehlt - ohne sie kein Zugang zur Boerse",
              "Sie wird NICHT mitkopiert, wenn man nur die Programmdateien\n"
              "zieht: viele Werkzeuge blenden Dateien aus, die mit einem\n"
              "Punkt beginnen.")


def main():
    print("\n" + "=" * 72)
    print("  LAEUFT DIESER ORDNER AUF DIESEM RECHNER?")
    print("=" * 72)
    for f in (pruefe_system, pruefe_python, pruefe_pakete, pruefe_aufgaben,
              pruefe_feste_pfade, pruefe_haken, pruefe_daten):
        try:
            f()
        except Exception as e:
            zeile("fehl", f"Pruefung '{f.__name__}' abgebrochen: "
                          f"{type(e).__name__}: {str(e)[:90]}")

    print("\n" + "=" * 72)
    print(f"  {ok_zahl} in Ordnung · {warn_zahl} zum Ansehen · {fehl_zahl} fehlen")
    if fehl_zahl:
        print("\n  Solange etwas FEHLT, nicht mit echtem Geld starten.")
        print("  Ein Bot, der halb laeuft, ist gefaehrlicher als einer,")
        print("  der gar nicht startet - der zweite faellt auf.")
    else:
        print("\n  Nichts fehlt. Als letzter Schritt vor dem Start:")
        print("     python prozess_frische.py")
        print("  Es beantwortet, ob ein laufender Prozess noch mit altem")
        print("  Programmtext arbeitet.")
    print("=" * 72 + "\n")
    return 1 if fehl_zahl else 0


if __name__ == "__main__":
    sys.exit(main())
