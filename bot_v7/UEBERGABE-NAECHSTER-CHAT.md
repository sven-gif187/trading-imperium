> **ÜBERHOLT — nicht mehr als Aufgabenliste benutzen.**
> Diese Datei ist eine **Momentaufnahme** vom Zeitpunkt ihres Schreibens.
> Am selben Tag wurde danach weitergearbeitet; einzelne Punkte darin
> waren schon erledigt, als sie hier hineingeschrieben wurden.
> **Die einzige gültige Liste ist `OFFEN.md`** (`python offen.py`).
> Wer von hier abschreibt, ohne gegen die Commits zu prüfen, trägt
> erledigte Punkte weiter — genau das ist am 18.08.2026 passiert.

# Übergabe an das nächste Chatfenster

**Geschrieben 17.08.2026, 11:05 UTC.** Der bisherige Chat läuft voll.
Bot und Sammler laufen durch, es muss nichts gestartet werden.

> **Diese Datei ist die neueste.** Sie ersetzt
> `UEBERGABE-MONTAG-17-08.md` und `NAECHSTE-SESSION.md` — beide sind
> älter. Bei Widersprüchen gilt diese hier.

---

## ⛔ Der Freeze läuft weiter — bis etwa 27.08.2026

**Am Handelspfad wird nichts geändert.** Nicht Entry, nicht Exit, nicht
Stop, nicht DCA, nicht Score, keine Schwelle, keine Ordertyp-Umstellung.

**Erlaubt:** Anzeige, Berichte, Auswertung, Dokumentation, Aufräumen.

**Zwei Epochen laufen:**

| Epoche | ab (UTC) | was |
|---|---|---|
| `E6_messfenster` | 13.08. 13:21 | Beginn des Messfensters |
| `E7_filter_schaerfer` | 15.08. 07:47 | `min_confirmations` 3 → 2, **vom Bot selbst geändert** |

**Der lernende Wächter ist pausiert** (`features/regime_adaptiv.py`,
`AKTIV = False`). Er misst und protokolliert weiter, verstellt aber
nichts mehr. **Nach dem 27.08. wieder auf `True`.**

---

## Drei Daueraufgaben — ohne Nachfrage

1. **Erklärstil:** Alltagssprache zuerst, Fachbegriff in Klammern daneben
2. **`BOT-HANDBUCH.md`** zu jeder Änderung fortführen — *„das ist unser
   Geschichtsbuch"*
3. **Tickets** selbständig in `tickets.txt`

**Und seit dem 17.08. eine vierte, ausdrücklich gefordert:**

4. **Alles doppelt prüfen.** Nicht zählen, wie viele Werte entstanden
   sind — die **Werte selbst ansehen**. An einem Tag sind mir vier
   Fehler unterlaufen, die alle gleich aussahen: eine Erfolgsmeldung,
   die keine war.

---

## Erster Handgriff

```bash
python lage_erzeugen.py
python schatten_universum.py --status
python nachlauf.py --status
```

| Prüfung | Erwartung |
|---|---|
| Bot | läuft, `system.log` wenige Minuten alt |
| Schatten-Universum | **genau EIN** Prozess, jetzt **18 Münzen** |
| Forschungs-Capture | läuft, jetzt **18 Symbole** |
| Regel-Schalter | `trend_exit=SHADOW` |
| `ZAHLENBUCH.pdf` | von heute, Tageskopien in `zahlenbuecher/` |

**Kam „REGEL-SCHALTER VERSTELLT":** sofort melden, das ist ein
Freeze-Bruch.

---

## Stand des Messfensters

| | |
|---|---|
| Trades seit `E6`-Start | **3** |
| letzter | 17.08. 08:20 ETH Breakeven-Sperre **+0,31 %** |
| davor | 16.08. 21:40 SOL Stop-Loss **−2,16 %** |
| Nachlauf | 1.394 Ereignisse, 608 mit 24-h-Kurs |
| Schatten-Universum | 466 Signale |

