<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Entscheidungsprotokoll · Prüfstand

Format: Datum · Entscheidung · wer · warum · Beleg. Neueste unten.

---

## 14.10.2026 · Antworten auf die Phase-0-Fragen (inventur.md Abschnitt 13)

| Nr. | Entscheidung | Wer | Warum / Beleg |
|---|---|---|---|
| F1 | **Im Prüfstand gilt die Konfidenz mit Prozent** ([SICHER]/[WAHRSCHEINLICH]/[VERMUTUNG] + Prozent, WEISS/SCHLIESSE/VERMUTE) nach MASTERPROMPT_AGENTEN.md. Die vier Stufen der v6-`CLAUDE.md` (ohne Prozent) gelten weiter in Sitzungen im Bot-Ordner. | Sven, Chat | Konflikt inventur.md Abschnitt 12. Sven als Eigentümer beider Regelwerke entscheidet. |
| F2 | **Der Prüfstand überwacht v6 und v7.** Zahlen bleiben strikt getrennt. | Sven, Chat | `instanzen.json` führt beide. |
| F3 | Die parallele Sitzung „Trading system status und entry method“ ist beendet. Der v6-Neustart um 10:08 kam von dort. | Sven, Chat | Befund P0-3 erledigt. |
| F4 | v7 läuft wieder. | Sven, Chat | Geprüft 10:36: PID 10452 seit 10:33:49 aus `v7\start_bot.bat`, Port 5070 lauscht, Log „Modus: paper“. |
| F5 | **Die Bots sollen nach einem Neustart oder einer Anmeldung automatisch wieder starten.** | Sven, Chat | Befund P0-2: 4,6 h Stillstand nach dem Windows Update am 14.10. Umsetzung: eigener Schritt, mit doppeltem Start ausgeschlossen (Port-Prüfung). |
| F6 | **v6 bekommt die vier Korrekturen von v7.** Umgesetzt als Epoche `E8_angleich_v7`, Start 2026-10-14T09:18:25Z. | Sven, Chat („alles tun, was das Projekt voranbringt“) | Vorab-Registrierung `epochen/E8_v6_angleich_v7.md`, BOT-HANDBUCH 10.11 |
| F8 | **Claude arbeitet den Plan selbstständig ab.** Rückfragen nur bei Echtgeld, Unumkehrbarem oder Börsen- und Strategiewahl. Die Handwerksregeln des Prompts gelten weiter. | Sven, Chat 14.10. | – |
| – | **v6 Epoche E9** (Befund 42, Kaufgebühr einfach) 09:35:46 UTC, **v7 Epoche L8** (Bybit-Einheitsgebühr) 09:51:17 UTC, **Autostart-Klick** in beiden. Umsetzung im Rahmen von F8. | Claude | `epochen/E9_…md`, `epochen/L8_…md`, Handbücher v6 10.11/10.12, v7 10.12 |
| Z1 | **Zielbörse und Kostenlatte: Bitvavo, USDC-Märkte** (0,05 % je Seite, K ≈ 0,150 % je Runde inkl. gemessenem Schlupf). **Beide Bots werden umgestellt**, mit neuer Epoche je Bot. Abschnitt 8 der v6-`CLAUDE.md` wird angepasst. | Sven, Chat 14.10.2026 („A Bitvavo, beide Bots umstellen“) | `berichte/2026-10-14_zielboerse.md` |
| Z2 | **Prüf-Agenten für Einstieg (A4) und Ausstieg (A5) starten sofort.** Sie suchen gewinnbringende Ein- und Ausstiege nach Kosten. Sie ändern nichts an den Bots, ihre Empfehlungen gehen über A10 an Sven. | Sven, Chat 14.10.2026 | – |
| Z3 | **Strategie-Labor Stufe 7 freigegeben:** Papier-Wettkampf A = heutiger Bot v6, B = K2 (Trend-Ensemble + BTC-200-Filter), C = K1 (Trend-Ensemble), B und C auf den 6 Bitvavo-USDC-Coins, je 500 $ Papier, mindestens 3 Monate. Messlatten M1–M3 laufen rechnerisch mit. | Sven, Chat 14.10.2026 („Stufe 7 freigegeben, C = K1“) | `berichte/2026-10-14_strategie_labor.md` |
| Z4 | **A5-Vorschlag V1:** Der Nachzieh-Start wird aus dem **wirksamen** Nachzieh-Abstand gerechnet (nach Regime-Skalierung und Trend-Bonus), nicht aus dem Config-Wert 1,0 %. Verhaltensänderung, also neue Epoche je Bot. | Sven, Chat 14.10.2026 („V1 Start aus wirksamem Abstand“) | `berichte/2026-10-14_ausstieg.md` |
| F5 | umgesetzt: Aufgabe `TI-Bots-Autostart`, `autostart/bots_starten.py`, Sperre `autostart/BOT_BEWUSST_AUS.bat` | Claude | Selbsttest 4/4, echter Start v6 11:18 erfolgreich |
| F5a | **Beide Bots (v6 und v7) sollen dauerhaft laufen.** Der Autostart gilt also für beide. | Sven, Chat | Antwort 14.10. |
| F7a | **Der Bybit-API-Schlüssel ist bei Bybit gelöscht.** Die Einträge in `v7\.env` sind damit wirkungslos. | Sven, Chat | Antwort 14.10. Nicht gegengeprüft (ginge nur durch Benutzen des Schlüssels). |
| – | Arbeitsstufe „Ultracode“ in der App ist eingeschaltet. Phase 0 wurde in voller Tiefe wiederholt (inventur.md v2). | Sven, Chat | Bildschirmfoto 14.10. |
| F7 | **v7 hat keinen Echtgeld-Zugang mehr.** Der Kommentar `_kommentar_live` in `v7\data_store\config.json` ist veraltet (aus Epoche L4, 16.–25.09.). | Sven, Chat | Log 14.10. 08:34 UTC: „Paper-Modus aktiv“, Telegram-Kennung PAPIER. Hinweis: `v7\.env` enthält weiter `BYBIT_API_KEY`/`BYBIT_API_SECRET` (gesetzt, Werte nicht gelesen). |

