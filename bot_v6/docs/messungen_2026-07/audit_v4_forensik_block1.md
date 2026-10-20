# Block 1 — V4-Forensik, read-only

**Lokal:** 04.08.2026 21:30 (MESZ) · **UTC:** 2026-08-04T19:30Z
**Status:** ERFOLG. V4-Ordner ausschließlich gelesen, nichts geändert,
nichts ausgeführt, nichts kopiert.

---

## 1.1 Einstiegs-Verdrahtung — der Pfad in beiden Systemen

### V4, vollständig

| # | Schritt | Datei:Zeile |
|---|---|---|
| 1 | Definition | `v4_referenz/trading_imperium_v4_25_ALARM.py:1061-1130` — `STRATEGIES`, 12 Einträge |
| 2 | Bewertung | `:1133-1289` `evaluate_strategy(strategy_id, df, price, fear_greed)` → `(signal, score 0-9, grund)`, 12 `elif`-Zweige |
| 3 | Datenversorgung | `:861-1041` — `calc_cvd`, `calc_vwap`, `calc_stoch_rsi`, `calc_obv`, `calc_tsi`, `calc_adx`, `calc_ichimoku`, `calc_fibonacci_levels`, `calc_fibonacci_extensions`, `detect_rsi_divergence` |
| 4 | **Auswahl** | `:6014-6019` — `for strat_id in STRATEGIES: … if signal and score > best_score: best_strat = strat_id` |
| 5 | Gates | inline `:5998-6002` (`active_count >= max_trades`, `share < 5.0`), `:6046-6052` (`min_score` 4/5/6), `:6058-6068` (BTC-Trend-Filter), `:6076-6091` (Phase-Memory-Block) |
| 6 | Order | `:6094` `self._execute_buy(coin, price, share, best_strat, best_grund, best_score)` → `:6098-6115` direkt `create_market_buy_order` |
| 7 | Zuordnung | `:6107` `self.trade_strategies[coin] = strategy_id` — die Gewinnerstrategie bleibt an der Position und bestimmt später den Ausstieg (`evaluate_sell`, `:1291-1361`) |

**Es gibt in V4 kein zentrales Risiko-Gate zwischen Auswahl und Order.**
Die Gates sind Vorbedingungen im selben Codeblock.

### V6, derselbe Pfad

| # | Schritt | Datei:Zeile |
|---|---|---|
| 1 | Definition | `agents/strategy_brain.py:15` (13 Einträge) **und** `agents/v4_strategies.py:29-35` (7 im Ensemble) — zwei getrennte Registries |
| 2 | Bewertung | `agents/v4_strategies.py:86-237` (7 Methoden) + `agents/signal_agent.py:78-146` (ein additiver Score) |
| 3 | Datenversorgung | `features/indicators.py:9-43`, `data/market_data.py:62-79` — **ohne** ICH_*, ohne Vol_high |
| 4 | **Auswahl** | `agents/v4_strategies.py:262-277` — Argmax über `raw * calibrator.get_weight(sid)`, mit `if weight == 0.0: continue` |
| 5 | Score-Einbau | `agents/signal_agent.py:151-166` — das Ergebnis wird zu **+2/+3/+4 Punkten** in einem additiven Gesamtscore |
| 6 | Schwelle | `agents/signal_agent.py:169-170` `min_score = 3` |
| 7 | Etikett | `agents/signal_agent.py:182` `strategy_id=v4_strategy_used or self.current_strategy` |
| 8 | Risiko-Gate | `risk/engine.py:76-134` `check()` — drei stille Frühabbrüche `:88-93`, `:98-102`, `:104-108` |
| 9 | Order | über Bus → `execution/` |
| 10 | Zweiter Kaufpfad | `app.py:1844` — DCA, `strategy_id="DCA_FEAR_GREED"` **hart verdrahtet** |

### Der Vergleich, Schritt für Schritt

