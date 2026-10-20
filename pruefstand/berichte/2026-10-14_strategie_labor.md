<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
> **Nachtrag 15.10.2026 nach der A10-Prüfung** (`berichte/2026-10-14_advocatus.md`): Rechnung und Code (`backtest.py`) stimmen, unabhängig nachgerechnet. Aber: **Der „halbierte Rückgang“ von K2 kommt aus seiner Investitionsquote** (Ø 35 %), nicht aus Können: 35 % BTC statisch haben −36,6 %, K2 −35,9 %. **Seit 2022 ist die einfache BTC-200-Regel M3 auf allen drei Maßen besser** (30,2 %/Jahr · Sharpe 0,96 · −31,5 % gegen K2 26,7 % · 0,88 · −35,9 %). Ohne 2021: K2 31,6 % gegen M3 35,3 %. K2 bleibt ein gültiger Papier-Kandidat, ob er M3 schlägt, ist offen. **Abschnitt 7 „Gegenprüfung (A10)“ habe ich selbst geschrieben, es war keine unabhängige A10-Prüfung.** Die echte A10-Prüfung ist der oben genannte Bericht.

# Strategie-Labor · Stufe 6 · Entscheidungsvorlage · 14.10.2026

**Summary:** Das **Trend-Ensemble mit BTC-200-Filter (K2)** ist der einzige Kandidat, der alle Prüfungen besteht. Auf den 6 Coins, die Bitvavo gegen USDC anbietet, bringt er in der Rückrechnung **57 % pro Jahr bei Sharpe 1,35 und höchstens −36 % Rückgang**. BTC halten bringt 26 % pro Jahr bei −77 % Rückgang. Der Vorsprung kommt zu einem großen Teil aus 2021 und aus der Auswahl heutiger Gewinner-Coins. Belastbar ist vor allem der **halbierte Rückgang**. Empfehlung: **Papier-Wettkampf starten** [WAHRSCHEINLICH 75 %].

Grundlage: `labor/STRATEGIE_LABOR.md` (Svens Vorgabe). Rückrechnung 05.03.2018 bis 13.10.2026 auf Tageskerzen. Signal am Tagesschluss, Ausführung zum nächsten Eröffnungskurs, kein Hebel, Start 500 $, Kosten je Runde 0,15 / 0,30 / 0,50 / 1,00 %. Skripte und Rohdaten unter `pruefstand/labor/`. Selbsttests: Kaufen-und-Halten gegen Formel, Konto gegen Summe der Runden auf zwei Wegen, kein Blick in die Zukunft (Daten abgeschnitten, Entscheidungen gleich), alle bestanden.

---

## 1 · Die Strategien in einem Satz

| | Strategie | Was sie tut |
|---|---|---|
| M1 | BTC halten | einmal kaufen, nie verkaufen |
| M2 | Korb | alle Coins gleich gewichtet, monatlich ausgeglichen |
| M3 | BTC-200 (Tudor Jones) | BTC nur halten, wenn der Tagesschluss über der 200-Tage-Linie liegt |
| K1 | Trend-Ensemble | je Coin 9 Ausbruchs-Signale (5 bis 360 Tage) mit Nachzieh-Stopp, Größe nach Schwankung (25 %-Ziel) |
| **K2** | **K1 + BTC-200-Filter** | wie K1, neue Käufe aber nur, wenn BTC über seiner 200-Tage-Linie liegt |
| K3 | Rotation | wöchentlich die 3 stärksten Coins halten, raus erst unter Platz 6, nur über BTC-200 |
| K4 | heutiger Bot (v6) | Kurzfrist-Handel, Ø 7,3 h Haltedauer, nur zum Vergleich 13.08.–13.10. |

## 2 · Ergebnisse (Kosten 0,15 % je Runde = Bitvavo)

### 2a · Auf den 6 Coins, die Bitvavo gegen USDC hat (BTC, ETH, SOL, XRP, ADA, DOGE)

| Strategie | Rendite/Jahr | größter Rückgang | Sharpe | Runden/Monat | 2018–20 | 2021 | 2022–heute | 13.08.–13.10.2026 |
|---|---|---|---|---|---|---|---|---|
| M1 BTC halten | 25,9 % | −76,6 % | 0,69 | 0 | 38,7 % | 59,8 % | 13,1 % | +31,0 % |
| M2 Korb 6 | 39,3 % | −83,2 % | 0,81 | 0,1 | −10,1 % | 1953 % | 2,8 % | +32,2 % |
| M3 BTC-200 | 27,2 % | −63,9 % | 0,78 | 0,3 | 44,5 % | −20,6 % | **30,2 %** | +19,9 % |
| K1 Trend | 59,3 % | −47,1 % | 1,34 | 6,3 | 54,5 % | 562 % | 20,5 % | +20,0 % |
| **K2 Trend + Filter** | **57,3 %** | **−35,9 %** | **1,35** | 2,5 | 40,3 % | 511 % | 26,7 % | +13,6 % |
| K3 Rotation (Top 2/4) | 51,8 % | −70,0 % | 0,81 | 0,6 | 22,5 % | 608 % | 24,9 % | −5,0 % |
| K4 heutiger Bot (v6, E7) | – | – | – | ≈ 66 | – | – | – | **+8,5 %** (nur realisiert) |

