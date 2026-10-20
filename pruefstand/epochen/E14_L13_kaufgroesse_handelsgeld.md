<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v6 Epoche E14 · v7 Epoche L13 · „Kaufgröße aus Handelsgeld“ (KG1)

Registriert: 15.10.2026, vor dem Einspielen. **Eingespielt 15.10.2026 20:35 UTC.** Entscheidung: Sven, Chat 15.10.2026, KG1 („Die Kaufgröße wird nur aus dem Handelsgeld berechnet, das Sparplan-Bitcoin zählt nicht mit … Umsetzung mit der nächsten Bot-Änderung als eigene Epoche“) und KG1a („gilt für beide Bots, v6 und v7“).
Die Nummern E14/L13 sind vorläufig. Kommt vorher eine andere Epoche, wird hochgezählt.
Grundlage: `berichte/2026-10-15_lage.md` Punkt 1, `berichte/2026-10-15_code.md` (A9), `berichte/2026-10-15_kurse_nach_ausfall.md` Befund 7.

## Änderung (eine Ursache: Basis der Kaufgröße)

| # | Bot | Datei | Art | Inhalt |
|---|---|---|---|---|
| 1 | v6, v7 | `portfolio/manager.py` (in beiden Bots identisch, CRLF) | neu, ohne eigene Wirkung | Neue Funktion `get_trading_capital()` = `get_total_capital()` minus Sparplan-BTC, nicht unter 0. `get_total_capital()` bleibt unverändert. |
| 2 | v6, v7 | `app.py`, Block „MANUELLES SIZING“ (`use_dynamic_sizing = false`, in beiden aktiv) | **verhaltensändernd** | `capital = self.portfolio.get_total_capital()` → `get_trading_capital()`. Nur diese eine Stelle. Portfolio-Prüfung, Drawdown-Guard, Tagesverlust, Tagesstart und Anzeige rechnen weiter mit Sparplan (E10-KAPITAL). |

Skript: `pruefstand/patches/patch_kg1_kaufgroesse_handelsgeld.py v6|v7 --pruefen|--selbsttest|--anwenden`. Am 15.10.2026 sind `--pruefen` (alle Anker genau einmal, BEREIT) und `--selbsttest` in beiden Bots bestanden: Kopie gepatcht, Zeilenenden gleich, idempotent, Original unberührt, dazu 7 Funktionsfälle.

**Nicht Teil dieser Epoche:**
- **„Begrenzen statt ersetzen“, bewusst NICHT dabei** (geprüft 15.10.2026): In v7 hat Sven am 25.09. „50 % und eine Position“ festgelegt (`config_epochs.json` L7_svens_drei_entscheidungen). Die Grenze `modes.balanced.max_coin_pct = 35` stammt von vorher und widerspricht dem. Würde der Münz-Deckel jetzt durchgesetzt, kaufte v7 nur ≈ 82 $ (35 %) statt der beschlossenen 50 %. Nach KG1 allein gilt: v7 kauft 50 % des Handelsgelds, die Reserve von 10 % bleibt von selbst frei (≈ 50 % frei). v6: 3 × 30 % = 90 %, Rest ≈ 10 % = Reserve. Teil (a) bringt also nach KG1 keinen Risikogewinn und würde in v7 eine Entscheidung von Sven aushebeln. Offen bleibt nur, den widersprüchlichen Wert 35 in der v7-Config aufzuräumen (kein Handel betroffen, solange der Deckel nicht durchgesetzt wird).
- **Kaufsperre bei altem Kurs** (`berichte/2026-10-15_kurse_nach_ausfall.md`): Kandidat für dieselbe Bot-Änderung, aber eigene Ursache, also eigene Zeile hier, wenn sie kommt.

## Hypothese

Die Kaufgröße zählt seit E10-KAPITAL (29.07.) das Sparplan-BTC mit. Dadurch kauft v7 mit 50 % von Handelsgeld plus Sparplan ≈ 232 $, obwohl nur ≈ 235 $ Handelsgeld da sind. Die Bargeld-Grenze kappt erst bei 95 %, und eine Münze trägt fast die ganze Handelskasse. Mit dem Handelsgeld als Basis kauft v7 ≈ 117 $ und v6 ≈ 122 $ (heute ≈ 172 $). **Erwartet:** gleiches Ergebnis je Runde in %, ungefähr halbe Dollar-Ausschläge und keine leere Kasse mehr nach dem dritten v6-Kauf. Einen Gewinn-Vorteil erwartet hier niemand. Es geht um Risiko.

