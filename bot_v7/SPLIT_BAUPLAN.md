# MONOLITH-SPLIT BAUPLAN — app.py (2.891 Zeilen → 6 Module + Rumpf)

Erstellt: 05.07.2026 | Basis: app.py Stand 04.07. (nach Journal-Fix A/B/C)
Status: PLAN — Umsetzung erst nach E4-Auswertung (eiserne Regel).
Ausnahme: Schritt 1 (Reporting) ist reine Observability und darf als
Generalprobe mid-epoch laufen.

---

## 1. IST-ZUSTAND (Funktionsinventar mit Zeilen, Stand 04.07.)

| Cluster | Methoden | Zeilen | Risiko |
|---|---|---|---|
| Init & Wiring | __init__, _setup_event_wiring, _setup_tasks | 137–515 | hoch (bleibt!) |
| Marktdaten→Signal | _on_market_update, _on_signal, _on_risk_approved | 516–731 | GELD |
| Ausführung | _execute_approved_trade (inkl. Impact-Hook), _record_twap_fill, _on_order_filled | 732–1107 | GELD |
| Not-Aus | _on_kill_switch, _on_error, _close_all_positions_safety | 1108–1155 | GELD |
| Exit-Monitor | _sl_tp_monitor, _fetch_current_price | 1156–1410 | GELD |
| V4-Sync | _v4_auto_sync | 1411–1616 | mittel |
| Signal-Tick | _trading_tick (338 Z!), _news_tick, _update_external_signals | 1617–2007 | GELD |
| ML/Wartung | _check_retrain, _cache_clear_with_export, _check_latency, _shadow_compare, _auto_optimize | 2008–2104 | niedrig |
| Reporting | generate_analyse_export, _daily_report, _weekly_report, _heartbeat | 2105–2190 | NULL |
| State | _auto_save, _restore_positions | 2191–2402 | hoch |
| Diagnose/Health | _run_startup_diagnostic, _start_heartbeat_pulse, _health_check, _reconcile | 2403–2616 | niedrig |
| Lifecycle | start, stop, _shutdown_handler, run_forever, get_system_status | 2617–2891 | hoch (bleibt!) |

## 2. ZIEL-ARCHITEKTUR

Neues Paket `runtime/` (Delegaten-Muster, KEINE Mixins):

```
runtime/
  __init__.py
  reporting.py       <- Schritt 1  (Reporting-Cluster + ML/Wartung-Kleinkram)
  state_manager.py   <- Schritt 2  (_auto_save, _restore_positions)
  exit_monitor.py    <- Schritt 3  (_sl_tp_monitor, _fetch_current_price,
                                    _close_all_positions_safety)
  execution_path.py  <- Schritt 4  (_execute_approved_trade, _record_twap_fill,
                                    _on_order_filled)
  signal_engine.py   <- Schritt 5  (_trading_tick, _on_market_update,
                                    _update_external_signals, _news_tick)
  v4_sync.py         <- Schritt 6  (_v4_auto_sync + Diagnose-Umzug optional)
```

app.py behält: __init__, Wiring, Tasks, Lifecycle, Not-Aus-Handler.
Zielgröße Rumpf: ~600 Zeilen.

**Muster (für jeden Schritt identisch):**
```python
# runtime/exit_monitor.py
class ExitMonitor:
    def __init__(self, app):
        self.app = app          # Zugriff auf risk_engine, execution, journal...
    def tick(self):
        ...  # Code 1:1 aus _sl_tp_monitor, self.X -> self.app.X

# app.py (Rumpf) — Scheduler/Wiring bleiben UNVERÄNDERT:
self.exit_monitor = ExitMonitor(self)
def _sl_tp_monitor(self):
    return self.exit_monitor.tick()   # dünner Weiterleiter
```

## 3. EISERNE UMZUGSREGELN

1. **Wortwörtlich umziehen** — beim Umzug wird KEINE Logik verbessert,
   egal wie verlockend. Verbesserungen = eigene Tickets danach.
2. Ein Schritt pro Sitzung. Vorher Vollkopie des Ordners
   (`xcopy ... V6_vor_split_N /E /I`).
3. Nach jedem Schritt: AST-Check, Bot-Start, Startup-Diagnostic grün,
   10 Min. Log beobachten (Tick läuft, Journal schreibt, Telegram lebt).
4. `self.` → `self.app.` per Suchen/Ersetzen NUR im umgezogenen Block.
5. Marker-Kommentare der Fixes (SIT-MEM, DOC-DEDUPE, FIX 1–8) ziehen MIT um —
   sie sind die Landkarte der Bugfix-Geschichte.
6. CRLF beibehalten (app.py ist CRLF; neue runtime/-Dateien ebenfalls CRLF).
7. Schritte 3–5 (Geldpfad) NUR nach E4-Auswertung und nie zwei in einer Woche.

## 4. BEKANNTE FALLEN (beim Inventar gefunden)

- `_ij_context`-Block (Impact-Hook, ~Z. 985) und Monitor-log_sell-Block
  (~Z. 1290) sind frisch gepatcht — beim Umzug von Schritt 3/4 exakt
  mitnehmen, Anker der Installer stimmen danach nicht mehr (egal,
  Installer sind verbraucht).
- Z. 561: toter Code `self.market_data.snapshots` (Attribut existiert
  nicht) — beim Umzug von Schritt 5 ERSATZLOS streichen (einzige
  erlaubte "Änderung", ist nachweislich toter Zweig).
- `hyperopt.py`: ungesicherter `import optuna` — beim Schritt-1-Umzug
  in try/except packen (Observability, Ticket erledigt sich mit).
- `_sl_tp_monitor` läuft im Scheduler-Thread, `_trading_tick` ebenfalls:
  Delegaten dürfen KEINEN eigenen Zustand puffern, der zwischen Threads
  geteilt wird — alles bleibt an self.app hängen.
- `_restore_positions` läuft VOR dem ersten Tick — Reihenfolge in
  start() darf sich durch den Umzug nicht ändern.

## 5. ABNAHME-CHECKLISTE (nach jedem Schritt)

[ ] python -c "import ast; ast.parse(open('app.py').read())" (+ runtime/*)
[ ] Bot-Start ohne Traceback, Startup-Diagnostic: alle Tests grün
[ ] 1 vollständiger Trading-Tick im Log
[ ] Impact-Journal: neuer Eintrag mit RSI/ADX != 0
[ ] Telegram /status antwortet
[ ] Wächter-Lauf ohne Invarianten-Fehler
[ ] Positionen nach Neustart korrekt restauriert (Anzahl vorher=nachher)

## 6. REIHENFOLGE & FREIGABEN

| Schritt | Modul | Freigabe |
|---|---|---|
| 1 | reporting.py | SOFORT möglich (Observability) |
| 2 | state_manager.py | nach Schritt 1 stabil (1 Woche Betrieb) |
| 3 | exit_monitor.py | NACH E4-Auswertung |
| 4 | execution_path.py | nach Schritt 3 stabil |
| 5 | signal_engine.py | nach Schritt 4 stabil |
| 6 | v4_sync.py + Rest | beliebig danach |

Geschätzte Dauer: 6 Sitzungen à 1–2 h. Kein Zeitdruck — Stabilität schlägt Tempo.
