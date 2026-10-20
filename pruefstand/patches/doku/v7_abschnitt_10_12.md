## 10.12 Epoche L8 — Bybit-Einheitsgebühr, und der Autostart nach Anmeldung

**Angelegt 14.10.2026** aus dem Prüfstand (`Desktop\pruefstand`), Freigabe Sven im Chat.

### Epoche `L8_einheitsgebuehr` (Start 14.10.2026 09:51:17 UTC)

**Was Bybit geändert hat.** Seit **05.10.2026 11:00 UTC** gilt bei Bybit EU eine Einheitsgebühr. Für VIP 0 sind das **0,25 %**, ein Maker-Rabatt existiert nicht mehr. Quelle ist die Seite „Trading Fee Structure“ („Last updated on 2026-10-05 13:01:39“), abgerufen am 14.10.2026.

**Was v7 falsch gebucht hat.** Käufe über Warte-Aufträge wurden weiter mit 0,10 % gebucht (`engine.py:486` → `backtest/fees.py:24`). Zwischen 05.10. und 14.10. betraf das 9 Käufe, zusammen rund 3,2 $ zu wenig Gebühr. Die v7-Zahlen seit dem 05.10. sind damit zu günstig.

**Die Änderung.** Es wurde genau ein Wert geändert, der Maker-Satz. Er steht an drei Stellen:

| Stelle | vorher | nachher |
|---|---|---|
| `backtest/fees.py:24` bybit maker | 0,10 | 0,25 |
| `execution/engine.py:393` Rückfall maker | 0,0010 | 0,0025 |
| `core/kosten.py:61` `MAKER_PCT` | 0,10 | 0,25 (damit `K_WARTE_PCT` 0,505) |

Das ist keine Handelsregel, aber der Satz geht über `pnl` in Lernen und Verlustzähler ein. Deshalb gibt es eine Epochengrenze.

**Folge.** Warte-Aufträge sparen bei Bybit EU keine Gebühr mehr. Was bleibt, ist ein womöglich besserer Einstiegskurs, und dem steht die Gegenauslese gegenüber. Ob sich das lohnt, ist eine eigene Messfrage (Markout).

**Bekannt.** Die SOL-Position, die beim Stopp offen war (Kauf 14.10. 08:41 UTC), trägt noch den alten Satz von 0,10 %.

Skript: `pruefstand\patches\patch_v7_bybit_einheitsgebuehr.py`. Vorab-Registrierung: `pruefstand\epochen\L8_v7_einheitsgebuehr.md`.

### Autostart nach Anmeldung

**Anlass.** Windows Update startete den Rechner am 14.10. um 05:32 neu. v6 und v7 blieben aus, und niemand bemerkte es.

**Was jetzt läuft.** Die Windows-Aufgabe **`TI-Bots-Autostart`** startet 2 Minuten nach jeder Anmeldung `pruefstand\autostart\bots_starten.py`. Läuft v7 nicht und liegt keine Datei `v7.BEWUSST_AUS` vor, startet das Skript die vorhandene `start_bot.bat` mit `TI_AUTOSTART=1`.

**Der automatische Klick.** Im Fenster-Modus handelt der Bot erst nach „▶ STARTEN“. Deshalb drückt das Cockpit mit dieser Variable nach 5 s selbst STARTEN (`ui/main_window.py`, Ende von `MainWindow.__init__`, Marke `AUTOSTART-KLICK 14.10.2026`). Ein Doppelklick auf `start_bot.bat` setzt die Variable nicht, dann bleibt alles wie bisher.

**Bot absichtlich aus lassen.** `pruefstand\autostart\BOT_BEWUSST_AUS.bat` doppelklicken.

**Anhalten für Patches.** `pruefstand\autostart\bot_anhalten.py v7 "Grund"`. Das Skript wartet auf die nächste Speicherung, beendet dann den Prozess und prüft, dass `bot_state.json` unverändert ist. Jeder Start und Stopp steht in `pruefstand\autostart\start_stopp.log`.
