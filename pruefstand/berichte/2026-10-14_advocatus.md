<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
**Summary:** Kein Rechenfehler gefunden. Alle 9 nachgerechneten Zahlen stimmen, teils auf den Cent. Drei Begründungen tragen aber nicht. Erstens gewinnt X3 (A5-V3) nur durch weniger Runden, sein Kurseffekt liegt bei −1,7 $. Zweitens ist der „halbierte Rückgang“ von K2 nur seine Investitionsquote von 35 %: Seit 2022 und ohne das Jahr 2021 ist die einfache BTC-200-Regel M3 gleich gut oder besser. Drittens lassen sich die S7-Erfolgskriterien für Instanz A im Programm gar nicht messen.

# Advocatus-diaboli-Prüfung · A4 Einstieg · A5 Ausstieg · Strategie-Labor · 14.10.2026

Agent: **A10 advocatus-diaboli** (Data Scientist + Security Auditor als Gegenprüfer, Denkschule Michael Burry) · Instanz: **v6** (E7, 136 Runden) und **Labor** (Rückrechnung, 6 Bitvavo-USDC-Coins), strikt getrennt · Kostenlatte K = 0,150 % (Bitvavo USDC, Z1).
Geprüft: `berichte/2026-10-14_einstieg.md` (A4), `…_ausstieg.md` (A5), `…_strategie_labor.md`, `epochen/S7_papier_wettkampf.md`, Code `labor/backtest.py`, `stufe4/5/5b/5c`, `labor/papier/papier_tag.py`, A5-Skripte `a5_nachspielung.py`, `a5_explorativ.py`, `a5_motor.py`.
Svens Entscheidungen (Z1–Z4, F1–F8) stelle ich nicht in Frage. Ich prüfe nur, ob Zahlen und Umsetzung die Begründung tragen.
**Eigene Skripte** (nur lesend): `skripte/a10_e7_gegenrechnung.py`, `skripte/a10_labor_k2.py` (eigener Simulator, importiert `backtest.py` **nicht**), `skripte/a10_zusatz.py`. **Ergebnisse:** `daten/a10_*.json`. In Bot-Ordner und fremde Dateien wurde nichts geschrieben.

---

## 0 · Die 5 wichtigsten Befunde

| # | Problem | Ursache | Fix (Vorschlag, nicht umgesetzt) | Prio | Risiko | Aufwand | Impact |
|---|---|---|---|---|---|---|---|
| 1 | **S7-Erfolgskriterien sind für A nicht messbar.** Kriterium 2 (Rückgang) und Hypothese 2 (Sharpe) brauchen für A eine Kontokurve, `bot_a()` liefert nur Kasse-Netto geschlossener Runden. Hypothese 3 (Kostenanteil am Brutto) und Kriterium 3 („Verhalten wie Rückrechnung“) werden nirgends berechnet und haben keinen Zahlenbereich. M3, laut Labor seit 2022 der stärkste Gegner, steht in keinem Kriterium. | Programm und Registrierung wurden nicht gegeneinander geprüft | Nachtrag zur S7-Registrierung **vor dem ersten Ergebnis**: Tageskurve für A, Sharpe, Rückgang und Kostenanteil für alle, M3 als Pflicht-Latte, Zahlenband für Kriterium 3 | HOCH | 6 | 3 | 7 |
| 2 | **K2: Der „belastbare halbierte Rückgang“ ist eine Folge der Investitionsquote, kein Können.** 35 % BTC statisch plus 65 % Bargeld haben −36,6 % Rückgang, K2 −35,9 % (im Mittel 34,6 % investiert). Seit 2022 schlägt M3 K2 auf allen drei Maßen (30,2 %/Jahr · Sharpe 0,96 · −31,5 % gegen 26,7 % · 0,88 · −35,9 %). Ohne 2021 gilt K2 31,6 % gegen M3 35,3 %, Sharpe beide 0,98. | Vergleich gegen M1 (100 % investiert) statt gegen eine gleich stark investierte Latte | Im Wettkampf **M3** als Pflicht-Latte, Rückgang immer neben der Investitionsquote ausweisen | HOCH | 5 | 1 | 8 |
| 3 | **A5-V3 (X3): Der Vorteil kommt nur aus weniger Runden.** +27,9 $ bei K 0,150 = **−1,7 $ Kurseffekt** + 14,8 $ gesparte Kosten + **14,8 $ Nachspiel-Abschlag**, der bei 60 Runden weniger einfach wegfällt. Das 24-h-Band allein liegt brutto bei −8,8 $, nur X1 (2 × ATR-Abstand) bei brutto +21,8 $. | `a5_nachspielung.py:80` zieht 0,15 je nachgespielter Runde ab, auch im gepaarten Vergleich bei ungleicher Rundenzahl. A5s eigene Eichung findet den Motor im Mittel aber **0,11 ungünstiger** als echt [−0,27; +0,06]. | X3 nicht als Bündel registrieren. X1 allein im Schatten messen. Gepaarte Vergleiche zerlegen in Kurseffekt, Kosten und Abschlag. | HOCH | 4 | 2 | 6 |
| 4 | **A4-V1 (Halteband 12 h) ist realistisch kleiner und eine Trendwette.** Die Rechnung ohne Stopp unterstellt für jeden der 136 Käufe eigene 12 h, aber bei 57 Käufen kauft der Bot dieselbe Münze binnen 12 h erneut. Mit 1 Position je Münze, höchstens 3 und Notstopp 2,12 %: **+0,30 [−0,18; +0,87]** (n 98) statt +0,42. August +0,68, **Sep/Okt −0,08** [−0,65; +0,39]. | 12 h ist das Maximum von 7 Horizonten (Gewinner-Fluch). Keine Kapitalbindung, kein Stopp. | Erwartung in der Registrierung auf **≤ +0,15 nach Abschlag** senken, je Marktlage getrennt, mit Bindung und Notstopp | MITTEL | 3 | 2 | 5 |
| 5 | **Das Bitvavo-Plus der E7-Runden (+42,66 $) ist zerbrechlich.** 18,98 $ davon sind Papier-Füllungen unter dem letzten Minutenschluss, 17,08 $ allein aus 10 Käufen in Kurseinbrüche (Docht). Ohne diesen Füllvorteil bleiben +23,68 $, und alles stammt aus dem August (+54,73 $ gegen −12,07 $ Sep/Okt). | Papier füllt zum Augenblickskurs. Ob ein dünnes USDC-Buch in Sekunden-Einbrüchen genauso füllt, ist ungeprüft. | Bei E10/E11 Netto immer zweifach ausweisen (Füllkurs **und** letzter Minutenschluss). W3/K6 misst die Spanne in schnellen Bewegungen. | MITTEL | 5 | 2 | 6 |

