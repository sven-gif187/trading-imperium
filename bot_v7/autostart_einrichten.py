# -*- coding: utf-8 -*-
"""Autostart fuer das Schatten-Universum - OHNE Adminrechte.

WAS HIER GELOEST WIRD
---------------------
In OFFEN.md stand seit dem 18.08.2026 dieser Punkt:

    "Autostart des Schatten-Sammlers mit Adminrechten. Die Aufgabe mit
     Ausloeser 'beim Hochfahren' scheitert an 'Zugriff verweigert'.
     Ersatz laeuft: SchattenUniversumWacht alle 15 Minuten."

Er war einen Monat lang als "nur Kosmetik" abgelegt. Das war er auch -
aber er war ausserdem UNNOETIG. Am 16.09.2026 nachgemessen:

    schtasks /create /sc onstart   -> FEHLER: Zugriff verweigert
    schtasks /create /sc onlogon   -> FEHLER: Zugriff verweigert
    Register-ScheduledTask  -AtLogOn -User <eigener Benutzer>  -> GEHT

DER UNTERSCHIED liegt nicht am Ausloeser, sondern daran, FUER WEN die
Aufgabe gilt. `schtasks /sc onlogon` legt sie ohne weitere Angabe fuer
JEDEN Benutzer des Rechners an - und wer etwas fuer fremde Benutzer
einrichtet, braucht Adminrechte, zu Recht. Wird derselbe Ausloeser auf
den eigenen Benutzer eingegrenzt, faellt dieser Grund weg.

Ein Monat Wartezeit auf Rechte, die nie gebraucht wurden - weil das
erste Werkzeug, das scheiterte, fuer die Antwort gehalten wurde.

WARUM TROTZDEM ZWEI AUFGABEN
----------------------------
    Bei Anmeldung   startet sofort nach dem Hochfahren - keine Luecke.
                    Stirbt der Sammler spaeter, kommt er nicht wieder.
    Alle 15 Minuten faengt genau das ab: Absturz, Abbruch, versehentlich
                    geschlossen.

Der eine deckt den Start ab, der andere den Betrieb. Sie stoeren einander
nicht: beide rufen schatten_starter.py, und der startet nur, wenn nichts
laeuft (seit 16.09. mit Ordnerpruefung, sonst verwechselt er Papier
und Live).

DER PYTHON-PFAD - UND WARUM ER HIER NICHT VERDRAHTET IST
--------------------------------------------------------
AUTOSTART_EINRICHTEN.bat trug den Pfad fest eingetragen:

    ...\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\pythonw.exe

Auf einem anderen Rechner steht dort eine andere Python-Version, und der
Eintrag zeigt ins Leere. Die Aufgabe wird trotzdem angelegt, meldet
Erfolg und tut nichts - dieselbe stille Art Fehler wie am 14.08.2026
(Handbuch, Abschnitt "Warum es keine geplante Windows-Aufgabe dafuer
gibt"). Deshalb wird der Pfad hier aus dem LAUFENDEN Prozess abgeleitet
und auf die bekannte Falle geprueft: der Windows-Store legt eine
0-Byte-Attrappe namens python.exe ab, die in der Aufgabenplanung still
versagt.

Aufruf:
    python autostart_einrichten.py --pruefen     nur nachsehen
    python autostart_einrichten.py               einrichten
    python autostart_einrichten.py --entfernen   beide Aufgaben loeschen
"""
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
STARTER = os.path.join(HIER, "schatten_starter.py")

# Zwei Aufgaben, ein Zweck. Namen tragen LIVE, damit sie nie mit
# SchattenUniversumWacht (Papier-Ordner) verwechselt werden.
T_ANMELDUNG = "SchattenUniversumLIVE_Anmeldung"
T_WACHE = "SchattenUniversumLIVE"
TAKT_MINUTEN = 15


