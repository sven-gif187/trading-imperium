<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · Strategie-Labor Stufe 7 · Papier-Wettkampf

Registriert: 14.10.2026, vor dem Start. Freigabe: Sven, Chat 14.10.2026 („Stufe 7 freigegeben, C = K1“, Z3).
Grundlage: `berichte/2026-10-14_strategie_labor.md`, Programm `labor/papier/papier_tag.py`, Windows-Aufgabe `TI-Labor-Papier` (täglich 02:15 Berlin und bei Anmeldung).

## Teilnehmer

| | Was | Kapital | Kosten |
|---|---|---|---|
| A | heutiger Bot **v6** (Epoche E11 ff.), ausgewertet aus `trades_v5.json`: abgeschlossene Runden mit Kauf ab 15.10., als Kasse | Bezug 500 $ | Bitvavo (im Bot) |
| B | **K2** Trend-Ensemble + BTC-200-Filter, 6 Coins (BTC, ETH, SOL, XRP, ADA, DOGE) | 500 $ Papier | 0,05 % + halbe Bitvavo-Spanne je Coin (BTC 0,066 % … DOGE 0,143 % je Seite) |
| C | **K1** Trend-Ensemble ohne Filter, dieselben 6 Coins | 500 $ Papier | wie B |
| M1–M3 | BTC halten, Korb 6 monatlich, BTC über 200-Tage-Linie, nur rechnerisch | 500 $ | wie B |

Erster Signal-Tagesschluss 14.10.2026 (UTC). Erste Ausführung zur **Eröffnung am 15.10.2026**. Danach Signal am Tagesschluss, Ausführung zur nächsten Eröffnung, genau wie in der Rückrechnung (derselbe Simulator, Determinismus geprüft).

**Startbild (Stand Schluss 12.10.):** BTC liegt über seiner 200-Tage-Linie, daher sind **B und C zur Zeit identisch**. Beide zielen auf BTC 16,7 / ETH 16,0 / SOL 14,8 / XRP 12,3 / ADA 7,4 %, zusammen 67 % investiert. Sie trennen sich erst, wenn BTC unter die Linie fällt.

## Hypothesen

1. B und C haben einen **kleineren größten Rückgang** als M1 und M2 und als A.
2. B und C haben nach Kosten eine **höhere Rendite je Risiko** (Sharpe) als A.
3. Kosten fressen bei B und C weniger als 15 % des Bruttogewinns, bei A über 100 %.

## Messgrößen (wöchentlich, Montag)

Rendite seit Start, größter Rückgang, Kosten in $ und als Anteil am Brutto, Zahl der Orders und Runden, Investitionsquote. Je Instanz gegen M1–M3 und gegen A.

## Erfolgskriterien nach mindestens 3 Monaten (vorab festgelegt, Vorschlag aus Stufe 6)

- **B (oder C) gilt als besser als A**, wenn alle drei Punkte erfüllt sind:
  1. Die Rendite nach Kosten ist höher.
  2. Der größte Rückgang ist nicht größer.
  3. Das Verhalten passt zur Rückrechnung: Investitionsquote und Rundenzahl liegen im Bereich der Rückrechnung für vergleichbare Marktlagen.
- **Ehrlich vorab:** Bei rund 2,5 Runden im Monat beweisen 3 Monate keinen Renditevorsprung statistisch. Die Entscheidung nach 3 Monaten ist deshalb „weiter beobachten, umstellen oder abbrechen“ und kein Beweis.

## Abbruchkriterien

- Rückgang von B oder C über 25 % in den ersten 3 Monaten. Die Rückrechnung hatte −36 % über 8 Jahre, 25 % in 3 Monaten wäre also auffällig. In dem Fall prüfen statt weiterlaufen.
- Kontrolle Konto ≠ Summe der Runden.
- Datenquelle fällt mehr als 3 Tage aus.

## Was hier NICHT gemessen wird

