# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W5 Betrieb (MASTERPROMPT_AGENTEN.md 6.1) - alle 5 Minuten, ohne KI, nur lesend auf die Bots.

ANLASS: Nachlauf v6 17 Tage tot (27.09.-14.10.), Bots 4,6 h aus nach Windows Update
(14.10.), Fenster wartete auf STARTEN (14.10.) - niemand hat es rechtzeitig gemerkt.

Je Instanz aus instanzen.json:
  prozess        app.py aus genau diesem Ordner laeuft (sonst ROT, ausser BEWUSST_AUS)
  port           Cockpit-Port offen (sonst GELB; ROT wenn > 15 min nach Prozessstart)
  bot_state      bot_state.json juenger als 10 min (Bot speichert alle 30 s)
  system_log     letzte BOT-Zeile in system.log juenger als 10 min (nur Kennungen, die allein der Bot schreibt;
                 [19.10.2026] vorher Datei-Alter - schatten_universum.py schreibt in dieselbe Datei, deshalb
                 waehrend des v6-Haengers 16./17.10. 25x falsch GRUEN, berichte/2026-10-17_v6_haenger.md)
  telemetrie     telemetrie.db/-wal juenger als 30 min (GELB) / 2 h (ROT)
  nachlauf       nachlauf.db juenger als 4 h (GELB) / 12 h (ROT)
  schatten       schatten_universum.db juenger als 2 h (GELB) / 12 h (ROT)
  positionsverl. positionsverlauf.db juenger als 1 h, nur wenn Positionen offen
  neustart       PID gewechselt ohne STOPP im Start/Stopp-Protokoll = Absturz/Fremdstart (GELB, Meldung)
Gemeinsam: Windows-Aufgaben vorhanden und letzter Lauf ok, Plattenplatz, Internet (Binance/Bitvavo).
[15.10.2026, Lagebericht Punkt 3] Netzausfall = "Datenquelle/Internet weg" (GELB), nicht "Prozess still" (ROT):
  Ist Binance (Kursquelle der Bots) nicht erreichbar oder erst seit < 30 min zurueck, werden ROT-Befunde der
  kursabhaengigen Dateien (telemetrie, nachlauf, schatten, positionsverlauf) zu GELB. Prozess, Port, bot_state
  und system_log bleiben scharf (ein haengender Bot schreibt auch ohne Netz seinen Zustand). Die Pruefung
  internet selbst ist hoechstens GELB. Vorher: v7 telemetrie 65 Laeufe ROT in der Nacht 14./15.10.

Ausgabe: pruefstand/waechter.db (WAL) Tabellen betrieb, ereignisse; pruefstand/status.json (Ampel W5).
Telegram: nur bei WECHSEL einer Pruefung nach ROT (und bei Erholung), hoechstens alle 6 h je Schluessel.
  [19.10.2026] Bleibt bot_state oder prozess ROT, kommt alle 2 h eine Erinnerung (v6-Haenger 16./17.10.: 35 h ROT,
  nur EIN Telegram). Zeitpunkte in w5_zustand.json unter "rot_meldung".
Totmannschalter: taeglich ab 08:00 Berlin einmal Lebenszeichen mit Tagesuebersicht.
Aufrufe: pythonw w5_betrieb.py | python w5_betrieb.py --zeigen | --selbsttest
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(P / "autostart"))
import telegram_meldung as tm  # noqa: E402
from bots_starten import laufende_bots, port_offen  # noqa: E402

DB = P / "waechter.db"
STATUS = P / "status.json"
ZUSTAND = HIER / "w5_zustand.json"
BERLIN = ZoneInfo("Europe/Berlin")
# [15.10.2026, F5b] TI-Bots-Neustart: bots_starten.py --takt alle 15 min startet ausgefallene Bots neu
AUFGABEN = ["TI-Bots-Autostart", "TI-Bots-Neustart", "TI6-Tagescheck", "TI7-Tagescheck", "TI6-Sammler",
            "ForschungCapture", "SchattenUniversumLIVE", "TI6-Wochensicherung"]
STUFE = {"GRUEN": 0, "GELB": 1, "ROT": 2}
NETZ_ABHAENGIG = {"telemetrie", "nachlauf", "schatten", "positionsverlauf"}   # schreiben nur mit frischen Kursen
NETZ_NACHLAUF_MIN = 30   # so lange nach Rueckkehr des Netzes gelten stille Kursdateien noch als Netzfolge
ZIELE = {"Binance": "https://api.binance.com/api/v3/time", "Bitvavo": "https://api.bitvavo.com/v2/time"}
# [19.10.2026] Kennungen, die nur der Bot-Prozess selbst schreibt (app.py, runtime/exit_monitor.py, runtime/reporting.py,
# runtime/state_manager.py, core/balance_reporter.py, core/auto_restart.py; v6 und v7 gleich). Die Hilfsprozesse
# schatten_universum.py, nachlauf.py und positionsverlauf.py schreiben ueber DataAgent/SignalAgent/StateStore in dasselbe
# system.log, aber nur mit DATA, SIGNAL, JOURNAL, STATE. Normal kommt eine Bot-Zeile alle <= 1,6 min (gemessen 17.-19.10.).
BOT_KENNUNGEN = {"MONITOR", "LOOP", "HEART", "HEARTBEAT", "BALANCE", "APP"}
LOG_ZEILE = re.compile(r"^\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\] \[[A-Z]+\] \[([^\]]+)\]")
LOG_FENSTER = (256 * 1024, 4 * 1024 * 1024)       # erst die letzten 256 KB, sonst die letzten 4 MB lesen
HAENGER_AUSZUG = HIER / "daten_w5" / "haenger_v6_20261016_auszug.log"
WIEDERHOLEN = {"bot_state", "prozess"}          # [19.10.2026] diese Pruefungen erinnern, solange sie ROT bleiben
WIEDERHOLEN_MIN = 120