Konfidenz: (1) [SICHER 95 %] · (2) [SICHER 90 %] für die Rechnung, [WAHRSCHEINLICH 75 %] für die Deutung · (3) [SICHER 90 %] Zerlegung, [WAHRSCHEINLICH 70 %], dass der Abschlag hier überzieht · (4) [SICHER 90 %] Rechnung, [WAHRSCHEINLICH 75 %] Deutung · (5) [SICHER 90 %] Rechnung, [VERMUTUNG 55 %] zur echten Bitvavo-Füllung.

---

## 1 · Unabhängig nachgerechnet (Pflicht: mindestens 2)

| Zahl | Bericht | A10 (eigener Code) | Skript | Urteil |
|---|---|---|---|---|
| E7 Runden · brutto · Gebühren · netto | 136 · +75,51 · 109,62 · −34,11 $ | **136 · +75,51 · 109,62 · −34,11 $** (eigene FIFO, qty × Kurs, Gebühr nur aus `fee`; 0 Teilverkäufe, 0 Mehrfachkäufe) | `a10_e7_gegenrechnung.py` | stimmt |
| E7 netto bei K 0,150 | +42,66 $ | **+42,66 $** (Volumen 43.794 $) | dto. | stimmt |
| Rückkauf binnen 24 h · Median · „Durchhalten besser“ | 117 / 6,0 h / +0,39 % | **117 / 6,0 h / +0,386 %** | dto. | stimmt, aber Mischwert: ≤ 6 h (40) −1,05 %, 6–24 h (77) **+1,13 %** |
| Bot 12 h ab letztem Minutenschluss · fest 12 h gegen Ist | +0,753 % · +0,42 | **+0,753 % · +0,421** | dto. | stimmt |
| Füllvorteil gegen letzten Minutenschluss · 10 Docht-Käufe | 20,06 $ · 17,15 $ | **18,98 $ · 17,08 $** (Docht-Runden brutto −8,29 $ = A4) | dto. | Größenordnung stimmt |
| K2 6 Coins: Rendite/Jahr · Rückgang · Sharpe | 57,3 % · −35,9 % · 1,35 | **57,3 % · −35,9 % · 1,35** | `a10_labor_k2.py` | stimmt exakt |
| K1 · M3 · M1 (6 Coins) | 59,3/−47,1/1,34 · 27,2/−63,9/0,78 · 25,9/−76,6/0,69 | **identisch** | dto. | stimmt |
| K2 Teilzeiträume P1/P2/P3 · Fenster 13.08.–13.10. | 40,3 / 511 / 26,7 % · +13,6 % | **40,3 / 511,1 / 26,7 % · +13,6 %** | dto. | stimmt |
| S7-Startbild Zielgewichte (Schluss 12.10.) | BTC 16,7 / ETH 16,0 / SOL 14,8 / XRP 12,3 / ADA 7,4 = 67 % | **identisch, 67,1 %** | dto. | stimmt |

**Was das heißt:** Rechenfehler habe ich keine gefunden [SICHER 95 %]. Die Schwächen liegen in der Deutung und im Versuchsaufbau, nicht in der Arithmetik.

---

## 2 · Urteile je offener Empfehlung (Übersicht)

