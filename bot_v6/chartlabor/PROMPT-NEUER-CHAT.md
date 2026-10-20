# Prompt für den nächsten Chat — Chartlabor

**Angelegt 06.09.2026.** Alles ab der Linie kopieren und in den neuen Chat
einfügen. Was `CLAUDE.md`, die Dauerregeln und `PROJEKT-ENTSCHEIDUNGEN.md`
schon sagen, steht hier bewusst **nicht** drin — das lädt der Sitzungsstart-Haken
von selbst.

---

Wir arbeiten am **Chartlabor** unter
`C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\chartlabor\`.

**Was das ist:** ein Kerzenchart mit Zeichenwerkzeugen, den ich am 06.09.2026
bekommen habe, weil die Chart-Reiter im Cockpit nur 150 Kerzen zeigen und kein
Werkzeug zum Selberzeichnen haben.

**Warum es außerhalb des Bots liegt — das bitte nicht "aufräumen":**
Die Cockpit-Reiter laufen im selben Prozess wie `app.py`. Jede Änderung dort
bräuchte einen Bot-Neustart, und ein Fehler im Zeichencode könnte die
Handelsschleife mitreißen. Das Messfenster läuft bis 18.09.2026. Deshalb:
eigener Ordner, eigener Prozess, **Port 8777 — 5050 ist im Code gesperrt.**
Nach dem Messfenster soll das Ganze in den Cockpit-Reiter wandern.

**Die Dateien:**

| Datei | wofür |
|---|---|
| `chartlabor.html` | der Chart samt Zeichenwerkzeugen und Indikatoren |
| `lernpfad.html` | 8 Programmier-Lektionen an genau diesem Code |
| `chartlabor_daten.py` | holt Kerzen von Binance nach `daten/*.json` |
| `chartlabor_start.py` | kleiner lokaler Server, Port 8777 |
| `CHARTLABOR.bat` / `LERNPFAD.bat` / `KURSVERLAUF_HOLEN.bat` | zum Doppelklicken |

**Stand:** 8 Zeitraster (Monat bis Sekunde), 118.154 Kerzen, Monatschart ab
01.09.2017. Werkzeuge: Fibonacci, Trendlinie, Waagerechte, Kasten, Dreieck —
in vier Farben. Indikatoren: EMA 20/50/200, Bollinger, Elliott-Wellen mit
Regelprüfung, Volumen, RSI, MACD. Zeichnungen werden in Zeit und Preis
gespeichert und wandern deshalb in jedes Zeitraster mit.

Seit 07.09.: Liegt eine Zeichnung außerhalb des Bildausschnitts, steht ein
Schild am Bildrand — Pfeil, Werkzeug, Preis und Abstand in Prozent zum letzten
sichtbaren Schlusskurs. Zwei Knöpfe **💾 Sichern** / **📂 Laden** schreiben alles
als JSON-Datei in den Download-Ordner und holen es zurück; Laden **hängt an**
und ersetzt nie. **Füllung** in drei Stufen (keine / leicht / kräftig) für
Kasten und Dreieck, dazu die fünfte Farbe **Grau** — Grau plus kräftig graut
einen Bereich aus. **Merken 1 2 3 / Holen 1 2 3**: drei Arbeitsplätze, die
Zeitraster, Bildausschnitt, Indikatoren und Zeichnungen zusammen wegstellen
und zurückholen; sie wandern in die gesicherte Datei mit.

Das Fibonacci ist nach TradingView-Vorbild gebaut: eigene Farbe je Stufe,
getönte Bänder dazwischen, Linien bis zum rechten Rand, Beschriftung mit
Kollisionsprüfung. **`FIB_STUFEN` ist bewusst eine reine Zahlenliste**, die
Farben stehen getrennt in `FIB_FARBEN` mit Rückfallwert — sonst wären
Lektion 1 und 3 im Lernpfad falsch. Bitte nicht zu Wertepaaren umbauen.

**Am 07.09.2026 gebaut — beides fertig, bitte nicht noch einmal bauen:**

1. **Randhinweis für Zeichnungen außerhalb des Bildausschnitts.** Anlass war
   die Waagerechte bei 75.000 $, die im Sekundenchart unsichtbar ist, weil
   dort nur 79.611 bis 79.631 $ im Bild stehen. Drei Punkte daran sind
   Entscheidungen, keine Zufälle: Die Sichtbarkeitsprüfung benutzt **dieselben**
   Umrechner (`xVonZeit`, `yVonPreis`) wie das Malen — eine zweite Rechnung
   wäre eine zweite Wahrheit. Der Prozentwert bezieht sich auf den Schlusskurs
   der letzten **sichtbaren** Kerze, nicht auf die letzte überhaupt. Und bei
   Fibonacci zählt der Bereich **aller neun Stufen**, nicht nur der zwei Anker.

2. **Sichern und Laden.** Geschrieben wird im Browser, **nicht** im Server —
   `chartlabor_start.py` schreibt weiterhin nichts. Einlesen **hängt an** und
   ersetzt nie, Doppelte werden erkannt; aufräumen macht nur „Zeichnung
   löschen". Geprüft wird der **Inhalt** jedes Eintrags, nicht seine
   Anwesenheit — ein Eintrag mit der Art `kasten` statt `rechteck` würde sonst
   klaglos gespeichert und nie gemalt. Die gültigen Arten kommen aus `WERKZEUG`
   selbst, damit ein eigenes Werkzeug aus Lektion 8 sofort mitgesichert wird.

**Ebenfalls am 07.09. gebaut:**

3. **Füllung und Ausgrauen** für Kasten und Dreieck, drei Stufen, plus die
   Farbe Grau. Der mittlere Wert ist bewusst `0.13` — der, der vorher fest im
   Code stand. Alte Zeichnungen ohne Eintrag fallen darauf zurück und sehen
   aus wie immer. **Lektion 2 im Lernpfad zeigt die Farbtabelle wörtlich** und
   wurde mitgezogen; wer `FARBEN` ändert, muss dort nachsehen.

4. **Drei Arbeitsplätze** (`Merken` / `Holen`). Bewusst zwei Gruppen statt
   eines Knopfes mit Nachfrage. Nach dem Speichern wird **zurückgelesen und
   verglichen** — „hat nicht gemeckert" ist keine Bestätigung. `Holen` ist die
   einzige Stelle, an der Laden etwas zerstören kann, und fragt deshalb nach.

**Nebenbei behoben:** Der Chartbereich rechnete mit `calc(100vh - 42px)`, also
einer festen Annahme über die Höhe der Bedienleiste. Gemessen waren es 71 px —
die Zeitachse lag 29 px außerhalb des Fensters und war unsichtbar. Jetzt teilt
sich der Platz von selbst auf (flex). Dazu prüft `zeichne()` bei **jedem**
Bildaufbau, ob Leinwand und Bühne noch dieselbe Größe haben, und korrigiert
sonst — der `ResizeObserver` ist zusätzlich da, war aber **nicht prüfbar**: im
Prüfbrowser ruht die Bildschleife, über die seine Rückrufe kommen. Eine
Zusicherung, die man nicht prüfen kann, ist keine.

**Am 07.09.2026 in der zweiten Runde dazugekommen:**

5. **Zeichnungsliste** (Knopf „Zeichnungen"). Jede Zeichnung einzeln aus- und
   einblenden, nachträglich Farbe und Füllung ändern, löschen. **Ausblenden ist
   nicht Löschen.** Ein Klick in den Chart wählt die Zeichnung darunter aus —
   dafür prüft der Code jetzt die Form (Kasten von innen, Linie nach Abstand),
   vorher traf man einen Kasten nur an seinen zwei Ecken.
6. **Werkzeug „Fib + Zonen"** — zieht zusätzlich die Rückzugszone (61,8–78,6 %)
   und die Zielzone (127,2–161,8 %) als grünes bzw. rotes Feld. Grün ist, wo
   gekauft wird; bei einem Fibonacci von oben nach unten dreht sich das um.
   Wie bei Elliott ausdrücklich als **Gewohnheit, nicht Messung** gekennzeichnet.
7. **Volle Historie**: 4h, 1h und 15m gehen bis 17.08.2017 zurück (15m = 317.075
   Kerzen), 1m auf 180 Tage. Weiter geht bei 1m/1s nicht — die volle Historie
   wären dort 4,76 Mio bzw. 285 Mio Kerzen.
8. **Einzeldatei** `Desktop\CHARTLABOR.py` (+ `.bat`, weil `.py` auf diesem
   Rechner mit nichts verknüpft ist). **Sie wird erzeugt, nicht gepflegt:**
   nach jeder Änderung an `chartlabor.html` `python chartlabor_py_bauen.py`
   laufen lassen. Sie merkt selbst, wenn sie veraltet ist, und zeigt dann die
   Vorlage statt ihrer eigenen Kopie.

**Zwei Fallen, die erst die volle Historie ausgelöst hätte** — beide gemessen,
bevor sie zuschlagen konnten: `Math.min(...liste)` bricht ab 147.578 Werten mit
„Maximum call stack size exceeded" ab (der 15m-Chart hat 317.075 — „Alles
zeigen" wäre ein sicherer Absturz gewesen), und die Indikatoren wurden bei
jedem Bild neu über den ganzen Bestand gerechnet: 190 ms je Bild. Jetzt 2,9 ms.

**Am 08.09.2026 dazugekommen:**

9. **Gold und Silber.** Zweite Quelle: Yahoo Finance (`GC=F` / `SI=F`) — das sind
   die **COMEX-Terminkontrakte**, nicht der Kassapreis; gegen den Binance-Token
   PAXG weichen sie um −1,3 bis +0,7 % ab. Tageskerzen ab **10.09.2001**, also
   weiter zurück als Bitcoin. 4-Stunden-Kerzen baut Yahoo nicht an, sie werden
   aus den Stundenkerzen zusammengefasst (gegen die Quelle nachgerechnet).
   `daten/uebersicht.json` sagt dem Chart, welche Märkte und Zeitraster es
   wirklich gibt — Gold hat keine Sekundenkerzen, der Knopf ist dort gesperrt.
   **Achtung bei Yahoo:** `range=max` liefert klaglos Monatskerzen auf eine
   Anfrage nach Tageskerzen. Der Holer misst deshalb den Abstand der gelieferten
   Punkte und bricht ab, statt der Beschriftung zu glauben.
10. **Fassung zum Weitergeben** (`chartlabor_teilen_bauen.py`) — zwei Abzüge mit
    eingebauten Kursen: einer für den Artifact-Link, einer zum Verschicken und
    Doppelklicken. Monat bis 1 Std für alle drei Märkte, 7,4 MB. Ohne Server,
    ohne Python. Die Verschickfassung macht **null Netzabrufe** — das ist der
    Beweis, dass sie allein läuft. Im Artifact sind Downloads gesperrt, deshalb
    geht „Sichern" dort über die Speicher-Fähigkeit der Plattform.

**Drei Abzüge, eine Quelle.** Nach jeder Änderung an `chartlabor.html`:
```
python chartlabor_py_bauen.py        # Desktop-Einzeldatei
python chartlabor_teilen_bauen.py    # Link- und Verschickfassung
```

**Am 21.09.2026 nachgebessert (Yahoo-Anbindung):**

11. **Zehn saubere Jahre statt zwanzig mit Löchern.** Gold und Silber kommen bei
    Tag und Woche jetzt über `10y` statt `25y`. Grund gemessen: in den alten
    Jahrgängen lagen **440 unstimmige Kerzen** in `GOLD_1d` (Schluss über dem
    Hoch), alle zwischen 2003 und 2011. Derselbe Tag kam auf zwei Rechnern mit
    verschiedenen Werten zurück — die alten Jahre haben nicht nur Löcher, sie
    wackeln. Beim **Monat** bleibt `max`, weil es dort keine andere Spanne gibt;
    die 4 bzw. 2 kaputten Balken werden einzeln weggelassen und gezählt
    (`[4 kaputte weggelassen]`, und als `verworfen` in `uebersicht.json`).
    **Nie zurechtbiegen** — eine fehlende Kerze sieht man, eine erfundene nicht.
12. **Ein Tor vor jedem Schreiben**, auch für Binance: stimmt der gemessene
    Abstand nicht zum Raster, das der Dateiname behaupten wird, wird nicht
    geschrieben. Eine alte richtige Datei ist besser als eine neue falsche.
13. **`python chartlabor_daten.py --pruefen`** — sieht den ganzen Datenordner
    durch, meldet Raster und kaputte Kerzen je Datei, Rückgabe 1 bei
    Beanstandung.
14. **4-Stunden-Zusammenfassung für Gold/Silber zurückgenommen.** Sie rechnete
    richtig, aber eine zusammengerechnete Kerze sieht im Chart aus wie eine
    gelieferte. Der 4h-Knopf ist dort jetzt grau; die zwei Dateien liegen in
    `daten/nicht_mehr_verwendet/`.

**Was als Nächstes offen ist:** nichts Bestimmtes. Nach dem Messfenster
(18.09.2026) soll das Chartlabor in den Cockpit-Reiter wandern.

**Bekannt und bewusst offen, bitte nicht als neuen Fund melden:**

- `features/chart_data.py:87-90` — der Lader des Bots holt bei vorhandenem
  Cache nur vorwärts, nie rückwärts, und kann deshalb keine tiefere Historie
  nachladen. Belegt: 15 Zeilen im Cache, Anfrage über 4000 Tage lieferte 37
  Kerzen. Das Chartlabor umgeht es mit eigenem Lader. Fix erst nach dem 18.09.
- `V4_START.bat` — die Doppelstart-Sperre findet sich selbst und meldet immer
  "läuft bereits". Ich starte V4 direkt über
  `v4_referenz\trading_imperium_v4_25_ALARM.py`. Fix steht aus.
- `trend_exit` steht **absichtlich** auf SHADOW. Der stündliche Wächter-Alarm
  ist ein Falschalarm, die Daten werden nebenher gesammelt und nach dem
  Messfenster ausgewertet.
- Der Sekundenchart zeigt bei Elliott oft "zu wenig Bewegung". Das ist richtig
  so — in 180 Sekunden bewegt sich Bitcoin um rund 0,03 %.

**Wie ich arbeite:** Gebaut wird erst, wenn geprüft ist. Kein "müsste passen".
Jede Zahl gegen einen von Hand nachgerechneten Fall. Prüfwerkzeuge in beide
Richtungen testen — meldet es nichts Falsches, **und** findet es den echten
Fall? Am 06.09. hat genau das zwei Fehler gefunden, die keine Fehlermeldung
erzeugt haben.
