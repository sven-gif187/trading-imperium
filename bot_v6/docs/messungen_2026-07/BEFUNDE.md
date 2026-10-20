# Befunde E1 / E2 / E5 — Stand 30.07.2026

Urteile mit Konfidenz. Rohzahlen in `ausgaben/`, Methode in `README.md`.
Konvention: [SICHER] = Messlauf oder Codezeile liegt bei · [WAHRSCHEINLICH]
= Deutung auf gemessener Basis · [VERMUTUNG] = markierte Hypothese.

**Absolute Dollarbeträge aus dem Harness sind NICHT auf den Livebetrieb
übertragbar** (E1: Nachkaufrate im Harness um Faktor ~8 zu niedrig).
Vergleichszahlen (Raten, R-Größen, Anteile) sind übertragbar, soweit beide
Vergleichsseiten gleich betroffen sind.

---

## E1 — Nachkauf-Schutz und Harness-Abweichung

1. **Nachkauf-Deckel** seit 29.07. verdrahtet: `app.py:1761` liest
   `dca_max_levels` (= 3) aus `config.json:55`; Sperre in
   `app.py:1806-1810`. [SICHER]
2. **Exposure-Check ist ein De-facto-Nachkaufverbot.** `app.py:1812-1819`
   blockiert bei `cur_val + fixed_amount > 25 %` des Equity
   (`config.json:25`). Mit `position_size_pct = 20` heißt das: Block,
   sobald die Position mehr als 5 % des Equity wert ist (~23–25 $ bei
   ~465–500 $) — der Erstkauf (~93 $) liegt immer darüber. Die
   ETH-Position (266,67 $, 4 Käufe) wäre schon beim ersten Nachkauf
   gestoppt worden. Künftige Live-Nachkaufrate ≈ 0 %. [SICHER für die
   Arithmetik, WAHRSCHEINLICH für die Rate]
3. **Cooldown dreifach fail-open:** `app.py:1789-1790` (`except: pass`),
   Risiko-Tore `app.py:1754-1755`, Reentry-Guard `app.py:1834-1835`;
   `last_dca_time` nur im RAM (`agents/dca_advanced.py:17`) — Neustart
   löscht alle Cooldowns. [SICHER]
4. **`dca_drop_pct` ist toter Code:** definiert in `config.json:56` und
   `config/settings.py:236`, aber die −2-%-Schwelle ist hart codiert
   (`app.py:1798`, `entry * 0.98`). Nur im Code verstellbar. [SICHER]
4b. **Stichtag der Live-Kennzahlen.** Die E1d-Zahlen (421 abgeschlossene
   Positionen, Verteilung 344/63/12/2 nach Nachkaufzahl, 5 offen,
   **18,29 %** Nachkaufrate) beruhen auf den **ersten 942** von 950
   Einträgen des Snapshots, Stand 29.07.2026 04:17. Der Bot lief bis
   21:04 weiter (8 weitere Einträge: 4 SELL, 4 BUY). Auf dem vollen
   Snapshot: **425** Positionen, 78 mit Nachkauf, Verteilung 347/64/12/2,
   **18,35 %**. Differenz +0,06 pp, Faktor gegen die Harness-Rate 8,34
   statt 8,31 — keine Schlussfolgerung ändert sich. Nachgerechnet mit
   chronologischer Positionsrekonstruktion, die den externen 942er-Stand
   exakt reproduziert. [SICHER]

5. **Harness-Nachkaufrate 2,2 % gegen 18,3 % live, erklärt:** Der Harness
   kauft nur zum 15m-Schlusskurs, prüft Exits vorher am Kerzentief
   (`backtest/ausstieg_backtest.py:279-314`) — das Rennen „Nachkauf bei
   −2,0 % gegen Stop bei −2,5 %" gewinnt strukturell immer der Stop, live
   (12-s-Takt) fast immer der Nachkauf. Mit Live-Timing: 17,7 %
   (Gesamtjahr) bzw. 16,4 % (Live-Fenster) gegen 18,3 % gemessen.
   Stunden-Gate sekundär (+4,8 pp), `max_stufen`/Exits ≈ 0 pp.
   Urteil: Harness TEILWEISE brauchbar — für A/B-Vergleiche ja, für
   absolute Zahlen nein. [SICHER]

## E2 — Stop-Abstand gegen Einstiegsqualität

