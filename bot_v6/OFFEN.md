# OFFEN — alles, was noch aussteht

**Angelegt 18.08.2026.** Diese Datei ist **die eine Liste**. Was hier
nicht steht, ist nicht offen. Was hier steht, ist nicht vergessen.

Anlass: An einem einzigen Tag habe ich zweimal etwas als „fertig"
gemeldet, das ich selbst vorgeschlagen hatte — zuletzt die Auswertung
der Merkmals-Schnappschüsse. Ein Vorschlag, der nur im Chat steht, ist
vergessen, sobald das Fenster weiterläuft.

**Regel 1 — Herkunft:** Kein Punkt kommt auf diese Liste, weil er in einer Übergabe oder im Chat stand. Jeder Punkt wird vorher **gegen das Verzeichnis geprüft** — Commits, Handbuch, Code. Eine Übergabe ist eine Momentaufnahme mit Uhrzeit; was danach passiert ist, steht nicht drin.

*Warum diese Regel existiert:* Am 18.08. stand „Log-Farben ansehen“ auf dieser Liste, obwohl die Arbeit am 17.08. **nach** dem Schreiben der Übergabe fertig geworden war (Commit `fc9afab`, Handbuch 4.42). Sven musste es anmahnen.

**Regel 2:** `- [ ]` heißt offen, `- [x]` heißt erledigt mit Beleg. Nach
jedem Commit zeigt der Haken `.git/hooks/post-commit` die offenen Punkte
der Gruppe A an. Erledigte Punkte bleiben stehen — die Liste ist auch
ein Nachweis.

---

## A — Jetzt möglich, Freeze-sicher (nur lesen und schreiben)

- [x] **Merkmals-Schnappschüsse ausgewertet** — `merkmale_auswertung.py`, Handbuch 4.52. Ergebnis: Schwäche ging steigenden Kursen voraus, Stärke fallenden; bester Vorsprung +0,19 % gegen 0,505 % Kosten je Runde.
- [x] **`volume_ratio` geklärt** — kein Formelfehler, sondern ein Vergleich zwischen laufender und abgeschlossener Kerze. `volume_ratio` und `high_low_range` messen die verstrichene Stunde, nicht den Markt (Faktor 100). `GEFUNDENE-PROBLEME.md` 39.
- [x] **Zahlenbuch** — von Sven am 18.08. geschlossen: kein Bedarf. Der Wunsch „leserlicher, wie die Chartbilder“ aus der Übergabe hat sich mit den Abschnitten 10 und 11 (Handbuch 4.32) erledigt.
- [x] **Log-Farben** — erledigt am 17.08., Commit `fc9afab`. Der Fehler darin („BUY“ als Handelsmerkmal, wodurch Vorschläge und Ablehnungen wie ausgeführte Trades aussahen) wurde gefunden **und behoben**, Handbuch 4.42. *Stand hier faelschlich offen — aus der Übergabe von 11:05 abgeschrieben, fertig wurde es um 13:13.*
- [x] **Suchauftrag alte Kostenannahmen erledigt** — es sind **neun** Stellen, nicht zwei. Handbuch 4.53. Fünf Messwerkzeuge mit 0,32, dazu `app.py:3563` (2 × 0,10) und zwei Rückrechnungen. Nur `schwelle_vergleich.py:77` ist mit 0,505 richtig.
- [x] **Trainings-Bruch beim KI-Modell geprüft — er ist da.** `models/xgboost_model.py:106` sagt auf `df.iloc[-1]` vorher, also auf der **offenen** Kerze; trainiert wurde auf abgeschlossenen. Zwei von dreizehn Merkmalen liegen im Betrieb außerhalb des gelernten Bereichs. `GEFUNDENE-PROBLEME.md` 39.
- [x] **Audit vollständig — alle sechs Etappen durch.** Handelskette, Ausstieg/Risiko, Order-Lebenslauf, Nebenläufigkeit, Datenabgleich, Marktvergleich. Befunde 40–54, Handbuch 4.59–4.75.


- [x] **Zwei Messwerkzeuge gebaut** (19.08.) — `positionsverlauf.py` (laeuft alle 5 Min, zeichnet je Position Preis/ATR/RSI/Struktur auf; damit ist jede Ausstiegsregel rueckwirkend rechenbar) und `drawdown_auswertung.py`. Handbuch 4.63.
- [x] **Groesster Rueckschlag gemessen** — 13,11 % (mit Sparplan-BTC) bzw. 3,64 % (ohne). Beide **im Ziel** von 15 %. Damit ist die vierte Zielgroesse belegt.
- [x] **Etappe 2 des Audits: Ausstieg und Risiko** — Befunde 45–47. Kernfund: Die Trailing-Schwelle steht bei 1,2 %, rentabel wird sie erst ab 1,52 %. 74 von 135 Trailing-Ausstiegen (55 %) enden brutto im Plus, netto im Minus. Handbuch 4.64.
- [x] **`stichtag.py` gebaut** — prüft am 27.08. automatisch Datenlage, Zielgrößen, unveränderte Codestellen und listet die acht Entscheidungen. Stand heute: 7× FEHLT, 2× PRÜFEN. Handbuch 4.65.
- [ ] **Ausstiegsregeln gegeneinander rechnen** — Werkzeug ist fertig: `ausstieg_vergleich.py` spielt acht Kandidaten auf denselben aufgezeichneten Verläufen ab, gegen die Trivial-Latte, nach Kosten. Selbsttest in beide Richtungen bestanden. **Es fehlen nur noch die Daten:** heute 5 echte Verläufe, und deren Aufzeichnung endet beim Verkauf des Bots — eine Regel, die *später* ausgestiegen wäre, lässt sich daran nicht messen. Die 16 Schattenpositionen laufen bis `MAX_TAGE = 7` durch und schließen **am 21.08.** alle auf einmal. Dann erstmals rechnen. Handbuch 4.100.
- [x] **Zielgrößen festgelegt** — am 19.08. entschieden und in `config_zielgroessen.json` eingetragen: zwei Klassen. **Freischaltung** (Erwartungswert > 0 %, größter Rückschlag ≤ 20 %) sperrt den Live-Gang, alles Übrige läuft im Schattenmodus mit. Der Punkt stand hier nur noch als Rest. Handbuch 4.80.
- [x] **Täglicher Sammler geklärt — er läuft.** Aufgabe `TI6-Sammler`, letzter Lauf **18.08. 06:00 mit Ergebnis 0**, nächster 19.08. 06:00. Er startet `job_sammler.py` einmal täglich und beendet sich; deshalb meldet `prozess_frische.py` „läuft nicht" — das ist bei einer geplanten Aufgabe normal. Beleg für die Daten: `metals/metals_data/scan_log.jsonl` reicht bis zum 18.08., die letzten sechs Tage lückenlos. Die alte `sammler.log` vom 10.08. stammt vom früheren Startweg. **Mein Verdacht war ein Fehlalarm.**
- [ ] **RSI-Ausstieg: Nachlauf weiter sammeln** (59) — gemessen 19.08.: nach RSI-Ausstiegen stieg der Kurs in der Folgestunde um im Schnitt **+5,15 %** weiter (n=2), nach Trailing-Stops um −0,51 % (n=4). **Warnsignal, kein Beleg** — beide RSI-Faelle am selben Tag, also faktisch einer. Ab n≈10 entscheidbar. Es wird nichts geaendert, die Messung laeuft von selbst mit. Handbuch 4.83.
- [ ] **Mark nachfragen.** Sein Bild vom 17.08. (BTC 4-Stunden, Ist-Kurs 63.637,05 $) enthält keine Prognose — Richtung, Ziel und Frist fehlen. Vier Pflichtangaben, Anleitung Handbuch 4.46.
- [ ] **Testnetz-Durchlauf** — Werkzeug ist fertig: `TESTNETZ_PROBE.bat` doppelklicken. Prueft den Order-Pfad an einer echten Boerse mit Spielgeld: kommt die Order an, wird bei einer Wiederholung **doppelt gekauft**, wie reagiert die Boerse auf eine zu kleine Order, ist der Auftragsstatus abfragbar, wie gross sind Gebuehr und Schlupf wirklich, stimmt der Kontostand. **Fehlt nur noch:** Sven holt sich Testnetz-Schluessel bei `testnet.binance.vision` und traegt sie als `BINANCE_TESTNET_KEY` / `_SECRET` in `.env` ein. Kein Eingriff in den Bot, kein Echtgeld. Handbuch 4.112.
- [ ] **Tilo im Blick behalten.** XRP-Ruf auf 0,30 $ bis Jahresende. Stand 17.08.: 1,0020 $ — nötig wären −70 %.

