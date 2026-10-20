# Spread-Messung — Annahme durch Messwert ersetzt

**31.07.2026 · Quelle: Live-Capture Bybit EU (`api.bybit.eu` v5/market/tickers)
· 145–148 Messpunkte je Coin · KEIN Trial, Zähler bleibt T-033**

Reproduktion: `python kosten_matrix_v3.py`, Rohausgabe
`ausgaben/kosten_matrix_v3_out.txt`.

---

## 1. Das Ergebnis in einem Satz

**Die pauschale Slippage-Annahme von 5 bp je Seite war in beide Richtungen
falsch** — für BTC/ETH um zwei Größenordnungen zu konservativ, für
DOT/ATOM um das Fünf- bis Sechsfache zu optimistisch.

## 2. Gemessene Spreads (Basispunkte)

| Coin | n | min | **Median** | p90 | max | Median in % |
|---|---|---|---|---|---|---|
| ETH | 148 | 0,053 | **0,054** | 5,007 | 10,719 | 0,0005 % |
| BTC | 148 | 0,016 | **0,118** | 4,319 | 11,945 | 0,0012 % |
| SOL | 147 | 1,358 | 1,366 | 2,742 | 5,480 | 0,0137 % |
| DOGE | 147 | 1,430 | 1,441 | 4,317 | 15,812 | 0,0144 % |
| ADA | 146 | 5,843 | 5,954 | 17,610 | 23,809 | 0,0595 % |
| XRP | 145 | 1,883 | 6,591 | 11,182 | 13,945 | 0,0659 % |
| LINK | 147 | 4,849 | 12,105 | 14,533 | 19,773 | 0,1211 % |
| AVAX | 146 | 1,551 | 12,372 | 17,207 | 34,050 | 0,1237 % |
| UNI | 145 | 6,841 | 16,519 | 30,118 | 45,548 | 0,1652 % |
| NEAR | 145 | 11,883 | 18,276 | 26,680 | 36,585 | 0,1828 % |
| ATOM | 145 | 32,310 | **56,887** | 64,746 | 73,201 | 0,5689 % |
| DOT | 147 | 39,500 | **65,232** | 66,094 | 79,470 | 0,6523 % |

**Spanne Median: Faktor 1208 zwischen ETH und DOT.** Die ursprüngliche
Vermutung „DOGE ist 90× weiter als BTC" war eine Untertreibung — DOGE ist
nur 12× weiter als BTC, aber DOT ist 553× weiter.

## 3. Neue Kosten je Coin

`slippage_je_seite = median(spread_bp) / 2 / 100` — eine Market-Order
zahlt gegenüber der Mitte den halben Spread.
`K-BASIS = 2 × 0,25 % Taker + 2 × slippage_je_seite`

| Coin | Slip/Seite | **K-BASIS neu** | alt | Δ | p_be ±5 % | ±7 % | ±10 % |
|---|---|---|---|---|---|---|---|
| ETH | 0,0003 % | **0,5005 %** | 0,60 % | −0,0995 | 55,01 % | 53,58 % | 52,50 % |
| BTC | 0,0006 % | **0,5012 %** | 0,60 % | −0,0988 | 55,01 % | 53,58 % | 52,51 % |
| SOL | 0,0068 % | 0,5137 % | 0,60 % | −0,0863 | 55,14 % | 53,67 % | 52,57 % |
| DOGE | 0,0072 % | 0,5144 % | 0,60 % | −0,0856 | 55,14 % | 53,67 % | 52,57 % |
| ADA | 0,0298 % | 0,5595 % | 0,60 % | −0,0405 | 55,60 % | 54,00 % | 52,80 % |
| XRP | 0,0330 % | 0,5659 % | 0,60 % | −0,0341 | 55,66 % | 54,04 % | 52,83 % |
| LINK | 0,0605 % | 0,6211 % | 0,60 % | +0,0211 | 56,21 % | 54,44 % | 53,11 % |
| AVAX | 0,0619 % | 0,6237 % | 0,60 % | +0,0237 | 56,24 % | 54,46 % | 53,12 % |
| UNI | 0,0826 % | 0,6652 % | 0,60 % | +0,0652 | 56,65 % | 54,75 % | 53,33 % |
| NEAR | 0,0914 % | 0,6828 % | 0,60 % | +0,0828 | 56,83 % | 54,88 % | 53,41 % |
| ATOM | 0,2844 % | **1,0689 %** | 0,60 % | +0,4689 | 60,69 % | 57,63 % | 55,34 % |
| DOT | 0,3262 % | **1,1523 %** | 0,60 % | +0,5523 | 61,52 % | 58,23 % | 55,76 % |

