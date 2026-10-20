# EXPERIMENT-REGISTER — Forschungsprogramm Pfad B

**Version 1.0 — 30.07.2026 — Status: ZUR FREIGABE VORGELEGT (eingefroren
nach Nutzer-Freigabe; Prüfsumme in REGISTER-PRUEFSUMME.txt).**

Änderungen an diesem Register nur durch neue Version (v1.x) mit
ausdrücklicher Freigabe des Eigentümers (Nutzer). Jede Auswertung gegen
Marktdaten, die eine Handelsregel bewertet, verbraucht eine Trial-Nummer —
auch fehlgeschlagene, verworfene oder „nur mal schauen"-Läufe.

## 0. Erfolgsdefinition des Programms

„Profitabel" heißt NACHWEIS, nicht Betrag:
1. EV je Entscheidung **netto** > 0, Block-Bootstrap-95 %-KI (über
   Kalendertage, 2000 Ziehungen, Seed 20260730) schließt 0 aus.
2. Vorzeichenstabilität über die drei vordefinierten Regime-Segmente
   (S-A 2017-08..2019-12, S-B 2020-01..2021-12, S-C 2022-01..2023-12).
3. MaxDD der Regel < MaxDD von BTC-Halten im selben Zeitraum; Calmar wird
   berichtet, BTC-Halten ist die Messlatte (Regel 12).
4. Endgültiger Beweis NUR per eingefrorener Regel + 90 Tage Forward-Paper
   (Gate 2). Backtest allein beweist nichts (Regel 8).

**Gates:** Gate 1 = Batterie-Verdict (mind. ein Kandidat erfüllt 1–3 im
Entwicklungszeitraum). Gate 2 = Forward-Paper. Zwei negative Gates ⇒
„mit unseren Mitteln nicht erreichbar", Programm-Ende (Regel 13).

## 1. Datengrundlage und Zeiträume

- Kerzen 1d/4h: Binance-Archiv via data-api.binance.vision (USDT-Paare als
  **Preis-Proxy**; Handel später in USDC auf der Zielbörse — Basisrisiko
  USDC/USDT ≈ wenige bp, dokumentiert in 03_DATEN-COVERAGE).
- Funding 8h: fapi.binance.com (öffentlich, ab 2019-09).
- Makro: FRED DTWEXBGS/DTWEXAFEGS als freier DXY-Ersatz
  (**Publikationslag: nur mit ≥ 1 Woche Verzögerung verwenden**).
- **Entwicklungszeitraum:** 2017-08-17..2023-12-31.
- **Kontaminiert:** 2024-01-01..2026-07-30 (mehrfach beforscht in E1–G2).
  Läufe darauf sind Bericht, NIE Beweis (Regel 7).
- **Beweiszeitraum:** Forward-Paper ab Einfrieren, ≥ 90 Tage.

## 2. Kostenmodell (Regel 10/11)

- **Basis:** Taker 0,10 % je Seite + 0,05 % Spread/Slippage je Seite ⇒
  **c = 0,30 % je Runde**. Sensitivität: c = 0,50 % (Alts/dünne Bücher)
  und c = 0,15 % (Maker-Best-Case) — Maker-Szenario nur nachrichtlich,
  mit F1e-Fill-Quoten (79–99 %) und Adverse-Selection-Abschlag
  0,02–0,04 % je Trade (messung_f1e_maker_out.txt).
- Ausführung: Signal am Tagesschluss UTC, Ausführung zum **nächsten
  Tages-Open**. Kein Fill am Signalbalken (Look-ahead-Sperre).

## 3. Hypothesen

### H1 — Zeitreihen-Trend Long/Flat (Priorität 1)

- **Hypothese:** Ein niederfrequentes Long/Flat-Trendsignal auf BTC/ETH
  erwirtschaftet netto EV > 0 je Runde und reduziert MaxDD gegenüber Halten.
- **Ökonomische Begründung:** Verhaltensbasierte Unter-/Überreaktion und
  Herding — dokumentiert Jahrzehnte vor Krypto in Aktien, Renten,
  Rohstoffen, FX.
