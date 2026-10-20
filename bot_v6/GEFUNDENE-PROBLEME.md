# Gefundene Probleme — Liste zum Abarbeiten

**Der Rundgang ist komplett — jeder Ordner im Projekt einmal durchgesehen**
(11 ursprüngliche Runden + Runde 12–14 für `docs/`, `scripts/`, `tests/`,
`v4_referenz/`, Archive). Diese Liste ist die Grundlage für die
Reparatur. Kein offener Bug greift ins Geld ein (sonst stünde das fett
dabei) — das war die Voraussetzung dafür, dass alles liegen bleiben
durfte, bis wirklich alles gesichtet war.

Jeder Eintrag: was ist kaputt/unvollständig, wo genau, warum es zählt.

---

## Aus Runde 4 — `execution/`

### 1. `futures_trader.py` + `multi_exchange.py` sind angeschlossen, aber tot

Beide werden beim Start verbunden, aber keine Kaufentscheidung ruft sie
je zum echten Handeln auf — nur `get_status()` fürs Dashboard.
**Wo:** `app.py:3394` (futures.connect), `execution/multi_exchange.py`.
**Warum wichtig:** Wirkt wie eine aktive Funktion, ist aber Attrappe.
Entweder fertig verdrahten oder als „geplant, noch nicht aktiv"
kennzeichnen.

### 2. `execution/exchange_client.py` wird von nirgends importiert

Kein `.bak`-Name, sieht aus wie aktiver Code. `engine.py` verbindet sich
stattdessen direkt über `ccxt`.
**Wo:** `execution/exchange_client.py`.
**Warum wichtig:** Verwirrend beim Suchen/Ändern — vermutlich ein
überholter erster Anlauf.

---

## Aus Runde 5 — `agents/` + `models/`

### 3. ✅ BEHOBEN (11.08. abends) — Meta-Voting-Gewicht wird berechnet, aber nie gelesen

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 4. ✅ BEHOBEN (11.08. abends, Notizbuch-Modus) — ML-Baustelle: vier Modelle ohne Anschluss

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 5. `bottom_detection.py` wird nie ausgewertet

