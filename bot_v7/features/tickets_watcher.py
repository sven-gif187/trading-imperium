"""
TicketsWatcher - Beobachtet tickets.txt und schickt Eintraege an DocAgent

Format pro Zeile:
    STICHWORT: Beschreibung

Stichworte:
    SPEICHERN     -> TODO im Handbuch
    ERLEDIGT      -> als erledigt markieren
    BUG           -> Bug-Tracker
    DOKUMENTIEREN -> ausfuehrliche Doku
    NOTIZ         -> einfache Notiz

Kommentare beginnen mit # und werden ignoriert.
Leere Zeilen werden ignoriert.
"""
import os
import threading
from datetime import datetime
from typing import Optional, List, Tuple

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a, **kw): pass
        def warn(self, *a, **kw): pass
    log = _Log()


VALID_STICHWORTE = {"SPEICHERN", "ERLEDIGT", "BUG", "DOKUMENTIEREN", "NOTIZ"}


class TicketsWatcher:
    """Liest tickets.txt und routet Eintraege zum DocAgent."""

    def __init__(self, doc_agent, tickets_path: Optional[str] = None):
        self.doc_agent = doc_agent
        if tickets_path is None:
            tickets_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "tickets.txt"
            )
        self.tickets_path = tickets_path
        self._lock = threading.Lock()
        self._last_mtime = 0
        self._processed_total = 0

    def _parse_line(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse eine Zeile. Gibt (stichwort, text) oder None zurueck."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None
        if ":" not in line:
            return None
        parts = line.split(":", 1)
        stichwort = parts[0].strip().upper()
        text = parts[1].strip()
        if stichwort not in VALID_STICHWORTE:
            return None
        if not text:
            return None
        return (stichwort, text)

    def check(self):
        """Prueft tickets.txt und verarbeitet neue Eintraege.

        Wird vom Scheduler aufgerufen (alle 30s).
        """
        with self._lock:
            try:
                if not os.path.exists(self.tickets_path):
                    return

                # Check ob Datei sich geaendert hat (mtime)
                mtime = os.path.getmtime(self.tickets_path)
                if mtime == self._last_mtime:
                    return  # nichts neues

                with open(self.tickets_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Parse alle Zeilen
                tickets = []
                for line in lines:
                    parsed = self._parse_line(line)
                    if parsed:
                        tickets.append(parsed)

                if not tickets:
                    # mtime trotzdem updaten damit wir nicht jede Runde lesen
                    self._last_mtime = mtime
                    return

                # Verarbeite Tickets via DocAgent
                processed = []
                for stichwort, text in tickets:
                    if self.doc_agent and hasattr(self.doc_agent, "add_note"):
                        try:
                            if stichwort == "NOTIZ":
                                # NOTIZ ist ein DOKUMENTIEREN-Alias
                                result = self.doc_agent.add_note("DOKUMENTIEREN", text)
                            else:
                                result = self.doc_agent.add_note(stichwort, text)
                            processed.append((stichwort, text, result))
                        except Exception as e:
                            log.warn("TICKETS", f"Fehler bei {stichwort}: {str(e)[:80]}")
                    else:
                        log.warn("TICKETS", "DocAgent nicht verfuegbar - Ticket nicht verarbeitet")

                self._processed_total += len(processed)

                # Leere die Datei mit Confirmation-Header
                self._write_confirmation(processed)
                self._last_mtime = os.path.getmtime(self.tickets_path)

                log.info("TICKETS", f"{len(processed)} Tickets verarbeitet -> ENTWICKLERHANDBUCH.md")

            except Exception as e:
                log.warn("TICKETS", f"Watcher-Fehler: {str(e)[:120]}")

    def _write_confirmation(self, processed: List[Tuple[str, str, str]]):
        """Schreibt Confirmation in tickets.txt und leert die Tickets."""
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = f"""# ===========================================================
# TICKETS.TXT - Befehls-Agent Eingangs-Datei
# ===========================================================
#
# Letzte Verarbeitung: {ts}
# Eintraege verarbeitet: {len(processed)} (Total: {self._processed_total})
#
# So gehts:
#   1. Eine Zeile pro Ticket im Format:  STICHWORT: Text
#   2. Datei speichern und schliessen
#   3. Bot frisst die Tickets in maximal 30s
#   4. Eintraege landen automatisch im ENTWICKLERHANDBUCH.md
#   5. Diese Datei wird danach geleert (mit dieser Bestaetigung)
#
# Stichworte:
#   SPEICHERN: <text>     -> TODO Liste im Handbuch
#   ERLEDIGT: <text>      -> als erledigt markiert
#   BUG: <text>           -> Bug-Tracker
#   DOKUMENTIEREN: <text> -> ausfuehrliche Doku
#   NOTIZ: <text>         -> einfache Notiz
#
# Zeilen die mit # beginnen werden ignoriert.
# Leere Zeilen werden ignoriert.
#
# ===========================================================

"""
            if processed:
                content += "# Letzte verarbeitete Tickets:\n"
                for stichwort, text, _result in processed:
                    content += f"#   [{stichwort}] {text[:60]}\n"
                content += "\n"
            with open(self.tickets_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            log.warn("TICKETS", f"Confirmation-Write Fehler: {str(e)[:80]}")

    def get_status(self) -> dict:
        return {
            "tickets_path": self.tickets_path,
            "processed_total": self._processed_total,
            "watching": os.path.exists(self.tickets_path),
        }
