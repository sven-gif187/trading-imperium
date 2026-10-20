# Rundgang-Checkliste

Wird von Claude geführt, nicht von Hand abtippen — bei jeder Runde direkt
aus dem Ordner ausgelesen, damit nichts übersehen wird. Screenshots sind
nicht nötig. Häkchen = im `BOT-HANDBUCH.md` (Teil 7) erklärt.

Reihenfolge und Begründung stehen in `NAECHSTE-SESSION.md`.

---

## Runde 1 — `app.py` ✅ erledigt

- [x] `app.py` (Hauptprogramm, als Ganzes + 8 Teilstücke)

## Runde 2 — `risk/` ✅ erledigt

- [x] `engine.py`
- [x] `exposure.py`
- [x] `drawdown_guard.py`
- [x] `kill_switch.py`
- [x] `position_sizing.py`
- [x] `exit_rules.py`
- [x] `reentry_guard.py`
- [x] `coin_stops.py`
- [x] `regime_profiles.py`
- [x] `adaptive_sizing.py`
- [x] Leichen notiert: `daily_loss_guard.py.UNUSED`, 4× `engine.py.bak_*`, `exposure.py.bak_failsafe_20260805`

## Runde 3 — `runtime/` ✅ erledigt

- [x] `exit_monitor.py`
- [x] `state_manager.py`
- [x] `reporting.py`
- [x] Leichen notiert: `exit_monitor.py.bak` (+4 weitere `.bak_*`), `state_manager.py.bak_20260807_toepfe1`, `state_manager.py.bak_guardfix`

## Runde 4 — `execution/` ✅ erledigt

- [x] `engine.py`
- [x] `circuit_breaker.py`
- [x] `retry_policy.py`
- [x] `idempotency.py`
- [x] `order_manager.py`
- [x] `fill_reconciler.py`
- [x] `twap_executor.py`
- [x] `futures_trader.py` (angeschlossen, aber im Leerlauf)
- [x] `multi_exchange.py` (angeschlossen, aber im Leerlauf)
- [x] `exchange_client.py` — **auffällig: nirgends importiert**, kein `.bak`/`.UNUSED`-Name, für Runde 11 vorgemerkt
- [x] Leichen notiert: `engine.py.bak_paperbuy_20260805`, `engine.py.bak_sleepmode_20260804`

## Runde 5 — `agents/` + `models/` ✅ erledigt

