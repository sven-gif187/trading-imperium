<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v6 Epoche E10 · v7 Epoche L9 · „Kostenlatte Bitvavo USDC“

Registriert: 14.10.2026, vor dem Einspielen. Entscheidung: Sven, Chat 14.10.2026 („A Bitvavo, beide Bots umstellen“, Z1).
Grundlage: `berichte/2026-10-14_zielboerse.md`, Schattenbuch `berichte/2026-10-14_kosten_schatten_v6_mit_schlupf.json`. Damit ist „Schattenbuch zuerst“ aus Phase 7 erfüllt.

## Hypothese

Die Papier-Bots sollen das Ergebnis an der künftigen Zielbörse vorhersagen. Mit Bybit-Kosten (K 0,505 %) liegt jede Runde im Mittel bei −0,21 %. Unter Bitvavo-USDC-Kosten (K 0,150 %) wäre es auf denselben 136 Runden +0,14 % gewesen. Die Ausstiegsgrenzen werden aus K gerechnet und fallen mit. Der Lerner im Regime-Filter bewertet geblockte Käufe gegen die richtige Latte.

## Änderung (eine Ursache: Zielbörse, in jedem Bot an allen Stellen gleichzeitig)

| Stelle | v6 | v7 | vorher → nachher |
|---|---|---|---|
| Gebührentabelle | `backtest/fees.py` | `backtest/fees.py` | neuer Eintrag `bitvavo_usdc` Maker 0,05 / Taker 0,05 |
| Papier-Gebühr | `execution/engine.py:248` | `execution/engine.py:320` | `PAPER_GEBUEHR_BOERSE` "bybit" → "bitvavo_usdc" |
| Papier-Schlupf | `execution/engine.py:266-268` | `execution/engine.py:338-340` | `SPREAD_BP` für BTC/ETH/SOL: Bybit-Messung 31.07. → Bitvavo-USDC-Stichprobe 14.10. |
| Kostenlatte | `risk/exit_rules.py:123` | `risk/exit_rules.py:129` + `core/kosten.py:60-70` | K_BASIS 0,505 → 0,150 (Gebühr 0,10 + Schlupf 0,05) |
| Nullsicherung-Puffer | aus K: 0,55 → **0,195** | aus K: 0,55 → **0,195** | Formel unverändert (K + 0,045) |
| Nachzieh-Start | `risk/exit_rules.py:133` | `risk/exit_rules.py:139` | 1,57 → **1,21** ((1+K)/(1−1 %) − 1 + 0,05) |
| Regime-Lerner | `features/regime_adaptiv.py:76` | automatisch über `core/kosten.py` | v6: 0,32 → 0,150 |
| Schatten-Ausstiege | `risk/exit_rules_schatten.py:104` | automatisch | v6: 0,32 → 0,150 (misst nur) |
| Zielgrößen | `config_zielgroessen.json:55` | dto. | `kosten_je_runde_pct` 0,505 → 0,150 |
| Regeldatei | `CLAUDE.md` 8 | `CLAUDE.md` 8 | Zielbörse und K-BASIS, alte Latte gilt weiter für alte Epochen |

Nicht geändert: Handels- und Kaufregeln, Positionsgröße, Verlustbremse 2,5 %, Kursquelle Binance, Echtgeld-Pfade (`handel_ccxt_id` usw. bleiben „bybit“, Echtgeld ist abgeschaltet).

## Messgrößen und Erfolgskriterien (vorab festgelegt)

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| K1 | gebuchte Gebühr / Nominal je Order | 0,050 % ± 0,001 | erste Order |
| K2 | simulierter Schlupf je Seite (Journal `slippage_pct`) | Median ≈ halbe Bitvavo-Spanne der Stichprobe | 10 Orders |
| K3 | Nullsicherung netto je Runde (Kasse, K 0,150) | ≥ 0,00 % | 15 Nullsicherungen |
| K4 | Nachzieh-Stopp: Anteil netto im Minus | ≤ 5 % | 30 Nachzieh-Ausstiege |
| K5 | Netto je Runde, beide Bots getrennt | 95-%-Bereich (Block-Bootstrap nach Tagen) über 0 | grob 600 Runden je Bot, bei heutigem Tempo v6 ≈ 9 Monate |
| K6 | echte Bitvavo-Spanne (W3, rund um die Uhr) gegen simulierte | Median nicht mehr als 50 % über der Simulation | 7 Tage W3 |

Jede Messgröße wird getrennt je Marktlage ausgewiesen. Gerechnet wird mit `pruefstand/skripte/runden_lib.py` (Kassenrechnung), nicht mit `pnl`.

## Abbruch- und Rückkehrkriterien