def alter_min(p: Path) -> float | None:
    kand = [x for x in (p, p.with_name(p.name + "-wal")) if x.exists()]
    if not kand:
        return None
    return (time.time() - max(x.stat().st_mtime for x in kand)) / 60


def ampel(alter: float | None, gelb: float, rot: float) -> str:
    if alter is None:
        return "ROT"
    return "ROT" if alter > rot else ("GELB" if alter > gelb else "GRUEN")


def letzte_bot_zeit(zeilen) -> datetime | None:
    """Juengster Zeitstempel (UTC) einer Zeile mit Bot-Kennung. Der Bot-Logger schreibt UTC ohne Zone."""
    best = None
    for z in zeilen:
        m = LOG_ZEILE.match(z)
        if m and m.group(2) in BOT_KENNUNGEN and (best is None or m.group(1) > best):
            best = m.group(1)
    return datetime.fromisoformat(best).replace(tzinfo=timezone.utc) if best else None


def bot_log_alter(pfad: Path, jetzt: datetime) -> tuple[float | None, str]:
    """[19.10.2026] Alter der letzten BOT-Zeile in system.log, nicht der Datei.
    Liest nur das Dateiende (256 KB, sonst 4 MB); findet sich dort keine Bot-Zeile, auch das Ende von system.log.1
    (der Bot rotiert ab 20 MB). (alter_min, befund); alter None = ROT."""
    if not pfad.exists():
        return None, "fehlt"
    for datei in (pfad, pfad.with_name(pfad.name + ".1")):
        if not datei.exists():
            continue
        groesse = datei.stat().st_size
        for fenster in LOG_FENSTER:
            with open(datei, "rb") as f:
                f.seek(max(0, groesse - fenster))
                t = letzte_bot_zeit(f.read().decode("utf-8", "replace").splitlines())
            if t:
                a = (jetzt - t).total_seconds() / 60
                return a, (f"letzte Bot-Zeile vor {a:.0f} min" + ("" if datei == pfad else " (in system.log.1)"))
            if fenster >= groesse:
                break
    return None, "keine Bot-Zeile am Ende von system.log/.1 (nur Zeilen anderer Prozesse)"


def pruefe_instanz(name: str, inst: dict, zustand: dict) -> list[tuple]:
    o = Path(inst["pfad"])
    ds = o / "data_store"
    out = []
    aus = (P / "autostart" / f"{name}.BEWUSST_AUS").exists()
    pids = laufende_bots(o)
    if not pids:
        out.append((name, "prozess", "GELB" if aus else "ROT", "bewusst aus" if aus else "app.py laeuft NICHT"))
        zustand[f"{name}_pid"] = None
        return out
    pid = pids[0]
    start = datetime.fromtimestamp(psutil.Process(pid).create_time(), timezone.utc)
    seit_min = (datetime.now(timezone.utc) - start).total_seconds() / 60
    out.append((name, "prozess", "GRUEN", f"PID {pid} seit {start.astimezone(BERLIN):%d.%m. %H:%M}"))
    vorher = zustand.get(f"{name}_pid")
    if vorher and vorher != pid:
        log = (P / "autostart" / "start_stopp.log")
        txt = log.read_text(encoding="utf-8", errors="replace")[-3000:] if log.exists() else ""
        geplant = f"{name}: STOPP" in txt or f"{name}: START" in txt
        out.append((name, "neustart", "GELB",
                    f"neuer Prozess (PID {vorher} -> {pid}), {'mit' if geplant else 'OHNE'} Eintrag im Start/Stopp-Protokoll"))
    zustand[f"{name}_pid"] = pid
    port = inst.get("dashboard_port")
    if port:
        offen = port_offen(port)
        out.append((name, "port", "GRUEN" if offen else ("GELB" if seit_min < 15 else "ROT"),
                    f"Port {port} {'offen' if offen else 'zu'}" + ("" if offen else f" (Prozess seit {seit_min:.0f} min - STARTEN gedrueckt?)")))
    for pr, datei, g, r in (("bot_state", ds / "bot_state.json", 5, 10), ("system_log", ds / "system.log", 5, 10),
                            ("telemetrie", ds / "telemetrie.db", 30, 120), ("nachlauf", ds / "nachlauf.db", 240, 720),
                            ("schatten", ds / "schatten_universum.db", 120, 720)):
        if pr == "system_log":                          # [19.10.2026] nur Bot-Zeilen zaehlen, nicht das Datei-Alter
            a, txt = bot_log_alter(datei, datetime.now(timezone.utc))
            out.append((name, pr, ampel(a, g, r), txt))
            continue
        a = alter_min(datei)
        out.append((name, pr, ampel(a, g, r), "fehlt" if a is None else f"zuletzt vor {a:.0f} min"))
    try:
        s = json.loads((ds / "bot_state.json").read_text(encoding="utf-8"))
        offene = len(s.get("open_positions_backup") or {})
    except Exception:
        offene = -1
    if offene > 0:
        a = alter_min(ds / "positionsverlauf.db")
        out.append((name, "positionsverlauf", ampel(a, 60, 180),
                    f"{offene} Position(en) offen, Verlauf zuletzt vor {a:.0f} min" if a is not None else "positionsverlauf.db fehlt"))
    return out