6. **Kein Stop rettet das System.** 7 Varianten × 2 Jahre: erzieltes R/R
   erreicht nie das Break-even-R/R (bester Fall 0,50 gegen 0,96 nötig).
   ATR-Stops ohne Eigeneffekt gegenüber festen Stops gleicher Weite.
   [SICHER: `ausgaben/messung_e2_stops_out.txt`]
7. **Der Verlust wird umgepackt, nicht beseitigt.** Stop-Anteil am
   Gesamtverlust konstant 88,8–93,6 %. Weitung 2,0→5,0 %: Stops 0,43x/0,28x
   so häufig, je Stop 2,59x/3,19x so teuer. [SICHER]
8. **Stop-Weitung 2,0→5,0 % bringt +0,134 R (J2, 95-%-KI [+0,078;+0,191])
   bzw. +0,131 R (J1, KI [+0,043;+0,236])** — gesichert (Null nicht im
   Intervall), schließt aber nur ~30–36 % der Lücke zum Break-even.
   [SICHER: `ausgaben/messung_e2_phasenplacebo_out.txt`]
9. **Kernbefund: kein Richtungsvorteil im Einstieg.** Symmetrisches
   ±2,5-%-Barrierenrennen: echt 47,66 % (J2) / 50,69 % (J1) gegen
   Zufall. Phasengleich (gleiche Tage, nur Uhrzeit zufällig): 45,46 % /
   51,52 % — echter Wert in beiden Jahren innerhalb des 95-%-KI
   ([42,58;52,56] bzw. [43,33;57,69]). Timing-Beitrag mit gegenläufigem
   Vorzeichen (+2,20 pp J2, −0,83 pp J1). Der Einstieg selektiert
   Volatilität (MFE UND MAE über Zufall), keine Richtung.
   Urteil phasengleich: BESTÄTIGT. [SICHER]
10. **Break-even-Schwelle:** Bei ±2,5-%-Schranken und 0,3 % Rundenreibung
    bräuchte es P(auf) = 56 %. Die J2-Obergrenze (52,56 %) liegt darunter —
    ein kostendeckender Richtungsvorteil ist für J2 **ausgeschlossen**,
    nicht bloß unbewiesen. J1-Obergrenze 57,69 % bei nur 43 Einstiegstagen:
    NICHT ENTSCHEIDBAR. Einschränkung: Schwelle gilt für das stilisierte
    Barrierensystem, nicht für die echte Stop/Ratsche/Breakeven-Kombination.
    [SICHER für die Intervalle, WAHRSCHEINLICH für die Übertragung]
11. **24h-Rückkehr über den Einstand** nach Stop: 56 % (J2) / 64 % (J1)
    beim Ist-Stop — misst Kursrauschen, nicht entgangenen Ertrag (bei 5 %
    Stop fällt sie auf 25/41 %, EV(R) steigt trotzdem nur um 0,13 R).
    [SICHER für Quoten, WAHRSCHEINLICH für Deutung]
12. **Giveback ~1,4 pp ist Konstruktion, kein Potenzial** (E[MFE] > 0 auf
    jedem driftfreien Pfad; Optional Stopping). Ausführlich:
    `DIE-GESCHICHTE.md` Anhang B. [SICHER]
13. **Kapitalgrenzen-Artefakt:** konstante Netto-P&L (~−450 $) über alle
    J2-Stopvarianten ist Sättigung bei 500 $ Startkapital, kein Beleg für
    Unempfindlichkeit. Unterschiede nur in EV(R) sichtbar. [SICHER]

## E5 — Coin-Universum

14. **Kein Coin mit positivem Erwartungswert** in einem der beiden Jahre
    (bester: LINK J1, −0,120 R). Universum „nur positive Coins" existiert
    nicht; Rangfolge zwischen den Jahren instabil (BTC: Platz 10 → 5).
    [SICHER: `ausgaben/messung_e5_universum_out.txt`]
15. **BTC-only verschärft die Reibung:** höchster Anteil Trades mit
    |Brutto| < 0,3 % (31,7 % J2 / 33,3 % J1) bei niedrigster Volatilität;
    Gebühr je Trade 0,199 $ statt 0,078 $. EV(R) besser, EV$/Trade
    schlechter — gegenläufig, kein Vorteil ableitbar. [SICHER]
