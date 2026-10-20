# Zahlenbuch — die Kernzahlen

**Automatisch erzeugt 20.10.2026 00:10 UTC mit `python zahlenbuch.py --md`. Nicht von Hand ändern.**

Das ausführliche Zahlenbuch mit allen Abschnitten steht in `ZAHLENBUCH.pdf`. Diese Fassung trägt die Zahlen, die man nachschlagen und vergleichen können muss.

Es wird nichts geschönt und nichts hochgerechnet. Wo die Fallzahl nicht reicht, steht das dabei.

---

## Wo wir stehen

| | |
|---|---|
| Aktuelle Epoche | `E14_kaufgroesse_handelsgeld` |
| Beginn (UTC) | 2026-10-15T20:35 |
| Läuft seit | 4.1 Tagen |

*Quelle: `config_epochs.json`. Auswertungen dürfen nur **innerhalb** einer Epoche verglichen werden.*

---

## Zielgrößen

| Kennzahl | ist | Ziel | |
|---|---:|---:|---|
| Erwartungswert je Trade | -0.188 | 0.3 | verfehlt |
| Gewinner / Verlierer | +0.841 | 1.27 | verfehlt |
| Profit-Faktor | +0.717 | 1.2 | verfehlt |
| Verschenkte Bewegung | +1.379 | 1.0 | verfehlt |
| Größter Rückschlag (mit Sparplan-BTC) | 33.36 | 15.0 | verfehlt |
| Größter Rückschlag (ohne) | 23.21 | 15.0 | verfehlt |
| Trefferquote *(bewusst ohne Ziel)* | 46.0 % | – | – |

*Quelle: `data_store/trades_v5.json`, **365 Verkäufe** mit Ergebnisangabe, davon 186 mit Höchststand. Netto = brutto minus 0.505 % Kosten je Runde. Ziele aus `config_zielgroessen.json`.*

Ø Gewinner **+1.037 %**, Ø Verlierer **−1.233 %**. Die Trefferquote ist fast am Ziel — das Problem ist das Verhältnis der beiden. Siehe `BOT-HANDBUCH.md` 4.60.

---

## Ausstiege gegenüber der Kostenschwelle

| Bereich (brutto) | Ausstiege | davon Trailing |
|---|---:|---:|
| unter -2,0 % | 59 | 0 |
| -2,0 bis -0,5 % | 18 | 1 |
| -0,5 bis 0 % | 2 | 0 |
| 0 bis 0,505 % | 118 | 89 |
| 0,505 bis 1,0 % | 70 | 51 |
| 1,0 bis 2,0 % | 65 | 42 |
| ueber 2,0 % | 33 | 18 |

**89 von 201 Trailing-Ausstiegen (44 %) enden brutto im Plus und netto im Minus.** Die Ratsche wird ab +1,2 % Höchststand scharf und hält 1,0 % Abstand; rentabel wird sie erst ab **+1,52 %**. Dazwischen verliert jeder Ausstieg rechnerisch.

Herleitung: `BOT-HANDBUCH.md` 4.64, `GEFUNDENE-PROBLEME.md` 45.

---

## Datenlage

| Quelle | Umfang |
|---|---|
| Kaufprüfungen | 979.139 |
| Schatten-Signale | 3.243 |
| Nachlauf-Ereignisse | 76.000 |
| Positionsverläufe | 146.765 |

---

*Erzeugt aus `data_store/telemetrie.db`, `schatten_universum.db`, `nachlauf.db`, `positionsverlauf.db`, `trades_v5.json`, `config_epochs.json`, `config_zielgroessen.json`. Alle Zeiten UTC. Kein Wert wurde von Hand eingetragen.*
