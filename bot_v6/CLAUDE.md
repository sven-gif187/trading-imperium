# CLAUDE.md — die Regeln, die in jeder Sitzung gelten

**Angelegt 19.08.2026.** Diese Datei lädt Claude Code automatisch bei jedem
Start. Sie ist bewusst kurz. Sie ersetzt nichts — sie sagt, **was gilt, wenn
zwei Quellen sich widersprechen**.

*Anlass:* Am 19.08. stellte sich beim Abgleich eines neuen Audit-Auftrags
heraus, dass drei Regelquellen nebeneinander liefen (`MASTERPROMPT.md`, die
Chat-Prompts, das Gedächtnis) und sich an drei Stellen widersprachen — Sprache,
Bestandsschutz, Konfidenz-Kennzeichnung. Wer den Regelsatz in jedem Chat neu
einfügt, bekommt in jedem Chat eine andere Fassung.

---

## 0. DIE WICHTIGSTE REGEL — alles doppelt und dreifach prüfen

**Gilt für ALLES, nicht nur für Messungen.** Code, Reparaturen, Diagnosen,
Zahlen, Behauptungen über den Systemzustand — nichts wird gemeldet, bevor es
gegengeprüft ist. Sven-Anweisung vom 17.08.2026, geschärft am 18.08.

*Warum:* An einem einzigen Tag (17.08.) sind vier Fehler unterlaufen, die alle
gleich aussahen: **eine Erfolgsmeldung, die keine war.** Eine Reparatur meldete
„400 Kurse nachgetragen" und schrieb viermal denselben Wert. Ein Werkzeug wurde
für kaputt erklärt, ohne nachzusehen, ob sein Ergebnis existiert — es existierte.
Sven hat die Häufigkeit dieser Selbstkorrekturen ausdrücklich angesprochen:
*„zum zehnten Mal korrigiert — wann hat das ein Ende?"* Sie kosten Vertrauen,
auch wenn der Fehler selbst gefunden wird.

**Die Regel, die die Fehlerquote wirklich senkt:**

> Keine ausgerechnete Zahl melden, bevor sie gegen **einen von Hand
> nachgerechneten Einzelfall** geprüft ist. Nicht gegen Plausibilität,
> nicht gegen eine Anzahl — gegen einen bekannten Wert.

**Im Einzelnen:**

| Was | Wie gegenprüfen |
|---|---|
| **Code** | Vor dem Melden: Syntax prüfen, und nachsehen, ob jede benutzte Variable an dieser Stelle wirklich existiert. Nie „müsste passen" |
| **Reparaturen** | Danach die **Werte selbst ansehen**, nicht ihre Anzahl. Prüfmuster: *Werte, die identisch sein dürfen, aber nicht identisch sein sollten* — zwei Kurse zu verschiedenen Zeitpunkten sind nie gleich |
| **Diagnosen** | Vor „X ist kaputt": nachsehen, ob das Ergebnis von X trotzdem da ist |
| **Zahlen** | Zweite unabhängige Quelle suchen. Stimmen beide überein, gilt der Wert — sonst nicht |
| **Fallzahlen** | Immer fragen, wie viele davon **unabhängig** sind. Der Bot prüft alle 12 s; bei Horizont H passen in T Tage nur T·24/H nicht überlappende Fenster |
| **Eigene Vorschläge** | Gegenlesen, ob sie sich widersprechen |
| **Prüfwerkzeuge** | Gegentest in **beide** Richtungen: meldet es nichts Falsches — **und** findet es den echten Fall? |

**Lieber ein „nicht entscheidbar" melden als eine Zahl, die gut aussieht.**

### Pflicht vor JEDEM neuen Befund

```bash
python schon_bekannt.py <datei.py:zeile>
python schon_bekannt.py <bezeichner>
```

Meldet es **BEKANNT**, ist es kein neuer Fund, sondern hoechstens eine
**Ergaenzung** - und muss als solche geschrieben werden, mit Verweis auf
den vorhandenen Abschnitt.

*Warum:* Am 19.08.2026 wurde die Gebuehren-Doppelbuchung als neuer Fund
gemeldet. Sie stand seit dem 18.08. in Handbuch 4.50, mit derselben
Codezeile. Grund war nicht Schlamperei, sondern Bauart: Das Handbuch hat
6.500 Zeilen, niemand liest es vor jedem Befund, und die Ueberschriften
sind erzaehlerisch - man erkennt sie nur, wenn man den Befund schon kennt.

