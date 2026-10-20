# Anweisung für den Reparatur-Chat

**Stand 11.08.2026, 23 Uhr.** Der Rundgang ist abgeschlossen — 19 Runden,
jeder Ordner, alle 2.511 Dateien klassifiziert. Ergebnis liegt in
`BOT-HANDBUCH.md` (57 Seiten), `GEFUNDENE-PROBLEME.md` (28 Punkte),
`RUNDGANG-CHECKLISTE.md` und `INVENTAR.md`.

**Diese Datei ist die Arbeitsanweisung für die Fortsetzung.**

---

## Zuerst lesen (in dieser Reihenfolge)

1. `GEFUNDENE-PROBLEME.md` — die Statustabelle ganz unten zeigt, was
   bereits behoben ist (Punkte 3, 4, 19, 20, 21) und was offen ist.
2. `BOT-HANDBUCH.md`, **Teil 8** — die Abwägung: was weg kann, was
   geprüft werden soll, was eingebaut werden soll, was bewusst
   liegenbleibt.
3. Erst danach anfangen zu arbeiten.

**Neu hinzugekommen seit dem letzten Stand des Fix-Chats:** Punkte 22–28.
Besonders Punkt 25 (Replace-Installer), 26 (zwei Hauptordner-Dateien
sind aktiver Bot-Code) und 28 (kein Backup außerhalb des Rechners).

---

## Aufgabe 0 — vor allem anderen: Sicherung anlegen

**Punkt 28 aus `GEFUNDENE-PROBLEME.md`.** Es gibt keine Kopie des
Projekts außerhalb dieses Rechners. Kein Git, kein externes Backup.
Sieben Monate Arbeit, alle Messreihen, beide Handbücher — auf einer
Festplatte.

Vorschlag zur Abstimmung mit Sven (er entscheidet):
- ein lokales Git-Repository anlegen (`git init`, erster Commit) —
  ändert nichts am laufenden Bot, macht aber jede künftige Änderung
  rückholbar
- zusätzlich eine Kopie des Ordners auf eine externe Festplatte

**Jeder andere Punkt dieser Liste ist reparabel. Dieser nicht.**

---

## Aufgabe 1 — Svens Beobachtung sauber beantworten

**Seine Frage:** „Seit wir mit dem BTC-only-Modus angefangen haben, geht
der Bot wieder ins Minus. Was haben wir verstellt?"

**Was am 11.08. bereits nachgemessen wurde** (Journal `trades_v5.json`,
441 Verkäufe):

| Ausstiegsart | Anzahl | Summe | je Trade | Gewinnerquote |
|---|---|---|---|---|
| TRAILING_STOP | 169 | **+156,51 $** | +0,93 | 99 % |
| DCA_FEAR_GREED | 137 | **+52,20 $** | +0,38 | 99 % |
| MANUAL_SELL | 9 | +7,38 $ | +0,82 | 89 % |
| STOP_LOSS | 68 | **−187,63 $** | −2,76 | **0 %** |
| TREND_EXIT | 46 | −36,08 $ | −0,78 | 0 % |
| DAILY_LOSS_SAFETY | 5 | −13,51 $ | −2,70 | 0 % |
| BREAKEVEN_LOCK | 7 | −1,44 $ | −0,21 | **0 %** |

Kumulierter Verlauf: bester Stand **06.08. mit −14,45 $**, heute
−22,58 $. Der Bruch liegt am **10.08.**: zwei Trades (ETH-Stop −4,36,
BTC-Trend-Exit −2,50) machen die −6,86 dieses Tages aus.

**Erste Einschätzung: keine verstellte Einstellung, sondern ein
schlechter Markttag.** Die Zahlen in `stoploss_analyse.py` (Stand 10.08.)
sind identisch mit den heutigen — die Struktur hat sich nicht verändert.

**Aber das ist noch kein Beweis.** Zu tun:
1. `python epoch_report.py` laufen lassen — trennt das Ergebnis nach
   Konfigurations-Epoche. Falls die Epochen-Definition in `epochs.py`
   nicht bis heute reicht: ergänzen.
2. Prüfen, ob zwischen 06.08. und 10.08. eine Einstellung geändert wurde
   (`config/versioning.py` führt Versionen; sonst
   `data_store/config.json` gegen Sicherungskopien vergleichen).
3. Ergebnis Sven **in einem Satz** sagen: verstellt ja/nein.

**Wichtig für den Ton:** Sven ist frustriert und glaubt, nicht
voranzukommen. Die Zahlen sagen etwas anderes — zwei von drei
Ausstiegswegen arbeiten mit 99 % Trefferquote profitabel. Das gehört in
die Antwort, nicht nur der Verlust.

---

## Aufgabe 2 — Der eine Befund, der alles überlagert

**68 Stop-Loss-Verkäufe kosten −187,63 $ — mehr als alle 169
Trailing-Gewinne einbringen (+156,51 $).** Trefferquote 0 %, im Schnitt
−2,76 $ je Fall.

