<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
**BERICHTIGT 15.10. ~14:45:** v7 hat um 08:29 UTC nicht mit einem alten Kurs gekauft, sondern mit dem Kurs vom falschen Paar: BTC/USDT statt BTC/USDC, weil der USDC-Abruf kurz scheiterte und der Code still auf USDT auswich. Die Füllung war trotzdem ein echter USDC-Preis, der Schaden ist praktisch null. Die Befunde 3 und 4 unten waren falsch, siehe Abschnitt „Berichtigung“.

# Kurse nach dem Internetausfall · v7 · 15.10.2026

Auslöser: Lagebericht `berichte/2026-10-15_lage.md` Punkt 3 („v7-Kurse nach dem Ausfall rund 1 h eingefroren, Kauf um 08:29 UTC zu altem Kurs?“). Nur gelesen, an den Bots nichts geändert. Nur **v7**, v6 hatte in dieser Zeit keine Position und hat nicht gekauft.

## Befunde

| # | Befund | Beleg | Konfidenz |
|---|---|---|---|
| 1 | Die Zeitstempel in `v7\data_store\system.log` sind **UTC**. | Neustart E13/L12 um 10:03 UTC steht als `[2026-10-15T10:03:18] … Konfiguration geladen` (Z. 38502) | [SICHER 95 %] |
| 2 | Das Netz war nicht um 07:28 stabil zurück, sondern **wackelte bis etwa 08:37 UTC**. | WebSocket verbunden 07:21, Abbruch 07:23 und 07:27, erst wieder 08:29:17 verbunden, danach zweimal „ping/pong timed out“ und `getaddrinfo failed` bis 08:37:08 (Z. 28214–32200). Der Abruf der Stundenkerzen scheiterte ab 14.10. 23:47 fast durchgehend bis 08:37 UTC (5.185 Fehlerzeilen, kurze Pausen nur 07:20–07:26 und 08:29–08:34). | [SICHER 90 %] |
| 3 | Der Kauf BTC/USDC um **08:29:47 UTC** nahm als Marktpreis **81.257,69 $**. Der echte BTC/USDC-Kurs lag in dieser Minute bei **81.142,52–81.180,92 $** (Binance-Minutenkerze). 81.257,69 kam bei BTC/USDC zuletzt zwischen **07:42 und 08:08 UTC** vor. Der Bezugskurs war also 20–45 Minuten alt und lag rund 0,1 % zu hoch. | Log Z. 31764 („Limit 81176.43 $ (0,10 % unter 81257.69 $)“), öffentliche Binance-Kerzen 1m und 1h, abgerufen 15.10. | [WAHRSCHEINLICH 85 %] |
| 4 | **Ursache:** `fetch_current_price` gibt bei gescheitertem Abruf den alten Wert aus dem Zwischenspeicher zurück, **ohne Altersangabe**. Das steht so im Bot selbst (`app.py:3729-3732`, Befund 95). Befund 95 sichert nur das Aufschreiben in die Zeitreihe ab, nicht die Kaufentscheidung. Der Kaufpreis kommt aus `snapshot.close` (`app.py:893/918/927`). | Code gelesen | [WAHRSCHEINLICH 80 %]: Den Weg von `snapshot.close` bis zum Zwischenspeicher habe ich nicht Zeile für Zeile verfolgt |
| 5 | **Die Füllung selbst war realistisch:** Das Limit 81.176,43 $ lag in der echten Spanne der Minute 08:29 (81.142,52–81.180,92). Gefüllt wurde 9 s später zum Limit. Der Vorteil „0,10 % unter Markt“ war aber nur Schein. In Wahrheit lag das Limit auf Marktpreis. Geldwirkung ≈ 0 (höchstens +0,02 % gegen einen Sofortkauf bei ≈ 81.160). | Log Z. 31766–31768, Minutenkerze | [SICHER 90 %] |
| 6 | **Die Verlustbremse lief nicht auf alten Kursen:** Von 07:28 bis 08:29 hatte v7 keine Position (`[BALANCE] Positionen: 0.00$`, z. B. Z. 31730). Der erste Überwachungseintrag nach dem Kauf (08:30:20, „Aktuell 81191.92“) passt zur echten Minute 08:30 (81.174,57–81.219,75). | Log, Minutenkerze | [SICHER 90 %] |
| 7 | **Nebenbeleg KG1:** Das Signal rechnete den Kauf mit **117,44 $** (50 % des Handelsgelds 234,88 $). Danach wurde der Betrag mit Sparplan auf **232,91 $** überschrieben und erst durch die Bargeld-Grenze auf 223,14 $ gekappt. | Log Z. 31757–31763 (`SIGNAL … BUY 117.44$`, `SCHATTEN-SIZING echt 232.91$`, `SIZING-CAP 232.91$ -> 223.14$`) | [SICHER 95 %] |