| Empfehlung | Urteil | Was fehlt |
|---|---|---|
| A4-V1 Schattenbuch „Halteband 12 h“ (Erwartung +0,27) | **TRÄGT NICHT** (in der registrierten Form) | Erwartung ≤ +0,15, Bindung und Notstopp, je Marktlage. Mit A5-X1 in **eine** Schattenregistrierung. |
| A4-V2 EMA_TREND nach Marktlage erst mit W1 | **TRÄGT** (als Reihenfolge), Wirkung +24 $ NICHT ENTSCHEIDBAR | W1-Definition vorab, ≈ 140 Runden je Lage |
| A4-V3 keine Score-Schwelle, IC-Test registrieren | **TRÄGT** | Rundenbedarf mit IC ≈ 0,09 statt 0,17 rechnen (≈ 1.241 statt 272/431) |
| A4-V4 kein Anstiegsfilter | **TRÄGT** (keine Änderung ist der Normalfall) | Beleg in beide Richtungen schwach, ≈ 82 Runden je Drittel |
| A4-V5 Einstiegsmessung als Dauerprüfung | **TRÄGT** | Entscheidungsregel für 300/616 Runden. Für einen Beleg ≈ 2.200 Runden ≈ 32 Monate: ein Überwachungswerkzeug, kein Entscheidungswerkzeug. |
| A5-V2 Puffer K + 0,10 = 0,25 | **TRÄGT** (Arithmetik, ≈ +1 $ je 2 Monate) | nichts Wesentliches; mit der nächsten Bitvavo-Epoche bündeln |
| A5-V3 Schattenregel X3 (2 × ATR + 24-h-Band) | **TRÄGT NICHT** (als Bündel) | X1 allein messen (≈ 570 Runden). Das Band lässt sich im Schattenbuch nicht sauber messen, weil es Käufe streicht. [VERMUTUNG, `exit_rules_schatten.py` nicht gelesen] |
| A5-V4 RSI-Verkaufssignal im Schatten | **TRÄGT** (als Messung), Regeländerung NICHT ENTSCHEIDBAR | je Marktlage getrennt; das Signal half im Sep/Okt (−1,09 nach 24 h) |
| A5-V5 breite Ausstiege NICHT einführen | **TRÄGT** | – |
| Labor: K2 als Kandidat | **TRÄGT** als Papier-Kandidat (Code korrekt). Die Begründung „belastbar = halbierter Rückgang“ TRÄGT NICHT, der Vorsprung vor M3 ist NICHT ENTSCHEIDBAR. | M3 als Pflicht-Latte, Rückgang je Investitionsquote |
| S7 Erfolgskriterien | **TRÄGT NICHT** (wie umgesetzt) | Kontokurve für A, Sharpe, Rückgang und Kostenanteil für alle, M3 im Kriterium, Zahlenband für Kriterium 3, A auf eine Epoche festlegen |
| S7 Abbruch „Rückgang > 25 % in 3 Monaten“ | **TRÄGT** | – (historisch 3,4 % aller 91-Tage-Fenster, seit 2022 6,2 %) |

---

## 3 · Debatten (je 3 stärkste Argumente mit Zahlen)

### A4-V1 · Schattenbuch „Halteband 12 h“
**Position A, richtig:**
1. Fest 12 h schlägt die echten Ausstiege auf denselben 136 Käufen um +0,42 [−0,03; +0,88] (nachgerechnet +0,421).
2. A5 sieht dasselbe Muster: 117 von 136 Verkäufen binnen 24 h zurückgekauft, Durchhalten +0,39 % [+0,01; +0,79].
3. Ein Schattenbuch kostet kein Geld und keine Runde.

**Position B, falsch:**
1. Die Rechnung gibt jedem Kauf eigene 12 h, aber 57 von 136 Käufen folgt binnen 12 h ein neuer Kauf derselben Münze (92 binnen 24 h). Mit 1 Position je Münze, höchstens 3 und Notstopp 2,12 % bleiben 98 Runden und **+0,30 [−0,18; +0,87]**, nach A4s eigenem Abschlag +0,15 und damit genau auf der Hypothesen-Schwelle.
2. Es ist eine Trendwette: August +0,68 [−0,03; +1,71], **Sep/Okt −0,08 [−0,65; +0,39]**. Netto K 0,150 im Sep/Okt liegt die Variante bei −20,39 $, das Ist auf denselben Käufen bei −8,18 $.
3. 12 h ist das Maximum von 7 Horizonten, nachträglich gewählt. Bei 24 h liegt der Vorsprung wieder bei −0,04.

**Urteil: TRÄGT NICHT** in der registrierten Form. Messen ja, aber mit Bindung, Notstopp, Erwartung ≤ +0,15 und getrennt je Lage.

### A4-V2 · EMA_TREND nach Marktlage, erst mit W1
**A:**
1. EMA_TREND bei K 0,150: August +33,41 $, Sep/Okt −24,25 $ (Differenz +0,75 je Runde).
2. Das Bot-Feld `market_regime` taugt nicht als Schalter: 40 von 73 Augustkäufen tragen RANGING, obwohl der Korb +30 % stieg.
3. Eine pauschale Sperre hätte gekostet: EMA_TREND gesamt +9,17 $ bei K 0,150.

**B:**
1. Die Lage-Trennung ist nach Kalender gezogen (Rückblick), und es gibt nur einen einzigen Lagewechsel in den Daten.
2. EMA im Sep/Okt −0,32 [−1,28; +0,52] bei 37 Runden. Ein Einzelbeleg bräuchte ≈ 478 Runden.
3. Seine Sep/Okt-Einstiege liegen 4 h danach +0,44 über Zufall. Der Verlust entsteht durch Stopps (15 von 37), also bei Ausstieg und Haltedauer. Eine Lage-Sperre träfe das falsche Bauteil.

**Urteil: TRÄGT** als Reihenfolge („jetzt nichts sperren, erst W1“). Die +24 $ sind NICHT ENTSCHEIDBAR.

### A4-V3 · Keine Score-Schwelle, IC-Test registrieren
**A:**
1. Die Score-Stufen steigen nicht durchgehend: 3–5 +0,01, 6–7 +0,38, 8 +0,72, 9–10 −0,01 % je Runde.
2. IC 12 h +0,17 [−0,02; +0,33], nach Bonferroni nicht belegt.
3. Auf 3.171 Kandidaten-Stunden liegt der IC nur bei 0,03–0,09.

