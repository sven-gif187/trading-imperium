# Bugfix-Runde 04.08.2026 — Bridge, Sleep-Mode, Argmax, Trade-Ebene

**Lokal:** 04.08.2026 23:25 (MESZ) · **UTC:** 2026-08-04T21:25Z
**Bot:** läuft, PID 9740, gestartet über `start_bot.bat`, mit allen Fixes.

---

## Der eigentliche Root Cause — gefunden und behoben

Alle bisherigen Analysen sagten: „der Kalibrator gewichtet DCA nach oben".
Das stimmte, war aber nicht die Ursache. Die Ursache ist eine Zeile:

**`app.py:270`** prüfte `if hasattr(self, 'v4_ensemble'):` — aber
`self.v4_ensemble` wird erst bei **`app.py:302`** erzeugt, in derselben
`__init__()`. Die Bedingung war damit **immer False**, der komplette Block
darunter wurde bei jedem einzelnen Start übersprungen, inklusive:

```python
self.signal_agent.v4_ensemble  = self.v4_ensemble
self.signal_agent.v4_calibrator = self.v4_calibrator
```

Beide blieben `None`. `agents/signal_agent.py:151` war nie erfüllt.
**Die V4-Bridge lief im Signalpfad nie.**

Damit fiel `strategy_id = v4_strategy_used or self.current_strategy`
(`signal_agent.py:182`) immer auf den Fallback zurück — genau deshalb
trugen alle 523 BUYs im V6-Journal `DCA_FEAR_GREED`.

**Laufzeitbeleg vor dem Fix:** 81 BUY-Signale nach einem Neustart,
**keine einzige** mit einem `V4-…`-Grund.
**Laufzeitbeleg nach dem Fix:** `[2026-08-04T21:14:35] [APP] V4-Bridge an
SignalAgent angeschlossen (ensemble=True, calibrator=True)`.

Der Block steht jetzt hinter der Erzeugung von `strategy_brain` (:289),
`v4_ensemble` (:302) und `v4_calibrator` (:304/310).
Backup: `app.py.bak_v4bridge_20260804`.

---

## Die vier Fixes dieser Runde

| # | Datei | Was | Backup |
|---|---|---|---|
| 1 | `execution/engine.py:172` | Sleep-Mode blockierte **jede** Order, auch NOTAUS-Verkäufe. Jetzt nur noch BUY — gleiche Bedingung wie `risk/engine.py:88` | `.bak_sleepmode_20260804` |
| 2 | `agents/v4_strategies.py:256` | Argmax wieder über den **rohen** Score wie in V4; die Hart-Sperre `weight==0.0 → continue` ist raus | `.bak_argmax_20260804` |
| 3 | `app.py:270/312` | V4-Bridge-Block hinter die Erzeugung verschoben | `.bak_v4bridge_20260804` |
| 4 | `forschung.db` | Trade-Ebene geprüft — Tabelle `trades_journal` existierte bereits, Dublette per Rollback verhindert | `.bak_vor_trades_20260804` |

**Fix 1 ist der wichtigste.** Am 03.08. um 12:32:56 und 12:32:57 traf es
zweimal hintereinander einen NOTAUS-Stop auf ETH bei −3,5 %: `[EXEC] Order
nicht gefuellt: rejected | Sleep-Mode (676s remaining)` — obwohl
`risk/engine.py:81-86` den Verkauf ausdrücklich genehmigt hatte. Im
Live-Betrieb hätte das Positionen festgehalten, deren Stop längst gerissen
war.

---

## Was der Fix NICHT gelöst hat — ehrlich

Nach dem Neustart tragen **2 021 von 2 021** BUY-Signalen weiterhin
`V4-DCA_FEAR_GREED`. Das ist diesmal **kein Bug**:

- Fear & Greed liegt heute konstant bei **25–28** (gemessen über das
  gesamte Tageslog: 21 850 × „Fear (25)", 2 017 × „Fear (27)",
  23 575 × „Fear (28)").
- `_dca_fear_greed` liefert bei `fg <= 25` den Rohscore **8**.
- Der Argmax über rohe Scores wählt damit korrekt DCA — geschlagen wird
  das nur von RSI < 30 (9), einem frischen MACD-Cross mit ADX > 25 (9)
  oder Fib 78,6 % + RSI tief (9).

**Der Selector funktioniert. Er wählt nur dauerhaft die Strategie, die im
V4-Journal netto −93,97 $ gemacht hat.** In V4 sah man Vielfalt, weil
Fear & Greed über den Monat schwankte — nicht weil der Selector anders war.

Das ist der Punkt, an dem eine Architekturentscheidung ansteht und kein
Bugfix mehr hilft: Eine Stimmungsstrategie mit konstant hohem Score
verdrängt jedes technische Signal, solange die Stimmung konstant bleibt.

---

## Trade-Ebene in der Datenbank

`forschung.db` hat bereits die Tabelle **`trades_journal`**: 1 137 Zeilen,
45 Spalten, Backfill aus `data_store/trades_v5.json`. Sie enthält genau
die Felder, die dein Chartanalyse-Konzept unter „Damit es wirklich besser
wird" verlangt — `regime_1d`, `regime_4h`, `regime_1h`, `key_level_typ`,
`key_level_preis`, `r_multiple`, `mfe_pct`, `mae_pct`, `regeln_erfuellt`,
plus `decision_id`, `cycle_id`, `feature_hash` für die Nachvollziehbarkeit.

Verteilung: DCA_FEAR_GREED 455, ICHIMOKU_CLOUD 250, EMA_TREND 155,
RSI_OVERSOLD 93, FIBONACCI_SUPPORT 69.

**Was fehlt — 24 der 45 Spalten sind komplett leer:**
`regime_1d`, `regime_4h`, `regime_1h`, `fear_greed`, `key_level_typ`,
`key_level_preis`, `entry_geplant`, `slippage_pct`, `stop_initial`,
`stop_final`, `tp1`, `tp2`, `spread_pct_entry`, `gebuehr_usd`,
`r_multiple`, `mfe_pct`, `mae_pct`, `regeln_erfuellt`, `regelverstoss`,
`decision_id`, `cycle_id`, `feature_hash`, `confidence`,
`strategie_version`.

Der Grund ist einfach: `trades_v5.json` enthält diese Werte nicht. Sie
müssen **beim Trade selbst** mitgeschrieben werden — das ist der nächste
Ausbauschritt und erfordert einen Eingriff in den Kauf- und Verkaufspfad.
Ohne diese Felder lässt sich nach 50 Trades nicht sagen, *warum* eine
Serie lief.

---

## Offen

1. **MFE/MAE, Regime, Spread und Regelkonformität beim Trade mitschreiben**
   — sonst bleibt die Trade-Tabelle halb leer.
2. **Zwei Backtest-Blocker:** Kapitaltod des Harness ab ~50 $ bei 20 %
   Positionsgröße (Jahr 2: 143 von 366 Tagen) und der 45-Minuten-Look-ahead
   in `zu_1h()` (bis 4,77 pp Verzerrung).
3. **Coin-Reduktion auf BTC/ETH/SOL** — senkt die Kostenschwelle von
   ~0,63 % auf ~0,50 %, also die Break-even-Trefferquote bei ±2,5 %-Barriere
   von 62,6 % auf 60,0 %. Statistisch verliert man dabei fast nichts:
   `messung_f2_ic.py:49` weist die effektive Coin-Zahl mit **1,3** aus
   (E5, Befund 16, gemessen 1,23–1,42).
4. **DCA-Dominanz bei konstanter Marktstimmung** — Architekturfrage,
   kein Bug.
5. **Drei stille Prozesstode** (03.08. 12:32:57, zwischen 17:22 und 00:45,
   sowie zwischen 02:45 und 17:29) — Ursache ohne Windows-Ereignisprotokoll
   NICHT ENTSCHEIDBAR, `wevtutil` liefert in dieser Umgebung keine Ausgabe.

---

## Sicherheit

Kein Echtgeld, keine Order, keine Kontobewegung, keine Secrets, keine
`.env` geöffnet, keine Datei gelöscht, `v4_referenz/` nur gelesen und
nichts daraus kopiert. Für jede geänderte Datei liegt ein Backup daneben.
Der Bot wurde einmal beendet und neu gestartet — ausdrücklich freigegeben.
