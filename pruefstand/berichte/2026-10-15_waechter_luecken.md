<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Wächter-Lücken geschlossen · 15.10.2026 (Sitzung „Wächter-Lücken“, 12:53–22:50 Berlin, mit Pause am Nutzungslimit)

**Fünf Wächter haben bei Alarm oder Rechenfehler GRÜN gezeigt. Alle fünf sind geändert. Je Wächter gibt es 3 Tests (Reproduktion, Normalfall, Grenzfall) im `--selbsttest`, alle bestanden. Dazu je ein Probelauf auf echten Daten.** [SICHER 95 %]

Grundsatz: Ein Wächter, der etwas nicht berechnen kann oder dessen Alarmregel greift, zeigt nicht GRÜN.
Die alten Fassungen liegen in `archiv/waechter_vor_failopen_2026-10-15/` (dazu `status_vorher.json`). In den Bot-Ordnern habe ich nichts geändert. v6 und v7 sind getrennt geblieben, neu ist die eigene Instanz `labor` (W3).

| Wächter | Problem | Ursache | Änderung | Tests | Probelauf echte Daten |
|---|---|---|---|---|---|
| **W7** `w6_w7_nachlauf_vorsprung.py` | `cusum_bruch = true` in allen Fenstern, Ampel GRÜN | Der Bruch wurde nur im Fenster „seit Epoche“ (0 Runden) ausgewertet, nie in den rollenden Fenstern | Neue Prüfung **`W7_cusum`**: Bruch in letzte 30/60/100 mit n ≥ 30 → **GELB**, mit Vermerk, wie viele Runden vor E10/L9 gekauft wurden (alte Kostenwelt). Unter 30 Runden GRÜN „nicht entscheidbar“ (Masterprompt 6.1). Neues Feld `runden_vor_epoche` in `vorsprung` | 3/3 | Echter Lauf 10:56 UTC: **v6 GELB** „nur Alt-Daten: alle 30/60/100 Runden vor E10“. v7 GRÜN „Bruch nur bei 17 Runden – nicht entscheidbar“. `status.json` W7 = GELB |
| **W2** `w2_vergleich.py` | 14.10.: „Korb +nan %“ GRÜN | W1 lief nachts ohne Netz nicht, der Tagesschluss 14.10. fehlte in `daten_w1`. `korb_rendite` gab `nan`, und `nan <= -5` ist falsch, also GRÜN (Lauf 15.10. 02:35) | Korb nur mit allen 3 Münzen (vorher still aus den vorhandenen gemittelt). `nan` → M1 **GELB „nicht berechenbar: Korb 14 T fehlt (…)“**. Keine `markt_historie` → M2 GELB | 3/3 | Nur lesend: echte Werte unverändert (Korb −7,96 %, v6 +1,25 / v7 +3,36 Punkte). Stand 02:35 auf echten CSVs nachgestellt → beide GELB |
| **W4** `w4_kasse.py` | `sparplan_btc_wert` zeitweise 0 | `preise()` schluckt Netzfehler, `pr.get("BTC", 0)` bewertet mit 0. Betroffen 14.10. 22:07 bis 15.10. 08:17 UTC, 11 Zeilen je Bot (v7 auch `positionen` 0) | Neue Funktion `kontozeile()`: Fehlt ein nötiger Preis, wird **keine Zeile mit 0** geschrieben. Die Prüfung `konto` meldet dann **GELB „nicht berechenbar“**, der nächste Lauf versucht es nach 5 min erneut. Takt je Instanz, `konto` steht jetzt immer im Status | 3/3 (+4 alte) | Echter Lauf grün. Netzausfall auf echten Bot-Daten nachgestellt → GELB statt 0. Geplanter Lauf 20:17 UTC: v6 168,31 $ / v7 234,09 $ |
| **W3** `w3_kosten.py` | (a) „Gebühren > Brutto“ feuert bei jedem Verlustmonat. (b) Spanne nur BTC/ETH/SOL | (a) Bei Brutto < 0 ist die Regel immer wahr. (b) Fest verdrahtete Liste, fehlende Messung wurde still übersprungen | (a) siehe unten. (b) Alle 6 Bitvavo-Märkte: Bots je **gehandelter** Münze (`config trading.coins`), XRP/ADA/DOGE nur als Hinweis. Neue Instanz **`labor`** (S7 handelt alle 6) gegen `SPANNE_BP` aus `labor/papier/papier_tag.py`. Keine Messung in 24 h oder keine Annahme → GELB | 3/3 + 3/3 (+4 alte) | Nur lesend (Bots wurden gerade gepatcht). Monat: v6 13 %, v7 14 % des Verlusts sind Gebühren → GRÜN. Spanne: Labor alle 6 GRÜN (x0,73–1,11) |
| **W5** `w5_betrieb.py` | Netzausfall erschien als „Datei still“ ROT | v7 schreibt Telemetrie nur bei neuen Kursen. Ohne Netz: „zuletzt vor 303 min“ ROT (65 Läufe). Die Internetprüfung wurde nach 15 min ROT | Netzprüfung läuft zuerst. Ist Binance (Kursquelle) weg oder erst seit < 30 min zurück, werden ROT-Befunde von telemetrie, nachlauf, schatten und positionsverlauf zu **GELB „Datenquelle/Internet weg“**. Prozess, Port, bot_state und system_log bleiben scharf. `internet` ist höchstens GELB | 3/3 (+4 alte) | Nacht 14./15.10. aus `betrieb` nachgespielt: **65 ROT → 1 ROT**. Live mit Kopie des Zustands: alles grün |