**B:**
1. IC 4 h +0,23 [+0,02; +0,42] ist ein Bereich ohne Null.
2. Score 8 bringt +33,84 $ netto bei K 0,150, mehr als jede andere Gruppe.
3. Gegen die Registrierung selbst: Der Bedarf von 272/431 Runden setzt den IC 0,17 der gekauften Runden an (Gewinner-Fluch). Mit 0,09 aller Kandidaten sind es ≈ 1.241 (A4s eigene Zahl für IC 0,10).

**Urteil: TRÄGT**, mit korrigiertem Rundenbedarf.

### A4-V4 · Kein Anstiegsfilter
**A:**
1. Das obere Vorlauf-Drittel liegt nach 4 h +0,46 [−0,04; +0,83] über Zufall, das untere −0,12.
2. Der Tagesvergleich, der für einen Filter sprach, ist verzerrt (Placebo −0,46 [−0,72; −0,19] ohne Signal).
3. Rangkorrelation Vorlauf ↔ Ist-Brutto −0,02 [−0,27; +0,20].

**B:**
1. Ist-Brutto im oberen Drittel +0,31 % gegen +0,57 % im mittleren, 13 gegen 9 Stopps.
2. Der Bot kauft nach +2,25 % in 24 h (Zufall +0,95 %). Wie das im Seitwärtsmarkt wirkt, ist nicht getrennt gezeigt.
3. 45/46 Runden je Drittel, nötig wären ≈ 82.

**Urteil: TRÄGT** (keine Änderung ist der Normalfall). Der Beleg ist schwach.

### A4-V5 · Einstiegsmessung als Dauerprüfung
**A:**
1. A4 hat zwei Messfehler gefunden (Tagesvergleich, Stundenraster: 1 h +0,08 statt +0,17). Eine feste Methode verhindert ihre Wiederkehr.
2. Die Messung liest nur und kostet nichts.
3. Sie liefert die Zerfallskurve je Lage für W1/A7.

**B:**
1. „12 h > K“ zu belegen braucht ≈ 2.200 Runden, also ≈ 32 Monate.
2. Der Laufzeit-Zufall hängt an `evaluations`, und jede neue Epoche ändert die Kandidatenmenge.
3. Kursquelle ist Binance, Zielbörse Bitvavo (Versatz < 0,005 %, unkritisch).

**Urteil: TRÄGT** als Überwachung. Es fehlt eine vorab festgelegte Entscheidungsregel für 300/616 Runden.

### A5-V2 · Puffer K + 0,10 = 0,25
**A:**
1. Auslöseverzug Ø 0,072, p90 0,17 bei einer Marge von nur 0,045: Jede Nullsicherung endet im Mittel bei −0,027 %.
2. Mit 0,25 sind es +0,028 %.
3. Die Nachspielung zeigt −0,7 $ [−5,0; +2,3]. Der Puffer kostet also nichts.

**B:**
1. Die Wirkung liegt bei ≈ +1 $ je 2 Monate, das ist kein Hebel.
2. Für 80 % Trennschärfe braucht es 94 Fälle.
3. Bei K 0,150 liegen 20 von 21 Nullsicherungen ohnehin im Plus (+4,16 $).

**Urteil: TRÄGT** (Arithmetik). Bündeln, keine eigene Epoche.

### A5-V3 · Schattenregel X3 (2 × ATR + 24-h-Halteband)
**A:**
1. X3 gepaart +27,9 $ [−17,9; +74,4] bei K 0,150, +62,9 $ [+18,6; +109,4] bei K 0,505.
2. 0,85 % Abstand liegt im Rauschband: Bei SOL reißen 70 % der Zufallsstarts ihn binnen 4 h.
3. 117 von 136 Verkäufen wurden binnen 24 h zurückgekauft.

**B:**
1. Die Zerlegung zeigt X3 = **−1,67 $ Kurseffekt** + 14,79 $ gesparte Kosten + **14,79 $ weggefallener Abschlag** (63 statt 123 Runden). Ohne das Abschlag-Artefakt bleiben +13,1 $, und das sind nur gesparte Gebühren.
2. Das Band allein (X2) liegt brutto bei −8,8 $, nur X1 bei +21,8 $. X3 bündelt einen positiven und einen negativen Teil.
3. Die Varianten wurden nach Datensicht gewählt. Gestrichene Käufe erzeugen in der Nachspielung keine Ersatzkäufe. Nötig wären ≈ 780 Runden.

**Urteil: TRÄGT NICHT** als Bündel. X1 allein ist NICHT ENTSCHEIDBAR und gehört als Schattenmessung registriert.

### A5-V4 · RSI-Verkaufssignal im Schatten
**A:**
1. Ohne Signal +22,5 $ [−0,5; +52,0], im August +19,2 $ [+0,5; +43,6].
2. Nach Signal-Verkäufen im August steigt der Kurs in 1 h um +0,86 [+0,21; +1,80].
3. Die Messung kostet nichts.

**B:**
1. Im Sep/Okt fällt der Kurs nach Signal-Verkäufen in 24 h um −1,09 [−2,40; −0,54]: Dort war das Signal richtig.
2. 21 Signale (13 August, 8 Sep/Okt).
3. Das Signal abzuschalten ist selbst eine Trendwette.

