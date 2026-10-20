# LAGE — was gerade läuft

**Automatisch erzeugt 20.10.2026 00:10 UTC mit `lage_erzeugen.py`. Nicht von Hand ändern.**

Diese Seite ist die Eingangstür ins Projekt. Sie beantwortet drei
Fragen: Was läuft? Welche Daten existieren? Was ist gerade eingefroren?

Für das *Warum* siehe `BOT-HANDBUCH.md`, für offene Punkte
`GEFUNDENE-PROBLEME.md`, für die Chronik `ENTWICKLERHANDBUCH.md`.

---

## Laufende Prozesse

| Was | Status |
|---|---|
| Bot (`app.py`) | läuft |
| Forschungs-Sammler | läuft |
| Täglicher Sammler | läuft nicht |
| Schatten-Universum | läuft |

## Konfiguration

| | |
|---|---|
| Modus | paper |
| Münzen | BTC/USDC, ETH/USDC, SOL/USDC |
| Zeitrahmen | 1h |
| Takt | 12 s |
| Aktiver Modus | balanced |
| Regel-Schalter | `trend_exit`=SHADOW, `drawdown_stopp`=SHADOW, `notbremse_tagesreset`=SHADOW, `verlustsperre_aufhebung`=SHADOW, `auto_verteidigung`=SHADOW, `nupl_bremse`=SHADOW, `sammel_notbremse`=SHADOW |

## Epochen (Regelwerks-Abschnitte)

Auswertungen dürfen **nur innerhalb** einer Epoche verglichen werden.

| Epoche | ab (UTC) |
|---|---|
| `E0_baseline` | 2026-05-01T00:00 |
| `E1_stufentrailing` | 2026-06-22T00:00 |
| `E2_regimefilter_aktiv` | 2026-06-24T22:56 |
| `E3_regimefilter_scharf` | 2026-06-26T07:03 |
| `E4_btc_only` | 2026-08-07T00:16 |
| `E5_balanced_zurueck` | 2026-08-10T04:26 |
| `E6_messfenster` | 2026-08-13T13:21 |
| `E7_filter_schaerfer` | 2026-08-15T07:47 |
| `E8_angleich_v7` | 2026-10-14T09:18 |
| `E9_kaufgebuehr_einfach` | 2026-10-14T09:35 |
| `E10_kostenlatte_bitvavo` | 2026-10-14T13:58 |
| `E11_trailstart_wirksam` | 2026-10-14T19:55 |
| `E12_puffer_pflichtfelder` | 2026-10-15T09:35 |
| `E13_kleinigkeiten` | 2026-10-15T10:03 |
| `E14_kaufgroesse_handelsgeld` | 2026-10-15T20:35 |

**Aktuelle Epoche: `E14_kaufgroesse_handelsgeld`**

## Vorhandene Daten

| Quelle | Umfang |
|---|---|
| `telemetrie.db` → Kaufprüfungen | 979139 Zeilen |
| `telemetrie.db` → Marktdaten-Zeitreihe | 4958 Zeilen |
| `telemetrie.db` → Schatten-Notizen | 7077 Zeilen |
| `telemetrie.db` → Schatten-Ausstiege | 124 Zeilen |
| `telemetrie.db` → Lern-Ereignisse | 154 Zeilen |
| `telemetrie.db` → Hintergrund-Läufe | 3217 Zeilen |
| … davon `ml_model` | 3483 |
| … davon `ensemble_technical` | 3507 |
| `schatten_universum.db` | 3243 Signale auf 18 Münzen |
| `nachlauf.db` | 76000 Ereignisse, davon 594 Ausstiege (590 mit 24-h-Kurs) |
| `trades_v5.json` | 1287 Einträge, 594 Verkäufe |
| Forschungs-Sammler | 70 Tage, zuletzt 2026-10-20 (91 Dateien, 18 Münzen) |

**Der Sammler erfasst je Münze:** Orderbuch, Ticker (mit `spread_bp`), Trades, Funding, offene Positionen — alle ~60 Sekunden.

## Messwerkzeuge (alle nur lesend)

| Aufruf | beantwortet |
|---|---|
| `python epoch_report.py` | Ergebnis je Regelwerks-Epoche |
| `python ml_notizbuch_auswertung.py` | Hat das KI-Modell Vorhersagekraft? |
| `python ensemble_notizbuch_auswertung.py` | Würde ein echter technical-Wert Käufe ändern? |
| `python schatten_universum.py --status` | Was auf allen beobachteten Münzen gesammelt wurde |
| `python telemetrie_pruefen.py` | Doppelverkäufe, Positionsabgleich |
| `python regel_waechter_bestaetigen.py` | Stehen die Regel-Schalter wie hinterlegt? |
| `python stoploss_analyse.py` | Warum laufen Positionen ins Minus? |
| `python lage_erzeugen.py` | Diese Seite neu schreiben |

## Sicherung

| | |
|---|---|
| Git | letzter Stand: 05dbc72 2026-09-29 05:05:44 +0200 Taegliche Systempruefung auch fuer v6 (tagesch |

Sicherung erneuern: `python sicherung.py <Ziel>`

---

*Diese Seite wird von `lage_erzeugen.py` erzeugt. Änderungen von Hand gehen beim nächsten Lauf verloren.*