**Erwartung ehrlich:** Bei diesem Tempo liefert das Fenster **unter 10
Trades**. Für eine belastbare Aussage bräuchte es 30–40 (Handbuch 4.44).
Das ist kein Defekt — der Bot handelt bewusst nicht, und das ist
gemessen richtig (4.30).

---

## Was jetzt zu tun ist

### Sofort — nichts

Es gibt keine offene Baustelle. Alles vom 17.08. ist committet
(`71c198f`), dokumentiert und geprüft.

### Wenn Sven Bilder schickt

| Person | Datei |
|---|---|
| **Tilo** | `prognosen/TILO.md` |
| **Mark** | `prognosen/MARK.md` |

**Die vier Pflichtangaben abfragen** — Richtung, Kursziel, Frist, und
vor allem **„ungültig ab"**. Anleitung: Handbuch **4.46**.

**Offen bei Mark:** Sein Bild vom 17.08. (BTC 4-Stunden-Chart, Ist-Kurs
63.637,05 $) enthält **keine** Prognose — Richtung, Ziel und Frist
fehlen. Nachfragen.

**Offen bei Tilo:** XRP-Ruf auf 0,30 $ bis Jahresende läuft. Stand
17.08.: **1,0020 $**, nötig wären −70 %.

### Freeze-sicher, wenn Zeit ist

| Was | Warum |
|---|---|
| Log-Farben im laufenden Programm ansehen | Nur am Testfall geprüft, nie im echten Fenster |
| `feature_snapshots` auswerten | 38 Indikatorspalten liegen da, aber niemand hat je gefragt, **welche Werte zu Gewinnen führten** |
| Zahlenbuch strukturieren | Sven wünscht es „leserlicher, wie die Chartbilder" |

### ⚠️ Am 17.08. spät gefunden — gehört ganz nach oben

**Die Breakeven-Sperre garantiert Verlust.** Sie stellt bei **+0,35 %**
glatt, eine Runde kostet aber **0,505 %**. Alle zehn bisherigen
Auslösungen sahen im Prozentwert nach Gewinn aus (Median **+0,23 %**) und
waren in echtem Geld Verlust (Median **−0,22 $**, Summe **−3,20 $**).

**Wichtig für die Einordnung:** Der Wert war **Absicht** und selbst schon
ein Fix vom 10.08. — nur beruht seine Rechnung auf **0,10 % Gebühr je
Seite**. Seit dem Messfenster gilt 0,25 %. **Eine Folgelücke der
Gebührenkorrektur, kein Konstruktionsfehler.**

Die Gegenprobe stand bereits im Code (`risk/exit_rules.py:105`) und ist
**jetzt fällig — sie fällt durch**:

| | Fälle | Durchschnitt |
|---|---|---|
| vor dem Fix (0,25 %) | 6 | −0,138 $ |
| nach dem Fix (0,35 %) | 4 | **−0,594 $** |

**Zweite Folgelücke:** `risk/exit_rules_schatten.py:104` rechnet mit
`KOSTEN_PCT = 0.32` statt 0,505 — die Schatten-Ratsche wird dadurch um
**0,185 Prozentpunkte zu günstig** bewertet. Gefährlicher als der erste
Fall: Die Regel verliert Geld, das man sieht; die Messung erzeugt
Zuversicht, die niemand prüft.

**Suchauftrag daraus:** Nach weiteren Stellen suchen, die auf der alten
Kostenannahme beruhen (`0.32`, `0.10 % Gebühr`, alte Slippage-Werte).
Dritter Treffer schon bekannt: `chartanalyse_backtest.py:42` mit 0,50.

### Nach dem 27.08. — in dieser Reihenfolge

0. **Breakeven-Puffer und die beiden Kostenkonstanten** — siehe oben.
   Kleiner Aufwand, sofort wirksam, und die Gegenprobe liegt schon vor.
1. **Warte-Aufträge im Schattenlauf** — der mit Abstand größte Hebel.
   Gemessen: **+0,23 Prozentpunkte je Runde**, Kosten von 0,505 % auf
   ~0,27 %. Damit dreht das Vorzeichen von −0,065 % auf **+0,17 %**.
   **Offener Einwand:** Gegenauslese (*adverse selection*) — Warte-Aufträge
   werden bevorzugt gefüllt, wenn der Kurs gegen einen läuft. Das ist
   nicht gemessen.
