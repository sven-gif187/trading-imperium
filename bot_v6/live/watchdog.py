"""
Trading Imperium V5 – Watchdog
Überwacht laufende Threads und startet tote Komponenten neu.
"""
import threading, time
from typing import Dict, List
from core.logger import log

class Watchdog:
    def __init__(self, health_monitor):
        self.health = health_monitor
        self.watched_threads = {}
        self.restart_callbacks = {}
        self._gestoppt = False          # [E13 KLEINIGKEITEN 15.10.2026] Befund 72, siehe stop()

    def stop(self):
        """Beendet die Ueberwachung. Wird beim Abschalten gerufen (app.py AppEngine.stop).

        [E13 KLEINIGKEITEN 15.10.2026] Befund 72 - Uebernahme des v7-Fixes (L6, 25.09.2026).
        Diese Methode FEHLTE, app.py rief sie trotzdem. Der AttributeError brach
        AppEngine.stop() ab, bevor state_manager.auto_save() und state.save() liefen:
        Der STOPPEN-Knopf speicherte den Positionsstand nicht, und beim naechsten Start
        kam ein veralteter zurueck. Ein zweiter Klick tat nichts mehr, weil _running
        schon vor dem Absturz auf False stand.

        Diese Klasse hat keinen eigenen Thread. stop() legt nur einen Riegel um, damit
        check() waehrend des Abschaltens keine gerade beendeten Threads neu startet.
        check() wird derzeit von keiner Stelle gerufen (toter Code) - das bleibt so.
        """
        self._gestoppt = True
        log.info("WATCHDOG", "Ueberwachung beendet - keine Neustarts mehr.")

    def watch(self, name, thread, restart_fn=None):
        self.watched_threads[name] = thread
        if restart_fn:
            self.restart_callbacks[name] = restart_fn

    def check(self):
        # [E13 KLEINIGKEITEN 15.10.2026] Befund 72: nach stop() nichts mehr neu starten.
        if self._gestoppt:
            return []
        dead = []
        for name, thread in self.watched_threads.items():
            if not thread.is_alive():
                dead.append(name)
                log.error("WATCHDOG", f"Thread '{name}' ist tot!")
                self.health.report_error(name, "Thread gestorben")
                if name in self.restart_callbacks:
                    try:
                        log.info("WATCHDOG", f"Starte '{name}' neu...")
                        self.restart_callbacks[name]()
                    except Exception as e:
                        log.error("WATCHDOG", f"Neustart '{name}' fehlgeschlagen: {e}")
        return dead

    def get_status(self):
        return {name: t.is_alive() for name, t in self.watched_threads.items()}
