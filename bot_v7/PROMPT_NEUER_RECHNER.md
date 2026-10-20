# Prompt zum Kopieren — „Richte den V6-Ordner auf dem neuen Rechner ein"

*Angelegt 01.09.2026. Alles darin ist an diesem Rechner nachgemessen, nicht
aus dem Gedächtnis geschrieben. Fundstellen stehen dabei, damit der andere
Claude nachsehen kann statt zu raten.*

---

Alles ab hier kopieren:

---

Du richtest auf einem **fabrikneuen Windows-Rechner** einen bestehenden
Trading-Bot ein. Der Ordner `trading_imperium_v6(21)` ist bereits kopiert.
Es ist **kein Python installiert**, es wurde noch **kein einziger Befehl**
ausgeführt.

## Wie ich angesprochen werden möchte

**Alltagssprache, das Fachwort in Klammern dahinter** — also „Sperre nach
Verlustserie (Cooldown)", nicht nur „Cooldown". Ich will die Begriffe
lernen, nicht überrollt werden. Härte gehört ins Urteil, nicht in die
Wortwahl. Kein Lob ohne Befund.

**Keine Befehlszeilen zum Abtippen.** Wenn ich etwas selbst starten soll,
bau eine `.bat` zum Doppelklicken. Der Ordnername enthält Klammern —
`trading_imperium_v6(21)` — das bricht `cmd` ohne Anführungszeichen. Jeder
Pfad gehört in `"..."`.

**Sag mir, wenn du etwas nicht weißt.** Vier Stufen, keine anderen:
**SICHER** (nur mit Fundstelle `datei.py:123`) · **WAHRSCHEINLICH** ·
**VERMUTUNG** · **OFFEN**. Nenne auch den Umfang deiner Prüfung: „Struktur
gesichtet, nicht jede Datei gelesen" ist eine Pflichtangabe, keine Schwäche.

---

## Ein Satz zur Einordnung

Derselbe Bot läuft auf meinem alten Rechner weiter. Die beiden Geschichten
laufen ab dem ersten Start hier auseinander — **das ist so gewollt.** Von
diesem Rechner fließt nichts zurück. Der mitkopierte Datenordner
`data_store/` bleibt, wie er ist; der Bot macht hier einfach dort weiter,
wo die Kopie aufhört. Du musst nichts leeren und nichts trennen.

---

## Was das Ding ist

**Papierhandel (Paper Trading), kein echtes Geld.** Der Modus steht in
`data_store/config.json` als `"mode": "paper"` und bleibt so. Zielbörse wäre
Bybit EU, Kosten **0,505 % je Runde** (Kauf und Verkauf zusammen) — diese
Zahl ist eine feste Konstante und wird **nie** aus `ccxt` geholt.
Kursdaten kommen von Binance (nur lesend, ohne Schlüssel).

---

## Schritt 0 — Kam beim Entpacken alles an?

Der Ordner ist als ZIP herübergekommen und schon entpackt. Sieh kurz nach,
ob diese Dinge da sind:

- `app.py`, `requirements.txt`, `.env`
- die Ordner `data_store/`, `core/`, `ui/`, `features/`, `execution/`,
  `models/`, `agents/`, `docs/forschungsprogramm_2026-07/capture/`
- die Bücher `BOT-HANDBUCH.md`, `GEFUNDENE-PROBLEME.md`, `OFFEN.md`,
  `PROJEKT-ENTSCHEIDUNGEN.md`, `CLAUDE.md`, `tickets.txt`

**Leere Ordner musst du nicht suchen.** Alles, was der Bot zur Laufzeit
braucht, legt er mit `os.makedirs(..., exist_ok=True)` selbst an — geprüft,
zwölf Stellen. Wenn ein ZIP leere Ordner verschluckt hat, heilt sich das
beim ersten Start.

## Schritt 1 — Python, und die Falle dabei

Gebraucht wird **Python 3.13** (auf dem Quellrechner läuft 3.13.14).

> **Die Falle:** Windows liefert ab Werk einen *Platzhalter* namens
> `python.exe` mit. Tippt man `python`, öffnet sich der Microsoft Store,
> statt dass etwas läuft. In geplanten Aufgaben scheitert er still.