- **Regeln (Regel 14 — Quellen vor 2015, andere Anlageklassen, Parameter
  wörtlich aus der Quelle, KEINE Krypto-Ableitung):**
  - **R1:** Monatsschluss > 10-Monats-SMA ⇒ long, sonst flat.
    Quelle: M. Faber, „A Quantitative Approach to Tactical Asset
    Allocation", Journal of Wealth Management, **2007** (US-Aktien,
    Renten, Rohstoffe, REITs, FX; Daten ab 1900).
  - **R2:** Vorzeichen der 12-Monats-Rendite, monatliche Anpassung ⇒
    long wenn > 0, sonst flat. Quelle: Moskowitz/Ooi/Pedersen, „Time
    Series Momentum", Journal of Financial Economics, **2012**
    (58 Futures-Märkte 1965–2009).
  - **R3:** Einstieg bei 20-Tage-Hoch, Ausstieg bei 10-Tage-Tief
    (Donchian-Kanal). Quelle: R. Donchian, 4-Wochen-Regel (**1960er**,
    Rohstoffe); Systemvergleich Lukac/Brorsen/Irwin, „A Test of Futures
    Market Disequilibrium", **1988**.
- **Erlaubter Parameterraum:** exakt {R1: 10M}, {R2: 12M}, {R3: 20/10}.
  KEINE weiteren Werte. Perturbation ±20 % NUR als nachgelagerter
  Robustheitsbericht, niemals zur Auswahl.
- **Assets:** primär BTCUSDT, ETHUSDT (längste Historie); sekundär
  gleichgewichtetes 12-Coin-Portfolio (ab jeweiligem Listing, Renditen ab
  Listing — kein Rückfüllen).
- **Trials:** T-016..T-021 (R1/R2/R3 × BTC/ETH), T-022..T-024
  (R1/R2/R3 × 12er-Portfolio). **9 Trials.**
- **Erfolg:** Kriterien 0.1–0.3; p-Werte (Bootstrap) über die 9 Trials
  BH-FDR-korrigiert, q = 0,10.
- **Widerlegung:** KI enthält 0 ODER Vorzeichenwechsel zwischen Segmenten
  ODER Placebo nicht geschlagen.
- **Placebo/Robustheit:** (a) 200 zufällige Long/Flat-Masken mit gleicher
  Long-Quote und gleicher mittlerer Blocklänge (Seed 20260730) — Regel
  muss > 95. Perzentil der Placebo-EVs liegen; (b) Ausführungs-Lag +1 Tag
  (Look-ahead-Detektor: Effekt darf nicht kollabieren); (c) Kosten-
  Sensitivität 0,15/0,30/0,50 %.
- **Risiken:** Survivorship klein für BTC/ETH, real für das 12er-Portfolio
  (heutige Überlebende) — Portfolio-Trials daher nur sekundär;
  Data-Snooping-Rest: die Regel-AUSWAHL kennt die Krypto-Geschichte
  (Regel 14 minimiert, eliminiert nicht — ehrlich ausgewiesen).

### H2 — Funding-Extreme als Richtungssignal (Priorität 2)

- **Hypothese:** Extreme Funding-Zustände (überfüllte Long- bzw.
  kapitulierte Positionierung) tragen Richtungsinformation für 3–14 Tage.
- **Begründung:** Funding misst Positionierungs-Überhang; Extreme erzeugen
  Squeeze-/Kapitulationsasymmetrien.
- **Regeln (Schwellen FIX, nicht datengefittet):**
  - **E-neg:** Funding ≤ 0 in 3 aufeinanderfolgenden 8h-Intervallen ⇒
    Long-Ereignis, Halten 7 Tage.
  - **E-pos:** Funding ≥ +0,05 %/8h in 3 aufeinanderfolgenden Intervallen
    ⇒ Kein-Long-/Flat-Ereignis (für Long/Flat: Warnzustand), Horizont 7 Tage.
- **Test:** Event-Study Forward-Renditen 1/3/7/14 d gegen
  volatilitäts-gematchtes Placebo (gleiche Vol-Dezile, zufällige Tage,
  40 Ziehungen) + Block-Bootstrap-KI. Assets: BTC, ETH.
- **Trials:** T-025..T-028 (E-neg/E-pos × BTC/ETH). **4 Trials.**
- **Erfolg/Widerlegung:** wie H1 (KI, Segmente ab 2020, FDR gemeinsam mit
  H1-Familie, q = 0,10). Ereigniszahl < 30 je Trial ⇒ INCONCLUSIVE, nicht
  CONFIRMED.
