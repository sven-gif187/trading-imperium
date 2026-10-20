# LAGE — was gerade läuft

**Automatisch erzeugt 20.10.2026 00:07 UTC mit `lage_erzeugen.py`. Nicht von Hand ändern.**

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
| Regel-Schalter | `trend_exit`=SHADOW |

## Epochen (Regelwerks-Abschnitte)

Auswertungen dürfen **nur innerhalb** einer Epoche verglichen werden.

| Epoche | ab (UTC) |
|---|---|
| `L1_echtgeld_start` |  |
| `L2_fraktal_tor` | 2026-09-15 07:26 |
| `L3_fraktal_komplett` | 2026-09-15 12:23 |
| `L4_warteauftraege_live` | 2026-09-16 23:43 |
| `L5_zurueck_auf_papier` | 2026-09-25T14:28 |
| `L6_abschalten_speichert` | 2026-09-25T21:32 |
| `L7_svens_drei_entscheidungen` | 2026-09-25T21:56 |
| `L8_einheitsgebuehr` | 2026-10-14T09:51 |
| `L9_kostenlatte_bitvavo` | 2026-10-14T13:59 |
| `L10_trailstart_wirksam` | 2026-10-14T19:56 |
| `L11_puffer_pflichtfelder` | 2026-10-15T09:35 |
| `L12_kleinigkeiten` | 2026-10-15T10:03 |
| `L13_kaufgroesse_handelsgeld` | 2026-10-15T20:35 |

**Aktuelle Epoche: `L13_kaufgroesse_handelsgeld`**

## Vorhandene Daten

| Quelle | Umfang |
|---|---|
| `telemetrie.db` → Kaufprüfungen | 53774 Zeilen |
| `telemetrie.db` → Marktdaten-Zeitreihe | 2202 Zeilen |
| `telemetrie.db` → Schatten-Notizen | 3336 Zeilen |
| `telemetrie.db` → Schatten-Ausstiege | 88 Zeilen |
| `telemetrie.db` → Lern-Ereignisse | 30 Zeilen |
| `telemetrie.db` → Hintergrund-Läufe | 42 Zeilen |
| … davon `ml_model` | 1665 |
| … davon `ensemble_technical` | 1671 |
| `schatten_universum.db` | 0 Signale auf 0 Münzen |
| `nachlauf.db` | 7723 Ereignisse, davon 31 Ausstiege (30 mit 24-h-Kurs) |
| `trades_v5.json` | 51 Einträge, 25 Verkäufe |

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
| Git | letzter Stand: e62446d 2026-09-29 05:05:03 +0200 Taegliche Systempruefung fuer v6 und v7 (tages |

Sicherung erneuern: `python sicherung.py <Ziel>`

---

*Diese Seite wird von `lage_erzeugen.py` erzeugt. Änderungen von Hand gehen beim nächsten Lauf verloren.*
