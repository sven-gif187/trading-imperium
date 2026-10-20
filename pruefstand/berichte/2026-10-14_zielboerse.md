<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Entscheidungsvorlage · Zielbörse und Kostenlatte · 14.10.2026

**Summary:** Mit **Bitvavo, USDC-Märkte** (0,05 % je Seite) sinkt die Kostenlatte von 0,50 % auf **0,15 % je Runde**. Dieselben 136 v6-Runden wären damit **+42,66 $** statt −34,85 $ (berichtigt 14.10., Abschnitt 0). Das ist die günstigste geprüfte Börse, MiCA-zugelassen und für Deutschland freigegeben. **Aber:** Auch dort ist der Gewinn je Runde statistisch noch nicht belegt. Die billige Börse ist also nötig, reicht allein aber nicht.

Agent: kosten-analyst (A6) · Instanzen: v6 (136 Runden E7) und v7 · Alle Gebühren an der Primärquelle geprüft am 14.10.2026 · Rechnungen als Skripte in `pruefstand\skripte\`.

---

## 0 · Berichtigung 14.10.2026, 16:30 (nach Prüf-Agent A5)

Die Zahlen der ersten Fassung (Bitvavo +33,65 $, Bybit −43,85 $, brutto +0,29 % je Runde) waren um 9,02 $ zu schlecht. Bei den 21 Signal-Verkäufen steht im Journal der Betrag schon nach Abzug der Gebühr, und das Rundenskript zog sie ein zweites Mal ab. Alle Tabellen unten sind berichtigt: brutto **+75,51 $ / +0,332 % je Runde**, Bitvavo **+42,66 $**, OKX +29,52 $, Gate +19,45 $, Bybit −34,85 $. **An der Rangfolge und an der Empfehlung ändert das nichts.** Der Vorsprung vor Kosten bleibt im Block-Bootstrap unbelegt (−0,18 % bis +0,81 %). Bitvavo EUR (≈ −34,2 $), OKX ohne X-Perps (≈ −80 $) und Coinbase (≈ −187 $) sind nur um +9 $ verschoben, nicht neu gerechnet.

## 1 · Was du entscheiden sollst (in einem Satz)

**Mit welcher Börse sollen die Papier-Bots ab jetzt rechnen?** Davon hängt ab, wie viel jede Runde kostet, und daraus berechnen sich die Grenzen für Nullsicherung und Nachzieh-Stopp. Ein Konto brauchst du dafür heute noch nicht. Das kommt erst vor Echtgeld.

## 2 · Die Kandidaten auf einen Blick

| Börse | Gebühr je Seite | gemessener Schlupf je Seite (161 $) | **K je Runde** | 136 Runden netto | MiCA / DE | Bedingung |
|---|---|---|---|---|---|---|
| **Bitvavo, USDC-Märkte** | 0,05 % | 0,016–0,038 % (Ø 0,025) | **0,150 %** | **+42,66 $** | AFM (NL), DE ja | keine |
| OKX EEA mit X-Perps | 0,10 % (Maker 0,08) | 0,000–0,010 % | 0,210 % | +29,52 $ | MFSA (MT), DE ja | Derivate-Konto mit Eignungstest |
| Gate EU | 0,10 % | 0,003–0,077 % | 0,256 % | +19,45 $ | MFSA (MT), DE ja | SOL-Buch dünn (Spanne 0,14 %) |
| Bybit EU (heute) | 0,25 % | 0,000–0,005 % | 0,504 % | −34,85 $ | FMA (AT), DE ja | – |
| Bitvavo, EUR-Märkte | 0,25 % | 0,000–0,001 % | 0,501 % | −43,19 $ | wie oben | EUR statt USDC |
| OKX EEA ohne X-Perps | 0,35 % | ≈ 0,005 % | 0,710 % | −88,95 $ | wie oben | – |
| Kraken Pro (Stufe 3) | 0,38 % | ≈ 0,011 % | 0,781 % | −95,51 $ | CBI (IE), DE ja | ab 10.000 $/Monat, darunter 0,80 % |
| Coinbase Advanced | ≈ 0,60 % (ungeprüft) | – | ≈ 1,2 % | ≈ −196 $ | CSSF (LU), DE ja | Sätze nur nach Anmeldung |
| Binance | – | – | – | – | **nicht im ESMA-Register** | nur Kursquelle |

**K** ist die Kostenlatte je Runde: Gebühr beim Kauf und beim Verkauf plus zweimal der Schlupf. Den Schlupf habe ich am 14.10. um 15:35 Uhr aus den öffentlichen Orderbüchern gemessen, 3 Proben je Münze, Marktkauf über 161 $. Die Gegenprobe für Bybit ergibt 0,504 %. Das deckt sich mit eurer K-BASIS von 0,505 %, die Messmethode stimmt also.

**136 Runden netto** ist die Kassenrechnung derselben Käufe und Verkäufe, nur mit anderer Gebühr und anderem Schlupf. Grundlage ist v6, Verkäufe vom 13.08. 13:21 UTC bis 14.10.

## 3 · Warum Bitvavo USDC vorne liegt, und was dagegen spricht

**Dafür** [SICHER 95 %, außer wo anders angegeben]:
- **Niedrigste Gebühr der Liste.** Die Kategorie B „All crypto trading pairs on USDC markets“ kostet 0,05 % Maker und 0,05 % Taker ab 0 € Umsatz (bitvavo.com/en/fees).
- **Seit langem so.** USDC-Paare mit „0,05 % oder weniger“ gibt es seit Juli 2024, das ist keine kurzfristige Aktion.
- **Die Märkte des Bots sind da.** BTC/USDC, ETH/USDC und SOL/USDC existieren, die Mindestorder liegt bei 5 USDC.
- **Kurs passt zur Kursquelle.** Bitvavo liegt im Median weniger als 0,005 % neben Binance, auf dessen Kursen der Bot entscheidet. Gemessen mit 5 Proben je Münze.
- **Zulassung geklärt.** MiCA über die niederländische AFM seit 26.06.2025, mit Passporting nach Deutschland (ESMA-Register, Stand 07.10.2026).
- **Keine Sonderbedingung.** Kein Derivate-Konto und kein Mindestvolumen nötig.

**Dagegen:**
- **Breitere Spanne als OKX und Bybit.** Die USDC-Bücher sind dünner: Spanne 0,03 % bei BTC, 0,04–0,05 % bei ETH, 0,05–0,09 % bei SOL. Der Gebührenvorteil schrumpft dadurch von 0,40 auf 0,35 Prozentpunkte je Runde gegenüber Bybit. Die Messung ist eine Momentaufnahme an einem Nachmittag [WAHRSCHEINLICH 70 %, dass es tagsüber so bleibt]. Nachts und bei Kurssprüngen kann es breiter werden.
- **Kein Maker-Vorteil.** Bei Bitvavo kosten Warteaufträge (v7) ebenfalls 0,05 %. Sie sparen nur die halbe Spanne und tragen das Risiko, nicht gefüllt zu werden.
- **Der Satz kann sich ändern.** Bybit hat am 05.10. ohne Vorwarnung umgestellt. Der Kosten-Wächter W3 soll die Gebührenseite deshalb wöchentlich prüfen.
- **USDC-Beschaffung.** Für Echtgeld müsste USDC erst gegen EUR gekauft werden, einmalig für 0,10 % (Kategorie C). SEPA-Einzahlung ist kostenlos.

## 4 · Was die billigere Börse NICHT beweist (Statistik, Aufgabe von A3)

| | je Runde | 95-%-Bereich (Block-Bootstrap nach 39 Kalendertagen) | belegt über null? |
|---|---|---|---|
| vor Kosten (brutto) | +0,332 % | −0,18 % bis +0,81 % | **nein** |
| Bitvavo USDC inkl. Schlupf | +0,181 % | −0,33 % bis +0,66 % | **nein** |
| OKX mit X-Perps inkl. Schlupf | +0,121 % | −0,39 % bis +0,60 % | nein |
| Bybit EU heute | −0,173 % | −0,68 % bis +0,30 % | nein (auch nicht sicher negativ) |

**Klartext:** Bei Bybit verliert der Bot mit hoher Wahrscheinlichkeit Geld, weil die Kosten fast doppelt so groß sind wie der beobachtete Vorsprung. Bei Bitvavo **könnte** er verdienen, belegt ist das nicht. 136 Runden an 39 Tagen reichen dafür nicht, die Tage schwanken zu stark. Für einen Beleg bei +0,14 % je Runde braucht es grob 600 Runden, also bei heutigem Tempo etwa 9 Monate (Tabelle 3.8). Mit zwei Bots parallel geht es schneller.

**Der richtige Schluss:** Erst die Kosten senken, sonst kann kein Vorsprung je sichtbar werden. Daneben den Vorsprung selbst prüfen, also den Einstieg gegen Zufallskäufe (A4).
**Der plausible, aber falsche Schluss:** „Bitvavo, und der Bot ist profitabel.“

## 5 · Drei Wege (Abwägung)

| Weg | Was | Für | Gegen | Urteil |
|---|---|---|---|---|
| **A** | Kostenlatte **Bitvavo USDC** (K 0,15 %) | größter Hebel, keine Sonderbedingung, MiCA geklärt | dünnere Bücher, Satz kann sich ändern | **empfohlen** [WAHRSCHEINLICH 75 %] |
| B | Kostenlatte **OKX EEA mit X-Perps** (K 0,21 %) | tiefste Bücher, auch für größere Beträge robust | Derivate-Konto mit Eignungstest, obwohl der Bot nur Spot handelt. Ohne dieses Konto 0,70 % | Ersatz, falls Bitvavo wegfällt |
| C | **Bybit bleibt**, Strategie ändern (länger halten, weniger Runden) | kein Börsenwechsel | Der Bot bräuchte +0,5 % Vorsprung je Runde, heute sind es 0,29 %. Das dauert Monate und ist ungewiss | nur zusätzlich, nicht statt A |

## 6 · Was ein Wechsel auf Bitvavo in den Bots bedeutet

Das ist eine Verhaltensänderung, sie braucht also je Bot eine Epoche (v6 E10, v7 L9). Eine Ursache, eine Grenze:

| Stelle | heute (Bybit) | Bitvavo USDC |
|---|---|---|
| Papier-Gebühr je Seite | 0,25 % | 0,05 % (Maker und Taker) |
| K_BASIS | 0,505 % | 0,150 % |
| Nullsicherung-Puffer (K + 0,045) | 0,55 % | **0,195 %** |
| Nachzieh-Start ((1+K)/(1−1 %) − 1 + 0,05) | 1,57 % | **1,21 %** |

**Wichtig zu E8:** Die heute eingespielten Werte 0,55 / 1,57 sind **aus der Bybit-Latte gerechnet**. Mit Bitvavo fallen sie wieder, nach derselben Formel. Das ist kein Rückschritt, sondern dieselbe Regel mit neuer Zahl. Gegen Bitvavo-Kosten wären die alten v6-Werte 0,35 / 1,2 übrigens zufällig fast richtig gewesen.

Dazu kommt die `CLAUDE.md` von v6 (Abschnitt 8: „Zielbörse Bybit EU, K-BASIS 0,505“). Das ist deine Regeldatei, sie wird nur mit deiner Zustimmung geändert.

## 7 · Gegenprüfung (Advocatus Diaboli, A10)

**Position A, Bitvavo ist richtig:**
1. K 0,150 % gegen 0,504 %, also 0,35 Punkte weniger je Runde. Bei 68 Runden im Monat sind das ≈ 38 $ im Monat bei 161 $ Einsatz.
2. Das Ergebnis vor Kosten ändert sich nicht, nur die Kosten. Das ist die einzige Stellschraube, die sicher wirkt.
3. MiCA, Passporting, Märkte, Mindestorder und Kursabstand sind geprüft. Keine Bedingung, die den Bot zu Derivaten zwingt.

**Position B, Bitvavo ist falsch:**
1. Der Schlupf wurde nur an einem Nachmittag gemessen. Ist die Spanne nachts dreimal so breit, steigt K auf etwa 0,25 % und liegt damit gleichauf mit OKX.
2. Wechselt Bitvavo wie Bybit den Tarif, war der Umbau umsonst.
3. Der Vorsprung vor Kosten ist nicht belegt (95-%-Bereich −0,20 % bis +0,75 %). Ist er in Wahrheit null, verliert der Bot auch bei Bitvavo, nur langsamer.

**Urteil: TRÄGT**, mit zwei Auflagen:
- Der Kosten-Wächter W3 misst die Bitvavo-Spanne rund um die Uhr, und die Gebührenseite wird wöchentlich geprüft.
- Parallel läuft der Zufallsvergleich der Einstiege (A4). Er entscheidet, ob es überhaupt einen Vorsprung gibt.

## 8 · Was ich NICHT weiß

- Wie sich die Bitvavo-Spanne über 24 h und bei Kurssprüngen verhält (eine Messung um 15:35 Uhr).
- Ob Bitvavo den USDC-Satz behält.
- Die gebührenfreien Paare bei OKX: Die Liste ist ohne Anmeldung nicht sichtbar.
- Die Coinbase-Sätze, die ebenfalls nur nach Anmeldung sichtbar sind.
- **Was die Empfehlung kippen würde:** Eine nächtliche Spanne bei Bitvavo SOL über 0,2 %. Dann wäre OKX mit X-Perps gleichauf, und die Bedingung „Derivate-Konto“ würde zur echten Abwägung.

## 9 · Sven entscheidet

- [ ] **Zielbörse und Kostenlatte für die Papier-Bots:** (A) Bitvavo USDC · (B) OKX EEA mit X-Perps · (C) Bybit EU bleibt
- [ ] Bei A oder B: **beide Bots jetzt umstellen** (neue Epochen v6 E10 / v7 L9), und die `CLAUDE.md` von v6, Abschnitt 8, wird angepasst

**Nächster Schritt nach deiner Wahl:** Patch „Kostenlatte“ für v6 und v7, mit Vorab-Registrierung, Selbsttest und Epoche, so wie heute bei E8/E9/L8. Parallel baue ich den Kosten-Wächter W3, der die Spanne der gewählten Börse dauerhaft misst.

## Quellen (abgerufen 14.10.2026)

- Bybit EU: https://www.bybit.eu/en-EU/help-center/article/Trading-Fee-Structure (Last updated 2026-10-05 13:01:39)
- Bitvavo: https://bitvavo.com/en/fees, https://bitvavo.com/en/news/usdc-pairs
- OKX EEA: https://www.okx.com/en-eu/help/what-are-the-new-trading-fees-for-eea-users (Updated Sep 3, 2026)
- Gate EU: https://www.gate.com/en-eu/fee
- Kraken: https://www.kraken.com/features/fee-schedule
- Coinbase: https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees (ohne Zahlen)
- ESMA MiCA-Register: https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv (Stand 07.10.2026)
- Messungen: `berichte\2026-10-14_orderbuch.json`, `berichte\2026-10-14_kostenlatte.json`, `berichte\2026-10-14_kosten_schatten_v6.json`, `berichte\2026-10-14_kosten_schatten_v6_mit_schlupf.json`

Selbstbewertung: Präzision 9 · Vollständigkeit 8 (Schlupf nur als Momentaufnahme) · Umsetzbarkeit 9.
