# GATE 1 — Befund der H1/H2/H4-Batterie

Stand 30.07.2026. Register v1.0 + v1.1 §2 (beide freigegeben).
Trials verbraucht: T-016…T-028 (13) + T-030 (1) = **14**. T-029 (H3)
unverbraucht — Registerbedingung Universum ≥ 30 nicht erfüllt (12 Coins).
Trial-Zähler steht damit bei **T-030, 1 Trial Restbudget**.

Rohausgaben: `ausgaben/batterie_h1_out.txt`, `batterie_h2_out.txt`,
`batterie_h4_out.txt`, `batterie_verdict_out.txt`.
Reproduktion: `python batterie_h1.py` (38 s), `batterie_h2.py` (6 s),
`batterie_h4.py` (11 s), `batterie_verdict.py`.

---

## 1. Formales Ergebnis

**GATE 1: POSITIV — aber mit einer schweren Einschränkung, die den
Befund auf eine einzige Beobachtung reduziert (Abschnitt 4).**

Nach BH-FDR (q = 0,10, m = 13, Schwelle p ≤ 0,0470) bestehen drei Trials
alle Registerkriterien unter K-BASIS:

| Trial | Regel / Asset | EV je Runde K-BASIS | 95 %-KI | Placebo-Rang | Urteil |
|---|---|---|---|---|---|
| T-020 | R3 Donchian 20/10 \| BTC | **+20,79 %** | [+1,51; +52,70] | 99. Perz. | CONFIRMED |
| T-021 | R3 Donchian 20/10 \| ETH | **+19,21 %** | [+1,79; +44,30] | 98. Perz. | CONFIRMED |
| T-024 | R3 Donchian 20/10 \| 12er-Portfolio | **+26,67 %** | [+15,98; +38,40] | 99. Perz. | CONFIRMED |

Alle übrigen: T-022/T-023 REJECTED (Segment-Vorzeichenwechsel, Placebo),
T-025 REJECTED (Placebo), T-016/017/018/019 INCONCLUSIVE (n < 12 Runden),
T-026/027/028 INCONCLUSIVE (n < 30 Events), T-030 REJECTED.

## 2. K-BASIS gegen K-MAKER — die vom Eigentümer verlangte Trennung

**Kein Kandidat hängt am Limit-Pfad.** Die Differenz zwischen K-MAKER
(0,26 %) und K-BASIS (0,60 %) beträgt konstruktionsbedingt exakt 0,34
Prozentpunkte je Runde. Bei EV-Werten von 19–27 % je Runde ist das
**1,3–1,8 % des Effekts** — irrelevant für jedes Urteil.

| Trial | K-MAKER | K-BASIS | K-KONSERVATIV | Differenz Maker↔Basis |
|---|---|---|---|---|
| T-020 | +21,13 % | +20,79 % | +20,64 % | 1,6 % des EV |
| T-021 | +19,55 % | +19,21 % | +19,06 % | 1,8 % des EV |
| T-024 | +27,01 % | +26,67 % | +26,52 % | 1,3 % des EV |
| T-025 (H2, REJECTED) | +3,29 % | +2,95 % | — | 11,5 % des EV |

**Antwort auf die Leitfrage:** Weder „knapp am Limit-Pfad" noch „auch mit
Limit-Pfad tot". Die Kandidaten sind kostenunempfindlich, weil sie
niederfrequent sind (28–30 Runden in 6,4 Jahren ≈ 4,5 Runden/Jahr). Der
Limit-Pfad ist für diese Regelfamilie **wirtschaftlich bedeutungslos** —
er würde den EV um gut ein Prozent seines Betrags heben. Damit entfällt
die Grundlage, ihn zu bauen; die Entscheidung „Exekution bauen" ist für
R3 mit Nein zu beantworten, unabhängig vom weiteren Verlauf.

Umgekehrt zeigt T-025 (H2, verworfen), wie ein kostenempfindlicher
Kandidat aussähe: dort macht der Limit-Pfad 11,5 % des Effekts aus.

## 3. Benchmark (Regel 12) — BTC-Halten im selben Zeitraum

| Asset | Strategie ges. | Halten ges. | CAGR S/H | MaxDD S/H | Calmar S/H |
|---|---|---|---|---|---|
| BTC | +1881 % | +887 % | 59,8 % / 43,2 % | 55,1 % / 83,2 % | **1,08 / 0,52** |
| ETH | +1937 % | +656 % | 60,5 % / 37,3 % | 69,1 % / 94,0 % | **0,88 / 0,40** |

Auf dem Entwicklungszeitraum schlägt R3 das Halten in Rendite **und**
Drawdown, Calmar rund verdoppelt. Das ist das erste Mal im gesamten
Projekt, dass eine Regel die Messlatte aus Regel 12 überspringt (F3:
der alte Bot verlor gegen Halten um 223 $/684 $).

## 4. Warum ich diesen Befund trotzdem für schwach halte

### 4.1 Drei CONFIRMED sind EIN Befund, nicht drei

T-020, T-021 und T-024 testen **dieselbe Regel**; T-024 (Portfolio)
**enthält BTC und ETH**. Die drei Trials sind hochgradig abhängig. Die
BH-FDR behandelt sie als unabhängig und überschätzt die Evidenz dadurch
systematisch. Ehrliche Lesart: **eine unabhängige Beobachtung**, in drei
Schnitten berichtet. Bei 200 Placebo-Ziehungen und einem 5-%-Kriterium
wäre unter reinem Rauschen ~0,65 Zufallstreffer je unabhängigem Test zu
erwarten — wir haben einen Treffer.

