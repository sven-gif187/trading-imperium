# Schritt 3 — Was vor dem Messfenster in die Datenbank muss

**Stand 13.08.2026, nachts. Vorbereitung — noch nichts implementiert.**
Wie zugesagt: erst die genaue Liste, welche Spalte wohin kommt und welche
Stelle im Code sie füllt, bevor eine Zeile geändert wird.

---

## Die gute Nachricht zuerst

Die Erweiterung ist **deutlich kleiner als befürchtet**. Zwei Gründe:

1. **Der Migrationsmechanismus existiert schon.** `core/telemetrie.py:270`
   `_migriere()` liest, welche Spalten vorhanden sind, und ergänzt nur
   Fehlendes per `ALTER TABLE ADD COLUMN`. Idempotent, gefahrlos
   wiederholbar, Altzeilen bleiben unangetastet (neue Felder sind dort
   einfach NULL). Eine neue Spalte kostet **eine Zeile** in der Liste
   `ZUSATZSPALTEN` (`core/telemetrie.py:197`).
2. **Die meisten Werte liegen schon vor** — sie werden nur nicht
   geschrieben. `DecisionIntent` (`core/events.py`) führt bereits
   `take_profit`, `trailing_stop_pct`, `max_slippage_pct`, `model_version`,
   `agent_id`, `quantity`. Der Spread liegt in `self._spread_cache`
   (`app.py:2496`), die Durchlaufnummer in `self._cycle_id`.

Es geht also überwiegend um **Durchreichen**, nicht um Neubau.

---

## Die schlechte Nachricht: RR-Netto ist so nicht berechenbar

**Belegt:** `take_profit` wird **an keiner einzigen Stelle im Code
gesetzt**. Suche über `app.py`, `agents/`, `risk/`, `execution/`,
`features/` — null Treffer für eine Zuweisung. Das Feld existiert im
Datenmodell und ist immer `None`.

**Warum das den Plan trifft:** Das klassische Chance-Risiko-Verhältnis ist

```
RR = (Kursziel − Einstieg) / (Einstieg − Stop)
```

Ohne Kursziel gibt es keinen Zähler. **RR-Netto lässt sich in diesem Bot
nicht berechnen, weil er gar nicht mit Kurszielen arbeitet.**

Das ist **kein Fehler**, sondern eine Eigenschaft der Strategie: Der Bot
steigt regelbasiert aus — nachziehender Stop (Trailing Stop),
Trend-Ausstieg, Notaus-Netz, Coin-Modus SL/HOLD/TP. Ein fester Zielkurs
würde diese Logik ersetzen, nicht ergänzen.

### Die richtige Kennzahl heißt R-Multiple

Bei regelbasierten Ausstiegen ist der Standard nicht RR, sondern das
**R-Vielfache**. Das funktioniert ohne Kursziel:

```
R (das Risiko)  = Einstieg − Stop-Loss        ← ist bekannt, steht im intent
Ergebnis in R   = realisierter Gewinn / R     ← nach dem Ausstieg messbar
```

Ein Trade, der 2,5-mal so viel einbringt, wie beim Stop verloren gegangen
wäre, ist „+2,5R". Über viele Trades ergibt der Mittelwert genau das, was
RR beantworten sollte: **Lohnt sich das eingegangene Risiko?**

**Vorteile hier:**
- Braucht kein Kursziel — passt zur bestehenden Strategie.
- Der Nenner (`entry − stop`) ist **schon heute** verfügbar.
- Netto-Version durch Abzug von Gebühren, Spread und Schlupf — alles seit
  Punkt 23/24 gemessen statt geraten.
- Über `position_id` mit dem tatsächlichen Ausgang verknüpfbar; `pnl_usd`,
  `mfe_pct`, `mae_pct` und `haltedauer_min` stehen bereits in der Tabelle.

**Empfehlung:** Schritt 4 des Plans (RR-Netto im Schattenmodus) wird zu
**R-Multiple im Schattenmodus**. Zusätzlich `rr_geplant_netto` als Spalte
anlegen — sie bleibt NULL, solange es keine Kursziele gibt, und ist sofort
da, falls je welche eingeführt werden. Eine leere Spalte kostet nichts;
eine fehlende kostet das Messfenster.

**Das ist eine Entscheidung, die Sven treffen sollte** — sie weicht vom
Masterprompt (Abschnitt F) ab, und zwar aus einem sachlichen Grund, nicht
aus Bequemlichkeit.

---

## Die Spaltenliste

Alle in `evaluations`, sofern nicht anders vermerkt. „Quelle" nennt die
Stelle, die den Wert **heute schon** kennt.

### Gruppe A — liegt vor, wird nur nicht geschrieben (billig)

| Spalte | Typ | Quelle | Warum |
|---|---|---|---|
| `take_profit` | REAL | `intent.take_profit` | Heute immer NULL — genau das ist der Beleg oben, und er gehört sichtbar in die Daten |
| `trailing_stop_pct` | REAL | `intent.trailing_stop_pct` | Der tatsächliche Ausstiegsmechanismus; ohne ihn ist kein Ausgang erklärbar |
| `max_slippage_pct` | REAL | `intent.max_slippage_pct` | Angenommener Schlupf — Vergleichswert zum gemessenen |
| `quantity_geplant` | REAL | `intent.quantity` | Geplante Menge vs. `qty` (tatsächlich) = Teilfüllungen sichtbar |
| `agent_id` | TEXT | `intent.agent_id` | Wer hat das Signal erzeugt |
| `model_version` | TEXT | `intent.model_version` | Pflicht laut Masterprompt Abschnitt J |
| `decision_id` | TEXT | `intent.id` | Existiert schon als `intent.id`, wird nur an **einer** Stelle benutzt (`app.py:1550`). Die Brücke Entscheidung → Order → Fill |
| `cycle_id` | INTEGER | `self._cycle_id` | Welcher Durchlauf — gruppiert alles, was im selben Takt entschieden wurde |
| `spread_pct` | REAL | `self._spread_cache[coin]` | Wird befüllt (`app.py:2496`), landet aber nirgends |