2. **Ausstiegsschwellen** — die Ratsche greift bei 0,8 %, die
   Rentabilitätsschwelle liegt bei ~0,84 %. Sie realisiert systematisch
   zu früh.
3. **`schwelle_vergleich.py` erneut laufen lassen** — hatte der lernende
   Wächter recht? Heute: nicht entscheidbar, nur 5 unabhängige Fenster
   bei 48 h. Mit doppelter Datenlage neu fragen.
4. **Münzfrage neu stellen** — SUI, OP, APT, ARB, INJ, RENDER sammeln
   seit dem 17.08. Erst nach mehreren Tagen vergleichbar.
5. `regime_adaptiv.py` auf `AKTIV = True`.

---

## Die drei Zahlen, die alles erklären

**1. Kapital hilft nicht.** Die Gebühr ist ein Prozentsatz und wächst
exakt mit:

| Einsatz | Netto je Runde |
|---|---|
| 100 $ | −0,07 $ |
| 10.000 $ | −6,50 $ |
| 100.000 $ | −65,00 $ |

**2. Überall dieselbe Krankheit** — hohe Trefferquote, negativer
Erwartungswert:

| | Trefferquote | nach Kosten |
|---|---|---|
| Trailing-Stop | 100 % im Plus | −0,065 % |
| SUPPORT_BOUNCE | 68,9 % | −0,586 % |
| RETEST | 69,2 % | −0,372 % |
| BREAKOUT | 67,5 % | −0,466 % |

**3. Überlappende Fenster** — dreimal an einem Tag aufgetreten:

| Auswertung | scheinbare Fälle | echte Fenster |
|---|---|---|
| Schwellen-Vergleich 48 h | 27.041 | **5** |
| Zyklus-Tab 30 Tage | 79 | **3** |

> In T Tagen passen bei Horizont H nur **T·24/H** nicht überlappende
> Fenster. Alles darüber ist dieselbe Beobachtung mehrfach gezählt.

---

## Teuer gelernt — bitte beherzigen

- **Echter Pfad für Hintergrundjobs:**
  `C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_*\pythonw.exe`.
  Der Pfad **ohne** Versionsordner (`WindowsApps\python.exe`) ist eine
  0-Byte-Attrappe. **Mit** Versionsordner ist er eine funktionierende
  Verknüpfung — das hatte ich am 15.08. falsch diagnostiziert.
- **Kein ungeschütztes `print()`** unter `pythonw` — `sys.stdout` ist
  `None`, das beendet das Programm.
- **Logs und Datenbanken schreiben UTC**, die Windows-Prozessliste
  Ortszeit (UTC+2).
- **Ein ausgeführter Handel** erkennt man an `[JOURNAL]` oder `[EXEC]` —
  **nie** am Wort „BUY". Das steht auch in Vorschlägen und Ablehnungen.
- **Wenn ein Pfad an einer Verteilstelle vorbeiführt**, verlieren ihn
  **alle** Empfänger — nicht nur der, bei dem es zuerst auffällt.

---

## Wo was steht

| Datei | Inhalt |
|---|---|
| `LAGE.md` | Was läuft, welche Daten es gibt — **die Eingangstür** |
| `BOT-HANDBUCH.md` | Teile **4.30–4.47** sind vom 17.08. |
| `tickets.txt` | Kurznotizen zu jeder Änderung |
| `TODO-NACH-DEM-MESSFENSTER.md` | Alles Offene |
| `prognosen/` | Tilo und Mark, getrennt |
| `zahlenbuecher/` | Tageskopien, aktueller Stand in `ZAHLENBUCH.pdf` |

**Neue Messwerkzeuge vom 17.08.** (alle nur lesend):

```bash
python schwelle_vergleich.py     # hatte der lernende Waechter recht?
python maker_schatten.py         # lohnen Warte-Auftraege?
python regime_filter_messung.py  # was haetten die Blockaden gebracht?
```
