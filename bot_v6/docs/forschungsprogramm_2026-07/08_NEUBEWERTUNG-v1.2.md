# Neubewertung unter Register v1.2 — verschärftes Segment-Kriterium

Stand 30.07.2026. **Kein neuer Trial** — identische Signale, Runden und
Kosten wie `batterie_h1.py`, geändert wurde ausschließlich die
Urteilsregel. Trial-Zähler unverändert bei T-030, Restbudget 1 (T-029).
Reproduktion: `python neubewertung_v12.py`, Rohausgabe
`ausgaben/neubewertung_v12_out.txt`.

---

## 1. Eine Mehrdeutigkeit im Auftrag — aufgelöst, aber sie muss benannt werden

Die in `batterie_h1_out.txt` berichteten Segmentwerte sind **bereits
netto**, also nach Abzug von K-BASIS (`netto_evs(runden, c) =
brutto − c`, batterie_h1.py). Damit hat „EV je Runde muss die
Kostenschwelle K-BASIS überschreiten" zwei Lesarten:

- **L1 — netto > 0** (⟺ brutto > 0,60 %): das ist exakt das *alte*
  Vorzeichen-Kriterium. Keine Verschärfung.
- **L2 — netto > 0,60 %** (⟺ brutto > 1,20 %): die Runde muss ihre
  Kosten **zweimal** verdienen. Echte Verschärfung.

Du hast 0,504 % und 0,157 % direkt gegen 0,60 % gestellt — das ist L2.
**Ich urteile nach L2.** Zur Kenntnis: L2 verlangt damit implizit einen
Sicherheitsaufschlag in Höhe der vollen Kosten. Das ist verteidigbar,
war aber möglicherweise nicht die bewusste Absicht. Beide Lesarten sind
gerechnet und ausgewiesen.

## 2. Ergebnis der Neubewertung

| Trial | Regel / Asset | v1.1 | **v1.2 (L2)** | Grund |
|---|---|---|---|---|
| T-020 | R3 Donchian \| **BTC** | CONFIRMED | **REJECTED** | S-C +0,504 % < 0,60 % |
| T-021 | R3 Donchian \| **ETH** | CONFIRMED | **REJECTED** | S-C +0,157 % < 0,60 % |
| T-024 | R3 Donchian \| 12er-Portfolio | CONFIRMED | **CONFIRMED** | S-A +3,68 / S-B +58,82 / S-C +7,89 — alle > 0,60 % |

T-016–T-019 bleiben INCONCLUSIVE (n < 12, unverändert), T-022/T-023
bleiben REJECTED. Kontrollrechnung: unter L1 hätten alle drei überlebt,
unter L2 überlebt einer.

**Deine Erwartung trifft für BTC und ETH zu, für das Portfolio nicht.**
T-024 besteht das verschärfte Kriterium in allen drei Segmenten.

## 3. Warum T-024 das Gate trotzdem nicht trägt

### 3.1 Das Register stuft Portfolio-Trials selbst als sekundär ein

v1.0 §3 H1, wörtlich: *„Assets: primär BTCUSDT, ETHUSDT (längste
Historie); sekundär gleichgewichtetes 12-Coin-Portfolio"* und
*„Survivorship … real für das 12er-Portfolio (heutige Überlebende) —
Portfolio-Trials daher nur sekundär"*.

