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
- [ ] **Ausstiegsregeln gegeneinander rechnen** — Werkzeug ist fertig: `ausstieg_vergleich.py` spielt acht Kandidaten auf denselben aufgezeichneten Verläufen ab, gegen die Trivial-Latte, nach Kosten. Selbsttest in beide Richtungen bestanden. **Es fehlen nur noch die Daten:** heute 5 echte Verläufe, und deren Aufzeichnung endet beim Verkauf des Bots — eine Regel, die *später* ausgestiegen wäre, lässt sich daran nicht messen. Die 16 Schattenpositionen laufen bis `MAX_TAGE = 7` durch und schließen **am 21.08.** alle auf einmal. Dann erstmals rechnen. Handbuch 4.90.
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

- [ ] **Regel-Wächter auf die Zahlenfelder erweitern.** Er überwacht heute nur `regel_modi`. Am 08.09. wurden **elf weitere** Felder still zurückgesetzt (Befund 97) — er hat sie nicht bemerkt, aufgefallen sind sie nur, weil Sven nachfragte. Freeze-sicher: das Werkzeug liest und meldet, es ändert nichts.

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

- [x] **0. Breakeven-Puffer — ERLEDIGT 12.09., Epoche E9** (Patch 00a: 0,35 → 0,55 %, aus K-BASIS gerechnet). Ursprung: (`risk/exit_rules.py:107`) und die zwei Kostenkonstanten. Gegenprobe liegt vor, sie fällt durch. Handbuch 4.48.
- [ ] **0a. Kaufgebühr doppelt gebucht** — **Ergänzung 19.08.:** Die Ursache in `execution/engine.py:401` steht bereits in Handbuch 4.50. Neu ist nur: die Doppelbuchung gilt **nur im Papiermodus** — im Livebetrieb liefert ccxt `cost` ohne Gebühr, dort wäre die Addition richtig. Wer also nur `app.py:1861/2933` ändert, macht den Live-Pfad kaputt. Sicherer Ort: `engine.py:401` → `amount - fee`. 220 auswertbare Verkäufe: gebucht −2,99 $, richtig mindestens +16,72 $. Handbuch 4.50 und 4.60, `GEFUNDENE-PROBLEME.md` 42, Werkzeug `gebuehren_gegenprobe.py`.
- [x] **1. Warte-Aufträge — GEBAUT am 11.09.2026, Schalter steht auf AUS.** Der offene Einwand ist erledigt: die Gegenauslese ist gemessen, und sie ist **real und stark**. An 382 echten Käufen des Bots: die Fälle, in denen der Auftrag *nicht* gefüllt hätte, liefen 4 h später **+1,142 %**, die gefüllten **−0,106 %** — Unterschied 1,248 Prozentpunkte. Der Bot verpasst genau die guten Fälle. **Der Vorteil überlebt das, halbiert sich aber: +0,161 statt +0,23 Prozentpunkte** (Vertrauensintervall +0,077 bis +0,237, enthält die Null nicht). **Zweite Korrektur:** Die Ursprungsmessung wies die **Trivial-Latte** nicht aus. Weil der Sofortkauf im Mittel negativ ist, ist Nichthandeln für sich genommen schon ein Gewinn — bei 0,50 % Abstand kommen **+0,327 von +0,435** daher, dass der Bot meistens gar nicht handelt. Bei 0,10 % ist der Anteil null. **Einstellung: 0,10 % Abstand, 4 Kerzen gültig** (nicht 12 — an den echten Kaufzeitpunkten ist kürzer besser, der Unterschied 4 gegen 12 ist mit +0,017 bis +0,086 belastbar). Gebaut: `execution/warteauftraege.py`, Abzweig in `execution/engine.py`, Takt in `app.py:_warteauftraege_takt`, Buchung über `app.py:_buche_ergebnis` (derselbe Weg wie ein Sofortkauf). Geprüft mit `warteauftrag_test.py` (10 Punkte) und `warteauftrag_maschine_test.py` (11 Punkte durch die echte Maschine), beide mit Gegentest. Handbuch 4.9.
  - [x] **1a. Scharfgeschaltet am 12.09.2026**, Epoche E9. Freigabe Sven. Die Kontrolle, ob der Bot wirklich mit dem neuen Stand laeuft: `E9_KONTROLLE.bat`. ~~Alter Text:~~ **1a. Scharfschalten** — braucht **vorher** eine Epochengrenze E9 in `config_epochs.json`. Danach `data_store/config.json` → `warteauftraege.aktiv` auf `true`. **Achtung:** Die gemessenen 73,3 % Ausführungsquote sind eine **Obergrenze** — die Messung sieht jedes Kerzentief, der Bot nur alle 12 Sekunden. Nach ein paar Tagen die echte Quote aus `data_store/warteauftraege.json` (`verlauf`) dagegen halten.
- [ ] **2. Ausstiegsschwellen** — **Reihenfolge steht jetzt fest** (Handbuch 4.75): erst (a) `TRAIL_AB_PCT` über die Kostenlinie heben (1,52 % statt 1,20 %, Einzeiler), dann (b) den RSI-Ausstieg ausbauen (+0,948 % gegen +0,357 % beim Trailing, aber nur 14 % der Fälle — **der naheliegendste Hebel**), dann (c) Trail an ATR normieren. **Nicht** Chandelier übernehmen: gegengerechnet an 43 Trades senkt er den Erwartungswert von +0,852 auf +0,592 %.
 Die Ratsche greift bei 0,8 %, die Rentabilitätsschwelle liegt bei ~0,84 % — sie realisiert systematisch zu früh.
