# ÜBERGABE AN CLAUDE-CHAT — Stand 28.07.2026, 23:20

`[CLEANUP-KEEP]` — diese Datei nie archivieren.

Erstellt von Claude Code. Alle Zahlen in TEIL 3 sind frisch verifiziert
(nicht aus Notizen). Paper-Trading, kein echtes Geld.

---

## TEIL 1 — Änderungen in dieser Session

### 1.1 Von MIR heute geändert

| Datei | Was | Warum |
|---|---|---|
| `features/doc_agent.py` | Atomarer Schreibvorgang + 3er-Backup-Rotation | Ursache der Handbuch-Korruption beseitigt |
| `tickets.txt` | 2 Zeilen angehängt (BUG + SPEICHERN) | Auftrag TEIL 4a — vom Bot um 23:06 verarbeitet |
| `ENTWICKLERHANDBUCH_KORRUPT_28072026.md` | **neu** (reine Kopie, 201.356 B) | Beweissicherung des korrupten Standes |
| `UEBERGABE-AN-CHAT_28072026.md` | **neu** | dieses Dokument |

**`doc_agent.py` im Detail**

Neue Methode `_atomic_write(path, data)`: Temp-Datei im Zielverzeichnis →
`flush()` → `os.fsync()` → `os.replace()`. `os.replace` ist auf einem
Dateisystem atomar — es gibt keinen Zwischenzustand mehr. Stirbt der Prozess
mitten im Schreiben, bleibt die alte Datei unversehrt; übrig bleibt nur eine
verwaiste `.tmp`.

Umgestellt wurden **drei** Schreibstellen (gemeldet war nur die erste):

| Stelle | vorher | Risiko |
|---|---|---|
| `_append_to_handbook` (ehem. Z. 98) | `open(...,"w")` auf die Live-Datei | **die Korruptionsquelle** |
| `_init_handbook` | `open(...,"w")` | identischer Fehler |
| `_persist` → `doc_agent_state.json` | `open(...,"w")` | Tagespuffer zerreißbar |

`write_daily_report` nutzt Append-Mode (kann keine Nullbytes erzeugen) — dort
nur `flush`+`fsync` für Durability ergänzt.

`_rotate_backups()`: rollierendes Backup `.bak1` (jüngster) bis `.bak3`
(ältester), gedrosselt auf max. alle 5 Minuten (sonst 200 KB Kopie pro
Trade-Event).

> **Bewusste Design-Entscheidung:** Die Rotation **überspringt Dateien mit
> Nullbytes**. Sonst hätte der erste Schreibvorgang den korrupten Stand über
> alle drei Backup-Slots geschoben und den Schaden zementiert. Folge:
> **Solange das Handbuch korrupt ist, entstehen keine Backups** — stattdessen
> einmalig eine Warnung im Log. Beabsichtigt, kein Fehler.

Keine Auto-Reparatur — die Entscheidung über den Nullblock ist offen.

**Test:** 20/20 bestanden, komplett in einer Sandbox (echtes Handbuch nicht
berührt): atomarer Write, Temp-Hygiene, 3-Stände-Rotation, Korruptions-Schutz,
Ende-zu-Ende über `on_start`/`on_trade`, Idempotenz.

**In Produktion bestätigt:** Bot lief 19:41:41 neu an und lud den Patch.
Schreibvorgang 19:42:02 → keine `.tmp`-Reste, keine Backup-Rotation (Schutz
greift), Nullbyte-Zahl unverändert. Um 23:06 verarbeitete der TicketsWatcher
meine zwei Tickets — ebenfalls sauber.

### 1.2 Angelegte Backups

