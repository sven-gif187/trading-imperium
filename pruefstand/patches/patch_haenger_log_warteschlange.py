# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH HAENGER - Logger-Rueckruf ueber eine Warteschlange statt self.after() aus fremden Threads.
v6 und v7 (gleiche Stelle). VORBEREITET, NICHT EINGESPIELT.
Bericht: pruefstand/berichte/2026-10-17_v6_haenger.md

Fehler: v6 stand vom 16.10.2026 09:08:24 UTC bis 17.10. 20:05 UTC still (35 h, Prozess lief).
Ursache: ui/main_window.py meldet beim Logger einen Rueckruf an, der aus JEDEM Thread
self.after(0, ...) aufruft. tkinter laesst diesen Thread warten, bis der Fenster-Thread den Aufruf
abarbeitet, und core/logger.py ruft die Rueckrufe VOR dem Schreiben in system.log. Steht der
Fenster-Thread, steht jeder Thread, der loggt: Handelsablauf, Stopp-Ueberwachung, Kontostand, Puls.
Der Fenster-Thread selbst nimmt im TERMINAL-Tab alle 2 s die Journal-Sperre (journal.get_all()),
und TradeJournal._save() loggt bei einem Speicherfehler, WAEHREND es diese Sperre haelt -> beide
warten aufeinander (Verklemmung). Nachgestellt im Zusatztest (Fall "alt").

Die eine Aenderung je Bot: ui/main_window.py, Block "Logger-Callback fuer Live-Updates".
Der Rueckruf reiht die Zeile nur noch ein (put_nowait, kehrt sofort zurueck); der Fenster-Thread
holt sie alle 250 ms selbst ab. Haengt das Fenster, haengt nur noch das Fenster - Handel, Stopps,
auto_save und system.log laufen weiter. Bei vollem Puffer (2000 Zeilen) verliert nur die ANZEIGE
Zeilen, system.log verliert keine (der Logger schreibt die Datei nach den Rueckrufen ohnehin selbst).
Keine Handelsregel betroffen.

Zeilenenden (byte-genau geprueft 17.10.): v6 ui/main_window.py CRLF, v7 LF - das Werkzeug haelt sie je Datei.
Bot vor --anwenden VOLLSTAENDIG schliessen (autostart/bot_anhalten.py), sonst bricht das Werkzeug ab.

Aufruf: python patch_haenger_log_warteschlange.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

MARKE = "HAENGER LOG-WARTESCHLANGE"

ALT_BLOCK = (
    "        # Logger-Callback für Live-Updates\n"
    "        from core.logger import log\n"
    "        log.add_callback(lambda entry: self.after(0, lambda e=entry: self._add_log(\n"
    "            f\"[{e['module']}] {e['msg']}\")))\n")

NEU_BLOCK = (
    "        # Logger-Callback für Live-Updates\n"
    f"        # [{MARKE} 17.10.2026] Vorher rief jeder log.*()-Aufruf - aus JEDEM\n"
    "        # Thread - self.after() auf. tkinter laesst den Thread dabei warten, bis der\n"
    "        # Fenster-Thread den Aufruf abarbeitet, und core/logger.py ruft die Rueckrufe\n"
    "        # VOR dem Schreiben in system.log. Am 16.10.2026 ab 09:08 UTC stand der\n"
    "        # Fenster-Thread, und mit ihm standen Handelsablauf, Stopp-Ueberwachung und\n"
    "        # auto_save 35 h lang (pruefstand/berichte/2026-10-17_v6_haenger.md).\n"
    "        # Jetzt reiht der Rueckruf die Zeile nur ein und kehrt sofort zurueck; der\n"
    "        # Fenster-Thread holt sie alle 250 ms selbst ab. Haengt das Fenster, haengt\n"
    "        # nur noch das Fenster. Voller Puffer: nur die ANZEIGE verliert Zeilen.\n"
    "        import queue as _log_q\n"
    "        from core.logger import log\n"
    "        self._log_warteschlange = _log_q.Queue(maxsize=2000)\n"
    "\n"
    "        def _log_einreihen(entry):\n"
    "            try:\n"
    "                self._log_warteschlange.put_nowait(entry)\n"
    "            except _log_q.Full:\n"
    "                pass\n"
    "\n"
    "        def _log_abholen():\n"
    "            try:\n"
    "                for _ in range(200):\n"
    "                    e = self._log_warteschlange.get_nowait()\n"
    "                    self._add_log(f\"[{e['module']}] {e['msg']}\")\n"
    "            except _log_q.Empty:\n"
    "                pass\n"
    "            except Exception:\n"
    "                pass\n"
    "            try:\n"
    "                self.after(250, _log_abholen)\n"
    "            except Exception:\n"
    "                pass\n"
    "\n"
    "        log.add_callback(_log_einreihen)\n"
    "        self.after(250, _log_abholen)\n")