- Startfehler oder Absturz.
- K1 verletzt.
- Bitvavo ändert die USDC-Gebühr (W3, Prüfsumme der Gebührenseite). Dann neu rechnen und Sven vorlegen.
- K6 verletzt. Dann wird `SPREAD_BP` nachgeeicht, als eigene Epoche.

## Bekannte Störgrößen

- **v6:** E8 (09:18 UTC) und E9 (09:35 UTC) haben bis zum E10-Start kaum Runden. E8/E9/E10 sind praktisch ein Block, ausgewertet wird **ab E10**.
- **v6:** Die 3 Positionen von vor E9 tragen ihre doppelte `cost_basis` weiter. Positionen von vor E10 wurden mit 0,25 % gekauft.
- **v7:** Die SOL-Position (Kauf 14.10. 08:41 UTC, 0,10 %) läuft weiter.
- **Spanne:** Die Bitvavo-Stichprobe stammt von einem Nachmittag (14.10.). Sie wird von W3 überwacht.

## Debatte (A10)

*Hinweis 15.10.2026: Diese Debatte habe ich selbst bei der Registrierung geschrieben. Sie war keine unabhängige A10-Prüfung (Nebenbefund A10, `berichte/2026-10-14_advocatus.md`).*

**Position A, trägt:**
1. Das Schattenbuch zeigt den Effekt auf denselben 136 Runden: +42,66 $ statt −34,85 $ (berichtigt 14.10. nach A5; zuerst +33,65 / −43,85).
2. Die Ausstiegsgrenzen bleiben dieselbe Formel, nur mit neuem K. E7 und E8 haben gezeigt, dass Grenzen unter K Geld kosten. Grenzen weit über K schneiden Gewinne ab.
3. Ohne realistische Kosten misst der Papier-Bot etwas, das es an der Zielbörse nicht gibt.

**Position B, trägt nicht:**
1. Ein Nachzieh-Start bei 1,21 % lässt öfter schon bei kleinen Hochs nachziehen. Das sind mehr kleine Gewinne, also mehr Runden und mehr Kosten.
2. Den Vorsprung vor Kosten hat niemand belegt (95-%-Bereich −0,20 % bis +0,75 %). Billige Kosten machen einen nicht vorhandenen Vorsprung nicht sichtbar.
3. Die dritte Verhaltensänderung an einem Tag (E8, E9, E10) macht Vergleiche mit E7 schwer.

**Urteil: TRÄGT** [WAHRSCHEINLICH 80 %]. B2 ist echt und wird von A4 (Einstieg gegen Zufall) parallel geprüft. B3 ist hinnehmbar: E7 bleibt die saubere Vergleichsbasis, alles ab E10 wird mit der neuen Latte gemessen.

## Start

- **Stichprobe:** Bitvavo USDC 14.10. 13:50 UTC, 120 Proben je Münze. Median / p90 in bp: BTC 2,779 / 4,351 · ETH 4,265 / 5,149 · SOL 5,724 / 8,118. Schlupf je Runde 0,043 %, K = 0,143 %, eingesetzt gerundet **0,15**.
- **v6:** Stopp 15:57 (1 Position BTC, USDC 235,43, Zustand unverändert). Patch 8 Ersetzungen. **E10_kostenlatte_bitvavo Start 2026-10-14T13:58:25Z**. Werte geprüft: K 0,15, Puffer 0,195, Trail 1,21, Regime und Schatten 0,15, Papier `bitvavo_usdc` 0,05/0,05.
- **v7:** Stopp 15:58 (1 Position ETH, USDC 12,03). Patch 10 Ersetzungen, Sicherungen = Originale (Prüfsumme). **L9_kostenlatte_bitvavo Start 2026-10-14T13:59:20Z**. `core/kosten.py` TAKER/MAKER 0,05, SCHLUPF 0,05, K 0,15, K_WARTE 0,15.
- **CLAUDE.md** Abschnitt 8 in beiden Bots angepasst.
- **Start:** 15:59:35 per Autostart, „startet“ 16:00:21 (v6) und 16:00:26 (v7), Ports 5050/5070 um 16:00:54 offen. `prozess_frische.py` meldet in beiden alles aktuell.
- **Doku:** BOT-HANDBUCH 10.13 in beiden Bots, Tickets eingelesen (v6 3, v7 2), BOT-HANDBUCH.pdf in beiden neu erzeugt.
- **Zwischenfall:** Das Patch-Werkzeug hat in v6 die Originalsicherung von `engine.py` und `exit_rules.py` überschrieben (gleicher Name). Die Originale wurden aus `pruefstand\sicherungen\20261014_155710_vor_kostenlatte_v6\` zurückgespielt und das Werkzeug repariert, bevor v7 dran war.