16. **Diversifikation ist nominell:** mittlere Paarkorrelation 0,72–0,75,
    Abwärtsphase 0,755/0,796 (steigt, geht nicht gegen 1);
    N_eff = 1,23–1,42 — 11 Coins wirken wie ~1,3 unabhängige Positionen.
    [SICHER für ρ, WAHRSCHEINLICH für N_eff]
17. **Universums-Mismatch:** Journal enthält XRP (119 Einträge), das in
    `config.json` und `data_store/backtest/` fehlt; ATOM/NEAR/UNI live nie
    gehandelt. `config.json` listet 11 Coins, nicht 12 (`app.py:1534`
    `coins[:12]` wirkungslos). [SICHER]

## Übergreifend widerlegt

18. Die Annahme **„der Einstieg funktioniert, das Leck ist Nachkauf plus
    Ausstieg" ist nicht haltbar.** Der Einstieg trägt keinen messbaren
    Richtungsvorteil; Nachkauf und Ausstieg verstärken ein System ohne
    Vorzeichen, sie verursachen den Verlust nicht. [SICHER auf Basis von
    Befund 9/10]

---

## F1 — Wie tief lässt sich die Kostenhürde senken?

19. **Der Bot kennt nur Market-Orders.** 12 echte Order-Aufrufe im
    Quelltext, alle `create_market_*` (`execution/engine.py:384-385`,
    `execution/exchange_client.py:364-366`, `execution/futures_trader.py:67`
    /`87`/`107`/`109`, `execution/multi_exchange.py:147-149`,
    `live/live_runner.py:60`/`68`). **Null** `create_limit_*`, null
    generisches `create_order(...)`, null `postOnly`/`timeInForce`. Die
    13. Fundstelle des Scans (`features/safety.py:100`) ist eine
    Rate-Limit-Gewichtstabelle, keine Order. Limit-Ausführung ist im
    Projekt nicht vorhanden — sie müsste gebaut werden.
    [SICHER: `ausgaben/messung_f1_reibung_out.txt`, F1a]
20. **`config.json` enthält keinen einzigen Gebühren- oder
    Slippage-Schlüssel.** Alle Kostenparameter sind hart codiert:
    `execution/engine.py:252` (`fee_rate = 0.001`),
    `execution/engine.py:243` (Slippage U(0,02;0,08) %),
    `backtest/ausstieg_backtest.py:59/60`. Die Rundenreibung 0,300 % ist
    damit als 2 × (0,100 % + 0,050 %) belegt, nicht angenommen. [SICHER]
21. **Maker bringt auf Binance Spot nach den Zahlen im Projekt exakt
    null Gebührenersparnis.** `backtest/fees.py:9` führt für Binance
    `maker: 0.10` und `taker: 0.10` — identisch. Der dort ebenfalls
    hinterlegte `bnb_discount: 0.075` ist **tote Daten**:
    `FeeCalculator.calculate()` (`fees.py:31`) liest ausschließlich den
    Schlüssel `order_type` (`"maker"`/`"taker"`) und erreicht den Rabatt
    nie. `FeeCalculator` selbst wird nur von `backtest/engine.py:121` und
    den Tests benutzt — weder vom Bot noch vom Ausstiegs-Harness.
    Der einzige reale Vorteil einer Limit-Order ist der Wegfall der
    Slippage. [SICHER]
22. **Kostensenkung allein rettet Jahr 2 nicht.** Break-even
    P(auf) = 0,5 + c/(2·2,5 %): 0,30 % → 56,0 % · 0,20 % → 54,0 % ·
    0,15 % → 53,0 % · 0,10 % → 52,0 % · 0,05 % → 51,0 %. Damit die
    J2-KI-Obergrenze von 52,56 % break-even wäre, müsste die Reibung
    unter **0,128 %** je Runde fallen. Die nach den Projektzahlen
    erreichbare Untergrenze (Limit ohne Slippage + BNB-Rabatt) liegt bei
    **0,150 %**. Sie unterschreitet 0,128 % nicht. Befund 10 bleibt
    bestehen, auch bei maximaler Kostensenkung. [SICHER für die
    Arithmetik, WAHRSCHEINLICH für die Übertragung auf das echte
    Ausstiegssystem]
