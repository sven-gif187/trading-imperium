## 10.18 Kaufgröße aus dem Handelsgeld, ohne Sparplan (E14 / L13)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung KG1 („Die Kaufgröße wird nur aus dem Handelsgeld berechnet, das Sparplan-Bitcoin zählt nicht mit“) und KG1a („gilt für beide Bots“). Epoche v6 **E14_kaufgroesse_handelsgeld**, v7 **L13_kaufgroesse_handelsgeld** (beide 20:35:04 UTC).

**Was falsch war.** Seit E10-KAPITAL (29.07.) zählt `get_total_capital()` das Sparplan-BTC zum Kapital. Für den Drawdown-Guard und die Anzeige ist das gewollt. Der Block „MANUELLES SIZING“ in `app.py` rechnete daraus aber auch die **Kaufgröße**. Beleg aus v7 am 15.10. um 08:29 UTC:
1. Das Signal rechnete 117,44 $ (50 % von 234,88 $ Handelsgeld).
2. Der Sizing-Block überschrieb den Betrag mit 232,91 $ (50 % von 465,76 $ samt Sparplan).
3. Erst die Bargeld-Grenze kappte ihn auf 223,14 $.

Damit steckten 95 % der Handelskasse in einer einzigen Münze. In v6 war die Kasse nach dem dritten Kauf leer.

**Was jetzt gilt (v6 und v7 gleich).**
- `portfolio/manager.py` hat die neue Funktion `get_trading_capital()` = `get_total_capital()` minus Sparplan, nie unter 0. `get_total_capital()` ist unverändert.
- `app.py` rechnet im Block „MANUELLES SIZING“ die Kaufgröße aus `get_trading_capital()`. Das ist nur diese eine Stelle.
- Drawdown-Guard, Tagesverlust, Tagesstart-Kapital und Anzeige rechnen weiter **mit** Sparplan.
- **Folge:** v7 kauft für 50 % des Handelsgelds (≈ 117 $ statt ≈ 223 $), v6 für 30 % (≈ 122 $ statt ≈ 172 $). Ein Stopp kostet bei v7 rund 3 $ statt 6 $.

**Bewusst nicht geändert.** Der Münz-Deckel des Modus `balanced` in v7 (`max_coin_pct` 35) widerspricht Svens L7-Entscheidung „50 % und eine Position“ (25.09.) und wird weiterhin nicht durchgesetzt. Nach dieser Änderung bleiben Reserve und Deckel ohnehin eingehalten. Der stille Ersatz BTC/USDT in `fetch_snapshot` bleibt ebenfalls, er ist bekannt (`pruefstand\berichte\2026-10-15_kurse_nach_ausfall.md`).

**Geprüft:**
- Selbsttest: Kopie gepatcht, Zeilenenden byte-genau, idempotent, Original unberührt.
- 7 Funktionsfälle, darunter der v7-Log-Wert 117,44 $ und v6 122,44 $. Ohne Sparplan ändert sich nichts, und wirft die Sparplan-Bewertung einen Fehler, gilt das alte Verhalten.
- Sicherungen `*.bak_kg1_kaufgroesse_handelsgeld_20261015_2234*`.

**Betriebshinweis.** Die Bots liefen seit 20:11 Berlin nicht mehr. Ein Update der Claude-App hat sie beendet, weil sie mittags aus einer Claude-Sitzung heraus gestartet worden waren und dadurch an der App hingen. Ab jetzt startet eine Sitzung die Bots nur noch über die Windows-Aufgabe `TI-Bots-Autostart` (`schtasks /run /tn TI-Bots-Autostart`), nie direkt mit `bots_starten.py`.

Skript: `pruefstand\patches\patch_kg1_kaufgroesse_handelsgeld.py`. Vorab-Registrierung: `pruefstand\epochen\E14_L13_kaufgroesse_handelsgeld.md`.