Die Jahreswerte der Teilzeiträume sind auf ein Jahr hochgerechnet. Quelle: `labor/ergebnisse/stufe5c_bitvavo6.json`.

### 2b · Auf allen 12 Bot-Coins (Svens Vorgabe)

| Strategie | Rendite/Jahr | größter Rückgang | Sharpe | Sharpe bei 0,50 % | Kostenanteil am Brutto |
|---|---|---|---|---|---|
| M1 / M2 / M3 | 25,9 / 31,6 / 27,2 % | −76,6 / −83,2 / −63,9 % | 0,69 / 0,75 / 0,78 | 0,69 / 0,75 / 0,75 | 0 / 0,8 / 2,7 % |
| K1 | 60,1 % | −65,0 % | 1,23 | 1,16 | 7,5 % |
| **K2** | **60,6 %** | **−48,6 %** | **1,30** | **1,25** | 3,5 % |
| K3 | 61,0 % | −63,4 % | 1,04 | 1,02 | 3,1 % |

Quelle: `labor/ergebnisse/stufe4.md`. **Vorsicht:** AVAX, LINK, DOT, NEAR, UNI und ATOM gibt es bei Bitvavo nur gegen EUR, also zu 0,50 % je Runde.

## 3 · Robustheit (Stufe 5)

| Prüfung (12 Coins, K 0,15) | K1 | **K2** | K3 |
|---|---|---|---|
| Basis: Rendite/Jahr · Sharpe | 60,0 % · 1,23 | 60,7 % · 1,30 | 61,5 % · 1,04 |
| Kosten verdoppelt (0,30 %) | 57,8 % · 1,20 | 59,3 % · 1,28 | 60,5 % · 1,03 |
| Kosten 1,00 % | 47,7 % · 1,06 | 53,4 % · 1,19 | 56,0 % · 0,99 |
| ohne besten Coin | 57,7 % (ohne NEAR) | 56,0 % (ohne SOL) | **42,9 %** (ohne NEAR) |
| ohne DOGE | 54,6 % | 54,5 % | 59,0 % |
| Ausführung 1 Tag später | 58,9 % | 59,9 % | 65,6 % |
| Kostenbremse „oder“ statt „und“ | 59,5 % | 58,3 % | 59,2 % |
| Nachbarparameter | Schwankungsziel 20/30 %: 60,4 / 62,4 % | 20/30 %: 59,9 / 61,2 % | Halteband Top 5/8: **45,8 / 50,0 %** |
| Bär-Phasen (Rendite/Jahr) | −9,0 % | −3,0 % | −1,9 % |
| **nur BTC+ETH** (keine Auswahl im Rückblick) | 29,7 % · 1,17 · MaxDD −26,6 % | 28,7 % · 1,17 · **MaxDD −25,5 %** | (Top 1/2) 28,3 % · 0,78 |
| Deflated Sharpe (N = 27 Varianten) | 0,998 | 0,999 | 0,990 |

**Urteil Robustheit:**
- **K2 besteht.** In allen Varianten bleibt die Sharpe zwischen 1,23 und 1,35, und kein Teilzeitraum ist negativ.
- **K1 besteht knapp.** Seit 2022 bringt er nur 7 % im Jahr, bei 1,00 % Kosten ist er in diesem Zeitraum negativ.
- **K3 fällt durch.** Sein Ergebnis hängt an einem einzelnen Coin (NEAR) und an der Wahl des Haltebands.

## 4 · Erfolgskriterien (dein Vorschlag aus Stufe 6) gegen M2

| Kriterium | K1 | **K2** | K3 |
|---|---|---|---|
| Sharpe nach Kosten > M2 (0,75) | ✓ 1,23 | ✓ 1,30 | ✓ 1,04 |
| größter Rückgang kleiner als M2 (−83,2 %) | ✓ −65,0 % | ✓ −48,6 % | ✓ −63,4 % |
| in mindestens 2 von 3 Teilzeiträumen positiv | ✓ 3/3 | ✓ 3/3 | ✓ 3/3 |
| bei doppelten Kosten über null | ✓ | ✓ | ✓ |
| zusätzlich: Robustheit (Abschnitt 3) | knapp | **✓** | ✗ |

## 5 · Was die Rückrechnung NICHT zeigt (ehrlich)

