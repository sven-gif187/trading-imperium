# EXPERIMENT-REGISTER v2.0 — Runde 2: Marktstruktur

**Version 2.0 — 30.07.2026 — Status: FREIGEGEBEN UND EINGEFROREN**
(Freigabe des Eigentümers vom 30.07.2026, **ohne H8**).
Trial-Zähler bei Freigabe: **T-030**.

## VERBINDLICHE LESART DIESER RUNDE (wörtlich, nicht umformulierbar)

> **Runde 2 testet KEINE neue Richtung, sondern die Teilfrage, ob
> Volatilitätskontraktion die Selektivität liefert, die Donchian fehlte.**

Dieser Satz ist auf Anweisung des Eigentümers wörtlich aufgenommen, damit
Runde 2 später **nicht** als unabhängiger Test gelesen werden kann. Wer
ein Ergebnis dieser Runde zitiert, zitiert diesen Satz mit.

## VORABSCHÄTZUNG — im Register, nicht nur im Bericht

**P(H5 übersteht den vollen Standard) = 10 %.** Zum Vergleich: für H1
lag die Vorabschätzung bei 25–35 %, und Gate 1 wurde negativ. Die
Schätzung steht hier, damit ein positives Ergebnis nachträglich nicht
als „erwartet" und ein negatives nicht als „Pech" umgedeutet werden kann.

**Bei Regel 13 ist Runde 2 der letzte Anlauf. Der wahrscheinlichste
Ausgang dieser Runde ist das Programmende.**

Übernimmt aus v1.0/v1.1/v1.2 **unverändert**: Regel 14
(Kontaminationsregel), Klausel A (Segment-Kriterium, Lesart L2), Klausel B
(sekundäre Trials tragen kein Gate allein), Kostenszenarien K-MAKER 0,26 %
/ K-BASIS 0,60 % / K-KONSERVATIV 0,75 %, Placebo-Design, Block-Bootstrap,
BH-FDR, Regel 13 (Runde 2 ist der letzte Anlauf).

---

## 0. Widerspruch zur Auftragsprämisse — bitte vor der Freigabe lesen

Der Auftrag nennt Marktstruktur „die einzige Richtung, die Gate 1 nicht
berührt hat". **Das ist nicht haltbar.**

`R3 Donchian 20/10` (T-020/T-021/T-024) ist ein **reiner
Preisstruktur-Ausbruch ohne jeden Indikator**: Einstieg beim 20-Tage-Hoch,
Ausstieg beim 10-Tage-Tief. Genau das ist klassische Marktstruktur. Diese
Regel war der stärkste Kandidat der gesamten Runde 1 — und sie ist an
Klausel A gescheitert, weil ihr Effekt 2022–2023 auf +0,50 % (BTC) bzw.
+0,16 % (ETH) je Runde zusammengefallen ist.

H5, H6 und H7 sind **Varianten derselben Grundannahme**: Preis setzt eine
Bewegung nach einem strukturellen Ereignis fort. Der Donchian-Befund ist
direkte Evidenz gegen diese Familie, nicht Neuland daneben.

**Ehrliche Formulierung von Runde 2:** Wir testen nicht eine unberührte
Richtung, sondern die eine verbleibende Teilfrage — *ob ein
selektiverer Ausbruchsfilter dort trägt, wo der grobe versagt hat.*
Donchian feuert auf **jedes** 20-Tage-Hoch. Die einzige inhaltlich neue
Frage ist, ob eine Vorbedingung (Volatilitätskontraktion) die Selektivität
liefert, die Donchian fehlt. Alles andere in H5–H8 ist Umbenennung.

Wer das anders sieht, sollte v2.0 nicht freigeben, sondern das Programm
nach Regel 13 mit dem negativen Gate 1 beenden.

## 1. Prüfung der vorgeschlagenen Hypothesen gegen Regel 14