**agents/**
- [x] `signal_agent.py`
- [x] `strategy_brain.py`
- [x] `context_agent.py`
- [x] `cycle_theory.py`
- [x] `btc_accumulator.py`
- [x] `v4_strategies.py`
- [x] `grid_bot.py` (config-gated aus)
- [x] `grid_trader.py` (angeschlossen, aber im Leerlauf)
- [x] `dca_advanced.py`
- [x] `smart_entry.py`
- [x] `arbitrage_agent.py` (reines Radar, kein Trade-Auslöser)
- [x] `llm_local.py` (angeschlossen, aber im Leerlauf)
- [x] `strategy_export.py`
- [x] Leichen notiert: `signal_agent.py.bak_einheit`, `strategy_brain.py.hooks_20260604_214935`, `v4_strategies.py.bak_argmax_20260804`

**models/**
- [x] `brain_persistence.py` (Teil 1.1)
- [x] `v4_calibrator.py`
- [x] `lern_journal_v6.py` (Teil 1.1)
- [x] `rl_feedback.py` (Teil 1.2)
- [x] `ensemble_signal.py`
- [x] `meta_voting.py` (Teil 1.4) — **Fund: berechnetes Gewicht wird nirgends gelesen (app.py:2147)**
- [x] `signal_model.py` — **ML-Baustelle, nicht am Steuer**
- [x] `xgboost_model.py` — **ML-Baustelle, nicht am Steuer**
- [x] `regime_model.py` — **ML-Baustelle, nicht am Steuer**
- [x] `model_registry.py` — **ML-Baustelle, nicht am Steuer**
- [x] `train_pipeline.py` — **ML-Baustelle, nicht am Steuer**
- [x] `auto_retrain.py` — trainiert Modelle, deren Vorhersage niemand liest

## Runde 6 — `features/` ✅ erledigt

- [x] `indicators.py`, `rsi_divergence.py`, `vwap_agent.py`, `regime_detection.py`, `multi_timeframe.py` (nur coins[:1]/BTC) — aktiv, füttern die Kaufentscheidung
- [x] `regime_adaptiv.py` (Teil 1.5)
- [x] `bottom_detection.py` — **Fund: `evaluate()` wird von niemandem aufgerufen**
- [x] `waechter.py`, `tickets_watcher.py`, `doc_agent.py`, `impact_journal.py` (Teil 1.3)
- [x] `chartanalyse.py`, `chartanalyse_agent.py` — nur Messung, kein Kaufpfad
- [x] `sensei.py` — reiner Erklärer
- [x] `akademie.py`, `chart_view.py`, `chart_data.py`, `stoploss_edge.py`, `strategy_lab.py`, `chart_refresher.py` — **Desktop-GUI (main_window.py), Standardstart ohne --headless**, volle Details in Runde 9
- [x] `safety.py` (schon Runde 4)
- [x] `market_regime.py` — **Fund: zweite, nirgends importierte `RegimeDetector`-Klasse, verwirrend gleicher Name**
- [x] `labels.py`, `portfolio_features.py` — ML-Baustelle (Runde 5), nicht angeschlossen
- [x] `situation_memory.py` — selbst dokumentiert „NICHT VERDRAHTET", Owner-Entscheidung 11.08.
- [x] **3 leere 0-Byte-Dateien** `cd`, `dir`, `python` — vermutlich Terminal-Tippfehler, Kandidat für Runde 11
- [x] Leichen notiert: `doc_agent.py.bak_*` (4×), `doc_agent_backup_20260611.py`, `sensei.py.bak_stichprobe_20260805`

## Runde 7 — `data/` ✅ erledigt

- [x] `market_data.py` — die Quelle allen Handels
- [x] `websocket_stream.py`
- [x] `source_health.py`
- [x] `nupl_monitor.py` (blockiert Käufe direkt) + `dxy_monitor.py` (Größen-Multiplikator)
- [x] `funding_rates.py`, `whale_alerts.py`, `capitol_trades.py`, `onchain_analytics.py`, `orderbook_depth.py`, `sentiment_data.py`, `reddit_sentiment.py` (403, bekannt)
- [x] `feature_store.py` — ML-Baustelle (Runde 5)
- [x] `cache.py`, `data_quality.py` — **Fund: nur in Tests referenziert, kein Live-Pfad**
- [x] `dxy_filter.py`, `news_data.py` — **Fund: nur ein Forschungs-Skript nutzt sie, nicht der Bot**
- [x] `top_coins.py` — **Fund: komplett verwaist, keine einzige Fundstelle**
- [x] `v4_importer.py` — einmaliges Migrations-Werkzeug
- [x] Leichen notiert: `market_data.py.bak_p1harden`, `market_data.py.bak_p4f`

## Runde 8 — `core/` ✅ erledigt

- [x] `bus.py` — Poststelle
- [x] `events.py`
- [x] `state_store.py`
- [x] `scheduler.py`
- [x] `health.py`
- [x] `logger.py`
- [x] `telemetrie.py` (Teil 2.1)
- [x] `hintergrund.py` (Teil 4.4)
- [x] `auto_restart.py`
- [x] `exceptions.py`
- [x] `balance_reporter.py`
- [x] `regel_schalter.py` — **Fund: fertig gebaut, aber von keiner der 8 Regeln tatsächlich genutzt — nur eine Testdatei ruft sie auf**
- [x] Leichen notiert: `bus.py.bak_sichtbarkeit_20260806`, `logger.py.bak_logrot`
- [x] `balance_reporter(12).py` — **Fund: kein Backup, sondern eine zweite, andere Fassung derselben Klasse (Datei(1)-Muster), technisch nicht importierbar**

## Runde 9 — `ui/` ✅ erledigt

- [x] `dashboard.py` — Browser, reine Anzeige, Port 5050
- [x] `ngrok_dashboard.py` — Tunnel, standardmäßig aus
- [x] `webhook_server.py` — **Fund: zweiter, von außen erreichbarer Kaufweg über Port 5051 (läuft aber normal durch Signal→Risiko→Ausführung)**
- [x] `main_window.py` — Cockpit-Fenster, Standardstart ohne `--headless`
  - [x] Cockpit-Reiter (echter VERKAUFEN-Knopf)
  - [x] Manuell-Reiter — **Fund: umgeht alle 8 Risk-Prüfungen aus Runde 2, auch den Kill-Switch, einzige Bremse Mindestbetrag 5$**
  - [x] Backtest/BTC/History/Agents/Settings/Log/Charts
  - [x] Akademie/Strategie-Labor/Stoploss-Kante als Pop-ups (Runde 6)
- [x] `terminal_tab.py`, `zyklus_tab.py`, `geldfluss_tab.py`, `chartanalyse_tab.py` — alle vier „REINE ANZEIGE", bestätigt [[tabs-bleiben-beobachtungsdeck]]
- [x] Leichen notiert: `main_window_backup_20260610.py` (komplette alte Fassung), `main_window.py.bak_*` (3×), `terminal_tab.py.bak_*` (6×)

## Runde 10 — `backtest/` + `portfolio/` ✅ erledigt

**backtest/** — Prüfstand, per Befehl, nicht automatisch
- [x] `engine.py`, `fees.py`, `slippage.py`, `metrics.py` — Fundament + Rechenbausteine
- [x] `optimizer.py` — Baustein hinter dem entfernten Auto-Optimizer-Knopf (Teil 4.6), hart stillgelegt
- [x] `hyperopt.py` — gebaut, nicht im Einsatz (nur `get_status()`)
- [x] `walk_forward.py`, `monte_carlo.py` — Bausteine von `engine.py`
- [x] `daten_holen.py`, `ausstieg_vergleich.py`, `strategie_studie.py`, `ausstieg_backtest.py` — **per Befehl aufrufbar, Befehle im Handbuch notiert**

**portfolio/** — Kontoführung, läuft ständig mit
- [x] `manager.py` — zentrale Kapitalverwaltung, praktisch jeder Kauf hängt daran
- [x] `agent.py`, `correlation_guard.py` — Klumpenrisiko-Wächter
- [x] `calculator.py` — reine Rechenbausteine
- [x] `daily_loss.py` — **Fund: läuft AKTIV (nicht Schatten), Grenze 6,0 % — pausiert Käufe, verkauft nie**
- [x] `rebalancer.py` (schon Runde 1) — abgeschaltet, Trockenlauf
- [x] Leichen notiert: `manager.py.bak_p5`, `daily_loss_guardian.py.UNUSED`

## Runde 11 — Der Rest (Hauptordner + 4 übersehene Ordner) ✅ erledigt

**Vier übersehene, aktive Ordner (fehlten im Original-Plan):**
- [x] `config/` — `settings.py` (AppConfig, zentral), `versioning.py`
- [x] `live/` — `live_runner.py`/`paper_runner.py` (austauschbare Zwillinge), `watchdog.py`, `state_recovery.py`, `shadow_mode.py`
- [x] `reports/` — `telegram.py` + `equity_tracker.py` aktiv; **Fund: `trade_journal.py`, `daily_report.py`, `weekly_report.py` komplett verwaist**
- [x] `metals/` — eigenständiges Metalle-Feature, selbst dokumentiert „fasst den Bot NICHT an"

**Hauptordner (~150 Dateien):**
- [x] Betriebs-Skripte (`start_bot.bat`, `telemetrie_frage.py`, `job_forschung_capture.py`, `job_sammler.py`, `sammler.py`, `config_update.py`)
- [x] Diagnose-Skripte — **Fund: `go_live_check.py` ist keine reine Diagnose, sondern die vom Bot selbst aufgerufene Live-Start-Sicherung (Runde 4)**
- [x] Auswertungs-/Forschungs-Skripte (E4/E5/E7, Gesamtauswertung, Journal-Abgleich, Zyklus-Forschung) — Belege hinter Teil 3/4
- [x] Install-/Fix-Skripte (12+3 Stück) — bereits erledigt, nicht erneut ausführen
- [x] Test-Skripte (5 Stück) — bestätigen die Fixes vom 11.08.
- [x] Sonstige Werkzeuge (Navigator, Brain-View, Cleanup, Metalle-CLI)
- [x] Handbücher/Doku (33 `.md`) + Konfig-Dateien — als Gruppe erfasst, nicht einzeln
- [x] Leichen komplett katalogisiert: `tickets.txt.bak_*` (23), `app.py.bak_*` (4), `ENTWICKLERHANDBUCH.md.bak*`/`.nullbyte`/`_KORRUPT_*` (6), `auto_export_*.txt` (9), `_*_payload*.py` (7), `install_e8_nachkauf_stop(1).py`, diverse `.txt`-Reste

---

## Runde 12 — `docs/forschungsprogramm_2026-07` ✅ erledigt

- [x] Eigene Datenbank `forschung.db` verstanden und abgefragt (`db_frage.py status/befunde/bugs/tot`)
- [x] Architektur-Scan (231 Module) gegen eigene Runden 1–11 abgeglichen — **Fund: `portfolio/calculator.py` fälschlich als aktiv beschrieben, korrigiert**
- [x] Gate-1/Gate-2-Verdikt (beide NEGATIV) für neue Kandidaten-Strategien verstanden und eingeordnet — kein Urteil über die Live-Strategien
- [x] `risk/position_sizing.py`-Status direkt nachgeprüft — eigene Runde-2-Beschreibung bestätigt richtig, DB-Korrektur war überholt
- [x] `features/indicators.py` korrigiert — nicht die „gemeinsame Rechenbasis", nur vom ML-Training genutzt
- [x] Neue Funde: #22 USDT-Rückfall unter MiCA sinnlos, #23 Slippage-Annahme ignoriert Münz-Unterschiede

## Runde 13 — `docs/messungen_2026-07` ✅ erledigt

- [x] Die zwei schwersten historischen Befunde verstanden: „kein Stop rettet das System", „kein Richtungsvorteil im Einstieg" — Grundlage der Ausstiegs-Leiter-Reparatur (Runde 2)
- [x] Gegen heutigen Code geprüft: „coins[:12] wirkungslos" ist überholt (heute 3 Coins statt 11)
- [x] Neuer Fund: #24 Ist-Slippage wird berechnet, aber nie ins Journal geschrieben

## Runde 14 — `scripts/`, `tests/`, `v4_referenz/`, Archive ✅ erledigt

- [x] `scripts/` — drei Reset-Fassungen (v3 aktuell), `reset_paper.py`, `migrate_v4_to_v6.py`
- [x] `tests/` — eigene Test-Sammlung (`run_all.py` + 6 Dateien), unabhängig von Runde 11
- [x] `v4_referenz/` — kompletter Vorgänger-Bot, reine Messquelle, kein aktiver Code
- [x] `_archive_20260716_065427/`, `uebergabe-dust/` — Altlasten; **Fund: `dust_manager.py` (950 Zeilen), nie angeschlossen**

## Runde 15 — Die 17 Installer/Fix-Skripte, einzeln ✅ erledigt

- [x] Jeden Installer im heutigen Code auf seine Spur geprüft: 14 angekommen, 1 ohne Spur (`fix_terminal_regime.py`, reine Anzeige)
- [x] `install_e8_nachkauf_stop.py` — **bewusst nie eingespielt**, Grundannahme am 29./30.07. durch das Mess-Audit widerlegt. Kein Versäumnis. Nicht ausführen.
- [x] **Fund #25:** `update_metals_indikatoren.py` ersetzt statt patcht — hat am 06.08. Stufe 3 gelöscht

## Runde 16 — Die Auswertungs-Skripte, einzeln ✅ erledigt

- [x] **Fund #26 (Korrektur):** `regime_filter.py` ist aktiver Kauf-Blocker (`app.py:905`), kein Skript
- [x] **Fund #26 (Korrektur):** `chartanalyse_backtest.py` läuft täglich über den Chartanalyse-Agenten
- [x] 10 echte Auswertungs-Werkzeuge einzeln erfasst, Befehle im Handbuch
- [x] Modul-Potenzial bewertet: `epochs.py`+`epoch_report.py` (stärkster Kandidat), `stoploss_analyse.py`/`regime_filter_messung.py` als wiederkehrende Berichte, `e5_walkforward.py` als Methoden-Vorlage

## Runde 17 — Alle 2.511 Dateien mechanisch klassifiziert ✅ erledigt

- [x] `inventar_agent.py` ausgeführt → `INVENTAR.md`: **125 KERN**, 130 Werkzeug, 39 verwaist, 93 Backup, 36 Duplikat, 153 Daten-alt, 1.733 Daten/Doku
- [x] Alle 39 verwaisten gegen den eigenen Rundgang gegengeprüft — jeder eigene Fund bestätigt
- [x] **Fund #25 (Teil 2):** `metals/metals_store.py` verwaist — zweiter Folgeschaden desselben Replace-Vorfalls

## Runde 18 — Modul-Kandidat gemessen ✅ erledigt

- [x] `situation_replay.py` ausgeführt (Voraussetzung seit Journal-Fix erfüllt, 625 Trades)
- [x] **Fund #27 (entschieden):** Situations-Gedächtnis 66,2 % gegen Baseline 72,0 % → **nicht anschließen**, jetzt gemessen statt vermutet

## Runde 19 — Die restlichen Werkzeuge ✅ erledigt

- [x] 10 Diagnose-Werkzeuge einzeln erfasst — **wertvollstes: `brain_view.py`** (zeigt, wie viel V4-Altlast im Gehirn steckt)
- [x] `bot_navigator.py` — baut HTML-Karte; vorhandene `bot_uebersicht.html` ist vom 6. Mai, veraltet
- [x] `check_punkt_a.py` — historisch, an alte Epochen gebunden
- [x] Die 50 `docs/code/`-Skripte nach Gruppen erfasst (20 Messläufe, 12 Selbst-Audits, 5 Batterien, 4 DB-Werkzeuge, 3 Kostenmatrizen)
- [x] `harness_ext.py` liegt bitgleich doppelt (beide `code/`-Ordner, gleiche Prüfsumme)

## TEIL 8 — Abwägung geschrieben ✅

- [x] 8.1 Kann weg: ~240 Dateien, Bedingung = Installer-Docstrings vorher sichern
- [x] 8.2 Erst prüfen: 7 Fälle, größter `dust_manager.py` (950 Zeilen)
- [x] 8.3 Einbauen: 5 Kandidaten, Reihenfolge nach Nutzen/Aufwand
- [x] 8.4 Entschieden dagegen: 5 Dinge, alle gemessen statt vermutet
- [x] 8.5 Gefahren: Replace-Installer, `regime_filter.py`-Verwechslung, **kein Backup außerhalb des Rechners (#28)**

---

**Stand: wirklich jeder Ordner im Projekt durchgesehen.**
Ursprüngliche 11 Runden + 4 zuvor übersehene Ordner (in Runde 11
nachgetragen) + 3 zusätzliche Runden für `docs/`, `scripts/`, `tests/`,
`v4_referenz/` und Archive. **24 Punkte** stehen in
`GEFUNDENE-PROBLEME.md`, mehrere bereits behoben.
Nächster Schritt: dort weiter einzeln beheben.
