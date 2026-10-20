# Block 2 — Lernt der Bot wirklich?

**Lokal:** 04.08.2026 21:40 (MESZ) · **UTC:** 2026-08-04T19:40Z
**Status:** ERFOLG. Die Frage ist beantwortet — und die Antwort ist
schlechter als der Verdacht.

> **Kein einziger Lernmechanismus in V4 oder V6 verändert eine
> Kaufentscheidung. Der einzige gelernte Wert, der überhaupt eine
> Entscheidung steuert, ist seit 90 Tagen eingefroren und stammt aus
> einem anderen System.**

---

## 2.1 / 2.2 Inventar und Wirkungskette

### V6

| Mechanismus | Datei:Zeile | a) lernt? | b) wird gelesen? | c) fließt in Entscheidung? | d) hat je etwas geändert? | Status |
|---|---|---|---|---|---|---|
| **RLFeedbackAgent** | `models/rl_feedback.py:15-118` | **ja** — `record_trade` `:24-54`, aufgerufen `app.py:1214`; `rl_weights.json` mtime 04.08. 20:36 | `_load` `:81-96` beim Start | **nein** | nein | **SCHREIBT NUR** |
| **V4Calibrator** | `models/v4_calibrator.py:47-131` | **nein** — kein Schreibpfad im Produktivcode | **ja** — `app.py:306` `V4Calibrator.load('v4_data/strategy_stats.json')` | **ja** — `v4_strategies.py:266-271` `ranked_score = raw * weight`, `weight==0.0 → continue` | **ja, dauerhaft** | **WIRKT OHNE ZU LERNEN** |
| **StrategyBrain** | `agents/strategy_brain.py`, `app.py:1600` | ja — `record_trade_result` `app.py:1213` | ja — `select_best` `app.py:1600` | **nur als Fallback** — `signal_agent.py:182` `v4_strategy_used or self.current_strategy`; da der Calibrator fast immer liefert, greift der Fallback praktisch nie | nicht belegbar | **LERNT OHNE WIRKUNG** |
| **brain_performance.json** | `app.py:272-275`, `:1411` | ja (V4-Sync) | ja beim Start | über StrategyBrain, also praktisch nicht | nein | **LERNT OHNE WIRKUNG** |
| **MetaVotingSystem** | `models/meta_voting.py`, `app.py:400/1051/1147` | ja — `evaluate_trade`, `record_prediction` | — kein Leser im Entscheidungspfad gefunden | **nein** | nein | **SCHREIBT NUR** |
| **SignalModel / TrainPipeline** | `models/signal_model.py`, `app.py:409-410/2015` | nur bei Retrain | — | **nein** | nein | **TOT** |
| **AutoRetrainer** | `models/auto_retrain.py`, `app.py:393/2013` | Intervall 168 h | — | nein | nicht belegbar | **NICHT ENTSCHEIDBAR** |
| **regime_model.py** | `models/regime_model.py` | — | **kein einziger Import** außerhalb der Datei | nein | nein | **TOT** |
| **ensemble_signal** | `models/ensemble_signal.py`, `app.py:79` | — | importiert | Ensemble über Quellen, nicht über Strategien | — | anderer Zweck |

### V4

| Mechanismus | Datei:Zeile | a) | b) | c) | d) | Status |
|---|---|---|---|---|---|---|
| **PhaseMemory** | `:1481-1545`; `record` `:1496-1514`, aufgerufen `:2947` | ja, aber nur aus **einem** der zwei Verkaufspfade — `_execute_sell:6146` ruft es **nicht** | ja — `:6072-6073` | **theoretisch ja** (`:6076-6091` PHASE-BLOCK / Bevorzugung) | **nein** | **SCHREIBT NUR** |
| **offline_ki.strategy_performance** | `:1729-1760` | ja — `record_trade_result` `:6166` | ja | Anzeige, Explorations-Schwelle `:6048` | marginal | **LERNT OHNE WIRKUNG** |
| **StrategyEvolver** | `:1627+`, `get_evolved_params` `:6047` | ja | ja | **ja, wenn `evolved_strategy_active`** — setzt `min_score` | nicht belegbar | **NICHT ENTSCHEIDBAR** |
| **ki_analyse_log.json** | 474 378 B, mtime 04.08. 02:42 | ja | — | nein | nein | **SCHREIBT NUR** |

### Der Beweis für PhaseMemory (V4)

