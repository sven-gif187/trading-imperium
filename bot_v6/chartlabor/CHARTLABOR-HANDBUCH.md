# Chartlabor — Handbuch

**Angelegt 22.09.2026.** Das Nachschlagewerk für das Chartlabor. Für den Bot
gibt es `BOT-HANDBUCH.md` eine Ebene höher — das hier hat damit nichts zu tun.

> **Wo liegt das alles?**
> `C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\chartlabor\`
>
> Auf dem Desktop liegen drei Projektordner. Das Chartlabor gibt es **nur in
> `trading_imperium_v6(21)`** — nicht in `_v7`, nicht in `_LIVE`.

---

## 1. Was das Chartlabor ist

Ein Kerzenchart mit Zeichenwerkzeugen, gebaut am 06.09.2026, weil die
Chart-Reiter im Cockpit nur 150 Kerzen zeigen und nichts zum Selberzeichnen
haben.

**Es läuft außerhalb des Bots, und das ist Absicht.** Die Cockpit-Reiter laufen
im selben Prozess wie `app.py`. Eine Änderung dort bräuchte einen Bot-Neustart,
und ein Fehler im Zeichencode könnte die Handelsschleife mitreißen. Deshalb:
eigener Ordner, eigener Prozess, **Port 8777 — 5050 ist im Code gesperrt**,
weil dort der Bot sitzt.

---

## 2. Wie man es startet — drei Wege

| Weg | Was passiert | Wann |
|---|---|---|
| **`CHARTLABOR.bat` auf dem Desktop** | startet `CHARTLABOR.py`, die Einzeldatei | der übliche Weg |
| **`CHARTLABOR.bat` im Ordner** | startet `chartlabor_start.py` | wenn man ohnehin im Ordner ist |
| **Der Link** | die Fassung im Netz, für andere | zum Weitergeben |

Alle drei landen auf **`http://127.0.0.1:8777`** und zeigen dasselbe. Läuft
schon eines, wird **kein zweites** gestartet — nur der Browser hingeschickt.

> **Warum das wichtig ist:** Die Zeichnungen liegen im Browser-Speicher, und
> der hängt an der **Adresse**. Zwei Server auf zwei Ports wären zwei getrennte
> Zeichnungssätze — man malt in das eine Fenster und sucht es im anderen.

**Den Lernpfad** startet `LERNPFAD.bat` (8 Programmier-Lektionen an genau
diesem Code).

---

## 3. Welche Datei was ist — und welche nur eine Kopie

Das ist die wichtigste Seite in diesem Handbuch. **Es gibt eine Quelle und
drei Abzüge.** Wer in einem Abzug etwas ändert, verliert es beim nächsten Bau.

```
chartlabor.html          <-- DIE QUELLE. Hier wird geändert.
   |
   +-- CHARTLABOR.py                        (Desktop, Einzeldatei)
   +-- teilen/chartlabor_geteilt.html       (der Link)
   +-- teilen/CHARTLABOR_ZUM_VERSCHICKEN.html  (zum Mailen)
```

**Nach jeder Änderung an `chartlabor.html` oder `lernpfad.html`:**

```
python chartlabor_py_bauen.py        (baut CHARTLABOR.py neu)
python chartlabor_teilen_bauen.py    (baut die beiden Teilfassungen neu)
```

`CHARTLABOR.py` merkt es **selbst**, wenn sie veraltet ist: sie vergleicht bei
jedem Abruf ihre Prüfsumme mit der Vorlage und zeigt dann **die Vorlage** statt
ihrer eigenen alten Kopie. Ein **F5** im Browser genügt also, um eine Änderung
zu sehen — das Fenster muss nicht neu gestartet werden.

> *Bis zum 22.09.2026 galt das nur beim **Starten**.* Wer die Vorlage änderte,
> während das Fenster lief, bekam weiter die alte Seite, ohne jeden Hinweis.

> **Die beiden Teilfassungen merken das nicht.** Sie zeigen den Stand, an dem
> sie gebaut wurden, bis jemand sie neu baut und neu veröffentlicht.

### Alle Dateien