- [ ] **3. `schwelle_vergleich.py`** — **erneut gelaufen 26.08., teilweise beantwortet.** Ueber 19,5 Tage und 37.888 Pruefungen: bei **4 h (117 unabhaengige Fenster) und 12 h (39)** lautet das Urteil **"Blocken war richtig"** — die geblockten Kaeufe haetten -0,341 % bzw. -0,248 % gebracht. Bei **24 h** fehlen noch **vier** unabhaengige Fenster (20 von 24 noetig), also rund vier Tage; bei 48 h sind es 10. Bis zum Stichtag erreichbar. Handbuch Teil 2, Abschnitt 2.4.
- [ ] **4. Muenzfrage** — **nachgerechnet 26.08.: mit dem heutigen Aufbau bis zum Stichtag NICHT beantwortbar, und zwar um den Faktor neun.** Aus 1.228 Signalen sind bisher nur **32 Positionen** geworden, ein bis zwei je Muenze. Grund ist die Bauart: je Muenze ist immer nur EINE Schattenposition offen, und sie laeuft bis `MAX_TAGE = 7`. Fuer 30 Faelle je Muenze braeuchte es **210 Tage**. Tatsaechlich 0,15 Positionen je Muenze und Tag; bis zum 18.09. kommen rund 3,4 je Muenze zusammen. **Was trotzdem belastbar ist:** die Kostenmessung je Muenze aus allen 1.228 Signalen (Handbuch Teil 4, Abschnitt 4.3). Wer die Ertragsfrage schneller will, muss die Bauart aendern — mehrere Positionen je Muenze oder `MAX_TAGE` senken. Beides Verhaltensaenderung am Sammler. Handbuch Teil 6, Abschnitt 6.2.
- [ ] **5. `features/regime_adaptiv.py` auf `AKTIV = True`** — **Vorbedingung erledigt 13.09.:** `KOSTEN_PCT` kommt jetzt aus `core/kosten.py` (0,505 statt 0,32). **Das Einschalten selbst bleibt offen und wurde bewusst NICHT in E9 aufgenommen:** dieser Lerner hat am 15.08. mitten im Messfenster die Filterschwelle selbständig geändert — das ist die Epoche E7. Solange 100 Verkäufe gezählt werden, darf der Bot seine eigenen Regeln nicht ändern. Frühestens nach der Auswertung von E9. Ursprünglich: — **erst nach** Korrektur von `KOSTEN_PCT` in Zeile 76 (0,32 → 0,505). Der Fehler ist einseitig: er kann nie zu falschem Verschärfen führen, wohl aber zu falschem Lockern. Handbuch 4.53.
- [x] **6. Kostenkonstanten — ERLEDIGT 13.09.** Es waren nicht acht, sondern **fünf** in ausführbarem Code (`chartanalyse_backtest.py`, `datenexport.py`, `features/regime_adaptiv.py`, `risk/exit_rules_schatten.py`, `stoploss_analyse.py`). **Ursache statt Symptom:** Sie stehen jetzt nicht mehr einzeln da, sondern kommen aus `core/kosten.py` — der einen Quelle. Neun Dateien mit neun Zahlen waren neun Gelegenheiten, eine zu vergessen. `python core/kosten.py` listet alle Fundstellen und meldet Abweichungen. Keine der fünf handelt (Schattenregel, Auswertungen, `AKTIV=False`), deshalb freeze-verträglich. Ursprünglich: (Liste in Handbuch 4.53) — zusammen mit einer Epochengrenze, sonst sind die bisherigen Schattenwerte nicht mehr vergleichbar.

- [ ] **7. `volume_ratio` und `high_low_range` geradeziehen** — betrifft **zwei** Baustellen: die Punktregel `models/signal_model.py:53` (feuert nie) **und** den Trainings-Bruch beim KI-Modell (zwei Merkmale außerhalb des gelernten Bereichs). Nach der Korrektur muß das Modell **neu trainiert** werden, sonst passen alte Gewichte auf neue Werte.

- [ ] **8. Regime-Filter auch im DCA-Pfad** (40) — er greift dort nicht. Im Signal-Pfad hat er rund 68.000 Käufe abgelehnt. Ob das auf dem Hauptweg gut oder schlecht wäre, ist **ungemessen** — erst messen, dann entscheiden.

- [ ] **8a. V4-Kalibrator auf eine lebende Quelle stellen** (76) — `app.py:352` lädt `v4_data/strategy_stats.json`, **Stand 6. Mai 2026**. Der V4-Referenzbot schreibt seit Monaten frische Zahlen nach `v4_referenz/strategy_stats.json` (zuletzt 24.08.), der Kalibrator sieht sie nie. Das zählt, weil das V4-Ensemble mit **bis zu +4 Punkten** der größte Einzelposten der Kaufwertung ist (`agents/signal_agent.py:153`) und der Kalibrator bestimmt, wie stark jede Strategie darin wiegt — bis hin zur vollständigen Sperre bei Gewicht 0,0. **Vormessung erledigt 26.08.** — Formel exakt nachgebaut, mit heutigen Zahlen gefuettert. **Fuenf von acht Strategien wuerden gesperrt:** DCA_FEAR_GREED, TSI_SIGNAL, ICHIMOKU_CLOUD, MACD_CROSS und EMA_TREND — letzteres ist heute das haeufigste Etikett ueberhaupt (192.414 Entscheidungen, 36 der 48 Kaeufe der laufenden Epoche). Uebrig blieben nur FIBONACCI_SUPPORT (0,88) und MOMENTUM_BREAKOUT (0,50), dazu knapp RSI_OVERSOLD (0,40). **Das ist keine Feinjustierung, sondern ein Umbau des Kaufverhaltens.** **Wichtig:** Alle sechs Sperren sind statistisch abgesichert, **keine der drei Freigaben** — deren Summen sind kleiner als ihre eigene Schwankungsbreite. **Und Befund 78:** Die Sperrregel ist ein harter Schalter genau auf der Nulllinie (`v4_calibrator.py:86`, `total_pnl <= 0`), ohne Puffer und ohne Mindestfallzahl. RSI_OVERSOLD stand am 25.08. bei -57,86 $ (gesperrt) und am 26.08. bei +2,55 $ (freigegeben), bei einer Schwankung von ±100 $. **Nur zusammen mit einer entschaerften Regel ausfuehren:** Sperre erst ab einem Verlust groesser als die eigene Schwankungsbreite und erst ab 30 Faellen. Handbuch Teil 5, Abschnitt 5.11.

