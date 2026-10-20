# Runde 2 — Befund der H5-Batterie

**31.07.2026 · Register v2.0 (freigegeben, ohne H8) · Trials T-031…T-033
verbraucht · Zähler jetzt T-033, Restbudget 2 (T-034/T-035 Reserve)**

Rohausgabe: `ausgaben/batterie_h5_out.txt`.
Reproduktion: `python batterie_h5.py` (31 s).

---

# ERGEBNIS: NEGATIV — kein Trial CONFIRMED

| Trial | Asset | Runden | EV/Runde K-BASIS | 95 %-KI | Placebo | Urteil |
|---|---|---|---|---|---|---|
| T-031 | BTC | 134 | +1,977 % | [−0,514; +4,639] | 86. Perz. | **REJECTED** |
| T-032 | ETH | 126 | +2,275 % | [−0,534; +5,504] | 81. Perz. | **REJECTED** |
| T-033 | Portfolio | 1105 | +3,993 % | [+2,367; +5,828] | 100. Perz. | **REJECTED** (sekundär) |

Ablehnungsgründe für die beiden gate-tragenden Trials: **Klausel A**
(Segment S-C), **KI enthält 0**, **Placebo nicht geschlagen** — alle drei
gleichzeitig.

## 1. Die registrierte Frage ist beantwortet — mit Nein

Register v2.0 fragte wörtlich: *ob Volatilitätskontraktion die
Selektivität liefert, die Donchian fehlte.*

**Sie liefert sie nicht.** Der Beleg ist die Segmentstruktur, und sie ist
identisch zum Donchian-Muster:

| Segment | Donchian BTC | **H5 BTC** | Donchian ETH | **H5 ETH** |
|---|---|---|---|---|
| S-A 2017–2019 | +18,99 % | +2,35 % | +4,85 % | +1,10 % |
| S-B 2020–2021 | +50,69 % | +5,04 % | +65,15 % | +6,51 % |
| **S-C 2022–2023** | **+0,50 %** | **−0,86 %** | **+0,16 %** | **−0,17 %** |

Donchian fiel in S-C auf null. H5 fällt in S-C **unter** null. Der
selektivere Filter hat den Zerfall nicht aufgehalten — er hat ihn nicht
einmal abgemildert.

## 2. Der schärfere Befund: H5 schlägt nicht einmal den Zufall

Donchian hatte immerhin das Placebo geschlagen (98.–99. Perzentil). **H5
tut das nicht:** BTC 86., ETH 81. Perzentil. Zufällige Long/Flat-Masken
mit gleicher Long-Quote und gleicher mittlerer Blocklänge erzeugen in
etwa jedem sechsten bis siebten Durchlauf ein besseres Ergebnis.

Das heißt: der positive Gesamt-EV von +1,98 % / +2,28 % je Runde ist
**kein Effekt der Regel**, sondern das, was jede Long/Flat-Maske mit
dieser Marktexposition in einem Zeitraum liefert, in dem BTC +887 % und
ETH +656 % gemacht hat. Die NR7-Bedingung fügt nichts hinzu.

Der Lag+1-Test bestätigt das von der anderen Seite: EV +2,010 % (BTC) und
+2,016 % (ETH) — praktisch unverändert gegenüber +1,977 % / +2,275 %. Ein
Signal, dessen Wert sich nicht ändert, wenn man es einen Tag später
ausführt, trägt keine zeitpunktspezifische Information.

## 3. T-033 — die Survivorship-Falle, ein zweites Mal

Der Portfolio-Trial schlägt als einziger das Placebo (100. Perzentil) und
hat mit p < 0,0001 den kleinsten p-Wert. **Genau dasselbe Bild wie T-024
in Runde 1** — und wieder scheitert er an Klausel A (S-C −0,336 %) und ist
nach Klausel B ohnehin nicht gate-tragend.

Dass zweimal hintereinander ausgerechnet der survivorship-belastete
Portfolio-Trial das stärkste Signal zeigt, ist selbst der Befund: **es ist
die Coin-Auswahl, die misst, nicht die Regel.** Klausel B hat in beiden
Runden genau das verhindert, wofür sie geschrieben wurde.

