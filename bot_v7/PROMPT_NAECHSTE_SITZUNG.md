# Prompt für den nächsten Chat — Stand 11.09.2026, 17:45

*Alles hier ist am Code und an den Daten nachgemessen, nicht aus dem
Gedächtnis geschrieben. Fundstellen stehen dabei.*

---

Alles ab hier kopieren:

---

Du arbeitest mit mir (Sven) an **Trading Imperium V6**, einem
Krypto-Handelsbot im Papiermodus. Wir sind seit sieben Monaten dran. Lies
zuerst `CLAUDE.md` — die Regeln dort gelten vor allem anderen.

## Wie ich angesprochen werden möchte

**Alltagssprache, das Fachwort in Klammern dahinter** — also „Sperre nach
Verlustserie (Cooldown)", nicht nur „Cooldown". Ich will die Begriffe
lernen, nicht überrollt werden. **Härte gehört ins Urteil, nicht in die
Wortwahl.** Kein Lob ohne Befund.

**Keine Befehlszeilen zum Abtippen.** Wenn ich etwas selbst starten soll,
bau eine `.bat` zum Doppelklicken. Der Ordnername hat Klammern —
`trading_imperium_v6(21)` — das bricht `cmd` ohne Anführungszeichen.

**Vier Konfidenzstufen, keine anderen:** SICHER (nur mit Fundstelle
`datei.py:123`) · WAHRSCHEINLICH · VERMUTUNG · OFFEN. Nenne auch den
Umfang deiner Prüfung.

---

## WO WIR GERADE STEHEN

**Der Freeze ist seit dem 11.09.2026 beendet.** Grund: Kriterium A der
Freigabe ist erreicht — **118 Verkäufe** seit dem Umbau, nötig waren 100.
Der einzige Zweck des Messfensters ist damit erfüllt.

Laufende Epoche: **`E8_gebuehren_korrekt`** (seit 11.09., 14:45 UTC).
Vergleiche über diese Grenze hinweg sind ungültig.

### Die Antwort, die sieben Monate gekostet hat

`python go_live_check.py` sagt heute:

| | | ist | soll |
|---|---|---|---|
| **A** | Stichprobe | ✅ 118 Verkäufe | ≥ 100 |
| **B** | Erwartungswert | ❌ **−0,416 $** | > 0 |
| **C** | Chance/Risiko | ❌ 0,98 bei 39 % Treffern | ≥ 1,88 |
| **E** | Größter Rückgang | ❌ 29,84 % | ≤ 15 % |
| **F** | **Vorteil belastbar** | ❌ **−0,908 … +0,076 $** | untere Grenze > 0 |
| **G** | Laufzeit | ✅ 43,8 Tage | ≥ 14 |

**Kriterium F ist das entscheidende:** Das Vertrauensintervall enthält die
Null. Der Bot hat **keinen nachweisbaren Vorteil**.

**Der Kern des Problems, dreimal unabhängig gemessen:** Die Trefferquote
ist **brutto 80,5 %**, **netto 39,0 %**. Der Bot liegt in vier von fünf
Fällen richtig und verliert trotzdem — die Bewegungen sind kleiner als die
Kosten von **0,505 % je Runde** (K-BASIS, nie aus `ccxt` holen).

### Was am 11.09. gebaut wurde

1. **Gebühren-Doppelbuchung behoben** (Befund 42) —
   `execution/engine.py:401`: `filled_cost = amount - fee` statt `amount`.
   Vorher wurden **drei** Gebühren abgezogen statt zwei (am 01.09. als
   Faktor 3,00 über 14 Verkäufe gemessen: 0,75 % statt 0,505 %).
   Bewiesen mit `gebuehren_test.py` durch die echte Maschine, Gegenprobe
   bestanden. **Wirkt ab dem nächsten Bot-Start.**

2. **Warte-Aufträge gemessen** (Befund 101) — siehe unten, noch nicht gebaut.

---

## DER WICHTIGSTE BEFUND — bitte zuerst lesen

**Befund 103, gemessen am 11.09.:** Der Einstiegs-Score trägt.

| | n | Ergebnis | Trefferquote |
|---|---:|---:|---:|
| **Score 3–6** | 23 | **−0,540 %** | 60,9 % |
| **Score 7–10** | 34 | **+0,468 %** | **79,4 %** |

**+1,008 Prozentpunkte Unterschied.** Zufallstest über 20.000 Mischungen:
So groß entsteht er zufällig nur in **1,18 %** der Fälle.