| Datei | wofür |
|---|---|
| `chartlabor.html` | **die Quelle** — Chart, Werkzeuge, Indikatoren |
| `lernpfad.html` | 8 Programmier-Lektionen an diesem Code |
| `chartlabor_daten.py` | holt die Kurse nach `daten/` |
| `chartlabor_start.py` | der kleine Server, Port 8777 |
| `chartlabor_py_bauen.py` | baut die Desktop-Einzeldatei |
| `chartlabor_teilen_bauen.py` | baut die zwei Fassungen zum Weitergeben |
| `CHARTLABOR.bat` / `LERNPFAD.bat` / `KURSVERLAUF_HOLEN.bat` | zum Doppelklicken |
| `daten\` | die Kursdateien (JSON) + `uebersicht.json` |
| `teilen\` | die zwei Fassungen zum Weitergeben |
| `PROMPT-NEUER-CHAT.md` | Startpunkt für einen neuen Chat mit Claude |

---

## 4. Die Kurse — woher sie kommen und wie alt sie sind

### Was drin ist

| Markt | Quelle | Zeitraster | ab wann |
|---|---|---|---|
| **BTC/USDT** | Binance | alle 8 | 17.08.2017 (Tag) |
| **Gold (COMEX)** | Yahoo `GC=F` | 6 — **kein 4 Std, kein 1 Sek** | 01.09.2000 (Monat) |
| **Silber (COMEX)** | Yahoo `SI=F` | 6 — **kein 4 Std, kein 1 Sek** | 01.09.2000 (Monat) |

> **Gold und Silber sind Terminkontrakte (Futures), nicht der Kassapreis.**
> Gegen den Binance-Goldtoken PAXG gemessen: −1,3 bis +0,7 % Unterschied. Kein
> Fehler, sondern zwei verschiedene Dinge.

Die grauen Knöpfe bei Gold und Silber sind **kein Fehler**: Yahoo liefert für
diese Raster nichts, und zusammengerechnet wird nichts — eine aus Stundenkerzen
gebaute 4-Stunden-Kerze sieht im Chart aus wie eine echte.

### Kurse nachholen

**`KURSVERLAUF_HOLEN.bat` doppelklicken** — das holt BTC. Für die Metalle:

```
python chartlabor_daten.py GOLD
python chartlabor_daten.py SILBER
```

**Das läuft nicht von selbst.** Wer eine Woche nicht holt, sieht eine Woche
alte Kurse.

### Der Warnstreifen

Ist die letzte Kerze zu alt, erscheint über dem Chart ein gelber Streifen:

> ⚠ Diese Kurse sind 16 Tage alt. Letzte Kerze: 6.9.2026 · BTC/USDT Tag.
> Zum Nachholen: KURSVERLAUF_HOLEN.bat im Chartlabor-Ordner doppelklicken.

*Warum es ihn gibt:* Am 22.09.2026 zeigte der Chart 79.630 $, während die Börse
bei 85.956 $ stand. Die Zahlen waren nicht falsch — sie waren **16 Tage alt**,
und nichts hat es gesagt. Alte Kurse sehen aus wie neue.

Die Schwelle: fünf Zeitraster Spielraum, mindestens drei Minuten, plus vier Tage
Marktpause bei Gold und Silber (Börsenwochenende).

### Den Datenordner prüfen

```
python chartlabor_daten.py --pruefen
```

Sieht jede Datei durch: steckt das Zeitraster drin, das der Dateiname behauptet,
und sind die Kerzen heil? Rückgabe 1, wenn etwas beanstandet wird.

---

## 5. Die Bedienung

### Maus

| | |
|---|---|
| **Rad** | zoomen |
| **Ziehen** (Werkzeug „Zeiger") | verschieben |
| **Ziehen** (Werkzeug gewählt) | einzeichnen |
| **Klick auf eine Zeichnung** | auswählen, Stellräder aufklappen |
| **Doppelklick auf eine Zeichnung** | löschen |
| **Esc** | zurück zum Zeiger |
| **Strg + Z** | letzte Zeichnung zurück |

### Zeichenwerkzeuge

| Werkzeug | was es tut |
|---|---|
| **Trendlinie** | Linie zwischen zwei Punkten |
| **Waagerechte** | waagerechte Linie über die ganze Breite, mit Preisschild |
| **Kasten** | Rechteck, zeigt seine Spanne in Prozent |
| **Dreieck** | Dreieck |
| **Fibonacci** | 9 Stufen von 0 bis 161,8 %, jede in eigener Farbe, mit getönten Bändern |
| **Fib + Zonen** | wie oben, **plus** Kaufzone (61,8–78,6 %) grün und Verkaufszone (127,2–161,8 %) rot |

**Farben:** Grün, Rot, Violett, Gelb, Grau.
**Füllung:** keine · leicht · kräftig · voll — für Kasten und Dreieck.
Grau + voll ergibt einen ausgegrauten Bereich, durch den die Kerzen scheinen.

Die Werte gelten für die **nächste** Zeichnung. Bestehende ändert man über die
Zeichnungsliste oder mit einem Klick in den Chart.

### 📋 Zeichnungen (die Liste)

Jede Zeichnung eine Zeile: Auge zum Aus- und Einblenden, Farbe, Beschreibung.
Klick auf die Zeile klappt die Stellräder auf — Farbe, Füllung, löschen.
Dazu „alle zeigen" / „alle aus".

**Ausblenden ist nicht Löschen.** Die Zeichnung bleibt blass in der Liste und
kommt mit einem Klick zurück. Dafür gebaut, dass sich mehrere Fibonaccis nicht
gegenseitig die Sicht nehmen.

### Die Preisachse einstellen

Standardmäßig richtet sich die Preisachse nach den **Kerzen**. Eine
Fibonacci-Zielzone liegt aber immer über dem Hoch — und fiel deshalb früher aus
dem Bild.

| | |
|---|---|
| **Auf der Preisachse ziehen** | nach unten staucht (mehr Preis ins Bild), nach oben dehnt |
| **Rad über der Preisachse** | dasselbe in kleineren Schritten |
| **Doppelklick auf die Preisachse** | zurück auf automatisch |
| **⤢ Einpassen** | stellt die Achse so ein, dass Kerzen **und** sichtbare Zeichnungen hineinpassen |
| **Schalter `Auto`/`Fest`** (unten rechts) | zeigt, ob die Achse von Hand steht — Klick stellt zurück |
| **Schalter `Lin`/`Log`** (unten rechts) | lineare oder logarithmische Achse |

Beim Wechsel von Münze oder Zeitraster geht die Achse wieder auf automatisch —
eine feste Spanne von Bitcoin wäre bei Silber (66 statt 86.000) eine Falle.

### Log-Achse — wann sie sich lohnt

Der ganze BTC-Verlauf geht von 2.817 auf 126.200 $, also das **45-fache**. Auf
einer linearen Achse liegen die Jahre 2017–2020 in den untersten zwei Prozent
der Höhe. Auf der **Log-Achse** nimmt die gleiche *prozentuale* Bewegung überall
gleich viel Platz ein — eine Verdopplung sieht 2017 genauso aus wie 2026
(nachgemessen: 58,9 Bildpunkte, unten wie oben).

Die Gitterlinien stehen dort auf runden Werten je Zehnerschritt (3.000, 5.000,
10.000, 20.000 …), nicht auf gleichen Abständen.

### Randhinweis

Liegt eine Zeichnung außerhalb des Bildausschnitts, erscheint am Bildrand ein
kleines Schild mit Pfeil, Preis und Abstand in Prozent:

> ▼ Waagerechte 75.000 · −5,27 %

Der Prozentwert ist der Abstand zum **letzten sichtbaren Schlusskurs**.

### Zeichnungen aufheben

| Knopf | was passiert |
|---|---|
| **Merken 1 2 3** | speichert den ganzen Stand: Münze, Zeitraster, Bildausschnitt, Indikatoren, alle Zeichnungen |
| **Holen 1 2 3** | holt ihn zurück; fragt nach, solange Zeichnungen da sind |
| **💾 Sichern** | alles als Datei in den Download-Ordner |
| **📂 Laden** | Datei einlesen — **hängt an, löscht nie** |

Zeichnungen werden in **Zeit und Preis** gespeichert, nicht in Bildpunkten.
Deshalb steht eine Trendlinie aus dem Tageschart auch im Stundenchart an
derselben Stelle. Gespeichert wird **je Münze**, nicht je Zeitraster.

> **Sie liegen im Browser-Speicher.** Anderer Browser oder gelöschte
> Websitedaten, und sie sind weg. Wer sie behalten will, drückt **💾 Sichern**.

### Indikatoren

| | |
|---|---|
| **EMA 20 / 50 / 200** | gleitende Durchschnitte |
| **Bollinger** | Band um den Durchschnitt |
| **Volumen / RSI / MACD** | eigene Felder unter dem Chart |
| **Elliott-Wellen** | Wellenzählung mit Prüfung der drei harten Regeln |

> **Elliott ist eine Deutung, keine Messung.** Zwei Fachleute zählen denselben
> Chart oft verschieden, und die Zählung ändert sich rückwirkend, wenn neue
> Kerzen dazukommen. Der Kasten rechts oben weist deshalb jede der drei Regeln
> einzeln aus. Im Sekundenchart steht oft „zu wenig Bewegung" — das ist richtig
> so, in 180 Sekunden bewegt sich Bitcoin um rund 0,03 %.

---

## 6. Wenn etwas nicht stimmt

| Was du siehst | Was es bedeutet |
|---|---|
| **Kurse viel zu niedrig/hoch** | alte Daten — der gelbe Streifen sagt es. `KURSVERLAUF_HOLEN.bat` |
| **Gelber Streifen bleibt nach dem Holen** | Seite mit **F5** neu laden |
| **Änderung an der Seite wirkt nicht** | F5. Hilft das nicht: `python chartlabor_py_bauen.py`, dann F5 |
| **„Kerzen nicht gefunden"** | Die Datei fehlt. `python chartlabor_daten.py --pruefen` |
| **Grauer Zeitraster-Knopf** | Gibt es für diese Münze nicht (Gold hat kein 4 Std, kein 1 Sek) |
| **Chart bleibt leer** | Läuft der Server? Fenster offen lassen — es hält ihn |
| **Chart lädt ewig, nichts kommt** | Das Serverfenster schließen und `CHARTLABOR.bat` neu doppelklicken. Trat bis zum 22.09.2026 auf, wenn sich mehrere Verbindungen stauten — seitdem behoben |
| **Zeichnungen weg** | Anderer Browser oder gelöschte Websitedaten. Aus der Sicherungsdatei laden |

---

## 7. Entscheidungen — was bewusst so ist

Diese Punkte sind **keine Fehler**. Wer sie ändern will, holt vorher eine
Freigabe.

| | Warum |
|---|---|
| **Port 8777, nie 5050** | Auf 5050 sitzt der Bot. Zwei Programme auf einem Port haben am 03.09.2026 fünf Stunden lang zwei getrennte Datenbestände erzeugt |
| **Außerhalb des Bots** | Ein Fehler im Zeichencode darf die Handelsschleife nicht mitreißen |
| **Kein zweiter Server** | Zwei Adressen wären zwei getrennte Zeichnungssätze |
| **`FIB_STUFEN` ist eine reine Zahlenliste** | Die Farben stehen getrennt in `FIB_FARBEN` mit Rückfallwert. Sonst wären Lektion 1 und 3 im Lernpfad falsch. **Nicht zu Wertepaaren umbauen** |
| **Ohne fremde Chart-Bibliothek** | Kerzen und Zeichnungen müssen zwingend dieselben Koordinaten benutzen, sonst laufen sie beim Zoomen auseinander |
| **Gold/Silber ohne 4 Std** | Yahoo liefert das nicht, und zusammengerechnet wird nichts |
| **Tag und Woche nur 10 Jahre** | Die Jahre davor haben unstimmige Balken (440 in Gold Tag) — zehn saubere Jahre statt zwanzig mit Löchern |
| **Der Server schreibt nichts** | Er liefert nur aus. Sichern läuft über den Browser |
| **Eigener Kurs-Lader** | Der Lader des Bots (`features/chart_data.py:87-90`) kann bei vorhandenem Zwischenspeicher keine tiefere Historie nachholen |

---

## 8. Die Fassung zum Weitergeben

Zwei Dateien in `teilen\`, beide 7,4 MB, beide mit den Kursen **in der Seite**:

| Datei | wofür |
|---|---|
| `chartlabor_geteilt.html` | wird als Link veröffentlicht |
| `CHARTLABOR_ZUM_VERSCHICKEN.html` | mailen, doppelklicken, fertig — **ohne Anmeldung** |

Der Link: `https://claude.ai/artifact/XwgK97vTLmny5dgmafbj8W`
(muss über das Teilen-Menü der Seite erst freigegeben werden).

Enthalten: **Monat, Woche, Tag, 4 Std, 1 Std** für alle drei Märkte. Nicht
enthalten: 15 Min, 1 Min, 1 Sek — allein bei BTC wären das 620.000 Kerzen und
48 MB. Es ist eine **Momentaufnahme**; neue Kurse kommen dort nicht nach.

---

## 9. Wo die Geschichte steht

| Wo | Was |
|---|---|
| **Dieses Handbuch** | wie man es benutzt |
| `PROMPT-NEUER-CHAT.md` | Startpunkt für einen neuen Chat mit Claude |
| `ENTWICKLERHANDBUCH.md` (eine Ebene höher) | die Chronik — jede Änderung mit Datum, Begründung und Messung |
| Die Kommentare im Code selbst | warum eine Stelle so ist, wie sie ist |

Die Chronik ist über 1 MB groß. Gezielt suchen:

```
python schon_bekannt.py <stichwort>
```
