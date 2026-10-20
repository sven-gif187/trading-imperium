# Prompt für die Weiterarbeit am Live-Bot (Windows-11-Rechner)

**Angelegt 21.09.2026.** Dieser Ordner (`trading_imperium_LIVE`) wurde vom
Laptop (Windows 10) auf den Rechner (Windows 11) gezogen. Alles Folgende
ist am Laptop gemessen, nicht angenommen.

> **Diesen Text in eine neue Claude-Code-Sitzung einfügen.** Er ersetzt
> nicht `CLAUDE.md` — der lädt automatisch. Er sagt, wo wir stehen.

---

## 0. ALS ERSTES — vor allem anderen

```bash
python umzug_pruefen.py
```

Sieben Prüfungen: Betriebssystem, Python, die 20 Pakete, geplante
Aufgaben, fest eingetragene Pfade, die Claude-Haken, Daten und `.env`.

**Solange dort etwas FEHLT, den Bot nicht mit echtem Geld starten.**
Ein Bot, der halb läuft, ist gefährlicher als einer, der gar nicht
startet — der zweite fällt auf.

Zwei Dinge, die nach einem Umzug **immer** neu gemacht werden müssen:

```bash
python autostart_einrichten.py     # die geplanten Aufgaben neu anlegen
python prozess_frische.py          # läuft irgendwo noch alter Programmtext?
```

Die alten Aufgaben tragen die Benutzerkennung (SID) des Laptops. Importiert
sehen sie aus, als liefen sie, und tun nichts.

---

## 1. Wo der Bot steht

| | |
|---|---|
| Betriebsmodus | **`live`** — echtes Geld, Bybit EU |
| Konto | **23,50 $**, keine offene Position (Stand 21.09.) |
| Bisher | 10 Trades, 6 Verkäufe, **−1,58 $** realisiert |
| Deckel | 25 $ je Order, 200 $ Gesamtkapital |
| Coins | BTC/USDC, ETH/USDC, SOL/USDC |
| Letzter Trade | 17.09. 11:45 — danach war der Bot **aus**, nicht defekt |

**Achtung, eine Anzeige lügt:** Das Guthaben-Feld in der Oberfläche zeigt
**500 $**. Das ist `initial_paper_balance`, ein Einstellfeld für den
Papierhandel — `ui/main_window.py:2081` setzt es unabhängig vom Modus.
Der Bot rechnet intern mit dem echten Börsenguthaben. **Noch nicht
behoben**, siehe Punkt 4.

---

## 2. Unter welcher Strategie er handelt

Das ist Svens Fraktal-Verfahren, in drei Stufen scharfgeschaltet. Jede
Stufe hat eine eigene Epochengrenze in `config_epochs.json`.

### Einstieg — das Fraktal-Tor (Epoche L2, seit 15.09. 07:26)

`features/fraktal_tor.py`. Der Bot kauft **nur**, wenn der Preis in einer
Konfluenzzone liegt. Gemessene Einstellungen:

| Konstante | Wert | Was sie bedeutet |
|---|---|---|
| `ZEITRAHMEN` | `1h, 4h, 1d` | Wellen werden auf drei Zeitebenen gesucht |
| `MIN_ZONEN_SCORE` | `3` | eine Zone zählt erst, wenn genug Zeitebenen sie bestätigen |
| `NAEHE_PCT` | `0.35` | der Preis muss bis auf 0,35 % an der Zone liegen |
| `PUFFER_PCT` | `0.5` | halbes Prozent Luft um die Zone |
| `MIN_WELLE_PCT` | `2.0` | **Wellen unter 2 % Spanne bilden keine Zone** |
| `MIN_RUECKSETZER` | `0.5` | die Kaufzone beginnt erst ab 50 % Rücksetzer |
| `NUR_AUFWAERTSWELLEN` | `True` | **Abwärtswellen sind Widerstand, keine Unterstützung** |

Die letzten drei sind die wichtigsten. Ohne sie ließ das Tor drei von vier
Käufen durch, die genau das Problem waren, über das Sven sich beschwert
hatte: *„warum kauft er Bitcoin zu so einem hohen Kurs"*. Abwärtswellen
bilden ihre tiefen Rücksetzer knapp unter dem letzten Hoch — exakt dort
kaufte der Bot.

### Ausstieg nach oben — Fibonacci-Ziele (Epoche L3, seit 15.09. 12:23)

`features/fraktal_ziele.py`. Berechnet aus der Kaufwelle:
`Ziel = Tief + Spanne × r`

| | |
|---|---|
| `ZIELE` | `1.0, 1.272, 1.618` |
| `ZIEL_VERKAUF` | **`1.0`** — verkauft wird am Wellenhoch |
| `ANTEILE` | `1.0 → 40 %, 1.272 → 30 %, 1.618 → 30 %` |
| `TOLERANZ_PCT` | `0.05` |