> **Eine Regel, die man befolgen muss, wird vergessen. Eine Pruefung, die
> zwei Sekunden dauert, wird gemacht.**

Nachschlagetabelle: `WISSENSSTAND.md` (147 Codestellen),

### Zweite Pflicht: in den alten Gespraechen suchen — bei ALLEM

**Nicht nur bei Datenbanken. Bei jedem Thema dieses Projekts.**
Sven am 19.08.: *"nicht nur das wissen ueber datenbanken sondern das
wissen um unser ganzes projekt - komplette chats abgleichen was schon
besprochen wurde, bitte trag das mit ein, in die pflicht"*

Vor jeder Arbeit an irgendeinem Thema:

```
search_session_transcripts("<stichwort>")
```

**Immer, bevor:**
- eine Datei angelegt oder ein Werkzeug gebaut wird
- ein Parameter, eine Schwelle oder eine Konstante geaendert wird
- etwas als Befund gemeldet wird
- eine Struktur, Trennung oder Abschaltung "reparieren" werden soll
- eine Frage beantwortet wird, die nach "haben wir das schon mal
  besprochen?" klingt

**Mindestens zwei Suchbegriffe** — der Fachbegriff und das Alltagswort.
Beispiel: `Trailing` und `Ratsche`; `forschung.db` und `Grenze A7`.

Findet die Suche etwas, gilt es als **Entscheidung**, nicht als Vorschlag.
Eine bestehende Entscheidung wird nicht umgeworfen, sondern angesprochen.

**Das Projektgedaechtnis umfasst 20 Sitzungen (27.07. bis heute):**

| Zeitraum | Sitzungen ueber |
|---|---|
| 27.–31.07. | Uebergabe, Projektordner, E7-Bestandsaufnahme, Audit, Nachkauf-Schutz, Prompt-App |
| 04.–06.08. | Reibungskosten und Break-even, stille Fruehausstiege, Tab-Audit |
| 10.–11.08. | balanced-Modus, Masterprompt, RR-Gate-Forensik, Lernsystem, Dateianalyse |
| 13.–18.08. | V6-Audit, NAECHSTE-SESSION, Bilderreihe, Aufgaben vor Bot-Start, Kurzes Update |

Wer nicht weiss, wonach er suchen soll, listet sie mit `list_sessions`.

**Das Ergebnis dieser Durchsicht steht in `PROJEKT-ENTSCHEIDUNGEN.md`** —
chronologisch vom 27.07. an, jede Stelle, an der etwas bewusst so ist,
wie es ist. **Diese Datei zuerst lesen**, bevor irgendetwas "repariert"
wird. Was dort steht, ist eine Entscheidung, kein Vorschlag.

*Warum:* Am 19.08. wollte ich die Rundgang-Befunde in `forschung.db`
uebertragen. Sven stoppte mich - die Trennung war eine bewusste
Entscheidung. Die Suche nach `Grenze A7` findet sie in der Sitzung vom
18.08., wortwoertlich: *"Keine Verbindung, kein gemeinsames Schema, kein
Schreibzugriff in beide Richtungen."*

Das Wissen war da. Es war durchsuchbar. Ich habe nicht gesucht.

> **Das Gedaechtnis fehlt nicht - der Griff danach fehlt.** Kein
> Uebergabeprotokoll behebt das: Die Dokumentation umfasst 264.000 Token
> bei 200.000 Kontext. Ein weiteres Dokument macht die Zahl groesser,
> nicht kleiner.

**Reihenfolge bei JEDEM Thema — nicht nur bei neuen:**
1. `python schon_bekannt.py <bezeichner>` — steht es in den Dokumenten?
2. `search_session_transcripts("<stichwort>")` — wurde es besprochen?
   Mit mindestens zwei Begriffen: Fachwort und Alltagswort.
3. Erst dann bauen, aendern oder als Befund melden.

**Beide Pruefungen dauern zusammen unter einer Minute.** Ein Fehler, den
sie verhindern, kostet eine Stunde — und einmal fast eine eingefrorene
Forschungsdatenbank.
neu erzeugen mit `python schon_bekannt.py --index`.

---

## 1. Rangfolge — wer gewinnt bei Widerspruch

1. **Diese Datei** (CLAUDE.md) — bei direktem Widerspruch
2. **`MASTERPROMPT.md`** — die ausführliche Fassung, alles Fachliche
3. **Der Auftrag im Chat** — gilt für *diese* Aufgabe, hebt 1 und 2 **nicht** auf
4. Alles Übrige (Übergaben, ältere Prompts) ist Momentaufnahme, keine Regel