- [ ] **8b. Die zwei Strategielisten zusammenführen** — `agents/strategy_brain.py:41` kennt `ICHIMOKU` und `TSI`, `agents/v4_strategies.py:27` dieselben Strategien als `ICHIMOKU_CLOUD` und `TSI_SIGNAL`. Ein Handel unter dem einen Namen kann den Zähler des anderen nie erhöhen. Deshalb steht ICHIMOKU mit 69 Trades im Gehirn und **0** im sauberen V6-Zähler. **Vormessung erledigt 26.08.: heute wirkungslos, zurueckstellen.** Diese Strategien feuern in V6 **ueberhaupt nicht** — ICHIMOKU_CLOUD, TSI_SIGNAL, STOCHRSI_REVERSAL und MOMENTUM_BREAKOUT stehen an **null** Handeln und **null** Entscheidungen. Ein Zusammenfuehren wuerde heute nichts aendern; es wird erst gebraucht, wenn sie tatsaechlich handeln, also fruehestens nach 8a. **Was sich stattdessen lohnt:** die Rueckfallebene `v4_strategy_used or self.current_strategy` (`agents/signal_agent.py:182`) hat seit dem 23.08. **3.606 Kaufentscheidungen** mit dem Etikett `GRID_BOT` versehen — dem Namen eines abgeschalteten Bausteins. Wer die Auswertung liest, haelt den Gitter-Handel fuer aktiv. Handbuch Teil 5, Abschnitte 5.2 und 5.11.

- [x] **9. `entry_score` auf dem DCA-Pfad — ERLEDIGT 13.09.** (Befund 41). Die Zeile stand inzwischen bei `app.py:3119`, nicht mehr bei 2971. `_dca_intent` gab es nirgends; die Variable heißt dort `intent` und trägt `score=5`. Am Syntaxbaum geprüft, dass sie an der Stelle gebunden ist. Reines Aufschreiben — keine Handelsregel liest `entry_score`, nachgezählt. Test: `reparaturen_test.py`. Ursprünglich: (41) — `app.py:3029` (Stand 11.09., früher 2971) greift auf `_dca_intent` zu, eine Variable, die es nirgends gibt (`grep`: 0 Treffer). Deshalb sind 0 von 220 Verkäufen mit Score versehen. Einzeiler. *Der Score in `telemetrie.db/evaluations` ist davon nicht betroffen — TODO-Punkt 3 bleibt auswertbar.*


- [x] **9a. `entry_score` überlebt keinen Neustart — BEHOBEN am 11.09.2026** (Befund 88, Glied 3). `runtime/state_manager.py` speichert eine offene Position nach einer **Whitelist** von 13 Feldern; `entry_score` und `entry_strategie` fehlten. Ihr eigener Kommentar warnt wörtlich: *„was nicht aufgezählt ist, überlebt keinen Neustart."* Am 29.08. war das noch OFFEN, weil *„es bräuchte eine offene Position zum Mitlesen, und es war keine da"* — am 11.09. war eine da: die BTC-Position trug genau diese 13 Felder. **Folge, solange es kaputt war:** Die Schreibwege-Reparatur vom selben Tag griff nur bei Positionen, die innerhalb *einer* Bot-Laufzeit auf- und wieder zugehen. Geprüft mit `whitelist_test.py` (Rundlauf, Gegenprobe mit erfundenem Feld, Gegentest gegen die alte Fassung). **Wirkt ab dem nächsten Bot-Start.** Handbuch 8.7 (Nachtrag 11.09.).

- [ ] **10. Zwei Cash-Puffer, 2 % und 5 %** (43) — beide in `_execute_approved_trade`, beide mit derselben Begründung. Der zweite gewinnt immer. LOW, aber ein Fallstrick für die nächste Änderung.

- [ ] **11. `total_equity` in zwei Spalten trennen** (44) — die Spalte enthaelt zwei Kapitalbegriffe, die sich um 96 $ bei 590 $ (16 %) unterscheiden: `app.py:952` **ohne** Sparplan-BTC, `portfolio/manager.py:70` **mit**. Beide fuer sich richtig, aber in derselben Spalte. Geht in Positionsgroesse **und** Risikopruefung. Vorschlag: `equity_handel` und `equity_gesamt` getrennt. Handbuch 4.63.

- [x] **12. Trailing-Schwelle — ERLEDIGT 12.09., Epoche E9** (Patch 45: 1,2 → 1,57 %). Ursprung: (45) — `TRAIL_AB_PCT` = 1,2 %, Nulllinie bei 1,52 %. Jeder Ausstieg aus einem Höchststand dazwischen verliert rechnerisch. **Nicht einfach hochsetzen** — wer später ratscht, gibt bei jedem Trade zwischen 1,2 und 1,6 % den ganzen Gewinn zurück. Erst die Positionsverläufe auswerten. Handbuch 4.64.

- [ ] **13. Take-Profit klären** (46) — `take_profit_pct = 0.0`, der Mechanismus ist tot. Vermutlich Absicht, steht aber nirgends. Ein abgeschalteter Mechanismus ohne Begründung ist von einem vergessenen nicht zu unterscheiden.

- [ ] **14. Exposure-Grenze folgt Moduswechsel nur nach oben** (48) — `risk/engine.py:323` nutzt `max()`, Reset nur im Konstruktor. Von `btc_only` (95 %) zurück auf `balanced` (35 %) kommt die Verschärfung nicht an. Wirkung durch drei weitere Deckel begrenzt.

- [ ] **15. Ereignisbus zählt ohne Sperre** (52) — `core/bus.py`: `_stats` und `_event_log` werden aus 26 Scheduler-Threads ungeschützt beschrieben, betrifft auch den Fehlerzähler. Einzeiler: zwei Zeilen in den Lock ziehen, der drei Zeilen später steht.

- [ ] **16. Laufzeit je Scheduler-Aufgabe messen** (53) — eine Aufgabe mit 12 s Takt, die 60 s braucht, läuft faktisch alle 60 s. Niemand erfährt es. LOW.

- [x] **17. Verlustzähler — ERLEDIGT 12.09., Epoche E9** (Patch 54). Ursprung: (54) — `coin_consecutive_losses` steht nicht in `bot_state.json`, die Cooldown-Sperre greift deshalb nie (0× in 12 Tagen trotz Serien von 4/3/3). Der Kill-Switch speichert seinen Tagesverlust, dieser Zähler nicht. Zusätzlich misst er den **gebuchten** Dollar-Wert statt des Netto-Ergebnisses. Handbuch 4.74.

- [ ] **18. Kapital wird beim Verkauf doppelt gezählt** (55) — zwischen Gutschrift des Erlöses und Entfernen der Position steht beides in der Bilanz. 2 Messungen von 203.432, aber sie ließen den größten Rückschlag von 13,11 auf 23,20 % springen. Kennzeichen: `offene_positionen IS NULL`. Auswertungsseitig bereits gefiltert; der Schreibpfad gehört korrigiert. Handbuch 4.78.