**Wichtig:** `ANTEILE` ist **dokumentiert, aber nicht angeschlossen.**
Gestaffelte Teilverkäufe gehen nicht, weil der Verkaufspfad die Position
als Ganzes entfernt — und bei 23 $ Konto lägen Teilmengen unter dem
Börsenminimum von 5 $. Verkauft wird derzeit alles bei Ziel 1,0.

### Kauf-Ausführung — Warte-Aufträge (Epoche L4, seit 16.09. 23:43)

`execution/warteauftraege_live.py` + Abzweig in `execution/engine.py`.

Der Bot kauft **nicht mehr sofort zum Marktpreis**. Er legt ein Angebot
**0,10 % unter den Markt** und wartet **4 Kerzen à 15 Minuten** (1 Stunde).

- Wird es bedient: **0,10 % Maker** statt 0,25 % Taker
- Wird es nicht bedient: **der Kauf findet nicht statt**

```
Kosten je Runde    0,505 %  ->  0,355 %
gemessener Vorteil +0,161 Prozentpunkte
                   (382 echte Käufe, Gegenauslese eingerechnet,
                    Vertrauensintervall +0,077 bis +0,237)
```

**Deshalb kauft er seltener als früher. Das ist gewollt, kein Fehler.**

**Verkäufe bleiben Sofort-Aufträge.** Ein Stop-Loss als Limit-Order wird
bei einem schnellen Rutsch nicht bedient — der Kurs springt darüber hinweg.

### Was NICHT nach Svens Verfahren läuft — die dritte Hälfte

**Der Stop-Loss.** Er sitzt starr bei **−2,5 %** vom Einstand. In der
aktuellen Marktphase zieht `risk/regime_profiles.py` ihn auf **−2,0 %**
(MID_BEAR × 0,80). Svens Verfahren würde ihn **unter das Wellentief**
legen.

Einstieg und Gewinnausstieg folgen seinem Verfahren, die **Notbremse
noch nicht.** Das ist der größte offene Punkt.

### Die Ausstiegsleiter (unverändert, alt)

```
Ratsche am Höchststand | Breakeven ab +1,0 % (Puffer +0,55 %)
Trail: ab +1,2 %: ×1,0 | ab +3,0 %: ×1,3 | ab +5,0 %: ×1,7 | ab +8,0 %: ×2,2
```

---

## 3. Was an Prozessen und Aufgaben dazugekommen ist

### Geplante Aufgaben (Windows-Aufgabenplanung)

| Aufgabe | Takt | Ordner |
|---|---|---|
| **`SchattenUniversumLIVE`** | alle 15 Min | **LIVE** (neu, 16.09.) |
| **`SchattenUniversumLIVE_Anmeldung`** | bei der Anmeldung | **LIVE** (neu, 16.09.) |
| `SchattenUniversumWacht` | alle 15 Min | Papier (alt) |
| `ForschungCapture` | Zeitplan | Papier |
| `ProzessFrische` | stündlich | Papier |
| `TI6-Sammler` | täglich | Papier |

**Der Fund dahinter:** Der Punkt „Autostart braucht Adminrechte" stand
seit dem 18.08. offen. Er brauchte keine. `schtasks /sc onstart` und
`/sc onlogon` scheitern beide an „Zugriff verweigert" —
`Register-ScheduledTask -AtLogOn -User <eigener Benutzer>` geht. Der
Unterschied ist nicht der Auslöser, sondern **für wen** die Aufgabe gilt.

### Laufende Prozesse im Normalbetrieb

- `app.py` — der Bot (ein Elternprozess-Paar, sieht aus wie zwei)
- `schatten_universum.py --dauer` — der Sammler, 18 Münzen stündlich
- dazu im Papier-Ordner dieselben noch einmal, getrennt

`schatten_starter.py` unterscheidet die beiden Ordner seit dem 16.09. über
das **Arbeitsverzeichnis** (psutil). Vorher hätte er den Papier-Sammler
gesehen, „läuft bereits" gemeldet und den LIVE-Sammler nie gestartet.

### Neue Dateien seit dem 16.09.

**Handelspfad:**
- `execution/warteauftraege_live.py` — echte Limit-Orders (neu)
- `execution/engine.py` — Abzweig + `_warteauftraege_live_takt()`
- `execution/warteauftraege.py` — neue Methode `erledigen()`

**Werkzeuge:**
- `warteauftraege_scharf.py` — Epoche + Schalter in einem Zug
- `autostart_einrichten.py` — Aufgaben ohne Adminrechte
- `umzug_pruefen.py` — die sieben Prüfungen (siehe Punkt 0)
- `ordner_scan.py` — sucht Muster, die hier schon geschadet haben
- `ausstieg_messung_neu.py` — Ausstiegsregeln gegeneinander

