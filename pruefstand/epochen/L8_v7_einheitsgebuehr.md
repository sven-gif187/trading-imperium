<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · Epoche L8 · Instanz v7 · „Bybit-EU-Einheitsgebühr“

Registriert: 14.10.2026, vor dem Einspielen. Freigabe: Sven, Chat 14.10.2026 (F8).

## Hypothese

Seit 05.10.2026 11:00 UTC gibt es bei Bybit EU keinen Maker-Rabatt mehr: 0,25 % für VIP 0, Primärquelle abgerufen am 14.10. v7 bucht Käufe über Warte-Aufträge weiter mit 0,10 %. Damit sind die v7-Zahlen seit dem 05.10. um 0,15 % je Kauf zu günstig, bisher 2,88 $ auf 8 Käufen. Mit 0,25 % stimmen Buchung und echte Börsengebühr überein.

## Änderung

Eine: der Maker-Satz, an drei Stellen (`backtest/fees.py:24`, `execution/engine.py:393`, `core/kosten.py:61`). Skript `pruefstand/patches/patch_v7_bybit_einheitsgebuehr.py`. Er ist keine Handelsregel, wirkt aber über `pnl` auf Lernen und Verlustzähler. Deshalb gibt es eine Epochengrenze.

## Messgrößen und Erfolgskriterien

| # | Messgröße | Vorher | Erfolg | Entscheidbar ab |
|---|---|---|---|---|
| G1 | Kaufgebühr / (Kaufbetrag + Gebühr) bei Warte-Auftrags-Käufen | 0,100 % | 0,250 % ± 0,001 | erster Kauf |
| G2 | gebucht − Kasse je Runde | 0,00 $ (Buchung seit 11.09. richtig) | weiter \|Δ\| ≤ 0,01 $ | erste Runde |
| G3 | Netto je Runde v7 | −0,37 % (15 Runden, Kasse) | Bericht, keine Erfolgsschwelle (reine Kostenkorrektur) | – |

## Folge für die Strategie

Warte-Aufträge sparen ab jetzt keine Gebühr mehr. Was bleibt, ist ein womöglich besserer Einstiegskurs, und dem steht die Gegenauslese gegenüber. Ob sich das lohnt, misst A6 als eigene Frage (Markout).

## Abbruch

- Startfehler.
- G1 ≠ 0,25 %.

## Start

- **Eintrag:** `L8_einheitsgebuehr`, Start **2026-10-14T09:51:17.558608+00:00** (11:51 Berlin).
- **Stopp:** 11:50 mit `bot_anhalten.py`. Zustand unverändert: 1 Position (SOL 2,180560, Kauf 08:41 UTC mit 0,10 % – trägt den alten Satz), USDC 12,32 $.
- **Patches:** Einheitsgebühr (fees.py LF, engine.py CRLF, kosten.py LF, alle erhalten) und Autostart-Klick (main_window.py LF). Werte geprüft: bybit 0,25/0,25, `MAKER_PCT` 0,25, `K_WARTE_PCT` 0,505.
- **Start:** 11:51:24 per Autostart, „V7 startet“ 11:52:14, Port 5070 11:52:42, Position wiederhergestellt.
- **Doku:** BOT-HANDBUCH v7 10.12, 2 Tickets eingelesen. `prozess_frische.py`: aktuell.
- **Korrektur zur Vorab-Lage:** G2 „gebucht − Kasse“ war schon vor L8 0,00 $. v7 bucht seit 11.09. richtig, der frühere Befund P0-5 ist zurückgezogen.