- [ ] **19. Das Gehirn lernt brutto statt netto** (58) — `strategy_brain.py:332` zaehlt `pnl > 0` als Gewinn: **76,8 %** Trefferquote statt der wahren **44,6 %** nach Kosten, 32,2 Punkte zu gut. Die Zahl wirkt: `select_best()` vergibt dafuer bis zu **+2,0 Punkte** (`strategy_brain.py:168-177`). Zusaetzlich stehen Ausstiegsgruende als „Strategien" in derselben Tabelle (`exit_monitor.py:336-362` → `:581`), 119 von 224 Verkaeufen. Reihenfolge: erst gegen K-BASIS messen, dann Ausstiegsgruende trennen. Handbuch 4.82.
- [x] **20. Allzeithoch — ERLEDIGT 12.09., Epoche E9** (Patch 63: jetzt aus den Wochenkerzen). Ursprung: (63) — `agents/cycle_theory.py:28` steht auf 109.114 $ (20.01.2025). Gegen drei Quellen geprueft liegt das echte Hoch bei **126.200 $** (06.10.2025). Der Bot misst dadurch **-34,1 statt -43,0 %** Abstand, steht auf EARLY_BEAR statt MID_BEAR und kauft **20 % groessere Positionen** (Multiplikator 0.6 statt 0.5). Patch liegt geprueft bereit: `patches_nach_27_08/patch_63_ath_dynamisch.py`. Handbuch 4.94.
- [x] **21. Breakeven-Puffer — ERLEDIGT 12.09. mit Punkt 0.** Ursprung: (Ergaenzung zu Punkt 0) — `risk/exit_rules.py:107` steht auf 0,35 %, hergeleitet aus der **alten** Gebuehrenannahme. Bei K-BASIS 0,505 % bedeutet das **-0,155 % netto**: die Sperre sichert nicht die Null, sondern einen kleinen Verlust. Die im Code selbst verlangte Gegenprobe ist faellig und faellt durch (vier Faelle nach dem Fix: -0,594 $ im Schnitt, schlechter als die sechs davor). Neuer Wert 0,55 %, aus K_BASIS_PCT gerechnet statt gesetzt. Patch bereit: `patches_nach_27_08/patch_00a_breakeven_puffer.py`. Handbuch 4.34 + 4.97.
- [ ] **22. Ausstiegsregeln gegeneinander rechnen** — **gelaufen 26.08., Ergebnis nicht verwertbar (Befund 79).** `ausstieg_vergleich.py` meldet, dass alle acht Regeln gegen die Trivial-Latte "Halten" verlieren (+6,063 % gegen +2,001 % beim Bot). **Diese Zeile traegt kein Urteil:** Die Latte rechnet ueber zwei Bestaende mit voellig verschiedener Aufzeichnungsdauer — echte Positionen **4,6 h** im Median, Schattenpositionen **99,4 h**. Faktor 21. Bei echten Verlaeufen endet die Aufzeichnung beim Verkauf, "Halten" heisst dort also "halten bis der Bot ohnehin verkauft". Verglichen wurde vier Stunden gegen vier Tage, in einem steigenden Markt. **Zu tun, beides freeze-vertraeglich:** entweder getrennte Tabellen fuer echt und Schatten, oder alle Verlaeufe auf dieselbe Zeitspanne stutzen. Handbuch Teil 8, Abschnitt 8.9, Fall 5.

- [x] **23. `AppConfig.save()` — ABGESICHERT 13.09., Ursache weiter OFFEN.** Am Code nachgesehen: es gibt im ganzen Projekt **keine Stelle**, die eine frische `AppConfig()` baut und speichert — nur die Tests. Wer den Verlust auslöst, ist damit **nicht bestimmt**, und deshalb steht dort ausdrücklich **kein Fallback**, der einen unverstandenen Fehler wegbügelt. Stattdessen: (1) eine **Sicherung** der alten Datei vor jedem Schreiben, rollierend die letzten zwölf — am 08.09. musste der Stand aus einem vier Wochen alten git-Commit geholt werden; (2) ein **lauter Hinweis**, wenn vier oder mehr Werte gleichzeitig auf ihre Vorgabe zurückfallen. Das Speichern wird **nicht** blockiert — ein Wachposten, der den Betrieb anhält, wäre gefährlicher als der Fehler. Sieben Prüfungen in `config_wachposten_test.py`. Ursprünglich: Am 08.09. setzte **ein** Speichervorgang in der Einstellungsmaske **zwölf** Werte gleichzeitig zurück: der Block `regel_modi` verschwand (Trend-Ausstieg fiel von SHADOW auf ACTIVE), `trading.coins` sprang von 3 auf 12, `telegram.enabled` auf false, dazu neun Zahlenfelder auf ihre Vorgabewerte (`take_profit_pct` 0,0 → 1,5 · `stop_loss_pct` 2,5 → 2,0 · `trailing_stop_pct` 1,0 → 1,5 · `daily_loss` aktiv/6 % → schatten/10 % · `initial_paper_balance` 500 → 300 u. a.). **Das ist Befund 31 vom 12.08. ein zweites Mal** — die damalige Reparatur hat nicht gehalten, obwohl der Kommentar `# [GEFUNDENE-PROBLEME #31]` noch in `config/settings.py` steht und „Unbekannte Bloecke ERHALTEN" verspricht. Wiederhergestellt aus dem git-Stand vom 12.08. 22:36 (Commit `bb6cc02`, dem Tag vor Beginn von E6). **Bis zur Reparatur gilt: nach jedem Speichern in der Einstellungsmaske einmal `python lage_erzeugen.py`** — es warnt bei fehlendem `regel_modi`.
- [x] **24. Doppelstart-Sperre — ERLEDIGT 13.09.** (Befund 93). `core/startsperre.py`, aufgerufen im `__main__`-Block. **Grundsatz: im Zweifel starten lassen** — ein Bot, der fälschlich nicht startet, ist schlimmer als zwei. Gesperrt wird nur, wenn die eingetragene Prozessnummer **noch lebt UND wirklich ein `app.py` ist**; tote Nummer, kaputte Datei, fremder Prozess oder fehlendes `psutil` lassen starten. Notausgang: `python app.py --trotzdem-starten`. Zehn Prüfungen in `startsperre_test.py`, davon sieben Durchlassfälle. Ursprünglich: `app.py:4573` erzeugt sofort `TradingImperiumV6()`, ohne nachzusehen, ob schon einer läuft. Die Sperrdatei in `core/hintergrund.py` schützt nur die Hintergrundjobs, und die Portbelegung bremst nicht: mit `netstat` nachgemessen hört der Bot-Prozess **keinen einzigen Port** ab. Damit läuft auch die Regel in `CLAUDE.md` ins Leere, die verlangt, vor jedem Neustart zu prüfen, wer Port 5050 hält — es hält ihn niemand. Am 01.09. hing dadurch die Handelsschleife 37 Minuten. Nötig: Sperrdatei im `__main__`-Block **samt Prüfung, ob die eingetragene Prozessnummer noch lebt** (sonst sperrt ein Absturz den nächsten Start dauerhaft aus).
- [x] **25. Eingefrorene Kurse — ERLEDIGT 13.09.** (Befund 95). Der Marktschnappschuss schreibt **keine Zeile** mehr, wenn BTC, ETH und SOL exakt dieselben Werte tragen wie beim letzten Mal — drei Kurse zu zwei Zeitpunkten sind nie auf acht Stellen gleich. **Bewusst NICHT in `fetch_current_price`:** die Funktion versorgt auch den Stop-Loss (`runtime/exit_monitor.py:657`); ihr bei altem Cache den Preis zu verweigern wäre eine Verhaltensänderung mit Kapitalrisiko. Abgesichert ist nur das **Aufschreiben**. Ursprünglich: `markt_historie` schreibt bei fehlgeschlagenem Kursabruf den **alten** Wert weiter, im normalen 15-Minuten-Takt. 129 von 2.162 Zeilen (6,0 %) über 15 von 24 Tagen, längste Serie 6 h 45 min. Eine Lücke wäre sichtbar; ein eingefrorener Wert sieht aus wie eine Messung. **Empfohlen: bei fehlgeschlagenem Abruf gar keine Zeile schreiben** — eine ehrliche Lücke statt einer falschen Messung. Die Sichtbarmachung ist seit 03.09. gebaut (Wiederholungsprüfung in `sammler_pruefen.py`), die Ursache nicht behoben.

