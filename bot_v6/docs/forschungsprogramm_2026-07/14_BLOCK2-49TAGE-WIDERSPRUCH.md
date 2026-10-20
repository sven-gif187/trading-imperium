# Block 2 — Der +31,44-$-Widerspruch: aufgelöst

**03.08.2026 · Kein Trial · Rohausgabe
`ausgaben/messung_block2_49tage_out.txt` · Reproduktion:
`python messung_block2_49tage.py`**

---

# Ergebnis: WEDER (a) NOCH (b) — die Frage war falsch gestellt

Der Vergleich „Bot reibungsfrei +31,44 $ über 49 Tage gegen Backtest
verliert haushoch" war **nie zulässig**. Beide Seiten stehen an
völlig verschiedenen Punkten ihrer Kapitalkurve.

## 2.1 Die Streuungsmessung — Erklärung (a) ist widerlegt

634 rollierende 49-Tage-Fenster aus beiden Backtest-Jahren,
reibungsfreie P&L je Fenster:

| | Jahr 2 | Jahr 1 | gesamt |
|---|---|---|---|
| Fenster | 317 | 317 | 634 |
| Minimum | −224,21 $ | −126,46 $ | −224,21 $ |
| Median | −13,05 $ | +0,00 $ | +0,00 $ |
| **Maximum** | **+9,73 $** | **+23,89 $** | **+23,89 $** |
| Anteil positiv | 5,4 % | 3,8 % | — |
| **Anteil ≥ +31,44 $** | **0,0 %** | **0,0 %** | **0,0 %** |

Bedingt auf Fenster **mit** Handelstätigkeit (die Nullfenster des
F&G-Filters entfernt): J2 191 Fenster, Spanne −224,21 bis **+9,73 $**;
J1 142 Fenster, Spanne −126,46 bis **+23,89 $**. Auch hier: 0,0 %
erreichen den Live-Wert.

**[BEFUND]** +31,44 $ liegt **außerhalb der gesamten Spannweite** von
634 Fenstern, in beiden Jahren, mit und ohne Nullfenster.
**[KONSEQUENZ]** Erklärung (a) „49 Tage sind Rauschen" ist **widerlegt**.
**[KONFIDENZ]** SICHER · Risiko 1 | Aufwand 3 | Impact 7

## 2.2 Die eigentliche Ursache — der Harness ist im Live-Fenster pleite

Der schärfste Test: was tat der Harness in **genau** dem Live-Fenster
10.06.–29.07.2026?

**Null Trades. Nicht wenige — keine.**

Die Ursachensuche in drei Schritten:

1. **F&G-Filter?** Nein. F&G lag an **47 von 50 Tagen unter 30**
   (Median 23, Minimum 9). Die Kaufbedingung `fg < 30` war fast
   durchgehend erfüllt.
2. **Wann hört der Harness auf?** Letzter Eintritt **15.02.2026**.
   Eintritte je Monat: 09/2025: 14 · 10/2025: 176 · 11/2025: 436 ·
   12/2025: 359 · 01/2026: 243 · 02/2026: 252 · **danach: 0**.
3. **Warum?** Endkapital **49,44 $** von 500 $ Start. `_kaufe` verlangt
   `betrag >= 10 $` (`backtest/ausstieg_backtest.py:198`); bei
   `groesse_pct = 20` braucht das **50 $ Eigenkapital**. Der Harness
   unterschreitet die Schwelle Mitte Februar und ist ab da handlungsunfähig.

**[BEFUND]** Der Backtest „Jahr 2" handelt **nicht 12 Monate, sondern
4,7** (26.09.2025 – 15.02.2026). Die restlichen 5,5 Monate ist er
kapital-tot.
**[BELEG]** Letzter Eintritt 2026-02-15, Bar am Ende 49,44 $,
Mindestschwelle 50 $ Eigenkapital.
**[KONSEQUENZ]** Der Live-Bot startete im Juni 2026 mit frischen 500 $ in
einem Fenster, in dem der Harness seit vier Monaten nicht mehr handeln
konnte. Die +31,44 $ sind **kein** Hinweis auf ein Modelldefizit —
sie stammen aus einem Kapitalzustand, den der Harness dort nicht hat.
**[KONFIDENZ]** SICHER · Risiko 2 | Aufwand 2 | Impact 9

## 2.3 Was daraus für die bisherigen Befunde folgt

Dies ist keine neue Erkenntnis, sondern die **Zuspitzung** von BEFUNDE.md
Nr. 13 („Kapitalgrenzen-Artefakt: konstante Netto-P&L ~−450 $ über alle
J2-Stopvarianten ist Sättigung bei 500 $ Startkapital"). Neu ist das
Ausmaß: die Sättigung tritt nicht am Rand ein, sondern **nach 47 % der
Laufzeit**.

**Konsequenzen, die dokumentiert gehören:**

1. **Absolute Dollarzahlen aus J2 beziehen sich auf 4,7 Monate**, nicht
   auf ein Jahr. Wer sie als Jahresergebnis liest, unterschätzt die
   Verlustrate um mehr als die Hälfte.
2. **Vergleiche „Bot gegen BTC-Halten" über J2 sind schief**: Halten
   läuft 12 Monate, der Bot 4,7. Der F3-Befund (Halten schlägt den Bot um
   223 $) bleibt in der Richtung gültig, in der Größe aber **NICHT
   ENTSCHEIDBAR** ohne Neurechnung mit konstantem Einsatz.
3. **Die E2/E5/G2-Befunde sind davon NICHT betroffen.** Sie messen
   Trefferquoten, R-Größen und Anteile je Trade — alles Relativgrößen,
   die von der Kapitalerschöpfung nicht verzerrt werden. Der Kernbefund
   „kein Richtungsvorteil" steht unverändert.
4. **Die Gate-1- und Gate-2-Batterien sind nicht betroffen.** Sie
   rechnen EV je Runde in Prozent, ohne Kapitalpfad.

## 2.4 Offener Punkt (keine Entscheidung getroffen)

Ob der Harness für künftige Arbeiten auf **konstanten Einsatz** statt
prozentualer Größe umgestellt werden sollte, ist eine Design-Entscheidung
mit Folgen für die Vergleichbarkeit **aller** bisherigen Läufe — der
Kontrollanker (1480 Trades / −450,5621) würde brechen. **NICHT
ENTSCHEIDBAR ohne Eigentümer-Entscheid.** Ich habe nichts geändert.
