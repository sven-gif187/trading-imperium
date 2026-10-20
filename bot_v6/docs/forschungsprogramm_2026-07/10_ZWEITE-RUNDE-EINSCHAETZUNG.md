# Zweite Runde — Einschätzung und Vorschlag (keine Entscheidung)

Stand 30.07.2026, nach negativem Gate 1. Regel 13: ein zweites negatives
Gate beendet das Programm endgültig. Die zweite Runde ist damit **die
letzte** — sie sollte auf die beste verfügbare Frage verwendet werden,
nicht auf den Rest aus dem alten Budget.

## 1. Was das Programm gebracht hat — auch mit negativem Gate

### Harte operative Fakten, die eine Fehlinvestition verhindert haben

1. **USDT ist als EU-Handels-Quote tot.** Per API verifiziert: Bybit EU
   führt 111 USDC-, 18 EUR-, **0 USDT**-Spot-Paare. Eine Migration nach
   der ursprünglichen Arbeitshypothese wäre gegen eine Wand gelaufen.
2. **Die Kostenhürde ist 2,5-mal höher als angenommen.** Bybit EU Taker
   0,25 % statt 0,10 % → 0,60 % je Runde statt 0,30 % → nötige
   Trefferquote bei ±5 % steigt von 53,0 % auf 56,0 %. Ohne die Korrektur
   hätten wir gegen eine zu niedrige Latte gemessen.
3. **`ccxt.bybit().fees` ist falsch** (maker 0,01 % / taker 0,075 %). Ein
   naiv gebauter Adapter hätte die Kostenbasis um Faktor 3 zu günstig
   angesetzt.
4. **Der Limit-Order-Pfad muss nicht gebaut werden.** K-MAKER gegen
   K-BASIS macht bei niederfrequenten Regeln 1,3–1,8 % des Effekts aus.
   Ein mehrtägiges Engineering-Projekt ist damit belegbar überflüssig —
   nicht vertagt, sondern erledigt.

### Erkenntnisse über den Markt, die vorher Vermutung waren

5. **Krypto-Trendfolge hat 2017–2021 funktioniert und tut es
   2022–2023 nicht mehr.** Gemessen, nicht behauptet: Donchian 20/10,
   netto EV je Runde nach Segment — BTC +18,99 / +50,69 / **+0,50 %**,
   ETH +4,85 / +65,15 / **+0,16 %**. Das ist das Zerfallsmuster einer
   arbitrierten Anomalie, und es betrifft die meistpublizierte
   Krypto-Strategiefamilie überhaupt.
6. **Trendfolge ist in Krypto ein Risiko-, kein Ertragswerkzeug.** Über
   den Gesamtzeitraum schlägt Donchian das Halten deutlich (BTC Calmar
   1,08 gegen 0,52, MaxDD 55,1 % gegen 83,2 %) — aber **im Bullenmarkt
   S-B verliert sie** (BTC +533 % gegen +542 %, ETH +1914 % gegen
   +2711 %). Der gesamte Vorsprung entsteht aus geringeren Verlusten in
   Abwärts- und Seitwärtsphasen. Wer Trendfolge für ein Alpha-Signal
   hält, verwechselt Drawdown-Vermeidung mit Prognose.
