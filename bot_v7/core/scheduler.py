"""
Trading Imperium V5 – Task Scheduler
Plant und führt periodische Aufgaben aus: Trading-Loop, News-Check,
Rebalancing, Heartbeat, Auto-Save, etc.
"""
import threading
import time
from typing import Callable, Dict, List
from datetime import datetime, timezone


class Task:
    """Eine periodische Aufgabe."""
    def __init__(self, name: str, callback: Callable, interval_sec: int, enabled: bool = True):
        self.name = name
        self.callback = callback
        self.interval_sec = interval_sec
        self.enabled = enabled
        self.last_run = 0.0
        self.run_count = 0
        self.error_count = 0
        self.last_error = ""
        self.running = False

    def should_run(self) -> bool:
        if not self.enabled or self.running:
            return False
        return (time.time() - self.last_run) >= self.interval_sec

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "interval": self.interval_sec,
            "enabled": self.enabled,
            "runs": self.run_count,
            "errors": self.error_count,
            "last_error": self.last_error,
        }


class Scheduler:
    """Verwaltet periodische Tasks in einem zentralen Loop."""

    def __init__(self):
        self._tasks: List[Task] = []
        self._running = False
        self._thread = None
        self._tick_interval = 1.0  # Prüfe jede Sekunde ob Tasks fällig sind

    def add_task(self, name: str, callback: Callable, interval_sec: int, enabled: bool = True):
        """Registriert einen periodischen Task."""
        task = Task(name, callback, interval_sec, enabled)
        self._tasks.append(task)
        return task

    def start(self):
        """Startet den Scheduler in einem eigenen Thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()

    def stop(self):
        """Stoppt den Scheduler."""
        self._running = False

    def _loop(self):
        """Haupt-Loop: Prüft periodisch ob Tasks fällig sind.

        FIX: Tasks laufen jetzt PARALLEL in eigenen Threads, damit
        ein langsamer Task (z.B. _trading_tick) nicht andere Tasks
        wie sl_tp_monitor blockiert!
        """
        while self._running:
            for task in self._tasks:
                if task.should_run():
                    # [DOPPELLAUF-FIX 29.07.] Task VOR dem Thread-Start als
                    # belegt markieren. Vorher setzte erst der neue Thread
                    # task.running=True - bis dahin (Thread-Start kann unter
                    # GIL-Last >1s dauern) sah der naechste Scheduler-Tick
                    # running=False + altes last_run und startete denselben
                    # Task ein ZWEITES Mal. Bei _trading_tick = Doppelkauf.
                    task.running = True
                    task.last_run = time.time()
                    threading.Thread(
                        target=self._run_task,
                        args=(task,),
                        daemon=True,
                        name=f"task-{task.name}"
                    ).start()
            time.sleep(self._tick_interval)

    def _run_task(self, task: 'Task'):
        """Führt einen Task in seinem eigenen Thread aus."""
        try:
            task.callback()
            task.run_count += 1
        except Exception as e:
            task.error_count += 1
            task.last_error = f"{datetime.now().strftime('%H:%M:%S')}: {str(e)[:100]}"
            # [GEFUNDENE-PROBLEME 37, behoben 18.08.2026]
            # Hier wurde NUR hochgezaehlt - keine Logzeile, nichts.
            # Ein Task konnte dadurch stundenlang bei jedem Lauf scheitern,
            # ohne dass es irgendwo auftauchte. Genau das ist am 18.08. mit
            # dem Ticket-Kanal passiert: Er stand ab 08:22 UTC still, das
            # System.log schwieg, und aufgefallen ist es erst, als jemand
            # auf eine ausbleibende Wirkung wartete.
            #
            # Jetzt: der ERSTE Fehler eines Tasks wird immer gemeldet,
            # danach nur noch jeder zehnte. Sonst flutet ein Task, der im
            # 12-Sekunden-Takt scheitert, das Log - und ein geflutetes Log
            # ist so wenig lesbar wie ein schweigendes.
            #
            # Der Logger wird HIER eingebunden, nicht oben in der Datei:
            # core/logger.py wird von vielen Bauteilen benutzt, und ein
            # Import ganz oben koennte einen Ringschluss ausloesen. Beim
            # ersten Versuch fehlte der Import komplett - der Aufruf waere
            # dann selbst still ins Leere gelaufen, also genau der Fehler,
            # der hier behoben werden soll.
            try:
                from core.logger import log as _log
                if task.error_count == 1 or task.error_count % 10 == 0:
                    _log.warn("SCHEDULER",
                              f"Task '{task.name}' gescheitert "
                              f"({task.error_count}. Mal): {str(e)[:120]}")
            except Exception:
                pass          # Melden darf den Scheduler nie anhalten
        finally:
            # last_run wurde beim Start gesetzt (Periode = Startabstand,
            # nicht Endabstand). Nur die Belegung wieder freigeben.
            task.running = False

    def get_status(self) -> List[Dict]:
        """Gibt den Status aller Tasks zurück."""
        return [t.to_dict() for t in self._tasks]

    def enable_task(self, name: str):
        for t in self._tasks:
            if t.name == name:
                t.enabled = True

    def disable_task(self, name: str):
        for t in self._tasks:
            if t.name == name:
                t.enabled = False