## D — Beobachten, nichts tun

- [x] **Sammler-Laufzeit gegengeprueft — erledigt 26.08.2026.** `sammler_taeglich` braucht im Schnitt **22,7 s**, im laengsten Fall 39,9 s (21 Laeufe). **Die 14 Minuten waren fremde Last, wie vermutet.** Dabei fiel **Befund 80** auf: die Spalte `laufzeit_sek` stand bei 42 von 43 Zahlenbuch-Laeufen und 1.722 von 2.036 Capture-Laeufen auf genau 0,0 — `job_start()` und `job_ende()` wurden direkt hintereinander gerufen, beide NACH getaner Arbeit. **Behoben**, gegengeprueft: Protokoll meldet 78 s, Tabelle traegt jetzt 77,7 s.
- [x] **London Liquidity Sweep — gemessen 08.09., Urteil NO-GO (Befund 96).** Svens Vorschlag, sauber geprüft: 6 Monate 15-Minuten-Kerzen, drei Münzen, 15 Varianten. Ergebnis netto je Handel −0,384 bis −0,493 %, **jede Variante negativ**. Trivial-Latte entscheidet: Bei BTC bringt „täglich um 07:00 blind kaufen" +0,035 % gegen +0,032 % beim Sweep — er ist **nicht besser als blindes Kaufen zur selben Uhrzeit**, bei SOL sogar schlechter. **Der Vorteil ist aber echt:** alle drei Münzen brutto im Plus (+0,027 · +0,121 · +0,012 %), nur vier- bis fünfzigmal zu klein für die 0,505 % Kosten. **Wieder aufmachen nur, wenn die Kosten unter 0,10 % fallen** — also zusammen mit Punkt C1 (Warte-Aufträge). Nicht durch Parameterdrehen, das wäre Überanpassung. Werkzeug: `london_sweep_messung.py`.
- [x] **Autostart des Schatten-Sammlers — ERLEDIGT 16.09.2026, und zwar OHNE Adminrechte.** Der Punkt stand vier Wochen als „braucht Rechte, die wir nicht haben“. Er brauchte keine. Nachgemessen: `schtasks /create /sc onstart` → *Zugriff verweigert*; `schtasks /create /sc onlogon` → *Zugriff verweigert*; `Register-ScheduledTask -AtLogOn -User <eigener Benutzer>` → **geht**. **Der Unterschied liegt nicht am Auslöser, sondern daran, für WEN die Aufgabe gilt:** `schtasks` legt sie ohne weitere Angabe für *jeden* Benutzer des Rechners an — und wer etwas für fremde Benutzer einrichtet, braucht Adminrechte, zu Recht. Auf den eigenen Benutzer eingegrenzt, fällt der Grund weg. Angelegt sind jetzt **zwei** Aufgaben, beide auf den LIVE-Ordner: `SchattenUniversumLIVE_Anmeldung` (bei der Anmeldung, 1 Min Verzug) schließt die Lücke nach dem Hochfahren, `SchattenUniversumLIVE` (alle 15 Min) fängt Abstürze ab. Werkzeug: `autostart_einrichten.py` (`--pruefen` / `--entfernen`). Gegengeprüft: beide in der Aufgabenplanung sichtbar, Starter läuft in 3,7 s durch (Exitcode 0), Sammler-Prozess im LIVE-Ordner bestätigt. **Die Lehre:** ein Monat Wartezeit auf Rechte, die nie nötig waren — weil das erste Werkzeug, das scheiterte, für die Antwort gehalten wurde. Im Papier-Ordner ließe sich `SchattenUniversumWacht` genauso um einen Anmelde-Auslöser ergänzen; dort **unangetastet** gelassen (Bestandsschutz). Handbuch 8.7c.
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

## E — Auftrag vom 04.09.2026: die neun Punkte

*Von Sven in einer Nachricht aufgegeben. Reihenfolge: erst der Prompt (E0),
dann E1 bis E9 der Reihe nach. Sven: „eins nach dem anderen … mit Backtests
natürlich, wie wir immer sagen: doppelt hält besser, und dreifach noch besser."*

