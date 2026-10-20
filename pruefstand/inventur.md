<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Phase 0 · Inventur · v2 · 14.10.2026

> **BERICHTIGUNG 14.10.2026, 16:30 (nach Prüf-Agent A5), gilt vor allem Folgenden:**
> - **Signal-Verkäufe:** Bei den 21 Signal-Verkäufen (`execute_approved_trade`) ist der Verkaufs-`amount` im Journal **netto**, die Gebühr ist schon abgezogen. `runden_lib.py` zog sie ein zweites Mal ab, der Profitabilitäts-Bericht ebenso.
> - **E7 richtig:** brutto **+75,51 $ / +0,332 % je Runde (t 2,15)**, Gebühren 109,62 $, **netto −34,11 $**. Die Bericht-Zahl „+0,33 % / 2,2 Standardfehler“ stimmt also. **P0-4 („Bericht zu günstig“) ist zurückgezogen.** Bestehen bleibt: Im Block-Bootstrap nach Tagen schließt der 95-%-Bereich (−0,18 % bis +0,81 %) die Null ein.
> - **P0-6 ist berichtigt:** Die doppelte Kaufgebühr (Befund 42) betraf **alle 136 Runden** (54,78 $), auch den Signal-Weg (`app.py:1746` über `cost_basis`). Die frühere Prüfung „= 0“ bei den 21 Signal-Runden war Zufall: Mein Skript zog die Verkaufsgebühr doppelt ab, der Bot die Kaufgebühr. Beide sind gleich groß.
> - Die Zahlen in Abschnitt 3/4 unten sind die **alte, falsche Fassung**. Richtig sind die Werte hier oben.

**Summary:** Die Kernzahlen des Berichts lassen sich exakt aus den Rohdaten nachbauen (136 Runden, −43,13 $). Drei Aussagen stimmen so aber nicht:

1. Der Vorsprung vor Kosten ist aus der Kasse gerechnet nur +0,29 % je Runde, nicht +0,33 %. Mit t = 1,93 statt 2,2 ist er statistisch nicht gesichert.
2. Die doppelte Kaufgebühr steckt auch in v7, nicht nur in v6.
3. Es gibt keinen fertigen Patch für die doppelte Kaufgebühr.

Bestätigt sind: der Bybit-Wechsel am 05.10. (Primärquelle), die 18,3 Tage Pausen, der tote Nachlauf von v6 und dass kein Bot nach einem Neustart von selbst startet.

v2 ersetzt v1 (gleicher Tag). Neu in v2: Prozent-Konfidenz (Entscheidung F1), Nachrechnung aus Rohdaten, Primärquelle Bybit, Vorgehen nach Abschnitt 7 vollständig, Korrekturliste für den Masterprompt.

**Umfang:** Alles nur lesend (SQLite `mode=ro`, JSON gelesen, eine öffentliche Webseite abgerufen).
- Rechnungen als Skripte im Sitzungs-Scratchpad: `runden.py`, `pruef2.py`, `markt.py`, `inventur_db.py`, `inventur_json.py`, `gebuehr_ist.py`.
- Nicht jede Datei gelesen. Nicht abgeglichen: `order_history.json` (der Dreifach-Abgleich ist Aufgabe von A2).
- Zeiten: Berlin (MESZ), wenn nicht UTC angegeben.

---

## 0 · Vorgehen nach Abschnitt 7 (sichtbar)

**RE2, Aufgabe in einem Satz:** Bestandsaufnahme beider Bot-Instanzen, nur lesend: was läuft, wo liegen Daten, Kosten- und Ausstiegsregeln, vorhandene Wächter. Dabei wird geprüft, ob das Fundament des Masterprompts (Abschnitt 2 und 3) stimmt, bevor darauf gebaut wird.

**Step-Back:** Teil 11 sagt: Gute Prompts retten keine schlechten Daten. Wenn die Ausgangszahlen falsch sind, ist jede Entscheidung in Phase 1 auf Sand gebaut. Deshalb habe ich zuerst nachgerechnet und erst danach inventarisiert.

**Zerlegung (T1–T8) und was Phase 0 dazu liefert:**