## 15.10.2026 · Entscheidungsvorlage nach A4, A5, Labor und A10 (`berichte/2026-10-15_entscheidungsvorlage.md`)

Antwort Sven im Chat am 15.10.2026: „E1 b, E2 ja, E3 jede, E4 ja, E5 ja, E6 a“.

| Nr. | Entscheidung | Umsetzung |
|---|---|---|
| E1 | **Die Hauptarbeit geht in die langsame Trendregel** (Papier-Wettkampf B/C gegen die 200-Tage-Regel). Der Kurzfrist-Bot läuft auf Papier unverändert als Vergleich und Messobjekt weiter, am Bot nur Kleinkram. Nach 3 Monaten (Mitte Januar 2027) entscheidet Sven: umstellen, weiter beobachten oder abbrechen. Kein Echtgeld. | Laufender Wettkampf S7 |
| E2 | **M3 (BTC über 200-Tage-Linie) ist Pflicht-Latte:** B/C gelten nur als besser, wenn sie den heutigen Bot **und** M3 schlagen. | S7-Nachtrag 2, `papier_tag.py` |
| E3 | **A = jede Version von v6 ab dem Start**, Epochengrenzen stehen im Wochenbericht. | wie in S7-Nachtrag 1 vorläufig eingetragen, jetzt fest |
| E4 | **W1 bekommt das Halteband:** Ein Auf- oder Abwärtstrend endet erst bei R ≤ 2 bzw. R ≥ −2. | `w1_marktlage.py` HALTEBAND = 2, Lage ab 01.01. neu geschrieben |
| E5 | **Puffer beim Absichern auf Null 0,195 → 0,25 %** (K + 0,10), aber **zusammen mit der nächsten Bot-Änderung**, nicht als eigene Epoche. | vorgemerkt, siehe `sitzung_stand.md` |
| E6 | **Ausstiegs- und Halte-Ideen** (X1 2 × ATR, 12 h Halten mit Notstopp und einer Position je Münze, RSI-Verkaufssignal, je Marktlage) werden **monatlich offline aus den vorhandenen Daten** nachgerechnet, ohne Eingriff in den Bot. Gepaarte Vergleiche immer zerlegt in Kurseffekt, Kosten und Abschlag (A10). | Monatsmessung als Windows-Aufgabe |
| E5 | **umgesetzt 15.10.2026 09:35:57 UTC** zusammen mit Befund 88 als v6 **E12_puffer_pflichtfelder** und v7 **L11_puffer_pflichtfelder**. Der Puffer liegt bei 0,25 %, W3 I1 ist grün. | `epochen/E12_L11_puffer_pflichtfelder.md`, Handbuch 10.16 |
| E5b | **Der Nachzieh-Start bekommt dieselbe Marge 0,10 wie der Puffer** (bisher 0,05, W3 I2 gelb). Start bei 0,85 → 1,11, 1,0 → 1,26, 1,3 → 1,57. Mit der nächsten Bot-Änderung. | Sven, Chat 15.10.2026 („ja, auch 0,10“). Dazu: „mach weiter mit den Kleinigkeiten“ und eine neue Sitzung für A1–A11 starten. |
| E5b | **umgesetzt 15.10.2026 10:03 UTC** als v6 **E13_kleinigkeiten** / v7 **L12_kleinigkeiten**, zusammen mit Befund 72 (v6), P0-11 (v6) und `maker_schatten` (beide). W3 I1/I2 grün. | `epochen/E13_L12_kleinigkeiten.md`, Handbuch 10.17 |