| Schritt | V4 | V6 | Unterschied | Folge |
|---|---|---|---|---|
| Registry | `:1061` 12 Strategien, eine Quelle | `strategy_brain.py:15` (13) + `v4_strategies.py:29` (7) | zwei Registries, unterschiedlicher Umfang | 5 Strategien haben in V6 gar keinen Bewerter |
| Bewertung | 12 unabhängige Bewerter, roher Score 0-9 | 7 Bewerter + ein additiver Gesamtscore | Strategien sind Summanden statt Kandidaten | Einzelsignale verschwinden in der Summe |
| **Auswahl** | **Argmax über rohen Score** `:6017` | **Argmax über `raw × weight`** `v4_strategies.py:266-271` | Gewichte entscheiden statt Signalstärke | **die Kernursache** |
| Sperre | keine | `if weight == 0.0: continue` `:267-268` | vier Strategien komplett übersprungen | STOCHRSI, RSI_DIV, BOLLINGER, MULTI feuern nie |
| Schwelle | `min_score` 5 bzw. 6 `:6050-6053` | `min_score = 3` `signal_agent.py:169` | V6 kauft bei halbem Score | 31 124 BUY-Signale/24 h gegen V4s 726 BUYs/Monat |
| Risiko-Gate | inline, protokolliert über `add_log` | `RiskEngine.check()`, drei stille Returns | Ablehnungen unsichtbar | Multi-Strategy-Bug |
| Zuordnung | `trade_strategies[coin]` steuert den Ausstieg `:6107` | ID ist nur ein Journal-Etikett | Strategie ohne Wirkung auf den Exit | Ein-/Ausstieg entkoppelt |

### Der EINE Unterschied

**V4 wählt zwischen Strategien. V6 summiert sie und vergibt das Etikett
nachträglich anhand eingefrorener Gewichte.**

- V4: `trading_imperium_v4_25_ALARM.py:6014-6019` + `:6094`
- V6: `agents/v4_strategies.py:262-277` + `agents/signal_agent.py:151-182`

Die Gewichte stammen aus `v4_data/strategy_stats.json`, geladen bei
`app.py:306`. **mtime dieser Datei: 06.05.2026 11:42:23 — seit 90 Tagen
eingefroren.** Der Docstring von `evaluate_buy` (`v4_strategies.py:245-248`)
beschreibt die Wirkung selbst:

> *„so gewinnt z.B. DCA_FEAR_GREED (Gewicht 0.91) mit Score 8 gegen
> RSI_OVERSOLD (Gewicht 0.43) mit Score 9"*

Die daraus berechneten Gewichte (`data_store/v4_strategy_weights.json`,
identisch reproduzierbar über `models/v4_calibrator.py:61-104`):

| Strategie | Gewicht | Wirkung |
|---|---|---|
| DCA_FEAR_GREED | **0.909** | gewinnt fast jeden Argmax |
| FIBONACCI_SUPPORT | 0.822 | konkurrenzfähig |
| TSI_SIGNAL | 0.820 | konkurrenzfähig |
| ICHIMOKU_CLOUD | 0.734 | ohne Daten wirkungslos |
| MACD_CROSS | 0.633 | |
| EMA_TREND | 0.540 | |
| MOMENTUM_BREAKOUT | 0.437 | ohne Daten wirkungslos |
| RSI_OVERSOLD | **0.434** | halbiert gegen DCA |
| BOLLINGER_BOUNCE | **0.0** | `continue` — feuert nie |
| RSI_DIVERGENCE | **0.0** | `continue` — feuert nie |
| **STOCHRSI_REVERSAL** | **0.0** | `continue` — feuert nie |
| MULTI_SIGNAL | **0.0** | `continue` — feuert nie |

**Die Strategie mit der höchsten Trefferquote im V4-Journal (STOCHRSI_
REVERSAL, WR 94 %) ist in V6 hart gesperrt.** Die Sperre kommt aus
`v4_calibrator.py:44` (`DANGER_ZONE`) in Verbindung mit `:88-91`
(`total_pnl < 50 → 0.0`) und dem Stand vom 06.05., der für STOCHRSI
−63,30 $ auswies.

---

## 1.2 Was bei der Fusion verloren ging

