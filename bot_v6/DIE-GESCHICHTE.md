# Trading Imperium V6 — Die Geschichte

**Stand: 29.07.2026, nach dem E9/E10-Umbau**
*Was gebaut wurde, was drin ist, was es tut, was es kostete, und was zwischen hier und Echtgeld liegt.*

---

## Teil 1 — Was das Ding eigentlich ist

Ein automatischer Krypto-Handelsbot, in Python, für Binance Spot. Er läuft als ein
Prozess (`python app.py`), öffnet ein Fenster, verbindet sich per WebSocket an die
Kursversorgung und arbeitet danach in Schleifen, die ein Scheduler alle paar
Sekunden anstößt.

Er ist über Monate gewachsen. Das merkt man ihm an: 44.000 Zeilen Python in
rund 200 Modulen, dazu ein Wildwuchs an Installer-Skripten, Handbüchern und
Sicherungskopien. Der Kern ist klein, drumherum liegen viele Schichten, die
irgendwann angeflanscht wurden.

**Die ehrliche Kurzfassung vor dem 29.07.:** Der Bot hat in 944 Journal-Einträgen
eine Trefferquote von 71,9 % erreicht — und dabei Geld verloren. Das ist kein
Widerspruch, sondern die Signatur eines ganz bestimmten Fehlers. Dazu Teil 4.

---

## Teil 2 — Der Aufbau

### Der Datenfluss, in einem Satz

Kurse rein → Indikatoren → Signal → Risikoprüfung → Order → Position → Ausstieg → Journal.

### Ausführlich

```
  data/market_data + websocket_stream
        │  Kerzen (1h) und Live-Preise
        ▼
  features/indicators + regime_detection + multi_timeframe
        │  RSI, MACD, EMA, ADX, ATR, Bollinger, VWAP, RSI-Divergenz
        │  Regime: TRENDING_UP / TRENDING_DOWN / RANGING
        ▼
  agents/strategy_brain  ──  wählt die Strategie zur Marktlage
        │  (in der Praxis fast immer: DCA_FEAR_GREED)
        ▼
  agents/signal_agent  +  models/ensemble_signal
        │  Punktesystem 0–10, ab 3 Punkten ein Kaufwunsch
        ▼
  risk/engine  ──  Vetorecht: Kill-Switch, Drawdown, Exposure, Cooldown
        ▼
  portfolio/agent  ──  Klumpenrisiko, Sektor-, Korrelationsgrenzen
        ▼
  execution/engine  ──  Order (Papier simuliert, Live über ccxt)
        ▼
  risk_engine.open_positions  ──  das Positionsregister im Arbeitsspeicher
        ▼
  runtime/exit_monitor  ──  alle 30 s: Stop-Loss, Trailing, Breakeven
        ▼
  data_store/trades_v5.json  ──  das Journal
```

### Die Ordner und was sie wirklich tun