- [x] **Die stillgelegten Bausteine durchrechnen — erledigt 25.08.2026.** **Am 25.08. war der Befund: nur zwei von sechs Bausteinen ueberhaupt auswertbar** — die Notizbuecher schrieben auf, was eine Regel getan HAETTE, aber nicht, wie es AUSGING (**Befund 77**). **Am 26.08. behoben und fertig gerechnet.** Horizont **24 Stunden** von Sven entschieden — bei 1 h ist die typische Bewegung achtmal kleiner als die Gebuehr. **Befund 77 behoben:** die Notizbuecher haengen jetzt am Nachlauf-System, 1.946 von 2.084 mit 24-h-Kurs, null verloren. **Ergebnis KI-Modell: kein Vorsprung** — 30,8 % gegen 30,8 % Trivial-Latte. **Ergebnis Groessenrechner: haette geschadet** — 8,30 $ ueber 37 Positionen, und schlechter als das stumpfe Halbieren. Er verkleinerte die Gewinner haerter als die Verlierer. Einschraenkung: 35 Gewinner gegen 2 Verlierer, wofuer er gebaut ist wurde nie geprueft — erneut ansehen ab zehn Verlierern. Handbuch Teil 5.10 und Teil 6.6.

- [x] **Die fuenf ungenutzten Strategien — erledigt 25.08.2026. Ergebnis: VERWERFEN.** Nachgerechnet an **779 echten Verkaeufen** des V4-Referenzbots mit den gemessenen Kosten je Muenze. Vier der fuenf verlieren nachweislich Geld: ICHIMOKU_CLOUD **-642,57 $** bei 267 Handeln (Median -0,42 $), EMA_TREND **-545,35 $** bei 167 (Median -0,58 $), STOCHRSI_REVERSAL -89,46 $ bei 15 % Trefferquote, TSI_SIGNAL nur 11 Faelle und damit nicht entscheidbar. Die fuenfte, MOMENTUM_BREAKOUT, sieht mit +420,87 $ nach einem Kandidaten aus — **ihr Median je Handel liegt aber bei -0,03 $**, der gesamte Gewinn haengt an EINEM Handel vom 21.08. (SOL +607,23 $). **Der eigentliche Hebel liegt woanders:** ICHIMOKU_CLOUD und EMA_TREND stehen fuer 434 von 779 Verkaeufen und zusammen -1.188 $ — sie gehoeren heruntergewichtet, nicht die anderen dazugenommen (Punkt 8a). Die drei gesperrten Strategien sind **richtig** gesperrt, alle drei verlieren. Vollstaendig in `BOT-HANDBUCH.md` Teil 5, Abschnitt 5.9.

