# Audit Multi-Strategy — Block 1: Strategiemessung T-034 bis T-041

**Lokal:** 04.08.2026 06:45 (MESZ) · **UTC:** 2026-08-04T04:45Z
**Status:** ERFOLG — 48 von 48 Tests gerechnet, Altlauf bitgleich reproduziert.

---

## 1.1 Capture-Herzschlag

Läuft: PID 15592 (`python.exe capture_daemon.py`, gestartet 04.08. 00:37:04
lokal), Zyklus 150 um 03:36:20Z mit `ok=36 fehler=0 dauer=64.8s
latenz_med=327ms`, letzter Schreibvorgang 03:56:22Z
(`capture/2026-08-04/trades_UNIUSDC.csv`), Fehlerzahl seit Tageswechsel 0;
die `ABBRUCH: eine andere Instanz haelt die Sperre`-Zeilen alle 10 Minuten
sind die erwarteten Watchdog-Läufe.

---

## 1.2 Warum ein neuer Lauf nötig war

`messung_t034_strategien.py` (04.08. 00:49) lieferte 5 von 48 Zeilen, danach
kein Prozess mehr (`tasklist` zeigt nur capture_daemon und app.py),
Ausgabedatei eingefroren 01:51. Zwei Ursachen, beide belegt:

| Ursache | Beleg | Behebung |
|---|---|---|
| Laufzeit | Placebo rief `rennen()` 40 × 40 799 = 1,63 Mio mal je Barriere (Altskript :289-301); Bootstrap iterierte 2000 × 366 × ~110 ≈ 80 Mio mal je Test (:211-218) | First-Touch je (Coin, Barriere) **einmal** für alle 1h-Indizes vorberechnet; Bootstrap summiert je Kalendertag vorab |
| kein Zwischenstand | Altskript hielt alles im RAM, `persistiere` existierte nicht | jede fertige Zeile sofort nach `ausgaben/messung_t034b_zwischenstand.jsonl` |

**Zulässigkeit der Optimierung:** `rennen()` hängt ausschließlich von
(Coin, 1h-Index, Barriere, Fenster) ab — Signal- und Placebopfad riefen im
Altskript denselben Ausdruck auf. Der Bootstrap ist arithmetisch identisch
und verbraucht dieselbe Anzahl `randrange()`-Aufrufe in derselben
Reihenfolge, also dieselbe RNG-Sequenz.

**Regressionsnachweis:** 5 von 5 Altzeilen **bitgleich** reproduziert
(n, P(auf), KI, Placebo, Schwelle) — siehe Abschnitt REGRESSION in
`ausgaben/messung_t034b_strategien_out.txt`.

Laufzeit neu: rund 50 Minuten für alle 48 Tests inklusive beider Jahre und
der Look-ahead-Sensitivität.

---

## 1.3 Signalbedingungen — drei Abweichungen im Altskript gefunden

Ich habe jede Bedingung gegen den Projektcode gelesen, nicht die
Vorgängerbehauptung übernommen. Fünf von acht stimmten wörtlich, drei nicht:

| Strategie | Altskript | Projektcode | Folge |
|---|---|---|---|
| FIBONACCI_SUPPORT | nur 61,8 %-Level; der zweite Oder-Zweig `(h > 0 and abs(d) < 0.005)` war eine Kopie des ersten und damit tot | `v4_strategies.py:176-190` hat **drei** Zweige: 78,6 % + RSI<40, 61,8 %, 38,2 % + MACD bullisch; Fenster `df.tail(100)` (`:44-45`), nicht 120 | Signalmenge war echte Teilmenge |
| MULTI_SIGNAL | EMA-Punkt bei `price>ema20 and price>ema50` | `signal_agent.py:97` verlangt `price > ema20 > ema50` | zu viele Signale |
| RSI_DIVERGENZ | letztes Swing-Tief gegen **alle** früheren, ohne Mindestabstand | `rsi_divergence.py:105-115` vergleicht **aufeinanderfolgende** Paare und verlangt `price2 < price1*(1-1,0/100)` (`:17`) und `rsi2 > rsi1+2` (`:80`) | deutlich zu viele Signale |

Alle drei sind im neuen Skript wörtlich nachgezogen. RSI_OVERSOLD und
EMA_TREND blieben unverändert — deshalb sind die fünf Altzeilen als
Regressionstest verwendbar.