7. **Funding-Extreme selektieren Volatilität, nicht Richtung.** T-025
   liefert +2,95 % netto über 7 Tage mit KI > 0 — und wird vom
   volatilitäts-gematchten Placebo (+5,57 %) geschlagen. **Das ist
   exakt dieselbe Pathologie wie beim alten F&G-Einstieg** (E2: „der
   Einstieg selektiert Volatilität, keine Richtung"). Zwei unabhängige
   Signalquellen, dieselbe Fehlerart — das ist ein Befund über das
   Projekt, nicht über ein Signal.
8. **Makro-Overlays kaufen nichts.** Der Dollar-Overlay senkt MaxDD
   46,9 % → 34,4 %, aber CAGR 85,0 % → 63,6 %; Calmar-Differenz +0,036
   mit KI [−1,476; +0,802], EV −4,48 bp/Tag signifikant negativ. Risiko
   und Ertrag fallen proportional.
9. **Survivorship ist erstmals beziffert.** Segment S-C: 10
   survivorship-selektierte Alts +9,780 % je Runde gegen BTC/ETH
   +0,331 % — **Faktor 30**. Jeder Krypto-Backtest auf „den heutigen
   Top-Coins" trägt einen Fehler dieser Größenordnung. Das ist die
   wertvollste einzelne Zahl des Programms.

### Bleibende Infrastruktur

10. **Datenfundament von 2 auf 9 Jahre erweitert**, kostenlos und
    prüfsummengesichert: 12 Coins Tageskerzen ab Listing (BTC 3270 Tage
    ab 2017-08), 4h für BTC/ETH, 7 Jahre 8h-Funding (BTC ab 2019-09,
    lückenlos im 8h-Raster), FRED-Makro. Das bleibt unabhängig vom
    Programmausgang nutzbar.
11. **Ein funktionierender Validierungs-Harness:** Placebo mit
    kalibrierter Blocklänge, Block-Bootstrap, BH-FDR, Segmentkriterium,
    Kostenszenarien, Trial-Register. Der Placebo-Test war der
    entscheidende Filter — R1 und R2 hatten positive EVs und wären ohne
    ihn durchgerutscht.

### Was das Programm gekostet hat

Ein Arbeitstag, 0 Euro Datenkosten, kein Live-Kapital, keine Änderung am
laufenden Bot. Dagegen steht ein verhinderter Live-Gang auf Basis eines
Backtests, dessen Vorteil im jüngsten Segment nicht mehr existiert.

## 2. Lohnt sich eine zweite Runde mit H3?

**Meine Empfehlung: nicht in dieser Form — und die Entscheidung über eine
zweite Runde überhaupt gehört gemeinsam getroffen, nicht automatisch.**

### Gegen H3 als Inhalt der letzten Runde

- **Befund 9 beschädigt H3 vorweg.** Cross-Sectional Momentum rankt Coins
  gegeneinander. Genau diese Konstruktion hat den T-024-Wert erzeugt, der
  sich als Survivorship herausgestellt hat. H3 auf einem nicht perfekt
  punkt-in-der-Zeit rekonstruierten Universum misst die Auswahl, nicht
  die Regel.
- **Die Vorbedingung ist wahrscheinlich unerreichbar.** N_eff wurde mit
  1,23–1,42 für 11 Coins gemessen, Paarkorrelation 0,72–0,75 und in
  Abwärtsphasen steigend. Krypto ist empirisch ein Ein-Faktor-Markt; dass
  30–60 Coins N_eff ≥ 5 erreichen, halte ich für unwahrscheinlich
  [VERMUTUNG, nicht gemessen].
- **Ein sauberes Universum zu bauen ist die eigentliche Arbeit.**
  Punkt-in-der-Zeit-Rekonstruktion mit Delistings, Liquiditätsfiltern und
  korrekten Listing-Daten ist mehrere Tage Arbeit mit hohem Fehlerrisiko —
  und ein Fehler darin macht das Ergebnis wertlos, ohne dass man es sieht.

### Der ehrlichere Rahmen, falls du weitermachen willst

Nicht „H3 mit 30 Coins", sondern zuerst eine **billige Vorprüfung ohne
Trial-Verbrauch**, weil sie keine Handelsregel gegen Marktdaten
auswertet:

> **N_eff-Vorprüfung:** Universum von ~40 Coins inklusive delisteter
> Namen aus dem Vision-Archiv aufbauen, N_eff auf Tagesrenditen
> 2020–2023 messen. Kosten: wenige Stunden, 0 Euro, kein Trial.
> Ergebnis N_eff < 5 → H3 ist beantwortet, ohne das letzte Gate zu
> verbrennen. Ergebnis N_eff ≥ 5 → die zweite Runde hat eine
> tragfähige Grundlage.

Das ist der einzige Vorschlag, den ich guten Gewissens mache: eine
Messung, die die Frage entweder billig erledigt oder die Runde
rechtfertigt.

### Der Fall für Aufhören

Er ist stärker, als er sich anfühlt. Das Programm hat sein Ziel erfüllt —
es sollte eine belastbare Antwort liefern, und es hat eine geliefert:
**Auf den geprüften Skalen, mit den verfügbaren Mitteln und unter realen
Kosten trägt keine der vorregistrierten Regeln.** Das ist kein
Zwischenstand, sondern ein Resultat. Eine zweite Runde, die die
schwächste der vier Hypothesen auf dem fehleranfälligsten Datenkonstrukt
prüft, hat eine hohe Wahrscheinlichkeit, das zweite negative Gate zu
liefern — und dann endet es ohnehin, nur mit mehr verbrauchter Zeit.

Bei 500 € Kapital ist der Unterschied zwischen „wir wissen es nicht" und
„wir wissen, dass es nicht geht" ohnehin größer als der Unterschied
zwischen beiden und einem funktionierenden Bot.

## 3. Was ich nicht entscheide

Ob die zweite Runde stattfindet, was sie enthält, und ob die
N_eff-Vorprüfung überhaupt gemacht wird. Regel 13 macht das zu einer
gemeinsamen Entscheidung, und die Datenlage gibt keine eindeutige
Antwort — sie gibt nur eine ungünstige Vorabwahrscheinlichkeit.