23. **Der Bot handelt genau in dem Horizontband, in dem die Reibung
    dominiert.** Mediane absolute Bewegung gegen 0,30 % Reibung, gepoolt:
    1 h 0,35 %/0,45 % (J2/J1) → nötige Trefferquote 92,9 %/83,7 % ·
    4 h 0,71 %/0,91 % → 71,1 %/66,6 % · 24 h 2,03 %/2,50 % → 57,4 %/56,0 % ·
    72 h 3,72 %/4,67 % → 54,0 %/53,2 % · 7 d 5,55 %/7,34 % → 52,7 %/52,0 %.
    Die gemessene mittlere Haltedauer des Harness liegt bei 4,7–15,8 h je
    Coin (Befund 14, E5a). Erst ab ~72 h wird die Reibung zweitrangig.
    [SICHER: `ausgaben/messung_f1_reibung_out.txt`, F1d]
24. **Die reale Rückrechnung: der Bruttovorteil deckt ein Drittel der
    Kosten.** 419 geschlossene Positionen aus dem Snapshot,
    61.460,86 $ Gesamtnotional. Ergebnis ohne jede Reibung **+31,44 $**
    = **+0,102 %** je Positionsrunde, gegen 0,300 % Ist-Reibung und
    0,150 % Untergrenze. Der Bruttovorteil deckt 34 % der Ist-Reibung und
    68 % der Untergrenze. Szenarien: Ist −60,75 $ · Maker statt Taker
    **±0,00 $** · Limit ohne Slippage +30,73 $ · Limit + BNB +46,10 $.
    Gegenprobe: die Rückrechnung mit den Journal-Gebühren ergibt
    −26,16 $ gegen −27,88 $ Summe der protokollierten `pnl`-Felder — die
    Rekonstruktion trifft das Journal auf 1,72 $. Sie reproduziert auch
    die 425 Positionen (419 geschlossen + 5 offen + 1 Geister-Verkauf)
    aus Befund 4b. [SICHER]
25. **Zwei Geister-Verkäufe im Journal**, SOL/USDC am 13.06. und
    26.06.2026, letzterer über 1,701317 Stück / 123,78 $ ohne Bestand.
    Wer sie als Erlös mitzählt, bekommt statt −26,16 $ ein Plus von
    +97,62 $ — die Größenordnung des Vorzeichenfehlers ist 124 $. Der
    Schutz in `execution/engine.py:291-299` datiert vom 29.07. und wirkt
    rückwirkend nicht. [SICHER]
26. **Limit-Orders werden nicht sicher gefüllt, und die Füllungen sind
    die schlechteren.** Berührungsquote (Obergrenze der Füllquote):
    Limit am Close 92–99 % je nach Wartefenster, 0,05 % passiver nur
    79–95 %; im 15-Minuten-Fenster bleiben 4,7 % bzw. **20,7 %**
    ungefüllt. Die adverse Selektion beträgt −0,019 bis −0,041 Prozent-
    punkte: gefüllt wird bevorzugt, wenn der Kurs weiterläuft. Sie frisst
    38–82 % der nominellen 0,05-%-Slippage-Ersparnis je Seite auf.
    Warteschlangenposition und Teilfüllung sind darin **nicht** abgebildet
    — die echte Füllquote liegt darunter. [SICHER für die Quoten,
    WAHRSCHEINLICH für die Deutung]

## F2 — Trägt eines der Features Information?

27. **Drei von acht V4-Strategien können strukturell nie feuern.**
    `features/indicators.py::calc_all_indicators` ist in `app.py:64`
    importiert und wird **nirgends aufgerufen**. Der Snapshot
    (`data/market_data.py:62-79`) erzeugt nur RSI, EMA20, EMA50, MACD,
    Bollinger, ADX, ATR. Damit fehlen die Spalten `ICH_*`, `TSI`,
    `TSI_signal` und `Vol_high` dauerhaft, und
    `agents/v4_strategies.py:127` (Ichimoku), `:162` (TSI) sowie `:148`
    (Momentum-Breakout) fallen jedes Mal in ihren Nichttreffer-Zweig.
    Ebenso unerreichbar: EMA200 — sie braucht 200 Balken, der Bot holt
    120 (`config.json candle_limit`). [SICHER]
