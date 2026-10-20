## 10.17 Nachzieh-Marge 0,10, STOPPEN-Knopf und Datenclient (E13 / L12)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung E5b („ja, auch 0,10“) und sein Auftrag „mach weiter mit den Kleinigkeiten“. Epoche v6 **E13_kleinigkeiten** (10:03:04 UTC), v7 **L12_kleinigkeiten** (10:03:05 UTC).

**1 · Nachzieh-Start mit derselben Sicherheit wie der Puffer (verhaltensändernd, v6 und v7).** In `risk/exit_rules.py` steigt `TRAIL_MARGE_PCT` von 0,05 auf 0,10. Der Start eines Nachzieh-Stopps liegt jetzt 0,10 Punkte über der Nulllinie:

| wirksamer Abstand | Start E11/L10 | Start E13/L12 |
|---|---|---|
| 0,85 % (EARLY_BEAR) | 1,06 | 1,11 |
| 1,0 % | 1,21 | 1,26 |
| 1,3 % (Trend) | 1,52 | 1,57 |

Der Grund ist derselbe wie beim Puffer (10.16): Ein Ausstieg löst im Mittel 0,072 % unter seiner Linie aus. Wächter W3 zeigt die Invarianten I1 und I2 jetzt grün.

**2 · STOPPEN-Knopf speichert wieder (nur v6, Befund 72).** `live/watchdog.py` hatte kein `stop()`, `app.py` rief es beim Abschalten trotzdem auf. Der Fehler brach das Abschalten ab, **bevor** der Positionsstand gespeichert wurde. Übernommen ist der Fix aus v7 (L6, 25.09.2026): `stop()` legt einen Riegel um, und `check()` startet danach nichts mehr neu. Für Patches gilt weiter `pruefstand\autostart\bot_anhalten.py`.

**3 · Kein roter Startfehler mehr (nur v6, P0-11).** `data/market_data.py` hat bei jedem Start eine feste Börsentabelle mit `ccxt.coinbasepro` gebaut. Das gibt es seit ccxt 4 nicht mehr. Die Folge war bei jedem Start „Client-Fehler (1. Versuch)“ und danach der Binance-Fallback. Jetzt wird nur die eingestellte Börse geholt, wie in v7 (`ccxt_id` = binance). Es ist also derselbe Client, nur ohne Fehlermeldung. Belegt im Log 10:03 UTC: „Client erstellt: Binance“ ohne Fallback.

**4 · `maker_schatten.py` rechnet mit Bitvavo-Gebühren (v6 und v7).** Bisher stand dort Bybit (Sofort-Auftrag 0,25 / Warte-Auftrag 0,10). Bei Bitvavo USDC kosten beide 0,05 %. Damit hat ein Warte-Auftrag keinen Gebührenvorteil mehr, messbar bleibt nur die halbe Spanne.

**Geprüft:**
- Funktionstest: Start ≥ Nulllinie + 0,10 für drei Abstände, Puffer bleibt 0,25, Bitvavo-Gebühren, Watchdog vor und nach `stop()`, kein `coinbasepro` mehr im Code.
- Zeilenenden byte-genau erhalten.
- Die Sicherung `watchdog.py.bak_e13_…` enthält das Original.
- Bots mit `bot_anhalten.py` gestoppt und per Autostart gestartet (10:04 UTC Ports offen).

Skript: `pruefstand\patches\patch_e13_kleinigkeiten.py`. Vorab-Registrierung: `pruefstand\epochen\E13_L12_kleinigkeiten.md`.
