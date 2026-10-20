# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Bots nach Anmeldung wieder starten (Entscheidung Sven F5/F5a, 14.10.2026).

ANLASS: Am 14.10.2026 startete Windows Update den Rechner um 05:32 neu.
v6 und v7 blieben 4,6 Stunden aus, niemand bekam es mit, und eine offene
BTC-Position lief so lange ohne Verlustbremse (inventur.md P0-2).

WAS ES TUT, je Instanz aus pruefstand/instanzen.json:
  1. Liegt autostart/<instanz>.BEWUSST_AUS  -> nichts tun (Sven hat den Bot
     absichtlich aus; z. B. vor einem Patch, Regel 9.3).
  2. Laeuft schon ein app.py aus diesem Ordner -> nichts tun.
  3. Ist der Cockpit-Port schon belegt        -> nichts tun (melden).
  4. Sonst: start_bot.bat der Instanz in einem eigenen Fenster starten,
     danach bis zu 4 Minuten warten, ob der Port aufgeht.
Jeder Lauf schreibt eine Zeile je Instanz nach autostart/autostart.log.

NEUSTART IM TAKT (Entscheidung Sven F5b, 15.10.2026):
  Bis 15.10. lief das Skript nur einmal je Anmeldung. Grund: Ein Neustart
  im Takt koennte einen Bot hochfahren, den Sven gerade fuer einen Patch
  geschlossen hat, und der Bot ueberschreibt dann die Korrektur aus dem
  Speicher. Am 15.10. beendete aber das Update der Claude-App beide Bots
  (20:11-22:36 Berlin aus), und niemand startete sie wieder.
  Seitdem ruft die Aufgabe TI-Bots-Neustart alle 15 min "--takt" auf.
  Schutz gegen den alten Grund: Ein bewusst geschlossener Bot hat IMMER
  eine Sperre (bot_anhalten.py setzt sie selbst, Sven nimmt
  BOT_BEWUSST_AUS.bat). Dann startet dieses Skript nichts (Punkt 1).
  Zwei gleichzeitige Laeufe (Anmeldung + Takt) verhindert die Startsperre
  .start_laeuft: der zweite Lauf tut dann nichts.
  --takt schreibt "laeuft schon" und "bewusst aus" NICHT ins Protokoll
  (sonst 192 Zeilen am Tag), Starts und Fehler schon.

WAS ES BEWUSST NICHT TUT:
  - Nichts am Bot aendern. Es ruft nur die vorhandene start_bot.bat.

Aufrufe:
  pythonw bots_starten.py              echter Lauf (Aufgabe TI-Bots-Autostart, bei Anmeldung)
  pythonw bots_starten.py --takt       echter Lauf, leise (Aufgabe TI-Bots-Neustart, alle 15 min)
  python  bots_starten.py --trocken    nur sagen, was es tun wuerde
  python  bots_starten.py --selbsttest Tests ohne echte Bots
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil

HIER = Path(__file__).resolve().parent
PRUEFSTAND = HIER.parent
LOG = HIER / "autostart.log"
# 14.10.2026 gemessen: v6 oeffnet Port 5050 erst 228 s nach dem Start
# (ATH-Abruf beim Import), am Vormittag war er nach 7 min noch zu.
WARTEN_SEK = 600
BERLIN = ZoneInfo("Europe/Berlin")


def jetzt() -> str:
    t = datetime.now(timezone.utc)
    return f"{t:%Y-%m-%d %H:%M:%S} UTC ({t.astimezone(BERLIN):%H:%M} Berlin)"


def schreibe(zeile: str, log: Path = LOG) -> None:
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{jetzt()}  {zeile}\n")