**Urteil: TRÄGT** als Messung, je Lage getrennt. Die Regeländerung ist NICHT ENTSCHEIDBAR.

### A5-V5 · Breite Ausstiege nicht einführen
**A:**
1. „weit“: August +62,6 $ (22 Runden), Sep/Okt +5,1 $ (16), also n < 30.
2. Stundenkerzen schönen breite Regeln um 27 bis 58 $.
3. Zerlegung: „mittel“ brutto **−2,83 $**, sein +36,2 $ ist 19,5 $ Kosten plus 19,5 $ Abschlag. „weit“ brutto +20,3 $ (von +67,7 $).

**B:**
1. „weit“ bei K 0,505: +123,8 $ [+5; +249], der einzige Bereich ohne Null (Bonferroni [−74; +317]).
2. Klammer-Raster August: S 2,12 / T 3 +1,09 [+0,22; +1,82].
3. Das Labor zeigt: Trendfolge mit weiten Ausstiegen ist die einzige Klasse mit Rendite nach Kosten.

**Urteil: TRÄGT.** B3 gehört in den Trend-Baustein (Labor), nicht in den Kurzfrist-Bot.

### Labor · K2 als Kandidat
**A:**
1. Unabhängig nachgerechnet: 57,3 %/Jahr, −35,9 %, Sharpe 1,35. Robust auch auf 6 Coins:

   | Variante | Rendite/Jahr | Sharpe | Rückgang |
   |---|---|---|---|
   | ohne SOL | 48,2 % | 1,21 | – |
   | ohne DOGE | 49,9 % | 1,33 | – |
   | Ausführung +1 Tag | 57,2 % | 1,34 | −39,7 % |
   | Kosten 1,00 % | 51,9 % | 1,26 | – |

   Diese Prüfung fehlte im Labor, das die Robustheit nur auf 12 Coins gerechnet hat.
2. 2,5 Runden im Monat, Kosten spielen kaum eine Rolle.
3. Ein 91-Tage-Rückgang über 25 % kam nur in 3,4 % der Fenster vor (M1: 44,8 %).

**B:**
1. **Ohne 2021: K2 31,6 %/Jahr gegen M3 35,3 %, Sharpe beide 0,98.** K2 war in 5 von 9 Kalenderjahren schlechter als M3 (2019, 2020, 2022, 2023, 2026).
2. **Seit 2022 schlägt M3 K2 auf allen drei Maßen:** 30,2 %/Jahr gegen 26,7 %, Sharpe 0,96 gegen 0,88, Rückgang −31,5 % gegen −35,9 %. K2s größter Rückgang lag zwischen 11.03. und 03.10.2024, also im heutigen Regime.
3. Der halbierte Rückgang kommt aus der Investitionsquote: 35 % BTC statisch haben −36,6 %. Dazu die Überlebenden: Mit nur BTC+ETH bringt K2 28,7 %/Jahr.

**Urteil: TRÄGT** als Papier-Kandidat (Svens Entscheidung Z3, Code korrekt). Die Begründung „belastbar = halbierter Rückgang“ TRÄGT NICHT, der Vorsprung vor M3 ist NICHT ENTSCHEIDBAR.

### S7 · Erfolgskriterien
**A:**
1. Vorab festgelegt, mit ehrlichem Vorbehalt („kein statistischer Beweis“).
2. Das Abbruchkriterium ist passend kalibriert: Ein Rückgang über 25 % in 91 Tagen kam in 3,4 % der Fenster vor, seit 2022 in 6,2 %.
3. Deterministisch, derselbe Simulator wie die Rückrechnung (von mir bestätigt).

**B:**
1. Für A nicht messbar: `bot_a()` (`papier_tag.py:149–160`) liefert keine Kontokurve, keinen Rückgang und keine Sharpe. Kostenanteil und Kriterium 3 fehlen ganz.
2. Die 3-Monats-Rendite ist ein Münzwurf: K2 lag in 33–36 % aller 91-Tage-Fenster im Minus, Median 0,0 %. K2 gegen M3 seit 2022: besser 33 %, gleich 27 %, schlechter 40 %.
3. Drei Aufbaufehler:
   - B = C, solange BTC über der 200-Tage-Linie liegt (heute +15,25 %).
   - A ist ein bewegliches Ziel: „Epoche E11 ff.“, 3 Coins, höchstens ≈ 90 % investiert, dagegen B/C 6 Coins und heute 67 %.
   - M3 fehlt im Kriterium.

**Urteil: TRÄGT NICHT** wie umgesetzt.

---

## 4 · Prüfliste (Matrix)

Zeichen: **ok** unkritisch · **!** Schwäche, offen benannt · **!!** trägt die Aussage nicht oder verzerrt sie stark · – nicht anwendbar

| Prüfpunkt | A4-V1 | A4-V2 | A4-V3 | A4-V4 | A4-V5 | A5-V2 | A5-V3 | A5-V4 | A5-V5 | K2 | S7 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zu wenige Runden | !! | !! | ! | ! | ok | ok | !! | !! | ! | ok | !! |
| überlappende Haltezeiten | **!!** | ok | ! | ok | ok | ok | ! | ok | ok | ok | ! |
| Blick in die Zukunft | ! | **!!** | ok | ok | ok | ok | !! | ! | ok | ok | ok |
| Überanpassung (viele Varianten) | ! | ! | ok | ok | ok | ok | **!!** | ! | ok | ! | ok |
| Überlebenden-Fehler | ok | ok | ok | ok | ok | ok | ok | ok | ok | **!!** | ok |
| Marktlage | **!!** | !! | ! | ! | ok | ok | ! | !! | !! | **!!** | **!!** |
| Nachspielung zu günstig | **!!** | – | – | – | – | ok | **!!** | ! | ! | ok | ! |
| Kosten zu niedrig | ! | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Instanzen vermischt | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | **!!** |
| Messfenster falsch geschnitten | ! | ! | ok | ok | ok | ok | ok | ! | ok | ! | ! |

