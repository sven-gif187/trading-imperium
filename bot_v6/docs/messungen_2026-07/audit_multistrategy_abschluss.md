# Audit Multi-Strategy — Abschluss

**Lokal:** 04.08.2026 07:05 (MESZ) · **UTC:** 2026-08-04T05:05Z
Vorgängerfassung gesichert als `audit_multistrategy_abschluss.md.bak_20260803`.

> **Keine der acht testbaren Strategien trägt einen Vorteil, der die
> coinweise Kostenschwelle überschreitet — 48 von 48 Tests, kein einziger
> übersteht die BH-FDR-Korrektur, keine Kombination ist in beiden Jahren
> stabil positiv, und die Architekturreparatur lohnt sich nicht.**

---

## 1. Vollständige Urteilstabelle

| Strategie | beste Lücke zur Kostenschwelle | Kombi/Jahr | ggü. Placebo | vorzeichenstabil | Urteil |
|---|---|---|---|---|---|
| RSI_DIVERGENZ | **+0,29 pp** | ±7 %/14d / J1 | +1,63 pp | ja, negativ | **TRÄGT NICHT** |
| FIBONACCI_SUPPORT | **+0,09 pp** | ±7 %/14d / J1 | +0,20 pp | nein | **TRÄGT NICHT** |
| MACD_CROSS | −0,61 pp | ±7 %/14d / J1 | −4,61 pp | nein | TRÄGT NICHT |
| TSI | −0,68 pp | ±7 %/14d / J1 | −5,71 pp | nein | TRÄGT NICHT |
| MULTI_SIGNAL | −0,98 pp | ±7 %/14d / J1 | −0,54 pp | nein | TRÄGT NICHT |
| EMA_TREND | −1,10 pp | ±7 %/14d / J1 | −3,63 pp | nein | TRÄGT NICHT |
| RSI_OVERSOLD | −3,87 pp | ±7 %/14d / J1 | +7,43 pp | ja, negativ | TRÄGT NICHT |
| BOLLINGER_BOUNCE | −4,34 pp | ±7 %/14d / J1 | +12,09 pp | ja, negativ | TRÄGT NICHT |
| ICHIMOKU | — | — | — | — | **NICHT TESTBAR** — keine Implementierung im Projekt |
| MOMENTUM_BREAKOUT | — | — | — | — | **NICHT TESTBAR** — `Vol_high` nirgends berechnet |
| STOCHRSI_REVERSAL | — | — | — | — | **NICHT TESTBAR** — Registry-Eintrag ohne Bedingung |
| DCA_FEAR_GREED | — | — | — | — | in E2 erledigt |
| GRID_BOT | — | — | — | — | Range-Handel, kein Richtungssignal |

Zwei Strategien schlagen ihr phasengleiches Placebo deutlich —
BOLLINGER_BOUNCE um 12,09 pp, RSI_OVERSOLD um 7,43 pp (J2: 12,02 pp).
Der Richtungsvorteil ist real. Er ist nur kleiner als der Spread.

---

## 2. Antwort auf 1.9

### **NEIN.** Die Architekturreparatur lohnt sich nicht.

Alle vier Bedingungen wurden geprüft, nicht drei:

| Bedingung | erfüllt von |
|---|---|
| Punktschätzer über Kostenschwelle | **2** von 48 |
| KI-Untergrenze über Schwelle | **0** |
| Placebo (95. Perzentil) geschlagen | **0** |
| in beiden Jahren vorzeichenstabil | **0** |

**Tragende Zahl:** Der beste Test (T-040 RSI_DIVERGENZ, J1, ±7 %/14d)
liegt **+0,29 pp** über seiner Kostenschwelle bei einem
Konfidenzintervall von **[40,88; 68,91]** — 28 Prozentpunkte breit, die
Schwelle mittendrin, n = 1 134. Die nächste KI-Untergrenze verfehlt ihre
Schwelle um **13,99 pp**.

Block 4 (Architekturentwurf) wurde deshalb **nicht ausgeführt** — so
vorgesehen. StrategyEvaluation-Vertrag, Selector, Regime-Gates,
Konfluenzlogik und Champion-Challenger bleiben ungebaut.

---

## 3. Bug-Liste mit Status