Deshalb: **Python von python.org installieren**, Haken bei „Add python.exe
to PATH". Danach unter *Einstellungen → Apps → Erweiterte App-Einstellungen
→ App-Ausführungsaliase* die beiden Einträge `python.exe` und `python3.exe`
**ausschalten**.

Prüfen — der Pfad darf **nicht** `WindowsApps` enthalten:

```
python --version
python -c "import sys; print(sys.executable)"
```

Zusätzlich installieren: **Git** (für die Versionsgeschichte) und
**Claude Code**.

## Schritt 2 — Abhängigkeiten (hier scheitert es sonst)

**Ohne diesen Schritt startet gar nichts.** Auf diesem Rechner ist bisher
kein einziger Befehl gelaufen; es fehlt jede Bibliothek.

Im Projekt liegt `requirements.txt` mit **gepinnten Versionen** — Absicht,
damit ein Update nicht heimlich etwas Neueres zieht, das etwas zerschießt.
Nicht „aktualisieren", nicht `--upgrade`.

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

20 Pakete, unter anderem `ccxt`, `pandas`, `numpy`, `pandas-ta`,
`scikit-learn`, `xgboost` (kein sichtbarer Import, aber zur Laufzeit fürs
Modell nötig), `matplotlib`, `mplfinance`, `customtkinter`, `Flask`,
`reportlab` (für die PDF-Bücher), `openpyxl`.

> **Diese Datei war bis zum 01.09.2026 unvollständig** — `reportlab` und
> `openpyxl` fehlten, obwohl der Code sie braucht (Befund 92). Sie sind
> nachgetragen. Sollte trotzdem etwas fehlen, ist das derselbe Fehlertyp:
> **nicht raten, sondern messen** — alle `.py` mit `ast` einlesen,
> Top-Level-Importe sammeln, Standardbibliothek und eigene Dateien
> abziehen, den Rest gegen die Datei halten.

**Danach prüfen, ob wirklich alles da ist** — bevor der Bot angefasst wird:

```
python -c "import ccxt, yfinance, websocket, requests, pandas, numpy, pandas_ta, sklearn, xgboost, matplotlib, mplfinance, customtkinter, PIL, praw, bs4, flask, pyngrok, psutil, reportlab, openpyxl; print('alle 20 Pakete geladen')"
```

Läuft die Zeile durch, sind die Bibliotheken in Ordnung. Bricht sie ab,
sagt die Meldung, welches Paket fehlt.

**`optuna` fehlt absichtlich.** `backtest/hyperopt.py:16-21` fängt das mit
`try/except` ab und setzt `HAS_OPTUNA = False`. Auch auf meinem alten
Rechner ist es nicht installiert, und der Bot läuft. **Nicht
nachinstallieren.**

Wenn eine Version auf dieser Maschine nicht baut: **melde es mir**, ändere
die Datei nicht eigenmächtig.

## Schritt 3 — Zugangsdaten

Es gibt `.env.example` mit acht Feldern. **Tatsächlich gefüllt sind nur
zwei** — `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID`. Börsenschlüssel gibt
es bewusst nicht; im Papierhandel werden keine gebraucht.

**Trage keine Schlüssel selbst ein und frag mich nicht nach ihnen im Chat.**
Sag mir nur, welche Datei welche Zeile braucht — ich fülle sie selbst aus.

## Schritt 4 — Zwei fest verdrahtete Pfade reparieren

Zwei Stellen zeigen auf den alten Benutzernamen und gehen hier ins Leere.
Beide **SICHER**, nachgemessen:

| Datei | Zeile | steht dort | was zu tun ist |
|---|---|---|---|
| `check_punkt_a.py` | 9 | `BASE = r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)"` | durch `os.path.dirname(os.path.abspath(__file__))` ersetzen |
| `lage_erzeugen.py` | 229 | `sich = r"C:\Users\<BENUTZER>\OneDrive\trading_imperium_sicherung"` | auf einen Pfad dieses Rechners zeigen lassen, oder den Sicherungszweig überspringen |
| `sammler_taeglich.bat` | — | `set "PROJ=..."` und ein absoluter Python-Pfad | beide auf diesen Rechner ziehen |

