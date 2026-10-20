# Börsen- und Quote-Asset-Entscheidung — Vorlage zur Freigabe

Stand 30.07.2026. Konfidenz-Tags: [SICHER] offiziell/technisch direkt
belegt · [WAHRSCHEINLICH] gute Evidenz, kontospezifisch zu prüfen ·
[UNGEKLÄRT] nur per Konto/Support klärbar. Keine Umstellung erfolgt.

## Zentrale Vorab-Erkenntnis: USDT ist auf EU-Börsen tot

Tether hat keine MiCA-Zulassung; lizenzierte EU-CASPs haben USDT-Paare
für EEA-Kunden entfernt (Kraken bis 31.03.2025 [WAHRSCHEINLICH, offizieller
Support-Artikel], Binance EEA analog). **Direkt verifiziert per
Bybit-EU-API (api.bybit.eu, 30.07.2026): 133 Spot-Paare im Status
Trading — 111 × USDC, 18 × EUR, 4 × PLN, 0 × USDT [SICHER].** Alle 12
Projekt-Coins (BTC, ETH, SOL, ADA, AVAX, LINK, DOT, DOGE, NEAR, UNI,
ATOM, XRP) sind als USDC-Paar vorhanden [SICHER].

⇒ Die USDT-Arbeitshypothese ist als **Handels**-Quote widerlegt. USDT
bleibt reine **Datenhistorien**-Quote (Binance-Archiv als Preis-Proxy);
Basis USDC/USDT liegt im Normalfall bei wenigen Basispunkten
[WAHRSCHEINLICH] und wird im Kostenmodell von der Slippage-Komponente
abgedeckt.

## Kandidaten

### Bybit EU (Bybit EU GmbH, Wien)
- MiCA-CASP durch FMA Österreich, Zulassung 28.05.2025, ESMA-Register,
  LEI 5299005V5GBSN2A4C303 [SICHER — FMA-Veröffentlichung]. Quellen:
  fma.gv.at „Granting of Authorisation Bybit EU GmbH"; AMF-Whitelist.
- Deutschland-Zugang: EEA-Neukunden werden auf bybit.eu geleitet
  [WAHRSCHEINLICH].
- Spot-Gebühren Standard: 0,10 % Maker / 0,10 % Taker [WAHRSCHEINLICH —
  Bybit-Hilfeseiten; es existiert eine Ankündigung „Upcoming Spot Taker
  Fee Changes" auf announcements.bybit.eu, Abruf scheiterte technisch:
  **UNGEKLÄRT, vor Kontoeröffnung prüfen**].
- Paare: 111 USDC-Spot-Paare [SICHER] — deckt 30–60er-Universum.
- Liquidität: global tief; ob das EU-Orderbuch mit dem globalen geteilt
  oder separat (dünner) ist: **UNGEKLÄRT — messbar erst per Live-Capture**.
- API: v5 REST + WebSocket, öffentliche Endpunkte ohne Key erreichbar
  (api.bybit.eu getestet, HTTP 200) [SICHER]; Klines/Orderbuch/Trades
  öffentlich; ccxt-Support `bybit` vorhanden und **bereits in beiden
  ex_maps des Bots** [SICHER].
- SEPA-Einzahlung EUR: angeboten; Kostenfreiheit [UNGEKLÄRT].
- Gegenpartei: EU-Entität jung (2025), globale Gruppe seit 2018;
  1,4-Mrd-Hack 2025 (ByBit-Cold-Wallet-Vorfall) wurde erstattet
  [WAHRSCHEINLICH] — Restrisiko dokumentiert; Paper-First mildert.

### Bitvavo (Amsterdam)
- MiCA-CASP durch AFM (NL), Juni 2025 [WAHRSCHEINLICH — offizieller
  Support-Artikel/ESMA].
- Gebühren Basis: 0,15 % Maker / 0,25 % Taker [WAHRSCHEINLICH — offizielle
  Gebührenseite war technisch nicht abrufbar (403), Sekundärquellen
  konsistent].
- **Nur EUR-Quote** [WAHRSCHEINLICH] ⇒ FX-Mismatch: Signale werden auf
  USD(T)-Historie entwickelt, gehandelt würde EUR-Paar — EUR/USD-Drift
  wandert in jede Messung. ~300 Assets, EUR-Bücher dünner als USD-Bücher
  großer Börsen [VERMUTUNG→UNGEKLÄRT je Paar].
- API: REST + WS, ccxt `bitvavo` vorhanden, aber NICHT in den ex_maps des
  Bots (Adapter nötig) [SICHER für ex_map-Fehlen].
- SEPA kostenlos [WAHRSCHEINLICH].