def _laeuft_wirklich(exe):
    """Startet dieser Interpreter - und fuehrt er aus, was man ihm gibt?

    WARUM NICHT os.path.exists ODER DIE DATEIGROESSE
    ------------------------------------------------
    Beides fuehrt in die Irre. Am 16.09.2026 nachgemessen:

        ...\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\python.exe
            exists = True    getsize = 0    laeuft = ja

    Die Store-Eintraege sind Verweise (reparse points), nicht Dateien -
    sie melden ALLE 0 Byte, die funktionierenden wie die Attrappen. Eine
    Groessenpruefung wirft deshalb genau die Interpreter weg, die gehen.

    pythonw.exe schreibt nichts auf den Bildschirm; ob es lief, laesst
    sich nur an seiner WIRKUNG ablesen. Also legt es eine Datei an, und
    wir sehen nach, ob sie da ist. Das ist genau der Weg, den die
    Aufgabenplanung spaeter geht.
    """
    if not exe or not os.path.exists(exe):
        return False
    import tempfile
    marke = os.path.join(tempfile.gettempdir(),
                         f"ti_pyw_probe_{os.getpid()}.txt")
    try:
        if os.path.exists(marke):
            os.remove(marke)
    except OSError:
        pass
    try:
        subprocess.run(
            [exe, "-c", f"open(r'{marke}','w').write('da')"],
            capture_output=True, timeout=60)
    except Exception:
        return False
    try:
        gut = os.path.exists(marke)
        if gut:
            os.remove(marke)
        return gut
    except OSError:
        return True


def pythonw_pfad():
    """Ein Interpreter, der in einer geplanten Aufgabe wirklich laeuft.

    Rueckgabe: (pfad, hinweis). pfad ist None, wenn keiner der Kandidaten
    den Probelauf bestand - dann wird NICHTS angelegt, statt eine Aufgabe
    zu hinterlassen, die Erfolg meldet und ins Leere zeigt.

    Die Reihenfolge ist absichtlich: erst neben dem laufenden Prozess
    (stimmt auf JEDEM Rechner, auch nach einem Umzug auf Windows 11),
    danach die ueblichen Installationsorte von python.org.
    """
    kandidaten = []
    eigen = sys.executable or ""
    if eigen:
        ordner = os.path.dirname(eigen)
        kandidaten.append(os.path.join(ordner, "pythonw.exe"))
        kandidaten.append(eigen)          # notfalls python.exe mit Fenster

    # Rueckfall fuer den Fall, dass dieses Skript aus einer fremden
    # Umgebung laeuft (venv ohne pythonw, eingebettetes Python).
    lokal = os.environ.get("LOCALAPPDATA", "")
    if lokal:
        basis = os.path.join(lokal, "Programs", "Python")
        try:
            for u in sorted(os.listdir(basis), reverse=True):
                kandidaten.append(os.path.join(basis, u, "pythonw.exe"))
        except OSError:
            pass

    gesehen = set()
    for k in kandidaten:
        if not k or k.lower() in gesehen:
            continue
        gesehen.add(k.lower())
        if not _laeuft_wirklich(k):
            continue
        fenster = "" if k.lower().endswith("pythonw.exe") else \
                  "  (ACHTUNG: python.exe statt pythonw.exe - bei jedem " \
                  "Lauf blitzt ein Konsolenfenster auf)"
        return k, fenster
    return None, "kein Interpreter hat den Probelauf bestanden"


def ps(befehl, zeit=300):
    """PowerShell aufrufen. Rueckgabe (rc, ausgabe)."""
    try:
        f = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
            capture_output=True, text=True, timeout=zeit)
        return f.returncode, (f.stdout or "") + (f.stderr or "")
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}"


