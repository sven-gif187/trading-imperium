# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH E13 / L12 - Nachzieh-Marge 0,10 und Kleinigkeiten. v6 E13, v7 L12.
Entscheidung Sven 15.10.2026: E5b ("ja, auch 0,10"), "mach weiter mit den Kleinigkeiten" (F8).

v6 und v7:
  1 (verhaltensaendernd) risk/exit_rules.py TRAIL_MARGE_PCT 0,05 -> 0,10. Nachzieh-Start = Nulllinie + 0,10
    (0,85 -> 1,11 | 1,0 -> 1,26 | 1,3 -> 1,57). Gleiche Begruendung wie der Puffer (E12): Ausloeseverzug Ø 0,072 %.
  2 (Auswertung) maker_schatten.py: Gebuehren Bybit (Taker 0,25 / Maker 0,10) -> Bitvavo USDC (0,05 / 0,05).
nur v6:
  3 (nur Abschalten) live/watchdog.py: stop() fehlte (Befund 72). app.py ruft self.watchdog.stop() beim Abschalten;
    der AttributeError brach AppEngine.stop() ab, BEVOR der Positionsstand gespeichert wurde. Uebernahme des
    v7-Fixes (L6, 25.09.2026): stop() setzt einen Riegel, check() startet danach nichts mehr neu.
  4 (keine Wirkung auf den Handel) data/market_data.py: ccxt.coinbasepro gibt es seit ccxt 4 nicht mehr (P0-11).
    Die feste Tabelle warf bei jedem Start einen Fehler, der Fallback nahm Binance. Jetzt wie v7: getattr(ccxt, id),
    ccxt_id ist "binance" -> derselbe Client, nur ohne roten Fehler bei jedem Start.
Aufruf: python patch_e13_kleinigkeiten.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "E13 KLEINIGKEITEN 15.10.2026"

MARGE = Ersetzung(
    "risk/exit_rules.py",
    "TRAIL_MARGE_PCT = 0.05\n",
    f"# [{MARKE}] 0,05 -> 0,10 (Entscheidung Sven E5b): gleiche Sicherheit wie der Puffer (E12),\n"
    "# Ausloeseverzug im Mittel 0,072 %, p90 0,17 %. Start 0,85 -> 1,11 | 1,0 -> 1,26 | 1,3 -> 1,57.\n"
    "TRAIL_MARGE_PCT = 0.10\n")

MAKER = Ersetzung(
    "maker_schatten.py",
    "# Gebuehren Bybit EU, je Seite. Der Unterschied ist der ganze Punkt.\nTAKER_PCT = 0.25\nMAKER_PCT = 0.10\n",
    f"# [{MARKE}] Zielboerse seit 14.10.2026: Bitvavo USDC (Z1, pruefstand/gebuehren.json),\n"
    "# Maker = Taker = 0,05 % je Seite. Der Gebuehrenvorteil des Warte-Auftrags ist damit NULL;\n"
    "# messbar bleibt nur die halbe Spanne (BTC ~1,4 bp, SOL ~2,9 bp) gegen verpasste Einstiege.\n"
    "# Vorher Bybit EU: TAKER_PCT = 0.25, MAKER_PCT = 0.10.\n"
    "TAKER_PCT = 0.05\nMAKER_PCT = 0.05\n")

WD_INIT = Ersetzung(
    "live/watchdog.py",
    "        self.restart_callbacks = {}\n\n    def watch(self, name, thread, restart_fn=None):\n",
    "        self.restart_callbacks = {}\n"
    f"        self._gestoppt = False          # [{MARKE}] Befund 72, siehe stop()\n"
    "\n"
    "    def stop(self):\n"
    "        \"\"\"Beendet die Ueberwachung. Wird beim Abschalten gerufen (app.py AppEngine.stop).\n"
    "\n"
    f"        [{MARKE}] Befund 72 - Uebernahme des v7-Fixes (L6, 25.09.2026).\n"
    "        Diese Methode FEHLTE, app.py rief sie trotzdem. Der AttributeError brach\n"
    "        AppEngine.stop() ab, bevor state_manager.auto_save() und state.save() liefen:\n"
    "        Der STOPPEN-Knopf speicherte den Positionsstand nicht, und beim naechsten Start\n"
    "        kam ein veralteter zurueck. Ein zweiter Klick tat nichts mehr, weil _running\n"
    "        schon vor dem Absturz auf False stand.\n"
    "\n"
    "        Diese Klasse hat keinen eigenen Thread. stop() legt nur einen Riegel um, damit\n"
    "        check() waehrend des Abschaltens keine gerade beendeten Threads neu startet.\n"
    "        check() wird derzeit von keiner Stelle gerufen (toter Code) - das bleibt so.\n"
    "        \"\"\"\n"
    "        self._gestoppt = True\n"
    "        log.info(\"WATCHDOG\", \"Ueberwachung beendet - keine Neustarts mehr.\")\n"
    "\n"
    "    def watch(self, name, thread, restart_fn=None):\n")