`schatten_starter.py:45` hat den alten Pfad ebenfalls, aber nur als
Rückfallwert hinter `os.environ.get("LOCALAPPDATA", ...)` — der greift von
allein. **Nicht anfassen.**

In `check_install.py:3` steht der Pfad nur in einem Kommentar. Ebenfalls
harmlos.

## Schritt 4b — Die drei Haken, sonst arbeitest du ohne meine Regeln

In `.claude/settings.json` stehen **drei Haken (Hooks)** mit fest
eingetragenen Pfaden auf den alten Rechner:

| Wann | Datei | Wozu |
|---|---|---|
| `SessionStart` | `.claude/hooks/sitzungsstart.py` | legt dir zu Sitzungsbeginn das Projektgedächtnis vor |
| `UserPromptSubmit` | `.claude/hooks/jede_nachricht.py` | legt bei **jeder** Nachricht die Dauerregeln bei |
| `PreToolUse` (Write/Edit) | `.claude/hooks/schreibschutz.py` | verhindert Schreiben in geschützte Dateien |

Alle drei zeigen auf
`C:/Users/<BENUTZER>/Desktop/trading_imperium_v6(21)/.claude/hooks/…`.

> **Stimmt der Pfad hier nicht, brechen sie STILL.** Claude Code führt den
> Haken dann einfach nicht aus, meldet nichts — und du arbeitest ohne die
> Projektregeln und ohne Schreibschutz, ohne es zu merken. Genau die Sorte
> Fehler, die dieses Projekt „stilles Scheitern" nennt und verbietet.

**Also:** Pfade in `.claude/settings.json` und `.claude/settings.local.json`
auf diesen Rechner ziehen. Falls Claude Code hier die Variable
`$CLAUDE_PROJECT_DIR` in Hook-Argumenten auflöst, ist das die bessere
Lösung — dann ist die Datei umzugsfest. **Erst ausprobieren, dann
behaupten.**

**Und dann beweisen, dass sie greifen:** Starte eine neue Sitzung und zeig
mir, dass das Projektgedächtnis tatsächlich vorgelegt wurde. „Die Datei ist
angepasst" ist kein Beleg.

## Schritt 5 — Erster Start

**Erst wenn Schritt 1 bis 4 durch sind.** Vorher startet nichts — es fehlen
die Bibliotheken.

**Der Bot startet seine Wächter selbst.** `app.py` ruft beim Hochfahren
`starten()` in `sammler_pruefen.py` auf — das ist Absicht und dokumentiert
(`sammler_pruefen.py:54`). Es gibt also **keinen** Handstart-Marathon:

```
start_bot.bat
```

Damit läuft alles: das Cockpit-Fenster, der Papierhandel, und die zwei
Dauerläufer, die nach einem Neustart fehlen würden —
**Schatten-Universum** (`schatten_universum.py --dauer`, beobachtet 18
Münzen, ohne zu handeln) und **Positionsverlauf** (`positionsverlauf.py`,
schreibt alle 5 Minuten den Stand jeder offenen Position).

Der dritte Dauerläufer, die **Forschungs-Erfassung**, hängt an der
geplanten Aufgabe aus Schritt 6.

**Es läuft immer nur EINE Bot-Instanz.** Vor jedem Neustart nachsehen, wer
Port **5050** hält. Achtung: Prozesse *zählen* führt in die Irre — der
Windows-Startwrapper erzeugt immer ein Elternprozess-Paar, das wie zwei
Instanzen aussieht.

**Drei `.bat` zum Doppelklicken sind schon da:**

| Datei | Was sie tut |
|---|---|
| `start_bot.bat` | Bot samt Wächtern starten |
| `SAMMLER_PRUEFEN.bat` | nur nachsehen, greift nicht ein |
| `SAMMLER_NEUSTART.bat` | alle Sammler beenden und frisch starten |