# Eine Zeile je Aufgabe: Name, Zustand, Ausloeserart, Zielordner.
#
# WARUM MIT -TaskName UND NICHT MIT Where-Object
# ----------------------------------------------
# Hier stand zuerst `Get-ScheduledTask | Where-Object {...}`. Das liest
# ERST alle Aufgaben des Rechners (bei Sven ueber 200, samt Windows-
# Wartung und OneDrive) und wirft danach weg. Auf dem laufenden System
# dauerte das laenger als drei Minuten und lief in den Zeitausfall -
# dreimal hintereinander, weil jeder Schritt eine eigene PowerShell
# startete. Mit -TaskName filtert der Dienst selbst: 13,1 s gemessen.
ABFRAGE = (
    "Get-ScheduledTask -TaskName 'SchattenUniversum*' -EA 0 | "
    "ForEach-Object { "
    "$ausloeser = ($_.Triggers | ForEach-Object { "
    "  $_.CimClass.CimClassName }) -join ',' ; "
    "$pfad = ($_.Actions | ForEach-Object { $_.Arguments }) -join ' ' ; "
    "\"$($_.TaskName)`t$($_.State)`t$ausloeser`t$pfad\" }")


def stand():
    """Was ist eingerichtet? Liest nur, aendert nichts."""
    rc, aus = ps(ABFRAGE)
    return [z for z in aus.splitlines() if z.strip() and "\t" in z]


def _zeige_zeilen(zeilen):
    if not zeilen:
        print("    (keine)")
        return zeilen
    for z in zeilen:
        teile = z.split("\t")
        name = teile[0] if teile else z
        zustand = teile[1] if len(teile) > 1 else "?"
        ausl = teile[2] if len(teile) > 2 else "?"
        ziel = teile[3] if len(teile) > 3 else ""
        # Der Ordner im Argument entscheidet, ob es Papier oder Live ist.
        ordner = "LIVE" if "LIVE" in ziel else \
                 "Papier" if "v6(21)" in ziel else "?"
        art = ("bei Anmeldung" if "Logon" in ausl else
               "nach Zeitplan" if "Time" in ausl else ausl)
        print(f"    {name:<34} {zustand:<8} {art:<15} Ordner: {ordner}")
    return zeilen


def zeige_stand(ueberschrift="Eingerichtete Aufgaben"):
    print(f"\n  {ueberschrift}")
    print("  " + "-" * 68)
    return _zeige_zeilen(stand())