def pruefe_gemeinsam() -> list[tuple]:
    out = []
    try:
        r = subprocess.run(["schtasks", "/query", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=60,
                           encoding="cp850", errors="replace")
        da = {z.split('","')[0].strip('"').lstrip("\\") for z in r.stdout.splitlines() if z}
        fehlen = [a for a in AUFGABEN if a not in da]
        out.append(("alle", "aufgaben", "ROT" if fehlen else "GRUEN", f"fehlen: {fehlen}" if fehlen else f"{len(AUFGABEN)} vorhanden"))
    except Exception as e:
        out.append(("alle", "aufgaben", "GELB", f"nicht abfragbar: {type(e).__name__}"))
    out.append(aufgaben_ergebnis())
    out.append(energie_pruefen())
    frei = shutil.disk_usage("C:\\").free / 2**30
    out.append(("alle", "platte", "ROT" if frei < 3 else ("GELB" if frei < 10 else "GRUEN"), f"{frei:.1f} GB frei"))
    return out


def aufgaben_ergebnis() -> tuple:
    """[15.10.2026] Nachts 02:15/02:20 fielen Papier-Wettkampf und W1 ohne Netz aus (Code 1) - niemand hat es gemeldet.
    Prueft das letzte Ergebnis aller Pruefstand-Aufgaben TI-*. 0 = ok, 267009 = laeuft gerade, 267011 = noch nie gelaufen."""
    ps = ("Get-ScheduledTask -TaskName 'TI-*' | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
          "[pscustomobject]@{n=$_.TaskName; r=$i.LastTaskResult; t=$i.LastRunTime.ToString('dd.MM. HH:mm')} } | ConvertTo-Json")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True,
                           timeout=60, encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        daten = json.loads(r.stdout or "[]")
        daten = [daten] if isinstance(daten, dict) else daten
        schlecht = [f"{d['n']} Code {d['r']} ({d['t']})" for d in daten if int(d["r"]) not in (0, 267009, 267011)]
        return ("alle", "aufgaben_ergebnis", "GELB" if schlecht else "GRUEN",
                ("letzter Lauf fehlgeschlagen: " + "; ".join(schlecht)) if schlecht else f"{len(daten)} TI-Aufgaben, letzter Lauf ok")
    except Exception as e:
        return ("alle", "aufgaben_ergebnis", "GELB", f"nicht abfragbar: {type(e).__name__}")


def energie_pruefen() -> tuple:
    """[15.10.2026] Lueckenklaerung P0-7: v6 stand 38 h still, weil der Rechner im Standby war. Sven hat Standby
    und Ruhezustand am 15.10. ausgeschaltet. Ein Windows-Update kann das Energieschema zuruecksetzen - deshalb
    prueft W5 die Wartezeiten am Netzstrom (0 = nie). Akku-Werte zaehlen nicht (Desktop-Betrieb)."""
    import re
    werte = {}
    for name in ("STANDBYIDLE", "HIBERNATEIDLE"):
        try:
            r = subprocess.run(["powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", name], capture_output=True, text=True,
                               timeout=30, encoding="cp850", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            m = re.search(r"(?:Wechselstrom|AC Power)[^:]*:\s*0x([0-9a-fA-F]+)", r.stdout)
            werte[name] = int(m.group(1), 16) if m else None
        except Exception:
            werte[name] = None
    if any(v is None for v in werte.values()):
        return ("alle", "energie", "GELB", f"Energieschema nicht lesbar: {werte}")
    an = {k: v for k, v in werte.items() if v > 0}
    return ("alle", "energie", "GELB" if an else "GRUEN",
            ("Rechner geht schlafen nach " + ", ".join(f"{k} {v // 60} min" for k, v in an.items()) + " - Bots stehen dann still")
            if an else "Standby und Ruhezustand am Netzstrom: nie")


def netz_pruefen(zustand: dict, jetzt: datetime, weg: list[str] | None = None) -> tuple:
    """[15.10.2026] Nacht 14./15.10. etwa 23:10-10:40 ohne Internet: Bots ohne Kurse, Nachtlaeufe gescheitert,
    Sammler-Luecke. W5 lief lokal weiter und sah nur Folgen. Jetzt direkt: Binance (Kurse der Bots) und Bitvavo
    (Zielboerse) erreichbar? Ein Netzausfall ist "Datenquelle/Internet weg" und hoechstens GELB (Lagebericht
    15.10. Punkt 3), egal wie lange. Merkt sich Beginn (netz_weg_seit) und Rueckkehr (netz_zurueck) im Zustand."""
    if weg is None:
        import urllib.request
        weg = []
        for n, u in ZIELE.items():
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "pruefstand-w5"}), timeout=10) as r:
                    r.read()
            except Exception:
                weg.append(n)
    zustand["netz_weg"] = weg
    seit = zustand.get("netz_weg_seit")
    if not weg:
        zustand["netz_weg_seit"] = None
        if seit:
            zustand["netz_zurueck"] = jetzt.isoformat()
            a = datetime.fromisoformat(seit)
            return ("alle", "internet", "GRUEN", f"wieder erreichbar, Ausfall {(jetzt - a).total_seconds() / 60:.0f} min "
                                                 f"({a.astimezone(BERLIN):%d.%m. %H:%M} bis {jetzt.astimezone(BERLIN):%H:%M})")
        return ("alle", "internet", "GRUEN", "Binance und Bitvavo erreichbar")
    if not seit:
        seit = jetzt.isoformat()
        zustand["netz_weg_seit"] = seit
    dauer = (jetzt - datetime.fromisoformat(seit)).total_seconds() / 60
    return ("alle", "internet", "GELB",
            f"Datenquelle/Internet weg: {', '.join(weg)} nicht erreichbar seit "
            f"{datetime.fromisoformat(seit).astimezone(BERLIN):%d.%m. %H:%M} ({dauer:.0f} min)")


