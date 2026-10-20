# Telemetrie-Datenbank — Anleitung und fertige Abfragen

**Datei:** `data_store/telemetrie.db`
**Werkzeug:** DB Browser for SQLite (sqlitebrowser.org)

---

## So öffnest du sie richtig

1. DB Browser starten
2. **Datenbank öffnen** — diesen Pfad einfügen:
   `C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\data_store\telemetrie.db`

**Nur-Lesen-Modus:** Der Menüpunkt heißt je nach Version anders und liegt
meist hinter dem **kleinen Dropdown-Pfeil ▾ neben dem Öffnen-Button**
(„Read only"). Als eigener Eintrag existiert er nicht — wer ihn nicht findet,
öffnet einfach normal.

**Normal öffnen ist gefahrlos, solange eine Regel gilt:** DB Browser schreibt
nichts in die Datei, bis oben **„Änderungen schreiben"** (*Write Changes*)
geklickt wird. Anschauen und Abfragen mit F5 ändern nie etwas.
**Diesen Knopf also nie drücken.** Ist er ausgegraut, wurde auch nichts
geändert.

**Warum diese Vorsicht:** Der Bot schreibt laufend in diese Datei. Zwei
Programme, die gleichzeitig schreiben wollen, beschädigen sie — genau das ist
am 07.08.2026 mit `bot_state.json` passiert (`WinError 5`, Ursache war eine
zweite Bot-Instanz).

**Der narrensichere Weg:** Datei kopieren (Rechtsklick → Kopieren → auf dem
Desktop einfügen) und die Kopie öffnen. Dann kann nichts passieren; der Stand
ist dafür eingefroren.

**Falls der Browser meckert** („database is locked"): einmal schließen und neu
öffnen. Der Bot hat Vorrang.

---

## Die vier Tabellen

| Tabelle | Eine Zeile ist … |
|---|---|
| `evaluations` | eine Kaufprüfung — gekauft oder abgelehnt, mit Preis, Score, Kapital |
| `rule_evaluations` | **ein einzelner Ablehnungsgrund**. Eine Prüfung kann mehrere haben |
| `chart_signale` | ein Signal der Chartanalyse aus dem Backtest, samt Ausgang |
| `chart_laeufe` | die Zusammenfassung eines kompletten Backtest-Laufs |

Zum Blättern: Reiter **„Daten durchsuchen"**, oben die Tabelle wählen.
Zum Abfragen: Reiter **„SQL ausführen"**, Text einfügen, **F5** drücken.

---

## Abfragen zum Kopieren

### 1. Warum kauft er nicht? — die wichtigste Frage

```sql
SELECT rule_name AS Regel,
       COUNT(DISTINCT evaluation_id) AS Faelle,
       ROUND(COUNT(DISTINCT evaluation_id) * 100.0 /
             (SELECT COUNT(*) FROM evaluations WHERE decision='REJECTED'), 1) AS Prozent
FROM rule_evaluations
WHERE result = 'BLOCK'
GROUP BY rule_name
ORDER BY Faelle DESC;
```

Die Summe kann über 100 % liegen — eine Ablehnung hat oft mehrere Gründe
gleichzeitig. Genau dafür ist die Tabelle da: Früher verdeckte der erste Grund
alle weiteren.

### 2. Was hat er tatsächlich gekauft?

```sql
SELECT substr(ts_utc, 1, 16) AS Zeit, symbol AS Coin,
       ROUND(amount_usd, 2) AS Betrag, ROUND(entry_price, 2) AS Preis,
       score AS Score, entry_reason AS Grund
FROM evaluations
WHERE decision = 'APPROVED'
ORDER BY ts_utc DESC;
```

### 3. Die letzten 50 Entscheidungen im Klartext

```sql
SELECT substr(ts_utc, 12, 8) AS Uhrzeit, symbol AS Coin,
       decision AS Ergebnis, reject_art AS Art,
       grund_anzahl AS Gruende, primary_reason AS Hauptgrund, score AS Score
FROM evaluations
ORDER BY ts_utc DESC
LIMIT 50;
```

`reject_art` übersetzt: **Kapazitaet** = er ist voll oder schon drin (gesund) ·
**Marktfilter** = Abwärtstrend-Schutz (gewollt) · **STOERUNG** = hier lohnt ein
Blick · **Zurueckgestellt** = wartet auf Rückgang.

### 4. Wie oft war er überhaupt kaufbereit? — je Coin

```sql
SELECT symbol AS Coin, COUNT(*) AS Pruefungen,
       SUM(decision='APPROVED') AS Gekauft,
       ROUND(SUM(decision='APPROVED') * 100.0 / COUNT(*), 2) AS Quote_Prozent
FROM evaluations
GROUP BY symbol
ORDER BY Pruefungen DESC;
```

### 5. Chartanalyse: lohnt sie sich? — die Kernfrage

```sql
SELECT signal AS Signalart, COUNT(*) AS Anzahl,
       ROUND(SUM(ergebnis='ZIEL') * 100.0 / COUNT(*), 1) AS Trefferquote,
       ROUND(AVG(rendite_pct), 3)   AS EV_brutto,
       ROUND(AVG(rendite_netto), 3) AS EV_netto
FROM chart_signale
GROUP BY signal
ORDER BY Anzahl DESC;
```

**Nur `EV_netto` zählt.** Negativ heißt: Die Regel kostet Geld — egal wie hoch
die Trefferquote ist. Genau dieser Fall liegt aktuell vor (~70 % Treffer, EV
negativ), weil die Ziele zu nah und die Stops zu weit liegen.

### 6. Welcher Zeitrahmen ist der beste?

```sql
SELECT symbol AS Coin, timeframe AS Zeitrahmen, signale AS Signale,
       quote_pct AS Quote, ev_netto_pct AS EV_netto, substr(ts_utc,1,10) AS Datum
FROM chart_laeufe
ORDER BY ev_netto_pct DESC;
```

Oben steht der beste Markt. So beantwortest du deine Zeitrahmen-Frage mit
Zahlen statt mit Gefühl.

### 7. Chartanalyse je Signalart **und** Zeitrahmen

```sql
SELECT timeframe AS Zeitrahmen, signal AS Signalart, COUNT(*) AS n,
       ROUND(SUM(ergebnis='ZIEL') * 100.0 / COUNT(*), 1) AS Quote,
       ROUND(AVG(rendite_netto), 3) AS EV_netto
FROM chart_signale
GROUP BY timeframe, signal
HAVING COUNT(*) >= 20
ORDER BY EV_netto DESC;
```

`HAVING COUNT(*) >= 20` blendet Gruppen mit zu wenig Fällen aus — unter etwa
20 Fällen ist jedes Ergebnis Zufall. Ändere die Zahl auf 50, wenn du strenger
sein willst.

### 8. Tagesübersicht

```sql
SELECT substr(ts_utc, 1, 10) AS Tag, COUNT(*) AS Pruefungen,
       SUM(decision='APPROVED') AS Kaeufe,
       SUM(reject_art='STOERUNG') AS Stoerungen
FROM evaluations
GROUP BY Tag
ORDER BY Tag DESC;
```

Die Spalte **Stoerungen** ist deine Alarmspalte: Steht dort dauerhaft etwas
über 0, stimmt technisch etwas nicht.

---

## Drei Regeln fürs Arbeiten damit

1. **Immer schreibgeschützt öffnen.** Kein `UPDATE`, kein `DELETE`, kein
   `INSERT` — die Daten sind Messwerte, keine Verhandlungsmasse.
2. **Kleine Fallzahlen bedeuten nichts.** Unter ~20 Fällen ist alles Zufall.
3. **Trefferquote ohne Erwartungswert ist wertlos.** 70 % Treffer und trotzdem
   Verlust ist der Normalfall, nicht die Ausnahme.

*(Wer lieber im Terminal arbeitet: `python telemetrie_frage.py status|gruende|kaeufe|verlauf|coin BTC` liefert dasselbe ohne Zusatzprogramm.)*