## 15.10.2026 · Erster Lagebericht des Leitstands (`berichte/2026-10-15_lage.md`, Punkt 1)

Antwort Sven im Chat am 15.10.2026: „Ich entscheide: Die Kaufgröße wird nur aus dem Handelsgeld berechnet, das Sparplan-Bitcoin zählt nicht mit. Bitte in entscheidungen.md eintragen. Umsetzung mit der nächsten Bot-Änderung als eigene Epoche.“

| Nr. | Entscheidung | Umsetzung |
|---|---|---|
| KG1 | **Die Kaufgröße wird nur aus dem Handelsgeld berechnet. Das Sparplan-Bitcoin zählt nicht mit.** Hintergrund: Die Basis der Kaufgröße enthält heute den Sparplan (v7 `portfolio/manager.py:116-121`, Kommentar „[E10-KAPITAL] Sparplan-BTC gehoert zum Kapital“, Zuweisung `app.py:1635-1641`). Deshalb hält v7 rund 95 % der Handelskasse in einer BTC-Position, eingestellt sind 35 % je Münze und 10 % Reserve. Folge laut Lagebericht: v7 kauft für ≈ 117 $ statt ≈ 232 $, v6 für ≈ 122 $ statt ≈ 172 $. Ein Stopp kostet bei v7 rund 3 $ statt 6 $. | **Vorgemerkt, noch nicht umgesetzt.** Mit der nächsten Bot-Änderung als **eigene Epoche** (Vorab-Registrierung, `bot_anhalten.py`, Patch-Skript, Handbuch, Tickets). (1) Geltungsbereich geklärt, siehe KG1a. (2) Bei der Umsetzung klären: Der Fehlerteil „begrenzen statt ersetzen“ (der berechnete Betrag überschreibt die geprüften Grenzen für Reserve und Münz-Deckel, `app.py:1587-1594`) ist von Sven nicht eigens entschieden. A10 trennt ihn als Fehler von der Risikofrage. Nachtrag 15.10.: **nicht nötig**, siehe `epochen/E14_L13_kaufgroesse_handelsgeld.md`. Der v7-Münz-Deckel von 35 % widerspricht Svens L7-Entscheidung „50 % und eine Position“ (25.09.), und nach KG1 bleibt die Reserve von selbst frei. |
| KG1a | **KG1 gilt für beide Bots, v6 und v7.** v6 ist im Papier-Wettkampf Teilnehmer A. Laut E3 zählt jede v6-Version, die Epochengrenze wird im Wochenbericht vermerkt. | Sven, Chat 15.10.2026 („KG1 gilt für beide Bots, v6 und v7.“). Umsetzung wie KG1: nächste Bot-Änderung, eigene Epoche je Bot (v6 E…, v7 L…). Die Zuweisungszeile in v6 ist noch nicht einzeln gelesen (Lagebericht: [WAHRSCHEINLICH 88 %]), vor dem Patch prüfen. |
| KS1 | **Kaufsperre bei altem Kurs:** Keine Käufe, solange der Kurs älter als 2 Minuten ist. Verkäufe und Verlustbremse bleiben frei. Zusammen mit KG1 einspielen, beide Bots. | Sven, Chat 15.10.2026 („Ja: Die Bots sollen keine Käufe machen, solange ihr Kurs älter als 2 Minuten ist … zusammen mit KG1 einspielen (beide Bots)“). **Angehalten, nichts eingespielt:** Die Grundlage war falsch. Der Kurs war nicht alt (Datenalter im Oktober höchstens 22 s), sondern kam vom Ersatzpaar USDT (`berichte/2026-10-15_kurse_nach_ausfall.md`, Berichtigung). Rückfrage an Sven, ob stattdessen der USDT-Ersatz gesperrt werden soll. |
| KS1b | **Keine Kaufsperre. Nur KG1 wird jetzt in beide Bots eingespielt.** KS1 ist damit verworfen. | Sven, Chat 15.10.2026: Er verstand die Rückfrage nicht und übertrug die Wahl („ja du bist der meister und ich richte mich nach dir, deinen vorgaben und empfehlungen“). Claudes Empfehlung war „nur Kaufgröße“: Das Ereignis vom 15.10. kostete etwa 20 Cent, und jede zusätzliche Bot-Änderung bringt eigenes Fehlerrisiko. Der stille USDT-Ersatz in `fetch_snapshot` bleibt bekannt (`berichte/2026-10-15_kurse_nach_ausfall.md`) und kann später als Kleinkram kommen. |
| KG1 | **umgesetzt 15.10.2026 20:35 UTC** als v6 **E14_kaufgroesse_handelsgeld** und v7 **L13_kaufgroesse_handelsgeld**. Die Bots waren seit 20:11 Berlin wegen des Claude-App-Updates aus und wurden über `TI-Bots-Autostart` neu gestartet. | `epochen/E14_L13_kaufgroesse_handelsgeld.md`, Handbuch 10.18 |
| F5b | **Ausgefallene Bots starten von selbst wieder, geprüft wird alle 15 Minuten.** Wer einen Bot absichtlich aus haben will, legt vorher die Sperre mit `autostart\BOT_BEWUSST_AUS.bat`. Patches laufen weiter über `bot_anhalten.py`, das die Sperre selbst setzt. | Sven, Chat 15.10.2026 („Ja: Die Bots sollen von selbst wieder starten, wenn sie ausgehen (Prüfung alle 15 Minuten). Wenn ich einen Bot absichtlich ausmachen will, nehme ich BOT_BEWUSST_AUS.bat.“). Anlass: Am 15.10. waren beide Bots von 20:11 bis 22:36 aus, weil das Update der Claude-App sie beendet hatte. Umsetzung: eigene Aufgabe `TI-Bots-Neustart`, `bots_starten.py --takt` (leise, mit Startsperre gegen einen Doppelstart). |