| | Teilproblem | Phase-0-Ergebnis |
|---|---|---|
| T1 | Stimmen die Daten? | Kernzahlen reproduziert. Zwei Buchungsfehler v6+v7, fehlende Pflichtfelder (Abschn. 3, 4) |
| T2 | Kosten senken | Bybit EU 0,25 % einheitlich bestätigt, Break-even 0,152 % je Seite bestätigt (Abschn. 5) |
| T3 | Vorsprung je Runde | brutto +0,29 %, t 1,93, nicht gesichert (Abschn. 3) |
| T4 | Ausstiege | v6 kostenblind (0,35/1,2), v7 kostenbezogen, aber unter I1/I2 (Abschn. 6) |
| T5 | Marktlage | Markt +31 bis +40 %, Bot handelt 3 Münzen, Capture hat 18 (Abschn. 3, 12) |
| T6 | Schnell messen | v7: 15 Runden, nicht entscheidbar |
| T7 | Betrieb sichtbar | kein Autostart, 4,6 h Ausfall heute, Tagescheck fängt das nicht (Abschn. 8) |
| T8 | Risiko / Live-Tore | Bybit-Schlüssel laut Sven gelöscht, beide Instanzen `paper` |

---

## 1 · Instanzen und Prozesse (Stand 10:40)