## 4. Pflichtkennzahlen — die Haltedauer-Referenz ist widerlegt

| | T-031 BTC | T-032 ETH | T-033 Portfolio |
|---|---|---|---|
| Haltedauer Median | **7 Tage** | **6 Tage** | **7 Tage** |
| 25./75. Perzentil | 4/12 | 3/13 | 3/13 |
| MFE Median | +4,58 % | +5,88 % | +7,19 % |
| MAE Median | −4,41 % | −6,84 % | −7,48 % |
| R/R Median | 0,76 | 0,61 | 0,83 |
| **Trefferquote** | **32,1 %** | **34,1 %** | **30,6 %** |
| **Payoff** | **3,28** | **2,91** | **4,06** |

**Zwei Befunde daraus:**

1. **Die Haltedauer liegt weit unter dem Referenzband 23–46 Handelstage**
   (Median 6–7 statt 23+). Registerpflichtiger Befund. Konsequenz: H5
   erzeugt ~20 Runden/Jahr statt der 4,5 von Donchian — die Regel ist
   damit **deutlich kostenempfindlicher**. Der Abstand K-MAKER ↔ K-BASIS
   beträgt hier 15–17 % des EV (Donchian: 1,3–1,8 %). Hätte H5 die
   übrigen Kriterien bestanden, wäre der Limit-Order-Pfad **relevant**
   geworden. Er wird es nicht, weil H5 durchfällt.
2. **Die externe 65-%-Referenz ist gemessen widerlegt.** Gemessen wurden
   30–34 % Trefferquote bei Payoff 2,9–4,1 — exakt das Profil, das ich im
   Register gegen die Referenz gesetzt hatte (35–45 % bei R/R > 2), und
   nicht das der Referenz. Ein System mit 65 % Trefferquote auf diesen
   Regeln existiert in unseren Daten nicht.

## 5. Was H5 kann — und warum es nicht reicht

MaxDD 76,3 % gegen 83,2 % (BTC) und 66,1 % gegen 94,0 % (ETH). Wie schon
bei Donchian: die Regel reduziert Drawdown. Aber sie tut es schlechter
als Donchian (55,1 % / 69,1 %) bei gleichzeitig fehlendem
Placebo-Nachweis. Es gibt keine Kennzahl, in der H5 besser ist als die
bereits verworfene Regel.

## 6. Regel-13-Status

Gate 1 war negativ (`09_GATE-1-VERDICT.md`). Die Runde-2-Batterie ist
ebenfalls negativ. **Das sind zwei negative, sauber dokumentierte Gates.**

Nach Regel 13 lautet das Ergebnis für dieses Projekt damit: **„mit
unseren Mitteln nicht erreichbar"**. Ein Forward-Paper ist nicht möglich,
weil es keinen überlebenden Kandidaten zum Einfrieren gibt.

**Eine Unklarheit muss der Eigentümer entscheiden, nicht ich:** In
`10_ZWEITE-RUNDE-EINSCHAETZUNG.md` §J2 hatte ich festgehalten, zwei
negative Gates seien final. Die Freigabeentscheidung vom 30.07.2026
(Punkt 4) formuliert dagegen, Regel 13 erlaube eine Neu-Registrierung
„mit Hypothesen auf NEUEN Daten" — und genau dafür läuft seit dem
31.07.2026 der Live-Capture. Beide Lesarten sind vertretbar; sie führen
zu unterschiedlichen Programmenden:

- **Lesart A (final):** Das Programm endet hier, dokumentiert. Der
  Live-Capture läuft als Datenarchiv weiter, ohne zugesagtes Folgeprojekt.
- **Lesart B (eine Neu-Registrierung auf neuen Daten):** Das Programm
  pausiert, bis der Capture genug Historie hat (Orderbuch/Spread/OI über
  Monate), und eine Runde 3 registriert ausschließlich Hypothesen, die
  **nur** mit diesen Daten testbar sind — also Mikrostruktur, nicht noch
  eine Preisregel.

Ich empfehle keine der beiden. Lesart B ist nur dann keine Endlosschleife,
wenn die Runde-3-Hypothesen auf Daten beruhen, die es heute nicht gibt —
sonst ist es dieselbe Familie im dritten Anlauf.
