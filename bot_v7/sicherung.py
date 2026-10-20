"""
Sicherung des gesamten Projekts auf eine zweite Festplatte.

WARUM ES DIESE DATEI GIBT (Punkt 28, GEFUNDENE-PROBLEME.md)
-----------------------------------------------------------
Bis zum 11.08.2026 gab es keine Kopie dieses Projekts ausserhalb dieser
einen Festplatte. Sieben Monate Arbeit, 2.511 Dateien, alle Messreihen,
beide Handbuecher. In der Forschungs-Dokumentation stand das sogar
woertlich: "Ein Festplattenfehler loescht Messung und Beleg gleichzeitig."

Seit dem 11.08. liegt der CODE in einem lokalen Git-Repository. Das
genuegt aber NICHT als Sicherung, aus zwei Gruenden:

  1. Git liegt im selben Ordner auf derselben Platte. Faellt die Platte
     aus, ist das Repository mit weg.
  2. Git enthaelt bewusst nicht die Daten - Datenbanken, Modelle und die
     671 MB Orderbuch-Aufzeichnungen sind ausgeschlossen, weil sie das
     Repository unbrauchbar aufblaehen wuerden.

Dieses Skript schliesst beide Luecken: es kopiert ALLES, auch das
Git-Repository und die ausgeschlossenen Daten.

WAS ES TUT
----------
Spiegelt den Projektordner auf ein Ziel (externe Platte, zweite interne
Platte, Netzlaufwerk). Beim zweiten Lauf werden nur Aenderungen
uebertragen, das dauert dann Sekunden statt Minuten.

Ausgelassen werden nur Dinge, die sich von selbst neu bilden:
__pycache__ (Python-Zwischenstand) und die Papierkorb-Ordner.

Die .env mit dem Telegram-Token wird standardmaessig NICHT mitkopiert.

[KORREKTUR 19.08.2026] Hier stand bis heute das Gegenteil ("wird
MITKOPIERT"). Der Text stammte aus der ersten Fassung, als das Ziel eine
externe Platte war. Inzwischen laeuft die Sicherung nach OneDrive - und
dort ist ein Token ein Risiko, das man nicht zurueckholen kann. Der Code
macht es seit laengerem richtig (Zeile 185), nur der Kopf behauptete das
Gegenteil. Aufgefallen beim Sicherungslauf am 19.08.: das Programm meldete
"bewusst ausgelassen", waehrend der Kopf drei Zeilen weiter oben
"MITKOPIERT" versprach.

Wer auf eine LOKALE Platte sichert, an die nur er herankommt, nimmt sie
mit dazu:

    python sicherung.py --mit-zugangsdaten D:\trading_imperium_sicherung

Ohne .env ist die Wiederherstellung um genau eine Sache unvollstaendig:
den Telegram-Token. Der ist bei BotFather in einer Minute neu erzeugt -
ein Leck dagegen ist endgueltig.

AUFRUF
------
    python sicherung.py D:\\trading_imperium_sicherung
    python sicherung.py --pruefen D:\\trading_imperium_sicherung

--pruefen zeigt nur an, was passieren wuerde, ohne etwas zu schreiben.
"""
import glob
import os
import sqlite3
import subprocess
import sys
import time

# Ordner, die sich von selbst neu bilden - kopieren waere Verschwendung.
AUSLASSEN_ORDNER = ["__pycache__", ".pytest_cache", ".mypy_cache"]

HIER = os.path.dirname(os.path.abspath(__file__))


def datenbank_schnappschuesse(ziel):
    """Sauberer Abzug jeder SQLite-Datenbank, waehrend der Bot weiterlaeuft.

    WARUM DAS NOETIG IST: robocopy kopiert eine Datei so, wie sie in dem
    Moment auf der Platte liegt. Schreibt der Bot gerade mitten hinein -
    und er schreibt alle paar Sekunden - entsteht eine Kopie mit halbem
    Datensatz. SQLite merkt das erst beim Oeffnen: "database disk image is
    malformed". Man haette also eine Sicherung, die aussieht wie eine
    Sicherung und im Ernstfall wertlos ist.

    sqlite3.backup() nimmt stattdessen einen in sich stimmigen Abzug, auch
    waehrend geschrieben wird. Die Kopien landen in einem eigenen Ordner
    NEBEN der robocopy-Kopie - damit gibt es beides: den rohen Stand und
    einen garantiert lesbaren.
    """
    abzug_ordner = os.path.join(ziel, "_datenbank_schnappschuss")
    os.makedirs(abzug_ordner, exist_ok=True)
    ergebnisse = []
    for db in sorted(glob.glob(os.path.join(HIER, "**", "*.db"), recursive=True)):
        if "__pycache__" in db or os.path.sep + "_archive" in db:
            continue
        name = os.path.relpath(db, HIER).replace(os.path.sep, "__")
        abzug = os.path.join(abzug_ordner, name)
        try:
            quelle = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            kopie = sqlite3.connect(abzug)
            with kopie:
                quelle.backup(kopie)
            kopie.close()
            quelle.close()
            # Gegenprobe: laesst sich der Abzug wirklich lesen?
            pruef = sqlite3.connect(abzug)
            pruef.execute("PRAGMA quick_check").fetchone()
            pruef.close()
            ergebnisse.append((name, os.path.getsize(abzug), None))
        except Exception as e:
            ergebnisse.append((name, 0, str(e)[:60]))
    return ergebnisse