| Ordner | Inhalt | Zustand |
|---|---|---|
| **(Wurzel)** | `app.py` (2.600 Zeilen, das Herz), `go_live_check.py`, `cockpit_server.py`, dutzende Installer | Kern + Werkzeugkasten |
| **core/** | `logger`, `state_store` (StateStore **und** TradeJournal), `scheduler`, `events`/`bus`, `health`, `balance_reporter` | Fundament |
| **agents/** | `signal_agent` (Kaufsignale), `dca_advanced`, `grid_trader`, `btc_accumulator`, `context_agent`, `strategy_brain` | Kern |
| **runtime/** | `exit_monitor` (**die** Ausstiegs-Autorität), `state_manager` (Speichern/Wiederherstellen), `reporting` | Kern |
| **risk/** | `engine` (Veto), `coin_stops`, `exit_rules` (neu), `reentry_guard` (neu), `drawdown_guard`, `kill_switch`, `regime_profiles` | Kern |
| **execution/** | `engine` (Papier + Live), `order_manager`, `idempotency`, `retry_policy`, `circuit_breaker`, `twap_executor`, `multi_exchange` | Kern |
| **data/** | `market_data`, `websocket_stream`, `sentiment_data` (F&G), `funding_rates`, `orderbook_depth`, `whale_alerts`, `reddit_sentiment`, `nupl_monitor`, `dxy_monitor`, `source_health` (neu) | Kern + tote Äste |
| **portfolio/** | `manager` (Kapital), `agent` (Allokation), `daily_loss`, `correlation_guard`, `rebalancer` | Kern |
| **models/** | `xgboost_model`, `ensemble_signal`, `meta_voting`, `rl_feedback`, `train_pipeline` | geladen, aber wirkungslos (Teil 4) |
| **features/** | `sensei`, `doc_agent` (schreibt Handbuch + Tagesbericht), `impact_journal`, `situation_memory`, `tickets_watcher` | Lern-/Doku-Schicht |
| **ui/** | `main_window` (3.100 Zeilen), `terminal_tab`, `chart_view`, `dashboard` (Web, Port 5050) | funktional, ungeprüft |
| **data_store/** | **Die Daten.** `trades_v5.json` (Journal), `bot_state.json`, `config.json`, Modelle, Logs | Herzkammer |

### Die vier Dateien, auf die es ankommt

1. **`data_store/trades_v5.json`** — jeder Kauf und Verkauf. Die Buchführung.
2. **`data_store/bot_state.json`** — Positionen, Papier-Bestände, Zähler. Überlebt Neustarts.
3. **`data_store/config.json`** — alle Stellschrauben. **Nur bei gestopptem Bot anfassen.**
4. **`.env`** — API-Schlüssel. Gehört nirgendwo hin außer auf diese Festplatte.

### Was gleichzeitig läuft

Der Scheduler (`core/scheduler.py`) startet ~20 Aufgaben in eigenen Threads:

| Aufgabe | Takt | Was sie tut |
|---|---|---|
| `sl_tp_monitor` | 30 s | **Die wichtigste.** Prüft jede Position auf Ausstieg. Läuft unabhängig vom Handels-Loop. |
| `trading_loop` | 12 s | Kurse holen, Signale bilden, DCA-Runde |
| `auto_save` | 30 s | Zustand sichern |
| `signal_update` | 120 s | Externe Quellen |
| `health_check` | 60 s | Selbsttest |
| `tickets_watcher` | 30 s | liest `tickets.txt` ins Handbuch |
| `daily_report` | 24 h | Tagesbericht |

Dass der Ausstiegs-Monitor **getrennt** vom Handels-Loop läuft, ist die wichtigste
Architekturentscheidung im ganzen System: hängt die Kursversorgung, laufen die
Stop-Losses trotzdem.

---

## Teil 3 — Was er handelt

**Eine Strategie, faktisch.** Das Journal ist eindeutig: **521 von 521 Käufen**
trugen die Signatur `DCA_FEAR_GREED`.

Die Regel ist simpel: Steht der Fear-&-Greed-Index unter 30, kauft der Bot.
Fällt ein Coin danach 2 % unter den eigenen Einstand, kauft er nach und mittelt
den Einstand herunter. Verkauft wird über Stop-Loss oder Trailing.

**Der ganze Rest hat nie eine einzige Order ausgelöst — er rechnet aber sehr wohl mit.**
Punktesystem, Ensemble und V4-Brücke fließen real in `signal_agent.analyze()` ein
(Ensemble bis +2 Punkte, V4 bis +4, bei einer Kaufschwelle von 3). Sie werden also
*benutzt* — nur führt ihr Pfad nie zu einer ausgeführten Order, weil die fünf
Positionsplätze dauerhaft von der DCA-Maschine belegt sind. Jeder Signal-Kauf
scheitert an „Bereits in Position" oder „Max Positionen".

> **Wie das belegt ist** (Prüfauftrag 29.07., Teil A): *nicht* über die
> Strategie-Spalte im Journal — die taugt dafür nicht. `DCA_FEAR_GREED` ist auch
> eine gültige Brain-ID, ein Signal-Kauf wäre also genauso etikettiert worden.
> Der Nachweis läuft über die Feld-Signatur: der Signal-Pfad
> (`_execute_approved_trade`, app.py:1016) schreibt `score`, `confidence`,
> `signal_reasons`, `market_regime`, `latency_ms`; der DCA-Pfad (app.py:1866)
> kennt keins davon. Ergebnis: **0 von 523 Käufen** tragen eines dieser Felder,
> während **81 von 425 Verkäufen** sie tragen — die Funktion lief also, hat aber
> nie einen Kauf erzeugt.
>
> **XGBoost ist ein Sonderfall:** Es wird geladen, sein Score erreicht das
> Ensemble aber nie. `EnsembleSignal.WEIGHTS` kennt die Schlüssel `ml_model`
> (0,20) und `vwap` (0,07) — `app.py` liefert beide nicht. 27 % des
> Ensemble-Gewichts sind unbesetzt.

Im Log sieht man das im Minutentakt:

```
[SIGNAL] ETH/USDC: Score 3/10 (30%) -> BUY 10.99$ | RSI niedrig (43) ...
```

— und danach passiert nichts. Das ist kein Fehler im engeren Sinn, aber es
bedeutet: du wartest und bezahlst Rechenzeit für eine Maschinerie, die stillsteht.

---

## Teil 4 — Was schiefging (der interessante Teil)

### Die Zahl, die alles erklärt

Über 423 Verkäufe:

| Kennzahl | Wert |
|---|---|
| Trefferquote | **71,9 %** |
| Mittlerer Gewinn | +0,689 $ |
| Mittlerer Verlust | −1,991 $ |
| **Chance/Risiko** | **0,35** |
| Summe | −27,57 $ (gebucht) |
| Summe wirklich | **≈ −47 $** |

Sieben von zehn Trades gewinnen — und trotzdem Minus. Weil jeder Verlust fast
dreimal so groß ist wie jeder Gewinn. Das ist das älteste Muster der Branche:
Gewinne mitnehmen, Verluste laufen lassen. Nur dass es hier keine menschliche
Schwäche war, sondern in Code gegossen.

### Die zwölf Defekte (E9, 29.07.)

**1. Der Gebühren-Kreisel** — der teuerste.
338 Wiederkäufe desselben Coins **binnen 15 Minuten** nach einem Verkauf, davon
**319 zu einem höheren Preis**. Beispiel aus dem echten Journal:

```
14:39:39  SELL BTC @ 64.018,99   Trailing-Stop, +1,51 %
14:39:59  BUY  BTC @ 64.131,68   DCA — 20 Sekunden später, 0,18 % teurer
```

Der DCA-Agent kannte nur eine Sperrfrist seit dem letzten **Kauf**. Nach einem
Ausstieg war die längst abgelaufen. Kosten je Runde ~0,4 % — auf 18.600 $
gedrehtes Volumen rund **70 $**.
→ Behoben: `risk/reentry_guard.py`. 90 Minuten Sperre **und** Wiedereinstieg nur
mindestens 1 % unter dem Ausstiegspreis.

**2. Die Kaufgebühr fehlte in jeder P&L.**
Beim Kauf gilt `Menge = (Betrag − Gebühr) / Preis`. Die Gewinnrechnung nahm aber
`Menge × Einstand` als Kosten — die Gebühr war damit unsichtbar. Jeder Trade
wurde um 0,1 % des Volumens zu gut gebucht: **≈ 19 $ Phantomgewinn** in einer
Bilanz, die −27,57 $ auswies.
→ Behoben: `cost_basis` je Position, echter Mittelabfluss inklusive Gebühr.

**3. Der Trailing-Stop feuerte nach jedem Nachkauf sofort.**
Beim Mitteln wurde der Einstand neu berechnet, der **Höchstkurs aber nicht
zurückgesetzt**. Der Monitor maß den Rückfall gegen ein Hoch, das zum alten,
höheren Einstand gehörte. Sobald die Position knapp ins Plus drehte, war der
gemessene Rückfall riesig — Ausstieg bei +0,4 %.
→ Behoben: Höchststände werden beim Mitteln zurückgesetzt.

**4. Die Hauptstrategie lief an der Risikoprüfung vorbei.**
Der DCA-Pfad rief die Ausführung direkt auf. Kein Kill-Switch, kein
Drawdown-Guard, kein Schlafmodus, keine Korrelationsprüfung. `dca_max_levels`
stand auf 3 und war **nirgends verdrahtet** — die Nachkauf-Leiter war unbegrenzt.
Da der Einstand beim Mitteln fällt, wird die nächste −2-%-Schwelle im Abwärtstrend
immer leichter erreicht: Martingale ohne Boden. Ergebnis im Depot: **651 ADA =
28 % des Kapitals in einem Coin**, bei einem Limit von 25 %.
→ Behoben: Risiko-Tore, Nachkauf-Deckel, Exposure-Prüfung im DCA-Pfad.

**5. Das Journal-Backup wurde nie geschrieben.**
`shutil` war nur lokal in einer anderen Methode importiert. `TradeJournal._save()`
warf bei jedem Speichern einen `NameError` — verschluckt von `except Exception`.
Nach 944 Speichervorgängen existierte **kein einziges** `trades_v5.json.bak`.
Die dokumentierte Absturzsicherung der Buchführung war seit jeher tot.

**6. Die Trailing-Leiter war logisch verdreht.**
```
alt:  ab +5 % → 0,5 % Trail   |   ab +3 % → 0,7 %   |   ab +1 % → 1,0 %
```
Je höher der Gewinn, desto **enger** der Ausstieg. Bei einem Stundenrauschen von
0,5–1,0 % wird jeder Trade über +3 % von der nächsten normalen Schwankung
hinausgeworfen. Der Beweis steht im Journal: **größter Gewinn in 423 Verkäufen:
+4,64 %**. Die Leiter war die Decke, nicht der Markt.
Dazu ein zweiter Fehler: der Faktor kam aus dem *aktuellen* Gewinn — fiel der
Kurs, weitete sich der Stop rückwirkend. Keine Ratsche, sondern eine bewegliche
Zielscheibe.
→ Behoben: `risk/exit_rules.py`. Faktor am **Höchststand**, monoton weiter
werdend, plus Breakeven-Sperre ab +1 %.

**7–12.** Scheduler-Wettlauf (Task konnte doppelt starten → Doppelkauf) ·
Tagesverlust-Wächter rechnete UTC gegen Ortszeit und lief zudem im wirkungslosen
Schattenmodus · `total_equity` war nur das Bargeld, nicht das Kapital · der
Live-Pfad buchte **jede** Börsenantwort als Vollausführung, auch abgelehnte ·
Papier-Einstand wurde beim Nachkauf überschrieben · Wiederherstellung erfand den
Einstand.

### Die vier Defekte aus dem laufenden Betrieb (E10, 29.07. abends)

**13. Ein Kapitalloch von 96,54 $.**
Der BTC-Sparplan zieht USDC vom Papier-Konto ab, bucht die gekauften BTC aber
**nur in seine eigene Datei**. In `get_balance()` taucht sie nicht auf. 27 Käufe,
96,01 $ investiert.

```
Der Bot meldete:      370,60 $   (−25,9 %)
Tatsächlich waren es: 467,14 $   (−6,6 %)
```

Auf der zu kleinen Bezugsgröße rechneten Positionsgröße, Exposure-Grenzen,
Drawdown-Wächter und das Tagesstart-Kapital.
→ Behoben: Der Sparplan wird als eigener Kapitaltopf gezählt und ausgewiesen —
aber bewusst **nicht** in die handelbaren Bestände gemischt, sonst würde ihn die
Wiederherstellung als Position vereinnahmen und beim nächsten Stop mitverkaufen.

**14. Der Tagesbericht brach seit Wochen ab.** `[DOC] Daily-Report Fehler: 'symbol'`
— zwei Schemata für denselben Puffer: ein Pfad schrieb `coin`, der Bericht las
`symbol`.

**15. Der Reset-Knopf hat nie zurückgesetzt.** `journal.clear()` fehlte und wurde
zur Laufzeit angeflanscht — der Ersatz griff auf `trades` statt `_trades` zu. Er
legte ein neues, leeres Attribut an, während gespeichert wurde, was schon da war.

**16. Tote Datenquellen zählten voll mit.** Reddit liefert 403, gibt still
`score: 0.5` zurück — und ging mit 30 % Gewicht in den Zusatz-Score ein. Eine tote
Quelle trug nicht *nichts* bei, sie zog jedes echte Signal Richtung neutral.
→ Behoben: `data/source_health.py`. Ausgefallene Quellen fallen aus der
Gewichtung; ihr Gewicht verteilt sich auf die lebenden.

---

## Teil 5 — Was jetzt anders läuft

### Die neue Ausstiegsregel

```
unter +1,0 %      nur Stop-Loss, kein Trailing
+1,0 % erreicht   Breakeven-Sperre scharf: fällt der Gewinn unter +0,25 %,
                  wird glattgestellt. Ein Gewinner wird nie wieder Verlierer.
ab +1,2 %         Trailing, Faktor am Höchststand (Ratsche):
                     +1,2 % → 1,0×      (alt: 1,0× — bewusst gleich)
                     +3,0 % → 1,3×      (alt: 0,7× ← hier wurde gewürgt)
                     +5,0 % → 1,7×      (alt: 0,5×)
                     +8,0 % → 2,2×
TRENDING_UP       ×1,3 auf alles
```

Am Median-Höchststand (2,36 %) ist das Verhalten **identisch** zu vorher. Unter
+1,5 % strikt besser. Über +3 % gibt es mehr Rauschtoleranz — im Tausch gegen
mehr Rückgabe, wenn es doch dreht. Details und Rückdrehwert stehen im Kopf von
`risk/exit_rules.py`.

> ### ⚠️ Nachtrag 29.07. abends — es gibt jetzt ein Messergebnis, und es spricht dagegen
>
> Hier stand ursprünglich „das ist eine begründete Wette, kein Messergebnis".
> Inzwischen liegt eines vor: ein Backtest über zwei volle Jahre 15-Minuten-Kerzen
> (2024-07…2025-07 Bulle, 2025-07…2026-07 Bär), 11 Coins, identische Einstiege,
> nur die Ausstiegsregel getauscht, Gebühren 0,2 % Roundtrip und Slippage drin.
>
> | | Bärenjahr | Bullenjahr |
> |---|---|---|
> | alte Leiter | −450,12 $ | **−290,00 $** |
> | neue Ratsche + Breakeven | −450,56 $ | −313,44 $ |
>
> Über **nicht überlappende** 60-Tage-Fenster ist die neue Regel in **1 von 9**
> Fenstern besser, p = 0,039 (zweiseitiger Vorzeichentest). Bei drei gegen
> dieselbe Grundlinie geprüften Varianten und Bonferroni-Korrektur: p ≈ 0,12 —
> **nicht signifikant.**
>
> **Die Zerlegung zeigt, welcher Teil kostet:** die Ratsche, nicht die
> Breakeven-Sperre. Im Bullenjahr kostet die Ratsche allein −37,79 $, die
> Breakeven-Sperre allein nur −3,34 $ — und beides zusammen (−23,44 $) ist
> *besser* als die Ratsche allein. Die Breakeven-Sperre gleicht einen Teil des
> Schadens wieder aus.
>
> #### Korrektur: R/R ist ohne Trefferquote wertlos
>
> Hier stand, die Breakeven-Variante habe „das mit Abstand beste Chance/Risiko
> (0,94 bzw. 1,13)". **Das war irreführend.** Ein R/R ist nur im Verhältnis zu
> seiner Trefferquote lesbar. Break-even liegt bei
>
> ```
> benötigtes R/R = (1 − Trefferquote) / Trefferquote
> ```
>
> Damit dreht sich das Bild um — die Variante mit dem *höchsten* R/R ist die
> vom Break-even am *weitesten* entfernte:
>
> | Variante (Bärenjahr) | WR % | R/R ist | R/R nötig | Abstand | E je Trade |
> |---|---|---|---|---|---|
> | a) alte Leiter | 53,2 | 0,41 | 0,88 | **−0,47** | −0,3274 $ |
> | b) nur Ratsche | 47,8 | 0,40 | 1,09 | −0,70 | −0,3144 $ |
> | c) nur Breakeven | 26,9 | 0,94 | 2,71 | **−1,78** | −0,2993 $ |
> | d) beides (aktuell) | 39,7 | 0,50 | 1,52 | −1,02 | −0,3044 $ |
> | **Live-Journal 2026** | **71,9** | **0,35** | **0,39** | **−0,04** | **−0,0652 $** |
>
> Die letzte Zeile ist die eigentliche Nachricht: der **echte Bot** steht mit
> R/R 0,35 nur **0,04 vom Break-even entfernt** — näher als jede
> Backtest-Variante. Seine hohe Trefferquote trägt fast. Das ist ein völlig
> anderes Bild als „R/R 0,35 ist katastrophal", das weiter oben in diesem
> Dokument steht: katastrophal ist das Verhältnis nur, wenn man die
> Trefferquote wegläßt.
>
> **Einschränkungen, ohne die diese Zahlen nicht zitiert werden dürfen:**
> in-sample, keine vorab festgelegte Train/Test-Trennung; nur zwei Jahre; die
> Einstiegslogik des Harness ist eine Vereinfachung des echten DCA-Pfads.
>
> **Warum die Leiter trotzdem drinbleibt:** die alte Regel hatte einen echten
> logischen Defekt (Selbstlockerung auf dem Rückweg), der unabhängig von der
> Rendite ist. Ein Rückbau auf Basis eines In-Sample-Backtests wäre derselbe
> Fehler in die andere Richtung. Siehe auch den Nachtrag zu Teil 6 weiter unten.

### Die Wiedereinstiegs-Sperre

Nach jedem Ausstieg: 90 Minuten gesperrt, danach nur ≥ 1 % unter dem
Ausstiegspreis, Fenster 6 Stunden. Neustartfest in
`data_store/reentry_guard.json`.

### Die Live-Sicherungen

Drei Schlösser, alle nur im Live-Modus wirksam:

1. **Freigabe-Pflicht.** Beim Start im Live-Modus ruft der Bot `go_live_check.py`.
   Fällt sie durch, fällt er auf Papier zurück und sagt warum. Ein geändertes Wort
   in der Config reicht nicht mehr.
2. **Schlüssel-Rechte.** Meldet Binance `canWithdraw: true`, bricht der Bot ab.
   Ein Handelsschlüssel mit Auszahlungsrecht ist ein gestohlenes Konto in Wartestellung.
3. **Deckel.** `live_max_order_usd` = 25 $ je Order, `live_max_capital_usd` = 200 $
   Gesamtkapital. Fangnetze gegen Rechenfehler im prozentualen Sizing.

---

## Teil 6 — Der Weg zu echtem Geld

### Das Werkzeug

```bash
python go_live_check.py
```

Liest nur, ändert nichts, sagt Ja oder Nein — mit Begründung je Kriterium.

### Der Stand heute (29.07., direkt nach dem Umbau)

```
ERGEBNIS: KEINE FREIGABE — 7 Kriterien nicht erfüllt
```

| | Kriterium | Ist | Soll |
|---|---|---|---|
| A | Stichprobe seit Umbau | 0 Verkäufe | ≥ 100 |
| B | **Erwartungswert je Trade** | — | **> 0 $** |
| C | Chance/Risiko | — | ≥ 0,8 |
| D | Gebühren-Kreisel | 0 % | ≤ 10 % ✔ |
| E | Größter Rückgang | 0,13 % | ≤ 15 % ✔ |
| F | Statistisch belastbar | zu wenig Daten | 95-%-Intervall > 0 |
| G | Mindestlaufzeit | 0 Tage | ≥ 14 |
| H1–H4 | Wächter, Kill-Switch, Deckel | scharf | ✔ |
| H5 | API-Schlüssel | fehlt | in `.env` |
| H7 | Journal deckungsgleich | SOL weicht ab | keine Abweichung |

**Kriterium B ist das Herzstück.** Nicht die Trefferquote — die stand bei 71,9 %,
während Geld verbrannte. Was zählt, ist der Erwartungswert je Trade.

**Kriterium F ist die Bremse gegen Selbstbetrug.** Bei kleinen Stichproben sieht
Glück wie Können aus. Erst wenn auch das pessimistische Ende des
95-%-Konfidenzintervalls im Plus liegt, ist der Vorteil belastbar.

> ### ⚠️ Bekannter Mangel: Kriterium C (`MIN_RR = 0.8`)
>
> `go_live_check.py:78` prüft das Chance/Risiko-Verhältnis gegen eine **absolute**
> Schwelle von 0,8. Das ist konzeptionell falsch, denn Break-even hängt an der
> Trefferquote: `nötig = (1 − WR) / WR`.
>
> | Trefferquote | Break-even-R/R | Urteil von Kriterium C bei R/R = 0,8 |
> |---|---|---|
> | 71,9 % (der echte Bot) | 0,39 | **zu streng** — verlangt das Doppelte des Nötigen |
> | 50 % | 1,00 | zu lax — lässt ein Verlustsystem durch |
> | 30 % | 2,33 | **irreführend** — lässt ein klares Verlustsystem durch |
>
> Ein System mit 30 % Trefferquote und R/R 0,9 besteht Kriterium C und verliert
> trotzdem sicher Geld. Umgekehrt scheitert der aktuelle Bot an C, obwohl er mit
> 71,9 % Trefferquote nur 0,04 R/R-Punkte vom Break-even entfernt ist.
>
> **Fachlich richtig sind ohnehin B (Erwartungswert > 0) und F (unteres Ende des
> Konfidenzintervalls > 0)** — beide sind schon scharf und decken den Fall
> vollständig ab. C ist redundant und im Zweifel schädlich.
>
> **Bewusst nicht geändert** (Stand 29.07.): Eine Lockerung des Freigabe-Gates
> während der Bot auf seine Freigabe wartet, ist ein Interessenkonflikt. Die
> Änderung sollte fallen, wenn das Messfenster leer ist — nicht wenn Zahlen
> darin stehen, die sie beeinflussen könnte.

### Der Ablauf

1. **Laufen lassen.** Papierbetrieb, mindestens 14 Tage, mindestens 100 Verkäufe
   unter der neuen Mechanik. Nichts an der Ausstiegsleiter drehen — sonst beginnt
   die Zählung von vorn.
2. **Zwischenstand prüfen.** `python go_live_check.py`, etwa alle drei Tage.
3. **Bei Freigabe:** API-Schlüssel bei Binance erzeugen — **nur** „Enable Reading"
   und „Enable Spot Trading". „Enable Withdrawals" bleibt aus. In `.env` eintragen.
4. **Klein anfangen.** Die Deckel stehen auf 200 $ Kapital und 25 $ je Order.
   Der erste Live-Betrag sollte einer sein, dessen Totalverlust nichts ändert.
5. **Gegenprobe nach 30 Live-Trades:** Weicht das Ergebnis stark vom Papierlauf ab,
   liegt es an Slippage oder Teilausführungen — dann zurück auf Papier.

### Was ich nicht getan habe und warum

Ich habe den Modus **nicht** auf `live` gestellt. Nicht aus Vorsicht als Prinzip,
sondern weil die Zahlen es nicht tragen: Die gemessene Erwartung war negativ, und
die Reparaturen haben **null** Trades Beweislage. Live zu gehen hieße heute, einen
gemessenen Papierverlust in einen echten zu verwandeln. Das Gate steht jetzt da,
um genau diese Entscheidung an Daten zu binden statt an Ungeduld — meine wie deine.

---

## Teil 7 — Was offen ist

| Thema | Warum es zählt |
|---|---|
| **Journal hat Lücken** | SOL: Journal −0,99 vs. Bestand +0,71. Mindestens ein Kauf ist nie gebucht worden. Ein lückenhaftes Journal kann keine Freigabe begründen (blockiert H7). |
| **Kein Backtest** | `backtest/engine.py` ist nicht mit `risk/exit_rules.py` verdrahtet. Die neue Leiter ist unbelegt. Der nächste sinnvolle Bauschritt. |
| **MFE/MAE erst 15 Trades** | Wird seit 25.07. protokolliert. Für die Frage „wie viel Gewinn geben wir zurück" braucht es ~50. |
| **`ui/main_window.py` ungeprüft** | 3.100 Zeilen. Im Journal tauchen `MANUAL_SELL` und `DAILY_LOSS_SAFETY` auf — es gibt also weitere Verkaufspfade, obwohl der Exit-Monitor als einzige Autorität dokumentiert ist. |
| **Signal-Apparat steht still** | ML, Ensemble, Meta-Voting erzeugen keine Trades. Entweder Positionsplätze für sie reservieren — oder abschalten und Komplexität sparen. |
| **Grid-Bot ungeprüft** | Hat am 29.07. ATOM gekauft. Ein sechster Handelspfad, den ich nicht auditiert habe. |
| **Futures-Modul aktiv** | `[FUTURES] Verbunden (Paper, Max 3x)`. Hebel gehört in einem Bot mit negativer Erwartung nirgendwohin. |
| **Tote Datenquellen** | Reddit 403. Jetzt sichtbar statt still — aber nicht repariert. |

---

## Teil 8 — Bedienung

```bash
python app.py              # Bot starten
python go_live_check.py    # Freigabe prüfen (liest nur)
python cockpit_server.py   # Auswertung im Browser, localhost:8110
```

**Regeln, die ich nicht gebrochen sehen möchte:**

- `data_store/config.json` nur bei **gestopptem** Bot ändern.
- `data_store/` nie von Hand löschen. Das ist die Buchführung.
- `.env` verlässt diesen Rechner nicht.
- Nach jeder Änderung an der Ausstiegslogik: Zählung für die Freigabe beginnt neu.

**Notizen an den Bot** gehen über `tickets.txt` — eine Zeile je Eintrag,
`STICHWORT: Text`, Stichworte `SPEICHERN`, `ERLEDIGT`, `BUG`, `DOKUMENTIEREN`,
`NOTIZ`. Der Bot frisst sie binnen 30 s ins `ENTWICKLERHANDBUCH.md`.

---

## Anhang — Alle Änderungen vom 29.07.2026

| # | Datei | Was |
|---|---|---|
| E9-1 | `risk/reentry_guard.py` *(neu)* | Wiedereinstiegs-Sperre gegen den Gebühren-Kreisel |
| E9-2 | `app.py`, `runtime/exit_monitor.py` | `cost_basis` — Kaufgebühr in der P&L |
| E9-3 | `app.py` | Höchststände beim Nachkauf zurücksetzen |
| E9-4 | `app.py` | Risiko-Tore, Nachkauf-Deckel, Exposure im DCA-Pfad |
| E9-5 | `core/state_store.py` | `shutil`-Import — Journal-Backup funktioniert |
| E9-6 | `risk/exit_rules.py` *(neu)* | Ausstiegs-Ratsche statt inverser Leiter |
| E9-7 | `core/scheduler.py` | Doppellauf-Wettlauf geschlossen |
| E9-8 | `portfolio/daily_loss.py`, `config/settings.py`, `config.json` | Zeitzone + Wächter scharf (6 %) |
| E9-9 | `app.py`, `risk/engine.py` | `total_equity` = Kapital, nicht Bargeld |
| E9-10 | `execution/engine.py`, `core/events.py` | Live-Ausführungsprüfung, Teilausführungen, Lot-Size |
| E9-11 | `execution/engine.py` | Papier-Einstand mengengewichtet |
| E9-12 | `runtime/state_manager.py` | Neue Felder persistiert, Restore-Warnung |
| E10-13 | `portfolio/manager.py`, `core/balance_reporter.py`, `app.py` | BTC-Sparplan sichtbar (96,54 $) |
| E10-14 | `features/doc_agent.py` | Tagesbericht repariert |
| E10-15 | `core/state_store.py` | Echtes `clear()`, leer ≠ kaputt, Backup ohne Verzug |
| E10-16 | `data/source_health.py` *(neu)*, `app.py` | Tote Quellen fallen aus der Gewichtung |
| E10-17 | `go_live_check.py` *(neu)* | Freigabe-Prüfung |
| E10-18 | `execution/engine.py`, `portfolio/manager.py`, `config/settings.py` | Live-Sicherungen: Gate, Schlüsselrechte, Deckel |

---

## Anhang B — Warnung vom 30.07.2026: der Giveback ist kein ungenutztes Potenzial

**Wer in sechs Monaten die Zahlen aus der E2-Messung wiederfindet, wird versucht
sein, sie falsch zu lesen. Diese Warnung steht hier, damit das nicht passiert.**

Die Messung ergab: Eine Position erreicht im Median einen Buchgewinn (MFE) von
1,27 %, realisiert wird aber im Median −0,10 %. Die Differenz von rund
1,4 Prozentpunkten heißt in der Auswertung "Giveback". Sie bleibt über alle
geprüften Stop-Abstände nahezu konstant (1,35 bis 1,53).

**Das ist kein Leck. Das ist Konstruktion.**

Der Grund ist arithmetisch, nicht strategisch. Das Maximum eines Kursverlaufs
liegt nie unter seinem Startwert. Deshalb ist der erwartete Buchgewinn einer
Position auch dann positiv, wenn der Kurs überhaupt keine Richtung hat — bei
einem driftfreien Verlauf gilt E[MFE] > 0 mit mathematischer Notwendigkeit. Ein
positiver Median-MFE neben einem negativen realisierten Ergebnis ist damit der
Normalzustand jeder Ausstiegsregel, die nicht in die Zukunft sehen kann.

Schärfer noch, und das ist der eigentliche Punkt: Nach dem Optional-Stopping-
Theorem kann **keine** Ausstiegsregel, die nur auf vergangene Kurse schaut, den
Erwartungswert auf einem driftfreien Verlauf verändern. Nicht eine bessere
Ratsche, nicht ein weiterer Stop, nicht ein cleveres Teilverkaufsschema. Wer
den Giveback systematisch einsammeln will, muss das Hoch erkennen, bevor es
vorbei ist — und das ist exakt der Richtungsvorteil, dessen Nichtexistenz die
Messung vom 30.07.2026 zeigt (symmetrisches Barrierenrennen: 47,7 % gegen
47,5 % bei Zufallseinstieg, phasengleich geprüft, Zufallsniveau innerhalb des
95-%-Konfidenzintervalls des echten Werts).

**Konsequenz für künftige Arbeit:** Der Satz "wir lassen im Median 1,4 Prozent
je Position liegen" ist keine Beschreibung eines Optimierungsspielraums. Wer
ihn als solchen liest und die Ausstiegsregel daraufhin umbaut, verschiebt
Trefferquote gegen Gewinngröße und landet nach Kosten wieder beim selben
Erwartungswert — nur mit anderer Verteilung und meist längerer Kapitalbindung.

**Zwei Präzisierungen, damit die Warnung nicht selbst falsch gelesen wird:**

1. Die Aussage betrifft ausschließlich den **Erwartungswert**. Ausstiegsregeln
   verändern sehr wohl Streuung, Maximalverlust, Haltedauer und Kapitalbindung.
   Als Risikowerkzeug bleiben sie sinnvoll — als Ertragsquelle nicht.
2. Die Aussage gilt unter der Annahme, dass der Kursverlauf keine ausnutzbare
   Richtung trägt. Genau diese Annahme wurde gemessen, nicht unterstellt. Fände
   sich später ein belastbarer Richtungsvorteil, wäre die Rechnung neu
   aufzumachen — dann aber wäre der Vorteil die Ertragsquelle, nicht der
   Giveback.

**Belege:** Messläufe E2 vom 30.07.2026, Giveback je Stop-Abstand; Placebo I/II
gegen Zufallseinstieg; phasengleiches Placebo mit Block-Bootstrap über
Kalendertage.