| Punkt | Status | tragender Beleg |
|---|---|---|
| 2.1 Handbuch-Nullbytes | **BESTEHT NOCH** | 68 328 Nullbytes ab Offset 0, in allen drei Kopien identisch; Anteil 27,29 % statt gemeldeter 34,5 % |
| 2.2 E7-Fenster 12 h zu früh | **BESTEHT NOCH** | `cockpit_server.py:112` nutzt 17.07. 00:00 UTC, `e7_auswertung.py:36` sagt `"2026-07-17T12"`; Fix-Diff liegt vor |
| 2.3 e7_final.txt | **BESTEHT NOCH** (Datei fehlt) | Skript ist read-only und lauffähig; heutige Ausgabe: „DATENLAGE ZU DUENN", K4 verfehlt (2 statt 3 wirksame Fälle) |
| 2.4 E8 nie installiert | **BESTEHT NOCH**, aber **GEGENSTANDSLOS** | `MARKER` 0×, beide Anker passen; Exposure-Check blockiert bei 20 % Positionsgröße jeden Nachkauf (40 % > 25 %), 5 116 Blockaden in 24 h, letzter Nachkauf 29.07. |
| 2.5 Backtest kapitaltot | **BESTEHT NOCH**, Block 1 **nicht betroffen** | `messung_t034b_strategien.py:80` importiert nur `lade_jahr`/`TAG_MS`, kein `Lauf`-Objekt, kein Kapitalstand |
| 2.6 ccxt-Gebühren | **GEGENSTANDSLOS** | keine Fundstelle im Produktivcode; Gebühren aus `backtest/fees.py:9-13` und `ausstieg_backtest.py:59-60` |
| 2.7 app.py-Selbststart | **GEKLÄRT** | AutoRestartMonitor ist in-process (Konfidenz 100 für den Ausschluss), keine Aufgabenplanung, kein Autostart, kein Registry-Run → manueller Start (Konfidenz 85) |
| 2.8 Umgebungsproblem | **BESTEHT NOCH** | zwei PowerShell-Timeouts zu Beginn, danach auf Bash umgestellt, Regel eingehalten |

Details je Punkt in `audit_multistrategy_block_2.md`.

---

## 4. Capture-Status

Läuft stabil. PID 15592 (`python.exe capture_daemon.py`), gestartet
04.08. 00:37:04 lokal. Zyklus 150 um 03:36:20Z: `ok=36 fehler=0
dauer=64.8s latenz_med=327ms`. Letzter Schreibvorgang 03:56:22Z
(`capture/2026-08-04/trades_UNIUSDC.csv`). Fehlerzahl seit Tageswechsel
**0**. Die `ABBRUCH`-Zeilen alle zehn Minuten sind die erwarteten
Watchdog-Läufe gegen die `msvcrt.locking()`-Sperre — genau das gewünschte
Verhalten.

---

## 5. Diff für die drei Logzeilen

Vollständig in `audit_multistrategy_block_3.md`. Kurzfassung:

- Drei `log.risk("RISK", f"REJECTED …")`-Zeilen unmittelbar vor den
  bestehenden `return intent` in `risk/engine.py:93`, `:102`, `:108`.
- Kein neuer Import (`log` ist über `:9` vorhanden), kein
  Verhaltenswechsel, kein Steuerfluss berührt.
- **Logvolumen:** +31 124 Zeilen / 24 h = **+2,81 MB**, von 11,93 auf
  14,74 MB (**+23,5 %**). Rotationsgrenze 20 MB wird statt nach ~1,7
  nach ~1,4 Tagen erreicht.
- Praktisch die gesamte Last trägt Zeile 1 (Schlafmodus). Die beiden
  Kill-Switch-Zeilen feuern im 24-Stunden-Fenster **null** mal.
- Rollback: `.bak` kopieren, drei Zeilen entfernen, Neustart. Kein
  persistenter Zustand.

**NICHT eingebaut.** `risk/engine.py` unverändert, mtime
2026-07-29T17:57:17.

---

## 6. Root Causes mit Beleg und Konfidenz

| # | Root Cause | Beleg | Konfidenz |
|---|---|---|---|
| 1 | **Stille Frühabbrüche in `RiskEngine.check()`** — `:88-93` Schlafmodus, `:98-102` und `:104-108` Kill-Switch setzen `risk_approved=False` und returnen ohne Log | 24-h-Log: 31 124 `[SIGNAL] -> BUY` gegen **0** `[RISK]`-Zeilen mit BUY, bei 2 995 `[RISK]`-Zeilen insgesamt (alle `APPROVED SELL`) | **98** |
| 2 | **Der Schlafmodus ist der dominante Zweig**, nicht der Kill-Switch | 7 598 Zeilen mit `Sleep-Mode`/`Schlafmodus`, **0** Zeilen mit `Kill-Switch` im gesamten 24-h-Log | **85** |
| 3 | **Handbuch-Korruption stammt nicht aus dem Code** | genau ein Nullblock ab Offset 0, Rest intakt (NTFS-delayed-write-Signatur); `doc_agent.py` hängt nur unter `## EVENTS-LOG` an und schreibt den Kopf unverändert zurück | **80** |
| 4 | **Der Multi-Strategy-Bug ist wirtschaftlich folgenlos** | 48 Tests, 0 über allen vier Bedingungen, beste Lücke +0,29 pp bei 28 pp KI-Breite | **90** |