Regel 14 verlangt: **Regel und Parameter** aus einer vor 2015 auf anderen
Anlageklassen publizierten Quelle. Streng gelesen heißt das: die Quelle
muss die Zahlen nennen. Ergebnis der Prüfung:

| | Quelle | vor 2015? | Nicht-Krypto? | Parameter in der Quelle? | Mechanisch ohne Ermessen? | Urteil |
|---|---|---|---|---|---|---|
| **H5** Crabel NR7 | Crabel 1990, *Day Trading with Short Term Price Patterns and Opening Range Breakout* (Futures) | ja | ja | **ja — NR7 nennt die 7** | ja | **AUFGENOMMEN** |
| **H6** Dow/Rhea | Rhea 1932, *The Dow Theory* (Aktienindizes) | ja | ja | **nein** — Rhea nennt keine Swing-Weite | nur mit selbst gewählter Fraktal-Weite | **GESTRICHEN** |
| **H7** Darvas-Kasten | Darvas 1960, *How I Made $2,000,000…* (Aktien) | ja | ja | **nein** — Kastengrenzen ergaben sich aus Darvas' Urteil über das Verhalten der Aktie | nein, drei frei zu wählende Parameter | **GESTRICHEN** |
| **H8** MTF-Konfluenz | — | — | — | — | ja, wenn auf H5 aufgesetzt | **AUFGENOMMEN, nur bedingt** |