Ein Chat-Prompt, der einer Dauerregel widerspricht, ist **kein** stiller
Freibrief. Er wird gemeldet, dann entscheidet Sven.

---

## 2. Sprache — entschieden am 19.08.2026

**Alltagssprache, das Fachwort in Klammern dahinter.** Beispiel:
„Sperre nach Verlustserie (Cooldown)", „Warteauftrag (Limit-Order)".

Sven will die Begriffe lernen, nicht überrollt werden. Das gilt auch dann,
wenn ein Chat-Prompt „kein Basics-Gerede" verlangt: **Härte gehört ins Urteil,
nicht in die Wortwahl.**

Code-, Datei-, Tabellen- und Spaltennamen bleiben englisch.
Direkt, kritisch, kein Lob ohne Befund.

---
### 2a. Nichts zum Abtippen — eine `.bat` zum Doppelklicken

**Ergänzt 02.09.2026 beim Umzug auf den neuen Rechner.**

Soll Sven etwas selbst starten, bekommt er **keine Befehlszeile**, sondern
eine `.bat` zum Doppelklicken. Sie erklärt oben in Kommentarzeilen, was sie
tut und warum, prüft ihre Voraussetzungen selbst und sagt es laut, wenn
etwas fehlt — statt lautlos nichts zu tun.

**Und jeder Pfad gehört in `"..."`.** Zwei Fallen auf diesem Rechner, beide
brechen `cmd` zuverlässig:

* der Ordnername enthält Klammern — `trading_imperium_v6(21)`
* der Benutzername enthält ein Leerzeichen — `Sven <NACHNAME>`

In `.bat`-Dateien wird der eigene Ort über `%~dp0` bestimmt, nie über
`%CD%` allein und nie fest verdrahtet. In Python entsprechend über
`os.path.dirname(os.path.abspath(__file__))`. Fest verdrahtete Pfade gibt
es nur an zwei Stellen, weil es dort nicht anders geht — den geplanten
Aufgaben und `.claude/settings.json` (Handbuch 10.10).


## 3. Ein Konfidenzsystem — vier Stufen, keine anderen

| Stufe | Bedeutung |
|---|---|
| **SICHER** | Im Code, Log oder Messwert nachweisbar — **mit Fundstelle** (`datei.py:123`) |
| **WAHRSCHEINLICH** | Plausibel, aber ungeprüft |
| **VERMUTUNG** | Hypothese, kein Beleg |
| **OFFEN** | Information fehlt und **verhindert** eine sichere Entscheidung |

Keine Parallelsysteme (kein zusätzliches WEISS/SCHLIESSE/VERMUTE). **OFFEN**
ist Pflicht, wo es zutrifft — es ist die einzige Stufe, die zu einer Handlung
führt: Daten beschaffen.

Auch der **Umfang der eigenen Prüfung** wird genannt: „Struktur gesichtet,
nicht jede Datei gelesen" ist eine Pflichtangabe, keine Schwäche.

---

## 4. Bestandsschutz — was ohne Freigabe nie angefasst wird

Ausführlich in `MASTERPROMPT.md` Abschnitt 0. Der Kern:

1. **Der laufende Papierhandel** (`app.py`). Nicht anhalten, nicht neu starten
   ohne zu fragen. Vor jedem Neustart prüfen, wer Port 5050 hält — Prozesse
   *zählen* führt in die Irre (der Windows-Startwrapper erzeugt immer ein
   Elternprozess-Paar, das wie zwei Instanzen aussieht).
2. **Die vier Cockpit-Reiter** (Chartanalyse, Geldfluss, Terminal, Zyklus) —
   bewusst reines Beobachtungsdeck, vom Handelspfad getrennt.
3. **`docs/forschungsprogramm_2026-07/forschung.db`** — absichtlich abgekoppelt.
   Nicht mit `data_store/telemetrie.db` verwechseln.
4. **Forschungs-Capture und V4-Referenzbot** — eigene Prozesse, laufen mit.
5. **Was im Code als bewusst stillgelegt markiert ist, ist eine Entscheidung,
   kein Bug.** Betrifft u. a. Grid-Bot, `backtest/optimizer.py`,
   `futures_trader.py`, `multi_exchange.py`, TradingView-Webhook, Reddit.
   **Solche Stellen nicht erneut als Befund melden** — sie stehen bereits in
   `GEFUNDENE-PROBLEME.md`.

---

## 5. Messfenster — der Grund für den Freeze