### Bitpanda (Wien)
- MiCA-Lizenzen (BaFin/FMA/MFSA) [WAHRSCHEINLICH]. Aber: Broker-Modell
  mit Spread ~0,99–1,49 % je Seite [WAHRSCHEINLICH] ⇒ Runde 2–3 %.
  Break-even bei ±5 % wäre 70–80 % Trefferquote — **strukturell
  disqualifiziert für systematisches Trading**. „Fusion"
  (0,25 %-Start) ist ein separates Produkt mit eigener, ungeklärter
  API-Lage [UNGEKLÄRT]. Keine weitere Betrachtung als Primärkandidat.

### Kraken (Payward Europe Solutions Ltd., Irland) — ergänzter Kandidat
- MiCA-CASP durch Central Bank of Ireland, 25.06.2025 [WAHRSCHEINLICH —
  offizielle Pressemitteilung/ESMA]; USDT in EEA delistet [WAHRSCHEINLICH].
- Kraken-Pro-Gebühren Einstiegsstufe: 0,25 % Maker / 0,40 % Taker
  [WAHRSCHEINLICH — offizielle Gebührenseite nicht abgerufen].
- EUR- und USD/USDC-Paare; solide API, ccxt `kraken` in ex_map vorhanden;
  OHLC-Historie via API auf ~720 Kerzen begrenzt [WAHRSCHEINLICH] —
  als Datenquelle schwach, als Handelsplatz ok.
- Gegenpartei: älteste Historie (2011), guter Sicherheitsruf.

## KORREKTUR 30.07.2026 — Gebührenbasis Bybit EU war falsch

Die Erstfassung dieses Dokuments unterstellte Bybit EU Maker 0,10 % /
Taker 0,10 %. Der Eigentümer hat die offizielle Gebührenseite direkt
geprüft (bybit.eu Help-Center „Bybit Spot Fees Explained", Stand
08.03.2026): **Maker 0,10 % / Taker 0,25 %** [SICHER]. Die in der
Erstfassung als UNGEKLÄRT markierte Taker-Änderungsankündigung war real
und material. Eigene Nachprüfung scheiterte dreimal technisch
(Timeout/ECONNRESET). Alle Zahlen unten sind neu gerechnet
(`code/kosten_matrix_v2.py`).

Nebenbefund: `ccxt.bybit().fees['trading']` meldet maker 0,01 % /
taker 0,075 % — für EU-Spot falsch, darf nie als Gebührenquelle dienen.

## Nötige Trefferquote je Börse (entscheidungsrelevant, v2)

p_be = 0,5 + c/(2B). Einheitliche Konvention für Vergleichbarkeit:
Taker-Pfad + 0,05 % Slippage je Seite (Majors); Maker-Pfad ohne
Slippage, aber mit 0,03 % Adverse Selection je Trade (Mittelwert des in
F1e **gemessenen** Bereichs 0,019–0,041 %). Slippage-Annahmen bis zur
Live-Capture-Messung: [UNGEKLÄRT].

### NACHTRAG 31.07.2026 — Bybit-Zeile durch Messung ersetzt

Die Slippage-Annahme von 0,05 % je Seite ist für Bybit EU **gemessen**
worden (Live-Capture, 145–148 Punkte je Coin; `12_SPREAD-MESSUNG.md`).
Sie war in beide Richtungen falsch. Statt eines Pauschalwerts gilt für
Bybit EU eine **coinweise Spanne**:

| Bybit EU, Taker-Pfad | c je Runde | ±5 % | ±7 % | ±10 % |
|---|---|---|---|---|
| **BTC / ETH** (Median-Spread 0,05–0,12 bp) | **0,50 %** | **55,01 %** | **53,58 %** | **52,50 %** |
| SOL / DOGE / ADA / XRP | 0,51–0,57 % | 55,1–55,7 % | 53,7–54,0 % | 52,6–52,8 % |
| LINK / AVAX / UNI / NEAR | 0,62–0,68 % | 56,2–56,8 % | 54,4–54,9 % | 53,1–53,4 % |
| **ATOM / DOT** (Median-Spread 57–65 bp) | **1,07–1,15 %** | **60,7–61,5 %** | **57,6–58,2 %** | **55,3–55,8 %** |

K-MAKER bleibt coinunabhängig bei 0,26 % (Limit zahlt keinen Spread).
Für DOT/ATOM wäre der Limit-Pfad damit ein Kostenvorteil von **Faktor
4,4**, für BTC/ETH nur 1,9.

**Die Rangfolge der Matrix v2 wird dadurch NICHT geändert.** Für Bitvavo
und Kraken liegen keine Messungen vor; deren Spread-Annahmen sind
weiterhin [UNGEKLÄRT]. Gemessene gegen angenommene Werte zu vergleichen
wäre irreführend. Die Tabelle unten bleibt daher als
Annahmen-Vergleich stehen; für Bybit EU gilt die Messung oben.

---