**Nicht behoben (dokumentiert):** MULTI_SIGNAL kann Ensemble-, Orderbuch-,
VWAP- und V4-Bridge-Komponenten (`signal_agent.py:131-160`) nicht
rekonstruieren. Diese erhöhen den Score ausschließlich — der Test ist
konservativ, nicht optimistisch.

---

## 1.4 Ergebnisse (Auszug, vollständig in der Rohausgabe)

Je Strategie × Barriere × Jahr: P(auf), Block-Bootstrap-KI über
Kalendertage (2000 Ziehungen), phasengleiches Placebo (40 Ziehungen,
Seed 20260730), n, Zensierungsanteil, coinweise Kostenschwelle
`p_be = 0,5 + c/(2B)`, Abstand in Prozentpunkten.

Die zwei einzigen Punktschätzer über ihrer Kostenschwelle:

| Trial | Strategie | Jahr | Barriere | n | P(auf) | KI | Schwelle | Abstand |
|---|---|---|---|---|---|---|---|---|
| T-040 | RSI_DIVERGENZ | J1 | ±7 %/14d | 1 134 | 55,20 % | [40,88; 68,91] | 54,92 % | **+0,29 pp** |
| T-039 | FIBONACCI_SUPPORT | J1 | ±7 %/14d | 13 676 | 54,72 % | [49,53; 59,98] | 54,63 % | **+0,09 pp** |

Beide Konfidenzintervalle schließen ihre Schwelle ein. Bei T-040 ist das
KI 28 Prozentpunkte breit — das ist kein Befund, das ist Rauschen mit
n = 1 134.

---

## 1.5 Multiple-Testing-Korrektur (Pflicht)

- m = **48** Tests (8 Strategien × 3 Barrieren × 2 Jahre), keiner ausgelassen.
- Benjamini-Hochberg, q = 0,10, einseitig gegen H₀: P(auf) ≤ Kostenschwelle.
- **k = 0** — kein einziger Test überlebt die Korrektur.
- Kleinster roher p-Wert: **0,4840** (T-040 J1 ±7 %/14d). Der zweitkleinste
  0,4864. Beide liegen praktisch bei Münzwurf.
- **Zufallserwartung:** bei p < 0,05 ohne Korrektur wären **2,4** Treffer
  rein zufällig zu erwarten, bei p < 0,10 **4,8**. Beobachtet wurden bei
  p < 0,05: **0**. Wir liegen also *unter* der Zufallserwartung.

---

## 1.6 Vorzeichenstabilität

Von 24 Strategie/Barriere-Kombinationen sind **5** vorzeichenstabil —
und **alle fünf stabil auf der falschen Seite** (P(auf) < 50 % in beiden
Jahren): RSI_OVERSOLD (±2,5 %/72h, ±5 %/7d), RSI_DIVERGENZ (±2,5 %/72h,
±5 %/7d), BOLLINGER_BOUNCE (±5 %/7d).

**Keine einzige Kombination ist stabil positiv.** Das Muster ist
systematisch: in J2 sind 23 von 24 Werten negativ, in J1 sind 18 von 24
positiv. Das ist ein Regimewechsel zwischen den beiden Jahren, kein
Strategieeffekt — nach unserer Konvention Rauschen.

---

## 1.7 Konfluenz

Deskriptiv, keine Gewichtungssuche, keine Schwellenoptimierung.

**Unabhängigkeit belegt, nicht angenommen.** Paarweise Jaccard-Überlappung
der Signalmengen (gleicher Coin, gleiche Stunde) in J1: MACD_CROSS /
MULTI_SIGNAL 0,592, EMA_TREND / TSI 0,519, MACD_CROSS / TSI 0,520,
TSI / MULTI_SIGNAL 0,323, EMA_TREND / MULTI_SIGNAL 0,293. Die
Trendstrategien teilen über die Hälfte ihrer Signale. Deshalb wurde nach
**Familien** gezählt: RSI (RSI_OVERSOLD, RSI_DIVERGENZ, BOLLINGER_BOUNCE,
MULTI_SIGNAL — alle mit RSI als Kernbedingung), TREND (EMA_TREND,
MACD_CROSS, TSI), PREIS (FIBONACCI_SUPPORT).

P(auf) nach Zahl gleichzeitig feuernder **unabhängiger Familien**
(Barriere ±2,5 %/72h):

| Familien | J2: n | J2: P(auf) | J1: n | J1: P(auf) |
|---|---|---|---|---|
| 1 | 32 698 | 48,70 % | 42 321 | 49,79 % |
| 2 | 46 236 | 46,12 % | 36 108 | 51,72 % |
| 3 | 8 745 | 46,63 % | 5 327 | 53,54 % |