Echte Ausführung bei Bitvavo (Füllung, Spanne nachts), Steuern, das Verhalten bei schnellen Abstürzen innerhalb eines Tages (Signale nur am Tagesschluss).

## Start

- Programm und Aufgabe eingerichtet am 14.10.2026, 22:05 Berlin. Erster Lauf mit Ausführung: 15.10.2026 02:15 Berlin (Eröffnung 15.10. UTC).

---

## Nachtrag 1 · Messung messbar gemacht (A10-Befund 1)

**Zeitpunkt und Ehrlichkeit:** Den Code habe ich am 14.10.2026 um 23:37 Berlin geschrieben, vor jedem Ergebnis (`papier.log`: „Wettkampf hat noch nicht begonnen“). Den Text hier habe ich am 15.10. gegen 10:50 Berlin eingetragen. Da lag schon der erste Tag vor: B und C −0,05 %, das sind nur die Kaufkosten. Daraus lässt sich nichts über die Kriterien ablesen. Der Lauf um 02:15 ist mangels Internet ausgefallen und wurde um 10:39 nachgeholt. Weil die Rechnung deterministisch ist, ändert das nichts.

**Anlass:** A10 (`berichte/2026-10-14_advocatus.md`, Befund 1) zeigt, dass die Kriterien für A gar nicht messbar waren. A hatte keine Kontokurve, keinen Rückgang und keine Sharpe. Kostenanteil und Kriterium 3 hatten keinen Zahlenbereich.

**Was sich ändert (nur Messung, an keiner Strategie ändert sich etwas):**

1. **Tageskurve für A:** 500 $ plus Netto der geschlossenen Runden mit Kauf ab 15.10. (Kasse, `runden_lib`) plus offene Käufe ab 15.10., bewertet mit Menge × Tagesschluss − Mittelabfluss. Investitionsquote = Marktwert offener Käufe / Wert. Daraus ergeben sich Rückgang, Sharpe und mittlere Investitionsquote wie bei B und C. `A_kurve.csv`. Selbsttest rückwärts im E7-Fenster: An Tagen ohne offene Käufe gilt Wert = 500 + Kasse, und runden_lib ergibt E7 = −34,11 $.
2. **Für alle (A, B, C, M1–M3):** Sharpe, Kostenanteil am Brutto, mittlere Investitionsquote, Runden je Monat.
3. **Zahlenband für Kriterium 3** (`labor/papier/s7_band.py` → `s7_band.json`). Die Grundlage ist die Rückrechnung auf denselben 6 Coins mit denselben Papierkosten je Coin. Dafür werden alle 91-Tage-Fenster ab 2018 (Schritt 7 Tage) betrachtet. Das Band reicht vom 10. bis zum 90. Perzentil. Gruppe „über“ heißt: BTC liegt an mindestens 50 % der Wettkampftage über seiner 200-Tage-Linie.

   | Kandidat · Lage | Fenster | Investiert Ø (Band) | Runden/Monat (Band) | Rendite 91 T (Band) | besser als M3 |
   |---|---|---|---|---|---|
   | B K2 · über | 228 | 33,4–78,6 % | 2,0–6,4 | −13,9 bis +111 % | 53 % der Fenster |
   | B K2 · unter | 209 | 0–31,7 % | 0–3,0 | −10,3 bis +13,8 % | 34 % |
   | C K1 · über | 228 | 35,6–79,1 % | 2,0–7,4 | −13,2 bis +117 % | 55 % |
   | C K1 · unter | 209 | 9,2–44,7 % | 5,0–12,4 | −12,4 bis +23,8 % | 42 % |

   Kriterium 3 ist erfüllt, wenn **beide**, mittlere Investitionsquote und Runden je Monat, im Band der passenden Gruppe liegen.
