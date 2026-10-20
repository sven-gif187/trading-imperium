# TESTLISTE — was ist gemessen, was fehlt

*Stand 11.08.2026. Aufgabe 6. Jede Zeile mit Datei und Datenquelle.
Zahlen frisch aus der Datenbank gezogen, nicht aus Erinnerung.*

---

## 1. Belegt — hier liegt eine echte Messung vor

| Was | Datei | Datenquelle | Stand | Ergebnis |
|---|---|---|---|---|
| **Kostenmatrix v4** | `docs/forschungsprogramm_2026-07/code/kosten_matrix_v4.py` | 11 Tage Live-Capture (`forschung.db`) | fertig | BTC/ETH **0,50 %** je Runde, Alt-Coins bis **0,91 %** (NEAR). Die alte Schätzung war exakt richtig. **Urteil: nicht einbauen.** |
| **Chartanalyse** | `chartanalyse_backtest.py` | `telemetrie.db` → `chart_signale` (**24 653** Zeilen), `chart_laeufe` (**54** Läufe) | läuft täglich weiter | ~70 % Trefferquote, **alle Signalarten netto negativ**. Ziele zu nah, Stops zu weit. **Urteil: nicht einbauen.** |
| **Regime-Filter-Wirkung** | `regime_filter_messung.py` | `telemetrie.db` → `rule_evaluations` (**78 942**) | fertig | Führte zu `min_confirmations` 2 → 3 (10.08.) |
| **Ablehnungsgründe** | `telemetrie_frage.py gruende` | `evaluations` (**64 043**) + `rule_evaluations` | laufend | Vollständige Gründeliste je Prüfung, nicht nur der erste |
| **Gesamtauswertung** | `gesamtauswertung.py` | `trades_v5.json` | fertig | — |
| **Excel-Export** | `datenexport.py` | `trades_v5.json`, `equity_history.json` | fertig | zuletzt `BOT-DATEN_20260810_2127.xlsx` |
| **E7-Epoche** | `e7_auswertung.py` | `trades_v5.json` | abgeschlossen | R/R 0,67 gegen Basis 0,54 → K1 erfüllt |

---

## 2. Datenlage zu dünn — gebaut, aber noch nicht aussagefähig

| Was | Datei | Datenquelle | Zeilen heute | Fehlt |
|---|---|---|---|---|
| **Stop-Loss-Analyse** | `stoploss_analyse.py` | `trades_v5.json` | — | zu wenige Fälle, bekannt |
| **Verkaufs-Telemetrie** | `core/telemetrie.py:protokolliere_verkauf` | `evaluations` mit `decision='SOLD'` | **2** | seit 10.08. aktiv, braucht Zeit |
| **Lern-Ereignisse** | `core/telemetrie.py:lern_ereignis` | `lern_ereignisse` | **0** | wartet auf den ersten Verkauf |
| **Markt-Historie** | `app.py:_markt_schnappschuss` | `markt_historie` | **0** | startet mit dem nächsten Bot-Start, dann 96/Tag |
| **Schatten-Sizing** | `app.py:_execute_approved_trade` | `schatten_sizing` | **0** | nur bei freigegebenen Käufen — davon gab es seit 07.08. **fünf**. Wochen bis zur Auswertbarkeit. |
| **Hintergrundjobs** | `core/hintergrund.py` | `jobs` | **17** | läuft seit heute |

---

## 3. BEFUND: Der TREND-EXIT-Schattenmodus sammelt nichts

`schatten_exits` enthält **0 Zeilen**.

Auf der offenen Liste steht „TREND_EXIT-Schattenmodus nach 20–30 Fällen
auswerten". Nach 20–30 Fällen wird es nie kommen, wenn die Tabelle leer
bleibt. Entweder löst die Regel nie aus, oder der Schreibpfad ist tot.

**Nicht geprüft**, welches von beidem — das braucht einen eigenen Blick in
`runtime/exit_monitor.py`. Vorher ist jede Aussage dazu geraten.

---

## 4. BEFUND: Gebaut, wird aber nie aufgerufen

| Datei | Zustand | Beleg |
|---|---|---|
| `backtest/walk_forward.py` | **nie aufgerufen** | Nur `BacktestEngine.walk_forward()` referenziert es (`backtest/engine.py:342`). Diese Methode hat **null** Aufrufer. |
| `backtest/monte_carlo.py` | **nie aufgerufen** | Dasselbe, `engine.py:348`. Null Aufrufer. |
| `backtest/hyperopt.py` | **nie genutzt** | In `app.py:418` erzeugt, aber nur `get_status()` wird gerufen (`app.py:3532`). `optimize()` hat null Aufrufer. |