**Tests (alle grün, zusammen 74 Prüfungen):**
- `warteauftrag_live_test.py` (31)
- `warteauftrag_anschluss_test.py` (20)
- `warteauftrag_test.py` (12) + `warteauftrag_maschine_test.py` (11)

---

## 4. Was noch zu erledigen ist

### Sofort prüfbar

1. **Warum kauft er nicht?** Seit dem 17.09. kein Trade — aber der Bot war
   aus. Erst ein paar Stunden Laufzeit abwarten, dann in **einer** Abfrage
   prüfen: Werden Warte-Aufträge gestellt (`WARTE-LIVE` im Log)? Macht das
   Fraktal-Tor zu? Erreicht der Signal-Score die Schwelle 7?

2. **Die Ausführungsquote gegenhalten.** Im Papier wurden **73,3 %**
   gemessen, aber als **Obergrenze** — dort sah der Bot nur alle 12
   Sekunden hin. Live hält die Börse den Auftrag und sieht jeden Handel,
   die Quote sollte also **höher** liegen. `python warteauftraege_scharf.py --stand`
   zeigt sie. Liegt sie deutlich darunter, stimmt etwas nicht.

3. **Die 500-$-Anzeige.** `ui/main_window.py:2081`. Reine Oberfläche,
   berührt den Handel nicht — aber sie erzeugt Misstrauen gegen richtige
   Zahlen.

### Größer, mit Messung

4. **Der strukturelle Stop-Loss** (Punkt 2, „die dritte Hälfte"). Braucht
   eine eigene Epochengrenze und vorher eine Messung. Achtung: Die
   bisherige Messung sagt, der Stop sei **nicht zu eng** — 95 % der
   Gewinner blieben flacher als 1,96 % Zwischentief, ein Stop bei 2,0 %
   wirft nur 3 von 64 Gewinnern raus. Der Hebel liegt woanders.

5. **Gestaffelte Teilverkäufe** (`ANTEILE`). Geht erst bei größerem Konto.

6. **Zweiter Telegram-Token** von BotFather. Papier- und Live-Bot laufen
   über denselben Schlüssel und stören sich bei `getUpdates`.

7. **Die alte Kostenannahme 0,32 %** steckt laut Handbuch 4.53 noch an
   mehreren Stellen. Zwei davon (`agents/btc_accumulator.py:131,167`) sind
   am 17.09. behoben — sie rechneten mit 0,1 % statt 0,25 %.

---

## 5. Die wichtigsten Zahlen

| | |
|---|---|
| Börse | Bybit EU (MiCA), Taker **0,25 %** je Seite |
| Kosten je Runde (K-BASIS) | **0,505 %** — nie aus `ccxt` holen |
| Kosten mit Warte-Auftrag (K_WARTE) | **0,355 %** |
| Trefferquote (419 Papier-Verkäufe, netto) | **59,7 %** |
| Nötig für die Null | **65,4 %** |
| Chance/Risiko | **1 : 1,89** |

**Die Diagnose in einem Satz:** Nicht die Trefferquote ist das Problem,
sondern das Verhältnis. Der Bot riskiert 1,89 $, um 1 $ zu gewinnen.

---

## 6. Zwei Fallen, die schon zugeschnappt sind

**`pnl_pct` im Handelsjournal ist BRUTTO.** Nur `pnl` in USD ist netto.
Wer über `pnl_pct` auswertet, bekommt 81,2 % Trefferquote bei nötigen
69,3 % — der Bot sähe profitabel aus. Über `pnl` sind es 59,7 % bei
nötigen 65,4 %. **Das Vorzeichen kippt.** Am Einzelfall nachgerechnet:
Kursdifferenz −2,232 %, Journal −2,200 %, tatsächlich −2,664 %.

**Ein Test, der Code liest statt ihn auszuführen, findet Fehler in der
Absicht, aber keine in der Ausführung.** Am 17.09. waren 74 Tests grün,
und trotzdem lief der Warte-Auftrags-Takt alle 12 Sekunden in
`'str' object has no attribute 'get'` — `offene()` gibt ein Dict zurück,
die Schleife lief über die Schlüssel. Der Anschluss-Test prüfte nur den
Quelltext mit Suchmustern. **Jeder neue Pfad braucht mindestens einen
Durchlauf mit echten Daten.**

---

## 7. Zurückschalten, wenn etwas schiefgeht

```bash
python warteauftraege_scharf.py --zurueck    # Warte-Aufträge aus
python autostart_einrichten.py --entfernen   # geplante Aufgaben weg
```

Beides ist reversibel. Der Bot muss danach **neu gestartet** werden — er
liest die Konfiguration beim Start.