### 4.2 Der Effekt ist 2022–2023 verschwunden

Segment-EV je Runde (K-BASIS): S-A/S-B/S-C

- BTC: +18,99 % / +50,69 % / **+0,50 %**
- ETH: +4,85 % / +65,15 % / **+0,16 %**
- Portfolio: +3,68 % / +58,82 % / +7,89 %

Das Registerkriterium verlangt nur „Vorzeichen > 0" — formal erfüllt.
Substanziell ist +0,16 % je Runde nach Kosten **nicht von null
unterscheidbar**. Der gesamte Effekt stammt aus 2017–2021. Genau davor
warnt Regel 14: Trendfolge ist die meistpublizierte Krypto-Strategie
dieses Zeitraums. Dass sie im letzten verfügbaren Segment auf null fällt,
ist das erwartbare Muster einer arbitrierten Anomalie — nicht der
Nachweis einer fortbestehenden Prämie.

**Ich betrachte das Vorzeichen-Kriterium hiermit als zu lasch. Eine
Verschärfung wäre eine Registeränderung (v1.2) und braucht deine
Freigabe — ich nehme sie nicht eigenmächtig vor.**

### 4.3 Segmentweise gegen Halten — der Vorteil ist Drawdown, nicht Rendite

| | S-A | S-B | S-C |
|---|---|---|---|
| BTC Strategie / Halten | +225,5 % / +67,9 % | +533,5 % / **+541,8 %** | −3,9 % / −11,4 % |
| ETH Strategie / Halten | +11,0 % / −57,2 % | +1913,6 % / **+2711,2 %** | −8,9 % / −39,4 % |

Im Bullenmarkt S-B **verliert** die Regel gegen Halten (sie steigt zu
spät ein, aus). Ihr Beitrag liegt in S-A und S-C: weniger Verlust im
Abwärts-/Seitwärtsmarkt. Das ist ein Risikomanagement-Effekt, keine
Prognosefähigkeit — und ökonomisch etwas anderes, als der EV je Runde
suggeriert.

### 4.4 Weitere Vorbehalte

- **Survivorship** im 12er-Portfolio (heutige Überlebende) — T-024 ist
  deshalb der schwächste der drei, nicht der stärkste, obwohl er das
  größte n hat.
- **EV je Runde schmeichelt Long/Flat im Bullenmarkt.** Der einzige
  Schutz dagegen ist der Placebo-Test — und nur er trägt den Befund.
- **Kein Trial ist ein Test auf 2024–2026.** Diese Zeit bleibt gesperrt
  (Regel 7).
- **T-016/T-018 hatten p ≤ 0,047, blieben aber INCONCLUSIVE** (4 Runden).
  Das ist korrekt so: bei n = 4 ist ein Bootstrap-KI Zierde, kein Beweis.

## 5. H2 — Funding: nichts Verwertbares

- T-025 (E-neg BTC, 30 Events): EV netto +2,95 % über 7 Tage, KI > 0 —
  **aber der Placebo (vol-gematcht) liegt bei +5,57 % im 95. Perzentil.**
  Das Signal erzeugt Rendite, indem es in Hochvolatilitätsphasen kauft;
  ein Zufallstag mit gleicher Vola tut das besser. REJECTED.
- T-026/027/028: 16–25 Events, unter der Registerschwelle von 30.
  INCONCLUSIVE, nicht REJECTED.
- Auffällig: T-028 (E-pos ETH) zeigt +5,93 % nach dem Warnsignal — das
  Gegenteil der Hypothese, Rang-p 0,925. Als Vermeidungssignal wäre es
  schädlich gewesen.

## 6. H4 — Dollar-Overlay: verworfen

Calmar 1,81 → 1,85 (Differenz +0,036, KI [−1,476; +0,802] — enthält 0).
MaxDD sinkt 46,9 % → 34,4 %, aber CAGR fällt 85,0 % → 63,6 %, und die
EV-Differenz je Tag ist mit −4,48 bp (KI [−8,99; −0,40]) **signifikant
negativ**. Das Overlay reduziert Risiko und Ertrag im gleichen Verhältnis
— es kauft nichts. REJECTED nach Registerkriterium.

## 7. Empfehlung für den nächsten Schritt

Der Befund ist stark genug, um nicht verworfen zu werden, und zu schwach,
um ihn zu glauben. Die einzige Instanz, die das entscheiden kann, ist
Gate 2 — genau dafür ist es da (Regel 8).

**Vorschlag:** Regel R3 Donchian 20/10 auf BTC und ETH einfrieren,
Long/Flat, Ausführung next-open, Market-Order (Limit-Pfad entfällt nach
Abschnitt 2), und 90 Tage Forward-Paper starten. Vorher: Walk-Forward-
Protokoll auf dem Entwicklungszeitraum als letzte Robustheitsprüfung.

**Erwartungsmanagement, unverändert zu deiner Vorgabe:** In 90 Tagen
fallen bei 4,5 Runden/Jahr je Asset etwa **1–2 Runden** an. Das ist keine
Stichprobe, aus der ein EV-KI etwas beweist. Gate 2 kann in diesem
Zeitraum nur **widerlegen** (grobe Fehlfunktion, Ausführungsprobleme,
Kostenabweichung), nicht bestätigen. Wer einen statistischen Nachweis
will, braucht bei dieser Frequenz Jahre — das ist die unvermeidliche
Kehrseite der Niederfrequenz, die uns die Kosten erst erträglich gemacht
hat. **Diese Spannung ist im Register nicht aufgelöst und muss vor
Gate-2-Start entschieden werden.**