| Börse / Pfad | c je Runde | ±5 % | ±7 % | ±10 % |
|---|---|---|---|---|
| **Bybit EU — Taker (ANNAHME, ersetzt s. o.)** | **0,60 %** | **56,00 %** | **54,29 %** | **53,00 %** |
| Bybit EU — Maker (nur mit Limit-Pfad) | 0,26 % | 52,60 % | 51,86 % | 51,30 % |
| **Bitvavo — Taker** | **0,60 %** | **56,00 %** | **54,29 %** | **53,00 %** |
| Bitvavo — Maker | 0,36 % | 53,60 % | 52,57 % | 51,80 % |
| Kraken Pro — Taker | 0,90 % | 59,00 % | 56,43 % | 54,50 % |
| Kraken Pro — Maker | 0,56 % | 55,60 % | 54,00 % | 52,80 % |
| Bitpanda Broker | 2,0–3,0 % | 70–80 % | 64–71 % | 60–65 % |

**Der zentrale neue Befund: Im Taker-Pfad ist Bybit EU exakt gleich teuer
wie Bitvavo (beide 0,60 %).** Der Kostenvorteil von Bybit existiert
ausschließlich im Maker-Pfad (0,26 % gegen 0,36 %) — und der setzt einen
Limit-Order-Pfad voraus, den der Bot nicht hat.

Konservative Variante des Eigentümers (0,125 % Slippage je Seite,
c = 0,75 %): ±5 % → 57,50 %, ±7 % → 55,36 %, ±10 % → 53,75 %. Die
Differenz zu 56,00 % ist rein die Slippage-Annahme, nicht die Gebühr;
beide Werte werden bis zur Messung parallel geführt (Register v1.1:
K-BASIS bzw. K-KONSERVATIV).

## Gewichtete Matrix v2 (0–10; Gewichte laut Auftrag)

Nur der Kosten-Score wurde neu vergeben; alle übrigen Scores unverändert.

| Kriterium (Gewicht) | Bybit EU | Bitvavo | Kraken | Bitpanda |
|---|---|---|---|---|
| Reale Gesamtkosten (25 %) | 6 *(v1: 8)* | 5 | 3 *(v1: 4)* | 1 |
| DE-/EU-Nutzbarkeit (20 %) | 9 | 9 | 9 | 9 |
| API/Bot-Integration (20 %) | 9 | 7 | 7 | 3 |
| Liquidität/Paare (15 %) | 7 | 6 | 7 | 4 |
| Quote-Asset-Eignung (10 %) | 8 | 5 | 7 | 5 |
| Migration/Testbarkeit (5 %) | 9 | 6 | 7 | 2 |
| Gegenpartei-Risiko (5 %) | 6 | 7 | 8 | 8 |
| **Gewichtete Summe v2** | **7,70** | **6,50** | **6,45** | **4,25** |
| *(v1)* | *8,20* | *6,50* | *6,70* | *4,25* |

Kosten-Score-Begründung: Bybit 8→6, weil der Taker-Vorteil vollständig
entfällt und der verbleibende Vorsprung an einer noch nicht existierenden
Limit-Ausführung hängt. Kraken 4→3 (Taker 0,90 % ist das teuerste
ernsthafte Angebot). Bitvavo unverändert 5 — es hat relativ gewonnen,
ohne besser geworden zu sein.

**Rangfolge v2: Bybit EU (7,70) > Bitvavo (6,50) > Kraken (6,45) >
Bitpanda (4,25).** Vorsprung Platz 1 zu Platz 2 schrumpft von 1,50 auf
1,20. Robustheitsprüfung: Auch bei einem Kosten-Gewicht von 75 % (statt
25 %) bleibt Bybit EU vorn (6,57 gegen 5,50) — die Empfehlung wird nicht
von der Kostenschätzung getragen, sondern von API-Integration,
Quote-Asset-Passung und Migrationsaufwand.

## Empfehlung (keine Umstellung, nur Vorlage) — v2 bestätigt

1. **Primär: Bybit EU, Quote USDC** — mit der neuen Auflage, dass der
   Limit-Order-Pfad Voraussetzung für die günstige Kostenbasis ist.
2. Alternative 1: **Kraken** (Maker-lastig gefahren), falls Bybit-EU-
   Kontoprüfung scheitert oder Taker-Fee-Änderung die Kostenbasis kippt.
3. Alternative 2: **Bitvavo** (EUR-Quote, FX-Mismatch dokumentiert
   behandeln), falls Stablecoin-Quote grundsätzlich unerwünscht wird.
4. Bitpanda: ausgeschlossen (Kostenstruktur).

**Kontospezifisch VOR Festlegung zu prüfen (UNGEKLÄRT-Liste):**
aktuelle Bybit-EU-Taker-Gebühr (Ankündigung!), SEPA-Kostenfreiheit,
KYC-Zugang aus Deutschland, tatsächliche Orderbuchtiefe der Ziel-Paare
(→ Live-Capture-Woche 1 als Messung), Mindestordergrößen der USDC-Paare.