def netz_grund(zustand: dict, jetzt: datetime) -> str | None:
    """Warum kursabhaengige Dateien gerade still sein duerfen: Binance weg oder erst kurz zurueck. Sonst None."""
    if "Binance" in (zustand.get("netz_weg") or []):
        seit = zustand.get("netz_weg_seit") or jetzt.isoformat()
        return f"Binance nicht erreichbar seit {datetime.fromisoformat(seit).astimezone(BERLIN):%d.%m. %H:%M}"
    zurueck = zustand.get("netz_zurueck")
    if zurueck and (jetzt - datetime.fromisoformat(zurueck)).total_seconds() / 60 < NETZ_NACHLAUF_MIN:
        return f"Netz erst seit {datetime.fromisoformat(zurueck).astimezone(BERLIN):%H:%M} zurueck"
    return None


def netz_daempfen(erg: list[tuple], grund: str | None) -> list[tuple]:
    """ROT einer kursabhaengigen Datei -> GELB 'Datenquelle/Internet weg', solange das Netz der Grund sein kann."""
    if not grund:
        return erg
    return [(a, b, "GELB", f"Datenquelle/Internet weg ({grund}): {d} - Prozess laeuft, Datei wartet auf Kurse")
            if c == "ROT" and b in NETZ_ABHAENGIG else (a, b, c, d) for a, b, c, d in erg]


def wechsel(erg: list[tuple], alt: dict) -> tuple[list[tuple], list[tuple]]:
    """Ampel-Wechsel gegen den letzten Lauf. -> (ereignisse [(instanz, pruefung, vorher, nach, befund)],
    meldungen [(schluessel, text)]). Gemeldet wird ROT, jeder Neustart und ROT -> GRUEN ("wieder in Ordnung").
    [19.10.2026] "wieder in Ordnung" fuer system_log nur, wenn bot_state derselben Instanz auch GRUEN ist: Waehrend
    des v6-Haengers 16./17.10. kam diese Entwarnung mehrfach, obwohl der Bot weiter stand. Das Ereignis wird
    trotzdem in waechter.db eingetragen."""
    neu = {f"{a}|{b}": c for a, b, c, _ in erg}
    ereignisse, meldungen = [], []
    for (a, b, c, befund) in erg:
        key = f"{a}|{b}"
        vorher = alt.get(key, "GRUEN")
        if c != vorher or b == "neustart":
            ereignisse.append((a, b, vorher, c, befund))
            erholt = vorher == "ROT" and c == "GRUEN"
            if erholt and b == "system_log" and neu.get(f"{a}|bot_state") != "GRUEN":
                continue
            if c == "ROT" or (b == "neustart") or erholt:
                stufe = "HOCH" if c == "ROT" else "INFO"
                meldungen.append((f"W5-{key}-{c}", f"[WAECHTER][{stufe}] W5 {a} {b}: {befund}"
                                  + (" (wieder in Ordnung)" if erholt else "")))
    return ereignisse, meldungen


def rot_wiederholen(erg: list[tuple], zustand: dict, jetzt: datetime, sender=None) -> list[str]:
    """[19.10.2026] Erinnerung alle WIEDERHOLEN_MIN, solange bot_state/prozess einer Instanz ROT bleibt.
    Die erste Meldung kommt wie bisher ueber den Wechsel; hier zaehlt die Uhr ab Beginn des ROT. sender(text) -> bool;
    nur ein gesendeter Text setzt die Uhr neu (Netz weg -> naechster Lauf versucht es wieder). sender None (--zeigen):
    nur Beginn merken, nichts senden. Gibt die gesendeten Texte zurueck."""
    rm = zustand.setdefault("rot_meldung", {})
    aktiv, gesendet = set(), []
    for a, b, c, d in erg:
        if b not in WIEDERHOLEN or c != "ROT":
            continue
        key = f"{a}|{b}"
        aktiv.add(key)
        e = rm.get(key)
        if e is None:
            rm[key] = {"seit": jetzt.isoformat(), "zuletzt": jetzt.isoformat()}
            continue
        if sender is None or (jetzt - datetime.fromisoformat(e["zuletzt"])).total_seconds() / 60 < WIEDERHOLEN_MIN:
            continue
        seit = datetime.fromisoformat(e["seit"])
        text = (f"[WAECHTER][HOCH] W5 {a} {b} weiterhin ROT seit {seit.astimezone(BERLIN):%d.%m. %H:%M} "
                f"({(jetzt - seit).total_seconds() / 3600:.1f} h): {d}")
        if sender(text):
            e["zuletzt"] = jetzt.isoformat()
            gesendet.append(text)
    for key in [k for k in rm if k not in aktiv]:
        del rm[key]
    return gesendet


