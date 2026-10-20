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
        self._gestoppt = False          # [BEFUND 72] siehe stop()

    def stop(self):
        """Beendet die Ueberwachung. Wird beim Abschalten gerufen.

        [BEFUND 72, behoben 25.09.2026] Diese Methode FEHLTE - und
        app.py:4731 rief sie trotzdem. Der AttributeError flog mitten in
        AppEngine.stop(), und alles danach lief nie: state_manager
        .auto_save() und state.save(), also genau der Doppelverkauf-Fix
        vom 13.08.2026. Der Bot vergass beim Beenden seinen
        Positionsstand, und beim naechsten Start holte
        restore_positions() einen veralteten zurueck. Im Papierhandel
        kostet das falsche Zahlen; live wuerde er Muenzen verkaufen, die
        er nicht mehr besitzt - genau der Vorfall vom 13.08.

        Weil `self._running = False` in AppEngine.stop() VOR dem Absturz
        steht, tat ein zweiter Klick auf den Stopp-Knopf gar nichts mehr
        und sah dabei ruhig aus.

        BELEGT, nicht hergeleitet: data_store/jobs/bot_konsole.log vom
        25.09.2026 fuehrt den vollstaendigen Traceback - Klick auf den
        Stopp-Knopf (ui/main_window.py:3236) -> app.py:4731 ->
        AttributeError: 'Watchdog' object has no attribute 'stop'.

        WAS SIE TUT. Diese Klasse hat keinen eigenen Thread, es gibt also
        nichts zu beenden oder zusammenzufuehren. Gefaehrlich ist etwas
        anderes: check() startet tote Threads NEU. Liefe es waehrend des
        Abschaltens, wuerde es genau die Komponenten wiederbeleben, die
        gerade beendet wurden. stop() legt deshalb einen Riegel um, den
        check() als erstes prueft.

        BEWUSST NICHT GETAN: check() an den Taktgeber haengen. Die
        Methode wird derzeit von KEINER Stelle im Projekt gerufen
        (geprueft 25.09.2026: die einzigen vier Fundstellen von
        `watchdog` sind der Import app.py:63, die Erzeugung app.py:554,
        dieser stop() und get_status app.py:4862). Die Neustart-Funktion
        ist also toter Code. Sie scharfzuschalten waere eine eigene
        Verhaltensaenderung mit eigener Messung - nicht etwas, das man
        im Vorbeigehen bei einer Abschalt-Reparatur mitnimmt.
        """
        self._gestoppt = True
        log.info("WATCHDOG", "Ueberwachung beendet - keine Neustarts mehr.")

    def watch(self, name, thread, restart_fn=None):
        self.watched_threads[name] = thread
        if restart_fn:
            self.restart_callbacks[name] = restart_fn

    def check(self):
        # [BEFUND 72] Nach stop() wird nichts mehr neu gestartet. Ohne
        # diesen Riegel koennte ein Takt, der waehrend des Abschaltens
        # noch durchlaeuft, genau die Threads wiederbeleben, die das
        # Abschalten gerade beendet hat.
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