Hier überlebt **ausschließlich der sekundäre Trial, während beide
primären Trials derselben Regel durchfallen.** Nach der Logik, die das
Register für H3 ausdrücklich formuliert (*„ein CONFIRMED aus H3 allein
kann Gate 1 nicht tragen"*), trägt auch ein alleinstehender
Portfolio-Trial Gate 1 nicht. **Diese Konsequenz ist für H1 im Register
nicht ausformuliert — das ist eine echte Lücke und deine Entscheidung,
nicht meine** (Abschnitt 5).

### 3.2 Der S-C-Wert stammt vollständig aus survivorship-selektierten Alts

Zerlegung von T-024, Segment S-C (2022–2023), netto je Runde:

| Gruppe | EV je Runde | n |
|---|---|---|
| **BTC + ETH** (längste, am wenigsten selektierte Historie) | **+0,331 %** | 22 |
| **10 Alts** (heutige Überlebende) | **+9,780 %** | 88 |

Je Coin in S-C: AVAX +52,04 %, NEAR +26,12 %, SOL +23,06 %, ADA +6,88 %,
UNI +5,96 %, DOT +2,69 %, LINK +2,21 % — und negativ: DOGE −1,44 %,
ATOM −2,26 %, XRP −4,91 %, plus BTC +0,50 % / ETH +0,16 %.

Die Coins mit den größten S-C-Beiträgen sind genau jene mit starker
2023er-Erholung, die bis 2026 gelistet blieben. **Das ist die Signatur
von Survivorship, nicht die einer Regel.** Ein Universum, das 2022 aus
damaliger Sicht gewählt worden wäre, hätte auch die enthalten, die nicht
zurückkamen — die fehlen in unseren Daten vollständig.

### 3.3 Das Kriterium wird knapp und mit weitem Intervall bestanden

Segment-KIs von T-024 (2000 Bootstrap, Punktschätzer-Kriterium; KIs sind
Zusatzinformation, kein Urteilsbestandteil):

- S-A +3,678 % — KI [−4,381; +13,541] → **enthält 0,60 %**
- S-B +58,821 % — KI [+34,602; +85,635] → klar darüber
- S-C +7,890 % — KI [−0,455; +18,660] → **enthält 0,60 %**

Zwei von drei Segmenten bestehen nur im Punktschätzer. Bei einem
Kriterium, das gerade verschärft wurde, um Scheinbestehen zu verhindern,
ist das kein belastbares Bestehen.

## 4. Antwort auf deine Fragen 2 und 3

**Frage 2 — bleibt ein CONFIRMED übrig?**
**Formal ja: T-024.** Nach dem Wortlaut von v1.2 (L2) besteht der
Portfolio-Trial alle Segmentschwellen. Ich stelle das so fest, obwohl es
deiner Erwartung widerspricht — die Zahl ist die Zahl.

**Substanziell nein.** Der einzige Überlebende ist der vom Register als
sekundär eingestufte, survivorship-belastete Trial, dessen tragendes
Segment zu 96 % aus Altcoin-Beiträgen besteht, während die beiden
primären Assets derselben Regel durchgefallen sind.

**Frage 3 — zählt das als erstes negatives Gate?**
Nur, wenn du T-024 nach Abschnitt 3.1 als nicht-tragend einstufst. Diese
Entscheidung nehme ich dir nicht ab, weil sie eine Registerlücke schließt
und damit deine Kompetenz ist. Beide Wege sind sauber:

- **Weg A — T-024 trägt nicht** (meine Empfehlung): Gate 1 = **NEGATIV**,
  erstes von zwei negativen Gates nach Regel 13. Ein weiterer,
  neu-registrierter Anlauf bleibt zulässig.
- **Weg B — T-024 trägt:** Gate 1 = positiv, aber der Kandidat wäre ein
  12-Coin-Portfolio-Donchian, dessen Wirkung auf BTC/ETH nachweislich
  fehlt. Ein Forward-Paper darauf würde 90 Tage lang etwas testen, dessen
  Backtest-Vorteil aus nicht reproduzierbarer Coin-Auswahl stammt.

## 5. Was v1.2 formal noch braucht

Die Verschärfung ist bisher nur als Auftrag formuliert. Für die Ablage
fehlt die Festlegung von zwei Punkten:

1. **Lesart L2 als verbindlich** (netto > K-BASIS, nicht netto > 0).
2. **Trägt ein sekundärer Trial Gate 1 allein?** — Vorschlag: Nein,
   analog zur bestehenden H3-Klausel. Ohne diese Festlegung bleibt der
   Gate-1-Status uneindeutig.

Erst mit beiden Punkten kann v1.2 eingefroren und der Gate-Status
protokolliert werden.

## 6. Frage 4 — T-029 (H3): meine Einschätzung

**Empfehlung: mit Gate 1 formal abschließen, nicht offenhalten.** Drei
Gründe, nach Gewicht:

1. **Die Vorbedingung ist vermutlich strukturell unerreichbar.** E5 hat
   N_eff = 1,23–1,42 für 11 Coins gemessen, mittlere Paarkorrelation
   0,72–0,75, in Abwärtsphasen steigend. Eine Erweiterung auf 30–60 Coins
   erhöht N_eff, aber Krypto ist empirisch ein Ein-Faktor-Markt; N_eff ≥ 5
   halte ich für unwahrscheinlich [VERMUTUNG — nicht gemessen, das wäre
   selbst eine Auswertung]. Ein Trial offenzuhalten, dessen Bedingung
   wahrscheinlich nie eintritt, täuscht eine Option vor.
2. **Abschnitt 3.2 hat H3 gerade vorweg beschädigt.** Cross-Sectional
   Momentum auf einem survivorship-selektierten Universum ist exakt die
   Konstruktion, die den T-024-Wert erzeugt hat. H3 würde denselben
   Fehler in reiner Form messen.
3. **Ein offener Rest-Trial in einem sonst erschöpften Budget erzeugt
   genau die „nur noch dieser eine"-Dynamik**, gegen die Regel 13
   geschrieben wurde.

Gegenargument, das ich nicht unterschlage: H3 ist die einzige nie
geprüfte Richtung des Programms, und formales Schließen verkauft
Unwissen als Wissen. Dagegen steht: Regel 13 lässt nach dem ersten
negativen Gate ohnehin **eine** neu-registrierte Runde zu. Wer H3 später
will, bekommt es dort — mit einem sauber vorregistrierten
Delisting-behandelten Universum, statt als Rest aus einem alten Budget.
Das ist der bessere Ort dafür.