Erläuterung der fetten Felder:
- **A4-V1 überlappend:** 57 von 136 12-h-Fenstern überlappen mit dem nächsten Kauf derselben Münze.
- **A4-V1 Nachspielung:** Die Rechnung läuft ohne Notstopp und ohne Bindung. Mit beidem sinkt der Effekt von +0,49 auf +0,30 (beide ab Füllkurs gerechnet).
- **A4-V2 Zukunft:** Die Lage ist nach Kalender gezogen.
- **A5-V3 Überanpassung:** X1–X3 wurden nach Sichtung der Daten gewählt, über 9 Vergleiche.
- **A5-V3 Nachspielung:** Der Abschlag wirkt bei ungleicher Rundenzahl wie eine Prämie für weniger Runden (14,8 $).
- **K2 Überlebende:** nur Gewinner von heute, mit nur BTC+ETH 28,7 %/Jahr.
- **K2 Marktlage:** Ohne 2021 liegt K2 nicht vor M3.
- **S7 Marktlage:** 3 Monate messen vor allem die Marktrichtung.
- **S7 Instanzen:** A wechselt Epochen, und Coins und Investitionsquote unterscheiden sich.

Weitere Hinweise:
- „Kosten zu niedrig“ bei A4-V1 und beim E7-Bitvavo-Plus: 18,98 $ Füllvorteil (Befund 5).
- „Messfenster“: Sep/Okt enthält die Abschaltung vom 08.–20.09. Beim Start im Hoch vom 10.11.2021 liegen K2 bei 21,5 %/Jahr und M3 bei 19,0 %/Jahr.

---

## 5 · Code-Gegenlesen

### 5.1 `labor/backtest.py` · kein Fehler gefunden [SICHER 90 %]
| Prüfung | Fundstelle | Ergebnis |
|---|---|---|
| Blick in die Zukunft | `K1Trend.ziel` Z. 135–167: Signal, Mitte, Schwankung nur aus `c[..i]`; `simuliere` Z. 257–263: Ausführung `o[i+1]` | ok. Zusätzlich hält mein eigener Simulator dieselben Regeln ein und kommt auf die Kommastelle zum selben Ergebnis. |
| Ausstieg gegen Vortages-Stopp | Z. 155–158: `if c[i] < s` mit `s` vom Vortag, danach `max(s, mitte)` | ok |
| Positionsgröße | Z. 166: `min(1/len(da), aktiv/9 · 0,25/vol)`; `da` = Coins mit ≥ 91 Schlüssen | ok. Hinweis: In den ersten Jahren ist N kleiner (z. B. 4), dann liegt die Obergrenze je Coin bei 25 % statt 16,7 %. So ist es auch vorgegeben. |
| Hebel | Gewichte ≤ 1/N, Kauf ≤ `cash/(1+k)` (Z. 311) | ok, Summe ≤ 100 % |
| Kosten | K/2 je Seite auf jeden gehandelten Betrag, auch beim Umschichten, Kaufgebühr obendrauf | ok |
| Kostenbremse | „und“ statt Svens wörtlichem „oder“, im Code-Kopf offen benannt, „oder“ als Robustheitstest | ok (benannte Abweichung) |
| Datenlücke | `verfuegbar()` falsch → alle L-Zustände des Coins auf None → Zwangsverkauf | historisch ohne Wirkung (0 Lücken laut `pruefbericht.json`). Im Papierbetrieb nur ein Risiko bei Datenfehlern. [VERMUTUNG, nicht ausgelöst] |
| Deflated Sharpe | `deflated_sharpe` mit der Varianz von 27 sehr ähnlichen Varianten | Wert nahe 1 ist geschönt (im Labor-Bericht 5.3 benannt) |

### 5.2 `labor/papier/papier_tag.py` · Abweichungen zur Rückrechnung

**[FEHLER] Erfolgskriterien von S7 für A nicht berechenbar**
- **[URSACHE]** `bot_a()` (Z. 149–160) zählt nur geschlossene Runden mit Kauf ab 15.10. als Kasse. Es gibt keine Tageskurve, offene Positionen werden nicht bewertet. `auswerten()` (Z. 133–146) liefert für B und C keine Sharpe und keinen Kostenanteil am Brutto. Kein Feld prüft Investitionsquote und Rundenzahl „im Bereich der Rückrechnung“.
- **[BEWEIS]** Rückgabefelder von `bot_a()`: `name, runden, netto_usd, rendite_pct_auf_500, kosten_usd, hinweis`. Gefordert sind laut S7 Kriterium 2 „größter Rückgang nicht größer“ sowie die Hypothesen 2 (Sharpe gegen A) und 3 (Kostenanteil).
- **[FIX]** (Vorschlag, nicht umgesetzt; Code vorher/nachher):