def groesse_lesbar(bytes_):
    for einheit in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {einheit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def projekt_groesse():
    """Gesamtgroesse und Dateizahl, ohne die ausgelassenen Ordner."""
    summe = anzahl = 0
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner if o not in AUSLASSEN_ORDNER]
        for d in dateien:
            try:
                summe += os.path.getsize(os.path.join(wurzel, d))
                anzahl += 1
            except OSError:
                pass
    return summe, anzahl


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith("--")]
    nur_pruefen = "--pruefen" in sys.argv
    mit_env = "--mit-zugangsdaten" in sys.argv

    print("=" * 66)
    print("SICHERUNG - Projektkopie auf eine zweite Festplatte")
    print("=" * 66)

    if not argumente:
        print("Es fehlt das Ziel.\n")
        print("  python sicherung.py D:\\trading_imperium_sicherung")
        print("  python sicherung.py --pruefen D:\\trading_imperium_sicherung\n")
        print("Verfuegbare Laufwerke:")
        for buchstabe in "DEFGHIJKLMNOPQRSTUVWXYZ":
            pfad = f"{buchstabe}:\\"
            if os.path.exists(pfad):
                try:
                    frei = groesse_lesbar(os.statvfs(pfad).f_bavail *
                                          os.statvfs(pfad).f_frsize)
                except (AttributeError, OSError):
                    import shutil
                    try:
                        frei = groesse_lesbar(shutil.disk_usage(pfad).free)
                    except OSError:
                        frei = "?"
                print(f"  {pfad}  ({frei} frei)")
        return 1

    ziel = os.path.abspath(argumente[0])

    # Sicherheitsnetz: niemals in den Projektordner selbst spiegeln -
    # robocopy /MIR wuerde sich sonst rekursiv selbst fressen.
    if os.path.normcase(ziel).startswith(os.path.normcase(HIER)):
        print(f"ABBRUCH: Das Ziel liegt INNERHALB des Projektordners.")
        print(f"  Quelle: {HIER}")
        print(f"  Ziel  : {ziel}")
        print("  Eine Sicherung auf derselben Platte im selben Ordner ist")
        print("  keine Sicherung - und /MIR wuerde sich selbst kopieren.")
        return 1

    summe, anzahl = projekt_groesse()
    print(f"Quelle : {HIER}")
    print(f"Ziel   : {ziel}")
    print(f"Umfang : {anzahl} Dateien, {groesse_lesbar(summe)}")
    print("-" * 66)

    if not os.path.exists(os.path.splitdrive(ziel)[0] + os.sep):
        print(f"ABBRUCH: Laufwerk {os.path.splitdrive(ziel)[0]} ist nicht da.")
        print("  Externe Platte angesteckt?")
        return 1

    # robocopy /MIR spiegelt: neue Dateien kommen dazu, geloeschte gehen weg.
    # /XD laesst Ordner aus, /R:2 begrenzt Wiederholungen bei Lesefehlern,
    # /NP unterdrueckt die Prozentanzeige (sonst tausende Zeilen).
    befehl = ["robocopy", HIER, ziel, "/MIR", "/R:2", "/W:2", "/NP", "/NDL"]
    for ordner in AUSLASSEN_ORDNER:
        befehl += ["/XD", ordner]

    # Zugangsdaten nur mitnehmen, wenn ausdruecklich gewuenscht.
    #
    # Bei einer Sicherung auf eine externe Platte, die im Schrank liegt, ist
    # der Token gut aufgehoben. Bei einer Cloud-Sicherung verlaesst er den
    # Rechner - und ein einmal hochgeladenes Geheimnis holt man nicht zurueck.
    # Der Token ist bei BotFather in einer Minute neu erzeugt; ein Leck ist
    # nicht rueckgaengig zu machen. Deshalb ist WEGLASSEN die Vorgabe.
    if not mit_env:
        befehl += ["/XF", ".env", ".env.local", "*.key", "*.pem"]
    if nur_pruefen:
        befehl.append("/L")     # nur auflisten, nichts schreiben
        print("PRUEFLAUF - es wird nichts geschrieben.\n")

    start = time.time()
    ergebnis = subprocess.run(befehl, capture_output=True, text=True,
                              errors="replace")
    dauer = time.time() - start

    # robocopy-Rueckgabewerte sind ein Bitmuster, kein normaler Exit-Code:
    #   1 = Dateien kopiert | 2 = Extras im Ziel | 4 = Abweichungen
    #   8 = EINZELNE Dateien nicht kopierbar | 16 = schwerer Fehler
    #
    # [KORRIGIERT 12.08.2026] Frueher galt hier alles ab 8 als Abbruch. Beim
    # ersten echten Lauf schlug genau das zu: eine einzige gesperrte Datei
    # (capture.lock des laufenden Forschungs-Sammlers) setzte Bit 8, und das
    # Skript brach ab - BEVOR es die Datenbank-Abzuege gezogen und die
    # Hinweisdatei geschrieben hatte. Also ausgerechnet die Schritte
    # uebersprungen, die gegen laufende Schreibzugriffe helfen sollen.
    #
    # Gesperrte Dateien sind bei laufendem Bot der Normalfall, und
    # .lock/.pid sind in einer Sicherung ohnehin wertlos. Nur Bit 16 ist
    # ein echter Abbruchgrund.
    if ergebnis.returncode & 16:
        print(f"ABBRUCH: schwerer robocopy-Fehler (Code {ergebnis.returncode})")
        print((ergebnis.stdout or "")[-1200:])
        return 1
    if ergebnis.returncode & 8:
        print(f"HINWEIS: einzelne Dateien konnten nicht kopiert werden "
              f"(robocopy-Code {ergebnis.returncode}).")
        print("  Meist Sperrdateien laufender Prozesse (.lock/.pid) - die")
        print("  sind in einer Sicherung wertlos. Die Datenbanken werden")
        print("  gleich zusaetzlich sauber abgezogen.")
        print()

    for zeile in (ergebnis.stdout or "").splitlines()[-12:]:
        if zeile.strip():
            print(zeile)

    print("-" * 66)
    if nur_pruefen:
        print(f"Prueflauf fertig ({dauer:.1f}s). Nichts geschrieben.")
        return 0

    print(f"Dateikopie fertig in {dauer:.1f}s.")

    # Der Bot schreibt weiter, waehrend kopiert wird - die rohen
    # Datenbank-Dateien koennen also mitten im Schreibvorgang erwischt
    # worden sein. Deshalb zusaetzlich saubere Abzuege.
    print()
    print("Datenbank-Schnappschuesse (lesbar geprueft):")
    for name, groesse, fehler in datenbank_schnappschuesse(ziel):
        if fehler:
            print(f"  FEHLER  {name}: {fehler}")
        else:
            print(f"  OK      {name}  ({groesse/1024/1024:.1f} MB)")

    hinweis = os.path.join(ziel, "WICHTIG-ZUM-WIEDERHERSTELLEN.txt")
    try:
        with open(hinweis, "w", encoding="utf-8") as f:
            f.write(
                "SICHERUNG DES TRADING-BOTS\n"
                "==========================\n\n"
                f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}\n"
                f"Quelle  : {HIER}\n\n"
                "WAS FEHLT UND WARUM\n"
                "-------------------\n")
            if not mit_env:
                f.write(
                    "Die Datei .env ist NICHT enthalten. Sie enthaelt den\n"
                    "Telegram-Bot-Token. Nach einer Wiederherstellung muss sie\n"
                    "neu angelegt werden:\n\n"
                    "    TELEGRAM_BOT_TOKEN=<neuer Token von BotFather>\n\n"
                    "Vorlage: .env.example. Der Token ist in einer Minute neu\n"
                    "erzeugt - ein Geheimnis in fremdem Speicher nicht.\n"
                    "Wer ihn doch mitsichern will: --mit-zugangsdaten\n\n")
            f.write(
                "__pycache__ fehlt ebenfalls - der bildet sich von selbst neu.\n\n"
                "ZWEI KOPIEN DER DATENBANKEN\n"
                "---------------------------\n"
                "1. In data_store/ liegen die Dateien so, wie sie waehrend des\n"
                "   laufenden Betriebs kopiert wurden. Sie KOENNEN mitten im\n"
                "   Schreibvorgang erwischt worden sein.\n"
                "2. In _datenbank_schnappschuss/ liegen saubere Abzuege, mit\n"
                "   SQLite selbst gezogen und danach auf Lesbarkeit geprueft.\n"
                "   Im Zweifel DIESE nehmen.\n\n"
                "WIEDERHERSTELLEN\n"
                "----------------\n"
                "Ordner zurueckkopieren, .env neu anlegen, dann:\n"
                "    python check_install.py\n")
        print(f"\nHinweis-Datei geschrieben: {os.path.basename(hinweis)}")
    except Exception as e:
        print(f"\nHinweis-Datei fehlgeschlagen: {str(e)[:60]}")

    print("-" * 66)
    print(f"Sicherung fertig. Kopie liegt in: {ziel}")
    if not mit_env:
        print("HINWEIS: .env (Telegram-Token) wurde bewusst ausgelassen.")
    print()
    print("Beim naechsten Lauf werden nur Aenderungen uebertragen.")
    print("Sinnvoll: einmal woechentlich, und immer vor groesseren")
    print("Umbauten am Bot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
