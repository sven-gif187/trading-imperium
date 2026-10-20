# V4-Bridge-Reparatur und Trade-Journal

**Lokal:** 04.08.2026 23:15 (MESZ) · **UTC:** 2026-08-04T21:15Z
**Status:** ERFOLG mit einem Vorbehalt (siehe „Was der Fix nicht löst").

---

## 1. Der eigentliche Root Cause des Multi-Strategy-Bugs

Die bisherige Erklärung (eingefrorene Kalibrator-Gewichte) war **richtig,
aber nicht der tiefste Punkt**. Darunter lag ein Reihenfolgefehler:

`app.py:270` (alt) prüfte `if hasattr(self, 'v4_ensemble'):`, aber
`self.v4_ensemble` wurde erst bei `app.py:304` erzeugt — **beide Zeilen in
derselben `__init__()`**. Die Bedingung war immer `False`, der gesamte
Block darunter wurde nie ausgeführt, und damit auch nicht:

```python
self.signal_agent.v4_ensemble  = self.v4_ensemble    # :283
self.signal_agent.v4_calibrator = self.v4_calibrator # :284
```

Beide blieben `None` (initialisiert in `agents/signal_agent.py:24-25`).
`signal_agent.py:151` (`if self.v4_ensemble is not None and
self.v4_calibrator is not None`) war damit **nie** erfüllt.

**Folge:** Die V4-Bridge lief im Signalpfad nie. `strategy_id =
v4_strategy_used or self.current_strategy` (`:182`) fiel ausnahmslos auf
den Fallback zurück — deshalb trugen alle 523 BUYs `DCA_FEAR_GREED`.

**Laufzeitbeleg vor dem Fix:** 81 BUY-Signale nach dem Neustart um 20:17
UTC, **keine einzige** mit einem `V4-…`-Grund.

**Laufzeitbeleg nach dem Fix** (`data_store/system.log`):

```
[2026-08-04T21:04:53] [APP] V4-Bridge an SignalAgent angeschlossen
                            (ensemble=True, calibrator=True)
[2026-08-04T21:04:53] [BRAIN] V4-Performance geladen: 15 Strategien,
                            638 Trades, +2631.23 EUR
```

Die Bridge greift jetzt: 19 von 19 BUY-Signalen im Fenster 21:0x tragen
einen `V4-…`-Grund, z. B. `V4-DCA_FEAR_GREED STARK (0.89)`.

**Konsequenz für den vorherigen Argmax-Fix:** Der war korrekt, wurde aber
nie erreicht. Erst beide zusammen wirken.

---

## 2. Was der Fix NICHT löst — ehrlich

Im Beobachtungsfenster gewinnt **DCA_FEAR_GREED weiterhin jeden Argmax**
(20 von 20 Nennungen). Das ist jetzt aber kein Defekt mehr, sondern die
Strategielogik: Fear & Greed steht bei **25**, und
`_dca_fear_greed` (`agents/v4_strategies.py`) vergibt bei `fg <= 25` den
Score 8 von 9 → `raw = 0,889`. Eine andere Strategie müsste Score 9
erreichen, um zu gewinnen. In V4 wäre das genauso ausgegangen.

**Erst bei anderer Marktlage** (F&G über 35, oder RSI unter 30 für
RSI_OVERSOLD Score 9, oder ein 78,6-Fib-Treffer mit RSI unter 40) werden
andere Strategien gewinnen. Der Mechanismus ist repariert; die Vielfalt
zeigt sich über die Zeit, nicht in zehn Minuten.

**Nebenwirkung, angekündigt und eingetreten:** Der zurückgegebene Score
ist jetzt der rohe statt des gedämpften. In `signal_agent.py:156-165`
ergibt `0,889` jetzt **+4 Punkte** statt vorher +2. Die Gesamt-Scores
sind sichtbar gestiegen — beobachtet 6/10 bis 9/10 statt vorher 3/10 bis
4/10. Bei `min_score = 3` wird damit **praktisch jedes Signal gekauft**.

> **Offene Empfehlung, nicht umgesetzt:** V4 hielt mit `min_score` 5 bzw.
> 6 dagegen (`trading_imperium_v4_25_ALARM.py:6050-6053`), V6 steht auf 3
> (`agents/signal_agent.py:169`). Wer die V4-Auswahl übernimmt, sollte
> auch die V4-Schwelle übernehmen — sonst steigt nur die Trade-Frequenz
> und damit die Kostenlast. Das ist eine Parameteränderung und braucht
> eine eigene Freigabe.

---

## 3. Trade-Journal in der bestehenden Datenbank

**Keine zweite Datenbank.** Neue Tabelle `trades_journal` in
`docs/forschungsprogramm_2026-07/forschung.db`, **45 Spalten**, drei
Indizes.

| Bereich | Felder |
|---|---|
| Herkunft | `quelle` (v6_live / v6_paper / v4_import / backtest_*), `eroeffnet_at`, `geschlossen_at`, `symbol`, `richtung` |
| Strategie | `strategie_id`, `strategie_version`, `setup_name`, `score`, `confidence` |
| Marktkontext | `regime_1d`, `regime_4h`, `regime_1h`, `fear_greed`, `key_level_typ`, `key_level_preis` |
| Preise | `entry_geplant`, `entry_fill`, `slippage_pct`, `stop_initial`, `stop_final`, `tp1`, `tp2`, `exit_fill`, `exit_grund`, `menge`, `einsatz_usd`, `nachkaeufe`, `nachkauf_usd` |
| Kosten | `spread_pct_entry`, `gebuehr_usd` |
| Ergebnis | `pnl_usd`, `pnl_pct`, `r_multiple`, **`mfe_pct`**, **`mae_pct`**, `haltedauer_min` |
| Regelkonformität | `regeln_erfuellt` (JSON), `regelverstoss` |
| Nachvollziehbarkeit | `decision_id`, `cycle_id`, `feature_hash`, `notizen` |

**Die Spalte `quelle` beantwortet die Vermischungsfrage:** Backtests
verschiedener Konfigurationen laufen als `backtest_<name>` nebeneinander,
jede Auswertung filtert auf ihre Quelle. Nichts vermischt sich.

**Backfill:** 1 137 Zeilen aus beiden Journalen.

| Quelle | Trades | Summe PnL |
|---|---|---|
| `v4_import` | 710 | −407,97 $ |
| `v6_paper` | 427 | −36,76 $ |

Top-Strategien im V4-Import: ICHIMOKU_CLOUD 250 (−241,82 $), EMA_TREND
155 (−217,46 $), RSI_OVERSOLD 93 (+125,36 $), FIBONACCI_SUPPORT 69
(+71,89 $), STOCHRSI_REVERSAL 31 (+44,61 $).

**Ehrlich zum Backfill:** 21 von 45 Spalten sind gefüllt. MFE, MAE,
Spread bei Entry, Regime, Key-Level, Stop, Take-Profit, R-Multiple,
Slippage und Regelkonformität existieren in den Altjournalen nicht und
bleiben **NULL**. Ein NULL ist ehrlicher als ein rekonstruierter
Schätzwert. Diese Felder füllen sich erst für neue Trades — dafür muss
der Schreibpfad noch angeschlossen werden (offen).

---

## 4. Alle Änderungen mit Backup

| Datei | Änderung | Backup |
|---|---|---|
| `app.py` | V4-Bridge-Block von `:270` nach `:314` verschoben | `app.py.bak_v4bridge_20260804` |
| `agents/v4_strategies.py` | Argmax über rohen Score, Sperre entfernt | `.bak_argmax_20260804` |
| `execution/engine.py` | Sleep-Mode blockiert keine SELLs mehr | `.bak_sleepmode_20260804` |
| `risk/engine.py` | drei `log.risk`-Zeilen | `.bak_logzeilen_20260804` |
| `cockpit_server.py` | E7-Fenster 12:00 UTC | `.bak_e7fix_20260804` |
| `features/doc_agent.py` | Nullbyte-Härtung, zwei Stellen | `.bak_haertung_20260804` |
| `ENTWICKLERHANDBUCH.md` | Nullblock entfernt | `.nullbyte_20260804` |
| `forschung.db` | 48 UPDATE, 2 INSERT-Sätze, 1 neue Tabelle | `.bak_block3_20260804`, `.bak_vor_trades_journal_20260804` |
| `02_EXPERIMENT-REGISTER_v2.0.md` | Nachtrag N1/N2 | `.bak_20260804` |

**Verifikation:** `py_compile` für jede geänderte Python-Datei, `diff`
gegen jedes Backup, AST-Prüfung der Reihenfolge in `app.py`
(Injektion bei 326/327, nach allen Erzeugungen bei 163/289/302/304).

---

## 5. Offen

1. **`min_score` 3 gegen 5/6** — siehe Vorbehalt oben. Braucht Freigabe.
2. **Schreibpfad für `trades_journal`** — neue Trades landen noch nicht
   automatisch in der Tabelle. MFE/MAE/Regelkonformität bleiben leer, bis
   das angeschlossen ist.
3. **Backtest-Blocker:** Kapitaltod des Harness ab ~50 $ und der
   45-Minuten-Look-ahead in `zu_1h()`.
4. **Coin-Reduktion auf BTC/ETH/SOL** — gemessen sinkt die
   Break-even-Hürde von 62,6 % auf 60,0 % bei ±2,5 %/72h, bei praktisch
   unverändertem Informationsgehalt (`N_EFF_COINS = 1,3`, E5 Befund 16).
5. **Prozessstabilität** — drei stille Tode, Ursache weiterhin NICHT
   ENTSCHEIDBAR (`wevtutil` liefert in dieser Umgebung nichts).