```python
# VORHER (papier_tag.py:155-158)
netto = sum(r["netto"] for r in rd)
return {"name": "A heutiger Bot v6", "runden": len(rd), "netto_usd": round(netto, 2),
        "rendite_pct_auf_500": round(netto / 5, 2), ...}

# NACHHER (Skizze): Tageskurve A = 500 + realisiertes Netto bis Tag d
#                   + offene Menge x Tagesschluss - offener Kaufabfluss
kurve = []
for d in tage_seit_start:                                   # UTC-Tage ab 15.10.
    real = sum(r["netto"] for r in rd if r["t"][:10] <= d)
    offen = offene_positionen_am(d)                         # aus trades_v5: BUY ohne SELL bis Tagesende d
    wert = sum(p["qty"] * schluss[p["coin"]][d] - p["abfluss"] for p in offen)
    kurve.append(500 + real + wert)
# dann dieselbe Rueckgang/Sharpe-Funktion wie fuer B, C und M1-M3; Kostenanteil = Kosten / (Netto + Kosten)
```
- **[TEST]** Für das E7-Fenster 13.08.–13.10. rückwärts laufen lassen. Der Endwert nach Kasse muss 500 − 34,11 $ ergeben. An Tagen mit offenen Positionen dürfen die Tagesrenditen nicht null sein.

**Weitere Abweichungen (LOW):**
1. **Kostenmodell:** Papier 0,05 % + halbe Spanne je Coin (BTC 0,066 % … DOGE 0,143 % je Seite), Rückrechnung pauschal 0,075 %. „Genau wie in der Rückrechnung“ (S7) gilt also nur für die Logik. Wirkung klein, K2 ist kostenunempfindlich.
2. **Ausführung zum 00:00-UTC-Eröffnungskurs**, der Lauf beginnt aber 02:15 Berlin (bis 25.10. 00:15 UTC, danach 01:15 UTC). Fällt der Rechner aus, werden vergangene Eröffnungen nachgerechnet. Das ist eine fortgeschriebene Rückrechnung, keine Ausführungsprobe (in S7 so benannt). Ein Blick in die Zukunft entsteht dadurch nicht.
3. **`selbsttest()` löscht** `B_/C_journal.csv` und `B_/C_kurve.csv` im Live-Ordner (Z. 249–250). Das ist harmlos, weil der nächste Lauf alles deterministisch neu erzeugt. Am Montag nach dem Wochenbericht aber nicht aufrufen.
4. **B = C bis BTC < SMA200:** BTC-Schluss 13.10. bei 83.169, SMA200 bei 72.167 (+15,25 %). C liefert erst nach einem Rückgang von mehr als ≈ 13 % eigene Information.

### 5.3 A5-Methode · Abschlag in gepaarten Vergleichen (Methodenfehler, kein Code-Fehler)
- **[FEHLER]** Gepaarte Vergleiche bei ungleicher Rundenzahl rechnen den Nachspiel-Abschlag als Vorteil für die Variante mit weniger Runden.
- **[URSACHE]** `a5_nachspielung.py:80` rechnet `kauf_nominal * (kurs_pct − K − ABSCHLAG)` in beiden Armen.
- **[BEWEIS]** Zerlegung des gepaarten Vorteils bei K 0,150 (`a10_e7_gegenrechnung.json`, `a10_zusatz.json`). Die Spalten Kostenersparnis und Abschlag sind gleich groß, weil K und Abschlag beide 0,15 betragen.

  | Variante | gepaart K 0,150 | Kurseffekt | Kostenersparnis | Abschlag |
  |---|---|---|---|---|
  | X3 | +27,9 | **−1,7** | 14,8 | 14,8 |
  | X1 | +36,4 | +21,8 | 7,4 | 7,4 |
  | X2 | +18,0 | **−8,8** | 13,4 | 13,4 |
  | mittel | +36,2 | **−2,8** | 19,5 | 19,5 |
  | weit | +67,7 | +20,3 | 23,7 | 23,7 |

  Gegenrechnung aus A5s eigener Eichung: Der Motor liegt im Mittel 0,11 [−0,27; +0,06] **unter** echt.
- **[FIX]** Gepaarte Ergebnisse immer dreigeteilt ausweisen. Den Abschlag nur für den Ausführungsfehler gleicher Ausstiegsart ansetzen (A5: +0,08 bis +0,14).
- **[TEST]** Kurseffekt + Kostenersparnis + Abschlag = gepaarte Differenz (geht in allen 8 Varianten auf).

---

## 6 · Gesamturteil (5 Sätze): Wie wird der Bot nach Kosten profitabel?

