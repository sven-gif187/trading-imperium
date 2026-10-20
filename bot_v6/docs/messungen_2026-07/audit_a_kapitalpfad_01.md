# BLOCK A — Kapitalerschöpfung: Reichweite

**UTC 2026-08-03 · Status: ERFOLG · read-only, kein Trial**
Skript: `code/audit_a_kapitalpfad.py` · Rohausgabe:
`ausgaben/audit_a_kapitalpfad_out.txt`

---

## A0 — Meine frühere Begründung war falsch

Ich hatte behauptet, E2/E5/G2 seien nicht betroffen, „weil sie
Relativgrößen ohne Kapitalpfad rechnen". **Die Begründung ist falsch.**
Der wirksame Mechanismus ist nicht Dollar-gegen-Prozent, sondern
**Auswahl**: hört der Harness auf zu handeln, existieren die
Eintrittsereignisse nicht mehr, auf denen E2/E5/G2 überhaupt rechnen.
Das Ergebnis (Gate-Batterien nicht betroffen) bleibt richtig — aus einem
anderen Grund als angegeben.

## A1 — Messung für Messung

| Messung | nutzt Kapitalpfad | Beleg | betroffen |
|---|---|---|---|
| E1 Nachkaufrate | nein | `messung_e1_nachkaufrate.py` lädt Rohkerzen, rekonstruiert Journal-Positionen | nein |
| E1 Fenster | nein | dito, Rohkerzen | nein |
| E2 Stops | **ja** | `messung_e2_stops.py` → `LaufMess` (10 Referenzen) | **ja** |
| E2 Einstieg | **ja** | `messung_e2_einstieg.py` → `LaufMess.kauf_events` | **ja** |
| E2 Placebo I/II | **ja** | `messung_e2_placebo*.py` → `LaufMess` | **ja** |
| E2 Phasenplacebo | **ja** | `messung_e2_phasenplacebo.py` → `LaufMess.kauf_events` | **ja** |
| E5 Universum | **ja** | `messung_e5_universum.py` → `LaufMess` | **ja** |
| F1 Reibung | nein | Codeinspektion + Arithmetik, keine Kerzen | nein |
| F1e Maker | nein | Journal-Snapshot + Kerzen, kein Harness | nein |
| F2 IC | nein | `messung_f2_ic.py` Rohkerzen 1h-Aggregate | nein |
| F3 Benchmark | **ja** | Bot-P&L stammt aus dem Harness-Kapitalpfad | **ja** |
| G1 Indikatoren | nein | Projektimplementierungen auf Rohkerzen | nein |
| G2 Horizonte | **ja** | `messung_g2_horizonte.py` → `LaufMess.kauf_events` | **ja** |
| **Gate 1, T-016…T-030** | **nein** | `batterie_h1.py` `netto_evs()` = `(exit/entry−1)*100 − c`; `runden_aus_signal()` erzeugt Runden allein aus der Signalserie | **nein** |
| **Gate 2, T-031…T-033** | **nein** | `batterie_h5.py` nutzt dieselben Funktionen | **nein** |
| T-030 H4 Overlay | nein | `batterie_h4.py`, Tagesrenditen ohne Kapital | nein |

## A2 — Gate-Batterien: Gegenprobe

**Die Frage nach Eintritten je Segment ist gegenstandslos**, weil die
Gate-Batterien den Harness gar nicht benutzen:

| | Harness (E1/E2/E5/G2/F3) | Gate-Batterien |
|---|---|---|
| Datenquelle | `data_store/backtest/*_15m.csv` | `docs/forschungsprogramm_2026-07/daten/klines_1d/` |
| Zeitraum | 2024-07 … 2026-07 | 2017-08 … 2023-12 |
| Überschneidung | **keine** | |
| Kapitalpfad | ja (`_kaufe`, `betrag >= 10`) | **keiner vorhanden** |

In `batterie_h1.runden_aus_signal()` gibt es keine Bedingung, die eine
Runde wegen fehlenden Kapitals unterdrücken könnte. Eine
Kapitalerschöpfung ist konstruktiv unmöglich. **[SICHER]**

Die Segmentzahlen S-A/S-B/S-C sind entsprechend besetzt (T-031:
43/41/50 Runden; T-033: 199/384/522) — kein Segment leer, keines durch
Kapitalmangel ausgedünnt.

## A3 — Größenordnung bei den betroffenen Messungen

**Neu gemessen (nicht geschätzt):**

