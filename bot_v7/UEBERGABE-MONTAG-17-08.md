> **ÜBERHOLT — nicht mehr als Aufgabenliste benutzen.**
> Diese Datei ist eine **Momentaufnahme** vom Zeitpunkt ihres Schreibens.
> Am selben Tag wurde danach weitergearbeitet; einzelne Punkte darin
> waren schon erledigt, als sie hier hineingeschrieben wurden.
> **Die einzige gültige Liste ist `OFFEN.md`** (`python offen.py`).
> Wer von hier abschreibt, ohne gegen die Commits zu prüfen, trägt
> erledigte Punkte weiter — genau das ist am 18.08.2026 passiert.

> **VERALTET — NEUER: `UEBERGABE-NAECHSTER-CHAT.md` (17.08.2026, 11:05 UTC).**
> Bei Widerspruechen gilt die neuere Datei.

# Übergabe an den Chat am Montag, 17.08.2026

**Geschrieben 14.08.2026 nach einer langen Sitzung.** Sven ist bis Montag
nicht am Rechner. Bot und Sammler laufen durch.

> **Diese Datei ist neuer als `NAECHSTE-SESSION.md` (Stand 13.08.) und
> ergänzt sie.** Bei Widersprüchen gilt diese hier.

---

## ⛔ FREEZE — das Wichtigste zuerst

Es läuft ein **Zwei-Wochen-Messfenster**: Epoche `E6_messfenster`, Beginn
**13.08.2026 13:21 UTC**, Ende etwa **27.08.2026**.

**Am Handelspfad wird NICHTS geändert.** Nicht Entry, nicht Exit, nicht
Stop, nicht DCA, nicht Score, nicht Ordertyp, keine Schwelle. Keine Regel
scharf schalten oder in den Schatten stellen.

**Warum so streng:** Am 12.08. löschte ein Speichervorgang in der
Einstellungsmaske versehentlich den Regel-Schalter und schaltete den
Trend-Ausstieg wieder scharf. Ein Trade für −2,68 $ — und niemand merkte
es, weil nur eine Protokollzeile *fehlte*.

**Erlaubt:** Anzeige, Berichte, Auswertung, Dokumentation, Aufräumen
außerhalb des Handelspfads.

---

## Zuerst lesen

1. **`LAGE.md`** — was läuft, welche Daten es gibt.
   `python lage_erzeugen.py` erzeugt sie neu. **Das ist die Eingangstür.**
2. **`TODO-NACH-DEM-MESSFENSTER.md`** — alles Offene
3. `BOT-HANDBUCH.md` Teil **4.20–4.27** — was zuletzt gebaut wurde
4. `GEFUNDENE-PROBLEME.md` — Statustabelle unten

---

## Erster Handgriff: läuft noch alles?

```bash
python lage_erzeugen.py
python schatten_universum.py --status
python nachlauf.py --status
```

| Prüfung | Erwartung |
|---|---|
| Bot | läuft, `system.log` wenige Minuten alt |
| Forschungs-Capture | läuft |
| Schatten-Universum | **genau EIN** Prozess (es liefen schon mal vier) |
| Zahlenbücher | je Tag eines seit 14.08. |
| Regel-Schalter | `trend_exit=SHADOW` |

**Fehlt der Sammler:** `schatten_universum_start.bat` starten. Nach dem
Start dauert es **20–40 s** bis zur ersten Logzeile — nicht zu früh auf
Ausfall schließen (dieser Irrtum ist mir zweimal passiert).

**Kam „REGEL-SCHALTER VERSTELLT" per Log oder Telegram:** sofort melden,
das ist ein Freeze-Bruch.

---

## Sechs offene Punkte — alle freeze-sicher

Reine Anzeige und Aufräumarbeit, kein Handelspfad.

| # | Was | Warum |
|---|---|---|
| **1** | **Nachlauf: 24-/48-Stunden-Kurse werden nicht nachgetragen** | `p1h`/`p4h` füllen sich, `p24h`/`p48h` bleiben bei **0** — bei 908 Ereignissen älter als 24 h. **Genau die Werte für die Hauptfrage.** Gemessen 15.08. |
| **2** | **`V6-Verwertung-Woche` reparieren** | Benutzt den kaputten AppData-Pfad → **der Montagsbericht entsteht nicht** |
| **2b** | **Nachlauf-Abschnitt ins Zahlenbuch** | `nachlauf.py` sammelt (1.003 Ereignisse), erscheint aber **nicht** im PDF |
| **3** | Indikator-Inhalte ins Zahlenbuch | `feature_snapshots` (38 Spalten: RSI, MACD, EMA20/50/200, Bollinger, OBV, VWAP, TSI …) wird nur als Füllstand gezeigt, nie inhaltlich. **Sven hat ausdrücklich danach gefragt.** |
| **4** | `TI6-Zahlenbuch`-Aufgabe entfernen | Doppelt zum Sammler, unzuverlässig |
| **5** | `nachlauf.db` in `LAGE.md` aufnehmen | Eingangstür kennt sie nicht |
| **6** | `job_schatten.py` aufräumen | Ungenutzter Fehlversuch |