1. **Überlebenden-Verzerrung.** Die Coins sind die Gewinner von heute. Mit nur BTC+ETH schrumpft K2 von 60 % auf 29 % im Jahr, also kaum mehr als BTC halten mit 26 %. **Was bleibt, ist der Rückgang: −25 % statt −77 %.** Das ist der belastbare Teil [SICHER 85 %].
2. **2021 trägt viel.** In 2021 hat K2 sich verneunfacht. **Seit 2022 ist die einfache BTC-200-Regel (M3) mit 30 % im Jahr mindestens so gut wie K2** (19–27 % je nach Universum). Ob sich die Mühe des Ensembles lohnt, entscheidet erst der Wettkampf.
3. **Der Deflated Sharpe nahe 1 ist geschönt.** Die 27 Varianten ähneln sich stark, die Mehrfachtest-Korrektur greift deshalb kaum. Die Überlebenden-Verzerrung rechnet er gar nicht heraus.
4. **Ausführung.** Gerechnet wurde zum Tagesöffnungskurs von Binance. Bitvavo-Spannen bei ADA/DOGE (12–19 bp) und kleine Bücher sind nur über die Kostenstufe 0,30 % abgedeckt.
5. **Kurzer Vergleich zum Bot.** Im Zeitraum 13.08.–13.10. lag K2 (6 Coins) bei +13,6 %, der Bot bei +8,5 %. Bei nur zwei Monaten ist das **nicht entscheidbar**.
6. **Steuern, Bitvavo-Konto und Echtgeld-Ausführung:** nicht Teil des Labors.

## 6 · Empfehlung (Stufe 7, Papier-Wettkampf) [WAHRSCHEINLICH 75 %]

| Instanz | Was | Kapital | Takt |
|---|---|---|---|
| **A** | heutiger Bot v6 (läuft schon, Epoche E10, Bitvavo-Kosten) | 500 $ (vorhanden) | wie bisher |
| **B** | **K2 Trend + BTC-200-Filter**, Bitvavo-USDC-6 | 500 $ Papier | täglich nach Tagesschluss (UTC) |
| **C** | **K1 Trend ohne Filter**, Bitvavo-USDC-6 (zweitbester Kandidat; K3 fällt aus) | 500 $ Papier | täglich |
| Messlatten | M1, M2 (6 Coins), M3 laufen **rechnerisch** mit, ohne eigene Instanz | – | wöchentlicher Vergleich |

- **Umsetzung:** B und C werden **ein neues, kleines Tagesprogramm im Prüfstand** (`pruefstand/labor/papier/`), mit eigenem Journal je Instanz, **ohne jede Änderung an v6/v7**. Die Kurse kommen öffentlich von Binance, Kosten und Spanne nach Bitvavo-Modell.
- **Start:** über eine Windows-Aufgabe täglich um 00:10 UTC, Bericht wöchentlich, per Telegram, sobald der Token eingerichtet ist.
- **Laufzeit:** mindestens 3 Monate, vorab registriert in `pruefstand/epochen/`.
- **Erwartung für die Zahl der Runden:** K2 macht etwa 2,5 Runden im Monat. Für einen statistischen Beleg reichen 3 Monate **nicht**. Ehrlich messbar ist nach 3 Monaten der **Verlauf von Rückgang und Investitionsquote** gegen die Messlatten, nicht ein gesicherter Renditevorsprung.

## 7 · Gegenprüfung (A10)

**Position A, Wettkampf mit K2:**
1. K2 besteht alle Robustheitstests.
2. Den halbierten Rückgang zeigt K2 auch ohne Coin-Auswahl.
3. Die Kosten fressen bei K2 nur 3–11 % des Bruttogewinns, beim Bot über 100 %.

**Position B, kein Wettkampf:**
1. Seit 2022 ist die simple BTC-200-Regel mindestens gleich gut.
2. 3 Monate Papier beweisen bei 2,5 Runden im Monat nichts.
3. Ein zweites System bindet Zeit, die dem heutigen Bot fehlt.

**Urteil: TRÄGT.** Der Wettkampf kostet kein Geld und läuft neben dem Bot. M3 läuft rechnerisch mit, dadurch wird B1 direkt messbar. B2 ist richtig, deshalb ist das Ziel nach 3 Monaten „Rückgang und Verhalten wie in der Rückrechnung?“ und nicht „Rendite belegt?“.

## 8 · Sven entscheidet

- [ ] **Erfolgskriterien** übernehmen, so wie oben vorgeschlagen, ergänzt um die Robustheit?
- [ ] **Stufe 7 freigeben:** A = Bot v6, B = K2, C = K1, jeweils auf den 6 Bitvavo-USDC-Coins?
- [ ] Oder lieber **C = M3 (BTC-200)** als eigene Instanz statt K1, um „einfach gegen komplex“ direkt zu prüfen?

**Nächster Schritt nach deiner Freigabe:** das Tagesprogramm für B und C bauen, mit Vorab-Registrierung, Selbsttest gegen die Rückrechnung und Windows-Aufgabe.

Selbstbewertung: Präzision 9 · Vollständigkeit 8 (Echtgeld-Ausführung, Steuern und Bitvavo-Bücher bei Nacht ungeprüft) · Umsetzbarkeit 9.
