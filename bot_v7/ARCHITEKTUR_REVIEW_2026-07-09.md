# ARCHITEKTUR-REVIEW — Trading Imperium V6

**Datum:** 09.07.2026
**Basis:** Vollständiger Code-Scan (137 Module) + Live-Dateien (app.py, config.json, market_data.py, live_runner.py)
**Methode:** Statische Analyse — kein Code verändert. "Erst verstehen, dann ändern."

---

## Gesamturteil

Der Bot ist **architektonisch überdurchschnittlich gut gebaut** — deutlich reifer als typische Hobby-Projekte. Ereignisgesteuert, 137 Module mit klarer Aufgabenteilung, **null zirkuläre Imports** (bei dieser Größe bemerkenswert sauber), Logger statt Print im Kern (516 Log-Aufrufe), echte Test-Suite, dedizierte Risk-/Execution-/Retry-Module.

Was fehlt, sind **Aufräumarbeiten und drei gezielte Härtungen — kein Neubau.** Das Fundament trägt.

---

## Stärken (was bereits sitzt)

- Keine hartcodierten Secrets im Code (Scan sauber)
- Null zirkuläre Imports über alle 137 Module
- Event-Bus-Architektur mit spezialisierten Agenten
- Kill-Switch (4 Referenzen) und Daily-Loss (5 Referenzen) in app.py verdrahtet
- Backtesting-Infrastruktur vorhanden: walk_forward, monte_carlo, strategy_lab, stoploss_edge, e5_walkforward
- Logger-basiert (516 log-Aufrufe im Kern)
- Test-Suite: test_backtest/data/execution/portfolio/risk/v6_modules + run_all

---

## Risiken — priorisiert

### P1 — Zwei kritische `except:` im Preis-Pfad (Fix liegt bereit)
Von 6 blanken `except:` sind zwei gefährlich:
- `market_data.py:90` — Ticker-Fehler wird still verschluckt → Preis friert auf altem Cache-Wert ein, ohne Warnung
- `live_runner.py:77` — `return 0` bei Fehler → 0-Preis im Geldpfad (Division, Positionsgröße)

**Dieselbe Wurzel, die die Geisterposition verursacht hat.** Ein Fehler, der nicht loggt, kostet Tage.
Die anderen 4 `except:` sind harmlos (sinnvolle Defaults: RSI→20, F&G→50).
Zusätzlich: `market_data.py:106` falsche F&G-URL (`/fnd/v2/crypto` statt `/fng/`) → Fallback greift immer → F&G aus diesem Pfad konstant/nutzlos.

**Status:** Fix in Arbeit (P1-Härtung).

### P2 — Risk-Guards gebaut, aber teils nicht verdrahtet
- `drawdown_guard` → läuft in engine.py ✅
- `correlation_guard` → läuft in agent.py ✅
- `position_sizing.py` → **0 Referenzen** in app.py/agent.py/manager.py ⚠️

Die Positionsgröße kommt aus festem `position_size_pct` (config), nicht risikobasiert.
Für Live relevant: volatilerer Coin sollte kleinere Position bekommen. **Lücke im Risikomanagement, kein Bug.**

### P3 — Daily-Loss doppelt (Audit P5)
`daily_loss_guard.py` UND `daily_loss_guardian.py` existieren beide — zwei konkurrierende Wahrheiten für dieselbe Notbremse. Genau die Struktur, die den schlimmsten Verlusttag (18.06.) verursachte.
**Neubau bleibt Pflicht vor Live:** ein Modul, echter Tagesreset, nur Kauf-Pause statt Zwangsverkauf.

### P4 — Zwei Monolithen
- `main_window.py` — 3.072 Zeilen (noch unangetastet)
- `app.py` — 2.891 Zeilen (Split läuft, Schritt 1 erledigt)

Wartbarkeitsrisiko, kein akutes Live-Hindernis.

### P5 — Aufräum-Altlasten
- 223 `except…: pass` gesamt (meiste harmlos, aber Rauschen)
- 282 `print()` außerhalb Tests (sollten Logger sein)
- Veraltete Backup-Dateien im Code: `main_window_backup_20260610.py` (2.640 Z.), `full_reset_final_v2/v3`

Technische Schuld, nicht Live-blockierend.

---

## Pflicht-vor-Live-Checkliste (aktualisiert)

1. **P1-Härtung** — Preis-Pfad-`except:` + F&G-URL *(Fix bereit)*
2. **E6-B** — ADA-Stop 3.0% (Per-Coin-Override)
3. **Daily-Loss-Neubau** — gefährlichster Altlast-Bug
4. **position_sizing verdrahten** — neu gefundene Risiko-Lücke
5. **R/R nachhaltig > 1 nachweisen** — in normalem Markt, nicht im Bär
6. **MiCA/Börse klären**

Alles Weitere (Monolith-Split 2–6, Aufräumen, main_window) = Wartbarkeit, nicht Live-blockierend.

---

## Bereits erledigt (Kontext)

- E4 abgeschlossen: Stop 2.5% bleibt, Problem coin-spezifisch (XRP+ADA)
- E6-A: XRP pausiert
- Geisterposition gefixt (Daten + Ursache/Restore-Härtung)
- Journal-Bias behoben (lernt jetzt aus Gewinnen UND Verlusten)
- Makro-Zyklus-These sauber widerlegt und geparkt
- Secrets-Härtung (P1 Audit), Token rotiert