**Punkt 1 zuerst** — ohne ihn misst das Fenster seine wichtigste Frage nicht.
Dann Punkt 2, sonst fehlt jede Woche ein Bericht.

---

## Wie es jetzt läuft (wichtig zu verstehen)

**Ein Prozess erledigt alles.** Der Sammler des Schatten-Universums läuft
über den **Autostart** und macht:

| Takt | Was |
|---|---|
| stündlich | 12 Münzen bewerten und mitschreiben |
| stündlich | Nachlauf-Kurse nachtragen (1/4/24/48 h nach jedem Ausstieg) |
| täglich | Zahlenbuch als PDF + `LAGE.md` |

**Keine geplante Aufgabe mehr** für diese Dinge — die hat viermal Erfolg
gemeldet und nichts ausgeführt.

---

## Teuer gelernt — bitte beherzigen

**Hintergrund-Jobs:**
- **Echter** Pfad:
  `C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_*\pythonw.exe`
- **NIE** `AppData\Local\Microsoft\WindowsApps\...` — das ist eine
  **0-Byte-Datei**. Die Aufgabe meldet Erfolg und tut **nichts**.
  Vier Fehlschläge an einem Tag.
- **Kein ungeschütztes `print()`** — unter `pythonw` ist `sys.stdout`
  `None`, das beendet das Programm. Erst ins Log, dann anzeigen.
- Nach dem Anlegen einer Aufgabe **prüfen, ob sie wirklich etwas tut.**

**Der Rechner:** 3,9 GB RAM, CPU dauerhaft 100 %. Bot und Sammler brauchen
zusammen nur **71 MB** — die Last kommt von Claude Desktop (805 MB) und
Firefox. Mini-PC kommt in etwa einem Monat.

**Zeitzonen:** Logs und Datenbanken schreiben **UTC**, die
Windows-Prozessliste **Ortszeit (UTC+2)**. Ich hielt deshalb aktuelle
Meldungen für veraltet.

---

## Drei Daueraufgaben — ohne Nachfrage

1. **Erklärstil:** Alltagssprache zuerst, Fachbegriff in Klammern daneben
2. **`BOT-HANDBUCH.md`** zu jeder Änderung fortführen
3. **Tickets** selbständig in `tickets.txt` schreiben

Sven musste alle drei am 14.08. einfordern, weil sie liegengeblieben
waren.

---

## Was am 27.08. ansteht

1. **War der Stop richtig?** (`nachlauf.py`) — größter Hebel
2. **Trailing-Schwelle gegen Kostenschwelle** — 0,8 % gegen ~1,37 %.
   Reine Rechnung, braucht keine neuen Daten, **könnte die ganze
   Priorisierung umwerfen**
3. Ist Score 8 besser als Score 6?
4. Welche Münze verdient ihre Reibung? (DOGE ist der Kandidat)
5. Waren die 98.000 Blockaden die richtigen?

**⚠️ KORREKTUR vom 15.08. — die Erwartung von ~40 Trades war falsch.**
Gemessen: seit Epochenstart **ein einziger Trade**, **null Verkäufe**.
Der Bot sitzt in einer Doppelsperre — 3 von 3 Plätzen mit genau den 3
handelbaren Münzen belegt (12.281 Kapazitäts-Ablehnungen), dazu der
Regime-Filter (18.980 Blockaden). Verkauft wird nicht, weil alle drei
Positionen zwischen −0,21 % und −0,85 % hängen: zu gut für den Stop
(−2,0 %), zu schlecht für die Ratsche (Breakeven ab +1,0 %).

**Das Fenster wird also fast keine Handelsdaten liefern.** Kein Defekt —
Folge der Verkleinerung auf 3 Münzen. **Sven muss entscheiden**, ob das
Fenster so weiterläuft; Auflösen der Sperre wäre ein Freeze-Bruch.

Was trotzdem trägt: das Schatten-Universum (~4.000 Signale) für die
Münz-Frage — und Frage 2, die bereits **am 14.08. beantwortet wurde**:
55 % der Trailing-Ausstiege realisieren unter der Kostenschwelle.

---

## Nebengleis: Verwertung

Eigener Ordner `Desktop\V6_Verwertung`, **liest** aus V6, schreibt nichts
hinein. Wochenbericht montags.

**Kernaussage bleibt:** Der Bot verliert nach ehrlichen Kosten Geld
(≈ −120 $ über 446 Trades) und darf **nicht** als Handelssystem verkauft
werden. Verkäuflich sind Werkzeuge, Prüfleistung und Lehrmaterial — der
Engpass ist ein **Referenzfall**.