def speichern(ergebnis: list[tuple], jetzt: datetime) -> None:
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS betrieb (ts_utc TEXT, instanz TEXT, pruefung TEXT, ampel TEXT, befund TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS ereignisse (ts_utc TEXT, waechter TEXT, instanz TEXT, pruefung TEXT, "
                "von TEXT, nach TEXT, befund TEXT)")
    con.executemany("INSERT INTO betrieb VALUES (?,?,?,?,?)", [(jetzt.isoformat(), *e) for e in ergebnis])
    con.commit()
    con.close()


def lauf(senden: bool = True) -> list[tuple]:
    jetzt = datetime.now(timezone.utc)
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    zustand = json.loads(ZUSTAND.read_text(encoding="utf-8")) if ZUSTAND.exists() else {}
    netz = netz_pruefen(zustand, jetzt)                 # zuerst: entscheidet ueber "Datenquelle weg" bei den Dateien
    grund = netz_grund(zustand, jetzt)
    erg = []
    for name, i in inst.items():
        erg += netz_daempfen(pruefe_instanz(name, i, zustand), grund)
    erg += pruefe_gemeinsam()
    erg.append(netz)
    speichern(erg, jetzt)
    # Wechsel erkennen und melden
    ereignisse, meldungen = wechsel(erg, zustand.get("ampeln", {}))
    con = sqlite3.connect(DB, timeout=30)
    con.executemany("INSERT INTO ereignisse VALUES (?,?,?,?,?,?,?)", [(jetzt.isoformat(), "W5", *e) for e in ereignisse])
    con.commit()
    con.close()
    zustand["ampeln"] = {f"{a}|{b}": c for a, b, c, _ in erg}
    gesamt = max((STUFE[c] for _, _, c, _ in erg), default=0)
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {"_cleanup": "[CLEANUP-KEEP]"}
    status["W5"] = {"ampel": [k for k, v in STUFE.items() if v == gesamt][0], "stand_utc": jetzt.isoformat(),
                    "pruefungen": [{"instanz": a, "pruefung": b, "ampel": c, "befund": d} for a, b, c, d in erg]}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False), encoding="utf-8")
    if senden:
        for schluessel, text in meldungen:
            tm.sende(text, schluessel=schluessel)
        rot_wiederholen(erg, zustand, jetzt, sender=lambda t: tm.sende(t))   # [19.10.2026] ohne 6-h-Sperre, Takt hier
        heute = jetzt.astimezone(BERLIN)
        if heute.hour >= 8 and zustand.get("totmann_tag") != heute.date().isoformat():
            rot = [f"{a} {b}" for a, b, c, _ in erg if c == "ROT"]
            gelb = [f"{a} {b}" for a, b, c, _ in erg if c == "GELB"]
            if tm.sende(f"[WAECHTER][LEBENSZEICHEN] {heute:%d.%m. %H:%M} - W5 laeuft. Rot: {rot or 'nichts'}. "
                        f"Gelb: {gelb or 'nichts'}."):
                zustand["totmann_tag"] = heute.date().isoformat()
    else:
        rot_wiederholen(erg, zustand, jetzt)            # --zeigen: nur Beginn merken, nichts senden
    ZUSTAND.write_text(json.dumps(zustand, indent=1), encoding="utf-8")
    return erg