## W3-Monatsregel · neuer Vorschlag (umgesetzt, Startwert [VERMUTUNG])

| Lage im Monat | alt | neu |
|---|---|---|
| Brutto > 0, Gebühren ≤ Brutto | GRÜN | GRÜN, mit Kostenquote |
| Brutto > 0, Gebühren > Brutto (Kosten machen aus Gewinn Verlust) | GELB | **GELB** |
| Brutto ≤ 0, Gebühren > 50 % des Nettoverlusts (Kosten sind die Hauptursache) | GELB | **GELB** |
| Brutto ≤ 0, Gebühren ≤ 50 % des Nettoverlusts (Verlust schon vor Kosten) | GELB | GRÜN mit Hinweis „Ursache ist der Handel, Vorsprung: W7“ |

Warum: W3 soll Kostenprobleme melden. Ein Verlust schon vor Kosten ist kein Kostenproblem, sondern fehlender Vorsprung, und den bewertet W7. Sonst ist W3 in jedem Verlustmonat gelb, und ein echter Kostenalarm geht darin unter. Abweichung vom Wortlaut in Masterprompt 6.1, dort heißen die Schwellen „Startwerte, A6 eicht“. [WAHRSCHEINLICH 80 %, dass das die sinnvollere Regel ist]

## W4 · Soll W4 ab Epochenstart statt ab seinem ersten Lauf zählen? **Nein** [WAHRSCHEINLICH 85 %]

- Die einzige Runde in der Lücke (v6 BTC, Verkauf 14.10. 14:28 UTC) habe ich auf drei Wegen nachgeprüft: Das Journal stimmt mit der Order-Historie überein (Menge, Gebühr 0,0864 $). Die Telemetrie-Kasse ging von 235,43 auf 408,14 $, das sind +172,71 $ = Erlös − Gebühr. v7 hatte in der Lücke keine Buchung (Kasse 12,03 → 12,03 $). [SICHER 95 %]
- „Gebucht gegen Kasse“ und „Pflichtfelder“ zählen schon heute ab Epoche (E9 bzw. E12/L11). Nur Saldo und Orders laufen ab dem ersten W4-Lauf.
- Ein Epochen-Anker bräuchte als Startwert die Telemetrie-Kasse des Bots. Dann hinge W4 an einer Bot-Datei, die er eigentlich prüfen soll. Die Lücke ist einmalig und jetzt geschlossen.
- Achtung für später: `order_history.json` hält nur 500 Einträge (v6 ist voll). Bei rund 3,4 Orders am Tag reicht das etwa 5 Monate ab W4-Start, danach drohen falsche „ohne Order“-Meldungen. [VERMUTUNG 60 %]