WD_CHECK = Ersetzung(
    "live/watchdog.py",
    "    def check(self):\n        dead = []\n",
    "    def check(self):\n"
    f"        # [{MARKE}] Befund 72: nach stop() nichts mehr neu starten.\n"
    "        if self._gestoppt:\n"
    "            return []\n"
    "        dead = []\n")

DATEN = Ersetzung(
    "data/market_data.py",
    '            ex_map = {"binance": ccxt.binance, "coinbasepro": ccxt.coinbasepro,\n'
    '                      "kraken": ccxt.kraken, "bybit": ccxt.bybit, "okx": ccxt.okx}\n'
    "            Ex = ex_map.get(config.exchange.ccxt_id, ccxt.binance)\n",
    f"            # [{MARKE}] P0-11, wie v7 (15.09.2026): Die feste Tabelle wertete JEDEN Eintrag aus,\n"
    "            # auch ccxt.coinbasepro, das es seit ccxt 4 nicht mehr gibt -> bei jedem Start\n"
    "            # 'Client-Fehler (1. Versuch): module ccxt has no attribute coinbasepro', danach\n"
    "            # Binance-Fallback. Ein roter Fehler bei jedem Start gewoehnt ans Ueberlesen.\n"
    "            # Jetzt wird nur die eingestellte Boerse geholt (ccxt_id = binance -> derselbe Client).\n"
    '            _id = str(getattr(config.exchange, "ccxt_id", "") or "binance")\n'
    "            Ex = getattr(ccxt, _id, None)\n"
    "            if Ex is None:\n"
    '                log.warn("DATA", f"ccxt kennt keine Boerse \'{_id}\' - nehme binance fuer die Kurse")\n'
    "                Ex = ccxt.binance\n")

ERS = {"v6": [MARGE, MAKER, WD_INIT, WD_CHECK, DATEN], "v7": [MARGE, MAKER]}


def funktionstest(name: str, ordner: Path) -> int:
    import importlib.util
    import shutil
    import tempfile
    import threading
    import types
    from _patchwerkzeug import anwenden
    fehler = 0
    with tempfile.TemporaryDirectory() as t:
        k = Path(t)
        for e in ERS[name]:
            (k / e.datei).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ordner / e.datei, k / e.datei)
        anwenden(k, ERS[name], MARKE, trocken_kopie=True)
        spec = importlib.util.spec_from_file_location("er", k / "risk" / "exit_rules.py")
        er = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(er)
        for d, soll in ((0.85, 1.11), (1.0, 1.26), (1.3, 1.57)):
            s = er.trail_start_pct(d)
            n = ((1 + er.K_BASIS_PCT / 100) / (1 - d / 100) - 1) * 100
            ok = abs(s - soll) < 0.006 and s >= n + 0.10 - 0.0005
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Abstand {d}: Start {s} (Nulllinie {n:.4f} + 0,10)")
        ok = abs(er.BREAKEVEN_PUFFER_PCT - 0.25) < 1e-9
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Puffer unveraendert {er.BREAKEVEN_PUFFER_PCT}")
        txt = (k / "maker_schatten.py").read_text(encoding="utf-8")
        ok = "TAKER_PCT = 0.05\nMAKER_PCT = 0.05\n" in txt.replace("\r\n", "\n")
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} maker_schatten: Bitvavo 0,05 / 0,05")
        if name == "v6":
            stub = types.ModuleType("core.logger")

            class L:
                def __init__(self):
                    self.z = []

                def __getattr__(self, a):
                    return lambda *x, **y: self.z.append((a, x))
            stub.log = L()
            alt = {m: sys.modules.get(m) for m in ("core", "core.logger")}
            sys.modules["core"] = types.ModuleType("core")
            sys.modules["core.logger"] = stub
            try:
                spec = importlib.util.spec_from_file_location("wd", k / "live" / "watchdog.py")
                wd = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(wd)
            finally:
                for m, v in alt.items():
                    if v is None:
                        sys.modules.pop(m, None)
                    else:
                        sys.modules[m] = v

            class H:
                def report_error(self, *a):
                    pass
            neu = []
            w = wd.Watchdog(H())
            tot = threading.Thread(target=lambda: None)
            tot.start()
            tot.join()
            w.watch("x", tot, restart_fn=lambda: neu.append(1))
            ok = w.check() == ["x"] and neu == [1]
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Watchdog vor stop(): toter Thread wird gemeldet und neu gestartet")
            w.stop()
            ok = w.check() == [] and neu == [1]
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Watchdog nach stop(): kein Neustart mehr, stop() wirft nicht (Befund 72)")
            md = (k / "data" / "market_data.py").read_text(encoding="utf-8")
            code = "\n".join(z for z in md.splitlines() if not z.strip().startswith("#"))
            import ccxt
            ok = "ccxt.coinbasepro" not in code and getattr(ccxt, "binance", None) is not None
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} market_data: kein ccxt.coinbasepro mehr im Code, getattr(ccxt, 'binance') vorhanden")
    return 1 if fehler else 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    main(pfad, ERS[name], MARKE, f"PATCH E13/L12 Kleinigkeiten {name}", zusatztest=lambda: funktionstest(name, pfad))
