# AUSWERTUNGS-HANDBUCH — Trading Imperium V6

**Für Sven. Stand: 27.07.2026, 14:30 UTC.**

Alle Zahlen in diesem Handbuch sind an diesem Tag frisch aus
`data_store/trades_v5.json` nachgerechnet (918 Einträge, 414 Verkäufe,
erster 10.06.2026, letzter 27.07.2026 14:30). Keine Zahl stammt aus einem
Report, einer Übergabe oder einer alten Notiz.

**Wichtig vorweg: Zahlen in diesem Dokument altern.** Es sind Beispiele zum
Lernen, keine Wahrheit für immer. Wie schnell sie altern, zeigt Kapitel 5.

---

# Inhalt

1. [Die Kennzahlen — was sie bedeuten](#1-die-kennzahlen)
2. [Das Epochen-System](#2-das-epochen-system)
3. [Drei Befunde, die du kennen musst](#3-drei-befunde)
4. [Das Cockpit im Alltag](#4-das-cockpit-im-alltag)
5. [Checkliste: Bevor ich eine Zahl ernst nehme](#5-checkliste)

---

<a name="1-die-kennzahlen"></a>
# 1. Die Kennzahlen — was sie bedeuten

## 1.1 R/R (Chance-Risiko-Verhältnis)

**Was es ist:** Wie groß ist dein durchschnittlicher Gewinn im Vergleich zu
deinem durchschnittlichen Verlust.

```
R/R  =  durchschnittlicher Gewinn  ÷  durchschnittlicher Verlust
```

**Beispiel aus unseren echten Daten (alle 414 Verkäufe):**

| | |
|---|---|
| Ø Gewinn bei den 297 Gewinnern | **+0,69 $** |
| Ø Verlust bei den 117 Verlierern | **−2,00 $** |
| **R/R** | **0,34** |

*Quelle: `trades_v5.json`, Feld `pnl`, alle Einträge mit `type: SELL`.*

**Wie liest man das?** R/R 0,34 heißt: Wenn wir gewinnen, gewinnen wir 69 Cent.
Wenn wir verlieren, verlieren wir 2 Dollar. Ein Verlust frisst also fast drei
Gewinne auf.

**Warum R/R wichtiger ist als die Win-Rate:** Wir gewinnen in 71,7 % der Fälle —
das klingt großartig. Trotzdem stehen wir bei **−29,65 $**. Genau das ist der
Punkt: Viele kleine Gewinne, wenige große Verluste. Die Trefferquote sagt dir
nichts darüber, ob du Geld verdienst.

**Die Faustregel dahinter:** Damit du mit einer Win-Rate von 71,7 % überhaupt
bei null rausläufst, brauchst du ein R/R von mindestens

```
R/R_break_even  =  (1 − 0,717) ÷ 0,717  =  0,39
```

Wir liegen bei 0,34 — knapp darunter. Und genau deshalb ist das Ergebnis leicht
negativ, obwohl fast drei von vier Trades gewinnen.

**Das Live-Ziel ist R/R > 1,0.** Davon sind wir weit weg. Das ist kein Drama, das
ist der Grund, warum noch kein echtes Geld im Spiel ist.

> ⚠️ **R/R wird im Projekt nicht überall gleich gerechnet.** Das Cockpit zählt
> Trades mit `pnl` genau 0 weder als Gewinn noch als Verlust, `e7_auswertung.py`
> zählt sie als Verlust (`pnl <= 0`). Aktuell gibt es null solche Trades, also
> macht es heute keinen Unterschied — aber merk dir, dass es ihn geben kann.

## 1.2 Win-Rate

**Was es ist:** Anteil der Verkäufe mit Gewinn.

```
Win-Rate  =  297 Gewinner ÷ 414 Verkäufe  =  71,7 %
```

**Wofür sie taugt:** Als Stimmungsbild und als Frühwarnung, wenn sie plötzlich
einbricht. **Wofür sie nicht taugt:** als Erfolgsmaß. Siehe oben — 71,7 % und
trotzdem im Minus.

## 1.3 Das 95-%-Konfidenzintervall

**Das ist die wichtigste Kennzahl, die man am leichtesten übersieht.**

**Was es ist:** Ein Bereich, in dem die *echte* Trefferquote wahrscheinlich
liegt. Denn 414 Trades sind eine Stichprobe, kein Gesetz. Hättest du die
gleiche Strategie in einer anderen Woche laufen lassen, wäre eine etwas andere
Zahl herausgekommen.

**Beispiel aus unseren Daten:**

| Fenster | Sells | Win-Rate | 95-%-Intervall |
|---|---|---|---|
| Gesamt | 414 | 71,7 % | **67,2 % – 75,9 %** |
| E6.1 (ab 14.07.) | 65 | 70,8 % | **58,8 % – 80,4 %** |
| E7 (Cockpit-Fenster) | 45 | 66,7 % | **52,1 % – 78,6 %** |

*Berechnet nach Wilson, wie in `cockpit_server.py:93`.*

**Wie liest man das?** Bei E7 steht da 66,7 %. Aber das Intervall reicht von
52,1 % bis 78,6 % — das ist eine Spanne von über 26 Prozentpunkten. Übersetzt:
**Wir wissen es einfach noch nicht.** Bei 45 Trades ist die Zahl ein Hinweis,
kein Beweis.

**Die praktische Lehre:** Je schmaler das Intervall, desto ernster darfst du die
Zahl nehmen. Bei 414 Trades ist es 8,7 Punkte breit — brauchbar. Bei 45 Trades
26,5 Punkte — dünn. Bei 6 Trades (unsere MFE-Daten) wäre es so breit, dass die
Zahl praktisch nichts aussagt.

**Wenn sich zwei Intervalle überlappen, ist der Unterschied nicht belegt.**
E6.1 (58,8–80,4) und E7 (52,1–78,6) überlappen sich fast vollständig. Das heißt:
Aus der Win-Rate allein kannst du **nicht** ableiten, dass E7 schlechter ist
als E6.1. Der Unterschied könnte reiner Zufall sein.

## 1.4 MFE und MAE

**MFE** = *Maximum Favorable Excursion* = wie weit lief der Trade **maximal ins
Plus**, bevor er beendet wurde.
**MAE** = *Maximum Adverse Excursion* = wie weit lief er **maximal ins Minus**.

Beides wird seit dem 25.07. bei jedem Verkauf mitgeschrieben
(`runtime/exit_monitor.py:227-228`). Es ist **reines Logging** — `lowest` wird
nie in einer Verkaufsentscheidung gelesen, das Trading-Verhalten ändert sich
dadurch nicht.

**Alle bisher erfassten Trades (Stand 27.07., das sind erst 6):**

| Zeit | Coin | Ausstieg | Ergebnis | MFE | MAE | Give-Back |
|---|---|---|---|---|---|---|
| 25.07. 13:58 | AVAX | TRAILING_STOP | +3,11 % | +3,73 % | −0,55 % | 0,62 % |
| 26.07. 17:28 | SOL | TRAILING_STOP | +1,84 % | +2,72 % | −0,46 % | 0,88 % |
| 27.07. 13:07 | BTC | TRAILING_STOP | +1,16 % | +2,16 % | 0,00 % | 1,00 % |
| 27.07. 14:21 | SOL | TRAILING_STOP | +1,19 % | +2,79 % | 0,00 % | 1,60 % |
| 27.07. 14:30 | ADA | STOP_LOSS | −3,15 % | +1,43 % | −3,15 % | 4,58 % |
| 27.07. 14:30 | AVAX | STOP_LOSS | −2,18 % | +0,57 % | −2,18 % | 2,75 % |

*Quelle: `trades_v5.json`, Felder `mfe_pct`, `mae_pct`, `pnl_pct`.*

**Wozu MAE gut ist:** Der SOL-Trade am 26.07. war nie schlimmer als −0,46 % im
Minus. Wenn viele Gewinner nie tiefer als −0,5 % fallen, ist ein Stop-Loss bei
−2,5 % vielleicht unnötig weit. **Wozu MFE gut ist:** siehe Give-Back.

## 1.5 Give-Back

**Was es ist:** Wie viel vom höchsten erreichten Gewinn du wieder hergegeben
hast, bevor der Trade zumachte.

```
Give-Back  =  MFE  −  tatsächliches Ergebnis
```

**Beispiel, SOL am 27.07. um 14:21:**

```
MFE                +2,79 %     (so weit lief er ins Plus)
Ergebnis           +1,19 %     (so ging er raus)
Give-Back           1,60 %     (das hat der Trailing-Stop liegen lassen)
```

Anders gesagt: **Wir haben 57 % des maximal möglichen Gewinns zurückgegeben.**

**Warum das die spannendste Zahl der nächsten Wochen ist:** Bei allen vier
Trailing-Exits oben liegt der Give-Back zwischen 0,62 % und 1,60 %. Wenn sich
das über 20–30 Trades bestätigt, heißt das: Unser Trailing steigt zu früh aus.
Das wäre ein direkter Hebel für R/R — größere Gewinne bei gleicher Trefferquote.

**Aber:** 6 Trades sind nichts. Vier davon sind vom selben Tag. Frühestens ab
20–30 erfassten Trades darf man daraus etwas ableiten. **Jetzt noch nicht.**

Bei Stop-Loss-Exits ist Give-Back übrigens weniger aussagekräftig — ADA zeigt
4,58 %, aber der Trade war schlicht ein Verlierer, der kurz im Plus war.

## 1.6 Gebühren

| | |
|---|---|
| Gebühr pro Seite (Median) | **0,1001 %** |
| Roundtrip (Kauf + Verkauf) | **0,200 %** |
| Median-Gewinntrade (brutto, Feld `pnl_pct`) | **+0,620 %** |
| Fee-Anteil am Rohgewinn | **32 %** |
| Gewinner unterhalb der Fee-Schwelle | **34 von 153 = 22 %** |

*Quelle: `trades_v5.json`, Felder `fee` / `amount` (50 Sells haben beide),
`pnl_pct` (185 Sells haben es).*

**Wie liest man das?** Fast ein Drittel jedes Rohgewinns geht an Binance. Und
22 % unserer „Gewinner" sind nach Gebühren de facto Nullnummern — sie stehen im
Journal als Erfolg, haben aber nichts eingebracht.

> ⚠️ **Zur Vorsicht bei dieser Zahl:** Es gibt zwei Rechenwege mit zwei
> Ergebnissen. Über das Feld `pnl_pct` (nur 185 der 414 Sells haben es, brutto)
> kommt **+0,620 %** heraus. Rechnet man den Median über alle 414 Sells netto
> aus `pnl` und Einsatz, kommt **+0,805 %** heraus. Beides ist richtig — sie
> messen Unterschiedliches auf unterschiedlichen Teilmengen. Sag immer dazu,
> welchen du meinst. (Die früher kursierende Zahl **+0,545 % ist veraltet** und
> aus der aktuellen Datei nicht mehr reproduzierbar.)

---

<a name="2-das-epochen-system"></a>
# 2. Das Epochen-System

## 2.1 Was eine Epoche ist

Eine Epoche ist **eine einzelne Änderung am Trading-Verhalten, die für einen
festen Zeitraum unangetastet läuft und danach gegen eine vorher festgelegte
Messlatte geprüft wird.**

Der Ablauf ist immer derselbe:

1. **Vorher festlegen** — was wird geändert, was ist die Messlatte, wie lange
   läuft das Fenster, wie viele Trades mindestens.
2. **Deployen und Finger weg.** Während das Fenster läuft, wird am
   Trading-Verhalten *nichts* geändert. Bugfixes und Logging sind erlaubt.
3. **Am Ende messen** — gegen die Kriterien von Schritt 1, nicht gegen neu
   erfundene.
4. **Entscheiden:** behalten, verwerfen, oder Datenlage zu dünn → verlängern.

## 2.2 Warum während einer Epoche nichts geändert wird

Wenn du mitten in der Messung etwas anfasst, weißt du hinterher nicht mehr,
welche Änderung das Ergebnis gemacht hat. Dann war das ganze Fenster umsonst
und du fängst von vorn an. Zwei Wochen weg.

Das ist keine Theorie. **E5 wurde nach einer Walk-Forward-Validierung als reine
Regime-Wette erkannt und verworfen** — die Zahlen sahen gut aus, hielten der
sauberen Prüfung aber nicht stand. Genau deshalb: erst validieren, dann glauben.

## 2.3 Wann ein Ergebnis „gut genug" ist

Ein Ergebnis zählt, wenn **alle** vorher festgelegten Kriterien erfüllt sind —
nicht, wenn eines davon gut aussieht.

Für E7 stehen die Kriterien in `e7_auswertung.py` (Zeilen 17–21), festgehalten
zum Deploy-Zeitpunkt:

| | Kriterium |
|---|---|
| **K1** | R/R im Fenster ≥ **0,54** (E6.1-Basis) |
| **K2** | Summe (E7 − alte Leiter) über alle wirksamen Fälle > 0 |
| **K3** | Keine Verschlechterung der Trailing-Exits gegenüber vorher |

Dazu das Fenster: **14 Tage / mindestens 15 Sells**, Ende **31.07.2026**.

**Beides ist längst erfüllt** — heute stehen 40 Sells im offiziellen Fenster.

## 2.4 Wo E7 gerade wirklich steht

Gerechnet mit der **offiziellen, vorregistrierten Definition** aus
`e7_auswertung.py` (Fenster ab `2026-07-17T12`, Basis 0,54):

| | |
|---|---|
| Sells im Fenster | **40** (Ziel 15 ✓) |
| Win-Rate | **75 %** |
| Ø Gewinn / Ø Verlust | +0,91 $ / −1,35 $ |
| **R/R** | **0,67** |
| **K1 (R/R ≥ 0,54)** | **✅ erfüllt** |
| Gesamt-P&L im Fenster | **+13,83 $** |

**K1 ist erfüllt.** K2 und K3 brauchen die Gegenprobe gegen Kerzendaten — die
macht `e7_auswertung.py` selbst, wenn du es am 31.07. laufen lässt:

```bash
python e7_auswertung.py
```

---

<a name="3-drei-befunde"></a>
# 3. Drei Befunde, die du kennen musst

Diese drei sind mir beim Nachrechnen für dieses Handbuch aufgefallen. Sie
ändern nichts am Bot, aber sie ändern, wie du die Zahlen liest.

## 3.1 Die E6.1-Basis ist 0,54 — nicht 0,68

In `UEBERGABE-CLAUDE-CODE.md` steht „E6.1-Basis-R/R: 0,68". **Das ist falsch.**

Die **vorregistrierte** Basis steht im Auswertungsskript selbst:

```python
E61_BASIS_RR = 0.54                  # vorregistrierte Basis
```
*(`e7_auswertung.py:37`)*

Das ist die maßgebliche Zahl, weil sie **zum Deploy-Zeitpunkt** festgeschrieben
wurde — bevor irgendjemand das Ergebnis kannte. Genau darum geht es bei
Vorregistrierung.

**Warum das entscheidend ist:** Mit der falschen Basis 0,68 hättest du am 31.07.
geschaut, 0,67 gesehen und „E7 verfehlt, verwerfen" entschieden. Mit der
richtigen Basis 0,54 ist K1 **klar erfüllt**. Zwei gegensätzliche Entscheidungen,
nur wegen einer Zahl aus einer Notiz.

## 3.2 Das Cockpit schneidet das E7-Fenster 12 Stunden zu früh an

`cockpit_server.py:112` nimmt als E7-Start:

```python
E7 = [t for t in sells if dt(t) >= datetime(2026, 7, 17, tzinfo=timezone.utc)]
```

Das ist **17.07. um 00:00**. E7 wurde aber erst **um 12:00** deployed —
`e7_auswertung.py:36` sagt `E7_DEPLOY = "2026-07-17T12"`.

In diese 12-Stunden-Lücke fallen genau **5 Verkäufe, alle Verlierer, zusammen
−8,75 $**:

| Zeit | Coin | Ausstieg | P&L |
|---|---|---|---|
| 00:37 | ETH | STOP_LOSS | −1,14 $ |
| 04:19 | BTC | TREND_EXIT | −0,64 $ |
| 04:20 | SOL | STOP_LOSS | −1,18 $ |
| 05:45 | ADA | STOP_LOSS | −5,17 $ |
| 06:16 | BTC | TREND_EXIT | −0,62 $ |

Das sind Trades **von vor E7** — sie liefen noch mit der alten Trailing-Leiter.

**Folge:** Das Cockpit zeigt E7 schlechter, als es ist.

| Rechnung | Sells | R/R | Netto |
|---|---|---|---|
| Cockpit (ab 00:00) | 45 | **0,61** | +5,09 $ |
| Offiziell (ab 12:00) | 40 | **0,67** | +13,83 $ |

**Für die Entscheidung am 31.07. gilt die offizielle Rechnung.** Das Cockpit ist
fürs tägliche Draufschauen gedacht, nicht für die Epochen-Entscheidung.

*(Nicht behoben — eine Änderung am Cockpit wäre zwar harmlos, aber wir fassen
während E7 nichts an, was die Auswertung mitten im Fenster verschiebt. Nach dem
31.07. gern.)*

## 3.3 Der „E6.1-Vergleich" im Cockpit vergleicht E7 mit sich selbst

Das Cockpit definiert das E6.1-Fenster als „alles ab 14.07." — **ohne Enddatum**.
Damit enthält E6.1 alle E7-Trades gleich mit. Man vergleicht E7 also gegen einen
Topf, in dem E7 zu zwei Dritteln drinsteckt.

Sauber getrennt sieht es so aus:

| Fenster | Sells | R/R |
|---|---|---|
| E6.1 rein (14.–16.07.) | 20 | 0,73 |
| E6.1 wie im Cockpit (ab 14.07., mit E7) | 65 | 0,62 |
| E7 offiziell (ab 17.07. 12:00) | 40 | 0,67 |

**Nimm für Entscheidungen die vorregistrierte Basis 0,54, nicht eines dieser
gleitenden Fenster.** Eine Messlatte, die mitwandert, ist keine Messlatte.

---

<a name="4-das-cockpit-im-alltag"></a>
# 4. Das Cockpit im Alltag

## 4.1 Starten

```bash
python cockpit_server.py
```

Dann im Browser: **http://localhost:8110** — stoppen mit Strg+C.

Es liest nur `trades_v5.json` und `equity_history.json`, schreibt nirgends hin,
läuft auf `127.0.0.1` (nur dein Rechner) und aktualisiert sich alle 60 Sekunden.
Es kann den Bot nicht stören, auch wenn du es dauerhaft offen lässt.

## 4.2 Wann reinschauen

| Wann | Warum |
|---|---|
| **1× am Tag**, gern abends | Reicht völlig. Häufiger führt nur dazu, dass du Rauschen für Signal hältst. |
| **Nach einem Bot-Neustart** | Kurz prüfen, ob die Trade-Zahl weiterläuft und das Equity nicht springt. |
| **Wenn Telegram auffällig viele Verluste meldet** | Nachsehen, ob es ein Muster gibt (ein Coin? ein Ausstiegsgrund?) oder normale Streuung. |
| **Am Ende eines Epochen-Fensters** | Aber für die *Entscheidung* `e7_auswertung.py` nehmen, nicht das Cockpit — siehe 3.2. |

**Nicht** ständig draufschauen. Bei 45 Trades ändert ein einzelner Verlust das
R/R sichtbar, ohne dass irgendetwas kaputt ist.

## 4.3 Worauf du achtest

**Von oben nach unten, in dieser Reihenfolge:**

1. **Stand-Zeile ganz oben.** Wenn der Zeitstempel alt ist, läuft der Bot nicht
   oder schreibt nicht mehr ins Journal. Das ist der wichtigste Blick.
2. **Warnbanner (gelb).** Wenn eins da ist, wurde die Datei gerade geschrieben —
   das Cockpit zeigt dann den letzten guten Stand. Einmal neu laden.
3. **Kapitalverlauf.** Sollte ruhig verlaufen. Ein Sprung nach unten ohne
   passende Verluste in der Liste ist ein Buchhaltungsproblem, kein Marktproblem.
4. **Averaging-Down-Tabelle.** Das ist unser bekanntester Befund, siehe 4.4.
5. **Ausstiegsgründe.** Interessant ist die Verteilung, nicht die einzelnen R/R.
6. **MFE/MAE-Kasten.** Zählt gerade hoch. Ab ~20 Trades wird er interessant.

## 4.4 Der wichtigste Kasten: Averaging Down

**Aktuelle Zahlen (alle 414 Verkäufe, aus `trades_v5.json` rekonstruiert):**

| Käufe pro Position | Anzahl | Netto | Ø Verlust | R/R |
|---|---|---|---|---|
| **1** (kein Nachkauf) | 334 | **+76,67 $** | −1,18 $ | 0,57 |
| **2** | 59 | **−68,10 $** | −3,51 $ | 0,17 |
| **3+** | 20 | **−47,49 $** | −4,28 $ | 0,11 |

**Das ist der Kern unseres Problems, in einer Tabelle.** Positionen, die wir
einmal kaufen und in Ruhe lassen, verdienen +76,67 $. Alles Minus im Gesamt-
ergebnis kommt aus nachgekauften Positionen. Und je öfter nachgekauft wurde,
desto schlimmer: Der durchschnittliche Verlust wächst von 1,18 $ auf 4,28 $.

Das ist **E8** — Nachkauf in offene Verlustpositionen abschalten. Vorgemerkt,
noch nicht umgesetzt, kommt nach E7.

**Was du hier beobachten sollst:** ob die erste Zeile positiv bleibt. Solange
„1 Kauf" im Plus steht, funktioniert der Einstieg. Das Leck ist woanders.

## 4.5 Warnsignale

| Signal | Was es bedeutet | Was tun |
|---|---|---|
| **Stand-Zeitstempel bewegt sich nicht** | Bot läuft nicht oder schreibt nicht mehr | Bot-Prozess und `system.log` prüfen |
| **Equity springt ohne passende Trades** | Buchhaltungsproblem | Nicht weiterrechnen, erst klären |
| **„1 Kauf"-Zeile wird negativ** | Der Einstieg selbst funktioniert nicht mehr | Ernst nehmen, das wäre neu |
| **Win-Rate fällt unter ~60 %** | Über mehrere Tage, nicht einen | Beobachten, nicht sofort handeln |
| **Ein Coin sammelt auffällig Minus** | So wurde XRP erkannt | Merken, am Epochen-Ende prüfen |
| **STOP_LOSS-Summe wächst schnell** | Stops zu eng oder Markt gedreht | Erst am Fenster-Ende bewerten |
| **Gelbes Banner bleibt dauerhaft** | JSON dauerhaft kaputt, nicht nur beim Schreiben | Journal prüfen, `.bak` existiert |

**Kein Warnsignal ist:** ein einzelner schlechter Tag. Am 27.07. haben zwei
Stop-Losses (ADA −3,61 $, AVAX −1,22 $) das E7-R/R im Cockpit von 0,69 auf 0,61
gedrückt. Das ist normale Streuung bei 45 Trades, kein Defekt.

## 4.6 Was das Cockpit bewusst NICHT zeigt

**Strategie-Performance.** Es gäbe eine Datei `brain_performance.json`, die
ICHIMOKU, FIBONACCI und EMA_TREND mit schönen Gewinnen zeigt. **Die ist für V6
unbrauchbar** — die Werte stammen aus einem V4-Bootstrap (`source: v4_bootstrap`,
`v6_trades_added: 0`). Sie zeigen nicht, was V6 verdient hat.

Das Cockpit blendet sie deshalb komplett aus und schreibt den Grund ins UI. Nicht
„vergessen" — bewusst weggelassen.

---

<a name="5-checkliste"></a>
# 5. Checkliste: Bevor ich eine Zahl ernst nehme

Zum Abhaken. Jeder Punkt ist uns schon mindestens einmal passiert.

### ☐ 1. Kommt die Zahl aus der Rohdatei oder aus einem Text?

Nur `data_store/trades_v5.json` zählt. Nicht aus einem Report, nicht aus einem
Handbuch, **nicht aus diesem Dokument hier**. Frisch nachrechnen.

*Passiert: Die Übergabe nennt Basis „0,68". Vorregistriert sind 0,54
(`e7_auswertung.py:37`). Hätte die E7-Entscheidung umgedreht.*

### ☐ 2. Wie alt ist die Zahl?

Zahlen altern **täglich**. Beleg aus unseren Daten:

| Stichtag | E7-Sells | E7-Netto | E7-R/R |
|---|---|---|---|
| 26.07. | 40 | +7,54 $ | **0,69** |
| 27.07. | 45 | +5,09 $ | **0,61** |

*(Cockpit-Fensterdefinition, damit beide vergleichbar sind.)*

Ein Tag, zwei Stop-Losses, 0,08 Punkte weg. Die Zahl von gestern war nicht
falsch — sie ist nur von gestern.

### ☐ 3. Ist es V6 — oder V4 mit drin?

Es gibt eine separate V4-Instanz mit anderen Coins (APT, OP, ARB, INJ, RENDER,
SUI) und anderen Strategien, in einem eigenen Projekt. **Nie vermischen.**

Konkret meiden:
- **`brain_performance.json`** — V4-Bootstrap-verseucht, für V6 wertlos
- **`v4_imported_*.json`** in `data_store/` — steht schon im Namen
- **`v4_data/`**

### ☐ 4. Welches Zeitfenster genau?

Nicht „E7", sondern **„ab 2026-07-17T12"**. 12 Stunden Unterschied bedeuten bei
uns 5 Trades und 0,06 R/R-Punkte (siehe 3.2).

Und: Überlappen sich die Fenster? Das Cockpit vergleicht E7 gegen ein E6.1, das
E7 enthält (siehe 3.3).

### ☐ 5. Wie viele Trades stecken dahinter — und wie breit ist das Intervall?

| Trades | Aussagekraft |
|---|---|
| unter 15 | nichts. Nicht diskutieren. |
| 15–50 | Hinweis. Richtung erkennbar, Höhe nicht. |
| 50–200 | brauchbar |
| über 200 | belastbar |

Immer das 95-%-Intervall danebenlegen. Wenn zwei Intervalle sich überlappen, ist
der Unterschied **nicht belegt**.

### ☐ 6. Brutto oder netto? Prozent wovon?

Unser Median-Gewinntrade ist **+0,620 %** (brutto, Feld `pnl_pct`, 185 Sells)
**oder +0,805 %** (netto, aus `pnl` gerechnet, alle 414 Sells). Beide korrekt,
verschiedene Dinge. Immer dazusagen, welchen.

*Passiert: Die Zahl „+0,545 %" kursierte und ist aus der aktuellen Datei nicht
mehr reproduzierbar.*

### ☐ 7. Steht das Feld überhaupt bei allen Trades?

Nicht jedes Feld existiert überall:

| Feld | vorhanden bei |
|---|---|
| `pnl` | 414 von 414 Sells ✅ |
| `amount` | fehlt bei 304 Einträgen (10.–22.06., altes Schema) |
| `pnl_pct` | 185 von 414 Sells |
| `fee` | 185 Sells, davon 50 zusammen mit `amount` |
| `mfe_pct` / `mae_pct` | **6** Sells (erst seit 25.07.) |

Rechnest du einen Durchschnitt über ein Feld, das nur die Hälfte hat, rechnest
du über eine andere Grundgesamtheit — ohne es zu merken. Für Werte lieber
`qty × price` nehmen, das gibt es überall.

### ☐ 8. Lese ich den richtigen Schlüssel?

In `data_store/bot_state.json` gibt es **`open_positions`** mit 5 Einträgen auf
`active: true` (ETH, SOL, ADA, XRP, BTC, Stand ~08.07.). **Die sind eine
Karteileiche.** Der Bot liest beim Neustart `open_positions_backup` — und der ist
leer.

Der Bot hat aktuell **0 offene Positionen**. Bestätigt durch `system.log`
(27.07. 14:47: „Positionen: 0.00$") und `paper_balances_backup` (nur USDC).

### ☐ 9. Bei Widersprüchen: nicht mitteln, sondern klären.

Beispiel von heute: Das Log meldet Total **371,70 $**, `equity_history.json`
sagt **468,06 $**. Differenz 96,36 $ — das entspricht fast exakt den **96,01 $**,
die der BTC-Akkumulator gesammelt hat (`btc_accumulator.json`, 27 Käufe). Der
hält BTC in einem eigenen Topf, der nicht in `_paper_balances` auftaucht.

Das ist eine **Vermutung**, kein Beweis — aber sie ist prüfbar, und genau so
soll man mit Widersprüchen umgehen. Nicht zwei Zahlen mitteln und weitermachen.

### ☐ 10. Ändere ich gerade etwas, während eine Epoche läuft?

Bis **31.07.2026** keine Trading-Verhaltensänderung. Logging, Analyse und
Dokumentation sind immer erlaubt.

---

## Anhang: Datenstand dieses Handbuchs

| | |
|---|---|
| Datei | `data_store/trades_v5.json` |
| Einträge | 918 (504 BUY, 414 SELL) |
| Zeitraum | 10.06.2026 – 27.07.2026 14:30 UTC |
| Netto realisiert | −29,65 $ |
| Equity aktuell | 468,06 $ (`equity_history.json`, 500 Messpunkte) |
| Modus | Paper, Quote-Währung USDC |
| Gehandelte Coins im Journal | ADA, AVAX, BTC, DOGE, DOT, ETH, LINK, SOL, XRP |

**Alles selbst nachrechnen:** Cockpit starten (`python cockpit_server.py`) oder
für die Epochen-Entscheidung `python e7_auswertung.py`.