| Element | in V4 | in V6 | Status | Bedeutung für die Einstiegsvielfalt |
|---|---|---|---|---|
| Argmax-Selector über rohe Scores | `:6014-6019` | — | **FEHLT** | **entscheidend** — ohne ihn gibt es keine Auswahl zwischen Strategien |
| `evaluate_strategy` 12 Zweige | `:1133-1289` | 7 Methoden `v4_strategies.py:86-237` | **TEILWEISE** | 5 Strategien ohne Bewerter |
| `calc_ichimoku` | `:914-922` | — | **FEHLT** | ICHIMOKU in V6 nicht berechenbar (`v4_strategies.py:128` prüft `ICH_tenkan`, findet nichts) |
| `Vol_high` / Volume-Spike-Flag | im Momentum-Zweig `:1215-1223` | — | **FEHLT** | MOMENTUM_BREAKOUT tot |
| `calc_stoch_rsi` | `:870-873` | `features/indicators.py:69` | **VORHANDEN, ungenutzt** | StochRSI wird berechnet, aber keine Strategie wertet sie aus |
| `calc_tsi` | `:887-894` | vorhanden | **VORHANDEN** | TSI in V6 testbar |
| `calc_fibonacci_extensions` | `:940-1019` | — | **FEHLT** | nur Retracements in V6 |
| `evaluate_sell` je Strategie | `:1291-1361`, 10 Zweige | `v4_strategies.py:280+` portiert, aber **nicht im Exit-Pfad** | **ANDERS** | V6-Exit läuft zentral über `runtime/exit_monitor.py` |
| Strategie-gebundener Exit | `trade_strategies[coin]` `:6107` | ID ohne Wirkung | **FEHLT** | Ein-/Ausstieg entkoppelt |
| `min_score` 5/6 | `:6050-6053` | 3 | **ANDERS** | V6 kauft bei halbem Konsens |
| BTC-Trend-Filter | `:6058-6068` | — | **FEHLT** | kein Altcoin-Schutz im Abwärtstrend |
| PhaseMemory-Block/Bevorzugung | `:6076-6091` | — | **FEHLT** (V6 hat eigenen StrategyBrain) | in V4 ohnehin wirkungslos, siehe Block 2 |
| StrategyEvolver | `:1627+` | — | **FEHLT** | — |
| Zentrales Risiko-Gate | — | `risk/engine.py:76` | **NEU in V6** | bringt die stillen Frühabbrüche mit |
| Zweiter DCA-Kaufpfad | — | `app.py:1844` | **NEU in V6** | ID hart auf DCA_FEAR_GREED verdrahtet |

**Nichts übernommen. Nur dokumentiert.**

---

## 1.3 Die drei positiven Strategien

### Einstiegsbedingungen, wörtlich aus V4

**RSI_OVERSOLD** (`:1145-1156`) — RSI unter 30 (Score 9), unter 35
(Score 7), unter 45 bei ADX < 25 (Score 5), unter 48 bei ADX < 20
(Score 4).

**FIBONACCI_SUPPORT** (`:1263-1275`) — `calc_fibonacci_levels(df)`;
|Preis − Fib78.6|/Preis < 0,005 **und** RSI < 40 (Score 9); oder
|Preis − Fib61.8|/Preis < 0,005 (Score 7); oder |Preis − Fib38.2|/Preis
< 0,005 **und** MACD bullisch (Score 5).

**STOCHRSI_REVERSAL** (`:1236-1244`) — StochRSI aus dem Bereich < 20
nach oben drehend.

### Ausstiegsregeln

`evaluate_sell` (`:1291-1361`) je Strategie plus ein globaler
Trailing-Stop (`trail_pct`, Vorgabe 1,0 %). Der Ausstieg ist **an die
Einstiegsstrategie gebunden** (`:6165` `strat = strategy_id or
self.trade_strategies.get(coin, …)`).

### Brutto oder netto? — Der Befund, der alles entscheidet

`PaperExchange` verrechnet Kosten **implizit in der Ausführung**
(`:741-767`): BUY `price*1.001` und `qty=(quote/price)*0.999`,
SELL `price*0.999` und `quote=qty*price*0.999`. Roundtrip **0,4 %**.

**Aber `_execute_sell:6151-6154` verwirft den Rückgabewert der Order und
rechnet:**

```python
self.exchange.create_market_sell_order(coin, qty, self.data_client)   # Ergebnis verworfen
entry = self.dca_avg_price.get(coin) or self.entry_prices.get(coin, price)
pnl = (qty * price) - (qty * entry)      # price = MARKTPREIS, nicht Fill-Preis
```