| Instanz | Pfad | Modus | Münzen | Größe/Pos. | Epoche | Läuft |
|---|---|---|---|---|---|---|
| **v6** | `C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)` | paper | BTC, ETH, SOL (USDC) | 30 % · max. 3 | E7_filter_schaerfer seit 15.08. 07:47 UTC | ja, PID 11332 seit 10:08, Port 5050 |
| **v7** | `C:\Users\<BENUTZER>\Desktop\trading_imperium_v7` | paper | BTC, ETH, SOL (USDC) | 50 % · max. 1 | L7 seit 25.09. 21:56 UTC | ja, PID 10452 seit 10:33, Port 5070 |
| – | `C:\trading_imperium_v6(21)` | – | leer (0 Dateien) | – | – | – |
| – | `C:\Users\<BENUTZER>\_ALT_v6_20260903` | – | Archiv, nur `docs\` | – | – | – |

Weitere Prozesse: v6 `schatten_universum.py` (seit 10:08), v6 `positionsverlauf.py`, v7 `schatten_universum.py` (seit 09:26), v6 Forschungs-Capture.
[SICHER 99 %, `Win32_Process`, `Get-NetTCPConnection`]

v7 läuft im Papiermodus: Das Log von 08:34 UTC zeigt „Paper-Modus aktiv“ und die Telegram-Kennung „PAPIER“. Die Kasse (246,45 $) plus Sparplan-BTC (238,37 $) ergeben 484,82 $, das passt zur Kontokurve vor dem Neustart. [SICHER 99 %]

## 2 · Aufgabenplanung

| Aufgabe | Ordner | Letzter Lauf | Ergebnis |
|---|---|---|---|
| TI6-Tagescheck | v6 | 13.10. 07:15 | 1 = Fehler gefunden |
| TI7-Tagescheck | v7 | 13.10. 07:30 | 1 = Fehler gefunden |
| TI6-Sammler / -OneDriveWacht / -Wochensicherung | v6 | 13.10. / 13.10. / 11.10. | 0 |
| ForschungCapture | v6 | alle 10 min | läuft |
| SchattenUniversumLIVE (+_Anmeldung) | **v7** | 10:04 | 0 |

- **Keine Aufgabe startet `app.py`** (weder v6 noch v7). [SICHER 99 %]
- Die Aufgabe `SchattenUniversumWacht` (v6) gibt es nicht mehr. [SICHER 99 %]

## 3 · Nachrechnung der Kernzahlen aus `trades_v5.json` (Abschnitt 2.1 / 3.2)

Methode: Jeder Verkauf wird dem offenen Kauf derselben Münze zugeordnet. Netto = (Verkaufsbetrag − Verkaufsgebühr) − Kaufbetrag. Brutto = Verkaufsbetrag − (Kaufbetrag − Kaufgebühr).

**Fenster:** Verkäufe ab **13.08.2026 13:21:19 UTC (E6-Start)** bis 13.10. Mit einem Fenster ab 13.08. 00:00 kommen 137 Runden heraus. Die zusätzliche Runde ist SOL, Verkauf 09:14:55 UTC, netto −0,2154 $.

| Kennzahl | Bericht | Nachgerechnet | Urteil |
|---|---|---|---|
| Runden | 136 | **136** | ✓ |
| Brutto | +66,49 $ | **+66,49 $** | ✓ |
| Gebühren (Kauf / Verkauf) | 109,62 $ (– / 54,84) | **109,62 $ (54,78 / 54,84)** | ✓ |
| Netto | −43,13 $ | **−43,13 $** | ✓ (3 Wege, s. u.) |
| Monate Aug / Sep / Okt | +5,37 (73) / −24,54 (45) / −23,96 (18) | **gleich** | ✓ |
| Im Cockpit gebucht | −88,89 $ | **−88,89 $** | ✓ |
| Trefferquote / nötig | 52,2 % / 60,6 % | **52,2 % / 60,6 %** | ✓ |
| Ø Gewinn / Ø Verlust | +0,98 / −1,50 % | **+0,98 / −1,50 %** | ✓ |
| Ø Einsatz | 161 $ | **161,13 $** | ✓ |
| Ausstiege Stopp / Null / Nachzieh | 33 −144,48 / 21 −7,90 / 61 +68,15 | **gleich** | ✓ |
| EMA_TREND / MACD_CROSS | 84 −46,03 / 9 +19,97 | **gleich** | ✓ |
| Break-even-Gebühr je Seite | 0,152 % | **0,1517 %** | ✓ |
| Kauf- / Verkaufsvolumen | ≈ 21.870 / 21.936 $ (geschätzt) | **21.914,04 / 21.925,74 $** (direkt) | Bericht leicht ungenau |
| „alle unter Epoche E7“ | ja | **nein: 3 Runden mit Kauf vor E7-Start**, erster Kauf 12.08. 17:30 UTC | Bericht falsch |
| **Vorsprung je Runde** | **+0,33 %, 2,2 Standardfehler** | **+0,29 %, t 1,93** (Kasse) | **Bericht zu günstig** |

**Netto auf drei Wegen** [SICHER 97 %]:
1. Summe der Kassenrechnungen: −43,13 $.
2. Brutto − Kosten: 66,49 − 109,62 = −43,13 $.
3. Gebucht + Doppelgebühr − Rundung: −88,89 + 45,91 − 0,16 = −43,14 $.

**Handprobe:**
- 16.08. SOL: 100,9718 − 0,2524 − 103,4700 = **−2,7506 $**. Gebucht −3,0093 $, Differenz 0,2587 $ = genau die Kaufgebühr.
- 12.10. BTC: 177,2279 − 0,4431 − 181,7657 = **−4,9809 $**. Gebucht −5,4353 $, Differenz 0,4544 $ = genau die Kaufgebühr.

**Woher +0,33 % kommt** [SICHER 95 % für die Zahl, WAHRSCHEINLICH 70 % für die Ursache]:
- Der Mittelwert des Bot-Feldes `pnl_pct` beträgt +0,336 %, t 2,18. Das ist die Bericht-Zahl.
- Aus der Kasse (Verkaufskurs ÷ Kaufkurs − 1) sind es nur +0,292 %, t 1,93.
- `pnl_pct` liegt im Mittel also 0,044 Punkte zu hoch. Vermutlich rechnet es gegen einen anderen Einstandskurs als den tatsächlichen Füllkurs (nicht geprüft).
- **Folge:** Der Vorsprung vor Kosten liegt knapp unter der 95-%-Schwelle, und das schon bei einfachem Standardfehler. Der vorgeschriebene Block-Bootstrap nach Tagen (Abschnitt 12.5) macht den Bereich breiter, nicht enger. „Brutto im Plus“ ist damit **nicht belegt**, nur wahrscheinlich.

**Markt im Fenster** (`telemetrie.db` → `markt_historie`, 13.08. 13:21 → 13.10. 13:21 UTC):
- Nachgerechnet: BTC +30,9 %, ETH +32,6 %, SOL +40,3 %, Korb +34,6 %.
- Bericht: +31,3 / +33,2 / +41,7 %.
- Größenordnung bestätigt. Die Abweichung kommt vermutlich vom Schnittzeitpunkt (Tagesschluss gegen Uhrzeit). [WAHRSCHEINLICH 85 %]

**Pausen über 3 h** (aus `evaluations`): 12 Lücken, zusammen **18,3 Tage** ✓.
- Die größten: 08.09.–20.09. (291 h, bewusst abgeschaltet) und **07.10. 07:34 → 09.10. 17:04 UTC (57,5 h, Ursache unbekannt)**.
- Heute kam die Lücke 05:29 → 10:08 dazu (Windows Update).

**v7** (15 Runden, Verkäufe 27.09.–13.10.), berichtigt am 14.10.:
- v7 hat Befund 42 seit 11.09. behoben. Der Kauf-`amount` ist dort **ohne** Gebühr, das Skript erkennt die Bedeutung jetzt an `qty × Kurs`.
- Ergebnis: Brutto **−0,97 $**, Kosten 12,73 $, netto **−13,70 $**, gebucht −13,70 $. Gebucht und Kasse stimmen in 15 von 15 Runden überein.
- Der Bericht (Masterprompt 2.1) nennt −10,06 $. Das ist um die Kaufgebühren (3,64 $) zu günstig, ihm ist dieselbe Verwechslung passiert.
- Mit der richtigen Bybit-Gebühr seit 05.10. wären es ≈ −16,58 $.
- Brutto je Runde −0,02 %. Unter 30 Runden: **nicht entscheidbar**.

## 4 · Buchhaltungsfehler (Befund 42 und 88, mit Ergänzung)

`schon_bekannt.py execution/engine.py:401` meldet BEKANNT (17 Stellen, Handbuch 4.5/4.50, Problemliste 42). Was folgt, ist deshalb eine **Ergänzung**, kein neuer Fund.

| | v6 (136 Runden) | v7 (15 Runden) |
|---|---|---|
| Ursache | `execution/engine.py:401` `filled_cost = amount` (Gebühr enthalten) | gleich |
| Doppelter Abzug | `app.py:1896`, `app.py:3085` `filled_cost + fee` | `app.py:2058`, `app.py:3218` |
| Runden mit Kaufgebühr doppelt | **115** (+45,91 $), alle über `exit_monitor` (61 Nachzieh, 33 Stopp, 21 Null) | **15 von 15** (+3,64 $) |
| Richtig gebucht | 21 Signal-Verkäufe (15 exakt, 6 auf Cent gerundet) | 0 |

**Pflichtfelder auf den 136 v6-Verkäufen** [SICHER 99 %]:
- `stop_initial` und `trailing_stop_pct`: **0 / 136**.
- `decision_id`, `signal_score`, `signal_reasons`, `active_strategy`: **21 / 136**, nämlich genau die Signal-Verkäufe.
- `fee`, `mfe_pct`, `mae_pct`, `market_regime`, `fear_greed_at_entry`: 136 / 136.

**Gemeinsame Ursache:** Der Schreibweg `exit_monitor` erzeugt beide Fehler. Er bucht die Kaufgebühr doppelt und lässt die Entscheidungsfelder leer. [WAHRSCHEINLICH 80 %, Muster in den Daten eindeutig, Code des Pfads nicht gelesen]

Datenqualität in der Datei: 2 Verkäufe ohne Kauf (26.06., 13.08. 09:36 UTC, beide außerhalb des Fensters). 97 Nachkäufe, der letzte am 05.08. (im Fenster keine).

## 5 · Gebührenmodell (H9)

**Primärquelle** [SICHER 95 %]: Bybit EU, „Trading Fee Structure“, Last updated 2026-10-05 13:01:39. Wörtlich: „From 05/10/2026 at 11:00 UTC, we're moving to a single unified fee structure“. VIP 0 zahlt 0,2500 %, nur eine Spalte „Trading Fee Rate“, also kein Maker-Rabatt mehr. Abgerufen am 14.10. per `curl`, HTTP 200.

| | v6 | v7 |
|---|---|---|
| Tabelle | `backtest/fees.py:24` bybit Maker 0,10 / Taker 0,25 | gleich |
| Papier-Satz | immer Taker, `execution/engine.py:352` | Kauf über Warte-Auftrag = Maker, `execution/engine.py:486`, Rückfall `:393` |
| Zentrale Konstante | keine | `core/kosten.py:60-69`: MAKER 0,10, K_WARTE 0,355 |
| Gebucht | 0,2500 % je Seite ✓ | Kauf 0,1001 % ✗, Verkauf 0,2500 % |

**Befund P0-1 · v7 bucht Käufe seit dem 05.10. zu billig** [SICHER 95 %]:
- 8 Käufe (05.10. 14:52 bis 12.10. 23:02 UTC) mit Summe 1.919,75 $.
- Zu wenig gebucht: 1.919,75 $ × 0,15 % = **2,88 $**. Gegenprobe: 4,80 $ Soll − 1,92 $ gebucht = 2,88 $.
- `schon_bekannt`: NEU.

## 6 · Ausstiegsregeln und Konstanten

| Konstante | v6 | v7 | Soll laut 3.9 (K 0,505) |
|---|---|---|---|
| `BREAKEVEN_AB_PCT` (Nullsicherung scharf ab) | 1,0 `risk/exit_rules.py:83` | 1,0 | – |
| `BREAKEVEN_PUFFER_PCT` | **0,35** `:107` | 0,55 `:131` = K + 0,045 | I1 ≥ 0,605 |
| `TRAIL_AB_PCT` | **1,2** `:108` | 1,57 `:139` | I2 ≥ 1,62 |
| `TREND_BONUS` | 1,3 `:109` | 1,3 | – |
| `LEITER` (Hoch % → Faktor auf Abstand 1,0 %) | (1,2→1,0) (3→1,3) (5→1,7) (8→2,2) `:113` | gleich, Start 1,57 | – |
| `risk.stop_loss_pct` / `trailing_stop_pct` | 2,5 / 1,0 | 2,5 / 1,0 | Stopp je Münze (Ansatz 5) |
| `CURRENT_ATH` | **109.114 fest** `agents/cycle_theory.py:28` | dynamisch `:65` | dynamisch |
| Verlustzähler gespeichert | nein | ja `runtime/state_manager.py:142` | – |
| `risk.daily_loss` | aktiv, 6 % | – | – |
| `live_max_order_usd` / `live_max_capital_usd` | 25 / 200 | – | Live-Tore A8 |

Zur Wirkung bei v7: BREAKEVEN_LOCK lieferte 6 Runden, netto +2,76 $, 83 % im Plus. Bei v6 waren es 21 Runden, 0 % im Plus. Die Richtung passt, aber unter 30 Runden ist das nicht entscheidbar.

## 7 · Patches `v6\patches_nach_27_08\`

| Datei | Befund | Inhalt | v7 |
|---|---|---|---|
| patch_00a_breakeven_puffer.py | 0 | 0,35 → 0,55 | drin |
| patch_45_trailing_schwelle.py | 45 | 1,2 → 1,57 | drin |
| patch_54_verlustzaehler.py | 54 | Verlustzähler speichern | drin |
| patch_63_ath_dynamisch.py | 63 | ATH aus Wochenkerzen | drin |

- **Für Befund 42 (doppelte Kaufgebühr) gibt es keinen Patch.** Das gilt für v6 und v7.
- `00_LIES_MICH.md` empfiehlt **eine** Epochengrenze für alle vier Patches und Patch 54 zusammen mit der Korrektur von Befund 42.

## 8 · Vorhandene Wächter-Bausteine

| Baustein | Was er kann | Lücke |
|---|---|---|
| `features/waechter.py` | Bestand gegen Position, USDC ≥ 0, alle 5 min, Telegram | läuft im Bot-Prozess und stirbt mit ihm |
| `tagescheck.py` (1.191 Z.) | Betrieb, Sammler, DB-Integrität, Aufgaben, Platte; erkennt Fremdordner-Prozesse | einmal am Tag; prüft das Log-Alter, nicht ob `app.py` läuft |
| `runtime/exit_monitor.py` | Ausstiege | Schreibweg mit Doppelgebühr und leeren Feldern (Abschn. 4) |
| `prozess_frische_wacht.py`, `onedrive_wacht.py`, `tickets_watcher.py` | alter Programmtext, OneDrive, Tickets | – |
| `nachlauf.py`, `schatten_*` | Nachlauf, Schatten-Signale | v6 wieder an seit 10:08 |
| `go_live_check.py`, `stichtag.py`, `e7_auswertung.py` | Freigabe, offizielle Auswertung | Grundlage für A3/A8 |

**Erweitern statt doppelt bauen** [WAHRSCHEINLICH 75 %]:
- W5 nutzt die Prüfungen aus `tagescheck.py` und läuft alle 5 min als eigener Prozess. Er prüft Port bzw. PID statt Log-Alter.
- W4 baut auf `features/waechter.py` auf, läuft aber außerhalb des Bots.

## 9 · Zeitzonen

- v6-Handelspfad: 44 × `datetime.now()` ohne Zeitzone, 33 × UTC, 0 × Europe/Berlin. [SICHER 90 %, grep-Zählung, Stellen nicht einzeln geprüft]
- `system.log` schreibt UTC ohne Kennzeichen, `trades_v5.json` UTC mit `+00:00`.
- Risiko an Tagesgrenzen (Tagesverlust-Reset): [VERMUTUNG 50 %], Aufgabe für A9.

## 10 · Ordnerbaum v6 (Dateien je Ordner)

`docs` 10.450 (fast alles Capture) · `data_store` 226 · `_archive_20260812_144758` 139 · `v4_referenz` 71 · `features` 51 · `chartlabor` 40 · `zahlenbuecher` 35 · `data` 35 · `core` 30 · `agents` 28 · `risk` 27 · `archiv` 26 · `models` 24 · `execution` 21 · `ui` 20 · `backtest` 17 · `metals` 15 · `portfolio` 14 · `live` 13 · `runtime` 10 · Rest unter 10.

Gesamt 11.645 Dateien, 2,8 GB. `telemetrie.db` allein 938 MB.

## 11 · Claude Code

- **App:** Arbeitsstufe „Ultracode“ eingeschaltet (Bildschirmfoto Sven).
- **CLI:** 2.1.295 unter `%APPDATA%\Claude\claude-code\2.1.295\…\claude.exe`, **nicht im PATH**.
- **Folge für Phase 6:** Die Aufgabenplanung braucht den vollen Pfad. Der Ordnername ändert sich mit jedem Update, also braucht es eine Suchroutine in der `.bat`.
- **Flags:** Alle für Phase 6 nötigen Flags existieren: `-p`, `--agent`, `--add-dir`, `--allowedTools`, `--permission-mode dontAsk`, `--permission-prompts none`, `--output-format json`, `--json-schema`, `--max-budget-usd`, `--no-session-persistence`. Die Pfadregel-Syntax ist noch nicht getestet.
- **Hooks:** Die v6-Hooks (Schreibschutz `forschung.db`) greifen in Prüfstand-Sitzungen **nicht**.

## 12 · Neue Befunde und Ergänzungen aus Phase 0

| Nr. | Befund | Status | Konfidenz |
|---|---|---|---|
| P0-1 | v7 bucht Käufe seit 05.10. mit 0,10 % statt 0,25 %, 2,88 $ zu wenig | NEU | SICHER 95 % |
| P0-2 | Kein Autostart. Windows Update 05:32 → 4,6 h Ausfall v6+v7, v6-BTC-Position ohne Stopp-Überwachung | NEU, F5 entschieden | SICHER 97 % |
| P0-3 | Parallele Claude-Sitzung im v6-Ordner | erledigt (F3) | – |
| P0-4 | Vorsprung vor Kosten aus der Kasse +0,29 %, t 1,93, nicht gesichert. `pnl_pct` liegt 0,044 Punkte zu hoch | NEU | SICHER 90 % (Zahl) |
| ~~P0-5~~ | ~~Doppelte Kaufgebühr auch in v7~~ **zurückgezogen:** v7 bucht seit 11.09. richtig. Mein Skript hatte den Kauf-`amount` falsch gelesen | – | – |
| P0-9 | Im Fenster-Modus handelt der Bot erst nach Klick auf STARTEN. Der Autostart öffnete nur das Fenster, v6 stand 11:36–11:49 ohne Überwachung. Behoben mit `patch_autostart_klick.py` | NEU, behoben | SICHER 97 % |
| P0-10 | Die alten Patches 00a/45/63 haben `exit_rules.py` und `cycle_theory.py` von LF auf CRLF umgestellt (Textmodus). Die Shell-Zählung `grep -c $'\r$'` ist in Git-Bash falsch. Auf LF zurückgesetzt | NEU, behoben | SICHER 99 % |
| P0-11 | `ccxt.coinbasepro` gibt es in ccxt 4.5.48 nicht mehr (`data/market_data.py:15`, `execution/exchange_client.py:219`). Der Rückfall auf Binance greift | NEU, LOW | SICHER 95 % |
| P0-6 | Doppelgebühr und leere Entscheidungsfelder kommen beide aus dem `exit_monitor`-Weg | Ergänzung zu 42 + 88 | WAHRSCHEINLICH 80 % |
| P0-7 | Unerklärte Lücke 07.10. 07:34 → 09.10. 17:04 UTC (57,5 h) | NEU | SICHER 95 % (Lücke), Ursache OFFEN |
| P0-8 | v7 lag schon ab 13.10. 23:59 UTC still, also vor dem Update | NEU | WAHRSCHEINLICH 70 % |

## 13 · Hypothesen H1–H9 · vorher (Masterprompt) → nach Phase 0

| | Hypothese | vorher | nachher | Grund |
|---|---|---|---|---|
| H1 | Kosten > Vorsprung | 90 % | **97 %** | brutto +0,29 % gegen K 0,50 % |
| H2 | Ausstiege kostenblind | 90 % | **97 % (v6)** | 0,35/1,2 im Code, Nullsicherung 21/21 im Minus |
| H3 | Gewinne zu früh, Verluste voll | 80 % | **85 %** | +0,98 / −1,50 %, Stopps −2,78 % |
| H4 | Einstieg ohne Vorsprung | 60 % | **60 %** | EMA_TREND brutto +21,27 $ (bestätigt 2.6), aber kein Zufallsvergleich gerechnet |
| H5 | Marktlage-blind | 75 % | **75 %** | Markt +31–40 %, Investitionsgrad nicht gerechnet |
| H6 | Verzerrte Lerndaten | 70 % | **75 %** | Doppelgebühr in v6 (115) und v7 (15). Ob das Brain `pnl` liest: nicht geprüft |
| H7 | Teil des Vorsprungs ist Drift | 60 % | **70 %** | brutto nicht signifikant, Drift ≈ 0,14 % je Runde laut Bericht |
| H8 | Betriebslücken verdecken Probleme | 85 % | **98 %** | 18,3 Tage Pausen, heute 4,6 h, Nachlauf 17 Tage tot, Tagescheck blind für `app.py` |
| H9 | Gebührenmodell passt nicht | 70 % | **v7 95 % · v6 5 %** | Primärquelle + Buchungen |

**Zweite Meinung: Was, wenn H1 falsch ist?**
- **Alternative A:** Das Signal selbst taugt nichts (H4). Dann hilft auch eine billige Börse kaum. Das ist weniger wahrscheinlich, weil MACD_CROSS (+28 $ brutto auf 9) und EMA_TREND (+21 $ auf 84) brutto positiv sind. Allerdings ist n klein.
- **Alternative B:** Die Ausstiege vernichten den Vorsprung (H3). Diese Alternative ist nicht schwächer als H1, sondern parallel. Stopps kosten −118,82 $ brutto, Nachzieh-Stopps bringen +117,02 $.
- **Fazit:** Kosten und Ausstiege sind gemeinsam die Hauptursache. Die Kosten allein (−109,62 $) sind die größere einzelne Zahl.

## 14 · Korrekturvorschläge für MASTERPROMPT_AGENTEN.md (Sven entscheidet, nichts geändert)

1. **2.1 Zeitraum:** „Verkäufe ab 13.08.2026 13:21:19 UTC (E6-Start)“ statt „13.08.“, sonst 137 Runden.
2. **2.1 Runden:** „136, davon 3 mit Kauf vor E7-Start“ statt „alle unter Epoche E7“.
3. **2.1 Ergebnis vor Kosten:** „+66,49 $ (+0,29 % je Runde aus der Kasse, t 1,93; das Bot-Feld `pnl_pct` zeigt +0,34 %, t 2,18)“ statt „+0,33 %, 2,2 Standardfehler“.
4. **2.2 doppelte Kaufgebühr:** Fundstelle `app.py:1896/3085`, Ursache `engine.py:401`. Betroffen sind 115/136 (nur `exit_monitor`). **Nur v6**, v7 seit 11.09. behoben. Für v6 seit 14.10. behoben (Epoche E9).
4a. **2.1 v7:** −13,70 $ statt −10,06 $ (Kauf-`amount` in v7 ohne Gebühr).
5. **2.2 Patches:** Die vier Patches sind 00a, 45, **54**, 63. Tabelle 2.2 gilt nur für v6, v7 hat sie bereits.
6. **2.3 Befund 88:** Ergänzen, dass auf 115/136 auch `decision_id`, `signal_score`, `signal_reasons` und `active_strategy` fehlen.
7. **2.4 Bybit:** an der Primärquelle bestätigt, Konfidenz bleibt SICHER.
8. **3.2 Volumen:** direkt 21.914,04 / 21.925,74 $.
9. **6.1 W1:** „12 Münzen“ → Bot handelt 3, Capture sammelt 18 (ADA APT ARB ATOM AVAX BTC DOGE DOT ETH INJ LINK NEAR OP RENDER SOL SUI UNI XRP).
10. **Phase 1:** Die Patch-Bündelung an `00_LIES_MICH.md` angleichen (eine Epochengrenze) oder bewusst davon abweichen.
11. **Phase 6:** `claude` nicht im PATH. Die Start-Skripte suchen die `claude.exe` selbst.
12. **0 Starter-Block:** Konfidenz-Regel im Prüfstand = Prozent (F1). Die v6-`CLAUDE.md` gilt im Bot-Ordner weiter.

## 15 · Prüffragen (CoVe)

1. **Stimmt meine Rundenbildung?** Ja. 14 Kennzahlen des Berichts sind exakt reproduziert, mit zwei Handproben und Netto auf drei Wegen. Nach dem ersten Lauf korrigiert: Fenster 13.08. 00:00 → E6-Start, sonst 137 Runden.
2. **Ist P0-1 belastbar?** Ja. Die Primärquelle ist abgerufen, die 2,88 $ sind auf zwei Wegen gerechnet, die Handprobe passt (0,368 $).
3. **Ist „t 1,93“ mit „2,2 Standardfehler“ vergleichbar?** Nur teilweise. Beide nutzen den einfachen Standardfehler, aber verschiedene Renditemaße. Mit Block-Bootstrap wird der Bereich breiter, die Aussage „nicht gesichert“ bleibt.

## 16 · Was ich NICHT weiß

- Den Dreifach-Abgleich mit `order_history.json` und dem Saldo-Verlauf (A2).
- Ob Brain und Strategie-Gedächtnis das zu schlechte `pnl`-Feld lesen. Davon hängt ab, wie stark H6 wirkt.
- Woher die Lücke 07.–09.10. kommt und warum v7 schon um 01:59 stand.
- Warum `pnl_pct` von der Kasse abweicht (anderer Einstandskurs? Rundung?).
- **Was die Antwort komplett ändern würde:** Ein Block-Bootstrap, der den Brutto-Vorsprung klar über null zeigt. Dann wäre „nur Kosten senken“ die richtige Strategie. Bleibt er bei null, muss zuerst das Signal (H4) geprüft werden.

## 17 · Selbstkritik

- In v1 hatte ich behauptet, es gebe keinen „Ultracode-Modus“. Das war falsch: Die App hat ihn, ich hatte nur die CLI geprüft.
- v1 hatte die Bericht-Zahlen ungeprüft übernommen. Das ist jetzt nachgeholt.
- Den `exit_monitor`-Code habe ich nicht gelesen. P0-6 stützt sich nur auf das Datenmuster.
- Bewertung: Präzision 9 · Vollständigkeit 8 (Dreifach-Abgleich fehlt, bewusst A2) · Umsetzbarkeit 9.

## Nachtrag 15.10.2026 · P0-7 Lücke 07.10. 07:34 → 09.10. 17:04 UTC geklärt, soweit es die Spuren erlauben

| Zeit (Berlin) | Was | Beleg |
|---|---|---|
| 07.10. 09:24 / 10:12 | Sven ist am Rechner (Eingabe, Entsperren) | System-Ereignis 566 (InputHid, SessionUnlock) |
| **07.10. 09:34** | **v6 schreibt nicht mehr ins `system.log`** | `dauercheck.log` 09.10. 08:06 UTC: „system.log 2912 Min alt“ → 07.10. 07:34 UTC |
| 07.10. 09:34 | kein Absturz-Ereignis (Application Error) und kein Neustart von Windows | Application- und System-Log 09:00–10:30 |
| 07.10. 19:32 | Standby, **vom Benutzer angefordert** (winlogon), danach zweimal kurz aufgewacht | Ereignisse 1074, 42, 107 |
| 07.10. 19:52 → 09.10. 10:05 | Rechner im Standby (Systemzeit springt beim Aufwachen von 07.10. 17:52 UTC auf 09.10.) | Kernel-General 1 |
| 09.10. 19:04 | v6 läuft wieder | Ende der Lücke |

**Schluss:** Der Bot wurde am 07.10. um 09:34 bei laufendem Rechner beendet, ohne Absturzspur in Windows. [VERMUTUNG 60 %] Das Fenster wurde von Hand geschlossen oder STOPPEN gedrückt, was mit Befund 72 nichts gespeichert hat. Die übrigen 34 von 57,5 h fallen in den Standby des Rechners. Die Logs aus der Zeit sind rotiert, genauer lässt es sich nicht mehr klären.
**Heute verhindert:** Autostart bei Anmeldung (F5), W5 meldet einen fehlenden Bot-Prozess und fehlendes Internet sofort per Telegram (seit 15.10. eingerichtet), Befund 72 ist in v6 behoben (E13).
**Offen bei Sven:** Standby bzw. Ruhezustand ausschalten, solange die Bots rund um die Uhr laufen sollen. Das ist eine Systemeinstellung.

## Nachtrag 15.10.2026 · P0-8 zurückgezogen

„v7 lag schon ab 13.10. 23:59 UTC still“ stimmt nicht. Das `system.log` von v7 zeigt durchgehenden Betrieb bis 14.10. 03:21 UTC: Herzschlag „Uptime 106h 16m“, Kurs-Schnappschüsse, Kontostand. Danach folgt der Neustart durch das Windows-Update um 05:32 Berlin (03:32 UTC). Die Fehlannahme kam vermutlich aus einer Datenquelle, die nachts nur selten schreibt, etwa der Telemetrie. W5 sah dort auch am 15.10. nachts wieder lange Pausen bei v7. [SICHER 95 %] v7 lief bis zum Update.