## Messgrößen und Erfolgskriterien (vorab festgelegt)

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| KG-a | Kaufbetrag je neuem Kauf (Journal `amount`, Log `SIZING`) | = Modus-% × Handelsgeld (USDC + offene Positionen, ohne Sparplan) ± 1 $ | erster Kauf je Bot |
| KG-b | v7: Anteil der Handelskasse in der Position direkt nach dem Kauf | ≤ 52 % (50 % + Gebühr/Schlupf), vorher 95 % | erster v7-Kauf |
| KG-c | v6: freies USDC bei 3 offenen Positionen | ≥ 10 % der Handelskasse (Reserve des Modus), vorher ≈ 0 | erste Lage mit 3 Positionen |
| KG-d | Drawdown-Guard, Tagesverlust, Anzeige | unverändert mit Sparplan (W4 `konto`: `handel_gesamt` + `sparplan_btc_wert` wie bisher) | erster Tag |
| KG-e | Netto je Runde in % (Kassenrechnung `runden_lib`) | **kein Kriterium**, nur ausweisen. Unter 30 Runden nicht entscheidbar. Getrennt je Marktlage | – |

## Abbruch / Rücknahme

- Startfehler oder Ausnahme im Sizing-Block (Log `SIZING Manuell (Fallback)` häuft sich).
- KG-a verletzt (Kaufbetrag weicht um mehr als 1 $ vom Soll ab).
- Mehrere Käufe in Höhe des Minimums von 5 $, ohne dass die Kasse leer ist: Das wäre ein Bewertungsfehler beim Sparplan.
- Rücknahme: `.bak_kg1_kaufgroesse_handelsgeld_*` beider Dateien zurückspielen (Bot geschlossen), neue Epoche „Rücknahme KG1“.

## Debatte (A10, aus dem Lagebericht übernommen, keine eigene A10-Prüfung)

- **Dafür:** Svens eigene Grenzen (Münz-Deckel 35 %, Reserve 10 %) gelten wieder sinngemäß. v7 hängt nicht mehr mit 95 % an einer Münze. Ein Stopp kostet ≈ 3 $ statt ≈ 6 $. Laut `app.py:973-974` sollte der Sparplan „bewusst DRAUSSEN“ bleiben, das stellt den alten Zustand wieder her.
- **Dagegen:** E1 erlaubt am Kurzfrist-Bot nur Kleinkram. Die Dollar-Kurve von Wettkampf-Teilnehmer A (v6) knickt einmal ab. Laut E3 ist das erlaubt, die Epochengrenze kommt in den Wochenbericht. Der Wert „investiert“ (W2 M2) sinkt. Der Vorsprung je Runde in % ändert sich nicht.
- **Urteil:** Es ist eine Risikoentscheidung von Sven (KG1/KG1a), keine Strategiewette. Die Umsetzung ist eine einzelne Zeile plus Hilfsfunktion, gut prüfbar.

## Start

- **v6 E14_kaufgroesse_handelsgeld:** Start 2026-10-15T20:35:04Z. **v7 L13_kaufgroesse_handelsgeld:** Start 2026-10-15T20:35:04Z.
- Ausgangslage: Beide Bots liefen seit 18:11 UTC (20:11 Berlin) nicht mehr. Das Update der Claude-App (2.37337 → 2.42304, neu gestartet 20:11:21 Berlin) hat sie beendet, weil sie mittags aus einer Claude-Sitzung gestartet worden waren. W5 meldete das um 18:15 UTC ROT. `bot_anhalten.py` setzte deshalb nur die Sperren („lief nicht“).
- Patch `--anwenden` v6/v7 um 20:34:50 UTC, Sicherungen `*.bak_kg1_kaufgroesse_handelsgeld_20261015_2234*`, danach `--pruefen` „bereits angewendet“. `config_epochs.json` byte-genau fortgeschrieben (CRLF). Handbuch 10.18, 3 Tickets je Bot, BOT-HANDBUCH.pdf neu.
- Neustart **über die Aufgabe `TI-Bots-Autostart`** (nicht aus der Sitzung) um 20:36 UTC, Ports 5050/5070 offen. v6: 3 Positionen wieder geladen (BTC, SOL, ETH; USDC 3,12), v7: 1 Position (ETH; USDC 11,70). KG-a wird beim nächsten Kauf geprüft. v6 ist voll (3/3), v7 hat eine Position (1/1).