**Antwort:** Nein. In J1 steigt P(auf) mit der Zahl der Familien
(+3,75 pp), in J2 **fällt** sie (−2,07 pp). Vorzeichenwechsel zwischen den
Jahren = Rauschen. Und selbst der beste Wert (53,54 %) liegt rund
**9,5 Prozentpunkte** unter der Kostenschwelle dieser Barriere (≈ 63 %).
Übereinstimmung trägt nicht mehr als das stärkste Einzelsignal.

Trial-Zählung: Die Konfluenzauswertung ist **deskriptiv** und fügt dem
48-Test-Set keine Tests hinzu. Würde man sie als Test führen, wären es
2 weitere (ein Jahr je Richtung) — auch dann bliebe k = 0.

---

## 1.8 Urteilstabelle

| Strategie | beste Lücke | Kombi/Jahr | ggü. Placebo | stabil | Urteil |
|---|---|---|---|---|---|
| RSI_DIVERGENZ | **+0,29 pp** | ±7 %/14d / J1 | +1,63 pp | ja (negativ) | **TRÄGT NICHT** |
| FIBONACCI_SUPPORT | **+0,09 pp** | ±7 %/14d / J1 | +0,20 pp | nein | **TRÄGT NICHT** |
| MACD_CROSS | −0,61 pp | ±7 %/14d / J1 | −4,61 pp | nein | TRÄGT NICHT |
| TSI | −0,68 pp | ±7 %/14d / J1 | −5,71 pp | nein | TRÄGT NICHT |
| MULTI_SIGNAL | −0,98 pp | ±7 %/14d / J1 | −0,54 pp | nein | TRÄGT NICHT |
| EMA_TREND | −1,10 pp | ±7 %/14d / J1 | −3,63 pp | nein | TRÄGT NICHT |
| RSI_OVERSOLD | −3,87 pp | ±7 %/14d / J1 | +7,43 pp | ja (negativ) | TRÄGT NICHT |
| BOLLINGER_BOUNCE | −4,34 pp | ±7 %/14d / J1 | +12,09 pp | ja (negativ) | TRÄGT NICHT |
| ICHIMOKU | — | — | — | — | **NICHT TESTBAR** (keine Implementierung im Projekt) |
| MOMENTUM_BREAKOUT | — | — | — | — | **NICHT TESTBAR** (`Vol_high` nirgends berechnet) |
| STOCHRSI_REVERSAL | — | — | — | — | **NICHT TESTBAR** (Registry-Eintrag ohne Bedingung) |
| DCA_FEAR_GREED | — | — | — | — | in E2 erledigt |
| GRID_BOT | — | — | — | — | Range-Handel, kein Richtungssignal |

Die zur Übergabe genannte Kernbeobachtung bleibt bestehen und wird
schärfer: RSI_OVERSOLD schlägt sein Placebo in J2 um 12,02 pp und in J1
um 7,43 pp — ein echter Richtungsvorteil gegen die Phase, der aber
**3,87 bis 14,43 Prozentpunkte unter der Kostenschwelle** endet.
BOLLINGER_BOUNCE schlägt sein Placebo sogar um 12,09 pp und liegt trotzdem
4,34 pp unter der Schwelle. Der Vorteil existiert; er ist nur kleiner als
der Spread.

---

## 1.9 Gesamturteil

| Bedingung | Tests, die sie erfüllen |
|---|---|
| 1) Punktschätzer über Kostenschwelle | **2** von 48 |
| 2) davon KI-Untergrenze über Schwelle | **0** |
| 3) davon Placebo (95. Perzentil) geschlagen | **0** |
| 4) davon vorzeichenstabil in beiden Jahren | **0** |
| zusätzlich FDR-signifikant | **0** |

### ARCHITEKTURREPARATUR ZUM FREILEGEN DIESER STRATEGIEN: **NEIN**

**Tragende Zahl:** Die beste gemessene Kombination (T-040 RSI_DIVERGENZ,
J1, ±7 %/14d) liegt +0,29 pp über ihrer Kostenschwelle bei einem
Konfidenzintervall von **[40,88; 68,91]** — 28 Prozentpunkte breit, die
Schwelle liegt mittendrin, n = 1 134. Die nächste KI-Untergrenze an ihrer
Schwelle verfehlt sie um **13,99 Prozentpunkte**.

Block 4 (Architekturentwurf) wird deshalb **nicht ausgeführt**.

---