| Backup | Ort |
|---|---|
| `doc_agent.py.bak_atomicwrite_20260728_165827` (21.382 B) | `features/` — bewusst **nicht** in Quarantäne |
| `ENTWICKLERHANDBUCH_KORRUPT_28072026.md` (201.356 B) | Hauptordner |
| Projekt-Vollkopie, 928 Dateien / 174,78 MB, 0 Fehler | `Desktop\_staging_backup_20260727\` (robocopy) |

Ein ZIP wurde **nicht** erstellt — mehrere Versuche scheiterten an gesperrten
Log-Dateien des laufenden Bots. Die robocopy-Vollkopie ersetzt es gleichwertig.

### 1.3 Aufräumen (`aufraeumen.ps1`)

Zwei Läufe, beide abgeschlossen: 27.07. 03:54 (139 Objekte, 140,6 MB) und
28.07. 17:14 (19 Objekte, 20,1 MB). **Verschoben, nichts gelöscht.**
Vollprotokoll mit jedem Pfad:
`Desktop\_AUFRAEUMEN_20260727\_VERSCHOBEN_LOG.txt`.

| Quarantäne-Ordner | Dateien | Größe | Inhalt |
|---|---:|---:|---|
| `01_altes_archiv` | 357 | 115,5 MB | verschachteltes Archiv-in-Archiv, 3 Ebenen |
| `02_data_store_backups` | 68 | 23 MB | Reset-/Crash-Stände + `system.log.1` |
| `08_pycache` | 253 | 3,1 MB | alle 16 `__pycache__`-Ordner |
| `03_quellcode_backups` | 26 | 888 KB | verstreute `.bak` + `app.py.bak_chartref` |
| `07_duplikate` | 2 | 328 KB | doppelte Produktbeschreibung, `SIZING_BAUPLAN_E8(1).md` |
| `04_patch_skripte` | 22 | 180 KB | ausgeführte Einmal-Patches + Payloads |
| `05_auto_exports` | 6 | 52 KB | alte Auto-Exports |
| `06_scratch` | 10 | 43 KB | Debug-Reste (`out.txt`, `check_a.txt` …) |

Vor dem Verschieben der Patch-Skripte geprüft: keines wird irgendwo importiert.

> ⚠️ **NACHTRAG — Teile sind wieder da.** Bei der Verifikation (28.07., 22:40)
> fand ich im Projekt erneut: `_archive_20260716_065427/` (303 Dateien,
> 113,6 MB — eine **andere** Kopie als die in Quarantäne mit 357 Dateien),
> sowie in `data_store/` wieder `system.log.1`, fünf `v4sync_backup`-Dateien,
> beide `sizing_backup`, `data_store_inhalt.txt` und die doppelte `.docx`.
> Herkunft ungeklärt. **Ich habe nichts erneut verschoben** — es könnte die
> aktive Arbeit einer anderen Session sein.

### 1.4 NICHT von mir — aus anderen Sessions vorgefunden

Diese Dateien standen im Auftrag, wurden von mir aber **nicht** angefasst:

| Datei | Größe | Stand |
|---|---:|---|
| `ARCHITEKTUR.md` | 8.760 B | 27.07. 17:23 |
| `cleanup.py` (Marker-Schutz v1) | 12.907 B | 27.07. 17:55 |
| `AUSWERTUNG-HANDBUCH.md` | 22.593 B | 28.07. 01:05 |
| `DUST-OFFENE-FRAGEN.md` | 7.853 B | 27.07. 17:20 |
| `uebergabe-dust/` (`dust_manager.py`, `LOGIK.md`, `README.md`) | 83 KB | 27.07. 08:32 |

---

## TEIL 2 — Was der Bot ist und kann

### 2.0 Überblick

Trading Imperium V6 ist ein **ereignisgesteuerter Krypto-Handelsbot** im
Paper-Betrieb (Binance-Symbole gegen USDC). Ein Event-Bus (`core/bus.py`)
verteilt typisierte Ereignisse (`core/events.py`: `MarketSnapshot`,
`DecisionIntent`, `ExecutionResult`) über vier Stufen:

```
DATEN   →   ENTSCHEIDUNG   →   VETO   →   AUSFÜHRUNG
data/       agents/            risk/      execution/
            models/            portfolio/