def _test_system_log() -> int:
    """[19.10.2026] Schritt 1: system_log nach Bot-Zeilen. Reproduktion = v6-Haenger 16./17.10. nachgespielt."""
    import tempfile
    from datetime import timedelta
    fehler = 0
    zeilen = HAENGER_AUSZUG.read_text(encoding="utf-8").splitlines()
    mit_zeit = [(datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc), z)
                for z in zeilen if (m := LOG_ZEILE.match(z))]

    def stand(t):                       # Dateiinhalt zum Zeitpunkt t: alle Zeilen, die bis t geschrieben waren
        return [z for ts, z in mit_zeit if ts <= t]

    def neu_ampel(t):
        b = letzte_bot_zeit(stand(t))
        return ampel(None if b is None else (t - b).total_seconds() / 60, 5, 10)

    def alt_ampel(t):                   # alte Regel: Datei-Alter = letzte Zeile irgendeines Prozesses
        return ampel((t - max(ts for ts, _ in mit_zeit if ts <= t)).total_seconds() / 60, 5, 10)

    # 1 Reproduktion: echte W5-Laufzeiten aus waechter.db (sonst 5-min-Raster), 16.10. 09:20 - 17.10. 20:00 UTC
    echt_gruen, laeufe = None, []
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        r = con.execute("SELECT ts_utc, ampel FROM betrieb WHERE instanz='v6' AND pruefung='system_log' "
                        "AND ts_utc BETWEEN '2026-10-16T09:20' AND '2026-10-17T20:01' ORDER BY ts_utc").fetchall()
        con.close()
        laeufe = [datetime.fromisoformat(ts) for ts, _ in r]
        echt_gruen = sum(a == "GRUEN" for _, a in r)
    except Exception:
        pass
    if not laeufe:
        t, laeufe = datetime(2026, 10, 16, 9, 20, 57, tzinfo=timezone.utc), []
        while t <= datetime(2026, 10, 17, 20, 0, 57, tzinfo=timezone.utc):
            laeufe.append(t); t += timedelta(minutes=5)
    neu = [neu_ampel(t) for t in laeufe]
    alt_gruen = sum(alt_ampel(t) == "GRUEN" for t in laeufe)
    ok = all(a == "ROT" for a in neu) and alt_gruen >= 15
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} system_log Reproduktion v6-Haenger ({len(laeufe)} W5-Laeufe 16.10. 09:20-17.10. 20:00): "
          f"neu {sum(a == 'ROT' for a in neu)}x ROT / {sum(a == 'GRUEN' for a in neu)}x GRUEN; alte Regel nachgespielt "
          f"{alt_gruen}x GRUEN" + ("" if echt_gruen is None else f", alte Regel echt (waechter.db) {echt_gruen}x GRUEN"))
    # 2 Normalfall: Bot schreibt -> GRUEN, auch wenn danach fremde Zeilen kommen; nach dem Neustart wieder GRUEN
    vor = neu_ampel(datetime(2026, 10, 16, 9, 8, 30, tzinfo=timezone.utc))
    nach = neu_ampel(datetime(2026, 10, 17, 20, 17, 30, tzinfo=timezone.utc))
    jetzt = datetime.now(timezone.utc)
    f = lambda t, k, txt: f"[{t:%Y-%m-%dT%H:%M:%S}] [INFO] [{k}] {txt}\n"   # noqa: E731
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "system.log"
        p.write_text(f(jetzt - timedelta(minutes=1), "MONITOR", "Checking 1 Position(en)")
                     + f(jetzt, "SIGNAL", "ARB/USDC: Score 3/10"), encoding="utf-8")
        a, txt = bot_log_alter(p, jetzt)
        datei = ampel(a, 5, 10)
    ok = vor == "GRUEN" and nach == "GRUEN" and datei == "GRUEN" and "vor 1 min" in txt
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} system_log Normalfall: 16.10. 09:08:30 {vor}, nach Neustart 20:17:30 {nach}, "
          f"Datei mit Bot-Zeile vor 1 min + fremder Zeile jetzt: {datei} ({txt})")
    # 3 Grenzfall: alte Bot-Zeile hinter 300 KB fremder Zeilen; Bot-Zeile nur in system.log.1; gar keine; Datei fehlt;
    #   kaputte Bytes; Schwellen 5/10 min
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "system.log"
        fremd = "".join(f(jetzt - timedelta(seconds=i), "SIGNAL", "X/USDC: Score 3/10 (30%) -> BUY 150.00$ " + "." * 60)
                        for i in range(2500, 0, -1))
        p.write_text(f(jetzt - timedelta(hours=35), "MONITOR", "Checking 3 Position(en)") + fremd, encoding="utf-8")
        a1, t1 = bot_log_alter(p, jetzt)
        p.write_text(fremd, encoding="utf-8")
        a3, t3 = bot_log_alter(p, jetzt)                       # ohne .1
        p.with_name("system.log.1").write_text(f(jetzt - timedelta(minutes=20), "LOOP", "3/3 Snapshots OK"), encoding="utf-8")
        a2, t2 = bot_log_alter(p, jetzt)
        p.write_bytes(b"\xff\xfe kaputt\n" + f(jetzt, "HEART", "Uptime").encode("utf-8"))
        a5, _ = bot_log_alter(p, jetzt)
        a4, t4 = bot_log_alter(Path(tmp) / "fehlt.log", jetzt)
    schwellen = (ampel(4.9, 5, 10), ampel(5.5, 5, 10), ampel(10.5, 5, 10))
    ok = (len(fremd) > 256 * 1024 and ampel(a1, 5, 10) == "ROT" and abs(a1 - 2100) < 1
          and ampel(a2, 5, 10) == "ROT" and abs(a2 - 20) < 1 and "system.log.1" in t2
          and a3 is None and "keine Bot-Zeile" in t3 and a4 is None and t4 == "fehlt"
          and a5 is not None and a5 < 1 and schwellen == ("GRUEN", "GELB", "ROT"))
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} system_log Grenzfall: Bot-Zeile hinter {len(fremd) // 1024} KB fremder Zeilen -> "
          f"{ampel(a1, 5, 10)} ({t1}); nur in .1 -> {ampel(a2, 5, 10)} ({t2}); keine -> {ampel(a3, 5, 10)}; "
          f"fehlt -> {t4}; kaputte Bytes ok; 4,9/5,5/10,5 min -> {'/'.join(schwellen)}")
    return fehler


