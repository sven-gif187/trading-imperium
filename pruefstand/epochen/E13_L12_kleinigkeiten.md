<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v6 Epoche E13 · v7 Epoche L12 · „Nachzieh-Marge 0,10 und Kleinigkeiten“

Registriert: 15.10.2026, vor dem Einspielen. Entscheidung: Sven, Chat 15.10.2026. E5b lautet „ja, auch 0,10“, dazu „mach weiter mit den Kleinigkeiten“ (F8).

## Änderungen

| # | Bot | Datei | Art | vorher → nachher |
|---|---|---|---|---|
| 1 | v6, v7 | `risk/exit_rules.py` | **verhaltensändernd** | `TRAIL_MARGE_PCT` 0,05 → **0,10**: Nachzieh-Start = Nulllinie + 0,10. Abstand 0,85 → 1,109 · 1,0 → 1,262 · 1,3 → 1,569 (vorher 1,06 / 1,21 / 1,52) |
| 2 | v6, v7 | `maker_schatten.py` | nur Auswertung | Gebühren Bybit 0,25/0,10 → Bitvavo USDC 0,05/0,05 |
| 3 | v6 | `live/watchdog.py` | nur Abschalten | `stop()` ergänzt (Befund 72, Übernahme aus v7 L6). Der STOPPEN-Knopf speichert damit wieder den Positionsstand |
| 4 | v6 | `data/market_data.py` | ohne Wirkung auf den Handel | `ccxt.coinbasepro` entfernt (P0-11). Börse per `getattr`, `ccxt_id` = binance → derselbe Client, nur ohne roten Fehler bei jedem Start |

Skript: `pruefstand/patches/patch_e13_kleinigkeiten.py`. Funktionstest:
- Start für 3 Abstände ≥ Nulllinie + 0,10.
- Der Puffer bleibt bei 0,25.
- `maker_schatten` rechnet mit Bitvavo-Gebühren.
- Watchdog vor und nach `stop()`: Vorher wird ein toter Thread neu gestartet, danach nicht mehr.
- Kein `coinbasepro` mehr im Code.

Nur Änderung 1 begründet die Epochengrenze.

## Hypothese (Änderung 1)

Ein Nachzieh-Stopp, der am Start-Hoch auslöst, endet bei 0,05 Marge und dem gemessenen Auslöseverzug (Ø 0,072 %) im Mittel knapp unter null. Mit 0,10 Marge endet er knapp darüber. Dafür setzt der Stopp etwas später ein, nämlich 0,05 Punkte höher. Die Wirkung ist klein und vergleichbar mit E12.

## Messgrößen und Erfolgskriterien

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| E13a | Nachzieh-Ausstiege: Anteil netto im Minus (Kasse, K 0,15) | ≤ 5 % (wie V1a) | 30 Nachzieh-Ausstiege je Bot |
| E13b | Nachzieh-Ausstiege netto je Runde, je W1-Lage | ≥ 0 | je Lage 15 Fälle |
| E13c | Abschalten über STOPPEN (v6) | Positionsstand gespeichert, kein `AttributeError` im Log | beim ersten Klick |
| E13d | Start-Log v6 | kein `coinbasepro`-Fehler mehr | beim nächsten Start |

Ausgewertet wird gemeinsam mit E10–E12 bzw. L9–L11 (gleiche Kostenlatte), als Kassenrechnung und je Marktlage.

## Abbruch / Rücknahme

- Der Bot startet nicht oder der Datenclient fehlt („KRITISCH: Auch Fallback fehlgeschlagen“) → Sicherung `*.bak_e13_kleinigkeiten_*` zurückspielen.
- Ein Nachzieh-Ausstieg endet häufiger netto im Minus als in E11 → prüfen.

## Debatte

*Diese Debatte habe ich selbst geschrieben. Eine A10-Prüfung liegt für diese kleine Änderung nicht vor. Die Begründung folgt derselben Arithmetik wie bei E12, und die hat A10 als tragend bestätigt.*

- **Dafür:** Puffer und Nachzieh-Start haben jetzt dieselbe Sicherheit gegen den Auslöseverzug. W3 wird an dieser Stelle grün. Befund 72 und P0-11 sind seit Wochen bekannt, und v7 hat beide Fixes längst.
- **Dagegen:** Ein späterer Nachzieh-Start lässt in seltenen Fällen eine Position länger laufen, die dann über die Nullsicherung oder die Verlustbremse endet. Die Ausstiegsregeln sind laut A5 insgesamt kein messbarer Hebel. Das ist Pflege, kein Vorsprung.

## Start

- **v6 E13_kleinigkeiten:** Start 2026-10-15T10:03:04Z. **v7 L12_kleinigkeiten:** Start 2026-10-15T10:03:05Z.
- Nachgetragen am 15.10.2026 aus `config_epochs.json` beider Bots (Agententest Phase 6, A11). Neustart belegt: v7 `system.log` Z. 38502 `[2026-10-15T10:03:18] Konfiguration geladen`, W5 meldet die Prozesse seit 12:03 Berlin.