```

Jede Kaufabsicht durchläuft zwingend die Veto-Instanz (`risk/engine.py`),
bevor ausgeführt wird. Darüber liegen Beobachtungs- und Lernschichten
(`features/`, `reports/`, `ui/`).

**Fähigkeiten im Überblick**

| Fähigkeit | Umgesetzt in |
|---|---|
| Multi-Coin-Spothandel mit Signalgenerierung | `agents/signal_agent.py`, `agents/strategy_brain.py` |
| Regime-Erkennung (Bulle/Bär/Seitwärts) + Anpassung | `features/market_regime.py`, `features/regime_detection.py`, `risk/regime_profiles.py` |
| Bitcoin-Zyklusphasen als Kontext | `agents/cycle_theory.py`, `ui/zyklus_tab.py` |
| ML-Signale (XGBoost, Ensemble, Meta-Voting) | `models/` |
| Verstärkungslernen aus eigenen Ergebnissen | `models/rl_feedback.py`, `models/brain_persistence.py` |
| Risikoveto, Kill-Switch, Drawdown-Wächter | `risk/engine.py`, `risk/kill_switch.py`, `risk/drawdown_guard.py` |
| Tagesverlust-Bremse | `portfolio/daily_loss.py` |
| Positionsgrößen prozentual + adaptiv | `portfolio/calculator.py`, `risk/adaptive_sizing.py` |
| Korrelations-Schutz | `portfolio/correlation_guard.py` |
| Exit-Überwachung inkl. **E7-Phasen-Trailing** | `runtime/exit_monitor.py`, `risk/coin_stops.py` |
| Idempotente Ausführung, Retry, Circuit-Breaker | `execution/` |
| Backtesting, Walk-Forward, Monte-Carlo, Hyperopt | `backtest/` |
| Sentiment: Reddit, News, Whale-Alerts, On-Chain | `data/` |
| Makro-Filter: DXY, Funding-Rates, NUPL | `data/dxy_filter.py`, `data/funding_rates.py`, `data/nupl_monitor.py` |
| Selbstdokumentation (dieses Handbuch) | `features/doc_agent.py`, `features/tickets_watcher.py` |
| Lehrer-Modus mit Tageslektionen | `features/sensei.py`, `features/akademie.py` |
| Buchhaltungs-Prüfung gegen Drift | `features/waechter.py` |
| Telegram-Benachrichtigungen | `reports/telegram.py` |
| Desktop-UI: Chart-, Terminal-, Zyklus-, Geldfluss-Tab | `ui/` |
| Edelmetall-Beobachtung | `metals/` |

### 2.1 `core/` — Fundament

| Datei | Z. | Funktion |
|---|---:|---|
| `bus.py` | 99 | Event-Bus — Herzstück der Kommunikation |
| `events.py` | 187 | Typisierte Ereignisse, `MarketRegime`, `CyclePhase` |
| `state_store.py` | 263 | `StateStore` + `TradeJournal` |
| `logger.py` | 112 | Strukturiertes Logging (`system.log`) |
| `scheduler.py` | 112 | Task-Scheduler |
| `health.py` | 216 | Health-Monitor |
| `auto_restart.py` | 94 | Neustart bei Hängern |
| `exceptions.py` | 58 | `RiskVetoError`, `KillSwitchError` u. a. |
| `balance_reporter.py` | 166 | Kontostand-Bericht v4 |
| `balance_reporter(12).py` | 188 | ⚠️ **Duplikat** (v3), Download-Suffix |

### 2.2 `data/` — Marktdaten & Kontext

| Datei | Z. | Funktion |
|---|---:|---|
| `market_data.py` | 132 | `DataAgent` — Kurse + Indikatoren |
| `websocket_stream.py` | 175 | Binance-Live-Preisstrom |
| `cache.py` | 129 | Daten-Cache |
| `data_quality.py` | 157 | Plausibilitätsprüfung |
| `feature_store.py` | 58 | Feature-Ablage |
| `top_coins.py` | 105 | Top-Coin-Auswahl |
| `orderbook_depth.py` | 91 | Orderbuch-Tiefe |
| `funding_rates.py` | 128 | Funding-Raten |
| `dxy_monitor.py` / `dxy_filter.py` | 92 / 99 | Dollar-Index als Makro-Filter |
| `nupl_monitor.py` | 107 | NUPL |
| `onchain_analytics.py` | 144 | On-Chain-Kennzahlen |
| `whale_alerts.py` | 190 | Großtransaktionen |
| `reddit_sentiment.py` | 233 | Reddit-Stimmung |
| `sentiment_data.py` | 113 | Sentiment-Aggregat |
| `news_data.py` | 97 | Nachrichten |
| `capitol_trades.py` | 243 | Trades von US-Politikern |
| `v4_importer.py` | 161 | ⚠️ **V4** |

### 2.3 `agents/` — Entscheider

| Datei | Z. | Funktion |
|---|---:|---|
| `strategy_brain.py` | 358 | **Das Gehirn** — wählt die aktive Strategie |
| `signal_agent.py` | 247 | Erzeugt Kauf-/Verkaufssignale |
| `cycle_theory.py` | 168 | Bitcoin-Zyklusphase |
| `btc_accumulator.py` | 225 | BTC-Daueransammlung |
| `smart_entry.py` | 74 | Einstiegs-Timing |
| `dca_advanced.py` | 81 | Erweiterter Cost-Average |
| `grid_bot.py` / `grid_trader.py` | 185 / 88 | Grid-Handel |
| `arbitrage_agent.py` | 97 | Cross-Exchange-Arbitrage |
| `context_agent.py` | 366 | LLM-Kontext + Nachrichtenanalyse |
| `llm_local.py` | 92 | Lokales LLM (Ollama) |
| `strategy_export.py` | 115 | Strategie-Export |
| `v4_strategies.py` | 348 | ⚠️ **V4** |

### 2.4 `models/` — Lernende Komponenten

| Datei | Z. | Funktion |
|---|---:|---|
| `xgboost_model.py` | 291 | XGBoost-Signalmodell |
| `signal_model.py` | 144 | ML-Signalmodell |
| `regime_model.py` | 145 | Regime-Klassifikation |
| `ensemble_signal.py` | 79 | Signal-Zusammenführung |
| `meta_voting.py` | 147 | Meta-Learning-Abstimmung |
| `rl_feedback.py` | 109 | Verstärkungslernen |
| `brain_persistence.py` | 145 | Gelerntes über Neustarts retten |
| `model_registry.py` | 143 | Modellverwaltung |
| `auto_retrain.py` | 133 | Automatisches Nachtrainieren |
| `train_pipeline.py` | 62 | Trainingsablauf |
| `v4_calibrator.py` | 143 | ⚠️ **V4** |

### 2.5 `risk/` — Veto-Instanz

| Datei | Z. | Funktion |
|---|---:|---|
| `engine.py` | 344 | **Risk-Engine** — kann jede Order blockieren |
| `kill_switch.py` | 67 | Not-Aus |
| `drawdown_guard.py` | 58 | Drawdown-Grenze |
| `exposure.py` | 61 | Gesamtengagement begrenzen |
| `position_sizing.py` | 71 | Positionsgröße |
| `adaptive_sizing.py` | 100 | KI-gestützte Größenanpassung |
| `regime_profiles.py` | 72 | Risiko je Marktregime |
| `coin_stops.py` | 21 | **Zentrale Stop-Tabelle — „EINE Wahrheit für ALLE Exit-Pfade"** |

### 2.6 `portfolio/` — Kapitalverwaltung

| Datei | Z. | Funktion |
|---|---:|---|
| `manager.py` | 487 | **Portfolio-Manager** — zentrale Kapitalverwaltung |
| `calculator.py` | 271 | `PortfolioSnapshot`, `TradeSizing` |
| `agent.py` | 170 | Portfolio-Agent (100 % prozentual) |
| `daily_loss.py` | 212 | Tagesverlust-Wächter (P5, 20.07.) |
| `correlation_guard.py` | 139 | Korrelations-Schutz |
| `rebalancer.py` | 253 | Umschichtung |

### 2.7 `execution/` — Ausführung

| Datei | Z. | Funktion |
|---|---:|---|
| `exchange_client.py` | 396 | Börsenanbindung + Retry + Idempotenz |
| `engine.py` | 305 | Ausführungs-Engine |
| `futures_trader.py` | 180 | Futures/Perpetuals |
| `multi_exchange.py` | 166 | Mehrere Börsen |
| `order_manager.py` | 152 | Orderverwaltung |
| `idempotency.py` | 96 | Doppelausführung verhindern |
| `fill_reconciler.py` | 92 | Ausführungen abgleichen |
| `twap_executor.py` | 89 | Große Orders zeitlich splitten |
| `circuit_breaker.py` | 80 | Bei Fehlerhäufung abschalten |
| `retry_policy.py` | 80 | Wiederholstrategie |

### 2.8 `runtime/` — Laufzeitsteuerung

| Datei | Z. | Funktion |
|---|---:|---|
| `exit_monitor.py` | 318 | **Ausstiegs-Überwachung — hier sitzt das E7-Phasen-Trailing** |
| `state_manager.py` | 249 | Zustandsverwaltung (Split-2) |
| `reporting.py` | 105 | Laufzeit-Berichte (Split-1) |

### 2.9 `features/` — Beobachtung, Lernen, Selbstdoku

| Datei | Z. | Funktion |
|---|---:|---|
| `doc_agent.py` | 577 | **DocAgent** — schreibt `ENTWICKLERHANDBUCH.md` (heute gepatcht) |
| `tickets_watcher.py` | 168 | Beobachtet `tickets.txt`, reicht an DocAgent |
| `sensei.py` | 358 | **Sensei** — Tageslektionen |
| `akademie.py` | 509 | Trading-Akademie |
| `waechter.py` | 124 | **Wächter** — Buchhaltungsprüfer gegen Drift |
| `situation_memory.py` | 324 | Marktsituationen merken |
| `phase_memory.py` | 143 | Phasen-Gedächtnis |
| `impact_journal.py` | 178 | Begründung je Trade |
| `indicators.py` | 80 | ADX, OBV, VWAP, StochRSI, TSI |
| `market_regime.py` / `regime_detection.py` | 54 / 127 | Regime-Erkennung |
| `multi_timeframe.py` | 140 | Signale über mehrere Zeitebenen |
| `rsi_divergence.py` | 151 | RSI-Divergenzen |
| `bottom_detection.py` | 87 | Boden-Erkennung |
| `vwap_agent.py` | 81 | VWAP + Volumenprofil |
| `portfolio_features.py` | 91 | Portfolio-Merkmale |
| `labels.py` | 97 | Trainingslabels |
| `safety.py` | 209 | Cash-Reservierung, Rate-Limit, Ablehnungszähler |
| `chart_data.py` / `chart_view.py` | 201 / 333 | Chart-Bausteine 1 + 2 |
| `chart_refresher.py` | 95 | Chart-Auto-Refresh (21.07.) |
| `stoploss_edge.py` | 174 | Stop-Loss-Kantenanalyse |
| `strategy_lab.py` | 178 | Was-wäre-wenn-Analyse |
| `doc_agent_backup_20260611.py` | 331 | ⚠️ **Alte DocAgent-Kopie** — als `.py` nicht in Quarantäne gewandert |

### 2.10 `backtest/` — Prüfstand

`engine.py` (380) · `metrics.py` (144) · `hyperopt.py` (137) ·
`monte_carlo.py` (131) · `walk_forward.py` (130) · `optimizer.py` (119) ·
`slippage.py` (57) · `fees.py` (50)

### 2.11 `live/`, `reports/`, `config/`, `ui/`, `metals/`, `scripts/`

| Datei | Z. | Funktion |
|---|---:|---|
| `live/paper_runner.py` | 87 | **Paper-Betrieb — das läuft aktuell** |
| `live/live_runner.py` | 82 | Echtgeld-Betrieb (inaktiv) |
| `live/shadow_mode.py` | 159 | Schatten-Trades ohne Ausführung |
| `live/state_recovery.py` | 52 | Zustand nach Absturz herstellen |
| `live/watchdog.py` | 36 | Überwachung |
| `reports/telegram.py` | 566 | Telegram-Benachrichtigungen |
| `reports/trade_journal.py` | 261 | Trade-Journal |
| `reports/equity_tracker.py` | 90 | Equity-Verlauf |
| `reports/daily_report.py` / `weekly_report.py` | 70 / 75 | Tages-/Wochenbericht |
| `config/settings.py` | 368 | **Zentrale Konfiguration** — Exchange, Risiko, Modi, KI, Telegram |
| `config/versioning.py` | 68 | Config-Versionierung |
| `ui/main_window.py` | **3.103** | Hauptfenster — größte Einzeldatei |
| `ui/terminal_tab.py` | 426 | Terminal-Cockpit + Epochen-Steuerung |
| `ui/geldfluss_tab.py` | 267 | Intermarket-Beobachtung (20.07.) |
| `ui/dashboard.py` | 265 | Flask-Web-Dashboard |
| `ui/zyklus_tab.py` | 204 | Bitcoin-Zyklus-Atlas (19.07.) |
| `ui/webhook_server.py` | 164 | TradingView-Webhooks |
| `ui/ngrok_dashboard.py` | 138 | Öffentliches Dashboard über ngrok |
| `ui/main_window_backup_20260610.py` | **2.640** | ⚠️ **Alte UI-Kopie** — als `.py` nicht in Quarantäne |
| `metals/metals_engine.py` | 475 | Metall-Analyse (RSI, ATR, MACD, Bollinger) |
| `metals/metals_tab.py` | 342 | Metall-Oberfläche |
| `metals/metals_store.py` | 109 | Metall-Zustand |
| `scripts/full_reset*.py` | 202–236 | **3 Versionen** desselben Skripts — v3 ist aktuell |
| `scripts/reset_paper.py` | 82 | Paper-Zustand zurücksetzen |
| `scripts/migrate_v4_to_v6.py` | 145 | ⚠️ **V4** |

### 2.12 Analyse-Werkzeuge im Hauptordner

| Datei | Funktion |
|---|---|
| `e7_auswertung.py` | **E7-Bewertung** — R/R, Kriterien K1/K2/K4 |
| `e7_gegenprobe.py` | E7 gegen die alte Trailing-Leiter |
| `e5_walkforward.py`, `e4_eval.py` | Walk-Forward, E4-Bewertung |
| `pnl_check.py`, `impact_report.py` | P&L- und Impact-Auswertung |
| `status.py`, `diagnose.py`, `voll_diagnose.py` | Systemzustand |
| `cockpit_server.py` | Analyse-Cockpit |
| `cleanup.py` | Aufräumskript mit Marker-Schutz (`[COCKPIT-KEEP]`, `[CLEANUP-KEEP]`); schützt **alle** `.md` und `.pdf` hart |
| `analyse_readiness.py`, `preflight.py` | Startbereitschaft |
| `situation_replay.py`, `macro_replay.py` | Situationen nachspielen |
| `history_harvester.py`, `backfill_impact_journal.py` | Historie nachziehen |
| `sensei`-nahe: `brain_view.py`, `epoch_report.py`, `epochs.py` | Gehirn-/Epochen-Sicht |

### 2.13 Ordnerbaum

```
trading_imperium_v6(21)/
├── core/          Fundament: Bus, Events, State, Logger, Health
├── data/          Marktdaten, Sentiment, Makro-Filter
├── agents/        Entscheider: Brain, Signale, Zyklus, Grid, DCA
├── models/        ML: XGBoost, Ensemble, Meta-Voting, RL
├── risk/          Veto: Engine, Kill-Switch, Stops, Sizing
├── portfolio/     Kapital: Manager, Daily-Loss, Korrelation
├── execution/     Ausführung: Börse, Orders, Idempotenz
├── runtime/       Exit-Monitor (E7), State-Manager
├── features/      DocAgent, Sensei, Wächter, Indikatoren, Charts
├── backtest/      Engine, Walk-Forward, Monte-Carlo
├── live/          Paper-/Live-Runner, Shadow, Watchdog
├── reports/       Telegram, Journal, Tages-/Wochenbericht
├── ui/            Hauptfenster + Tabs
├── metals/        Edelmetall-Modul
├── config/        settings.py, versioning.py
├── scripts/       Reset & Migration
├── tests/         8 Unit-Tests
├── data_store/    ► LAUFZEITDATEN
├── v4_data/       ► NUR V4
├── uebergabe-dust/  Dust-Manager (andere Session)
└── _archive_20260716_065427/  ⚠️ siehe 1.3
```

### 2.14 Aktive Laufzeitdateien (`data_store/`)

| Datei | Funktion |
|---|---|
| `bot_state.json` | Bot-Zustand, offene Positionen, Balances |
| `trades_v5.json` | Trade-Journal V6 — **maßgeblich für Auswertungen** |
| `order_history.json` | Orderhistorie inkl. abgelehnter Orders |
| `equity_history.json` | Equity-Kurve |
| `impact_journal.json` | Impact-Journal je Entscheidung |
| `situation_history.json` | Marktsituationen (1,3 MB) |
| `sensei_lessons.json` | Lektions-Datenbank |
| `daily_loss_state.json` / `daily_loss_schatten.json` | Tagesverlust-Zähler |
| `doc_agent_state.json` | Tagespuffer des DocAgent |
| `brain_performance.json` | Strategie-Performance |
| `rl_weights.json` | RL-Gewichte |
| `btc_accumulator.json` | BTC-Ansammlung |
| `geldfluss_history.json` | Geldfluss-Verlauf |
| `rebalancer_state.json` | Rebalancer-Zustand |
| `idempotency_keys.json` | Idempotenz-Schlüssel |
| `akademie_fortschritt.json` | Lernfortschritt |
| `telegram_alerts.json` | Versendete Alerts |
| `system.log` | Laufendes Systemlog (20 MB) |
| `models/`, `charts/` | Modelle, Chartbilder |

### 2.15 Dokumentation

`ARCHITEKTUR.md` · `AUSWERTUNG-HANDBUCH.md` (R/R-Definitionen) ·
`DUST-OFFENE-FRAGEN.md` · `ENTWICKLERHANDBUCH.md` (⚠️ korrupt) ·
`SENSEI_LEKTIONEN.md` · `INVENTAR.md` · `BEFEHLE_REFERENZ.md` ·
`UEBERGABE-CLAUDE-CODE.md` · `HANDBUCH.md` · `ANLEITUNG.md` ·
`LIVE_TRADING.md` · `SPLIT_BAUPLAN.md` · `DAILY_LOSS_BAUPLAN_P5.md` ·
`Trading_Imperium_V6_Handbuch.pdf`

### 2.16 ⚠️ V4-Daten — NICHT für V6-Auswertung verwenden

```
v4_data/                              alle 5 Dateien
data_store/v4_imported_equity.json
data_store/v4_imported_trades.json
data_store/v4_imported_state.json
data_store/v4_strategy_weights.json
data_store/brain_performance.json.v4sync_backup_*   (5 Stück)
config_v4_sync.json  ·  v4_harvest_konsole.txt
agents/v4_strategies.py  ·  models/v4_calibrator.py
data/v4_importer.py  ·  scripts/migrate_v4_to_v6.py
```

Diese Daten stammen aus dem Vorgängersystem V4 und würden jede V6-Kennzahl
verfälschen. Für Auswertungen ausschließlich `data_store/trades_v5.json`.

---

## TEIL 3 — Zustand, frisch verifiziert (28.07., 22:40–23:10)

### Bot

| | |
|---|---|
| **Läuft** | ja — PID 8648 (`python3.13`) + PID 10320 |
| **Start** | 28.07.2026 19:41:41 |
| **Uptime** | ~3 h 30 min |
| **CPU** | 1.892 s |

Der Neustart um 19:41 hat das gepatchte `doc_agent.py` geladen — der Fix ist
produktiv aktiv und hat um 23:06 bereits sauber gearbeitet.

### Offene Positionen (`open_positions_backup` — maßgeblich)

| Coin | Menge | Einstieg |
|---|---|---|
| SOL/USDC | 1,4820290 | 73,3125 |
| AVAX/USDC | 8,4801576 | 6,4309 |
| BTC/USDC | 0,00085563 | 63.106,66 |
| ETH/USDC | 0,02740801 | 1.911,3959 |
| ADA/USDC | 330,5869042 | 0,158287 |

`open_positions` enthält ebenfalls 5 Einträge — der in `tickets.txt` notierte
Diskrepanz-Bug ist derzeit **nicht** sichtbar.

### E7-Status (`python e7_auswertung.py`, 28.07. 22:57)

| | |
|---|---|
| **Deploy** | 17.07.2026 12:00 |
| **Vergangen** | 11 Tage 11 h |
| **Fenster endet** | 31.07.2026 — noch ~2,5 Tage |
| **Sells im Fenster** | 43 |
| **Win-Rate** | 74 % |
| **AvgWin / AvgLoss** | +0,89 $ / −1,29 $ |
| **R/R** | **0,69** (Basis E6.1: 0,54) |
| **Gesamt-P&L** | +14,42 $ |

| Kriterium | Ergebnis |
|---|---|
| K1 — R/R ≥ 0,54 | ✅ JA (0,69) |
| K2 — Gegenprobe-Summe > 0 | ✅ JA (+3,42 pp über 2 Fälle) |
| K4 — mind. 3 wirksame Fälle | ❌ NEIN (2) |

**Urteil des Skripts:** *„Datenlage zu dünn. E7-Fenster verlängern, weiter
sammeln."* — E7-Up-Treffer: 5 gesamt, **alle ADA/USDC**; davon 2 wirksam
(≥ 1 %), 3 neutral. Warnung im Skript: 1h-Kerzen, konservative Annahmen,
ADA-lastige Stichprobe.

Gegenprobe-Einzelfälle:
- 20.07. 20:03 ADA: E7 +1,91 % vs. ALT +1,32 % = **+0,59 pp** (+0,62 $)
- 21.07. 07:22 ADA: E7 +3,03 % vs. ALT +0,19 % = **+2,84 pp** (+1,57 $)

*Nur Anzeige — keine Entscheidung, keine Verhaltensänderung.*

### Offene Punkte, noch nicht in `tickets.txt`

1. **Wiederaufgetauchte Dateien** (1.3) — Archivordner und mehrere
   `data_store`-Backups sind zurück im Projekt. Herkunft unklar.
2. **`.tmp`-Dateien in `data_store/`**: `bot_state.json.tmp` und
   `trades_v5.json.tmp`. Entweder Reste eines abgebrochenen Schreibvorgangs
   oder ein anderer Writer nutzt bereits ein Temp-Muster — ungeprüft.
3. **Handbuch schrumpfte** von 201.356 B (01:17) auf 198.265 B (19:42),
   −3.091 B bei unveränderter Nullbyte-Zahl. Ursache nicht ermittelt.
4. **Diese Datei verschwand einmal.** Die erste Fassung wurde um ~23:10
   erfolgreich geschrieben und war vier Minuten später spurlos weg — in
   keinem Archiv auffindbar. `cleanup.py` scheidet aus (schützt alle `.md`
   hart und archiviert statt zu löschen). Ursache unbekannt. Deshalb trägt
   diese Fassung `[CLEANUP-KEEP]` im Kopf.
5. **`.py`-Altkopien nicht erfasst**: `features/doc_agent_backup_20260611.py`
   (331 Z.) und `ui/main_window_backup_20260610.py` (2.640 Z.) sind Backups,
   die als `.py` durch das Aufräum-Muster fielen.
6. **`core/balance_reporter(12).py`** — Duplikat mit Download-Suffix.
7. **Nullblock-Entscheidung offen**: Schattenkopien und Quarantäne-Archive
   wurden noch nicht gelesen — beides wäre rein lesend.

---

## TEIL 4 — Erledigt

**a) Tickets eingetragen** — beide Zeilen standen um 23:05 in `tickets.txt`
und wurden vom TicketsWatcher um 23:06 verarbeitet (Datei danach geleert,
Einträge stehen jetzt im Handbuch). Der ausgelöste Schreibvorgang lief bereits
atomar.

**b) `aufraeumen.ps1`** — war bereits vollständig durchgelaufen (beide Läufe,
siehe 1.3). Nichts nachzuholen; der Nachtrag zu wiederaufgetauchten Dateien
ist dort dokumentiert.

---

## Was offen bleibt

| # | Punkt | Nächster Schritt |
|---|---|---|
| 1 | **Nullblock im Handbuch** | Schattenkopien / Quarantäne-Archive lesend prüfen |
| 2 | **Verschwundene Dateien** | klären, was die erste Fassung dieses Dokuments entfernt hat |
| 3 | **Wiederaufgetauchte Dateien** | klären, welche Session sie zurückgeholt hat |
| 4 | **`.tmp` in `data_store`** | Reste oder aktiver Writer? |
| 5 | **Andere `data_store`-Schreiber** | gleiches Atomic-Muster prüfen (Ticket gesetzt) |
| 6 | **E7-Fenster** | endet 31.07. — K4 fehlt, Skript rät zur Verlängerung |
| 7 | **Restliche `.py`-Altkopien** | 2 Backup-Dateien + 1 Duplikat aufräumen |

Keine Trading-Verhaltensänderung in dieser Session.