**Und: das Problem ist nicht der Einstieg, sondern der Ausstieg.** Der Kurs
lief im Median **+1,350 %** zu unseren Gunsten (`mfe_pct`), in **92,5 %**
der Fälle über der Kostenlinie. Gebucht wurden −0,28 %. Der Bot sieht die
Bewegung und lässt sie liegen.

**Die Kette, die ins Plus zeigt:**

| | |
|---|---:|
| Score ≥ 7, brutto | +0,468 % |
| minus echte Kosten | −0,505 % |
| **heute** | **−0,04 %** |
| plus Warte-Aufträge | +0,20 % |
| **möglich** | **+0,16 %** |

> **Nicht anschließen, bevor 30 NEUE Verkäufe mit vollständigem Score
> vorliegen.** Die Schwelle stammt aus denselben Daten, an denen sie
> gemessen wurde — das ist Überanpassung, solange sie sich nicht vorwärts
> bestätigt. Bei ~4 Verkäufen am Tag ist das in gut einer Woche
> entscheidbar. **Das ist die erste Frage, die du beim Start prüfen
> sollst.**

**Befund 88 wurde am 11.09. behoben**, damit das überhaupt messbar wird:
Verkäufe entstehen auf zwei Wegen (`runtime/exit_monitor.py:413` und
`app.py:1658`), und nur einer schrieb `entry_score`, `entry_strategie`,
`position_id`, `haltedauer_min`, `mfe_pct`, `mae_pct` mit. Deshalb stand
die Rechnung oben auf **57 von 120** Verkäufen. Jetzt schreiben beide alles.
Prüfen mit `python schreibwege_test.py`.

**Der Anteil muss steigen.** Heute: `entry_score` bei 47,5 %. Wenn er nach
ein paar Tagen nicht deutlich höher liegt, greift die Reparatur nicht —
das ist der Beleg, den du einfordern musst.

---

## AUFGABE 1 — Warte-Aufträge bauen (das Wichtigste)

**Gemessen und abgesichert, Bau steht aus.** `warteauftrag_gegenauslese.py`
liest nur und rechnet.

**Das Ergebnis:** Warte-Aufträge (Limit-Orders) statt Sofortkauf bringen
**+0,18 bis +0,44 Prozentpunkte je Runde**. 36 von 36 Kombinationen über
drei Münzen sprechen dafür.

**Der alte Einwand ist ausgeräumt.** `OFFEN.md` C1 sagte: *„Gegenauslese
ist nicht gemessen."* Jetzt ist sie es — nicht ausgeführte Aufträge zählen
als 0 %, und der Vorteil überlebt das. Zusätzlich wurde eine **strenge
Füllregel** gerechnet (der Kurs muss 0,02 % unter den eigenen Preis laufen,
dort hat also wirklich gehandelt): Der Vorteil bleibt praktisch gleich.

**Die beschlossene Einstellung: 0,10 % Abstand, 12 Kerzen gültig.**
Ausführungsquote 79–89 %, Vorteil +0,18 bis +0,20 Prozentpunkte. Die
aggressiveren Einstellungen kaufen sich mehr Vorteil damit, dass der Bot
meistens gar nicht handelt (bei 0,50 % Abstand nur 16 % Ausführung).

**Warum das der entscheidende Hebel ist:** Der Bot verliert 0,416 $ je
Handel auf ~150 $ Position, das sind **−0,28 %**. Gebührenreparatur
(+0,25 pp) und Warte-Aufträge (+0,20 pp) zusammen sind **+0,45
Prozentpunkte** — das dreht das Vorzeichen.

**Der Bauplan:**

| Schritt | |
|---|---|
| 1 | Warteschlange in `execution/engine.py`, **nur Papierpfad** |
| 2 | Prüfung bei jedem Takt: gefüllt, verfallen, oder weiter warten |
| 3 | Schalter in `data_store/config.json` |
| 4 | Test in beide Richtungen, Vorbild: `gebuehren_test.py` |

**Warum es noch nicht gebaut ist:** Ein Warte-Auftrag braucht einen
Zustandsspeicher im Handelspfad, der bei jedem Neustart und Absturz richtig
aufräumt. Das gehört an den Anfang einer Sitzung, nicht ans Ende.

**Nicht vergessen:** Epochengrenze setzen (E9), bevor es scharf geht.

---