**Nicht benutzen:** die zwei Dateien, die mit `ZZ_NICHT_BENUTZEN_`
beginnen. Der Name ist die Warnung — sie starten Dinge doppelt.

## Schritt 6 — Die zwei geplanten Aufgaben

Im Ordner `aufgabenplanung_backup/` liegen `TI6-Sammler.xml` und
`ForschungCapture.xml`.

> **Diese XML-Dateien NICHT einfach importieren.** Sie enthalten die
> Benutzerkennung (SID) des alten Rechners und dessen Pfade. Ein Import
> erzeugt eine Aufgabe, die aussieht als liefe sie, und still nichts tut.

Lies sie als **Vorlage** und lege die Aufgaben neu an:

| Aufgabe | Was | Wann |
|---|---|---|
| `TI6-Sammler` | `sammler_taeglich.bat` | täglich **06:00** |
| `ForschungCapture` | `capture_start.bat` | alle **10 Minuten** |

**Zur zweiten:** Der Capture ist ein **Dauerläufer**. Die 10-Minuten-Aufgabe
ist nur der Wächter, der ihn neu startet, falls er tot ist. Sie wird im Log
fast immer `UEBERSPRUNGEN - laeuft bereits` schreiben, und der
Windows-Rückgabewert `267009` heißt „läuft gerade". **Beides ist der
gesunde Zustand, kein Fehler.**

## Schritt 7 — Prüfen, und zwar richtig

Das Projekt bringt seine eigenen Prüfwerkzeuge mit. Benutze die, statt neue
zu bauen:

| Werkzeug | Antwortet auf |
|---|---|
| `python check_install.py` | Sind die Bausteine da? |
| `python prozess_frische.py` | Läuft irgendwo noch alter Programmtext? |
| `python sammler_pruefen.py` | Schreibt jeder Sammler das, was gebraucht wird? |
| `python vollstaendigkeit.py` | Welche Felder haben Lücken? |
| `python stichtag.py` | Reichen die Daten? |
| `python lage_erzeugen.py` | Erzeugt `LAGE.md` — **nie von Hand schreiben** |

> **Der Prüfmaßstab, auf den es ankommt:** „Der Prozess läuft" ist **kein**
> Beleg dafür, dass Daten ankommen. Nimm die Zeilenzahl aller Tabellen,
> warte drei Minuten, nimm sie erneut, und zeig mir die **Differenz**. Nur
> gewachsene Tabellen beweisen, dass geschrieben wird.
>
> Und prüfe deine Abfrage gegen einen **von Hand nachgerechneten
> Einzelfall**, bevor du eine Zahl meldest. Am Quellrechner meldete ich
> einmal „0 Trades heute", weil ich im Handelsbuch nach `timestamp` suchte —
> das Feld heißt `time`. Es waren acht. **Das Messgerät war falsch, nicht
> das Gemessene.**

---

## Die Dauerregeln, die auch hier gelten

**1. Alles doppelt prüfen.** Keine ausgerechnete Zahl melden, bevor sie
gegen einen bekannten Wert geprüft ist. Nicht gegen Plausibilität, nicht
gegen eine Anzahl. Lieber ein „nicht entscheidbar" als eine Zahl, die gut
aussieht.

**2. Ursache vor Symptom.** Kein `try/except`, kein Fallback, kein
Notbehelf, um einen Fehler zu verstecken. Bei jedem Fehler: Ursachenkette,
Auswirkung, drei Wege (minimal / sauber / strukturell) — und **genau eine**
Empfehlung.

**3. Kein stilles Scheitern.** Kein Fehler darf nur ins Log wandern und dann
vergessen werden. Nach dem Anlegen eines Hintergrundjobs **nachsehen, ob
wirklich etwas passiert**.

**4. Bestandsschutz — ohne meine Freigabe wird nichts davon angefasst:**
- Die vier Cockpit-Reiter (Chartanalyse, Geldfluss, Terminal, Zyklus) sind
  reines Beobachtungsdeck und bleiben vom Handelspfad getrennt.
- `docs/forschungsprogramm_2026-07/forschung.db` bleibt von
  `data_store/telemetrie.db` **abgekoppelt**. Keine Verbindung, kein
  gemeinsames Schema, kein Schreibzugriff. Das ist eine Entscheidung.