Die Slot-Hypothese bleibt widerlegt: `Max Positionen` kommt im Log 0 mal
vor, `risk/engine.py:123` wird nie erreicht.

---

## 7. Erstellte und gelesene Dateien

**Erstellt (6):**
- `docs/messungen_2026-07/code/messung_t034b_strategien.py`
  (SHA256 `5e669c69…81fecb`)
- `docs/messungen_2026-07/code/audit_db_t034_eintrag.py`
- `docs/messungen_2026-07/code/audit_bugliste.py`
- `docs/messungen_2026-07/ausgaben/messung_t034b_strategien_out.txt`
- `docs/messungen_2026-07/ausgaben/messung_t034b_zwischenstand.jsonl` (48 Zeilen)
- `docs/messungen_2026-07/ausgaben/audit_bugliste_out.txt`

**Berichte (4):** `audit_multistrategy_block_1.md`, `_block_2.md`,
`_block_3.md`, `_abschluss.md`

**Backups (3):** `forschung.db.bak_vor_t034_20260804`,
`audit_multistrategy_abschluss.md.bak_20260803`,
`tickets.txt.bak_20260804`

**Nur gelesen:** `agents/v4_strategies.py`, `agents/signal_agent.py`,
`features/rsi_divergence.py`, `features/doc_agent.py`,
`core/auto_restart.py`, `core/logger.py`, `core/events.py`,
`risk/engine.py`, `app.py`, `config/settings.py`, `cockpit_server.py`,
`e7_auswertung.py`, `install_e8_nachkauf_stop.py`,
`backtest/fees.py`, `backtest/ausstieg_backtest.py`,
`ui/main_window.py`, `ENTWICKLERHANDBUCH.md` (+2 Kopien),
`data_store/system.log`, `data_store/trades_v5.json`,
`data_store/config.json`, `data_store/backtest/*_15m*.csv`,
`docs/messungen_2026-07/code/{harness_ext,messung_f2_ic,messung_t034_strategien}.py`,
`docs/forschungsprogramm_2026-07/forschung.db`

---

## 8. Datenbankschreibungen

**Eine.** Tabelle `trials` in
`docs/forschungsprogramm_2026-07/forschung.db`: **48 Zeilen** eingefügt
(`hypothese='MS-NACHTRAG'`, `runde=0`, `segment='GESAMT'`,
`kostenszenario='K-BASIS'`, `status='REJECTED'`). Ablauf: Backup →
Schema read-only geprüft → Dry-Run → `BEGIN` → `executemany` →
Zählprüfung im selben Transaktionsfenster → `COMMIT` →
SELECT-Verifikation in getrennter Nur-Lese-Verbindung.
Zeilenzahl `trials`: **99 → 147**, verifiziert: 48 Zeilen mit
`hypothese='MS-NACHTRAG'`.

Keine Schemaänderung, keine neue Tabelle, keine neue Spalte, kein
Trigger, kein Index, kein View, kein `UPDATE`, kein `DELETE`.

**Offene Registerfrage:** `zeile_id` 83 und 84 belegen T-034 und T-035
bereits als `runde=2, VORREGISTRIERT, "Runde 2, Reserve"`. Ich habe sie
**nicht angefasst** und die Nachtragsmessung mit `runde=0` danebengelegt.
Ob die Trial-IDs doppelt vergeben bleiben dürfen, entscheidest du.

---

## 9. Nicht durchgeführte Änderungen

- **Die drei Logzeilen** in `risk/engine.py` — Diff liegt vor, nichts
  eingebaut, keine `.bak` angelegt.
- **Der Fix in `cockpit_server.py:112`** — Diff liegt vor, nicht eingebaut.
- **Die Handbuch-Reparatur** — Plan liegt vor, nichts abgeschnitten,
  nichts überschrieben.