28. **Inventar: 25 Features rekonstruierbar, 13 nicht prüfbar.**
    Rekonstruierbar 19 aktiv im Kaufpfad, 4 berechenbar aber nicht
    verdrahtet, 2 tot. Nicht prüfbar, weil nur live und nicht archiviert:
    Orderbuch-Imbalance, Whale, Reddit, Capitol, Funding, On-Chain/NUPL,
    News, DXY, das daraus gebildete Ensemble, Multi-Timeframe (braucht
    5m-Kerzen, es liegen nur 15m) sowie die beiden toten Spalten.
    Für diese 13 gilt: **NICHT ENTSCHEIDBAR**, nicht "kein Effekt".
    [SICHER: `ausgaben/messung_f2_ic_out.txt`, F2a]
29. **Die rohen p-Werte sind wertlos, und zwar massiv.** 75 Tests je
    Jahr. Naiv gerechnet: 65 (J2) bzw. 59 (J1) Tests mit p < 0,05, nach
    BH-FDR unverändert 65 bzw. 59. Auf der effektiven Stichprobe
    (n_eff = Balken/h × N_eff = 1,3 aus Befund 16) bleiben 24 bzw. 10 mit
    p < 0,05 und nach BH-FDR **12 bzw. 6**. Bei reinem Zufall wären 3,8
    Treffer zu erwarten. Wer die naive Zahl liest, sieht 65 Entdeckungen,
    wo höchstens 12 stehen. [SICHER]
30. **Kein einziges Feature erreicht die ökonomische Schwelle.** Genau
    vier Feature/Horizont-Paare sind in **beiden** Jahren
    vorzeichengleich **und** überstehen in beiden die BH-FDR auf der
    effektiven Stichprobe: Close/EMA20 (1 h, IC −0,0329/−0,0325),
    Close/Close[−5] (1 h, −0,0278/−0,0358), Lage im Bollinger-Band
    (1 h, −0,0314/−0,0272), StochRSI (1 h, −0,0257/−0,0328). Alle vier
    sind negativ, alle liegen auf 1 h, und alle messen dieselbe Größe:
    kurzfristige Überdehnung gegen das jüngste Mittel. Das ist **ein**
    Befund, nicht vier. Der stärkste |IC| = 0,036 entspricht einer
    Trefferquote von 51,1 %. Nötig wären 56 % (IC ≈ 0,179) bei 0,30 %
    Reibung bzw. 53 % (IC ≈ 0,090) bei der Untergrenze 0,15 %. Direkt
    gemessen statt genähert: das günstigste Feature-Fünftel liefert über
    1 h im Mittel +0,008 % (J2) bzw. +0,027 % (J1) — gegen 0,30 %
    Reibung. Faktor 11 bis 37 zu klein. [SICHER]
31. **Die stärksten Roh-ICs sind Jahr-2-Artefakte.** Close/VWAP(120) über
    24 h: −0,0937 in J2, −0,0279 in J1 (q_eff 0,98 — nicht signifikant).
    Abstand zu Fib 61,8 % über 24 h: −0,0901 gegen −0,0296 (q_eff 0,98).
    Schrumpfung um Faktor 3 bei Jahreswechsel. J2 war ein
    Abwärtsjahr (BTC −45,4 %), J1 ein Aufwärtsjahr (+74,4 %) — beide
    Features messen "Kurs über dem Mittel" und wechseln mit dem Regime
    die Stärke. [SICHER für die Zahlen, WAHRSCHEINLICH für die Ursache]
32. **Die EMA-Trendregel des Bots zeigt gegen den gemessenen
    Zusammenhang.** `agents/signal_agent.py:95-97` vergibt +1 Punkt für
    `price > ema20 > ema50`. Der gemessene IC von Close/EMA20 ist in
    **beiden** Jahren und auf **allen drei** Horizonten negativ
    (J2: −0,0329/−0,0370/−0,0427; J1: −0,0325/−0,0196/−0,0081), ebenso
    Close/EMA50 und EMA20/EMA50. Die Regel belohnt genau das Vorzeichen,
    das in den Daten schlechter abschneidet. Wie groß der Schaden im
    Gesamtsystem ist, ist damit **nicht** gemessen — der IC ist zu klein,
    um daraus einen Beitrag zur P&L abzuleiten. [SICHER für die
    Richtungsdiskrepanz, NICHT ENTSCHEIDBAR für die Wirkung]