### Gruppe B — vorhanden, muss durchgereicht werden (mittel)

| Spalte | Typ | Quelle | Warum |
|---|---|---|---|
| `git_commit` | TEXT | `git rev-parse --short HEAD` beim Start, einmal | **Beweist, dass im Messfenster nichts geändert wurde.** Ohne das ist jede Auswertung anfechtbar |
| `regime` | TEXT | `self.regime_detector.current_regime` | Auswertung nach Marktregime ist ausdrückliches Ziel |
| `fear_greed` | INTEGER | `self.state.get("fear_greed")` | Steht in `markt_historie`, fehlt aber am Einzelfall |
| `daten_alter_sec` | REAL | Zeitstempel der letzten Kerze vs. jetzt | Erklärt später die Ausreißer. Masterprompt Abschnitt C |
| `quellen_gesund` | TEXT | `self.source_health` | Welche externen Quellen lebten zur Entscheidungszeit |

### Gruppe C — muss gerechnet werden (Schattenmodus, greift nicht ein)

| Spalte | Typ | Formel | Warum |
|---|---|---|---|
| `risiko_r_usd` | REAL | `(entry − stop) × qty` | Der Nenner für alles Weitere. Rein rechnerisch, kein Eingriff |
| `risiko_pct` | REAL | `(entry − stop) / entry × 100` | Stop-Abstand, vergleichbar über Münzen hinweg |
| `kosten_erwartet_usd` | REAL | Gebühr ein + aus + Spread + Schlupf je Münze (Punkt 23) | Die Netto-Komponente |
| `r_multiple_netto` | REAL | `(pnl_usd − Kosten) / risiko_r_usd`, beim Ausstieg | **Die Kernkennzahl.** Ersetzt RR-Netto |
| `rr_geplant_netto` | REAL | nur wenn `take_profit` gesetzt ist | Bleibt vorerst NULL — bewusst |

### Gruppe D — neu zu erheben (der größte Brocken)

| Was | Wohin | Warum |
|---|---|---|
| `feature_snapshot_id` | Spalte in `evaluations` | Verweis auf … |
| Neue Tabelle `feature_snapshots` | eigene Tabelle | RSI, MACD, EMA 20/50/200, ATR, ADX, Bollinger, Volumen-Verhältnis, Trend je Zeitebene, Abstand zu Unterstützung/Widerstand — **die Werte, mit denen entschieden wurde** |

**Warum eine eigene Tabelle:** Ein Schnappschuss hat ~20 Zahlen. Als
Spalten in `evaluations` wäre die Tabelle unlesbar; außerdem entstehen
mehrere Entscheidungen aus demselben Schnappschuss.

**Ohne diese Gruppe:** kein Nachtraining der KI und keine Antwort auf
„warum hat er das gedacht". **Das ist das Feld, dessen Fehlen die zwei
Wochen wertlos machen würde** — Kurse lassen sich nachladen, der
Rechenstand des Bots nicht.

---

## Umsetzungsreihenfolge

| # | Was | Risiko | Aufwand | Wirkt |
|---|---|---|---|---|
| 1 | Gruppe A: 9 Zeilen in `ZUSATZSPALTEN`, Befüllung in `_baue_datensatz()` | 1 | 2 | sofort |
| 2 | Gruppe B: 5 Spalten, Werte durchreichen | 2 | 3 | sofort |
| 3 | Gruppe D: Tabelle `feature_snapshots` + Schreibstelle | 3 | 6 | sofort |
| 4 | Gruppe C: Rechnung im Schattenmodus | 2 | 5 | beim Ausstieg |

Alles reines Aufschreiben — **keine einzige Verhaltensänderung**. Nach
Masterprompt Abschnitt 0 damit auch während eines laufenden Fensters
zulässig; trotzdem besser vorher, damit die Daten von Tag 1 an vollständig
sind.

---

## Was Sven entscheiden muss

1. **R-Multiple statt RR-Netto** — ja oder nein? (Empfehlung: ja, mit
   `rr_geplant_netto` als leerer Reserve.)
2. **Sollen Kursziele eingeführt werden?** Das wäre eine
   Verhaltensänderung und gehört **vor** das Fenster oder gar nicht. Meine
   Meinung: nein — der regelbasierte Ausstieg ist gemessen und
   funktioniert; ein Kursziel wäre eine neue Strategie, kein Messwerkzeug.
3. **Umfang von Gruppe D:** alle Indikatoren oder nur die, die tatsächlich
   in die Entscheidung eingehen? (Empfehlung: alle, die berechnet werden —
   der Preis dafür ist Speicherplatz, der Preis für das Gegenteil sind
   zwei Wochen.)

---

## Offen, ehrlich vermerkt

- **Ob jeder Indikator zum Entscheidungszeitpunkt greifbar ist**, habe ich
  noch nicht geprüft. Manche werden evtl. erst später oder woanders
  berechnet. Das ist die erste Aufgabe bei Gruppe D.
- **Kosten für Gruppe D** sind grob geschätzt: bei ~10 Münzen im
  Minutentakt entstehen einige Millionen Zeilen im Jahr. Für zwei Wochen
  unkritisch, dauerhaft braucht es eine Ausdünnung — messen, bevor
  entschieden wird.
- **`_baue_datensatz()`** (`core/telemetrie.py:697`) habe ich nur
  überflogen, nicht Zeile für Zeile gelesen. Vor der Umsetzung nötig.