## 15.10.2026 · Wächter-Lücken (`berichte/2026-10-15_waechter_luecken.md`)

| Nr. | Entscheidung | Wer | Warum / Beleg |
|---|---|---|---|
| WL1 | **W3-Monatsregel neu:** GELB nur, wenn Brutto > 0 und Gebühren > Brutto (Kosten machen aus Gewinn Verlust) oder wenn Brutto ≤ 0 und die Gebühren > 50 % des Nettoverlusts sind (Startwert [VERMUTUNG]). Ein Verlust schon vor Kosten ist GRÜN mit Hinweis auf W7. Weicht vom Wortlaut in Masterprompt 6.1 („Gebühren im Monat > Brutto im Monat“) ab, dort sind die Schwellen Startwerte. | Claude, im Rahmen von F8 | Die alte Regel war in jedem Verlustmonat wahr (Agententest 3.4). v6 Oktober: Gebühren 13 % des Verlusts, v7 14 %, beide jetzt GRÜN. |
| WL2 | **W4 zählt Saldo und Orders weiter ab seinem ersten Lauf (14.10. 20:15 UTC), nicht ab E10/L9.** | Claude, im Rahmen von F8 | Die einzige Runde in der Lücke (v6, 14.10. 14:28 UTC) ist auf drei Wegen nachgeprüft (Journal = Order-Historie = Telemetrie-Kasse +172,71 $). Ein Epochen-Anker bräuchte die Kasse aus der Bot-Telemetrie als Startwert. |
| WL3 | **W7: Ein CUSUM-Bruch ist erst ab 30 Runden im Fenster GELB,** darunter heißt er „nicht entscheidbar“ (Masterprompt 6.1). | Claude | v7 hat 17 Runden. Bei 2–10 Runden schlägt der CUSUM schon bei wenigen Verlusten an. |

## 17.10.2026 · Leitstand-Wiederholung (`skripte/leitstand_lauf.py`)

