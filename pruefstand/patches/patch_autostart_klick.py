# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH Autostart-Klick (v6 und v7) - das Cockpit-Fenster drueckt STARTEN selbst,
wenn der Bot ueber den Autostart des Pruefstands gestartet wurde.

BEFUND 14.10.2026: Im Fenster-Modus startet app.py nur das Cockpit. Gehandelt
wird erst nach Klick auf "STARTEN" (ui/main_window.py, _toggle_bot ->
threading.Thread(target=self.engine.start)). Der Autostart nach Windows-Update
(pruefstand/autostart/bots_starten.py) haette also nur ein Fenster geoeffnet -
v6 stand am 14.10. von 11:36 bis zur Korrektur mit 3 offenen Positionen ohne
Ueberwachung, Fenster offen, "reagiert".

AENDERUNG (eine): am Ende von MainWindow.__init__, nach self._start_updater():
    if os.environ.get("TI_AUTOSTART") == "1" and not self.is_running:
        self.after(5000, self._toggle_bot)
bots_starten.py setzt TI_AUTOSTART=1 nur fuer den Bot, den es startet.
Doppelklick auf start_bot.bat: Variable fehlt -> alles wie bisher.

KEINE Handelsregel, keine Epoche: Es wird nur der Klick automatisiert.

Aufruf:  python patch_autostart_klick.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "AUTOSTART-KLICK 14.10.2026"
ALT = "        # Periodisches Update\n        self._start_updater()\n"
NEU = (
    "        # Periodisches Update\n"
    "        self._start_updater()\n"
    "\n"
    "        # [" + MARKE + ", Pruefstand] Startet der Bot ueber\n"
    "        # pruefstand/autostart/bots_starten.py (setzt TI_AUTOSTART=1), drueckt\n"
    "        # das Fenster nach dem Aufbau selbst STARTEN. Ohne die Variable\n"
    "        # (Doppelklick auf start_bot.bat) bleibt alles wie bisher.\n"
    "        # Anlass: Windows-Update-Neustart 14.10.2026 - der Autostart oeffnete\n"
    "        # nur das Fenster, gehandelt und ueberwacht wurde nichts.\n"
    "        if os.environ.get(\"TI_AUTOSTART\") == \"1\" and not self.is_running:\n"
    "            self.after(5000, self._toggle_bot)\n"
)

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    inst = json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]
    main(Path(inst["pfad"]), [Ersetzung("ui/main_window.py", ALT, NEU)], MARKE,
         f"PATCH Autostart-Klick {name}")