## Was das heißt

- **Die Fehlerklasse ist echt:** Nach einem Netzausfall kann v7 auf einem alten Kurs kaufen, ohne es zu merken. Hier ging es glimpflich aus, weil der Kurs nur 0,1 % daneben lag. Bei einem schnellen Markt nach einem langen Ausfall kann das mehrere Prozent sein. v6 hat denselben Code-Weg (`data/market_data.py` ohne Zeitstempel). Nicht geprüft, [WAHRSCHEINLICH 75 %].
- **Fix-Vorschlag** (Bot-Änderung, also nur mit Epoche):
  - Zum Zwischenspeicher-Kurs einen Zeitstempel ablegen.
  - **Käufe sperren**, wenn der Kurs älter als z. B. 120 s ist. Log: „Kauf gesperrt: Kurs X s alt“.
  - Verkäufe und Verlustbremse bleiben bewusst ungesperrt, aus demselben Grund wie in Befund 95.
  - Das passt als Kleinkram in die nächste Bot-Änderung zusammen mit KG1. Tests:
    1. Kurs 300 s alt → kein Kauf.
    2. Kurs 5 s alt → Kauf wie heute.
    3. Kurs alt und offene Position im Minus → Verlustbremse greift weiter.
- **Für W5:** Die „1 h eingefroren“ nach 07:28 war kein Hänger des Bots, sondern das wackelnde Netz.

## Was ich NICHT weiß

- Wie alt die Stundenkerzen waren, auf denen das Signal (RSI 42, MACD-Kreuz, ADX 43) um 08:29:47 gerechnet wurde. Zwischen 08:29:00 und 08:34 gibt es keine Fehlerzeile, ein frischer Abruf ist also möglich.
- Ob v6 denselben Fehler hat (Code nicht gelesen).

Selbstbewertung 8/10: Zeitzone, Kurs und Füllung sind auf zwei Wegen belegt (Log und Börsenkerzen). Die Ursachenkette im Code ist nicht vollständig verfolgt.

## Berichtigung (15.10.2026 ~14:45, nach Svens Entscheidung zur Kaufsperre, vor jedem Einspielen)

Die Befunde 3 und 4 oben sind **falsch**. Ich hatte die Ursache aus dem Log erschlossen, ohne den Kaufweg im Code zu verfolgen.

| # | Richtig | Beleg | Konfidenz |
|---|---|---|---|
| B1 | Der Kaufpreis im Signal-Weg kommt **nicht** aus dem Kurs-Zwischenspeicher, sondern aus frisch geholten 5-Minuten-Kerzen (`snapshot.close`, `data/market_data.py` `fetch_snapshot`). Scheitert der Abruf für BTC/USDC, nimmt der Code **ohne Meldung** BTC/USDT (`v7 data/market_data.py:112`, `v6 :90`: `alt = symbol.replace("USDC", "USDT")`). | Code gelesen | [SICHER 90 %] |
| B2 | Um 08:29:47 stand in der Telemetrie `entry_price` 81.257,69 bei `daten_alter_sec` **0,0**. 12 s später stand dort 81.180,92, genau das Hoch der USDC-Minute 08:29. 81.257,69 liegt in der USDT-Minute 08:29 (81.246,78–81.290,48), nicht in der USDC-Minute. | `v7 telemetrie.db` Tabelle `evaluations` (nur lesend), Binance-Minutenkerzen | [WAHRSCHEINLICH 90 %] |
| B3 | **Alte Kurse kamen im Oktober nicht vor:** `daten_alter_sec` war höchstens 21,6 s (v7, 28.598 Kaufprüfungen) bzw. 21,0 s (v6, 221.605). Eine Sperre „Kurs älter als 2 Minuten“ hätte im Oktober **nie** gegriffen, auch nicht am 15.10. um 08:29. | `evaluations` beider Bots seit 01.10. | [SICHER 90 %] |
| B4 | Die Übereinstimmung von 81.257,69 mit USDC-Kursen von 07:42–08:08 war Zufall. Befunde 5–7 (Füllung realistisch, Verlustbremse nicht betroffen, KG1-Beleg) bleiben richtig. | – | [WAHRSCHEINLICH 85 %] |

**Folge für die Kaufsperre:** Sven hat am 15.10. eine Sperre „kein Kauf, solange der Kurs älter als 2 Minuten ist“ entschieden, auf Grundlage der falschen Befunde 3 und 4. Sie hätte das Ereignis nicht verhindert. Die passende Regel wäre: **kein Kauf, wenn der Kurs nur vom Ersatzpaar USDT kommt.** Nichts eingespielt, Rückfrage an Sven.