- Was im Code als **bewusst stillgelegt** markiert ist, bleibt stillgelegt:
  Grid-Bot, `backtest/optimizer.py`, `futures_trader.py`,
  `multi_exchange.py`, TradingView-Webhook, Reddit. Das sind Entscheidungen,
  keine Fehler — **nicht erneut als Befund melden.**

**5. Vor jedem neuen Befund — beides, nicht eins davon:**

```
python schon_bekannt.py <datei.py:zeile>
python schon_bekannt.py <bezeichner>
```

Meldet es **BEKANNT**, ist es kein neuer Fund, sondern höchstens eine
**Ergänzung** — und muss als solche geschrieben werden, mit Verweis auf den
vorhandenen Abschnitt. Das Handbuch hat über 6.000 Zeilen; niemand liest es
vor jedem Befund. Die Prüfung dauert zwei Sekunden.

**6. `PROJEKT-ENTSCHEIDUNGEN.md` zuerst lesen**, bevor irgendetwas
„repariert" wird. Was dort steht, ist eine Entscheidung, kein Vorschlag.

**7. Wo was hingehört — es gibt keine sechste Liste:**

| Datei | Wofür |
|---|---|
| `OFFEN.md` | Die **eine** Liste offener Punkte |
| `GEFUNDENE-PROBLEME.md` | Befunde mit Nummer, dauerhaft — auch behobene bleiben stehen |
| `BOT-HANDBUCH.md` | Das *Warum*. **Zu jeder Änderung ein Abschnitt** — Pflicht |
| `tickets.txt` | Eingang für die Chronik |
| `LAGE.md` | Was gerade läuft — **nie von Hand**, nur `lage_erzeugen.py` |

**Zu `tickets.txt`:** Format `STICHWORT: Text`. **Nur fünf Stichworte sind
gültig** — `SPEICHERN`, `ERLEDIGT`, `BUG`, `DOKUMENTIEREN`, `NOTIZ`. Jedes
andere wird **still verworfen** und beim nächsten gültigen Ticket
**mitgelöscht**. Im Zweifel `DOKUMENTIEREN:` nehmen.

**Die Bücher immer in beiden Fassungen** — `.md` **und** `.pdf`. Sie laufen
sonst auseinander. Das PDF wird erzeugt (`handbuch_pdf.py`, `zahlenbuch.py`),
**nie von Hand geändert**.

**8. Nichts anschließen ohne Messung.** Vier fertige Bausteine wurden schon
verworfen, weil sie schlechter waren als die einfachste Alternative. Und
die **Trivial-Latte** immer mit ausweisen — „immer nein sagen" schlägt viele
Modelle. Ein Modell ohne diesen Vergleich gilt als ungemessen.

---

## Was ich am Ende von dir will

**Das Ziel ist schlicht: Der Bot läuft, das Cockpit-Fenster geht auf, und
alle Wächter sammeln — genau wie auf meinem alten Rechner.**

Dazu:

1. **Ein Prüflauf, der zeigt, dass Daten wirklich ankommen** — mit der
   Zeilenzahl-Differenz, nicht mit „Prozess läuft".
2. **Ein Abschnitt in `BOT-HANDBUCH.md`**, der festhält, was auf diesem
   Rechner anders ist als auf dem alten — Pfade und geplante Aufgaben.
3. **Tickets in `tickets.txt`** über alles, was du gemacht hast.
4. **Eine ehrliche Liste dessen, was du nicht prüfen konntest.**

## Was du nicht tun sollst

- Den Betriebsmodus von `paper` auf `live` stellen. Nie, unter keinen
  Umständen, auch nicht „zum Testen".
- Versionen in `requirements.txt` aktualisieren.
- Etwas als Befund melden, ohne vorher `schon_bekannt.py` laufen zu lassen.
- Einen Fehler mit `try/except` zudecken.
- Mir sagen, alles laufe, weil ein Prozess in der Liste steht.

Wenn dir etwas auffällt, das ich nicht gefragt habe — sag es.
