# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Bot sauber anhalten - fuer Patches (Regel 9.3: Bot muss vollstaendig geschlossen sein).

WARUM NICHT DER STOPPEN-KNOPF: Befund 72 (BOT-HANDBUCH 7.4) - der Knopf stuerzt
ab, bevor der Positionsstand gespeichert wird. Der Bot speichert aber selbst
alle 30 s (bot_state.json). Sicher ist deshalb: auf eine frische Speicherung
warten, dann den Prozess beenden, dann pruefen, dass sich nichts mehr geaendert hat.
So am 03.09. und 14.10.2026 gemacht, beide Male Zustand vollstaendig.

Ablauf:
  1. autostart/<instanz>.BEWUSST_AUS mit Grund anlegen (Autostart laesst ihn in Ruhe)
  2. auf die naechste Speicherung von bot_state.json warten (max. 90 s)
  3. app.py, seine Kindprozesse und das start_bot.bat-Fenster beenden
  4. 5 s spaeter: bot_state.json unveraendert? Positionen und USDC ausgeben
  5. STOPP-Zeile in autostart/start_stopp.log (Start-/Stopp-Protokoll)

Aufruf:  python bot_anhalten.py v6 "Grund in einem Satz"
Wieder an: python bots_starten.py  (nachdem die .BEWUSST_AUS-Datei geloescht ist)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bots_starten import HIER, PRUEFSTAND, laufende_bots, port_offen, schreibe  # noqa: E402

PROTOKOLL = HIER / "start_stopp.log"


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def zustand(p: Path) -> str:
    s = json.loads(p.read_text(encoding="utf-8"))
    pos = s.get("open_positions_backup") or {}
    usdc = (s.get("paper_balances_backup") or {}).get("USDC", 0)
    teile = [f"{k} {float(v.get('qty', 0)):.6f}" for k, v in pos.items()] if isinstance(pos, dict) else [str(pos)]
    return f"{len(teile)} Positionen ({', '.join(teile) or '-'}), USDC {float(usdc):.2f}"


def anhalten(name: str, grund: str) -> int:
    inst = json.loads((PRUEFSTAND / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]
    ordner = Path(inst["pfad"])
    state = ordner / "data_store" / "bot_state.json"
    (HIER / f"{name}.BEWUSST_AUS").write_text(f"{time.strftime('%d.%m.%Y %H:%M')} {grund}", encoding="utf-8")
    pids = laufende_bots(ordner)
    if not pids:
        print(f"{name}: laeuft nicht. Sperre gesetzt. Zustand: {zustand(state)}")
        schreibe(f"{name}: STOPP (lief nicht) - {grund}", PROTOKOLL)
        return 0
    port = inst.get("dashboard_port")
    if port and not port_offen(port):
        # Fenster offen, aber STARTEN nie gedrueckt: engine.start() lief nicht,
        # es wird nichts gespeichert und nichts gehandelt (14.10.2026 gesehen).
        print(f"{name}: Port {port} zu - Bot nur im Wartezustand, keine Speicherung abzuwarten.")
    else:
        alt = state.stat().st_mtime
        ende = time.time() + 90
        while state.stat().st_mtime == alt and time.time() < ende:
            time.sleep(1)
        if state.stat().st_mtime == alt:
            print(f"{name}: ABBRUCH - in 90 s keine Speicherung. Bot NICHT beendet, Sperre bleibt.")
            return 1
        time.sleep(2)                   # Schreibvorgang sicher abgeschlossen
    vorher = _hash(state)
    opfer = []
    for pid in pids:
        p = psutil.Process(pid)
        opfer += p.children(recursive=True)
        opfer.append(p)
        eltern = p.parent()
        if eltern and eltern.name().lower() == "cmd.exe" and "start_bot.bat" in " ".join(eltern.cmdline()):
            opfer.append(eltern)
    for p in opfer:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(opfer, timeout=10)
    time.sleep(5)
    gleich = _hash(state) == vorher
    meldung = (f"{name}: STOPP - {grund} | PIDs {pids} + {len(opfer) - len(pids)} weitere | "
               f"Zustand nach Stopp {'unveraendert' if gleich else 'VERAENDERT'} | {zustand(state)} | "
               f"Port {port} {'noch offen!' if port and port_offen(port) else 'zu'}")
    print(meldung)
    schreibe(meldung, PROTOKOLL)
    return 0 if gleich and not laufende_bots(ordner) else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    sys.exit(anhalten(sys.argv[1], " ".join(sys.argv[2:])))