Die Oberfläche ruft am Backtest-Motor ausschließlich `bt.run()` auf
(`ui/main_window.py:859` und `:916`) — nie Walk-Forward, nie Monte-Carlo.

**Damit ist die Frage aus Aufgabe 6 beantwortet: nein, sie werden nie
aufgerufen.** Sie sind vorhanden und vermutlich funktionsfähig, aber
nirgends angeschlossen.

---

## 5. BEFUND MIT GEWICHT: Der Auto-Optimizer

**Er ist aus — aber ein Knopf in der Oberfläche schaltet ihn an.**

| | |
|---|---|
| Code | `app.py:2644 _auto_optimize` |
| Eingeplant | **ja**, alle 30 Minuten (`app.py:604`, `interval_sec=1800`) |
| Schalter | `auto_optimize_enabled = False` (`app.py:603`), **fest im Code** |
| Anschalter | Häkchen in der Oberfläche (`ui/main_window.py:2046` → `:2613`) |

**Was er täte, wenn er anspringt:** Er durchsucht 27 Kombinationen aus
Stop-Loss, Trailing und Positionsgröße auf **300 Stundenkerzen BTC**
(≈ 12,5 Tage), nimmt die beste — und schreibt sie in die Konfiguration:

```
app.py:2669-2672
    self.config.risk.stop_loss_pct     = best["sl"]
    self.config.risk.trailing_stop_pct = best["trail"]
    self.config.trading.position_size_pct = best["pos"]
    self.config.save()          # dauerhaft
```

Alle 30 Minuten neu. **Das ist Overfitting im Reinformat** — aus 27
Varianten die auf 12 Tagen beste zu wählen und live zu schalten, ist genau
das „Drehen, bis die Zahlen gefallen", das Regel 5 verbietet.

Und es fehlt **jede** der in Regel 6 geforderten Sicherungen: keine harten
Grenzen, keine Mindestdatenmenge, keine Sperrfrist, keine Protokollierung
außer einer Logzeile. Wer das Häkchen setzt, merkt hinterher nicht einmal,
welcher Wert wann warum verstellt wurde.

**Nichts geändert** — der Handelspfad wird nicht ohne Freigabe angefasst.
**Vorschlag zur Entscheidung:** Häkchen aus der Oberfläche entfernen, oder
die Automatik nach dem Vorbild von `features/regime_adaptiv.py` mit den
fünf Sicherungen nachrüsten. Nichtstun ist die schlechteste Variante: der
Knopf sieht harmlos aus.

---

## 6. Was fehlt — noch nirgends gemessen

| Frage | Was dafür nötig wäre | Vorhanden? |
|---|---|---|
| Sagt Funding / Whale / DXY / NUPL / Onchain etwas vorher? | Zeitreihe + Ausgang danach | Zeitreihe **ab jetzt** (`markt_historie`), Auswertung fehlt |
| Hätten kleinere Positionen in Verlustserien geholfen? | `schatten_sizing` gegen echten Ausgang | Erfassung steht, Daten fehlen |
| Lernt der Bot aus Verlusten etwas Brauchbares? | `lern_ereignisse` + `brain_performance_v6.json` | Erfassung steht, **noch kein einziger Verkauf** |
| Sagt die V4-Rangliste V6-Ergebnisse vorher? | V4-Zahlen als Messquelle einlesen | **nicht gebaut** (Entscheidung 11.08.: nur Messquelle) |
| Wie oft greift welche Ausstiegsregel, und lohnt sie? | `schatten_exits` je Regel | Tabelle da, **leer** — siehe Abschnitt 3 |
| Ist die Wiedereinstiegs-Sperre wirksam? | Churn-Zahlen vor/nach dem 29.07. | **nicht gemessen** |

---

## 7. Nächste sinnvolle Schritte

1. **Abschnitt 3 klären** — warum `schatten_exits` leer ist. Kleinster
   Aufwand, größte Aussage: hier hängt eine bereits beschlossene Auswertung.
2. **Abschnitt 5 entscheiden** — Auto-Optimizer entschärfen oder absichern.
3. Markt-Historie zwei Wochen laufen lassen, dann erstmals auswerten.
4. Churn-Messung nachziehen (Wiedereinstiegs-Sperre).
