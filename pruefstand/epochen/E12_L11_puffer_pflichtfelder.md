<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v6 Epoche E12 · v7 Epoche L11 · „Puffer K + 0,10 und Kauf-Felder am Verkauf“

Registriert: 15.10.2026, vor dem Einspielen. Entscheidung: Sven, Chat 15.10.2026. E5 lautet „Puffer 0,25 mit der nächsten Bot-Änderung“. Die Aufzeichnungs-Änderung (Befund 88) fällt unter F8 (Kleinkram, selbstständig).

## Änderungen

| # | Datei | Art | vorher → nachher |
|---|---|---|---|
| 1 | `risk/exit_rules.py` | **verhaltensändernd** | `BREAKEVEN_MARGE_PCT` 0,045 → **0,10**, also Puffer der Nullsicherung 0,195 → **0,25 %** (K 0,150 + 0,10) |
| 2 | `app.py` `_journal_add()` | nur Aufzeichnung | Fehlende Felder eines Verkaufs (`stop_initial`, `trailing_stop_pct`, `decision_id`, `signal_score`, `signal_reasons`, `active_strategy`, dazu `entry_score`/`entry_strategie`) kommen aus dem ersten Kauf der laufenden Runde. Die Herkunft steht in `felder_aus_kauf`. |

Skript: `pruefstand/patches/patch_e12_puffer_pflichtfelder.py` (Werkzeug `_patchwerkzeug.py`, Zeilenenden je Datei, Sicherung, Rücknahme). Funktionstest: Puffer = 0,25, dazu 7 Fälle für die Feld-Übernahme. Abgedeckt sind: erbt alle Felder, vorhandene Werte bleiben, kein Kauf → nichts erfunden, andere Münze, zwei Käufe, Fehler wirft nicht, Kauf unberührt.

Nur Änderung 1 begründet die Epochengrenze. Änderung 2 verändert keinen Handel.

## Hypothese (Änderung 1)

Die Nullsicherung löst im Mittel 0,072 % (p90 0,17 %) unter ihrer Linie aus (A5, Auslöseverzug). Mit 0,045 % Marge endete eine Nullsicherung im Mittel bei −0,027 % netto, mit 0,10 % sollte sie bei etwa +0,028 % enden. Die Wirkung ist klein, A5 schätzt rund +1 $ in zwei Monaten. A10: „trägt (Arithmetik)“.

## Messgrößen und Erfolgskriterien

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| E12a | Nullsicherungs-Ausstiege (BREAKEVEN_LOCK): netto je Runde (Kasse, K 0,15) | ≥ 0 im Mittel | ≈ 94 Fälle je Bot (A5: 80 % Trennschärfe) |
| E12b | Anteil der Nullsicherungen netto im Minus | kleiner als in E10/E11 | 30 Fälle |
| E12c | Verkäufe mit vollständigen Pflichtfeldern (W4) | ≥ 95 % der Verkäufe mit einem Kauf in derselben Runde | sofort, ab dem ersten Verkauf |

Ausgewertet wird als Kassenrechnung (`runden_lib`), getrennt je Marktlage (W1) und je Bot. Netto je Runde gesamt wird mit E10/E11 bzw. L9/L10 zusammen betrachtet, weil die Kostenlatte gleich bleibt. Eine Aussage zum Gesamt-Netto ist hier nicht zu erwarten.

## Abbruch / Rücknahme

- `_journal_add` wirft einen Fehler oder das Journal schreibt nicht mehr (W4 „orders“/„plausibel“ rot) → sofort zurücknehmen (Sicherung im Bot-Ordner, `.bak_e12_…`).
- Die Nullsicherung löst häufiger aus als vorher, mehr als doppelt so oft je Runde → prüfen. Erwartet ist eher seltener, weil der Puffer höher liegt.

## Debatte

*Diese Debatte habe ich selbst geschrieben. Eine unabhängige Prüfung durch A10 liegt nur für den Puffer vor (`berichte/2026-10-14_advocatus.md`: „A5-V2 trägt“).*

- **Dafür:** Die Arithmetik ist eindeutig. Die Änderung kostet nichts (Nachspielung −0,7 $ [−5,0; +2,3]), und W3 I1 wird grün. Die Feld-Übernahme schließt eine seit dem 21.08. bekannte Lücke (Befund 88), ohne den Handel zu berühren.
- **Dagegen:** Die Wirkung liegt im Rauschen. Die Feld-Übernahme setzt voraus, dass Kauf und Verkauf über „Käufe seit dem letzten Verkauf“ zusammengehören. Bei Teilverkäufen gilt das nicht. Seit E7 gab es 0 davon (A10), und bei einem Teilverkauf bleibt das Feld wie bisher leer, es wird nichts erfunden.

## Start

- **v6 E12_puffer_pflichtfelder:** Start 2026-10-15T09:35:57Z. **v7 L11_puffer_pflichtfelder:** Start 2026-10-15T09:35:57Z.
- Nachgetragen am 15.10.2026 aus `config_epochs.json` beider Bots (Agententest Phase 6, A11). Laut `sitzung_stand.md` waren beide Bots um 09:37 UTC wieder erreichbar.