- [x] **E0. Der Prompt für Claude Code.** Enthält alle neun Punkte als
  Auftrag. Vorlage: Svens eigener `securityprompt.txt` (Expertenrollen +
  nummerierte Aufgabenblöcke). → `PROMPT_MEISTERWERK.md`

- [ ] **E1. Strukturelles Hoch im Analyse-Reiter.** Dunkelrot/schwarz, dicker
  gestreifter Balken. Freeze-sicher, weil der Reiter reines Beobachtungsdeck
  ist. **Gegentest Pflicht:** erkennt es ein echtes strukturelles Hoch — und
  meldet es keines, wo keines ist?

- [ ] **E2. Svens Beobachtung messen: „der Kurs fällt oder steigt immer mit
  etwas Zeitabstand".** Das ist eine **Hypothese über eine Verzögerung
  (Lag)**, und sie ist messbar: Kreuzkorrelation zwischen Auslöser und
  Kursbewegung über verschiedene Zeitversätze. **Nicht bauen, bevor gemessen
  ist.** Trivial-Latte: Zufallsverschiebung.

- [ ] **E3. Video-zu-Text-Werkzeug.** Sven filmt Charts mit dem iPhone.
  Offline-Umschrift (Whisper), Ausgabe als Textdatei, `.bat` zum
  Doppelklicken. Damit werden seine Videos für die Arbeit nutzbar.

- [ ] **E4. Fernzugriff bis Mittwoch 09.09.** — **einziger Punkt mit harter
  Frist.** Rechner bleibt zu Hause, Zugriff per Tailscale: an-/ausschalten,
  Bildschirm sehen, Claude Code bedienen. **Kein Serverumzug vor dem 18.09.**
  — das bräche das Messfenster.

- [ ] **E5. Manuell-Reiter und Charts anpassen** — als Option, nicht als
  Zwang. Offen, was genau. Erst fragen, dann bauen.

- [ ] **E6. Das Meisterwerk-Buch.** Die vier Bücher abgleichen
  (`BOT-HANDBUCH.md` 6.996 Zeilen, `ENTWICKLERHANDBUCH.md` 20.264,
  `ZAHLENBUCH.md` 70, dazu die drei PDF-Fremdbücher), Lücken suchen,
  zusammenführen. **Achtung:** Zusammen über 30.000 Zeilen — das passt in
  kein Kontextfenster am Stück. Muss in Abschnitten laufen.

- [ ] **E7. Systemdurchleuchtung.** Was läuft noch, was wurde herausgenommen
  und würde heute helfen, was ist vergessen. Ausgangspunkt:
  `PROJEKT-ENTSCHEIDUNGEN.md` — was dort steht, ist Entscheidung, nicht Bug.

- [ ] **E8. Serverfrage für die Zeit nach dem 18.09.** Gemessen:
  `app.py --headless` gibt es (`app.py:4620`), Projekt 1,8 GB, Bot braucht
  805 MB. Ein kleiner Server genügt. **Erst nach dem Messfenster, mit
  Epochengrenze.**

- [ ] **E9. Konto und E-Mail verknüpfen.** — **Kann Claude nicht.** Nur Sven
  selbst unter `claude.ai` → Einstellungen. Steht hier, damit der Punkt nicht
  verlorengeht, nicht weil jemand daran arbeitet.

**OFFEN geblieben:** Sven schrieb „erstell sie dann im Schema Punkt 18".
In `securityprompt.txt` reicht das Schema bis **10**, in `MASTERPROMPT.md`
bis **12**. Einen Punkt 18 gibt es in keiner der beiden Dateien. Rückfrage
steht aus; bis dahin wurde das volle Schema aus `MASTERPROMPT.md`
Abschnitt 1 benutzt.

---

## F — Stand 26.09.2026, nach dem Umzug auf den Windows-11-Rechner

**Herkunft dieser Liste, nach Regel 1 dieser Datei:** Die Punkte sind in
drei Gruppen getrennt, weil sie **nicht denselben Beleggrad** haben. Wer
das übersieht, hält eine fremde Behauptung für einen geprüften Befund.

### F1 — Selbst geprüft, mit Fundstelle (SICHER)

- [ ] **Befund 122: der Wächter hat keinen Aufrufer.** `live/watchdog.py:20`
  `check()` startet tote Threads neu — wird aber von **keiner** Stelle
  gerufen. Alle vier Fundstellen von `watchdog`: `app.py:63`, `:554`,
  `:4731` (das neue `stop()`), `:4862` (`get_status`). Entscheidung
  ausstehend: verdrahten (eigene Epochengrenze **und** vorher eine
  Messung, geschätzt Risiko 7 / Aufwand 6 / Wirkung 10) oder als bewusst
  stillgelegt markieren. **Solange gilt: es gibt keinen automatischen
  Thread-Neustart.**
- [ ] **50 % Positionsgröße und 35 % Obergrenze schließen sich aus.**
  `risk/engine.py:47` rechnet `max(35, 50+5)` = 55; eine 35er Grenze würde
  die eigene 50-%-Position blockieren. Dazu liest der aktive Modus
  `risk.max_exposure_per_coin_pct` gar nicht (nur Rückfallzweig `:51`),
  und `ui/main_window.py:2663` rechnet den Wert beim Speichern erneut auf
  `position_size_pct+5`. Sven ist unterrichtet; die 35 steht auf seinen
  Wunsch in der Datei und ist wirkungslos. **Wenn er wirklich 35 will,
  muss die Positionsgröße unter 30.**
- [ ] **`trades_v5.json` trägt kein Modus-Feld** (43 Felder geprüft).
  Echtgeld- und Papier-Trades sind nur über Zeitstempel und
  Epochengrenze trennbar. **Jede Auswertung muss `epochs.py split_trades`
  benutzen**, sonst mischt sie die 10 Echtgeld-Trades mit Papier-Trades
  und liefert eine Trefferquote, die nichts bedeutet. Zuordnung am
  26.09. an der Sekundengrenze und an allen 10 echten Trades geprüft.