33. **Vorzeichenkonstanz 56 von 75 (75 %) ist keine gute Nachricht.**
    Die 75 Tests sind stark redundant: Close/EMA20, Close/EMA50,
    EMA20/EMA50, Lage im BBand, StochRSI, VWAP-Abstand und Fib-Abstand
    sind Varianten derselben Größe. 75 % Konstanz über eine redundante
    Familie belegt nicht 56 unabhängige stabile Befunde. Zum Vergleich:
    die Volatilitätsfamilie (Vola(14), BBand-Breite, ATR/Close,
    High-Low-Range) **wechselt** auf 24 h geschlossen das Vorzeichen
    zwischen den Jahren. [SICHER für die Zahlen, WAHRSCHEINLICH für die
    Deutung]

## F3 — Der Vergleichsmaßstab

34. **Der Bot verliert in beiden Jahren deutlich gegen stures Halten.**
    Startkapital 500 $, gleiche Reibung.
    Jahr 2 (BTC −45,35 %): BTC halten −227,15 $ (−45,4 %, MaxDD 53,9 %) ·
    BTC-DCA wöchentlich −114,37 $ (−22,9 %, MaxDD 31,1 %) ·
    11 Coins gleichgewichtet −309,25 $ (−61,9 %) · **Bot −450,56 $
    (−90,1 %)**. Abstand zum Halten −223,41 $, zum DCA −336,19 $.
    Jahr 1 (BTC +74,39 %): BTC halten **+370,62 $** (+74,1 %) ·
    BTC-DCA +207,43 $ (+41,5 %) · 11 Coins gleichgewichtet +86,66 $
    (+17,3 %) · **Bot −313,44 $ (−62,7 %)**. Abstand zum Halten
    **−684,06 $**, zum DCA −520,87 $.
    Der Bot verliert im Aufwärtsjahr Geld und im Abwärtsjahr doppelt so
    viel wie ein Sack BTC. [SICHER:
    `ausgaben/messung_f3_benchmark_out.txt`; Bot-Zahlen aus dem
    Kontrollanker bzw. `messung_e2_stops_out.txt` Zeile 38]
35. **Wöchentliches DCA schlägt Halten im Abwärtsjahr, verliert im
    Aufwärtsjahr — wie es die Konstruktion vorgibt.** −22,9 % gegen
    −45,4 % (J2), +41,5 % gegen +74,1 % (J1). Das ist kein Vorteil,
    sondern die geringere durchschnittliche Investitionsdauer. Der
    MaxDD halbiert sich entsprechend (31,1 % gegen 53,9 %). [SICHER]
36. **Im Live-Fenster des Journals (10.06.–29.07.2026, 49 Tage) lag der
    Bot mit Ist-Kosten bei −57,81 $, BTC-Halten bei +16,54 $, BTC-DCA
    bei +4,22 $, 11 Coins gleichgewichtet bei +3,01 $.** Ohne jede
    Reibung stünde der Bot bei +34,38 $. Die Zahlen sind **nicht**
    risikoparitätisch: der Bot war nie voll investiert und handelte neun
    Coins inklusive XRP. Als Größenordnung taugen sie, als sauberer
    Vergleich nicht. [SICHER für die Zahlen, VERMUTUNG für jede
    Verhältnisaussage]

---

## G1 — Verifikation der F2-Indikatoren

37. **17 von 21 numerisch geprüften Nachbauten sind exakt.** Spearman
    1,0000 gegen die Projektimplementierung auf 11 Coins (J2, ab Balken
    200), darunter alle vier stabilen F2-Kandidaten in ihrer Kernform:
    RSI, EMA-Abstände, MACD, Bollinger, ATR, ADX (market_data-Variante),
    StochRSI, TSI, VWAP (nach Aufklärung, s. Befund 40), Volumen-Ratio,
    Hoch(20). Die Handrechnung RSI(14) nach Wilder (ausgeschriebener
    Rechenweg, BTC Balken 0–16) trifft den Nachbau exakt; pandas_ta
    weicht früh ab (ewm-adjust-Start), konvergiert danach.
    [SICHER: `ausgaben/messung_g1_indikatoren_out.txt`]
