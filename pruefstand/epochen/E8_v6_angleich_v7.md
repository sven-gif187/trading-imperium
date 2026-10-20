<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · Epoche E8 · Instanz v6 · „Angleich an v7“

Registriert: 14.10.2026, **vor** dem Einspielen. Freigabe: Sven, Chat 14.10.2026 (F6 „ja“, „alles tun, was das Projekt voranbringt“).
Start (UTC): wird beim Eintrag in `v6\config_epochs.json` gesetzt und unten nachgetragen.

## Hypothese

Die Ausstiegs-Konstanten von v6 stammen aus der Zeit mit 0,10 % Gebühr je Seite und liegen unter der heutigen Kostenlatte K = 0,505 %:

- **Nullsicherung:** Puffer 0,35 %. Damit endet jede Nullsicherung garantiert mit −0,155 % netto. In E7 waren es 21 von 21 im Minus, −7,90 $.
- **Nachzieh-Stopp:** Er startet bei +1,2 %, rentabel ist er aber erst ab +1,52 %.

Mit den aus K gerechneten Werten 0,55 % und 1,57 % verschwinden diese garantiert negativen Ausstiege. Das ATH (126.200 statt 109.114) und der Verlustzähler, der Neustarts übersteht, bringen v6 auf denselben Stand wie v7.

## Änderungen (eine Epochengrenze, vier Patches)

| Patch | Datei | vorher → nachher |
|---|---|---|
| 00a | `risk/exit_rules.py:107` | `BREAKEVEN_PUFFER_PCT` 0,35 → 0,55 |
| 45 | `risk/exit_rules.py:108` | `TRAIL_AB_PCT` 1,2 → 1,57 (aus K und Trail gerechnet) |
| 54 | `runtime/state_manager.py` | `coin_consecutive_losses` wird gespeichert und geladen |
| 63 | `agents/cycle_theory.py:28` | ATH fest 109.114 → aus Wochenkerzen, Rückfall 126.200 |

**Warum gebündelt, obwohl der Masterprompt „eine Änderung je Epoche“ bevorzugt:**

1. **Gleicher Stand wie v7:** v7 läuft seit 25.09. mit genau diesen vier Werten. Gebündelt unterscheiden sich v6 und v7 danach nur noch im Einstieg (Warteauftrag, 50 %/1 Position gegen 30 %/3). Der Vergleich der beiden wird dadurch sauberer.
2. **Gleiche Ursache:** 00a und 45 haben dieselbe Ursache (Konstanten ohne Kostenbezug), getrennt messen bringt nichts.
3. **Dauer:** Einzelepochen für kleine Effekte dauern je 4–9 Monate (Tabelle 3.8).
4. **Readme:** `patches_nach_27_08\00_LIES_MICH.md` verlangt ausdrücklich eine Grenze für alle vier.

**Preis:** Die Wirkung der vier ist nicht trennbar. Patch 63 wirkt über die Zyklusphase auch auf die Positionsgröße.

**Abweichung von „Schattenbuch zuerst“ (Phase 7):** 00a und 45 korrigieren Arithmetik (ein Ausstieg unter der Kostenlinie ist ein garantierter Verlust) und keine Strategie-Wette. Den Beleg im Echtbetrieb liefert v7.

## Messgrößen und Erfolgskriterien (vorab festgelegt)

| # | Messgröße | E7-Wert (136 Runden) | Erfolg | Entscheidbar ab |
|---|---|---|---|---|
| M1 | Nullsicherung: netto je Runde | −0,22 %, 0 % im Plus | Ø ≥ 0,00 % | 15 Nullsicherungen |
| M2 | Nachzieh-Stopp: Anteil netto im Minus | 18 % (11 von 61) | ≤ 5 % | 30 Nachzieh-Ausstiege |
| M3 | Netto je Runde gesamt | −0,209 % (Streuung 1,75) | > E7, 95 %-Bereich über E7 | ≈ 290 Runden für +0,2 Punkte (≈ 4 Monate) |
| M4 | Verlust-Sperre greift | 0× in 12 Tagen trotz Serien | ≥ 1× bei jeder Serie ≥ 3 | erste Serie |

Jede Messgröße wird getrennt je Marktlage (W1) ausgewiesen. Rechnung als Kassenrechnung (`runden.py`-Logik), nicht aus `pnl`/`pnl_pct`.

## Abbruchkriterien

- Startfehler oder Absturz durch einen der Patches (Log, Rückgabewert).
- Kassen-Abweichung, die nicht von der bekannten doppelten Kaufgebühr kommt.
- Nach 30 Runden: netto je Runde unter −0,85 %. Das ist E7 minus 2 Standardfehler bei n = 30.

## Bekannte Störgrößen

- **Doppelte Kaufgebühr bleibt** (Befund 42, Weg `exit_monitor`). Patch 54 zählt Verluste nach dem gebuchten `pnl`, der durch die Doppelgebühr zu schlecht ist. Die Verlust-Sperre kann deshalb öfter greifen als netto gerechtfertigt. Die Korrektur kommt als eigene Epoche, für v6 und v7 gleichzeitig.
- Die Marktlage wechselt (Aufwärtstrend August, seitwärts Oktober).
- Befund 72 (STOPPEN-Knopf speichert nicht) bleibt in v6 offen.

## Debatte (A10)

*Hinweis 15.10.2026: Diese Debatte habe ich selbst bei der Registrierung geschrieben. Sie war keine unabhängige A10-Prüfung (Nebenbefund A10, `berichte/2026-10-14_advocatus.md`).*

**Position A, trägt:**
1. 00a/45 sind Arithmetik: 0,35 < 0,505 und 1,2 < 1,52.
2. In E7 haben diese Werte nachweislich Geld gekostet: Nullsicherung −7,90 $ bei 0/21 im Plus.
3. v7 hat dieselben Werte seit drei Wochen ohne Betriebsfehler: 6 Nullsicherungen, +2,76 $, 5/6 im Plus.

**Position B, trägt nicht:**
1. Ein späterer Nachzieh-Start lässt Runden zwischen +1,2 und +1,57 % weiterlaufen. Ein Teil fällt danach in die Verlustbremse. Das kann mehr kosten, als die Korrektur spart.
2. Vier Änderungen auf einmal lassen sich nicht zuordnen.
3. Patch 63 vergrößert bzw. verkleinert die Positionen über die Zyklusphase. Das ist eine Strategie-Änderung, keine Arithmetik.

**Urteil:** TRÄGT für 00a/45 (95 %). TRÄGT für 54/63 als Angleich an v7 (75 %). Punkt B1 ist echt und wird in M2/M3 sichtbar.

## Start

- **Eintrag:** `E8_angleich_v7` in `v6\config_epochs.json`, Start **2026-10-14T09:18:25.132061+00:00** (11:18 Berlin).
- **Bot-Stopp:** 11:16:19 nach frischer Speicherung, per Prozessende (nicht STOPPEN, Befund 72). `bot_state.json` unverändert: 3 Positionen (BTC 0,002112 · ETH 0,070103 · SOL 0,563959), USDC 3,22 $.
- **Eingespielt:** 00a → 45 → 54 → 63, nach jedem Schritt AST, Import und CRLF geprüft.
- **Neustart:** 11:18:35 über `pruefstand\autostart\bots_starten.py`. Port 5050 offen um 11:22:23. Log: „Positionen wiederhergestellt: 3 aktiv“.
- **Kontrolle:** `prozess_frische.py` meldet alle Prozesse aktuell. Handbuch 10.11, Tickets eingelesen (Chronik Z. 5943).
