# ARCHITEKTUR — Trading Imperium V6

**Stand: 16.07.2026 · v0.1 (Ordner-Ebene) · lebendes Dokument**
*Pflege-Regel: Jeder Installer vermerkt seine Änderung hier oder im
ENTWICKLERHANDBUCH. Großer Aktualisierungs-Durchlauf vor Live-Gang.*
*Basis: INVENTAR.md vom 16.07. (413 Dateien, 112 KERN-Module).*

---

## Der Bot in einem Absatz

`app.py` (2.475 Zeilen, das schrumpfende Herz — Monolith-Split 3/6) startet
Scheduler, WebSocket-Preisfeed, Agenten und GUI. Signale entstehen im
Zusammenspiel aus Strategie-Gehirn (`strategy_brain`), Regime-/Zyklus-
Erkennung und Indikatoren; Käufe laufen über die Execution-Schicht (Paper),
Exits ausschließlich über den **Exit-Monitor** (`runtime/exit_monitor.py`
— seit Exit-Einheit 14.07. die EINE Autorität, mit Notaus-Netz im
signal_agent als Rückfallebene). Jede Bewegung landet im Journal
(`data_store/trades_v5.json` = Wahrheit), dokumentiert vom DocAgent.

## Ordner-Übersicht

| Ordner | Zweck | Zustand |
|---|---|---|
| **(Root)** | `app.py` + Installer/Werkzeuge + `cockpit_server.py` (siehe unten) | Kern; Werkzeuge rotieren via cleanup.py |
| **core/** | Fundament: `logger` (Rotation seit 16.07.), `state_store` (⚠️ enthält das ECHTE TradeJournal!), `settings`, `scheduler`, `events`/`bus`, Balance-Reporter | stabil |
| **agents/** | Handelnde Einheiten: `signal_agent` (Kauf-Signale + Notaus-Netz + RSI-Exit), `context_agent`, `vwap_agent`, Arbitrage/Grid (inaktiv) | Kern |
| **runtime/** | Aus dem Monolith befreite Laufzeit-Teile: `reporting`, `state_manager` (Auto-Save/Restore), `exit_monitor` (Stops/Stufen-Trailing/E6-B, E7-Ziel) | wächst mit Split 4–6 |
| **risk/** | `coin_stops` (EINE Wahrheit für Per-Coin-Stops), `regime_profiles` (Phasen-Anpassung), `exposure`, `manager` (Daily-Loss-Logik, inaktiv), `position_sizing` (⚠️ verwaist — NICHT direkt verdrahten, E8-Plan beachten) | Kern + Baustellen |
| **execution/** | `engine` (Paper-Fills, Phantom-Sell-Fix), `order_manager`, `multi_exchange` (Binance+Bybit), `idempotency`, `retry_policy` | Kern; `exchange_client.py` als verwaist gemeldet → PRÜFEN vor Anfassen (dynamische Imports möglich!) |
| **data/** | Marktdaten: `market_data`, `websocket_stream` (Pricefeed-Fix), `sentiment_data` (F&G), `funding_rates`, `orderbook_depth`, `dxy_monitor`, `whale_alerts` | Kern; einige 70-Tage-Leichen (news_data, cache, dxy_filter, top_coins) |
| **features/** | Analyse-Hirn: `indicators`, `regime_detection` (TRENDING_UP etc.), `market_regime`/`cycle` (Zyklus), `phase_memory`, `situation_memory`/`sensei` (Lern-Schicht), `doc_agent` (Handbuch, Tagesbericht-Fix 16.07.), `impact_journal` | Kern |
| **models/** | ML: `xgboost_model` (aktiv), `train_pipeline`, `rl_feedback`; `regime_model`/`model_registry` verwaist | teilaktiv |
| **strategies/** (via strategy_brain) | `v4_strategies`, `dca_advanced`, `smart_entry`, `cycle_theory` — DCA_FEAR_GREED ist das Arbeitspferd | Kern |
| **ui/** | `main_window` (3.072 Zeilen — nächster Split-Kandidat), `terminal_tab` (v2+Scrollfix), `chart_view`, `dashboard` | funktional, Redesign geplant |
| **metals/** | Gold/Silber-Seitenprojekt, eigenes Journal, Stufe-2/3-Installer warten auf Deploy | getrennt vom Bot |
| **reports/** | ⚠️ `trade_journal.py` = das FALSCHE Journal (monatelang wirkungslos gepatcht) — Archiv-Kandidat; daily/weekly_report verwaist (DocAgent übernahm) | großteils tot |
| **backtest/** | `engine`, `walk_forward` (hat E5 gekillt), `monte_carlo`, `metrics`, `fees`/`slippage` | Analyse-Werkzeuge |
| **live/** | `live_runner`, `paper_runner`, `watchdog`/`auto_restart` (pre-live Pflicht!), `state_recovery`, `shadow_mode` | teils vorbereitet |
| **portfolio/**, **scripts/**, **tests/**, **config/** | Rebalancer/Hilfen/Tests/Configs | Rand |
| **data_store/** | DIE Daten: `trades_v5.json` (Wahrheit), `order_history`, `bot_state`, `config.json` (nur bei geschlossenem Bot patchen!), Kerzen-Cache, Modelle, `system.log` (rotiert jetzt) | Herzkammer — nie manuell löschen |

## Analyse-Cockpit — `cockpit_server.py` (Hauptordner)  `[COCKPIT-KEEP]`

*Ergänzt 27.07.2026, verifiziert gegen die Datei (Stand 26.07. 21:43, 21 KB).*

Lokales Auswertungs-Cockpit im Browser. **Fasst den Bot mit keiner Zeile an** —
reine Anzeige, E7-konform.

- **Liest (nur lesend):** `data_store/trades_v5.json` und
  `data_store/equity_history.json`. Kein einziger Schreibzugriff in der Datei;
  beide `open()`-Aufrufe sind Lesemodus. Findet die Dateien über `_find()`
  robust, egal ob das Skript im Hauptordner oder in `data_store/` liegt.
- **Isoliert:** bindet auf `127.0.0.1:8110` (nur dieser Rechner, kein
  Netzzugriff). Nur Python-Standardbibliothek — nichts zu installieren.
  Kein Import aus dem Bot, keine gemeinsame Laufzeit. Läuft als eigener
  Prozess, unabhängig davon ob der Bot läuft.
- **Aktualisierung:** die Seite lädt sich alle 60 s neu (`meta refresh`);
  bei jedem Aufruf werden die JSON-Dateien frisch gelesen.
- **Robust gegen halb geschriebene JSON:** bei `JSONDecodeError` bleibt der
  letzte gute Stand stehen (`_last_good`) und ein Warnbanner erscheint —
  statt einer leeren oder falschen Auswertung.
- **Berechnet selbst** (nichts aus Reports übernommen): R/R, Win-Rate,
  95%-Konfidenzintervall nach Wilson, Netto-PnL gesamt sowie je Fenster
  E6.1 (ab 14.07.) und E7 (ab 17.07.), Saldo je Coin und je Ausstiegsgrund,
  Averaging-Down-Buckets (1 / 2 / 3+ Käufe pro Position), Gebühren-Analyse,
  MFE/MAE inkl. Give-Back, Equity-Sparkline.
- **Nutzt bewusst NICHT `brain_performance.json`** — die ist
  V4-Bootstrap-verseucht (`source: v4_bootstrap`, `v6_trades_added: 0`).
  Das Cockpit blendet Strategie-Performance deshalb komplett aus und
  erklärt den Grund im UI. Nur V6-Daten.
- **`/health`** liefert `ok` (für Watchdog/Uptime-Check später brauchbar).
- Start: `python cockpit_server.py` → `http://localhost:8110`, Stopp mit Strg+C.
  Handbuch: `COCKPIT_HANDBUCH.md`.

**Marker `[COCKPIT-KEEP]`** steht im Datei-Kopf (Zeile 3 und 16) und bedeutet:
diese Datei ist ein Dauer-Werkzeug, kein erledigter Installer — `cleanup.py`
darf sie nicht archivieren.

> ⚠️ **Der Marker ist derzeit nur eine Konvention, keine Durchsetzung.**
> `cleanup.py` (v4) liest keine Dateiinhalte; der Schutz läuft ausschließlich
> über Dateinamen-Muster und die Menge `KEEP_FILES`. `cockpit_server.py` steht
> **nicht** in `KEEP_FILES`, trifft aber auch **kein** `ARCHIVE_PATTERNS`-Muster
> und landet deshalb bei jedem Lauf in der Liste „UNBEKANNT — wird NICHT
> angefasst". Faktisch sicher, aber nur zufällig. Sauber wäre, `cockpit_server.py`
> in `KEEP_FILES` aufzunehmen (`cleanup.py:59-65`) oder cleanup.py den Marker
> lesen zu lassen. Noch offen.

## Müll-Aktionsplan (aus INVENTAR 16.07.)

**⛔ NIEMALS anfassen:** alle `__init__.py` (die Inventur meldet sie als
"verwaist/Duplikat", aber sie SIND die Paket-Marker — ohne sie importiert
nichts mehr; Klassifizierer-Blindstelle, hiermit dokumentiert).
Ebenso `cockpit_server.py` — Dauer-Werkzeug, Marker `[COCKPIT-KEEP]`
(siehe Abschnitt oben; Schutz noch nicht in cleanup.py verdrahtet).

**Sofort erledigt:** system.log-Rotation + Kürzung (460 MB → ~5 MB). ✓

**Archiv-Kandidaten (cleanup.py-Regeln erweitern, nie löschen):**
`*_backup_*.py`-Handkopien (main_window/doc_agent), `balance_reporter(12).py`,
`_terminal_tab_payload*.py` nach Install, `.bak_*` auch in Unterordnern,
Duplikate in data_store/ (Installer-Kopie, docx-Kopie), Zufalls-Müll
`features/cd|dir|python`, XGB-Modelle älter als die 2 neuesten.

**PRÜFEN vor Archivierung (könnten dynamisch importiert werden):**
`execution/exchange_client.py`, `data/cache.py`, `data/data_quality.py`,
`reports/trade_journal.py` (das falsche Journal), `analyse_readiness.py`.
→ Verifikation per String-Import-Suche in der nächsten Session.

**DATEN-ALT (75 Dateien, >30 Tage):** Liste liegt in INVENTAR.md;
Einzeldurchsicht bei der nächsten Aufräum-Session.

## Offene Baustellen (Verweis)

E6.1 läuft → E7 (19.07.) → E8 Sizing → Split 4–6 → Daily-Loss-Neubau →
Watchdog/Uptime → MiCA/Börse → R/R>1-Beweis → Live. Details: tickets.txt,
SIZING_BAUPLAN_E8.md, SPLIT_BAUPLAN.md, userMemories des Sensei.

## Changelog dieses Dokuments

- 27.07.2026 v0.2: Abschnitt „Analyse-Cockpit (`cockpit_server.py`)" ergänzt
  (read-only, 127.0.0.1:8110, liest trades_v5 + equity_history, `[COCKPIT-KEEP]`).
  Gegen die tatsächliche Datei verifiziert, nicht aus Notizen. Dabei aufgefallen:
  cleanup.py wertet den Marker nicht aus — dokumentiert, noch nicht behoben.
- 16.07.2026 v0.1: Erstfassung Ordner-Ebene (Basis INVENTAR.md).
  Nächste Ausbaustufe: KERN-Dateien im Detail (Zweck/Abhängigkeiten/Aufrufer),
  Etappe 1 = core/ + runtime/ + risk/.