4. **A = v6 in jeder Epoche ab Start** (zum Start läuft E11). Jede neue Epochengrenze steht im Wochenbericht. Der Grund: A soll „den heutigen Bot“ messen, auch wenn er weiterentwickelt wird. Bei einer Festlegung auf E11 würde A mit dem nächsten Patch enden. **Sven kann das bis zum ersten Wochenbericht am 19.10. auf „nur E11“ ändern.**
5. **M3 (BTC über 200-Tage-Linie)** wird für B und C immer mitgerechnet und berichtet (`zusatz_m3_*`). **Pflicht-Latte wird M3 erst, wenn Sven es bestätigt** (Entscheidungsvorlage 15.10.). Zur Einordnung: K2 schlug M3 in der Rückrechnung nur in 53 % der 91-Tage-Fenster. 3 Monate sagen dazu also wenig.
6. **Selbsttest** schreibt nur in einen Temp-Ordner. Bisher hat er die Live-CSV gelöscht (A10, LOW 3).
7. **Betrieb:** Die Aufgabe wiederholt sich bei einem Fehler 4 × alle 15 min und startet nach, wenn sie verpasst wurde. W5 meldet fehlgeschlagene TI-Aufgaben.

**Was gleich bleibt:** Hypothesen, Kriterien 1–2, Abbruchkriterien, Teilnehmer, Kosten, Simulator.

---

## Nachtrag 2 · Svens Entscheidungen E2 und E3 (15.10.2026)

Freigabe: Sven im Chat am 15.10.2026 („E2 ja, E3 jede“), siehe `entscheidungen.md`. Eingetragen am ersten Wettkampftag. Bis dahin lagen nur die Kaufkosten vor (B/C −0,05 %).

- **E2 · M3 ist Pflicht-Latte.** B oder C gilt nach mindestens 3 Monaten nur dann als besser, wenn alle drei Punkte erfüllt sind:
  1. Die Rendite nach Kosten ist höher als bei **A und bei M3**.
  2. Der größte Rückgang ist nicht größer als bei **A und bei M3**.
  3. Das Verhalten liegt im Band aus Nachtrag 1.
  Im Wochenbericht stehen die Vergleiche gegen A und gegen M3 auch einzeln.
- **E3 · A = jede Version von v6 ab dem Start.** Die Epochengrenzen stehen im Wochenbericht. Eine Änderung am Bot beendet den Vergleich also nicht.
- Unverändert bleiben Hypothesen, Abbruchkriterien und der Vorbehalt „kein statistischer Beweis nach 3 Monaten“. Zur Einordnung: K2 schlug M3 in der Rückrechnung in 53 % der 91-Tage-Fenster.

---

## Nachtrag 3 · Echte Ausführungskosten bei Bitvavo messen (15.10.2026)

Anlass: Laut Svens Entscheidung E1 gilt die Hauptarbeit der Trendregel. Bisher steht unter „Was hier NICHT gemessen wird“ die echte Ausführung bei Bitvavo. Das wird jetzt teilweise gemessen. **Kriterien und Simulator bleiben unverändert**, es ist nur eine zusätzliche Messung.

- Beim Tageslauf (bis 25.10. um 00:15 UTC, danach 01:15 UTC) liest `papier_tag.py` das öffentliche Bitvavo-Orderbuch der 6 USDC-Märkte (nur lesen).
- Je Coin wird festgehalten: die halbe Spanne und die Kosten der Tagesorder von B über das Buch gegen die Mitte, in bp je Seite ohne Gebühr. Gibt es an dem Tag keine Order, gilt ein Testbetrag von 100 $.
- Verglichen wird mit der Annahme im Simulator, also halbe Spanne aus der Messung vom 14.10.
- Datei: `labor/papier/ausfuehrung.csv`. Im Wochenbericht steht eine Zeile „Median Buchkosten / Annahme“.
- Gezählt werden nur Messungen bis 3 h nach der Eröffnung. Der Testlauf am 15.10. um 10:11 UTC steht in der Datei, zählt aber nicht.
- Prüfung nach 3 Monaten: Liegen die Buchkosten im Median über der Annahme, werden B und C mit den gemessenen Kosten nachgerechnet. Das wird im Bericht ausgewiesen, die Kriterien bleiben.