## AUFGABE 2 — Marks Methode: NICHT ENTSCHEIDBAR, und was fehlt

Mark ist ein Bekannter von mir, der Charts mit **Elliott-Wellen und
Fibonacci** liest. Sein Vortrag liegt als `Merkvideo1.txt` (Transkript)
vor. Sein Kernsatz, wörtlich (8:04–8:15):

> *„Wenn sich mehrere Anlaufzonen kreuzen, dann wird auch die Chance
> höher, dass der dort dreht."*

**Das ist Konfluenz, und es wurde gemessen** (`konfluenz_messung.py`):

| | Konfluenz | Zufall, gleicher Abstand |
|---|---|---|
| BTC | 18,4 % | 20,6 % |
| ETH | 28,2 % | 26,9 % |
| SOL | 32,6 % | 33,0 % |

**Plus/minus zwei Punkte um die Null — kein Effekt, in keine Richtung.**

**Aber das ist KEIN Urteil über Mark.** Mein Werkzeug nimmt mechanisch das
höchste Hoch und tiefste Tief aus festen Rückblickfenstern. **Mark wählt
die Welle aus** — welche Bewegung eine Eins ist, wo die Subwelle beginnt.
Genau dieser Teil ist nicht automatisierbar, und wenn er das Entscheidende
ist, dann ist er nicht Beiwerk der Methode, sondern **die Methode**.

**Konfidenz: NICHT ENTSCHEIDBAR.**

> **Zwei Messfehler auf diesem Weg, beide selbst gefunden** — sie gehören
> als Warnung dazu:
> 1. Die erste Fassung rechnete `Hoch − Tief` im Fenster und nannte das
>    „gedreht". Das ist die **Schwankungsbreite**, nicht die Umkehr — ein
>    Kurs, der weiterfällt, hat auch 1 % Spanne.
> 2. Die Zufallslatte streute über ±4 %, die Konfluenzzonen lagen aber viel
>    näher am Kurs (727 Berührungen gegen 264). Verglichen wurde **nah
>    gegen fern**, nicht Konfluenz gegen Zufall.
>
> Beide Male sah das Ergebnis eindeutig aus und war falsch.

### Was die Frage entscheiden würde

Ich habe Fotos von Marks Charts geschickt (BTCUSD 30 min, 11.09.2026).
**Aus Bildschirmfotos lassen sich die Preise nicht genau genug ablesen.**

**Frag mich nach den Zahlen, nicht nach Bildern:** Zu jeder Zone
`Untergrenze`, `Obergrenze`, `Datum/Uhrzeit des Einzeichnens`, `Münze`,
`Zeitrahmen`. Zehn bis fünfzehn Zonen reichen. Dann kann jede einzelne
gegen die echten Kerzen geprüft werden — gegen den Zeitpunkt **vor** der
Bewegung, und gegen eine Zufallszone im selben Abstand.

**Wichtig:** Ich habe seine Zonen selbst nachgeprüft und sie wurden
getroffen. Das ist **keine Rückschau**, sondern eine Vorhersage mit
anschließender Kontrolle — und damit ein Datensatz, den man ernst nimmt.

---

## AUFGABE 3 — Die offenen Punkte aus `OFFEN.md`

**`OFFEN.md` ist die eine Liste.** Was dort nicht steht, ist nicht offen.
Ein Befund, der nur in `GEFUNDENE-PROBLEME.md` steht, taucht auf keiner
Arbeitsliste auf und wird nie angefasst — das ist am 09.09. passiert.

**Abschnitt E, meine neun Punkte vom 04.09.** (E0 erledigt):

| | |
|---|---|
| **E1** | Strukturelles Hoch im Analyse-Reiter, dunkelrot/schwarz gestreift |
| **E2** | Meine Beobachtung messen: der Kurs reagiert mit Zeitversatz |
| **E3** | Video-zu-Text-Werkzeug (ich filme Charts mit dem iPhone) |
| **E4** | Fernzugriff — **Tailscale empfohlen**, Rechner bleibt zu Hause |
| **E5** | Manuell-Reiter und Charts anpassen |
| **E6** | Das Meisterwerk-Buch: die vier Bücher abgleichen und zusammenführen |
| **E7** | Systemdurchleuchtung: was läuft noch, was wurde herausgenommen |
| **E8** | Serverfrage für nach dem 18.09. |
| **E9** | Konto/E-Mail verknüpfen — **kann Claude nicht**, mache ich selbst |