## Wann es wirkt

Die Aufgaben rufen die geänderten Dateien direkt auf. W4 und W5 wirken also ab dem nächsten 5-Minuten-Lauf, W3 stündlich, W2 um 02:35 und W6/W7 um 02:50 (das ist der erste Lauf dieser Aufgabe überhaupt). Geprüft: Der geplante W4-Lauf hat um 20:17 UTC mit dem neuen Code geschrieben, der geplante W5-Lauf um 20:45:56 UTC ist mit dem neuen Code durchgelaufen (GRÜN, 21 Prüfungen, Ergebnis 0).

## Nebenbefunde (nicht in dieser Sitzung bearbeitet)

1. **[erklärt] Beide Bots waren ab 18:11 UTC (20:11 Berlin) aus.** W5 meldete das um 18:15:56 UTC ROT. Die Hauptsitzung hat die Ursache gefunden: Das Update der Claude-App hat die Bots beendet, weil sie aus einer Sitzung gestartet worden waren. Neue Regel: Bots nur über `TI-Bots-Autostart` starten (`sitzung_stand.md`, Block 22:45). W5 hat hier richtig ROT gezeigt.
2. **[MITTEL] W4 v7 `pflichtfelder` GELB:** **Berichtigt 17.10.:** Nicht nur der MANUAL_SELL (15.10. 11:00:45 UTC), sondern alle 4 v7-Verkäufe seit L11 haben kein `stop_initial` und kein `trailing_stop_pct`, auch TRAILING_STOP (15.10. 23:13, 16.10. 18:44) und STOP_LOSS (16.10. 16:02). Der Befund-88-Fix ist in v7 für diese beiden Felder unwirksam. v6 hat 1 Verkauf, vollständig. [SICHER 95 %]
3. **[MITTEL] W6 reißt W7 mit:** Ohne Netz bricht `kerzen()` (ccxt) ab. Dann läuft auch W7 nicht, und der Status bleibt auf dem alten Grün stehen. Nicht geändert (eine Änderung je Wächter).
4. **[MITTEL] Altes Grün fällt niemandem auf:** Der W6/W7-Status war 26 h alt. W5 `aufgaben_ergebnis` zählt 267011 („noch nie gelaufen“) als ok. Vorschlag: W5 prüft das Alter jedes Wächter-Eintrags in `status.json`.
5. **[LOW] Spannen-Annahme der Bots für DOGE** 1,44 bp, gemessen 13,7 bp (x9,5), ADA x1,8. Das wirkt erst, wenn ein Bot diese Münzen handelt. W3 zeigt es als Hinweis.

## Nachtrag 22:55 · W5 prüft TI-Bots-Neustart

Auf Wunsch der Phase-6-Sitzung steht `TI-Bots-Neustart` (F5b: `bots_starten.py --takt` alle 15 min) jetzt in der W5-Liste `AUFGABEN`. Fehlt die Aufgabe, meldet W5 ROT „fehlen“. Test: Lesetest „8 vorhanden“, die Gegenprobe mit einer erfundenen Aufgabe ergibt ROT, Selbsttest bestanden. Das Ergebnis der Aufgabe deckt `aufgaben_ergebnis` schon ab (alle TI-*). Nicht umgesetzt (kein Muss): bei „app.py läuft NICHT“ den letzten Neustart aus `autostart/autostart.log` anzeigen.

## Selbstbewertung
8/10. Jeder Fix ist an dem echten Fall reproduziert, der den Fehler ausgelöst hat. Abzüge: W2 und W3 habe ich nur lesend auf echten Daten geprüft (die Bots wurden gerade gepatcht). Bei W5 bleibt ein Rot-Lauf aus der Nacht übrig, weil der Ausfallbeginn unsicher ist (Log 23:47 UTC, `sitzung_stand.md` „ca. 23:10 Berlin“).