def einrichten():
    pyw, hinweis = pythonw_pfad()
    print("\n" + "=" * 72)
    print("  AUTOSTART FUER DAS SCHATTEN-UNIVERSUM (Ordner trading_imperium_LIVE)")
    print("=" * 72)

    if not os.path.exists(STARTER):
        print(f"\n  ABBRUCH: {STARTER} fehlt.")
        return 1
    if pyw is None:
        print(f"\n  ABBRUCH: {hinweis}")
        print("  Es wird bewusst NICHTS angelegt - eine Aufgabe, die Erfolg")
        print("  meldet und ins Leere zeigt, ist schlimmer als keine.")
        return 1

    print(f"\n  Interpreter : {pyw}{hinweis}")
    print(f"  Starter     : {STARTER}")
    print(f"  Aufgabe 1   : {T_ANMELDUNG}  (bei der Anmeldung)")
    print(f"  Aufgabe 2   : {T_WACHE}  (alle {TAKT_MINUTEN} Minuten)")

    # ALLES IN EINEM POWERSHELL-LAUF. Jeder Start kostet auf dem
    # laufenden System zweistellige Sekunden; drei Starts nacheinander
    # liefen am 16.09. in den Zeitausfall. Anlegen, sofort ausfuehren
    # und Gegenprobe gehoeren ohnehin zusammen.
    befehl = (
        f"$ErrorActionPreference='Stop'; "
        f"$exe = '{pyw}'; $arg = '\"{STARTER}\"'; "
        r"$wer = $env:COMPUTERNAME + '\' + $env:USERNAME; "
        f"$a = New-ScheduledTaskAction -Execute $exe -Argument $arg "
        f"-WorkingDirectory '{HIER}'; "
        # RunLevel Limited: ausdruecklich OHNE erhoehte Rechte. Genau das
        # macht das Anlegen ohne Adminrechte moeglich.
        f"$p = New-ScheduledTaskPrincipal -UserId $wer "
        f"-LogonType Interactive -RunLevel Limited; "
        f"$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        f"-DontStopIfGoingOnBatteries -StartWhenAvailable "
        f"-ExecutionTimeLimit ([TimeSpan]::Zero); "
        # 1) bei der Anmeldung, eine Minute Luft nach dem Hochfahren
        f"try {{ $t = New-ScheduledTaskTrigger -AtLogOn -User $wer; "
        f"$t.Delay = 'PT1M'; "
        f"Register-ScheduledTask -TaskName '{T_ANMELDUNG}' -Action $a "
        f"-Trigger $t -Principal $p -Settings $s -Force | Out-Null; "
        f"'ANGELEGT\t{T_ANMELDUNG}' }} "
        f"catch {{ 'FEHLER\t{T_ANMELDUNG}\t' + $_.Exception.Message }}; "
        # 2) alle 15 Minuten als Waechter gegen Absturz
        f"try {{ $t = New-ScheduledTaskTrigger -Once -At (Get-Date) "
        f"-RepetitionInterval (New-TimeSpan -Minutes {TAKT_MINUTEN}); "
        f"Register-ScheduledTask -TaskName '{T_WACHE}' -Action $a "
        f"-Trigger $t -Principal $p -Settings $s -Force | Out-Null; "
        f"'ANGELEGT\t{T_WACHE}' }} "
        f"catch {{ 'FEHLER\t{T_WACHE}\t' + $_.Exception.Message }}; "
        # 3) sofort ausfuehren, damit nicht bis zum Taktschlag gewartet wird
        f"try {{ Start-ScheduledTask -TaskName '{T_WACHE}'; 'GESTARTET' }} "
        f"catch {{ 'STARTFEHLER\t' + $_.Exception.Message }}; "
        # 4) Gegenprobe im selben Lauf
        f"'--- STAND ---'; {ABFRAGE}")

    print()
    rc, aus = ps(befehl, zeit=300)
    kopf, _, schwanz = aus.partition("--- STAND ---")

    fehler = 0
    for z in kopf.splitlines():
        z = z.strip()
        if not z:
            continue
        if z.startswith("ANGELEGT"):
            print(f"    [ok]      {z.split(chr(9))[-1]}")
        elif z == "GESTARTET":
            print("    [ok]      sofort ausgefuehrt, nicht erst beim Taktschlag")
        else:
            fehler += 1
            print(f"    [FEHLER]  {' '.join(z.split())[:150]}")
    if rc != 0 and not kopf.strip():
        fehler += 1
        print(f"    [FEHLER]  {' '.join(aus.split())[:180]}")

    # === GEGENPROBE: nicht der Rueckgabewert zaehlt, sondern was da ist ===
    zeilen = [z for z in schwanz.splitlines() if z.strip() and "\t" in z]
    print("\n  Gegenprobe - was die Aufgabenplanung jetzt wirklich fuehrt")
    print("  " + "-" * 68)
    _zeige_zeilen(zeilen)

    namen = [z.split("\t")[0] for z in zeilen]
    fehlt = [n for n in (T_ANMELDUNG, T_WACHE) if n not in namen]
    if fehlt:
        print(f"\n  NICHT ANGELEGT: {', '.join(fehlt)}")
        return 1

    print("\n" + "=" * 72)
    print("  Entfernen liesse sich beides mit:")
    print("     python autostart_einrichten.py --entfernen")
    print("=" * 72 + "\n")
    return 1 if fehler else 0


def entfernen():
    print()
    for name in (T_ANMELDUNG, T_WACHE):
        rc, aus = ps(f"Unregister-ScheduledTask -TaskName '{name}' "
                     f"-Confirm:$false -ErrorAction Stop; 'weg'")
        print(f"    {name}: {'entfernt' if rc == 0 else 'nicht vorhanden'}")
    zeige_stand()
    print()
    return 0


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if arg in ("--pruefen", "-p"):
        pyw, hinweis = pythonw_pfad()
        print(f"\n  Interpreter fuer geplante Aufgaben: {pyw or hinweis}{hinweis if pyw else ''}")
        zeige_stand()
        print()
        return 0
    if arg in ("--entfernen", "-e"):
        return entfernen()
    return einrichten()


if __name__ == "__main__":
    sys.exit(main())