| | Jahr 2 | Jahr 1 |
|---|---|---|
| Nominalzeitraum | 366 Tage | 366 Tage |
| Erster Eintritt | 2025-09-26 | 2024-08-05 |
| **Letzter Eintritt** | **2026-02-15** | **2025-04-16** |
| Gehandelte Spanne | 143 Tage = **39,1 %** | 255 Tage = **69,7 %** |
| Tage mit Eintritt | 104 (28,4 %) | 43 (11,7 %) |
| Endkapital (bar) | **49,44 $** | **186,56 $** |
| Handelsschwelle | 50,00 $ | 50,00 $ |

**[BEFUND] Nur Jahr 2 ist kapitalerschöpft, Jahr 1 nicht.**
→ [BELEG] Endkapital J1 = 186,56 $ gegen Schwelle 50 $; letzter Eintritt
16.04.2025 mit 3,5 Monaten Restlaufzeit und ausreichend Kapital. Die
Eintrittslücke in J1 stammt vom F&G-Filter, nicht vom Geld.
→ [KONSEQUENZ] Meine Pauschalaussage „der Harness" war J2-spezifisch.
J1-Ergebnisse sind von Kapitalerschöpfung **nicht** betroffen.
→ [KONFIDENZ] SICHER

**Auswirkung auf E2/E5/G2 [WAHRSCHEINLICH]:** Die Kennzahlen bleiben
intern gültig, beschreiben aber nur 26.09.2025–15.02.2026 (J2) statt
eines Jahres. Vorzeichen und Reihenfolge ändern sich nicht — der
Barrierentest ist skaleninvariant und wurde gegen ein phasengleiches
Placebo aus **demselben** Fenster geprüft. Was sich ändert, ist die
**Generalisierbarkeit**: „Jahr 2" ist als Etikett irreführend.

## A4 — F3 neu gerechnet

| Jahr | Bot P&L | Halten NOMINAL | Diff NOM (bisher berichtet) | Halten IST-SPANNE | **Diff IST** |
|---|---|---|---|---|---|
| Jahr 2 | −450,56 $ | −227,50 $ | −223,06 $ | −186,48 $ | **−264,08 $** |
| Jahr 1 | −313,44 $ | +380,63 $ | −694,07 $ | +277,41 $ | **−590,85 $** |

**[BEFUND] Die Korrektur verschlechtert Jahr 2 und verbessert Jahr 1 —
das Vorzeichen kippt in keinem Fall.**
→ [BELEG] Tabelle oben, `audit_a_kapitalpfad_out.txt`.
→ [KONSEQUENZ] Die bisher berichtete F3-Zahl war für J2 sogar **zu
günstig** für den Bot. Der Befund „BTC-Halten schlägt den Bot" bleibt in
beiden Jahren und beiden Rechnungen bestehen.
→ [KONFIDENZ] SICHER für die Zahlen, WAHRSCHEINLICH für die Deutung —
auch „Diff IST" ist eine Näherung: der Bot hält in seiner Spanne nicht
durchgehend Positionen, und sein Einsatz schrumpft mit dem Kapital.

## A5 — Urteil je Befund

| Befund | Status |
|---|---|
| E2: kein Richtungsvorteil | **GÜLTIG**, Geltungsbereich auf J2-Fenster einzuschränken |
| E2: Stop-Variation bringt 0,13 R | **GÜLTIG**, dito |
| E5: kein Coin mit positivem EV | **GÜLTIG**, dito |
| E5: N_eff 1,23–1,42 | **GÜLTIG** (Korrelation aus Kerzen, nicht aus Trades) |
| G2: lange Horizonte | **GÜLTIG**, dito |
| **F3: Bot verliert gegen Halten** | **KORRIGIERT** — Beträge −264,08 / −590,85 statt −223,06 / −694,07; Aussage unverändert |
| Gate 1 negativ | **GÜLTIG, nicht betroffen** |
| Gate 2 negativ | **GÜLTIG, nicht betroffen** |
| „J2 = ein Jahr" | **KORRIGIERT** → 39,1 % eines Jahres |

## A6 — Umbau auf konstanten Einsatz: Kosten/Nutzen (nicht ausgeführt)

**Kosten:** Der Kontrollanker (1480 Trades / −450,5621 $) bricht sofort.
Alle 9 Messläufe E1–E5 und G2 werden unvergleichbar und müssten neu
gerechnet **und neu interpretiert** werden. Die eingefrorenen
Rohausgaben verlieren ihren Beweiswert.
**Nutzen:** J2 würde 12 statt 4,7 Monate abdecken; F3 wäre ein sauberer
Vergleich; E5-Coin-Kennzahlen wären nicht mehr durch Cash-Konkurrenz
verkoppelt.
**Bewertung:** Aufwand 7 | Risiko 8 | Impact 4. Der Nutzen betrifft
ausschließlich Messungen zu einem Signalpfad, der bereits als
richtungslos belegt ist. **Nicht empfohlen — Entscheidung liegt beim
Eigentümer.**