1. A4 und A5 zusammen zeigen, dass der heutige Kurzfrist-Bot weder beim Einstieg noch beim Ausstieg einen nachweisbaren Vorsprung hat. Sein Brutto in E7 ist Marktdrift (Können −0,05 [−0,55; +0,41]), und auch bei Bitvavo-Kosten kommt das ganze Plus aus dem August (+54,73 $ gegen −12,07 $ im Sep/Okt), knapp die Hälfte davon aus Papier-Füllungen unter dem letzten Minutenschluss (18,98 $).
2. Beim E7-Umschlag kostet selbst Bitvavo rund 197 $ im Jahr, also 39 % der 500 $ (bei Dauerbetrieb 56 %). Das ist mehr, als BTC halten in der Rückrechnung je Jahr bringt (25,9 %), deshalb kann dieser Bot nach Kosten nur in starken Anstiegen verdienen.
3. Jede Variante, die in den drei Berichten „gewinnt“ (Halteband 12/24 h, X3, weite Ausstiege, K2), gewinnt auf dieselbe Weise: weniger Runden und länger im Markt während eines Anstiegs. Ein Zeitpunkt-Können zeigt keine (X3 Kurseffekt −1,7 $, „mittel“ −2,8 $, 12 h Halten im Sep/Okt −0,08 je Runde).
4. Profitabel nach Kosten wird der Bot daher am ehesten, wenn er vom Kurzfrist-Handel auf eine langsame Trendregel mit wenigen Runden wechselt. Ob dafür das Ensemble K2 nötig ist oder die einfache BTC-200-Regel M3 reicht, ist offen: Seit 2022 und ohne 2021 ist M3 gleich gut oder besser.
5. Konfidenz: [WAHRSCHEINLICH 75 %], dass der Kurzfrist-Bot auch bei K 0,150 in einer Seitwärts- oder Abwärtsphase nach Kosten nicht profitabel ist, und [VERMUTUNG 55 %], dass eine langsame Trendregel ihn über 12 Monate nach Kosten schlägt. Der 3-Monats-Wettkampf entscheidet keins von beiden statistisch.

---

## 7 · WEISS | SCHLIESSE | VERMUTE

- **WEISS:**
  - Alle 9 nachgerechneten Zahlen stimmen (Abschnitt 1).
  - X3 hat einen Kurseffekt von −1,7 $, „mittel“ −2,8 $, X2 −8,8 $.
  - K2 erreicht seit 2022 bei keinem der drei Maße M3.
  - 35 % BTC statisch haben −36,6 % Rückgang.
  - 57 von 136 E7-Käufen folgt binnen 12 h ein Kauf derselben Münze.
  - `bot_a()` liefert keine Kontokurve.
- **SCHLIESSE:**
  - Die Kurzfrist-Mechanik erzeugt Kosten, aber keinen belegten Wert.
  - Der Gewinnhebel aller drei Berichte heißt „Marktlage × Belichtung × wenige Runden“.
- **VERMUTE:**
  - Ein dünnes Bitvavo-USDC-Buch füllt Käufe in Kurseinbrüche schlechter als das Papier [55 %].
  - Das Schattenbuch im `exit_monitor` kann ein Rückkauf-Band nicht sauber abbilden [60 %, `exit_rules_schatten.py` nicht gelesen].

## 8 · Nicht geprüft

- A4s Drift-Rechnung (Laufzeit-Stunden aus `evaluations`). Ich habe die Methode gelesen, aber nicht nachgerechnet.
- A5s Motor Minute für Minute (Reihenfolge Hoch/Tief innerhalb der Minute). Die Eichung (115 von 136 gleiche Ausstiegsart) habe ich übernommen.
- Die 12-Coin-Robustheit (Stufe 5) habe ich nicht erneut gerechnet. Stattdessen habe ich die 6-Coin-Robustheit neu gerechnet, weil der Wettkampf auf 6 Coins läuft.
- `exit_rules_schatten.py`, die echte Bitvavo-Füllung in schnellen Bewegungen sowie Steuern.

---

## 9 · Sven entscheidet

- [ ] **S7-Nachtrag vor dem ersten Ergebnis:** Kontokurve für A, Sharpe, Rückgang und Kostenanteil für alle Instanzen, Zahlenband für Kriterium 3.
- [ ] **M3 (BTC-200) als Pflicht-Latte** in die S7-Erfolgskriterien aufnehmen (B/C müssen auch M3 schlagen, nicht nur A)?
- [ ] **A in S7 auf eine Epoche festlegen** (z. B. E11) oder ausdrücklich „v6, jede Epoche“ mit Epochengrenzen im Wochenbericht?
- [ ] **A5-V3:** X1 (2 × ATR-Abstand) allein im Schatten statt des Bündels X3?
- [ ] **A4-V1:** Registrierung mit Bindung, Notstopp, Erwartung ≤ +0,15 und Trennung je Lage, zusammen mit X1 in **einer** Schattenregistrierung?

**Genau EIN nächster Schritt:** Den S7-Nachtrag (Kontokurve A, M3 im Kriterium, Zahlenband für Kriterium 3) vor dem ersten Wochenbericht am Montag, 19.10.2026, registrieren, mit Zeitstempel vor jeder Ergebnis-Sicht.

**Selbstbewertung:** Präzision 8 · Vollständigkeit 7 · Umsetzbarkeit 8 → **7,5 / 10**.
- Stark: Ich habe alles nachgerechnet, die Labor-Ergebnisse mit eigenem Code reproduziert und die Abschlag-Zerlegung gefunden.
- Abzug: Drift-Rechnung und Motor im Detail sind nicht nachgerechnet, und die Schattenbuch-Machbarkeit ist nur vermutet.
- Nebenbefund zum Ablauf: Die Abschnitte „Gegenprüfung (A10)“ im Labor-Bericht (Abschnitt 7) sowie in E10 und E11 hat der jeweils ausführende Agent selbst geschrieben. Eine unabhängige A10-Prüfung waren sie nicht.

### Dateien
- Bericht: `pruefstand\berichte\2026-10-14_advocatus.md` und `.json`
- Skripte: `pruefstand\skripte\a10_e7_gegenrechnung.py`, `a10_labor_k2.py`, `a10_zusatz.py`
- Ergebnisse: `pruefstand\daten\a10_e7_gegenrechnung.json`, `a10_labor_k2.json`, `a10_zusatz.json`