- **Risiken:** Funding-Historie beginnt 2019/2020 (nur 2 Segmente);
  Methodikwechsel der Börse [UNGEKLÄRT]; Look-ahead durch
  Settlement-Zeitpunkte — Signal erst NACH fundingTime verwenden.

### H3 — Cross-Sectional Momentum (bedingt)

- **Nur wenn** Universum ≥ 30 handelbare-und-historisierte Coins UND
  N_eff ≥ 5 (auf Tagesrenditen 2020–2023, Kovarianz-basiert). Sonst
  dokumentiert NICHT AUSGEFÜHRT.
- **Regel:** 4-Wochen-Rendite-Rang, wöchentlich, long oberstes Quintil
  gleichgewichtet, sonst flat. Quelle: Jegadeesh/Titman 1993 (Aktien,
  vor 2015, andere Anlageklasse).
- **Trial:** T-029. Erfolg/Widerlegung/Placebo wie H1; Survivorship-
  Behandlung: Universum = Schnitt (Bybit-EU-USDC-Paare heute) ∩
  (Binance-Archiv-Historie); diese Konstruktion ist survivorship-belastet
  und wird als solche ausgewiesen — ein CONFIRMED aus H3 allein kann
  Gate 1 nicht tragen.

### H4 — Makro-Overlay (bedingt)

- **Nur nach** positivem H1-Kandidaten (Regel: niemals Rettung eines
  Null-Signals).
- **Regel:** FRED-Dollarindex, 13-Wochen-Änderung > 0 (mit 1 Woche
  Publikationslag) ⇒ Positionsgröße des H1-Kandidaten × 0,5.
- **Trial:** T-030. Erfolg: Calmar-Verbesserung mit Bootstrap-KI > 0;
  EV darf nicht signifikant fallen.

## 4. Globale Trial-Zählung

Historische Trials (rekonstruiert aus docs/messungen_2026-07/, zählen im
Budget):

| T | Lauf | Ergebnis |
|---|---|---|
| T-001 | messung_e1_nachkaufrate | Harness-Abweichung erklärt |
| T-002 | messung_e1_fenster | bestätigt |
| T-003 | messung_e2_stops | kein Stop rettet (REJECTED Exit-These) |
| T-004 | messung_e2_einstieg | Einstieg = Volatilität, keine Richtung |
| T-005 | messung_e2_placebo | kein Vorteil vs. Zufall |
| T-006 | messung_e2_placebo2 | Volatilitätsselektion bestätigt |
| T-007 | messung_e2_phasenplacebo | phasengleich bestätigt, KIs |
| T-008 | messung_e5_universum | kein Coin EV>0, N_eff 1,2–1,4 |
| T-009 | messung_ableitungen | Verlust-Umverteilung |
| T-010 | messung_f1_reibung | Untergrenze 0,150 % |
| T-011 | messung_f1e_maker | Fill-Quoten, Adverse Selection |
| T-012 | messung_f2_ic | 25 Features, kein IC trägt (REJECTED) |
| T-013 | messung_f3_benchmark | BTC-Halten schlägt Bot |
| T-014 | messung_g1_indikatoren | F2 verifiziert |
| T-015 | messung_g2_horizonte | lange Horizonte REJECTED |

Neue Trials: T-016..T-030 wie oben (max. 15). **Trial-Budget der Batterie:
15. Jede Überschreitung erfordert Registerversion v1.x mit Freigabe.**

## 5. Verbotsliste (unverändert verbindlich)

Kein Exit-Tuning, kein ML auf Null-IC-Features, keine offene Suche/
Evolution/LLM-Generierung, keine Parameterexpansion, kein Live vor Gates,
keine Optimierung des alten Signalpfads.

## 6. Offene Entscheidungen des Eigentümers

1. Freigabe dieses Registers (Voraussetzung für Phase 5).
2. Börsen-/Quote-Entscheidung (04_BOERSEN-QUOTE-ENTSCHEIDUNG.md) —
   beeinflusst NUR Kostenannahme-Basis und späteren Forward-Paper-/
   Capture-Ort, nicht die Regeldefinitionen.
3. Bestätigung des 12er-Portfolio-Sekundärtests (T-022..T-024) oder
   Streichung (reduziert Trial-Budget auf 12).