def port_offen(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def laufende_bots(ordner: Path) -> list[int]:
    """PIDs von Python-Prozessen, die app.py aus genau diesem Ordner fahren."""
    treffer = []
    ziel = str(ordner.resolve()).lower()
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            cmd = p.info["cmdline"] or []
            if not name.startswith("python") or not any(c.endswith("app.py") for c in cmd):
                continue
            if str(Path(p.cwd()).resolve()).lower() == ziel:
                treffer.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return treffer


def starte(ordner: Path) -> None:
    bat = ordner / "start_bot.bat"
    # TI_AUTOSTART=1: das Cockpit-Fenster drueckt nach dem Aufbau selbst
    # STARTEN (patch_autostart_klick.py). Ohne sie wartet der Bot im
    # Fenster-Modus auf einen Klick und handelt nicht - so am 14.10. gesehen.
    env = dict(os.environ, TI_AUTOSTART="1")
    # Doppelte Anfuehrungszeichen wie in den vorhandenen Aufgaben: cmd /c
    # entfernt sonst bei Klammern im Pfad (v6(21)) die aeusseren Zeichen.
    subprocess.Popen(f'cmd.exe /d /c ""{bat}""', cwd=str(ordner), env=env,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)


def entscheide(name: str, inst: dict, hier: Path) -> tuple[str, str]:
    """Liefert (aktion, begruendung). aktion: starten | nichts | fehler."""
    ordner = Path(inst["pfad"])
    sperre = hier / f"{name}.BEWUSST_AUS"
    if sperre.exists():
        grund = sperre.read_text(encoding="utf-8", errors="replace").strip()[:200]
        return "nichts", f"bewusst aus ({grund or 'ohne Grund'})"
    if not (ordner / "start_bot.bat").exists():
        return "fehler", f"start_bot.bat fehlt in {ordner}"
    pids = laufende_bots(ordner)
    if pids:
        return "nichts", f"laeuft schon (PID {', '.join(map(str, pids))})"
    port = inst.get("dashboard_port")
    if port and port_offen(port):
        return "nichts", f"Port {port} belegt, aber kein app.py aus diesem Ordner - bitte ansehen"
    return "starten", "laeuft nicht"


SPERRE_ALT_SEK = 20 * 60     # laenger als WARTEN_SEK: eine aeltere Startsperre ist ein Rest


def startsperre_holen(hier: Path) -> Path | None:
    """[F5b 15.10.2026] Nur ein Lauf zur Zeit (Anmeldung und Takt koennen zusammenfallen).
    Liefert den Sperrpfad oder None, wenn gerade ein anderer Lauf startet."""
    sperre = hier / ".start_laeuft"
    for _ in range(2):
        try:
            fd = os.open(str(sperre), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {jetzt()}".encode("utf-8"))
            os.close(fd)
            return sperre
        except FileExistsError:
            try:
                if time.time() - sperre.stat().st_mtime < SPERRE_ALT_SEK:
                    return None
                sperre.unlink()           # Rest eines abgebrochenen Laufs, kein Datenverlust
            except FileNotFoundError:
                pass
    return None


def lauf(trocken: bool, instanzen_datei: Path = PRUEFSTAND / "instanzen.json",
         hier: Path = HIER, log: Path = LOG, leise: bool = False) -> dict:
    sperre = None if trocken else startsperre_holen(hier)
    if not trocken and sperre is None:
        if not leise:
            schreibe("alle: NICHTS - ein anderer Startlauf ist gerade aktiv", log)
        return {}
    try:
        return _lauf(trocken, instanzen_datei, hier, log, leise)
    finally:
        if sperre is not None:
            try:
                sperre.unlink()
            except FileNotFoundError:
                pass


def _lauf(trocken: bool, instanzen_datei: Path, hier: Path, log: Path, leise: bool) -> dict:
    daten = json.loads(instanzen_datei.read_text(encoding="utf-8"))["instanzen"]
    ergebnis = {}
    for name, inst in daten.items():
        try:
            aktion, grund = entscheide(name, inst, hier)
        except Exception as e:          # eine Instanz darf die andere nicht blockieren
            aktion, grund = "fehler", repr(e)
        ergebnis[name] = (aktion, grund)
        if trocken or aktion != "starten":
            # --takt: Normalzustand (laeuft schon / bewusst aus) nicht alle 15 min protokollieren
            if not (leise and aktion == "nichts" and grund.startswith(("laeuft schon", "bewusst aus"))):
                schreibe(f"{name}: {'TROCKEN ' if trocken else ''}{aktion.upper()} - {grund}", log)
            continue
        starte(Path(inst["pfad"]))
        schreibe(f"{name}: GESTARTET - {grund}", log)
        schreibe(f"{name}: START durch Autostart - {grund}", hier / "start_stopp.log")
    if not trocken:
        for name, (aktion, _) in ergebnis.items():
            if aktion != "starten":
                continue
            port = daten[name].get("dashboard_port")
            ende = time.time() + WARTEN_SEK
            while time.time() < ende and not (port and port_offen(port)):
                time.sleep(5)
            ok = bool(port and port_offen(port))
            schreibe(f"{name}: {'OK Port ' + str(port) + ' offen' if ok else 'FEHLER Port ' + str(port) + ' nach ' + str(WARTEN_SEK) + ' s noch zu'}", log)
    return ergebnis


def selbsttest() -> int:
    """Drei Tests ohne echte Bots: Reproduktion, Normalfall, Grenzfall."""
    fehler = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ordner = tmp / "bot (21)"
        ordner.mkdir()
        (ordner / "start_bot.bat").write_text("@echo off\n", encoding="utf-8")
        frei = 59999
        inst = {"pfad": str(ordner), "dashboard_port": frei}
        datei = tmp / "instanzen.json"
        datei.write_text(json.dumps({"instanzen": {"tX": inst}}), encoding="utf-8")
        log = tmp / "test.log"

        # 1 Reproduktion 14.10.: Bot aus, keine Sperre -> muss STARTEN sagen
        r = lauf(True, datei, tmp, log)["tX"][0]
        fehler += r != "starten"
        print(f"  {'OK  ' if r == 'starten' else 'FEHL'} Reproduktion: Bot aus -> {r}")

        # 2 Normalfall: Sperre gesetzt -> nichts tun, Grund im Log
        (tmp / "tX.BEWUSST_AUS").write_text("Patch E8", encoding="utf-8")
        r = lauf(True, datei, tmp, log)["tX"]
        ok = r[0] == "nichts" and "Patch E8" in r[1]
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Sperre: {r}")

        # 2b F5b: Takt-Lauf (echt, leise) mit Sperre -> nichts starten, keine Logzeile
        zeilen = len(log.read_text(encoding="utf-8").splitlines())
        r = lauf(False, datei, tmp, log, leise=True)["tX"]
        neu = len(log.read_text(encoding="utf-8").splitlines()) - zeilen
        ok = r[0] == "nichts" and neu == 0 and not (tmp / ".start_laeuft").exists()
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Takt mit Sperre: {r[0]}, {neu} Logzeilen, Startsperre wieder frei")
        (tmp / "tX.BEWUSST_AUS").unlink()

        # 2c F5b: laeuft gerade ein anderer Startlauf -> dieser tut nichts (kein Doppelstart)
        (tmp / ".start_laeuft").write_text("fremd", encoding="utf-8")
        r = lauf(False, datei, tmp, log, leise=True)
        ok = r == {} and (tmp / ".start_laeuft").read_text(encoding="utf-8") == "fremd"
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Startsperre eines anderen Laufs: kein Start ({r})")
        alt = time.time() - SPERRE_ALT_SEK - 60
        os.utime(tmp / ".start_laeuft", (alt, alt))
        r = startsperre_holen(tmp)
        ok = r is not None and (tmp / ".start_laeuft").read_text(encoding="utf-8") != "fremd"
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} veraltete Startsperre (Rest) wird uebernommen")
        if r is not None:
            r.unlink()

        # 3 Grenzfall: Port belegt von fremdem Prozess -> nichts tun, melden
        srv = socket.socket(); srv.bind(("127.0.0.1", frei)); srv.listen(1)
        try:
            r = lauf(True, datei, tmp, log)["tX"]
        finally:
            srv.close()
        ok = r[0] == "nichts" and "belegt" in r[1]
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Port belegt: {r}")

        # 3b Grenzfall: start_bot.bat fehlt -> fehler, kein Absturz
        (ordner / "start_bot.bat").unlink()
        r = lauf(True, datei, tmp, log)["tX"][0]
        fehler += r != "fehler"
        print(f"  {'OK  ' if r == 'fehler' else 'FEHL'} start_bot.bat fehlt -> {r}")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    erg = lauf(trocken="--trocken" in sys.argv, leise="--takt" in sys.argv)
    if "--trocken" in sys.argv:
        for k, v in erg.items():
            print(f"{k}: {v[0]} - {v[1]}")