| Nr. | Entscheidung | Wer | Warum / Beleg |
|---|---|---|---|
| LW1 | **Der Leitstand-Lauf wiederholt vorübergehende Fehler selbst:** bis zu 3-mal nach 2 / 3,5 / 5 min, nur wenn claude noch nichts gekostet hat (Kosten 0, höchstens 1 Turn, keine echte Modell-Antwort) und der Grund die OAuth-Erneuerung oder ein API-Fehler ist. Ein Lauf mit Kosten wird nie wiederholt, Kosten-Deckel und Telegram-Sperre bleiben gleich. | Claude, im Rahmen von F8 | 17.10. 07:30 endete der Tageslauf nach 7 s mit „Failed to refresh OAuth token …“ (Code 1). Die Aufgabe wiederholt bei Code 1 nicht. `--selbsttest` 3/3, `probelauf` mit Attrappe 3/3. |
| LW2 | **Der Lagebericht vom 17.10. wird nicht nachgeholt.** Der nächste Tageslauf am 18.10. 07:30 läuft normal. | Sven, Chat 17.10.2026 („AUSLASSEN“) | Nachholen hätte etwa 3 $ gekostet. |

## 19.10.2026 · Hänger-Schutz, nächster Strategie-Schritt, GitHub (Sven, Chat ~23:05)

| Nr. | Entscheidung | Umsetzung |
|---|---|---|
| H1 | **Der Schutz gegen das Einfrieren kommt heute in beide Bots** (`patches/patch_haenger_log_warteschlange.py`, Bericht `berichte/2026-10-17_v6_haenger.md`), mit den Auflagen von A10 aus dem Lagebericht 19.10.: direkt vorher `--pruefen` und `--selbsttest`, Anhalten und Neustart in `start_stopp.log`, Verkäufe in den ersten 15 min nach dem Neustart als „Neustart-Ausstieg“ getrennt, ein Zeitpunkt ohne Stopp kurz vor dem Auslösen. Keine Handels-Epoche. Neustart nur über `TI-Bots-Autostart`. | heute |
| S1 | **Der Kurzfrist-Bot kauft nur noch, wenn die Marktlage (W1) „Aufwärts“ meldet**, sonst Kauf-Pause. Verkäufe laufen weiter. Als neue Epoche mit Vorab-Registrierung und Gegenprüfung A10, nur Papier. | Entwurf, Registrierung, Patch |
| G1 | **Bot als Open Source auf GitHub:** ein **neues, sauberes öffentliches Repo** mit v6, v7 und dem Prüfstand, **Lizenz GPL-3.0**. Die bestehenden privaten Repos werden **nicht** auf öffentlich gestellt (alte Versionsgeschichte). Ohne Daten, Logs, `.env`, Schlüssel, Tokens und fremden Code, mit Geheimnis-Scan, README mit ehrlichem Stand, Haftungsausschluss und Regeln fürs Mitmachen. **Veröffentlicht wird erst nach Svens Durchsicht und ausdrücklichem OK.** | Vorbereitung |

## 19.10.2026 · Hänger-Patch und v7-Warte-Kauf-Felder einspielen

| Nr. | Entscheidung | Wer | Warum / Beleg |
|---|---|---|---|
| HP1 | **Beide Patches werden jetzt eingespielt:** Log-Warteschlange gegen Hänger in v6 und v7, Warte-Kauf-Felder (Befund 88, Rest) in v7, mit W4-Anpassung. | Sven, Chat 19.10.2026 („Ja, spiel jetzt beide Patches ein: den Hänger-Patch in v6 und v7 und den Pflichtfelder-Patch in v7, nach den üblichen Regeln mit W4-Anpassung.“) | `berichte/2026-10-17_v6_haenger.md`, `epochen/L14_warte_kauf_felder.md` |
| HP2 | **Keine neue Epoche.** Meine zuerst angelegten Einträge E15/L14 in `config_epochs.json` sind zurückgenommen. Laufend bleibt v6 E14 / v7 L13. | Claude, nach H1 („keine Handels-Epoche“) | Die Bots lesen `config_epochs.json` selbst als Messgrenze (TERMINAL-Tab, Zahlenbuch, Vollständigkeit, Wochenbericht A); `epochen/E15_L14_log_warteschlange.md` |
| G2 | **Repo-Name `trading-imperium`**, der alte V4-Bot (`v4_referenz/`) bleibt draußen, **zuerst PRIVAT hochladen**. Öffentlich erst nach Svens zweitem OK. | Sven, Chat 20.10.2026 |