`BottomDetector` wird beim Start gebaut (sogar doppelt, siehe Fund #7),
aber `evaluate()` — die einzige Methode, die etwas berechnet — ruft im
gesamten Projekt niemand auf.
**Wo:** `features/bottom_detection.py`, gebaut in `app.py:221`+`236`.
**Warum wichtig:** Toter Baustein, wie #4 — nur kleiner.

### 6. `market_regime.py` enthält eine verwirrende Namens-Dopplung

Eine zweite, komplett unabhängige `RegimeDetector`-Klasse — mit exakt
demselben Namen wie die echte in `features/regime_detection.py` — und
nirgends importiert.
**Wo:** `features/market_regime.py` vs. `features/regime_detection.py`.
**Warum wichtig:** Kein aktiver Bug, aber ein Stolperdraht: ein
versehentlicher Import von der falschen Datei würde ein anderes
Verhalten liefern, ohne dass ein Fehler auftaucht. Sollte umbenannt oder
entfernt werden.

### 7. `BottomDetector` und `PortfolioRebalancer` werden beim Start doppelt gebaut

Bereits in Runde 1 vermerkt: zwei wortgleiche Init-Blöcke in `app.py`
(Zeile 219–225 und 234–248). Ändert nichts am Verhalten (zweites
Exemplar überschreibt das erste), ist aber unnötiger Code.
**Wo:** `app.py:219-248`.

---

## Aus Runde 7 — `data/`

### 8. Trend-Ausstieg wirkt technisch nur für BTC

`multi_tf`-Analyse läuft laut `app.py:2082` nur für `coins[:1]` (BTC).
Die Regel selbst steht seit 10.08. im Notizbuch-Modus
(`TREND_EXIT_SCHATTEN = True` in `runtime/exit_monitor.py:24`) — **aktuell
folgenlos fürs Geld**, muss aber behoben sein, bevor die Regel je wieder
scharf geschaltet wird.
**Wo:** `app.py:2082`, `runtime/exit_monitor.py:24`.

### 9. Töpfe Schritt 3 offen

Positionen sind weiterhin nach Coin-Symbol geführt, nicht nach
`position_id`. Mehrere gleichzeitige Positionen in derselben Münze sind
deshalb nicht möglich. Plan steht im `ENTWICKLERHANDBUCH.md`.

---

**Stand 11.08.2026 abends — vollständiger Voll-Abgleich inkl. `docs/`
abgeschlossen, Reparatur-Phase läuft parallel weiter.** 24 Punkte
(16 aus dem ursprünglichen Rundgang, 5 beim Reparieren neu gefunden,
3 beim `docs/`-Abgleich neu gefunden).

| | Punkt | Stand |
|---|---|---|
| ✅ | 3 — Meta-Voting-Wert wurde verworfen | behoben, 50/50-Mischung |
| ✅ | 4 — ML-Baustelle (+ 3 versteckte Fehler) | behoben, Notizbuch-Modus |
| ✅ | 19 — Zeitreihe schrieb 19 leere Zeilen | behoben, eine Zeile |
| ✅ | 20 — tote Quellen als Messwert aufgezeichnet | behoben, NULL statt Wert |
| ✅ | 21 — Papier-Gebühren 2,5-fach zu billig | behoben, echte Bybit-EU-Gebühr |
| ✅ | 11 — Drei-Stufen-Schalter nicht angeschlossen | behoben, `trend_exit` bleibt SHADOW |
| ✅ | 24 — Ist-Slippage nicht im Journal | behoben, drei fehlende Schreibpfade |
| ✅ | 28 — keine Sicherung außerhalb | **erledigt**: Git + OneDrive-Kopie (854 MB, DB-Abzüge geprüft) |
| ✅ | 29 — Reddit tot seit 29.07. | **entschieden**: stillgelegt, Code behalten |
| ✅ | 12 — `balance_reporter(12).py` Geister-Duplikat | mit archiviert |
| ✅ | 25 — gefährliches Metals-Skript | archiviert **und** 116 verlorene Zeilen zurückgeholt |
| ✅ | Aufgabe 4 — Aufräumen | 70 Dateien archiviert, Begründungen vorher gerettet |
| 🟡 | 17 — `technical` hängt fest auf 0,5 | gemessen, Notizbuch läuft, Entscheidung offen |
| ✅ | 30 — Wächter hält tote Quelle nach Neustart kurz für gesund | behoben, `hat_gemeldet()` |
| ✅ | 18 — ML-Trainingsdaten verdorben | behoben; Neutraining steht aus |
| ⬜ | 22 — USDT-Rückfall unter MiCA sinnlos | offen, aktuell folgenlos |
| ✅ | 23 — Slippage-Annahme ignoriert Münz-Unterschiede | behoben, gemessene Tabelle je Münze |
| ✅ | 13 — Handkauf umgeht Risk **und** Stop-Wächter | **entfernt** 13.08.; Verkauf bleibt |
| ✅ | 14 — Webhook Port 5051 | **stillgelegt** 13.08.; war offen im Heimnetz, ohne Passwort |
| ✅ | 32 — `_manual_sell` erzeugt Geisterposition | **behoben** 13.08.; zwei Wege, Teilverkauf abgelehnt |
| ✅ | 33 — Web-Dashboard lieferte immer HTTP 500 | **behoben** 13.08.; hatte seit dem 1. Commit nie funktioniert |
| ✅ | 34 — Start ohne Sicherungsbauteile | **behoben** 13.08.; Startabbruch statt Warnzeile |
| ✅ | 35 — „data_store löschen" als Standardrat | **behoben** 13.08.; an zwei Stellen |
| ⬜ | 1, 2, 5–10, 15, 16 | offen (11 und 12 sind erledigt, siehe oben) |
| ⬜ | 8, 9 | offen, aus früheren Sitzungen |

**Drei Messgeräte laufen jetzt mit** (alle geeicht, alle ohne Einfluss
aufs Geld): `ml_notizbuch_auswertung.py`,
`ensemble_notizbuch_auswertung.py` und die reparierte Marktdaten-Zeitreihe.
Sie brauchen Zeit — frühestens in ein bis zwei Wochen sind sie
aussagekräftig.

**Korrektur vom 13.08.2026 zu diesem Absatz:** Die frühere Einschätzung
„Punkt 13 ist eine Design-Entscheidung, kein Fehler, Punkt 14 eine reine
Kenntnisnahme" war **zu milde**. Beim Nachprüfen stellte sich heraus: Der
Handkauf ließ die Position komplett aus der Stop-Überwachung fallen
(kein SL, kein TP, kein Trailing), und der Webhook war ohne Passwort im
ganzen Heimnetz erreichbar. Beides ist am 13.08. geschlossen worden.

**Weiterhin gilt:** kein offener Punkt beeinflusst das laufende
Papier-Trading von selbst — sie brauchen alle einen Auslöser von außen.

**Achtung:** Die Fixes für 3 und 4 sind im Code, aber **noch nicht
aktiv** — der Bot lädt seinen Code beim Start. Neustart ist bewusst
aufgeschoben, bis mehr Punkte fertig sind.

---

## Neu gefunden am 18.08.2026

### 10. Fünf Dateien im Datenordner ohne jeden Anschluss

`cache.py` und `data_quality.py` werden nur in `tests/test_data.py`
referenziert — `market_data.py` hat seine eigene, einfachere Cache-Logik
eingebaut und nutzt beide nicht. `dxy_filter.py` und `news_data.py`
werden nur von einem Forschungs-Skript benutzt
(`docs/messungen_2026-07/code/messung_f2_ic.py`), nicht vom Bot.
`top_coins.py` hat außer sich selbst **keine einzige** Fundstelle im
ganzen Projekt.
**Wo:** `data/cache.py`, `data/data_quality.py`, `data/dxy_filter.py`,
`data/news_data.py`, `data/top_coins.py`.
**Warum wichtig:** Kein Bug, aber fünf weitere Dateien, die wie aktiver
Code aussehen und keiner sind — besonders `dxy_filter.py` neben dem
aktiven `dxy_monitor.py` ist eine Verwechslungsfalle beim Suchen.

---

## Aus Runde 8 — `core/`

### 11. ✅ BEHOBEN (11.08. nachts) — Der Drei-Stufen-Schalter ist an nichts angeschlossen

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 12. ✅ BEHOBEN (12.08.) — `balance_reporter(12).py` ist ein Geister-Duplikat

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 13. ✅ BEHOBEN (13.08.) — Manueller Kauf im „Manuell"-Reiter umgeht alle Risk-Prüfungen

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 14. ✅ BEHOBEN (13.08.) — Der TradingView-Webhook (Port 5051) ist ein unauffälliger zweiter Kaufweg

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 15. `hyperopt.py` ist gebaut, aber nicht im Einsatz

Wie schon mehrfach gesehen (Punkte 1, 4): `app.py` liest nur
`hyperopt.get_status()`, ruft aber nie eine echte Optimierung auf.
**Wo:** `backtest/hyperopt.py`.
**Warum wichtig:** Klein, reiht sich in die Liste der „gebaut, nicht am
Steuer"-Funde ein — kein eigenständiges Problem, aber der Vollständigkeit
halber notiert.

**Keine neuen echten Probleme sonst in dieser Runde** — `daily_loss.py`
läuft sogar aktiv und wie vorgesehen, `optimizer.py` ist absichtlich
stillgelegt (Teil 4.6), das ist beides in Ordnung.

---

## Aus Runde 11 — Hauptordner + `config/`, `live/`, `reports/`, `metals/`

### 16. Drei weitere verwaiste Dateien in `reports/`

`trade_journal.py` enthält eine zweite, ungenutzte `TradeJournal`-Klasse
neben der echten in `core/state_store.py` (Runde 8) — gleicher Name,
anderer Inhalt, wie schon bei `market_regime.py` (Fund #6).
`daily_report.py` und `weekly_report.py` sind ebenfalls verwaist — die
echten Tages-/Wochenberichte laufen über `TelegramReporter`s eigene
Methoden (`runtime/reporting.py`).
**Wo:** `reports/trade_journal.py`, `reports/daily_report.py`,
`reports/weekly_report.py`.
**Warum wichtig:** Dritter Fall derselben Namens-Dopplungs-Falle wie
Fund #6 — beim Suchen nach „TradeJournal" landet man leicht in der
falschen, toten Datei.

**Keine weiteren neuen Bugs in Runde 11** — der Rest sind Werkzeuge,
Belege und bereits erledigte Install-Skripte, die per Konstruktion
nichts am laufenden Handel ändern.

---

## Neu gefunden am 11.08. abends, bei der Reparatur von Punkt 3 und 4

### 17. 🟡 GEMESSEN, NOCH NICHT SCHARF (11.08. abends) — `raw_scores["technical"]` hängt fest auf 0,5

In `app.py:2130` steht `"technical": 0.5` mit dem Kommentar „Wird pro
Coin ueberschrieben". **Wird es nicht.** `self.ensemble.calculate()`
läuft **einmal vor** der Münz-Schleife, der Wert ist für alle Coins
derselbe und bewegt sich nie.
**Wo:** `app.py:2130` (Kommentar), `app.py:2149` (Berechnung vor der
Schleife), `app.py:2173` (Schleifenbeginn).
**Warum wichtig:** „technical" hat in `ensemble_signal.py` das größte
Einzelgewicht (30 % von 73 vergebenen Prozentpunkten = **rund 41 %** des
Ensemble-Werts, mehr wenn Quellen ausfallen). Ein gutes Drittel bis
knapp die Hälfte des Werts, der in die Kaufentscheidung einfließt, ist
damit eine feste 0,5. Der Kommentar behauptet das Gegenteil — genau die
Sorte stiller Fehler, die beim Lesen nicht auffällt.

**Nachgemessen mit den echten Werten des Bots** (Fear & Greed 29,
Onchain 0,65): Ensemble liegt bei **0,566**. Der Bonus zählt erst ab
0,65. Die festgenagelte 0,5 verwässert also nicht nur — sie **deckelt**
den Wert in einem bullischen Moment unter die Schwelle. Das Ensemble ist
als Eingang in die Kaufentscheidung praktisch tot.

**Warum nicht einfach repariert:** Zwei Gründe, beide gegen einen
Schnellschuss.
1. Ein echter Wert weckt den Bonus zum Leben — Käufe würden **leichter**
   ausgelöst (ab 0,65 gibt es +1, ab 0,75 sogar +2 Punkte, bei einer
   Kaufschwelle von 3).
2. **Doppelzählung:** `signal_agent` bewertet RSI, MACD und Bollinger
   bereits direkt mit eigenen Punkten — dieselben Indikatoren zählten
   über das Ensemble ein zweites Mal.

**Outcome (Zwischenstand):** Technischer Wert gebaut
(`app.py:_technischer_wert`, an der Code-Vorgabe „RSI, MACD, Bollinger"
entlang, an drei bekannten Fällen geprüft: 0,833 / 0,500 / 0,167) und im
**Notizbuch-Modus** angeschlossen (`app.py:_ensemble_notizbuch`, je Coin
und Stunde). Festgehalten wird die entscheidende Frage: *wäre der Bonus
anders ausgefallen?* Messwerkzeug: `ensemble_notizbuch_auswertung.py`
(geeicht mit 120 erfundenen Notizen, davon 30 abweichend — es meldete
genau 30). Handbuch-Eintrag: Teil 4.10.
**Offen bleibt die Entscheidung:** scharf schalten ja/nein, sobald genug
Notizen da sind (mindestens 100).

### 18. ✅ BEHOBEN (12.08.) — Die ML-Trainingsdaten sind verdorben (Coin-Grenzen)

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 19. ✅ BEHOBEN (11.08. abends) — Die Marktdaten-Zeitreihe schrieb 19 leere Zeilen

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 20. ✅ BEHOBEN (11.08. abends) — Tote Quellen wurden als Messwert aufgezeichnet

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 21. ✅ BEHOBEN (11.08. abends) — Papier-Trading rechnete mit 2,5-fach zu billigen Gebühren

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 22. USDT-Rückfall in `market_data.py` ist unter der Zielbörse sinnlos

`data/market_data.py:54` fällt bei fehlendem USDC-Paar auf USDT zurück.
Bybit EU (die beschlossene Zielbörse, Teil 4.11) führt unter MiCA
**keine** USDT-Paare — nur USDC, EUR, PLN (per API verifiziert vom
Forschungsprogramm, 133 Spot-Paare gescannt, 0 USDT). Der Rückfall
liefe dort ins Leere, ohne Fehler zu werfen.
**Wo:** `data/market_data.py:54`.
**Warum wichtig:** Aktuell folgenlos, weil Kursdaten weiter von Binance
kommen (Teil 4.11) — Binance hat USDT-Paare. Wird erst zum Problem, wenn
Kursdaten je auf Bybit umgestellt werden. Kein akuter Bug, aber eine
stille Falle für später — am besten vorher entfernen oder auf den
Bybit-Kurs ummünzen.

### 23. ✅ BEHOBEN (12.08.) — Slippage-Annahme im Papierhandel ignoriert riesige Unterschiede zwischen Münzen

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 24. ✅ BEHOBEN (12.08.) — Ist-Slippage wird berechnet, aber nie ins Journal geschrieben

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 25. ✅ BEHOBEN (12.08.) — entschärft UND Code zurückgeholt — `update_metals_indikatoren.py` ersetzt Dateien, statt sie zu patchen

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 26. KORREKTUR (kein Bug) — zwei Hauptordner-Dateien sind aktiver Bot-Code

In Runde 11 als „Skripte" eingeordnet, tatsächlich vom laufenden Bot
importiert:
- **`regime_filter.py`** → `app.py:905`. Blockiert **aktiv neue Käufe**
  bei bestätigtem Abwärtstrend (Stand: `enabled: true`,
  `min_confirmations: 3`). Bildet zusammen mit
  `config_regime_filter.json` (live editierbar),
  `features/regime_adaptiv.py` (Teil 1.5) und `regime_filter_messung.py`
  ein System über zwei Ordner hinweg.
- **`chartanalyse_backtest.py`** → `features/chartanalyse_agent.py:96`.
  Teil des täglichen Agenten-Laufs, kein reines Zuruf-Werkzeug.
**Warum wichtig:** Beide sehen im Hauptordner zwischen 150 Dateien wie
Werkzeuge aus. Wer `regime_filter.py` für ein Analyse-Skript hält und
löscht, schaltet eine der schärfsten Kaufbremsen ab. Im Handbuch
korrigiert (Runde 16).

### 27. ✅ ENTSCHIEDEN (11.08. nachts) — Situations-Gedächtnis wird nicht angeschlossen

Behoben 11.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 28. ⚠️ GRÖSSTES EINZELRISIKO — keine Sicherung außerhalb dieses Rechners

Kein Versionsverwaltungssystem (kein Git), kein externes Backup, keine
Kopie in der Cloud. Steht wörtlich auch in der Forschungs-Dokumentation
(`docs/messungen_2026-07/README.md`): „Es gibt keine Kopie außerhalb
dieses Rechners. Ein Festplattenfehler löscht Messung und Beleg
gleichzeitig."
**Betrifft:** das gesamte Projekt — sieben Monate Arbeit, 2.511 Dateien,
alle Messreihen, alle Belege, beide Handbücher.
**Warum es hier steht:** Es ist kein Code-Fehler, aber das mit Abstand
größte Risiko im Projekt. Jeder andere Punkt dieser Liste ist reparabel;
dieser nicht.
**Naheliegende Abhilfe (unentschieden, Sven entscheidet):** eine Kopie
des Ordners auf eine externe Festplatte, und/oder ein lokales Git-Repo,
damit Änderungen nachvollziehbar bleiben. Beides ändert nichts am
laufenden Bot.

**🟡 ZUR HÄLFTE ERLEDIGT (11.08. abends).**

**Erledigt — Git:** Lokales Repository angelegt, erster Commit mit 559
Dateien (9 MB). Enthalten sind Code, beide Handbücher, Doku und die
Auswertungs-Skripte. Vor dem Commit zweimal der gesamte vorgemerkte
**Inhalt** nach Geheimnissen durchsucht (nicht nur die Dateinamen) —
sauber. `.env` mit dem Telegram-Token ist per `.gitignore` ausgeschlossen;
einmal committet stünde ein Geheimnis für immer in der Historie. Nichts
wurde hochgeladen, alles rein lokal.

**Bewusst NICHT im Git:** Datenbanken, Protokolle, Modelle und die
671 MB Orderbuch-Aufzeichnungen. Git ist kein Backup für Binärdaten, die
sich stündlich ändern oder nie — das bläht die Historie auf, ohne etwas
zu sichern.

**⬜ Offen — die Datenkopie.** Und das ist der Teil, der gegen den
Plattenausfall hilft: Das Git liegt **auf derselben Platte**. Geprüft:
Es ist **keine externe Platte angesteckt** — nur `C:` (interne SSD,
120,7 GB frei) und `D:` als leeres CD-Laufwerk.

Werkzeug ist gebaut und getestet: `python sicherung.py D:\ziel` spiegelt
das ganze Projekt inklusive Git und der ausgeschlossenen Daten; beim
zweiten Lauf werden nur Änderungen übertragen. Der Selbstschutz gegen ein
Ziel innerhalb des Projektordners ist geprüft.

**Solange das nicht passiert ist, bleibt dieser Punkt offen** — und
Aufgabe 4 (Aufräumen von 240 Dateien) darf laut Arbeitsanweisung nicht
anfangen.

---

**🔴 RÜCKFALL DURCH DEN UMZUG (02.09.2026) — beide Hälften sind wieder weg. SICHER.**

Dieser Punkt war erledigt (Git seit 11.08., OneDrive-Kopie 854 MB — siehe
Zeile 106 dieser Liste). **Auf dem neuen Rechner ist beides nicht vorhanden.**

| Was | alter Rechner | dieser Rechner (geprüft 02.09. 20:57) |
|---|---|---|
| Git-Repository | seit 11.08., 559 Dateien | **fehlt** — kein `.git` im Projektordner |
| OneDrive-Kopie | 854 MB | **leer** — `~/OneDrive` enthält nur `desktop.ini` |
| zweite Platte | keine | **keine** — nur `C:` (186 GB frei von 231 GB) |

*Wie geprüft:* `ls -d .git` (nicht vorhanden), Inhalt von
`C:\Users\<BENUTZER>\OneDrive` (eine Datei, 103 Bytes),
`Win32_LogicalDisk` (ein einziges Laufwerk).

**Warum das schwerer wiegt als am 11.08.:** Damals war es ein Versäumnis.
Jetzt ist es ein **Rückfall**, der niemandem auffällt, weil `sicherung.py`
im Kopftext weiterhin behauptet, der Code liege in einem Git-Repository —
das gilt für den alten Rechner, nicht für diesen. Wer die Datei liest,
hält sich für gesichert.

**Was noch da ist:** Der alte Rechner läuft weiter und hat Git und
OneDrive-Kopie. Solange er lebt, ist nichts verloren. Die Daten **dieses**
Rechners ab dem 01.09. — die gesamte Messung im laufenden Fenster — hängen
aber an einer einzigen Platte ohne jede Kopie.

**Warum das den Freeze nicht bricht:** Eine Sicherung liest und kopiert.
Sie ändert kein Bot-Verhalten und braucht keine Epochengrenze. Sie fällt
unter die ausdrückliche Ausnahme „Kapital- oder Datenverlustrisiko"
(CLAUDE.md Abschnitt 5).

**Werkzeug ist da, Ziel fehlt.** `sicherung.py` ist gebaut und getestet.
Es braucht ein Ziel außerhalb von `C:` — externe Platte, USB-Stick oder ein
eingerichtetes OneDrive. **Das ist eine Entscheidung für Sven**, keine, die
sich im Code treffen lässt.

**✅ ERLEDIGT 03.09.2026 — die Sicherung steht und ist nachgezählt.**

Nach dem Umzug nach `C:	rading_imperium_v6(21)` wurde die geplante Aufgabe
`TI6-Wochensicherung` angelegt (sonntags 04:00, `sicherung.py` nach
`OneDrive	rading_imperium_sicherung`). Erster Lauf am 03.09. um 21:00,
Dateikopie in 75,9 Sekunden.

**Nicht nur `quick_check`, sondern gezählt** — genau der Fehler, der heute
schon einmal passiert ist (eine leere Datenbank besteht `quick_check`):

| in der Sicherung | Zeilen | im Betrieb |
|---|---|---|
| `telemetrie.db` | 1.135.690 | 1.135.617 |
| `positionsverlauf.db` | 68.796 | 68.774 |
| `trades_v5.json` | 1145 Trades | 1145 |
| `.env` (Telegram-Token) | **nicht enthalten** | — |

Die Abzüge sind jeweils etwas größer als der Betriebsstand, weil der Bot
während der Sicherung weiterlief — genau dafür zieht `sicherung.py` saubere
SQLite-Abzüge statt roher Dateikopien.

**Offen bleibt eine Kleinigkeit:** Die Sicherung ist mit 4,09 GB und 12.621
Dateien doppelt so groß wie nötig, weil `_onedrive_konflikte` mitgesichert
wird (6.156 beiseitegelegte Dateien plus eine 449-MB-Altfassung der
Telemetrie). Sobald klar ist, dass beim Aufräumen am 03.09. nichts
Wichtiges verlorenging, kann diese Ablage weg — dann schrumpft die
Sicherung um rund 1,5 GB.


### 29. ✅ ENTSCHIEDEN (12.08.) — Reddit ist seit 29.07. tot

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 30. ✅ BEHOBEN (12.08.) — Quellen-Wächter hält eine tote Quelle nach dem Neustart kurz für gesund

Behoben 12.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 32. ✅ BEHOBEN (13.08.) — `_manual_sell` erzeugt eine Geisterposition

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 33. ✅ BEHOBEN (13.08.) — Das Web-Dashboard hat noch NIE funktioniert

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 34. ✅ BEHOBEN (13.08.) — Startabbruch statt Weiterlaufen ohne Sicherungen

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 35. ✅ BEHOBEN (13.08.) — „Lösche den Ordner data_store" als Standardrat

Behoben 13.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 36. ✅ BEHOBEN (18.08.) — Ticket-Kanal stand still; Ursache unbekannt, aber nicht mehr unsichtbar

Behoben 18.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 37. ✅ BEHOBEN (18.08.) — Der Scheduler verschluckt Fehler lautlos

Behoben 18.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 38. ✅ BEHOBEN (18.08.) — Jeder Verkauf meldet sich zweimal in Telegram

Behoben 18.08.. Voller Text: → `archiv/GEFUNDENE-PROBLEME_behoben.md`

### 39. Zwei Indikatoren messen die Uhrzeit statt den Markt


**Gefunden am 18.08.2026** beim Nachgehen einer Auffälligkeit:
`volume_ratio` hatte den Median **0,0028**, obwohl ein „Verhältnis zum
Durchschnitt" um 1,0 liegen müsste.

**Die Formel ist richtig** (`features/indicators.py:39`,
Volumen ÷ 20-Perioden-Schnitt). Falsch ist, **womit** verglichen wird:

> Der Zähler ist das Volumen der **noch laufenden** Kerze, der Nenner
> der Durchschnitt **abgeschlossener** Kerzen.

Alle 380 Schnappschüsse tragen `kerze_offen = 1`, und 345 davon
entstehen in den ersten zehn Minuten der Stunde — wenn die Kerze also
fast leer ist.

| Minute der Stunde | Fälle | `volume_ratio` | `high_low_range` |
|---|---|---|---|
| 0–9 | 345 | 0,0020 | 0,00006 |
| 10–19 | 1 | 0,1774 | 0,00074 |
| 20–29 | 10 | 0,3957 | 0,00190 |
| 30–39 | 9 | 0,5344 | 0,00319 |
| 40–49 | 6 | **1,1737** | **0,00600** |
| 50–59 | 9 | 0,6165 | 0,00369 |

**Beide Spalten messen die verstrichene Zeit, nicht den Markt.** Zwischen
Stundenanfang und -ende liegt Faktor 100.

### Drei Folgen, absteigend nach Gewicht

**1. Eine Punktregel, die nie feuert.** `models/signal_model.py:53`:

```python
if vol_ratio > 1.5: score += 0.15   # "Volume hoch"
```

Bei einem Median von 0,002 wird dieser Punkt **praktisch nie** vergeben.
Er steht seit jeher im Regelwerk und hat vermutlich noch nie gewirkt.

**2. Trainings-Bruch beim KI-Modell — geprüft und bestätigt.**
`models/xgboost_model.py:106` wählt für die Vorhersage
`df_or_row.iloc[-1]` — im Betrieb also die **offene** Kerze. Trainiert
wird auf Kursverläufen, deren Zeilen **abgeschlossene** Kerzen sind.

| Merkmal | im Training | im Betrieb (Minute 0–9) |
|---|---|---|
| `volume_ratio` | um 1,0 | **0,002** |
| `high_low_range` | um 0,006 | **0,00006** |

Zwei von dreizehn Merkmalen liegen im Einsatz also **außerhalb des
Bereichs**, den das Modell je gesehen hat. Was es daraus macht, ist
nicht vorhersagbar — es hat für diese Werte keine gelernte Erfahrung.
Das entwertet die Vorhersage nicht zwingend, aber es macht sie
unberechenbar, und niemand hat es je bemerkt.

**3. Auswertungen über diese Spalten sind wertlos**, solange sie nicht
nach der Minute getrennt werden. In `merkmale_auswertung.py` ist
`volume_ratio` deshalb ausdrücklich mit diesem Vorbehalt versehen.

### Was NICHT falsch ist

Dass Indikatoren auf der laufenden Kerze rechnen, ist im Livebetrieb
**normal und unvermeidlich** — man muss entscheiden, bevor die Stunde
vorbei ist. RSI, EMA, MACD und ADX arbeiten mit dem aktuellen Kurs und
sind davon kaum betroffen.

Betroffen sind nur die Merkmale, die eine **Summe über die Kerze**
bilden: Volumen und Spanne. Sie wachsen mit der Zeit und sind deshalb
nur vergleichbar, wenn man entweder

- die **letzte abgeschlossene** Kerze nimmt, oder
- auf den verstrichenen Anteil hochrechnet (Volumen bisher ÷ erwarteter
  Anteil).

> **Eine Summe, die noch wächst, darf nicht gegen fertige Summen
> verglichen werden.** Der Fehler ist unsichtbar, weil das Ergebnis eine
> plausible Zahl ist — nur eben eine Zahl über die Uhr.

**Reparatur:** ändert den Score, also Handelspfad — **nach dem 27.08.**

---

## Neu gefunden am 19.08.2026 — Tiefen-Audit, Etappe 1 (Handelskette)

### 40. Der Pfad mit 98 % der Käufe läuft an der zentralen Risikoprüfung und der Telemetrie vorbei

Es gibt zwei Kaufwege. Der DCA-Pfad (`fg < 30`) macht **538 von 547
Käufen (98,4 %)**, der Signal-Pfad 9. Alle Werkzeuge messen den
Signal-Pfad.

**Wo:** DCA-Block `app.py:2700–2996`, Signal-Pfad `app.py:1129–1221`.

**Dreifach belegt:**
- `grep -n "risk_engine.check(" app.py` → **genau ein** Treffer:
  `app.py:1206`. Der DCA-Block ruft sie nie.
- `_telemetrie_schreiben` an sechs Stellen (1010, 1048, 1067, 1116, 1196,
  1214) — **alle** im Signal-Pfad, keine im DCA-Block.
- Zwei unabhängige Quellen stimmen überein: `telemetrie.db` kennt seit
  dem 06.08. genau 9 angenommene Käufe, `trades_v5.json` genau 9
  Signal-Käufe — auf die Minute dieselben. Die 4 DCA-Käufe im selben
  Zeitraum fehlen in `evaluations` vollständig.

**Warum wichtig:** 188.955 protokollierte Ablehnungen beschreiben den Weg
mit 1,6 % der Käufe. Vom Hauptweg existiert keine einzige protokollierte
Entscheidung. Jede Aussage der Form „der Bot lehnt ab, weil …" gilt
derzeit nur für einen Nebenpfad.

**Nicht ungeprüft, aber anders geprüft:** Der DCA-Pfad hat seit dem 29.07.
eigene Tore (Kill-Switch, Schlafmodus, Drawdown, Modus-Sperre, Cooldown,
Nachkauf-Grenze, Exposure, Wiedereinstiegs-Sperre). Es fehlt dort vor
allem der **Regime-Filter** — die Regel, die im Signal-Pfad rund 68.000
Käufe abgelehnt hat.

**Verwandt mit Punkt 13** (manueller Kauf umgeht `risk_engine.check()`,
`ui/main_window.py:1366`). Dasselbe Muster an einer zweiten Stelle: ein
Kaufweg, der an der zentralen Prüfung vorbeigeht. Punkt 13 betrifft einen
Handgriff, dieser hier 98 % des automatischen Handels.

**Priorität:** HOCH. Reine Protokollierung wäre Freeze-sicher; den
Regime-Filter nachzuziehen wäre eine Verhaltensänderung → nach dem 27.08.

### 41. `entry_score` ist auf dem DCA-Pfad immer leer — der Fix vom 10.08. greift nicht

`app.py:2971` setzt den Einstiegs-Score über eine Variable, die es nicht
gibt:

```
getattr(_dca_intent, "score", None) if "_dca_intent" in dir() else None
```

Die Variable heißt an dieser Stelle `intent`.
`grep -c "_dca_intent = " app.py` → **0 Treffer**. Die Bedingung ist
immer falsch.

**Belegt in den Daten:** 0 von 220 Verkäufen in `trades_v5.json` haben
einen `entry_score`, ebenso 0 eine `entry_strategie`.

**Entwarnung:** `telemetrie.db` führt den Score getrennt mit
(`evaluations.score`, 188.965 von 188.976 Zeilen befüllt, Bereich 3–12,
Ø 7,09). TODO-Punkt 3 („Ist Score 8 besser als Score 6?") bleibt also
beantwortbar — nur nicht über die Journaldatei.

**Priorität:** MITTEL. Einzeilig, aber Verhaltensänderung an einer
Schreibstelle → mit der nächsten Epochengrenze.

### 42. Ergänzung zu Handbuch 4.50: die Doppelbuchung gilt nur im Papiermodus

**Das meiste hier war schon bekannt.** Handbuch **4.50** (18.08.) nennt die
Ursache bereits Zeile für Zeile, einschließlich
`execution/engine.py:401  result.filled_cost = amount  # Gebühr ist also DRIN`
und der Rechnung am Einzelhandel vom 13./18.08. (Differenz 0,2583 $ =
exakt die Kaufgebühr).

**Neu ist nur ein Punkt** — und der ändert, *wo* repariert werden muss:

Im **Livebetrieb** kommt `filled_cost` nicht aus `amount`, sondern aus
`order["cost"]` von ccxt (`execution/engine.py:546`). In der
ccxt-Einheits-API ist `cost` als `filled × average` definiert, also
**ohne** Gebühr. Dort wäre `filled_cost + fee` **richtig**.
**[WAHRSCHEINLICH]** — nicht am lebenden Objekt geprüft, weil kein
Live-Zugang besteht.

**Folge:** Wer nur die Addition in `app.py:1861/2933` entfernt, repariert
den Papiermodus und macht den Live-Pfad kaputt — und würde es nicht
merken, weil im Papiermodus getestet wird. Der sichere Ort ist
`engine.py:401` (`filled_cost = amount - fee`), damit beide Betriebsarten
dasselbe bedeuten. **Vorher muss das ccxt-Verhalten belegt werden.**

**ERGAENZUNG 21.08.2026 — jetzt beziffert.** Der Befund war seit dem 18.08.
beschrieben, aber nie in Zahlen gefasst. Gemessen an 95 Verkaeufen mit
Volumen und beiden PnL-Feldern:

| Monat | n | Median-Abzug je Runde |
|---|---|---|
| Juli 2026 | 64 | 0,114 % (alte Gebuehrenannahme) |
| **August 2026** | 31 | **0,752 %** |

Sollwert ist K-BASIS **0,505 %** — im August werden also **+0,247
Prozentpunkte je Runde zu viel** abgezogen, fast genau eine halbe Runde
(eine Handelsseite = 0,25 %).

Ueber den Gesamtbestand mittelt sich das weg (Median 0,178 %), weil zwei
Drittel der Faelle aus dem Juli stammen. **Wer nur die Gesamtzahl ansieht,
sieht das Problem nicht.**

Folge fuer die Freischaltung: der Erwartungswert der Epoche E7 liegt
gebucht bei **+0,353 %**, nach K-BASIS gerechnet bei **+0,622 %**. Beide
ueber null — die Verzerrung geht also in die harmlosere Richtung: sie macht
den Bot schlechter als er ist. Eine Freischaltung wird dadurch nicht zu
Unrecht erteilt, hoechstens zu Unrecht verweigert. Handbuch 4.108.

**Priorität:** Diese Ergänzung an Punkt 0a in `OFFEN.md` anhängen. Die
Reparatur selbst bleibt wie bisher geplant nach dem 27.08.

### 43. Zwei verschiedene Cash-Puffer in derselben Funktion

`_execute_approved_trade` deckelt den Kaufbetrag zweimal auf das
verfügbare Geld — mit unterschiedlichen Puffern:

| Stelle | Puffer | Kommentar im Code |
|---|---|---|
| `app.py:~1467` | **2 %** (`free_cash * 0.98`) | „2% Puffer fuer Fees/Slippage" |
| `app.py:~1583` | **5 %** (`_free_cash * 0.95`) | „5% Buffer fuer Slippage/Fees" |

Beide begründen sich mit derselben Sache. Der zweite gewinnt immer, weil
er später läuft — der erste ist damit wirkungslos, außer er lehnt ganz ab
(`buffer < 5`).

**Warum wichtig:** Nicht gefährlich, aber es sind zwei Wahrheiten für
dieselbe Frage. Wer eine davon ändert, ändert nichts — ein Fallstrick für
die nächste Anpassung.

**Priorität:** LOW.

### 44. `total_equity` bedeutet je nach Schreibstelle zwei verschiedene Dinge

In `evaluations.total_equity` landen zwei Kapitalbegriffe, die sich um
rund **96 $ bei ~590 $ (16 %)** unterscheiden:

| Stelle | rechnet | Ø Wert |
|---|---|---:|
| `app.py:952` | Cash + Positionen, **ohne** Sparplan-BTC | ~494 $ |
| `portfolio/manager.py:70` (`get_total_capital`) | Cash + Positionen, **mit** Sparplan-BTC | ~591 $ |

Beide Definitionen sind für sich richtig — `app.py:931` begründet den
Ausschluss ausdrücklich („langfristige Akkumulation, darf die
Handelsgröße nicht aufblähen"). Falsch ist nur, dass beide in dieselbe
Spalte schreiben.

**Belegt:** In 35 % von 189.795 Messungen springt der Wert um über 5 %.
Am 07.08. um 00:16 im Sekundenabstand: 595,80 → 498,64 → 595,77 → 498,63,
je nachdem, welche Prüfung gerade schrieb. Die Differenz entspricht dem
Sparplan-BTC (97,82 $ laut `equity_history.json`).

**Blast Radius — nicht nur Anzeige:**
- `app.py:962` gibt `_kapital` an `signal_agent.analyze()` → daraus
  entsteht die **Positionsgröße**
- `app.py:1206` gibt `portfolio["total_equity"]` an `risk_engine.check()`
  → daraus entstehen **Exposure-Grenzen**

Je nach Pfad unterscheidet sich die Bezugsgröße um 16 %. Ob daraus je
eine falsche Ordergröße entstand, ist **noch nicht gemessen** — gehört in
Etappe 2 des Audits.

**Wie es auffiel:** Der erste Drawdown-Lauf meldete 27,36 % und damit
eine verletzte Schmerzgrenze. Die Zahl passte nicht zu den realisierten
Verlusten (−7,34 $ gegen 183,36 $ angeblichen Rückschlag). Nach
Definitionen getrennt: **13,11 %** (mit Sparplan) und **3,64 %** (ohne) —
beide im Ziel.

**Vorschlag zur Diskussion (nicht umgesetzt):** Zwei getrennte Spalten,
`equity_handel` und `equity_gesamt`, statt einer mehrdeutigen. Ändert
Schreibpfade → Epochengrenze nötig, also nach dem 27.08.

**Priorität:** HOCH für die Auswertung (jede Kennzahl auf dieser Spalte
ist ohne Trennung falsch), MITTEL für den Handel (Wirkung ungemessen).
Handbuch 4.63.

### 45. Die Trailing-Schwelle liegt unter der Rentabilitätsschwelle

Der Trailing-Stop wird ab **+1,2 %** Höchststand scharf
(`risk/exit_rules.py`, `TRAIL_AB_PCT`) und hält **1,0 %** Abstand
(`config.json`, `trailing_stop_pct`). Rentabel wird er erst ab
**+1,520 %**. Dazwischen liegt ein Streifen, in dem jeder Ausstieg
rechnerisch garantiert Verlust macht.

**Die Formel** (mit den echten Funktionen aus `risk/exit_rules.py`
gerechnet):

| Höchststand | Ausstieg bei | netto nach 0,505 % Kosten |
|---:|---:|---:|
| 1,20 % | +0,188 % | **−0,317 %** |
| 1,50 % | +0,485 % | **−0,020 %** |
| 1,52 % | +0,505 % | ±0,000 % |
| 2,00 % | +0,980 % | +0,475 % |

**Die Daten:** 74 von 135 Trailing-Ausstiegen (**55 %**) enden brutto im
Plus und netto im Minus. Zusammen −19,61 Prozentpunkte. Der
Median-Trailing-Ausstieg liegt bei **+0,450 % brutto** gegen 0,505 %
Kosten — der typische Fall dieser Regel verliert.

**Gegenprobe:** Drei Trades hatten ihren Höchststand in der
vorhergesagten Verlustzone. Ergebnis −0,058 % netto im Mittel, während
alle 22 mit Höchststand-Daten +1,691 % erreichten. Vorhersage bestätigt —
bei n=3 aber nur **[WAHRSCHEINLICH]**. Die Formel selbst ist Arithmetik
und damit **[SICHER]**.

**Warum es entstanden ist:** Die Leiter wurde am 29.07. gegen einen echten
Defekt gebaut und war damals richtig — bei Gebühren von 0,10 % je Seite
(Kosten je Runde ~0,32 %). Bei 0,32 % lag die Nulllinie bei 1,33 %, die
Schwelle von 1,2 % war knapp darunter. Seit dem 13.08. sind es 0,25 % je
Seite, Kosten 0,505 %, Nulllinie 1,52 %. **Die Kostenschwelle ist unter
der Regel weggewandert.**

Dieselbe Wurzel wie Punkt 0 in `OFFEN.md` (Breakeven-Puffer) und die
neun alten Kostenkonstanten (Handbuch 4.53).

**Blast Radius:** Der Trailing-Stop ist mit 135 von 220 Verkäufen
(61 %) der häufigste Ausstieg überhaupt.

**Nicht sofort reparieren.** Die naheliegende Korrektur (`TRAIL_AB_PCT`
auf 1,6) hat einen Preis: Wer später ratscht, gibt bei jedem Trade
zwischen 1,2 und 1,6 % den ganzen Gewinn zurück — die Position fällt dann
bis zum Stop-Loss durch. Die Alternative ist nicht „kein Ausstieg",
sondern ein anderer. Genau dafür sammelt seit dem 19.08.
`positionsverlauf.py`. Handbuch 4.64.

**Priorität:** HOCH, aber nach dem 27.08. und erst nach Auswertung der
Positionsverläufe.

### 46. Take-Profit ist abgeschaltet, ohne dass es irgendwo steht

`config.json` führt `take_profit_pct = 0.0`. Der Exit-Monitor prüft ihn
(`elif not sell_reason and tp_pct > 0`), die Bedingung trifft also nie zu.

Möglicherweise Absicht — die Ausstiegsleiter soll den Gewinn laufen
lassen. Steht aber in keinem Dokument. **Priorität:** LOW, aber
klärungsbedürftig: Ein abgeschalteter Mechanismus ohne Begründung ist von
einem vergessenen nicht zu unterscheiden.

### 47. Trailing und Breakeven greifen nur im Modus „SL"

`runtime/exit_monitor.py` prüft die Ausstiegsleiter nur unter
`elif not sell_reason and coin_mode == "SL"`. Hat eine Position einen
anderen Modus, greift weder Trailing noch Breakeven-Sperre — nur der
Stop-Loss.

Ob je ein anderer Modus gesetzt war, ist **ungemessen**. `bot_state.json`
zeigt für beide offenen Positionen `"mode": "SL"`. **Priorität:** LOW
(Beobachtung), aber der Fall gehört geprüft, bevor jemand einen Modus
umstellt.

### 48. Die Exposure-Grenze folgt einem Moduswechsel nur nach oben
`risk/engine.py:323` hebt die Obergrenze für den Anteil eines einzelnen
Coins nach jedem genehmigten Kauf an — und **nur nach oben**:

```
new_max = max(self.config.max_exposure_per_coin_pct,
              intent.amount_usd / total_eq * 100 + 5 if total_eq > 0 else 25)
self.exposure.max_coin_pct = max(self.exposure.max_coin_pct, new_max)
```

Ein `max()` kann nicht sinken. Zurückgesetzt wird der Wert **nur im
Konstruktor** (`risk/engine.py:47`), also erst beim Neustart.

**Der Fall, der zählt — ein Moduswechsel zur Laufzeit:**

| Modus | erlaubter Anteil je Coin |
|---|---:|
| `all_in` | 100 % |
| `btc_only` | **95 %** |
| `balanced` | **35 %** |
| `diversified` | 15 % |

Wechselt der Bot von `btc_only` auf `balanced`, sagt die Konfiguration
35 % — die Engine behält aber 95 %. **Die Verschärfung kommt nicht an,
die Lockerung schon.**

**Genau dieser Wechsel hat stattgefunden:** Epoche `E4_btc_only` ab
07.08. 00:16, `E5_balanced_zurueck` ab 10.08. 04:26.

**Ob es real gewirkt hat, ist [WAHRSCHEINLICH], nicht SICHER** — es hängt
davon ab, ob zwischen den beiden Zeitpunkten ein Neustart lag. Der
Mechanismus selbst ist **[SICHER]**: `max()` geht nur nach oben, und
außerhalb des Konstruktors setzt nichts zurück.

**Warum die Wirkung trotzdem begrenzt ist:** Drei weitere Deckel greifen
davor — `max_open_positions = 3`, die Deckelung auf freies Cash und
`position_size_pct = 30 %`. Eine Position kann also auch bei 95 %
erlaubtem Anteil nicht beliebig groß werden. Der Fehler öffnet eine Tür,
durch die selten jemand geht.

**Warum es trotzdem zählt:** Eine Risikogrenze, die sich nur lockern
lässt, ist keine Grenze. Und der nächste Moduswechsel — etwa auf
`diversified` mit 15 % — würde vollständig wirkungslos bleiben.

**Vorschlag zur Diskussion (nicht umgesetzt):** Beim Moduswechsel
`self.exposure.max_coin_pct` neu aus dem aktiven Modus setzen statt mit
`max()` zu verrechnen. Ändert Verhalten → nach dem 27.08.

**Priorität:** MITTEL · **Risiko** 4/10 · **Aufwand** 2/10 · **Impact** 4/10
Handbuch 4.70.

### 49. Der gesamte Order-Lebenslauf ist im Papiermodus abgeschaltet — und damit unerprobt
Fünf Bausteine sichern den Weg einer Order ab: `RetryPolicy`,
`CircuitBreaker`, `IdempotencyGuard`, `OrderManager`, `FillReconciler`.
Sie sind vollständig gebaut und sauber verdrahtet — **aber drei davon
laufen im Papiermodus nie:**

| Baustein | im Papiermodus | Beleg |
|---|---|---|
| `IdempotencyGuard` | **aktiv** | `engine.py:168-227`, beide Modi |
| `OrderManager` | **aktiv** | `engine.py:209-224`, beide Modi |
| `RetryPolicy` | **inaktiv** | nur `engine.py:508, 591` — Live-Pfad |
| `CircuitBreaker` | **inaktiv** | dieselben zwei Stellen |
| `FillReconciler` | **inaktiv** | `engine.py:575`: `if self._paper_mode or not self.exchange: return []` |

**Beleg aus dem Betrieb:** Der Scheduler ruft `_reconcile` alle 300 s auf
(`app.py:651`). In `data_store/system.log` steht **null** mal `RECONCILE` —
die Funktion kehrt sofort zurück.

**Das ist kein Fehler.** Im Papiermodus gibt es keine Börse zum Abgleichen
und keine Netzwerkfehler zum Wiederholen. Die Rückgabe von `[]` ist
richtig.

**Aber es hat eine Folge, die vor dem Live-Gang zählt:** Der Pfad, der
bei echtem Geld die Sicherheit trägt, ist **nie unter echten Bedingungen
gelaufen**. `tests/test_execution.py` prüft die Bausteine einzeln, nicht
ihr Zusammenspiel mit einer Börse, die zeitweise nicht antwortet.

**Vorschlag zur Diskussion:** Vor dem Live-Gang ein Probelauf gegen das
Testnetz der Börse, bei dem Rate-Limit, Zeitüberschreitung und
Verbindungsabbruch absichtlich provoziert werden. Das ist dieselbe Art
Gegentest, die bei `prozess_frische.py` und `dauercheck.py` Fehlalarme
gefunden hat.

**Priorität:** HOCH **vor dem Live-Gang**, sonst keine.
**Konfidenz:** SICHER (Codepfade belegt).

### 50. `RateLimitExceeded` wartet nach dem letzten Versuch noch bis zu 30 Sekunden
`execution/retry_policy.py`, `execute()`: Der Zweig für
`RETRYABLE_EXCEPTIONS` bricht ordentlich ab —

```
except RETRYABLE_EXCEPTIONS as e:
    if attempt >= self.max_retries:
        raise
```

— der Zweig für `ccxt.RateLimitExceeded` **hat diese Prüfung nicht**. Er
schläft und lässt die Schleife weiterlaufen. Beim letzten Durchgang wird
also noch einmal gewartet, obwohl kein Versuch mehr folgt:

| Versuch | Wartezeit |
|---|---:|
| 0 | 3,0 s |
| 1 | 6,0 s |
| 2 | 12,0 s |
| **3 (letzter)** | **bis 30 s — danach wirft die Schleife** |

**Folge:** Bei anhaltendem Rate-Limit dauert es bis zu 30 Sekunden länger
als nötig, bis der Fehler sichtbar wird. `time.sleep()` **blockiert
dabei den Thread** — bei einem Verkauf unter Zeitdruck (Stop-Loss) ist
das die falsche Sekunde zum Warten.

**Zweiter Punkt derselben Datei:** Der abschließende `except Exception`
wiederholt **jeden** Fehler, auch Programmierfehler wie `TypeError` oder
`KeyError`. Ein Tippfehler im Code führt damit zu vier Versuchen mit
Wartezeit statt zu einem sofortigen, sichtbaren Fehler.

**Minimaler Fix:** dieselbe Abbruchprüfung in den Rate-Limit-Zweig
einsetzen. **Sauberer Fix:** zusätzlich den generischen `except Exception`
auf eine Liste bekannter transienter Fehler einengen.

**Wirkt nur im Live-Modus** — im Papiermodus wird `RetryPolicy` nicht
aufgerufen (siehe Punkt 49).

**Priorität:** MITTEL (HOCH vor dem Live-Gang) · **Risiko** 3/10 ·
**Aufwand** 1/10 · **Impact** 5/10 · **Konfidenz:** SICHER

### 51. ✅ BEHOBEN (19.08.) — Die Wiederherstellung zerstörte beim ersten Live-Start jede Position
**Der schwerste Fund des Audits. Wirkt ausschließlich im Live-Modus, dort
aber sofort und vollständig.**

`live/state_recovery.py` gleicht nach dem Start den lokalen Zustand mit
der Börse ab. Es vergleicht dabei **Asset-Namen mit Symbolen** — zwei
verschiedene Schlüssel:

| Quelle | Schlüssel |
|---|---|
| `fetch_balance()` → `real_positions` | `"ETH"`, `"BTC"` |
| `bot_state.json` → `local_positions` | `"ETH/USDC"`, `"BTC/USDC"` *(nachgeprüft)* |

**Die Kette, Zeile für Zeile:**

```
1) for asset, amount in real_positions.items():
       if asset not in local_positions:        # "ETH" not in {"ETH/USDC"} -> WAHR
           local_positions[asset] = {"qty": amount, "recovered": True}

2) for asset in list(local_positions.keys()):
       if asset not in real_positions:         # "ETH/USDC" not in {"ETH"} -> WAHR
           del local_positions[asset]          # die ECHTE Position wird geloescht

3) self.state.set("open_positions", local_positions)
   self.state.save()                           # und sofort dauerhaft gespeichert
```

**Ergebnis nach dem ersten Live-Start:**
`{"ETH": {"qty": 0.092, "recovered": True}}`

**Was verlorengeht:** `entry_price`, `active`, `cost_basis`,
`highest_price`, `lowest_price`, `hoechst_pnl_pct`, `position_id`,
`entry_score`, `entry_strategie`, `dca_levels`.

**Die Folge ist der eigentliche Schaden.** `runtime/exit_monitor.py:102`
lautet:

```
for sym, pos in list(self.app.risk_engine.open_positions.items()):
    if not pos.get("active"):
        continue
```

Die wiederhergestellten Positionen haben **kein `active`** — sie werden
also übersprungen. **Kein Stop-Loss, kein Trailing, kein Breakeven, kein
Trend-Ausstieg.** Die Position liegt im Depot und wird von niemandem mehr
überwacht.

Und ohne `entry_price` wäre selbst ein manueller Verkauf ergebnislos: Es
gibt keinen Einstand, gegen den gerechnet werden könnte.

**Wann es zuschlägt:** `app.py:4010`, nur wenn
`config.trading.mode == "live"` und die Verbindung steht. Im Papiermodus
wird `StateRecovery` nie aufgerufen — **deshalb ist der Fehler bisher
unsichtbar geblieben.**

**Teilweise bekannt, aber anders:** `app.py:3739` beschreibt bereits, dass
`state_recovery.py` den Papier-Fall *nicht* abdeckt. Der Schlüssel-Fehler
im Live-Fall ist **neu**.

**Blast Radius:** Alle offenen Positionen beim ersten Live-Start.
Zusätzlich wird der falsche Zustand mit `state.save()` sofort
festgeschrieben — ein Neustart heilt ihn nicht.

**Vorschlag zur Diskussion (nicht umgesetzt):**
1. Vergleich über eine einheitliche Schlüsselform (Asset aus dem Symbol
   ableiten: `sym.split("/")[0]`), nicht über zwei verschiedene.
2. Vorhandene Felder **erhalten** statt die Position zu ersetzen —
   `qty` aktualisieren, alles andere behalten.
3. Bei „lokal vorhanden, an der Börse nicht": **nicht löschen**, sondern
   melden und den Handel blockieren, bis ein Mensch entschieden hat. Eine
   Position stillschweigend zu löschen ist die gefährlichste der drei
   möglichen Reaktionen.

**BEHOBEN am 19.08.2026.** `live/state_recovery.py` neu gebaut, drei Regeln:

1. **Einheitlicher Schlüssel** — verglichen wird über das Asset, das aus
   dem Symbol abgeleitet wird (`asset_von("ETH/USDC") -> "ETH"`).
2. **Erhalten statt ersetzen** — bei Übereinstimmung wird nur die Menge
   nachgezogen, alle anderen Felder bleiben.
3. **Nicht löschen, sondern melden** — eine lokal bekannte, an der Börse
   fehlende Position bleibt stehen; stattdessen wird `recovery_blockade`
   im Zustand gesetzt.

Gegentest in **sechs Richtungen** bestanden (`python live/state_recovery.py
--selbsttest`): der Originalfall, abweichende Menge, lokal ohne Börse,
Börse ohne lokal, leere Eingaben, Schlüsselableitung.

**Freeze-sicher**, weil `StateRecovery` nur unter `mode == "live"`
aufgerufen wird und `config.json` `paper` führt — der Pfad ist im
laufenden Betrieb tot. Sicherung:
`live/state_recovery.py.bak_vor_fix51_20260819`.

**Offen geblieben:** `recovery_blockade` wird gesetzt, aber **noch von
niemandem gelesen**. Die Auswertung im Handelspfad wäre eine
Verhaltensänderung und gehört hinter den 27.08. Steht in `OFFEN.md`
Gruppe D.

**Priorität:** **KRITISCH vor dem Live-Gang**, keine im Papierbetrieb.
**Risiko** 9/10 · **Aufwand** 3/10 · **Impact** 10/10 · **Konfidenz:** SICHER
(Codepfade und Schlüsselformen beide nachgeprüft).

### 52. Der Ereignisbus zählt und protokolliert ohne Sperre
`core/bus.py`: `publish()` hält einen Lock für die Abonnentenliste —

```
with self._lock:
    callbacks = list(self._subscribers.get(event_type, []))
```

— aber die beiden Zeilen darüber laufen **ungeschützt**:

```
self._stats[event_type] += 1                       # read-modify-write
self._event_log.append({...})
if len(self._event_log) > self._max_log:
    self._event_log = self._event_log[-self._max_log:]   # Liste wird ERSETZT
```

`publish()` wird aus vielen Threads aufgerufen: Der Scheduler startet
**26 Aufgaben** in eigenen Threads (`core/scheduler.py:86`), dazu
`publish_async()`, das für jedes Ereignis einen weiteren Thread öffnet.

**Zwei Folgen:**
1. `+= 1` ist keine atomare Operation — Zähler gehen verloren. Betroffen
   ist auch `_stats["BUS_ERROR"]`, also ausgerechnet der Fehlerzähler.
2. Die Neuzuweisung von `_event_log` ersetzt das Objekt. Ein gleichzeitig
   laufendes `append` schreibt dann in die alte Liste und ist weg.

**Wie schwer:** Kein Handelsfehler — es geht nur Statistik und
Ereignisprotokoll verloren. Aber genau das wird bei der Fehlersuche
gebraucht, und der Bus hat am 06.08. schon einmal 14.986 verschwundene
Kaufsignale verschleiert (Handbuch, Sichtbarkeits-Reparatur).

**Minimaler Fix:** beide Zeilen in denselben `with self._lock`-Block
ziehen, der ohnehin drei Zeilen später steht.

**Priorität:** MITTEL · **Risiko** 2/10 · **Aufwand** 1/10 ·
**Impact** 4/10 · **Konfidenz:** SICHER

### 53. Kein Alarm, wenn eine Aufgabe chronisch länger braucht als ihr Takt
`core/scheduler.py` überspringt eine Aufgabe, solange sie noch läuft
(`if not self.enabled or self.running: return False`). Das ist richtig —
so kann sich nichts überholen.

**Aber niemand erfährt davon.** Eine Aufgabe mit 12 Sekunden Takt, die 60
Sekunden braucht, läuft faktisch nur alle 60 Sekunden. Die Klasse `Task`
führt `run_count`, `error_count` und `last_error` — **aber keine
Laufzeit**.

Beim Handelstakt wäre das relevant: `_trading_tick` enthält
`time.sleep(0.5)` je Münze plus Netzabrufe. Bei drei Münzen sind das
mindestens 1,5 Sekunden, und niemand misst, wie viel es wirklich ist.

**Vorschlag:** `dauer_sek` je Aufgabe mitführen und melden, sobald sie
das Intervall überschreitet — analog zur Fehlermeldung, die am 18.08.
ergänzt wurde (Punkt 37).

**Priorität:** LOW (Beobachtbarkeit) · **Aufwand** 2/10 · **Konfidenz:** SICHER

### 54. Der Verlustzähler überlebt keinen Neustart — die Cooldown-Sperre greift deshalb nie
**Gefunden in Etappe 5, durch Abgleich von Code und Daten.**

`risk/engine.py` soll nach drei Verlusten in Folge auf einer Münze eine
Pause einlegen (`cooldown_after_losses = 3`). In **12 Tagen Telemetrie
mit 197.511 Kaufprüfungen** steht dazu:

```
Cooldown-Ablehnungen: 0
```

**Und es hätte greifen müssen.** Nach der Bot-eigenen Definition
(`pnl < 0` in Dollar) gab es seit dem 06.08.:

| Münze | längste Verlustserie | zuletzt |
|---|---:|---|
| BTC/USDC | **4** | 12.08. 18:55 |
| SOL/USDC | **3** | 16.08. 21:40 |
| ETH/USDC | **3** | 11.08. 15:10 |

Alle drei über der Schwelle von 3.

**Die Ursache:** `coin_consecutive_losses` ist ein reines Speicher-Dict
(`risk/engine.py:78`). Es steht **nicht** in `bot_state.json` — geprüft,
die Datei kennt nur `daily_loss`. Bei jedem Neustart beginnt der Zähler
wieder bei null.

**Wie oft wird neu gestartet?** `evaluations` führt **12 verschiedene
git-Commits** in 12 Tagen, die Chronik 197 Starteinträge. Eine Serie von
drei Verlusten auf derselben Münze muss also innerhalb eines einzigen
Programmlaufs zustande kommen — bei 3,7 Trades pro Woche praktisch
unmöglich.

**Der Widerspruch, der es verrät:** Der Kill-Switch speichert seinen
Tagesverlust (`daily_loss` steht in `bot_state.json`), der Cooldown-Zähler
nicht. Zwei Schutzmechanismen, zwei verschiedene Behandlungen —
ohne dass irgendwo stünde, dass das Absicht ist.

**Zweiter, tieferliegender Punkt:** Der Zähler misst `pnl` in Dollar,
also das **gebuchte** Ergebnis. **217 von 220 Verkäufen** sind gebucht
positiv, nach echten Kosten (K-BASIS 0,505 %) aber negativ. Jeder davon
setzt den Zähler auf null. Nach der ehrlichen Rechnung wären die längsten
Serien 37 (BTC), 25 (ADA), 25 (SOL) — nach der gebuchten sind es 4, 3, 3.

**Blast Radius:** Eine Schutzregel, die seit Monaten im Code steht, im
Dashboard als aktiv erscheint und faktisch nie eingreift. Wer sich auf
sie verlässt, hält eine Verlustserie für abgesichert, die es nicht ist.

**Vorschlag zur Diskussion (nicht umgesetzt):**
1. `coin_consecutive_losses` in `bot_state.json` mitspeichern — dieselbe
   Behandlung wie `daily_loss`.
2. Den Zähler gegen das **Netto**-Ergebnis führen, nicht gegen den
   gebuchten Dollar-Wert. Hängt an Punkt 42 (Gebühren an der Quelle).
3. Falls beides gewollt anders ist: im Code begründen, damit die nächste
   Prüfung nicht dieselbe Frage stellt.

**Priorität:** HOCH · **Risiko** 5/10 · **Aufwand** 2/10 · **Impact** 6/10
**Konfidenz:** SICHER (Code, `bot_state.json` und Telemetrie einzeln
nachgeprüft). Handbuch 4.74.

### 55. Im Moment des Verkaufs wird das Kapital doppelt gezählt
**Gefunden am 19.08.2026 abends, beim Scan des laufenden Betriebs.**

`evaluations.total_equity` enthält zwei Ausreißer, beide **exakt im
Moment eines Verkaufs**:

| Zeit | Symbol | Kapital | `offene_positionen` |
|---|---|---:|---|
| 14:56:11 | BTC/USDC | 497,21 $ | 1 |
| 14:56:12 | ETH/USDC | 596,74 $ | 1 |
| **14:56:12** | **ETH/USDC** | **776,62 $** | **None** |
| 14:56:23 | BTC/USDC | 491,08 $ | 0 |

**776,62 − 596,74 = 179,88 $** — das ist genau der ETH-Verkaufserlös
(Terminal-Log: *„[PAPER] SELL ETH/USDC: Netto 179.89$"*).

Dasselbe bei BTC um 14:54:48: **774,84 $**, Verkaufserlös 179,19 $.

**Was passiert:** Zwischen der Gutschrift des Verkaufserlöses auf das
Cash-Konto und dem Entfernen der Position aus `open_positions` gibt es
ein Zeitfenster. Wer in diesem Fenster das Kapital berechnet, zählt
beides — den Erlös **und** die Position, die ihn erzeugt hat.

Das Feld `offene_positionen` steht dabei auf **`None`**, nicht auf 0 oder
1. Auch das deutet auf einen Zwischenzustand hin, in dem die Buchung
weder abgeschlossen noch unangetastet ist.

**Wie oft:** 2 Messungen von 203.432 (0,001 %). Beide heute, beide beim
Verkauf.

**Warum es trotzdem zählt — die Wirkung ist unverhältnismäßig groß:**

Der ausgewiesene größte Rückschlag sprang dadurch von 13,11 % auf
**23,20 %** — also scheinbar über die Schmerzgrenze von 20 %. Die Zahl
ist ein **Artefakt**: Sie misst den Rückfall von einem Kapitalwert, den es
nie gab, auf den echten Wert danach.

**Zwei Messungen von 203.432 haben die wichtigste Risikokennzahl des
Projekts verfälscht.** Ein einzelner Ausreißer wirkt beim Drawdown
stärker als bei jedem Durchschnitt, weil er den Gipfel setzt, gegen den
alles Folgende gemessen wird.

**Verwandt mit Befund 44** (`total_equity` bedeutet je nach Schreibstelle
zwei verschiedene Dinge). Dies ist ein dritter Zustand: nicht „mit oder
ohne Sparplan-BTC", sondern „während einer laufenden Buchung".

**Vorschlag zur Diskussion (nicht umgesetzt):**
1. Während einer laufenden Verkaufsbuchung **keinen** Kapitalwert
   schreiben — oder ihn als `NULL` lassen statt als Zahl.
2. `offene_positionen IS NULL` in allen Auswertungen als Ausschlusskriterium
   führen; das Feld markiert den Zwischenzustand bereits.
3. Sofortmaßnahme ohne Codeänderung: `drawdown_auswertung.py` verwirft
   Messungen mit `offene_positionen IS NULL`.

**Priorität:** MITTEL für den Handel (kein Geld betroffen, reine Buchung),
**HOCH für die Auswertung** — jede Kennzahl auf `total_equity` ist ohne
diesen Filter angreifbar.
**Risiko** 2/10 · **Aufwand** 2/10 · **Impact** 6/10 · **Konfidenz:** SICHER
(zwei Einzelfälle vollständig nachgerechnet, Differenz stimmt auf den Cent
mit dem Verkaufserlös überein). Handbuch 4.78.

### 56. Ein zweiter Wächter, den niemand füttert — Dauer-Rotalarm ohne Anlass
**Gefunden am 19.08.2026 beim Abarbeiten des `/api/status`-Punkts.**

`/api/status` liefert seit heute wieder HTTP 200. In der Antwort steht
aber Folgendes:

```
"auto_restart": {
  "data":      {"status": "frozen", "age_sec": 25501, "ampel": "🔴"},
  "signal":    {"status": "frozen", "age_sec": 25501, "ampel": "🔴"},
  "risk":      {"status": "frozen", "age_sec": 25501, "ampel": "🔴"},
  "execution": {"status": "frozen", "age_sec": 25501, "ampel": "🔴"},
  "context":   {"status": "frozen", "age_sec": 25501, "ampel": "🔴"}
}
```

**Fünf Module, alle „eingefroren", alle rot — seit 7,1 Stunden, also seit
dem Start.**

Zwei Zeilen weiter in derselben Antwort:

```
"health": {"healthy": true, "dead_components": [], "permanently_dead": []}
```

**Zwei Wächter überwachen dieselben fünf Komponenten und sagen das
Gegenteil.** Und der Bot handelt nachweislich — heute drei Ausführungen,
zwei Verkäufe im Plus.

**Die Ursache:** `grep -rn "auto_restart.heartbeat"` findet **null**
Treffer. Der Monitor setzt `last_seen` beim Registrieren
(`core/auto_restart.py:23`) und bekommt danach nie wieder ein Lebenszeichen.
Nach `timeout_sec=120` gilt alles als eingefroren.

Der zentrale Heartbeat-Pulse (`app.py:_start_heartbeat_pulse`) füttert
alle 30 Sekunden **`self.health`** — für exakt dieselben fünf Namen
`data`, `signal`, `risk`, `execution`, `context`. Nur `self.auto_restart`
steht nicht in der Liste.

**Warum es harmlos ist:** `app.py:4186` registriert mit
`self.auto_restart.register(comp)` — **ohne `restart_fn`**. Die Bedingung
im Monitor lautet `if agent["restart_fn"] and agent["restarts"] < 5:` und
ist damit immer falsch. **Es wird nichts neu gestartet.** Belegt auch
durch `"restarts": 0` nach 7 Stunden.

**Warum es trotzdem zählt:** Eine Ampel, die immer rot ist, wird nach
zwei Tagen nicht mehr gelesen. Genau diese Lektion steht schon zweimal im
Handbuch — bei `prozess_frische.py` (4.49) und `dauercheck.py` (4.57):

> *„Eine Warnlampe, die beim Einschalten viermal grundlos leuchtet, hätte
> man nach zwei Tagen abgeklebt."*

Hier leuchtet sie seit Monaten. Und sie steht im Web-Dashboard, das seit
dem 13.08. wieder Daten zeigt — sie ist also sichtbar geworden, ohne dass
jemand sie prüfen konnte.

**Drei Wege, zur Diskussion (nicht umgesetzt):**

1. **Mitfüttern** — eine Zeile im Heartbeat-Pulse, analog zu
   `self.health.heartbeat(...)`. Kleinster Eingriff, aber dann laufen zwei
   Wächter mit identischer Aufgabe.
2. **Abschaffen** — `health` tut bereits dasselbe, mit Fehlerzähler und
   Selbsttest. `auto_restart` wäre dann redundant.
3. **Schärfen** — `restart_fn` tatsächlich hinterlegen, damit der Monitor
   seinen Namen verdient. **Das wäre eine Verhaltensänderung** und gehört
   frühestens hinter den 27.08. — ein Wächter, der Module neu startet,
   muss vorher gegen Fehlalarm geprüft sein, und genau das ist er heute
   nicht.

**Empfehlung:** Weg 2. Zwei Wächter für dieselbe Frage sind einer zu
viel, und der gefütterte ist der bessere.

**Priorität:** MITTEL (Sichtbarkeit, kein Handelsrisiko) ·
**Risiko** 1/10 · **Aufwand** 1/10 · **Impact** 4/10 ·
**Konfidenz:** SICHER (Codepfade, Laufzeitwerte und Gegenwächter alle
nachgeprüft). Braucht einen Bot-Neustart → Gruppe B. Handbuch 4.79.

---

### 57. ✅ BEHOBEN (19.08.) — Der Metall-Reiter zeigte die Tagesempfehlung wie eine laufende Position
**Gefunden am 19.08.2026, weil Sven schrieb: „irgendwie kommen da keine
neuen gewinne oder verluste dazu! und wenn ich es selbst aktualisiere dann
nimmt er einen komplett neuen einstieg (neue position)".**

**Zuerst das Wichtigste: es gab keinen Datenfehler.** Beide offenen
Aufzeichnungen sind korrekt offen, und `track_signals()` legt kein zweites
Signal an, solange für dasselbe Metall eines läuft — die Sperre steht in
`metals/metals_engine.py` (`has_open` → `continue`). Gegengeprüft gegen die
Kurse von heute:

| Metall | Richtung | seit | Einstieg | Kurs heute | läuft |
|---|---|---|---|---|---|
| Silber | LONG | 24.06. | 56,61 $ | 63,94 $ | **+12,95 %** |
| Gold | SHORT | 12.08. | 4.463,80 $ | 4.366,00 $ | **+2,19 %** |

Beides stand auch vorher schon unten in der Mitschrift. **Der Fehler war
die Karte darüber:** sie zeigte `a['entry']` — und das ist der *aktuelle
Kurs als hypothetische Empfehlung*, nicht der Einstieg der laufenden
Aufzeichnung. Beim Aktualisieren änderte sich diese Zahl (weil der Kurs
sich änderte), und genau das sah aus wie ein neuer Einstieg.

Zwei verschiedene Dinge, gleich dargestellt, ohne ein Wort dazwischen.

**Der zweite Teil — warum die Gründe unten nicht lesbar waren.** Nicht die
Schriftgröße war die Ursache, sondern die Bauart: der Reiter hatte keine
Rollleiste. Gemessen im Render-Test bei 1400 × 900 px:

```
Inhalt braucht : 1035 px
Fensterhöhe    :  900 px
```

**135 px wurden schlicht abgeschnitten** — und ganz unten standen die
Indikator-Stimmen, also genau die „Gründe", nach denen Sven gefragt hat.

**Behoben (reine Anzeige, kein Eingriff in Engine oder Aufzeichnung):**

1. Die Karte weist jetzt aus: `AUFZEICHNUNG LÄUFT (LONG) seit 2026-06-24`,
   mit echtem Einstieg, laufendem Stand, Stop und Ziel. Die Tagesempfehlung
   steht darunter, ausdrücklich als *„wird NICHT aufgezeichnet, solange oben
   eines läuft"*.
2. Der ganze Reiter sitzt in einem Rollrahmen (`CTkScrollableFrame`) — nichts
   wird mehr abgeschnitten. Fällt der Rollrahmen aus, wird wie vorher gebaut.
3. Gründe von Schrift 10 auf 12, Farbe `#888` → `#b8b8c0`. Mitschrift von 10
   auf 12 und vollständig statt nur der letzten sechs.
4. Charts nehmen nicht mehr allen übrigen Platz (`expand=True` → `fill="x"`).

Gegengeprüft mit einem Render-Test in beide Richtungen (echte Daten aus dem
Journal + drei Ausfallfälle inkl. leerem Journal): alle bestanden. Der
Reiter berührt den Handelspfad an keiner Stelle.

**Priorität:** HOCH für seinen Zweck (der Reiter ist reine Recherche — was
man nicht lesen kann, sammelt keine Daten) · **Risiko** 0/10 ·
**Aufwand** 1/10 · **Impact** 6/10 · **Konfidenz:** SICHER (Signalstand
gegen aktuelle Kurse nachgerechnet, Höhe gemessen). Braucht einen
Bot-Neustart, damit der Reiter neu gebaut wird. Handbuch 4.81.

---

### 58. Das Gehirn lernt mit der falschen Elle — und misst Ausstiegsgründe als Strategien
**Gefunden am 19.08.2026 auf Svens Frage: „berechnet er das auch schon mit
und nimmt dann entscheidungen daraus?"**

**Korrektur einer eigenen Aussage von heute Nachmittag.** Ich hatte gesagt,
`select_best()` benutze die gelernten Zahlen gar nicht. Das ist falsch —
sie fließen in den Score ein, `agents/strategy_brain.py:168-177`:

```python
# 4. Historische Performance (0-2 Punkte)
perf = self.performance.get(sid, {})
wr = perf.get("win_rate", 0)
trades = perf.get("trades", 0)
if   trades >= 3 and wr > 60: score += 2.0
elif trades >= 3 and wr > 40: score += 1.0
elif trades >= 3 and wr < 30: score -= 1.0
```

Das ändert die Bewertung: das Gelernte wirkt. **Die Frage ist damit nicht
mehr „wirkt es?", sondern „was genau wirkt da?" — und die Antwort ist
schlechter als die erste.**

**Drei Fehler in derselben Zahl.**

**(a) Gewonnen heißt „brutto über null", nicht „nach Kosten übrig".**
`strategy_brain.py:332`: `if pnl > 0: p["wins"] += 1`. Über die 224
Verkäufe im Journal gerechnet:

| Maßstab | Treffer | Quote |
|---|---|---|
| `pnl` (USD) > 0 — **was das Gehirn zählt** | 172 / 224 | **76,8 %** |
| `pnl_pct` > 0 | 185 / 224 | 82,6 % |
| `pnl_pct` − 0,505 % > 0 — **die Wahrheit** | 100 / 224 | **44,6 %** |

**32,2 Prozentpunkte Unterschied.** Das Gehirn hält `DCA_FEAR_GREED` bei
91,3 % Trefferquote (322 Trades) — und vergibt dafür die vollen **+2,0
Punkte**, während derselbe Pfad in Wahrheit einen Erwartungswert von
−0,121 % je Runde hat (Befund 45). Es lernt nicht das Falsche, es lernt
das Richtige an der falschen Messlatte.

**(b) Ausstiegsgründe stehen als „Strategien" in derselben Tabelle.**
`runtime/exit_monitor.py:336-362` setzt `strategy` auf den *Ausstiegsgrund*
(`STOP_LOSS`, `TRAILING_STOP`, `BREAKEVEN_LOCK`, `TREND_EXIT`) und reicht
genau das in Zeile 581 als `strategy_id` an `record_trade_result` weiter.
Ergebnis in `data_store/brain_performance.json`:

```
BREAKEVEN_LOCK      5 Trades,  0 wins,   0.0 %
TRAILING_STOP       4 Trades,  3 wins,  75.0 %
STOP_LOSS           1 Trade,   0 wins,   0.0 %
```

Im Journal betrifft das **119 von 224 Verkäufen** (53 %), die einen
Ausstiegsgrund im Feld `strategy` tragen. Auf den Score wirkt es nicht —
`select_best()` läuft nur über `STRATEGIES`, und dort stehen keine
Ausstiegsgründe. Es macht aber jede Auswertung der Datei unlesbar: was
aussieht wie „diese Strategie verliert immer", ist in Wahrheit „so oft hat
die Breakeven-Sperre ausgelöst".

**(c) Vom Ausstieg lernt es überhaupt nichts.** Gespeichert werden vier
Felder je Eintrag: `trades`, `wins`, `total_pnl`, `win_rate`. Kein
Höchststand, kein zurückgegebener Gewinn, kein Nachlauf. **Die Frage „bin
ich zu früh raus?" kann das Gehirn nicht einmal stellen** — die dafür
nötige Zahl steht in keinem seiner Felder.

**Was das für Svens Frage bedeutet:** Nein. Das Gehirn rechnet die
verschenkte Bewegung nicht mit, und es kann es in dieser Bauform auch
nicht. Es wählt den *Einstieg*; der *Ausstieg* liegt komplett außerhalb
seines Blickfelds.

**Kein Eingriff jetzt** — jede Änderung an der Lernzahl ist eine
Verhaltensänderung und braucht eine Epochengrenze. Vorschlag für nach dem
27.08., in dieser Reihenfolge:

1. **`pnl` gegen K-BASIS messen** statt gegen null (`pnl_netto = pnl_pct −
   0,505`). Kleinster Eingriff, größte Wirkung, kein neues Feld.
2. **Ausstiegsgründe trennen** — eigener Aufruf, eigene Datei. Dann sagt die
   Tabelle wieder, was draufsteht.
3. Erst danach über ein Ausstiegs-Lernen nachdenken, und nur mit den Daten
   aus `positionsverlauf.py` — vorher gibt es nichts zu lernen.

**Priorität:** HOCH (das Gehirn lenkt die Einstiegswahl mit einer um 32
Punkte zu guten Zahl) · **Risiko** 0/10 solange nichts geändert wird ·
**Aufwand** 2/10 für Schritt 1 · **Impact** 7/10 ·
**Konfidenz:** SICHER (Codestellen zitiert, beide Aufrufwege verfolgt,
Quoten aus dem Journal gegen zwei Maßstäbe nachgerechnet).
Gruppe C — wartet auf die Epochengrenze. Handbuch 4.82.

---

### 59. Ergänzung zu Handbuch 4.75/4.80: der RSI-Ausstieg ist der beste — und trotzdem zu früh
**Gemessen am 19.08.2026 auf Svens Einwand: „was ist wenn es nur eine
kleine korrektur ist und er dann aber zb noch 10 % Plus machen würde?"**

**Sven hat recht, und es korrigiert meine eigene Empfehlung.** Ich hatte den
RSI-Ausstieg als den offensichtlichsten Hebel bezeichnet, weil er den besten
Erwartungswert je Ausstieg realisiert (+0,948 % über 31 Fälle). Das stimmt
weiter. Es beantwortet aber nur die halbe Frage — nämlich was *im Moment des
Verkaufs* auf dem Konto landet, nicht was danach passiert.

`data_store/nachlauf.db` beantwortet die andere Hälfte:

| Ausstiegsart | n | Kursbewegung in der Stunde **nach** dem Verkauf |
|---|---|---|
| **RSI overbought** | 2 | **+5,15 %** |
| Trailing-Stop | 4 | −0,51 % |
| alle übrigen | 10 | +0,05 % |

Die beiden Einzelfälle vom 19.08.:

```
14:54  BTC  RSI overbought (80)  Verkauf +2,19 %  ->  danach +4,43 %
14:56  ETH  RSI overbought (80)  Verkauf +2,54 %  ->  danach +5,87 %
```

**Lesart:** Der Trailing-Stop steigt aus, *weil* die Bewegung vorbei ist —
danach passiert nichts mehr (−0,51 %), das ist der richtige Zeitpunkt. Der
RSI steigt aus, *weil eine Kennzahl 80 überschreitet* — und der Markt lief
danach weiter. Genau das, was Sven beschrieben hat.

**Wie belastbar ist das? Nicht sehr — und das gehört dazu.**

- **n = 2.** Beide am selben Tag, beide in derselben Marktbewegung. Das sind
  keine zwei unabhängigen Fälle, das ist einer.
- Von **453 aufgezeichneten Ausstiegen haben nur 16 überhaupt Nachlaufwerte.**
  Die 437 vor dem 09.08. sind mit dem 200-Kerzen-Fenster nicht mehr
  auflösbar (`nachlauf.py`, Zweig `if ziel < erste: continue`) und stehen
  trotzdem als `vollstaendig=1` in der Tabelle — sie sind abgeschlossen, aber
  nie gemessen worden. Wer `vollstaendig` als „gemessen" liest, überschätzt
  die Datenbasis um den Faktor 28.

**Also: WARNSIGNAL, kein Beleg.** Die Zahl, die es entscheidet, sammelt sich
gerade an — jeder weitere RSI-Ausstieg trägt einen unabhängigen Fall bei.
Ab etwa n = 10 ist die Frage beantwortbar.

**Was jetzt NICHT passiert:** der RSI-Ausstieg wird nicht angefasst. Er
bleibt der Ausstieg mit dem besten realisierten Ergebnis; ihn wegen zwei
Fällen zu ändern wäre genau der Fehler, gegen den die Trivial-Latte da ist.

**KORREKTUR am selben Tag, 21:30** — die Datenbasis ist inzwischen von 16 auf
453 Ausstiege gewachsen (Befund 60). Damit gilt: die **Richtung stimmt**
(RSI +0,92 %, Trailing −0,00 % über 1 Stunde), aber die **Größenordnung war
falsch** — +5,15 % waren zwei Ausreißer, über 35 Fälle sind es +0,92 %. Und
auf unabhängige Tage zusammengefasst (11 Tage) bleibt +0,36 % ± 0,59, also
nichts Belegbares. Die Schwelle „ab n = 10" war zu einfach: es zählen die
**Tage**, nicht die Verkäufe. Neues Ziel: 25 Tage mit RSI-Ausstieg.
Handbuch 4.84.

**Priorität:** MITTEL (Messauftrag, keine Reparatur) · **Risiko** 0/10 ·
**Aufwand** 0/10 (läuft von selbst mit) · **Impact** 7/10, falls es sich
bestätigt · **Konfidenz:** WAHRSCHEINLICH (Messung sauber, Fallzahl zu
klein). Gruppe A — beobachten. Handbuch 4.83.

---

### 60. ✅ BEHOBEN (19.08.) — Jeder dritte Nachlauf-Messwert stammte aus einer noch laufenden Kerze
**Gefunden am 19.08.2026 durch die Gegenprobe des Nachtrag-Werkzeugs — sie
sollte den Nachtrag prüfen und fand stattdessen einen Fehler im Bestand.**

Sven fragte, ob sich die 437 nie gemessenen Ausstiege rekonstruieren lassen.
Sie lassen sich (siehe unten). Bei der Pflicht-Gegenprobe — *rechne die
bereits gemessenen Werte nach und halte sie gegen die echten* — kam heraus:

```
Womit stimmt der LIVE gemessene Wert überein?
  erste Kerze NACH dem Ziel (die Regel)  :  7.271  (64,9 %)
  mit gar keiner fertigen Kerze          :  3.870  (34,6 %)
```

**Ein Drittel der Messwerte gehört zu keinem Schlusskurs, den es je gab.**

**Die Ursache.** Eine Kerze trägt ihre **Öffnungszeit** als Stempel. Die
23:00-Kerze ist erst um 00:00 fertig. `nachlauf.py` nahm einfach
`df["Close"].iloc[treffer[0]]` — und wenn diese Kerze noch lief, ist ihr
„Close" nicht der Schlusskurs, sondern **der Preis in diesem Augenblick**.
Der wird dauerhaft als Messwert gespeichert und sieht hinterher aus wie eine
Messung.

Belegt an einem Einzelfall, von Hand nachgerechnet:

```
SOL/USDC, Ausstieg 16.08. 21:40 UTC, Frist 1 Stunde -> Ziel 22:40
  Kerze 22:00  schließt bei 74,45
  Kerze 23:00  schließt bei 74,55   <- die richtige (erste ab 22:40)
  gespeichert wurde: 74,45
```

74,45 ist der Stand *mitten in* der laufenden Kerze. Größte gemessene
Abweichung: **2,24 %** — bei Nachlaufwerten, die im Schnitt unter 1 % liegen,
also größer als das gesuchte Signal.

**Derselbe Fehlertyp wie zweimal zuvor:** `volume_ratio` und
`high_low_range` messen die verstrichene Stunde statt den Markt (Befund 39),
und das KI-Modell sagt auf `df.iloc[-1]` vorher, also auf der offenen Kerze.

> **Die letzte Kerze ist noch keine Kerze.** Wer sie liest, misst die Uhrzeit
> mit.

**Behoben** in `nachlauf.py`: eine Kerze mit Öffnungszeit `T` wird erst ab
`T + 1h` akzeptiert, vorher gilt der Wert als noch nicht fällig und kommt in
der nächsten Runde dran. Reines Aufschreiben, kein Handelsverhalten —
freeze-verträglich.

**Und die 437 alten Fälle sind zurück.** Nicht die Daten fehlten, sondern der
Griff danach: `fetch_snapshot(limit=200)` reicht bei Stundenkerzen acht Tage
zurück, `ccxt.fetch_ohlcv(since=…)` beliebig weit. Neues Werkzeug
`nachlauf_rueckwirkend.py`:

| | vorher | nachher |
|---|---|---|
| Ausstiege mit Nachlaufwert | 16 von 453 | **453 von 453** |
| Blockaden mit Nachlaufwert | 3.519 | 4.199 |
| Werte aus laufenden Kerzen | 3.870 | 0 (2.900 überschrieben) |

Die Spalte `quelle` sagt bei jedem Wert, woher er kommt: `live`,
`nachgetragen`, `korrigiert`. Sicherung vor dem Eingriff:
`data_store/nachlauf.db.bak_vor_nachtrag_20260819`.

**Die Gegenprobe prüft in drei Richtungen** (`--gegenprobe`): gegen einen von
Hand nachgerechneten Einzelfall mit vier bekannten Werten, gegen die
Live-Messwerte als Statistik, und gegen drei Ausfallfälle (leere Kerzenliste,
Ziel in der Zukunft, laufende Kerze). Teil 1 und 3 fehlerfrei.

**Priorität:** HOCH für die Messqualität (die verfälschten Werte waren die
Grundlage der Ausstiegs-Bewertung) · **Risiko** 0/10 · **Aufwand** 2/10 ·
**Impact** 8/10 · **Konfidenz:** SICHER (Einzelfall von Hand gegen die
Kerzenliste geprüft, Ursache im Code gezeigt, Wirkung an 11.200 Werten
gemessen). Handbuch 4.84.

---

### 61. ✅ BEHOBEN (19.08.) — Der Marktzustand fehlte in allen 697 Schatten-Zeilen
**Gefunden am 19.08.2026 durch `sammler_pruefen.py`, das genau danach sucht:
Felder, die eine Auswertung braucht und die trotzdem leer sind.**

`schatten_universum.db` sammelt seit dem 12.08. für zwölf Münzen dieselbe
Punktzahl, die der Bot rechnet — die Grundlage für die Frage, **welche Münze
ihre Reibungskosten überhaupt verdient.** Jede Zeile trägt 21 Felder. Zwanzig
davon sind gefüllt. Eines nicht:

```
regime   697 von 697 leer  (100 %)
```

**Die Ursache ist eine Auslassung, kein Fehler.** `schatten_universum.py:333`
legt an:

```python
zusatz = {"fear_greed": 50, "regime": None, "zyklus": None, "balance": 500.0}
```

Danach holt der Code `fear_greed` und `zyklus` aus dem Bot-Zustand —
**`regime` nicht.** Es blieb also für immer `None`. Niemand hat es bemerkt,
weil die Zeile ansonsten vollständig aussieht.

**Was dadurch nicht ging:** Die Auswertung „welche Münze verdient ihre
Reibung" ließ sich nicht nach Marktlage trennen. Ein Signal, das im Trend
funktioniert und in der Seitwärtsbewegung Geld verbrennt, sieht in der
Gesamtzahl aus wie ein mittelmäßiges Signal.

**Behoben** — und zwar an der besseren Stelle: der Wert kommt jetzt aus dem
**Schnappschuss der jeweiligen Münze**, nicht aus einem globalen Feld. Er war
die ganze Zeit da; `DataAgent` legt ihn beim Holen der Kerzen hinein
(`market_data.py:102`). Ein Wert aus `zusatz` wäre für alle zwölf Münzen
derselbe gewesen — obwohl BTC im Trend laufen kann, während SOL seitwärts
geht.

**Und die 697 alten Zeilen sind nachgetragen**, exakt statt geschätzt: der
Marktzustand hängt allein am ADX, und der steht in jeder Zeile mit drin.

```
market_data.py:102
reg = TRENDING if adx > 25 else RANGING if adx < 20 else UNKNOWN
```

Dieselbe Eingabe, dieselbe Regel, dasselbe Ergebnis, das der Sammler
geschrieben hätte. Werkzeug: `schatten_regime_nachtragen.py`, Gegenprobe in
zwei Richtungen (sieben Grenzfälle von Hand **und** gegen die echte
Bot-Klasse `MarketRegime`) — bestanden.

| Marktzustand | Zeilen | Anteil |
|---|---|---|
| TRENDING | 621 | 89 % |
| RANGING | 40 | 6 % |
| UNKNOWN | 36 | 5 % |

Sicherung: `data_store/schatten_universum.db.bak_vor_regime_20260819`.

**Priorität:** MITTEL · **Risiko** 0/10 · **Aufwand** 1/10 · **Impact** 5/10 ·
**Konfidenz:** SICHER (Auslassung im Code gezeigt, Nachtrag gegen die echte
Bot-Klasse geprüft). Handbuch 4.86.

---

### 62. ✅ BEHOBEN (19.08.) — Die Regime-Messung zählte dieselbe Stunde 300-mal
**Gefunden beim Nachsehen, was `regime_filter_messung.py` eigentlich tut —
auf Svens Frage hin.**

Sie meldete **89.291 geblockte Kaufgelegenheiten**. Das klingt nach
erdrückender Beweislage und ist keine.

**Der Bot prüft alle rund 12 Sekunden.** Bleibt eine Marktlage eine Stunde
bestehen, steht dieselbe geblockte Gelegenheit 300-mal in der Datenbank — und
wurde 300-mal gezählt. In zwölf Tagen passen bei 24-Stunden-Sicht **12 nicht
überlappende Fenster je Münze**, nicht 53.806.

CLAUDE.md, Regel 0, sagt es wörtlich: *„Immer fragen, wie viele davon
unabhängig sind. Bei Horizont H passen in T Tage nur T·24/H nicht
überlappende Fenster."*

**Dazu der zweite Fehler: die Kosten.** Sie rechnete mit 0,32 % je Runde statt
der 0,505 % (K-BASIS). Die Stelle steht auf der Liste in Handbuch 4.53 —
bekannt, aber noch nicht korrigiert. Da es eine reine Messung ist und kein
Handelsverhalten, ist die Korrektur freeze-verträglich.

**Beides zusammen drehte das Urteil um:**

| | vorher | nachher |
|---|---|---|
| Fälle (Regime-Filter, 24 h) | 53.806 | **22** |
| Kosten je Runde | 0,32 % | 0,505 % |
| Ergebnis | +0,351 % | **−0,283 %** |
| Urteil | „Block war TEUER" | „zu wenig Fälle" |

Die alte Fassung hätte geraten, den Filter zu **lockern**. Die neue sagt: die
geblockten Käufe hätten Verlust gebracht — und selbst das steht auf 22 Fällen.

**Behoben:** Die Auswertung zählt je (Münze, Regel, Horizont) nur den ersten
Fall eines Fensters. Die Ausgabe führt beide Spalten — `unabh.` und `roh` —
und Zeilen unter 30 unabhängigen Fällen tragen ausdrücklich das Urteil „zu
wenig Fälle" statt einer Zahl, die gut aussieht.

> **Eine große Zahl ist kein Beleg.** 53.806 Fälle klingen nach Gewissheit und
> sind doch dieselbe Stunde, dreihundertmal aufgeschrieben.

**Priorität:** HOCH (das Urteil hätte zu einer Lockerung geführt) ·
**Risiko** 0/10 · **Aufwand** 2/10 · **Impact** 8/10 · **Konfidenz:** SICHER
(beide Spalten nebeneinander gemessen). Handbuch 4.86.

---

### 63. ⚠️ OFFEN (Freeze) — Das Allzeithoch im Code ist 15,7 % zu niedrig, die Zyklusphase dadurch zu optimistisch
**Gefunden am 20.08.2026, weil Sven fragte: „ich sehe ‚early Bärenmarkt' — sind
wir nicht im späten Bärenmarkt?"**

Er hatte recht, dass etwas nicht stimmt. Nur aus einem anderen Grund als
vermutet.

**Zuerst zur Benennung.** Die Phasen sind **nicht zeitlich** benannt, sondern
nach der **Tiefe** — dem Abstand vom Allzeithoch (`agents/cycle_theory.py:90`):

| Phase | Abstand vom Hoch |
|---|---|
| EUPHORIA | über −5 % |
| DISTRIBUTION | −5 bis −20 % |
| **EARLY_BEAR** | −20 bis −35 % |
| **MID_BEAR** | −35 bis −50 % |
| DEEP_BEAR | −50 bis −70 % |
| CAPITULATION | −70 bis −80 % |
| ACCUMULATION | unter −80 % |

„EARLY" heißt hier also **flach**, nicht *früh*. Ein `LATE_BEAR` gibt es
nicht — tiefer geht es über DEEP_BEAR und CAPITULATION.

**Und jetzt der Fehler.** Das Allzeithoch steht fest verdrahtet in
`agents/cycle_theory.py:28`:

```python
CURRENT_ATH = 109_114
CURRENT_ATH_DATE = "2025-01-20"
```

Gegen **drei unabhängige Quellen** geprüft:

| Quelle | höchster Kurs | wann |
|---|---|---|
| Binance BTC/USDT | 126.200 $ | 06.10.2025 |
| Binance BTC/USDC | 126.296 $ | 06.10.2025 |
| Bybit BTC/USDT | 126.196 $ | 06.10.2025 |

**Das echte Hoch liegt 15,7 % höher und ist neun Monate jünger.** Der Bot
misst den Abstand also gegen einen Gipfel, der längst überboten wurde.

**Was das ändert:**

| | Bezugspunkt | Abstand | Phase |
|---|---|---|---|
| im Code | 109.114 $ | −34,1 % | **EARLY_BEAR** |
| tatsächlich | 126.200 $ | **−43,0 %** | **MID_BEAR** |

Heute Morgen um **08:27** ist die Anzeige von MID_BEAR auf EARLY_BEAR
gesprungen, als BTC von 70.963 auf 71.257 $ stieg — mit dem richtigen Hoch
wäre sie MID_BEAR geblieben. Sven hat den Sprung sofort bemerkt und
angezweifelt. Sein Bauchgefühl war genauer als die Konstante.

**Warum das nicht nur Kosmetik ist.** Die Phase steuert die Positionsgröße
(`cycle_theory.py:145`):

```python
"EARLY_BEAR": 0.6,      # Nur DCA
"MID_BEAR":   0.5,      # Kleine DCA
```

Der Bot kauft in EARLY_BEAR also **20 % größere Positionen** als die Lage
hergibt. Dazu geht die Phase in die Strategiewahl des BRAIN, in den
Kontext-Agenten und in jede Telemetriezeile — auch alle bisherigen
Auswertungen tragen die zu flache Einstufung.

**Warum es nicht sofort repariert wird:** Es ist eine **Verhaltensänderung**
mitten im Messfenster. Nach CLAUDE.md Abschnitt 5 wird ein solcher Fund
**gemeldet**, aber nicht angefasst — die Entscheidung trifft Sven. Der Bot
läuft im Papierhandel, es steht kein echtes Geld im Feuer.

**Vorbereitet für den 28.08.:**
`patches_nach_27_08/patch_63_ath_dynamisch.py` — holt das Hoch aus den
Wochenkerzen statt es zu verdrahten. Eine Zahl, die man von Hand pflegen
muss, veraltet; genau derselbe Fehler wie bei den Epochen im Cockpit (4.92)
und der Münzzahl (4.93).

**Priorität:** HOCH · **Risiko** 3/10 (ändert Positionsgröße) · **Aufwand**
2/10 · **Impact** 7/10 · **Konfidenz:** SICHER (drei Quellen, Fundstelle,
Wirkung im Code gezeigt). Handbuch 4.94.

---

### 64. ⚠️ OFFEN (Freeze) — Der Hauptkaufpfad schließt genau dann, wenn der Kurs steigt
**Gefunden am 20.08.2026, weil Sven es satt hatte:** *„das Einkaufsverhalten
des Bots ist zum Kotzen, so wie das aufgebaut ist … was ist denn jetzt, wenn
wir auf 120 k wieder hoch gehen, und der Bot würde alles verpassen, weil er
nicht kaufen kann?"*

**Er hat recht. Es ist keine Einstellung, es ist die Bauart.**

96,6 % aller Käufe kommen aus einem einzigen Pfad (`app.py:2700`):

```python
if fg < 30:   # DCA bei Fear
```

Der Pfad braucht **Angst**. Über 866 gemessene Stunden war er an 292 offen —
**34 % der Zeit**. Die restlichen 66 % trägt der Signalpfad, und der hat in
der gesamten Historie **0,0 %** der Käufe erzeugt (12 × EMA_TREND, 6 ×
Fibonacci, 1 × MACD, zusammen 19 von 557).

**Und jetzt der Zusammenhang, der es strukturell macht:**

| | |
|---|---|
| Zusammenhang BTC-Preis ↔ Fear & Greed | **+0,85** |
| Messungen | 866 |

Steigt der Kurs, steigt die Gier. Steigt die Gier über 30, **schließt der
Hauptkaufpfad**. Der Bot kauft also nach Konstruktion umso seltener, je besser
es läuft — und in einem anhaltenden Aufwärtsmarkt praktisch gar nicht mehr.

Heute: **F&G 62**, Kaufpfad zu.

**Was das NICHT ist.** Sven vermutete die Wiedereinstiegs-Sperre als Ursache.
Sie ist es nicht: `ReentryGuard(sperr_minuten=90, preisfenster_stunden=6,
mindest_abschlag_pct=1.0)` — nach **sechs Stunden verfällt sie vollständig**
(`risk/reentry_guard.py:108`). Sie kann einen Aufwärtsmarkt nicht verpassen
lassen, sondern höchstens sechs Stunden davon.

Gemessen, was die Blockaden gekostet haben (nach Kosten, je Horizont eigene
nicht überlappende Fenster):

| Blockiergrund | n (1 h) | +1 h | n (4 h) | +4 h |
|---|---|---|---|---|
| schon in Position | 199 | −0,36 % | 80 | −0,16 % |
| Regime-Filter | 133 | −0,43 % | 52 | −0,33 % |
| **Wiedereinstiegs-Sperre** | **62** | **±0,00 %** | 19 | +0,59 % |
| Bärenmarkt-Regel | 50 | −0,11 % | 20 | +0,45 % |

**Auf der Zeitskala mit belastbarer Fallzahl kostet die Sperre nichts.** Bei
4 h und 24 h sieht sie teuer aus (+0,59 %, +2,98 %) — aber dort sind es 19
bzw. 7 Fälle. Dazu kommt: die gesamte Blockade-Aufzeichnung liegt in einer
Woche, in der BTC 14,6 % gestiegen ist. **In einem steigenden Markt sieht
jedes „nicht gekauft" teuer aus.** Das ist keine Messung des Filters, sondern
eine Messung der Woche.

**Der Fund ist also nicht die Sperre, sondern die Asymmetrie:** Es gibt einen
gut funktionierenden Kaufpfad für fallende Märkte und faktisch keinen für
steigende.

**Zahlen zum Bild (20.08.):** BTC 72.778 $, −42,3 % unter dem echten
Allzeithoch, aber **+25,9 %** über dem Tief vom 01.07. Der Kurs steht über
allen vier gleitenden Durchschnitten (20/50/100/200 Tage), die 50 liegt aber
**noch unter** der 200. +14,6 % in einer Woche, −3,7 % über drei Monate.

**Warum jetzt nichts geändert wird:** Verhaltensänderung mitten im
Messfenster. Der Freeze läuft bis 29.08.

**Was gebraucht wird, bevor daran gedreht wird** — und das ist der eigentliche
Punkt: Es gibt bis heute **keine Messung, was ein Kaufpfad für steigende
Märkte gebracht hätte**. Der Signalpfad existiert, feuert aber praktisch nie.
Ob das an der Punkteschwelle liegt, am Regime-Filter oder an der
Kapazitätsgrenze, ist **ungemessen**.

Das Schatten-Universum misst bereits die Einstiegspunktzahl auf 18 Münzen ohne
zu handeln — es sammelt genau die Daten, die diese Frage beantworten. Was
fehlt, ist die Auswertung „hätte ein Kauf bei Punktzahl ≥ X in Gier-Phasen
nach Kosten getragen?".


**ERSTE MESSUNG, 20.08. (mit dem neuen Instrument, siehe Handbuch 4.103):**

| Marktstimmung | Fälle | Tage | +1 h | +4 h | +24 h | +48 h |
|---|---|---|---|---|---|---|
| Angst (unter 30) | 152 | **1** | −0,53 % | −0,36 % | −0,10 % | −0,78 % |
| **Gier (30 und mehr)** | **638** | **7** | −0,28 % | +0,01 % | **+1,53 %** | +0,93 % |

Der Richtung nach stützt es Sven: Käufe in Gier hätten in dieser Woche nach
Kosten getragen, Käufe in Angst nicht. **Aber es trägt noch kein Urteil:**
sieben Tage, und die Angst-Fälle stammen aus einem einzigen. Vor allem fällt
der ganze Zeitraum in eine Woche mit **+14,6 %** — in einer Aufwärtswoche
zahlt sich jeder Kauf aus. Nötig sind 25 Tage über verschiedene Marktphasen.

Das Instrument läuft jetzt mit. Die Frage beantwortet sich von selbst, wenn
die Tage da sind.

**Priorität:** HOCH (betrifft die Grundmechanik, nicht ein Detail) ·
**Risiko** 6/10 (ein zweiter Kaufpfad ändert das Risikoprofil) · **Aufwand**
5/10 · **Konfidenz:** SICHER für die Beschreibung (Code, 866 Messungen,
Korrelation), **OFFEN** für die Lösung — die muss gemessen werden.
Handbuch 4.102.

---

### 65. ⚠️ OFFEN (Freeze) — Die Stufen-Leiter greift, aber auf einer geschrumpften Basis: 0,80 % statt 1,20 %
**Gefunden am 21.08.2026, weil Sven es satt hatte:** *„der Bot hat so viel
liegen lassen, dass er bei jedem kleinen Rücksetzer raus ist. Wäre er ganz
normal nach Leiter raus, wäre es gut gewesen. Ich habe damals doch extra das
Stufen-Trailing rein gemacht!"*

**Die Leiter ist da. Sie wird auch angewendet. Aber nicht auf den Wert, den sie
selbst nennt.**

### Der Beleg

Aus den Verkaufsbegründungen im Journal, die die Auslöseschwelle mitschreiben:

| Datum | Hoch | Fall | Schwelle **war** | Leiter **sagt** |
|---|---|---|---|---|
| 27.07. | +1,54 % | 1,08 % | **0,80 %** | 1,20 % |
| 06.08. | +1,27 % | 0,81 % | **0,80 %** | 1,20 % |
| 07.08. | +1,34 % | 1,02 % | **0,80 %** | 1,20 % |
| 12.08. | +1,99 % | 0,80 % | **0,80 %** | 1,20 % |
| 18.08. | +1,67 % | 0,88 % | **0,80 %** | 1,20 % |
| 19.08. | +1,38 % | 0,82 % | **0,80 %** | 1,20 % |

**10 von 12** der zuletzt geprüften Trailing-Ausstiege lösten bei 0,80 % aus.
Nur die beiden mit sehr hohem Höchststand (+8,06 % und +23,21 %) trafen die
Leiter (2,63 ≈ 2,64 %).

### Die Ursache — und sie ist kein Bug, sondern eine Verkettung

`runtime/exit_monitor.py:353`

```python
eff_trail = effektiver_trail(hoechst_pnl_pct, trail_pct, _rr_regime)
```

Das zweite Argument ist **`trail_pct`**, nicht `TRAIL_AB_PCT`. Und
`effektiver_trail()` rechnet:

```python
return round(trail_pct * faktor, 3)      # risk/exit_rules.py:146
```

Die Leiter liefert also nur den **Faktor** (×1,0 / ×1,3 / ×1,7 / ×2,2). Die
**Basis** kommt von woanders — aus der Konfiguration, durchgereicht durch das
Marktphasen-Profil (`risk/regime_profiles.py:58`):

```
trail = base_trail × Zyklus-Faktor × Regime-Faktor
```

| Zyklus / Regime | Basis aus 1,0 % |
|---|---|
| MID_BEAR / RANGING | **0,80 %** |
| MID_BEAR / TRENDING | 0,92 % |
| MID_BEAR / VOLATILE | 0,72 % |
| EARLY_BEAR / TRENDING | 0,98 % |

Und darauf wird die Leiter multipliziert:

| | Hoch +1,2 % | +3 % | +5 % | +8 % |
|---|---|---|---|---|
| Basis 0,8 % (Ist) | **0,80 %** | 1,04 % | 1,36 % | 1,76 % |
| Basis 1,2 % (wie dokumentiert) | 1,20 % | 1,56 % | 2,04 % | 2,64 % |

**`TRAIL_AB_PCT = 1.2` wird ausschließlich als Einschaltschwelle benutzt** —
„ab welchem Höchststand wird überhaupt getrailt". Als Basis taucht es nie auf.
Wer die Leiter im Code liest, erwartet 1,20 %; wer den Bot beobachtet, sieht
0,80 %.

> Sven hat das Stufen-Trailing eingebaut und bekommt seit Wochen die
> Bärenmarkt-Schrumpfung serviert. Beides ist für sich richtig gebaut — das
> Zusammenspiel hat niemand nachgerechnet.

### Was es bei BTC gekostet hat

| Datum | Hoch | Verkauf | hergeschenkt |
|---|---|---|---|
| 27.07. | +2,16 % | +1,16 % | **1,00 PP** |
| 29.07. | +2,37 % | +1,51 % | 0,86 PP |
| 06.08. | +1,27 % | +0,45 % | 0,82 PP |
| 07.08. | +1,34 % | +0,31 % | **1,03 PP** |
| 18.08. | +1,67 % | +0,77 % | 0,90 PP |
| 19.08. | +1,39 % | +0,56 % | 0,83 PP |

Sechs BTC-Ausstiege, jedes Mal **0,8 bis 1,0 Prozentpunkte** zurückgegeben —
bei einem Erwartungswert, der um null herum entschieden wird.

### Und der zweite Punkt: es gibt keine Teilverkäufe

`runtime/exit_monitor.py:377` verkauft `quantity=qty` — und `qty` ist die
**volle Positionsmenge** (`:106`). Im ganzen Code gibt es keinen
Teilverkauf-Pfad.

**Ein kleiner Rücksetzer schließt also immer 100 %.** Es gibt keine
Möglichkeit, die Hälfte laufen zu lassen. Sven: *„er hat immer volle 100
Prozent mitgenommen."*

### Die erste zweiseitige Messung — und sie ist unbequem

Am 21.08. schlossen die ersten neun Schattenläufe (7 Tage Laufzeit, ohne
Ausstieg). Damit ließ sich zum ersten Mal messen, was eine Regel gekostet
hätte, die **später** ausgestiegen wäre:

| Regel | Mittel je Position | gegen „einfach halten" |
|---|---|---|
| **Halten (Trivial-Latte)** | **+13,10 %** | — |
| Bot heute (Basis 0,80) | +5,18 % | −7,91 PP |
| Basis 1,20 | +4,78 % | −8,32 PP |
| Basis 2,00 | +7,10 % | −6,00 PP |
| Basis 3,00 und weiter | +7,51 % | −5,59 PP |
| Chandelier ATR×3 | +6,34 % | −6,76 PP |

**Keine einzige Ausstiegsregel schlägt das Nichtstun.** Auch nicht mit
Basis 6 %.

Der Grund steht in den Läufen selbst: BTC +16,4 %, ETH +24,5 %, LINK +22,6 %,
SOL +17,3 % — **alle neun endeten fast auf ihrem Höchststand.**

### Was das heißt — und was ausdrücklich nicht

**Es heißt:** In einer Woche wie dieser kostet jede Ausstiegsregel Geld. Der
Bot hat je Position rund **8 Prozentpunkte** liegen lassen. Svens Ärger ist
messbar berechtigt.

**Es heißt NICHT**, dass Trailing generell schlecht ist. Neun Läufe, **eine
Woche, ein Regime** (BTC +14,6 %). In einer Aufwärtswoche gewinnt Halten
immer — das ist keine Erkenntnis über die Regel, sondern über die Woche. Wer
jetzt die Basis auf 3 % stellt, weil sie hier am besten war, hat sie auf diese
Woche angepasst: **Overfitting**, genau das, was der Quant-Forscher zu
verhindern hat.

### Die eigentliche Frage, die daraus folgt

Nicht *„welche Basis?"*, sondern: **soll in einem bestätigten Aufwärtstrend
überhaupt getrailt werden?** Der `TREND_BONUS = 1.3` erkennt die Lage bereits,
lockert aber nur um 30 % — im Ergebnis 1,04 % statt 0,80 %. Das ändert nichts
an einem Lauf, der 16 % macht.

**Nötig, bevor gedreht wird:** dieselbe Messung in einer Seitwärts- und einer
Abwärtswoche. Das Werkzeug steht (`ausstieg_vergleich.py`), die
Schattenläufe erneuern sich alle sieben Tage von selbst.

**Priorität:** HOCH · **Risiko** 5/10 (Ausstiegsregeln sind der Kern) ·
**Aufwand** 2/10 (eine Zahl) · **Konfidenz:** SICHER für die Mechanik
(Fundstellen, 12 Verkaufsbegründungen) · **OFFEN** für die Lösung — sie
braucht mehr als eine Marktphase. Handbuch 4.109.

---

### 66. ⚠️ OFFEN (Freeze) — Der Nachzieh-Stopp überlebt nur 15 bis 40 % der normalen Rücksetzer
**Gemessen am 21.08.2026 auf Svens Frage:** *„wichtig ist zu wissen, wie hat es
sich in den letzten Jahren verhalten — um wie viel Prozent hat er korrigiert,
bevor es weiter nach oben ging?"*

**Die Frage war goldrichtig, und sie war nie gemessen.** Jetzt ist sie es.

### Die Methode

Über drei Jahre Stundenkerzen (26.280 Stück) wurde jede Stelle gesucht, an der
der Kurs auf einem Hoch stand — genau die Lage, in der eine Position im Gewinn
steht und der Nachzieh-Stopp (Trailing-Stop) greift. Dann: **wie tief fiel er
zurück, bevor er dieses Hoch wieder überschritt?**

Gezählt wurden nur **überlebte** Rücksetzer — solche, nach denen es innerhalb
von 48 Stunden weiterging. Das sind genau die Fälle, in denen ein Ausstieg ein
Fehler war. Ein Hoch, das der Wendepunkt war, zählt nicht mit.

Stundenkerzen, nicht Tageskerzen: die mittlere Haltedauer des Bots liegt bei
**27,6 Stunden** — Tages-Korrekturen sieht er gar nicht.

### Das Ergebnis — BTC, drei Jahre, nach Marktphase

| Marktphase | Fälle | Median | 75 % | 90 % | Stopp 0,80 % übersteht |
|---|---|---|---|---|---|
| EUPHORIA | 1.173 | 0,95 % | 1,58 % | 2,57 % | **39 %** |
| DISTRIBUTION | 2.024 | 0,93 % | 1,55 % | 2,54 % | **41 %** |
| EARLY_BEAR | 692 | 1,09 % | 1,86 % | 2,85 % | **36 %** |
| MID_BEAR | 732 | 0,95 % | 1,60 % | 2,52 % | **40 %** |
| DEEP_BEAR | 120 | 0,98 % | 1,68 % | 2,81 % | **37 %** |
| **zusammen** | **4.741** | **0,96 %** | **1,62 %** | **2,60 %** | **40 %** |

**Der heutige Stopp von 0,80 % wirft den Bot bei sechs von zehn normalen
Rücksetzern aus dem Markt.** Nicht bei Wendepunkten — bei ganz gewöhnlichen
Atembewegungen, nach denen es weiterging.

### Und die Überraschung: die Marktphase spielt fast keine Rolle

Median 0,93 bis 1,09 %. Neunzigstes Perzentil 2,52 bis 2,85 %. **Über alle
fünf Phasen praktisch identisch.**

Das trifft eine Annahme, die im Bot fest verdrahtet ist: `regime_profiles.py`
schrumpft den Stopp im Bärenmarkt auf 0,80 %, weil dort „mehr Vorsicht" nötig
sei. **Die Daten geben das nicht her.** Rücksetzer sind im Bärenmarkt nicht
tiefer als im Bullenmarkt — sie sind gleich tief. Die Verengung macht den Bot
also empfindlicher, ohne dass ein gemessener Grund dafür existiert.

### Gegenprobe mit zwei weiteren Münzen — und sie verschärft das Bild

| Münze | Fälle | Median | 75 % | 90 % | Stopp 0,80 % übersteht |
|---|---|---|---|---|---|
| BTC | 4.741 | 0,96 % | 1,62 % | 2,60 % | **40 %** |
| ETH | 3.330 | 1,36 % | 2,29 % | 3,65 % | **24 %** |
| SOL | 3.244 | 1,62 % | 2,74 % | 4,43 % | **15 %** |

**Bei SOL übersteht der Stopp nur 15 von 100 normalen Rücksetzern.**

Und das ist der zweite blinde Fleck: **der Bot benutzt für alle drei Münzen
denselben Wert.** SOL schwankt fast doppelt so stark wie BTC — ein Stopp, der
für BTC eng ist, ist für SOL absurd eng. Zusammen 11.315 gemessene Fälle.

### Was daraus NICHT folgt

**Nicht:** „also den Stopp auf 2,6 % stellen."

Ein weiter Stopp überlebt mehr Rücksetzer — gibt dafür bei einer echten Wende
mehr zurück. Diese Messung sagt nur, **wie viel Luft eine normale Bewegung
braucht**. Was das unterm Strich bringt, rechnet `ausstieg_vergleich.py` auf
den aufgezeichneten Verläufen aus.

Beide zusammen ergeben erst eine Empfehlung:
* **diese Messung** sagt, wo die Untergrenze liegt (unter ~1 % ist jeder Stopp
  reines Rauschen),
* **der Ausstiegs-Vergleich** sagt, was oberhalb davon am meisten trägt.

### Was daraus folgt

1. **0,80 % ist unterhalb des Medians jeder einzelnen Münze.** Der Stopp löst
   häufiger bei Rauschen aus als bei echten Wenden — unabhängig davon, welche
   Weite am Ende die beste ist.
2. **Die Verengung im Bärenmarkt ist unbegründet.** Sie beruht auf einer
   Annahme, die die Daten nicht stützen.
3. **Ein Wert für drei Münzen ist zu grob.** Die nötige Weite unterscheidet
   sich um den Faktor 1,7 zwischen BTC und SOL — und folgt damit der
   Schwankungsbreite (Volatilität), nicht der Marktphase.

**Priorität:** HOCH · **Risiko** 5/10 · **Aufwand** 3/10 · **Konfidenz:**
SICHER für die Messung (11.315 Fälle, drei Münzen, drei Jahre, Selbsttest in
fünf Richtungen bestanden) · **OFFEN** für die Weite selbst — die braucht die
Gegenrechnung. Werkzeug: `rueckschlaege.py`. Handbuch 4.110.

---

### 67. ⚠️ OFFEN — Die Freigabe-Prüfung misst den Kapitalrückgang aus einer Datei mit 4,2 Stunden Inhalt
**Gefunden am 21.08.2026, weil Sven endlich live gehen will** und die Prüfung
`go_live_check.py` fünf Kriterien als nicht erfüllt meldete. Zwei davon
sahen nach Messfehlern aus. **Einer war es.**

### Der Befund

`go_live_check.py:206` liest den größten Kapitalrückgang (Drawdown) aus
`data_store/equity_history.json`:

```python
eq = _lade_json(_pfad("data_store", "equity_history.json"), {})
```

Diese Datei ist ein **Ringpuffer mit 500 Punkten**. Nachgesehen:

| | |
|---|---|
| Punkte | 500 |
| Zeitraum | **21.08. 00:40 bis 04:50 UTC** |
| **Inhalt** | **4,2 Stunden** |
| höchster Wert darin | 815,65 $ |
| tiefster Wert darin | 623,62 $ |
| daraus errechneter Rückgang | **23,04 %** |

Zum Vergleich die richtige Quelle — dieselbe Kennzahl aus `telemetrie.db`,
gerechnet von `drawdown_auswertung.py`:

| | |
|---|---|
| Messpunkte | **231.765** |
| Zeitraum | seit Beginn der Aufzeichnung |
| größter Rückgang | **13,11 %** |

**Die Grenze liegt bei 15 %.** Die Prüfung blockiert den Live-Gang also mit
einer Zahl aus 4,2 Stunden, während die Messung über den ganzen Zeitraum das
Kriterium **erfüllt**.

### Und die 23,04 % sind zusätzlich verfälscht

Ein Sprung von 815,65 $ auf 623,62 $ innerhalb von vier Stunden bei einem
Kapital von rund 620 $ ist keine Marktbewegung. Es ist derselbe
Doppelzählungs-Effekt wie in **Befund 55**: zwischen der Gutschrift des
Verkaufserlöses und dem Entfernen der Position wird das Kapital doppelt
gezählt. `drawdown_auswertung.py` filtert das heraus
(`offene_positionen IS NOT NULL`), `equity_history.json` nicht.

Die Prüfung nimmt also **die kürzeste verfügbare Zeitreihe und den
verfälschten Wert darin** — und macht daraus ein Ausschlusskriterium.

### Warum das niemandem auffiel

Am 19.08. wurde `drawdown_auswertung.py` gebaut, gerade **weil**
`equity_history.json` als Ringpuffer erkannt wurde. Der Terminal-Reiter,
`stichtag.py` und das Analyse-Cockpit wurden auf die neue Quelle umgestellt.

**`go_live_check.py` wurde dabei übersehen** — die eine Datei, an der die
Freigabe hängt.

> Vier Werkzeuge wurden umgestellt, das fünfte nicht. Genau deshalb ist die
> Frage *„wer benutzt diese Datei noch?"* Teil jeder Umstellung — sie wurde
> hier nicht gestellt.

### Was zu tun ist

`go_live_check.py` muss dieselbe Quelle benutzen wie alle anderen:

```python
import drawdown_auswertung as da
k = da.kapitalkurve()
d = da.drawdown(da.geteilte_kurven(k)[0] if da.zwei_niveaus(k)[0] else k)
```

Das ist eine **reine Messkorrektur** — die Prüfung ändert kein Bot-Verhalten,
sie liest nur. Sie könnte sofort erfolgen. Sie wird trotzdem **nicht während
des Messfensters** gemacht: eine Änderung an genau dem Werkzeug, das über die
Freigabe entscheidet, gehört nicht in einen laufenden Messzeitraum gerechnet,
sondern davor oder danach — und mit Ansage.

**Priorität:** HOCH (blockiert eine Entscheidung mit einer falschen Zahl) ·
**Risiko** 1/10 · **Aufwand** 1/10 · **Konfidenz:** SICHER (beide Zahlen
nachgerechnet, Fundstelle benannt). Handbuch 4.111.

---

### 68. 🔴 KRITISCH FÜR LIVE — Eine Wiederholung nach Zeitüberschreitung kann zweimal kaufen
**Gefunden am 21.08.2026.** Sven kam nicht an die Testnetz-Schlüssel und war
kurz davor, den Probelauf zu streichen. Beim Nachsehen stellte sich heraus:
**die Börsenregeln liefert Binance ohne jede Anmeldung.** Damit ließ sich der
Order-Pfad gegen die echten Regeln prüfen — und dabei fiel genau das auf, wofür
der Testnetz-Lauf gedacht war.

**Im Papiermodus passiert nichts.** Vor dem Live-Gang ist es ein Muss.

### Die Kette

`execution/engine.py:503-508` — so wird die Order gesendet:

```python
def _do():
    if intent.side == Side.BUY:
        return best_exchange.create_market_buy_order(intent.symbol, menge)
    return best_exchange.create_market_sell_order(intent.symbol, menge)

order = self.retry.execute(lambda: self.circuit.call(_do)) or {}
```

`execution/exchange_client.py:56` — was `retry.execute` tut:

```python
for attempt in range(self.max_retries + 1):
    try:
        return func()                    # Order senden
    except self.TRANSIENT_EXCEPTIONS as e:
        time.sleep(delay)                # und nochmal
```

**Bei einer Zeitüberschreitung wird dieselbe Order erneut gesendet.** Und
genau bei einer Zeitüberschreitung ist völlig offen, ob die Börse den ersten
Versuch nicht doch ausgeführt hat — die Antwort ging verloren, die Order nicht
unbedingt.

### Warum die vorhandene Sperre nicht greift

Es **gibt** einen Schutz: `execution/idempotency.py` blockiert doppelte Orders
über eine eindeutige Kennung. `engine.py:168` erzeugt sie:

```python
client_id = self.idempotency.create_id(intent.id, intent.symbol)
result.client_order_id = client_id
if not self.idempotency.check_and_lock(client_id):
    result.status = "rejected"; ...
```

**Und der Order-Lebenslauf aus Handbuch 4.71 ist ebenfalls aktiv** —
gegengeprüft: `engine.py:209` trägt die Order über
`order_manager.place(client_id, ...)` lokal ein, **bevor** sie hinausgeht, und
`fill_reconciler` gleicht sie danach ab. Das ist alles richtig gebaut.

**Die Lücke ist die letzte Meile.** Zwei Punkte:

1. **Die Sperre schützt nur lokal.** Sie prüft, ob `execute()` zweimal
   *aufgerufen* wird. Die Wiederholung passiert aber **innerhalb** eines
   einzigen Aufrufs — unterhalb von `order_manager.place()`, nach der
   Prüfung. Lokal entsteht keine zweite Order; an der Börse schon.

2. **Die Kennung wird nie an die Börse geschickt.** `create_market_buy_order`
   bekommt nur Symbol und Menge. Der Parameter, mit dem Binance einen
   Doppelversuch selbst erkennen würde, heißt `newClientOrderId` — er kommt im
   ganzen Handelspfad **nicht vor** (gegengeprüft: `clientOrderId` steht nur in
   `core/events.py:138` als Feldname und in `engine.py:169` als Zuweisung ans
   Ergebnis).

Anders gesagt: **Der Bot weiß immer, was er gewollt hat. Die Börse weiß nicht,
dass sie es schon einmal gehört hat.**

> Das Feld heißt im Code wörtlich *„Unsere eindeutige ID (Idempotenz!)"* — es
> wird erzeugt, es wird gesetzt, es wird gespeichert. **Nur gesendet wird es
> nicht.**

### Was zusätzlich fehlt

| | fehlt | Folge im Live-Betrieb |
|---|---|---|
| **Auftragsstatus abfragen** | `fetch_order` kommt im ganzen Bot nicht vor | Nach Zeitüberschreitung oder Neustart weiß er nicht, ob die Order durchging. Er kann nicht nachsehen — nur raten |
| **Mindestbetrag prüfen** | `minNotional` wird nirgends geprüft | Binance verlangt **5,00 $** je Order. Bei 147 $ Positionsgröße unkritisch — bei einem Teilverkauf oder kleinem Kapital wird die Order abgelehnt |

Die Rundung auf die Schrittweite (`amount_to_precision`) ist dagegen
vorhanden, ebenso die Behandlung von Teilausführungen. **Zwei von fünf
Prüfungen bestanden.**

### Die Reparatur — drei Zeilen, aber im Handelspfad

```python
def _do():
    p = {"newClientOrderId": client_id}          # die Kennung mitsenden
    if intent.side == Side.BUY:
        return best_exchange.create_order(intent.symbol, "market", "buy",
                                          menge, None, p)
    return best_exchange.create_order(intent.symbol, "market", "sell",
                                      menge, None, p)
```

Damit lehnt Binance den zweiten Versuch von sich aus ab — mit derselben
Kennung wird keine zweite Order angelegt.

**Nicht während des Messfensters.** Es ist der Handelspfad. Und es ist im
Papiermodus wirkungslos, weil dort nichts gesendet wird — es eilt also nicht,
aber es muss **vor** der ersten echten Order stehen.

### Was das für den Probelauf heißt

Svens Wunsch war richtig, und der Fund bestätigt ihn: Frage 2 der
Testnetz-Probe (*„wird bei einer Wiederholung zweimal gekauft?"*) hätte genau
das gezeigt. Nur brauchte es dafür am Ende keine Schlüssel — die
Code-Prüfung gegen die öffentlichen Börsenregeln reichte.

> Eine Testnetz-Order zeigt, **dass** es schiefgeht. Die Code-Prüfung zeigt,
> **wo**.

Prüfbar jederzeit mit `python testnetz_probe.py --ohne-schluessel`.

**Priorität:** KRITISCH vor Live, **null** im Papiermodus · **Risiko** der
Reparatur 2/10 · **Aufwand** 1/10 · **Konfidenz:** SICHER (drei Fundstellen,
Wiederholungsschleife gelesen, Gegenprobe über das ganze Projekt).
Handbuch 4.113.

---

### 69. ⚠️ OFFEN — Die Konfiguration steht auf Binance, gehandelt werden soll bei Bybit EU

**Gefunden am 21.08.2026, weil Sven mich korrigiert hat:** *„ich werde nicht
auf Binance handeln, weil Binance nicht MiCA-reguliert ist."* Das steht seit
Wochen in `CLAUDE.md` §8 — und die Konfiguration weiß nichts davon.

**Nichts davon hatte bisher eine Wirkung.** Der Live-Pfad ist dreifach
verschlossen (siehe unten). Vor der Freigabe muss es trotzdem weg.

### Der Befund — vier Stellen

| Stelle | steht dort | müsste sein |
|---|---|---|
| `data_store/config.json` (laufend) | `"name": "Binance"`, `"ccxt_id": "binance"` | `bybit` |
| `config/settings.py:44-45` | dieselben Werte als Vorgabewert | `bybit` |
| `config/settings.py:64-65` | liest **nur** `BINANCE_API_KEY` / `BINANCE_API_SECRET` | Bybit-Schlüssel |
| `execution/engine.py:138` | `... or ccxt.binance` als Rückfall | `ccxt.bybit` |

Würde jemand den Bot auf `live` stellen und Schlüssel eintragen, verbände er
sich mit **Binance** — der Börse, auf der nicht gehandelt werden soll.

### Und der Kostenrechner widerspricht der Konfiguration

`engine.py:350` rechnet mit **K-BASIS 0,505 %** — das ist der Bybit-EU-Satz
(0,25 % Taker je Seite). Die Verbindung zeigt auf Binance, die Kosten rechnen
mit Bybit. **Zwei Wahrheiten in einem Programm.**

### Warum bisher nichts passiert ist — dreifach gesichert

Gegengeprüft, nicht vermutet:

| Sicherung | Stand heute |
|---|---|
| Betriebsmodus | `paper` — kein Handelsauftrag verlässt das Programm |
| API-Schlüssel | `.env` enthält **keinen einzigen** (Binance nicht, Bybit nicht) |
| Freigabe-Prüfung | `go_live_check.py` meldet NO-GO, `engine.py:115` lehnt den Live-Start ab |

**Alle drei greifen unabhängig voneinander.** Die falsche Börse in der
Konfiguration ist eine Zeitbombe ohne Zünder — sie wird erst gefährlich, wenn
alle drei Sicherungen fallen, und das ist genau der Moment, in dem sie
repariert sein muss.

**Die Kurse dürfen weiter von Binance kommen.** Öffentliche Kurse lesen ist
kein Handeln und berührt MiCA nicht. Das war die Entscheidung vom 13.08. und
sie bleibt.

### Was die Umstellung wirklich kostet

Kein Umbau — vier Zeilen plus eine Prüfung:

1. `ccxt_id` und `name` auf `bybit` (Konfiguration **und** Vorgabewert)
2. `load_api_keys()` auf `BYBIT_API_KEY` / `BYBIT_API_SECRET`
3. Rückfall in `engine.py:138` auf `ccxt.bybit`
4. Log-Text in `engine.py:133` (nennt noch die Binance-Schlüssel)

**Zwei Punkte, die vorher geklärt sein müssen:**

- **Der Doppelkauf-Schutz heißt bei Bybit anders.** Befund 68 nennt
  `newClientOrderId` — das ist Binance. Bybit v5 nennt dasselbe Feld
  `orderLinkId`. Die Reparatur zu 68 muss also **nach** dieser Umstellung
  geschrieben werden, sonst schreibt man sie zweimal.
- **Handelspaare prüfen.** Die Konfiguration handelt in `USDC`. Ob Bybit EU
  für alle 18 Münzen USDC-Paare mit brauchbarer Liquidität führt, ist
  **OFFEN** — nachprüfbar ohne Schlüssel über die öffentliche
  Instrumentenliste.

### Und eine Korrektur in eigener Sache

Handbuch 4.112 behauptet, `BINANCE_API_KEY` und `BINANCE_API_SECRET` kämen
*„im ganzen Programm nicht vor — gegengeprüft"*. **Das ist falsch.** Sie
stehen in `config/settings.py:64-65`. Gemeint war: sie kommen in
`testnetz_probe.py` nicht vor — das stimmt. Geschrieben stand etwas anderes,
und das „gegengeprüft" war eine Behauptung ohne Prüfung. Abschnitt korrigiert.

**Priorität:** HOCH vor Live, **null** heute · **Risiko** 2/10 · **Aufwand**
1/10 (plus Paar-Prüfung) · **Konfidenz:** SICHER (vier Fundstellen gelesen,
laufende Konfiguration ausgelesen, alle drei Sicherungen einzeln geprüft).
Handbuch 4.114.

---

### 70. ⚠️ OFFEN (Freeze) — `LAGE.md` meldet den täglichen Sammler dauerhaft als ausgefallen, obwohl er läuft

**Gefunden 21.08.2026.** Sven widersprach der Anzeige sofort:
*„schattenuniversum.bat sagt aber da alles läuft"* — und hatte recht.

| | |
|---|---|
| **Fundstelle** | `lage_erzeugen.py:93` |
| **Zeile** | `("Täglicher Sammler", "job_sammler"),` |
| **Risiko** | kein Kapital-, kein Datenverlust — reine Anzeige |
| **Wirkung** | Fehlalarm bei jedem, der `LAGE.md` liest |

**Zwei Gründe, beide in derselben Zeile:**

1. `laeuft()` sucht einen **laufenden Prozess**. Der tägliche Sammler
   ist eine geplante Aufgabe, die um 04:00 UTC startet, ~31 Sekunden
   arbeitet und sich beendet. Die Frage „läuft er gerade?" kann für ihn
   fast nie „ja" ergeben.
2. Gesucht wird nach `job_sammler`, in der Telemetrie heißt der Job
   `sammler_taeglich`.

**Beleg, dass er läuft:** Tabelle `jobs` in `telemetrie.db` — 12 Läufe,
jeder Exit-Code 0 / Status OK, letzter am 21.08. 04:00:02 (31,2 s).
`data_store/jobs/sammler_taeglich.log` endet mit
`ENDE - Exit-Code 0, 31.2s`.

**Bereits dokumentiert, nie behoben:** Handbuch 4.69 (19.08.) beschreibt
denselben Fehlalarm. Die Erkenntnis wurde festgehalten, die Anzeige
blieb stehen — und kostete am 21.08. erneut Zeit.

**Korrektur nach dem 29.08.:** Dauerprozesse und geplante Aufgaben
getrennt anzeigen. Für letztere nicht „läuft ein Prozess?", sondern
„wann war der letzte erfolgreiche Lauf?" — die Tabelle `jobs`
beantwortet das bereits. Freeze-sicher, weil reine Anzeige, aber es
besteht kein Anlass zur Eile.

**Bis dahin gilt:** `sammler_pruefen.py` (bzw. `SAMMLER_PRUEFEN.bat`)
ist die verlässliche Quelle. Es antwortet korrekt.

#### Ergänzung 28.08.2026 — derselbe Fehlalarm trifft auch den **Forschungs-Sammler**

*Kein neuer Fund, sondern eine zweite Zeile mit demselben Fehler —
`schon_bekannt.py` hat richtig auf diesen Abschnitt verwiesen.*

`lage_erzeugen.py:92` sucht nach `job_forschung_capture`. Der Prozess
heißt aber **`capture_daemon.py`**. Das Muster kann nie treffen, also
meldet `LAGE.md` dauerhaft „läuft nicht“.

**Zwei unabhängige Belege, dass er sehr wohl läuft** (Stand 28.08. 19:40 UTC):

| Quelle | Aussage |
|---|---|
| Prozessliste | `capture_daemon.py`, PID 3980, seit **59,2 Stunden** |
| `LAGE.md` selbst, Abschnitt *Vorhandene Daten* | „29 Tage, zuletzt **2026-08-28**, 91 Dateien, 18 Münzen“ |

> **Die Datei widerspricht sich also auf derselben Seite:** oben steht
> „läuft nicht“, unten stehen die Daten von heute.

**Damit sind zwei der vier Muster falsch und zwei richtig:**

| Zeile | gesucht | Prozess heißt wirklich | Status |
|---|---|---|---|
| :91 | `app.py` | `app.py` | ✅ trifft |
| :92 | `job_forschung_capture` | **`capture_daemon.py`** | ❌ trifft nie |
| :93 | `job_sammler` | geplante Aufgabe, `sammler_taeglich` | ❌ trifft nie |
| :94 | `schatten_universum` | `schatten_universum.py` | ✅ trifft |

**Korrektur** — zusammen mit der oben beschriebenen, nach dem Stichtag:
`:92` auf `capture_daemon` ändern (eine Zeile, reine Anzeige), und
`:93` auf die Job-Tabelle umstellen statt auf eine Prozesssuche.

**Bis dahin unverändert:** `sammler_pruefen.py` bzw. `SAMMLER_PRUEFEN.bat`
ist die verlässliche Quelle — es hat am 28.08. korrekt „Alle sammeln“
gemeldet, während `LAGE.md` zwei Ausfälle behauptete.

---

### 71. ⚠️ OFFEN — Zwei Werkzeuge, zwei Antworten auf dieselbe Bestandsfrage

**Gefunden 21.08.2026** beim Gegenlesen der Freigabeprüfung.

| Werkzeug | Aussage |
|---|---|
| `go_live_check.py` (H7) | **Abweichung** — BTC 0,0022 vs 0,0014; ETH 0,0276 vs 0,0000; SOL −0,2670 vs 2,1004 |
| `telemetrie_pruefen.py` | **0 Abweichungen** — BTC 0,00139244 passt, SOL 2,10036827 passt |

Beide vergleichen Journal gegen Bestand. Beide können nicht recht haben.

**Warum das zählt:** H7 ist eines der fünf offenen Freigabekriterien.
Vier lösen sich durch Zeit oder das Bybit-Konto; H7 nicht. Ist die
Abweichung echt, steckt ein Rechenfehler im Journal. Ist sie es nicht,
blockiert ein defektes Prüfwerkzeug die Freigabe.

Der SOL-Wert ist der auffälligste: **−0,2670 gegen +2,1004**. Ein
negativer Bestand ist physisch unmöglich — das deutet darauf hin, dass
`go_live_check.py` Käufe und Verkäufe gegeneinander aufrechnet, ohne die
Eröffnungsposition zu berücksichtigen. **VERMUTUNG**, nicht geprüft.

**Nicht entschieden, weil ungeprüft.** Zu klären vor dem 29.08.: welches
der beiden Werkzeuge richtig rechnet. Prüfmuster: beide gegen einen von
Hand nachgerechneten Einzelfall — eine SOL-Position mit bekanntem
Kauf- und Verkaufsdatum.

---

### 72. 🔴 KRITISCH FÜR LIVE — Der Stopp-Knopf bricht ab, bevor der Positionsstand gespeichert wird

**Gefunden 24.08.2026** in einer Protokolldatei, die Sven mitschickte.
**SICHER**, mit Fundstelle.

```
app.py:4357          self.watchdog.stop()
                     AttributeError: 'Watchdog' object has no attribute 'stop'
live/watchdog.py:9   class Watchdog  ->  watch(), check(), get_status()
```

Die Klasse hat kein `stop()`. Sie hatte nie eins. `app.py:4357` ist die
einzige Stelle im Projekt, die es aufruft.

**Warum das zählt:** Alles nach Zeile 4357 wird nie ausgeführt — und dort
steht der Doppelverkauf-Fix vom 13.08.:

| Zeile | Was sie tut | Läuft sie? |
|---|---|---|
| `self._running = False` | sperrt einen zweiten Versuch | ja |
| `self.scheduler.stop()` | hält die Zeitsteuerung an | ja |
| `self.watchdog.stop()` | — | **bricht ab** |
| `self.state_manager.auto_save()` | **sammelt den aktuellen Positionsstand ein** | nein |
| `self.state.save()` | schreibt den Zustand weg | nein |
| `self.bus.shutdown()` | schließt den Nachrichtenweg | nein |

Betroffen sind **alle** Abschaltwege: der Knopf im Cockpit
(`ui/main_window.py:3229`), Strg+C (`_shutdown_handler`) und
`run_forever`.

Weil `self._running = False` **vor** dem Absturz steht, greift beim
zweiten Klick die Sperre in Zeile 2 — der zweite Versuch tut gar nichts
mehr und sieht dabei ruhig aus.

Die Zeile ist älter als der erste Commit (12.08.). Sie war also bereits
vorhanden, als der Doppelverkauf am 13.08. auftrat, den der Fix
verhindern sollte.

**Pflichtprüfung:** `schon_bekannt.py` meldet für `app.py:4357` und
`watchdog.stop` **NEU**. Suche über alle 20 Sitzungen: nichts.

**Nicht repariert — Freeze.** Ein `stop()` nachzurüsten ändert das
Verhalten beim Abschalten und braucht eine Epochengrenze.

**Bis dahin gilt:** Bot nicht über den Knopf stoppen. Im Papierhandel
kostet ein verschluckter Positionsstand falsche Zahlen; live würde der
Bot Münzen verkaufen, die er nicht mehr besitzt. Details in
`BOT-HANDBUCH.md` 4.122.

---

### 73. ✅ BEHOBEN (24.08.) — Ein Sammler konnte laufen und trotzdem woanders hinschreiben

**Gefunden 24.08.2026**, nachdem es bereits zugeschlagen hatte.
**SICHER**, mit Fundstelle.

Eine frühere Sitzung hatte einen Arbeitsordner (Worktree) unter
`.claude/worktrees/sharp-cohen-278314` stehen gelassen — eine vollständige
Projektkopie mit neun eigenen `.bat` und einem leeren `data_store`.

Jede `.bat` beginnt mit `cd /d "%~dp0"` („wechsle in meinen eigenen
Ordner"). Aus der Kopie gestartet, arbeitet sie also **in der Kopie**.

Am 24.08. um 20:00 Uhr beendete die Kopie von `SAMMLER_NEUSTART.bat` die
beiden echten Dauersammler und startete an ihrer Stelle sich selbst.

```
ECHT      17:58:05   2 echt + 16 schatten offen, 18 Zeilen
KOPIE     18:00:08   0 echt +  0 schatten offen,  0 Zeilen
```

**Kosten: 40 Minuten Positionsverlauf und ein Schatten-Lauf, endgültig.**

**Warum es niemand merkte:** `sammler_pruefen.py:215` suchte den
Dateinamen im Text aller laufenden Befehlszeilen. Ein Prozess namens
`positionsverlauf.py` lief ja — nur aus dem falschen Ordner. Die Ampel
blieb grün.

**Behoben** durch `_fremder_ordner()` in `sammler_pruefen.py`: eine
**zusätzliche** Prüfung, aus welchem Verzeichnis ein Sammler gestartet
wurde. Bewusst additiv — eine Verschärfung der vorhandenen Erkennung
könnte einen laufenden Sammler übersehen und doppelt starten.

Gegentest in beide Richtungen bestanden (fremder Prozess → rot mit
Pfadangabe; korrekter Sammler → OK; Warnung nimmt sich zurück;
eingebauter `--selbsttest` bestanden).

**Offen bleibt:** Der Worktree-Ordner selbst muss entfernt werden, sonst
bleibt die Verwechslungsgefahr im Explorer bestehen. Einzigartiger Inhalt
daraus ist nach `archiv/worktree_20260824_gerettet/` gesichert.

Details in `BOT-HANDBUCH.md` 4.121.

---

### 74. ⚠️ OFFEN — Zwei Startdateien suchen den falschen Prozessnamen

**Gefunden 24.08.2026** beim Durchsehen aller `.bat`. **SICHER**.

Die Sammler laufen als `python3.13.exe` (geprüft: PID 3536 und 6056).
Zwei Startdateien suchen aber ausschließlich nach `pythonw.exe`:

| Datei | Zeile sucht | Folge |
|---|---|---|
| `schatten_universum_stop.bat` | `name='pythonw.exe'` | findet nichts, **stoppt nichts** — meldet aber Erfolg (`exit /b 0`) |
| `positionsverlauf_start.bat` | `name='pythonw.exe'` | sieht den laufenden nicht, startet einen **zweiten** |

Der zweite Fall ist der gefährlichere: zwei Positionsverlauf-Sammler
schreiben gleichzeitig in dieselbe Datenbank.

**Nicht repariert.** Beide Dateien werden von `SAMMLER_PRUEFEN.bat` und
`SAMMLER_NEUSTART.bat` ohnehin überflüssig gemacht — die erkennen beide
Prozessarten korrekt. Empfehlung: die zwei Einzeldateien nicht mehr
benutzen.


---

### 75. ⚠️ OFFEN (Freeze) — Vier Objekte werden beim Start gebaut und nie benutzt

**Gefunden 24.08.2026** beim Auffrischen des Rundgangs. **SICHER.**

Im Aufbau des Bots (`app.py`, `__init__`) stehen zwei fast gleiche Blöcke
direkt untereinander:

| | erster Block | zweiter Block |
|---|---|---|
| Bottom-Detector | `app.py:270` | `app.py:285` — überschreibt den ersten |
| Rebalancer | `app.py:277` → `self.portfolio_rebalancer` | `app.py:292` → **`self.rebalancer`** |

Die Importe stehen ebenfalls doppelt (`app.py:47–50`).

**Der eigentliche Punkt ist nicht die Verdopplung, sondern:** Keines dieser
Felder wird jemals *gelesen*. `self.bottom_detector`,
`self.portfolio_rebalancer` und `self.rebalancer` kommen im ganzen `app.py`
ausschließlich auf der **linken** Seite eines Gleichheitszeichens vor.

**Warum es folgenlos bleibt:** Beide Rebalancer werden mit
`enabled=False, dry_run=True` gebaut. Sie könnten also selbst dann nichts
tun, wenn jemand sie benutzte. Es ist verschwendete Arbeit beim Start, kein
Verhaltensfehler.

**Nicht verwechseln** mit `portfolio/agent.py:28`. Das ist ein **anderer**
Rebalancer (Klasse `Rebalancer`, nicht `PortfolioRebalancer`) und wird
tatsächlich benutzt.

**Vorgeschichte:** Im Handbuch stand seit dem Rundgang, die zwei Blöcke seien
„wortgleich" und das zweite Exemplar überschreibe einfach das erste. Für den
Bottom-Detector stimmt das; für den Rebalancer nicht — dort entstehen **zwei**
Objekte in zwei verschiedenen Feldern. Berichtigt in `BOT-HANDBUCH.md`,
Teil 9, Runde 1.

**Pflichtprüfung:** `schon_bekannt.py` meldet für `portfolio_rebalancer` und
`app.py:285` **NEU**.

**Nicht repariert — Freeze.** Aufräumen im Startpfad wäre eine
Verhaltensänderung und braucht eine Epochengrenze. Nach der
Stichtags-Regel blockiert dieser Befund den Live-Weg **nicht**: kein Kapital-
und kein Datenverlust.


---

### 76. ⚠️ OFFEN (Freeze) — Der V4-Kalibrator rechnet mit Zahlen vom 6. Mai

**Gefunden 25.08.2026** beim Nachgehen von Svens Frage, warum fünf
Strategien nie handeln. **SICHER.**

Der V4-Kalibrator bestimmt, wie stark jede der acht Vorgänger-Strategien in
die Kaufwertung eingeht. Er rechnet seine Gewichte bei **jedem Start neu** —
aber aus einer Datei, die stillsteht:

```
app.py:352   V4Calibrator.load('v4_data/strategy_stats.json')
```

| Datei | zuletzt geschrieben |
|---|---|
| `v4_data/strategy_stats.json` — **die Quelle** | **6. Mai 2026, 11:42** |
| `v4_referenz/strategy_stats.json` — der laufende V4-Bot | 24. August 2026, 18:45 |

**Der V4-Referenzbot läuft durchgehend mit und schreibt frische Statistiken
in einen anderen Ordner.** Der Kalibrator sieht sie nie.

**Warum das zählt:** Das V4-Ensemble ist der **größte Einzelposten der
Kaufwertung** — bis zu **+4 Punkte** von drei benötigten
(`agents/signal_agent.py:153-165`). Der Kalibrator entscheidet, wie stark
jede Strategie darin wiegt, und er sperrt Strategien mit Gewicht 0,0
vollständig (`agents/v4_strategies.py:285`).

Gesperrt sind derzeit `STOCHRSI_REVERSAL`, `BOLLINGER_BOUNCE` und
`RSI_DIVERGENCE` — auf Grundlage von V4-Ergebnissen, die dreieinhalb Monate
alt sind.

**Nebenbefund, dieselbe Ursache:** `data_store/v4_strategy_weights.json`
trägt `computed_at: 2026-05-06`. Kein Programmteil schreibt diese Datei
mehr; nur `diagnose.py:163` liest sie. Sie ist eine Momentaufnahme, die wie
ein aktueller Stand aussieht.

**Pflichtprüfung:** `schon_bekannt.py` meldet für
`v4_data/strategy_stats.json`, `app.py:352` und `V4Calibrator.load`
jeweils **NEU**. Suche über alle Sitzungen: nichts.

**Nicht repariert — Freeze.** Die Quelle umzustellen ändert die Gewichte und
damit das Kaufverhalten. Braucht eine Epochengrenze.

**Blockiert den Live-Weg nicht** — kein Kapital- und kein Datenverlust. Es
ist eine Frage der Güte, nicht der Sicherheit. Details in `BOT-HANDBUCH.md`
Teil 5, Abschnitt 5.9.


---

### 77. ✅ BEHOBEN (26.08.) — Zwei Notizbücher schrieben die Entscheidung auf, aber nie den Ausgang

**Gefunden 25.08.2026** beim Abarbeiten von Punkt 6 der Gruppe A. **SICHER.**

*Die Tabellen selbst sind bekannt* (`schon_bekannt.py` meldet BEKANNT, sie
stehen im Handbuch Teil 8, Abschnitt 8.11). **Neu ist, dass ihre
Ergebnisspalte leer ist.**

Der Notizbuch-Modus soll die Frage beantworten: *„Wäre es besser gewesen,
es anders zu machen?"* Dafür braucht es zwei Dinge — was die Regel getan
**hätte**, und wie es danach **ausging**. Zwei von drei Notizbüchern
schreiben nur das Erste auf.

| Notizbuch | Zeilen | Entscheidung | **Ausgang** | auswertbar? |
|---|---:|---|---|---|
| `schatten_exits` | 45 | ja | ✅ `pnl_pct`, `hoechst_pnl_pct` gefüllt | **ja** |
| `schatten_regeln` | **1.994** | ja | ❌ `pnl_pct` **0 von 1.994**, `position_id` **0 von 1.994** | **nein** |
| `schatten_sizing` | 46 | ja | ❌ **es gibt gar kein Ergebnisfeld** | **nein** |

**Was das kostet:** `schatten_regeln` sammelt seit dem 11.08. für das
KI-Modell und den Ensemble-Vergleich — 1.994 Zeilen in vierzehn Tagen. In
dieser Form kann es seine Frage **nie** beantworten. Der Größenrechner
ebenso: 46 Fälle, aber ohne Ergebnis lässt sich nicht sagen, ob kleinere
Positionen besser gewesen wären.

> Es ist genau die Krankheit, die dieses Projekt schon einmal hatte:
> **Ein Sammler, der läuft, ist noch kein Sammler, der sammelt.**

**Behelfsweise nachrechenbar — aber nur für `schatten_regeln`.** Die Zeilen
tragen `symbol`, `ts_utc` und `preis`; `nachlauf.db` hält die Folgekurse
(`r1h`, `r4h`, `r24h`, `r48h`). Über eine Zuordnung nach Münze und Zeit
(Toleranz 2 h) ließen sich am 25.08. **895 von 996** ML-Notizen einem
Folgekurs zuordnen. Das Ergebnis steht im Handbuch Teil 5, Abschnitt 5.10.

Für `schatten_sizing` geht auch das nicht — dort fehlt die Spalte
vollständig, nicht nur der Inhalt.

**Nicht repariert.** Das Nachtragen der Ergebnisspalte ist **reines
Aufschreiben** und wäre freeze-verträglich; es ändert kein Bot-Verhalten.
Aber es braucht eine Entscheidung darüber, **wann** der Ausgang feststeht
(nach 1 h? 24 h? beim Schließen der Position?) — und die gehört Sven.

**Blockiert den Live-Weg nicht.**

---

**BEHOBEN am 26.08.2026.** Statt einer zweiten Nachtrage-Mechanik hängen die
Notizen jetzt an der bereits laufenden: `nachlauf.py:ereignisse_aufnehmen()`
nimmt sie als vierte Ereignisart `'notiz'` auf, `kurse_nachtragen()` füllt
r1h/r4h/r24h/r48h automatisch. Genau so wurde am 20.08. schon die Art
`'schatten'` nachgerüstet.

**Zwei Fehler fielen dabei beim Gegentest an einer Kopie auf — beide behoben:**

1. **`ORDER BY id DESC LIMIT 400`** hätte bei jedem Lauf dieselben neuesten
   400 gegriffen; die älteren 1.684 wären nie an die Reihe gekommen. Jetzt
   wird die höchste bereits übernommene Nummer gelesen und dort
   weitergemacht.
2. **Das Kerzenfenster stand fest verdrahtet auf 200** — bei Stundenkerzen
   rund acht Tage. Die Notizen reichen 15 Tage zurück. Rund drei Viertel
   wären **leer abgehakt** worden, und ein leer abgehaktes Ereignis ist für
   immer verloren (`vollstaendig=1` nimmt es aus der Warteschlange). Jetzt
   `KERZEN = 600`, also 25 Tage.

**Ergebnis im Betrieb:** 2.084 Notizen aufgenommen, **1.946 mit
24-Stunden-Kurs, null leer abgehakt.** Die restlichen 138 sind jünger als
24 Stunden und füllen sich von selbst.

**Horizont 24 Stunden**, von Sven am 26.08. entschieden. Begründung aus den
Daten (29.807 vollständige Blockaden): Bei einer Stunde liegt die typische
Bewegung bei +0,061 % — **achtmal kleiner als die Gebühr von 0,505 %**, und
nur 54,8 % der Fälle bewegen sich überhaupt über die Reibung hinaus. Bei
24 Stunden sind es +2,104 % und 88,4 %. Alle vier Horizonte werden weiter
mitgeschrieben; 24 h ist nur das Urteilsmaß.

**Was die Messung ergab:** kein Vorsprung bei der Richtung — 30,8 % gegen
30,8 % Trivial-Latte. Details in `BOT-HANDBUCH.md` Teil 5, Abschnitt 5.10.

**`schatten_sizing` ist ebenfalls beantwortet — ohne Codeänderung.** Die
Notizen tragen keine Positionsnummer, aber einen exakten Schlüssel: Münze,
Zeitpunkt und **Betrag auf den Cent**. Damit ließen sich **39 von 50**
Notizen eindeutig einem Kauf zuordnen (null mehrdeutig) und 37 bis zum
Verkauf verfolgen.

**Ergebnis:** Der Größenrechner hätte über 37 Positionen **8,30 $ gekostet**
(+5,86 $ statt +14,16 $) und lag damit **unter der Trivial-Latte**
„immer halbe Größe" (+7,08 $). Er verkleinerte die **Gewinner** auf 35,4 %,
die Verlierer nur auf 46,7 % — genau verkehrt herum.

**Einschränkung, die dazugehört:** 35 Gewinner gegen 2 Verlierer. In einer
solchen Phase verliert jede Verkleinerung Geld; wofür der Rechner gebaut ist,
wurde nie geprüft. Empfehlung: weiter mitlaufen lassen, erneut ansehen ab
zehn Verlierern. Details in `BOT-HANDBUCH.md` Teil 6, Abschnitt 6.6.

**Damit ist Befund 77 in beiden Teilen erledigt** — das KI-Modell über den
Nachlauf, der Größenrechner über den Betragsschlüssel. Eine Ergebnisspalte
in `schatten_sizing` bleibt wünschenswert, ist aber nicht mehr nötig.


---

### 78. ⚠️ OFFEN (Freeze) — Die Sperrregel des Kalibrators ist ein Schalter genau auf der Nulllinie

**Gefunden 26.08.2026** bei der Vormessung zu `OFFEN.md` Gruppe C,
Punkt 8a. **SICHER.**

`models/v4_calibrator.py:86` entscheidet über die vollständige Sperre einer
Strategie:

```python
if total_pnl <= 0:
    self.weights[sid] = 0.0
```

**Kein Puffer, keine Mindestfallzahl, keine Rücksicht auf die
Schwankungsbreite.** Genau null ist die Grenze.

**Warum das zählt:** Der Kalibrator bestimmt, wie stark jede Strategie im
V4-Ensemble wiegt — und das ist mit bis zu **+4 Punkten** von drei
benötigten der größte Einzelposten der Kaufwertung
(`agents/signal_agent.py:153`).

**Nachgemessen an `RSI_OVERSOLD`:**

| Tag | netto | Gewicht |
|---|---:|---:|
| 25.08.2026 | **−57,86 $** | 0,00 — gesperrt |
| 26.08.2026 | **+2,55 $** | 0,40 — freigegeben |

Die Schwankungsbreite dieser Summe liegt bei **±100 $**. Ein einziger
Handelstag des mitlaufenden V4-Bots dreht die Entscheidung.

**Zusammenhang mit Befund 76:** Solange die Quelle eingefroren ist (Stand
6. Mai), fällt das nicht auf — die Gewichte ändern sich nie. Wird die
Quelle auf den laufenden V4-Bot umgestellt, wie in `OFFEN.md` 8a
vorgesehen, **wackelt die Sperre ab dann täglich**.

**Die belastbaren Fälle sind davon nicht betroffen.** Nachgerechnet für
alle zwölf Strategien: Sechs liegen so weit im Minus, dass das Vorzeichen
gesichert ist (ICHIMOKU_CLOUD −648 ± 211, EMA_TREND −552 ± 118 und vier
weitere). Drei liegen innerhalb ihrer eigenen Schwankung — darunter beide,
die heute als Gewinner gelten.

**Pflichtprüfung:** `schon_bekannt.py` meldet für `v4_calibrator.py:86` und
`total_pnl <= 0` **NEU**. Suche über alle Sitzungen: nichts.

**Nicht repariert — Freeze.** Empfehlung für den Stichtag: Punkt 8a **nur
zusammen mit einer entschärften Regel** ausführen — Sperre erst, wenn der
Verlust größer ist als die eigene Schwankungsbreite, und erst ab 30 Fällen.
Sonst wird eine veraltete Zahl gegen eine zittrige getauscht.

**Blockiert den Live-Weg nicht.** Details in `BOT-HANDBUCH.md` Teil 5,
Abschnitt 5.11.


---

### 79. ⚠️ OFFEN — Die Trivial-Latte im Ausstieg-Vergleich mischt zwei verschiedene Fragen

**Gefunden 26.08.2026** beim Abarbeiten von `OFFEN.md` Gruppe C,
Punkt 22. **SICHER.**

`ausstieg_vergleich.py` meldet, dass **alle acht** Ausstiegsregeln gegen die
Trivial-Latte „Halten" verlieren:

```
Halten (Trivial-Latte)      +6.063%   Latte selbst
Bot heute                   +2.001%   -4.062 PP  schlechter
Chandelier ATRx3            +3.220%   -2.843 PP  schlechter
Festes Ziel +2 %            +0.473%   -5.590 PP  schlechter
```

**Diese Zeile trägt kein Urteil.** Sie rechnet über 49 Verläufe aus zwei
Beständen, deren Aufzeichnung **unterschiedlich lange** läuft:

| Herkunft | n | Aufzeichnung, Median | „Halten" bis Ende |
|---|---:|---:|---:|
| **echte Positionen** | 36 | **4,6 h** | **+0,645 %** |
| **Schattenpositionen** | 32 | **99,4 h** | **+10,012 %** |

**Faktor 21 in der Beobachtungsdauer.** Bei echten Positionen endet die
Aufzeichnung, wenn der Bot verkauft — „Halten" heißt dort also *„halten,
bis der Bot ohnehin verkauft"*. Bei Schattenpositionen läuft sie bis
`MAX_TAGE = 7` durch.

Die **+6,063 %** stammen damit fast vollständig aus den Schattenpositionen
und aus einem steigenden Markt. Verglichen wird nicht „Regel gegen Halten",
sondern **„vier Stunden gegen vier Tage"**.

**Das Werkzeug warnt selbst davor** — direkt unter der Tabelle steht der
Hinweis, dass die Aufzeichnung echter Verläufe beim Verkauf endet. Die
**Urteilsspalte** berücksichtigt es nur nicht.

> Eine Trivial-Latte muss dieselbe Frage beantworten wie das, was sie
> schlagen soll. Sonst ist sie keine Latte, sondern ein anderes Rennen.

**Pflichtprüfung:** `ausstieg_vergleich.py` ist **BEKANNT** (13 Fundstellen),
der Mischfehler in der Latte ist **NEU**; Suche über alle Sitzungen: nichts.

**Nicht repariert.** Zwei Wege, beide reines Aufschreiben und
freeze-verträglich:

1. **Getrennt ausweisen** — je eine Tabelle für echte und für
   Schattenverläufe. Die einfachere Lösung.
2. **Auf gleiche Dauer stutzen** — jeden Verlauf nach derselben Zeitspanne
   abschneiden. Sauberer, kostet aber die langen Schattenverläufe, die
   gerade den Vergleich „später aussteigen" erst möglich machen.

**Folge für Punkt 22:** Die Frage *„welche Ausstiegsregel wäre besser
gewesen"* bleibt **unbeantwortet**. Für die Richtung „früher aussteigen"
reichen die 36 echten Verläufe; für „später aussteigen" braucht es die
Schattenverläufe — und beide Richtungen dürfen nicht in einer Zahl landen.


---

### 80. ✅ BEHOBEN (26.08.) — Die Laufzeit der Hintergrund-Aufträge wurde nie gemessen

**Gefunden 26.08.2026** beim Abarbeiten von `OFFEN.md` Gruppe D,
Punkt 1. **SICHER.**

Die Tabelle `jobs` führt eine Spalte `laufzeit_sek`. Sie stand bei fast
allen Einträgen auf **genau 0,0**:

| Auftrag | Einträge mit `laufzeit_sek = 0` | von |
|---|---:|---:|
| `zahlenbuch_morgen` | **42** | 43 |
| `forschung_capture` | **1.722** | 2.036 |
| `sammler_taeglich` | 0 | 21 |

**Die Ursache war kein Fehler in der Schreibfunktion.** In
`job_zahlenbuch.py` standen `job_start()` und `job_ende()` direkt
hintereinander — **beide nach getaner Arbeit**. Damit war `start == ende`.

Die Dauer war sogar bekannt: `in_telemetrie(name, alle, dauer)` bekam sie
als Parameter herein und benutzte sie nie.

> Eine Spalte, die „0,0" zeigt, sagt *„hat keine Zeit gebraucht"*. Gemeint
> war *„nicht gemessen"*. Das ist der Unterschied zwischen einer Lücke, die
> auffällt, und einer, die wie ein Messwert aussieht.

**Behoben.** `core/telemetrie.py:618` nimmt jetzt einen optionalen
Parameter `start_utc`; ohne Angabe bleibt alles wie bisher, sodass **kein
bestehender Aufrufer betroffen ist** — auch nicht der laufende Bot, der
diese Datei erst bei einem Neustart neu liest. `job_zahlenbuch.py` reicht
den echten Startzeitpunkt nach.

**Gegenprobe gegen einen bekannten Wert:** Der Lauf vom 26.08. um 12:56
meldete im Protokoll *„Fertig in 78s"*. Die Tabelle trägt jetzt
**77,7 Sekunden** — vorher 0,0.

**Was damit beantwortet ist (Gruppe D, Punkt 1):** `sammler_taeglich`
braucht im Schnitt **22,7 Sekunden**, im längsten Fall 39,9. Die einst
gemessenen 14 Minuten waren **fremde Last**, wie vermutet.

**Offen bleibt `forschung_capture`.** Dort misst die Spalte etwas anderes:
Die längsten Einträge stehen bei bis zu **178.580 Sekunden** (rund zwei
Tage) — das sind ganze Daemon-Sitzungen, keine Einzelläufe. Die Zahl ist
richtig, beantwortet aber eine andere Frage.


---

### 81. ⚠️ OFFEN — Die Chartanalyse zielt zu kurz, und ihre Gütezahl sagt nichts

**Gefunden 26.08.2026**, als Sven bat, ihm den Analyse-Reiter zu
erklären. **SICHER.**

#### Teil 1 — das Ziel ist oft dieselbe Zone, die das Signal ausgelöst hat

Zwei Zeilen in `features/chartanalyse.py` passen nicht zusammen:

```python
:359   ueber = [z for z in zonen if z.preis > preis]   # Mitte oben  -> "Widerstand"
:404   fuer_retest = [z for z in res_zonen if z.enthaelt(preis)]  # Kurs IM Band
```

Eine Zone, deren **Mitte** über dem Kurs liegt, deren **Band** ihn aber
umschließt, ist damit **gleichzeitig Auslöser und Kursziel**. Die Chance
schrumpft auf den halben Zonenabstand, das Risiko reicht unter das ganze
Band plus eine halbe Schwankungsbreite.

**Gemessen an allen 117.199 Signalen:**

| Signalart | Median Chance/Risiko | erreicht 1,5 |
|---|---:|---:|
| SUPPORT_BOUNCE | **0,342** | **1,9 %** |
| RETEST | 0,417 | 6,3 % |
| BREAKOUT | 0,367 | 12,5 % |

Das Werkzeug schreibt selbst in seine Ausgabe *„unter 1.5 lohnt sich nach
Kosten selten"* — und erreicht diese Schwelle in **unter 13 %** der Fälle.

#### Teil 2 — die Gütezahl hat keinen messbaren Wert

`einstieg_guete` ist die Zahl, die im Reiter am größten angezeigt wird.
Gerechnet über **2.589 einzigartige** Signale (die 117.199 enthalten
dieselbe Kerze 45-fach):

| Filter | n | Trefferquote | EV netto |
|---|---:|---:|---:|
| alles nehmen | 2.589 | 71,1 % | **−0,455 %** |
| **nur Güte ≥ 0,8** | 1.369 | 72,9 % | **−0,406 %** |
| nur Chance/Risiko ≥ 1,5 | 105 | 37,1 % | **+0,395 %** |
| nur Chance/Risiko ≥ 2,0 | 55 | 34,5 % | **+0,772 %** |

**Ein Filter auf die Güte verbessert das Ergebnis um 0,05 Prozentpunkte** —
bei 1.369 Fällen, also belastbar gemessen. Das ist nichts.

**Das Chance/Risiko-Verhältnis dreht dagegen das Vorzeichen**, und die
Trefferquote fällt dabei von 71 % auf 35 %.

> Die beste Regel, die sich in diesen Daten finden lässt, trifft nur jedes
> dritte Mal — und verdient trotzdem Geld. Wer nach Trefferquote optimiert,
> optimiert in die falsche Richtung.

**Pflichtprüfung:** `rr_verhaeltnis` und `einstieg_guete` melden **NEU**;
Suche über alle Sitzungen: nichts.

**Nicht repariert.** Die Chartanalyse ist Beobachtungsdeck und löst keinen
Handel aus — es besteht **keine Eile**. Zwei Wege, beide reines
Aufschreiben:

1. **Zielwahl korrigieren** — als Kursziel nur Zonen nehmen, deren
   **Unterkante** über dem Kurs liegt. Danach neu messen.
2. **Signale unter einem Mindest-Chance/Risiko gar nicht erst melden.**

**Belastbarkeit:** Die Aussagen zu „verliert" beruhen auf 1.369 bis 2.589
unabhängigen Fällen und sind gesichert. Die Aussagen zu „+0,395 %" und
„+0,772 %" beruhen auf **105 und 55** Fällen und sind **nicht
entscheidbar** — sie zeigen eine Richtung, keine Gewissheit.

Details in `BOT-HANDBUCH.md` Teil 6, Abschnitt 6.9.

---

### 82. ⚠️ OFFEN — Das Schatten-Universum wirft 97,5 % seiner eigenen Daten weg

**Gefunden 26.08.2026** bei Svens Frage, ob mehr Schattenwächter nötig
sind. **SICHER.**

Der Sammler erzeugt Signale und verfolgt sie als Papierpositionen. Nur
verfolgt er fast keine:

```
Signale im Schatten-Universum : 1.266
daraus Positionen             :    32   = 2,5 %
verworfen                     : 1.234
```

**Der Grund ist die Bauart:** Je Münze ist immer nur **eine**
Schattenposition offen, und sie läuft bis zu `MAX_TAGE = 7` Tage. Ein
neues Signal derselben Münze in dieser Zeit wird verworfen.

**Was das kostet:** Für 30 unabhängige Fälle je Münze — die Mindestzahl
dieses Projekts — braucht es damit **210 Tage**. Die Münzfrage aus
`OFFEN.md` Gruppe C, Punkt 4 ist deshalb bis zum Stichtag nicht
beantwortbar (Teil 6, Abschnitt 6.2).

**Was eine höhere Grenze brächte:**

| gleichzeitige Positionen je Münze | Positionen je Tag | 30 Fälle je Münze in |
|---:|---:|---:|
| **1 (heute)** | 2,6 | **210 Tage** |
| 3 | 7,7 | 70 Tage |
| 5 | 12,9 | **42 Tage** |
| 10 | 25,7 | **21 Tage** |

**Signale sind reichlich da:** 9 bis 13 je Münze und Tag.

> **Es fehlt kein Schattenwächter. Der vorhandene wirft weg, was er selbst
> erzeugt.**

**Pflichtprüfung:** `MAX_OFFEN` meldet **NEU**; Suche über alle Sitzungen:
nichts.

**Nicht repariert.** Es ist **reines Aufschreiben** — der Sammler handelt
nicht —, aber es ändert das Verhalten des Sammlers und braucht deshalb eine
saubere Entscheidung: Ab wann gilt eine Position als „dieselbe Gelegenheit"
und ab wann als neue? Ohne diese Abgrenzung entstehen Scheindaten, die
dasselbe Ereignis mehrfach zählen — genau der Fehler aus Teil 8,
Abschnitt 8.9, Fall 1.


---

### 83. ✅ BEANTWORTET (27.08.) — Eine Chartmethode lässt sich aus ihren Zahlen nicht zurückrechnen

**Gefunden 27.08.2026** auf Svens Auftrag, ein Werkzeug zu bauen, das aus
Tilos bekannten Prognosezahlen sein Verfahren ermittelt. **SICHER.**

Das Werkzeug steht: `prognose_ruecktechnik.py`. Es probiert alle gängigen
Chart-Verfahren durch, die mit den Kursen **von damals** möglich waren —
Fibonacci-Rückgänge, -Verlängerungen und -Projektionen über alle
Swing-Paare, runde Zahlen, Prozentaufschläge, Vielfache des Hochs. Es
achtet dabei auf Kausalität: Ein Swing-Hoch gilt erst als bekannt, wenn die
bestätigenden Kerzen gelaufen sind.

**Das Ergebnis ist ein Nein — und zwar ein belegtes.**

#### Versuch 1: eine einzelne Zahl (Tilo, BTC-Ziel 123.000 $)

| Toleranz | Treffer beim echten Ziel | Treffer bei einem **gewürfelten** Ziel |
|---:|---:|---:|
| 0,50 % | 115 | **79,4** |
| 0,10 % | 23 | **15,7** |
| 0,02 % | 5 | **3,1** |
| 0,01 % | 5 | 1,5 |

Bei 17.238 durchprobierten Rechnungen wird **fast jede Zahl erklärt**. Erst
bei ±12 $ Toleranz löst sich der echte Wert überhaupt vom Rauschen — und
dort bleiben nur zwei verschiedene Rechnungen übrig, was für eine
Identifikation nicht reicht.

#### Versuch 2: neun Zahlen aus einem Chart (Mark, Wochenchart)

Der stärkere Ansatz: Nicht eine Rechnung für eine Zahl suchen, sondern
**ein Raster, das viele Zahlen gleichzeitig erklärt.** Marks vier Bilder vom
19.08.2026 liefern neun Marken: 48.199 · 44.225 · 39.014 · 18.223 · 5.891 ·
77.015 · 69.048 · 65.025 · 37.079.

Geprüft wurden 3.481 Hoch-Tief-Raster auf Wochenkerzen seit 2017:

| Toleranz | bestes Raster erklärt von Marks 9 | von **9 gewürfelten** Zahlen |
|---:|---:|---:|
| 0,50 % | 5 | **4,8** (Höchstwert 6) |
| 0,20 % | 4 | 3,5 (Höchstwert 5) |
| 0,10 % | 3 | 2,7 (Höchstwert 4) |
| 0,05 % | 2 | 2,2 |

**Auf keiner Stufe unterscheiden sich Marks echte Marken von Zufallszahlen.**

#### Warum das so ist

Ein Fibonacci-Raster über ein Hoch-Tief-Paar erzeugt **40 Linien**. Bei 59
Hochs und 59 Tiefs sind das über 139.000 Linien im Kursbereich. Dieses Netz
ist so dicht, dass es jede Zahlenmenge einfängt.

> **Eine Methode, die alles erklären kann, erklärt nichts.** Der Nachweis,
> dass jemand mit Fibonacci arbeitet, lässt sich aus seinen Ergebniszahlen
> grundsätzlich nicht führen — nicht weil das Werkzeug zu schwach wäre,
> sondern weil der Suchraum zu reich ist.

#### Was daraus folgt — und was es bestätigt

Die Regel, die in `prognosen/TILO.md` und `MARK.md` seit dem 15.08. steht,
ist damit **gemessen bestätigt**: Eine Prognose zählt nur mit **Datum,
genauer Zahl, genauer Frist und Ist-Kurs**. Man kann eine Methode nicht
nachträglich aus den Zahlen erschließen — man muss sie sich **vorher**
sagen lassen und dann messen, ob sie trifft.

**Pflichtprüfung:** `prognose_ruecktechnik` und `Fibonacci Raster` melden
**NEU**; Suche über alle Sitzungen: nichts.

**Das Werkzeug bleibt nützlich** — aber für die umgekehrte Frage: Wenn Tilo
oder Mark eine Methode **nennen**, rechnet es nach, ob ihre Zahlen daraus
folgen. Selbsttest in beide Richtungen bestanden (findet, was da ist;
meldet nicht, was fehlt; erkennt ein zu grobes Netz selbst).

#### Nachtrag vom 27.08. — die Suche war zusätzlich im falschen Raum

Wenige Stunden nach diesem Befund schickte Sven **zwei Chartbilder von
Tilo** — das alte vom 07.05.2025 und ein aktuelles. Beide zeigen dasselbe:

**Dreiecke, Keile und Trendlinien durch Wendepunkte. Kein einziges
Fibonacci-Raster.**

Damit hat die Suche nicht nur ein zu dichtes Netz gehabt, sondern auch
**das falsche Netz**. Sie probierte Fibonacci-Verhältnisse durch; die
gesuchte Methode ist Geometrie.

Der Unterschied ist wesentlich: Ein Fibonacci-Raster liefert **Kurse**.
Zwei sich schneidende Trendlinien liefern **Kurs und Zeitpunkt** — und
genau das erklärt, warum Tilo im neuen Bild Kästen mit Uhrzeit setzen
kann (*„FREITAG AB 19 UHR"*, *„SAMSTAG AB 7"*).

**Klarstellung durch Sven, 27.08.:** *„Mark arbeitet mit Fibonacci, nicht
Tilo."* Damit zerfällt der Befund in zwei Teile, und nur einer davon trägt:

| | Methode | Suchraum war | Ergebnis |
|---|---|---|---|
| **Tilo** | Geometrie (Keile, Trendlinien) | **falsch** — Fibonacci | sagt gar nichts aus |
| **Mark** | **Fibonacci** | **richtig** | trotzdem nicht von Zufall zu trennen |

**Der Mark-Teil ist damit der eigentliche Befund** — und er wiegt schwerer
als gedacht: Selbst als im **richtigen** Verfahren gesucht wurde, waren
seine neun Marken von neun gewürfelten Zahlen nicht zu unterscheiden. Das
liegt allein an der Dichte des Rasters, nicht an einer falschen Annahme.

**Der Tilo-Teil ist hinfällig.** Dass die Suche seine 123.000 nicht erklären
konnte, beweist nichts — sie hat im falschen Raum gesucht.

**Was gültig bleibt:** Auch ein Geometrie-Netz wäre zu dicht, um aus
Ergebniszahlen zurückgerechnet zu werden — bei freier Wahl der Ankerpunkte
gibt es noch mehr Geraden als Fibonacci-Linien. Der Weg bleibt:
**Methode nennen lassen, dann messen.**

Erste Messung dazu steht in `prognosen/TILO.md`: Seine Spanne
76.067–78.678 fing **44,9 %** der Stunden ein, eine zufällig gesetzte
Spanne gleicher Breite nur **20,3 %**. Auffällig — aber 14,6 % der
Zufallsspannen waren genauso gut, also **noch kein Beweis**.


---

### 84. ✅ BEANTWORTET (27.08.) — MACD und PVSRA bringen auf Stundenkerzen nichts

**Gemessen 27.08.2026** auf Svens Auftrag, Marks Indikatoren
nachzurechnen. Zwei neue Werkzeuge: `macd_zeitrahmen.py` und `pvsra.py`,
beide mit Selbsttest in beide Richtungen bestanden. **SICHER.**

#### MACD 12/26/9 über vier Zeitrahmen (BTC/USDT, ab 2019)

Mark benutzt MACD 12/26/9 auf **Wochenkerzen**, unser Bot denselben
Indikator mit denselben Einstellungen auf **Stundenkerzen** — Faktor 168.

| Zeitrahmen | unabh. Kreuze | MACD | Trivial-Latte | Vorsprung |
|---|---:|---:|---:|---:|
| **1 h** *(unser Bot)* | 1.592 | **−0,265 %** | **−0,347 %** | +0,082 PP |
| 4 h | 542 | −0,088 % | −0,180 % | +0,092 PP |
| 1 d | 97 | +1,061 % | +0,767 % | +0,294 PP |
| **1 w** *(Mark)* | 13 | +5,823 % | +5,443 % | +0,380 PP |

**Der Vorsprung wächst gleichmäßig mit dem Zeitrahmen** — aber auf
**keinem** schlägt MACD die Latte belastbar.

**Der eigentliche Befund steht in der Latten-Spalte.** Gegengeprüft an
drei Münzen, Horizont 24 Stunden:

```
BTC  -0,347 %      ETH  -0,351 %      SOL  -0,119 %
```

**Auf Stundenbasis verliert man Geld, ganz ohne Indikator** — bei 1.188
bis 1.592 unabhängigen Fällen je Münze. Der Kursanstieg über 24 Stunden
deckt die 0,505 % Reibung nicht.

Die Wochenwerte schwanken dagegen zwischen **−4,055 PP** (ETH) und
**+35,030 PP** (SOL) bei 8 bis 13 Fällen — reines Rauschen.

#### PVSRA, nachgebaut (BTC/USDT, 1 h, 49.496 Kerzen)

Der Indikator, den Mark im Bild ausgewählt hatte und den wir als
einzigen seiner acht nicht hatten. Standardregel: Volumen × Spanne
≥ 2,0 × Mittel der letzten zehn Kerzen → Klimax.

| Kerzenart | Anteil | EV netto | gegen Latte | Urteil |
|---|---:|---:|---:|---|
| klimax_auf | 7,3 % | **−0,446 %** | −0,038 PP | kein Unterschied |
| klimax_ab | 7,9 % | −0,364 % | +0,044 PP | kein Unterschied |
| steigend_auf | 2,0 % | −0,244 % | +0,164 PP | kein Unterschied |
| steigend_ab | 1,9 % | −0,399 % | +0,008 PP | kein Unterschied |
| normal | 80,9 % | −0,413 % | −0,005 PP | kein Unterschied |
| **alle (Latte)** | 100 % | **−0,408 %** | — | |

**Keine einzige Kerzenart unterscheidet sich von der Latte.** Die
stärkste Klimax-Kerze — das Kaufsignal des Indikators — ist mit
−0,446 % sogar minimal schlechter als beliebige Kerzen.

#### Was daraus folgt

> **Es liegt nicht am Indikator, sondern am Zeitrahmen.** Auf
> Stundenbasis frisst die Reibung von 0,505 % je Runde mehr, als der
> Markt in 24 Stunden im Mittel hergibt. Ein Indikator kann daran nichts
> ändern — er wählt nur aus, er erzeugt keine Bewegung.

Das deckt sich mit allem anderen in diesem Projekt: der Chartanalyse
(0 von 245 Läufen netto positiv, Befund 81), den Ausstiegsregeln (Teil 3)
und dem V4-Referenzbot (75,6 % Trefferquote, netto −108 $).

**Nicht repariert, nichts zu reparieren.** Das Ergebnis ist eine Absage
an zwei Kandidaten — genau wofür die Messung da ist. `pvsra.py` bleibt
im Werkzeugkasten, falls die Frage auf einem anderen Zeitrahmen neu
gestellt wird.


---

### 85. ✅ BEHOBEN (27.08.) — Der Fibonacci-Rechner war toter Code, und die Ankerwahl zweimal falsch

**Fundstelle:** `features/chartanalyse.py:236` (`fibonacci_ziele`),
`ui/chartanalyse_tab.py` (`_zeichne`).

**Konfidenz: SICHER** — im Code nachgewiesen, danach gezeichnet und gezählt.

**Der Fund.** `fibonacci_ziele()` stand seit Anlage der Datei im Code, mit
Docstring und Rückgabewert. Aufgerufen hat sie **niemand**. `analysiere()`
reichte das Ergebnis nicht in die `Analyse` weiter, das Datenfeld gab es gar
nicht. Wer den Code liest, hält Fibonacci für eine aktive Funktion des Bots
— sie war nie eine.

> Das ist die gefährlichere Sorte toter Code: nicht auskommentiert, nicht
> als stillgelegt markiert (CLAUDE.md 4.5), sondern **vollständig und
> plausibel** — nur eben nirgends angeschlossen.

**Behoben** auf Svens Auftrag *„fang an mit linien zeichnen!"*: Die Funktion
rechnet jetzt bei jedem Bildaufbau mit, `Analyse` hat ein Feld `fibonacci`,
und der Chart zeichnet die Stufen selbst. Beschreibung in Handbuch 6.9,
Abschnitt *Die violetten Linien*.

**Zwei Folgefehler bei der Ankerwahl — beide erst an echten Daten sichtbar:**

| | Was gewählt wurde | Was dabei herauskam |
|---|---|---|
| 1 | die **jüngsten** Wendepunkte | Spanne 682 $ auf 80.500 = **0,85 %**. Alle 13 Stufen lagen als **eine einzige Linie** übereinander |
| 2 | die **Extreme über alle 300 geladenen** Kerzen | Der Chart zeigt nur 150. Auf Stundenkerzen lag das Ankertief bei 62.716, der sichtbare Bereich begann erst bei 75.190 — **11 von 13 Stufen unter dem Bildrand, gezeichnet wurden 2** |

**Die Lösung** ist beides zugleich: die **Extreme innerhalb der angezeigten
150 Kerzen**. Das entspricht auch Marks eigenem Vorgehen — in seinem
30-Minuten-Chart vom 19.08. lagen seine Anker 59 Kerzen auseinander, bei
64.545 und 62.671, den äußersten Punkten des Bildes.

Die Zahl 150 steht deshalb nur noch an **einer** Stelle
(`ui/chartanalyse_tab.py`, `ZEIGE_KERZEN`) und bestimmt Bildausschnitt und
Ankersuche gemeinsam.

**Nachweis nach der Korrektur** — 3 Münzen × 5 Zeitrahmen, jeweils wirklich
gezeichnet und vermessen:

| | BTC | ETH | SOL |
|---|---|---|---|
| 15m | 9 Linien · 4,7 % | 9 · 5,2 % | 9 · 14,2 % |
| 30m | 10 · 4,5 % | 9 · 5,9 % | 9 · 14,2 % |
| 1h | 9 · 7,0 % | 9 · 8,2 % | 9 · 20,7 % |
| 4h | 9 · 23,3 % | 9 · 28,8 % | 9 · 30,2 % |
| 1d | 9 · 30,2 % | 9 · 40,9 % | 9 · 38,9 % |

Alle 15 Fälle sauber: keine schiefe Linie, keine außerhalb des Bildes, das
engste Linienpaar 15,1 px auseinander, die engsten zwei Beschriftungen
12,4 px. Damit ist Svens Bedingung erfüllt, dass es *„nicht nur bei den
Tageskerzen"* funktioniert.

**Was das Verfahren angeht, nicht den Fund.** Beide Fehler hätten einen
Syntaxtest bestanden. Der erste fiel auf, als die *Spanne* nachgerechnet
wurde; der zweite erst, als der Chart in einem unsichtbaren Fenster wirklich
gezeichnet und die Linien **gezählt** wurden. Beim ersten Anlauf zählte
dieses Prüfwerkzeug selbst falsch — die Farbwerte darin waren **geraten**
statt aus dem Code geholt, dadurch erkannte es 9 Linien als 1. Erst nach dem
Eichen und einem Gegentest gegen den bekannt kaputten Zustand (der 2 von 13
meldet und anschlägt) war die Messung belastbar.

> **Ein Bild, das entsteht, ist noch kein Bild, das stimmt.**

**Ungemessen bleibt:** ob Fibonacci überhaupt trägt. Der Reiter ist
Beobachtungsdeck (Befund 81, Handbuch 6.7), es wird nichts gehandelt. Die
Messung steht in `OFFEN.md` und braucht die Epochengrenze nach dem 18.09.

#### Nachtrag 28.08. — ein dritter Ankerfehler, gefunden durch Marks Zahlen

Sven schickte zehn Bilder vom **30.04.2026**, vier davon mit vollständig
lesbaren Fibonacci-Zahlen. Sie deckten einen Fehler auf, den **keine
Messung am eigenen System** hätte finden können.

**Der Fehler:** Der Code rechnete fest `hoch − spanne × r`, legte die Null
also **immer ans Hoch**. Richtig ist: **Die Null liegt am Ende der
Bewegung**, und welcher Anker das Ende ist, entscheidet die **Zeit**.

| Bewegung | zuletzt | 0 liegt | Stufen laufen |
|---|---|---|---|
| aufwärts (Tief zuerst) | das Hoch | am Hoch | nach unten |
| abwärts (Hoch zuerst) | das Tief | am **Tief** | nach **oben** |

Marks August-Charts waren der erste Fall, seine April-Charts der zweite —
die Umsetzung konnte nur einen davon.

**Beleg, durch die echte Funktion gerechnet:** vier seiner Raster vom 30.04.,
achtzehn Stufen, **größte Abweichung 0,01 $**. Dazu die Gegenprobe mit
denselben Ankern in umgekehrter Reihenfolge — die Stufen spiegeln sich, wie
sie sollen. Vorher lieferten beide Richtungen dasselbe Ergebnis; genau das
war der Fehler.

> **Warum das die gefährlichste der drei Ankerfehler war:** Die ersten beiden
> sah man am Bild — dreizehn Linien auf einem Haufen, oder zwei statt
> dreizehn. Dieser hier hätte weiterhin **dreizehn saubere, waagerechte, gut
> verteilte Linien** gezeichnet. Sie wären nur in der falschen Hälfte
> gewesen. Der Zeichentest hätte „sauber" gemeldet, und das zu Recht — er
> prüft die Lage im Bild, nicht die Richtigkeit.
>
> **Ein Fehler, der richtig aussieht, wird nur durch einen bekannten Wert
> gefunden.** Das ist CLAUDE.md Abschnitt 0, wörtlich, und hier hat es
> gehalten.

**Zusätzlich:** Der Reiter kannte nur 15m/1h/4h/1d. Da Mark auf
30-Minuten-Kerzen zeichnet und laut Sven auf **Monatskerzen** am besten
trifft, stehen jetzt **30m, 1w und 1M** mit zur Wahl. Geprüft: 30m liefert
300 Kerzen, 1w 300 (ab Nov 2020), 1M **109** (ab Aug 2017, die gesamte
Binance-Historie). Alle drei zeichnen sauber. **Wartet auf den nächsten
Neustart.**

---

### 86. ⚠️ OFFEN (Freeze) — E7 hat das Gewinn/Verlust-Verhältnis fast repariert und dabei die Trefferquote verloren

**Gefunden 29.08.2026** beim Vergleich gegen sieben blind getestete
Signalanbieter (Handbuch 10.9, Svens Datensatz).

**Konfidenz: SICHER** für die Zahlen (508 Verkäufe aus
`data_store/trades_v5.json`, gegengeprüft gegen die Reihe `trades` in
`data_store/equity_history.json` — dieselbe Zahl aus zweiter Quelle).
**OFFEN** für das Urteil zu E7: 62 Verkäufe, Kriterium A verlangt 100.

*Der Profit-Faktor unter Ziel ist **kein neuer Fund** — er wurde am 24.08.
(0,901), 25.08. und 28.08. (je 0,764) gemessen, `schon_bekannt.py` und die
Sitzungssuche haben korrekt darauf verwiesen. Neu ist die **Aufteilung
nach Epoche** und die daraus sichtbare Ursache.*

| | mittl. Gewinn | mittl. Verlust | Verhältnis | Winrate ist | Winrate **nötig** | Lücke |
|---|---:|---:|---:|---:|---:|---:|
| gesamt (508) | +0,80 $ | −1,86 $ | **0,43 : 1** | 67,1 % | 69,9 % | −2,8 PP |
| **E7 (62)** | +1,77 $ | −1,81 $ | **0,98 : 1** | 45,2 % | 50,5 % | −5,4 PP |

**Was das heißt:** E7 hat genau das getan, was es sollte — die Gewinne
laufen jetzt so weit wie die Verluste (0,43 → 0,98). **Aber die
Trefferquote ist von 67 auf 45 % gefallen.** Der schärfere Filter hat
offenbar nicht nur schlechte, sondern auch gute Einstiege aussortiert.

> **Zwei verschiedene Krankheiten in zwei Epochen.** Wer nur den
> Profit-Faktor betrachtet (0,880 → 0,806, „wurde schlechter"), sieht das
> nicht. Erst die Zerlegung in Verhältnis und Trefferquote zeigt, dass die
> eine Hälfte repariert und die andere kaputtgegangen ist.

**Bemerkenswerte Bestätigung der eigenen Zielgröße:** Aus den Zahlen ergibt
sich ein nötiges Verhältnis von **1,22 : 1**. In `config_zielgroessen.json`
steht seit dem 19.08. als Ziel **1,27**. Zwei unabhängige Wege, fast
dieselbe Zahl.

**Gegen die äußere Latte** (sieben Anbieter, blind auf echten MT4-Konten):

| | unser Bot (E7) | Anbieter-Schnitt |
|---|---:|---:|
| Winrate | 45,2 % | 74,1 % |
| Profit-Faktor | 0,806 | 2,33 |
| Größter Rückschlag | 6,6 % | 14,4 % |

Der Vergleich hinkt (Papierhandel gegen echte Konten, Krypto mit 0,505 %
je Runde gegen Forex-Spreads) und taugt nicht für einen Rangplatz. Was
bleibt: **ein Profit-Faktor unter 1,00 ist in jedem Markt ein
Verlustgeschäft.** Der Bot ist damit schlechter als die Trivial-Latte
„gar nicht handeln" (0,00 $).

**Risiko: kein Kapital-, kein Datenverlust** — Papierhandel. Blockiert den
Live-Weg aber sehr wohl, und zwar über Kriterium F, nicht über diesen
Befund.

**Nicht vor dem Stichtag anfassen.** Jede Regeländerung setzt die Zählung
auf null. Die 5,4 Prozentpunkte sind nach dem 18.09. anzugehen, dann mit
Epochengrenze.

**Zu tun nach dem Stichtag, in dieser Reihenfolge:**

1. **Ursache der eingebrochenen Trefferquote klären.** E7 verschärfte den
   Filter — welche Einstiege fallen jetzt weg, die vorher gewonnen hätten?
   Das Schatten-Notizbuch sollte das beantworten können.
2. **Erst danach am Ausstieg drehen.** Das Verhältnis steht bei 0,98 und
   braucht 1,22 — aber es ist nicht mehr das größere Loch.
3. **Erste Hürde ist 1,00, nicht 2,33.** Deckt sich mit der Warnschwelle
   in Handbuch 10.7.

**Werkzeug:** `python provider_vergleich.py`, Handbuch 10.9.

---

### 87. ⚠️ OFFEN (Freeze) — Der Ticket-Wächter verwirft unbekannte Stichworte still und löscht sie beim nächsten Schreiben

**Gefunden 29.08.2026.** Sven: *„was ist mit den tickets los, trotz Neustart
tut sich nichts!"*

| | |
|---|---|
| **Fundstelle** | `features/tickets_watcher.py:31` (`VALID_STICHWORTE`), `:56` (`_parse_line`), `:113` (`_write_confirmation`) |
| **Risiko** | **Datenverlust** — Dokumentation, kein Kapital |
| **Konfidenz** | **SICHER**, am Code nachgelesen und am Verhalten bestätigt |

**Die Regel im Code:**

```python
VALID_STICHWORTE = {"SPEICHERN", "ERLEDIGT", "BUG", "DOKUMENTIEREN", "NOTIZ"}
```

`_parse_line` gibt für jede Zeile mit einem anderen Stichwort `None`
zurück. Kein Log, keine Warnung, kein Hinweis in der Bestätigung.

**Und jetzt der Teil, der wehtut** — die beiden Zweige in `check()`:

| Lage | Was passiert |
|---|---|
| **kein** gültiger Eintrag in der Datei | `_last_mtime` wird gesetzt, `return`. Die Datei bleibt unangetastet — die ungültigen Zeilen überleben |
| **mindestens einer** gültig | Die gültigen werden verarbeitet, danach überschreibt `_write_confirmation()` die **ganze Datei**. **Jede ungültige Zeile ist damit endgültig weg, ungelesen** |

> **Ein einziges richtig beschriftetes Ticket löscht alle falsch
> beschrifteten mit.**

**Belegt am eigenen Fall:** Die Kopfzeile meldete
`Letzte Verarbeitung: 2026-08-28 22:41:34 — Einträge verarbeitet: 1`.
An dem Punkt lagen mehrere Tickets vom 28.08. in der Datei (Stichworte
`FIBONACCI:`, `PRUEFUNG:`, `FALLE:`, `ANALYSE-REITER:`, `MESSUNG:`). Einer
war gültig, die übrigen wurden mit der Bestätigung überschrieben. In
`ENTWICKLERHANDBUCH.md` findet sich keiner davon.

**Warum das passieren konnte — der eigentliche Konstruktionsfehler:**

Die gültigen Stichworte stehen **in der Kopfzeile von `tickets.txt` selbst**.
Diese Kopfzeile wird bei jedem Schreiben neu erzeugt — man liest sie also
nur, wenn man die Datei öffnet. Wer die Regel dagegen in `CLAUDE.md`
nachschlägt, findet dort:

> `tickets.txt` | Eingang für die Chronik | `STICHWORT: Text`, wird vom Bot
> binnen 30 s eingelesen und geleert

**Kein Wort davon, dass nur fünf Stichworte zulässig sind.** Genau so ist
der Fehler entstanden, mehrfach, über Wochen.

**Verstoß gegen eine eigene Dauerregel:** CLAUDE.md Abschnitt 7.4 —
*„Kein stilles Scheitern. Kein Fehler darf nur geloggt und dann ignoriert
werden."* Hier wird nicht einmal geloggt.

**Sofortmaßnahme 29.08.:** Die 12 wartenden Tickets wurden auf
`DOKUMENTIEREN:` umgeschrieben, das ursprüngliche Stichwort bleibt als
Präfix im Text erhalten (`DOKUMENTIEREN: VERGLEICH - …`). Sicherung der
alten Fassung im Scratchpad. **Nichts weiter verloren.**

**Korrektur nach dem Stichtag** — drei Zeilen, reine Anzeige, kein
Handelsverhalten:

1. **Unbekanntes Stichwort nicht verwerfen, sondern als `DOKUMENTIEREN`
   annehmen** und das Original als Präfix in den Text schreiben. Ein Ticket
   ohne passendes Fach ist immer noch ein Ticket.
2. **Ersatzweise mindestens:** unbekannte Zeilen **stehen lassen** statt
   überschreiben, und die Zahl in der Bestätigung ausweisen
   (`3 Einträge nicht erkannt, unverändert gelassen`).
3. **`CLAUDE.md` Abschnitt 6 um die fünf Stichworte ergänzen** — dort wird
   nachgeschlagen, nicht in der Kopfzeile der Datei.

**Bis dahin gilt:** Nur `SPEICHERN`, `ERLEDIGT`, `BUG`, `DOKUMENTIEREN`
oder `NOTIZ` als Stichwort verwenden.

---

### 88. ⚠️ OFFEN (Freeze) — Zwei halbe Schreibwege: drei Felder erreichen den Verkauf nie

**Gefunden 21.08.2026, nummeriert am 29.08.2026.** Sven beim Lesen der
Vollständigkeitsprüfung: *„da fehlen doch einige Sachen! Ist dir das
bekannt?"*

> **Ja — und genau das ist der Befund.** Die Sache steht seit dem 21.08.
> ausführlich in der Chronik (*„Was die Prüfung gefunden hat — zwei halbe
> Schreibwege"*), mit Ursache und Tabelle. Sie hatte nur **keine
> Befundnummer** und stand **nicht in `OFFEN.md`** — der einen Liste, von
> der CLAUDE.md sagt: *„Was hier nicht steht, ist nicht offen."*
>
> Eine Erkenntnis, die nur in der Chronik steht, ist kein offener Punkt,
> sondern eine Anekdote. Deshalb bekommt sie jetzt eine Nummer.

**Konfidenz: SICHER.** Am Code und an `trades_v5.json` nachgemessen.

### Die Ursache

Zwei Wege schreiben einen Verkauf, und jeder schreibt nur seine Hälfte:

| Feld | `exit_monitor` | `execute_approved_trade` |
|---|---|---|
| `position_id`, `haltedauer_min`, `entry_strategie` | ✅ | ❌ |
| `decision_id` | ❌ | ✅ |
| `stop_initial`, `trailing_stop_pct` | ❌ | ❌ |

**Bei drei Feldern schreibt keiner von beiden.** Deshalb landen die
Anteile nicht zufällig bei 80,6 / 54,8 / 19,4 % — das Muster *ist* die
Aufteilung.

### Was am 29.08. dazukam — die Prüfung sagte die Unwahrheit

`vollstaendigkeit.py:62` behauptete:

```
stop_initial → "NICHT nachtragbar - wird nirgends geschrieben"
```

**Das ist falsch.** Nachgemessen an `data_store/trades_v5.json`: Auf der
**Kauf**-Seite stehen alle drei Felder in **64 von 68 Käufen seit dem
06.08. (94,1 %)**. Geschrieben werden sie sehr wohl — sie werden nur nicht
an den Verkauf weitergereicht.

| Feld | am Kauf (ab 06.08.) | am Verkauf (E7) |
|---|---:|---:|
| `stop_initial` | **94,1 %** | 0 % |
| `trailing_stop_pct` | **94,1 %** | 0 % |
| `decision_id` | **94,1 %** | 19,4 % |

**Der Unterschied ist nicht akademisch.** „Wird nirgends geschrieben"
heißt: das Schreiben muss erst gebaut werden. „Wird geschrieben, aber
nicht weitergereicht" heißt: es fehlt nur die Übergabe — deutlich weniger
Arbeit, und für die betroffenen Käufe liegen die Werte bereits vor.

### Ein Irrweg, den ich am 29.08. selbst gegangen bin

Erster Versuch: Verkauf und Kauf über **FIFO** verbinden (gleiche Münze,
ältester offener Kauf). Ergebnis sah gut aus — 62 von 62 zugeordnet,
46,8 % nachtragbar.

**Die Stichprobe hat es widerlegt:** Die Mengen passen nicht.

```
Verkauf SOL 1,357058   gegen   Kauf SOL 0,714138
Verkauf ETH 0,093611   gegen   Kauf ETH 0,027693
```

Positionen werden per Nachkauf aufgebaut und teilweise verkauft. **Ein
Kauf entspricht keinem Verkauf.** Die 46,8 % waren wertlos.

> **Eine Zuordnung, die 100 % meldet, ist verdächtig, nicht beruhigend.**
> Die Zahl kam zustande, weil *immer* irgendein Kauf übrigbleibt — nicht,
> weil er der richtige war. Aufgefallen ist es nur, weil drei Paare von
> Hand nachgesehen wurden.

**Auch `positionsverlauf.db` hilft nicht:** Tabelle `positionen` führt
`pos_id, quelle, muenze, eroeffnet, einstieg, menge, strategie, score,
geschlossen, schluss_grund` — **keines der drei Felder.**

**Ergebnis:** Die Schlussfolgerung des Werkzeugs („nicht nachtragbar")
stimmt, ihre Begründung nicht. Beides am 29.08. richtiggestellt.

### Was dabei noch aufgefallen ist

Das Werkzeug entschied „nachtragbar oder nicht" an der **Zeichenkette**
`"NICHT"` im Quellentext (`vollstaendigkeit.py:243`). Nach der
Textkorrektur meldete es prompt *„Nachtragbar: 7, Endgültig fehlend: 0"* —
falsch, und ohne zu murren. Jetzt steht eine ausdrückliche Liste
(`NACHTRAGBAR`) dort. **Eine Logik, die an einer Formulierung hängt,
bricht beim nächsten Umformulieren.**

### Zu tun

| | Wann | Was |
|---|---|---|
| 1 | **nach dem Stichtag** | Die drei Felder beim Verkauf mitschreiben — der eine Weg holt sie aus dem Positionsdatensatz, der andere aus dem Kaufeintrag |
| 2 | **nach dem Stichtag** | Besser noch: `positionen` in `positionsverlauf.db` um `stop_initial`, `trailing_stop_pct` und `decision_id` erweitern. Dann hängen sie an der Position, nicht am einzelnen Handel |
| 3 | sofort möglich | Die vier **nachtragbaren** Felder (`position_id`, `haltedauer_min`, `entry_strategie`, `entry_score`) wirklich nachtragen — 80,6 bzw. 54,8 % sind vorhanden |

**Blockiert die Freigabe nicht** (Stichtags-Regel, CLAUDE.md 5): kein
Kapital-, kein Datenverlustrisiko. Die Freigabefelder sind zu **100 %**
vollständig. Was fehlt, blockiert die *nächste Verbesserung*, nicht den
Live-Weg.

#### Ergänzung 29.08. — der Nachtrag hielt 41 Sekunden

Sven: *„trag die vier Felder nach bitte."* Gemacht, geprüft, geschrieben —
und **vom Bot überschrieben, bevor die Tinte trocken war.**

| Zeit | Was geschah |
|---|---|
| 16:55:17 | 12 Einträge ergänzt, Sicherung angelegt, Gegenprobe meldet **Erfolg** |
| 16:55:58 | `app.py` schreibt `trades_v5.json` neu — aus seiner Kopie im Arbeitsspeicher |
| danach | `_nachgetragen` weg, `position_id` wieder `None`. **41 Sekunden.** |

**Die Ursache:** `TradeJournal` (`core/state_store.py:108`) lädt das
Journal **einmal beim Start** in den Speicher und schreibt bei jedem
Speichern die **ganze Datei** neu. Der Klassenkommentar sagt
*„append-only, nie überschreiben"* — das gilt für die Einträge, nicht für
die Datei. Jede Änderung von außen ist beim nächsten Handel weg.

> **Das Tückische ist nicht der Verlust, sondern die Erfolgsmeldung.** Die
> Gegenprobe unmittelbar nach dem Schreiben las die Datei neu und fand
> alles vor. Sie war richtig — nur zu früh. Erst der zweite Blick, eine
> Minute später, zeigte den leeren Stand.
>
> Ein Nachtrag, der still verschwindet, ist schlimmer als einer, der gar
> nicht stattfindet: **man hält die Lücke danach für geschlossen.**

**Kein Schaden entstanden:** 1113 Einträge vorher wie nachher, nichts
verloren, Sicherung liegt unter
`trades_v5.json.vor_nachtrag_20260829_165517`.

**Eingebaut:** `felder_nachtragen.py` prüft jetzt vor dem Schreiben, ob
`app.py` läuft, und **bricht ab**, wenn ja — mit der Anleitung: Bot
beenden, nachtragen, Bot starten. Lässt sich das nicht feststellen, wird
ebenfalls abgebrochen. Lieber nichts tun als lautlos scheitern
(CLAUDE.md 7.4).

**Zwei weitere Funde auf dem Weg dorthin:**

1. **`entry_strategie` wäre mit einer LEEREN Zeichenkette gefüllt worden.**
   `positionen.strategie` ist bei **allen 58 echten** Positionen leer;
   gefüllt ist sie nur bei den **28 Schattenpositionen**. Das Feld hätte
   danach als „vorhanden" gezählt, ohne etwas zu enthalten — die
   Vollständigkeitsstatistik wäre geschönt worden, ausgerechnet von dem
   Werkzeug, das sie verbessern soll. Jetzt gilt: leer ist kein Wert.

2. **Die Positionstabelle mischt echte und Schatten-Positionen** (58 zu
   28), und `zuordnen()` filterte nicht danach — weder hier noch in
   `vollstaendigkeit.py`. Gemessen passiert derzeit **nichts Falsches**
   (alle 58 Treffer sind `echt`, die Schlusszeiten liegen auseinander),
   aber darauf soll sich niemand verlassen. Filter `quelle='echt'`
   eingebaut.

**Damit sind es nicht vier nachtragbare Felder, sondern zwei:**
`position_id` und `haltedauer_min`. `entry_strategie` und `entry_score`
haben in der Quelle nichts stehen.

#### Ergänzung 29.08. — `entry_strategie` und `entry_score` sind für die Zukunft zu haben

Svens Frage: *„was ist aber mit dem entry_strategie wie entry_score, können
wir die Daten anderweitig besorgen — wenn auch nicht nachträglich, dass wir
es für die Zukunft dann aber haben?"*

**Ja. Die Daten existieren bereits, nur an der falschen Stelle.**

| Feld am **Kauf** in `trades_v5.json` | Abdeckung |
|---|---|
| `strategy` | **605 von 605 = 100 %** |
| `score` | 68 von 75 seit 06.08. = 90,7 % |

**Jeder einzelne Kauf trägt seine Strategie.** EMA_TREND 46×,
FIBONACCI_SUPPORT 10×, DCA_FEAR_GREED 9×, RSI_OVERSOLD 5×, MACD_CROSS 4×.

### Warum es trotzdem nicht ankommt — eine Kette mit vier Gliedern

| # | Stelle | Was passiert |
|---|---|---|
| 1 | `agents/signal_agent.py:182` | setzt `strategy_id` am Auftrag (Intent) |
| 2 | `app.py:1871-1873` | schreibt `entry_score` und `entry_strategie` an die Position |
| 3 | `runtime/state_manager.py:63-88` | speichert nach `bot_state.json` — **nach einer Whitelist** |
| 4 | `positionsverlauf.py:179` | liest `entry_strategie` aus `bot_state.json`, sonst `strategie_id`, sonst `""` |

**Die Whitelist in Glied 3 kennt `entry_strategie` und `entry_score` nicht.**
Ihr eigener Kommentar warnt davor:

> *„Diese Liste ist eine Whitelist: was nicht aufgezaehlt ist, ueberlebt
> keinen Neustart."*

Sie führt `strategie_id` — ein **dritter** Name für dieselbe Sache, neben
`strategy_id` (Glied 1) und `entry_strategie` (Glied 2). Geschrieben wird
das eine, gespeichert das andere.

**Belegt am Ergebnis:** Alle 58 echten Positionen vom 17.08. bis 28.08.
haben `strategie=''` und `score=NULL` — **auch die von gestern**. Es ist
kein Altlastenproblem, es ist jetzt kaputt.

**Konfidenz: SICHER** für die vier Glieder und das Ergebnis (am Code
nachgelesen, an der Datenbank nachgezählt). **OFFEN**, an welchem Glied
genau der Wert verlorengeht — dafür bräuchte es eine **offene Position**
zum Mitlesen, und es war keine da.

### Der Vorschlag — nicht die Kette reparieren, sondern sie umgehen

**Drei Namen für dieselbe Sache über vier Glieder zu synchronisieren, ist
die aufwendigste und fehleranfälligste Lösung.** Die Alternative:

> `positionsverlauf.py` holt die Strategie beim Öffnen einer Position
> **direkt aus dem Kaufeintrag** in `trades_v5.json` — dort steht sie zu
> **100 %**.

| | |
|---|---|
| **Aufwand** | eine Funktion in einem Sammler |
| **Freeze** | **verträglich** — `positionsverlauf.py` ist ein eigener Prozess, kein Handelspfad, und schreibt nur auf |
| **Risiko** | keines für Kapital; schlimmstenfalls bleibt das Feld leer wie bisher |
| **Nebenwirkung** | Die Whitelist bleibt unberührt — dort etwas zu ändern, würde das Verhalten nach einem Neustart berühren und bräuchte eine Epochengrenze |

**Nicht nachträglich**, wie Sven richtig annimmt: Für die bestehenden
58 Positionen fehlt weiterhin die belastbare Verbindung Position → Kauf.
**Aber ab dem Einbau trägt jede neue Position ihre Strategie und ihren
Score** — und damit wird die Frage beantwortbar, an der die nächste
Verbesserung hängt: *enden schwache Signale schlechter als starke?*

#### Ergänzung 29.08. abends — die Strategie kommt jetzt aus dem Handelsbuch

Sven: *„ja bau das ein!"* — erledigt in `positionsverlauf.py`.

**Neue Funktion `einstieg_aus_journal()`.** Beim Öffnen einer Position sucht
der Sammler den **letzten Kauf derselben Münze**, höchstens **30 Minuten**
vor der Eröffnung, und übernimmt dessen `strategy` und `score`.

**Warum ein Zeitfenster?** Ohne es fände die Suche irgendeinen alten Kauf
und ordnete seine Strategie falsch zu — genau die Falle, in die die
FIFO-Zuordnung am selben Tag gelaufen ist. Die Grenze ist einschließlich:
genau 30 Minuten zählen noch, 31 nicht mehr.

**Gegen echte Daten geprüft** — die zwölf jüngsten Positionen, alle mit
`strategie=''` und `score=NULL` in der Datenbank:

| Position | in der DB | aus dem Handelsbuch |
|---|---|---|
| `pos_ETH_2995be36` (29.08. 19:24) | leer / NULL | **FIBONACCI_SUPPORT**, Score 8 |
| `pos_SOL_514424e0` | leer / NULL | RSI_OVERSOLD, 3 |
| `pos_SOL_05443221` | leer / NULL | EMA_TREND, 4 |
| … 9 weitere | leer / NULL | gefunden |

**12 von 12 gefunden.**

> **Der überzeugendste Beleg kam aus Svens eigenem Log.** Dort steht zum
> ETH-Kauf um 21:24:55: *„Score **8**/10 (80 %) … V4-**FIBONACCI_SUPPORT**
> STARK"*. Die neue Funktion liefert für dieselbe Position
> `FIBONACCI_SUPPORT`, Score 8. **Zwei voneinander unabhängige Quellen,
> dasselbe Ergebnis** — genau die Gegenprobe, die CLAUDE.md Abschnitt 0
> verlangt.

**Neun Selbsttests**, unter anderem: jüngster Kauf im Fenster gewinnt,
andere Münze wird nicht genommen, ein Kauf *nach* der Eröffnung zählt
nicht, die 30-Minuten-Grenze ist einschließlich, ein Verkauf wird nicht als
Kauf verwechselt, und eine **leere Strategie bleibt leer** — ein Scheinwert
wäre schlimmer als eine Lücke.

**Zwei der neun Tests fielen beim ersten Lauf durch — beide wegen falscher
Erwartungen in meinem Test, nicht wegen des Codes.** In einem Fall lag der
Kauf 39 Minuten zurück (korrekt außerhalb), im anderen genau auf der
30-Minuten-Grenze (korrekt innerhalb). Korrigiert und erneut geprüft.

**Freeze-verträglich:** `positionsverlauf.py` ist ein eigener Prozess, kein
Handelspfad, liest `trades_v5.json` nur und schreibt ausschließlich in
seine eigene Datenbank. Die Whitelist in `runtime/state_manager.py` bleibt
**unberührt** — dort zu ändern hieße, das Verhalten nach einem Neustart zu
ändern, und das bräuchte eine Epochengrenze.

**Wirkt ab dem nächsten Öffnen einer Position, nicht rückwirkend.**

---

### 89. ⚠️ OFFEN (Freeze) — Die KI-Prognose hat noch nie funktioniert: 19 Werte geteilt durch 20

**Gefunden 29.08.2026 spätabends.** Sven schickte einen frischen Startlauf:
*„hier ist mir grad was aufgefallen."* Die Meldung
`Chart-Fehler: operands could not be broadcast together with shap…`
stand darin **zwölfmal** hintereinander.

| | |
|---|---|
| **Fundstelle** | `ui/main_window.py:1362` |
| **Zeile** | `returns = np.diff(closes[-20:]) / closes[-21:-1]` |
| **Risiko** | kein Kapital-, kein Datenverlust — **reine Anzeige** |
| **Konfidenz** | **SICHER**, nachgerechnet |

### Der Fehler ist ein Zeichen

```
np.diff(closes[-20:])   ->  19 Werte
closes[-21:-1]          ->  20 Werte
                            ^^^^
```

`np.diff` gibt aus n Werten immer **n − 1** Differenzen zurück. Der Zähler
hat also 19 Einträge, der Nenner 20. numpy kann das nicht zusammenbringen
und wirft wörtlich die Meldung aus dem Log:

```
operands could not be broadcast together with shapes (19,) (20,)
```

**Richtig wäre `closes[-20:-1]`** — dann sind beide Seiten 19 Werte lang.
Ein einziges Zeichen, die `1` vor der Klammer.

### Warum das nie auffiel — und was es bedeutet

Die Zeile steht hinter `if n > 20:` (`:1360`). Bei den 200 Kerzen des
Charts ist diese Bedingung **immer** wahr.

> **Die KI-Prognose ist also nie gelaufen.** Nicht selten, nicht manchmal —
> **kein einziges Mal**, seit es sie gibt. Wer das Häkchen setzt, bekommt
> keine Prognose, sondern eine Ausnahme.

**Und der Schaden reicht weiter als die Prognose selbst.** Der Aufruf steht
bei `:1309`, mitten in der Zeichenroutine. Die Ausnahme springt sofort in
den `except`-Block bei `:1340` — also **vor**:

| Zeile | was übersprungen wird |
|---|---|
| `:1325` | Legende |
| `:1331` | Achsenformatierung |
| `:1335` | Statuszeile mit Preis, RSI, ADX |
| **`:1339`** | **`man_canvas.draw_idle()` — das Bild wird nie neu gezeichnet** |

**Folge:** Mit gesetztem Häkchen **friert der Chart ein.** Er zeigt weiter
das letzte gelungene Bild, während unten die Fehlermeldung steht. Genau das
ist auf Svens Bildschirmfoto zu sehen — ein vollständiger Chart *und* eine
Fehlerzeile darunter.

### Was daraus folgt

**Svens Entscheidung vom selben Abend steht:** *„kann man nach dem Freeze
löschen."* Das bleibt richtig — und der Fund stützt sie zusätzlich:

- Die Funktion hat **nie** ein Ergebnis geliefert. Es geht nichts verloren.
- Sie schreibt ohnehin nur den Trend fort und addiert eine **Zufallszahl
  mit festem Startwert** (`np.random.seed(42)`, `:1387`). Der feste
  Startwert lässt sie bei jedem Aufruf gleich aussehen — er macht sie nicht
  richtiger. **Gemessen wurde sie nie.**

**Zwei Wege nach dem Stichtag, beide reine Anzeige:**

| | Aufwand | Ergebnis |
|---|---|---|
| **Entfernen** (Svens Wahl) | Häkchen und Funktion raus | Chart friert nicht mehr ein, eine ungemessene Linie weniger |
| Reparieren | ein Zeichen: `closes[-20:-1]` | Die Prognose liefe — bliebe aber ungemessen |

> **Unabhängig davon gehört der Aufruf in ein eigenes `try`.** Dass ein
> Fehler in einer *Zusatzlinie* den **ganzen** Chart am Neuzeichnen hindert,
> ist der eigentliche Konstruktionsfehler. Ein Indikator, der scheitert,
> darf das Bild nicht mitreißen.

**Nicht anfassen bis zum Stichtag:** Der MANUELL-Reiter läuft im
Bot-Prozess, jede Änderung braucht einen Neustart.

---

### 90. ✅ BEHOBEN (30.08.) — Die Regeldatei nannte einen Stichtag, der seit neun Tagen falsch war

**Gefunden 30.08.2026** beim Morgencheck.

| | |
|---|---|
| **Fundstelle** | `.claude/hooks/DAUERREGELN.txt`, Zeile 10 |
| **Zeile** | `- Messfenster bis 29.08.2026: keine Aenderung, die das VERHALTEN…` |
| **Maßgeblich** | `config_zielgroessen.json` → `messfenster_ende` = **2026-09-18** |
| **Risiko** | **hoch, aber indirekt** — kein Kapitalverlust, wohl aber der Verlust der ganzen Epoche |
| **Konfidenz** | **SICHER** |

### Warum das gefährlich war

Diese Datei wird **bei jedem einzelnen Zug** automatisch vorgelegt. Sie ist
die Regelquelle, die immer im Blick ist — und genau deshalb die, der man
glaubt.

Das Fenster wurde am **21.08.** auf den 18.09. verlängert (Svens
Entscheidung: *„dass lass ich den verfickten bot jetzt eben nochmal 20 Tage
länger laufen"*). Die Hook-Datei wusste davon nichts.

> **Heute ist der 30.08.** Nach dieser Datei war der Freeze also **seit
> gestern vorbei.** Wer ihr geglaubt hätte, hätte heute angefangen, Regeln
> zu ändern — und damit die Zählung auf null gesetzt, elf Tage vor dem
> echten Stichtag.

**Genau der Mechanismus, der das Projekt sieben Monate gekostet hat.** Aus
sieben Monaten Laufzeit wurden effektiv sechs Tage verwertbare Daten, weil
immer wieder mitten in der Messung Regeln geändert wurden.

### Die Ursache ist keine Nachlässigkeit, sondern die Bauart

CLAUDE.md schreibt es selbst vor:

> *„Das verbindliche Datum steht in `config_zielgroessen.json`
> (`messfenster_ende`), nicht hier. Wer es ändert, ändert es dort — sonst
> laufen zwei Wahrheiten nebeneinander."*

Die Hook-Datei hielt sich nicht daran. Sie trug eine **Kopie** des Datums —
und Kopien altern.

### Behoben

Das feste Datum ist raus. Stattdessen steht dort jetzt der Verweis auf die
maßgebliche Datei, mit dem Befehl zum Nachsehen:

```
python -c "import json;print(json.load(open('config_zielgroessen.json',encoding='utf-8'))['messfenster_ende'])"
```

**Gegengeprüft:** `29.08.2026` steht in der Datei nur noch **einmal** — in der Erklärung, warum es dort nicht mehr als Regel steht. Als **Vorgabe** kommt es nicht mehr vor.

> *Meine erste Gegenprüfung zählte einfach das Vorkommen der Zeichenkette und lieferte 1 statt 0 — ich hätte fast „null“ geschrieben. Ein Zähler misst, wie oft etwas dasteht, nicht, ob es als Regel oder als Erklärung dasteht.*

> **Die Lehre ist nicht „besser aufpassen".** Ein Datum, das an zwei
> Stellen steht, geht irgendwann auseinander — sicher, nur der Zeitpunkt
> ist offen. Die einzige Abhilfe ist, es an **einer** Stelle stehen zu
> lassen und überall sonst darauf zu zeigen.

**Reine Dokumentation**, kein Code, kein Handelspfad, kein Neustart nötig.

---

### 91. ✅ BEHOBEN (01.09.) — Der Manuell-Reiter beschriftet Fibonacci aufwärts spiegelverkehrt

**Fundstelle:** `ui/main_window.py:1289` (vorher). **SICHER.**

Der Zwilling von **Befund 85**. Dort war die Ankerwahl im *Analyse*-Reiter
zweimal falsch; behoben am 27.08. Im *Manuell*-Reiter stand derselbe Fehler
noch — vier Tage länger, unbemerkt, weil niemand dort hingesehen hat.

Der alte Code:

```python
fib_levels = {"0.0": swing_low, "0.382": swing_low + diff*0.382, ...}
```

Die Null klebt fest am Tief. Das ist die **Abwärtsvariante** — und nur die.

#### Warum das falsch ist

Die Regel lautet: **Die 0 liegt am ENDE der Bewegung, die 1 an ihrem Anfang.**
Welcher Anker das Ende ist, entscheidet die **Zeit**, nicht die Höhe.

| Bewegung | zuletzt | die 0 gehört ans |
|---|---|---|
| aufwärts (Tief kam zuerst) | das Hoch | **Hoch** |
| abwärts (Hoch kam zuerst) | das Tief | **Tief** |

Kam das Tief zuerst, ging es aufwärts — dann gehört die 0 ans Hoch. Der alte
Code setzte sie trotzdem ans Tief und drehte damit die ganze Leiter um.

#### Der Beleg — nachgerechnet an echten Ankern

BTC/USDC, 4 Stunden, Anker Hoch 81.494,43 / Tief 62.480,00, Richtung **AUF**:

| Stufe | Manuell-Reiter (alt) | richtig | dieselbe Linie heißt richtig |
|---|---:|---:|---|
| 0,0 | 62.480,00 | 81.494,43 | **1,0** |
| 0,382 | 69.743,51 | 74.230,92 | **0,618** |
| 0,5 | 71.987,21 | 71.987,21 | 0,5 |
| 0,618 | 74.230,92 | 69.743,51 | **0,382** |
| 1,0 | 81.494,43 | 62.480,00 | **0,0** |

**Die Linien lagen richtig — die Namen darauf waren vertauscht.** Genau das
macht den Fehler so zäh: Der Chart sieht vollkommen plausibel aus. Nur 0,5
stimmt immer, weil die Mitte gespiegelt die Mitte bleibt.

Wer nach dem Goldenen Schnitt (0,618) handelt, sah bei jeder
Aufwärtsbewegung die 0,382-Linie an und hielt sie dafür.

#### Die Korrektur

```python
auf = int(df["Low"].values.argmin()) < int(df["High"].values.argmax())
_fp = (lambda r: swing_high - diff*r) if auf else (lambda r: swing_low + diff*r)
```

Dieselbe Regel wie in `features/chartanalyse.py`, nur an der zweiten Stelle.

**Gegengeprüft in beide Richtungen** an zwei von Hand gerechneten Fällen
(Spanne 50–200, also 150): aufwärts muss 0,382 bei 142,7 liegen, abwärts bei
107,3. Die neue Formel besteht beides, die alte nur den Abwärtsfall.

> *Mein erster Prüflauf meldete eine Abweichung — er erwartete, dass die
> alte Formel **immer** falsch ist. Sie ist abwärts richtig. Das ist ja der
> Fehler: Sie hat eine der zwei Richtungen fest eingebaut. Die Erwartung war
> falsch, nicht der Code.*

#### Was das über die Suche sagt

Befund 85 wurde am 27.08. behoben — an **einer** Stelle. Dass dieselbe Formel
ein zweites Mal im Projekt steht, hat damals niemand geprüft.

> **Wer einen Fehler behebt, hat die Fehlerart nicht behoben.** Nach jeder
> Korrektur gehört die Frage dazu: *Wo steht dasselbe noch einmal?*
> Ein `grep` nach der Formel hätte am 27.08. gereicht.

**Kein Handelspfad, keine Bot-Änderung, keine Epochengrenze nötig** — der
Block sitzt in der Zeichenroutine hinter `if ind.get("Fibonacci")`. Er wirkt
beim **nächsten Start** des Cockpits; nichts wurde neu gestartet.

**Nicht mitkorrigiert:** Der Sichtbarkeitsfilter eine Zeile darunter
(`swing_low * 0.95 <= price <= swing_high * 1.1`) nimmt an, dass die
Verlängerungen nach *oben* laufen. Aufwärts laufen sie nach unten und werden
dadurch teils ausgeblendet. Das ist ein eigener, kleinerer Punkt — er
verschweigt Linien, er benennt keine falsch. Steht in `OFFEN.md`.

#### Der grep, den die Lehre verlangt — sofort angewandt

Direkt nach der Korrektur nach derselben Formel gesucht. Sie steht noch an
**zwei** weiteren Stellen:

```
v4_referenz/trading_imperium_v4_25_ALARM.py:966          "0.0 (Tief)": swing_low
v4_referenz/test perplexityshit/..._SAFE_FINAL.py:787    "0.0 (Tief)": swing_low
```

**Beide bleiben unverändert.** Zwei Gründe:

1. Der **V4-Referenzbot ist die eingefrorene Vergleichsgrundlage.** Wer ihn
   ändert, macht jeden Vorher-Nachher-Vergleich wertlos — Bestandsschutz.
2. Er beschriftet die Stufe ausdrücklich **`"0.0 (Tief)"`**. Damit sagt er,
   was er tut. Das ist keine falsche Beschriftung, sondern eine andere,
   offengelegte Festlegung. V6 behauptete `0.0` und meinte manchmal das Hoch
   — das ist der Unterschied zwischen einer Konvention und einem Fehler.

Notiert, damit die Stellen bekannt sind, falls V4 je aufgetaut wird.

---

# Neu gefunden am 01./02.09.2026 — Umzug auf den neuen Rechner

*Alle fünf beim Einrichten einer fabrikneuen Windows-Maschine gefunden.
Vier davon konnten auf dem alten Rechner gar nicht auffallen, weil dort
die fehlende Voraussetzung zufällig vorhanden war. Der Umzug war damit
ein Prüfstand, den kein Audit ersetzt.*

*Vor jedem Eintrag lief `python schon_bekannt.py <bezeichner>` — alle
Rückmeldungen lauteten NEU.*

---

### 92. ✅ BEHOBEN (01.09.) — `requirements.txt` nannte zwei Pakete nicht, die der Code braucht

**Nachgetragen, weil die Nummer in `requirements.txt:46` schon vergeben war,
in dieser Datei aber kein Eintrag stand.**

`reportlab` und `openpyxl` fehlten in `requirements.txt`, obwohl der Code
sie benutzt:

| Paket | wofür | Fundstelle |
|---|---|---|
| `reportlab==5.0.1` | `BOT-HANDBUCH.pdf`, `ZAHLENBUCH.pdf` | `handbuch_pdf.py`, `zahlenbuch.py` |
| `openpyxl==3.1.5` | `BOT-DATEN_*.xlsx` | `datenexport.py` |

**Warum es auf dem alten Rechner nie auffiel:** Dort waren beide
irgendwann von Hand installiert worden. Eine Installation nach Vorschrift
— genau das, was `requirements.txt` verspricht — hätte sie nie bekommen.
Die PDF-Erzeugung wäre im Hintergrund gescheitert, und zwar still.

**Behoben:** beide gepinnt in `requirements.txt` ergänzt.

**Die Lehre, die über diesen Fall hinausgeht:** Nicht raten, sondern
messen — alle `.py` mit `ast` einlesen, Top-Level-Importe sammeln,
Standardbibliothek und eigene Dateien abziehen, den Rest gegen die Datei
halten. `pakete_pruefen.py` tut genau das und meldet beides jetzt als
abgedeckt.

---

### 93. ✅ BEHOBEN (02.09.) — `wmic` gibt es in Windows 11 nicht mehr, und ein pauschales `except` machte daraus eine Antwort

**Der teuerste Fund des Umzugs.**

Microsoft hat `wmic` aus Windows 11 entfernt. Auf der neuen Maschine
(10.0.26200) gibt es weder den Befehl noch `System32/wbem/wmic.exe`.
Jeder Aufruf wirft `FileNotFoundError [WinError 2]` — nachgestellt und
bestätigt.

**Vier laufende Dateien** fragten die Prozessliste darüber ab:

| Datei | Verhalten bei Fehler | Folge |
|---|---|---|
| `sammler_pruefen.py:240` | `except Exception: return ""` | **gefährlich** |
| `prozess_frische.py:94` | sagt „nicht lesbar", gibt `[]` | ehrlich, unbrauchbar |
| `lage_erzeugen.py:66` | gibt `None` | LAGE.md zeigt überall „?" |
| `schatten_starter.py:68` | gibt `True` | startet nie mehr etwas |

Die erste ist die schlimme. Eine **leere** Prozessliste bedeutet dort
„nichts läuft".

**Nachgemessen, nicht vermutet.** Am 01.09.2026 um 21:48:42 UTC meldete
die Aufsicht im Botlog:

```
[SAMMLER] FEHL  Schatten-Universum    ist wieder weg
[SAMMLER] FEHL  Positionsverlauf      ist wieder weg
```

Zur selben Zeit liefen die Prozesse **11524** (`schatten_universum.py
--dauer`) und **2076** (`positionsverlauf.py`), beide seit 21:48:26,
belegt durch eine Prozessliste um 21:49:20 und dadurch, dass sie um
23:52:05 immer noch liefen.

**Die zweite, schwerere Folge:** `starten()` prüft in Zeile 875
`if skript.lower() in prozesse`. Bei leerem Text ist das **immer
falsch**. Die Funktion hätte bei jedem Aufruf einen **zweiten** Sammler
gestartet — genau die Doppelstarts, wegen derer die beiden
`ZZ_NICHT_BENUTZEN_`-Dateien existieren.

> **Ein pauschales `except`, das einen leeren Wert zurückgibt, macht aus
> einem Ausfall eine Antwort. Das ist schlimmer als der Absturz — beim
> Absturz sieht man wenigstens, dass etwas kaputt ist.**

**Behoben** über eine gemeinsame Quelle, `prozessliste.py`, auf Basis von
`psutil`. Das steht ohnehin gepinnt in `requirements.txt` und wurde in
`sammler_pruefen._fremder_ordner()` bereits benutzt — keine neue
Abhängigkeit. Sie wirft `ProzesslisteFehler`, statt still eine leere
Liste zu liefern.

Das Fehlerverhalten der vier Aufrufstellen blieb **unverändert**:
`schatten_starter` sagt weiterhin im Zweifel „nicht starten",
`prozess_frische` scheitert weiterhin laut.

**Gegentest in beide Richtungen** eingebaut (`python prozessliste.py`):
findet es den eigenen Prozess — und meldet es einen erfundenen Namen
*nicht*? Beide Richtungen bestanden.

**Nachweis der Reparatur:** Dieselbe Ampel, die vorher „ist wieder weg"
meldete, listet jetzt alle neun Sammler mit Zeilenzahlen und Status;
`prozess_frische.py` findet alle drei Prozesse mit Nummer, Startzeit und
Frische-Urteil.

---

### 94. ✅ BEHOBEN (02.09.) — Beide geplanten Aufgaben hätten auf dieser Maschine bei jedem Lauf mit Exit-Code 8 abgebrochen

`sammler_taeglich.bat` und
`docs/forschungsprogramm_2026-07/capture/capture_start.bat` suchten
Python so:

```bat
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do ...
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do ...
if not defined PY for /f ... ('where python ^| findstr /i /v "WindowsApps"') ...
if not defined PY ( echo [FEHLER] ... & exit /b 8 )
```

Auf diesem Rechner gibt es **keinen** dieser Orte. Hier läuft der
Python-Verwalter (Python Install Manager); der legt Python nach
`%LOCALAPPDATA%\Python\pythoncore-3.13-64\`. Und der letzte Rückfall
verwarf ausgerechnet das Einzige, was vorhanden war: Die Weichen unter
`WindowsApps` sind hier **nicht** die kaputten Store-Platzhalter von
früher, sondern die echten Dispatcher des Verwalters.

**Beide Aufgaben wären also bei jedem Lauf mit Exit-Code 8 abgebrochen** —
mit Meldung immerhin, nicht lautlos. Aber gesammelt hätte nichts.

**Behoben:** Die Suche steht jetzt in **einer** Datei,
`_python_finden.bat`, und prüft nach dem Finden nach, ob das Gefundene
wirklich startet **und wirklich 3.13 ist**. „Die Datei existiert" ist
kein Beleg. Beide `.bat` binden sie per `call` ein.

**Nachweis:** `sammler_taeglich.bat` einmal ausgeführt → Exit-Code 0,
Eintrag 3016 in `telemetrie.db`, Tabelle `jobs`: `sammler_taeglich`,
PID 11624, 13,9 s, Status OK, mit den Pfaden dieses Rechners.

---

### 95. ✅ BEHOBEN (02.09., Datei angelegt) — Der Rechner schläft nach 15 Minuten und nimmt Bot und Sammler mit

In der ersten Nacht fehlten Daten. Die Lücken decken sich **auf die
Minute** mit dem Windows-Ereignisprotokoll:

| Datenlücke (UTC) | Ereignisprotokoll |
|---|---|
| 01.09. 22:50 → 23:07 | Standby 22:53:21 → 23:05:26 |
| 01.09. 23:18 → 23:54 | Standby 23:20:56 → 23:51:55 |
| 02.09. 00:46 → 10:37 | **Standby 00:48:29 → 10:33:41** |

`powercfg` zeigt Standby nach **15 Minuten** Untätigkeit am Netz
(`0x384` = 900 Sekunden).

**Wie es auffiel — und warum das der eigentliche Punkt ist:** Die
Wachstumsmessung ging nicht auf. In 806 Minuten hätte
`positionsverlauf.verlauf` bei 18 Zeilen alle 5:14 Minuten rund **2772**
Zeilen schreiben müssen. Gewachsen war die Tabelle um **600**. Nach Abzug
der Schlafphasen bleiben **34 Runden × 18 Zeilen = 600** — exakt.

> **Eine Zahl, die nicht aufgeht, ist ein Fund. Eine Zahl, die man
> aufgehen lässt, ist ein Fehler.**

**Behoben:** `SCHLAF_ABSCHALTEN.bat` angelegt. Setzt Standby **nur am
Netzbetrieb** auf „nie", zeigt vorher den alten Wert, fragt nach und ist
umkehrbar. Der Akkubetrieb bleibt unverändert.

**Noch nicht ausgeschlossen:** Der Ruhezustand (Hibernate) hat einen
eigenen Zeitgeber, und „moderner Standby" mancher Geräte ignoriert diese
Einstellung teilweise. Beides erst prüfen, wenn nachts wieder Daten
fehlen — nicht auf Verdacht umstellen.

---

### 96. ⚠️ OFFEN — Ein Telegram-Zugang steht im Klartext im Quelltext

`v4_referenz/trading_imperium_v4_25_ALARM.py:2271` enthält einen
Telegram-Bot-Zugang als Zeichenkette im Programmtext.

**Kein akuter Konflikt:** Über Fingerabdrücke verglichen (SHA-256,
gekürzt) ist es **nicht** derselbe Zugang wie `TELEGRAM_BOT_TOKEN` in
`.env` — V4 und V6 stören sich also nicht gegenseitig. Zwei Poller auf
demselben Zugang würden einander Nachrichten wegnehmen; das passiert hier
nicht.

**Trotzdem offen:** Ein Zugang im Quelltext ist ein Zugang, der in jeder
Kopie, jedem Backup und jedem ZIP mitreist. Er gehört gewechselt und
danach aus `.env` gelesen wie bei V6.

*Der Wert wird hier bewusst nicht wiederholt.*

---

### 97. ✅ BEHOBEN (02.09.) — Der Bot friert ein, wenn jemand in sein Konsolenfenster klickt

**Gefunden am 02.09.2026, nachdem der Bot dreimal hintereinander im Start
stehenblieb.** Der Mechanismus hat mit dem Bot nichts zu tun — er trifft
jedes Programm, das in eine Windows-Konsole schreibt.

`schon_bekannt.py`: `QuickEdit` und `Schnellbearbeitung` **NEU**;
`start_bot.bat` und `Konsole` **BEKANNT** — dies ist deshalb eine
**Ergänzung** zu Handbuch 8.1 („Zum Doppelklicken") und zur Tabelle der
Betriebs-Skripte (Handbuch Zeile 5235), nicht ein Fund über einen neuen
Gegenstand.

#### Das Krankheitsbild

Dreimal in Folge — 13:11, 13:17 und 13:27 UTC — blieb der Start an
**exakt derselben Stelle** stehen:

```
[2026-09-02T13:17:15] [INFO] [REBAL] Zustand wiederhergestellt: enabled=True, dry_run=True
[2026-09-02T13:19:04] [INFO] [WAECHTER] Buecher-Check OK
[2026-09-02T13:24:04] [INFO] [WAECHTER] Buecher-Check OK
```

Danach nichts mehr. Die nächste Zeile hätte
`app.py:4102` schreiben müssen: *„🚀 Trading Imperium V6 startet…"*. Sie
kam nie. Zum Vergleich der funktionierende Lauf vom Vortag: dieselbe
Stelle, 70 Sekunden Pause, dann ging es weiter.

**Was besonders in die Irre führte:**

| Anzeichen | was man daraus schloss | was stimmte |
|---|---|---|
| CPU 17 %, 23 Threads | „er rechnet, alles gut" | er rechnete in Threads, die nichts ausgeben |
| Fenster „reagiert: True" | „kein Absturz" | das Cockpit-Fenster ist ein anderes Fenster |
| `Buecher-Check OK` alle 5 Min | „der Scheduler läuft" | dieser Thread schreibt nur ins Log, nicht auf die Konsole |
| Tickets wurden gefressen | „der Bot arbeitet" | auch der Ticket-Wächter gibt nichts auf der Konsole aus |

> **Ein Prozess, der CPU verbraucht, ist kein Prozess, der arbeitet.**
> Genauso wenig wie ein Prozess in der Liste ein Prozess ist, der sammelt.

#### Die Ursache

```
HKCU\Console  QuickEdit = 1
```

Der **Schnellbearbeitungsmodus** der Windows-Konsole ist eingeschaltet.
Wird in einem Konsolenfenster Text markiert — auch versehentlich, durch
einen einzigen Klick ins Fenster —, blockiert Windows **jede weitere
Ausgabe**. Der schreibende Prozess bleibt an seiner nächsten Zeile
stehen, bis jemand die Markierung aufhebt. Alles, was nicht schreibt,
läuft weiter.

Das ist kein Fehler des Bots und auch keiner von Windows im engeren
Sinne — es ist eine Voreinstellung, die für ein Programm gedacht war,
aus dem man gelegentlich etwas herauskopiert, nicht für einen Dauerläufer.

#### Der Beweis — A/B, dieselbe Maschine, dieselbe Minute

| Ausgabe geht … | Ergebnis |
|---|---|
| ins Konsolenfenster | hängt; *„V6 startet"* kommt nie |
| in eine Datei umgeleitet | *„V6 startet"* nach **50 s**, danach DXY, WebSocket, XGBoost |

Zusätzlich abgesichert mit einem Stapelabzug (`faulthandler`) des
laufenden Prozesses: **kein einziger Thread hing** — Flask bediente,
WebSocket empfing, Scheduler lief. Es war ausschließlich die Ausgabe
blockiert.

#### Die Behebung

`start_bot.bat` leitet die Ausgabe jetzt in eine Datei um:

```bat
"%PY%" app.py > "%~dp0data_store\jobs\bot_konsole.log" 2>&1
```

Eine Datei kann nicht blockiert werden. Damit ist die **ganze
Fehlerklasse** weg — unabhängig davon, ob jemand ins Fenster klickt.

Zwei Kleinigkeiten dazu:

* Die Datei des vorherigen Laufs wird nach `.vorher` verschoben statt
  überschrieben. Nach einem Absturz ist sonst genau das weg, was man
  braucht.
* Endet der Bot mit einem Rückgabewert ungleich 0, druckt die `.bat` die
  letzten 25 Zeilen ins Fenster. Ein Fehler soll nicht in einer Datei
  verschwinden, die keiner öffnet.

Das eigentliche Protokoll des Bots (`data_store\system.log`) ist davon
nicht berührt — die umgeleitete Ausgabe ist nur das, was **daneben** auf
die Konsole ginge.

#### Was NICHT gemacht wurde, und warum

`HKCU\Console\QuickEdit` auf 0 zu setzen, würde die Ursache ebenfalls
beseitigen — aber nur für diesen Benutzer, nur bis jemand es
zurückstellt, und es ändert eine Windows-Einstellung für **alle**
Konsolenfenster. Die Umleitung wirkt lokal, ist im Projekt sichtbar und
überlebt jede Neuinstallation von Windows. Deshalb die Umleitung.

Wer den Bot von Hand ohne Umleitung startet, muss weiterhin wissen:
**nicht ins Fenster klicken.** Der Hinweis steht jetzt in `start_bot.bat`.

---

### 98. 🔴 AKUT (02.09.2026) — OneDrive verschob den laufenden Projektordner in die Cloud

**Gefunden am 02.09.2026 um 21:20, mitten in einer Messreihe.** Ein Befehl
meldete plötzlich `BOT-HANDBUCH.md: No such file or directory`. Beim Nachsehen
enthielt der Projektordner **33 Unterordner und null Dateien** — `app.py`,
`config.json`, alle `.md`, alle `.bat` waren verschwunden.

**Es war kein Datenverlust.** OneDrive hatte die **Ordnersicherung für den
Desktop** aktiviert und war dabei, das Projekt Datei für Datei nach
`C:\Users\<BENUTZER>\OneDrive\Desktop\trading_imperium_v6(21)` zu
**verschieben** — nicht zu kopieren.

**Der Stand um 21:29 (SICHER, gemessen):**

| Ort | Dateien | Größe | Wurzeldateien |
|---|---|---|---|
| Desktop (alt) | 68 | 468 MB | **0** |
| OneDrive (neu) | 6.361 | 1.120 MB | 236 |

**Warum ausgerechnet 68 übrig blieben, ist der Kern:** Es sind die Dateien,
die der laufende Bot **offen hält** — `telemetrie.db` (449 MB),
`positionsverlauf.db`, `schatten_universum.db`, `bot_state.json`. Windows gab
sie nicht frei, also blieben sie liegen. **Der laufende Prozess war der
einzige Grund, dass die Messdatenbank nicht mitgewandert ist.**

> Eine 449-MB-SQLite-Datei, die verschoben wird, während sie beschrieben wird,
> ist genau der Fall, für den Befund 28 die Warnung enthält. Es hat nur
> deshalb nicht zugeschlagen, weil der Bot sie festhielt.

**Was daran gefährlich ist — und nicht auffällt:**

1. Der Desktop ist **nicht** umgeleitet. Registry (`User Shell Folders\Desktop`)
   und Ordnerattribute geprüft: kein Reparse Point, kein Junction. Es sind
   also **zwei verschiedene Orte**, nicht zwei Namen für einen.
2. Der Bot lief unbeirrt weiter, weil er `app.py` im Arbeitsspeicher hat. Ein
   Neustart wäre in diesem Zustand **fehlgeschlagen** — `app.py` gab es am
   Startpfad nicht mehr.
3. `nachlauf.db` (19 MB) **war bereits drüben**, während der Sammler noch am
   alten Pfad suchte.
4. Die `.env` mit dem Telegram-Token liegt jetzt in der Cloud. Genau davor
   warnt `sicherung.py` im Kopftext: *„dort ist ein Token ein Risiko, das man
   nicht zurückholen kann."*

**Was getan wurde (02.09. 21:29–21:32):**

| Schritt | |
|---|---|
| OneDrive angehalten | durch Sven, Taskleiste → Synchronisierung anhalten |
| Rückholung | `robocopy /E /XC /XN /XO` — kopiert **nur**, was am Ziel fehlt |
| 6.295 Dateien / 1,086 GB zurück | 66 übersprungen, **8 Extras unberührt** (die aktiven Datenbanken) |
| Bot | **nicht** angehalten, PID 9180 durchgehend seit 20:42:14, Port 5050 |
| Gegenprobe | alle Kerndateien wieder da, heutige Änderungen in Handbuch, `OFFEN.md` und dieser Datei unversehrt |

**Der Auslöser ist OFFEN.** Vor 20:57 enthielt der OneDrive-Ordner nur
`desktop.ini`; um 21:20 lief die volle Ordnersicherung. Ob eine verzögerte
Ersteinrichtung des neuen Rechners oder ein Klick — nicht feststellbar.
`SICHERUNG_AUF_USB.bat` war es nicht: sie brach bei „kein Stick" ab und hat
`sicherung.py` nie aufgerufen.

**Noch offen — der eigentliche Fix.** Solange die **Ordnersicherung für den
Desktop** eingeschaltet bleibt, beginnt das Verschieben beim Fortsetzen von
vorn. Das Anhalten ist eine Pause, keine Lösung. Zu tun: in den
OneDrive-Einstellungen unter *Sicherung → Ordnersicherung verwalten* den
**Desktop abschalten**. Das ist eine Systemeinstellung und gehört Sven.

**Die Ironie, die man festhalten sollte:** Was hier passierte, war der Versuch
einer Sicherung — desselben Projekts, dessen fehlende Sicherung seit dem
11.08. als größtes Einzelrisiko in Befund 28 steht. Nur wurde daraus ein
Verschieben statt eines Kopierens, und das mitten im Betrieb. Eine Sicherung,
die das Original wegnimmt, ist keine.

**Priorität:** HOCH · **Risiko** 9/10 (traf die 449-MB-Messdatenbank knapp
nicht) · **Aufwand** 1/10 (ein Schalter) · **Konfidenz:** SICHER für Ablauf
und Zahlen (Dateizählung, Registry, Prozessliste, robocopy-Protokoll),
**OFFEN** für den Auslöser. Siehe auch Befund 28.

---

**ZWEITER DURCHLAUF UND UMZUG NACH `C:\` (03.09.2026). SICHER.**

Der PC-Neustart hob die Synchronisierungs-Pause auf. Um 14:35 lief OneDrive
wieder, und diesmal war der Bot nicht da, um seine Datenbanken festzuhalten:
**der Desktop-Ordner war vollständig leer, auch die Datenbanken waren weg.**
Bestätigt, was oben stand — Anhalten ist eine Pause, keine Lösung.

**Entscheidung (Sven, 03.09.):** Das Projekt liegt jetzt unter
`C:\trading_imperium_v6(21)`. OneDrive sichert nur Desktop, Dokumente und
Bilder; direkt unter `C:\` kommt es nicht mehr heran. Das beendet die Ursache
statt des Symptoms.

**Was nachgezogen wurde** — dieselben Stellen wie bei U3, die Liste stimmt:

| Stelle | |
|---|---|
| `.claude/settings.json` (3 Haken) | ✅ auf `C:/trading_imperium_v6(21)/...`, alle drei Ziele geprüft |
| Aufgabe `TI6-Sammler` | ✅ Programm + Arbeitsverzeichnis |
| Aufgabe `ForschungCapture` | ✅ Programm + Arbeitsverzeichnis |
| `lage_erzeugen.py:233` | **nicht nötig** — nutzt `expanduser("~")`, zeigt auf den OneDrive-Sicherungsordner, nicht auf den Projektort |
| `check_punkt_a.py:5`, `check_install.py:3` | nur Kommentare |

### Die Konfliktkopien — und ein Fehler von mir

OneDrive hatte **6.529 Konfliktkopien** angelegt (13.015 Dateien statt ~6.400).
Beim Aufräumen galt die Regel: die neuere Fassung gewinnt, die ältere wandert
nach `_onedrive_konflikte`, **gelöscht wird nichts**. Protokoll:
`_onedrive_konflikte_protokoll.txt`. Ergebnis: 160 getauscht, 6.156 beiseite.

**Der Tausch nach Zeitstempel allein war falsch.** `telemetrie - Kopie.db` war
**0 Bytes**, aber sieben Sekunden neuer als das Original — also machte das
Skript die leere Datei zur Hauptdatenbank. Dasselbe bei `nachlauf.db` und
sieben weiteren Dateien.

> Aufgefallen ist es nur, weil danach `quick_check` **und** die Zeilenzahl
> geprüft wurden: 449,6 MB waren plötzlich 0,0 MB und 1.128.382 Zeilen waren
> 0. Wer nur `quick_check` gelesen hätte, hätte „ok" gesehen — eine leere
> Datenbank ist formal fehlerfrei.

Behoben, weil verschoben statt gelöscht wurde. Alle vier Datenbanken sind
zurück und geprüft:

| | Größe | `quick_check` | Zeilen |
|---|---|---|---|
| `telemetrie.db` | 449,6 MB | ok | 1.128.382 |
| `positionsverlauf.db` | 16,9 MB | ok | 68.546 |
| `nachlauf.db` | 19,2 MB | ok | 49.447 |
| `schatten_universum.db` | 0,7 MB | ok | 2.321 |

**Lehre für das nächste Aufräumen:** Zeitstempel allein entscheidet nicht.
Eine Datei, die auf einen Bruchteil schrumpft, ist verdächtig — unabhängig
davon, wie neu sie ist.

### Zwei Datenlücken, die bleiben

1. **`telemetrie.db` 02.09. 21:37 bis 03.09. 04:40** — der Bot lief weiter
   (`positionsverlauf.db` schrieb bis 04:40), aber die Telemetrie war zu dem
   Zeitpunkt schon verschoben. Auf der ganzen Platte gibt es keine neuere
   Fassung; die Lücke ist real, rund sieben Stunden.
2. **Sieben Dateien** legte der Bot in der Lücke neu und klein an
   (`trades_log_v4.json`, `geldfluss_history.json`,
   `daily_loss_schatten.json`, vier Protokolle). Die vollständigen Fassungen
   stehen wieder; die kleinen liegen daneben als `*.luecke_20260903`, damit
   nichts verloren geht. Für `nachlauf.db` gilt dasselbe: 523 Zeilen aus der
   Lücke liegen in `nachlauf.db.luecke_20260903`.

### Stand nach dem Neustart (03.09. 14:55)

| Prozess | |
|---|---|
| V6-Bot | PID 6796, Port 5050, frisch |
| V4-Referenzbot | PID 964, schreibt `imperium_state.json` |
| Schatten-Universum | PID 11892 |
| Forschungs-Sammler + Starter | PID 2180, 11652 |
| Positionsverlauf | PID 3772 |
| Täglicher Sammler | läuft als geplante Aufgabe, nicht dauerhaft |

Der Bot braucht nach dem Start **gut zwei Minuten**, bis Port 5050 steht —
eine Messung nach 15 Sekunden meldet fälschlich „läuft nicht".