Das ist kein neuer Fund, sondern der Kern des ganzen Projekts. Das
Mess-Audit (`docs/messungen_2026-07/BEFUNDE.md`) hat dazu bereits zwei
Dinge belegt:
- „Kein Stop rettet das System" — sieben Stop-Varianten getestet, keine
  erreicht das nötige Chance/Risiko-Verhältnis.
- „Der Verlust wird umgepackt, nicht beseitigt" — weitere Stops sind
  seltener, aber teurer.

**Nicht wieder an der Stop-Weite drehen.** Das ist gemessen und
erledigt. Wenn hier etwas verbessert werden soll, dann am **Einstieg**
(warum geraten 68 Positionen überhaupt so weit ins Minus?) — und das
braucht eine eigene, vorregistrierte Messung, keine Bastelei.

Vorschlag: `python stoploss_analyse.py` laufen lassen, das Werkzeug
beantwortet genau diese Frage und ist bereits gebaut.

---

## Aufgabe 3 — Die fünf Einbau-Kandidaten (Teil 8.3 im Handbuch)

In dieser Reihenfolge, jeweils **ein Punkt nach dem anderen**, mit
Handbuch-Eintrag danach:

1. **Drei-Stufen-Schalter anschließen** (`core/regel_schalter.py`,
   Punkt 11). Fertig gebaut und getestet, aber von keiner Regel benutzt.
   Danach kann jede Regel einzeln in den Notizbuch-Modus, ohne dass
   dafür jedes Mal eigener Code entsteht.
   **Vorher klären:** Sven erinnert sich, dass in der Sitzung vom 11.08.
   gesagt wurde, der Schalter sei „verdrahtet bzw. getestet" — im
   `ENTWICKLERHANDBUCH.md` nachlesen, was genau gemeint war.
2. **Ist-Slippage ins Journal** (Punkt 24). Die Zahl wird bei jedem
   Trade berechnet und dann weggeworfen. Eine Zeile Aufwand, macht
   Punkt 23 überhaupt erst messbar.
3. **Automatischer Epochen-Schnitt** (`epochs.py` +
   `config/versioning.py`). Löst auch Aufgabe 1 dauerhaft.
4. **Wiederkehrende Berichte** aus `stoploss_analyse.py` und
   `regime_filter_messung.py` — als wöchentlicher Lauf wie der
   Chartanalyse-Agent.
5. **Trend-Ausstieg für alle Münzen** (Punkt 8). Muss behoben sein,
   **bevor** die Regel je wieder scharf geschaltet wird — steht aktuell
   im Notizbuch-Modus, also ungefährlich.

---

## Aufgabe 4 — Aufräumen (erst wenn Aufgabe 0 erledigt ist)

Teil 8.1 im Handbuch: rund 240 Dateien können weg, keine davon wird vom
Bot geladen.

**Bedingung vorher:** Die 17 `install_*.py`/`fix_*.py`-Skripte tragen in
ihren Kopfzeilen Begründungen mit Messzahlen, die sonst nirgends stehen.
Diese Docstrings in eine Textdatei sichern, dann können auch sie weg.

**Werkzeug:** `python cleanup.py` — verschiebt ins Archiv statt zu
löschen, schützt `docs/` und die Handbücher ausdrücklich.

**Achtung:** `update_metals_indikatoren.py` **nicht** ausführen — es
ersetzt Dateien statt sie zu patchen und hat am 06.08. bereits zweimal
etwas gelöscht (Punkt 25).

---

## Dauerregeln für diesen Chat

- **Ein Punkt nach dem anderen.** Nach jedem Fix zeigen, was sich
  geändert hat, dann weiter.
- **Jede Änderung bekommt einen Handbuch-Eintrag** in `BOT-HANDBUCH.md`,
  Format wie Teil 4.7–4.11.
- **Nach jedem behobenen Punkt** das Häkchen in `GEFUNDENE-PROBLEME.md`
  setzen und die Statustabelle unten nachziehen.
- **Bot und Forschungs-Capture laufen weiter** — nicht anhalten. Vor
  einem Neustart prüfen, dass nur **eine** `app.py`-Instanz läuft:
  ```
  Get-CimInstance Win32_Process -Filter "Name='python3.13.exe'" | Select-Object ProcessId, CommandLine
  ```
  (Der Forschungs-Capture läuft ebenfalls als `python3.13.exe` — auf die
  Befehlszeile schauen, nicht nur auf die Anzahl.)
- **Nichts anschließen ohne Messung.** Vier fertige Bausteine wurden
  bereits verworfen, weil sie schlechter waren als die einfachste
  Alternative (Teil 8.4). Diese Prüfung gilt für jeden neuen Kandidaten.
- **Offen: die Fixes für Punkt 3 und 4 sind im Code, aber noch nicht
  aktiv** — der Bot lädt seinen Code beim Start. Ein Neustart wurde
  bewusst aufgeschoben.