**Abschnitt C, die gemessenen Hebel** (jetzt erlaubt, Freeze ist vorbei):

- **C0a Gebühren-Doppelbuchung** — ✅ am 11.09. erledigt
- **C1 Warte-Aufträge** — siehe Aufgabe 1
- **C2 Ausstiegsschwellen** — RSI-Ausstieg bringt +0,948 % gegen +0,357 %
  beim Trailing, betrifft aber nur 14 % der Fälle
- **C23 `AppConfig.save()`** — verliert beim Speichern Einstellungen
  (Befund 97, zweiter Fall). Am 08.09. wurden **zwölf** Werte gleichzeitig
  zurückgesetzt. **Bis zur Reparatur: nach jedem Speichern in der
  Einstellungsmaske einmal `python lage_erzeugen.py`** — es warnt bei
  fehlendem `regel_modi`
- **C24 Doppelstart-Sperre** für `app.py` (Befund 93)
- **C25 Eingefrorene Kurse** bei Netzausfall (Befund 95)

---

## DIE REGELN, DIE IMMER GELTEN

**1. Alles doppelt prüfen.** Keine ausgerechnete Zahl melden, bevor sie
gegen einen **von Hand nachgerechneten Einzelfall** geprüft ist. Lieber ein
„nicht entscheidbar" als eine Zahl, die gut aussieht.

> **Ein unplausibles Ergebnis ist ein Befund über die MESSUNG, nicht über
> die Welt** — bis das Gegenteil gezeigt ist. In dieser Sitzung hat das
> dreimal gegriffen.

**2. Die Trivial-Latte immer mit ausweisen** — „gar nicht handeln" schlägt
viele Strategien. Ein Ergebnis ohne diesen Vergleich gilt als ungemessen.

**3. Vor jedem neuen Befund — beides:**

```
python schon_bekannt.py <datei.py:zeile>
python schon_bekannt.py <bezeichner>
```

und `search_session_transcripts("<stichwort>")` mit **zwei** Begriffen
(Fachwort und Alltagswort). Meldet es BEKANNT, ist es eine **Ergänzung**,
kein Fund.

**4. Ursache vor Symptom.** Kein `try/except`, kein Fallback, um einen
Fehler zu verstecken. Drei Fix-Optionen (minimal/sauber/strukturell), genau
eine Empfehlung.

**5. Bestandsschutz** — ohne meine Freigabe nicht anfassen:
- `app.py` nicht anhalten, nicht neu starten
- Die vier Cockpit-Reiter (Chartanalyse, Geldfluss, Terminal, Zyklus) sind
  Beobachtungsdeck, vom Handelspfad getrennt
- `docs/forschungsprogramm_2026-07/forschung.db` bleibt abgekoppelt
- Bewusst stillgelegt bleibt stillgelegt: Grid-Bot, `optimizer.py`,
  `futures_trader.py`, `multi_exchange.py`, TradingView-Webhook, Reddit

**6. Jede Änderung** → Abschnitt in `BOT-HANDBUCH.md` **und** Ticket in
`tickets.txt`. Gültig sind **nur fünf Stichworte**: `SPEICHERN`,
`ERLEDIGT`, `BUG`, `DOKUMENTIEREN`, `NOTIZ`. Jedes andere wird **still
verworfen und beim nächsten gültigen Ticket mitgelöscht**.

**7. Bücher immer als `.md` UND `.pdf`** (`handbuch_pdf.py`,
`zahlenbuch.py`). Nie von Hand ins PDF.

**8. Verhaltensänderungen brauchen eine Epochengrenze** in
`config_epochs.json`.

---

## WAS ICH NICHT MEHR HÖREN WILL

- **Hebel.** Auf ein System mit negativem Erwartungswert ist Hebel ein
  Beschleuniger, kein Werkzeug. Erst wenn B und F erfüllt sind.
- **Short als Lösung.** Beim London Sweep mitgemessen: −0,412 bis −0,677 %
  je Handel, also **schlechter** als Long. Der Bot hat kein
  Richtungsproblem, er hat ein Kostenproblem.
- **Neue Strategien, bevor die gemessenen Hebel gebaut sind.**

## WAS ICH BRAUCHE

Fang an mit: **Läuft alles, wird alles gesammelt?** (`sammler_pruefen.py`,
`prozess_frische.py`, und eine Wachstumsmessung — Zeilenzahl zweimal
nehmen, nicht „Prozess läuft"). Dann Aufgabe 1.