**Laufendes Fenster: `E6_messfenster` / `E7_filter_schaerfer`, bis
18.09.2026.**

*Verlaengert am 21.08. auf den 18.09.*, Entscheidung Sven: *"dass lass ich
den verfickten bot jetzt eben nochmal 20 tage laenger als besprochen
laufen"*. Zuvor am 20.08. von 27.08. auf 29.08. verlaengert.

**Der Grund fuer die 20 Tage:** Nicht die 30 Faelle des Messfensters -
die sind mit 42 erwartbar erreicht -, sondern **Kriterium A der
Freigabe: 100 Verkaeufe.** Bei 3,05 Verkaeufen am Tag ist das um den
19.09. erreichbar. Zum ersten Mal in sieben Monaten steht damit eine
Zahl in Aussicht, die eine echte Antwort erlaubt.

**Die Bedingung, an der alles haengt:** In diesen Tagen darf **keine
einzige Regel** geaendert werden. Jede Verhaltensaenderung setzt die
Zaehlung auf null - das ist der Mechanismus, der das Projekt sieben
Monate lang zurueckgeworfen hat. Aus sieben Monaten Laufzeit sind
dadurch effektiv sechs Tage verwertbare Daten geworden.

**Das verbindliche Datum steht in `config_zielgroessen.json`
(`messfenster_ende`), nicht hier.** `stichtag.py` und das Terminal
lesen es von dort. Wer es aendert, aendert es dort - sonst laufen
zwei Wahrheiten nebeneinander.

Solange es läuft: **keine Änderung, die das Verhalten des Bots berührt.**
Erlaubt sind nur Änderungen, die ausschließlich *aufschreiben* (Logs,
Auswertungen, Dokumentation).

**Jede Verhaltensänderung braucht eine Epochengrenze** (`config_epochs.json`),
sonst sind alle Vorher-Nachher-Vergleiche wertlos.

### Die Stichtags-Regel — Befunde blockieren den Live-Weg nicht mehr

**Beschlossen am 21.08.2026 von Sven**, nachdem er sagte: *„jeden Tag kommen
neue Erkenntnisse, was noch fehlt — ich habe keine Hoffnung mehr, dass ich den
scharf kriege."* Berechtigt: 68 Befunde in sieben Monaten, und jeder neue
schob den Live-Gang weiter nach hinten.

**Ab dem Ende des Messfensters (jetzt 18.09.2026) gilt:**

*Die Regel wurde am 21.08. fuer den 29.08. beschlossen. Mit der
Verlaengerung des Messfensters wandert sie mit - sie haengt am Stichtag,
nicht an einem festen Datum. Waehrend das Fenster laeuft, gilt ohnehin
der Freeze: dann blockiert nicht der Befund, sondern die Messung.*

| | |
|---|---|
| **Weiter sammeln** | Neue Befunde werden **unverändert** gesucht, gemessen und geschrieben. Daran ändert sich nichts |
| **Aber nicht mehr blockieren** | Ein Befund hält den Live-Weg nur auf, wenn er **Kapital- oder Datenverlust** riskiert |
| **Alles andere** | kommt hinten an die Liste und wird **nach** der Freigabe gemacht |

*Warum:* Solange jeder Fund den Weg versperrt, kommt der Bot nie live — denn
Funde hören nie auf. Das ist keine Nachlässigkeit, sondern die Trennung
zwischen *„gefährlich"* und *„verbesserungswürdig"*. Die erste Gruppe blockt,
die zweite wartet.

**Nicht betroffen:** Die Freigabekriterien selbst (`go_live_check.py`) bleiben
unangetastet. Kriterium F — der belegte Vorteil — entscheidet weiterhin allein.

---

**Ausnahme vom Freeze:** Ein Fund mit Kapital- oder Datenverlustrisiko wird
**sofort** gemeldet — als eigener Block, mit Fundstelle. Der Freeze bleibt
trotzdem bestehen; die Entscheidung trifft Sven.

---

## 6. Wo was hingehört — es gibt keine sechste Liste