**6 Coins günstiger, 6 teurer.** K-BASIS-Spanne 0,50 % bis 1,15 % —
Faktor 2,30. **Eine einheitliche Kostenzahl über alle Coins ist damit
hinfällig.**

**K-MAKER bleibt bei 0,26 % und ist bewusst nicht coinabhängig:** Eine
Limit-Order zahlt keinen Spread. Der Adverse-Selection-Abschlag von
0,03 % je Trade stammt aus der F1e-Messung und ist von der Buchbreite
unabhängig. Nebenfolge: **für DOT und ATOM wäre der Limit-Pfad ein
Kostenvorteil von Faktor 4,4** (1,15 % → 0,26 %) — bei BTC/ETH nur
Faktor 1,9.

## 4. Rückwirkung auf die gefällten Urteile — keine

Klausel A verlangt Netto-EV je Segment > K-BASIS. Das kritische Segment
war S-C:

| Trial | S-C alt | Korrektur | S-C neu | Schwelle | Urteil |
|---|---|---|---|---|---|
| T-031 BTC | −0,855 % | +0,0988 | **−0,756 %** | 0,5012 % | **fällt** |
| T-032 ETH | −0,173 % | +0,0995 | **−0,074 %** | 0,5005 % | **fällt** |

**GATE-2-VERDIKT UNVERÄNDERT NEGATIV.** Die günstigeren Kosten heben die
S-C-Werte, aber nicht über die Schwelle — beide bleiben negativ, während
die Schwelle bei +0,50 % liegt.

Für T-033 (12er-Portfolio) wirkt die Messung **gegen** den Trial: DOT,
ATOM, NEAR und UNI liegen deutlich über der alten Annahme und senken den
Portfolio-EV zusätzlich. Der ohnehin verworfene Trial wird dadurch nicht
besser.

## 5. Was das für die Börsenmatrix bedeutet

Die Matrix v2 nannte für Bybit EU pauschal 56,00 % nötige Trefferquote
bei ±5 %. Korrekt ist eine **Spanne von 55,01 % (BTC/ETH) bis 61,52 %
(DOT)**. Der Vergleich mit Bitvavo und Kraken bleibt davon unberührt,
solange dort keine Messung vorliegt — deren Spread-Annahmen sind weiterhin
[UNGEKLÄRT], und ein Vergleich gemessener gegen angenommene Werte wäre
irreführend. **Die Rangfolge der Matrix v2 wird deshalb nicht geändert**,
nur die Bybit-Zeile um die coinweise Spanne ergänzt.

## 6. Vorbehalt — ausdrücklich

**Das ist eine Momentaufnahme, keine Verteilung.** 145–148 Punkte aus
einem einzigen Tag (31.07.2026, ca. 5,5 h), unterbrochen von drei
Ausfallphasen zwischen 12:16 und 13:22 UTC. Die Definition of Done des
Capture lautet **7 Tage lückenlos**; erst dann sind diese Zahlen
belastbar. Bis dahin: **[WAHRSCHEINLICH], nicht [SICHER].**

Der Median ist gegen die Ausfallphasen robuster als das Mittel und wird
deshalb verwendet. p90 und max sind mitgeführt, weil sie zeigen, wie weit
die Spreads in Stressmomenten aufgehen — bei BTC vom Median 0,118 bp auf
11,9 bp im Maximum, also **Faktor 100**. Wer mit dem Median rechnet,
rechnet mit dem ruhigen Markt.

**Nicht gemessen:** die Buchtiefe. Die Annahme „Market-Order zahlt den
halben Spread" gilt nur, solange die Order im Top-of-Book Platz findet.
Bei 25–100 $ Ordergröße ist das plausibel, aber ungeprüft — die
Orderbuch-Reihe des Capture liegt vor und ist separat auszuwerten.