Die journalisierte `pnl` enthält damit die Verkaufsseite (0,1 %
Slippage + 0,1 % Fee) **überhaupt nicht**, und die Kaufseiten-Fee wurde
als Mengenabzug realisiert und fällt aus der Differenzformel heraus.
**Die V4-Zahlen sind brutto um rund 0,3 % des Positionswerts je Trade.**

Korrektur, gerechnet in `docs/messungen_2026-07/code/audit_v4_journal.py`
über den tatsächlichen Einsatz je Position (Erstkauf + alle Nachkäufe):

| Strategie | Sells | pnl roh | Einsatz | fehlende Gebühr | **pnl netto** | je Trade |
|---|---|---|---|---|---|---|
| RSI_OVERSOLD | 93 | +125,36 $ | 25 290 $ | 75,87 $ | **+49,49 $** | +0,532 $ |
| STOCHRSI_REVERSAL | 32 | +58,29 $ | 11 752 $ | 35,26 $ | **+23,03 $** | +0,720 $ |
| FIBONACCI_SUPPORT | 69 | +71,89 $ | 23 097 $ | 69,29 $ | **+2,60 $** | **+0,038 $** |
| *alle 12 zusammen* | 710 | −470,73 $ | — | — | **−1 157,92 $** | — |

FIBONACCI_SUPPORT verdient nach Kosten **3,8 Cent pro Trade**. Das ist
kein Vorteil, das ist Rauschen um die Null.

### DCA-Anhang je Strategie

DCA-Einträge tragen kein `strategy`-Feld. Rekonstruiert über offene
Position je Coin (Erstkauf setzt die Strategie, jeder folgende Kauf und
jedes DCA bis zum Verkauf wird ihr zugeschlagen):

| Strategie | Erstkäufe | Erstvolumen | DCA-Käufe | DCA-Volumen | DCA/Erst |
|---|---|---|---|---|---|
| RSI_OVERSOLD | 94 | 19 820 $ | 140 | 5 775 $ | 0,29× |
| FIBONACCI_SUPPORT | 76 | 19 185 $ | 119 | 5 054 $ | 0,26× |
| STOCHRSI_REVERSAL | 32 | 10 851 $ | 34 | 1 196 $ | 0,11× |
| ICHIMOKU_CLOUD | 251 | 59 823 $ | 361 | 15 294 $ | 0,26× |
| EMA_TREND | 158 | 39 855 $ | 278 | 12 269 $ | 0,31× |

Nicht zuordenbar: 6 DCA-Einträge über 509,78 $. Der DCA-Effekt selbst
steckt bereits in der pnl, weil `entry = dca_avg_price` verwendet wird.

### Kausalität — besonders Fibonacci

`calc_fibonacci_levels(df, lookback=50)` (`:924-938`) nimmt
`df['High'].tail(lookback).max()` und `df['Low'].tail(lookback).min()`.
`df` endet zum Signalzeitpunkt beim letzten geschlossenen Balken.
**Swing-High und Swing-Low liegen damit vollständig in der
Vergangenheit — kein Look-ahead.** Der Anker ist allerdings ein
gleitendes Extremum ohne Bestätigungsregel: er springt, sobald ein neues
Extrem ins Fenster wandert. Das ist kein Zukunftszugriff, aber auch keine
stabile Struktur.

### Urteil je Strategie

| Strategie | Urteil | Begründung |
|---|---|---|
| RSI_OVERSOLD | **KOSTEN_UNVOLLSTAENDIG** | netto +49,49 $ statt +125,36 $; bleibt positiv, aber 87,1 % der Summe stammen aus drei Trades |
| STOCHRSI_REVERSAL | **KOSTEN_UNVOLLSTAENDIG** | netto +23,03 $; in V4s eigener kumulativer Buchhaltung −110,44 $ über 57 Trades |
| FIBONACCI_SUPPORT | **KOSTEN_UNVOLLSTAENDIG** | netto +2,60 $ über 69 Trades; ohne die drei besten Trades **−15,57 $** |

Kein Look-ahead nachweisbar. Keine ist REPRODUZIERBAR_POSITIV.

---

## 1.4 Warum der Widerspruch zum Barrierentest — und wie fragil das ist

