<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · Hänger-Patch v6 + v7 und L14-Warte-Kauf-Felder v7 · „Log-Warteschlange gegen Hänger“ (ohne neue Epoche)

Registriert: 19.10.2026 ~23:05 Berlin, **vor dem Einspielen**. Grundlage: Svens Auftrag im Chat am 19.10.2026 („Ja, spiel jetzt beide Patches ein: den Hänger-Patch in v6 und v7 und den Pflichtfelder-Patch in v7, nach den üblichen Regeln mit W4-Anpassung“). Befund und Beweise: `berichte/2026-10-17_v6_haenger.md`.

## Änderung

| # | Bot | Datei | Art | vorher → nachher |
|---|---|---|---|---|
| 1 | v6, v7 | `ui/main_window.py`, Block „Logger-Callback für Live-Updates“ (v6 CRLF, v7 LF) | **ohne Handelswirkung**, Betrieb | Der Logger-Rückruf ruft nicht mehr `self.after(0, …)` aus fremden Threads auf, sondern reiht die Zeile in eine Warteschlange ein (`put_nowait`, Puffer 2000). Der Fenster-Thread holt alle 250 ms bis zu 200 Zeilen ab. Hängt das Fenster, laufen Handel, Stopp-Überwachung, `auto_save` und `system.log` weiter. |

Skript: `patches/patch_haenger_log_warteschlange.py v6|v7`, Marke `HAENGER LOG-WARTESCHLANGE`. In v7 kommt im selben Stopp **L14 Warte-Kauf-Felder** dazu (`epochen/L14_warte_kauf_felder.md`, ebenfalls ohne Handelswirkung).

## Epoche

Keine Handelsregel ändert sich. **Keine neue Epoche** (H1: „keine Handels-Epoche“). Die Version steht in Handbuch 10.19, in den Tickets und in `start_stopp.log`.

**Berichtigt 19.10. ~23:15:** Die Einträge `E15_log_warteschlange` / `L14_warte_kauf_felder` in `config_epochs.json` habe ich um 21:01 UTC angelegt und um ~21:10 UTC wieder zurückgenommen (Original aus der Sicherung, atomar; die Fassung mit Eintrag liegt als `config_epochs.json.mit_<id>_zurueckgenommen` daneben). Grund: Svens Entscheidung H1 sagt „keine Handels-Epoche“, und die Bots werten `config_epochs.json` selbst als Messgrenze aus (TERMINAL-Tab, Zahlenbuch, Vollständigkeit, Wochenbericht A). **Laufende Epoche bleibt v6 E14 / v7 L13.**

## Prüfung vor dem Einspielen (19.10.2026 ~23:00 Berlin)

- `--pruefen`: v6 BEREIT (CRLF), v7 BEREIT (LF). L14 v7 BEREIT (`execution/engine.py` CRLF).
- `--selbsttest`: Hänger-Patch v6 und v7 BESTANDEN. Verhaltenstests je 3/3: Alt verklemmt, Neu ohne Hänger, Grenzfall 2500 Zeilen bei längstem Log-Aufruf ≤ 3 ms. L14 BESTANDEN, Funktionsfälle 12/12, Handel identisch.

## Messgrößen (vorab)

| # | Messgröße | Erfolg |
|---|---|---|
| H1 | Nach dem Start erscheinen Logzeilen im Fenster, `system.log` wächst, W5 `bot_state` GRÜN | innerhalb von 5 min nach dem Start |
| H2 | Kein Stillstand mit `bot_state` ROT bei laufendem Prozess | 30 Tage ohne Vorfall |
| H3 | Handel unverändert: W4 `saldo`/`bestand`/`orders`/`gebucht_vs_kasse` grün | 24 h nach dem Start |

## Start

- Eingespielt 2026-10-19 um 21:00 UTC, **ohne neue Epoche** (siehe Berichtigung oben).
- Gestoppt mit `bot_anhalten.py`: v6 20:59:4x UTC (1 Position BTC 0,001467, USDC 280,77), v7 21:00:19 UTC (1 Position BTC 0,001404, USDC 114,79). Zustand nach dem Stopp unverändert.
- `--anwenden`: v6 Hänger 20:59:45 UTC (Sicherung `ui/main_window.py.bak_haenger_log_warteschlange_20261019_225945`, CRLF 3551/3551). v7 Hänger 21:00:27 UTC (LF), v7 L14 21:00:28 UTC (`execution/engine.py` CRLF 1582/1582, Marke 5×). Danach `--pruefen` überall „bereits angewendet“, Syntaxprüfung ok.
- Handbuch 10.19 in beiden Bots, je 3 Tickets (vom Bot um 23:02 verarbeitet, im ENTWICKLERHANDBUCH), BOT-HANDBUCH.pdf neu.
- Start über `schtasks /run /tn TI-Bots-Autostart` um 21:02 UTC, Ports 5050/5070 offen um 21:03:50 UTC. v6: „Positionen wiederhergestellt: 1 aktiv“, v7: BTC-Position im Zustand. `bot_state.json` wird wieder alle 30 s geschrieben, kein Fehler im Log (H1 erfüllt, außer der Anzeige im Fenster, die nicht eigens angesehen wurde).
- W4 angepasst (`PFLICHT_AB["v7"]` = L14-Start, Altkauf-Filter `KAUF_AB`). Probelauf: W4 v6/v7 `saldo`, `bestand`, `orders` grün, v7 `pflichtfelder` grün („0 Verkäufe seit L14“).