def _test_rot_wiederholen() -> int:
    """[19.10.2026] Schritt 2: Erinnerung alle 2 h, solange bot_state/prozess ROT bleibt."""
    from datetime import timedelta
    fehler = 0
    t0 = datetime(2026, 10, 16, 9, 20, 57, tzinfo=timezone.utc)      # v6 bot_state ROT ab hier (waechter.db)

    def spiel(ampeln, sender_ok=lambda i: True, pruefung="bot_state", z=None):
        """ampeln: Liste je W5-Lauf (5 min Takt). -> (gesendete Laufnummern, Texte, Zustand)"""
        z = {} if z is None else z
        nr, texte = [], []
        for i, c in enumerate(ampeln):
            g = rot_wiederholen([("v6", pruefung, c, "zuletzt vor X min")], z, t0 + timedelta(minutes=5 * i),
                                sender=lambda t, i=i: sender_ok(i))
            nr += [i] * len(g); texte += g
        return nr, texte, z
    # 1 Reproduktion: 35 h ROT (16.10. 09:20:57 - 17.10. 20:00:57 = 417 Laeufe). Vorher: nur die Wechselmeldung.
    nr, texte, _ = spiel(["ROT"] * 417)
    abst = {(b - a) * 5 for a, b in zip(nr, nr[1:])}
    ok = len(nr) == 17 and nr[0] == 24 and abst == {120} and "seit 16.10. 11:20" in texte[0] and "(2.0 h)" in texte[0]
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} ROT-Wiederholung Reproduktion 35 h v6 bot_state: {len(nr)} Erinnerungen "
          f"(vorher 0), Abstand {sorted(abst)} min, erste: {texte[0][:80] if texte else '-'}")
    # 2 Normalfall: 60 min ROT, dann GRUEN -> keine Erinnerung, Eintrag geloescht; ROT bei telemetrie -> keine
    nr1, _, z1 = spiel(["ROT"] * 12 + ["GRUEN"] * 3)
    nr2, _, z2 = spiel(["ROT"] * 40, pruefung="telemetrie")
    ok = nr1 == [] and z1["rot_meldung"] == {} and nr2 == [] and z2["rot_meldung"] == {}
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} ROT-Wiederholung Normalfall: 60 min ROT dann GRUEN -> {len(nr1)} Erinnerungen, "
          f"Eintrag weg; telemetrie 200 min ROT -> {len(nr2)} (nur bot_state/prozess)")
    # 3 Grenzfall: Senden scheitert bei 2 h -> naechster Lauf; ROT-GRUEN-ROT -> Uhr neu; --zeigen (sender None);
    #   prozess GELB (bewusst aus) -> nichts
    nr3, _, _ = spiel(["ROT"] * 60, sender_ok=lambda i: i != 24)                       # Lauf 24 = 2 h: Netz weg
    nr4, t4, _ = spiel(["ROT"] * 20 + ["GRUEN"] + ["ROT"] * 30)                        # neuer Beginn bei Lauf 21
    z5 = {}
    for i in range(30):
        rot_wiederholen([("v6", "bot_state", "ROT", "x")], z5, t0 + timedelta(minutes=5 * i))   # ohne sender
    nr6, _, _ = spiel(["GELB"] * 40, pruefung="prozess")
    ok = (nr3 == [25, 49] and nr4 == [45] and "seit 16.10. 13:05" in t4[0]
          and z5["rot_meldung"]["v6|bot_state"]["zuletzt"] == t0.isoformat() and nr6 == [])
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} ROT-Wiederholung Grenzfall: Senden scheitert bei 2 h -> Laeufe {nr3} "
          f"(2:05 h, 4:05 h); ROT-GRUEN-ROT -> {nr4} (2 h nach neuem Beginn); --zeigen sendet nichts; prozess GELB -> {nr6}")
    return fehler


def _test_entwarnung() -> int:
    """[19.10.2026] Schritt 3: "wieder in Ordnung" fuer system_log nur mit bot_state GRUEN."""
    fehler = 0
    entw = lambda m: [t for _, t in m if "system_log" in t and "wieder in Ordnung" in t]   # noqa: E731
    # 1 Reproduktion: echte v6-Laeufe aus waechter.db im Haengerfenster (alte system_log-Werte, also mit falschem GRUEN)
    laeufe = {}
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        for ts, b, c, d in con.execute("SELECT ts_utc, pruefung, ampel, befund FROM betrieb WHERE instanz='v6' "
                                       "AND ts_utc BETWEEN '2026-10-16T09:00' AND '2026-10-17T20:01' ORDER BY ts_utc"):
            laeufe.setdefault(ts, []).append(("v6", b, c, d))
        con.close()
    except Exception:
        pass
    alt, neu_n, alt_n = {}, 0, 0
    for ts in sorted(laeufe):
        e, m = wechsel(laeufe[ts], alt)
        alt_n += sum(1 for x in e if x[1] == "system_log" and x[2] == "ROT" and x[3] == "GRUEN")   # alte Regel: jede meldet
        neu_n += len(entw(m))
        alt = {f"{a}|{b}": c for a, b, c, _ in laeufe[ts]}
    ok = len(laeufe) > 400 and alt_n >= 20 and neu_n == 0
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Entwarnung Reproduktion v6-Haenger ({len(laeufe)} echte W5-Laeufe): "
          f"system_log 'wieder in Ordnung' alte Regel {alt_n}x, neu {neu_n}x (bot_state war ROT)")
    # 2 Normalfall: beide erholen sich gemeinsam -> beide Entwarnungen; neues ROT und Neustart werden weiter gemeldet
    _, m1 = wechsel([("v6", "bot_state", "GRUEN", "a"), ("v6", "system_log", "GRUEN", "b")],
                    {"v6|bot_state": "ROT", "v6|system_log": "ROT"})
    _, m2 = wechsel([("v6", "bot_state", "ROT", "a"), ("v6", "system_log", "ROT", "b"), ("v6", "neustart", "GELB", "c")], {})
    ok = len(m1) == 2 and len(entw(m1)) == 1 and len(m2) == 3
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Entwarnung Normalfall: beide wieder GRUEN -> {len(m1)} Meldungen; "
          f"ROT/ROT/Neustart -> {len(m2)} Meldungen (wie bisher)")
    # 3 Grenzfall: bot_state GELB; bot_state fehlt; andere Instanz GRUEN zaehlt nicht; telemetrie-Erholung bleibt
    e3, m3 = wechsel([("v6", "bot_state", "GELB", "a"), ("v6", "system_log", "GRUEN", "b")], {"v6|system_log": "ROT"})
    _, m4 = wechsel([("v6", "system_log", "GRUEN", "b")], {"v6|system_log": "ROT"})
    _, m5 = wechsel([("v7", "bot_state", "GRUEN", "a"), ("v6", "bot_state", "ROT", "a"), ("v6", "system_log", "GRUEN", "b")],
                    {"v6|system_log": "ROT", "v6|bot_state": "ROT"})
    _, m6 = wechsel([("v6", "bot_state", "ROT", "a"), ("v6", "telemetrie", "GRUEN", "t")],
                    {"v6|bot_state": "ROT", "v6|telemetrie": "ROT"})
    ok = (entw(m3) == [] and len(e3) == 2 and entw(m4) == [] and entw(m5) == []
          and any("telemetrie" in t and "wieder in Ordnung" in t for _, t in m6))
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Entwarnung Grenzfall: bot_state GELB -> keine (Ereignis trotzdem in db); "
          f"bot_state fehlt -> keine; v7 GRUEN zaehlt nicht fuer v6; telemetrie-Erholung wird weiter gemeldet")
    return fehler


