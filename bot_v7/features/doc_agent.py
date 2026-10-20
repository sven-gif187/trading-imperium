"""
DocAgent - Automatisches Dokumentations-System

Schreibt wichtige Bot-Events ins ENTWICKLERHANDBUCH.md.
Empfaengt Stichworte vom User (SPEICHERN, ERLEDIGT, BUG, etc.).

Thread-safe, schreibt in Append-Mode mit File-Lock-Logik.
"""
import os
import shutil
import tempfile
import threading
import time
from datetime import datetime, date
from collections import defaultdict, deque
from typing import Optional, Dict, List

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a, **kw): pass
        def warn(self, *a, **kw): pass
        def error(self, *a, **kw): pass
    log = _Log()


class DocAgent:
    """Automatischer Documentation Agent."""

    def __init__(self, handbook_path: Optional[str] = None):
        # Default: ENTWICKLERHANDBUCH.md im Projekt-Root
        if handbook_path is None:
            handbook_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "ENTWICKLERHANDBUCH.md"
            )
        self.handbook_path = handbook_path
        self._lock = threading.Lock()

        # Event-Buffer fuer Tagesbericht
        self.daily_buffer = {
            "trades": deque(maxlen=200),
            "strategy_changes": deque(maxlen=50),
            "errors": deque(maxlen=50),
            "events": deque(maxlen=100),
            "v4_syncs": deque(maxlen=20),
            "bottom_signals": deque(maxlen=20),
            "auto_defense": deque(maxlen=50),
        }
        self.last_strategy = None
        self.last_daily_report = None
        self.start_time = datetime.now()

        # Stichworte
        self.todos_added = []
        self.completed_today = []
        self.bugs_today = []

        # Throttle: identische Events nicht spammen
        self._last_log_time = defaultdict(float)
        self._throttle_sec = 60

        # === DOC-V2: Marktkontext + Persistenz (ueberlebt Neustarts) ===
        self.market_context = {"cycle": "", "regime": "", "fg": None}
        self._state_path = os.path.join(
            os.path.dirname(self.handbook_path), "data_store", "doc_agent_state.json")
        self.buffer_date = date.today().isoformat()

        # === ATOMIC-WRITE: rollierendes Backup der letzten 3 Staende ===
        # .bak1 = juengster Stand, .bak3 = aeltester.
        self._backup_count = 3
        # Nicht bei jedem Event kopieren (200 KB x jedes Trade-Event waere
        # unnoetige Disk-Last) - hoechstens alle N Sekunden ein neuer Stand.
        self._backup_min_interval = 300
        self._last_backup_ts = 0.0
        self._corruption_warned = False

        self._load_state()

    # === ATOMIC-WRITE: sicheres Schreiben ===
    def _atomic_write(self, path: str, data: str, encoding: str = "utf-8"):
        """Schreibt `data` atomar nach `path`.

        temp-Datei im selben Verzeichnis -> flush -> fsync -> os.replace.
        os.replace ist auf einem Dateisystem atomar: es gibt nie einen
        Zustand, in dem `path` halb geschrieben oder genullt ist. Stirbt
        der Prozess mittendrin, bleibt die alte Datei unveraendert stehen
        und nur die temp-Datei ist Muell.
        """
        # [HAERTUNG 04.08.] Zweite Verteidigungslinie: kein Aufrufer darf
        # Nullbytes in eine Dokumentationsdatei schreiben, egal woher der
        # Inhalt stammt.
        if "\x00" in data:
            raise ValueError("Schreibvorgang abgelehnt: Inhalt enthaelt "
                             "Nullbytes")
        target_dir = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(target_dir, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=".doc_agent_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())          # Daten wirklich auf Platte
            os.replace(tmp, path)             # atomarer Austausch
            tmp = None
        finally:
            if tmp is not None and os.path.exists(tmp):
                try:
                    os.remove(tmp)            # Aufraeumen falls fehlgeschlagen
                except Exception:
                    pass

    def _has_nullbytes(self, path: str) -> bool:
        """True wenn die Datei Nullbytes enthaelt (Korruptions-Signatur)."""
        try:
            with open(path, "rb") as f:
                return b"\x00" in f.read()
        except Exception:
            return False

    def _rotate_backups(self, path: str):
        """Rollierendes Backup: .bak1 (neu) .. .bak3 (alt).

        Wird uebersprungen, wenn die Quelldatei Nullbytes enthaelt - sonst
        wuerde ein korrupter Stand die intakten Backups ueberschreiben.
        """
        try:
            if not os.path.isfile(path):
                return
            now = time.time()
            if now - self._last_backup_ts < self._backup_min_interval:
                return
            if self._has_nullbytes(path):
                if not self._corruption_warned:
                    log.warn("DOC", "Handbuch enthaelt Nullbytes - Backup-Rotation "
                                    "ausgesetzt, damit intakte Staende erhalten bleiben")
                    self._corruption_warned = True
                return

            oldest = "{0}.bak{1}".format(path, self._backup_count)
            if os.path.exists(oldest):
                os.remove(oldest)
            for i in range(self._backup_count - 1, 0, -1):
                src = "{0}.bak{1}".format(path, i)
                if os.path.exists(src):
                    os.replace(src, "{0}.bak{1}".format(path, i + 1))
            shutil.copy2(path, path + ".bak1")
            self._last_backup_ts = now
        except Exception as e:
            log.warn("DOC", "Backup-Rotation fehlgeschlagen: " + str(e)[:80])

    def _append_to_handbook(self, section_key: str, content: str):
        """Append content to handbook unter spezieller Section."""
        with self._lock:
            try:
                # Wenn Handbook nicht existiert, leg eines an
                if not os.path.exists(self.handbook_path):
                    self._init_handbook()

                with open(self.handbook_path, "r", encoding="utf-8") as f:
                    book = f.read()

                # [HAERTUNG 04.08.] Nullbytes sind gueltiges UTF-8 (U+0000),
                # der Lesevorgang oben wirft deshalb keinen Fehler. Ohne diese
                # Pruefung wird ein beschaedigter Kopf bei JEDEM Event erneut
                # festgeschrieben - genau so ueberlebten 68.328 Nullbytes vom
                # 28.07. bis zum 04.08. Lieber diesen einen Eintrag verlieren
                # als den Schaden zementieren.
                if "\x00" in book:
                    if not self._corruption_warned:
                        log.warn("DOC", "Handbuch enthaelt Nullbytes - Eintrag "
                                        "VERWORFEN statt Schaden erneut zu "
                                        "schreiben. Datei pruefen.")
                        self._corruption_warned = True
                    return

                # Sektion "EVENTS-LOG" am Ende anhaengen
                marker = "## EVENTS-LOG"
                if marker not in book:
                    book += "\n\n## EVENTS-LOG\n\n*Auto-generiert vom DocAgent*\n\n"

                # Append unter dem Marker
                idx = book.rfind(marker)
                section_start = book.find("\n", idx) + 1
                # Finde naechstes "## " section header oder Ende
                next_section = book.find("\n## ", section_start)
                if next_section == -1:
                    insert_at = len(book)
                else:
                    insert_at = next_section

                new_entry = f"{content}\n"
                book = book[:insert_at] + new_entry + book[insert_at:]

                # Erst den bisherigen Stand sichern, dann atomar ersetzen
                self._rotate_backups(self.handbook_path)
                self._atomic_write(self.handbook_path, book)
            except Exception as e:
                log.warn("DOC", f"Schreib-Fehler: {str(e)[:80]}")

    def _init_handbook(self):
        """Erstelle initiales Handbuch wenn keins da."""
        try:
            content = f"""# TRADING IMPERIUM V6 - ENTWICKLERHANDBUCH (Auto-Generiert)

> Auto-generiert vom DocAgent
> Start: {datetime.now().isoformat()}

## EVENTS-LOG

*Auto-generiert vom DocAgent*

"""
            self._atomic_write(self.handbook_path, content)
        except Exception:
            pass

    def _throttle_check(self, key: str) -> bool:
        """True wenn Throttle erlaubt zu loggen."""
        now = time.time()
        if now - self._last_log_time[key] < self._throttle_sec:
            return False
        self._last_log_time[key] = now
        return True

    # === DOC-V2: Persistenz ===
    def _load_state(self):
        """Laedt Tagespuffer von Festplatte (Neustarts loeschen die Statistik nicht mehr)."""
        try:
            import json
            if not os.path.exists(self._state_path):
                return
            with open(self._state_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.last_daily_report = saved.get("last_report_date")  # DOC-DEDUPE
            if saved.get("buffer_date") != date.today().isoformat():
                return  # alter Tag -> frisch anfangen
            self.buffer_date = saved["buffer_date"]
            for key in self.daily_buffer:
                for item in saved.get(key, []):
                    self.daily_buffer[key].append(item)
            self.todos_added = saved.get("todos_added", [])
            self.completed_today = saved.get("completed_today", [])
            self.bugs_today = saved.get("bugs_today", [])
            self.market_context.update(saved.get("market_context", {}))
            log.info("DOC", "Tagespuffer wiederhergestellt: "
                     + str(len(self.daily_buffer["trades"])) + " Trades heute")
        except Exception as e:
            log.warn("DOC", "State-Load Fehler: " + str(e)[:80])

    def _persist(self):
        """Speichert Tagespuffer auf Festplatte."""
        try:
            import json
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            data = {"buffer_date": self.buffer_date}
            data["last_report_date"] = self.last_daily_report  # DOC-DEDUPE
            for key, buf in self.daily_buffer.items():
                data[key] = list(buf)
            data["todos_added"] = self.todos_added
            data["completed_today"] = self.completed_today
            data["bugs_today"] = self.bugs_today
            data["market_context"] = self.market_context
            # Gleiche Absicherung: ein Absturz darf den Tagespuffer nicht zerreissen
            self._atomic_write(self._state_path,
                               json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    def update_market_context(self, cycle: str = "", regime: str = "", fg=None):
        """Optional: Marktkontext fuer den Tagesbericht setzen."""
        if cycle:
            self.market_context["cycle"] = cycle
        if regime:
            self.market_context["regime"] = regime
        if fg is not None:
            self.market_context["fg"] = fg

    # === PUBLIC API ===
    def on_start(self, mode: str = "paper", balance: float = 0):
        """Bot-Start dokumentieren."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"- **{ts}** [START] Bot gestartet ({mode}, Balance: {balance:.2f} USDC)"
        self.daily_buffer["events"].append({"time": ts, "type": "START", "msg": msg})
        self._persist()
        self._append_to_handbook("events", msg)

    def on_stop(self, reason: str = "manual"):
        """Bot-Stop dokumentieren."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"- **{ts}** [STOP] Bot gestoppt ({reason})"
        self.daily_buffer["events"].append({"time": ts, "type": "STOP", "msg": msg})
        self._persist()
        self._append_to_handbook("events", msg)

    def on_trade(self, side: str, symbol: str, amount_usd: float,
                 price: float = 0, strategy: str = "", pnl: float = None):
        """Trade dokumentieren."""
        if not self._throttle_check(f"trade_{symbol}_{side}"):
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pnl_str = f" PnL: {pnl:+.2f}$" if pnl is not None else ""
        msg = (f"- **{ts}** [{side}] {symbol}: {amount_usd:.2f}$ @ {price:.4f}$"
               f" [{strategy}]{pnl_str}")
        self.daily_buffer["trades"].append({
            "time": ts, "side": side, "symbol": symbol,
            "amount": amount_usd, "strategy": strategy, "pnl": pnl,
        })
        self._persist()
        self._append_to_handbook("events", msg)

    def on_strategy_change(self, new_strategy: str, regime: str = "",
                          cycle: str = "", fg: int = 0):
        """Strategie-Wechsel dokumentieren (nur bei echtem Wechsel)."""
        if new_strategy == self.last_strategy:
            return
        self.last_strategy = new_strategy
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (f"- **{ts}** [BRAIN] Strategie -> {new_strategy} "
               f"(Regime: {regime}, Zyklus: {cycle}, F&G: {fg})")
        self.daily_buffer["strategy_changes"].append({
            "time": ts, "strategy": new_strategy,
            "regime": regime, "cycle": cycle, "fg": fg,
        })
        self.update_market_context(cycle=cycle, regime=regime, fg=fg)
        self._persist()
        self._append_to_handbook("events", msg)

    def on_error(self, module: str, error: str):
        """Fehler dokumentieren."""
        if not self._throttle_check(f"error_{module}"):
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"- **{ts}** [ERROR][{module}] {error[:200]}"
        self.daily_buffer["errors"].append({"time": ts, "module": module, "error": error})
        self._persist()
        self._append_to_handbook("events", msg)

    def on_v4_sync(self, source: str, trades_count: int, pnl: float):
        """V4-Sync Event."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (f"- **{ts}** [V4-SYNC] Quelle: {source} | "
               f"{trades_count} Trades importiert, {pnl:+.2f}$ PnL")
        self.daily_buffer["v4_syncs"].append({
            "time": ts, "source": source, "trades": trades_count, "pnl": pnl,
        })
        self._append_to_handbook("events", msg)

    def on_bottom_signal(self, active: bool, score: int, indicators: str = ""):
        """Bottom-Signal Aktivierung/Deaktivierung."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "AKTIV" if active else "BEENDET"
        msg = f"- **{ts}** [BOTTOM] Signal {status} (Score: {score}, {indicators})"
        self.daily_buffer["bottom_signals"].append({
            "time": ts, "active": active, "score": score,
        })
        self._append_to_handbook("events", msg)

    def on_auto_defense(self, symbol: str, pnl_pct: float, reason: str = ""):
        """Auto-Defense Trigger."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"- **{ts}** [AUTO-DEFENSE] {symbol} verkauft @ PnL {pnl_pct:+.2f}% ({reason})"
        self.daily_buffer["auto_defense"].append({
            "time": ts, "symbol": symbol, "pnl_pct": pnl_pct,
        })
        self._append_to_handbook("events", msg)

    # === STICHWORT-EMPFANG ===
    def add_note(self, stichwort: str, text: str) -> str:
        """Verarbeitet Stichworte vom User.

        stichwort: SPEICHERN | ERLEDIGT | BUG | DOKUMENTIEREN
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stichwort = stichwort.upper().strip()

        if stichwort == "SPEICHERN":
            self.todos_added.append({"time": ts, "text": text})
            msg = f"\n### TODO (vom User, {ts})\n- [ ] {text}\n"
            self._append_to_handbook("todo", msg)
            return f"TODO eingetragen: {text}"
        elif stichwort == "ERLEDIGT":
            self.completed_today.append({"time": ts, "text": text})
            msg = f"\n### ERLEDIGT ({ts})\n- [x] {text}\n"
            self._append_to_handbook("done", msg)
            return f"Als erledigt markiert: {text}"
        elif stichwort == "BUG":
            self.bugs_today.append({"time": ts, "text": text})
            msg = f"\n### BUG REPORT ({ts})\n- {text}\n"
            self._append_to_handbook("bugs", msg)
            return f"Bug eingetragen: {text}"
        elif stichwort == "DOKUMENTIEREN":
            msg = f"\n### DOKU-EINTRAG ({ts})\n{text}\n"
            self._append_to_handbook("docs", msg)
            return f"Dokumentation hinzugefuegt"
        else:
            return f"Unbekanntes Stichwort: {stichwort}"

    def _auto_sensei_lesson(self, today: str):
        """Laesst den Sensei taeglich automatisch eine Lektion rechnen.
        JSON-DB wird immer aktualisiert; SENSEI_LEKTIONEN.md bekommt
        nur EINEN Eintrag pro Tag (kein Spam bei Neustarts)."""
        import json as _json
        import os as _os
        from features.sensei import Sensei
        s = Sensei()
        md_already = False
        try:
            if _os.path.exists(s.lessons_json_path):
                with open(s.lessons_json_path, "r", encoding="utf-8") as f:
                    md_already = any(e.get("date") == today
                                     for e in _json.load(f))
        except Exception:
            pass
        s.daily_lesson(write_md=not md_already)
        log.info("DOC", "Sensei-Lektion automatisch erzeugt"
                 + (" (nur DB-Update)" if md_already else " (+ Markdown)"))

    def write_daily_report(self, force: bool = False):
        """Schreibt Tagesbericht (wird vom Scheduler aufgerufen).
        DOC-DEDUPE: max. 1 Bericht pro Tag, force=True erzwingt."""
        try:
            today = date.today().isoformat()
            # === DOC-DEDUPE: Neustarts erzeugen keine Duplikate mehr ===
            if not force and self.last_daily_report == today:
                log.info("DOC", "Tagesbericht heute bereits geschrieben - uebersprungen")
                return

            # === TAGESBERICHT-FIX2 22.07.: Kennzahlen aus dem JOURNAL des
            # abgeschlossenen VORTAGS statt aus leerem RAM-Puffer. ===
            try:
                from datetime import timedelta as _td
                import json as _json
                _report_day = (date.today() - _td(days=1)).isoformat()
                _root = os.path.dirname(os.path.abspath(self.handbook_path))
                _jt = []
                for _cand in (os.path.join(_root, "data_store", "trades_v5.json"),
                              os.path.join(_root, "trades_v5.json")):
                    if os.path.isfile(_cand):
                        with open(_cand, "r", encoding="utf-8") as _jf:
                            _all = _json.load(_jf)
                        _jt = [x for x in _all
                               if str(x.get("time", "")).startswith(_report_day)]
                        break
                if _jt:
                    # RAM-Puffer fuer diesen Bericht durch Journal-Daten ersetzen
                    _buf = []
                    for _x in _jt:
                        _c = _x.get("coin", "?")
                        _buf.append({
                            "side": _x.get("type", ""),
                            # [E10-DOC 29.07.] BEIDE Schluessel schreiben.
                            # Dieser Pfad schrieb nur "coin", der Bericht liest
                            # aber "symbol" (on_trade schreibt "symbol"). Ergebnis:
                            # KeyError 'symbol' -> der Tagesbericht ist seit
                            # Einbau von TAGESBERICHT-FIX2 bei JEDEM Lauf aus dem
                            # Journal stumm abgebrochen. Im Log sichtbar als
                            # "[TAGESBERICHT-FIX2] ... 16 Trades" direkt gefolgt
                            # von "Daily-Report Fehler: 'symbol'".
                            "coin": _c,
                            "symbol": _c,
                            "amount": _x.get("amount", 0) or 0,
                            "pnl": (float(_x["pnl"]) if _x.get("pnl") is not None
                                    and _x.get("type") == "SELL" else None),
                            "strategy": _x.get("strategy") or _x.get("active_strategy"),
                        })
                    self.daily_buffer["trades"] = _buf
                    today = _report_day  # Berichtstitel zeigt den dokumentierten Tag
                    _last = _jt[-1]
                    if not self.market_context.get("regime"):
                        self.market_context["regime"] = _last.get("market_regime", "")
                    if not self.market_context.get("cycle"):
                        self.market_context["cycle"] = _last.get("cycle_phase", "")
                    if self.market_context.get("fg") is None:
                        self.market_context["fg"] = _last.get("fear_greed_at_entry")
                    log.info("DOC", f"[TAGESBERICHT-FIX2] Vortag {_report_day} "
                                    f"aus Journal: {len(_buf)} Trades")
            except Exception as _tbf_err:
                log.warn("DOC", f"[TAGESBERICHT-FIX2] Journal-Lesen fehlgeschlagen: "
                                f"{str(_tbf_err)[:60]}")

            uptime = datetime.now() - self.start_time
            uptime_h = uptime.total_seconds() / 3600

            trade_count = len(self.daily_buffer["trades"])
            error_count = len(self.daily_buffer["errors"])
            strat_changes = len(self.daily_buffer["strategy_changes"])
            v4_syncs = len(self.daily_buffer["v4_syncs"])
            auto_defs = len(self.daily_buffer["auto_defense"])

            # [E10-DOC 29.07.] Durchgaengig .get() statt []. Der Puffer wird aus
            # ZWEI Quellen gefuellt (on_trade -> "symbol", TAGESBERICHT-FIX2 ->
            # frueher nur "coin") und ausserdem aus doc_agent_state.json
            # wiederhergestellt, die aeltere Schemata enthalten kann. Ein
            # einziger fehlender Schluessel hat bisher den kompletten
            # Tagesbericht verschluckt - gefangen von except Exception.
            _tr = self.daily_buffer["trades"]

            def _feld(t, *namen, default=None):
                for n in namen:
                    v = t.get(n)
                    if v is not None:
                        return v
                return default

            def _pnl(t):
                v = t.get("pnl")
                if v is None:
                    return None
                try:
                    return float(v)
                except Exception:
                    return None

            buys = sum(1 for t in _tr if _feld(t, "side", "type", default="") == "BUY")
            sells = sum(1 for t in _tr if _feld(t, "side", "type", default="") == "SELL")
            total_pnl = sum(_pnl(t) or 0.0 for t in _tr if _pnl(t) is not None)

            # === DOC-V2: Win-Rate + bester/schlechtester Trade ===
            closed = [t for t in _tr if _pnl(t) is not None]
            wins = sum(1 for t in closed if (_pnl(t) or 0) > 0)
            win_rate = (wins / len(closed) * 100) if closed else 0.0
            best_trade = max(closed, key=lambda t: _pnl(t) or 0.0) if closed else None
            worst_trade = min(closed, key=lambda t: _pnl(t) or 0.0) if closed else None

            # Top-Strategien des Tages
            strat_count = defaultdict(int)
            for t in _tr:
                if t.get("strategy"):
                    strat_count[t["strategy"]] += 1
            top_strats = sorted(strat_count.items(), key=lambda x: -x[1])[:3]

            report = f"""

---

## TAGESBERICHT {today}

*Auto-generiert vom DocAgent um {datetime.now().strftime("%H:%M:%S")}*

**Uptime:** {uptime_h:.1f} Stunden

### Marktlage (letzter Stand)
- **Zyklus:** {self.market_context.get("cycle") or "n/a"} | **Regime:** {self.market_context.get("regime") or "n/a"} | **F&G:** {self.market_context.get("fg") if self.market_context.get("fg") is not None else "n/a"}

### Aktivitaet
- **Trades:** {trade_count} ({buys} BUYs, {sells} SELLs)
- **Abgeschlossen:** {len(closed)} | **Win-Rate:** {win_rate:.0f}%
- **Total P&L:** {total_pnl:+.2f}$
- **Strategie-Wechsel:** {strat_changes}
- **V4-Syncs:** {v4_syncs}
- **Auto-Defense ausgeloest:** {auto_defs}x
- **Fehler:** {error_count}

### Top-Strategien heute
"""
            if best_trade:
                report += ("**Bester Trade:** "
                           + str(_feld(best_trade, "symbol", "coin", default="?"))
                           + " " + format(_pnl(best_trade) or 0.0, "+.2f") + "$"
                           + " | **Schlechtester:** "
                           + str(_feld(worst_trade, "symbol", "coin", default="?"))
                           + " " + format(_pnl(worst_trade) or 0.0, "+.2f") + "$\n\n")
            for sid, count in top_strats:
                report += f"- {sid}: {count} Trades\n"

            if self.todos_added:
                report += "\n### Neue TODOs vom User\n"
                for t in self.todos_added:
                    report += f"- [ ] {t['text']}\n"

            if self.completed_today:
                report += "\n### Heute erledigt\n"
                for t in self.completed_today:
                    report += f"- [x] {t['text']}\n"

            if self.bugs_today:
                report += "\n### Bugs heute\n"
                for b in self.bugs_today:
                    report += f"- {b['text']}\n"

            if error_count > 0:
                report += f"\n### Letzte 5 Errors\n"
                for e in list(self.daily_buffer["errors"])[-5:]:
                    report += f"- [{e['module']}] {e['error'][:100]}\n"

            report += "\n---\n"

            with self._lock:
                # Append kann die Datei nicht nullen; fsync sorgt dafuer, dass
                # der Bericht einen Stromausfall direkt danach uebersteht.
                self._rotate_backups(self.handbook_path)
                with open(self.handbook_path, "a", encoding="utf-8") as f:
                    f.write(report)
                    f.flush()
                    os.fsync(f.fileno())

            # === DOC-V3: Sensei-Auto-Lektion (taeglich, fuettert Lektions-DB) ===
            try:
                self._auto_sensei_lesson(today)
            except Exception as _se:
                log.warn("DOC", "Sensei-Auto-Lektion fehlgeschlagen: " + str(_se)[:80])

            log.info("DOC", f"Tagesbericht geschrieben: {trade_count} Trades, "
                            f"Win-Rate {win_rate:.0f}%, P&L {total_pnl:+.2f}$, {error_count} Errors")

            # === DOC-V2: Buffer NUR bei Tageswechsel leeren ===
            # (Frueher wurde bei jedem Aufruf geleert -> jeder Neustart loeschte die Tagesstatistik)
            if self.buffer_date != today:
                self.daily_buffer["trades"].clear()
                self.daily_buffer["errors"].clear()
                self.daily_buffer["strategy_changes"].clear()
                self.todos_added.clear()
                self.completed_today.clear()
                self.bugs_today.clear()
                self.buffer_date = today
                self._persist()
            self.last_daily_report = today
            self._persist()  # DOC-DEDUPE

        except Exception as e:
            # [E10-DOC 29.07.] Mit Ort statt nur Meldung. Vorher stand im Log
            # nur "Daily-Report Fehler: 'symbol'" - ein nackter KeyError ohne
            # Zeile. Genau deshalb blieb der Defekt wochenlang unbemerkt.
            import traceback
            _tb = traceback.extract_tb(e.__traceback__)
            _ort = f"{_tb[-1].filename.split(chr(92))[-1]}:{_tb[-1].lineno}" if _tb else "?"
            log.warn("DOC", f"Daily-Report Fehler: {type(e).__name__}: {str(e)[:60]} "
                            f"@ {_ort}")

    def get_status(self) -> Dict:
        return {
            "handbook_path": self.handbook_path,
            "trades_today": len(self.daily_buffer["trades"]),
            "errors_today": len(self.daily_buffer["errors"]),
            "todos_today": len(self.todos_added),
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
        }
