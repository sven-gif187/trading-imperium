# GATE 1 — FORMELLER ABSCHLUSS

**Datum: 30.07.2026 · Register v1.0 + v1.1 §2 + v1.2 (alle eingefroren
und freigegeben) · Trial-Zähler: T-030, Budget 15 erschöpft**

---

# GATE 1: NEGATIV

Kein Trial der Batterie erfüllt alle Registerkriterien. Dies ist das
**erste von zwei negativen Gates** nach Regel 13. Ein zweites negatives
Gate beendet das Programm mit dem Ergebnis „mit unseren Mitteln nicht
erreichbar".

Das negative Ergebnis ist nach der Programmdefinition ein **zulässiges
und vollwertiges Resultat**, kein Fehlschlag der Durchführung.

---

## 1. Alle 15 Trials mit finalem Status

| Trial | Hypothese / Regel | Asset | n | Status final (v1.2) | Grund |
|---|---|---|---|---|---|
| T-016 | H1 R1 Faber 10M-SMA | BTC | 4 Runden | INCONCLUSIVE | n < 12 |
| T-017 | H1 R1 Faber 10M-SMA | ETH | 8 Runden | INCONCLUSIVE | n < 12 |
| T-018 | H1 R2 MOP 12M-Momentum | BTC | 4 Runden | INCONCLUSIVE | n < 12 |
| T-019 | H1 R2 MOP 12M-Momentum | ETH | 5 Runden | INCONCLUSIVE | n < 12 |
| T-020 | H1 R3 Donchian 20/10 | BTC | 28 Runden | **REJECTED** | v1.2 Klausel A: S-C +0,504 % < 0,60 % |
| T-021 | H1 R3 Donchian 20/10 | ETH | 30 Runden | **REJECTED** | v1.2 Klausel A: S-C +0,157 % < 0,60 % |
| T-022 | H1 R1 Faber | Portfolio | 50 Runden | **REJECTED** | Segment S-A −13,68 %; zudem sekundär (Klausel B) |
| T-023 | H1 R2 MOP | Portfolio | 36 Runden | **REJECTED** | Segment S-A −9,49 %, Placebo verfehlt; sekundär |
| T-024 | H1 R3 Donchian | Portfolio | 248 Runden | **REJECTED** | v1.2 Klausel B: sekundärer Trial trägt Gate 1 nicht allein (§2) |
| T-025 | H2 E-neg Funding | BTC | 30 Events | **REJECTED** | Placebo (vol-gematcht) nicht geschlagen |
| T-026 | H2 E-neg Funding | ETH | 25 Events | INCONCLUSIVE | n < 30 |
| T-027 | H2 E-pos Funding | BTC | 16 Events | INCONCLUSIVE | n < 30 |
| T-028 | H2 E-pos Funding | ETH | 18 Events | INCONCLUSIVE | n < 30 |
| T-029 | H3 Cross-Sectional | — | — | **NICHT AUSGEFÜHRT, formal abgeschlossen** | Universum 12 < 30, N_eff-Bedingung nicht erfüllt (§3) |
| T-030 | H4 Dollar-Overlay | Portfolio | — | **REJECTED** | Calmar-Differenz +0,036, KI [−1,476; +0,802] enthält 0; EV −4,48 bp/Tag signifikant negativ |

**Bilanz: 0 CONFIRMED · 7 REJECTED · 7 INCONCLUSIVE · 1 nicht ausgeführt.**
Verbrauchte Trials: 14 (T-016…T-028, T-030). T-029 unverbraucht und
formal abgeschlossen.

## 2. Begründung für T-024 — der einzige formale Überlebender vor v1.2

T-024 (R3 Donchian, 12er-Portfolio) bestand als einziger Trial das
verschärfte Segment-Kriterium aus Klausel A in allen drei Segmenten
(+3,678 % / +58,821 % / +7,890 %). Er wird durch **Klausel B**
verworfen. Der Survivorship-Befund aus `08_NEUBEWERTUNG-v1.2.md` §3.2
wird hier wörtlich übernommen:

> ### Der S-C-Wert stammt vollständig aus survivorship-selektierten Alts
>
> Zerlegung von T-024, Segment S-C (2022–2023), netto je Runde:
>
> | Gruppe | EV je Runde | n |
> |---|---|---|
> | **BTC + ETH** (längste, am wenigsten selektierte Historie) | **+0,331 %** | 22 |
> | **10 Alts** (heutige Überlebende) | **+9,780 %** | 88 |
>
> Je Coin in S-C: AVAX +52,04 %, NEAR +26,12 %, SOL +23,06 %, ADA
> +6,88 %, UNI +5,96 %, DOT +2,69 %, LINK +2,21 % — und negativ: DOGE
> −1,44 %, ATOM −2,26 %, XRP −4,91 %, plus BTC +0,50 % / ETH +0,16 %.
>
> Die Coins mit den größten S-C-Beiträgen sind genau jene mit starker
> 2023er-Erholung, die bis 2026 gelistet blieben. **Das ist die Signatur
> von Survivorship, nicht die einer Regel.** Ein Universum, das 2022 aus
> damaliger Sicht gewählt worden wäre, hätte auch die enthalten, die
> nicht zurückkamen — die fehlen in unseren Daten vollständig.

Ergänzend: T-024 enthält BTC und ETH, deren primäre Einzeltrials
(T-020/T-021) unter Klausel A durchgefallen sind. Der Portfolio-Trial ist
damit keine unabhängige Bestätigung, sondern eine Umgruppierung, die zwei
Fehlschläge mit zehn selektierten Alts mischt. Zwei der drei
Segment-Konfidenzintervalle enthalten zudem die Schwelle 0,60 %
(S-A [−4,381; +13,541], S-C [−0,455; +18,660]).

## 3. T-029 (H3) — Status

**Formal mit Gate 1 abgeschlossen, nicht als erledigt.** Der Trial wurde
nie ausgeführt, weil die Registerbedingung (Universum ≥ 30 handelbare und
historisierte Coins, N_eff ≥ 5) mit 12 Coins nicht erfüllt war.

Festlegung des Eigentümers vom 30.07.2026: H3 **gehört in eine etwaige
neu-registrierte zweite Runde**, mit vorregistriertem,
delisting-behandeltem Universum ab 30 Coins. Keine Fortsetzung in dieser
Runde. Der Trial gilt als nicht verbraucht; das Budget dieser Runde ist
mit 14 verbrauchten Trials abgeschlossen.

## 4. Was Gate 1 nicht bedeutet

- Es bedeutet **nicht**, dass R3 Donchian wertlos ist. Auf dem gesamten
  Entwicklungszeitraum schlug die Regel BTC-Halten (Calmar 1,08 gegen
  0,52; MaxDD 55,1 % gegen 83,2 %). Sie fällt an Klausel A, weil dieser
  Vorteil im jüngsten Segment (2022–2023) verschwunden ist.
- Es bedeutet **nicht**, dass keine der INCONCLUSIVE-Hypothesen tragen
  könnte. Sieben Trials scheiterten an zu kleiner Stichprobe, nicht an
  gemessener Wirkungslosigkeit. Mehr Historie oder mehr Assets könnten
  sie entscheidbar machen — das wäre Gegenstand einer zweiten Runde.
- Es bedeutet, dass **keine Regel den vorab festgelegten Nachweis
  erbracht hat**, und dass nach Regel 8/9 kein Forward-Paper und kein
  Live-Kapital folgt.

## 5. Nächste Schritte

Kein Gate 2. Kein Forward-Paper. Kein Limit-Order-Pfad (nach
`07_GATE-1-BEFUND.md` §2 ohnehin wirtschaftlich bedeutungslos). Keine
Börsenmigration. Der Bot bleibt im Leerlauf, unangetastet.

Offen und **ausschließlich gemeinsam zu entscheiden** (Regel 13): ob eine
zweite, neu-registrierte Runde stattfindet. Einschätzung und Vorschlag in
`10_ZWEITE-RUNDE-EINSCHAETZUNG.md`.