- [ ] **Mehrzeitrahmen-Analyse für alle drei Münzen.** `app.py:2538` rechnet sie nur für **eine** (`for coin in coins[:1]  # BTC als Regime-Indikator`). Der Trend-Ausstieg sucht sie aber je Münze (`runtime/exit_monitor.py:275`) und findet für ETH und SOL nichts — die Regel **kann** dort technisch nie greifen. Der Wächter meldet das selbst (`exit_monitor.py:292-299`: *„multi_tf laeuft nur fuer coins[:1]"*). **Muss behoben sein, BEVOR der Trend-Ausstieg je scharf geschaltet wird** — sonst gilt eine Regel für ein Drittel des Bestands, und niemand sieht den Unterschied. Handbuch Teil 3, Abschnitt 3.5.

- [ ] **Automatischer Epochen-Schnitt.** Der Bot merkt, wenn eine Einstellung sich ändert, führt aber keine Epochengrenze mit — `config_epochs.json` wird von Hand gepflegt (nachgeprüft 25.08.: kein Programmteil schreibt sie). Folge: Auswertungen können Ergebnisse aus verschiedenen Regelwerken vermischen. Genau das ist am 15.08. beinahe passiert, als der lernende Wächter selbständig eine Schwelle verstellte. Handbuch Teil 10, Abschnitt 10.3.

- [ ] **Wiederkehrende Berichte.** `stoploss_analyse.py` und `regime_filter_messung.py` beantworten Fragen, die sich immer wieder stellen, laufen aber nur auf Zuruf. Als wöchentlicher Bericht — Vorbild ist der Chartanalyse-Agent — würden sie eine Verschlechterung von selbst melden, statt darauf zu warten, dass jemand nachsieht. Handbuch Teil 8, Abschnitt 8.4.

- [ ] **Neue Funde aus dem Handbuch-Umbau landen hier.** *Sven am 25.08.2026: „auch für zukünftige Sachen, die wir jetzt in den folgenden Arbeitsschritten noch finden, während wir das Buch vervollständigen."* Der Umbau geht Teil für Teil durch Code und Daten und fördert dabei Befunde zutage, die keiner Suche entsprangen. **Regel:** Jeder dabei gefundene Punkt kommt in diese Liste, mit Verweis auf den Handbuch-Abschnitt, in dem die Belege stehen. Stand des Umbaus: `docs/handbuch_umbau_2026-08/UMBAU-LISTE.md`.

- [ ] **Chance/Risiko als Filter der Chartanalyse messen** (81) — *Svens Frage vom 26.08.: „wie koennen wir das verbessern?"* **Der einzige Hebel, der in den Daten greift.** Gerechnet ueber 2.589 einzigartige Signale: alles nehmen **-0,455 %** (sicher verliert), nur Guete >= 0,8 **-0,406 %** (sicher verliert, also wertlos), nur **Chance/Risiko >= 1,5 +0,395 %**, nur **>= 2,0 +0,772 %**. Die Trefferquote faellt dabei von 71 % auf 35 % — genau das ist der Punkt. **Aber nur 105 bzw. 55 Faelle, damit nicht entscheidbar.** Zu tun, alles freeze-vertraeglich: (a) `chartanalyse_backtest.py` haeufiger und ueber mehr Muenzen/Zeitrahmen laufen lassen, bis 30 unabhaengige Faelle je Schwelle stehen; (b) die Zielwahl in `features/chartanalyse.py:359` korrigieren — als Kursziel nur Zonen nehmen, deren UNTERKANTE ueber dem Kurs liegt — und danach neu messen. Handbuch Teil 6, Abschnitt 6.9.

- [ ] **Schatten-Universum: mehr Positionen je Muenze zulassen** (82) — *Antwort auf Svens Frage nach mehr Schattenwaechtern: es fehlt keiner, der vorhandene wirft 97,5 % weg.* 1.266 Signale ergeben nur 32 Positionen, weil je Muenze immer nur EINE offen ist (bis `MAX_TAGE = 7`). Fuer 30 Faelle je Muenze braucht es so **210 Tage**; bei 5 gleichzeitigen waeren es **42**, bei 10 nur **21**. Signale sind reichlich da (9 bis 13 je Muenze und Tag). **Vorher zu klaeren:** ab wann gilt ein Signal als NEUE Gelegenheit und ab wann als dieselbe? Ohne diese Abgrenzung entstehen Scheindaten. Reines Aufschreiben, aber Verhaltensaenderung am Sammler. Handbuch Teil 6, Abschnitt 6.2.

- [x] **Bollinger-Baender im Analyse-Reiter** — *erledigt 29.08.2026.* Drei blaue Kurven: oberes und unteres Band durchgezogen, der gleitende Durchschnitt gestrichelt dazwischen (20 Perioden, 2 Standardabweichungen). Gerechnet auf allen 300 Kerzen, gezeigt die sichtbaren 150 — sonst wären die ersten 20 Punkte leer. Lücken unterbrechen die Kurve, statt eine Verbindung zu behaupten, die es nicht gibt. Nachweis: 3–4 Kurvenzüge je Chart mit rund 440 Punkten, kein einziger waagerecht. Der Zeichentest prüft jetzt auch, ob das **obere Band wirklich über dem unteren** liegt — wäre die Rechnung vertauscht, sähe der Chart trotzdem plausibel aus. **Sichtbar nach dem nächsten Neustart.** Handbuch 6.9.

- [ ] **Trägt Bollinger überhaupt?** — *offen seit 29.08., seit die Bänder gezeichnet werden.* Wie bei Fibonacci: **ungemessen**. Zu messen gegen die **Trivial-Latte** — was passierte, wenn der Kurs ein Band berührte, gegen einen zufällig gesetzten Zeitpunkt? Getrennt für oberes und unteres Band, und getrennt nach Marktlage: ein Band-Kontakt im Aufwärtstrend bedeutet etwas anderes als im Seitwärtsmarkt. **Fallzahl-Falle:** ein Kurs, der am Band entlangläuft, liefert nicht hundert Belege, sondern einen. Freeze-verträglich, reines Rechnen.
- [ ] **Trägt Fibonacci überhaupt?** — *Offen seit 27.08., seit die Linien gezeichnet werden (85).* Der Chart zeigt sie jetzt, **ob sie etwas wert sind, ist ungemessen.** Zu messen wie bei MACD und PVSRA (84): Was passierte, wenn der Kurs eine Rückzugsmarke berührte — gegen die **Trivial-Latte**, also gegen eine zufällig gesetzte Linie gleicher Lage? Getrennt für 0,382 / 0,5 / 0,618 und für die Wurzelverhältnisse 0,707 / 0,866, die Mark zusätzlich benutzt. **Fallzahl-Falle beachten:** Ein Kurs, der eine Stunde an einer Linie klebt, liefert nicht zwölf Belege, sondern einen. Reines Rechnen auf Kursdaten, **freeze-verträglich**, kein Neustart nötig.

- [ ] **Trifft Fibonacci auf MONATSkerzen besser?** — *Svens Eingang 28.08.: „laut ihm im treffen monatstimeframe sein besser.“* Marks eigene Aussage, **nicht belegt**. Der Reiter kann seit dem 28.08. Monatskerzen anzeigen (vorher nur 15m/1h/4h/1d), damit ist es überhaupt nachsehbar. **Die Falle steht schon fest:** BTC hat bei Binance **109 Monatskerzen insgesamt** (ab Aug 2017). Bei drei Monaten Messhorizont sind das rund **36 unabhängige Fälle** — zum Vergleich stützte sich die MACD-Messung (84) auf Tausende. **Erwartbares Ergebnis: „nicht entscheidbar“** — und das ist dann auch das ehrliche Ergebnis, kein Fehlschlag. Vorher zu klären: was heißt bei ihm „trifft“ — Zone berührt, oder Kurs dreht dort? `prognosen/MARK.md`.

- [ ] **Warum ist die Trefferquote in E7 eingebrochen?** (86) — *Gefunden 29.08. beim Vergleich gegen blind getestete Signalanbieter.* E7 hat das Gewinn/Verlust-Verhältnis fast repariert (0,43 → **0,98 : 1**), aber die Trefferquote fiel von 67 auf **45,2 %**. Der schärfere Filter hat offenbar auch gute Einstiege aussortiert. **Zu messen — freeze-verträglich, reines Rechnen:** Welche Einkäufe lässt E7 weg, die unter E5/E6 gewonnen hätten? Das Schatten-Notizbuch sollte das beantworten können. **Nötig zum Break-even:** +5,4 Prozentpunkte Trefferquote *oder* Verhältnis über **1,22 : 1** (Zielgröße im Projekt: 1,27 — unabhängig fast dieselbe Zahl). **Urteil noch nicht möglich:** 62 von 100 Verkäufen. `python provider_vergleich.py`, Handbuch 10.9.

- [ ] **Vier Analysefelder nachtragen — und drei künftig mitschreiben** (88) — *Von Sven am 29.08. aus der Vollständigkeitsprüfung geholt. Stand seit dem 21.08. in der Chronik, hatte aber nie eine Nummer und stand nie hier — genau deshalb war es kein offener Punkt.* **Zwei Schreibwege schreiben je ihre Hälfte**, bei drei Feldern schreibt keiner. **Nachtragen — aber NUR bei gestopptem Bot** (29.08. geprüft: ein Nachtrag bei laufendem Bot hielt **41 Sekunden**, dann überschrieb `app.py` die Datei aus dem Arbeitsspeicher). Es sind **zwei** Felder, nicht vier: `position_id` und `haltedauer_min` (je +12 Verkäufe). `entry_strategie` und `entry_score` haben in der Quelle nichts stehen — `positionen.strategie` ist bei allen 58 echten Positionen **leer**. Ablauf: Bot beenden → `python felder_nachtragen.py --schreiben` → Bot starten. Das Werkzeug bricht von selbst ab, solange der Bot läuft. **Nach dem Stichtag:** `stop_initial`, `trailing_stop_pct`, `decision_id` beim Verkauf mitschreiben — sie stehen am **Kauf** zu 94,1 %, werden nur nicht weitergereicht (die Prüfung behauptete fälschlich „wird nirgends geschrieben“, am 29.08. richtiggestellt). **Kein Freigabe-Blocker:** die zehn Freigabefelder sind zu 100 % vollständig. `python vollstaendigkeit.py`.

- [x] **Einstiegs-Strategie und -Score künftig an der Position festhalten** (88) — *erledigt 29.08.2026 abends.* `positionsverlauf.py` holt beides jetzt aus dem **Handelsbuch**: neue Funktion `einstieg_aus_journal()` sucht den letzten Kauf derselben Münze, höchstens **30 Minuten** vor der Eröffnung. Gegen echte Daten geprüft: **12 von 12** der jüngsten Positionen gefunden, die in der Datenbank alle leer waren. **Stärkster Beleg:** Svens Log meldet zum ETH-Kauf um 21:24:55 *„Score 8/10 … V4-FIBONACCI_SUPPORT STARK“* — die Funktion liefert genau das. Neun Selbsttests bestanden. **Freeze-verträglich** (eigener Prozess, kein Handelspfad); die Whitelist in `state_manager.py` blieb unberührt. **Wirkt ab dem nächsten Öffnen einer Position, nicht rückwirkend.**
- [ ] **KI-Prognose im MANUELL-Reiter: nach dem Freeze entfernen** — *Svens Entscheidung vom 29.08.: „das war damals eine Art Zukunftsprognose, kann man nach dem Freeze löschen.“* **Ursache am 29.08. gefunden — Befund 89: die Funktion ist NIE gelaufen** (`ui/main_window.py:1362` teilt 19 Werte durch 20). Der Fehler `Chart-Fehler: operands could not be broadcast together with shapes` kommt aus diesem Reiter. **Was die Funktion tut** (`ui/main_window.py:1345 _draw_ki_prognose`): sie schreibt 30 Kerzen in die Zukunft fort — aus Trend, RSI und Schwankungsbreite, **plus einer Zufallskomponente mit festem Startwert** (`np.random.seed(42)`). **Das ist keine Prognose mit belegtem Wert**, sondern eine fortgeschriebene Linie; der feste Startwert sorgt nur dafür, dass sie bei jedem Aufruf gleich aussieht. **Nie gemessen.** Entfernen ist reine Anzeige, kein Handelspfad — aber ein Neustart nötig, deshalb nach dem Stichtag.

- [ ] **Zwei Chart-Reiter zeichnen jetzt beide Fibonacci** — *aufgefallen 29.08. an Svens Bild.* Der **MANUELL**-Reiter hat Fibonacci und Bollinger längst als Ankreuzfelder (`ui/main_window.py:1151`, `:1285`), der **ANALYSE**-Reiter hat beides seit dem 27./29.08. dazubekommen. Zwei Rechenwege für dieselbe Sache laufen frueher oder spaeter auseinander. **Zu klären nach dem Stichtag:** rechnen beide dasselbe? Und soll einer der beiden Reiter die Fibonacci-Anzeige abgeben? **Konfidenz: OFFEN** — nur die Ankreuzfelder gesehen, die Rechnung im MANUELL-Reiter nicht nachgeprüft.

- [ ] **Marks Indikatoren nachmessen** — *Eingang 27.08.2026: seine Werkzeugliste liegt vor, damit sind es benannte und pruefbare Verfahren statt geratener Linien.* **Fuenf von acht haben wir schon** (MACD 12/26/9, RSI, Stochastic RSI, Bollinger, Volumen), den 2-Jahres-Multiplikator sinngemaess in `agents/cycle_theory.py`. **Zwei fehlen: PVSRA** (Trademania, BitbullTrading — der, den er im Bild ausgewaehlt hatte) und **Advanced Order Blocks with Volume**. Zu messen, jeweils gegen die Trivial-Latte: (a) bringt PVSRA einen Vorteil, wenn man ihn nachbaut? (b) taugt der 2-Jahres-Multiplikator, den wir schon haben, aber nie gemessen haben? (c) **der interessanteste Punkt: MACD 12/26/9 auf WOCHENkerzen** — Mark und unser Bot benutzen denselben Indikator mit denselben Einstellungen, nur auf Zeitrahmen, die sich um den Faktor 168 unterscheiden. Alles reines Messen, freeze-vertraeglich. `prognosen/MARK.md`.

- [ ] **Eine Frage an Mark: von welchem Hoch zu welchem Tief?** Seine Beschriftung „0,618 2er und 707er" steht bei 48.199 / 44.225 / 39.014. Der Rueckrechnungsversuch vom 27.08. fand eine Kombination, die das Zyklushoch vom April 2021 auf **0,3 %** trifft (65.038 gegen echte 64.854) — aber das zugehoerige Tief liegt 5 % daneben, und keine der fuenfzehn geprueften Annahmen benutzt die Verhaeltnisse, die dranstehen. **Zwei Zahlen von ihm entscheiden die Sache in einer Minute** statt in fuenfzehn Hypothesen. Warum das zaehlt: Befund 83 — bei genug Parameterfreiheit passt immer etwas.

- [ ] **Tilos Zonen fortlaufend messen** — *Eingang 27.08.2026.* Er arbeitet mit **Geometrie** (Keile, Trendlinien durch Wendepunkte), nicht mit Fibonacci, und setzt **Zeit-und-Kurs-Fenster** („FREITAG AB 19 UHR"). Erste Messung: seine Spanne 76.067–78.678 fing **44,9 %** der Stunden ein, eine zufaellig gesetzte Spanne gleicher Breite nur **20,3 %** — aber 14,6 % der Zufallsspannen waren genauso gut. **Auffaellig, nicht gesichert.** Bei einer einzigen Beobachtung geht nicht mehr. Zu tun: ein kleines Werkzeug, das jede neue Zone von ihm automatisch gegen die Trivial-Latte prueft, damit sich die Trefferquote von selbst ansammelt. **Wichtigste offene Angabe: wann wurde die Zone gezeichnet — vor oder nach dem Zeitraum?** `prognosen/TILO.md`.

- [ ] **VERABREDET FUER DEN 28.08.2026: einen kompletten Handelstag durchgehen.** *Sven am 27.08.: „morgen gehen wir die komplette Chartanalyse von einem Tag durch, ich gebe dir alles was du brauchst von den letzten drei Tagen."* **Ziel:** Marks Verfahren ist seit dem 27.08. entschluesselt (Fibonacci vom letzten Swing-Tief zum folgenden Swing-Hoch, neun Stufen inkl. 0,707 und 0,866 — `prognosen/MARK.md`). Jetzt geht es darum, es an einem **vollstaendigen Tag** gegen den echten Kursverlauf zu rechnen: Wo lagen seine Stufen, wo hat der Kurs gedreht, und haetten seine Limit-Zonen ausgeloest? **Was Sven mitbringt:** die Bilder der letzten drei Tage. **Was ich vorbereite:** die 30-Minuten- und Stundenkerzen desselben Zeitraums, sodass jede Linie sofort gegen echte Kerzen gehalten werden kann. **Pflicht wie immer:** Trivial-Latte daneben — eine Zone, die getroffen wird, sagt erst etwas, wenn eine zufaellig gesetzte Zone es nicht genauso tut.

## B — Gefunden, aber ohne Bot-Neustart nicht zu beheben

Diese vier ändern kein Handelsverhalten, brauchen aber einen Neustart.
Damit fallen sie hinter den 27.08. — oder brauchen eine ausdrückliche
Freigabe.

- [x] **Ticket-Kanal wieder in Betrieb** (36) — war ein hängender Task, durch Svens Neustart geheilt. Die Ursache bleibt unbekannt; dagegen hilft jetzt die Scheduler-Meldung (37).
- [x] **Scheduler meldet Fehler jetzt** (37) — behoben 18.08., erster Fehler je Task plus jeder zehnte. Mit einem absichtlich scheiternden Task belegt. Handbuch 4.56.
- [x] **Telegram-Doppelmeldung behoben** (38) — alter Absender entfernt, der Grund steht jetzt in der verbleibenden Nachricht. Wirksam ab dem nächsten Bot-Start. Handbuch 4.56.
- [x] **DCA-Pfad protokolliert jetzt** (40) — `_dca_telemetrie()` gebaut, vier Aufrufstellen im DCA-Block (Runde übersprungen, Positionsplätze voll, Wiedereinstiegs-Sperre, Zusage). Kein Verhalten geändert, Gegentest in vier Richtungen bestanden. **Wartet auf den nächsten Neustart.** Wirkt erst wenn F&G unter 30 fällt (heute 46). Handbuch 4.79.
- [x] **`/api/status` geklärt — es funktioniert.** Gemessen am 19.08.: **HTTP 200 in 0,49 s**. Der Punkt stammte vom 18.08., behoben wurde er schon am 13.08. (Befund 33, Umbau von `get_system_status`). Der Eintrag war veraltet.
- [x] **Zweiter Wächter bekommt Futter** (56) — Punkt 8 im Heartbeat-Pulse füttert `auto_restart`, aber nur mit dem was `health` als `ok` führt. **Wartet auf den nächsten Neustart.** Handbuch 4.79.
- [x] **Metall-Reiter lesbar und ehrlich** (57) — die Karte zeigte die Tagesempfehlung wie eine laufende Position, und 135 px Inhalt fielen unten aus dem Fenster (1035 px Inhalt in 900 px Fenster, ohne Rollleiste). Jetzt: Rollrahmen, „AUFZEICHNUNG LAEUFT" mit echtem Einstieg, groessere Schrift bei den Gruenden. Reine Anzeige, kein Datenfehler gefunden. **Wartet auf den naechsten Neustart.** Handbuch 4.81.
- [x] **Analyse-Chart lesbar gemacht** — die Skala richtete sich nach den Zonen statt nach dem Kurs, neun gefuellte Baender ueberdeckten die Kurslinie, und rechts standen acht Preismarken uebereinander. Jetzt: echte Kerzen, Preis- und Zeitachse, entzerrte Beschriftung, starke Zonen kraeftig / schwache blass, 420 statt 270 px. Gegentest in beide Richtungen bestanden. **Wartet auf den naechsten Neustart.** Handbuch 4.85.
- [x] **Fibonacci-Linien zeichnen sich selbst** (85) — *Svens Auftrag vom 27.08.: „fang an mit linien zeichnen!“* `fibonacci_ziele()` war **toter Code** — vorhanden, vollständig, von niemandem aufgerufen. Jetzt rechnet sie bei jedem Bildaufbau mit, und der Chart zieht dreizehn Stufen in Violett: zwei Anker kräftig, sieben Rückzüge gestrichelt, vier Verlängerungen gepunktet; beschriftet werden nur fünf. **Zwei Ankerfehler unterwegs gefunden und behoben** (jüngste statt äußerste Wendepunkte → 0,85 % Spanne; Suche über 300 Kerzen bei 150 im Bild → 2 von 13 Linien sichtbar). Nachweis: 3 Münzen × 5 Zeitrahmen wirklich gezeichnet und vermessen, alle 15 sauber, überall 9–10 Linien im Bild. Neues Werkzeug `chart_zeichentest.py`, Selbst- und Gegentest bestanden. **Wartet auf den nächsten Neustart.** Handbuch 6.9.
## C — Nach dem 29.08., in dieser Reihenfolge

Alles hier ändert **Verhalten** und braucht eine Epochengrenze.

- [ ] **0. Breakeven-Puffer** (`risk/exit_rules.py:107`) und die zwei Kostenkonstanten. Gegenprobe liegt vor, sie fällt durch. Handbuch 4.48.
- [ ] **0a. Kaufgebühr doppelt gebucht** — **Ergänzung 19.08.:** Die Ursache in `execution/engine.py:401` steht bereits in Handbuch 4.50. Neu ist nur: die Doppelbuchung gilt **nur im Papiermodus** — im Livebetrieb liefert ccxt `cost` ohne Gebühr, dort wäre die Addition richtig. Wer also nur `app.py:1861/2933` ändert, macht den Live-Pfad kaputt. Sicherer Ort: `engine.py:401` → `amount - fee`. 220 auswertbare Verkäufe: gebucht −2,99 $, richtig mindestens +16,72 $. Handbuch 4.50 und 4.60, `GEFUNDENE-PROBLEME.md` 42, Werkzeug `gebuehren_gegenprobe.py`.
- [ ] **1. Warte-Aufträge im Schattenlauf** — größter gemessener Hebel: +0,23 Prozentpunkte je Runde, Vorzeichen dreht von −0,065 % auf +0,17 %. **Offener Einwand: Gegenauslese ist nicht gemessen.**
- [ ] **2. Ausstiegsschwellen** — **Reihenfolge steht jetzt fest** (Handbuch 4.75): erst (a) `TRAIL_AB_PCT` über die Kostenlinie heben (1,52 % statt 1,20 %, Einzeiler), dann (b) den RSI-Ausstieg ausbauen (+0,948 % gegen +0,357 % beim Trailing, aber nur 14 % der Fälle — **der naheliegendste Hebel**), dann (c) Trail an ATR normieren. **Nicht** Chandelier übernehmen: gegengerechnet an 43 Trades senkt er den Erwartungswert von +0,852 auf +0,592 %.
 Die Ratsche greift bei 0,8 %, die Rentabilitätsschwelle liegt bei ~0,84 % — sie realisiert systematisch zu früh.
- [ ] **3. `schwelle_vergleich.py`** — **erneut gelaufen 26.08., teilweise beantwortet.** Ueber 19,5 Tage und 37.888 Pruefungen: bei **4 h (117 unabhaengige Fenster) und 12 h (39)** lautet das Urteil **"Blocken war richtig"** — die geblockten Kaeufe haetten -0,341 % bzw. -0,248 % gebracht. Bei **24 h** fehlen noch **vier** unabhaengige Fenster (20 von 24 noetig), also rund vier Tage; bei 48 h sind es 10. Bis zum Stichtag erreichbar. Handbuch Teil 2, Abschnitt 2.4.
- [ ] **4. Muenzfrage** — **nachgerechnet 26.08.: mit dem heutigen Aufbau bis zum Stichtag NICHT beantwortbar, und zwar um den Faktor neun.** Aus 1.228 Signalen sind bisher nur **32 Positionen** geworden, ein bis zwei je Muenze. Grund ist die Bauart: je Muenze ist immer nur EINE Schattenposition offen, und sie laeuft bis `MAX_TAGE = 7`. Fuer 30 Faelle je Muenze braeuchte es **210 Tage**. Tatsaechlich 0,15 Positionen je Muenze und Tag; bis zum 18.09. kommen rund 3,4 je Muenze zusammen. **Was trotzdem belastbar ist:** die Kostenmessung je Muenze aus allen 1.228 Signalen (Handbuch Teil 4, Abschnitt 4.3). Wer die Ertragsfrage schneller will, muss die Bauart aendern — mehrere Positionen je Muenze oder `MAX_TAGE` senken. Beides Verhaltensaenderung am Sammler. Handbuch Teil 6, Abschnitt 6.2.
- [ ] **5. `features/regime_adaptiv.py` auf `AKTIV = True`** — **erst nach** Korrektur von `KOSTEN_PCT` in Zeile 76 (0,32 → 0,505). Der Fehler ist einseitig: er kann nie zu falschem Verschärfen führen, wohl aber zu falschem Lockern. Handbuch 4.53.
- [ ] **6. Die acht falschen Kostenkonstanten geradeziehen** (Liste in Handbuch 4.53) — zusammen mit einer Epochengrenze, sonst sind die bisherigen Schattenwerte nicht mehr vergleichbar.

- [ ] **7. `volume_ratio` und `high_low_range` geradeziehen** — betrifft **zwei** Baustellen: die Punktregel `models/signal_model.py:53` (feuert nie) **und** den Trainings-Bruch beim KI-Modell (zwei Merkmale außerhalb des gelernten Bereichs). Nach der Korrektur muß das Modell **neu trainiert** werden, sonst passen alte Gewichte auf neue Werte.

- [ ] **8. Regime-Filter auch im DCA-Pfad** (40) — er greift dort nicht. Im Signal-Pfad hat er rund 68.000 Käufe abgelehnt. Ob das auf dem Hauptweg gut oder schlecht wäre, ist **ungemessen** — erst messen, dann entscheiden.

- [ ] **8a. V4-Kalibrator auf eine lebende Quelle stellen** (76) — `app.py:352` lädt `v4_data/strategy_stats.json`, **Stand 6. Mai 2026**. Der V4-Referenzbot schreibt seit Monaten frische Zahlen nach `v4_referenz/strategy_stats.json` (zuletzt 24.08.), der Kalibrator sieht sie nie. Das zählt, weil das V4-Ensemble mit **bis zu +4 Punkten** der größte Einzelposten der Kaufwertung ist (`agents/signal_agent.py:153`) und der Kalibrator bestimmt, wie stark jede Strategie darin wiegt — bis hin zur vollständigen Sperre bei Gewicht 0,0. **Vormessung erledigt 26.08.** — Formel exakt nachgebaut, mit heutigen Zahlen gefuettert. **Fuenf von acht Strategien wuerden gesperrt:** DCA_FEAR_GREED, TSI_SIGNAL, ICHIMOKU_CLOUD, MACD_CROSS und EMA_TREND — letzteres ist heute das haeufigste Etikett ueberhaupt (192.414 Entscheidungen, 36 der 48 Kaeufe der laufenden Epoche). Uebrig blieben nur FIBONACCI_SUPPORT (0,88) und MOMENTUM_BREAKOUT (0,50), dazu knapp RSI_OVERSOLD (0,40). **Das ist keine Feinjustierung, sondern ein Umbau des Kaufverhaltens.** **Wichtig:** Alle sechs Sperren sind statistisch abgesichert, **keine der drei Freigaben** — deren Summen sind kleiner als ihre eigene Schwankungsbreite. **Und Befund 78:** Die Sperrregel ist ein harter Schalter genau auf der Nulllinie (`v4_calibrator.py:86`, `total_pnl <= 0`), ohne Puffer und ohne Mindestfallzahl. RSI_OVERSOLD stand am 25.08. bei -57,86 $ (gesperrt) und am 26.08. bei +2,55 $ (freigegeben), bei einer Schwankung von ±100 $. **Nur zusammen mit einer entschaerften Regel ausfuehren:** Sperre erst ab einem Verlust groesser als die eigene Schwankungsbreite und erst ab 30 Faellen. Handbuch Teil 5, Abschnitt 5.11.

- [ ] **8b. Die zwei Strategielisten zusammenführen** — `agents/strategy_brain.py:41` kennt `ICHIMOKU` und `TSI`, `agents/v4_strategies.py:27` dieselben Strategien als `ICHIMOKU_CLOUD` und `TSI_SIGNAL`. Ein Handel unter dem einen Namen kann den Zähler des anderen nie erhöhen. Deshalb steht ICHIMOKU mit 69 Trades im Gehirn und **0** im sauberen V6-Zähler. **Vormessung erledigt 26.08.: heute wirkungslos, zurueckstellen.** Diese Strategien feuern in V6 **ueberhaupt nicht** — ICHIMOKU_CLOUD, TSI_SIGNAL, STOCHRSI_REVERSAL und MOMENTUM_BREAKOUT stehen an **null** Handeln und **null** Entscheidungen. Ein Zusammenfuehren wuerde heute nichts aendern; es wird erst gebraucht, wenn sie tatsaechlich handeln, also fruehestens nach 8a. **Was sich stattdessen lohnt:** die Rueckfallebene `v4_strategy_used or self.current_strategy` (`agents/signal_agent.py:182`) hat seit dem 23.08. **3.606 Kaufentscheidungen** mit dem Etikett `GRID_BOT` versehen — dem Namen eines abgeschalteten Bausteins. Wer die Auswertung liest, haelt den Gitter-Handel fuer aktiv. Handbuch Teil 5, Abschnitte 5.2 und 5.11.

- [ ] **9. `entry_score` auf dem DCA-Pfad** (41) — `app.py:2971` greift auf `_dca_intent` zu, eine Variable, die es nirgends gibt (`grep`: 0 Treffer). Deshalb sind 0 von 220 Verkäufen mit Score versehen. Einzeiler. *Der Score in `telemetrie.db/evaluations` ist davon nicht betroffen — TODO-Punkt 3 bleibt auswertbar.*


- [ ] **10. Zwei Cash-Puffer, 2 % und 5 %** (43) — beide in `_execute_approved_trade`, beide mit derselben Begründung. Der zweite gewinnt immer. LOW, aber ein Fallstrick für die nächste Änderung.

- [ ] **11. `total_equity` in zwei Spalten trennen** (44) — die Spalte enthaelt zwei Kapitalbegriffe, die sich um 96 $ bei 590 $ (16 %) unterscheiden: `app.py:952` **ohne** Sparplan-BTC, `portfolio/manager.py:70` **mit**. Beide fuer sich richtig, aber in derselben Spalte. Geht in Positionsgroesse **und** Risikopruefung. Vorschlag: `equity_handel` und `equity_gesamt` getrennt. Handbuch 4.63.

- [ ] **12. Trailing-Schwelle gegen die Kostenschwelle** (45) — `TRAIL_AB_PCT` = 1,2 %, Nulllinie bei 1,52 %. Jeder Ausstieg aus einem Höchststand dazwischen verliert rechnerisch. **Nicht einfach hochsetzen** — wer später ratscht, gibt bei jedem Trade zwischen 1,2 und 1,6 % den ganzen Gewinn zurück. Erst die Positionsverläufe auswerten. Handbuch 4.64.

- [ ] **13. Take-Profit klären** (46) — `take_profit_pct = 0.0`, der Mechanismus ist tot. Vermutlich Absicht, steht aber nirgends. Ein abgeschalteter Mechanismus ohne Begründung ist von einem vergessenen nicht zu unterscheiden.

- [ ] **14. Exposure-Grenze folgt Moduswechsel nur nach oben** (48) — `risk/engine.py:323` nutzt `max()`, Reset nur im Konstruktor. Von `btc_only` (95 %) zurück auf `balanced` (35 %) kommt die Verschärfung nicht an. Wirkung durch drei weitere Deckel begrenzt.

- [ ] **15. Ereignisbus zählt ohne Sperre** (52) — `core/bus.py`: `_stats` und `_event_log` werden aus 26 Scheduler-Threads ungeschützt beschrieben, betrifft auch den Fehlerzähler. Einzeiler: zwei Zeilen in den Lock ziehen, der drei Zeilen später steht.

- [ ] **16. Laufzeit je Scheduler-Aufgabe messen** (53) — eine Aufgabe mit 12 s Takt, die 60 s braucht, läuft faktisch alle 60 s. Niemand erfährt es. LOW.

- [ ] **17. Verlustzähler übersteht keinen Neustart** (54) — `coin_consecutive_losses` steht nicht in `bot_state.json`, die Cooldown-Sperre greift deshalb nie (0× in 12 Tagen trotz Serien von 4/3/3). Der Kill-Switch speichert seinen Tagesverlust, dieser Zähler nicht. Zusätzlich misst er den **gebuchten** Dollar-Wert statt des Netto-Ergebnisses. Handbuch 4.74.

- [ ] **18. Kapital wird beim Verkauf doppelt gezählt** (55) — zwischen Gutschrift des Erlöses und Entfernen der Position steht beides in der Bilanz. 2 Messungen von 203.432, aber sie ließen den größten Rückschlag von 13,11 auf 23,20 % springen. Kennzeichen: `offene_positionen IS NULL`. Auswertungsseitig bereits gefiltert; der Schreibpfad gehört korrigiert. Handbuch 4.78.

- [ ] **19. Das Gehirn lernt brutto statt netto** (58) — `strategy_brain.py:332` zaehlt `pnl > 0` als Gewinn: **76,8 %** Trefferquote statt der wahren **44,6 %** nach Kosten, 32,2 Punkte zu gut. Die Zahl wirkt: `select_best()` vergibt dafuer bis zu **+2,0 Punkte** (`strategy_brain.py:168-177`). Zusaetzlich stehen Ausstiegsgruende als „Strategien" in derselben Tabelle (`exit_monitor.py:336-362` → `:581`), 119 von 224 Verkaeufen. Reihenfolge: erst gegen K-BASIS messen, dann Ausstiegsgruende trennen. Handbuch 4.82.
- [ ] **20. Das Allzeithoch ist verdrahtet und 15,7 % zu niedrig** (63) — `agents/cycle_theory.py:28` steht auf 109.114 $ (20.01.2025). Gegen drei Quellen geprueft liegt das echte Hoch bei **126.200 $** (06.10.2025). Der Bot misst dadurch **-34,1 statt -43,0 %** Abstand, steht auf EARLY_BEAR statt MID_BEAR und kauft **20 % groessere Positionen** (Multiplikator 0.6 statt 0.5). Patch liegt geprueft bereit: `patches_nach_27_08/patch_63_ath_dynamisch.py`. Handbuch 4.94.
- [ ] **21. Der Breakeven-Puffer deckt die Kosten nicht** (Ergaenzung zu Punkt 0) — `risk/exit_rules.py:107` steht auf 0,35 %, hergeleitet aus der **alten** Gebuehrenannahme. Bei K-BASIS 0,505 % bedeutet das **-0,155 % netto**: die Sperre sichert nicht die Null, sondern einen kleinen Verlust. Die im Code selbst verlangte Gegenprobe ist faellig und faellt durch (vier Faelle nach dem Fix: -0,594 $ im Schnitt, schlechter als die sechs davor). Neuer Wert 0,55 %, aus K_BASIS_PCT gerechnet statt gesetzt. Patch bereit: `patches_nach_27_08/patch_00a_breakeven_puffer.py`. Handbuch 4.34 + 4.97.
- [ ] **22. Ausstiegsregeln gegeneinander rechnen** — **gelaufen 26.08., Ergebnis nicht verwertbar (Befund 79).** `ausstieg_vergleich.py` meldet, dass alle acht Regeln gegen die Trivial-Latte "Halten" verlieren (+6,063 % gegen +2,001 % beim Bot). **Diese Zeile traegt kein Urteil:** Die Latte rechnet ueber zwei Bestaende mit voellig verschiedener Aufzeichnungsdauer — echte Positionen **4,6 h** im Median, Schattenpositionen **99,4 h**. Faktor 21. Bei echten Verlaeufen endet die Aufzeichnung beim Verkauf, "Halten" heisst dort also "halten bis der Bot ohnehin verkauft". Verglichen wurde vier Stunden gegen vier Tage, in einem steigenden Markt. **Zu tun, beides freeze-vertraeglich:** entweder getrennte Tabellen fuer echt und Schatten, oder alle Verlaeufe auf dieselbe Zeitspanne stutzen. Handbuch Teil 8, Abschnitt 8.9, Fall 5.

## D — Beobachten, nichts tun

- [x] **Sammler-Laufzeit gegengeprueft — erledigt 26.08.2026.** `sammler_taeglich` braucht im Schnitt **22,7 s**, im laengsten Fall 39,9 s (21 Laeufe). **Die 14 Minuten waren fremde Last, wie vermutet.** Dabei fiel **Befund 80** auf: die Spalte `laufzeit_sek` stand bei 42 von 43 Zahlenbuch-Laeufen und 1.722 von 2.036 Capture-Laeufen auf genau 0,0 — `job_start()` und `job_ende()` wurden direkt hintereinander gerufen, beide NACH getaner Arbeit. **Behoben**, gegengeprueft: Protokoll meldet 78 s, Tabelle traegt jetzt 77,7 s.
- [ ] **Autostart des Schatten-Sammlers mit Adminrechten.** Die Aufgabe mit Auslöser „beim Hochfahren“ scheitert an „Zugriff verweigert“. Ersatz läuft: `SchattenUniversumWacht` alle 15 Minuten. Nur Kosmetik — die Lücke beträgt höchstens eine Viertelstunde.
- [x] 🔴 **`state_recovery.py` repariert** (51) — am 19.08. behoben. Einheitlicher Schlüssel, Felder erhalten, nicht löschen sondern melden. Gegentest in sechs Richtungen bestanden. Freeze-sicher, weil der Pfad im Papiermodus tot ist. Handbuch 4.76.
- [ ] **`recovery_blockade` auswerten** — **nachgesehen 26.08.: sie wurde bis heute NIE gesetzt.** In `bot_state.json` gibt es keinen solchen Schluessel, und im ganzen Projekt gibt es genau **zwei** Fundstellen: `live/state_recovery.py:206` setzt sie, `:216` loescht sie wieder. **Niemand liest sie.** Es gibt also nichts auszuwerten — entweder trat der Fall nie ein, oder die Sperre greift nicht. Vor einer Pruefung im Handelspfad (Verhaltensaenderung) muesste erst belegt werden, dass sie ueberhaupt jemals ausloest.
- [ ] **Patches einspielen** — **alle vier am 26.08. gegen den heutigen Code geprueft, alle passen und melden BEREIT.** 00a (Breakeven-Puffer 0,35 -> **0,55 %**; nachgerechnet: 0,35 ergibt netto -0,155 %, garantierter Verlust, 0,55 ergibt +0,045 %), 45 (Trailing-Schwelle 1,2 -> **1,52 %**, nicht 1,57 wie hier bisher stand - der Patch rechnet den Wert aus K-BASIS statt ihn zu verdrahten), 54 (Verlustzaehler sichern, Selbsttest bestanden), 63 (Allzeithoch: im Code 109.114 $ vom 20.01.2025, tatsaechlich **126.200 $** vom 06.10.2025 - **15,7 % zu niedrig**). 00a und 45 fassen beide die Ausstiegs-Leiter an und gehoeren zusammen gemessen. Alle vier brauchen EINE Epochengrenze, nicht vier. **Achtung:** der Puffer von 0,55 % liegt nur 0,045 Prozentpunkte ueber K-BASIS - sehr knapp. Anleitung: `patches_nach_27_08/00_LIES_MICH.md` (Stichtag dort am 26.08. von 27.08. auf 18.09. berichtigt).
- [ ] **Vor dem Live-Gang: Order-Pfad am Testnetz erproben** (49) — `RetryPolicy`, `CircuitBreaker` und `FillReconciler` laufen im Papiermodus nie. Der Pfad, der bei echtem Geld die Sicherheit trägt, ist nie unter echten Bedingungen gelaufen. Rate-Limit, Zeitüberschreitung und Verbindungsabbruch absichtlich provozieren. Handbuch 4.71.
- [ ] **`retry_policy.py`: Abbruchprüfung im Rate-Limit-Zweig** (50) — Einzeiler. Wirkt nur live, aber dort kostet er bis zu 30 Sekunden bei blockiertem Thread.
- [ ] **Die Zyklusphasen heißen irreführend.** `EARLY_BEAR` bedeutet **flach** (-20 bis -35 % vom Hoch), nicht *früh*; ein `LATE_BEAR` gibt es gar nicht. Sven ist am 20.08. genau darüber gestolpert und wird nicht der Letzte sein. Die Namen stecken in Telemetrie, Lernsystem und Situationsgedächtnis - umbenennen wäre teuer. **Vorschlag: nur die ANZEIGE beschriften**, etwa `EARLY_BEAR · 20-35 % unter dem Hoch`, Code unverändert. Handbuch 4.94.
- [ ] **Tote Payload-Dateien.** Sieben `_*_payload.py` im Hauptordner sind Duplikate gepflegter Module; alle Verweise darauf stehen nur in `inventar_daten.json`, keiner ist ein Import. Eine eigene Sitzung hat sie am 20.08. in einem **getrennten Arbeitsordner** nach `archiv/` verschoben - das Ergebnis ist **noch nicht im Hauptordner**. Entweder übernehmen oder verwerfen, aber nicht liegen lassen: `_chart_refresher_payload.py` trug noch die alte Münzzahl, während die echte Datei längst korrigiert war.
- [ ] **Mini-PC-Umzug.** Vorher ein Ablaufplan, damit nichts mit altem Programmtext hochkommt. `python prozess_frische.py` gehört als letzter Schritt dazu.
- [ ] **Messfenster-Ausbeute.** Nachgerechnet am 20.08.: E7 liegt bei **11 Verkäufen** und 2,13/Tag. Bis zum ursprünglichen 27.08. wären es 25 gewesen — nötig sind 30. **Deshalb bis zum 29.08. verlängert** (Entscheidung Sven, Handbuch 4.97). Lehre für die nächste Epoche: bei dieser Handelsrate **vier Wochen**, nicht zwei.

---

## Erledigt am 18.08.2026

- [x] Beide Sammler auf 18 Münzen neu gestartet — belegt durch `18/18 Münzen` und `CAPTURE START | 18 Coins`
- [x] Vier doppelte Signale aus der Schatten-Datenbank entfernt (drei von meinem Diagnoselauf, eines vom 14.08.)
- [x] `prozess_frische.py` gebaut, Gegentest in beide Richtungen bestanden
- [x] Läuft selbständig: stündlich per Aufgabe `ProzessFrische`, nach jedem Commit per Haken
- [x] Kaufgebühren-Doppelbuchung gefunden und gemessen (`gebuehren_gegenprobe.py`)
- [x] Sammler-Laufzeit geklärt — kein Defekt
- [x] Ticket-Kanal und Scheduler als Punkt 36/37 dokumentiert
- [x] Telegram-Doppelmeldung als Punkt 38 dokumentiert (von Sven gefunden)
- [x] Merkmals-Schnappschüsse ausgewertet (Handbuch 4.52) — die Frage, die Sven zweimal stellen musste
- [x] Suchauftrag alte Kostenannahmen (Handbuch 4.53) — neun Stellen gefunden, die Entscheidung vom 15.08. gegengeprüft und bestätigt
- [x] Liste gegen das Verzeichnis geprüft statt aus der Übergabe abgeschrieben — zwei Punkte waren längst erledigt (Sven fiel es auf)
- [x] Zahlenbuch-Frage geklaert — Sven: kein Bedarf
- [x] `volume_ratio` geklärt — zwei Indikatoren messen die Uhrzeit statt den Markt (Punkt 39)
- [x] Trainings-Bruch beim KI-Modell nachgewiesen — Folge aus Punkt 39
- [x] Punkt 37 und 38 behoben, solange der Bot für das Windows-Update aus war — kein Handelspfad berührt
- [x] `schatten_starter.py` plus Aufgabe `SchattenUniversumWacht` (alle 15 Min) — der Sammler kommt nach Neustart und Absturz von selbst wieder

## Fibonacci-Sichtbarkeitsfilter im Manuell-Reiter (aus Befund 91)

`ui/main_window.py` — der Filter unter den Fibonacci-Stufen lautet
`if swing_low * 0.95 <= price <= swing_high * 1.1`. Er nimmt an, dass die
Verlängerungen (1,272 · 1,618 · 2,0) **über** dem Hoch liegen. Bei
Aufwärtsbewegung liegen sie unter dem Tief und fallen aus dem Fenster —
sie werden dann gar nicht gezeichnet.

Anders als der Richtungsfehler selbst (behoben) benennt das keine Linie
falsch, es lässt welche weg. Deshalb nachrangig.

Offen ist die Vorfrage, nicht die Reparatur: **Wofür war der Filter da?**
Vermutlich, damit weit entfernte Verlängerungen die Preisachse nicht
auseinanderziehen. Wenn das stimmt, ist die Abhilfe nicht, ihn zu
erweitern, sondern die Achsengrenzen getrennt zu setzen. Erst messen,
was ohne Filter passiert. **VERMUTUNG**, ungeprüft.

Nach dem Messfenster. Kein Kapital-, kein Datenverlustrisiko.

---

## Umzug auf den neuen Rechner — was noch aussteht (02.09.2026)

Der Bot läuft, das Cockpit ist offen, alle Sammler schreiben (nachgewiesen
über Zeilenzahl-Differenzen, nicht über die Prozessliste). Offen ist nur
noch das Folgende.

### U1 — ~~Die drei Haken~~ ✅ ERLEDIGT 02.09.

**Beide Fragen sind beantwortet, der Messaufbau ist abgebaut.**

**Die Haken greifen (SICHER).** Beleg: Einer Nachricht am 02.09. wurden die
Dauerregeln aus `.claude/hooks/DAUERREGELN.txt` beigelegt
(`UserPromptSubmit`), und `CLAUDE.md` war geladen. Vorher — solange Claude
Code aus dem falschen Ordner lief — geschah beides nicht. Die gesamte
Einrichtung vom 01./02.09. lief also ohne Projektregeln und ohne
Schreibschutz.

**`$CLAUDE_PROJECT_DIR` wird in Hook-Argumenten NICHT aufgelöst (SICHER).**
Gemessen am 02.09. um 20:35 mit zwei Proben nebeneinander: die Gegenprobe
mit ausgeschriebenem Pfad schrieb ihre Datei, die Probe über die Variable
nicht. Der Haken **hat** also gefeuert — nur der Pfad mit der Variablen
zeigte ins Leere. Eine dritte Ursache wurde ausgeschlossen: das Probenskript
von Hand gestartet schreibt seine Datei anstandslos.

*Der feine Unterschied:* Als **Umgebungsvariable** ist `CLAUDE_PROJECT_DIR`
im Hakenprozess korrekt gesetzt — nur die Ersetzung im `args`-Feld findet
nicht statt. Wer sie im Text einer Hakendatei über
`os.environ["CLAUDE_PROJECT_DIR"]` liest, bekommt den richtigen Ordner; nur
der Pfad **zur Datei hin** muss ausgeschrieben bleiben.

**Folge:** Die festen Pfade in `.claude/settings.json` bleiben Pflicht. Wer
den Projektordner umbenennt, muss die drei Haken **und** die zwei geplanten
Aufgaben von Hand nachziehen. Steht in `BOT-HANDBUCH.md` 10.10.

**Abgebaut:** beide Proben aus `settings.json` entfernt (die drei echten
Haken geprüft — alle zeigen auf existierende Dateien), `_umzugsprobe.py`,
`_probe_fest.py` und die Ergebnisdateien gelöscht. Voriger Stand gesichert
in `.claude/settings.json.bak_vor_probenausbau_20260902`.
`PROBE_AUSWERTEN.bat` ist damit gegenstandslos — sie meldet ohne die
Ergebnisdateien „Haken feuerte nicht", was jetzt falsch wäre.

> Zwei Ursachen, ein Bild — das ist kein Ergebnis, sondern ein Messaufbau,
> der die Frage nicht trennt. Die Gegenprobe hat sie getrennt.

### U2 — ~~`SCHLAF_ABSCHALTEN.bat` noch nicht ausgeführt~~ ✅ ERLEDIGT 02.09.

**Nachgesehen statt gefragt.** `powercfg` sagt:

| Einstellung | Netzbetrieb | Akku |
|---|---|---|
| Standby (`STANDBYIDLE`) | `0x0` = **nie** | `0x258` = 10 Min |
| Ruhezustand (`HIBERNATEIDLE`) | `0x0` = **nie** | `0x0` = nie |

Der Netzbetrieb steht bereits auf „nie" — genau das, was die Datei setzen
würde. Sie muss nicht mehr ausgeführt werden. Der Akkubetrieb blieb
unverändert, wie beabsichtigt.

**Auch der zweite Zeitgeber ist zu.** Die Datei warnt selbst, dass der
Ruhezustand (Hibernate) einen **eigenen** Zeitgeber hat, den sie nicht
anfasst. Nachgeprüft: der steht auf beiden Seiten auf „nie". Es bleibt also
keine Lücke offen, durch die der Rechner nachts doch noch wegkippt.

**Letztes Einschlafen:** 02.09. um 13:38:15 (Ereignisprotokoll,
Kernel-Power 42). Davor die drei Nachtlücken aus Befund 95. Seitdem keines
mehr. Die Datei `SCHLAF_ABSCHALTEN.bat` bleibt liegen — sie fragt vorher
nach und richtet keinen Schaden an, wenn sie versehentlich läuft.

### U3 — ~~Der Ordnername weicht von der Absprache ab~~ ✅ ERLEDIGT 02.09.

Der Ordner hieß nach dem Entpacken `windows_neu_v6` und wurde am
02.09.2026 auf `Desktop\trading_imperium_v6(21)` umbenannt — den Namen,
der überall im Projekt steht. Gegengezählt: 6289 Dateien,
1.654.313.259 Bytes vorher wie nachher, identisch.

**Was dabei nachgezogen werden musste** — und beim nächsten Mal wieder
nachgezogen werden muss, weil es die einzigen Stellen mit absoluten
Pfaden sind:

| Stelle | erledigt |
|---|---|
| `.claude/settings.json` (3 Haken) | ✅ |
| Aufgabe `TI6-Sammler` | ✅ neu angelegt |
| Aufgabe `ForschungCapture` | ✅ neu angelegt |
| `lage_erzeugen.py:233` (OneDrive-Kopie) | ✅ |
| `check_punkt_a.py:5` (nur Kommentar) | ✅ |
| `BOT-HANDBUCH.md` 10.10 | ✅ |

Alles Übrige zog von selbst mit: die `.bat` über `%~dp0`, die
Python-Dateien über `os.path.dirname(os.path.abspath(__file__))`.

### U4 — Der leere Ordner `Desktop\trading_imperium_v6(3)` — Ursache gefunden

**Stand 02.09. abends: der Ordner steht noch da, und der Grund ist bekannt.**

`LEEREN_ORDNER_LOESCHEN.bat` bricht mit **Windows-Fehler 32** ab — „von
einem anderen Prozess verwendet". Die Datei rät dann auf „Claude Code läuft
noch aus diesem Ordner heraus". Das ist **fast** richtig, aber nicht
wörtlich, und die Datei verschluckt die echte Fehlermeldung mit `2>nul`.

**Gemessen (SICHER):** Der Ordner ist wirklich leer (0 Einträge, auch
versteckte). Genau **ein** Prozess hat sein Arbeitsverzeichnis darin:

| | |
|---|---|
| Prozess | `powershell.exe`, PID 10628 |
| Arbeitsverzeichnis | `Desktop\trading_imperium_v6(3)` |
| Kindprozesse | keine |
| Elternprozess | `claude.exe` **PID 9184** — eine **zweite, ältere** Claude-Code-Instanz, gestartet 02.09. um 13:10:09 |

Nicht dieses Fenster also (das ist `claude.exe` PID 1540), sondern ein
zweites, das noch offen steht und zwei PowerShell-Fenster hält.

**Was zu tun ist:** Das **andere** Claude-Code-Fenster schließen, dann
`LEEREN_ORDNER_LOESCHEN.bat` doppelklicken. Kein Rechner-Neustart — der
würde den laufenden Papierhandel anhalten, für einen leeren Ordner.

*Warum das hier steht:* Die Fehlersuche hat dreimal fast auf die falsche
Fährte geführt — die `.bat` riet auf das falsche Fenster, eine Suche nach
Prozess-Kommandozeilen fand nur **sich selbst** (der Suchbegriff stand in
der eigenen Kommandozeile), und `2>nul` hatte die einzige Zeile verschluckt,
die die Antwort enthielt. Erst die Frage nach dem **Arbeitsverzeichnis**
statt nach dem Programmpfad hat den Halter gefunden.

### U5 — Befund 96: Telegram-Zugang im Klartext

`v4_referenz/trading_imperium_v4_25_ALARM.py:2271`. Kein Konflikt mit V6
(anderer Zugang, über Fingerabdrücke geprüft), aber er reist in jeder
Kopie mit und gehört gewechselt.

### U6 — `optuna` und `scipy` in der Paketprüfung

`pakete_pruefen.py` meldet beide als „Lücke". Beide sind keine:

* `optuna` fehlt **absichtlich** — `backtest/hyperopt.py:16-21` fängt das
  mit `try/except ImportError` ab und setzt `HAS_OPTUNA = False`.
  Nachgeprüft und bestätigt. Nicht nachinstallieren.
* `scipy` ist eine erklärte Abhängigkeit von scikit-learn
  (`scipy>=1.10.0`), kommt also mit und ist installiert (1.18.1).

Dem Werkzeug fehlt eine Liste „bewusst draußen". Kleinigkeit, aber es
meldet sonst bei jedem Lauf zwei Fehlalarme — und ein Werkzeug, das immer
etwas meldet, wird irgendwann nicht mehr gelesen.

### U7 — ~~OneDrive-Ordnersicherung~~ ✅ ERLEDIGT 03.09. (Projekt nach `C:\` umgezogen)

**Angelegt nach Befund 98.** OneDrive hat am 02.09. um 21:20 begonnen, den
laufenden Projektordner in die Cloud zu **verschieben**. Sven hat die
Synchronisierung angehalten, der Ordner wurde vollständig zurückgeholt, der
Bot lief durchgehend weiter.

**Das Anhalten ist eine Pause, keine Lösung.** Beim Fortsetzen beginnt das
Verschieben von vorn.

| zu tun | wo |
|---|---|
| **Ordnersicherung für den Desktop abschalten** | OneDrive-Symbol → Einstellungen → *Sicherung* → *Ordnersicherung verwalten* → Desktop aus |
| danach prüfen, ob der Projektordner am Desktop-Pfad vollständig bleibt | `python zeilen_zaehlen.py`, Differenz zweier Messungen |
| `.env` mit dem Telegram-Token liegt jetzt in der Cloud | Token bei BotFather neu erzeugen — ein Leck lässt sich nicht zurückholen. Betrifft auch Befund 96 (U5) |

**Warum nicht einfach so lassen:** Eine Sicherung, die das Original wegnimmt,
ist keine. Und sie greift auf eine 449-MB-Datenbank zu, die alle paar Sekunden
beschrieben wird.

### U8 — ~~Sicherung auf USB-Stick~~ ✅ ANDERS GELÖST 03.09.

`SICHERUNG_AUF_USB.bat` ist angelegt und geprüft: Sie findet Python über
`_python_finden.bat`, sucht den Stick selbst (Wechseldatenträger), prüft den
freien Platz und sagt es laut, wenn keiner steckt — das ist nachgewiesen, der
Lauf ohne Stick meldete sauber `[KEIN STICK]` und tat nichts.

**Es fehlt nur der Stick.** Rund 2,5 GB (Projekt 1,65 GB + Datenbank-Abzüge).
Einstecken, Datei doppelklicken. Sie ruft das vorhandene `sicherung.py` auf,
das saubere SQLite-Abzüge zieht, während der Bot weiterläuft, und die `.env`
bewusst auslässt.

**Der zweite Teil des Gegentests steht noch aus** — ob sie einen eingesteckten
Stick auch wirklich findet, ließ sich ohne Stick nicht prüfen.

---

## Fehlende Bausteine — gefunden 14.10.2026 beim Profitabilitäts-Bericht

*Svens Auftrag vom 14.10.: „falls doch etwas vergessen wurde, notiere dir die
fehlenden Bausteine und nimm sie auf die To-do-Liste mit auf!"* Die
Handelsliste selbst fehlt **nicht**: Sie liegt in `data_store/trades_v5.json`
(1.261 Einträge seit 22.06., seit 13.08. kein Betrag und keine Gebühr leer),
nicht in `telemetrie.db`. Der Bericht selbst: Claude-Dokument
„Profitabilitäts-Bericht v6" (https://claude.ai/code/artifact/be02d398-cc1c-437f-bb0f-f4dfd9e96b2a).

- [x] **ERLEDIGT 14.10.2026 — Nachlauf läuft wieder, die 26 verpassten Verkäufe sind nachgetragen.**
  Die Daten lagen NICHT im v7-Ordner (0 von 26 v6-Verkäufen im v7-Nachlauf).
  Ursache: Rechner-Neustart 27.09. 14:32, keine Aufgabe zum Wiederanlegen, und
  der alte `schatten_starter.py` hätte ohnehin nicht gestartet: fester
  WindowsApps-Pfad ohne Datei und keine Ordnerprüfung, er hielt also den
  v7-Sammler für den eigenen. Starter repariert (Gegentest in beide Richtungen),
  Aufgaben `SchattenUniversumWacht` und `_Anmeldung` neu angelegt. Ausstiege in
  `nachlauf.db`: 556 → 582. Endgültig verloren ist die Blockaden-Stichprobe
  der 17 Tage, außer man füllt sie mit `nachlauf_rueckwirkend.py` nach.
  BOT-HANDBUCH 6.2a. Ursprünglicher Eintrag:
  **Nachlauf für v6 steht seit 27.09.2026** — `data_store/nachlauf.db` und
  `data_store/schatten_universum.db` zuletzt beschrieben am 27.09. um 14:14
  (letzte Zeile in `schatten_universum.log`: „Nachlauf: 69438 Ereignisse").
  Die Windows-Aufgabe `SchattenUniversumWacht` (angelegt 18.08., OFFEN Zeile 181)
  **existiert nicht mehr**. Es laufen nur `SchattenUniversumLIVE` und
  `SchattenUniversumLIVE_Anmeldung`, beide mit `trading_imperium_v7\schatten_starter.py`.
  Folge: Für v6-Verkäufe und -Kaufsperren fehlt seit 17 Tagen der Kurs
  1/4/24/48 h danach. Warum die Aufgabe weg ist: **OFFEN**, keine Entscheidung
  gefunden (gesucht: `SchattenUniversumWacht`, `SchattenUniversumLIVE`). Vor dem
  Wiederanlegen klären, ob die v7-Sitzung sie absichtlich ersetzt hat, damit
  nicht zwei Sammler dieselben Münzen doppelt zählen.
- [ ] **Keine dauerhafte, saubere Kontokurve** — `data_store/equity_history.json`
  behält nur die letzten 500 Werte (am 14.10. gemessen: 4,2 Stunden). Die
  Telemetrie-Spalte `total_equity` mischt mit und ohne Sparplan-BTC (Befund 44,
  Punkt C11). Gemessen am 14.10.: 589 $ → 490 $ → 619 $ → 445 $ → 589 $ an fünf
  Stichtagen, das sind Sprünge zwischen den beiden Kapitalbegriffen, keine
  Handelsergebnisse. Ein Kontoverlauf über Wochen lässt sich nur aus den
  Kassenbuchungen der Handelsliste nachrechnen.
- [ ] **Kein Laufzeit-Protokoll mit Grund** — In 61 Tagen (13.08.–14.10.)
  summieren sich die Pausen über 3 Stunden in `telemetrie.db` auf 18,3 Tage,
  zwölf Stück. Die größte vom 08.09. 17:08 bis 20.09. 20:34 (291 h) war Svens
  Abschaltung („weil ich keinen Sinn mehr gesehen habe"), ebenso fehlt der Grund
  für 07.10. 07:34 bis 09.10. 17:04 (57,5 h). Ohne Start-/Stopp-Zeile mit Grund
  ist eine gewollte Pause von einem Absturz nicht zu unterscheiden, und
  Auswertungen über „Tage" zählen Stillstand als Handelszeit.