def selbsttest() -> int:
    import tempfile
    fehler = 0
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "x.db"
        ok = ampel(alter_min(p), 5, 10) == "ROT"
        fehler += not ok; print(f"  {'OK  ' if ok else 'FEHL'} fehlende Datei -> ROT")
        p.write_text("x")
        ok = ampel(alter_min(p), 5, 10) == "GRUEN"
        fehler += not ok; print(f"  {'OK  ' if ok else 'FEHL'} frische Datei -> GRUEN")
        import os
        alt = time.time() - 3600
        os.utime(p, (alt, alt))
        ok = ampel(alter_min(p), 5, 10) == "ROT" and ampel(alter_min(p), 30, 120) == "GELB"
        fehler += not ok; print(f"  {'OK  ' if ok else 'FEHL'} 60 min alt -> ROT bei 10 min, GELB bei 30/120 min")
        os.utime(p, (time.time(), time.time()))
        (Path(t) / "x.db-wal").write_text("w")
        os.utime(p, (alt, alt))
        ok = ampel(alter_min(p), 5, 10) == "GRUEN"
        fehler += not ok; print(f"  {'OK  ' if ok else 'FEHL'} alte .db, aber frische -wal -> GRUEN (WAL zaehlt)")
    # Netzausfall [15.10.2026]: Nacht 14./15.10., v7 telemetrie 303 min still, Netz weg seit 23:47 UTC
    from datetime import timedelta
    t0 = datetime(2026, 10, 14, 23, 47, tzinfo=timezone.utc)
    jetzt = t0 + timedelta(minutes=303)
    befunde = [("v7", "prozess", "GRUEN", "PID 6928"), ("v7", "bot_state", "GRUEN", "zuletzt vor 0 min"),
               ("v7", "telemetrie", "ROT", "zuletzt vor 303 min")]
    z = {"netz_weg_seit": t0.isoformat()}
    netz = netz_pruefen(z, jetzt, weg=["Binance", "Bitvavo"])
    e = {b: (c, d) for _, b, c, d in netz_daempfen(befunde, netz_grund(z, jetzt))}
    ok = (netz[2] == "GELB" and "Datenquelle/Internet weg" in netz[3] and e["telemetrie"][0] == "GELB"
          and "Datenquelle/Internet weg" in e["telemetrie"][1] and e["prozess"][0] == "GRUEN")
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion Nacht (frueher ROT/ROT): internet {netz[2]}, telemetrie {e['telemetrie'][0]}")
    # Normalfall: Netz da -> stille Telemetrie bleibt ROT (Bot haengt); Netz weg, aber bot_state still -> bleibt ROT
    z = {}
    netz = netz_pruefen(z, jetzt, weg=[])
    e1 = netz_daempfen(befunde, netz_grund(z, jetzt))
    z2 = {"netz_weg_seit": t0.isoformat()}
    netz_pruefen(z2, jetzt, weg=["Binance", "Bitvavo"])
    e2 = netz_daempfen([("v7", "bot_state", "ROT", "zuletzt vor 40 min")], netz_grund(z2, jetzt))
    ok = netz[2] == "GRUEN" and e1[2][2] == "ROT" and e2[0][2] == "ROT"
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: Netz da -> telemetrie {e1[2][2]}; Netz weg, bot_state still -> {e2[0][2]}")
    # Grenzfall: Netz vor 10 min zurueck -> noch GELB, nach 31 min ROT; nur Bitvavo weg -> nicht daempfen
    z = {"netz_weg_seit": t0.isoformat()}
    netz_pruefen(z, jetzt, weg=[])
    g10 = netz_daempfen(befunde, netz_grund(z, jetzt + timedelta(minutes=10)))[2][2]
    g31 = netz_daempfen(befunde, netz_grund(z, jetzt + timedelta(minutes=31)))[2][2]
    z3 = {}
    n3 = netz_pruefen(z3, jetzt, weg=["Bitvavo"])
    b3 = netz_daempfen(befunde, netz_grund(z3, jetzt))[2][2]
    ok = g10 == "GELB" and g31 == "ROT" and n3[2] == "GELB" and b3 == "ROT"
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: 10 min nach Rueckkehr {g10}, nach 31 min {g31}; "
          f"nur Bitvavo weg: internet {n3[2]}, telemetrie {b3}")
    fehler += _test_system_log()
    fehler += _test_rot_wiederholen()
    fehler += _test_entwarnung()
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return fehler


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    e = lauf(senden="--zeigen" not in sys.argv)
    if "--zeigen" in sys.argv or sys.stdout:
        for a, b, c, d in e:
            print(f"{c:5s} {a:4s} {b:16s} {d}")