# ----------------------------------------------------------------------------
# Verhaltenstest: fuehrt den ALTEN bzw. NEUEN Block in einem Kind-Prozess aus.
# Der Logger ist eine Nachbildung von core/logger.py._emit (Rueckrufe VOR der
# Datei); der echte Bot-Logger wird NICHT importiert (er wuerde ins echte
# system.log schreiben). Eine Verklemmung zeigt sich als Zeitueberschreitung.
# ----------------------------------------------------------------------------
KIND = r'''
import sys, threading, time, types, json, tkinter as tk
block, fall, logdatei = open(sys.argv[1], encoding="utf-8").read(), sys.argv[2], sys.argv[3]

class Logger:                                   # = core/logger.py, Reihenfolge wie dort
    def __init__(self): self._lock = threading.Lock(); self._callbacks = []
    def add_callback(self, cb): self._callbacks.append(cb)
    def _emit(self, modul, msg):
        entry = {"module": modul, "msg": msg}
        for cb in self._callbacks:              # 1. Rueckrufe (hier haengt der alte Block)
            try: cb(entry)
            except Exception: pass
        with self._lock:                        # 2. erst dann die Datei
            with open(logdatei, "a", encoding="utf-8") as f: f.write(f"[{modul}] {msg}\n")
    def info(self, m, s): self._emit(m, s)
    def error(self, m, s): self._emit(m, s)
log = Logger()
core = types.ModuleType("core"); core.logger = types.ModuleType("core.logger"); core.logger.log = log
sys.modules["core"], sys.modules["core.logger"] = core, core.logger

class Fenster(tk.Tk):
    def __init__(self): super().__init__(); self.withdraw(); self.angezeigt = []
    def _add_log(self, msg): self.angezeigt.append(msg)
fenster = Fenster()
exec(block, {"self": fenster, "__builtins__": __builtins__})   # der Block aus main_window.py
sperre, dauer = threading.Lock(), []

if fall == "verklemmung":
    def speichern():                            # = TradeJournal.save -> _save -> _melde_fehler
        time.sleep(0.5)
        with sperre:
            time.sleep(0.3)                     # os.replace-Wiederholungen
            log.error("JOURNAL", "Trade-Journal NICHT gespeichert")
        log.info("STATE", "auto_save fertig")
    def refresh():                              # = terminal_tab._refresh -> journal.get_all()
        with sperre: pass
        fenster.after(100, refresh)
    threading.Thread(target=speichern, daemon=True).start()
    fenster.after(100, refresh)
    fenster.after(3000, fenster.quit)
else:                                           # "fenster_blockiert": Fenster 2 s weg, 2500 Zeilen
    def netz(): time.sleep(2.0)                 # = Kerzenabruf im Fenster-Thread mit Zeitgrenze
    def flut():
        time.sleep(0.2)
        for i in range(2500):
            t = time.monotonic(); log.info("MONITOR", f"Zeile {i}"); dauer.append(time.monotonic() - t)
    fenster.after(100, netz)
    threading.Thread(target=flut, daemon=True).start()
    fenster.after(4000, fenster.quit)
fenster.mainloop()
zeilen = open(logdatei, encoding="utf-8").read().splitlines()
print(json.dumps({"datei": len(zeilen), "journal": any("JOURNAL" in z for z in zeilen),
                  "angezeigt": len(fenster.angezeigt), "max_dauer": max(dauer) if dauer else 0}))
'''


def _kind(block: str, fall: str) -> dict | None:
    """None = Zeitueberschreitung (Verklemmung)."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "block.py").write_text(textwrap.dedent(block), encoding="utf-8")
        (t / "kind.py").write_text(KIND, encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", str(t / "kind.py"), str(t / "block.py"), fall,
                                str(t / "system.log")], capture_output=True, text=True, timeout=12)
        except subprocess.TimeoutExpired:
            return None
        if r.returncode != 0:
            return {"fehler": (r.stderr or r.stdout)[-300:]}
        return json.loads(r.stdout.strip().splitlines()[-1])


def verhaltenstest(name: str, ordner: Path) -> int:
    fehler = 0
    t = (ordner / "ui/main_window.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
    if NEU_BLOCK in t:
        print("  Verhaltenstest: Bot ist schon gepatcht - nur Fall 2 und 3.")
    elif ALT_BLOCK not in t:
        print("  FEHL Verhaltenstest: Anker nicht im Bot gefunden"); return 1
    print(f"  Verhaltenstest {name} (Kind-Prozesse, Fenster unsichtbar, je max. 12 s):")
    if ALT_BLOCK in t:
        r = _kind(ALT_BLOCK, "verklemmung")
        ok = r is None
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} 1 Reproduktion ALT: Speicher-Thread loggt unter der Journal-Sperre, "
              f"Fenster-Thread will die Sperre -> {'VERKLEMMT wie am 16.10.' if ok else f'nicht verklemmt ({r})'}")
    r = _kind(NEU_BLOCK, "verklemmung")
    ok = bool(r) and "fehler" not in r and r["journal"] and r["datei"] == 2 and r["angezeigt"] == 2
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} 2 Normalfall NEU, gleicher Ablauf: "
          f"{'kein Haenger, JOURNAL-Zeile in der Datei, 2/2 Zeilen im Fenster' if ok else r}")
    r = _kind(NEU_BLOCK, "fenster_blockiert")
    ok = (bool(r) and "fehler" not in r and r["datei"] == 2500 and 0 < r["angezeigt"] <= 2000
          and r["max_dauer"] < 0.25)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} 3 Grenzfall NEU, Fenster 2 s blockiert, 2500 Zeilen: "
          + (f"Datei {r['datei']}, Fenster {r['angezeigt']} (Puffer 2000), "
             f"laengster Log-Aufruf {r['max_dauer'] * 1000:.0f} ms" if r and "fehler" not in r else str(r)))
    return 1 if fehler else 0


ERS = None  # wird in __main__ gesetzt (Werkzeug-Import erst dort, damit --help ohne psutil geht)

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    from _patchwerkzeug import Ersetzung, main  # noqa: E402
    name = sys.argv.pop(1)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    ERS = [Ersetzung("ui/main_window.py", ALT_BLOCK, NEU_BLOCK)]
    main(pfad, ERS, MARKE, f"PATCH HAENGER Log-Warteschlange {name}",
         zusatztest=lambda: verhaltenstest(name, pfad))