- [ ] **`start_bot.bat` setzt kein `PYTHONUNBUFFERED`.** Weil die Ausgabe
  in eine Datei geht, puffert Python blockweise:
  `data_store/jobs/bot_konsole.log` hing nach zwölf Minuten Laufzeit bei
  acht Zeilen, obwohl der Bot normal arbeitete. Für „läuft er noch?" ist
  `data_store/system.log` die richtige Quelle. Kein Fehler der Umleitung
  — die verhindert weiter die Konsolensperre (Befund 109).
- [ ] **Der Sammler läuft mit altem `config/settings.py`.** PID 8368,
  gestartet 21.09., also vor der Portumstellung. Für ihn ohne Folgen (er
  benutzt die Dashboard-Anschlüsse nicht), aber `prozess_frische.py`
  meldet es stündlich, bis er einmal durchstartet.
- [ ] **`lage_erzeugen.py:252` zeigt auf `C:\Users\<BENUTZER>\OneDrive\...`** —
  das Sicherungsziel des Laptops. Wohin es auf diesem Rechner zeigen
  soll, weiß nur Sven.
- [ ] **Zwölf weitere `sven7`-Pfade** in Auswertungsskripten
  (`pnl_check.py`, `e7_auswertung.py`, `inventar_agent.py` …), alle in
  Kommentaren und Aufrufbeispielen. Kein Handelspfad betroffen.
- [x] **Eigener Fehler im Ordnerfilter behoben** (26.09.). Mein Fix vom
  21.09. verglich in `prozess_frische.py:236` nur `ordner == HIER` und
  verlor damit jeden Prozess in einem **Unterordner** — in v6 fiel so der
  Forschungs-Sammler heraus, und das Werkzeug meldete „LÄUFT NICHT" für
  einen Prozess, der lief. Gefunden von der v6-Sitzung, selbst
  nachgeprüft. Behoben, aber **enger als dort vorgeschlagen**: echte
  Unterordner gelten, `.claude/worktrees` und `v4_referenz` nicht. Sonst
  würde eine stehengelassene Projektkopie als Prozess dieses Ordners
  zählen — derselbe Zuordnungsfehler eine Ebene tiefer, und genau der
  Fall von **Befund 73** (24.08., eine Kopie lief 40 Minuten und schrieb
  ins Nichts). Gegentest über acht Fälle, alle richtig, danach Durchlauf
  mit echten Daten.
- [ ] **Nachtrag zum Ordnerfilter: mein Gegentest prüfte eine Kopie, nicht
  den Code.** `_gehoert_hierher` steht verschachtelt in `main()` und ist
  von außen nicht aufrufbar. Der Achtfall-Test hat die Logik deshalb
  **nachgebaut** — wäre die Kopie von der echten Zeile abgewichen, hätte
  der Test bestanden und der Code trotzdem falsch gelegen. Genau die
  Fehlerklasse aus Abschnitt 6 der Übergabe. Belastbar geprüft sind damit
  nur die Fälle, die der Durchlauf mit echten Daten abdeckt: eigener
  Ordner **ja**, Nachbar-Bot v6(21) **nein**. Die exotischen Fälle
  (Unterordner, `.claude/worktrees`, `…v7x`) hängen an der Kopie.
  **Zu tun:** Funktion auf Modulebene ziehen — `gehoert_hierher(ordner,
  hier=HIER)`, so hat es die v6-Sitzung gemacht — und den Achtfall-Test
  gegen die **echte** Funktion laufen lassen. Klein, reines Prüfwerkzeug,
  kein Handelspfad, keine Epochengrenze.
- [x] **Der leere Hüllordner `Desktop\trading_imperium_LIVE` ist weg** —
  er war beim Umzug vom Shell-Prozess gesperrt, am 26.09. nicht mehr
  vorhanden. Auf dem Schreibtisch stehen jetzt nur noch
  `trading_imperium_v6(21)` und `trading_imperium_v7`.
- [x] **Sichtbare Beschriftungen von V6 auf V7 umbenannt** (26.09., Wunsch
  Sven). 14 Stellen in 6 Dateien, nicht blind ersetzt — berechtigte
  V6-Verweise und `version 6.1.0` blieben unberührt, V7 bezeichnet die
  **Instanz**. Der Fenstertitel trägt zusätzlich den Modus:
  `TRADING IMPERIUM V7 – Multi-Agent · PAPIER`. *Sichtbar wird es beim
  nächsten Neustart — `prozess_frische.py` meldet bis dahin fünf
  geänderte Dateien, und zwar **ausschließlich** die Beschriftungen. Am
  Handel ändert sich nichts, die L7-Regeln laufen korrekt.*

### F2 — Aus dem Regel-Inventar der v6-Sitzung, von mir NICHT nachgeprüft

Diese Punkte stehen in `GEFUNDENE-PROBLEME.md` 113–121 und
`REGEL-INVENTAR_2026-09-25.md`. Ich habe sie **nicht** selbst gegen den
Code gehalten — das ist nach Regel 1 dieser Datei kein Mangel der Punkte,
sondern eine Pflichtangabe über meinen Prüfumfang.

- [ ] **113 — Warteaufträge werden nie als ausgeführt erkannt.**
  `warteauftraege_live.py:133`. **Blockiert die Rückkehr zu echtem Geld.**
- [ ] **114 — Zusatzaufträge ohne Stornoverfolgung.** `engine.py:1075-1110`.
  **Blockiert Echtgeld.**
- [ ] **115 — Verbindungsfehler schaltet still auf Papier.**
  `engine.py:227`. **Blockiert Echtgeld.** Betrifft rückwirkend den
  ETH-Verkauf vom 17.09. 11:45, der ohne Kennzeichen im Echtgeld-Journal
  steht.
- [ ] **116 — Füllung geht verloren, wenn die Handelssperre 10 Sekunden
  belegt ist.** `app.py:1328-1333`. Gilt **auch auf Papier**, verfälscht
  also die laufende Messung.
- [ ] **121 — Handbuch weicht an sieben Stellen vom Code ab.**
- [ ] **Die versteckten Regeln** (Inventar §3g) gehören in Handbuch
  Teil 2/3, damit sie nicht versteckt bleiben.

**Wichtig zur Reihenfolge, Entscheidung Sven am 26.09.:** 113 bis 115
sperren nur den Weg zurück zu echtem Geld. Dorthin will er ohnehin erst
mit Zahlen. Deshalb läuft die Papiermessung zuerst — jede weitere
Reparatur am Handelspfad braucht eine Epochengrenze, und jede Grenze
setzt die Zählung auf null. Genau dieser Mechanismus hat aus sieben
Monaten Laufzeit sechs verwertbare Tage gemacht.

