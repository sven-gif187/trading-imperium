# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH Sammler-Start nur fuer den EIGENEN Ordner (v6 und v7) - Befund W5 14.10.2026.

BEFUND: v7 hat seit 02.10.2026 keinen Positionsverlauf geschrieben (W5: positionsverlauf.db
17.387 min alt bei offener Position). Ursache sammler_pruefen.py starten():
    if skript.lower() in prozesse and skript not in trotzdem:
prozesse = Befehlszeilen ALLER Python-Prozesse. Laeuft positionsverlauf.py aus dem v6-Ordner,
haelt v7 seinen eigenen fuer "laeuft schon" und startet ihn nie. Dieselbe Fehlerklasse wie der
tote v6-Nachlauf 27.09.-14.10. (dort am 14.10. in schatten_starter.py behoben). Der Tagescheck
meldete es ("laeuft aus FREMDEM Ordner"), aber nur einmal am Tag und ohne Folge.

FIX: Ein Sammler gilt nur als laufend, wenn ein Python-Prozess ihn aus GENAU diesem Ordner faehrt
(Skriptpfad oder Arbeitsordner = HIER). Nur Datensammeln, keine Handelsregel -> keine Epoche
(CLAUDE.md 5: Aenderungen, die ausschliesslich aufschreiben).
Aufruf: python patch_sammler_eigener_ordner.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "SAMMLER EIGENER ORDNER 14.10.2026"
ALT1 = "        if skript.lower() in prozesse and skript not in trotzdem:\n"
NEU1 = (f"        # [{MARKE}] Vorher: skript.lower() in prozesse - zaehlte auch Sammler aus\n"
        "        # FREMDEN Ordnern (v6 hielt v7 seit 02.10. vom Positionsverlauf ab).\n"
        "        if _laeuft_hier(skript) and skript not in trotzdem:\n")
ALT2 = "def starten(melden=None, trotzdem=()):\n"
NEU2 = (
    "def _laeuft_hier(skript):\n"
    f"    \"\"\"[{MARKE}] Laeuft `skript` aus GENAU diesem Ordner (HIER)?\n"
    "\n"
    "    Massgeblich ist der Pfad des Skripts in der Befehlszeile, ersatzweise der\n"
    "    Arbeitsordner des Prozesses. Ein gleichnamiger Sammler aus einem anderen\n"
    "    Bot-Ordner zaehlt NICHT.\n"
    "    \"\"\"\n"
    "    import psutil\n"
    "    hier = os.path.normcase(os.path.abspath(HIER))\n"
    "    for p in psutil.process_iter([\"pid\", \"name\", \"cmdline\"]):\n"
    "        try:\n"
    "            if \"python\" not in (p.info[\"name\"] or \"\").lower():\n"
    "                continue\n"
    "            teile = [str(x) for x in (p.info[\"cmdline\"] or [])]\n"
    "            treffer = [t for t in teile if t.lower().endswith(skript.lower())]\n"
    "            if not treffer:\n"
    "                continue\n"
    "            ordner = os.path.dirname(os.path.abspath(treffer[0]))\n"
    "            if not os.path.isabs(treffer[0]) or os.path.dirname(treffer[0]) == \"\":\n"
    "                ordner = p.cwd()\n"
    "            if os.path.normcase(os.path.abspath(ordner)) == hier:\n"
    "                return True\n"
    "        except Exception:\n"
    "            continue\n"
    "    return False\n"
    "\n"
    "\n"
    "def starten(melden=None, trotzdem=()):\n"
)


def probe() -> int:
    """Gegenprobe am echten System: v6-Positionsverlauf laeuft -> fuer v6 True, fuer v7 False."""
    import importlib.util
    import os
    import shutil
    import tempfile
    from _patchwerkzeug import anwenden
    fehler = 0
    inst = json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    for name in ("v6", "v7"):
        with tempfile.TemporaryDirectory() as t:
            k = Path(t)
            shutil.copy2(Path(inst[name]["pfad"]) / "sammler_pruefen.py", k / "sammler_pruefen.py")
            anwenden(k, [Ersetzung("sammler_pruefen.py", ALT1, NEU1), Ersetzung("sammler_pruefen.py", ALT2, NEU2)],
                     MARKE, trocken_kopie=True)
            spec = importlib.util.spec_from_file_location("sp_" + name, k / "sammler_pruefen.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.HIER = inst[name]["pfad"]                      # so tun, als laege die Kopie im Bot-Ordner
            r = mod._laeuft_hier("positionsverlauf.py")
            print(f"  {name}: _laeuft_hier('positionsverlauf.py') = {r}")
    # Erwartung zum Zeitpunkt der Probe (14.10. 21:50): nur v6 faehrt positionsverlauf.py
    return fehler


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    inst = json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]
    main(Path(inst["pfad"]), [Ersetzung("sammler_pruefen.py", ALT1, NEU1), Ersetzung("sammler_pruefen.py", ALT2, NEU2)],
         MARKE, f"PATCH Sammler eigener Ordner {name}", zusatztest=probe)