| Datei | Wofür | Regel |
|---|---|---|
| `OFFEN.md` | **Die eine Liste offener Punkte.** Was hier nicht steht, ist nicht offen. | Jeder Punkt wird **gegen das Verzeichnis geprüft** (Commits, Handbuch, Code) — nie aus einer Übergabe abgeschrieben |
| `GEFUNDENE-PROBLEME.md` | Befunde mit Nummer, dauerhaft. Auch behobene bleiben stehen. | Neue Befunde bekommen die nächste freie Nummer |
| `BOT-HANDBUCH.md` | Das *Warum* — zu jeder Änderung ein Abschnitt | Pflicht seit 11.08. Keine Änderung ohne Eintrag |
| `BOT-HANDBUCH.pdf` | wird von `handbuch_pdf.py` erzeugt | **Nie von Hand ändern** |
| `ENTWICKLERHANDBUCH.md` | Chronik, wird über `tickets.txt` gefüllt | nicht von Hand, sondern per Ticket |
| `tickets.txt` | Eingang für die Chronik | `STICHWORT: Text`, binnen 30 s eingelesen. **Nur fünf Stichworte sind gültig:** `SPEICHERN`, `ERLEDIGT`, `BUG`, `DOKUMENTIEREN`, `NOTIZ`. Jedes andere wird **still verworfen** — und beim nächsten gültigen Ticket **mitgelöscht** (Befund 87). Im Zweifel `DOKUMENTIEREN:` nehmen |
| `PROJEKT-ENTSCHEIDUNGEN.md` | Was **bewusst** so ist — aus allen 20 Sitzungen | **Zuerst lesen.** Wird beim Finden ergänzt, nicht von Hand nachgetragen |
| `LAGE.md` | Was gerade läuft | **Nie von Hand.** `python lage_erzeugen.py` |

**Achtung Dateinamen:** Es heißt `BOT-HANDBUCH.md` und `BOT-HANDBUCH.pdf`
(mit Bindestrich, groß). Nicht `bothandbuch.md`. Wer den falschen Namen
schreibt, legt ein zweites, leeres Handbuch an.

---

## 7. Dauerregeln

1. **Nichts anschließen ohne Messung.** Vier fertige Bausteine wurden schon
   verworfen, weil sie schlechter waren als die einfachste Alternative.
2. **Die Trivial-Latte immer mit ausweisen** — „immer nein sagen" schlägt viele
   Modelle. Ein Modell ohne diesen Vergleich gilt als ungemessen.
3. **Ursache vor Symptom.** Kein `try/except`, kein Fallback, kein
   UI-Workaround, um einen Fehler zu verstecken. Bei jedem Fehler:
   Ursachenkette, Blast Radius, drei Fix-Optionen (minimal/sauber/strukturell)
   mit Risiko / Aufwand / Wirkung je 0–10, genau eine Empfehlung.
4. **Kein stilles Scheitern.** Kein Fehler darf nur geloggt und dann ignoriert
   werden. Hintergrund-Jobs: echter `pythonw`-Pfad, kein ungeschütztes
   `print()`, nach dem Anlegen **prüfen, ob wirklich etwas passiert**.
5. **Jede Änderung** → Abschnitt in `BOT-HANDBUCH.md` **und** Ticket in
   `tickets.txt`. Was nur im Chat steht, ist vergessen, sobald das Fenster
   weiterläuft.
6. **Vor jeder Auswertung:** `python prozess_frische.py` — beantwortet, ob ein
   laufender Prozess noch mit altem Programmtext arbeitet.
7. **Erst bestehende Aufgaben fertig.** Neue Wünsche kommen ausdrücklich
   hinten an, sie verdrängen nichts Laufendes.

---

## 8. Zahlen, die man kennen muss

| | |
|---|---|
| Zielbörse | **Bitvavo, USDC-Märkte** (MiCA, AFM), **0,05 %** je Seite — seit E10 (14.10.2026, Entscheidung Sven). Vorher Bybit EU 0,25 % |
| Kosten je Runde (K-BASIS) | **0,150 %** ab E10 (0,10 Gebühr + 0,05 Schlupf, Bitvavo-Stichprobe) — **für ältere Epochen gilt weiter 0,505 %**. Nie aus `ccxt` holen |
| Herleitung | `pruefstand/berichte/2026-10-14_zielboerse.md`, `pruefstand/gebuehren.json` [ZIELBOERSE BITVAVO 14.10.2026] |
| Betriebsmodus | `paper` (Papierhandel), nie unbeabsichtigt `live` |
| Datenquelle | Binance (nur Kurse), Zielbörse Bitvavo USDC (Kursabstand < 0,01 %, gemessen 14.10.) |

**Bekannter offener Fehler:** An acht Stellen im Projekt steht noch die alte
Kostenannahme 0,32 % bzw. 2 × 0,10 %. Liste in `BOT-HANDBUCH.md` 4.53,
Korrektur wartet auf die Epochengrenze nach dem 18.09.
