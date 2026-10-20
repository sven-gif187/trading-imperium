<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v6 Epoche E11 · v7 Epoche L10 · „Nachzieh-Start aus wirksamem Abstand“ (A5-V1)

Registriert: 14.10.2026, vor dem Einspielen. Entscheidung: Sven, Chat 14.10.2026 („V1 Start aus wirksamem Abstand“, Z4).

## Hypothese

Der Nachzieh-Stopp startete bei einem festen Hoch (zuletzt 1,21 %, gerechnet für 1,0 % Abstand). Wirksam ist aber der Abstand nach Regime (EARLY_BEAR ×0,85), Leiter und Trend-Bonus (×1,3). Im Aufwärtstrend (Abstand 1,3 %) endet ein Ausstieg zwischen 1,21 % und 1,52 % Hoch nach Kosten im Minus. In EARLY_BEAR (0,85 %) wartet der Stopp dagegen unnötig lange, nämlich bis 1,21 statt 1,06. Wird der Start aus dem wirksamen Abstand gerechnet, endet **kein** Nachzieh-Ausstieg mehr wegen der Startgrenze unter null.

## Änderung

Eine Änderung in `risk/exit_rules.py`, Funktion `effektiver_trail()` (v6 und v7 gleich): Start = (1 + K) ÷ (1 − Abstand) − 1 + 0,05. Skript: `pruefstand/patches/patch_v1_trailstart_wirksam.py`. Funktionstest: 7 Fälle, dazu die Nachrechnung, dass ein Ausstieg am Start netto +0,05 % ergibt.

| wirksamer Abstand | Start vorher | Start nachher |
|---|---|---|
| 0,85 % (EARLY_BEAR) | 1,21 | **1,06** |
| 1,0 % | 1,21 | 1,21 |
| 1,105 % (EARLY_BEAR + Trend) | 1,21 | **1,32** |
| 1,3 % (Trend) | 1,21 | **1,52** |

## Messgrößen und Erfolgskriterien

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| V1a | Nachzieh-Ausstiege: Anteil netto im Minus (Kasse, K 0,15) | ≤ 5 % | 30 Nachzieh-Ausstiege je Bot |
| V1b | Nachzieh-Ausstiege netto je Runde, getrennt nach Regime | ≥ 0 in jedem Regime | je Regime 15 Fälle |
| V1c | Netto je Runde gesamt gegen E10/L9 | nicht schlechter (95-%-Bereich schließt −0,10 aus) | ≈ 300 Runden |

Ausgewertet wird nur als Kassenrechnung (`runden_lib`), getrennt je Marktlage.

## Abbruch

- Startfehler.
- Ein Nachzieh-Ausstieg mit Hoch ≥ Start und netto < −0,05 % zeigt einen Rechenfehler in der Umsetzung.

## Bekannt

E10/L9 (Bitvavo-Kosten) liefen nur rund 6 Stunden. E10–E11 bzw. L9–L10 werden **gemeinsam** ausgewertet, die Kostenlatte ist dieselbe. Die Grenze trennt nur die Startregel.

## Debatte (A10)

*Hinweis 15.10.2026: Diese Debatte habe ich selbst bei der Registrierung geschrieben. Sie war keine unabhängige A10-Prüfung (Nebenbefund A10, `berichte/2026-10-14_advocatus.md`).*

**A, trägt:**
1. Reine Arithmetik, dieselbe Formel wie Patch 45, nur mit dem Abstand, der wirklich gilt.
2. A5 hat belegt, dass 49 von 61 E7-Nachzieh-Stopps mit einem anderen Abstand als 1,0 auslösten.
3. Der Funktionstest zeigt für jeden Abstand Ausstieg ≥ +0,05 % netto.

**B, trägt nicht:**
1. In EARLY_BEAR startet der Stopp früher (1,06). Das sind mehr kleine Gewinne, also mehr Runden und mehr Gebühren.
2. A5 zeigte, dass die Ausstiegsregeln insgesamt kein messbarer Hebel sind (±10 $ in 2 Monaten). Der Effekt wird kaum sichtbar.
3. Noch eine Verhaltensänderung am selben Tag.

**Urteil: TRÄGT** [WAHRSCHEINLICH 80 %]. Es geht um Arithmetik, nicht um Strategie. B2 ist richtig, deshalb ist das Ziel „kein garantierter Verlust mehr“ und nicht „mehr Gewinn“.

## Start

- **v6 E11_trailstart_wirksam:** Start 2026-10-14T19:55:41Z. **v7 L10_trailstart_wirksam:** Start 2026-10-14T19:56:08Z.
- Vor dem Eintrag geprüft: `trail_start_pct(1,3) > 1,5` und `effektiver_trail(1,4; 1,0; TRENDING_UP) = 0`. Beide Bots per Autostart um 21:57 wieder gestartet, `prozess_frische.py` meldet alles aktuell, Handbuch 10.15, 2 Tickets je Bot, PDFs neu.