**Begründung der Streichungen** (nach der Auftragsvorgabe „wo Ermessen
nötig wäre: Hypothese streichen, nicht zurechtbiegen"):

- **H6:** Rhea beschreibt höhere Hochs und höhere Tiefs qualitativ. Ein
  mechanischer Test braucht eine Fraktal-Weite (3? 5? 10 Balken?), die
  Rhea nicht liefert. Jede Wahl wäre unsere, nicht die der Quelle — und
  damit genau die Hintertür, die Regel 14 schließen soll. Hinzu kommt:
  Dow Theory verlangt Bestätigung zwischen **zwei** Indizes (Industrials
  und Rails). Dieser Kern ist auf ein einzelnes Kryptoasset nicht
  übertragbar; was bliebe, wäre ein Rumpf, der Donchian sehr nahe kommt.
- **H7:** Darvas' Kasten entstand aus seiner Beurteilung, wann eine Aktie
  sich „weigerte" zu fallen. Eine mechanische Fassung braucht mindestens
  drei frei gewählte Zahlen (Neuhoch-Rückblick, Bestätigungstage,
  Ausbruchsschwelle). Das ist die größte Overfitting-Fläche der ganzen
  Familie bei der schwächsten Quellenbindung.

Elliott-Wellen und Orderblöcke sind auftragsgemäß **nicht** aufgenommen.

## 2. Hypothesen von Runde 2

### H5 — Volatilitätskontraktion und Ausbruch (primär)

**Hypothese:** Ein Ausbruch aus einer Volatilitätskontraktion trägt netto
EV > 0 je Runde, wo ein unbedingter Ausbruch (Donchian, widerlegt) es
nicht tut.

**Ökonomische Begründung:** Volatilitäts-Clustering (Engle 1982, ARCH,
Makro-/Finanzzeitreihen — vor 2015, Nicht-Krypto). Kontraktion und
Expansion wechseln sich ab; die Regel prognostiziert **nicht die
Richtung**, sondern positioniert sich zur Expansion. Das ist die einzige
Begründung, die nach dem F&G- und Funding-Befund („selektiert
Volatilität, nicht Richtung") noch zulässig ist — dort war
Volatilitätsselektion der *Fehler*, hier ist sie die *erklärte Absicht*,
und die Richtung kommt aus dem Ausbruchsvorzeichen, nicht aus einer
Prognose.

**Regel (mechanisch, keine Ermessensstelle):**
- **NR7-Signalbalken:** Tagesbalken, dessen Spanne (High − Low) die
  kleinste der letzten 7 Balken ist (inklusive sich selbst). Quelle:
  Crabel 1990.
- **Einstieg:** Am Folgetag long, wenn der Schlusskurs über dem **High
  des NR7-Balkens** liegt. Ausführung zum nächsten Tages-Open
  (Look-ahead-Sperre wie Runde 1).
- **Ausstieg (flat):** Wenn der Schlusskurs unter dem **Low des jeweils
  jüngsten NR7-Balkens** liegt. Symmetrisch zum Einstieg, **kein neuer
  Parameter, keine zweite Quelle**.
- Long/Flat, Spot, keine Shorts.

**Parameterraum: ausschließlich {7}.** Keine weiteren Werte. Eine
±20-%-Perturbation (5/9) ist **ausschließlich** nachgelagerter
Robustheitsbericht und darf niemals zur Auswahl dienen.

**Assets:** primär BTCUSDT, ETHUSDT. Sekundär 12er-Portfolio — trägt nach
Klausel B kein Gate allein und dient nur der Robustheitsaussage.

### H8 — GESTRICHEN durch Freigabeentscheidung vom 30.07.2026

H8 (Wochenfilter als Overlay) war im Entwurf als bedingte, sekundäre
Hypothese vorgesehen und ist vom Eigentümer **gestrichen** worden. Zwei
Gründe, beide übernommen:

1. **Regel-14-Verstoß:** Das 4-Wochen-Fenster steht in keiner Quelle. Es
   war die schwächste Quellenbindung des Entwurfs und im Entwurf auch so
   markiert.
2. **H4-Präzedenz:** Overlays kürzen Risiko und Ertrag proportional
   (T-030: Calmar-Differenz +0,036, KI [−1,476; +0,802] enthält 0;
   EV −4,48 bp/Tag signifikant negativ).

**Runde 2 enthält damit genau eine Hypothese: H5.** Ein Overlay darf in
dieser Runde nicht nachträglich eingeführt werden; das wäre v2.x mit
neuer Freigabe.

## 2b. Bindende Konvention: Funding-Regeln in Kalenderzeit

Aus dem Datenbank-Befund vom 30.07.2026 (SOLUSDT: 101 Nicht-8h-Abstände,
98 × 2 h — die anderen 11 Coins sauber im 8h-Raster):

> **Jede künftige Funding-Regel wird in KALENDERZEIT definiert, nicht in
> Intervallen.**

„3 aufeinanderfolgende 8h-Intervalle" wäre auf SOL ein 6-Stunden- statt
24-Stunden-Fenster gewesen. Die Runde-1-Trials T-025…T-028 liefen
ausschließlich auf BTC/ETH und sind **nicht betroffen**; sie bleiben
gültig. Die Konvention gilt ab sofort für alle künftigen Runden.

## 3. Haltedauer-Kalibrierung (B2)

Die externe Referenz „23–46 Handelstage bei rund 65 % Trefferquote" ist
**[VERMUTUNG]**, nicht verifizierbar, und ich halte sie für in sich
fragwürdig: klassische Ausbruchs-/Chartsysteme in der Tradition, auf die
sich Runde 2 beruft, arbeiten typischerweise mit **Trefferquoten um
35–45 % bei R/R deutlich über 2**, nicht mit 65 %. Eine Quote von 65 %
impliziert frühes Gewinnmitnehmen und damit R/R < 1 — ein anderes System
als das hier registrierte.

**Konsequenz, verbindlich:** Die Referenz wird **nicht** zur Kalibrierung
verwendet. Es wird **nichts** auf 23–46 Tage oder 65 % hin eingestellt.
Stattdessen sind folgende Größen **Pflichtbestandteil jedes Berichts**:

- Verteilung der Haltedauer (Median, 25./75. Perzentil, Min/Max)
- MFE und MAE je Runde
- realisiertes R/R je Runde und dessen Verteilung
- Trefferquote **und** Payoff getrennt

**Befundpflicht:** Hält H5 systematisch deutlich kürzer als 23 Handelstage,
ist das als Befund auszuweisen — mit der Konsequenz, dass die Regel
kostenempfindlicher wird (mehr Runden je Jahr) und der K-MAKER/K-BASIS-
Abstand wieder relevant werden kann. In Runde 1 war er es nicht
(1,3–1,8 % des Effekts bei 4,5 Runden/Jahr).

**Methodische Anmerkung zu den Barrieren:** Symmetrische Schranken
(±5/7/10 %) messen P(auf) bei R/R = 1. Das ist genau der Rahmen, den
klassische Chartanalyse ablehnt. Da CONFIRMED nach Klausel A ohnehin
**EV-basiert** entschieden wird, dienen die Barrieren nur der
Break-even-Einordnung (p = 0,5 + c/(2B)); die R/R-Verteilung oben ist die
inhaltlich passende Kennzahl. Keine zusätzlichen Trials.

## 4. Testdesign (unverändert zu Runde 1, keine Abschwächung)

- Entwicklung **2017-08-17 … 2023-12-31**. 2024–2026 bleibt gesperrt.
  Beweis nur Forward.
- Kostenszenarien K-MAKER / K-BASIS / K-KONSERVATIV, alle drei berichtet.
- **CONFIRMED nur, wenn Netto-EV je Runde in JEDEM Segment (S-A/S-B/S-C)
  K-BASIS = 0,60 % überschreitet** (Klausel A, Lesart L2).
- **Sekundäre Trials tragen ein Gate nicht allein** (Klausel B).
- Placebo: Markov-Masken mit kalibrierter Long-Quote und Blocklänge,
  200 Ziehungen, **Seed 20260730**. Echter EV muss über dem
  95. Perzentil liegen.
- Block-Bootstrap über Runden (= zusammenhängende Kalendertagblöcke),
  2000 Ziehungen, Seed 20260730.
- BH-FDR über **alle** Trials von Runde 2, q = 0,10.
- Lag+1-Kontrolle als Look-ahead-Detektor.
- MaxDD der Regel < MaxDD BTC-Halten (Regel 12).
- **n < 12 Runden ⇒ INCONCLUSIVE**, nie CONFIRMED.

### Survivorship — VOR dem ersten Lauf festgelegt (B3)

Der T-024-Befund (Faktor 30) zwingt zu einer Vorabfestlegung:

1. **Primärtrials laufen ausschließlich auf BTC und ETH.** Beide sind
   seit 2017-08 durchgehend gelistet; Survivorship ist dort minimal.
2. **Das 12er-Portfolio ist survivorship-belastet und bleibt sekundär.**
   Es wird berichtet, kann aber nach Klausel B kein Gate tragen.
3. **Es wird KEIN erweitertes Universum aufgebaut.** Ein
   punkt-in-der-Zeit-korrektes Universum mit Delisting-Behandlung ist
   mehrere Tage Arbeit mit hohem, unsichtbarem Fehlerrisiko. Ohne dieses
   Universum ist jede Aussage über 30+ Coins wertlos — also wird sie
   nicht getroffen.
4. Für jede Portfolio-Zeile ist die Zerlegung **BTC/ETH gegen Alts**
   verpflichtend auszuweisen, wie in `08_NEUBEWERTUNG-v1.2.md` §3.2.

## 5. Trial-Budget: 5 (B4, nach Streichung von H8)

| Trial | Inhalt | Rolle |
|---|---|---|
| T-031 | H5 NR7-Ausbruch, BTCUSDT | primär |
| T-032 | H5 NR7-Ausbruch, ETHUSDT | primär |
| T-033 | H5 NR7-Ausbruch, 12er-Portfolio | sekundär (Klausel B) |
| T-034 | Reserve | nur mit schriftlicher Freigabe |
| T-035 | Reserve | nur mit schriftlicher Freigabe |

Geplant sind **drei** Trials. Nur T-031 und T-032 können Gate 2 tragen;
T-033 ist nach Klausel B ausdrücklich nicht gate-tragend. Die beiden
Reserven sind **nicht** für Parametervarianten von H5 gedacht.

**Begründung der Zahl 5 statt 15:** Runde 1 verbrauchte 14 Trials für vier
Hypothesen und lieferte 7 INCONCLUSIVE — die Hälfte des Budgets ging an
Trials ohne Aussagekraft (n < 12 Runden bzw. n < 30 Events). Ein größeres
Budget hätte daran nichts geändert; es hätte nur die FDR-Schwelle
verschärft und damit echte Effekte schwerer nachweisbar gemacht. Sechs
Trials, davon vier tatsächlich geplant, konzentrieren die verbleibende
statistische Kraft auf die **eine** Frage aus §0. Die zwei Reserven sind
ausdrücklich **nicht** für Parametervarianten von H5 gedacht — jede
Erweiterung erfordert v2.x mit Freigabe.

## 6. Risiken dieses Registers — offen benannt

- **Data Snooping auf Familienebene:** H5 ist eine Verfeinerung genau der
  Familie, die in Runde 1 zerfallen ist. Dass wir sie überhaupt wählen,
  ist selbst ein Ergebnis der Beobachtung, dass Donchian *fast*
  funktioniert hätte. Regel 14 schützt gegen Parameter-Kontamination,
  **nicht** gegen diese Familien-Kontamination. [SICHER, dass das Risiko
  besteht; NICHT ENTSCHEIDBAR, wie groß es ist]
- **Erwartete Rundenzahl unbekannt.** NR7-Balken sind häufig; die Regel
  könnte deutlich mehr als 4,5 Runden/Jahr erzeugen und damit
  kostenempfindlicher werden. Das ist kein Ausschlussgrund, aber es kann
  K-BASIS zur bindenden Hürde machen. [VERMUTUNG]
- **S-A (2017–2019) ist dünn und strukturell anders** (flache Bücher,
  andere Marktmikrostruktur). Klausel A verlangt Bestehen auch dort — das
  ist streng, aber bewusst so.
- **Restwahrscheinlichkeit:** Meine Vorabschätzung, dass H5 den vollen
  Standard übersteht, liegt bei **10 %**. Zum Vergleich: für H1 lag sie
  bei 25–35 %, und Gate 1 wurde negativ.

## 7. Was Freigabe bedeutet

Runde 2 ist nach Regel 13 der **letzte Anlauf**. Ein negatives Gate 2
beendet das Programm mit dem Ergebnis „mit unseren Mitteln nicht
erreichbar". Bei einer Vorabwahrscheinlichkeit von 10 % ist der
wahrscheinlichste Ausgang dieser Runde das Programmende.

Das ist kein Argument gegen die Freigabe — ein sauber dokumentiertes Ende
war von Anfang an ein zulässiges Ziel. Es ist ein Argument dafür, die
Freigabe **bewusst** zu erteilen und nicht als Fortsetzungsautomatik.


---

# NACHTRAG 04.08.2026 — zwei Eintragungen zu einem eingefrorenen Register

Register v2.0 bleibt inhaltlich eingefroren. Die folgenden zwei Zeilen
ändern keinen Abschnitt oben, sie hängen an.

## N1. Korrekturvermerk zu E2 und G2 — 45 Minuten Look-ahead

`messung_f2_ic.py:57-70` (`zu_1h()`) vergibt als Zeitstempel den
**Stundenbeginn** H, als Preis aber den Close am **Stundenende** H+60min.
`rennen()` startet bei `bisect_right(zeiten, H)`, also bei H+15min — die
Viertelstunden H+15, H+30 und H+45 werden mitgerennt, obwohl der
Signalpreis dort noch nicht bekannt ist.

**Betroffen:** E2, G2 und die Nachtragsmessung T-034N…T-041N.

**Gemessen** am Sensitivitätslauf mit Start bei H+60min
(`messung_t034b_strategien.py`, Spalte `q_la`): größter
Verzerrungsbetrag **4,77 pp** (BOLLINGER_BOUNCE J1 ±2,5 %/72h:
49,33 % → 44,56 %), Richtung der großen Abweichungen **durchweg
negativ**.

**Folge:** Der Look-ahead hat P(auf) systematisch **überschätzt**. Ohne
ihn fallen die Ergebnisse schlechter aus, nicht besser. Die negativen
Urteile zu E2, G2 und zur Nachtragsmessung werden dadurch **bestätigt,
nicht entwertet**. Eine Neurechnung ist zur Absicherung der Urteile nicht
erforderlich — sie wäre nur nötig, wenn aus diesen Messungen ein
**positives** Ergebnis abgeleitet werden sollte.

Datenbank: `befunde`, befund_id 31, `konfidenz='SICHER'`.

## N2. H9 — Chartstruktur-basierte Entry-Hypothesen · VORGEMERKT

**Zur ID:** Der Auftraggeber bezeichnet diese Hypothese als „H5". H5 ist
seit Runde 2 durch **Crabel NR7 / Volatilitätskontraktion und Ausbruch**
belegt (Abschnitt 2, Trials T-031 bis T-033, 18 Zeilen in `trials`).
H6, H7 und H8 sind vergeben und gestrichen. Die Vormerkung erhält daher
die nächste freie Nummer **H9**. Keine bestehende Zeile wurde geändert.

**Status:** VORGEMERKT — nicht vorregistriert, nicht getestet, kein
Trial-Budget, kein Trial-Zähler berührt.

**Kandidaten:** Breakout über mehrfach bestätigten Widerstand plus
Retest · Pullback an bestätigtem Support im Aufwärtstrend ·
Marktstrukturwechsel (Higher Low nach Strukturbruch) · Range-Breakout mit
Retest · Fibonacci-Retest ausschließlich als Zusatzkonfluenz.

**Bedingung für die Vorregistrierung:** Der Multi-Strategy-Bug muss
gelöst sein.

**Regel 14 gilt:** Quelle vor 2015, andere Anlageklasse. Alle
Swing-Anker müssen kausal sein und einen `confirmation_timestamp`
tragen.

**Offener Einwand, der vor einer Vorregistrierung zu klären ist:**
Abschnitt 0 dieses Registers (Zeile 46) stellt fest, dass H5, H6 und H7
„Varianten derselben Grundannahme" sind — Preis setzt eine Struktur, die
Struktur hält oder bricht. H6 (Rhea 1932) und H7 (Darvas 1960) wurden
nach Regel 14 **gestrichen**, weil ihre Quellen keine Swing-Weite nennen
und die Anker damit frei wählbar wären. Mindestens drei der fünf
H9-Kandidaten (bestätigter Widerstand, bestätigter Support,
Marktstrukturwechsel) haben genau dieses Problem. Ohne eine Quelle vor
2015, die die Bestätigungsweite **zahlenmäßig** festlegt, würde H9 an
derselben Stelle scheitern wie H6 und H7. Das ist kein Ausschluss — es
ist die Hürde, die vor der Vorregistrierung genommen werden muss.

## N3. H10 — Wyckoff-Phasen als Regime-Klassifikator · VORGEMERKT

**Eingetragen:** 05.08.2026 · **Status:** VORGEMERKT — nicht
vorregistriert, nicht getestet, kein Trial-Budget, kein Trial-Zähler
berührt.

**Zur ID:** H5 ist durch Crabel NR7 belegt, H6 (Rhea 1932) und H7
(Darvas 1960) wurden nach Regel 14 gestrichen, H8 durch
Freigabeentscheidung, H9 ist die Chartstruktur-Vormerkung vom 04.08.
H10 ist die nächste freie Nummer.

**Herkunft:** Vorschlag des Auftraggebers vom 05.08.2026 in Form eines
vollständigen Implementierungsauftrags („Wyckoff-Makrozyklus-Strategie",
`WyckoffMacroCycleStrategy` mit Phasen-Scoring, DCA, Teilgewinnen,
Trailing-Stops, optionalem Short und eigener Backtest-Engine).

**Was NICHT übernommen wird und warum:**

Der Auftrag wurde als Neubau bewusst **nicht ausgeführt**. Vier Gründe,
alle gegen den Bestand geprüft:

1. **Regel 14.** Wyckoff (1930er, Aktien) erfüllt „vor 2015" und „andere
   Anlageklasse", **beziffert aber keine Schwellen**. Der Auftrag verlangt
   rund 40 frei wählbare Parameter (RSI-Grenzen, BB-Perioden, Score-
   Gewichte je Phase, Bestätigungs-Candles, ATR-Multiplikatoren,
   R-Multiples). Das ist exakt der Grund, aus dem H6 und H7 gestrichen
   wurden — siehe Abschnitt 1 dieses Registers.
2. **Parameterraum.** 4 Phasen × ~9 gewichtete Kriterien plus Schwellen,
   gegen zwei Jahre Daten mit **1,3 effektiv unabhängigen Coins**
   (E5, Befund 16, `messung_f2_ic.py:49`).
3. **Widerspruch zur Datenlage.** `core/events.py:15-18` kennt kein
   `SHORT` — der Bot handelt Spot gegen USDC. Und die geforderten
   Teilgewinne bei 1R/2R/3R würden genau die drei V4-Strategien
   ausschließen, die im Journal positiv waren: RSI_OVERSOLD R/R **0,32**,
   STOCHRSI_REVERSAL **0,32**, FIBONACCI_SUPPORT **0,54**.
4. **Zweiter Bot.** Eigene Config, Engine, Portfolio und Metriken —
   gegen die gesetzte Grenze „kein zweiter Bot, keine parallele
   Datenarchitektur".

**Was H10 tatsächlich ist — der messbare Kern:**

Wyckoff-Phasen als **Regime-Klassifikator**, nicht als Strategie, geprüft
über die vorhandene Barrieren-Infrastruktur
(`messung_t034b_strategien.py`). Eine einzige Frage:

> Liegt P(auf) nach einem bestätigten ACCUMULATION→MARKUP-Wechsel über
> der coinweisen Kostenschwelle `p_be = 0,5 + c/(2B)`?

Getestet würde wie bisher: drei Barrieren, beide Jahre, Block-Bootstrap
über Kalendertage, phasengleiches Placebo, BH-FDR über das Gesamtset.
Aufwand: ein Tag statt zwei Wochen, kein neuer Code außerhalb von
`docs/messungen_2026-07/code/`.

**Bedingungen für die Vorregistrierung:**

1. Der Multi-Strategy-Bug muss gelöst sein. *(Stand 05.08.: die
   Bridge-Ursache ist behoben, Strategievielfalt nachgewiesen.)*
2. **Regel 14 muss erfüllt sein**: eine Quelle vor 2015, die die
   Phasen-Schwellen **zahlenmäßig** nennt. Ohne diese Quelle ist H10
   nicht vorregistrierbar — dieselbe Hürde wie bei H6, H7 und H9.
3. Alle Phasen-Anker müssen kausal sein und einen
   `confirmation_timestamp` tragen.
4. Kein Short, solange `core/events.py` keine Short-Seite kennt.

**Was aus dem Auftrag unabhängig von H10 übernommenswert ist** — als
Backtest-Disziplin, nicht als Hypothese: Signalbildung auf Candle Close
mit Ausführung am Open der Folgekerze, Warm-up-Sperre bis alle
Indikatoren valide sind, feste Konfliktpriorität (Stop vor Teilverkauf,
Exit vor Einstieg), Gebühren und Slippage auf beiden Seiten, keine
Annahme exakter Stop-Füllung bei Gaps. Diese Punkte sind gute Praxis
und in den vorhandenen Messskripten teilweise bereits umgesetzt.
