<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Agententest Phase 6 · 15.10.2026 · ca. 12:10–12:20 Berlin (10:10–10:20 UTC)

**Alle elf Prüf-Agenten (A1–A11) sind in der Sitzung verfügbar und haben ihren Mini-Auftrag erledigt. Keiner hat dabei eine Datei geschrieben. Die Antworten sind plausibel, nur der Risiko-Manager hat mit einem veralteten Gebührensatz gerechnet, weil `instanzen.json` veraltet war.** [SICHER 95 %]

## 1 · Verfügbarkeit

| Prüfung | Ergebnis |
|---|---|
| Dateien in `pruefstand\.claude\agents\` | 11 Stück, Dateiname = `name`-Feld, Frontmatter vollständig (`name`, `description`, `tools`, `model: inherit`) |
| Als Agententyp in dieser Sitzung | alle 11: leitstand, kassenpruefer, quant-statistiker, einstiegs-pruefer, ausstiegs-pruefer, kosten-analyst, marktlage-stratege, risiko-manager, code-forensiker, advocatus-diaboli, epochen-verwalter |
| Fehlende Agenten | keiner, also keine Ursachensuche nötig (`skripte\agenten_anlegen.py` nicht gebraucht) |

## 2 · Ergebnis je Agent

Alle Aufträge waren nur lesend: keine Datei schreiben, SQLite nur mit `mode=ro`, Python mit vollem Pfad. Laufzeit = Zeit bis zur Antwort.

| Agent | Mini-Auftrag | Lief | Antwort plausibel | Probleme |
|---|---|---|---|---|
| A1 leitstand | Mini-Tagesprüfung: Ampeln W1–W7, Ereignisse 24 h, veraltete Wächter | ja, 63 s | **ja.** Ampeln stimmen mit `status.json`. W3 GELB richtig begründet. Werkzeug `Agent` (Beauftragen) vorhanden. Wichtigster Fund: v7-Telemetrie in 24 h dreimal ROT, jedes Mal nachts (23:45, 02:40, 05:40 UTC, einmal 303 min ohne Daten) | Masterprompt aus Zeitgründen nicht gelesen. Der gemeldete „Widerspruch“ bei NEAR ist erklärbar (siehe 3.6) |
| A2 kassenpruefer | v6-Runden seit E10 als Kasse gegen W4 `kasse`/`konto` | ja, 56 s | **ja.** 1 Runde seit E10 (BTC, 14.10. 14:28 UTC, Kasse −4,14 $, gebucht −4,58 $, Differenz = doppelte Kaufgebühr, Befund 42, Kauf lag vor E9). Saldo 408,14 $ = `konto` (selbst nachgeprüft) | keine |
| A3 quant-statistiker | W7-Kennzahlen v6 (letzte 100 Runden) nachrechnen | ja, 84 s | **ja.** Mittel −0,438 %, n 100, s 1,915 %, Bereich [−1,075; +0,191] unabhängig per Block-Bootstrap bestätigt ([−1,10; +0,19]). Urteil „Vorsprung nicht belegt, Verlust auch nicht gesichert“ richtig | keine |
| A4 einstiegs-pruefer | v6-Runden der letzten 7 Tage je Kaufweg | ja, 41 s | **ja.** 12 Runden, alle drei Kaufwege netto im Minus (zusammen −25,94 $). n = 2–6 je Weg, keine Aussage möglich. Passt zum Bericht vom 14.10. | keine |
| A5 ausstiegs-pruefer | Wirken Puffer 0,25 und Nachzieh-Marge 0,10 (E13/L12)? | ja, 55 s | **ja.** In beiden Bots im Code (`risk/exit_rules.py`), nachgerechnet 1,109 / 1,262 / 1,569. W3 I1/I2 grün | Ob der laufende Prozess den neuen Code geladen hat, nur indirekt belegt (W5: Prozesse seit 12:03 Berlin) |
| A6 kosten-analyst | `gebuehren.json` gegen W3-Status | ja, 47 s | **ja.** Bitvavo 0,05 % stimmt mit W3, `geprueft_am` 1 Tag alt. GELB kommt nur von „Gebühren > Brutto im Monat“ bei 1 Verlustrunde je Bot (selbst nachgeprüft) | keine |
| A7 marktlage-stratege | heutige W1-Lage | ja, 45 s | **ja.** Stand 14.10.: SEITWÄRTS, Breite 50 %. BTC seit 08.10. SEITWÄRTS. Für AUFWÄRTS fehlen R +4 Punkte und 10 Punkte Marktbreite (selbst nachgeprüft: BTC R 1, ADX 27,5, ER 0,16) | keine |
| A8 risiko-manager | Risiko je Bot (offene Positionen, Größe, Verlust beim Stopp) | ja, 64 s | **teilweise.** Positionen richtig: v6 0 Positionen, v7 1 BTC-Position mit 95 % der Handelskasse (222,71 von 234,46 $, selbst nachgeprüft). **Falsch:** Verkaufsgebühr mit Taker 0,25 % (Bybit) statt 0,05 % (Bitvavo seit L9) gerechnet, ebenso „Maker 0,10 % bei v7“ | Ursache: `instanzen.json` stand noch auf dem Stand vom 14.10. 08:20 (Bybit, E7/L7). **Behoben** in dieser Sitzung, siehe 4 |
| A9 code-forensiker | Ist Befund 72 (v6 `watchdog.stop`) wirklich behoben? | ja, 82 s | **ja.** `live/watchdog.py:16` hat `stop()`, Aufruf `app.py:4527`, gleich wie v7. AST ok, CRLF erhalten, kein zweites Muster | keine |
| A10 advocatus-diaboli | Aussage „kumuliert 139 Runden, nicht entscheidbar“ aus `monatsmessung_2026-10.md` widerlegen | ja, 127 s | **ja.** Aussage hält (85 %). 139 exakt nachgezählt. Kritik: Verglichen wird auf 89–128 Runden (je Marktlage nur 31–90), nicht auf 139. Die Schwelle 570 ist nicht für 9 gleichzeitige Tests korrigiert (eher ≈ 1.000). Der Bericht sagt nicht, dass Oktober ein Teilmonat ist | keine |
| A11 epochen-verwalter | `config_epochs.json` beider Bots gegen `epochen\*.md` | ja, 38 s | **ja.** E8–E11 und L8–L10 sekundengenau gleich. Aktuell E13_kleinigkeiten (10:03:04 UTC) und L12_kleinigkeiten (10:03:05 UTC). In den Registrierungen von E12/L11 und E13/L12 fehlt ein Abschnitt „Start“ mit UTC-Zeit | keine |

## 3 · Fachliche Nebenbefunde aus den Tests (nicht in dieser Sitzung bearbeitet)

1. **[erklärt] v7-Telemetrie nachts ROT** (A1): In 24 h dreimal ROT (23:45, 02:40, 05:40 UTC), einmal 303 min ohne Daten [SICHER 95 %, `waechter.db` Tabelle `ereignisse`]. Laut `sitzung_stand.md` (Block 15.10. ~12:30, vorige Sitzung) waren das echte Ausfälle durch den Internetausfall in der Nacht 14./15.10. (ca. 23:10–10:40 Berlin), keine Fehlalarme. Alle drei Zeiten liegen in diesem Fenster. Der Vorschlag von A1, den code-forensiker anzusetzen, ist damit erledigt. [WAHRSCHEINLICH 85 %]
2. **[MITTEL] W7 meldet einen CUSUM-Bruch nicht:** Das v6-Fenster „letzte 30 Runden“ in `waechter.db` `vorsprung` hat `cusum_bruch: true` und den 95-%-Bereich [−1,721; −0,007], liegt also ganz unter null. In `status.json` stehen aber nur die Prüfungen „seit Epoche“ und „letzte 100“, beide GRÜN. Laut Masterprompt 6.1 ist ein CUSUM-Bruch ein Alarm. [WAHRSCHEINLICH 80 %, eigene Abfrage `vorsprung`, Stand 14.10. 20:22 UTC. Ob W7 das bewusst nicht meldet, habe ich nicht im Code geprüft]
3. **[MITTEL] W4 deckt die Runde nach E10 nicht ab** (A2): W4 zählt erst ab seinem ersten Lauf (14.10. 20:15 UTC). Die eine Runde nach E10 (14:28 UTC) fehlt dort. Außerdem springt `sparplan_btc_wert` in `konto` zwischen 0 und rund 166 $, die Sparplan-Bewertung fällt also zeitweise aus. Die Handelskasse betrifft das nicht. [SICHER 90 %]
4. **[MITTEL] W3-Gelb-Regel feuert bei jedem Verlustmonat** (A6): „Gebühren > Brutto“ ist bei negativem Brutto immer wahr. Die Spanne prüft W3 nur für BTC/ETH/SOL, nicht für DOGE (13,3 bp), ADA, XRP. [WAHRSCHEINLICH 85 %]
5. **[LOW] Monatsmessung:** n je Vergleich statt 139 angeben, Schwelle für 9 Tests korrigieren, Teilmonat kennzeichnen (A10). In den Registrierungen von E12/L11 und E13/L12 fehlt die Startzeit (A11). `trading_imperium_v7\e9_kontrolle.py:73` prüft noch auf den alten Wert 1,57 und meldet deshalb einen falschen Fehler (A5). In v6 laufen `app.py:4526-4527` ohne `try`: Wirft dort künftig ein Aufruf einen Fehler, wird wieder nichts gespeichert (A9).
6. **Erklärt, kein Befund:** A1 sah einen Widerspruch bei NEAR. Das Ereignis vom 14.10. 20:18 UTC sagt AUFWÄRTS → SEITWÄRTS, `status.json` zeigt aber AUFWÄRTS. Grund: Am 15.10. wurde die W1-Lage mit Halteband neu geschrieben (E4). Seitdem ist der 14.10. bei NEAR der erste von zwei Bestätigungstagen (`marktlage`: Label AUFWAERTS, roh SEITWAERTS, R 2). Das Ereignis stammt von vorher. [WAHRSCHEINLICH 85 %]

## 4 · Probleme des Testaufbaus und was geändert wurde

| Problem | Folge | Maßnahme |
|---|---|---|
| Python ist im Bash der Agenten nicht im PATH (`python` startet den Store-Platzhalter, nur `py` geht) | Ohne Hinweis scheitert jeder Rechenschritt | Im Test als voller Pfad mitgegeben. Neu: Hinweis `_python` in `instanzen.json`, den lesen alle Agenten zuerst |
| `instanzen.json` stand auf 14.10. 08:20 (Bybit-Gebühren, Epochen E7/L7) | A8 hat mit 0,25 % statt 0,05 % gerechnet | `instanzen.json` aktualisiert (Epochen E13/L12, Bitvavo 0,05 %). Alte Fassung in `archiv\instanzen_2026-10-14_0820.json` |
| Bei 5 Minuten Grenze haben A1 und A8 den Masterprompt nur teilweise gelesen | Im Test egal, für echte Prüfungen nicht | Die headless Läufe haben genug Zeit |
| Zeitgleich hat die vorige Sitzung um 12:13 Berlin Tickets in v6/v7 eingeworfen (`tickets.txt`, `ENTWICKLERHANDBUCH.md`) | Sah zuerst nach einem Schreibzugriff eines Agenten aus | Geklärt: Inhalt (W5 Energieschema, P0-7, P0-8, S7 Nachtrag 3) und Zeit (letzte Aktivität der Sitzung „MASTERPROMPT_AGENTEN Phase 0“ 10:13:52 UTC) passen zur vorigen Sitzung. Keiner der Test-Aufträge betraf diese Themen [WAHRSCHEINLICH 90 %] |

Gegenprobe „nichts geschrieben“: Im Prüfstand gab es nach dem Teststart außer `waechter.db` und `status.json` (Wächter) keine neue oder geänderte Datei. In den Bot-Ordnern gibt es außerhalb von `data_store`, Logs und Capture nur die E13-Dateien von 12:03–12:07 und die Ticket-Verarbeitung von 12:13. [SICHER 95 %, `find -newer`, Änderungszeiten]

## 5 · Nachtrag 12:55 · Leitstand headless

| Schritt | Ergebnis |
|---|---|
| Anmeldung des Kommandozeilen-Claude | Sven, `LEITSTAND_ANMELDEN.bat`, 12:37 Berlin. Vorher waren geplante Läufe nicht möglich (Probelauf 12:24 brach wegen der Anmeldung ab) |
| Rechteprobe 1 (12:37) | „nicht bestanden“, weil mein Kriterium zu streng war: Bash fehlte ganz statt „abgelehnt“ zu werden, und den Bot-Ordner hat der Agent selbst verweigert, die technische Sperre blieb ungeprüft. Probe verbessert |
| Rechteprobe 2 (12:40) | **bestanden** [SICHER 95 %]: Lesen im Bot-Ordner erlaubt, Schreiben in `berichte/` erlaubt, Schreiben in `daten/leitstand/` und in einem per `--add-dir` eingebundenen Attrappen-Ordner (steht für die Bot-Ordner) technisch abgelehnt, Bash nicht vorhanden, `.env`-Attrappe abgelehnt. Beleg: `daten/leitstand/rechteprobe_20261015_103948.json` |
| Erster echter Lauf über die Aufgabe `TI-Leitstand-Tag` (12:40–12:50) | Ergebnis 0, 22 Schritte, 3,46 $, Agenten A9 und A10 beauftragt, 0 Ablehnungen. Geschrieben nur `berichte/2026-10-15_lage.md`, `berichte/2026-10-15_lage.json` (alle Pflichtfelder laut Anhang A) und `berichte/2026-10-15_code.md` (A9). Telegram-Kurzfassung gesendet |
| Inhalt des Lageberichts | plausibel und belegt [WAHRSCHEINLICH 85 %]. Er greift Nebenbefund 3.2 (W7-CUSUM) selbst auf und findet zusätzlich: Die Kaufgröße zählt das Sparplan-BTC mit, v7 hat dadurch 95 % der Handelskasse in einer Münze; W2 zeigt bei „Korb +nan %“ grün; nach dem Internetausfall waren die v7-Kurse etwa 1 h eingefroren (Vermutung). Frage 4 im Bericht (warum der Lauf um 12:24 abbrach) ist beantwortet: Es fehlte die Anmeldung |
| Anpassung danach | Budget-Deckel Tag 5 → 8 $, Woche 30 → 40 $. Ein erreichter Deckel bricht den Lauf ohne Bericht ab |

## 6 · Selbstbewertung

8/10. Jeder Agent ist einmal gelaufen, und die Kernzahlen habe ich bei fünf Agenten selbst nachgeprüft. Nicht geprüft habe ich die Antworten von A4, A9 und A10 im Detail. Die Mini-Aufträge zeigen, dass die Agenten laufen, aber nicht, wie sie in einer tiefen Prüfung arbeiten.
