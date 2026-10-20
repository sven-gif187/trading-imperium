# Zahlenbuch — die Kernzahlen

**Automatisch erzeugt 20.10.2026 00:07 UTC mit `python zahlenbuch.py --md`. Nicht von Hand ändern.**

Das ausführliche Zahlenbuch mit allen Abschnitten steht in `ZAHLENBUCH.pdf`. Diese Fassung trägt die Zahlen, die man nachschlagen und vergleichen können muss.

Es wird nichts geschönt und nichts hochgerechnet. Wo die Fallzahl nicht reicht, steht das dabei.

---

## Wo wir stehen

| | |
|---|---|
| Aktuelle Epoche | `L13_kaufgroesse_handelsgeld` |
| Beginn (UTC) | 2026-10-15T20:35 |
| Läuft seit | 4.1 Tagen |

*Quelle: `config_epochs.json`. Auswertungen dürfen nur **innerhalb** einer Epoche verglichen werden.*

---

## Zielgrößen

| Kennzahl | ist | Ziel | |
|---|---:|---:|---|
| Erwartungswert je Trade | -0.821 | 0.3 | verfehlt |
| Gewinner / Verlierer | +0.265 | 1.27 | verfehlt |
| Profit-Faktor | +0.208 | 1.2 | verfehlt |
| Verschenkte Bewegung | +1.474 | 1.0 | verfehlt |
| Größter Rückschlag (mit Sparplan-BTC) | 20.96 | 15.0 | verfehlt |
| Größter Rückschlag (ohne) | 24.30 | 15.0 | verfehlt |
| Trefferquote *(bewusst ohne Ziel)* | 44.0 % | – | – |

*Quelle: `data_store/trades_v5.json`, **25 Verkäufe** mit Ergebnisangabe, davon 25 mit Höchststand. Netto = brutto minus 0.505 % Kosten je Runde. Ziele aus `config_zielgroessen.json`.*

Ø Gewinner **+0.490 %**, Ø Verlierer **−1.851 %**. Die Trefferquote ist fast am Ziel — das Problem ist das Verhältnis der beiden. Siehe `BOT-HANDBUCH.md` 4.60.

---

## Ausstiege gegenüber der Kostenschwelle

| Bereich (brutto) | Ausstiege | davon Trailing |
|---|---:|---:|
| unter -2,0 % | 8 | 0 |
| -2,0 bis -0,5 % | 1 | 0 |
| -0,5 bis 0 % | 1 | 0 |
| 0 bis 0,505 % | 4 | 2 |
| 0,505 bis 1,0 % | 6 | 2 |
| 1,0 bis 2,0 % | 5 | 4 |
| ueber 2,0 % | 0 | 0 |

**2 von 8 Trailing-Ausstiegen (25 %) enden brutto im Plus und netto im Minus.** Die Ratsche wird ab +1,2 % Höchststand scharf und hält 1,0 % Abstand; rentabel wird sie erst ab **+1,52 %**. Dazwischen verliert jeder Ausstieg rechnerisch.

Herleitung: `BOT-HANDBUCH.md` 4.64, `GEFUNDENE-PROBLEME.md` 45.

---

## Datenlage

| Quelle | Umfang |
|---|---|
| Kaufprüfungen | 53.774 |
| Schatten-Signale | 0 |
| Nachlauf-Ereignisse | 7.723 |
| Positionsverläufe | 2.095 |

---

*Erzeugt aus `data_store/telemetrie.db`, `schatten_universum.db`, `nachlauf.db`, `positionsverlauf.db`, `trades_v5.json`, `config_epochs.json`, `config_zielgroessen.json`. Alle Zeiten UTC. Kein Wert wurde von Hand eingetragen.*