`v4_referenz/phase_memory.json`, **204 Bytes**, mtime **07.07.2026** —
seit einem Monat kein Update, obwohl im selben Zeitraum 710 Verkäufe
stattfanden. Inhalt vollständig:

```json
{"MID_BEAR|TRENDING": {"ICHIMOKU_CLOUD": {"wins": 0, "losses": 1,
 "total_pnl": -0.1387, "trades": 1, ...}}}
```

`best_strategy_for` (`:1516-1532`) und `worst_strategies_for`
(`:1534+`) verlangen beide `min_trades=3`. Bei genau **einem** Trade
liefert die erste immer `(None, 0.0)` und die zweite eine leere Liste.
In `_check_trade:6076-6091` bedeutet das: `_pm_bad` ist immer leer, also
kein PHASE-BLOCK; `_pm_best` ist immer `None`, also keine Bevorzugung.

**PhaseMemory hat in V4 nie eine Entscheidung verändert.** Der Bot
protokolliert an einer Stelle, liest an einer anderen, und die
Mindeststichprobe verhindert jede Wirkung.

---

## 2.3 Gewichtsverlauf

### V6 — RL-Gewichte

`data_store/rl_weights.json`: 85 History-Einträge, ausschließlich
**DCA_FEAR_GREED (79)** und **MANUAL_SELL (6)**. Kein weiterer
Strategiename — konsistent damit, dass V6 nur DCA-Trades erzeugt.

| Zeitpunkt | DCA_FEAR_GREED |
|---|---|
| erster Eintrag 2026-06-18 14:27 | 1,100 |
| Spanne über alle 79 Einträge | 1,100 … **1,626** |
| letzter Eintrag 2026-07-27 08:06 | 1,284 |
| **heutiger Stand** | **1,010** |

Die Gewichte **haben sich bewegt** — und wurden anschließend vom
`decay_all`-Scheduler (`app.py:570`, `rl_feedback.py:76-80`, Faktor 0,95
Richtung 1,0) wieder auf 1,01 zurückgezogen. Die Datei-mtime ist 04.08.
20:36, der letzte gelernte Trade vom 27.07.: **seit acht Tagen schreibt
nur noch der Decay.**

Das ist der sauberste denkbare Beleg: Die gesamte Lernleistung wurde
neutralisiert, und es ist niemandem aufgefallen — weil `get_weight()`
und `apply_to_scores()` **nirgends** im Entscheidungspfad aufgerufen
werden. Belegt durch vollständige Suche: die einzigen Aufrufer außerhalb
der Datei selbst sind `tests/test_v6_modules.py:16-21`,
`app.py:2589` (`get_status`, Dashboard) und `ui/main_window.py:3087`
(`len(history)`, Anzeige).

### V6 — die Gewichte, die tatsächlich wirken

`v4_strategy_weights.json`: `computed_at: 2026-05-06T21:14:43`,
mtime 06.05.2026. Diese Datei ist ein **toter Cache** aus
`scripts/migrate_v4_to_v6.py:103` und wird im Produktivpfad gar nicht
gelesen. Gelesen wird `v4_data/strategy_stats.json` (`app.py:306`) —
**mtime ebenfalls 06.05.2026 11:42:23**, und daraus werden die Gewichte
bei jedem Start identisch neu berechnet.

**Konstant seit 90 Tagen. Das ist der Beweis, dass nicht gelernt wird.**

### V4 — Gewichtsverlauf

Es gibt keine Gewichte im eigentlichen Sinn. `strategy_stats.json`
(mtime 04.08. 00:43) wird laufend fortgeschrieben, beeinflusst aber nur
Anzeige und Explorations-Schwelle. Der Argmax in `:6017` läuft über
**rohe** Scores — genau deshalb handeln in V4 elf Strategien.

---

## 2.4 Fehlende Schutzmechanismen — Feststellung, keine Empfehlung

Sollte das Lernen jemals wirksam geschaltet werden, fehlen **alle**
Kontrollen. Ein Bot, der aus den eigenen Trades Gewichte anpasst, lernt
ohne diese Kontrollen Rauschen als Muster:

| Schutz | Zustand | Beleg |
|---|---|---|
| Out-of-Sample-Trennung | **fehlt** | `v4_calibrator._compute_weights:61-104` bewertet dieselben Trades, die die Gewichte erzeugt haben |
| Mindeststichprobe | **teilweise** | `trades < 5 → 0.7` (`:95-97`) ist eine Abschwächung, keine Sperre. RL hat gar keine (`rl_feedback.py:35-42` reagiert auf **einen** Trade) |
| Trial-Zählung / Multiple Testing | **fehlt vollständig** | 13 Strategien werden fortlaufend bewertet, ohne dass diese Vergleiche irgendwo gezählt werden |
| Rückfall auf Champion | **fehlt** | keine Referenzkonfiguration, gegen die eine gelernte Änderung antreten müsste |
| Schutz vor Selbstverstärkung | **fehlt** | Nur ausgeführte Strategien erzeugen Trades, nur Trades erzeugen Gewicht. Gesperrte Strategien (Gewicht 0,0) können sich **nie wieder** rehabilitieren — `v4_strategies.py:267-268` überspringt sie, sie sammeln keine Daten, ihr Gewicht bleibt 0,0. **Eine Einbahnstraße.** |
| Alterung / Wiedervorlage | **fehlt** | nichts erzwingt eine Neuberechnung; 90 Tage alte Zahlen steuern die Auswahl unbemerkt weiter |

Der letzte Punkt ist der gefährlichste und **bereits eingetreten**:
STOCHRSI_REVERSAL wurde am 06.05. auf Gewicht 0,0 gesetzt, weil der
damalige Stand −63,30 $ auswies. Seither ist die Strategie in V6
gesperrt, kann keine Trades erzeugen und damit ihr Gewicht nie
korrigieren — während dieselbe Strategie in V4 parallel weiterläuft.

---

## 2.5 Arbeitet V6 auf V4-Gewichten, die nie zu V6 gehörten? — **Ja**

Zwei getrennte Belege:

**1. `brain_performance.json`** (mtime 27.07.) trägt bei **jeder**
Strategie das Feld `"source": "v4_bootstrap"`. Bei RSI_OVERSOLD:
`v4_baseline_trades: 7`, `v4_baseline_wins: 5`, `v4_baseline_pnl: 88.54`,
`v6_trades_added: 8`, `last_v4_sync_trade_time: "2026-04-27T18:21:16"`.
Die V4-Basis stammt aus **April**.

**2. Schwerwiegender: `v4_data/strategy_stats.json`** (mtime 06.05.) ist
die Quelle **jeder** Strategieauswahl in V6 — und ihr Inhalt ist ein
anderer Datensatz als der, den V4 heute führt:

| Strategie | V6-Quelle (06.05.) | V4 heute (04.08.) | Journal 1 Monat, netto |
|---|---|---|---|
| DCA_FEAR_GREED | **+935,13 $** | +551,04 $ | −93,97 $ |
| EMA_TREND | **+132,96 $** | **−1 658,57 $** | −376,24 $ |
| ICHIMOKU_CLOUD | **+255,58 $** | −31,78 $ | −467,19 $ |
| FIBONACCI_SUPPORT | **+306,69 $** | **−108,43 $** | +2,60 $ |
| TSI_SIGNAL | **+45,13 $** | **−24,96 $** | −92,30 $ |
| MACD_CROSS | **+38,58 $** | **−66,06 $** | −66,05 $ |
| MOMENTUM_BREAKOUT | **+13,83 $** | **−93,74 $** | −87,56 $ |
| RSI_OVERSOLD | +10,03 $ | +92,64 $ | +49,49 $ |
| STOCHRSI_REVERSAL | −63,30 $ | −110,44 $ | **+23,03 $** |

**Bei sechs von zwölf Strategien stimmt nicht einmal das Vorzeichen.**
EMA_TREND geht mit +132,96 $ in die Gewichtung ein und steht real bei
−1 658,57 $ — eine Abweichung von 1 791 $. Die einzige Strategie, die in
allen drei Spalten positiv ist (RSI_OVERSOLD), erhält wegen der
veralteten +10,03 $ das Gewicht **0,434** und verliert damit systematisch
gegen DCA_FEAR_GREED mit **0,909**.

---

## Belege

**Nur gelesen:** `models/{rl_feedback,v4_calibrator,meta_voting,signal_model,regime_model,auto_retrain,ensemble_signal,brain_persistence}.py`,
`agents/{signal_agent,v4_strategies,strategy_brain}.py`, `app.py`,
`data_store/{rl_weights,brain_performance,v4_strategy_weights}.json`,
`v4_data/strategy_stats.json`,
`v4_referenz/{trading_imperium_v4_25_ALARM.py,phase_memory.json,strategy_stats.json}`.

**Nichts geändert.** Keine Lerndatei geschrieben, kein Modell trainiert,
kein Gewicht angepasst.