### Verteilung

| Strategie | n | Summe | Median | p10 | p90 | größter Verlust | Top-3 Anteil | ohne Top-3 |
|---|---|---|---|---|---|---|---|---|
| RSI_OVERSOLD | 93 | +125,36 $ | +1,75 $ | −9,95 $ | +5,72 $ | −36,98 $ | **87,1 %** | +16,23 $ |
| FIBONACCI_SUPPORT | 69 | +71,89 $ | +3,39 $ | −13,68 $ | +10,56 $ | −42,73 $ | **121,7 %** | **−15,57 $** |
| STOCHRSI_REVERSAL | 32 | +58,29 $ | +0,89 $ | +0,17 $ | +5,05 $ | −9,36 $ | 63,8 % | +21,11 $ |

### Tail-Risiko

| Strategie | größter Verlust | Ø Gewinn | frisst … Gewinner | Gewinner | Puffer |
|---|---|---|---|---|---|
| RSI_OVERSOLD | −36,98 $ | 4,03 $ | 9,2× | 78 | 8,5× |
| FIBONACCI_SUPPORT | −42,73 $ | 7,69 $ | 5,6× | 48 | 8,6× |
| STOCHRSI_REVERSAL | −9,36 $ | 2,45 $ | 3,8× | 30 | 7,9× |

### Antwort

**Beides stimmt, und der Widerspruch ist kleiner als er aussieht.**

Der Barrierentest misst „berührt der Kurs zuerst +B oder −B" — eine
symmetrische Frage. V4 handelt asymmetrisch: viele kleine Gewinne
(Median +0,89 bis +3,39 $), seltene große Verluste (bis −42,73 $). Ein
Richtungsvorteil unterhalb der Kostenschwelle kann so in einen positiven
Erwartungswert übersetzt werden — solange die Verlustseite nicht zuschlägt.

Wie tragfähig das ist, zeigen drei Zahlen:

1. **Die Serie hängt an Ausreißern.** Bei RSI_OVERSOLD machen drei von
   78 Gewinnern 87,1 % des Ergebnisses. Bei FIBONACCI_SUPPORT sind es
   121,7 % — ohne die drei besten Trades ist die Strategie **negativ**.
2. **Nach Gebühren bleibt fast nichts.** FIBONACCI +0,038 $/Trade,
   RSI_OVERSOLD +0,532 $/Trade bei einem größten Einzelverlust von
   −36,98 $: **70 gewinnende Trades**, um einen einzigen solchen Verlust
   auszugleichen.
3. **V4s eigene Buchhaltung widerspricht.** `v4_referenz/strategy_stats.json`
   (mtime 04.08. 00:43, kumulativ) führt FIBONACCI_SUPPORT mit
   **−108,43 $** über 168 Trades und STOCHRSI_REVERSAL mit **−110,44 $**
   über 57 Trades. Nur RSI_OVERSOLD ist auch dort positiv (+92,64 $ über
   141 Trades).

**Zwei der drei „positiven" Strategien sind über die volle Historie klar
negativ und waren nur im Messmonat positiv.** Der Vorbehalt „ein Monat,
ein Regime" aus der Auftragsstellung ist damit nicht theoretisch — er ist
gemessen.

---

## Belege

**Skript:** `docs/messungen_2026-07/code/audit_v4_journal.py` (read-only)
**Ausgabe:** `docs/messungen_2026-07/ausgaben/audit_v4_journal_out.txt`
**Eingabe:** `v4_referenz/trades_log_v4.json` (2 719 Einträge,
2026-07-05T00:20:42 bis 2026-08-04T00:35:16),
`v4_referenz/strategy_stats.json`, `v4_data/strategy_stats.json`
**Formel Gebührenkorrektur:** `netto = pnl_roh − Einsatz × (0,002 + 0,001)`
**Ausschlüsse:** 6 nicht zuordenbare DCA-Einträge (509,78 $); Strategien
mit weniger als 3 Verkäufen in der Verteilungstabelle.

**Nur gelesen in V4:** `trading_imperium_v4_25_ALARM.py`,
`trades_log_v4.json`, `strategy_stats.json`, `phase_memory.json`.
**Nichts geändert, nichts ausgeführt, nichts kopiert.**