- **`install_e8_nachkauf_stop.py`** — nicht ausgeführt.
- **Block 4** — nicht ausgeführt, weil 1.9 = NEIN.
- **Nichts** in `risk/`, `portfolio/`, `execution/`, `agents/`,
  `config.json`, `app.py`.
- **Kein** Prozess gestartet, gestoppt oder neu gestartet. app.py läuft
  unverändert als PID 9300, capture_daemon als PID 15592.
- **Keine** Datei gelöscht. `data_store/` ausschließlich gelesen.
- **Keine** `.env` geöffnet, kein Secret gelesen, geloggt oder gespeichert.
- **Kein** Kommentar zur A/B-Entscheidung.

---

## 10. Was ich nicht weiß

**Ich weiß nicht, warum der app.py-Prozess zweimal still gestorben ist.**
Am 03.08. um 12:32:37 UTC endet das Log mitten im Betrieb ohne
Abschaltmeldung und ohne Traceback; zwischen 03.08. 17:22 und 04.08. 00:45
ein zweites Mal. Ohne Windows-Ereignisprotokoll ist die Ursache **NICHT
ENTSCHEIDBAR**.

**Ich weiß nicht, ob die 48 Tests die Strategien so abbilden, wie der Bot
sie live rechnet.** Die Features stammen aus `messung_f2_ic.py`, das in G1
gegen die Projektimplementierung verifiziert wurde (17 von 21 exakt) — vier
also nicht exakt. MULTI_SIGNAL kann Ensemble, Orderbuch, VWAP und
V4-Bridge nicht rekonstruieren.

### Zwei alternative Erklärungen für das Gesamtergebnis

1. **Der Test misst das Falsche.** Die Barrieren-Metrik fragt „berührt der
   Kurs zuerst +B oder −B", nicht „verdient eine Position mit Trailing-Stop
   und Teilverkäufen Geld". Eine Strategie mit P(auf) unter 50 % kann bei
   asymmetrischem Ausstieg profitabel sein. Dagegen spricht: E2 hat die
   Ausstiegsseite separat gemessen und ebenfalls nichts gefunden — aber
   die Kombination aus beidem ist hier nicht getestet.
2. **Der Einstiegszeitpunkt ist falsch modelliert.** Der Bot handelt nicht
   auf dem 1h-Close, sondern im Decision-Cycle alle ~19,5 Sekunden
   (gemessen: 185 Loops/Stunde). Wenn der Vorteil einer Strategie innerhalb
   der Stunde liegt, sieht ihn diese Messung nicht. Der
   Look-ahead-Sensitivitätslauf zeigt allerdings, dass ein *früherer*
   Einstieg die Ergebnisse **verschlechtert**, nicht verbessert.

### Welcher Beleg meine Hauptschlussfolgerung widerlegen würde

Eine Strategie, deren **Bootstrap-KI-Untergrenze** in **beiden** Jahren
über ihrer coinweisen Kostenschwelle liegt und die ihr phasengleiches
Placebo im 95. Perzentil schlägt. Heute verfehlt die beste KI-Untergrenze
ihre Schwelle um 13,99 pp — es müsste sich also nicht ein Detail ändern,
sondern die Größenordnung. Zweitens: ein Nachweis, dass die coinweisen
Kostenschwellen aus `12_SPREAD-MESSUNG.md` um mehr als den Faktor 2 zu
hoch sind. Bei halbierten Kosten läge die Schwelle für ±7 %/14d bei
52,3 % statt 54,8 % — dann würden sechs Tests darüber liegen. Die
Schwellen sind coinweise gemessen, aber sie sind die empfindlichste
Annahme der ganzen Auswertung.

---

## 11. Drei Verifikationsfragen, beantwortet

**Frage 1 (Pflicht): Wie viele der gefundenen Treffer wären bei reinem
Zufall zu erwarten?**

Bei m = 48 Tests und einem unkorrigierten Schwellenwert p < 0,05 wären
**2,4 Treffer** rein zufällig zu erwarten, bei p < 0,10 **4,8**.
Beobachtet wurden bei p < 0,05: **null**. Der kleinste rohe p-Wert liegt
bei **0,4840** — praktisch Münzwurf. Die zwei Punktschätzer über ihrer
Kostenschwelle (+0,29 pp und +0,09 pp) sind damit *weniger* als das, was
Zufall geliefert hätte. Nach BH-FDR bei q = 0,10 überlebt **k = 0**.

**Frage 2: Ist die Optimierung des Messskripts methodisch neutral, oder
habe ich die Zahlen verändert?**