## 1.10 Nicht behobener methodischer Mangel: 45 Minuten Look-ahead

`zu_1h()` (`messung_f2_ic.py:57-70`) vergibt als Zeitstempel den
**Stundenbeginn** H, als Preis aber den Close am **Stundenende** H+60min.
`rennen()` startet bei `bisect_right(zeiten, H)`, also bei H+15min — die
Viertelstunden H+15, H+30, H+45 werden mitgerennt, obwohl der Signalpreis
dort noch nicht bekannt ist. **Das betrifft E2 und G2 genauso.**

Der Hauptlauf behält die Konvention (Vergleichbarkeit mit E2/G2).
Zusätzlich wurde jede Zeile mit Start bei H+60min gerechnet:

- Größter Betrag der Verzerrung: **4,77 pp** (BOLLINGER_BOUNCE J1
  ±2,5 %/72h: 49,33 % → 44,56 %).
- **Richtung:** Die größten Abweichungen sind durchweg **negativ** — der
  Look-ahead hat P(auf) systematisch **überschätzt**. Ohne ihn sind die
  Ergebnisse schlechter, nicht besser. Das Urteil 1.9 wird dadurch
  bestätigt, nicht gefährdet.
- Diese Sensitivität geht **nicht** in die BH-FDR ein (keine Doppeltests).

---

## 1.11 Verwendete Dateien, Skripte, Datenbank

**Erstellt:**
- `docs/messungen_2026-07/code/messung_t034b_strategien.py` (24 918 B)
  SHA256 `5e669c693058fafeb6b53ae8af94a7344da30e81ae40307995e4ee0a6081fecb`
- `docs/messungen_2026-07/code/audit_db_t034_eintrag.py`
- `docs/messungen_2026-07/ausgaben/messung_t034b_strategien_out.txt`
- `docs/messungen_2026-07/ausgaben/messung_t034b_zwischenstand.jsonl` (48 Zeilen)
- `docs/forschungsprogramm_2026-07/forschung.db.bak_vor_t034_20260804` (237 568 B, Backup)

**Nur gelesen:** `agents/v4_strategies.py`, `agents/signal_agent.py`,
`features/rsi_divergence.py`, `features/indicators.py`,
`docs/messungen_2026-07/code/messung_f2_ic.py`,
`docs/messungen_2026-07/code/harness_ext.py`,
`docs/messungen_2026-07/code/messung_t034_strategien.py`,
`data_store/backtest/*_15m*.csv` (11 Coins × 2 Jahre).

**Eingangsdaten:** dieselben 15m-Kerzen wie E2/G2, 11 Coins
(BTC, ETH, SOL, ADA, AVAX, LINK, DOT, DOGE, NEAR, UNI, ATOM), je 8 761
1h-Balken pro Jahr, Warmlauf 210 Balken.

**Datenbankschreibung:** Tabelle `trials`, **48 Zeilen** eingefügt
(`hypothese='MS-NACHTRAG'`, `runde=0`, `segment='GESAMT'`,
`status='REJECTED'`), Transaktion mit Zählprüfung, Commit,
SELECT-Verifikation in getrennter Nur-Lese-Verbindung. Zeilenzahl
`trials`: **99 → 147**. Keine Schemaänderung, kein Trigger, keine neue
Spalte, kein UPDATE, kein DELETE.

---

## 1.12 Offene Punkte

1. **ID-Kollision in `forschung.db`:** `zeile_id` 83 und 84 belegen
   T-034 und T-035 bereits als `runde=2, VORREGISTRIERT, "Runde 2,
   Reserve"`. Die Nachtragsmessung wurde mit `runde=0` eingetragen und ist
   dadurch unterscheidbar, aber die Trial-IDs sind jetzt doppelt vergeben.
   **Ich habe die Altzeilen nicht angefasst.** Ob das Register das so
   führen soll, ist deine Entscheidung.
2. Der 45-Minuten-Look-ahead betrifft rückwirkend auch **E2 und G2**.
   Deren Zahlen sind damit um bis zu ~5 pp zu optimistisch. Das ändert an
   deren negativen Urteilen nichts, sollte aber im Register vermerkt werden.
3. `fear_greed` wird bei fehlendem Wert auf 50 gesetzt
   (`messung_t034b:baue_jahr`) — wie im Altskript. Betroffen sind nur
   Tage ohne F&G-Datensatz.

**Nächster sicherer Schritt:** keiner für Block 1 — die Messung ist
abgeschlossen. Block 4 entfällt laut 1.9.