38. **Vier echte Abweichungen, alle benannt, drei mit IC-Neuberechnung:**
    (a) `pump_5`: app.py:747 rechnet 4 Balken zurück, der Nachbau 5
    (Off-by-one). Neu gerechnet mit der App-Formel: IC 1 h
    −0,0232 (J2) / −0,0354 (J1) — Vorzeichen und Größenordnung
    unverändert, der stabile Kandidat bleibt.
    (b) `fib_dist_618`: v4_strategies.py:46-47 nutzt tail(100), der
    Nachbau 120. Neu: −0,0958 (J2, 24 h) gegen −0,0196 (J1) — bleibt
    Jahr-2-Artefakt.
    (c) `di_diff`: F2 zitierte regime_detection.py:42 (ta.adx, Wilder),
    nachgebaut wurde die SMA-Variante aus market_data.py:117 — Pearson
    zwischen beiden Projektvarianten **−0,51**. Mit der Wilder-Variante
    kippt der IC auf schwach positiv (max +0,029). Die F2-Zeile di_diff
    war unbrauchbar; am Urteil ändert sich nichts, weil beide Varianten
    weit unter der Schwelle liegen.
    (d) `rsi_div_bull`: der Projektdetektor verlangt 1 % Mindestschwung,
    +2 RSI-Marge und benachbarte Swing-Tiefs — der Nachbau feuerte 407
    von 471 Malen, wo das Projekt nicht feuert (Prävalenz Projekt: 1,0 %).
    Die F2-Zeile ist NICHT belastbar; IC-Neuberechnung nicht in
    vertretbarer Laufzeit möglich: NICHT ENTSCHEIDBAR. [SICHER]
39. **F2-Urteil: BESTÄTIGT.** Kein neu gerechneter IC erreicht 0,090
    (ökonomische Schwelle der Reibungs-Untergrenze), kein stabiler
    Kandidat kippt das Vorzeichen. Zwei Detailzeilen der F2-Tabelle
    (di_diff, rsi_div_bull) sind als unbelastbar zu streichen, das
    Gesamturteil trägt ohne sie. [SICHER]
40. **`vwap_agent.py:64` rundet den zurückgegebenen VWAP auf 2
    Dezimalen.** Bei DOGE (~0,1 $) macht das das Rückgabefeld wertlos
    (24,6 % Vorzeichenabweichung gegen die ungerundete Formel); gegen
    die ungerundete Agentenformel ist der F2-Nachbau exakt
    (Spearman 1,0000). Die Bias-Entscheidung des Agenten rechnet VOR
    der Rundung und ist nicht betroffen — aber jeder künftige Nutzer
    des `vwap`-Felds bekommt für Kleinpreis-Coins Schrott. [SICHER]
41. **Der Warmup-Effekt des 120-Balken-Fensters ist vernachlässigbar.**
    Fensterwert gegen Vollserienwert (beides Projektweg, BTC/ETH/DOGE,
    6423 Fenster): Spearman ≥ 0,9998 für RSI, EMA20/50, MACD, ADX, ATR,
    BBand. Die F2-Vollserienrechnung ist damit auf den Live-Bot
    übertragbar. [SICHER]

## G2 — Lange Horizonte mit weiten Schranken

42. **Jahr 2: je länger der Horizont, desto schlechter.** P(auf) fällt
    monoton: 47,66 % (±2,5/72 h) → 42,68 % (±5/7 d) → 39,50 % (±7/14 d)
    → 35,72 % (±10/30 d). Alle vier Kombinationen liegen mit der
    KI-Obergrenze unter dem Break-even, selbst bei der Reibungs-
    Untergrenze 0,15 %: **AUSGESCHLOSSEN**. E[r] je Runde inkl.
    Zensierter: −0,11 % → −0,71 % → −1,42 % → −2,78 % brutto. [SICHER:
    `ausgaben/messung_g2_horizonte_out.txt`]
43. **Jahr 1: die scheinbar guten langen Quoten sind Phasen-Beta, nicht
    Einstiegsleistung.** P(auf) steigt auf 52,10/55,98/62,93 % — aber
    das phasengleiche Placebo S2 (gleiche Tage, zufällige Uhrzeit) liegt
    bei 51,89/55,90/62,57 %. Echt minus S2: **+0,21/+0,08/+0,35 pp** —
    praktisch null. Was über dem Jahres-Placebo S1 (~51,5 %) liegt, ist
    die Auswahl der Angst-Tage im Bullenjahr. [SICHER für die Zahlen,
    WAHRSCHEINLICH für die Zuordnung]