Neutral, und das ist nachgewiesen statt behauptet: alle **5** Zeilen des
Altlaufs werden **bitgleich** reproduziert — n, P(auf), beide KI-Grenzen,
Placebo-Mittel, Kostenschwelle. Der Grund ist, dass `rennen()`
ausschließlich von (Coin, 1h-Index, Barriere, Fenster) abhängt und der
Bootstrap dieselbe Anzahl `randrange()`-Aufrufe in derselben Reihenfolge
verbraucht.

**Frage 3: Habe ich die Signalbedingungen wirklich aus dem Projektcode
genommen — oder die Behauptung der Vorgängersitzung übernommen?**

Selbst gelesen, und dabei **drei Abweichungen** gefunden, die das
Altskript enthielt: FIBONACCI_SUPPORT testete nur eines von drei Levels
(mit einem toten Oder-Zweig), MULTI_SIGNAL prüfte `price>ema20 and
price>ema50` statt `price>ema20>ema50`, RSI_DIVERGENZ verglich das letzte
Swing-Tief gegen alle früheren ohne den geforderten Mindestabstand von
1 % und ohne `rsi2 > rsi1+2`. Alle drei sind wörtlich nachgezogen. Hätte
ich die Behauptung übernommen, wären drei der acht Strategien falsch
getestet — und ausgerechnet FIBONACCI_SUPPORT und RSI_DIVERGENZ sind die
beiden, die am Ende knapp über ihrer Schwelle landen.

**Sichtbar korrigiert:** Ich hatte im Block-2-Bericht zunächst geschrieben,
ab 04.08. 00:47 werde *jede* Logzeile dreifach geschrieben. Das war zu
stark. Nachgezählt: von 7 454 BUY-Signalzeilen nach 00:47 ist **keine
einzige** eine exakte Wiederholung ihrer Vorzeile, und im Fenster
03:00–04:00 UTC entspricht die Wiederholungsrate von 185–186 exakt der
Decision-Loop-Frequenz. Betroffen sind nur die **Initialisierungs**meldungen.
Die Korrektur steht im Bericht; die Logvolumen-Hochrechnung in Block 3
beruht auf der ungeteilten Zahl 31 124 und ist davon unberührt.

---

## 12. Selbstkritik

**Was gut lief:** Der Altlauf wäre mit dieser Methodik nie fertig
geworden — die Hochrechnung ergibt Tage. Die Umstellung auf vorberechnete
First-Touch-Tabellen war die einzige Möglichkeit, 48 Tests in einer
Sitzung zu rechnen, und der bitgleiche Regressionsnachweis macht sie
überprüfbar statt glaubwürdig.

**Was ich zu spät bemerkt habe:** Den 45-Minuten-Look-ahead in `zu_1h()`.
Der steckt seit E2 in der Methodik und ist mir erst beim Lesen von
`rennen()` aufgefallen — nach vier Wochen Messungen, die alle darauf
aufbauen. Die Verzerrung ist mit bis zu 4,77 pp größer, als ich beim
ersten Hinsehen erwartet hätte. Dass sie in die konservative Richtung
zeigt, ist Glück, nicht Sorgfalt.

**Was ich hätte besser machen können:** Ich habe zwei PowerShell-Aufrufe
in den Timeout laufen lassen, obwohl das Problem in der Übergabe
ausdrücklich benannt war. Vier Minuten für einen bekannten Fehler.

**Was offen bleibt und mich stört:** Zwei stille Prozesstode in 36 Stunden
sind ein größeres Problem als alles in der Bug-Liste. Ich habe sie
gefunden, aber nicht erklärt — dafür hätte ich das Windows-Ereignis-
protokoll gebraucht, und das wäre über den Auftrag hinausgegangen.

**Wo ich mir unsicher bin:** Ob die Familienbildung für die
Konfluenzanalyse (RSI / TREND / PREIS) die richtige Aufteilung ist.
Ich habe sie an der Kernbedingung festgemacht und mit Jaccard-Werten
belegt, aber MULTI_SIGNAL zur RSI-Familie zu zählen ist eine Entscheidung,
keine Messung. Bei anderer Zuordnung ändern sich die Konfluenzzahlen —
nicht das Ergebnis, weil alle Werte weit unter der Schwelle liegen.

---

## 13. Abschlusssatz

**KEINE ECHTGELDORDER, KEIN BOT-STOPP, KEIN NEUSTART UND KEINE
PRODUKTIVÄNDERUNG OHNE FREIGABE DURCHGEFÜHRT: JA**