### F3 — In v6 fertig gebaut, Übertragung nach v7 steht aus

**Stand 26.09.2026, 01:00.** Die v6-Sitzung hat 118 und 119 dort gebaut
und getestet. Die Übertragung nach v7 ist **bewusst nicht gemacht** —
Begründung unten.

- [ ] **118 — die sieben Regel-Schalter verdrahten** (ACTIVE wie bisher,
  OFF übersprungen, SHADOW nur notiert, per Test belegt).
- [ ] **119 — die sechs toten Schutzregeln im SCHATTEN anschließen**
  (rechnen und notieren, nicht eingreifen).

**Wo die fertige Arbeit liegt** (in `trading_imperium_v6(21)`, Existenz
und Umfang am 26.09. selbst geprüft):

| Datei | |
|---|---|
| `schalter_anschluss_20260926.diff` | 41,9 KB, **526 geänderte Zeilen in 6 Dateien** |
| `schalter_anschluss_test.py` | 18,7 KB, 43 Prüfungen |
| `BOT-HANDBUCH.md` 1.5a | das Warum |

Betroffen: `app.py`, `core/regel_schalter.py`, `core/regel_waechter.py`,
`regel_waechter_bestaetigen.py`, `risk/engine.py`,
`runtime/exit_monitor.py`. *Kleine Abweichung zur Beschreibung des
Kollegen: dort ist von `data/nupl_monitor.py` die Rede, im Diff stehen
stattdessen die beiden Wächter-Dateien.* Die Zeilennummern weichen
zwischen den Ordnern ab — **Stelle für Stelle übertragen, nicht blind
anwenden.**

**Warum nicht sofort übertragen — drei Gründe:**

1. **Sven hat am 26.09. entschieden, zuerst zu messen** („ja ich schliesse
   mich dir voll an"). Die Anweisung, die der Kollege zitiert, ist
   **älter** als diese Entscheidung.
2. **SHADOW heißt nicht wirkungslos.** Die sechs Regeln rechnen dann im
   12-Sekunden-Takt mit und schreiben mit. Das ist neuer Code im
   Handelspfad — neue Absturzfläche, neue Schreibvorgänge. Der Kollege
   musste dafür selbst eine Sperre einbauen (höchstens ein Eintrag je
   Regel, Symbol und Stunde), „sonst flutet der 12-s-Takt die Tabelle".
3. **Zwei v7-Fragen sind offen, die der Kollege ausdrücklich an Sven
   weitergibt:** die Wechselwirkung mit dem Fraktal-Tor und Kaufweg 2,
   und der Kill-Switch bei Papierkapital.

**Zum Kill-Switch, selbst nachgerechnet (SICHER):**

```
Position 250 $, Stop 2,5 %   ->  6,25 $ Verlust je Trade
Kill-Switch 100 $            ->  16 Verlust-Trades
Tagesverlust 6 % = 30 $      ->  4,8 Verlust-Trades   (Modus: aktiv)
```

Der Tagesverlust-Wächter ist **schon verdrahtet** (`portfolio/daily_loss.py`,
`daily_loss_state.json` führt heute `start_equity: 500.0`) und pausiert
Käufe nach knapp fünf Verlust-Trades. Bei einer gemessenen Trefferquote
zwischen 42 und 60 % ist das an einem Tag gut erreichbar — **die Messung
kann also regelmäßig stillstehen, ohne dass etwas kaputt ist.** Das gehört
geprüft, bevor weitere Notbremsen dazukommen.

*Gegen die Doppelarbeit: Die Module sind in beiden Ordnern fast gleich,
zwei getrennte Bauten wären genau das, was `wmic` schon gekostet hat
(Befund 105). Deshalb baut v6, wir übertragen — nur eben zum von Sven
gewählten Zeitpunkt.*

### F4 — Messen, nicht reparieren

- [ ] **120 — das Fibonacci-Ziel liegt außer Reichweite.** Ziel 1,0 bei
  +6 bis +10 %, Stop bei −2 %, Ziel **0-mal** erreicht. An den 6 echten
  Verkäufen selbst nachgesehen und bestätigt: 4× Stop-Loss, 1× Breakeven,
  1× Trailing, **null** Fibonacci-Ausstiege, höchster je erreichter
  Zwischengewinn **1,95 %**. Aufgabe: messen, was Ziel 1,0 aus der
  *Kaufwelle* gegenüber der *größten* Welle ergäbe, und Sven vorlegen.
  Das ist Strategie, kein Tippfehler.
  > **Korrektur einer eigenen Aussage vom 25.09.:** Ich hatte
  > vorgerechnet, das Ziel liege nur ~1 % über dem Einstieg, und
  > empfohlen, `ZIEL_VERKAUF` auf 1,272 zu **erhöhen**. Meine Prämisse
  > war die Mindestwelle (2 % Spanne); gerechnet wird mit der größten.
  > Die Empfehlung zeigte in die falsche Richtung — das Ziel gehört
  > **näher**, nicht weiter weg.
- [ ] **Gestaffelte Teilverkäufe sind jetzt erstmals messbar.** Laut
  Epoche L3 sind die `ANTEILE` (40/30/30 bei 1,0 / 1,272 / 1,618) *nur*
  wegen der Kontogröße nicht angeschlossen: Teilmengen lägen unter der
  Börsen-Mindestmenge von 5 $. Auf Papier sind die Positionen jetzt
  **250 $** — ein Drittel davon ist weit über dem Minimum. Genau der
  Teil des Verfahrens, in dem der Vorteil stecken soll, ließe sich
  also messen. **Vorher klären, ob das die laufende Messung wert ist**
  (eigene Epochengrenze).
- [ ] **Zweiter Telegram-Zugang.** Papier- und Live-Bot teilen einen
  Token und rufen beide `getUpdates` ab — Befehle landen zufällig bei
  einem von beiden. Holen kann den nur Sven bei BotFather. Dazu
  **Befund 108**: ein Telegram-Zugang steht im Klartext im Quelltext,
  auch in v7. Der gehört heraus **und** der Token neu gezogen.