44. **Dieselbe Tagesauswahl wechselt zwischen den Jahren das
    Vorzeichen.** J1, ±10/30 d: S2−S1 = +11,1 pp. J2, gleiche
    Konstruktion: S2−S1 = **−9,9 pp** (35,21 gegen 45,11). Die
    F&G<30-Tage wirken als Verstärker der jeweiligen Jahresdrift —
    nach derselben Konvention, mit der E2 den Timing-Beitrag und F2d
    instabile Features verworfen hat (Vorzeichenwechsel = Rauschen),
    ist auch das kein Vorteil. Zwei Jahresfenster desselben Zyklus
    genügen nicht, um Drift-Beta von Können zu trennen: für die
    Anlage-These „nach Angst kaufen und 30 Tage halten" ist das
    Ergebnis NICHT ENTSCHEIDBAR, für den Bot-Einstieg als Signal ist
    es negativ. [SICHER für die Zahlen]
45. **Zensierung ist unkritisch, die nominelle Fallzahl nicht.**
    Zensierte Rennen: 0,3–3,0 % über alle Kombinationen; die Schranken
    „Zensierte als Verlierer/Gewinner" verschieben P(auf) um < 1,8 pp
    und ändern kein Urteil. Die eigentliche Schwäche der langen
    Kombinationen: 1514 (J2) bzw. 797 (J1) Rennen überlappen sich in
    maximal 12 unabhängigen 30-Tage-Fenstern je Jahr; die
    Bootstrap-KIs (±7 pp J2, ±11 pp J1) sind entsprechend breit und
    eher noch zu schmal, weil Tage innerhalb eines Fensters gekoppelt
    sind. [SICHER]

## Offene Lücken

- F&G nur als Tageswert — Intraday-Verhalten seit E1 offen, nur mit
  archivierten Live-Logs messbar.
- Survivorship: getestet wurden die 11 heute gelisteten Coins —
  NICHT ENTSCHEIDBAR.
- Zwei Jahresfenster desselben Zyklus, nicht unabhängig; J1 nur 43
  Einstiegstage.
- Break-even-Schwelle des echten Ausstiegssystems nicht gerechnet.
- Bootstrap resampelt Tage bei gegebenem Kurspfad, nicht alternative
  Marktpfade.
- **Die realen Binance-Konditionen des Kontos sind nirgends im Projekt
  hinterlegt.** `backtest/fees.py:9` ist eine abgeschriebene
  Standardtabelle ohne Datum und ohne Kontobezug; VIP-Stufe,
  BNB-Guthaben, laufende Gebührenaktionen für USDC-Paare — nichts davon
  steht im Repository. F1b vergleicht Code gegen Code, nicht Code gegen
  Wirklichkeit. Ob 0,10 %/0,10 % stimmt: **NICHT ENTSCHEIDBAR** ohne
  einen Blick in den echten Gebührenbericht des Kontos.
- Die Slippage je Einzeltrade ist nicht protokolliert
  (`ExecutionResult.slippage_pct` wird gesetzt, aber nicht ins Journal
  geschrieben). F1e rechnet mit dem Erwartungswert 0,05 % und gibt die
  Spanne 0,02/0,08 % an — die exakte Ist-Reibung des Live-Laufs bleibt
  unbekannt.
- Die Füllquote in F1e ist eine **Berührungsquote**. Warteschlangen-
  position, Teilfüllung, Ordergröße gegen Orderbuchtiefe und das
  Verhalten unter Stress sind nicht abgebildet — nur die Obergrenze.
- Der Feature-Screen misst **univariate** Rangkorrelation gegen die
  Rendite über feste Horizonte. Wechselwirkungen, Nichtlinearitäten,
  bedingte Effekte (Feature nur in einem Regime) und der Zusammenhang
  mit dem First-Touch-Barrierentest aus E2 sind damit **nicht**
  ausgeschlossen: NICHT ENTSCHEIDBAR.
- F&G geht als Tageswert in den Screen ein, wie schon in E1/E2. Der
  Intraday-Verlauf fehlt weiterhin.
- Die 1h-Befunde in F2 können Mikrostruktur sein (Geld-Brief-Sprung in
  den aus 15m aggregierten Schlusskursen) statt eines handelbaren
  Effekts. Ohne Tick- oder Orderbuchdaten: NICHT ENTSCHEIDBAR — und
  praktisch ohne Belang, weil die 1h-Bewegung die Kosten ohnehin nicht
  trägt (Befund 23).
- F3 vergleicht Endwerte, nicht risikobereinigte Größen. Der Bot war nie
  voll investiert; ein Vergleich bei gleicher Kapitalbindung ist nicht
  gerechnet.
