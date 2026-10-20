# Das Gehirn deines Bots

**Handbuch für Sven — was der Bot lernt, wo er es speichert, was er auswertet.**

Stand: 24. August 2026 · Betriebsart: Papierhandel (kein echtes Geld)

---

## Wie du dieses Handbuch liest

**Es ist nach Gegenstand geordnet, nicht nach Datum.** Wer wissen will, wie
der Schattenwächter arbeitet, schlägt an *einer* Stelle nach — und findet dort
immer den heutigen Stand, nicht die Ablagerung von acht Monaten.

Jeder Abschnitt beantwortet vier Fragen:

- **Was tut es?** — in der Gegenwart, in Alltagssprache
- **Wie benutzt du es?** — Befehl, Knopf, oder wo es von selbst läuft
- **Warum ist es so?** — kurz, mit Verweis auf die Chronik
- **Was ist offen?** — mit Befundnummer

Fachwörter stehen in Klammern daneben. Du musst sie nicht lernen — aber wenn
du sie irgendwo liest, weißt du, was gemeint ist.

### Die drei Bücher — und welches du wann aufschlägst

| Buch | Beantwortet |
|---|---|
| **`BOT-HANDBUCH`** (dieses) | *Wie arbeitet Teil X?* — zum Nachschlagen und Lernen |
| **`ENTWICKLERHANDBUCH`** | *Was ist wann passiert?* — die Chronik, nach Datum |
| **`ZAHLENBUCH`** | *Welche Zahl, aus welcher Quelle, aus wie vielen Fällen?* |

Alle drei gibt es als Markdown **und** als PDF. Die PDF werden erzeugt und
nie von Hand geändert.

### Der Aufbau

| Teil | Beantwortet | |
|---|---|---|
| **1** | **Was der Bot ist und was er kann** — Betriebsarten, Münzen, der Regel-Schalter | **fertig** |
| **2** | **Wie der Bot kauft** — fünf Stationen, fünfzehn Absagemöglichkeiten | **fertig** |
| **3** | **Wie der Bot verkauft** — die fünf Ausstiegsregeln und was sie einbringen | **fertig** |
| **4** | **Was der Handel kostet** — K-BASIS, die Doppelbuchung, die sieben zu billigen Stellen | **fertig** |
| **5** | **Was der Bot lernt** — sieben Bausteine, zwei davon entscheiden mit | **fertig** |
| **6** | **Was er beobachtet, ohne zu handeln** — Schattenlauf, Nachlauf, Chartanalyse | **fertig** |
| **7** | **Das Cockpit** — vierzehn Reiter, jeder Knopf, die zwei Browser-Seiten | **fertig** |
| **8** | **Der Werkzeugkasten — welcher Befehl bringt welches Ergebnis** | **fertig** |
| **9** | **Der Rundgang — Datei für Datei durch den Bot** | **fertig** |
| **10** | **Betrieb** — Freeze, Messfenster, Freigabekriterien, der Weg live | **fertig** |
| **11** | **Wie wir arbeiten** — das Projektgedächtnis und die Pflichtprüfungen | **fertig** |

**Alle elf Teile stehen** (fertig am 25.08.2026, Umbau abgeschlossen). Sie sind aus dem **Code
und den Messdaten** geschrieben, nicht aus älteren Abschnitten
abgeschrieben — und jede Zeilenangabe darin wird von einem Programm gegen
den echten Code geprüft:

```
python handbuch_zeilen_pruefen.py
```

**Stand: 63 von 63 Verweisen stimmen.**

### Wenn du einen Verweis auf „Handbuch 4.53" findest

Bis zum 25.08.2026 war dieses Buch nach Datum sortiert und hatte über 120
Abschnitte mit Nummern wie `4.53`. Diese Abschnitte stehen jetzt
**vollständig und wortwörtlich** in `ENTWICKLERHANDBUCH.md`, der Chronik —
dort heißen sie `ALT 4.53`. Es ist nichts gekürzt und nichts weggeworfen.

Zwei Wege führen hin:

```
python schon_bekannt.py 4.53        durchsucht alle Dokumente
```

oder eine Textsuche in `ENTWICKLERHANDBUCH.md`. Umgekehrt nennt **jeder**
Abschnitt dieses Buches am Ende, aus welchen alten er entstanden ist —
etwa *„Früher: ALT 4.11, 4.14, 4.19 …"*.

Welcher alte Abschnitt in welchen neuen Teil eingearbeitet wurde, steht in
`docs/handbuch_umbau_2026-08/UMBAU-LISTE.md`.

---


# TEIL 1 — Was der Bot ist und was er kann

**Stand: 25.08.2026.** Alle Angaben aus `data_store/config.json` und dem
Code gelesen, am Tag des Schreibens.

---

## 1.1 In einem Satz

> Der Bot beobachtet rund um die Uhr achtzehn Münzen, handelt davon drei,
> und schreibt **jede** Entscheidung mit — auch die, nicht zu handeln.

Er läuft derzeit mit **Spielgeld** (`mode = paper`). Kein echtes Geld ist im
Spiel, und das bleibt so, bis die Freigabeprüfung durchgeht (Teil 10).

---

## 1.2 Die drei Betriebsarten

| Modus | Was passiert | Geld |
|---|---|---|
| **`paper`** | Der Bot rechnet alles echt durch und bucht die Handel in ein Journal, ohne eine Order zu senden | **kein echtes** |
| `testnet` | Orders gehen an eine echte Börse, aber auf ein Übungskonto | kein echtes |
| `live` | Orders gehen an die echte Börse mit echtem Geld | **echtes** |

**Heute steht er auf `paper`** (`execution/engine.py:35`). Der Modus ist
zugleich die letzte Sicherung: Fehlt der Zugangsschlüssel, fällt der Bot
beim Start selbständig auf Papier zurück (`execution/engine.py:120`).

> **Diese Rückfallebene ist wichtig zu kennen.** Sie verhindert einen
> Fehlstart mit echtem Geld — sie kann aber auch verschleiern, dass ein
> Live-Start gar nicht stattgefunden hat. Die Freigabeprüfung nennt es
> deshalb ausdrücklich (Kriterium H5).

---

## 1.3 Was er handelt und was er beobachtet

| | |
|---|---|
| **Gehandelt** | `BTC/USDC`, `ETH/USDC`, `SOL/USDC` — **drei** |
| **Beobachtet** | 18 Münzen im Schatten-Universum (Teil 6) |
| Positionsgröße | **30 %** des Kapitals je Position |
| Höchstens gleichzeitig offen | drei |

**Deshalb ist „kein Platz" der Normalzustand.** Bei drei erlaubten
Positionen und drei gehandelten Münzen lauten die zwei häufigsten
Ablehnungsgründe „Bereits in Position" und „Max Positionen 3/3" — zusammen
über 78.000 Fälle (Teil 2, Abschnitt 2.8).

**Warum nur drei?** Die Verkleinerung von zwölf auf drei war eine
Entscheidung. Ob sie richtig war, ist eine der Fragen, die das
Schatten-Universum beantworten soll — es misst seit Wochen mit, was die
anderen fünfzehn gebracht hätten (Teil 6, Abschnitt 6.2).

---

## 1.4 Woher die Kurse kommen — und wo gehandelt werden soll

Das sind **zwei verschiedene Börsen**, und die Unterscheidung ist wichtig:

| | Börse | wofür |
|---|---|---|
| **Datenquelle** | Binance | nur Kurse, Kerzen, Orderbuch |
| **Zielbörse** | **Bybit EU** (MiCA-lizenziert) | dort soll gehandelt werden |

Daraus folgt die wichtigste Zahl des Projekts: **K-BASIS = 0,505 %** je
Runde, aus dem Bybit-EU-Taker von 0,25 % je Seite. Nie aus `ccxt` holen
(Teil 4).

> **Offener Punkt — Befund 69.** In `data_store/config.json` steht bei
> `exchange` weiterhin `"name": "Binance"`. Solange der Bot auf `paper`
> läuft, ist das folgenlos: Es wird ohnehin keine Order gesendet, und die
> Kosten kommen aus K-BASIS, nicht aus der Börsenangabe. Vor einem
> Live-Start muss es umgestellt werden.

---

## 1.5 Jede Regel hat einen Drei-Stufen-Schalter

Das ist eine der besten Bauentscheidungen des Projekts
(`core/regel_schalter.py`):

| Stufe | Was die Regel tut |
|---|---|
| **ACTIVE** | Sie entscheidet mit |
| **SHADOW** | Sie rechnet und schreibt auf, was sie **tun würde** — greift aber nicht ein |
| **OFF** | Sie läuft gar nicht und schreibt auch nichts |

**Der Stand heute** (`data_store/config.json`, `regel_modi`):

```
trend_exit             SHADOW     <- rechnet mit, verkauft nicht
baerenmarkt            ACTIVE
breakeven_sperre       ACTIVE
trailing_leiter        ACTIVE
smart_entry            ACTIVE
wiedereinstieg_sperre  ACTIVE
dca_stufen             ACTIVE
meta_voting            ACTIVE
```

**Zwei Dinge, die man dazu wissen muss:**

**Fehlt ein Eintrag oder steht Unsinn drin, gilt `ACTIVE`** — im Zweifel
das heutige Verhalten, nie ein stilles Abschalten. Deshalb warnt `LAGE.md`
ausdrücklich, wenn der ganze Block fehlt: dort steht dann **„BLOCK FEHLT —
alle fallen auf ACTIVE!"** statt einer harmlosen Liste.

**`SHADOW` ist nicht gratis.** Eine Regel auf Schatten zu stellen ist selbst
eine **Verhaltensänderung** — der Bot handelt danach anders. Der Schalter
*einzubauen* ändert nichts, ihn *umzulegen* sehr wohl. Während des
Messfensters ist beides gesperrt (Teil 10).

---

## 1.6 Der BTC-Sparplan läuft nebenher

Ein Teil der Gewinne wird in Bitcoin umgewandelt und **nicht wieder
gehandelt** — langfristiges Ansammeln statt Umschlagen.

| | |
|---|---:|
| Bestand heute | **0,00186 BTC** |
| Umwandlungen bisher | 0 |

**Warum das für die Zahlen zählt:** Der Sparplan-BTC bleibt bewusst aus der
Handelsgröße heraus (`app.py:931`) — *„er ist langfristige Akkumulation und
darf die Handelsgröße nicht aufblähen"*. Genau daraus entstand einer der
verwirrendsten Befunde des Projekts: Zwei Stellen rechnen das Gesamtkapital
verschieden, einmal mit und einmal ohne Sparplan-BTC. Der Unterschied
beträgt rund 96 $, und beide Werte landeten in derselben Datenspalte
(Befund 44).

---

## 1.7 Was der Bot bewusst **nicht** tut

Diese Bausteine sind gebaut, funktionsfähig und **abgeschaltet**. Das sind
Entscheidungen, keine Fehler — sie werden nicht „repariert".

| Baustein | Datei | Warum |
|---|---|---|
| Gitter-Handel (*Grid*) | `agents/grid_bot.py` | ein **zweiter** Einstiegspfad neben dem Direktkauf — während des Messfensters aus. Schalter: `grid_enabled` in `data_store/config.json`, steht auf `false` |
| Parameter-Optimierer | `backtest/optimizer.py` | Parameter auf alten Kursen zu suchen ist eine Wette, keine Messung |
| Termingeschäfte (*Futures*) | `execution/futures_trader.py` | nie erprobt, Hebel gehört nicht in einen ungetesteten Bot |
| Mehrere Börsen | `execution/multi_exchange.py` | eine Börse ist noch nicht bewiesen |
| TradingView-Webhook | — | stillgelegt; der freigewordene Knopf trägt jetzt das Analyse-Cockpit (Teil 7) |
| Reddit-Stimmung | — | Quelle liefert seit Wochen nichts; der Bot merkt es von selbst |

Dazu kommen die Bausteine, die **mitlaufen, ohne zu entscheiden** — KI-Modell,
Positionsgrößen-Rechner, Belohnungs-Zähler. Die sind nicht abgeschaltet,
sondern **ungemessen** (Teil 5, Abschnitt 5.6).

> **Der Unterschied ist wichtig:** Abgeschaltet heißt „wir wollen es nicht".
> Ungemessen heißt „wir wissen noch nicht, ob es hilft".

*Früher verstreut in ALT 4.5, 4.12, 4.13, 4.15, 4.20, 4.37, 4.114, 4.115.*

---

# TEIL 2 — Wie der Bot kauft

**Stand: 24.08.2026.** Alles hier ist am Code nachgelesen, nicht aus älteren
Abschnitten übernommen. Die Zahlen stammen aus `telemetrie.db`, Epoche seit
dem 15.08.

---

## 2.1 Der ganze Weg auf einen Blick

Zwischen „ein neuer Kurs kommt an" und „es wird gekauft" liegen **fünf
Stationen** und **fünfzehn Stellen, an denen abgesagt werden kann**.

```
   Ein neuer Kurs trifft ein
              |
   [1] DIE WEICHE                app.py:766  _on_market_update
       Habe ich diese Münze schon?
              |
       ja --> Verkaufsprüfung (Teil 3)          nein --> weiter
              |
   [2] DER SIGNAL-AGENT          agents/signal_agent.py
       Punkte sammeln aus ADX, Angst/Gier, Bollinger,
       RSI-Divergenz, Volumen, Ensemble, VWAP ...
       Punktzahl >= 3 ?   ---- nein ---->  Ende, kein Kandidat
              |
   [3] VIER SPERREN IM SIGNALPFAD           app.py:962-1127
       Cash-Deckel . Regime-Filter . Wiedereinstiegs-Sperre . Modus-Sperre
              |
   [4] DER TUERSTEHER            risk/engine.py:188  check()
       acht Regeln, ALLE Gruende werden protokolliert
              |
   [5] LETZTE HUERDEN            app.py:1403  _execute_approved_trade
       Klumpenrisiko . Euphorie-Bremse . Cash . (live: Spread, Volumen)
              |
       Order an execution/engine.py
```

**Verkäufe nehmen diesen Weg nicht.** Der Türsteher lässt sie ausnahmslos
durch — `risk/engine.py:196` sagt wörtlich *„SELL immer erlaubt"*. Er hält
niemanden vom Ausgang ab, nur vom Eingang.

---

## 2.2 Station 1 — die Weiche

`app.py:766`, `_on_market_update`. Sie beantwortet als Erstes eine einzige
Frage: **Habe ich in dieser Münze schon eine Position?**

| Antwort | wohin |
|---|---|
| ja | Verkaufsprüfung — siehe Teil 3 |
| nein | weiter zum Signal-Agenten |

Davor liegt noch eine Abzweigung: Wartet für diese Münze ein *Smart Entry*
(ein zurückgestellter Kaufwunsch, der auf einen besseren Kurs lauert), wird
nur dieser geprüft und die normale Analyse übersprungen.

**Was bei Löschen passiert:** Der Bot wäre blind für neue Kurse. Weder Kauf
noch Verkauf würde je ausgelöst — und zwar **ohne Fehlermeldung**. Das ist
die gefährlichste Art von Ausfall.

---

## 2.3 Station 2 — der Signal-Agent: wer stimmt ab

Der Agent vergibt **Punkte**. Jede Beobachtung, die für einen Kauf spricht,
legt welche drauf:

| Beobachtung | Punkte |
|---|---:|
| **V4-Ensemble stark** (Wert ab 0,70) | **+4** |
| **V4-Ensemble mittel** (ab 0,50) | **+3** |
| **V4-Ensemble schwach** (ab 0,30) | +2 |
| Starker Trend (ADX über 25) | +1 |
| **Extreme Angst** (Angst-und-Gier-Wert sehr tief) | **+3** |
| Extreme Angst, eine Stufe schwächer | +2 |
| Angst | +1 |
| Kurs unter dem unteren Bollinger-Band **und** RSI unter 40 | +2 |
| Bullische RSI-Abweichung (*Divergenz*) | +2 |
| Volumen-Ausschlag über dem Doppelten, RSI unter 60 | +1 |
| Ensemble stark bullisch (über 0,75) | +2 |
| Ensemble bullisch (über 0,65) | +1 |
| Über dem volumengewichteten Durchschnitt (*VWAP*) | +1 |

**Die Schwelle steht bei drei Punkten** (`agents/signal_agent.py:169`,
`min_score = 3`), und es müssen mindestens 10 $ frei sein. Darunter entsteht
gar kein Kandidat.

**Woran man die Bauart erkennt:** Der Angst-und-Gier-Wert allein kann drei
Punkte bringen — die volle Schwelle. Zwei technische Beobachtungen zusammen
schaffen das oft nicht. Der Bot ist also im Kern ein **Angstkäufer**, kein
Trendfolger. Das ist eine Entscheidung, kein Fehler — aber man sollte sie
kennen, wenn man sich über das Kaufverhalten wundert.

### Der größte Posten ist das V4-Ensemble

**Berichtigt am 25.08.2026** — in der ersten Fassung dieses Abschnitts fehlte
er. Mit **bis zu +4 Punkten** ist er der stärkste Einzelposten der ganzen
Tabelle, stärker als extreme Angst.

`agents/signal_agent.py:153` fragt acht Strategien aus dem Vorgänger-Bot ab
(`agents/v4_strategies.py`) und nimmt das beste Signal. Dessen Name wird
gleichzeitig zum **Etikett** des Handels (`agents/signal_agent.py:182`):

```python
strategy_id = v4_strategy_used or self.current_strategy
```

Deshalb steht in den angenommenen Käufen fast immer eine
V4-Ensemble-Strategie — und fast nie die, die das Strategie-Gehirn gewählt
hat. Gemessen über die ganze Datenbank:

| Etikett in angenommenen Käufen | Anzahl |
|---|---:|
| EMA_TREND | 34 |
| FIBONACCI_SUPPORT | 8 |
| MACD_CROSS | 2 |
| RSI_OVERSOLD | 1 |
| DCA_FEAR_GREED | 1 |

Wie stark jede Strategie zählt, bestimmt der **V4-Kalibrator** — und der
rechnet mit Zahlen vom 6. Mai. Das ist **Befund 76**, siehe Teil 5,
Abschnitt 5.9.

**Wie viel gekauft wird**, entscheidet sich schon hier: Grundlage ist
*Bargeld plus Wert der offenen Positionen*, davon der eingestellte
Prozentsatz. Die Rechnung steht im Protokoll:

```
[SIZING] Basis 512.40$ (Cash 210.30 + Positionen 302.10) -> 20% = 102.48$
```

---

## 2.4 Station 3 — die vier Sperren im Signalpfad

Zwischen Punktzahl und Türsteher liegen vier Prüfungen, alle in `app.py`
zwischen Zeile 962 und 1127. Jede kann den Kandidaten allein beenden.

### Der Cash-Deckel

Die Größe wird aus dem *Gesamtkapital* gerechnet — das kann mehr sein, als
frei liegt. Deshalb wird der Betrag auf 98 % des freien Bargelds gedeckelt.

**Warum der Puffer wichtig ist:** Ohne ihn liefe die Order in der
Ausführung auf „abgelehnt: Guthaben". **Zehn Ablehnungen in Folge schicken
den Bot für 15 Minuten in den Schlafmodus** (`features/safety.py`,
`RejectionCounter max_in_row=10`). Lieber kleiner kaufen als den ganzen Bot
anhalten.

### Der Regime-Filter

Blockt neue Käufe bei bestätigtem Abwärtstrend. Offene Positionen und ihr
Stop-Kurs bleiben **unberührt**. Die Schwellen stehen in
`config_regime_filter.json`, die Logik in `regime_filter.py`.

Er meldet, wie viele Bestätigungen zusammengekommen sind:

```
Regime-Filter: 2/2 Bestaetigungen [Kurs<EMA50, MTF-bearish]
```

**Hat er sich gelohnt? Teilweise beantwortet, Stand 26.08.2026.**
`schwelle_vergleich.py` rechnet nach, wie die geblockten Käufe ausgegangen
wären — über 19,5 Tage und 37.888 Prüfungen:

| Horizont | unabhängige Fenster | ohne Stop | Urteil |
|---|---:|---:|---|
| **4 h** | **117** | **−0,341 %** | **Blocken war richtig** |
| **12 h** | **39** | **−0,248 %** | **Blocken war richtig** |
| 24 h | 20 | −0,029 % | nicht entscheidbar |
| 48 h | 10 | +0,847 % | nicht entscheidbar |

**Auf kurze Sicht ist der Filter belegt sein Geld wert** — die geblockten
Käufe hätten in den ersten Stunden Verlust gebracht.

Auf 24 Stunden fehlen noch **vier unabhängige Fenster**, also rund vier Tage.
Bis zum Stichtag ist das erreicht.

> Die Spalte, auf die es ankommt, ist **„unabhängige Fenster"** — nicht die
> 37.888 Prüfungen. Der Bot prüft alle zwölf Sekunden; dieselbe Marktlage
> steht hundertfach in der Tabelle (Teil 8, Abschnitt 8.9, Fall 1).

### Die Wiedereinstiegs-Sperre

Verhindert, dass der Bot Sekunden nach einem Verkauf teurer zurückkauft.
Der Anlass steht im Code, mit Belegen:

```
07.08. 16:02:19 SELL ETH @1914.60  ->  16:02:26 BUY @1917.70   (7 Sekunden)
07.08. 20:48:26 SELL BTC @64658.86 ->  20:48:30 BUY @64732.29  (4 Sekunden, +74$)
10.08. 01:22:32 SELL BTC @64837.57 ->  01:22:39 BUY @64925.31  (7 Sekunden, +88$)
```

Die BTC-Menge sank dabei über die Rundläufe von 0,002779 auf 0,002766.
**Jeder solche Hin-und-Her-Handel (*Churn*) frisst Bestand** — genau gegen
das Ziel, Bitcoin anzusammeln.

Diese Sperre wird **zweimal** geprüft: hier und noch einmal im Trichter
(2.5). Das ist Absicht. Greift schon die erste, kommt die zweite nie zum
Zug und kostet nichts. Umgeht ein Weg die erste — etwa ein zurückgestellter
Smart-Entry —, fängt ihn die zweite.

> Bei Geld sind Gürtel und Hosenträger vertretbar.

### Die Modus-Sperre

Im „nur BTC"-Modus werden Käufe anderer Münzen abgelehnt. Offene Positionen
in gesperrten Münzen bleiben unberührt.

**Alle vier Sperren schreiben ihre Ablehnung ins Protokoll.** Das war nicht
immer so: Bis zum 06.08. starb ein vom Regime-Filter geblockter Kandidat
lautlos. SOL fehlte deshalb vollständig in der Datenbank, obwohl es
durchgehend blockiert wurde — wer nur die Zahlen las, hätte SOL für inaktiv
gehalten.

---

## 2.5 Station 4 — der Türsteher und seine acht Regeln

`risk/engine.py:188`, `check()`. **Dies ist die einzige Stelle im ganzen
Projekt, die die zentrale Risikoprüfung aufruft** — nachgeprüft:
`grep -n "risk_engine.check(" app.py` liefert genau einen Treffer,
`app.py:1206`.

| # | Regel | lehnt ab, wenn |
|---|---|---|
| 1 | Schlafmodus | nach zu vielen Ablehnungen in Folge (15 Min.) |
| 2 | Notbremse (*Kill-Switch*) | ausgelöst |
| 3 | Rückschlag-Wächter (*Drawdown*) | zu weit unter dem Höchststand |
| 4 | Höchstzahl Positionen | schon so viele offen wie erlaubt |
| 5 | Klumpengrenze (*Exposure*) | zu viel in einer Münze oder einem Sektor |
| 6 | Sperre nach Verlustserie (*Cooldown*) | diese **eine** Münze zuletzt mehrfach verloren |
| 7 | Bärenmarkt-Regel | im Bärenmarkt nur noch BTC und ETH |
| 8 | Bereits in Position | die Münze liegt schon im Bestand |

Zwei Feinheiten, die man kennen sollte:

- **Die Verlustsperre gilt je Münze, nicht global.** Drei Verluste in ETH
  sperren ETH, nicht BTC.
- **Eine hohe Punktzahl kann die Verlustsperre aufheben.** Im Protokoll
  sieht man beides: `Cooldown: 3x ETH/USDC Verlust (Score 7 < 50)` — die 7
  hätte 50 erreichen müssen.

**Alle** zutreffenden Gründe werden aufgeschrieben, nicht nur der erste.
Ohne das wäre „warum hat er nicht gekauft" nur per Forensik im 20-MB-Log zu
beantworten.

---

## 2.6 Station 5 — die letzten Hürden vor der Order

`app.py:1403`, `_execute_approved_trade`. Auch nach der Freigabe kann noch
abgesagt werden:

| Prüfung | wann sie greift |
|---|---|
| Klumpenrisiko | zu viel Gewicht in einer Münze — kann den Betrag auch nur **kürzen** statt absagen |
| Euphorie-Bremse (*NUPL*) | der Markt ist „zu gierig" — `app.py:1482`, **immer aktiv** |
| Cash-Verfügbarkeit | mehr gewollt als frei — wird auf das freie Bargeld reduziert |
| Spanne (*Spread*) | **nur im Echtbetrieb** — zu teurer Ein- und Ausstieg |
| Handelsvolumen | **nur im Echtbetrieb** — zu dünner Markt |

Dazu eine Sperre gegen Gleichzeitigkeit (*Trade-Lock*): Es kann immer nur
ein Handel gleichzeitig ausgeführt werden.

---

## 2.7 Es gibt zwei Kaufwege — und das Verhältnis hat sich gedreht

Neben dem beschriebenen Signalpfad gibt es einen zweiten, kürzeren:
**Direktkauf bei Angst** (`app.py:2700`, `if fg < 30`). Er hat eigene
Risiko-Tore und ruft die zentrale Prüfung **nicht** auf.

Am 18.08. war das der beherrschende Weg:

| Weg | Käufe damals | Anteil |
|---|---:|---:|
| Direktkauf bei Angst | 538 | **98,4 %** |
| Signalpfad | 9 | 1,6 % |

**Heute ist es umgekehrt.** In der laufenden Epoche (seit 15.08.) sind
**alle 39 angenommenen Käufe** über den Signalpfad gegangen, kein einziger
über den Direktkauf.

Der Grund steht in den Daten: Der Direktkauf braucht einen
Angst-und-Gier-Wert **unter 30**. Seit dem 15.08. lag er zwischen **29 und
73**, im Mittel bei **52,7** — und nur **125 von 186.728** Messungen fielen
überhaupt unter 30.

> Der Weg ist nicht abgeschaltet. Er wartet nur auf Angst, die nicht kommt.

**Was das fürs Lesen von Auswertungen heißt:** Wer heute die Kaufstatistik
ansieht, sieht den Signalpfad — und das ist derzeit auch der Weg, der
handelt. Kippt die Marktstimmung, kippt auch die Statistik. Beide Wege
schreiben inzwischen mit (`_dca_telemetrie`, `app.py:3646`, aufgerufen an
vier Stellen); bis zum 18.08. tat das nur der Signalpfad.

---

## 2.8 Was den Bot heute wirklich vom Kaufen abhält

Nicht Vermutung — die häufigsten Ablehnungsgründe der laufenden Epoche,
gezählt in `telemetrie.db`:

| Grund | Fälle |
|---|---:|
| Bereits in Position | 53.868 |
| Höchstzahl Positionen erreicht (3 von 3) | 24.741 |
| Regime-Filter, 2 von 2 Bestätigungen | 22.660 |
| Bärenmarkt-Regel: nur BTC und ETH | 17.358 |
| Regime-Filter, MTF-bearish | 5.872 |
| Sperre nach Verlustserie | 1.393 |

**Vorsicht bei diesen Zahlen.** Der Bot prüft alle rund 12 Sekunden. Bleibt
eine Marktlage eine Stunde bestehen, steht derselbe Grund 300-mal in der
Tabelle. Die Reihenfolge ist aussagekräftig, die Höhe **nicht**. Wer daraus
etwas ableiten will, muss auf unabhängige Fälle umrechnen — siehe Teil 8,
Abschnitt 8.9, Fall 1.

Die beiden ersten Gründe sagen dasselbe: **Der Bot ist meistens voll.** Bei
drei erlaubten Positionen und drei gehandelten Münzen ist „kein Platz" der
Normalzustand, nicht die Ausnahme.

---

## 2.9 Der stillste Fehler, den dieses Projekt hatte

Er gehört in diesen Teil, weil er genau hier passierte — und weil er zeigt,
wonach man suchen muss.

Am 06.08.2026 zeigte das Protokoll **14.986 erzeugte Kaufsignale und null
Aufrufe der Risikoprüfung**. Jeder Kandidat starb zwischen Station 2 und
Station 4.

**Die Ursache** war eine einzige überflüssige Zeile in einer fast nie
durchlaufenen Verzweigung:

```python
from core.events import DecisionIntent, Side
```

Beide Namen waren längst global importiert. Aber nach der Python-Regel
macht **eine Zuweisung irgendwo im Funktionskörper den Namen in der ganzen
Funktion lokal**. Die Zeile lag in einem Zweig, der nur bei fallendem Markt
*und* bearischer Mehrzeitrahmen-Analyse überhaupt läuft. Also war `Side`
praktisch immer unzugewiesen:

```
UnboundLocalError: cannot access local variable 'Side'
```

**Und niemand merkte es**, weil der Event-Bus die Ausnahme verschluckte.
Der Bot hielt sich für gesund.

Zwei Dinge sind daraus entstanden, beide noch aktiv:

- Ein **Wächter für den Signalpfad** (`_waechter_signalpfad`), der alle
  fünf Minuten meldet, wenn erzeugte Kandidaten die Risikoprüfung nicht
  erreichen. Er zählt beide Seiten mit — erzeugt und angekommen.
- Die Regel, **jede Ablehnung zu protokollieren**, auch die aus den
  Vorsperren.

> Ein Fehler, der laut kracht, kostet eine Stunde. Ein Fehler, der still
> ist, kostet Monate. Dieser kostete Wochen — und aufgefallen ist er nicht
> durch eine Fehlermeldung, sondern durch **zwei Zahlen, die nicht
> zueinander passten**.

*Früher verstreut in 4.7, 4.8, 4.10, 4.36, 4.52, 4.54, 4.58, 4.59, 4.70,
4.79, 4.102.*

---

# TEIL 3 — Wie der Bot verkauft

**Stand: 24.08.2026.** Alles am Code nachgelesen. Die Zahlen sind die
**39 Verkäufe der laufenden Epoche** seit dem 15.08., gezählt in
`telemetrie.db`.

> *Nachtrag 29.08.:* Es sind inzwischen **62** Verkäufe. Die Zahlen dieses
> Kapitels bleiben die von damals — sie nachträglich zu überschreiben würde
> ihre Grundlage fälschen. Der aktuelle Stand steht in 10.8 und 10.9.

---

## 3.1 Der Weg auf einen Blick

Verkauft wird nicht an einer Stelle, sondern an **zwei** — und das ist der
häufigste Grund für Verwirrung beim Lesen der Auswertungen.

```
   Ein neuer Kurs trifft ein
              |
   Habe ich diese Muenze?  ---- nein ---->  Kaufweg (Teil 2)
              |  ja
              |
   +---- Ist der Modus HOLD? ---- ja ---->  nichts tun, nie verkaufen
   |
   +---- Laeuft schon ein Verkauf? -- ja -->  nichts tun
   |
   +---- AUTO-VERTEIDIGUNG                app.py:800 ff.
   |     nur bei fallendem Markt UND bearischer Mehrzeitrahmen-Analyse
   |
   +---- SIGNAL-AGENT                     agents/signal_agent.py:229
   |     RSI ueber 80 UND Gewinn ueber 1 %  ->  Verkauf
   |
   +---- AUSSTIEGS-WAECHTER               runtime/exit_monitor.py
         alle 30 Sekunden, der Reihe nach:

           1. TREND-AUSSTIEG    (misst nur, verkauft nicht)
           2. STOP-LOSS         immer aktiv
           3. TAKE-PROFIT
           4. TRAILING-STOP     \  nur im Modus "SL",
           5. BREAKEVEN-SPERRE  /  die erste zutreffende gewinnt
              |
   Der Tuersteher laesst Verkaeufe IMMER durch   risk/engine.py:196
              |
   Order an execution/engine.py
```

> **Der Türsteher hält niemanden vom Ausgang ab.** `risk/engine.py:196` sagt
> wörtlich *„SELL immer erlaubt"*. Alle acht Kaufregeln aus Teil 2 gelten für
> Verkäufe nicht.

---

## 3.2 Die fünf Ausstiegsregeln

| Regel | greift, wenn | Zustand |
|---|---|---|
| **Trend-Ausstieg** | Mehrzeitrahmen-Analyse dreht bearisch | **misst nur** — `TREND_EXIT_SCHATTEN = True`, `runtime/exit_monitor.py:37` |
| **Stop-Loss** | Verlust erreicht die Münz-Grenze | immer aktiv |
| **Take-Profit** | Gewinn erreicht die Zielmarke | **feuert nie** — `take_profit_pct = 0.0`, und `runtime/exit_monitor.py:338` verlangt `> 0` |
| **Trailing-Stop** | Kurs fällt weit genug vom Höchststand | nur im Modus „SL" |
| **Breakeven-Sperre** | Position stand über +1 %, fällt dann unter den Puffer | nur im Modus „SL" |

Dazu der **RSI-Ausstieg** aus dem Signal-Agenten: RSI über 80 **und** Gewinn
über 1 %. Er läuft nicht über den Wächter, sondern über denselben Weg wie ein
Kaufsignal.

**Der Modus je Münze entscheidet mit.** Steht eine Position auf `HOLD`, wird
sie **nie** automatisch verkauft — weder von der Ratsche noch von der
Breakeven-Sperre. Nur `SL` schaltet die volle Leiter scharf.

---

## 3.3 Die Ratsche — wie das Nachziehen wirklich funktioniert

Der Trailing-Stop ist eine **Ratsche** (`risk/exit_rules.py`): Der Abstand
wird am **Höchststand** des Gewinns gemessen, nicht am aktuellen. Nur so
lockert er sich auf dem Rückweg nicht wieder.

```
BREAKEVEN_AB_PCT     = 1.0     ab hier darf der Trade nicht mehr ins Minus
BREAKEVEN_PUFFER_PCT = 0.35    Sicherheitsabstand fuer Kosten
TRAIL_AB_PCT         = 1.2     darunter laeuft gar kein Trailing
TREND_BONUS          = 1.3     Faktor obendrauf bei TRENDING_UP

LEITER = ( (1.2, 1.0),     ab +1,2 % Hoechststand:  Abstand x1,0
           (3.0, 1.3),     ab +3,0 %:               x1,3
           (5.0, 1.7),     ab +5,0 %:               x1,7
           (8.0, 2.2) )    ab +8,0 %:               x2,2
```

**So liest man das:** Der Grundabstand kommt aus der Konfiguration
(`trailing_stop_pct`). Je höher die Position stand, desto **großzügiger** wird
der Abstand — ein Gewinner bekommt mehr Leine, damit ein normaler Rücksetzer
ihn nicht herauswirft.

**Und hier liegt die Schwäche:** Die unterste Stufe (`1.2` → Faktor `1.0`)
deckt die **Masse aller Fälle** ab. Wer nie über +3 % kommt, bekommt nie mehr
Leine. In der laufenden Epoche stand kein einziger der 16 Trailing-Ausstiege
über +3 %.

---

## 3.4 Die Breakeven-Sperre sichert derzeit keinen Breakeven

Die Regel lautet: Stand die Position einmal über **+1 %**, wird verkauft,
sobald der Gewinn unter **+0,35 %** fällt. Der Puffer soll die Kosten decken,
damit am Ende wenigstens die Null steht.

**Er deckt sie nicht.** Der Wert wurde am 10.08. auf 0,35 % gesetzt und
rechnete gegen die damalige Kostenannahme:

```
Gebuehren   2 x 0,10 %  =  0,20 %
Slippage    2 x 0,06 %  =  0,12 %
--------------------------------
Kosten je Runde         =  0,32 %      Puffer 0,35 %  ->  0,03 % Marge
```

Seit dem Wechsel zu **Bybit EU** gilt aber **K-BASIS = 0,505 %** je Runde.
Der Puffer liegt damit **0,155 Prozentpunkte unter** den echten Kosten.

**Die Folge, gemessen an allen acht Fällen der laufenden Epoche:**

```
-0,82 $   -0,75 $   -0,83 $   -1,00 $
-0,86 $   -0,89 $   -1,07 $   -1,11 $
```

**Acht von acht im Minus.** Brutto standen alle acht im Plus (im Schnitt
+0,27 %), netto verlor jeder einzelne — im Mittel **−0,92 $**.

> Die Sperre tut genau das, was dasteht. Nur ist das, was dasteht, gegen die
> falsche Kostenzahl gerechnet.

Das ist **kein neuer Fund** — der Puffer steht auf der Liste der acht Stellen
mit der alten Kostenannahme (`ALT 4.53` in der Chronik, ausführlich in
Teil 4, Abschnitt 4.6). Neu sind nur
die acht frischen Belege. **Nicht geändert:** Eine Korrektur wäre eine
Verhaltensänderung und braucht eine Epochengrenze nach dem 18.09.

---

## 3.5 Was die 39 Verkäufe wirklich zeigen

Alle Verkäufe der laufenden Epoche, nach Ausstiegsart. `brutto` ist der
Kursgewinn, `netto` das, was nach Gebühren übrig blieb.

| Ausstiegsart | n | Summe netto | Mittel | brutto Ø | brutto im Plus | **netto im Plus** |
|---|---:|---:|---:|---:|---:|---:|
| RSI überkauft | 12 | **+24,94 $** | +2,08 $ | +1,95 % | 12/12 | **12/12** |
| Trailing-Stop | 16 | +4,79 $ | +0,30 $ | +0,94 % | 16/16 | **8/16** |
| Breakeven-Sperre | 8 | **−7,32 $** | −0,92 $ | +0,27 % | 8/8 | **0/8** |
| Stop-Loss | 3 | **−16,75 $** | −5,58 $ | −2,61 % | 0/3 | 0/3 |
| **gesamt** | **39** | **+5,66 $** | +0,15 $ | +0,84 % | 36/39 | 20/39 |

Vier Dinge stehen in dieser Tabelle:

**1. Der RSI-Ausstieg trägt das ganze Ergebnis.** Ohne ihn stünde die Epoche
bei **−19,28 $**. Er ist die einzige Regel, die zuverlässig netto liefert —
zwölf von zwölf.

**2. Der Trailing-Stop verliert die Hälfte an Reibung.** Alle 16 standen
brutto im Plus, nur 8 blieben es netto. Der durchschnittliche Bruttogewinn
von +0,94 % liegt knapp über den 0,505 % Kosten — ein Ausstieg dort ist ein
Münzwurf.

**3. Die Breakeven-Sperre ist ein sicherer Verlust** — siehe 3.4.

**4. Drei Stop-Loss kosten mehr, als 16 Trailing-Ausstiege einbringen.**
−16,75 $ gegen +4,79 $. Das Problem sitzt nicht im Ausstieg, sondern im
**Einstieg**: Eine Position, die auf −2,8 % läuft, war selten gut gekauft.

> **Brutto zu rechnen führt in die Irre.** 36 von 39 Verkäufen sahen aus wie
> Gewinne. Nach Kosten waren es 20. Jede Auswertung dieses Projekts muss
> netto rechnen — sonst misst man den Markt und nicht den Bot.

**Zur Belastbarkeit:** 39 Fälle sind für ein Gesamturteil zu wenig — die
Freigabe verlangt 100 (Kriterium A). Für die *Richtung* reicht es: Dass acht
von acht Breakeven-Verkäufen im Minus enden, ist kein Zufall, sondern
Arithmetik.

---

## 3.6 Wie viel Bewegung jeder Ausstieg verschenkt

Die andere Frage neben „hat er verdient" lautet: **Wie viel vom Höchststand
hat er liegengelassen?** Gemessen über 49 Verkäufe:

| Ausstiegsart | n | Höchststand Ø | Ausstieg Ø | **verschenkt** | Anteil gerettet |
|---|---:|---:|---:|---:|---:|
| DCA_FEAR_GREED | 6 | +1,93 % | +1,93 % | **±0,00 PP** | 100 % |
| BREAKEVEN_LOCK | 11 | +1,16 % | +0,24 % | −0,92 PP | 21 % |
| TRAILING_STOP | 23 | +3,39 % | +2,12 % | −1,26 PP | 63 % |
| **TREND_EXIT** | 4 | +0,52 % | **−1,07 %** | −1,58 PP | — |
| **STOP_LOSS** | 5 | +1,15 % | **−2,34 %** | **−3,49 PP** | — |
| **zusammen** | **49** | **+2,25 %** | **+0,96 %** | **−1,28 PP** | 43 % |

**Im Schnitt werden 1,28 Prozentpunkte liegengelassen** — bei einer
Zielgröße von 1,0 PP. Das ist eine der fünf Zielgrößen (Teil 10), und sie
ist verfehlt.

**Die zwei letzten Zeilen sind die schmerzhaften.** Beim Stop-Loss stand die
Position im Schnitt einmal bei **+1,15 %** — und ging dann mit **−2,34 %**
raus. Dreieinhalb Prozentpunkte, die einmal auf dem Tisch lagen.

> Ein Stop-Loss ist kein Ausstiegsfehler. Er ist die Quittung für einen
> Einstieg, der nie hätte stattfinden dürfen — die Position war schon einmal
> im Plus und wurde trotzdem gehalten.

**Diese Zahl trägt**, weil sie auf unabhängige Tage zusammengefasst wurde:
n = 20 statt 49 Einzelfälle.

*Früher: ALT 4.95.*

---

## 3.6 Wann Nichtstun das richtige Verhalten ist

Ein stillstehender Bot sieht aus wie ein kaputter. Meistens ist er es nicht.

| Beobachtung | was wirklich los ist |
|---|---|
| Keine Verkäufe, obwohl der Kurs schwankt | Keine Position stand je über +1,2 % — die Ratsche ist noch gar nicht scharf |
| Position läuft ins Minus, nichts passiert | Bis zur Stop-Grenze wird gehalten. Das ist die Regel, nicht ein Ausfall |
| Position steht auf `HOLD` | Wird nie automatisch verkauft. Absicht |
| Trend dreht bearisch, kein Verkauf | Der Trend-Ausstieg **misst nur** (`TREND_EXIT_SCHATTEN = True`) |

**Der Trend-Ausstieg ist bewusst im Schattenbetrieb.** Er schreibt mit, was
er getan *hätte*, damit sich später ausrechnen lässt, ob er besser gewesen
wäre — ohne dafür echtes Geld zu riskieren. Scharfschalten wäre eine
Verhaltensänderung und braucht eine Epochengrenze.

### Und er könnte für zwei der drei Münzen ohnehin nicht greifen

Der Trend-Ausstieg braucht die Mehrzeitrahmen-Analyse (*MTF*) — die Frage,
ob mehrere Zeitrahmen in dieselbe Richtung zeigen. Diese Analyse läuft aber
nur für **eine** Münze:

```
app.py:2538   for coin in coins[:1]:   # BTC als Regime-Indikator
```

Das ist Absicht — BTC dient als Marktrichtungsgeber. Die Folge ist trotzdem:
`runtime/exit_monitor.py:275` sucht die Analyse **je Münze**
(`last_signals.get(sym)`) und findet für ETH und SOL nichts.

**Der Wächter merkt das selbst** und meldet es einmalig je Münze
(`runtime/exit_monitor.py:292-299`):

```
multi_tf laeuft nur fuer coins[:1]
```

> **Bevor der Trend-Ausstieg je scharf geschaltet wird, muss das behoben
> sein** — sonst gilt eine Regel, die für zwei von drei Münzen gar nicht
> greifen kann, und niemand sieht den Unterschied.

Genau deshalb ist der Schattenbetrieb hier doppelt richtig: Er misst die
Regel *und* deckt auf, dass sie nur für ein Drittel des Bestands überhaupt
funktioniert.

---

## 3.7 Was am Ausstieg offen ist

| | Punkt | wo |
|---|---|---|
| **Befund 66** | Der Nachzieh-Stopp überlebt nur 15 bis 40 % der normalen Rücksetzer | `GEFUNDENE-PROBLEME.md` |
| **4.53** | Breakeven-Puffer rechnet mit 0,32 % statt 0,505 % | acht Stellen im Projekt |
| offen | Ist der Ausstieg zu früh? | `nachlauf.db` sammelt die Antwort — Teil 8, Abschnitt 8.5 |
| offen | Welche Regel wäre besser gewesen? | `python ausstieg_vergleich.py`, braucht Positionsverläufe |

**Alle vier warten auf den 18.09.** Solange das Messfenster läuft, wird an
keiner Ausstiegsregel gedreht — jede Änderung setzt die Zählung auf null.

*Früher verstreut in 4.30, 4.48, 4.64, 4.71, 4.83, 4.98, 4.101, 4.109, 4.110.*

---

# TEIL 4 — Was der Handel kostet

**Stand: 24.08.2026.** Alle Zahlen hier sind gemessen, nicht angenommen —
aus `schatten_universum.db` (1.102 Signale) und `telemetrie.db` (39 Verkäufe
der laufenden Epoche). Jede Behauptung ist gegen einen von Hand
nachgerechneten Einzelfall geprüft.

Dieser Teil ist der wichtigste des Buches, wenn man verstehen will, warum
ein Bot mit 92 % Bruttogewinnern trotzdem Verlust machen kann.

---

## 4.1 Die eine Zahl, die man kennen muss

```
K-BASIS  =  0,505 %  je Runde
```

Eine **Runde** ist ein vollständiger Handel: einmal kaufen, einmal
verkaufen. Alles, was ein Handel weniger einbringt als 0,505 %, ist ein
Verlust — auch wenn der Kurs gestiegen ist.

Sie steht an genau **einer** Stelle:

```
config_zielgroessen.json:55   "kosten_je_runde_pct": 0.505
config_zielgroessen.json:56   "_kosten_warum": "K-BASIS, Bybit EU Taker
                               0,25 % je Seite plus Spread.
                               Nie aus ccxt holen."
```

> **Nie aus `ccxt` holen.** Die Handelsbibliothek liefert die Gebühren, die
> die Börse *gerade meldet* — nicht die, die für unser Konto gelten. Eine
> Zahl, die sich hinter unserem Rücken ändern kann, taugt nicht als
> Rechengrundlage für Vorher-Nachher-Vergleiche.

---

## 4.2 Woraus sich die Kosten zusammensetzen

| Posten | Anteil | Wer bekommt es |
|---|---:|---|
| Handelsgebühr Kauf (*Taker*) | 0,250 % | Bybit EU |
| Handelsgebühr Verkauf | 0,250 % | Bybit EU |
| Spanne (*Spread*) | ~0,005 % | der Markt |
| **Summe je Runde** | **0,505 %** | |

**Die Spanne** ist der Abstand zwischen dem, was Käufer bieten, und dem, was
Verkäufer verlangen. Wer sofort handelt, zahlt sie — man merkt sie nicht,
weil sie im Preis steckt.

**Der Schlupf** (*Slippage*) — dass man einen anderen Kurs bekommt als
gesehen — ist in dieser Rechnung nicht getrennt aufgeführt. Er wird je Münze
gemessen und steckt in der Spanne.

---

## 4.3 Was eine Runde wirklich kostet — je Münze gemessen

Der Schatten-Sammler misst zu jedem Signal die tatsächliche Spanne mit. Aus
1.102 Signalen über 18 Münzen:

| Münze | Signale | Spanne Ø | **Kosten je Runde** | über K-BASIS |
|---|---:|---:|---:|---:|
| BTC/USDC | 140 | 0,14 bp | **0,501 %** | im Rahmen |
| ETH/USDC | 111 | 0,31 bp | **0,503 %** | im Rahmen |
| SOL/USDC | 102 | 2,04 bp | **0,520 %** | im Rahmen |
| LINK/USDC | 113 | 2,40 bp | 0,524 % | im Rahmen |
| ADA/USDC | 47 | 7,73 bp | 0,577 % | +0,07 PP |
| AVAX/USDC | 109 | 10,36 bp | 0,604 % | +0,10 PP |
| UNI/USDC | 95 | 16,58 bp | 0,666 % | +0,16 PP |
| DOT/USDC | 54 | 25,47 bp | 0,755 % | +0,25 PP |
| NEAR/USDC | 85 | 31,83 bp | **0,818 %** | **+0,31 PP** |
| OP/USDC | 1 | 40,38 bp | **0,904 %** | **+0,40 PP** |

*bp = Basispunkte, ein Hundertstel Prozent.*

**Zwei Befunde stecken in dieser Tabelle.**

**Erstens: K-BASIS ist richtig geeicht.** Für die drei tatsächlich
gehandelten Münzen (BTC, ETH, SOL) liegt der gemessene Mittelwert bei
**0,507 %** — die Annahme von 0,505 % trifft es auf zwei Tausendstel genau.
Das ist keine Selbstverständlichkeit, sondern ein Beleg, dass die Zahl
sauber hergeleitet wurde.

**Zweitens: Sie gilt nur für diese drei.** Über alle 18 Münzen liegt der
Mittelwert bei **0,607 %**. Wer das Universum erweitert, muss die Zahl
mitziehen — sonst rechnet er NEAR mit den Kosten von BTC.

> Eine Konstante ist immer nur für den Bereich gültig, in dem sie gemessen
> wurde. NEAR kostet **63 % mehr** je Runde als BTC.

---

## 4.4 Was ein Handel verdienen muss, um bei null zu landen

Das ist die Rechnung, die alles erklärt:

```
   Kurs steigt um 0,50 %   ->  netto  -0,005 %   Verlust
   Kurs steigt um 0,505 %  ->  netto   0,000 %   die Null
   Kurs steigt um 1,00 %   ->  netto  +0,495 %   Gewinn
   Kurs steigt um 2,00 %   ->  netto  +1,495 %   Gewinn
```

**Und jetzt die Wirklichkeit dazu** (aus Teil 3, den 39 Verkäufen der
laufenden Epoche):

| Ausstiegsart | Bruttogewinn Ø | netto |
|---|---:|---|
| RSI überkauft | +1,95 % | **verdient** — 12 von 12 im Plus |
| Trailing-Stop | +0,94 % | **Münzwurf** — 8 von 16 im Plus |
| Breakeven-Sperre | +0,27 % | **immer Verlust** — 0 von 8 im Plus |

Der Trailing-Stop steigt im Schnitt mit **+0,94 %** aus. Die Kosten liegen
bei 0,505 %. Es bleiben 0,44 Prozentpunkte — und die reichen nicht, sobald
ein einzelner Ausstieg etwas schwächer läuft. Genau deshalb sind es nur 8
von 16.

> **36 von 39 Verkäufen sahen brutto wie Gewinne aus. Netto waren es 20.**
> Wer brutto rechnet, misst den Markt — nicht den Bot.

### Und warum mehr Kapital das nicht heilt

Sven fragte am 17.08.: *„Heißt das, wir müssen einfach mit mehr Geld
handeln?"* Die Antwort ist **nein**, und man braucht dafür nicht einmal eine
Messung — die Rechnung genügt.

Angenommen, ein Handel bringt brutto +0,44 %:

| Einsatz | brutto +0,44 % | Kosten 0,505 % | **netto** |
|---:|---:|---:|---:|
| 100 $ | 0,44 $ | 0,51 $ | **−0,07 $** |
| 1.000 $ | 4,40 $ | 5,05 $ | **−0,65 $** |
| 10.000 $ | 44,00 $ | 50,50 $ | **−6,50 $** |
| 100.000 $ | 440,00 $ | 505,00 $ | **−65,00 $** |

**Der Grund in einem Satz:** Die Börsengebühr ist ein **Prozentsatz**. Sie
wächst genauso mit wie der Gewinn — der Abstand zwischen beiden bleibt.

> **Ein System mit negativem Erwartungswert wird durch mehr Einsatz nicht
> profitabel, sondern nur teurer.** Kapital ist ein Verstärker, kein
> Heilmittel.

*Früher: ALT 4.45.*

### Der Beweis über 772 Handel: dein Vorgänger-Bot V4

39 Fälle sind wenig. Es gibt aber einen zweiten Bestand, der viel größer ist
— der **V4-Referenzbot**, der bis heute nebenher läuft. Sein Handelsbuch hat
**772 Verkäufe** über ein Volumen von **284.955 $**.

Und er hat **kein Gebührenfeld**. Seine Zahlen sind roh.

| | | |
|---|---:|---|
| Ergebnis **brutto** | **+1.330,58 $** | sieht nach einem Gewinner aus |
| Kosten bei alter Annahme 0,32 % | −911,86 $ | → **+418,72 $**, noch im Plus |
| **Kosten bei K-BASIS 0,505 %** | **−1.439,02 $** | → **−108,44 $** |

**Das Vorzeichen kippt.** Zwischen „alter Annahme" und „richtiger
Kostenzahl" liegt der Unterschied zwischen einem Bot, der 419 $ verdient
hat, und einem, der 108 $ verloren hat.

### Und jetzt der zweite Blick, der die erste Zahl entwertet

Die +1.330,58 $ stimmen — und sie führen trotzdem in die Irre. Nach Monaten
aufgeteilt:

| Monat | Verkäufe | Summe brutto |
|---|---:|---:|
| Juli 2026 | 676 | **−479,24 $** |
| August 2026 | 96 | **+1.809,82 $** |

Und in diesen 96 Augusttagen stecken **drei** Handel vom 21.08.:

```
AVAX/USDC   +796,15 $
SOL/USDC    +607,23 $
ETH/USDC    +235,04 $
            ---------
            +1.638,42 $     aus DREI von 772 Verkaeufen
```

**Ohne diese drei stünde V4 bei −307,84 $ brutto.** Der Median eines
V4-Handels liegt bei **+1,20 $**; der größte einzelne bei +796 $.

> **Ein Gesamtergebnis, das an drei Handeln hängt, ist kein Ergebnis.** Es
> ist ein Einzelfall mit Nachkommastellen. Genau der Fehler, den die Regel
> „gegen einen von Hand nachgerechneten Einzelfall prüfen" verhindern soll —
> hier hätte ich ihn beinahe in die andere Richtung gemacht und V4 als
> Gewinner ausgewiesen.

Was **trotz** dieser Streuung trägt, ist die Trefferquote — weil sie zählt
und nicht summiert:

| | |
|---|---:|
| Trefferquote **brutto** | **75,6 %** (584 von 772) |
| Trefferquote **netto**, nach K-BASIS | **48,3 %** (373 von 772) |

**27,3 Prozentpunkte Unterschied.** Bei 772 Fällen ist das kein Zufall mehr,
sondern Arithmetik.

> Ein Bot mit drei Vierteln Gewinnern, der trotzdem Geld verliert. Das ist
> keine Theorie und kein Sonderfall — das ist der Normalfall, wenn man die
> Reibung nicht mitrechnet.

**Berichtigung:** Im alten Abschnitt `D.1` stand für V4 *„75,4 % Treffer bei
−492 $"*. Die Trefferquote stimmt fast auf den Punkt (heute 75,6 %), die
Summe nicht — nachgerechnet am 25.08.2026 über den heutigen Bestand von 772
Verkäufen sind es **−108,44 $** gegen K-BASIS. Der Bot lief seitdem weiter.

---

## 4.5 Die Doppelbuchung — eine halbe Gebühr zu viel

**Befund 42, hier in frischen Zahlen.**

Rechnet man für jeden Verkauf nach, wie viel zwischen dem Bruttogewinn und
dem gebuchten Ergebnis verschwindet, kommt heraus:

| | |
|---|---:|
| Median abgezogen je Runde | **0,758 %** |
| Mittelwert | 0,774 % |
| K-BASIS (soll) | 0,505 % |
| **zu viel** | **+0,253 Prozentpunkte** |

**0,25 % ist genau eine Handelsseite.** Es wird also eine halbe Runde zu
viel abgezogen.

**Von Hand nachgerechnet** an einem einzelnen Handel, damit die Zahl nicht
nur gut aussieht:

```
18.08. 03:33   BTC/USDC
  Volumen             103,88 $
  brutto (pnl_pct)    +0,802 $
  gebucht (pnl_usd)   +0,019 $
  abgezogen            0,783 $  =  0,754 %      <- statt 0,505 %
```

**Wo es passiert:**

```
execution/engine.py:401   result.filled_cost = amount
                          result.fee = round(fee, 4)
                          ^ die Gebuehr steckt bereits in 'amount'
                            und wird zusaetzlich gemeldet

app.py:1712               pnl = (avg_fill_price * filled_qty)
                                 - _entry_cost - (result.fee or 0)
                          ^ hier wird sie ein zweites Mal abgezogen
```

**Die Richtung ist die harmlose.** Der Bot erscheint dadurch **schlechter**,
als er ist. Eine Freischaltung wird davon nicht zu Unrecht erteilt —
höchstens zu Unrecht verweigert.

**Nicht repariert.** Die Korrektur gehört nach `execution/engine.py:401`,
**nicht** nach `app.py` — sonst repariert man den Papiermodus und macht den
Echtbetrieb kaputt. Sie wartet auf die Epochengrenze nach dem 18.09.

> **Und die Lehre aus der ersten Auswertung:** Aus dem einen auffälligen
> Handel wurde zunächst geschlossen, das Journal rechne generell zu teuer.
> Über alle 95 damals auswertbaren Verkäufe kam das **Gegenteil** heraus —
> weil 64 davon aus dem Juli stammten, als noch die alte Gebühr galt. Ein
> Einzelfall, zur Regel erklärt. Erst die Trennung nach Monat zeigte die
> zwei Welten in einer Tabelle.

---

## 4.6 Neun Stellen, eine Zahl — der heutige Stand

Am 18.08. wurden neun Stellen gefunden, die mit einer eigenen Kostenannahme
rechnen. Hier der **mechanisch geprüfte** Stand von heute:

| Stelle | Wert | Urteil |
|---|---:|---|
| `schwelle_vergleich.py:77` | 0,505 | ✅ richtig |
| `regime_filter_messung.py:55` | 0,505 | ✅ **seit dem 19.08. berichtigt** |
| `features/regime_adaptiv.py:76` | 0,32 | ⚠️ **entscheidet mit** |
| `risk/exit_rules_schatten.py:104` | 0,32 | zu billig |
| `stoploss_analyse.py:46` | 0,32 | zu billig |
| `datenexport.py:37` | 0,32 | zu billig |
| `chartanalyse_backtest.py:42` | 0,50 | nah dran, nicht K-BASIS |
| `risk/exit_rules.py:107` | 0,35 | Puffer deckt nur 0,32 |
| `backtest/ausstieg_backtest.py:59` | 0,001 je Seite | = 0,2 % je Runde |
| `app.py:3588` | `2 * 0.10` | schreibt in die Datenbank |

**Zwei sind inzwischen richtig, sieben rechnen zu billig.**

**Jede 0,32 macht ein Ergebnis um 0,185 Prozentpunkte zu schön.**

### Die Stelle, die in die Datenbank schreibt

`app.py:3588` war in der alten Liste als „Anzeige" geführt. Das stimmt nicht
ganz — sie füllt eine **Datenspalte**:

```python
def _kosten():
    gebuehr = 2 * 0.10          # 0,20 %  -- Bybit EU sind 2 x 0,25 %
    schlupf = 2 * 0.06          # 0,12 %
    spread  = <live gemessen>
    return round(gebuehr + schlupf + spread, 4)
```

Jede der über 187.000 Zeilen in `evaluations` trägt damit ein
`kosten_erwartet_pct` von mindestens **0,32** statt 0,50.

**Heute folgenlos** — nachgeprüft: kein einziges Werkzeug liest diese Spalte
derzeit aus. Aber sie liegt als Falle bereit: Wer sie später für eine
Auswertung heranzieht, bekommt ein zu schönes Ergebnis, ohne dass irgendwo
eine Warnung erscheint.

---

## 4.7 Die eine, die nicht nur misst

`features/regime_adaptiv.py` ist der **lernende Wächter**. Er ist das
Bauteil, das am 15.08. selbständig eine Schwelle verstellt und damit die
Epoche `E7` ausgelöst hat — mitten im Messfenster.

Er bewertet jede Beobachtung so (`features/regime_adaptiv.py:193`):

```python
renditen.append((spaeter / preis - 1) * 100 - KOSTEN_PCT)
```

Mit `KOSTEN_PCT = 0.32` statt 0,505. Sein Ergebnis vergleicht er dann mit
einer Schwelle von 0,5 %. **Eine Regel, die bei ihm knapp über der Schwelle
liegt, liegt in Wirklichkeit darunter.**

**Die Entscheidung vom 15.08. hält trotzdem.** Nachgerechnet: Mit der
richtigen Kostenannahme wäre die Rendite **−0,827 %** statt −0,642 %
gewesen — noch deutlicher im Minus, dieselbe Richtung.

---

## 4.8 Warum ein zu billiger Kostenwert gefährlicher ist als ein zu teurer

Das ist der Gedanke, der alle sieben Stellen zusammenbindet.

Ein zu billiger Kostenwert lässt Ergebnisse **besser** aussehen. Daraus
folgt eine Asymmetrie:

| | |
|---|---|
| Er kann **nie** zu einem falschen **Verschärfen** führen | ein schlechtes Ergebnis bleibt schlecht |
| Er kann **sehr wohl** zu einem falschen **Lockern** führen | ein knapp schlechtes Ergebnis sieht knapp gut aus |

Solange alles tief im Minus liegt, fällt das nicht auf — jede Regel wird
verschärft, und das ist zufällig richtig. **Sobald der Markt dreht und die
Werte um die Schwelle pendeln, entscheidet die Konstante mit.**

Umgekehrt bei der Doppelbuchung aus 4.5: Sie zieht **zu viel** ab, macht den
Bot also schlechter. Diese Richtung kann eine Freischaltung nur zu Unrecht
**verweigern**, nie zu Unrecht erteilen.

> **Ein einseitiger Fehler ist harmlos, bis die Werte in die Nähe der
> Schwelle kommen.** Dann entscheidet nicht die Messung, sondern die
> Konstante.

---

## 4.9 Warte-Aufträge — der Hebel, der das Vorzeichen dreht

**Gebaut am 11.09.2026. Schalter steht auf aus.**

Bis hierher kauft der Bot ausschließlich mit **Sofort-Aufträgen**
(Market-Order, Fachbegriff *Taker*): er nimmt den Preis, der gerade da ist,
und zahlt dafür 0,25 % je Seite. Ein **Warte-Auftrag** (Limit-Order,
*Maker*) legt ein Angebot etwas unter den Markt und wartet, bis der Kurs
dorthin kommt — dafür nur 0,10 % je Seite, und der Einstieg liegt
günstiger.

Beides zusammen ist der größte Hebel, den wir gemessen haben. Er wirkt auf
genau die Lücke, an der das System hängt: Der Bot liegt brutto in vier von
fünf Fällen richtig, aber die Bewegungen sind kleiner als die 0,505 %
Kosten je Runde.

### Warum die erste Messung zu gut aussah

Die Ursprungsmessung (`warteauftrag_gegenauslese.py`, 11.09.) ergab
+0,18 bis +0,44 Prozentpunkte. Zwei Prüfungen haben diese Zahl halbiert —
beide fehlten, und beide ändern das Ergebnis.

**Erstens: die Trivial-Latte fehlte.** Ein nicht ausgeführter Auftrag zählt
in der Rechnung als 0 %. Weil der Sofortkauf im Mittel **negativ** ist
(−0,485 % je Runde), ist Nichthandeln für sich genommen schon ein Gewinn.
Ein Verfahren, das nie ausführt, schlägt den Bot um fast einen halben
Prozentpunkt — ohne irgendetwas besser zu machen.

Zerlegt man den Vorteil in seine zwei Quellen, trennt sich Schein von
Substanz:

| Abstand | Vorteil | davon Nichthandeln | davon besserer Preis |
|---|---|---|---|
| 0,10 % | +0,200 | **−0,006** | +0,207 |
| 0,25 % | +0,277 | +0,036 | +0,241 |
| **0,50 %** | +0,373 | **+0,134** | +0,239 |
| 0,50 %, kurz | +0,435 | **+0,327** | +0,108 |

*(BTC, zufällige Einstiegszeitpunkte, 2.193 Gelegenheiten je Zeile)*

Bei 0,50 % Abstand kommen drei Viertel des Vorteils daher, dass der Bot
**meistens gar nicht handelt**. Das ist kein Hebel, das ist eine
Handelspause mit Zusatzschritten. Bei 0,10 % ist der Anteil null oder
leicht negativ — dort ist der Vorteil echt. **Deshalb steht der Abstand
fest auf 0,10 % und nicht höher.**

### Zweitens: gemessen wurde an den falschen Zeitpunkten

Die Ursprungsmessung nahm **zufällige** Zeitpunkte — jede achte Kerze. Der
Bot kauft aber nicht zufällig, er kauft nach einem Signal. Genau dann ist
die **Gegenauslese** (adverse selection) stärker: Ein Warte-Auftrag unter
dem Markt wird nur bedient, wenn der Kurs zu dir *fällt*. Fällt er nach
einem Kaufsignal, war das Signal vielleicht falsch.

An den **382 echten Käufen des Bots** nachgerechnet:

| | |
|---|---|
| Kurs 4 h nach dem Kauf, wenn der Auftrag **gefüllt** hätte | −0,106 % |
| Kurs 4 h nach dem Kauf, wenn er **nicht** gefüllt hätte | **+1,142 %** |
| Gegenauslese | **+1,248 Prozentpunkte** |

**Der Bot verpasst genau die Fälle, die gut laufen.** Das ist kein
Messfehler, das ist die Natur der Sache: Wer nur kauft, wenn der Kurs zu
ihm herunterkommt, bekommt überproportional die Fehlsignale.

Der Vorteil überlebt das — aber er halbiert sich.

### Die Einstellung, die daraus folgt

| gültig | Ausführungsquote | Vorteil | Vertrauensintervall |
|---|---|---|---|
| 2 Kerzen (30 min) | 66,2 % | +0,177 | +0,091 bis +0,256 |
| **4 Kerzen (1 h)** | **73,3 %** | **+0,161** | **+0,077 bis +0,237** |
| 8 Kerzen (2 h) | 78,3 % | +0,126 | +0,041 bis +0,201 |
| 12 Kerzen (3 h) | 81,9 % | +0,112 | +0,030 bis +0,186 |

Je länger der Auftrag liegt, desto mehr Aufträge werden bedient — der
Preisvorteil steigt von +0,197 auf +0,228. Aber die Gegenauslese wächst
**schneller**, von −0,020 auf −0,116. Netto ist **kürzer besser**.

Alle vier Vertrauensintervalle liegen ganz über null (20.000 Ziehungen mit
Zurücklegen). Der Unterschied zwischen 4 und 12 Kerzen, am selben Kauf
gepaart: **+0,017 bis +0,086** — enthält die Null nicht, ist also belastbar.

**Gewählt: 0,10 % Abstand, 4 Kerzen gültig.** Nicht 2 Kerzen, obwohl dort
der höchste Wert steht — 2 liegt am Rand des geprüften Bereichs, und ob es
darunter kippt, ist nicht gemessen.

> **Am 11.09. war die Einstellung zunächst auf 12 Kerzen beschlossen.** Sie
> stammte aus der Messung an zufälligen Zeitpunkten, wo die Ausführungsquote
> zählte. An den echten Kaufzeitpunkten ist sie die schwächste der vier.

### Was die Messung NICHT verspricht

**Die 73,3 % Ausführungsquote sind eine Obergrenze, keine Vorhersage.** Die
Messung sieht das *Tief* jeder 15-Minuten-Kerze. Der Bot sieht nur, was bei
seiner Abfrage gerade auf dem Ticker steht — alle 12 Sekunden, rund 75
Blicke je Kerze. Ein Tief, das dazwischen liegt und sofort wieder weg ist,
entgeht ihm.

Dasselbe steht in `docs/messungen_2026-07/BEFUNDE.md:406` über die
Vorgänger-Messung F1e: *„Die Füllquote in F1e ist eine BERÜHRUNGSQUOTE …
nur die Obergrenze."*

Was im Betrieb wirklich herauskommt, steht nach dem Scharfschalten in
`data_store/warteauftraege.json` unter `verlauf` und lässt sich gegen die
73,3 % halten.

### Wie es gebaut ist

| Stück | Datei | Was es tut |
|---|---|---|
| Warteschlange | `execution/warteauftraege.py` | hält die Aufträge, räumt nach Neustart auf |
| Abzweig | `execution/engine.py` `_execute_paper` | legt beim Kauf einen Auftrag hin statt zu kaufen |
| Takt | `app.py` `_warteauftraege_takt` | prüft alle 12 s gegen die Kurse |
| Buchung | `app.py` `_buche_ergebnis` | derselbe Weg wie ein Sofortkauf |
| Schalter | `data_store/config.json` → `warteauftraege.aktiv` | steht auf **false** |

**Vier Entscheidungen, die man kennen muss:**

**1. Verkäufe bleiben immer Sofort-Aufträge.** Ein Stop-Loss oder Notaus,
der als Warte-Auftrag liegen bleibt und nie bedient wird, wäre genau die
Art von stillem Scheitern, die am 03.08. schon einmal einen NOTAUS-NETZ-Stop
gefressen hat.

**2. Es wird kein Geld reserviert.** Der naheliegende Weg wäre, den Betrag
beim Anlegen aus der Papierkasse zu nehmen. Die Kasse liegt aber in
`bot_state.json`, die Warteschlange in einer eigenen Datei — zwei Kassen,
die bei jedem Absturz auseinanderlaufen können. Stattdessen führt die
Warteschlange nur die *Absicht*; ob das Geld reicht, wird beim Füllen
geprüft, dort wo es der Sofortkauf auch prüft.

**3. Ein eigener Status `wartet`.** Nicht `pending` — das ist der
Standardwert von `ExecutionResult` (`core/events.py:134`) und wäre von
„noch nichts passiert" nicht zu unterscheiden. Ohne den eigenen Namen hätte
`execute()` jeden hingelegten Auftrag als **abgelehnt** verbucht.

**4. Die Buchung steht in einer eigenen Methode.** `_buche_ergebnis` wurde
aus `_execute_approved_trade` herausgelöst, damit ein bedienter
Warte-Auftrag **genau denselben** Weg nimmt wie ein Sofortkauf. Ein zweiter
Buchungsweg wäre Befund 88 noch einmal — dort schrieben zwei Verkaufswege
verschiedene Felder, und es fiel drei Wochen lang niemandem auf.

### Bevor der Schalter umgelegt wird

1. **Epochengrenze setzen** (E9) in `config_epochs.json`. Einschalten ist
   eine Verhaltensänderung; ohne Grenze sind alle Vorher-Nachher-Vergleiche
   über sie hinweg wertlos.
2. `python warteauftrag_maschine_test.py` — 11 Prüfungen durch die echte
   Maschine, in beide Richtungen.
3. Nach ein paar Tagen die echte Ausführungsquote gegen die 73,3 % halten.

---

## 4.10 Die eine Stelle, an der die Kosten stehen

**Gebaut am 13.09.2026.** Bis dahin standen in **zwölf** Dateien zwölf
eigene Kostenzahlen. **Fünf davon waren falsch** — sie trugen noch die
alte Annahme 0,32 % aus der Zeit vor Bybit EU, eine sogar 0,50 % statt
0,505 %.

Das ist kein Schreibfehler, sondern eine Bauart:

> **Wer eine Zahl an zwölf Stellen pflegen muss, pflegt sie irgendwann an
> elf.** Dasselbe Muster wie beim Messfenster-Datum (Befund 90): eine
> zweite Wahrheit geht irgendwann falsch aus.

Seitdem gibt es `core/kosten.py`:

| | |
|---|---|
| `TAKER_PCT` | 0,25 % je Seite |
| `MAKER_PCT` | 0,10 % je Seite (Warte-Auftrag) |
| `SCHLUPF_PCT` | 0,005 % je Runde |
| **`K_BASIS_PCT`** | **0,505 %** — zwei Taker-Seiten plus Schlupf |
| `K_WARTE_PCT` | 0,355 % — Maker beim Kauf, Taker beim Verkauf |

Umgestellt wurden `chartanalyse_backtest.py`, `datenexport.py`,
`features/regime_adaptiv.py`, `risk/exit_rules_schatten.py` und
`stoploss_analyse.py`. **Keine davon handelt** — Schattenregel,
Auswertungen, und `regime_adaptiv` steht auf `AKTIV = False`. Deshalb war
die Umstellung freeze-verträglich.

**`risk/exit_rules.py` wurde bewusst nicht umgestellt.** Sie liegt im
Handelspfad und bestimmt Breakeven-Sperre und Trailing-Schwelle; ein
zusätzlicher Import wäre dort ein neuer Weg, auf dem der Start scheitern
kann. Ihre Zahl wird stattdessen gegengelesen.

**`python core/kosten.py`** listet alle Fundstellen und meldet
Abweichungen. Es fand eine Datei mehr, als in `OFFEN.md` stand.

### Ein Fall, in dem sich zwei Messgeräte widersprachen

Nach der Umstellung meldete `core/kosten.py` „alle stimmen", `stichtag.py`
aber „2 falsch". **Beide hatten recht und keiner hatte den Fehler:** Die
zwei Treffer standen in **Kommentaren**, die die Herleitung des alten Werts
erklären — und dort sind sie richtig.

Zwei Folgen daraus:

1. Der Kommentar in `risk/exit_rules.py` trägt jetzt ein Datum, damit die
   0,32 % nicht als gültiger Wert gelesen wird.
2. `stichtag.py` prüft nur noch ausführbaren Code. **Und es erkennt die
   neuen Schreibweisen** — vorher meldete es „nicht gefunden" bei
   *richtigem* Code, weil dort statt einer Zahl eine Rechnung steht.

> **Ein Prüfwerkzeug, das nichts findet, wo alles stimmt, ist so wertlos
> wie eines, das falsch meldet.** Beide Male lernt man, die Zeile zu
> überlesen.

---

## 4.11 Was hier offen ist

| | Punkt | wartet auf |
|---|---|---|
| **Befund 42** | Doppelbuchung, `execution/engine.py:401` | Epochengrenze nach 18.09. |
| **ALT 4.53** | sieben Stellen mit zu billiger Annahme | dieselbe Grenze |
| — | `app.py:3588` schreibt 0,32 in jede Datenzeile | dieselbe Grenze |
| — | K-BASIS gilt nur für BTC, ETH, SOL | erst nötig, wenn mehr gehandelt wird |
| **4.9** | Warte-Aufträge — ✅ scharf seit 12.09., Epoche E9 | läuft |

**Keiner dieser Punkte blockiert den Live-Weg.** Nach der Stichtags-Regel
hält ein Befund nur auf, wenn er Kapital- oder Datenverlust riskiert. Diese
vier verzerren Auswertungen — sie kosten kein Geld.

*Früher verstreut in ALT 4.11, 4.14, 4.19, 4.45, 4.50, 4.53, 4.60, 4.95, 4.108.*

---

# TEIL 5 — Was der Bot lernt

**Stand: 24.08.2026.** Am Code nachgelesen und an den Lerndateien gemessen.
Der wichtigste Satz vorweg, weil er beim Lesen alles einordnet:

> **„Lernen" heißt in diesem Bot fast überall: mitschreiben.** Von sieben
> Lernbausteinen greifen **zwei** wirklich in eine Entscheidung ein. Die
> übrigen fünf sammeln — teils seit Monaten — ohne dass jemand ihr Ergebnis
> abfragt.

---

## 5.1 Die sieben Lernbausteine auf einen Blick

| Baustein | lernt er? | **wirkt er?** | wo |
|---|---|---|---|
| **Agenten-Abstimmung** | ja, aus 25 Verkäufen | **JA** — 50/50 in den Ensemble-Wert | `models/meta_voting.py` |
| **Lernender Wächter** | ja | **JA** — verstellt seine eigene Schwelle | `features/regime_adaptiv.py` |
| Strategie-Gedächtnis | ja, 683 Trades | nur als **Etikett** — siehe 5.2 | `agents/strategy_brain.py` |
| Phasen-Gedächtnis | ja | nur als Etikett, über dasselbe Gehirn | `features/phase_memory.py` |
| Belohnungs-Zähler | ja | **nein** — niemand liest ihn | `models/rl_feedback.py` |
| Positionsgrößen-Rechner | Notizbuch | nein — abgeschaltet | `risk/adaptive_sizing.py` |
| KI-Modell (*ML*) | Notizbuch | nein — 20-%-Platz bewusst leer | `models/signal_model.py` |

**Warum das nicht schlimm ist:** Ein Baustein, der mitschreibt, ohne zu
entscheiden, ist kein toter Code — er ist eine **Messung**. Erst wenn genug
Fälle beisammen sind, lässt sich beantworten, ob sein Anschließen den Bot
besser macht. Vier fertige Bausteine sind in diesem Projekt schon verworfen
worden, weil sie schlechter waren als die einfachste Alternative.

---

## 5.2 Das Strategie-Gedächtnis — es wählt, aber es entscheidet nicht

Der Bot kennt Strategien wie „kaufe, wenn alle Angst haben"
(`DCA_FEAR_GREED`) oder „kaufe bei überverkauftem Kurs" (`RSI_OVERSOLD`).
Nach jedem Verkauf merkt er sich, ob sie gewonnen hat.

Beim Start lädt er dieses Wissen (`app.py:369-372`):

```
[BRAIN] V4-Performance geladen: 19 Strategien, 683 Trades, ... EUR
```

Und bei jedem Handelstakt wählt er daraus die passende Strategie
(`app.py:2576`). Die Wahl bringt Punkte (`agents/strategy_brain.py:170`):

```python
if   trades >= 3 and wr > 60: score += 2.0
elif trades >= 3 and wr > 40: score += 1.0
elif trades >= 3 and wr < 30: score -= 1.0
```

### Und jetzt der Teil, der oft missverstanden wird

**Diese Wahl entscheidet nicht, ob gekauft wird.** Nachgeprüft: Das
Ergebnis landet in `signal_agent.current_strategy` — und dieses Feld wird
im Signal-Agenten an genau zwei Stellen benutzt
(`agents/signal_agent.py:182` und `:237`), beide Male als **`strategy_id`
beim Erzeugen des Kaufwunsches**. Also als Beschriftung.

In die Punktzahl, die über den Kauf entscheidet (Teil 2, Abschnitt 2.3),
fließt `current_strategy` **nirgends** ein.

### Ein Etikett, das einen abgeschalteten Baustein nennt

**Gefunden am 26.08.2026.** Im Handelsjournal steht ein Kauf mit der
Strategie **`GRID_BOT`** — obwohl der Gitter-Handel abgeschaltet ist
(`grid_enabled: false`, Teil 1, Abschnitt 1.7).

Der Grid-Bot hat **nicht** gehandelt. Der Satz sagt es selbst:

```
strategy       GRID_BOT              <- das Etikett
agent_id       signal_agent          <- wer wirklich gekauft hat
schreibpfad    execute_approved_trade
reason         RSI niedrig (42) + Starker Trend (ADX 56) + Ueber VWAP
               + Orderbook Kaufdruck (+0.32)
```

**Was passiert ist:** Das V4-Ensemble hat für diesen Kauf kein Signal
geliefert. Dann greift die Rückfallebene in `agents/signal_agent.py:182`:

```python
strategy_id = v4_strategy_used or self.current_strategy
```

`current_strategy` stand gerade auf `GRID_BOT`, weil das Strategie-Gehirn
den Gitter-Handel als „passend für Seitwärtsphasen" gewählt hatte. Es weiß
nicht, dass er abgeschaltet ist — es wählt aus seiner Liste, nicht aus dem,
was läuft.

> **Ein Etikett, das niemanden steuert, kann trotzdem Schaden anrichten:**
> Wer die Auswertung liest, hält den Gitter-Handel für aktiv. Nach Teil 1,
> Abschnitt 1.7 ist er es ausdrücklich nicht.

`schon_bekannt.py` meldet `GRID_BOT` als **BEKANNT** (der Baustein ist als
stillgelegt beschrieben) — dass sein Name als Etikett auf einem echten Kauf
erscheinen kann, stand nirgends. Suche über alle Sitzungen: nichts.

**Nicht repariert.** Die Rückfallebene zu ändern berührt den Kaufpfad. Steht
in `OFFEN.md` bei Punkt 8b, wo ohnehin die zwei Strategielisten
zusammengeführt werden.

> Das Strategie-Gedächtnis klebt dem Handel ein Schild an. Es sucht ihn
> nicht aus.

Das ist eine wichtige Entlastung — und zugleich der Grund, warum die
Etiketten so verwirrend sind (5.3).

---

## 5.3 Was das Gehirn glaubt, gegen das, was V6 erlebt hat

Es gibt **zwei** Gedächtnisdateien, und der Unterschied ist der Kern dieses
Abschnitts:

| Datei | was drinsteht | Trades |
|---|---|---:|
| `brain_performance.json` | alles seit V4, gemischt | **683** |
| `brain_performance_v6.json` | nur V6, sauber ab 11.08. | **45** |

Die zweite trägt ihren Zweck im Kopf: *„Reiner V6-Zaehler ab 11.08.2026.
Enthaelt KEINE V4-Altdaten. Beeinflusst keine Handelsentscheidung."*

**Geladen wird die erste** (`models/brain_persistence.py:36`). Nebeneinander
gestellt sieht das so aus:

| Strategie | Gehirn: Trades / Quote / Punkte | nur V6: Trades / Quote / Punkte |
|---|---|---|
| DCA_FEAR_GREED | 326 · 91,4 % · **+2,0** | 6 · 100 % · +2,0 |
| EMA_TREND | 73 · 76,7 % · **+2,0** | 3 · 100 % · +2,0 |
| **ICHIMOKU** | 69 · 82,6 % · **+2,0** | **0** · — · 0,0 |
| **FIBONACCI_SUPPORT** | 61 · 77,0 % · **+2,0** | **0** · — · 0,0 |
| **STOCHRSI_REVERSAL** | 19 · 89,5 % · **+2,0** | **0** · — · 0,0 |
| **MOMENTUM_BREAKOUT** | 18 · 66,7 % · **+2,0** | **0** · — · 0,0 |
| **TSI** | 9 · 88,9 % · **+2,0** | **0** · — · 0,0 |
| BREAKEVEN_LOCK | 11 · 0 % · −1,0 | 11 · 0 % · −1,0 |

**Fünf Strategien bekommen die volle Punktzahl für Handel, den der jetzige
Bot kein einziges Mal geführt hat.** Ihre gesamte Bilanz stammt aus der Zeit
vor dem 11.08. — teils aus V4, teils aus V6 unter anderen Regeln.

Der V4-Anteil ist dabei geringer als oft angenommen: **105 von 683 Trades =
15 %**, konzentriert auf genau diese selten benutzten Strategien (ICHIMOKU
39 %, FIBONACCI 36 %, EMA_TREND 33 %).

**Und warum es trotzdem wenig ausmacht:** Weil `wr > 60` so leicht zu
erreichen ist, dass **zwölf von neunzehn** Strategien ohnehin auf dem
Höchstwert +2,0 sitzen. Eine Regel, die fast jedem die volle Punktzahl gibt,
unterscheidet nichts. Und weil die Wahl ohnehin nur ein Etikett vergibt
(5.2), bleibt der Schaden bei null.

> **Aber:** Sollte diese Wahl je an den Kaufpfad angeschlossen werden, wäre
> genau das der Moment, in dem 15 % Fremddaten anfangen zu kosten. Der
> saubere Zähler liegt bereit — er wird nur nicht geladen.

**Das Handbuch sagte bisher, die Entscheidung vom 27.07. laute, diese Zahlen
„nicht mehr anzuzeigen".** Das stimmt. In `PROJEKT-ENTSCHEIDUNGEN.md` steht
die stärkere Fassung — *„Gilt für Cockpit und Strategiewahl gleichermaßen"*.
Für die Strategiewahl trifft sie nicht zu: die alte Datei **wird** geladen.
Berichtigt am 24.08.2026.

---

## 5.4 Die Agenten-Abstimmung — der Baustein, der wirklich mitentscheidet

Mehrere kleine Programme geben unabhängig ihre Meinung ab. Nach jedem
Verkauf wird das Gewicht dessen, der recht hatte, erhöht — und das der
anderen gesenkt. Spanne: 0,3 bis 2,0.

**Der Stand nach 25 Verkäufen:**

```
regime          1,05  #####################
ensemble        1,00  ####################
fear_greed      1,00  ####################
mtf             1,00  ####################
onchain         1,00  ####################
orderbook       0,70  ##############
technical       0,30  ######      <- am Boden
vwap            0,30  ######      <- am Boden
funding         0,30  ######      <- am Boden
```

**Der Bot hat aus eigener Erfahrung die klassische Chartanalyse
heruntergestuft** — `technical` und `vwap` sitzen beide auf dem Minimum.

**Und dieses Gewicht wirkt wirklich** (`app.py:2611-2614`):

```python
ensemble_result["score"] = round(
    (typ_gewichtet_score + meta_ensemble_score) / 2, 3)
```

Eine 50/50-Mischung, und dieser Wert geht als `ensemble` in den
Signal-Agenten — wo er laut Teil 2 bis zu **+2 Punkte** von drei benötigten
bringen kann.

**Die Einschränkung gehört dazu: 25 Verkäufe sind wenig.** Bei neun
Teilnehmern und 25 Fällen ist ein Gewicht von 0,30 gegen 1,05 noch keine
belegte Rangfolge, sondern eine Tendenz. Das Messfenster braucht 100.

---

## 5.5 Der lernende Wächter — das Vorbild für alles Weitere

`features/regime_adaptiv.py` blockiert Käufe bei fallendem Markt und passt
seine eigene Strenge an. Er ist in diesem Projekt das **Muster, an dem sich
jede künftige Automatik messen lassen muss**, weil er alle fünf Sicherungen
hat:

| Sicherung | Wert |
|---|---|
| harte Grenzen | `GRENZE_MIN, GRENZE_MAX = 2, 4` |
| Mindestdatenmenge | `MIN_FAELLE = 24` **unabhängige Stunden** |
| Sperrfrist nach einer Änderung | `SPERRE_TAGE = 3` |
| Abschalter | ja |
| vollständige Protokollierung | Tabelle `regime_lernen`, 54 Zeilen |

**Am 15.08. hat er selbständig gehandelt** und `min_confirmations` von 3 auf
2 gestellt — mitten im Messfenster, was die Epoche `E7` auslöste. Die
Entscheidung war inhaltlich richtig (nachgerechnet in Teil 4, Abschnitt
4.7), der Zeitpunkt war es nicht.

**Er rechnet mit der falschen Kostenzahl** — `KOSTEN_PCT = 0.32` statt
0,505. Warum das seine bisherigen Entscheidungen nicht gedreht hat, und
warum es trotzdem gefährlich ist, steht in Teil 4, Abschnitt 4.7 und 4.8.

---

## 5.6 Was mitläuft, ohne zu entscheiden

**Der Belohnungs-Zähler** (`rl_weights.json`, 17,5 KB). Er vergibt nach
jedem Verkauf Noten:

```
DCA_FEAR_GREED  1,484      RSI_OVERSOLD  1,192
EMA_TREND       1,280      MACD_CROSS    1,100
```

Nachgeprüft: **Kein Programmteil liest diese Gewichte für eine
Entscheidung.** Sie werden geschrieben und exportiert, mehr nicht.

Zusätzlich hatte er bis zum 11.08. einen eingebauten Verfall — **5 % je
Stunde**. Bei zwei Verkäufen am Tag wurde mehr gelöscht als gelernt. Er
*konnte* nichts behalten. Der Verfall ist abgeschaltet.

**Der Positionsgrößen-Rechner** (`risk/adaptive_sizing.py`) würde in
Verlustserien kleinere Beträge einsetzen — vergrößern kann er nie, nur
verkleinern. Läuft im Notizbuch-Modus: Er rechnet aus, was er getan hätte,
und schreibt es auf.

**Das KI-Modell.** In der Formel des Ensembles ist ein **20-%-Platz für
`ml_model` reserviert — der bleibt bewusst leer.** Das Modell rechnet bei
jedem Takt mit und wird protokolliert, entscheidet aber nichts, bis
gemessen ist, ob es überhaupt Vorhersagekraft hat.

> Das ist die Dauerregel dieses Projekts: **Nichts anschließen ohne
> Messung.** Und jede Messung braucht die Trivial-Latte daneben — „immer
> nein sagen" schlägt erstaunlich viele Modelle.

---

## 5.7 Warum die Trefferquoten des Gehirns nicht lesbar sind

**Befund 58, hier mit frischen Belegen.** In einer einzigen Zahl stecken
drei Fehler.

### Die Etiketten sind vermischt

Die 45 Lernereignisse seit dem 11.08. kommen aus zwei Quellen — und die
tragen **verschiedene Arten von Namen**:

| Quelle | Ereignisse | Summe | Etikett |
|---|---:|---:|---|
| `order_filled` | 12 | **+24,94 $** | **Einstiegs**strategie (`DCA_FEAR_GREED`, `EMA_TREND` …) |
| `exit_monitor` | 33 | **−22,81 $** | **Ausstiegs**regel (`TRAILING_STOP`, `BREAKEVEN_LOCK` …) |

**Beide landen in derselben Tabelle.** Deshalb steht `DCA_FEAR_GREED` mit
91 % neben `BREAKEVEN_LOCK` mit 0 % — als wären sie vergleichbar. Sie messen
nicht dasselbe: Das eine ist „wie oft endete ein so etikettierter Handel
gut", das andere ist „wie oft hat diese Ausstiegsregel Geld gebracht".

Und die zwölf positiven Ereignisse sind genau die zwölf Verkäufe, die über
den RSI-Ausstieg gelaufen sind (Teil 3): **+24,94 $, auf den Cent gleich**.
Gutgeschrieben wurde das aber der **Einstiegs**strategie.

> Der Einstieg bekommt die Lorbeeren für einen Ausstieg, den eine ganz
> andere Regel ausgelöst hat.

### Der Maßstab ist zu großzügig

Gezählt wird `if pnl > 0` — und `pnl` ist der gebuchte Wert aus dem Journal.
Der ist je nach Zeitraum verschieden streng (Teil 4, Abschnitt 4.5): Im Juli
wurden nur 0,114 % abgezogen, seit August 0,758 %. Über 224 Verkäufe
gerechnet ergab das:

| Maßstab | Quote |
|---|---:|
| `pnl` in Dollar über null — **was das Gehirn zählt** | 76,8 % |
| `pnl_pct` minus K-BASIS über null — **die Wahrheit** | **44,6 %** |

**32,2 Prozentpunkte Unterschied.**

### Vom Ausstieg lernt es gar nichts

Gespeichert werden vier Felder: `trades`, `wins`, `total_pnl`, `win_rate`.
Kein Höchststand, kein zurückgegebener Gewinn, kein Nachlauf.

**Die Frage „bin ich zu früh raus?" kann das Gehirn nicht einmal stellen** —
die dafür nötige Zahl steht in keinem seiner Felder. Es wählt den Einstieg;
der Ausstieg liegt außerhalb seines Blickfelds. Dafür gibt es den
Positionsverlauf (Teil 8, Abschnitt 8.5).

---

## 5.8 Was bewusst nicht gelernt wird

| Was | Warum |
|---|---|
| Das KI-Modell entscheidet nicht | ungemessen — der 20-%-Platz bleibt leer, bis Vorhersagekraft belegt ist |
| Der Positionsgrößen-Rechner greift nicht ein | Notizbuch, bis der Vergleich vorliegt |
| Der Belohnungs-Zähler wird nicht gelesen | war als zweite Meinung gedacht, nie angeschlossen |
| Keine Parameter-Anpassung im Messfenster | jede Verhaltensänderung setzt die Zählung auf null |

### Fünf Bausteine, die gemessen und verworfen wurden

Sie stehen fertig da. Jeder einzelne ist **gemessen**, nicht vermutet:

| Was | Warum nicht angeschlossen |
|---|---|
| **Situations-Gedächtnis** | 66,2 % Treffer gegen **72 %** für „immer Gewinn tippen" |
| **Die KI-Modelle** | 71,4 % gegen **77,4 %** für „immer nein" — und die Trainingsdaten sind verdorben |
| **E8 Nachkauf-Stopp** | Grundannahme durch das Mess-Audit widerlegt |
| **Auto-Optimierer** | wählt die Einstellung, die auf zwölf zufälligen Tagen am besten aussah |
| **Vier Forschungs-Strategien** | Trendfolge, Funding-Extreme, Volatilitäts-Kontraktion, Makro-Overlay — alle unter strengen Kriterien verworfen |

**Der rote Faden:** Vier von fünf scheiterten daran, dass sie **nicht besser
waren als die einfachste denkbare Alternative**.

> Ein Modell mit 71,4 % Trefferquote klingt gut — bis danebensteht, dass
> „immer nein sagen" auf denselben Daten 77,4 % erreicht. **Das ist die
> Trivial-Latte, und sie ist die wichtigste Prüfung überhaupt.**

Und die Regel dahinter:

> **Nichts anschließen ohne Messung.** Ein Modell ohne Vergleich gegen die
> Trivial-Latte gilt als ungemessen — nicht als vielversprechend.

*Früher: A.4.*

---

## 5.9 Warum fünf Strategien nie handeln — und die Zahlen dahinter sind vom Mai

**Svens Frage am 25.08.2026:** *„Was auch interessant wäre — warum wir die
fünf Strategien nicht in unseren Handel mit einbeziehen."* Berechtigt. Hier
die nachgemessene Antwort. Sie hat **drei** Gründe, und der dritte ist ein
neuer Befund.

### Grund 1 — zwei Listen mit verschiedenen Namen

Es gibt **zwei** Strategielisten im Bot, und sie benutzen für dieselbe Sache
verschiedene Schlüssel:

| Strategie-Gehirn (`agents/strategy_brain.py:41`) | V4-Ensemble (`agents/v4_strategies.py:27`) |
|---|---|
| `ICHIMOKU` | **`ICHIMOKU_CLOUD`** |
| `TSI` | **`TSI_SIGNAL`** |
| `STOCHRSI_REVERSAL` | **gibt es dort nicht** |
| `FIBONACCI_SUPPORT` | `FIBONACCI_SUPPORT` ✓ |
| `MOMENTUM_BREAKOUT` | `MOMENTUM_BREAKOUT` ✓ |

Das Etikett am Handel kommt aus der **rechten** Spalte (2.3). Die Statistik
im Gehirn steht in der **linken**. Ein V6-Handel mit `ICHIMOKU_CLOUD` kann
den Zähler von `ICHIMOKU` deshalb nie erhöhen — es sind zwei verschiedene
Schubladen mit ähnlichem Aufdruck.

**Das erklärt die Null in 5.3:** ICHIMOKU steht mit 69 Trades im Gehirn und
0 im sauberen V6-Zähler. Nicht weil V6 sie nie benutzt hätte, sondern weil
V6 sie unter anderem Namen bucht.

### Grund 2 — der Kalibrator hat drei davon gesperrt

`data_store/v4_strategy_weights.json`:

| Strategie | Gewicht | Wirkung |
|---|---:|---|
| DCA_FEAR_GREED | 0,91 | gedämpft |
| FIBONACCI_SUPPORT | 0,82 | gedämpft |
| TSI_SIGNAL | 0,82 | gedämpft |
| ICHIMOKU_CLOUD | 0,73 | gedämpft |
| MACD_CROSS | 0,63 | gedämpft |
| EMA_TREND | 0,54 | gedämpft |
| MOMENTUM_BREAKOUT | 0,44 | gedämpft |
| RSI_OVERSOLD | 0,43 | gedämpft |
| **STOCHRSI_REVERSAL** | **0,00** | **gesperrt** |
| BOLLINGER_BOUNCE | 0,00 | gesperrt |
| RSI_DIVERGENCE | 0,00 | gesperrt |

`agents/v4_strategies.py:285` wirft jede Strategie mit Gewicht 0,0 sofort
raus. `STOCHRSI_REVERSAL` **kann** also gar nicht handeln.

Die anderen sind nicht gesperrt, nur gedämpft — sie werden bei jedem Takt
geprüft und verlieren den Wettbewerb um das beste Signal.

### Grund 3 — die Gewichte stammen vom 6. Mai (Befund 76)

**SICHER.** Der Kalibrator rechnet bei jedem Start neu — aber aus einer
Datei, die seit Monaten stillsteht:

```
app.py:352   V4Calibrator.load('v4_data/strategy_stats.json')

  v4_data/strategy_stats.json         6. Mai 2026, 11:42     <- Quelle
  v4_referenz/strategy_stats.json    24. August 2026, 18:45  <- der laufende V4-Bot
```

**Der V4-Referenzbot läuft die ganze Zeit mit und schreibt frische
Statistiken — in einen anderen Ordner.** Der Kalibrator sieht sie nie.

Das zählt, weil der Kalibrator entscheidet, wie stark der größte Posten der
Kaufwertung wiegt: die bis zu **+4 Punkte** aus dem V4-Ensemble (2.3).

**Pflichtprüfung:** `schon_bekannt.py` meldet für `v4_data/strategy_stats.json`,
`app.py:352` und `V4Calibrator.load` **NEU**. Suche über alle Sitzungen:
nichts.

**Nicht repariert.** Die Quelle umzustellen würde die Gewichte ändern und
damit das Kaufverhalten — eine Verhaltensänderung, die eine Epochengrenze
braucht. Sie steht in `OFFEN.md` Gruppe C.

> **Der Bot lernt aus einem Vorgänger, der weitergelernt hat — nur hört er
> ihm seit dem 6. Mai nicht mehr zu.**

### Und was hätten die fünf wirklich eingebracht?

**Nachgerechnet am 25.08.2026** an **779 echten Verkäufen** des
V4-Referenzbots — mit den **gemessenen Kosten je Münze** (Teil 4,
Abschnitt 4.3), nicht mit einer Pauschale.

| Strategie | Gewicht (6. Mai) | n | **netto** | Median je Handel | Trefferquote netto |
|---|---:|---:|---:|---:|---:|
| FIBONACCI_SUPPORT | 0,82 | 80 | **+753,78 $** | **+2,00 $** | 72,5 % |
| MOMENTUM_BREAKOUT | 0,44 | 47 | +420,87 $ | **−0,03 $** | 48,9 % |
| RSI_OVERSOLD | 0,43 | 97 | −57,86 $ | +0,33 $ | 59,8 % |
| STOCHRSI_REVERSAL | **0,00** | 40 | −89,46 $ | −0,51 $ | 15,0 % |
| DCA_FEAR_GREED | 0,91 | 32 | −141,75 $ | +2,24 $ | 59,4 % |
| **EMA_TREND** | 0,54 | 167 | **−545,35 $** | −0,58 $ | 35,9 % |
| **ICHIMOKU_CLOUD** | 0,73 | **267** | **−642,57 $** | −0,42 $ | 33,0 % |
| *zusammen* | | *779* | *−602,63 $* | | |

*Unter 30 Fällen und damit nicht entscheidbar: TSI_SIGNAL (11),
MACD_CROSS (20), RSI_DIVERGENCE (10), MULTI_SIGNAL (7).*

**Die Antwort auf „warum nehmen wir die fünf nicht dazu" lautet: weil vier
davon nachweislich Geld verlieren — und die fünfte nur einmal Glück
hatte.**

### Der Median entscheidet, nicht die Summe

`MOMENTUM_BREAKOUT` sieht mit +420,87 $ nach einem Kandidaten aus. Nimmt man
ihr den **größten einzelnen** Handel weg, bleibt **−167,70 $**:

```
21.08.  SOL/USDC   MOMENTUM_BREAKOUT   +607,23 $     <- dieser eine
```

Ihr Median je Handel liegt bei **−0,03 $**. Der typische Handel dieser
Strategie verdient **nichts**.

Dasselbe gilt abgeschwächt für `FIBONACCI_SUPPORT` (+753,78 → −9,21 $ ohne
ihren größten, AVAX +796,15 $ am selben Tag). **Der Unterschied:** Ihr
Median liegt bei **+2,00 $** und ihre Trefferquote bei 72,5 % — der typische
Handel verdient. Nur die *Summe* hängt am Ausreißer, nicht die Regel.

> **Eine Summe sagt, was passiert ist. Ein Median sagt, was üblich ist.**
> Bei einer Strategie will man das Zweite wissen.

### Die Gewichte passen nicht mehr zur Wirklichkeit

Das ist die gemessene Folge von Befund 76:

| Rangfolge | 1. | 2. | 3. | 4. | 5. |
|---|---|---|---|---|---|
| **nach Gewicht** | DCA_FEAR_GREED | FIBONACCI | TSI_SIGNAL | ICHIMOKU | MACD_CROSS |
| **nach Ertrag** | FIBONACCI | MOMENTUM | RSI_OVERSOLD | MACD_CROSS | TSI_SIGNAL |

**Von acht nicht gesperrten Strategien steht keine einzige am selben
Platz.**

Am deutlichsten: `ICHIMOKU_CLOUD` trägt Gewicht **0,73** und hat über
267 Handel **642 $ verloren** — mehr als jede andere. `MOMENTUM_BREAKOUT`
trägt **0,44** und liegt im Ertrag auf Platz zwei.

**Was dagegen stimmt: die Sperren.** Alle drei auf 0,00 gesetzten Strategien
verlieren tatsächlich Geld (`STOCHRSI_REVERSAL` −89 $ bei 15 % Trefferquote,
`RSI_DIVERGENCE` −42 $, `MULTI_SIGNAL` −39 $). Der Kalibrator sperrt richtig
— er gewichtet nur falsch.

**Empfehlung, nach dem Stichtag:** Nicht die fünf dazunehmen, sondern die
zwei großen Verlierer heruntergewichten. `ICHIMOKU_CLOUD` und `EMA_TREND`
stehen für **434 von 779 Verkäufen** und zusammen für **−1.188 $**. Das ist
der Hebel, nicht die ungenutzten Strategien. Steht in `OFFEN.md` als
Punkt 8a.

**Umfang der Prüfung:** V4-Journal vollständig gelesen (2.947 Sätze, davon
779 Verkäufe mit Menge und Preis), Kosten für 17 der 18 Münzen gemessen, für
`ARB/USDC` mit K-BASIS gerechnet. Nicht geprüft: ob V4s Einstiegsregeln
denen von V6 gleichen — die Strategienamen sind dieselben, der Code ist es
nicht zwingend.

---

---

## 5.10 Was die stillgelegten Bausteine wirklich taugen

**Svens Auftrag vom 25.08.2026:** *„Für die verfügbaren Bausteine, die noch
nicht verwendet werden — überlegen und nachrechnen, für was wir sie nutzen
können."* Hier die Antwort, Baustein für Baustein.

### Die Kurzfassung

| Baustein | messbar? | Ergebnis |
|---|---|---|
| **Schatten-Ausstiegsregeln** | **ja** | ausgewertet — Teil 6, Abschnitt 6.3 |
| **KI-Modell** | **ja, seit 26.08.** | **kein Vorsprung** — 30,8 % gegen 30,8 % |
| **Positionsgrößen-Rechner** | **nein** | kein Ergebnisfeld — braucht den Schließzeitpunkt |
| **Belohnungs-Zähler** | **nein** | kein Bezug zwischen Note und Ausgang |
| **Strategie-Gedächtnis** | ja, indirekt | wirkt nur als Etikett — 5.2 |
| **Phasen-Gedächtnis** | ja, indirekt | wirkt über dasselbe Gehirn, also auch nur als Etikett |

**Drei von sechs sind jetzt auswertbar.** Bis zum 26.08. waren es zwei: Die
Notizbücher schrieben auf, was eine Regel getan **hätte** — aber nicht, wie
es **ausging**. `schatten_regeln` hatte 2.084 Zeilen und **null** gefüllte
Ergebnisfelder (Befund 77). Seit dem 26.08. hängen sie am Nachlauf-System
und bekommen ihre Folgekurse automatisch.

### Das KI-Modell, jetzt exakt nachgerechnet

**Seit dem 26.08. gibt es die Ergebnisse wirklich** — die Notizbücher hängen
am Nachlauf-System (Befund 77, behoben). **1.946 von 2.084** Notizen tragen
ihren 24-Stunden-Kurs, keine einzige ging verloren.

Das Modell hat in diesen Fällen **VERKAUF** gesagt. Es hat recht, wenn der
Kurs danach fällt. Gegen die **Trivial-Latte** — dieselben Münzen, derselbe
Zeitraum, ohne jedes Modell:

| | `ml_model` | `ensemble_technical` | Trivial-Latte |
|---|---:|---:|---:|
| Fälle | 972 | 974 | 30.621 |
| Kurs 24 h später, **Median** | **+0,635 %** | +0,623 % | **+1,892 %** |
| Mittelwert | +2,040 % | +2,056 % | +2,837 % |
| danach **gefallen** (Modell hätte recht) | **30,8 %** | 30,9 % | **30,8 %** |

### Das Urteil: kein Vorsprung bei der Richtung

**30,8 % gegen 30,8 %.** Das Modell trifft die Richtung exakt so oft wie ein
Würfel, der gar nichts weiß. Es gibt keinen Vorsprung — nicht einen halben
Prozentpunkt.

**Was dagegen bleibt: es findet schwächere Momente.** Der Median nach seinen
Verkaufssignalen liegt bei **+0,635 %** gegen **+1,892 %** in der
Grundgesamtheit — rund **1,26 Prozentpunkte niedriger**. Das Modell sagt
nicht, *ob* es runtergeht, aber es markiert Zeitpunkte, nach denen es
**weniger stark hochgeht**.

Für ein reines Verkaufssignal ist das zu wenig. Als Dämpfer neben anderen
Quellen wäre es einen zweiten Blick wert — aber erst nach dem Stichtag.

> **`ml_model` und `ensemble_technical` sind praktisch nicht zu
> unterscheiden** (30,8 gegen 30,9 %, Mediane 0,635 gegen 0,623). Zwei
> Notizbücher, die dasselbe sagen, sind eines zu viel.

### Und eine Lehre über das Messen selbst

Bevor die Ergebnisse fest verknüpft waren, hatte ich sie **behelfsweise**
zugeordnet — über Münze und Zeit mit zwei Stunden Toleranz. Das ergab:

```
KI-Modell 25,4 %  gegen  Trivial-Latte 23,9 %   ->  Vorsprung +1,4 Punkte
```

**Diesen Vorsprung gibt es nicht.** Mit exakter Zuordnung sind es 30,8 gegen
30,8. Die Toleranz von zwei Stunden hatte jeder Notiz einen fremden
Folgekurs untergeschoben und daraus einen Vorteil erzeugt, der reines
Zuordnungsrauschen war.

> **Eine Zuordnung über „ungefähr dieselbe Zeit" ist keine Zuordnung.** Sie
> sieht aus wie eine Messung und liefert eine Zahl mit Nachkommastellen —
> und diese Zahl kann das Vorzeichen einer Entscheidung drehen.

### Was jeder Baustein bräuchte, um beurteilbar zu werden

| Baustein | was fehlt | Aufwand |
|---|---|---|
| ~~KI-Modell~~ | **erledigt 26.08.** — hängt am Nachlauf, 1.946 Ergebnisse | — |
| Positionsgrößen-Rechner | Ergebnisfeld gibt es **gar nicht** — Spalte anlegen | reines Aufschreiben |
| Belohnungs-Zähler | Bezug zwischen Note und späterem Ausgang | Entwurfsfrage |
| Strategie-Gedächtnis | die zwei Strategielisten zusammenführen (`OFFEN.md` 8b) | Verhaltensänderung |

**Alle vier sind freeze-verträglich bis auf den letzten.** Sie warten nicht
auf den Stichtag, sondern auf eine Entscheidung: **wann gilt der Ausgang als
festgestellt** — nach einer Stunde, nach 24 Stunden, oder beim Schließen der
Position? Das ist keine technische, sondern eine Messfrage, und sie gehört
Sven.

*Auftrag vom 25.08.2026, `OFFEN.md` Gruppe A.*

---

## 5.11 Was die Umstellung des Kalibrators bewirken würde

**Vormessung vom 26.08.2026** zu `OFFEN.md` Gruppe C, Punkte 8a und 8b.
Beide ändern Verhalten und dürfen erst nach dem Stichtag ausgeführt werden —
aber beide verlangen vorher eine Rechnung. Hier ist sie.

Die Gewichtsformel aus `models/v4_calibrator.py:61` wurde **exakt
nachgebaut** und mit den heutigen Zahlen des V4-Referenzbots gefüttert.

### Fünf von acht Strategien würden gesperrt

| Strategie | Gewicht 6. Mai | mit heutigen Zahlen | |
|---|---:|---:|---|
| DCA_FEAR_GREED | 0,91 | **0,00** | **gesperrt** |
| FIBONACCI_SUPPORT | 0,82 | 0,88 | bleibt |
| TSI_SIGNAL | 0,82 | **0,00** | **gesperrt** |
| ICHIMOKU_CLOUD | 0,73 | **0,00** | **gesperrt** |
| MACD_CROSS | 0,63 | **0,00** | **gesperrt** |
| EMA_TREND | 0,54 | **0,00** | **gesperrt** |
| MOMENTUM_BREAKOUT | 0,44 | 0,50 | bleibt |
| RSI_OVERSOLD | 0,43 | 0,40 | bleibt, knapp |

**Das ist keine Feinjustierung, sondern ein Umbau.** Das V4-Ensemble
liefert bis zu **+4 Punkte** von drei benötigten (Teil 2, Abschnitt 2.3).
Blieben nur noch zwei Strategien übrig, würde es viel seltener feuern — der
Bot kaufte messbar anders.

Besonders auffällig: **EMA_TREND** würde gesperrt. Es ist heute das
häufigste Etikett überhaupt (192.414 Entscheidungen, 36 der 48 Käufe der
laufenden Epoche).

### Die Sperren sind belastbar — die Freigaben nicht

Für jede Strategie: Wie groß ist die Summe im Vergleich zu ihrer eigenen
Schwankungsbreite?

| Strategie | n | netto | Unsicherheit ± | Urteil |
|---|---:|---:|---:|---|
| ICHIMOKU_CLOUD | 267 | −648,03 $ | 210,89 | **SICHER** |
| EMA_TREND | 168 | −551,83 $ | 118,35 | **SICHER** |
| MACD_CROSS | 22 | −193,37 $ | 88,33 | **SICHER** |
| DCA_FEAR_GREED | 32 | −143,74 $ | 60,30 | **SICHER** |
| TSI_SIGNAL | 11 | −119,16 $ | 57,17 | **SICHER** |
| STOCHRSI_REVERSAL | 40 | −90,11 $ | 35,03 | **SICHER** |
| **FIBONACCI_SUPPORT** | 85 | +653,04 $ | **827,48** | **nicht entscheidbar** |
| **MOMENTUM_BREAKOUT** | 48 | +396,44 $ | **590,34** | **nicht entscheidbar** |
| **RSI_OVERSOLD** | 102 | +2,55 $ | **100,12** | **nicht entscheidbar** |

**Alle sechs Verlierer sind statistisch abgesichert. Keiner der drei
Gewinner ist es.** Ihre Summen sind kleiner als ihre eigene Schwankung —
sie hängen an wenigen großen Handeln (Teil 5, Abschnitt 5.9).

> **Man kann heute sicher sagen, welche Strategien Geld verlieren. Man kann
> nicht sagen, welche Geld verdienen.** Das ist kein Widerspruch: Verluste
> sammeln sich gleichmäßig an, Gewinne kommen in Sprüngen.

### Befund 78 — die Sperre ist ein Schalter genau auf der Nulllinie

`models/v4_calibrator.py:86` sperrt hart:

```python
if total_pnl <= 0:
    self.weights[sid] = 0.0
```

**Kein Puffer, keine Mindestfallzahl.** Bei `RSI_OVERSOLD` steht die Summe
heute auf **+2,55 $** — bei einer Schwankungsbreite von **±100 $**. Ein
einziger Handelstag entscheidet zwischen *„voll gesperrt"* und *„Gewicht
0,40"*.

Wie schnell das kippt, zeigt derselbe Bestand einen Tag zuvor: Am 25.08.
stand `RSI_OVERSOLD` bei **−57,86 $** (gesperrt), am 26.08. bei **+2,55 $**
(freigegeben). **Der V4-Bot handelt weiter, und die Grenze wandert mit.**

`schon_bekannt.py` meldet für `v4_calibrator.py:86` und `total_pnl <= 0`
**NEU**; Suche über alle Sitzungen: nichts.

**Empfehlung:** Wenn die Quelle umgestellt wird, dann **nicht ohne die Regel
zu entschärfen** — etwa Sperre erst ab einem Verlust, der größer ist als die
eigene Schwankungsbreite, und erst ab 30 Fällen. Sonst tauscht man eine
veraltete Zahl gegen eine zittrige.

### Punkt 8b ist heute wirkungslos

Die zwei Strategielisten benutzen verschiedene Namen (5.9, Grund 1). Das ist
richtig — aber **es hat derzeit keine Folgen**, denn diese Strategien feuern
in V6 überhaupt nicht:

```
ICHIMOKU_CLOUD     0 Handel, 0 Entscheidungen
TSI_SIGNAL         0            0
STOCHRSI_REVERSAL  0            0
MOMENTUM_BREAKOUT  0            0
```

Ein Zusammenführen der Listen würde heute **nichts** ändern. Es wird erst
gebraucht, wenn diese Strategien tatsächlich handeln — also frühestens nach
8a, und auch dann nur für die zwei, die dabei überleben.

**Was stattdessen auffiel:** Die Rückfallebene `v4_strategy_used or
self.current_strategy` (`agents/signal_agent.py:182`) hat seit dem 23.08.
**3.606 Kaufentscheidungen** mit dem Etikett `GRID_BOT` versehen — dem
Namen eines abgeschalteten Bausteins (5.2). Das ist der Teil von 8b, der
sich wirklich lohnt.

*Vormessung zu `OFFEN.md` Gruppe C, Punkte 8a und 8b.*

---

*Früher verstreut in ALT 4.1, 4.17, 4.18, 4.35, 4.80, 4.82 sowie B.1 bis B.6.*

---

# TEIL 6 — Was der Bot beobachtet, ohne zu handeln

**Stand: 25.08.2026, abends nachgezogen.** Alle Zahlen aus `telemetrie.db` und
`schatten_universum.db`, am Tag des Schreibens abgefragt.

---

## 6.1 Warum es sich lohnt, ohne Geld mitzuspielen

Der Bot handelt drei Münzen. Er **beobachtet** achtzehn. Er benutzt eine
Ausstiegsregel. Er **rechnet** vier weitere mit. Das ist kein Ballast,
sondern die einzige Möglichkeit, eine Frage zu beantworten, die sonst
unbeantwortbar bleibt:

> **Wäre es besser gewesen, es anders zu machen?**

Wer nur mitschreibt, was er getan hat, kann nie mehr als „es lief so".
Wer daneben mitschreibt, was er **hätte** tun können, kann rechnen.

Das ist auch die Antwort auf „warum ändern wir nicht einfach die Regel":
Weil vier fertige Bausteine in diesem Projekt schon verworfen wurden,
nachdem der Schattenlauf zeigte, dass sie schlechter waren als das, was
schon lief.

| Was mitläuft | Zeilen heute | beantwortet |
|---|---:|---|
| Schatten-Universum | 1.104 Signale | Welche Münze verdient ihre Reibung? |
| Schatten-Ausstiege | 38 | Wäre eine andere Ausstiegsregel besser? |
| Nachlauf | 30.205 | War der Ausstieg zu früh? |
| Positionsverlauf | 26.935 | Wie **verlief** eine Position, nicht nur wie sie endete |
| Schatten-Größenrechner | 41 | Wäre kleiner kaufen besser gewesen? |
| Schatten-Regeln | 1.880 | Was hätte das KI-Modell gesagt? |
| Chartanalyse | 253 Läufe | Trifft Chartanalyse überhaupt? |

**Nichts davon fasst Geld an.**

---

## 6.2 Das Schatten-Universum — achtzehn Münzen, drei gehandelt

Jede Stunde rechnet der Sammler für **18 Münzen** dieselbe Punktzahl aus wie
der Bot für seine drei — mit denselben Regeln, denselben Indikatoren,
derselben Kostenrechnung. Nur ohne zu kaufen.

**Was er schon beantwortet hat:** die Frage nach den Kosten je Münze. Eine
Runde kostet bei BTC **0,501 %**, bei NEAR **0,818 %** und bei OP
**0,904 %** (die vollständige Tabelle steht in Teil 4, Abschnitt 4.3).

> Ohne den Schattenlauf hätte man das nur erfahren können, indem man NEAR
> gekauft und bezahlt hätte.

**Was er noch nicht beantworten kann:** ob eine der fünfzehn ungehandelten
Münzen den Handel wert wäre. Dafür braucht es Signale *und* deren Ausgang —
und der Sammler schreibt nur den Einstiegszeitpunkt. Der Positionsverlauf
(6.5) schließt genau diese Lücke, indem er jedes Schattensignal wie eine
Position weiterverfolgt.

### Und hier stößt der Aufbau an eine Grenze

**Gemessen am 26.08.2026.** Aus **1.228 Signalen** sind bisher nur **32
Positionen** geworden — ein bis zwei je Münze. Der Grund liegt in der Bauart:
Je Münze ist immer nur **eine** Schattenposition offen, und sie läuft bis zu
`MAX_TAGE = 7` Tage.

```
Hoechstens moeglich:  1 Position je Muenze und 7 Tage
Fuer 30 Faelle je Muenze:  30 x 7 = 210 Tage  =  6,9 Monate
```

Tatsächlich seit dem 14.08.: **2,7 Positionen je Tag** über alle 18 Münzen,
also **0,15 je Münze und Tag**. Bis zum Stichtag am 18.09. kommen rund 61
weitere dazu — **3,4 je Münze** statt der nötigen 30.

Der Stand nach 24 Stunden, nach den Kosten der jeweiligen Münze, sieht heute
so aus — und **keine einzige Zeile trägt ein Urteil**:

| Münze | n | Median | | Münze | n | Median |
|---|---:|---:|---|---|---:|---:|
| RENDER | 1 | +7,30 % | | NEAR | 2 | −2,04 % |
| ADA | 2 | +6,09 % | | SUI | 2 | −2,30 % |
| INJ | 2 | +5,92 % | | UNI | 2 | −2,36 % |
| BTC | 2 | +3,26 % | | ATOM | 2 | −3,52 % |
| SOL | 2 | +1,98 % | | OP | 1 | **−14,46 %** |

> **Die Münzfrage ist mit dem heutigen Aufbau bis zum Stichtag nicht
> beantwortbar** — und zwar nicht knapp, sondern um den Faktor neun.

**Was das nicht heißt:** Der Sammler ist nicht nutzlos. Die **Kostenmessung
je Münze** (Teil 4, Abschnitt 4.3) beruht auf allen 1.228 Signalen und ist
belastbar. Nur die Frage nach dem *Ertrag* je Münze braucht Positionen, und
die entstehen langsam.

Wer sie schneller beantworten will, muss die Bauart ändern — etwa mehrere
Positionen je Münze zulassen oder `MAX_TAGE` senken. Beides wäre eine
Verhaltensänderung am Sammler und gehört hinter den Stichtag.

**Die Einschränkung gehört ins Bild:** Das Schatten-Universum misst
**Signalqualität**, nicht Portfolio-Leistung. Im Schatten gibt es keine
Kapitalkonkurrenz — jedes Signal darf „kaufen". In Wirklichkeit sind drei
Plätze belegt, und der häufigste Ablehnungsgrund lautet „bereits in
Position" (Teil 2, Abschnitt 2.8).

---

## 6.3 Die Schatten-Ausstiegsregeln — was eine andere Regel getan hätte

Zwei Regeln laufen mit, ohne zu verkaufen:

| Regel | Fälle | Ausstieg bei Ø | Höchststand war Ø | zurückgegeben |
|---|---:|---:|---:|---:|
| `GEWINN_RATSCHE_25` | 32 | **+0,906 %** | +1,482 % | 0,58 PP |
| `TREND_EXIT` | 6 | **−1,078 %** | +0,599 % | 1,68 PP |

**So liest man das.** Die Ratsche wäre im Schnitt bei +0,906 % ausgestiegen.
Gegen K-BASIS 0,505 % blieben **+0,40 Prozentpunkte netto** — sie wäre
rentabel gewesen. Das ist ungefähr dasselbe wie beim echten Trailing-Stop
(+0,94 % brutto, Teil 3).

**Der Trend-Ausstieg dagegen wäre bei −1,078 % ausgestiegen**, obwohl die
Position vorher bei +0,599 % stand. Er hätte einen kleinen Gewinn in einen
Verlust verwandelt — sechsmal von sechs.

> **Genau dafür gibt es den Schattenbetrieb.** Hätte man den Trend-Ausstieg
> scharfgeschaltet, weil er „plausibel klingt", hätte er sechs Positionen
> ins Minus gedreht. Sechs Fälle sind kein Beleg — aber sie sind ein Grund,
> ihn weiter im Schatten zu lassen.

Der Trend-Ausstieg ist deshalb bis heute nicht scharf
(`runtime/exit_monitor.py:37`, `TREND_EXIT_SCHATTEN = True`).

---

## 6.4 Der Nachlauf — war der Ausstieg zu früh?

**30.205 Zeilen.** Nach jedem Ausstieg und stichprobenartig nach jeder
Blockade wird nachgetragen, wie der Kurs **1, 4, 24 und 48 Stunden** später
stand.

| Ergebnis | Bedeutung |
|---|---|
| Kurs erholte sich | Stop war zu eng — Aussitzen wäre besser gewesen |
| Kurs fiel weiter | Stop war richtig — das Problem sitzt beim **Einstieg** |

**Warum bei Blockaden nur eine Stichprobe:** Rund 98.000 Ablehnungen sind zu
99 % dieselben Gründe im Endlostakt. Eine Probe je Stunde, Münze und Grund
sagt dasselbe, ohne die Datenbank vollaufen zu lassen. Dieselbe Überlegung
wie bei der Fallzahl-Frage in Teil 8, Abschnitt 8.9.

**Der Zwischenstand ist ein Warnsignal, kein Beleg:** Nach RSI-Ausstiegen
stieg der Kurs in der Folgestunde um im Schnitt **+5,15 %** weiter — aber
bei n = 2, und beide am selben Tag. Nach Trailing-Stops **−0,51 %** bei
n = 4. Ab etwa zehn unabhängigen Fällen wird das entscheidbar.

---

## 6.5 Der Positionsverlauf — der Film statt des Fotos

**26.935 Zeilen, alle fünf Minuten eine je offener Position.**

Der Bot speicherte über den Verlauf einer Position bisher genau zwei Zahlen:
den höchsten und den tiefsten Stand. Damit lässt sich **keine**
Ausstiegsregel nachrechnen, weil der **Zeitpunkt** fehlt.

Ein Beispiel vom 18.08.: Höchststand +1,67 %, verkauft bei +0,77 %,
Haltedauer **5,1 Tage**. War das Hoch nach zwanzig Minuten oder am vierten
Tag? Ein Stop, der sich am Schwankungsmaß orientiert, hätte völlig anders
reagiert — und ohne den Verlauf ist die Frage nicht zu beantworten.

Aufgezeichnet wird je Zeile: Preis, Ergebnis, Hoch und Tief seit Einstieg,
Fall vom Hoch, Schwankungsmaß (auch in Prozent), RSI, ADX, MACD-Histogramm,
letztes höheres Tief und Hoch, Marktlage.

**Zwei Quellen, weil eine nicht reicht:**

| Quelle | woher | warum |
|---|---|---|
| echte Positionen | `bot_state.json`, nur gelesen | wahrheitsgetreu, aber nur 15–20 Verläufe in zwei Wochen |
| Schattenpositionen | `schatten_universum.db` | jedes Signal eröffnet eine Papierposition — mehrere hundert |

Schattenpositionen laufen **ohne Ausstieg** bis zur Höchstdauer von sieben
Tagen durch. Das ist Absicht: Wir wollen den rohen Verlauf, damit sich
später jede Ausstiegsregel darauf rechnen lässt — auch eine, die **später**
ausgestiegen wäre.

---

## 6.6 Der Größenrechner im Schattenbetrieb

Er würde in Verlustserien und schlechten Phasen kleinere Beträge einsetzen.
Vergrößern kann er nie, nur verkleinern.

**Was er in 41 Fällen getan hätte:**

| | |
|---|---:|
| eingestellte Positionsgröße | **30 %** des Kapitals |
| was der Bot wirklich kaufte | Ø **186,78 $** |
| was der Schattenrechner genommen hätte | Ø **67,93 $** |
| entspricht | **10,9 %** des Kapitals |

**Er wäre also gut dreimal vorsichtiger gewesen.**

### Jetzt beantwortet: Nein, es wäre nicht besser gewesen

**Gemessen am 26.08.2026.** Die Notizen tragen keine Positionsnummer, aber
einen exakten Schlüssel: **Münze, Zeitpunkt und Betrag auf den Cent**. Damit
ließen sich **39 von 50** Notizen eindeutig einem Kauf zuordnen, **null
mehrdeutig** — und 37 davon bis zum Verkauf verfolgen.

Weil das Ergebnis linear mit der Größe geht, ist der Vergleich reine
Arithmetik:

| Variante | Ergebnis über 37 Positionen | gegen echt |
|---|---:|---:|
| **echt gehandelt** (30 % des Kapitals) | **+14,16 $** | — |
| **Schattenrechner** | +5,86 $ | **−8,30 $** |
| *Trivial-Latte: immer halbe Größe* | *+7,08 $* | *−7,08 $* |
| *Trivial-Latte: immer 35 % (sein Mittel)* | *+5,01 $* | *−9,15 $* |

**Er hätte 8,30 $ gekostet — und lag damit unter der einfachsten
Vergleichsgröße**, dem stumpfen Halbieren.

### Warum, und was das wirklich zeigt

**Er verkleinerte am stärksten dort, wo es am meisten kostete:**

| | Fälle | verkleinert auf |
|---|---:|---:|
| **Gewinner** | **35** | **35,4 %** der Größe |
| Verlierer | 2 | 46,7 % der Größe |

Er schnitt die **Gewinner härter** als die Verlierer. Das ist genau
verkehrt herum.

**Aber Vorsicht — die Aussage trägt nur halb.** In diesem Zeitraum gab es
**35 Gewinner und 2 Verlierer**. In einer solchen Phase verliert **jede**
Verkleinerung Geld; das ist Arithmetik, kein Urteil über den Rechner. Und
wofür er gebaut ist — schützen, wenn es schlecht läuft —, wurde an **zwei**
Fällen nie geprüft.

**Was man fair sagen kann:** Gegen eine feste Verkleinerung auf seinen
eigenen Mittelwert (35 %) war er **0,85 $ besser**. Seine Auswahl brachte
also einen winzigen Vorteil — er stellte nur die **Höhe** viel zu niedrig
ein.

> **Ein Größenrechner wird nicht daran gemessen, ob er kleiner macht,
> sondern ob er bei den richtigen kleiner macht.** Zwei Verlierer reichen
> für diese Frage nicht.

**Empfehlung:** Nicht anschließen, weiter mitlaufen lassen — und erst wieder
ansehen, wenn mindestens **zehn Verlierer** im Bestand sind.

*Nachgerechnet am 26.08.2026, `OFFEN.md` Gruppe A.*

---

## 6.7 Die Chartanalyse — 69 % Treffer und trotzdem Verlust

Das ist das lehrreichste Ergebnis dieses Teils, und es beantwortet eine
Frage, die man sich sonst jahrelang stellt.

`chartanalyse_backtest.py` sucht in Kursverläufen die klassischen Muster —
Ausbruch (*Breakout*), Rücktest (*Retest*), Abpraller an einer
Unterstützung (*Support Bounce*) — und rechnet nach, wie oft sie
funktionierten.

**253 Läufe, 115.446 Signale, vom 07.08. bis 25.08.:**

| Zeitrahmen | Läufe | Signale | Trefferquote Ø | **Erwartungswert netto Ø** |
|---|---:|---:|---:|---:|
| 1 h | 66 | 35.189 | **73,3 %** | **−0,482 %** |
| 4 h | 187 | 80.257 | **67,4 %** | **−0,503 %** |
| **gesamt** | **253** | **115.446** | **69,0 %** | **−0,498 %** |

Und die Zahl, auf die es ankommt:

```
Laeufe mit positivem Erwartungswert nach Kosten:  0 von 253
```

**Nicht einer.** Bei einer Trefferquote von fast 70 %. *Am 24.08. waren es
0 von 245 — acht Läufe später hat sich daran nichts geändert.*

### Warum sich das nicht widerspricht

Weil eine Trefferquote nichts darüber sagt, **wie groß** Treffer und
Fehlschläge sind. Sieben kleine Gewinne und drei große Verluste ergeben
70 % Trefferquote und ein Minus.

Und weil jede Runde **0,505 %** kostet. Der durchschnittliche Vorteil je
Signal liegt bei etwa **null** — er reicht knapp nicht einmal für die
Gebühren. Die Kostenlinie liegt genau dort, wo die Muster aufhören zu
wirken.

> **Eine hohe Trefferquote ist kein Ertrag.** Sie ist nur die Antwort auf
> „wie oft", nicht auf „wie viel". Nach 111.932 Signalen ist das keine
> Vermutung mehr.

**Was daraus folgt:** Die Chartanalyse bleibt ein **Beobachtungsdeck**. Sie
ist nicht an den Handelspfad angeschlossen, und nach diesem Ergebnis gibt es
auch keinen Grund dafür. Genau dieselbe Rechnung hat die Agenten-Abstimmung
von selbst gefunden — sie hat `technical` auf das Minimum von 0,30 gesenkt
(Teil 5, Abschnitt 5.4).

**Und der Vorbehalt gehört dazu:** Die 115.446 Signale sind **nicht
unabhängig**. Dasselbe Muster erscheint in aufeinanderfolgenden Läufen immer
wieder. Für ein Urteil zählt die Zahl der nicht überlappenden Fenster, nicht
die Rohzahl. Dass **alle 253** Läufe im Minus liegen, ist trotzdem
aussagekräftig — es gibt keinen einzigen Gegenbeleg.

---

## 6.8 Was die Beobachtung bereits entschieden hat

Der Schattenbetrieb ist kein Selbstzweck. Er hat in diesem Projekt schon
mehrfach eine Entscheidung getragen:

| Beobachtung | Folge |
|---|---|
| Chartanalyse: 0 von 253 Läufen netto positiv | bleibt Beobachtungsdeck, wird nicht angeschlossen |
| Trend-Ausstieg: 6 von 6 hätten Verlust gemacht | bleibt im Schatten |
| Schatten-Kosten je Münze | K-BASIS als richtig geeicht belegt (Teil 4) |
| Chandelier-Ausstieg gegengerechnet | **verworfen** — senkt den Erwartungswert von +0,852 auf +0,592 % |
| Positionsgrößen-Rechner | noch offen — Daten reichen nicht |

> **Nichts anschließen ohne Messung.** Vier fertige Bausteine sind in diesem
> Projekt daran gescheitert — und das ist der Beleg, dass die Regel
> funktioniert, nicht dass sie bremst.

*Früher verstreut in ALT 4.3, 4.9, 4.22, 4.26, 4.40, 4.43, 4.44, 4.55, 4.89,
4.103, 4.104, 4.105.*

---

---

## 6.9 Den Analyse-Reiter lesen — Zone für Zone

**Stand: 26.08.2026.** Svens Bitte: *„erkläre mir, wie man die Chartanalyse
aus unserem Analyse-Tab liest und wie das Ganze funktioniert."* Hier ist es,
von oben nach unten durch das Bild.

Alles darin rechnet `features/chartanalyse.py` aus. **Es löst keinen Handel
aus** und wird von keinem Kaufpfad importiert (6.7).

---

### Die Linien im Chart

| Was du siehst | Was es ist |
|---|---|
| **grüne Linie**, durchgezogen | **Unterstützung** — hier hat der Kurs mehrfach nach oben gedreht |
| **rote Linie**, durchgezogen | **Widerstand** — hier hat er mehrfach nach unten gedreht |
| **gestrichelt**, mit `ema2`/`ema5` beschriftet | gleitender Durchschnitt (EMA 50 und 200) als *bewegliche* Zone |
| **`ZIEL`** und **`STOP`**, gepunktet | die Vorschläge des aktuellen Signals |
| Zahl rechts, z. B. `74,296 swin` | Preis der Zone; `swin` = aus Swing-Punkten gebildet |
| **violett**, kräftig durchgezogen | Fibonacci-**Anker** — das Hoch (0) und das Tief (1) der Bewegung, aus der alles gerechnet ist |
| **violett**, gestrichelt | Fibonacci-**Rückzugsmarke** (Retracement) — 0,236 bis 0,866 |
| **violett**, fein gepunktet | Fibonacci-**Verlängerung** (Extension) — 1,272 bis 2,618, unterhalb des Tiefs |
| **blau**, zwei durchgezogene Kurven | **Bollinger-Bänder** — oberes und unteres Band (20 Perioden, 2 Standardabweichungen) |
| **blau**, gestrichelte Kurve dazwischen | der gleitende Durchschnitt, die Mitte der Bänder |

**Eine Zone ist kein Strich, sondern ein Band.** Sie reicht eine halbe
Schwankungsbreite (ATR) nach oben und unten. Deshalb kann der Kurs „in" einer
Zone stehen.

### Die violetten Linien — Fibonacci, von selbst gezogen

**Stand: 27.08.2026.** Svens Auftrag: *„fang an mit linien zeichnen!"*

Bis dahin gab es im Bot eine Funktion `fibonacci_ziele()`, die **niemand
aufrief** — toter Code. Jetzt rechnet sie bei jedem Bildaufbau mit, und der
Chart zieht die Linien selbst.

**Was Fibonacci überhaupt ist — in einem Satz:** Nach einer größeren Bewegung
läuft der Kurs oft ein Stück zurück, bevor er weitergeht. Fibonacci sagt
nicht *ob*, sondern *wo* dieses Stück typischerweise endet — bei festen
Bruchteilen der ursprünglichen Bewegung.

**Wie der Bot die zwei Anker wählt.** Das ist die ganze Entscheidung; alles
andere ist Rechnen:

1. Er nimmt alle **bestätigten** Wendepunkte der letzten 150 Kerzen
   (dieselben 150, die der Chart anzeigt).
2. Davon das **höchste Hoch** und das **tiefste Tief**.
3. Aus deren Abstand — der *Spanne* — kommen alle dreizehn Linien.

Die Reihenfolge „höchstes und tiefstes, nicht jüngstes" ist gemessen, nicht
geraten. Siehe Abschnitt *Zwei Irrwege* weiter unten.

**Die dreizehn Stufen:**

| Gruppe | Werte | Bedeutung |
|---|---|---|
| Anker | 0 und 1 | das Hoch und das Tief selbst |
| Rückzug | 0,236 · 0,382 · **0,5** · **0,618** · 0,707 · 0,786 · 0,866 | wie weit der Kurs zurückläuft |
| Verlängerung | 1,272 · 1,618 · 2,0 · 2,618 | wie weit er *über* das Tief hinausläuft |

0,618 heißt **Goldener Schnitt** und ist die meistbeachtete Marke.
0,707 und 0,866 sind **Wurzelverhältnisse** (√0,5 und √0,75) — sie stehen
hier, weil Mark sie in seinen Charts benutzt; die meisten Werkzeuge zeigen
sie nicht.

**Beschriftet werden nur fünf** — die beiden Anker und 0,382 / 0,5 / 0,618.
Alle dreizehn zu beschriften ergab genau die Textwand, gegen die am 19.08.
schon einmal aufgeräumt wurde.

**Kausalität:** Auch hier gilt der Satz von oben. Ein Hoch ist erst drei
Kerzen später erkennbar, deshalb trägt auch das Fibonacci-Ergebnis ein
`bestaetigt_ab`. Eine Linie, die es damals noch nicht gab, wird nicht
gezeichnet.

**Was es NICHT tut:** Es löst keinen Handel aus. Wie der ganze Reiter ist es
Beobachtungsdeck (6.7).

#### Gemessen am 12.09.2026 — die Stufen halten besser als Zufall

Hier stand bis zum 12.09.: *„Ob Fibonacci überhaupt trägt, ist ungemessen."*
Das ist beantwortet, und der Weg dorthin ist lehrreicher als das Ergebnis.

**Am 11.09. lautete das Urteil NICHT ENTSCHEIDBAR — und war falsch.** Die
damalige Messung (`konfluenz_messung.py`) benutzte diesen Code gar nicht,
sondern einen eigenen Nachbau mit **vier** Stufen statt neun. Es fehlten
0,707 und 0,866 — ausgerechnet die zwei Wurzelverhältnisse, die Marks
Verfahren ausmachen. Dazu streute die Zufallslatte über ±4 %, während die
echten Stufen dicht am Kurs lagen: verglichen wurde **nah gegen fern**.

> **Derselbe Fehler zum zweiten Mal.** `prognosen/MARK.md` sagt zum 27.08.
> wörtlich, dass genau diese zwei Stufen im Suchnetz fehlten und die
> Rücktechnik deshalb nichts fand (Befund 83). Die Datei lag im Projekt und
> wurde vor dem Messen nicht gelesen.

**Neu gerechnet** — mit `fibonacci_ziele()` selbst und einer Zufallslinie im
**selben Abstand vom Kurs** wie die Stufe, gegen die sie antritt:

| Münze | Fälle | Marks Stufen | Zufallslinie | Unterschied |
|---|---:|---:|---:|---:|
| BTC | 2.333 | 18,7 % | 16,9 % | +1,8 |
| ETH | 2.373 | 26,8 % | 24,7 % | +2,1 |
| SOL | 2.265 | 32,4 % | 29,6 % | +2,8 |
| **zusammen** | **6.971** | **25,9 %** | **23,8 %** | **+2,1** |

*Gehalten* heißt scharf: Das Tief kommt auf 0,10 % an die Stufe heran, und
danach steigt der Kurs 1,0 % darüber, **bevor** er 0,5 % darunter fällt.
Nicht die Schwankungsbreite — die hat ein fallender Kurs auch.

**Und 6.971 ist nicht die Zahl, die zählt.** An einem Zeitpunkt werden bis
zu sieben Stufen geprüft, die alle am selben Kursverlauf hängen. Deshalb ein
**Block-Bootstrap** über Tagesblöcke: 525 Blöcke, Vertrauensintervall
**+1,20 bis +3,01** Prozentpunkte — enthält die Null nicht. Im Mischungstest
entsteht der Vorsprung zufällig in **0,00 %** von 5.000 Mischungen.

**Das Werkzeug selbst ist gegen Marks eigene Zahlen geprüft**
(`mark_gegenprobe.py`): 16 von ihm beschriftete Stufen aus **zwei Märkten** —
BTC 30 min und Silber 4 h — größte Abweichung 0,26 $, das ist seine Rundung
beim Ablesen. Der Silberfall ist der stärkere Beleg: ein anderer Markt
schließt aus, dass hier eine BTC-Eigenheit nachgebaut wurde.

**Was das NICHT heißt.** Eine Stufe, die hält, ist noch kein Gewinn. Der Kurs
muss danach weit genug laufen, um 0,505 % Kosten je Runde zu decken. Genau
derselbe Unterschied wie beim London Sweep (Befund 96): dort lagen alle drei
Münzen brutto im Plus und trotzdem verlor jede Variante nach Kosten.

**Eine Einschränkung, offen benannt.** Viele geprüfte Stufen liegen sehr nah
am Kurs (Median 0,42 bis 0,66 %). Solche werden fast immer berührt, und ob
sie halten, hängt stark an der nächsten Bewegung. Der Vergleich bleibt fair,
weil die Zufallslinie im selben Abstand liegt — aber die absolute Quote von
25,9 % ist eine Aussage über *alle* Stufen, nicht über *gute*.

**Im Reiter sichtbar** unter MESSUNG. Werkzeuge: `mark_gegenprobe.py`,
`mark_messung.py`, `mark_belastbarkeit.py` (schreibt nach `telemetrie.db`,
Tabelle `fib_messung`). Befund 102.

#### Zwei Irrwäge, beide an echten Daten aufgeflogen

**Irrweg 1: die jüngsten Wendepunkte als Anker.** Naheliegend, und falsch.
Am 27.08. gemessen ergab das eine Spanne von 682 $ auf 80.500 — **0,85 %**.
Alle dreizehn Stufen lagen innerhalb eines knappen Prozents und waren im
Chart **eine einzige Linie**. Marks eigene Charts zeigen, wie er es macht:
im 30-Minuten-Bild vom 19.08. lagen seine Anker 59 Kerzen auseinander, bei
64.545 und 62.671 — die äußersten Punkte des Bildes, nicht die letzten.

**Irrweg 2: die Extreme über alle geladenen Kerzen.** Der Tab lädt 300
Kerzen, zeigt aber nur 150. Wer die Anker über alle 300 sucht, findet sie
oft **außerhalb des Bildes**. Gemessen auf Stundenkerzen: Ankertief 62.716,
sichtbarer Bereich aber erst ab 75.190 — **elf von dreizehn Stufen lagen
unter dem Bildrand, gezeichnet wurden zwei.**

Deshalb steht die Zahl 150 jetzt an **genau einer** Stelle
(`ui/chartanalyse_tab.py:42`, `ZEIGE_KERZEN`) und bestimmt beides: den
Bildausschnitt **und** die Ankersuche. Zwei getrennte Zahlen wären zwei
Wahrheiten, die auseinanderlaufen.

> **Die Lehre daraus:** Beide Fehler hätten einen Syntaxtest bestanden. Der
> erste fiel auf, als die *Spanne* nachgerechnet wurde; der zweite erst, als
> der Chart wirklich gezeichnet und die Linien **gezählt** wurden. Ein Bild,
> das entsteht, ist noch kein Bild, das stimmt.

**Nachweis nach der Korrektur** — gezeichnet, nicht geschätzt:

| Zeitrahmen | Spanne | Linien im Bild |
|---|---|---|
| 15m | 3,98 % | 9 von 13 |
| 30m | 4,48 % | 10 von 13 |
| 1h | 7,05 % | 9 von 13 |
| 4h | 23,34 % | 9 von 13 |
| 1d | 30,24 % | 9 von 13 |

Dass auf jedem Zeitrahmen rund neun Linien im Bild stehen, ist der Punkt:
Sven hatte ausdrücklich verlangt, dass es *„nicht nur bei den Tageskerzen"*
funktioniert.

#### Die Richtung — wo die Null liegt

**Nachtrag 28.08.2026.** Sven schickte vier Fibonacci-Raster von Mark vom
**30.04.** Sie haben einen Fehler aufgedeckt, der in der ersten Fassung drin
war und den keine Messung hätte finden können — nur ein Vergleich mit
seinen Zahlen.

**Die Regel lautet:** Die **Null liegt am Ende** der Bewegung, die **Eins an
ihrem Anfang.** Welcher der beiden Anker das Ende ist, entscheidet die
**Zeit**, nicht die Höhe:

| Bewegung | zuletzt | 0 liegt | Stufen laufen | Verlängerungen |
|---|---|---|---|---|
| **aufwärts** (Tief zuerst) | das Hoch | am **Hoch** | nach **unten** | unter das Tief |
| **abwärts** (Hoch zuerst) | das Tief | am **Tief** | nach **oben** | über das Hoch |

In der ersten Fassung stand fest `hoch − spanne × r` — also **immer** die
obere Zeile. Das passte zu Marks August-Charts und war für seine
April-Charts **genau spiegelverkehrt**.

**Nachgerechnet gegen vier seiner Raster vom 30.04.** — alle vier auf einem
fallenden Kurs, die Null also unten:

| | Tief (= 0) | Hoch (= 1) | Prüfstufe | seine Zahl | gerechnet | Abweichung |
|---|---|---|---|---|---|---|
| 1 | 74.904,22 | 77.925,02 | 0,236 | 75.617,13 | 75.617,13 | **0,00 $** |
| 2 | 75.324,64 | 76.430,19 | 1,618 | 77.113,42 | 77.113,42 | **0,00 $** |
| 3 | 74.841,93 | 77.909,45 | 0,618 | 76.737,66 | 76.737,66 | **0,00 $** |
| 4 | 75.835,87 | 76.314,59 | 0,786 | 76.212,14 | 76.212,14 | **0,00 $** |

Größte Abweichung über **alle** Stufen aller vier Raster: **0,01 $** — und
zwar durch die echte Funktion gerechnet, nicht durch eine Formel daneben.

> **Warum das ohne seine Bilder nie aufgefallen wäre:** Der Chart hätte
> weiter dreizehn saubere, waagerechte, gut verteilte Linien gezeichnet. Sie
> wären nur in der falschen Hälfte gewesen. **Ein Fehler, der richtig
> aussieht, wird nur durch einen bekannten Wert gefunden** — genau das,
> wozu CLAUDE.md Abschnitt 0 verpflichtet.

#### Derselbe Fehler stand ein zweites Mal im Projekt

**Nachtrag 01.09.2026.** Beim Erzeugen der Texte für alle sieben Zeitrahmen
fiel auf, dass der **Manuell-Reiter** dieselben Anker fand wie der
Analyse-Reiter. Das sah zuerst nach einer erfreulichen Bestätigung aus. Es
war der Hinweis auf **Befund 91**.

`ui/main_window.py` zeichnet Fibonacci selbst — mit genau der Formel, die im
Analyse-Reiter am 27.08. korrigiert worden war:

```python
fib_levels = {"0.0": swing_low, ...}      # die Null klebt am Tief
```

Die Null klebt fest am Tief. Das ist die **Abwärtsvariante**, und nur die.

**Nachgerechnet**, BTC/USDC 4 Stunden, Anker 81.494,43 / 62.480,00,
Richtung **aufwärts**:

| Stufe | Manuell-Reiter (alt) | richtig | dieselbe Linie heißt richtig |
|---|---:|---:|---|
| 0,0 | 62.480,00 | 81.494,43 | **1,0** |
| 0,382 | 69.743,51 | 74.230,92 | **0,618** |
| 0,5 | 71.987,21 | 71.987,21 | 0,5 |
| 0,618 | 74.230,92 | 69.743,51 | **0,382** |
| 1,0 | 81.494,43 | 62.480,00 | **0,0** |

**Die Linien lagen richtig — die Namen darauf waren vertauscht.** Nur die
0,5 stimmt in beiden Fällen, weil die Mitte gespiegelt die Mitte bleibt.

Wer nach dem Goldenen Schnitt (0,618) handelt, hat bei jeder
Aufwärtsbewegung die 0,382-Linie angesehen und für 0,618 gehalten.

**Warum die beiden Reiter bei Sven trotzdem übereinstimmten:** Der
Stundenchart lief zu dem Zeitpunkt **abwärts**. In dieser Richtung ist die
alte Formel zufällig richtig — sie hat ja genau diesen einen Fall fest
eingebaut. Die Übereinstimmung war kein Beleg, sondern ein Zufall.

> **Wer einen Fehler behebt, hat die Fehlerart nicht behoben.** Befund 85
> wurde am 27.08. an *einer* Stelle korrigiert. Dass dieselbe Formel ein
> zweites Mal im Projekt steht, hat niemand geprüft. Nach jeder Korrektur
> gehört die Frage dazu: **Wo steht dasselbe noch einmal?** Ein `grep` nach
> der Formel hätte vier Tage früher gereicht.

### Die blauen Kurven — Bollinger-Bänder

**Stand: 29.08.2026.** Svens Wunsch vom 26.08., jetzt eingebaut.

**Was sie sind — in einem Satz:** Ein gleitender Durchschnitt über
20 Kerzen, und darüber und darunter je eine Linie im Abstand von zwei
**Standardabweichungen**. Die Standardabweichung ist ein Maß dafür, wie
weit der Kurs zuletzt gestreut hat — also wie unruhig er war.

| Was du siehst | Was es bedeutet |
|---|---|
| **Bänder weit auseinander** | unruhiger Markt, große Ausschläge |
| **Bänder eng beieinander** | ruhiger Markt („Enge", engl. *squeeze*) |
| Kurs am **oberen** Band | ungewöhnlich hoch gemessen an der jüngsten Streuung |
| Kurs am **unteren** Band | ungewöhnlich tief |
| **gestrichelte Mitte** | der gleitende Durchschnitt selbst |

**Wichtig, damit du sie nicht falsch liest:** Ein Kurs am oberen Band ist
**kein Verkaufssignal**. In einem starken Aufwärtstrend läuft der Kurs
tage- oder wochenlang am oberen Band entlang. Die Bänder sagen *wie weit
weg vom Durchschnitt*, nicht *wohin als Nächstes*.

**Anders als alles andere im Chart sind das Kurven**, keine waagerechten
Linien — sie folgen dem Kurs. Deshalb Blau: Grün und Rot gehören den
Zonen, Violett dem Fibonacci, Weiß der Jetzt-Linie.

**Einstellung: 20 Perioden, 2 Standardabweichungen** — die Standardwerte,
dieselben wie in `features/chart_view.py:91` und dieselben, die Mark
benutzt. Sie stehen als `BOLL_PERIODE` und `BOLL_ABWEICHUNG` oben in
`ui/chartanalyse_tab.py`.

#### Zwei Kleinigkeiten, die den Unterschied machen

**Gerechnet wird auf allen 300 Kerzen, gezeigt werden 150.** Ein
gleitender Durchschnitt über 20 Kerzen hat vor der zwanzigsten keinen
Wert. Würde man nur auf dem sichtbaren Ausschnitt rechnen, wären die
ersten 20 Punkte im Bild leer — ein abgeschnittener Anfang, den man für
eine Marktbesonderheit halten könnte.

**Lücken unterbrechen die Kurve.** Verlässt ein Band den Bildausschnitt und
kommt später zurück, wird **nicht** durchgezogen. Ein Strich über die
Lücke hinweg würde eine Verbindung behaupten, die es nicht gibt.

**Nachweis** (BTC, wirklich gezeichnet und vermessen):

| Zeitrahmen | Kurvenzüge | Punkte |
|---|---|---|
| 15m | 3 | 447 |
| 1h | 4 | 429 |
| 1d | 4 | 441 |

Kein einziger Zug waagerecht — sie folgen dem Kurs, wie sie sollen.

> **Was der Zeichentest zusätzlich prüft:** ob das **obere Band wirklich
> über dem unteren** liegt. Wäre die Rechnung vertauscht, sähe der Chart
> trotzdem plausibel aus — drei Kurven eben. Es ist genau die Sorte
> Fehler, die kein Blick auf das Bild findet.

**Auch das ist Beobachtungsdeck.** Ob Bollinger überhaupt trägt, ist
**ungemessen** — wie bei Fibonacci steht die Messung in `OFFEN.md`.

#### Das Werkzeug dazu: `chart_zeichentest.py`

**Wann du es brauchst:** immer dann, wenn am Analyse-Chart etwas geändert
wurde — neue Linien, neue Beschriftung, andere Farben. Es beantwortet die
Frage, die ein Blick auf das Bild nicht sicher beantwortet: *sitzt wirklich
alles dort, wo es hingehört?*

**Was es tut.** Es baut den Chart in einem **unsichtbaren** Fenster auf —
es öffnet sich nichts, es wird nichts gehandelt — und vermisst danach jedes
gezeichnete Objekt: Liegen die Linien waagerecht? Innerhalb des Bildes?
Klebt ein Paar auf demselben Pixel? Überlagern sich Beschriftungen? Liegt ein
Anker in der Zukunft?

| Befehl | Wozu | Dauer |
|---|---|---|
| `python chart_zeichentest.py` | Der Vollauf: 3 Münzen × 5 Zeitrahmen | ~8 Min (holt Kerzen von der Börse) |
| `python zahlenbuch.py` | Erzeugt das **Zahlenbuch** — MD *und* PDF. **Nicht** über `handbuch_pdf.py` gehen: das nimmt zwar auch `ZAHLENBUCH.md` an, erzeugt daraus aber die **kurze** Fassung und überschreibt das ausführliche PDF (24 KB → 7 KB) |
| `python chart_zeichentest.py --muenzen BTC/USDT` | nur eine Münze | ~3 Min |
| `python chart_zeichentest.py --gegentest` | Findet der Test den bekannten Fehler wieder? | ~30 Sek |
| `python chart_zeichentest.py --selbsttest` | Bewertet er richtig? Ohne Börse | sofort |

**Was du liest:** Am Ende steht `ALLE 15 FAELLE SAUBER` oder eine Zeile je
Problem. Die Spalte *engste* sagt, wie nah sich die beiden dichtesten Linien
kommen — unter 3 Pixel wäre das eine Gitterwand statt eines Charts.

> **Warum `--gegentest` wichtiger ist als der Vollauf:** Ein Prüfwerkzeug,
> das immer „ok" sagt, sieht genauso aus wie eines, das nichts findet. Der
> Gegentest stellt den bekannt kaputten Zustand wieder her und verlangt,
> dass das Werkzeug **anschlägt**. Erst dann ist ein „sauber" etwas wert.

**Was es NICHT prüft:** ob die Linien inhaltlich richtig liegen. Das kann
nur ein Vergleich mit einem bekannten Wert — siehe die Richtung oben.

### Wie eine Zone überhaupt entsteht

In drei Schritten:

**1. Swing-Punkte finden.** Ein *Swing-Hoch* ist eine Kerze, deren Hoch höher
liegt als die drei Kerzen davor **und** die drei danach.

```
                    X          <- Swing-Hoch
              ^  ^     ^  ^
           ^                 ^
```

> **Der wichtigste Satz an dieser Stelle:** Ein Swing-Hoch ist erst **drei
> Kerzen später** erkennbar — vorher weiß niemand, dass es das Hoch war.
> Deshalb trägt jede Zone einen `bestaetigt_ab`-Index, und vor diesem Index
> existiert sie für jede Auswertung **nicht**. Wer das weglässt, misst die
> Zukunft mit und bekommt eine Rückrechnung, die großartig aussieht und im
> Echtbetrieb verliert.

**2. Nahe Punkte zusammenfassen.** Liegen mehrere Swing-Punkte innerhalb
einer ATR-Breite, werden sie **eine** Zone. Ein einzelnes Hoch ist noch kein
Widerstand — es braucht **mindestens zwei** Berührungen.

**3. Stärke vergeben.** `Stärke = Berührungen ÷ 5`, gedeckelt bei 100 %.

```
2x beruehrt  ->  40 %
3x beruehrt  ->  60 %
5x beruehrt  -> 100 %   (mehr bringt nichts)
```

In deinem Bild: `78.713,81 — 5x berührt — Stärke 100 %`. Das ist die
stärkste Zone, die dieses System kennt.

**„(durchbrochen)"** heißt: Der Kurs stand schon einmal auf der anderen
Seite. Eine durchbrochene Widerstandszone wird oft zur Unterstützung — das
ist die Idee hinter dem *Retest*.

---

### Die Formationen

| Formation | Was sie bedeutet |
|---|---|
| **DOPPEL_TIEF** | zweimal fast derselbe Tiefpunkt, dazwischen ein Hoch (die *Nackenlinie*). Bricht der Kurs über die Nackenlinie, gilt es als bullisch |
| **DOPPEL_HOCH** | dasselbe umgekehrt — bärisch |
| SCHULTER_KOPF_SCHULTER | drei Hochs, das mittlere am höchsten — bärisch |
| DREIECK | Hochs fallen, Tiefs steigen — Ausbruch in eine Richtung |

Das **Kursziel** ist die Höhe der Formation, an der Nackenlinie nach oben
abgetragen. In deinem Bild:

```
DOPPEL_TIEF   Tiefs 62.225,83 / 62.480,00   Nackenlinie 65.446,00
Hoehe = 65.446,00 - 62.225,83 = 3.220,17
Ziel  = 65.446,00 + 3.220,17 = 68.666  (angezeigt: 68.539,09)
```

> **Achtung, ein häufiges Missverständnis:** Dass zwei Formationen
> gleichzeitig dastehen — bei dir DOPPEL_TIEF *bullisch* und DOPPEL_HOCH
> *bärisch* — ist kein Widerspruch. Sie beschreiben **verschiedene
> Zeitfenster** im selben Chart. Beide sind vergangen; nur die jüngere ist
> handlungsrelevant.

---

### Das Signal — und wie die Güte zustande kommt

Es gibt genau **drei** Anlässe:

| Signal | wann |
|---|---|
| **SUPPORT_BOUNCE** | der Kurs steht **in** einer Unterstützungszone |
| **BREAKOUT** | der Kurs ist gerade **über** einen Widerstand gestiegen |
| **RETEST** | der Kurs testet eine **gebrochene** Linie von oben |

Die Güte ist reine Arithmetik:

```
SUPPORT_BOUNCE :  0,40 + 0,60 x Staerke
BREAKOUT       :  0,35 + 0,55 x Staerke
RETEST         :  0,50 + 0,50 x Staerke

danach:  Trend AUFWAERTS   x 1,20
         Trend ABWAERTS    x 0,60
         bullische Formation x 1,15      (Deckel bei 100 %)
```

**Nachgerechnet an deinem Bild:**

```
RETEST an einer Zone mit Staerke 100 %  ->  0,50 + 0,50 = 1,00
Trend AUFWAERTS                         ->  x 1,20 = 1,20  -> gedeckelt 1,00
Formation DOPPEL_TIEF bullisch          ->  x 1,15         -> gedeckelt 1,00
                                                              = 100 %  ✓
```

Deshalb steht dort 100 %. **Die Güte war schon nach dem ersten Schritt am
Anschlag** — Trend und Formation haben nichts mehr hinzugefügt.

### Und jetzt die Zahl, auf die es wirklich ankommt

```
Chance/Risiko 0.36   (unter 1.5 lohnt sich nach Kosten selten)
```

Sie sagt: **Du riskierst 2.036 $, um 729 $ zu gewinnen.**

```
Risiko = 77.984,65 - 75.948,25 = 2.036,40
Chance = 78.713,81 - 77.984,65 =   729,16
0,36
```

Bei diesem Verhältnis müsstest du **74 % der Fälle** gewinnen, nur um bei
null herauszukommen — vor Kosten.

**Merke: Güte 100 % und Chance/Risiko 0,36 im selben Kasten sind kein
Widerspruch.** Die Güte bewertet, wie **verlässlich** die Zone ist. Das
Chance/Risiko-Verhältnis bewertet, ob sich der Handel **lohnt**. Das sind
zwei völlig verschiedene Fragen — und nur die zweite entscheidet über Geld.

---

### Warum das Ziel so nah liegt — der Bauartfehler dahinter

In deinem Bild ist das **Ziel 78.713,81** — und das ist **dieselbe Zone**,
die den Retest ausgelöst hat.

Der Grund steckt in zwei Zeilen, die nicht zusammenpassen
(`features/chartanalyse.py:359` und `:404`):

```python
ueber = [z for z in zonen if z.preis > preis]     # Zone gilt als "darueber",
                                                   # wenn ihre MITTE oben liegt
...
fuer_retest = [z for z in res_zonen if z.enthaelt(preis)]   # Retest heisst,
                                                   # der Kurs ist IM Band
```

Eine Zone, deren **Mitte** über dem Kurs liegt, deren **Band** ihn aber
umschließt, ist damit **gleichzeitig** Auslöser und Ziel. Die Chance
schrumpft auf den halben Zonenabstand, während der Stop unter dem ganzen
Band liegt.

**Das ist kein Einzelfall.** Über alle 117.199 Signale:

| Signalart | Median Chance/Risiko | erreicht 1,5 |
|---|---:|---:|
| SUPPORT_BOUNCE | **0,342** | **1,9 %** |
| RETEST | **0,417** | 6,3 % |
| BREAKOUT | **0,367** | 12,5 % |

**Das Werkzeug schreibt selbst „unter 1.5 lohnt sich selten" — und erreicht
diese Schwelle in unter 13 % der Fälle.** Steht als **Befund 81**.

---

### Was die Messung sagt — und was daraus folgt

Damit ist die Frage aus 6.7 endgültig beantwortet: *warum 70 % Treffer und
trotzdem Verlust?* **Weil die Gewinne ein Drittel so groß sind wie die
Verluste.**

Gerechnet über **2.589 einzigartige** Signale (nicht die 117.199 —
dieselbe Kerze wird in jedem Lauf neu bewertet, 45-fach):

| Filter | n | Trefferquote | **EV netto** | Urteil |
|---|---:|---:|---:|---|
| **alles nehmen (heute)** | 2.589 | **71,1 %** | **−0,455 %** | **verliert, sicher** |
| nur Güte ≥ 0,8 | 1.369 | 72,9 % | −0,406 % | **verliert, sicher** |
| nur SUPPORT_BOUNCE | 1.544 | 71,6 % | −0,523 % | verliert |
| nur RETEST | 824 | 70,9 % | −0,339 % | verliert |
| nur BREAKOUT | 221 | 68,8 % | −0,418 % | verliert |
| **nur Chance/Risiko ≥ 1,5** | **105** | **37,1 %** | **+0,395 %** | nicht entscheidbar |
| **nur Chance/Risiko ≥ 2,0** | **55** | **34,5 %** | **+0,772 %** | nicht entscheidbar |

**Drei Dinge stehen in dieser Tabelle:**

**1. Die Güte ist wertlos.** Sie ist die Zahl, die im Reiter am größten
prangt — und ein Filter darauf verbessert das Ergebnis um **0,05
Prozentpunkte**, bei 1.369 Fällen. Das ist nichts.

**2. Keine der drei Signalarten trägt.** Alle drei verlieren, alle drei
sicher.

**3. Das Chance/Risiko-Verhältnis ist der einzige Hebel, der greift.**
Es dreht das Vorzeichen — von −0,455 % auf **+0,772 %**. Und die
Trefferquote **fällt dabei von 71 % auf 35 %**.

> **Die beste Regel, die wir finden konnten, trifft nur jedes dritte Mal —
> und verdient trotzdem Geld.** Wer nach Trefferquote optimiert, optimiert
> in die falsche Richtung.

**Die Einschränkung gehört dazu:** 55 Fälle. Das reicht für eine Richtung,
nicht für eine Entscheidung. Steht als Vorhaben in `OFFEN.md`.

---

### Was du im Reiter zuerst ansehen solltest

| Reihenfolge | Worauf | Warum |
|---|---|---|
| **1.** | **Chance/Risiko** | die einzige Zahl mit belegtem Zusammenhang zum Ergebnis |
| 2. | Stärke der Zone (Berührungen) | wie verlässlich die Linie ist |
| 3. | Abstand Stop ↔ Ziel | ob der Handel überhaupt Platz hat |
| **zuletzt** | **Güte** | sieht wichtig aus, ist es nicht |

*Auftrag von Sven, 26.08.2026.*


## 6.10 Der neue Handelsweg — Fraktale, Konfluenz, Aussitzen

**Angelegt 14.09.2026 auf Svens Vorlage.** Ein zweiter Weg, wie der Bot
kaufen und halten könnte. Er handelt **nicht** — er rechnet mit.

### Die Idee in drei Sätzen

Statt auf Indikatoren zu hören, sucht dieser Weg **Fraktale**: Punkte, an
denen der Kurs sichtbar gedreht hat. Aus je zwei benachbarten Wendepunkten
entsteht eine Welle, aus der Welle ein Fibonacci-Raster. Wo sich Stufen
**mehrerer Zeitrahmen** treffen, liegt eine Konfluenzzone — und genau dort
wird gekauft.

Das Besondere kommt danach: Geht die Position ins Minus, wird sie **nicht
verkauft**, sondern ausgesessen, solange die Struktur hält.

### Die Hälfte war schon gebaut — und zwar der schwierige Teil

| Baustein | Woher |
|---|---|
| Fraktale mit Kausalitätsschutz | `features/chartanalyse.py:127` — war seit dem 27.08. da |
| Fibonacci, neun Stufen | ebd. `:232` |
| Bar-by-bar-Backtest | `chartanalyse_backtest.py:162` |
| Kosten je Münze | `core/kosten.py`, `engine.py` SPREAD_BP |

Der **Kausalitätsschutz** ist der Teil, an dem solche Projekte scheitern:
Ein Fraktal ist erst *n* Kerzen später erkennbar. Wer es vorher benutzt,
zeichnet eine Linie, die es damals nicht gab — und misst eine Trefferquote,
die niemand handeln konnte. Bei uns steht das Feld `bestaetigt_ab` an
**vierzehn** Stellen.

### Was neu ist

**`features/fraktal_konfluenz.py`** ergänzt genau drei Dinge:

**1. Das Golden Pocket** — das Band zwischen 0,618 und 0,65. Die Kanten
werden **sortiert**, nicht angenommen: bei einer Abwärtsbewegung liegt die
0,65 *über* der 0,618.

**2. Konfluenz über mehrere Zeitrahmen.** Die Toleranz ist **relativ**
(0,35 %), nicht in Dollar — sonst wäre die Regel bei BTC eine völlig
andere als bei SOL.

**3. Ein Score, der nicht doppelt zählt.** Das ist der heikle Teil:

> **Drei Stufen aus derselben Welle sind eine Beobachtung, nicht drei.**

Deshalb zählt der Score nach *Herkunft*: je Zeitrahmen und Welle nur die
stärkste Stufe. Der Unterschied ist messbar:

| Lage | Score | Quellen | Linien |
|---|---|---|---|
| Drei Stufen, **eine** Welle | 2 | 1 | 3 |
| Drei Stufen, **drei** Quellen | 4 | 3 | 3 |

Ohne diese Regel bekäme jede Stelle im Chart einen hohen Score, sobald man
genug Linien einzeichnet — **der Score wäre eine Funktion der Zeichenwut,
nicht des Marktes.**

### Warum Marks Stufensatz unangetastet bleibt

`FIB_RUECK` ist **Marks** Satz (mit 0,707 und 0,866). Die 0,65 steht in
einem eigenen Satz `STUFEN_HANDEL`. Hätte man sie dort hineingeschrieben,
würde `mark_messung.py` beim nächsten Lauf etwas anderes messen als beim
letzten — und der Vergleich zu Befund 102 wäre **still** kaputt.

### Hold/Recovery — und warum es eine Notbremse hat

`risk/hold_recovery.py`, fünf Zustände:

| | |
|---|---|
| **NORMAL** | im Plus oder nie im Minus gewesen |
| **RECOVERY** | im Minus, Struktur hält — wird ausgesessen |
| **ERHOLT** | zurück über null |
| **INVALIDIERT** | Kurs unter dem Swing-Tief: die These ist widerlegt |
| **NOTBREMSE** | −15 % erreicht, unabhängig von der Struktur |

**Svens Vorlage sah gar keinen Stop vor.** Die Notbremse ist seine
Entscheidung vom 14.09. — und der Wert ist nicht gegriffen: **Kriterium E
der Freigabe erlaubt höchstens 15 % Rückgang.** Eine Regel, die eine
einzelne Position tiefer fallen lässt, könnte dieses Kriterium mit einem
einzigen Handel reißen.

**Die Reihenfolge ist nicht beliebig:** Die Notbremse wird **vor** der
Struktur geprüft. Andersherum liefe eine Position bei −20 % weiter, solange
die Struktur formal hält. Und sie hängt am **tiefsten** Stand, nicht am
aktuellen — sonst wäre sie durch eine Zwischenerholung umgehbar.

**Kein Scale-in.** Svens Vorlage hatte es „standardmäßig deaktiviert";
diese Datei kennt es gar nicht. Nachkaufen im Verlust verschiebt den
Einstand nach unten **und** erhöht den Einsatz genau dann, wenn die These
gerade nicht aufgeht.

### Der Haken, den man kennen muss

> **Ein Verfahren, das Verlierer aussitzt, erzeugt zwangsläufig eine hohe
> Trefferquote.** Fast jede Position wird irgendwann grün — bis eine es
> nicht wird. Der Verlust kommt selten und dann groß.

Das ist die häufigste Erklärung für „80 % Trefferquote". Nicht weil die
Methode schlecht wäre — sondern weil die Trefferquote bei dieser Bauart
allein nichts aussagt. Was zählt, ist der Erwartungswert über **alle**
Fälle, der größte Rückgang und die längste Verlustserie.

### Gemessen, nicht geraten

`nachlauf.db` schreibt seit dem 25.07. zu jedem Ausstieg mit, wie der Kurs
1, 4, 24 und 48 Stunden danach stand (Befund 59/60). Damit ließ sich
Hold/Recovery **rückwirkend an echten Ausstiegen** rechnen —
`hold_recovery_rueckblick.py`, 39 Fälle, alle vier Fenster auf **derselben**
Stichprobe:

| Fenster | verkauft | gehalten | Unterschied |
|---|---|---|---|
| 1 Stunde | −2,752 % | −2,375 % | +0,377 |
| **4 Stunden** | −2,752 % | −1,953 % | **+0,799** |
| 24 Stunden | −2,752 % | −2,527 % | +0,225 |
| **48 Stunden** | −2,752 % | **−3,241 %** | **−0,489** |

**Aussitzen hilft — aber nur kurz, und dann kippt es.** Nach Grund
getrennt wird es deutlicher:

| Grund | n | Halten bringt |
|---|---|---|
| TREND-EXIT | 16 | +0,680 |
| **STOP-LOSS** | 15 | **−0,114** |

Der TREND-EXIT ist die Regel, die seit dem 10.08. ohnehin stillgelegt ist.
**Beim Stop-Loss — genau dem Fall, den Hold/Recovery umgehen würde —
bringt Halten praktisch nichts.**

**Zwei Messfehler auf dem Weg dorthin**, beide selbst gefunden:

1. Jedes Fenster rechnete zunächst auf **verschiedenen** Stichproben (57
   gegen 39 Fälle). Der Sprung von +0,314 auf −0,489 hätte auch daher
   kommen können.
2. Die Trivial-Latte „gar nicht handeln" stand als Vergleich da — hier
   **irreführend**, weil die Stichprobe nur Verlierer enthält. Wer diese
   Null als Latte liest, vergleicht die schlechtesten Trades mit dem
   Nichtstun.

### Was die Zahl nicht ist

**Sie endet nach 48 Stunden.** Hold/Recovery kann Wochen dauern; was dann
noch im Minus steht, ist nicht verloren, sondern **offen**. Die Zahl ist
eine Obergrenze für den Nutzen des Haltens.

**Sie kennt die Struktur nicht.** In `nachlauf.db` steht kein Swing-Tief.
Gerechnet ist nur die Notbremse.

**39 Fälle sind wenig.** Das ist ein Hinweis, kein Urteil.

### Der Stand

| Stufe | Was | Zustand |
|---|---|---|
| **1** | Fraktale, Golden Pocket, Multi-Timeframe-Konfluenz | ✅ 33 Prüfungen |
| **2** | Hold/Recovery als Schattenregel, Notbremse −15 % | ✅ 17 Prüfungen, eingehängt |
| 3 | Backtest mit In-Sample/Out-of-Sample, Wilson-Intervall, Kontrollgruppen | offen |
| 4 | Walk-Forward, Parameter-Heatmaps, Monte-Carlo, Reports | offen |

**In Stufe 2 fehlt die Struktur-Prüfung.** Das Swing-Tief der Kaufzone ist
an der Position nicht gespeichert — es entsteht erst, wenn dieser Weg
selbst kauft. Gemessen wird deshalb *Aussitzen bis zur Notbremse*, und das
ist wieder eine **Obergrenze**: eine echte Struktur hätte einen Teil der
Positionen früher geschlossen, meist mit kleinerem Verlust.

**Nichts davon handelt.** Der echte Stop-Loss, die Breakeven-Sperre und die
Trailing-Leiter laufen unberührt weiter. Bevor daraus ein Handel wird,
braucht es Stufe 3, eine eigene Epochengrenze und Svens Freigabe.

> **Nachtrag 14.09.2026, abends — der letzte Satz gilt nicht mehr.**
> Nach dem ersten Echtgeld-Abend ist aus diesem Beobachtungsweg ein
> Handelsweg geworden, allerdings nur in eine Richtung: als Tor, das
> Käufe **verhindern** kann. Siehe 6.11.

---

## 6.11 Das Fraktal-Tor — als der Bot am Hoch kaufte

**Stand: 14.09.2026.** Der Tag, an dem sich zeigte, dass der ganze
Abschnitt 6.10 am Handel vorbeirechnete.

### Was passiert ist

Am 14.09. lief der Live-Bot zum ersten Mal mit echtem Geld und kaufte
innerhalb von zwei Minuten viermal BTC. Sven sah sich die Kurse an und
schrieb: *„ich verstehe auch nicht warum er bitcoin zu so einem hohen
kurs kauft das kann doch nur schief gehen […] da läuft mit sicherheit
nicht nach meinem system mit den fraktalen das ich dir vorgegeben
habe!"*

Er hatte recht, und der Beleg stand wörtlich im eigenen Log
(`data_store/system.log:248`):

```
BTC/USDC: Score 9/10 (90%) -> BUY | MACD positiv + EMA-Trend up
 + Starker Trend (ADX 35) + Ueber VWAP + Orderbook Kaufdruck
 + V4-EMA_TREND STARK (0.89)
```

Fünf Signale, alle Trendfolge. Kein Fibonacci, keine Fraktale, keine
Konfluenz.

### Die Ursache — eine Datei, die niemand fragte

`features/fraktal_konfluenz.py` hat 33 Prüfungen und rechnet richtig.
Sie wurde nur von **niemandem aufgerufen**. Die Suche über das ganze
Projekt ergab genau einen Treffer außerhalb der Datei selbst: ihre
eigene Testdatei (`fraktal_konfluenz_test.py:32`).

Das ist der unangenehme Teil: Es war kein Rechenfehler und keine
schlechte Idee. Es war eine fertige, geprüfte, dokumentierte Komponente
ohne Anschluss. Sie stand im Handbuch, sie hatte Tests, sie hatte einen
eigenen Abschnitt — und sie hing an nichts.

> **Eine Datei mit Tests sieht aus wie ein laufendes Feature.** Der
> Unterschied ist ein einziger Import, und den sieht man nur, wenn man
> danach sucht.

### Warum Trendfolge das Gegenteil von Svens Verfahren ist

| | kauft wann | heißt übersetzt |
|---|---|---|
| **Trendfolge** (was lief) | MACD positiv, ADX hoch, über VWAP | „der Kurs läuft schon" |
| **Svens Verfahren** | Golden Pocket, 61,8–65 % Rücksetzer | „der Kurs ist zurückgekommen" |

Das sind keine zwei Geschmacksrichtungen derselben Sache. Sie kaufen an
entgegengesetzten Punkten derselben Bewegung.

### Warum ein Tor und keine zusätzlichen Punkte

Der naheliegende Einbau wäre gewesen, Konfluenz als weitere Punkte in
den Score zu geben. Das hätte nichts geändert: Bei Schwelle 7 erreichten
die Trendfolge-Signale die Schwelle bereits allein — Score 9 kam ganz
ohne Fibonacci zustande. Zusätzliche Punkte hätten den Kauf am Hoch
nicht verhindert, nur die Zahl daneben erhöht.

Ein Tor wirkt andersherum. Es **kann nur ablehnen, nie erlauben**:

- Der Score sagt: *die Lage ist günstig.*
- Das Tor sagt: *aber der Preis ist es nicht.*

Damit bleibt auch die an 57 Verkäufen gemessene Schwelle 7 (Befund 103)
unangetastet, und der Vergleich zum Papier-Bot hält.

### Was die Rückmessung zutage förderte

`fraktal_rueckblick.py` stellt dem Tor dieselbe Lage noch einmal, mit
den echten Kerzen von damals und einem harten Kausalitätsschnitt — es
sieht nur Kerzen, die zum Kaufzeitpunkt abgeschlossen waren.

**Die erste Fassung hätte drei der vier Käufe durchgelassen.** Nicht
weil die Konfluenz-Rechnung falsch war, sondern weil zwei Bedingungen
fehlten, die beide zum Kern des Verfahrens gehören:

**Erstens: winzige Wellen zählten wie große.** Auf dem 1-Stunden-Raster
fanden sich Wellen mit 0,63 % Spanne. Ihr Golden Pocket war 16 $ breit —
bei 0,505 % Handelskosten schmaler als die Gebühren. Eine Zone aus
solchen Wellen ist Rauschen mit einer Zahl daneben.

**Zweitens: flache Rücksetzer galten als Kaufzone.** Die Zone, die den
Kauf erlaubt hätte, lag bei 79.068 $ und bestand aus **0,236er und
0,382er** Stufen der großen Tageswellen. Bei einem 23,6 %-Rücksetzer
steht der Kurs noch fast am Hoch.

Die Zahlen zum Kaufzeitpunkt, nachgerechnet:

| | |
|---|---|
| Golden Pocket der Tageswellen | 78.377 – 78.642 $ |
| **Kaufpreis des Bots** | **78.982 $** |
| Differenz | rund 400 $ **zu früh** |

Der Bot kaufte oberhalb des Bereichs, auf den Svens Verfahren zielt.

### Die zwei Regeln, die daraus wurden

```
MIN_WELLE_PCT   = 2.0    Wellen unter 2 % Spanne bilden keine Zone
MIN_RUECKSETZER = 0.5    Kaufzone erst ab 50 % Rücksetzer
```

2,0 % ist rund das Vierfache der Kosten. Vom Golden Pocket zurück zum
Wellenhoch sind das etwa 1,3 % Weg — knapp, aber messbar oberhalb der
0,505 %.

Beide Filter greifen **vor** der Zonenbildung. Danach wäre es zu spät:
Die aussortierten Stufen hätten den Score der Zone schon aufgebläht, und
der Score soll die Zahl unabhängiger Beobachtungen sein, nicht die Zahl
gezeichneter Linien.

### Was das Tor nicht tut

Es löst **keinen** Kauf aus. Ein Preis mitten im Golden Pocket, zu dem
der Score unter der Schwelle liegt, führt zu keinem Handel. Und bei
einem Fehler im Tor wird **nicht** gekauft — ein Tor, das bei Störungen
durchlässt, ist keines.

### Schalter

| Schalter | Vorgabe | Wirkung |
|---|---|---|
| `trading.fraktal_tor_aktiv` | aus | an = Tor kann Käufe ablehnen |
| `trading.fraktal_tor_nur_messen` | aus | an = Tor rechnet und schreibt ins Log, hält aber nichts auf |

Der Schattenbetrieb ist der Weg, der CLAUDE.md 7.1 erfüllt („nichts
anschließen ohne Messung"): Erst misst das Tor mit, ohne das Verhalten
zu ändern, dann entscheidet die Zahl.

**Prüfen:** `FRAKTAL_PRUEFEN.bat` (Doppelklick) startet alle drei
Prüfungen — Kontostand, Funktionstest, Rückmessung.

---

## 6.12 Die Bestandsübernahme im Live-Betrieb

**Stand: 14.09.2026.** Der zweite Fund desselben Abends, und der
gefährlichere.

### Der Zustand

Nach den vier Käufen lagen 0,00041 BTC (rund 32 $, also **90 % des
Kontos**) auf der Börse. Im Positionsregister des Bots standen sie
nicht. Damit galt für sie: kein Stop-Loss, kein Trailing, keine
Breakeven-Sperre. Zugleich rechnete die Größenbestimmung mit 3,69 $
statt mit 36 $ — sichtbar in jeder zweiten Logzeile:

```
[SIZING] Basis 3.69$ (Cash 3.69 + Positionen 0.00) -> 50% = 1.85$
[BALANCE] USDC: 3.69$ | Positionen: 0.00$ | Total: 3.69$ (ROI: -89.81%)
```

Der Wächter erkannte es korrekt und meldete es als Alarm
(`features/waechter.py:96`). Nur: Der Wächter **liest nur** — das steht
in seinem eigenen Kopfkommentar und ist eine bewusste Entscheidung. Es
gab also eine richtige Meldung und niemanden, der sie ausführt.

### Die Ursache

`runtime/state_manager.py:280`. Über der Stelle stand seit Monaten ein
Kommentar, der genau dieses Problem beschreibt:

```python
# WURZEL-FIX: NICHT abbrechen wenn Backup leer - aus Balances
# rekonstruieren (sonst bleiben Coins als Geisterbestand liegen).
elif self.app.config.trading.mode != "paper":
    return          # ← und hier bricht sie doch ab
```

Die Reparatur gegen Geisterbestände war gebaut — und im Live-Modus
abgeschaltet. Die Rekonstruktion darunter stand komplett hinter
`if mode == "paper"`. Sieben Monate lang fiel das nicht auf, weil
sieben Monate lang niemand live handelte.

### Warum der Einstand aus den Ausführungen kommt

Die Papier-Rekonstruktion setzt den **aktuellen Kurs** als Einstand und
warnt im selben Atemzug davor:

> „ACHTUNG: Einstand = aktueller Preis, ein bereits aufgelaufener
> Buchverlust ist damit unsichtbar und der Stop-Loss hängt am falschen
> Bezugspunkt!"

Bei echtem Geld ist das nicht hinnehmbar. Ein Bestand, der schon 2 %
gefallen ist, bekäme einen Stop-Loss 2,5 % unter dem **gefallenen**
Kurs — der Verlust wäre dann 4,5 %, nicht 2,5 %.

Der echte Einstand steht an genau einer Stelle: in den Ausführungen der
Börse. Dieselbe Quelle, über die am 14.09. abends auch die
Füll-Erkennung repariert wurde (`execution/engine.py:800`) — sie ist
die einzige, die eine Börse immer hat.

`execution/engine.py: bestand_einstand()` geht die Ausführungen von neu
nach alt durch und sammelt die Käufe, bis ihre Summe die vorhandene
Menge deckt. Das ist eine **„zuletzt gekauft"-Annahme**: exakt richtig,
solange nicht zwischendurch verkauft wurde, sonst eine Näherung.
Deshalb meldet die Funktion mit, ob sie Verkäufe gesehen hat.

### Drei Fälle, in denen bewusst nichts angelegt wird

| Fall | Warum |
|---|---|
| Kein belegbarer Einstand | Ein Stop-Loss auf geratener Zahl **sieht aus wie Schutz und ist keiner**. Lieber ein lauter Alarm |
| Menge unter der Börsen-Mindestmenge | Ein Stop-Loss, der nicht verkaufen kann, scheitert bei jedem Auslösen — eine Dauerbaustelle |
| Position existiert bereits | Sonst ginge der echte Einstand einer laufenden Position verloren |

---

## 6.13 Der Fibonacci-Ausstieg — die zweite Hälfte

**Stand: 15.09.2026.** Bis zu diesem Tag stieg der Bot nach Svens
Verfahren **ein** und nach dem alten Schema **aus**.

### Woran es auffiel

Der erste echte Handel nach dem Einschalten des Tors sah so aus:

```
05:32  BTC übernommen, Einstand 79.202,74 $
05:32  STOP-LOSS TRIGGERED (-2,26 % ≤ -2,0 %)
05:34  ETH gekauft — Grund: Fraktal-Konfluenz, GOLDEN POCKET
```

Einstieg im Golden Pocket, Ausstieg per starrer Prozentmarke. Eine
Suche über `runtime/exit_monitor.py` ergab **null Treffer** für
Fraktale, Konfluenz oder Golden Pocket. Verkauft wurde allein nach
Stop-Loss, Trailing, Breakeven-Sperre.

Sven: *„das system vervollständigen damit er komplett nach dem neuen
muster handelt […] im ein und ausstieg mit fibonacci zonen."*

### Die Rechnung

Gekauft wird im Rücksetzer einer **Aufwärtswelle** (Tief → Hoch). Die
Ziele sind Verlängerungen genau dieser Welle, gemessen vom Tief:

| Ziel | Rechnung | bei Welle 100 → 200 |
|---|---|---|
| 1,000 | Tief + Spanne × 1,000 | **200,00** — das Wellenhoch |
| 1,272 | Tief + Spanne × 1,272 | 227,20 |
| 1,618 | Tief + Spanne × 1,618 | 261,80 |

Die Verhältnisse stammen aus `FIB_VOR`
([chartanalyse.py:233](features/chartanalyse.py:233)) und sind dort an
Marks eigenen Charts nachgerechnet — Abweichung 0,01 $ über vier
Raster.

**Deckt Ziel 1 die Kosten?** Kauf im Golden Pocket bei 138,20, Ziel bei
200,00 — das sind +44,7 %, nach 0,505 % Gebühren +44,2 %. Reichlich.

### Ein Punkt, der leicht schiefgeht — Marks Richtung

`fibonacci_ziele()` in `chartanalyse.py` legt die Verlängerungen nach
**Marks** Konvention an: über den *älteren* Anker hinaus. Bei einer
Aufwärtsbewegung zeigt Marks 1,618 deshalb nach **unten**.

Das ist für *seine* Frage richtig (wohin läuft die Korrektur) und für
*unsere* falsch (wohin läuft der Gewinn). Deshalb rechnet
`features/fraktal_ziele.py` eigens und ruft jene Funktion **nicht** auf.

> Wer dort die Richtung gedreht hätte, um hier ein Ziel zu bekommen,
> hätte Marks Gegenprobe (`mark_gegenprobe.py`) still zerstört — und es
> hätte niemand gemerkt, bis die nächste Messung andere Zahlen liefert
> als die letzte.

### Die Kette, die dafür nötig war

Damit der Ausstieg die Kaufwelle kennt, braucht es drei Glieder — und
das dritte ist das, das man vergisst:

1. **Das Tor** hängt die Welle an jede Stufe (`fraktal_tor.py`)
2. **Der Kauf** schreibt sie an die Position (`app.py`, nach dem Fill)
3. **Die Whitelist** in `state_manager.auto_save()` führt sie mit

Ohne Glied 3 wäre die Welle nach jedem Neustart weg und der Ausstieg
fiele **still** auf die alten Prozentmarken zurück. Das ist wörtlich
die Falle von Befund 88.

Damit ist auch der offene Punkt aus 6.10 geschlossen: *„Das Swing-Tief
der Kaufzone ist an der Position nicht gespeichert."* Jetzt ist es das.

### Ein Fehler, der fast durchgerutscht wäre

Das Fibonacci-Ziel wurde zunächst als `elif` in die Ausstiegskette
eingefügt, direkt vor dem Trailing-Zweig:

```python
if   not sell_reason and pnl_pct <= -sl:        # Stop-Loss
elif not sell_reason and tp_pct > 0 ...:        # Take-Profit
elif not sell_reason and pos.get("welle_hoch"): # Fibonacci-Ziel
elif not sell_reason and coin_mode == "SL":     # Trailing  ← nie erreicht
```

Sobald eine Position eine Kaufwelle trug, traf der Fibonacci-Zweig zu —
**auch wenn das Ziel noch weit weg war und er gar keinen Verkaufsgrund
setzte.** Die Kette war damit beendet. Trailing und Breakeven-Sperre
wurden nie mehr geprüft.

Sichtbar geworden wäre das erst, wenn ein Gewinner ungesichert bis in
den Stop-Loss zurückgelaufen wäre — also genau dann, wenn es Geld
kostet. Behoben: `if` statt `elif`. Jedes Glied prüft ohnehin
`not sell_reason`, die Reihenfolge bleibt, aber ein nicht zutreffender
Zweig bricht die Kette nicht mehr ab.

### Was bewusst **nicht** gebaut ist

Gestaffelte Teilverkäufe (40 % bei 1,0 / 30 % bei 1,272 / 30 % bei
1,618). Zwei harte Gründe:

1. Der Verkaufspfad ist auf Ganz-oder-nichts gebaut — nach einem
   Verkauf räumt `exit_monitor.py:588` die Position über
   `record_result()` atomar weg. Ein Teilverkauf bräuchte einen Umbau
   dieser Kette, und ein halb umgebauter Verkaufspfad ist ein
   Kapitalrisiko, kein Feature.
2. Bei der aktuellen Kontogröße trägt es nicht: 30 % der ETH-Position
   vom 15.09. wären 0,00126 ETH, rund 3 $ — unter der
   Börsen-Mindestordergröße. Der Teilverkauf würde scheitern und die
   Position stehen lassen.

Die Anteile stehen als `ANTEILE` in `fraktal_ziele.py` dokumentiert,
sind aber an **keiner** Stelle angeschlossen. Sie sind zudem nicht
gemessen, sondern gesetzt.

### Der Regime-Filter

Gleichzeitig abgeschaltet (Epoche L3). Der Grund steht im Log des
15.09.: Das Tor meldete stundenlang „Einstiegspreis bestätigt", und
jedes Mal kam danach `BUY blockiert — 3/2 Bestätigungen`. Der Bot
handelte seit 05:34 nicht mehr.

**Ehrlich dazu:** Der Filter *ist* gemessen, und die Messungen sprachen
für ihn (15.08.: geblockte Käufe −0,64 % über 99 Stunden). Aber beide
Messungen entstanden **ohne** Fraktal-Tor davor — damals blockte er
Trendfolge-Käufe am Hoch, also genau die schlechten. Jetzt kommt vor
ihm ein Tor, das nur in Rücksetzern kauft.

> Das macht das Abstellen nicht richtig. Es macht die alte Zahl
> ungültig. Was der Filter mit einem Tor davor noch bringt, ist
> ungemessen — und Epoche L3 ist die Messung.

**Einschalten:** `FRAKTAL_VERVOLLSTAENDIGEN.bat`, danach Bot neu
starten — der Ausstieg steckt im Programmtext, nicht in einer
Einstellung.

---

## 6.14 Vier stille Fehler — und warum drei davon gefährlicher waren als ein Absturz

**Stand: 15.09.2026.** Gefunden beim Durchsehen der Logs des laufenden
Echtgeld-Bots, nicht durch einen Ausfall.

### Der Anlass

Nach dem Einschalten des Fraktal-Systems sah alles gut aus. Eine
Auszählung aller Fehler- und Warnmuster seit dem Neustart förderte
trotzdem vier Dinge zutage — und die drei unauffälligsten waren die
schlimmeren.

### 1. Befund 69 war nur halb repariert

`live/live_runner.py` trug dieselbe Verwechslung, die am 14.09. im
Haupt-Handelspfad behoben wurde. Der Aufrufer übergibt
`config.exchange.ccxt_id` — und das ist die **Kursquelle** (Binance),
nicht die Handelsbörse (Bybit EU).

```
[ERROR] [LIVE] Verbindung fehlgeschlagen: binance
        {"code":-2008,"msg":"Invalid Api-Key ID."}
[ERROR] [APP] Live-Verbindung fehlgeschlagen → Paper
```

Der Bot meldete sich mit dem **Bybit-Schlüssel bei Binance** an. Der
Handel war nie betroffen — der läuft über `execution/engine.py`.
Betroffen waren die Statusanzeige `runner_mode` (meldete „paper",
während echtes Geld lief) und `StateRecovery`, das dadurch bei jedem
Start übersprungen wurde.

> Eine Reparatur ist nicht fertig, wenn *eine* Stelle stimmt. Sie ist
> fertig, wenn alle Stellen stimmen — und die findet man nur, wenn man
> nach dem Muster sucht, nicht nach dem Symptom.

### 2. Eine Handelssperre, die nichts sperrt

`live/state_recovery.py` schrieb bei Abweichungen ein Feld
`recovery_blockade` und protokollierte:

> „Handel bleibt blockiert, bis sie geklärt sind."

Eine Suche über das ganze Projekt findet dieses Feld an **genau einer
Stelle**: hier, beim Schreiben. Kein Handelspfad liest es je aus. Der
Bot hätte nach dieser Meldung ungebremst weitergehandelt.

**Das ist die gefährlichere Sorte Fehler.** Nicht ein fehlender Schutz,
sondern einer, der im Log *bestätigt*, dass er greift. Wer die Zeile
liest, hört auf zu suchen.

Dazu las der Abgleich `open_positions` — ein Feld, das außer dieser
Datei niemand benutzt. Der Bot führt seine Positionen in
`open_positions_backup`. Der Abgleich verglich den echten
Börsenbestand also gegen ein **leeres Feld**.

**Warum es nie auffiel:** Fehler 1 sorgte dafür, dass `run()` gar nicht
so weit kam. Zwei Fehler, die einander verdeckten.

Die Meldung heißt jetzt, was sie ist — eine Warnung. Ob daraus eine
echte Sperre wird, ist eine Entscheidung: Ein Bot, der sich selbst
anhält, ist nicht harmlos und braucht eine eigene Epoche.

### 3. Ein Wächter, der falschen Alarm gab

Der Signalpfad-Wächter (angelegt 06.08.) meldete regelmäßig:

```
12:14   486 → 486 geprüft      in Ordnung
12:19   1 von 538 fehlt        Warnung
12:24   590 → 590 geprüft      in Ordnung   ← Lücke zu
12:29   1 von 636 fehlt        Warnung
12:34   669 → 669 geprüft      in Ordnung   ← Lücke zu
```

Die Zähler sind **kumulativ**. Eine echte Lücke müsste bestehen
bleiben — sie schloss sich jedes Mal. Es war eine Momentaufnahme: ein
Kandidat, der beim Lesen gerade zwischen zwei Zählern unterwegs war.

**Warum das repariert gehört, obwohl nichts kaputt war:**

> Ein Wächter, der regelmäßig falschen Alarm gibt, wird überlesen — und
> dann fällt der echte Fall auch nicht mehr auf. Eine Warnung, die man
> wegzudrücken lernt, ist schlimmer als keine.

Jetzt wird erst gemeldet, wenn die Lücke bei **zwei** Prüfungen
hintereinander besteht. Geprüft in beide Richtungen
(`waechter_signalpfad_test.py`, 5 Prüfungen): Der echte Verlauf vom
15.09. löst keinen Alarm aus, ein wachsender **und** ein
gleichbleibender Verlust dagegen schon.

Außerdem wird `bus_errors.log` nur noch erwähnt, wenn die Datei
existiert. Vorher stand der Verweis immer da — und wer nachsah, fand
nichts und wusste nicht, ob das gut oder schlecht ist.

### 4. Ein roter Fehler bei jedem Start

```
[ERROR] [DATA] Client-Fehler (1. Versuch):
        module 'ccxt' has no attribute 'coinbasepro'
```

`data/market_data.py` baute eine feste Börsentabelle, die beim Anlegen
**jeden** Eintrag auswertete — auch ungenutzte. `ccxt.coinbasepro` gibt
es seit ccxt 4.x nicht mehr (hier läuft 4.5.48). Der Zugriff warf einen
`AttributeError`, *bevor* überhaupt eine Börse ausgewählt wurde — selbst
wenn Binance eingestellt war.

Der Fallback fing es auf, alles lief. Aber dieselbe Begründung wie
bei 3: Ein immergleicher roter Fehler beim Start bringt einem bei,
Fehler zu überlesen.

Jetzt wird die Börse per `getattr` erst geholt, wenn sie gebraucht
wird — kennt jede Börse, die ccxt hat, ohne Pflegeliste. Geprüft:
`bybit → bybit`, `binance → binance`, `coinbasepro → binance` mit
klarer Warnung statt Absturz.

### Das gemeinsame Muster

Drei der vier Fehler haben nichts kaputtgemacht. Sie haben die
**Wahrnehmung** beschädigt:

| Fehler | was er dem Leser einredete |
|---|---|
| Tote Handelssperre | „der Handel ist blockiert" — war er nicht |
| Wächter-Fehlalarm | „hier geht dauernd was verloren" — ging es nicht |
| Start-Fehler | „ein Fehler beim Start ist normal" — ist er nicht |

Alle drei machen dasselbe: Sie senken den Wert jeder künftigen Meldung.
Ein Log, in dem immer etwas Rotes steht, ist ein Log, das niemand mehr
liest.

---

# TEIL 7 — Das Cockpit: was du siehst, und was die Knöpfe tun

**Stand: 25.08.2026.** Am Code nachgelesen (`ui/main_window.py`), die zwei
Browser-Seiten im laufenden Betrieb abgefragt.

---

## 7.1 Vierzehn Reiter — die Landkarte

```
 📊 COCKPIT     die Münzkarten, Preise, offene Positionen, die Knöpfe
 🛒 MANUELL     von Hand kaufen und verkaufen
 📈 BACKTEST    Strategien auf alten Kursen durchrechnen
 ₿  BTC         der Sparplan-Bestand
 📜 HISTORY     die Handelsliste
 🤖 AGENTS      was die einzelnen Agenten gerade sagen
 ⚙️  SETTINGS    Einstellungen
 📋 LOG         das laufende Protokoll
 🕯️  CHARTS      Kerzencharts
 ─────────────────────────────────────────────────────────────
 🥇 METALLE     \
 🖥️  TERMINAL    |  die fünf abgekoppelten
 🌍 ZYKLUS      |  BEOBACHTUNGSREITER
 🌊 GELDFLUSS   |  (7.2)
 📐 ANALYSE     /
```

Die unteren fünf werden **einzeln in `try`-Blöcken** geladen
(`ui/main_window.py:198-240`). Fällt einer aus, erscheint er nicht — der
Bot läuft weiter. Im Protokoll steht dann etwa `[METALLE] Tab nicht
geladen: …`.

> Ein Anzeigefehler darf niemals den Handel anhalten. Deshalb steht jeder
> dieser Reiter in seiner eigenen Absicherung.

---

## 7.2 Die Beobachtungsreiter sind bewusst abgekoppelt

**Das ist eine Entscheidung, kein Versehen.** Fünf Reiter sind reines
Beobachtungsdeck: Sie lesen, zeigen an, und lösen **keinen** Handel aus.

| Reiter | zeigt | Datenquelle |
|---|---|---|
| 📐 ANALYSE | Zonen, Formationen, Signale samt Backtest-Zahlen | `chart_laeufe`, `chart_signale` |
| 🌊 GELDFLUSS | wohin das Geld im Markt fließt | `geldfluss_history.json` |
| 🌍 ZYKLUS | in welcher Marktphase wir stehen | `agents/cycle_theory.py` |
| 🖥️ TERMINAL | Zielgrößen, Freeze-Stand, Systemzustand | `config_zielgroessen.json`, Telemetrie |
| 🥇 METALLE | Gold und Silber | `metals/metals_data/` |

**Warum abgekoppelt:** Der ANALYSE-Reiter zeigt Chartsignale mit rund 69 %
Trefferquote. Sie sind trotzdem **nach Kosten negativ** — 0 von 245
Messläufen liegen im Plus (Teil 6, Abschnitt 6.7). Wäre der Reiter
angeschlossen, hätte der Bot danach gehandelt.

> Anzeigen heißt nicht handeln. Erst messen, dann anschließen — und dieser
> Reiter ist der Beleg, dass die Reihenfolge richtig ist.

---

## 7.3 Die Knöpfe und was sie wirklich tun

| Knopf | was passiert |
|---|---|
| **▶ STARTEN** | startet den Handel — wird zu **STOPPEN**, wenn er läuft (aber siehe 7.4) |
| **VERKAUFEN** | verkauft die gewählte Position sofort, von Hand |
| **🔓 NUR POSITIONEN SCHLIESSEN** | schließt alle offenen Positionen, hält den Bot aber nicht an |
| **🗑️ SESSION ZURUECKSETZEN** | setzt die laufende Sitzung zurück — **die Handelshistorie bleibt** |
| **💾 State speichern** | schreibt den Zustand sofort weg, statt auf die 30-Sekunden-Automatik zu warten |
| **💾 EINSTELLUNGEN SPEICHERN** | übernimmt Stop-Loss, Trailing und Positionsgröße |
| **🌐 Dashboard (localhost:5070)** | öffnet die Browser-Übersicht des Bots (7.5) |
| **🔬 Analyse-Cockpit (8170)** | öffnet die zweite Übersicht, die nur misst (7.5) |
| **▶ EINZELTEST** / **🏆 MULTI-COIN TEST** | Rückrechnung auf alten Kursen, ändert nichts |
| **⚡ OPTIMIZER** | **bewusst stillgelegt** — `backtest/optimizer.py` |
| **Stop-Loss-Analyse** | startet `stoploss_analyse.py`, reine Auswertung |
| **Trading-Akademie**, **Quiz starten**, **Tages-Lektion** | Lernteil, ohne Verbindung zum Handel |

**Die Risiko-Leiste oben im Cockpit** (`ui/main_window.py:246`) zeigt drei
Felder zum Ändern: Stop-Loss %, Trailing % und Positionsgröße. Die Werte
stehen heute auf **2,5 %**, **1,0 %** und **30 %**.

> **Achtung, Messfenster.** Diese drei Felder ändern das *Verhalten* des
> Bots. Solange das Messfenster läuft (bis 18.09.), setzt jede Änderung
> hier die Zählung auf null. Anschauen ja, verstellen nein.

---

## 7.4 Der Stopp-Knopf — was er tat, und was er seit dem 25.09. tut

> **✅ Behoben am 25.09.2026, Epoche `L6_abschalten_speichert`.**
> `live/watchdog.py` hat jetzt ein `stop()`, der Abschaltvorgang läuft
> durch, und der Positionsstand wird beim Beenden wieder gespeichert.
> **Der Knopf darf benutzt werden.** Der Rest dieses Abschnitts
> beschreibt, was vorher galt — er bleibt stehen, weil die Ursachenkette
> lehrreich ist.
>
> Vorher hat es noch einmal zugeschlagen, und diesmal **belegt statt
> hergeleitet**: Am 25.09. um 17:15 klickte Sven im Papierbetrieb auf
> Stopp, `data_store/jobs/bot_konsole.log` führt den vollständigen
> Traceback. Ein Befund, der vier Wochen nur auf dem Papier stand, wurde
> damit zum Vorfall.
>
> Ein **Nebenfund** kam bei der Reparatur heraus: `check()` — die
> Methode, die tote Threads neu startet — wird von **keiner Stelle im
> Projekt gerufen**. Die vier einzigen Fundstellen von `watchdog` sind
> `app.py:63` (Import), `app.py:554` (Erzeugung), das neue `stop()` und
> `app.py:4862` (`get_status`). Die Neustart-Funktion ist toter Code und
> hat nie gearbeitet. Sie scharfzuschalten ist eine eigene
> Verhaltensänderung und braucht eine eigene Messung — deshalb wurde sie
> hier **nicht** mitgemacht.

**Befund 72, SICHER.** Wenn du auf **STOPPEN** drücktest, stürzte der
Abschaltvorgang ab, bevor der Positionsstand gespeichert wurde:

```
ui/main_window.py:3229   self.engine.stop()
app.py:4357              self.watchdog.stop()
                         AttributeError: 'Watchdog' object has no attribute 'stop'
```

`live/watchdog.py:9` hat die Methoden `watch`, `check` und `get_status` —
**kein `stop()`**. Es hat nie eins gegeben.

**Was dadurch nie ausgeführt wird:** das Einsammeln und Speichern des
aktuellen Positionsstands — also genau der Doppelverkauf-Fix vom 13.08.

Und weil `self._running = False` **vor** dem Absturz gesetzt wird, greift
beim zweiten Klick die Sperre ganz oben in der Funktion: **Ein zweiter
Versuch tut gar nichts mehr** und sieht dabei ruhiger aus als der erste.

> **~~Bis zur Epochengrenze gilt: den Bot nicht über den Knopf stoppen.~~**
> *Diese Einschränkung ist seit dem 25.09.2026 aufgehoben (Epoche L6).*
> Sonst wurde der Positionsstand nicht gespeichert, und der nächste Start
> konnte eine bereits verkaufte Position zurückholen. Im Papierhandel
> kostet das falsche Zahlen — live würde der Bot Münzen verkaufen, die er
> nicht mehr besitzt.

Die vollständige Ursachenkette steht in `GEFUNDENE-PROBLEME.md` 72.

---

## 7.5 Die zwei Übersichtsseiten im Browser

Es gibt **zwei**, und sie beantworten Verschiedenes:

| | Port **5070** | Port **8170** |
|---|---|---|
| Name | Web-Dashboard | Analyse-Cockpit |
| gestartet von | `app.py:463`, läuft mit dem Bot | `python cockpit_server.py`, von Hand |
| zeigt | den **laufenden Zustand** — Kontostand, Positionen, Modus | die **Auswertung** — Ausstiegswege, Erwartungswert, Zielgrößen |
| bindet auf | alle Schnittstellen | **nur 127.0.0.1** — kein Zugriff von außen |
| steht in | `dashboard.port` | `dashboard.cockpit_port` |

**Am 25.08. beide geprüft:** `/api/status` antwortet mit HTTP 200,
**63 Feldern und keinem einzigen Fehlertext**; das Cockpit liefert die Seite.
*(Damals noch auf 5050 und 8110.)*

### [25.09.2026] Warum es jetzt 5070 und 8170 sind — Befund 111

Auf diesem Rechner läuft der **v6-Papier-Bot daneben** und hält 5050
(`0.0.0.0`) und 8110 (`127.0.0.1`). Beide Zahlen standen in v7 an **neun
Stellen fest im Quelltext**. Folge:

- v7 meldete „Dashboard `http://localhost:5050`" — der Browser zeigte die
  Zahlen des **v6-Bots**.
- Der Cockpit-Knopf prüfte nur, ob auf 8110 **etwas antwortet**. Es
  antwortete v6. Also meldete er „läuft bereits", öffnete v6-Daten und
  startete nie ein eigenes Cockpit.

Eine Anzeige, die die Zahlen eines anderen Bots zeigt und dabei behauptet,
die eigenen zu zeigen, ist schlimmer als keine Anzeige — dieselbe Sorte
Fehler wie das Guthaben-Feld, das im Echtbetrieb 500 $ anzeigte.

**Die Zahlen stehen jetzt an einer Stelle:** `data_store/config.json` →
`dashboard.port` und `dashboard.cockpit_port`. Alles andere liest von dort
— `app.py`, die beiden Knöpfe in `ui/main_window.py`, `cockpit_server.py`.
`dashboard.cockpit_port` musste zusätzlich als **Feld** in
`config/settings.py` angelegt werden: `AppConfig._from_dict` übernimmt nur
Schlüssel, für die `hasattr(section, k)` gilt — ein bloßer Eintrag in der
JSON wäre **still verworfen** worden, genau wie beim Tagesverlust-Wächter.

Die Rückfallwerte in `ui/dashboard.py` und `ui/ngrok_dashboard.py` wurden
auf 5070 mitgezogen. Ein Rückfall darf nicht still auf dem Anschluss des
anderen Bots landen.

### Warum diese Prüfung nicht selbstverständlich ist

Bis zum 13.08. lieferte `/api/status` **ausnahmslos HTTP 500**. Das
Web-Dashboard auf Port 5050 hatte damit **noch nie Daten angezeigt** — seit
dem allerersten Commit.

Die Ursache war eine Zeile, die eine Methode aufrief, die es nicht gibt
(`order_manager.get_status()` statt `get_stats()`). Weil die ganze Antwort
**ein einziges Dict-Literal** war, ließ dieser eine Fehlschlag die
**gesamte** Statusabfrage scheitern.

**Und es fiel niemandem auf**, weil das Cockpit-Fenster die Objekte direkt
liest und deshalb normal weiterlief. Ein stiller Totalausfall.

Seitdem werden die 63 Statusfelder **einzeln** eingesammelt. Fällt eines
aus, steht der Fehlertext **im Feld** — sichtbar, nicht versteckt — und die
übrigen kommen trotzdem durch.

> **Ein Fehler, der laut kracht, kostet eine Stunde. Ein Fehler, der still
> ist, kostet Monate.** Dieselbe Lehre wie beim verschluckten Kaufsignal in
> Teil 2, Abschnitt 2.9.

---

## 7.6 Fünf Anzeigefehler, die es gab — und was sie lehren

Alle fünf sind behoben. Sie stehen hier, weil sie dasselbe Muster zeigen:
**eine Anzeige, die etwas Falsches zeigt, ist schlimmer als eine, die
nichts zeigt** — denn man merkt es nicht.

| Was | Was man sah | Was wirklich war |
|---|---|---|
| **Metall-Reiter** (Befund 57) | eine laufende Position | nur die **Tagesempfehlung** — zwei verschiedene Dinge gleich dargestellt |
| **Protokoll-Reiter** | „BUY" wie ein ausgeführter Handel eingefärbt | auch Vorschläge und **Ablehnungen** trugen das Wort |
| **Analyse-Chart** | ein zu kleiner, unlesbarer Chart | nicht zu klein, sondern **falsch skaliert** |
| **Übersichtsseiten** | Stand vom Mai und vom Juli | wurden nie neu erzeugt |
| **Terminal-Reiter, Epochen-Block** (26.09.) | „Epoche E6.1 (seit 14.07.)", Tage **74 / 14 in Grün** | die Epoche des **Papier-Ordners**. In v7 lief L7, einen Tag alt |

### Der fünfte, und warum er der gefährlichste der Reihe war

`ui/terminal_tab.py` trug `E61_START = "2026-07-14"` fest im Quelltext, dazu
die Ziele **14 Tage** und **15 Verkäufe**. Das ist die Zeitrechnung des
Papier-Ordners — Messbeginn der Epoche E6.1 im Juli.

In `v7` zeigte der Block deshalb ein Fenster an, das es hier **nie gab**.
Und weil 74 Tage die Marke von 14 überschreiten, färbte die Zeile **grün**:

```
--- Epoche E6.1 (seit 14.07.) ---
| Sells             | 0 / 15                 |
| Tage              | 74 / 14                |   <- grün, "Ziel erreicht"
```

Eine grüne Meldung „genug Tage gemessen" — während die laufende Epoche einen
Tag alt war und das Journal am 25.09. geleert wurde. Das ist nicht nur eine
falsche Zahl, sondern eine **falsche Entwarnung** in genau dem Feld, das
sagen soll, ob die Datenlage trägt.

**Jetzt** kommt der Beginn aus der jüngsten Epochengrenze
(`_freeze_status()` liest `config_epochs.json`) und die Fallzahl-Schwelle aus
`config_zielgroessen.json` → `mindest_fallzahl`, derzeit **30**. Das
Tage-Ziel ist **bewusst entfallen**: die 14 Tage gehörten zu E6.1, nicht zu
jeder künftigen Epoche. Die Tage werden gezeigt, aber nicht bewertet.

```
--- Epoche L7_svens_drei_entscheidungen (seit 25.09.) ---
| Sells             | 0 / 30                 |
| Tage              | 1                      |
```

> **Ein festes Datum in einer zweiten Datei ist eine zweite Wahrheit, und
> die geht irgendwann falsch aus.** Dasselbe Muster wie Befund 90, wo ein
> hartes Datum in den `DAUERREGELN` den Freeze für beendet erklärte.

*Ergänzung, kein neuer Fund:* Die Chronik vermerkt diese Reparatur bereits
für die Zeile „Epoche" weiter unten im selben Reiter — *„liest jetzt die
jüngste Epochengrenze, damit altert er nie wieder"*. Der E6.1-Block war
dabei übersehen worden und lief weiter auf dem Juli-Datum. Die lokalen
Variablen hießen ebenfalls noch `e61…` und heißen jetzt `ep_…`.

Und der Knopf, der weg musste: Ein Bedienelement löste eine Aktion aus, die
niemand erwartete. Es gibt zu jedem eine Regel dahinter —

> Ein Knopf, dessen Wirkung man erklären muss, ist der falsche Knopf.

**Der tote Knopf, der nützlich wurde:** Der stillgelegte
TradingView-Webhook hinterließ eine Schaltfläche ohne Funktion. Statt sie zu
entfernen, liegt jetzt das **Analyse-Cockpit auf Port 8110** darunter — die
zweite Übersichtsseite aus 7.5.

---

## 7.7 Was du im Cockpit **nicht** tun solltest

| | Warum |
|---|---|
| Den Bot über **STOPPEN** anhalten | Befund 72 — der Positionsstand wird nicht gespeichert (7.4) |
| Stop-Loss, Trailing oder Positionsgröße verstellen | Verhaltensänderung, setzt das Messfenster auf null |
| Den **OPTIMIZER** starten | bewusst stillgelegt |
| Aus einem Beobachtungsreiter auf den Handel schließen | sie sind abgekoppelt, absichtlich (7.2) |

**Was du gefahrlos tun kannst:** alles Anschauen, die Rückrechnungen, die
Akademie, die zwei Browser-Seiten, `💾 State speichern`.

*Früher verstreut in ALT 4.4, 4.6, 4.38, 4.39, 4.41, 4.42, 4.62, 4.81, 4.85,
4.87, 4.92, 4.96, 4.122.*

---

# TEIL 8 — Der Werkzeugkasten: welcher Befehl bringt welches Ergebnis

**Stand: 24.08.2026.** Dieser Teil beantwortet genau eine Frage:
*Ich will etwas wissen — was muss ich starten, und wie lese ich das Ergebnis?*

Alles hier ist **nachgeprüft**, nicht abgeschrieben: Jede genannte Datei wurde
am 24.08. daraufhin geprüft, ob es sie noch gibt. Aufruf immer aus dem
Projektordner.

> **Warum es `.bat`-Dateien gibt und nicht nur Befehle:** Der Ordner heißt
> `trading_imperium_v6(21)` — **mit Klammern**. Ohne Anführungszeichen bricht
> die Eingabeaufforderung genau daran ab. Das war der Grund, warum es früher
> „irgendwie nicht funktioniert" hat. In jeder `.bat` steht `cd /d "%~dp0"`,
> das fängt es ab.

---

## 8.1 Zum Doppelklicken — ohne Befehlszeile

Diese fünf brauchst du regelmäßig. Kein Tippen, kein Ordnerwechsel.

| Datei | Wann du sie anklickst |
|---|---|
| **`start_bot.bat`** | Bot starten |
| **`SAMMLER_PRUEFEN.bat`** | Wenn du wissen willst, ob alles sammelt |
| **`SAMMLER_NEUSTART.bat`** | **Nur** wenn die Prüfung „läuft — ABER mit altem Programmtext!" meldet |
| **`VOLLSTAENDIGKEIT.bat`** | Haben wir am Stichtag wirklich alle Daten? |
| **`datenbank_ansehen.bat`** | Menü: Käufe, Ablehnungsgründe, Verlauf |

**Zwei für später:** `freigabe_pruefen.bat` (die Freigabekriterien) und
`TESTNETZ_PROBE.bat` (Bybit-Testnetz).

**Eine, die du nicht anfasst:** `sammler_taeglich.bat` — die startet die
Windows-Aufgabenplanung selbst.

### Zwei Dateien tragen eine Warnung im Namen

```
ZZ_NICHT_BENUTZEN_positionsverlauf_start.bat
ZZ_NICHT_BENUTZEN_schatten_universum_stop.bat
```

**Befund 74, gefunden am 24.08.2026.** Beide suchen nach `pythonw.exe`, die
Sammler laufen aber als `python3.13.exe` (nachgeprüft, PID 3536 und 6056).
Folge: Die Stopp-Datei stoppt **nichts** und meldet trotzdem Erfolg. Die
Start-Datei sieht den laufenden Sammler nicht und startet einen **zweiten** in
dieselbe Datenbank. `SAMMLER_PRUEFEN.bat` und `SAMMLER_NEUSTART.bat` erkennen
beide Prozessarten richtig — nimm die.

`schatten_universum_start.bat` funktioniert einwandfrei (sie ruft
`sammler_pruefen.py --starten`), ist aber überflüssig.

*Früher: 4.88, ergänzt um Befund 74.*

---

## 8.2 Die fünf Befehle für den Alltag

| Befehl | Was du bekommst |
|---|---|
| `python status.py` | Bot-Übersicht auf einen Blick: läuft er, Kontostand, offene Positionen, letzte Trades |
| `python offen.py` | Die offenen Punkte aus `OFFEN.md`, kurz. `--alle` zeigt auch B/C/D |
| `python sammler_pruefen.py` | Schreibt jeder Sammler das, was die Auswertung braucht? |
| `python prozess_frische.py` | Läuft irgendwo noch alter Programmtext? Beantwortet „muss ich neu starten?" |
| `python stichtag.py` | Reichen die Daten bis zum Stichtag, wo stehen die Zielgrößen, ist der Code unverändert |

> **Die zwei Frische-Werkzeuge gehören zusammen.** `prozess_frische.py` sagt,
> ob ein Prozess mit altem Code läuft. `sammler_pruefen.py` sagt, ob er
> überhaupt noch etwas Brauchbares schreibt. Am 19.08. war
> `positionsverlauf.py` genau dazwischen: der Prozess war weg, die Datenbank
> sah frisch aus, weil die letzte Zeile 20 Minuten alt war.

**Der Stichtag steht in `config_zielgroessen.json`** (`messfenster_ende`), nicht
im Programmtext. Aktuell: **18.09.2026**. Wer ihn ändert, ändert ihn dort —
sonst laufen zwei Wahrheiten nebeneinander.

### `stichtag.py` im Einzelnen

```
python stichtag.py               volle Prüfung
python stichtag.py --kurz        nur die Ampel
python stichtag.py --selbsttest  Gegentest in beide Richtungen
```

Es beantwortet vier Fragen und sagt bei jeder, ob sie bereit ist:

| | Frage | Woran gemessen |
|---|---|---|
| **A** | Reichen die Daten? | Verkäufe im Messfenster, Positionsverläufe, Schatten-Signale, Ausstiege mit Nachlauf — jeweils mit Mindestzahl und Begründung |
| **B** | Wo stehen die Zielgrößen? | alle fünf gegen `config_zielgroessen.json` |
| **C** | Ist der Code noch unverändert? | liest die echten Werte aus `risk/exit_rules.py` und `features/regime_adaptiv.py` und zählt die Dateien mit der alten Kostenannahme 0,32 |
| **D** | Was muss ein Mensch entscheiden? | acht Entscheidungen, jede mit Verweis auf ihre Grundlage |

**Punkt C ist der wertvollste.** Er belegt, ob eine geplante Korrektur schon
passiert ist — statt es zu glauben.

> Was man von Hand prüfen muss, prüft man einmal. Was ein Programm prüft, wird
> jedes Mal geprüft.

*Früher: 4.86 A und 4.65. Stichtag am 24.08. von 27.08. auf 18.09. berichtigt.
Der Messstand vom 19.08. aus 4.65 gehört nach Teil 10 und wartet dort.*

---

## 8.3 Etwas ansehen

| Befehl | Was passiert |
|---|---|
| `python cockpit_server.py` | **Das Dashboard.** Kleiner Webserver, dann im Browser **http://localhost:8110**. Bindet auf 127.0.0.1 — nur dieser Rechner. Beenden mit Strg+C |
| `python bot_navigator.py` | Baut `bot_uebersicht.html` — eine anklickbare Karte des Projekts |
| `python datenexport.py` | Schreibt **alle** gemessenen Daten in eine Excel-Mappe (`BOT-DATEN_*.xlsx`) |
| `python brain_view.py` | Was das lernende Gehirn über die Strategien gespeichert hat |
| `python epoch_report.py` | Epochenvergleich — was hat sich seit welcher Änderung geändert |
| `python impact_report.py` | Welche Änderung was gebracht hat |

*Früher: 4.86 B und 4.87.*

---

## 8.4 Die Auswertungen — jede beantwortet genau eine Frage

Alle sind reine **Leseoperationen**. Sie ändern weder Bot noch Verhalten und
sind deshalb auch während des Freeze erlaubt.

| Befehl | Die Frage dahinter |
|---|---|
| `python regime_filter_messung.py` | Ist der Kauf-Blocker sein Geld wert? (siehe 8.9) |
| `python stoploss_analyse.py` | Wo genau entsteht der Verlust, und was würde helfen? |
| `python drawdown_auswertung.py` | Wie tief ging es vom Höchststand herunter? |
| `python gesamtauswertung.py` | Alles Gemessene in einem Bericht |
| `python pnl_check.py` | Wann und wo ist das Minus entstanden? |
| `python e7_auswertung.py` | Der große Bericht zur laufenden Epoche |
| `python e7_gegenprobe.py` | Dieselben Zahlen, unabhängig zweimal gerechnet |
| `python merkmale_auswertung.py` | Welche Indikatorwerte gingen steigenden Kursen voraus? |
| `python schwelle_vergleich.py` | Hatte der lernende Wächter recht, als er strenger stellte? |
| `python maker_schatten.py` | Lohnt der Wechsel auf Warteaufträge (Limit-Order)? |
| `python schatten_leiter_auswertung.py` | Schatten-Ausstiegsregel gegen die echte Leiter |
| `python gebuehren_gegenprobe.py` | Wird die Kaufgebühr doppelt abgezogen? |
| `python telemetrie_frage.py` | Warum hat der Bot gekauft — oder eben nicht? |
| `python ml_notizbuch_auswertung.py` | Was hätte das KI-Modell entschieden, wenn es gedurft hätte? |
| `python ensemble_notizbuch_auswertung.py` | Dasselbe für das Modell-Ensemble |
| `python chartanalyse_backtest.py` | Trifft die Chartanalyse überhaupt? **Läuft nicht von selbst mit** |
| `python chart_zeichentest.py` | Zeichnet den Analyse-Chart unsichtbar und misst nach, ob die Linien sauber sitzen (siehe 6.9). Dauert acht Minuten — für schnell: `--selbsttest` oder `--gegentest` |
| `python provider_vergleich.py` | Wie steht unser Bot gegen sieben blind getestete Signalanbieter — und gegen unsere eigenen Zielgrößen? (siehe 10.9) |
| `python nachlauf_rueckwirkend.py --stand` | Wie viele Ausstiege haben ihren Nachlaufwert? |
| `python ausstieg_vergleich.py` | Welche Ausstiegsregel wäre besser gewesen? |
| `python rueckschlaege.py` | Wie oft und wie tief geht es zwischendurch zurück? |
| `python prognose_ruecktechnik.py --ziel 123000 --stichtag 2025-05-07` | Mit welcher Rechnung kam jemand auf seine Prognosezahl? (siehe 8.12) |
| `python schon_bekannt.py <begriff>` | Steht das schon in der Doku? Zwei Sekunden statt 12.600 Zeilen |

**Pflicht vor jeder Auswertung:** `python prozess_frische.py` — sonst wertest du
vielleicht Daten aus, die ein Prozess mit altem Programmtext geschrieben hat.

*Früher: 4.86 C.*

---

## 8.5 Die Sammler — was von selbst läuft

**Du musst nichts starten.** Seit dem 20.08. prüft der Bot beim Hochfahren die
zwei Dauerläufer und startet, **was nicht schon läuft** — geprüft an der
Prozessliste, nicht geraten. Im Log steht dann:

```
[SAMMLER] Schatten-Universum    laeuft schon - nichts zu tun
[SAMMLER] Positionsverlauf      gestartet ...
[SAMMLER]   OK   Positionsverlauf   laeuft
```

Der Bot beendet **nie** von selbst einen Prozess. Etwas Laufendes abzuschießen
ist eine Entscheidung, und die trifft niemand still im Hintergrund.

### Die neun Sammler und wofür sie gebraucht werden

| Sammler | wird gebraucht für | Prozess |
|---|---|---|
| Bot-Entscheidungen | Erwartungswert, Ablehnungsgründe, Zielgrößen | `app.py` |
| Merkmals-Schnappschuss | KI-Modell, Merkmalsauswertung | `app.py` |
| Marktlage stündlich | Regime-Auswertung, Zyklus-Reiter | `app.py` |
| Chartanalyse-Läufe | Trefferquote der Chartanalyse | **du selbst**, `chartanalyse_backtest.py` |
| Schatten-Ausstiege | Ausstieg bei −1 % gegen Aussitzen | `app.py` |
| Nachlauf nach Ausstieg | War der Ausstieg zu früh? (Befund 59/60) | `app.py` |
| Positionsverlauf | Ausstiegsregeln gegeneinander rechnen | `positionsverlauf.py` |
| Schatten-Universum | Welche Münze ihre Reibung verdient | `schatten_universum.py` |
| Hintergrund-Aufträge | Ist ein Hintergrundjob still gescheitert? | `app.py` |

### Das Schatten-Universum im Einzelnen

Es rechnet **stündlich für 18 Münzen** dieselbe Punktzahl aus wie der Bot —
**ohne zu handeln**. Damit lässt sich beantworten, welche Münze ihre Reibung
(Gebühr + Spanne) überhaupt verdient, ohne dafür Geld zu riskieren.

Es erledigt nebenbei zwei weitere Aufgaben, weil es der Prozess ist, der
nachweislich läuft:

| Takt | Was |
|---|---|
| stündlich | 18 Münzen bewerten und mitschreiben |
| stündlich | Nachlauf-Kurse nachtragen |
| täglich | Zahlenbuch als PDF und Markdown, `LAGE.md` |

**Warum es keine geplante Windows-Aufgabe dafür gibt:** Am 14.08. meldete die
Aufgabenplanung dreimal Erfolg und führte **nichts** aus. Der Pfad
`AppData\...\WindowsApps\python.exe` ist eine **0-Byte-Datei**, nur ein Verweis.
In der Benutzersitzung greift er, in der Aufgabenplanung nicht.

> Lieber einen Prozess, dem man beim Arbeiten zusehen kann, als drei, die
> behaupten zu arbeiten.

### Der Positionsverlauf

Zeichnet **alle 5 Minuten** auf, *wie* eine Position verlief — nicht nur, wie
sie endete. Ohne ihn lässt sich keine Ausstiegsregel gegen eine andere rechnen,
weil dafür der Kursverlauf **zwischen** Kauf und Verkauf fehlt.

### Der Nachlauf — was WÄRE passiert?

Zwei Fragen waren lange nicht beantwortbar, weil nach einer Entscheidung
niemand mehr hinsah: War der Stop-Loss richtig? Waren die Blockaden richtig?

Beide brauchen dasselbe: **den Kursverlauf nach der Entscheidung.**
`nachlauf.py` merkt sich jeden Ausstieg und stichprobenartig jede Blockade und
trägt nach, wie der Kurs **1, 4, 24 und 48 Stunden** danach stand.

| Ergebnis | Bedeutung |
|---|---|
| Kurs erholte sich | Stop war zu eng — Aussitzen wäre besser gewesen |
| Kurs fiel weiter | Stop war richtig — das Problem sitzt beim **Einstieg** |

Bei Blockaden nur eine Stichprobe, weil rund 98.000 Ablehnungen zu 99 %
dieselben Gründe im Endlostakt sind.

*Früher: 4.22, 4.25, 4.26, 4.27, 4.88, 4.99. Münzzahl am 24.08. von 12 auf 18
berichtigt.*

---

## 8.6 Die drei Bücher und wer sie schreibt

| Buch | Beantwortet | Wird erzeugt von |
|---|---|---|
| `BOT-HANDBUCH.md` / `.pdf` | *Wie arbeitet Teil X?* — dieses Buch | Hand + `python handbuch_pdf.py` |
| `ENTWICKLERHANDBUCH.md` / `.pdf` | *Was ist wann passiert?* — die Chronik | `tickets.txt` + `python handbuch_pdf.py ENTWICKLERHANDBUCH.md` |
| `ZAHLENBUCH.md` / `.pdf` | *Welche Zahl, aus welcher Quelle, aus wie vielen Fällen?* | `python zahlenbuch.py`, täglich automatisch |

**Die PDF nie von Hand ändern.** Sie werden erzeugt.

### `LAGE.md` — die Eingangstür

Beantwortet auf einer Seite drei Fragen: **Was läuft gerade?** (echte
Prozessprüfung, keine Behauptung) · **Welche Daten existieren?** (jede Datenbank
mit Zeilenzahl) · **Was gilt gerade?** (Münzen, Modus, Regel-Schalter, Epoche).

Sie wird **nie von Hand gepflegt** — `python lage_erzeugen.py` liest den
tatsächlichen Zustand der Festplatte. Sie kann deshalb nicht veralten, solange
man sie erzeugt.

Sie warnt auch: Fehlt der `regel_modi`-Block, steht dort
**„BLOCK FEHLT — alle fallen auf ACTIVE!"** statt einer harmlosen Liste.

### Das Zahlenbuch — zwei Ausgaben, ein Lauf

```
python zahlenbuch.py        das ausführliche PDF (12 Abschnitte)
python zahlenbuch.py --md   die Kernzahlen als Markdown
```

- Das **PDF** ist die vollständige Fassung: Capture, Forschung, Chartanalyse,
  Datenqualität, Nachlauf, Indikatoren.
- Die **Markdown-Fassung** trägt die Zahlen zum *Nachschlagen* — Epoche,
  Zielgrößen, Ausstiegsverteilung, Datenlage. Sie steht in git, lässt sich
  zwischen zwei Tagen vergleichen, und **`schon_bekannt.py` durchsucht sie
  mit**. Eine Zahl, die dort steht, taucht bei jeder künftigen Befund-Prüfung
  auf.

Der tägliche Lauf (`job_zahlenbuch.py`) erzeugt **beide** und meldet Fehler,
wenn einer der drei Schritte scheitert:

```
OK   Zahlenbuch (PDF)      ZAHLENBUCH.pdf
OK   Zahlenbuch (Markdown) ZAHLENBUCH.md
OK   LAGE.md
```

> **Eine zweite Ausgabe desselben Berichts muss im selben Lauf entstehen wie
> die erste.** Sonst hat man zwei Wahrheiten mit verschiedenem Datum, und die
> ältere sieht genauso vertrauenswürdig aus.

### Das Zahlenbuch — die eingebaute Ehrlichkeit

- Jede Tabelle nennt ihre **Quelle** (Datenbank, Tabelle, Zeitraum)
- Unter 30 Fällen steht ausdrücklich **„Nicht entscheidbar"** dabei
- Die Notizbücher zeigen „auswertbar?" — unter 100 Notizen steht „noch nicht"
- Beim Schatten-Universum steht die Einschränkung mit im Dokument: Es misst
  Signal-Qualität, nicht Portfolio-Leistung

> Eine Zahl ohne Herkunft und Fallzahl ist keine Messung, sondern eine Meinung
> mit Nachkommastellen.

**Die Bücher dürfen nicht auseinanderlaufen.** Am 18.08. war die Handbuch-PDF
eine Woche älter als das Markdown — wer sie las, las einen alten Stand, ohne es
zu merken. `sammler_pruefen.py` zeigt deshalb am Ende, ob Markdown und PDF
gleich alt sind.

### Stimmen die Verweise im Handbuch noch?

```
python handbuch_zeilen_pruefen.py              alles
python handbuch_zeilen_pruefen.py --nur-fehler nur die Abweichungen
python handbuch_zeilen_pruefen.py --selbsttest Gegentest in vier Richtungen
```

Es hält **jede** Zeilenangabe des Buches gegen den echten Code: `funktion,
Zeile N`, `datei.py:N` und `(NNN Zeilen)`. Den Ordner erschließt es aus dem
Zusammenhang; bleibt ein Name mehrdeutig — `engine.py` gibt es dreimal —,
meldet es **unklar** statt zu raten.

Am 24.08. fand es beim ersten Lauf 7 von 8 falschen Verweisen im Rundgang.
Nach der Berichtigung: **86 von 86 stimmen.**

> Beim allerersten Lauf lag das Werkzeug an neun Stellen **selbst** falsch —
> es meldete "engine.py:575" als „Datei gibt es nicht", gemeint war
> `risk/engine.py`. Ein Prüfwerkzeug, das den Autor für seinen eigenen blinden
> Fleck rügt, ist schlimmer als keines. Deshalb der Gegentest in beide
> Richtungen, bevor man einer Ampel glaubt.

*Früher: 4.23, 4.24, 4.32, 4.57, 4.66. Chronik-PDF am 24.08. ergänzt.*

---

## 8.7 Vor dem Live-Gang

| Befehl | Was er prüft |
|---|---|
| `python go_live_check.py` | Die Freigabe-Prüfung: sind alle Bedingungen erfüllt? |
| `python vollstaendigkeit.py` | Haben wir am Stichtag alle Daten, die die Freigabe braucht? |
| `FELDER_NACHTRAGEN.bat` | Trägt fehlende Analysefelder nach — **nur bei gestopptem Bot** (siehe 8.7a) |
| `python testnetz_probe.py --pruefen` | Läuft der Weg zur Börse, ohne Echtgeld? |
| `python preflight.py` | Ist der Bot technisch bereit — Schlüssel, Verbindung, Konfiguration? |
| `python sicherung.py` | Sicherung des ganzen Projekts auf die zweite Festplatte |

`vollstaendigkeit.py` trennt zwei Dinge, die man leicht verwechselt:
**Freigabe-Felder** (hier darf nichts fehlen) und **Analyse-Felder** (Lücken
hier blockieren die Freigabe nicht, machen aber die nächste Verbesserung
unbeantwortbar). Stand 24.08.: alle zehn Freigabe-Felder zu 100 % gefüllt.

*Früher: 4.86 E und 4.120.*

---

## 8.7a Fehlende Analysefelder nachtragen

**Stand: 29.08.2026.** Svens Auftrag: *„trag die vier Felder nach bitte."*

### Wann du das brauchst

Wenn `VOLLSTAENDIGKEIT.bat` unter Punkt 2 Felder mit `!!` zeigt. Diese
Lücken blockieren die **Freigabe nicht** — die zehn Freigabe-Felder sind zu
100 % gefüllt —, aber sie machen Fragen unbeantwortbar wie *„wie lange lagen
die Verlierer im Depot?"*

### Der eine Satz, auf den es ankommt

> **Der Bot muss dabei AUS sein.**

`TradeJournal` (`core/state_store.py:108`) lädt das Journal **einmal beim
Start** in den Arbeitsspeicher und schreibt beim Speichern die **ganze
Datei** neu. Läuft er, ist jeder Nachtrag beim nächsten Handel weg.

Am 29.08. ausprobiert: geschrieben um **16:55:17**, vom Bot überschrieben um
**16:55:58**. **Einundvierzig Sekunden.** Und die Gegenprobe direkt nach dem
Schreiben meldete noch Erfolg — sie war richtig, nur zu früh.

> **Ein Nachtrag, der still verschwindet, ist schlimmer als einer, der gar
> nicht stattfindet: man hält die Lücke danach für geschlossen.**

Deshalb bricht das Werkzeug von selbst ab, solange `app.py` läuft. Es kann
nicht mehr lautlos danebengehen.

### So machst du es

**Reihenfolge ist alles:**

| | |
|---|---|
| 1 | **Bot beenden** — sein Fenster schließen |
| 2 | **`FELDER_NACHTRAGEN.bat`** doppelklicken, dann `2` wählen |
| 3 | **Bot wieder starten** — er liest die ergänzte Datei beim Start ein |

Die `.bat` prüft selbst, ob der Bot läuft, und sagt dir, wenn die
Reihenfolge nicht stimmt. Der **Probelauf** geht jederzeit — auch bei
laufendem Bot — und ändert nichts.

### Was es nachträgt — und was nicht

| Feld | Quelle | nachtragbar? |
|---|---|---|
| `position_id` | `positionen.pos_id` | **ja** |
| `haltedauer_min` | `geschlossen` minus `eroeffnet` | **ja** |
| `entry_strategie` | `positionen.strategie` | **nein** — Spalte ist bei allen 58 echten Positionen **leer** |
| `entry_score` | `positionen.score` | **nein** — Spalte ist `NULL` |
| `stop_initial`, `trailing_stop_pct`, `decision_id` | — | **nein** — stehen am *Kauf*, aber es gibt keine belastbare Verbindung Verkauf → Kauf (Befund 88) |

**Es sind also zwei Felder, nicht vier.** Die Vollständigkeitsprüfung nennt
vier, weil sie nur die *Herkunft* kennt, nicht den *Inhalt* der Spalte.

### Drei Sicherungen im Werkzeug

1. **Vorhandene Werte werden nie überschrieben.** Nur `None` wird gefüllt.
2. **Leer ist kein Wert.** Ohne diese Regel hätte `entry_strategie` bei 12
   Verkäufen eine **leere Zeichenkette** bekommen — das Feld hätte danach
   als „vorhanden" gezählt, ohne etwas zu enthalten. Die
   Vollständigkeitsstatistik wäre geschönt worden, ausgerechnet von dem
   Werkzeug, das sie verbessern soll.
3. **Nur eindeutige Zuordnungen.** Gleiche Münze, Schlusszeit innerhalb von
   600 Sekunden, und nur wenn es **genau einen** Kandidaten gibt. Gäbe es
   zwei, wäre das Ergebnis geraten.

Jeder nachgetragene Wert bekommt ein Feld `_nachgetragen` mit Datum, Quelle
und Feldliste. **Ein rekonstruierter Wert darf nicht wie ein gemessener
aussehen.**

### Ein Irrweg, der fast durchgegangen wäre

Erster Versuch der Zuordnung: **FIFO** — gleiche Münze, ältester offener
Kauf. Ergebnis sah glänzend aus: **62 von 62 zugeordnet**, 46,8 %
nachtragbar.

Die Stichprobe hat es widerlegt — die **Mengen passen nicht**:

```
Verkauf SOL 1,357058   gegen   Kauf SOL 0,714138
Verkauf ETH 0,093611   gegen   Kauf ETH 0,027693
```

Positionen werden per Nachkauf aufgebaut und teilweise verkauft. **Ein Kauf
entspricht keinem Verkauf.**

> **Eine Zuordnung, die 100 % meldet, ist verdächtig, nicht beruhigend.**
> Die Zahl kam zustande, weil *immer* irgendein Kauf übrigbleibt — nicht,
> weil er der richtige war.

### Nachtrag 11.09.2026 — warum `entry_score` leer war, und wo es abriss

Am 29.08. stand hier: *„`entry_strategie` und `entry_score` haben in der
Quelle nichts stehen."* Das stimmte, aber die Frage **warum** war offen —
und zwar mit einer klaren Begründung: *„dafür bräuchte es eine offene
Position zum Mitlesen, und es war keine da."*

**Am 11.09. war eine da.** Die Antwort steht seitdem fest.

Die Kette hat vier Glieder. `app.py:1904` schreibt den Score beim Kauf an
die Position, `runtime/exit_monitor.py:443` liest ihn beim Verkauf wieder
aus. Dazwischen liegt Glied 3:

> `runtime/state_manager.py` speichert eine offene Position nach
> `bot_state.json` — aber **nach einer Whitelist**. Ihr eigener Kommentar
> warnt wörtlich: *„was nicht aufgezählt ist, überlebt keinen Neustart."*

Sie führte 13 Felder. `entry_score` und `entry_strategie` waren nicht
darunter.

**Am lebenden Objekt belegt:** Die an diesem Tag offene BTC-Position trug
in `bot_state.json` genau diese 13 Felder — keines davon der Score. Und der
Verkauf um 20:49 UTC (Einstieg 15:54, zwei Neustarts dazwischen) wurde mit
`entry_score: None` gebucht.

**Die Folge war stiller als der Fehler selbst.** Am 11.09. wurden beide
Verkaufswege repariert, damit sie alle sechs Pflichtfelder schreiben —
`schreibwege_test.py` bestätigt das. Aber ein Schreibweg kann nur schreiben,
was die Position *hat*. Ohne diese zwei Zeilen wäre der Anteil nie über die
Positionen hinausgekommen, die innerhalb **einer** Bot-Laufzeit auf- und
wieder zugehen — und niemand hätte gesehen, warum.

**Behoben:** zwei Felder in die Whitelist. Der Rückweg
(`state_manager.py:239`) nimmt das Dict ohnehin ungefiltert, dort war nichts
zu tun.

**Geprüft mit `whitelist_test.py`** — Rundlauf anlegen/speichern/laden über
sechs Pflichtfelder, eine Gegenprobe mit einem erfundenen Feld (darf nicht
durchkommen) und ein Gegentest gegen die alte Fassung (muss den Fehler
finden). Alles drei besteht.

**Was das nicht behebt:** Auf dem Nachkauf-Pfad (DCA) bleibt der Score leer.
`app.py:3029` liest dort eine Variable, die es nicht gibt — `_dca_intent`
wird an keiner Stelle im Projekt zugewiesen (`grep -c "_dca_intent *="` →
**0**). Das ist **Befund 41**, weiterhin offen.

*Angelegt 29.08.2026. Werkzeuge: `felder_nachtragen.py`,
`FELDER_NACHTRAGEN.bat`, `whitelist_test.py`. Hintergrund: Befund 88, 41.*

---

## 8.7b Der Autostart im Live-Ordner — und ein Fehler, der ihn wertlos gemacht hätte

**Stand: 16.09.2026.** Sven: *„ist es aber nicht besser das er von selbst
startet damit wir immer alle daten haben falls ich das jemals vergessen
sollte."*

### Was eingerichtet ist

`AUTOSTART_EINRICHTEN.bat` legt die geplante Aufgabe
**`SchattenUniversumLIVE`** an — alle 15 Minuten ruft sie
`schatten_starter.py` auf, und der startet den Sammler **nur, wenn er
gerade nicht läuft**.

**Warum alle 15 Minuten und nicht „beim Hochfahren":** Dieser Auslöser
braucht Adminrechte und scheitert hier an „Zugriff verweigert" — steht
seit dem 18.08. in `OFFEN.md` Zeile 161. Der Viertelstundentakt ist der
erprobte Ersatz; die Lücke nach einem Neustart beträgt höchstens 15
Minuten.

Die vorhandene Aufgabe `SchattenUniversumWacht` zeigt auf den
**Papier**-Ordner und bleibt unangetastet.

### Der Fehler, der dabei auffiel

Der Starter prüfte, ob der Sammler schon läuft, indem er die
**Befehlszeile** durchsuchte. Die sieht je nach Startart verschieden
aus:

```
...\trading_imperium_v6(21)\schatten_universum.py --dauer
schatten_universum.py --dauer          ← relativ, kein Ordner!
```

Der zweite Fall entsteht beim Start aus dem eigenen Ordner — also im
Normalfall. **Damit kann die alte Prüfung LIVE und Papier nicht
unterscheiden.**

Die Folge wäre genau das Gegenteil dessen, wofür das Skript gebaut
wurde:

> Stirbt der LIVE-Sammler, sieht der Starter den **Papier**-Sammler,
> meldet „läuft bereits" und startet nichts. Die Datensammlung stünde
> still — und im Log stünde, alles sei in Ordnung.

Ein Wächter, der beim Ausfall Entwarnung gibt, ist schlimmer als keiner.

**Behoben:** `psutil` kennt das Arbeitsverzeichnis jedes Prozesses.
Damit ist die Frage eindeutig zu beantworten. Gegengeprüft an den
laufenden Prozessen, in drei Richtungen:

| geprüfter Ordner | Ergebnis | soll |
|---|---|---|
| fremder Ordner | `False` (würde starten) | ✅ |
| LIVE | `True` | ✅ |
| Papier | `True` | ✅ |

Fehlt `psutil`, bleibt der alte Weg — dann meldet der Starter
ausdrücklich, dass er die Ordner nicht sicher unterscheiden kann. Eine
unscharfe Aussage mit Hinweis ist besser als eine scharfe, die falsch
ist.

---


## 8.7c Vier Wochen gewartet auf Rechte, die nie nötig waren

**16.09.2026.** In `OFFEN.md` stand seit dem 18.08. ein Punkt, abgelegt
als *„nur Kosmetik"*:

> Autostart des Schatten-Sammlers mit Adminrechten. Die Aufgabe mit
> Auslöser „beim Hochfahren" scheitert an „Zugriff verweigert".

Sven bot an, Adminrechte freizugeben. Vor dem Annehmen nachgemessen:

| Weg | Ergebnis |
|---|---|
| `schtasks /create /sc onstart` | FEHLER: Zugriff verweigert |
| `schtasks /create /sc onlogon` | FEHLER: Zugriff verweigert |
| `Register-ScheduledTask -AtLogOn -User <eigener Benutzer>` | **geht** |

**Der Unterschied liegt nicht am Auslöser, sondern daran, für WEN die
Aufgabe gilt.** `schtasks` legt sie ohne weitere Angabe für *jeden*
Benutzer des Rechners an — und wer etwas für fremde Benutzer einrichtet,
braucht Adminrechte, zu Recht. Auf den eigenen Benutzer eingegrenzt,
fällt der Grund weg.

> **Die Lehre:** Das erste Werkzeug, das scheitert, wird für die Antwort
> gehalten. „Geht nicht ohne Adminrechte" war die Erfahrung mit
> `schtasks` — nicht die Eigenschaft der Aufgabe. Vier Wochen lang hat
> niemand das zweite Werkzeug probiert.

### Was jetzt eingerichtet ist

Zwei Aufgaben, beide auf den Live-Ordner, beide ohne erhöhte Rechte:

| Aufgabe | Auslöser | Wofür |
|---|---|---|
| `SchattenUniversumLIVE_Anmeldung` | bei der Anmeldung, 1 Min Verzug | schließt die Lücke nach dem Hochfahren |
| `SchattenUniversumLIVE` | alle 15 Minuten | fängt Absturz und Abbruch ab |

Der eine deckt den Start ab, der andere den Betrieb. Sie stören einander
nicht: beide rufen `schatten_starter.py`, und der startet nur, wenn
nichts läuft.

Werkzeug: `python autostart_einrichten.py` (`--pruefen`, `--entfernen`).

### Der Python-Pfad — und warum die Dateigröße die falsche Frage ist

`AUTOSTART_EINRICHTEN.bat` trug den Pfad fest eingetragen, samt Version
`Python.3.13`. Auf einem anderen Rechner zeigt das ins Leere, und die
Aufgabe meldet Erfolg und tut nichts.

Beim Umbau lief die erste Fassung in eine eigene Falle: Sie prüfte den
Interpreter über `os.path.getsize()`, weil die bekannte Attrappe
0 Byte groß ist. Nachgemessen:

```
...\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe
    exists = True    getsize = 0    läuft = ja
```

**Die Einträge unter `WindowsApps` sind Verweise, keine Dateien — sie
melden alle 0 Byte, die funktionierenden wie die Attrappen.** Eine
Größenprüfung wirft genau die Interpreter weg, die gehen.

Geprüft wird jetzt die **Wirkung**: `pythonw` legt eine Datei an, und wir
sehen nach, ob sie da ist. Das ist genau der Weg, den die Aufgabenplanung
später geht. Dasselbe Verfahren steckt in `schatten_starter.py`, wo der
Pfad ebenfalls verdrahtet war.

### Und der Fehler, der das Werkzeug selbst lahmlegte

Die erste Fassung lief dreimal in den Zeitausfall. Ursache war
`Get-ScheduledTask | Where-Object {...}` — das liest **erst alle 258
Aufgaben des Rechners** und wirft danach weg, dazu drei getrennte
PowerShell-Starts. Mit `-TaskName` gefiltert: **13,1 s statt über 180.**

> Ein Filter hinter der Abfrage ist kein Filter, sondern eine Sortierung
> nach getaner Arbeit.

## 8.7d Umzug auf einen anderen Rechner — als Prüfung, nicht als Notiz

**16.09.2026.** Sven: *„der laptop hier läuft auf windows 10 aber mein
rechner zuhause auf 11 — mach einen vermerk rein, dass er das weiß, wenn
ich den live ordner rüberziehe."*

Ein Vermerk in einer Datei wird gelesen, wenn man ihn sucht — also nie.
Deshalb ist der Vermerk ein Werkzeug: `python umzug_pruefen.py`. Es sagt
nicht, woran man denken soll, sondern **was gerade nicht stimmt.**

Jede der sieben Prüfungen steht für einen Fehler, der schon passiert ist.
Alle haben dieselbe Bauart: **sie melden Erfolg und tun nichts.**

| Prüfung | Der Fehler dahinter |
|---|---|
| Betriebssystem | Windows 11 meldet sich selbst als „10" — erkennbar nur an der Baunummer ab 22000 |
| Python | Der Store-Alias öffnet den Microsoft Store statt zu starten; in geplanten Aufgaben scheitert er **still** (14.08.) |
| Die 20 Pakete | `requirements.txt` altert still — am 02.09. fehlten `reportlab` und `openpyxl` |
| Geplante Aufgaben | Eine importierte XML trägt die Benutzerkennung des **alten** Rechners. Dazu: zeigt die Aufgabe überhaupt auf *diesen* Ordner? Seit dem 14.09. gibt es zwei |
| Feste Pfade | Dateien mit altem Benutzernamen oder dem anderen Projektordner |
| Die Haken | `.claude/settings.json` verweist absolut. Stimmt der Pfad nicht, arbeitet Claude ohne Projektregeln und **ohne Schreibschutz** |
| Daten und `.env` | Die `.env` wird beim Kopieren übersehen, weil viele Werkzeuge Dateien mit führendem Punkt ausblenden. Geprüft wird nur, **dass** sie da ist — nie ihr Inhalt |

**Erster Lauf:** 16 in Ordnung, 11 zum Ansehen, 0 fehlen. Dabei fiel
gleich etwas auf, das nichts mit dem Umzug zu tun hat: **der Live-Ordner
hat gar kein `.claude`-Verzeichnis.** Der Papier-Ordner hat dort drei
Haken, darunter den Schreibschutz. Im Ordner mit echtem Geld fehlen sie.

Und ein Fehler im Werkzeug selbst: Es sucht nach dem Wort `Users` — und
fand **sich selbst**, weil diese Suche in seinem eigenen Code steht.

> Ein Prüfwerkzeug, das sich selbst meldet, bringt dem Leser bei, die
> Meldung zu überlesen. Das ist dieselbe Krankheit wie ein Log, in dem
> immer etwas Rotes steht.

## 8.8 Was du nicht starten musst

Rund 44 weitere Dateien: `test_*.py`, `cleanup*.py`, `config_update.py`,
`backfill_*.py`, `e4_eval.py`, `e5_walkforward.py`, `macro_replay.py`,
`phase_prior_check.py`, `situation_replay.py`, `history_harvester.py`,
`inventar_agent.py`, `diagnose.py`, `check_install.py`, `telegram_test.py`,
`voll_diagnose.py`, `regime_diag_toggle.py`, `journal_abgleich.py`,
`metals_check.py`, `metals_signals.py`, `epochs.py`,
`erledigtes_archivieren.py`, `regel_waechter_bestaetigen.py`,
`schatten_starter.py`, `prozess_frische_wacht.py`, `dauercheck.py`,
`telemetrie_pruefen.py`, `schatten_regime_nachtragen.py`.

Sie sind entweder einmalig gelaufen, laufen automatisch mit, oder gehören zu
einer abgeschlossenen Aufgabe. **Gelöscht werden sie nicht** — sie sind der
Beleg, dass eine Messung stattgefunden hat.

*Früher: 4.86 F.*

---

## 8.9 Wenn ein Werkzeug lügt — vier Fälle aus diesem Projekt

Ein Messgerät muss selbst geeicht sein. Diese vier Fälle sind der Grund, warum
in diesem Projekt jedes Prüfwerkzeug einen Gegentest in **beide** Richtungen
braucht: *Meldet es nichts Falsches — und findet es den echten Fall?*

### Fall 1: Die große Zahl, die keine war

`regime_filter_messung.py` meldete **89.291 geblockte Gelegenheiten**. Der Bot
prüft alle rund 12 Sekunden — bleibt eine Marktlage eine Stunde bestehen, steht
dieselbe Gelegenheit 300-mal in der Datenbank. In zwölf Tagen passen bei
24-Stunden-Sicht **12 nicht überlappende Fenster je Münze**.

| | vorher | nachher |
|---|---|---|
| Fälle (24 h) | 53.806 | **22** |
| Kosten je Runde | 0,32 % | 0,505 % |
| Ergebnis | +0,351 % | **−0,283 %** |
| Urteil | „Block war TEUER" | „zu wenig Fälle" |

**Das Urteil drehte sich um.** Die Ausgabe führt jetzt beide Spalten: `unabh.`
und `roh`. Ein Urteil trägt nur die linke.

> Eine große Zahl ist kein Beleg. 53.806 Fälle klingen nach Gewissheit und sind
> doch nur dieselbe Stunde, dreihundertmal aufgeschrieben.

### Fall 2: Der Prozess lief, die Reparatur kannte er nicht

Am 19.08. lief der Schatten-Sammler, die Ampel war grün — und er schrieb
trotzdem leere Regime-Felder. Er war um 22:11 gestartet, die Reparatur kam um
22:38. **Ein laufender Prozess kennt keine Reparatur.**

Die Prüfung sagt das jetzt selbst:

```
Schatten-Universum    laeuft - ABER mit altem Programmtext!
    gestartet 20.08. 00:11, Datei geaendert 20.08. 00:32
    -> SAMMLER_NEUSTART.bat doppelklicken
```

### Fall 3: Die Ampel, die nicht grün werden konnte

Bei den Bot-Entscheidungen stand dauerhaft „Lücke 2,8 h — PRÜFEN". Die Lücke
war echt, aber sie war der Nacht geschuldet, in der der Rechner aus war.

> Eine Ampel, die dauerhaft gelb steht und nicht grün werden **kann**, bringt
> einem bei, sie zu ignorieren.

Jede Lücke wird seitdem gegen den Herzschlag des Bots gehalten. Nur eine Lücke,
in der der Bot **nachweislich lief**, ist ein Ausfall.

Am 24.08. tauchte derselbe Denkfehler ein zweites Mal auf: Der Takt des
Schatten-Universums wurde gegen die Tabelle `signale` gemessen — die bekommt
aber nur bei einem **Treffer** eine Zeile. Findet der Markt stundenlang nichts,
sieht ein fleißiger Sammler aus wie ein ausgefallener. Seitdem wird der Takt
gegen `laeufe` gemessen.

> Nicht „wann kam zuletzt ein Ergebnis", sondern „wann hat er zuletzt
> **gearbeitet**".

### Fall 4: Der Sammler lief — und schrieb woanders hin

**24.08.2026.** Eine stehengelassene Projektkopie unter `.claude/worktrees/`
enthielt eigene `.bat`-Dateien und einen leeren zweiten `data_store`. Aus der
Kopie gestartet, beendete `SAMMLER_NEUSTART.bat` die echten Sammler und startete
sich selbst.

```
ECHT      17:58:05   2 echt + 16 schatten offen, 18 Zeilen
KOPIE     18:00:08   0 echt +  0 schatten offen,  0 Zeilen
```

**40 Minuten endgültig verloren.** Die Prüfung meldete währenddessen „OK,
läuft" — sie suchte den *Dateinamen* in der Prozessliste, nicht den *Ordner*.

Seitdem gibt es `_fremder_ordner()`: eine **zusätzliche** Prüfung, aus welchem
Verzeichnis ein Sammler gestartet wurde. Bewusst additiv — eine Verschärfung der
vorhandenen Erkennung könnte einen laufenden Sammler übersehen und doppelt
starten, und ein doppelter Sammler wäre schlimmer als der blinde Fleck.

> Ein Sammler, der läuft, ist noch kein Sammler, der **hier** sammelt.

### Fall 5: Die Latte, die ein anderes Rennen lief

**26.08.2026.** `ausstieg_vergleich.py` meldete, dass **alle acht**
Ausstiegsregeln gegen die Trivial-Latte „Halten" verlieren — die schlechteste
um 5,6 Prozentpunkte.

Die Latte rechnet über 49 Verläufe aus zwei Beständen. Deren Aufzeichnung
läuft unterschiedlich lange:

| Herkunft | n | Aufzeichnung, Median | „Halten" bis Ende |
|---|---:|---:|---:|
| echte Positionen | 36 | **4,6 h** | **+0,645 %** |
| Schattenpositionen | 32 | **99,4 h** | **+10,012 %** |

**Faktor 21.** Bei einer echten Position endet die Aufzeichnung, wenn der Bot
verkauft — „Halten" heißt dort *„halten, bis der Bot ohnehin verkauft"*.
Die Schattenpositionen laufen bis `MAX_TAGE = 7` weiter.

Verglichen wurde also nicht „Regel gegen Halten", sondern **„vier Stunden
gegen vier Tage"** — in einem steigenden Markt.

> **Eine Trivial-Latte muss dieselbe Frage beantworten wie das, was sie
> schlagen soll.** Sonst ist sie keine Latte, sondern ein anderes Rennen.

Das Werkzeug warnt selbst unter der Tabelle, dass echte Verläufe beim
Verkauf enden. Nur die **Urteilsspalte** berücksichtigt es nicht. Steht als
**Befund 79**.

*Früher: 4.63, 4.86, 4.88, 4.90, 4.121.*

---

## 8.10 Wo deine Trades wirklich stehen

Am 21.08. fragte Sven, warum eine Anzeige 36 Verkäufe meldet, während es
tatsächlich 464 gab. Beide Zahlen waren richtig — sie zählten Verschiedenes:

| Quelle | Was sie zählt |
|---|---|
| `data_store/trades.json` | **alle** Verkäufe seit Projektbeginn |
| Epochen-Auswertung | nur die Verkäufe der **laufenden** Regelwerks-Epoche |

Eine Epochengrenze setzt die Zählung auf null — das ist ihr Zweck. Wer die
Gesamtzahl sucht, fragt die erste Quelle; wer wissen will, was das *aktuelle*
Regelwerk taugt, die zweite.

`python telemetrie_frage.py verlauf` zeigt beides nebeneinander.

*Früher: 4.116.*

---

## 8.11 Wo die Daten liegen

### Die Telemetrie-Datenbank

`data_store/telemetrie.db` — hier steht **jede Entscheidung**, auch die,
nicht zu handeln. Heute rund **320 MB**.

**Warum es sie gibt:** Am 6. August gab es 14.986 Kaufsignale und **null**
tatsächliche Prüfungen. Der Bot meldete dabei durchgehend „alles in
Ordnung". Der Fehler war unsichtbar, weil nirgends aufgeschrieben wurde, was
schiefging (Teil 2, Abschnitt 2.9). Diese Datenbank ist die Antwort darauf.

| Tabelle | Was drinsteht | Zeilen |
|---|---|---:|
| `evaluations` | jede Kaufprüfung: gekauft oder abgelehnt, mit Ergebnis | 304.000+ |
| `rule_evaluations` | **alle** Ablehnungsgründe, nicht nur der erste | 378.000+ |
| `chart_signale` | Signale der Chartanalyse (Messlauf, kein Handel) | 111.932 |
| `chart_laeufe` | Übersicht je Chart-Messlauf | 245 |
| `feature_snapshots` | Merkmale zum Entscheidungszeitpunkt | 891 |
| `markt_historie` | Marktwerte alle 15 Minuten | 1.278 |
| `lern_ereignisse` | jeder Verkauf, aus dem gelernt wurde | 45 |
| `regime_lernen` | Anpassungen des lernenden Wächters | 54 |
| `schatten_regeln` | was eine Regel im Notizbuch getan hätte | 1.880 |
| `schatten_exits` | was die Schatten-Ausstiegsregeln getan hätten | 39 |
| `schatten_sizing` | was der Größenrechner getan hätte | 41 |
| `jobs` | Hintergrundprogramme: Start, Ende, Fehler | 1.883 |

### Die vier weiteren Datenbanken

| Datei | Inhalt |
|---|---|
| `data_store/positionsverlauf.db` | alle 5 Minuten der Stand jeder offenen Position |
| `data_store/schatten_universum.db` | die stündliche Bewertung der 18 Münzen |
| `data_store/nachlauf.db` | wie der Kurs **nach** einer Entscheidung weiterlief |
| `docs/forschungsprogramm_2026-07/forschung.db` | **bewusst abgekoppelt** — keine Verbindung zu den anderen |

### Die Zustandsdateien

| Datei | Inhalt |
|---|---|
| `bot_state.json` | der aktuelle Stand: offene Positionen, Kontostand |
| `trades_v5.json` | jeder Kauf und Verkauf des V6-Bots |
| `v4_referenz/trades_log_v4.json` | dasselbe für den mitlaufenden V4-Bot |
| `system.log` | das laufende Protokoll |
| `bus_errors.log` | die Fehlerakte — **wird nie überschrieben** |

### Wie du reinschaust

```
python telemetrie_frage.py status      Übersicht
python telemetrie_frage.py gruende     Warum wurde nicht gekauft?
python telemetrie_frage.py kaeufe      Was wurde gekauft?
python telemetrie_frage.py verkaeufe   Was wurde verkauft?
python telemetrie_frage.py markt       Die Marktdaten-Zeitreihe
python telemetrie_frage.py verlauf     Die letzten 30 Entscheidungen
```

Oder per Doppelklick: **`datenbank_ansehen.bat`**

> **Eine Warnung zu den Zeilenzahlen.** 304.000 Entscheidungen klingen nach
> Gewissheit. Der Bot prüft alle rund 12 Sekunden — dieselbe Marktlage steht
> deshalb hundertfach in der Tabelle. Für ein Urteil zählt nur die Zahl der
> **unabhängigen** Fälle (Abschnitt 8.9, Fall 1).

*Früher: C.1 und C.2.*

---

> ## Dieses Buch wird gerade umgebaut
>
> **Begonnen am 24.08.2026.** Oben stehen die **fertigen** Teile — nach
> Gegenstand gegliedert, auf dem heutigen Stand, zum Nachschlagen.
> Unter der Trennlinie steht das **alte Material**, unveraendert, bis es
> eingeordnet ist. Es geht nichts verloren: Was wohin wandert, steht in
> `docs/handbuch_umbau_2026-08/UMBAU-LISTE.md`, maschinell erzeugt aus den
> echten Ueberschriften.
>
> Ein alter Abschnitt wird erst geloescht, wenn **jedes** Stueck daraus
> ein neues Zuhause hat. `4.63` zeigte warum: ein einziger Abschnitt
> enthielt zwei Werkzeuge, einen Kapitalbegriff-Fehler und Befund 44 —
> drei verschiedene Kapitel.

---


---

## 8.12 Die Prognose-Ruecktechnik — und warum sie ein Nein liefert

**Stand: 27.08.2026.** Svens Auftrag: *„bau ein Tool, das alles durchrechnet
und sucht, wie er es gemacht hat."* Gemeint war Tilo, ein Börsenprofi mit
27 Jahren Erfahrung, dessen BTC-Prognose vom 07.05.2025 traf — Triggerzone
97–104K, Ziel 123.000 $. Seine Chartbilder haben wir nicht, nur die Zahlen.

```
python prognose_ruecktechnik.py --ziel 123000 --stichtag 2025-05-07
python prognose_ruecktechnik.py --selbsttest
```

**Was es tut:** Es probiert alle gängigen Chart-Verfahren durch, die mit den
Kursen **von damals** möglich waren — Fibonacci-Rückgänge, -Verlängerungen
und -Projektionen über alle Swing-Paare, runde Zahlen, Prozentaufschläge,
Vielfache des bisherigen Hochs. Für BTC am 07.05.2025 sind das **17.238
Rechnungen**.

**Kausalität ist eingebaut:** Ein Swing-Hoch gilt erst als bekannt, wenn die
bestätigenden Kerzen gelaufen sind — dieselbe Regel wie in 6.9. Sonst fände
man Methoden, die damals niemand kennen konnte.

### Die wichtigste Eigenschaft: es misst sich selbst

Wer genug Formeln durchprobiert, trifft jede Zahl. Deshalb rechnet das
Werkzeug **immer** eine Trivial-Latte mit: Es sucht dieselbe Anzahl
**gewürfelter** Ziele im selben Kursbereich und zählt, wie oft die auch
getroffen werden.

> Trifft die Suche das echte Ziel genauso gut wie ein gewürfeltes, hat sie
> nichts gefunden — nur bewiesen, dass ihr Netz zu grob ist.

### Das Ergebnis

**Eine einzelne Zahl (Tilos 123.000 $):**

| Toleranz | echtes Ziel | **gewürfeltes Ziel** |
|---:|---:|---:|
| 0,50 % | 115 Treffer | **79,4** |
| 0,10 % | 23 | **15,7** |
| 0,01 % | 5 | 1,5 |

**Neun Zahlen aus einem Chart (Marks Wochenchart):** Der stärkere Ansatz —
nicht eine Rechnung für eine Zahl, sondern **ein Raster für viele Zahlen**.
Geprüft wurden 3.481 Hoch-Tief-Raster:

| Toleranz | erklärt von Marks 9 | von **9 gewürfelten** |
|---:|---:|---:|
| 0,50 % | 5 | **4,8** (Höchstwert 6) |
| 0,20 % | 4 | 3,5 |
| 0,10 % | 3 | 2,7 |

**Auf keiner Stufe unterscheiden sich die echten Marken von Zufallszahlen.**

### Warum das so ist — und warum es trotzdem ein wertvolles Ergebnis ist

Ein Fibonacci-Raster über **ein** Hoch-Tief-Paar erzeugt 40 Linien. Bei 59
Hochs und 59 Tiefs sind das über **139.000 Linien** im Kursbereich. Dieses
Netz fängt jede Zahlenmenge ein.

> **Eine Methode, die alles erklären kann, erklärt nichts.**

Das ist **Befund 83** — und es bestätigt eine Regel, die seit dem 15.08. in
`prognosen/TILO.md` steht: Eine Prognose zählt nur mit **Datum, genauer
Zahl, genauer Frist und Ist-Kurs**. Man kann eine Methode nicht nachträglich
aus Zahlen erschließen; man muss sie sich **vorher** nennen lassen.

**Wofür das Werkzeug trotzdem taugt:** für die umgekehrte Frage. Nennt Tilo
oder Mark ein Verfahren — „ich nehme das Wochenhoch und projiziere 1,618" —,
rechnet es nach, ob ihre Zahlen daraus wirklich folgen. Das ist eine
prüfbare Behauptung; „irgendein Fibonacci" ist keine.

*Auftrag von Sven, 27.08.2026.*

## 8.13 Der Prüf-Agent `bot-pruefer` — und warum es nur noch eine Befundliste gibt

*Angelegt 25.09.2026, Auftrag Sven.* Die Anregung kam von einem Kollegen,
dessen KI sein Botsystem durchleuchtet und dabei *„alle Regeln raussucht"*.
Sven wollte dasselbe für diesen Bot.

**Wo er liegt:** `C:\Users\<BENUTZER>\.claude\agents\bot-pruefer.md`, also
nicht im Projektordner, sondern benutzerweit. Er gilt damit für **beide** Bot-Ordner
(`v7` und `v6(21)`). Claude Code lädt ihn erst in einer **neu gestarteten**
Sitzung.

**Aufruf:** Im Chat schreiben, zum Beispiel *„Lass den bot-pruefer das
Regel-Inventar für den Kaufweg machen"*. Man kann den Umfang eingrenzen:
„nur Kaufweg", „nur `risk/`" oder „nur Inventar".

**Was er tut:** Er liest nur. Er ändert keine Datei, startet keinen Prozess
und öffnet die `.env` nicht.

1. **Regel-Inventar:** Er sammelt jede Stelle, die einen Kauf oder Verkauf
   verhindert, auslöst, verzögert oder in der Größe ändert. Zu jeder Stelle
   nennt er Fundstelle, aktuellen Wert, Schalter, ob sie im Handbuch steht
   (Teil 2 oder 3), ob sie je gemessen wurde und wie oft sie in den letzten
   7 Tagen gegriffen hat. Regeln, die weder in `config.json` noch im
   Handbuch stehen, markiert er als **VERSTECKT**. Das sind die Kandidaten
   für den nächsten Prüfstand.
2. **Fehlersuche:** Er sucht nach den zwölf Mustern, die in diesem Projekt
   schon Schaden angerichtet haben. Dazu gehören alte Kostenannahmen, die
   Brutto-Falle bei `pnl_pct`, stilles Scheitern, fest eingetragene Pfade
   und Ports, Phantom-Positionen, `wmic` und Tests, die nur Suchmuster
   prüfen.

**Was er bewusst nicht tut:** Er baut keine Strategie aus dem, was er
findet. Die Reihenfolge bleibt: erst das Inventar, dann die Messung, dann
der Bau (Dauerregel 1: nichts anschließen ohne Messung).

**Sein Bericht geht an die aufrufende Sitzung, nicht in eine Datei.** Neue
Befunde bekommen die nächste freie Nummer in **dieser**
`GEFUNDENE-PROBLEME.md`. Eine neue Liste gibt es nicht.

**Eine Befundliste statt zwei.** Bis zum 25.09. führten `v6(21)` und der
Live-Ordner getrennte Listen, und ab Nummer 93 bedeuteten dieselben Nummern
Verschiedenes. Ein Fehler (`wmic`) wurde dadurch zweimal gefunden und
zweimal repariert. **Seit dem 25.09. ist v7 der Master** (Entscheidung
Sven). Was nur in v6 stand, wurde als Befunde 105–110 übernommen, und für
jeden Eintrag wurde neu geprüft, ob er in v7 gilt. Dazu kamen 111 (beide Bots
teilen Port 5050 und 8110) und 112 (Vortageshoch und Opening Gap: kein
Vorteil). Bis `schon_bekannt.py` in beiden Ordnern denselben Stand hat,
fragt der Agent **beide** ab.


# TEIL 9 — Der Rundgang: Datei für Datei durch den Bot

**Stand: 24.08.2026.** Ab hier gehen wir gemeinsam jeden Ordner durch — Sinn,
Aufbau, und ob eine Datei dein Geld anfasst. Bei jedem Baustein die vier
wichtigsten Fragen: **Was tut er? Warum gibt es ihn? Greift er in den Handel
ein? Was passiert, wenn man ihn löscht?**

> ### Zu den Zeilennummern in diesem Teil
>
> Sie sind die verderblichste Angabe im ganzen Buch. Am 24.08. waren **sieben
> von acht** falsch — um 20 bis **1.135** Zeilen daneben, weil `app.py`
> zwischenzeitlich von 3.580 auf 4.634 Zeilen gewachsen ist. Niemand hatte
> etwas falsch gemacht; sie altern von allein.
>
> Deshalb gilt hier: **Der Name der Funktion ist die Adresse, die Zeilennummer
> nur die Hausnummer.** Findest du unter der Nummer etwas anderes, suche nach
> dem Namen — der stimmt.
>
> Und damit es nicht wieder acht Monate unbemerkt bleibt, prüft es jetzt ein
> Programm statt eines Vorsatzes:
>
> ```
> python handbuch_zeilen_pruefen.py
> ```
>
> Es hält jede Zeilenangabe dieses Teils gegen den echten Code und nennt die
> Abweichung. Reine Leseoperation.

## Runde 1 — `app.py` (das Hauptprogramm)

**Bild zuerst:** `app.py` ist der **Dirigent** eines Orchesters. Er spielt
selbst kein Instrument — aber ohne ihn weiß kein Musiker, wann er dran ist.
Eine einzige Klasse (`TradingImperiumV6`), 4.634 Zeilen, rund 65 andere
Bausteine (*Module*) werden hier zusammengerufen und verbunden.

### 1. Der Aufbau — `__init__`, Zeile 158

**Was tut er?** Baut beim Start rund 65 Bausteine und hält sie fest:
Datenagent (holt Kurse), Signal-Agent (sucht Kaufchancen), Risiko-Prüfer,
Ausführung, Kapitalverwaltung, dazu Dutzende Zusatz-Module — Chartmuster,
Stimmungsanalyse, Wal-Alarme, Termingeschäfte (*Futures*), Telegram und
mehr.

**Warum gibt es ihn?** Ohne eine zentrale Stelle, die jedes Modul kennt,
könnten die Module nicht zusammenarbeiten.

**Greift er ins Geld ein?** Nur mittelbar — er baut die Werkzeuge, handelt
selbst nicht.

**Was bei Löschen?** Der Bot startet gar nicht mehr. Totalausfall.

### 2. Die Verdrahtung — `_setup_event_wiring`, Zeile 540

**Was tut sie?** Legt den Weg fest, den jede Information nimmt:
**Marktdaten → Signal → Risiko → Ausführung → Journal.** Dazu die
Notbremse (*Kill-Switch*) und eine Fehler-Sammelstelle.

**Bild:** Wie eine Poststelle (*Event-Bus*) — jede Abteilung bekommt nur
die Post, die sie betrifft. Die Module kennen sich nicht persönlich, sie
reden nur über diese Post miteinander.

**Greift sie ins Geld ein?** Ja, mittelbar — sie legt den Pfad fest, auf
dem jeder Kauf und Verkauf überhaupt läuft.

**Was bei Löschen?** Die Module würden nie erfahren, dass ein neuer Kurs
da ist. Der Bot stünde still — ohne dass irgendwo ein Fehler auftaucht.
Das ist die gefährlichste Art von Ausfall: stumm, nicht laut.

### 3. Der Fahrplan — `_setup_tasks`, Zeile 566

**Was tut sie?** Meldet rund 25 wiederkehrende Aufgaben beim Taktgeber
(*Scheduler*) an. Die wichtigsten:

| Takt | Aufgabe | Was sie tut |
|---|---|---|
| alle 30 Sek. | SL/TP-Monitor | prüft offene Positionen auf Stop-Kurs |
| dein Einstellwert | Trading-Loop | sucht neue Käufe |
| alle 5 Min. | Wächter-Signalpfad | meldet, wenn Kauf-Kandidaten die Prüfung nicht erreichen |
| alle 15 Min. | Markt-Historie | reine Messung, neu seit 11.08. |
| täglich | Regime-Lernen, Chartanalyse-Agent | passt Schwellen an / misst nach |
| alle 30 Sek. | Auto-Save, Heartbeat | speichert Zustand, meldet „lebt noch" |

**Warum gibt es sie?** Ohne diese Anmeldung würden die einzelnen
Programme zwar existieren, aber nie aufgerufen.

**Greift sie ins Geld ein?** SL/TP-Monitor und Trading-Loop: ja, direkt.
Der Rest ist Messung oder Bericht.

**Was bei Löschen?** Der Bot würde nie von selbst kaufen oder verkaufen —
er bliebe rechnerisch am Leben, aber untätig.

### 4. Kommt ein neuer Kurs — `_on_market_update`, Zeile 766

**Was tut sie?** Für jeden neuen Kurs zuerst die Frage: Habe ich hier eine
offene Position? Wenn ja → Verkaufs-Prüfung (darunter eine
„Auto-Verteidigung", die bei fallendem Markt zusätzlich prüft). Wenn nein
→ weiter zum Signal-Agent für eine Kauf-Prüfung.

**Greift sie ins Geld ein?** Ja, direkt — das ist die Weiche zwischen
„verkaufen prüfen" und „kaufen prüfen".

**Was bei Löschen?** Der Bot wäre blind für neue Kurse — weder Kauf noch
Verkauf würde je ausgelöst.

### 5. Der Kaufpfad — `_execute_approved_trade`, Zeile 1403

**Was tut sie?** Nachdem Signal und Risiko-Prüfung schon Ja gesagt haben,
rechnet diese Funktion den tatsächlichen Betrag aus — und kann noch
absagen: Klumpenrisiko-Check (nicht zu viel in eine Münze), im
Live-Modus Spread- und Volumen-Check, Bargeld-Deckel, Euphorie-Bremse
(*NUPL* — kauft nicht, wenn der Markt „zu gierig" ist).

**Greift sie ins Geld ein?** Ja, direkt — das ist die letzte Stelle vor
der eigentlichen Order.

**Was bei Löschen?** Keine Käufe mehr möglich, gar keine.

### 6. Nach dem Kauf oder Verkauf — `_on_order_filled`, Zeile 1956

**Was tut sie?** Schreibt den Trade ins Protokoll, meldet an Telegram —
und seit dem Fix vom 11.08. meldet sie **jeden** Verkauf, auch Verluste,
an die Lernmodule (siehe Teil 4.1 oben).

**Greift sie ins Geld ein?** Nein — reine Nachbereitung, sie kann den
Trade nicht mehr verhindern.

**Was bei Löschen?** Der Bot würde weiterhandeln, aber nichts mehr lernen
und keine Telegram-Nachricht mehr schicken.

### 7. Die Notbremse — `_close_all_positions_safety` + `_on_kill_switch`

**Was tut sie?** Verkauft im Notfall (z. B. Tagesverlust-Limit erreicht)
alle offenen Positionen auf einmal. Der Kill-Switch stoppt zusätzlich den
gesamten Bot.

**Greift sie ins Geld ein?** Ja, direkt.

**Was bei Löschen?** An einem schweren Verlusttag gäbe es keine
automatische Vollbremsung mehr — Positionen blieben offen.

### 8. Start und Stopp — `start`, `stop`, `run_forever`, Zeile 4402 ff.

**Was tut sie?** `start()` fährt alles hoch: Börse verbinden, offene
Positionen wiederherstellen, Dashboard und Echtzeit-Kursstrom (*WebSocket*)
starten. `stop()` fährt sauber runter und speichert den Zustand.
`run_forever()` hält das Programm am Leben, bis Strg+C kommt.

**Greift sie ins Geld ein?** Mittelbar — ohne sauberes Stoppen könnte der
Zustand beim nächsten Start verloren gehen.

**Was bei Löschen?** Der Bot ließe sich gar nicht starten oder beenden.

![Der Weg eines Kaufwunsches durch app.py: Neuer Kurs → Signal-Agent → Risiko-Prüfung → Ausführung → Journal. Kill-Switch und Fehler-Sammelstelle stoppen von unten alles.](grafiken/runde1_datenfluss.png)

### Kurzfassung für `app.py` als Ganzes

- **Was tut sie?** Sie ist der Dirigent — verbindet alle ~65 Bausteine und
  bestimmt die Reihenfolge.
- **Warum gibt es sie?** Ohne eine zentrale Stelle wüsste kein Modul vom
  anderen.
- **Greift sie in den Handel ein?** Ja, direkt — hier laufen Kauf- und
  Verkaufsentscheidung zusammen.
- **Was bei Löschen?** Der Bot existiert nicht mehr. Alle anderen Ordner
  sind Werkzeuge, die `app.py` aufruft — ohne Dirigent bleiben sie stumm.

**Beobachtet, nicht dringend — am 24.08.2026 nachgemessen und dabei
berichtigt.** Hier stand bisher, Bottom-Detector und Portfolio-Rebalancer
würden „wortgleich" zweimal aufgebaut. Das stimmt so nicht:

| | erster Aufbau | zweiter Aufbau | |
|---|---|---|---|
| Bottom-Detector | `app.py:270` | `app.py:285` | wirklich gleich — das zweite überschreibt das erste |
| Rebalancer | `app.py:277` → `self.portfolio_rebalancer` | `app.py:292` → **`self.rebalancer`** | **zwei verschiedene Felder** — beide Objekte bleiben bestehen |

Dazu stehen die Importe doppelt (`app.py:47–50`).

**Und der eigentliche Punkt:** Kein einziges dieser Felder wird jemals
*gelesen*. Gegengeprüft mit einer Suche über alle Zuweisungen hinaus —
`self.bottom_detector`, `self.rebalancer` und `self.portfolio_rebalancer`
kommen ausschließlich auf der linken Seite eines Gleichheitszeichens vor.

Vier Objekte, die beim Start gebaut werden und die niemand benutzt. Beide
Rebalancer stehen ohnehin auf `enabled=False, dry_run=True`, das Verhalten
ändert sich also nicht. Steht als **Befund 75**. Nicht angefasst — der
Freeze läuft, und ein Aufräumen im Startpfad wäre eine Verhaltensänderung.

> Nicht verwechseln mit `portfolio/agent.py:28`. Das ist ein **anderer**
> Rebalancer (`Rebalancer`, nicht `PortfolioRebalancer`) und wird benutzt.

**Nächste Runde:** `risk/` — hier wird entschieden, ob überhaupt gekauft
werden darf.

## Runde 2 — `risk/` (entscheidet, ob gekauft wird)

**Bild zuerst:** `risk/` ist der **Türsteher**. Jeder Kaufwunsch muss hier
durch, bevor er zur Kasse (`execution/`) darf. Verkäufe lässt der Türsteher
**immer** durch — er hält niemanden vom Ausgang ab, nur vom Eingang.

Zehn Dateien sind aktiv im Einsatz, angeführt von `engine.py`.

### 1. `engine.py` — die Haupt-Prüfstelle (519 Zeilen)

**Was tut sie?** Prüft jeden Kaufwunsch nacheinander gegen rund acht
Regeln: Notbremse (*Kill-Switch*), Gesamtverlust seit Höchststand
(*Drawdown*), Höchstzahl offener Positionen, Klumpenrisiko je Münze und
Sektor (*Exposure*), Cooldown nach Verlusten, Bärenmarkt-Regel (nur noch
BTC+ETH), „schon investiert", Positionsgröße. **Verkäufe werden immer
genehmigt — nie blockiert.**

**Warum gibt es sie?** Zentrale Stelle, die die spezialisierten Module
(unten) der Reihe nach aufruft und am Ende Ja oder Nein sagt.

**Greift sie ins Geld ein?** Ja, direkt — die wichtigste Bremse vor jedem
Kauf.

**Was bei Löschen?** Nichts würde mehr geprüft — jeder Kaufwunsch ginge
ungebremst durch. Der gefährlichste denkbare Ausfall in diesem Ordner.

Zwei Dinge stecken zusätzlich in dieser Datei:
- Die **Töpfe-Vorbereitung** (`position_id`, `topf`) — reine Struktur,
  ändert noch nichts am Verhalten. Das ist der offene „Töpfe Schritt 3".
- Der **Schlafmodus**: nach 10 echten Störungen in Folge pausiert der Bot
  15 Minuten. „Bin einfach voll" zählt seit dem Schlaffalle-Fix vom
  06.08. ausdrücklich **nicht** als Störung — sonst bestrafte sich der
  Bot fürs korrekte Arbeiten.

### 2. `exposure.py` — Klumpenrisiko-Wächter

**Was tut sie?** Rechnet aus, wie viel Prozent des Vermögens nach einem
Kauf in einer Münze oder einem Sektor (z. B. alle L1-Coins zusammen)
stecken würden, und lehnt ab, wenn die Grenze (Standard 20 % / 40 %)
gerissen würde.

**Warum gibt es sie?** Verhindert „alles auf eine Karte".

**Greift sie ins Geld ein?** Ja, direkt, über `engine.py` aufgerufen.

**Was bei Löschen?** `engine.py` stürzt schon beim Start ab — der Bot
startet gar nicht.

### 3. `drawdown_guard.py` — Gesamt-Bremse

**Was tut sie?** Merkt sich den bisherigen Höchststand des Vermögens und
misst den Abstand zum aktuellen Wert. Über der Grenze (Standard 15 %):
Handelsstopp.

**Warum gibt es sie?** Bremst, wenn es insgesamt schlecht läuft —
unabhängig davon, welche einzelne Münze schuld ist.

**Greift sie ins Geld ein?** Ja, direkt.

**Was bei Löschen?** Bot startet nicht (Absturz beim Import).

### 4. `kill_switch.py` — die Notbremse

**Was tut sie?** Zählt den Tagesverlust in Dollar. Über der Grenze:
sofortiger Vollstopp, kein Kauf mehr, bis der Tag zurückgesetzt wird.

**Warum gibt es sie?** Ein fester Dollarbetrag als harte Grenze — anders
als eine Prozentrechnung lässt sich das leicht verstehen: „mehr als X$
am Tag verliere ich nicht automatisch weiter".

**Greift sie ins Geld ein?** Ja, direkt — die schärfste Bremse im Ordner.

**Was bei Löschen?** Bot startet nicht.

### 5. `position_sizing.py` — der Betragsrechner

**Was tut sie?** Rechnet aus, wie groß ein Kauf sein soll: Grundprozentsatz,
angepasst nach Zuversicht (*Confidence*), Marktzyklus und Schwankungsbreite
(*Volatilität*).

**Warum gibt es sie?** Nicht jeder Kauf soll gleich groß sein.

**Greift sie ins Geld ein?** Ja, direkt — bestimmt den Betrag.

**Was bei Löschen?** Bot startet nicht. **Nebenbei bemerkt:** Die Datei
enthält auch eine Kelly-Formel (`kelly_fraction`, aus der Wett- und
Investmenttheorie) — die ruft aber aktuell niemand auf. Reine Reserve.

### 6. `exit_rules.py` — die Ausstiegs-Leiter

**Was tut sie?** Bestimmt, wie eng der Verkaufs-Sicherheitsabstand
(*Trailing-Stop*) ist, je nachdem wie hoch der Gewinn **einmal** stand.
Dazu eine Breakeven-Sperre: stand eine Position einmal über +1 % im Plus,
wird bei Rückfall auf +0,35 % glattgestellt — aus einem Gewinner soll nie
ein Verlierer werden.

**Warum gibt es sie?** Die alte Regel hatte einen eingebauten Fehler: sie
lockerte sich auf dem Rückweg, statt sich zu verengen. Hier steht die
reparierte Version, mit der Messung dahinter (423 ausgewertete Verkäufe).

**Greift sie ins Geld ein?** Ja, direkt — läuft aber über
`runtime/exit_monitor.py` (Runde 3), nicht direkt aus `app.py`.

**Was bei Löschen?** Der Verkaufspfad bricht — Positionen hätten keinen
abgestuften Sicherheitsabstand mehr.

### 7. `reentry_guard.py` — Wiedereinstiegs-Sperre

**Was tut sie?** Verbietet den sofortigen Rückkauf einer Münze nach einem
Verkauf — außer der Preis ist deutlich gefallen. Beide Bedingungen müssen
gelten: mindestens 90 Minuten seit dem Verkauf, **und** mindestens 1 %
günstiger als der Verkaufspreis.

**Warum gibt es sie?** Gemessen: 338 Fälle, in denen innerhalb von 15
Minuten dieselbe Münze zurückgekauft wurde — 94 % davon teurer. Kostete
rund 70 $, bei einem Gesamtergebnis von −27,57 $ der Unterschied zwischen
Plus und Minus.

**Greift sie ins Geld ein?** Ja, direkt, nur bei Käufen.

**Was bei Löschen?** Der Bot würde wieder teurer zurückkaufen, wie vor
dem 29.07.

### 8. `coin_stops.py` — Mindest-Stop je Münze

**Was tut sie?** Eine kleine Tabelle: für ADA gilt ein Mindest-Stop-Abstand
von 3,0 %, egal was die normale Regel sagt — kann den Abstand nur
**lockern**, nie enger machen.

**Warum gibt es sie?** ADA schwankt stärker, als der Standard-Abstand
verträgt.

**Greift sie ins Geld ein?** Ja, aber nur für ADA und nur lockernd.

**Was bei Löschen?** ADA bekäme wieder den normalen, zu engen Stop.

### 9. `regime_profiles.py` — Anpassung an die Marktphase

**Was tut sie?** Multipliziert Stop-Loss, Trailing-Abstand und
Positionsgröße mit Faktoren je nach Marktzyklus (z. B. Bärenmarkt: enger
und kleiner) und Regime (z. B. volatil: vorsichtiger).

**Warum gibt es sie?** Ein Stop, der im ruhigen Aufwärtstrend passt, ist
im Crash zu weit.

**Greift sie ins Geld ein?** Ja, direkt.

**Was bei Löschen?** Alle Positionen liefen mit denselben starren Werten,
egal wie der Markt gerade steht.

### 10. `adaptive_sizing.py` — der Positionsgrößen-Rechner

Schon aus Teil 1.6 bekannt: rechnet mit, was er täte, **greift aber nicht
ein** — Notizbuch-Modus. Geprüft: `use_dynamic_sizing` steht in
`data_store/config.json` auf `false`. Erst wenn das auf `true` wechselt,
würde er wirklich die Kaufgröße verändern.

### Leichen in diesem Ordner (Runde 11, jetzt nicht angefasst)

- `daily_loss_guard.py.UNUSED` — ein nie eingebauter Vorläufer des
  Kill-Switch, ausdrücklich mit „.UNUSED" markiert.
- `engine.py.bak_*` (vier Stück) — Sicherungskopien früherer Stände.
- `exposure.py.bak_failsafe_20260805` — eine weitere Sicherungskopie.

Keine davon wird geladen — Python importiert keine `.bak`- oder
`.UNUSED`-Dateien. Reines Altpapier, kostet nur Speicherplatz.

### Kurzfassung für `risk/` als Ganzes

- **Was tut er?** Der Türsteher — prüft jeden Kaufwunsch gegen rund acht
  Regeln, bevor Geld bewegt wird. Verkäufe lässt er immer durch.
- **Warum gibt es ihn?** Ohne ihn gäbe es keine Bremse zwischen „ich hätte
  gern gekauft" und „es wurde gekauft".
- **Greift er in den Handel ein?** Ja, direkt und zentral — das ist seine
  einzige Aufgabe.
- **Was bei Löschen?** Kein Kauf mehr möglich (`engine.py` fehlt) — oder,
  schlimmer, gar keine Prüfung mehr, falls nur die Prüf-Logik entfernt
  würde.

**Nächste Runde:** `runtime/` — der Exit-Monitor, durch den jeder Verkauf
läuft.

## Runde 3 — `runtime/` (der Exit-Monitor)

**Bild zuerst:** Wenn `app.py` der Dirigent ist, ist `runtime/` sein
**Erste-Hilfe-Team** — drei ausgelagerte Organe, wortwörtlich aus `app.py`
umgezogen, damit die Datei nicht noch größer wird. Sie hängen an keinem
eigenen Zustand, sondern greifen direkt auf `app.py` zurück (technisch:
*Delegaten*).

### 1. `exit_monitor.py` — das Exit-Organ (585 Zeilen)

**Was tut sie?** Prüft **alle 30 Sekunden** jede offene Position:
aktuellen Preis holen, Gewinn/Verlust berechnen, dann der Reihe nach:
Trend-Ausstieg (aktuell im Notizbuch-Modus, siehe unten), Stop-Loss,
Take-Profit, die Ausstiegs-Leiter und Breakeven-Sperre aus
`risk/exit_rules.py` (Runde 2). Löst eine Regel aus, wird **sofort**
verkauft — nicht über die Poststelle (*Event-Bus*), sondern direkt, damit
keine Zeit verloren geht.

**Warum gibt es sie?** Das ist der Wächter, der zwischen zwei normalen
Kursabfragen wacht — er darf nicht auf den nächsten Trading-Takt warten,
sonst könnte ein Stop-Loss zu spät greifen.

**Greift sie ins Geld ein?** Ja, direkt und zentral — **jeder einzelne
Verkauf** im ganzen Bot läuft über diese Datei.

**Was bei Löschen?** Katastrophal: keine automatischen Verkäufe mehr.
Stop-Loss, Take-Profit und Trailing würden nie mehr auslösen — offene
Positionen liefen ungeschützt, bis jemand von Hand eingreift.

**Wichtig zu wissen — der Preis der Geschwindigkeit:** Weil hier direkt
verkauft wird (nicht über die Poststelle), lief 15 Tage lang **kein**
Verkauf bei den Lernmodulen an (siehe Teil 4.1). Der Fix steht jetzt
direkt in dieser Datei: nach jedem Verkauf werden `strategy_brain`,
`rl_feedback`, `adaptive_sizer`, `meta_voting` und `shadow_mode` per Hand
aufgerufen — fünf Module, einzeln abgesichert, damit ein Fehler beim
Lernen nie einen abgeschlossenen Verkauf stören kann.

**Nachtrag zu Teil 5, Punkt 2 (Trend-Ausstieg nur BTC):** Diese Regel
steht seit dem 10.08. auf **Notizbuch-Modus** (`TREND_EXIT_SCHATTEN =
True`, Zeile 24). Sie rechnet mit und schreibt in die Telemetrie-Tabelle
`schatten_exits`, verkauft aber nicht. Der BTC-only-Fehler ist also
aktuell **folgenlos für dein Geld** — erst wenn diese Zeile auf `False`
gesetzt wird, muss der Fehler vorher behoben sein.

### 2. `state_manager.py` — das Gedächtnis fürs Überleben (278 Zeilen)

**Was tut sie?** Zwei Aufgaben. `auto_save()` (alle 30 Sek.): sichert
Zustand, Journal, Vermögensverlauf und eine Sicherungskopie aller offenen
Positionen. `restore_positions()` (einmal beim Start): stellt offene
Positionen aus dieser Sicherung wieder her — und falls die Sicherung
fehlt, rekonstruiert sie Positionen notfalls aus dem tatsächlichen
Kontostand, damit kein „Geisterbestand" entsteht (eine Münze im Depot,
von der der Bot nichts weiß).

**Warum gibt es sie?** Der Bot läuft dauerhaft — ein Neustart (Absturz,
Update, Stromausfall) darf nicht dazu führen, dass er vergisst, was er
gerade hält.

**Greift sie ins Geld ein?** Nicht direkt — sie kauft und verkauft nicht.
Aber ohne sie könnte der Bot nach einem Neustart eine bereits gehaltene
Münze für „nicht vorhanden" halten und blind nachkaufen, oder umgekehrt
eine Position ohne Stop-Loss-Überwachung zurücklassen.

**Was bei Löschen?** Jeder Neustart wäre ein Reset auf „ich besitze
nichts" — mit echtem Geld im Depot, das der Bot dann nicht mehr
überwacht.

### 3. `reporting.py` — die Berichte (105 Zeilen)

**Was tut sie?** Baut den Analyse-Export (Textbericht), verschickt
Tages- und Wochenbericht per Telegram, schreibt die
„Herzschlag"-Logzeile (*Heartbeat*) mit Laufzeit und Gesamt-PnL.

**Warum gibt es sie?** Reine Information — damit du den Überblick behältst,
ohne selbst nachzuschauen.

**Greift sie ins Geld ein?** Nein — kann keinen Kauf oder Verkauf
auslösen.

**Was bei Löschen?** Keine Telegram-Berichte, keine Heartbeat-Zeile im
Log mehr. Der Handel selbst läuft unverändert weiter.

![exit_monitor.py läuft alle 30 Sekunden: Preis holen → Gewinn/Verlust berechnen → Regeln prüfen → bei Treffer sofort verkaufen → Journal und 5 Lernmodule melden. Danach beginnt die Schleife von vorn.](grafiken/runde3_exit_monitor.png)

### Leichen in diesem Ordner (Runde 11)

`exit_monitor.py.bak` (+ vier weitere `.bak_*`-Stände),
`state_manager.py.bak_20260807_toepfe1`, `state_manager.py.bak_guardfix`
— Sicherungskopien, werden nicht geladen.

### Kurzfassung für `runtime/` als Ganzes

- **Was tut er?** Drei ausgelagerte Organe: der Verkaufs-Wächter
  (`exit_monitor.py`), das Überlebens-Gedächtnis (`state_manager.py`) und
  die Berichte (`reporting.py`).
- **Warum gibt es ihn?** Damit `app.py` nicht noch größer wird — der Code
  ist wortwörtlich umgezogen, nicht neu geschrieben.
- **Greift er in den Handel ein?** `exit_monitor.py` ja, direkt und
  kritisch. Die anderen beiden nicht direkt, aber `state_manager.py` ist
  kritisch fürs Überleben eines Neustarts.
- **Was bei Löschen?** Ohne `exit_monitor.py`: keine automatischen
  Verkäufe mehr. Ohne `state_manager.py`: Positionen überleben keinen
  Neustart. Ohne `reporting.py`: nur stumm, sonst nichts.

**Nächste Runde:** `execution/` — führt die genehmigten Aufträge
tatsächlich aus.

## Runde 4 — `execution/` (führt die Order tatsächlich aus)

**Bild zuerst:** Wenn `risk/` der Türsteher ist, ist `execution/` die
**Kasse**. Hier wird nicht mehr diskutiert, ob gekauft werden darf — das
ist längst entschieden. Hier passiert die eigentliche Order, mit allen
Sicherungen gegen Wackelkontakt: doppelt gesendete Bestellungen, eine
kranke Börsen-Verbindung, ein Netzwerk-Aussetzer mittendrin.

### 1. `engine.py` — die Hauptkasse (532 Zeilen)

**Was tut sie?** Jede Order durchläuft dieselbe Kette, egal ob Papier-
oder Echtgeld-Modus:

![execution/engine.py execute(): Kaufwunsch → Doppel-Order-Sperre → Schlafmodus-Check (nur Kauf) → Bargeld reservieren (nur Kauf) → Papier oder Börse ausführen → Ergebnis. Im Live-Modus zusätzlich über Circuit-Breaker und Retry.](grafiken/runde4_execution.png)

Im **Papier-Modus** simuliert sie eine echte Order realistisch mit: eine
zufällige Verzögerungskosten (*Slippage*, 0,02–0,08 %) und Binance-Gebühr
(0,10 %) — damit die Zahlen im Journal nicht schöner aussehen, als sie im
Echtbetrieb wären.

Im **Live-Modus** kommen drei zusätzliche Sicherungen dazu, bevor
überhaupt eine echte Order rausgeht:
1. **Freigabe-Prüfung** (`go_live_check.py`) — trägt die Statistik den
   Echtgeld-Betrieb überhaupt?
2. **Schlüssel-Rechte-Check** — darf der API-Schlüssel Geld **abheben**?
   Wenn ja: sofortiger Abbruch. Ein Handelsbot braucht nur Kauf-/Verkaufs-
   Rechte, nie Auszahlung.
3. **Order-Deckel** — ein harter Höchstbetrag je Order, unabhängig davon,
   was die Positionsgrößen-Rechnung ausgibt. Ein Rechenfehler irgendwo
   davor darf im Echtbetrieb nie das halbe Konto in eine Order kippen.

**Warum gibt es sie?** Sie ist die letzte Stelle vor der Börse — hier
entscheidet sich, ob aus einer Absicht ein tatsächlicher Kauf oder
Verkauf wird.

**Greift sie ins Geld ein?** Ja, direkt und vollständig — das ist ihre
einzige Aufgabe.

**Was bei Löschen?** Kein einziger Trade mehr möglich, weder Papier noch
echt.

### 2. `circuit_breaker.py` — der Sicherungsautomat

**Was tut sie?** Zählt Fehler bei Börsen-Anfragen. Ab 5 Fehlern in Folge
sperrt sie **alle** weiteren Anfragen für 60 Sekunden — testet danach
vorsichtig mit einer einzelnen Anfrage, ob die Verbindung wieder gesund
ist, bevor sie ganz öffnet.

**Warum gibt es sie?** Ohne diese Bremse würde der Bot bei einer kranken
Börsen-Verbindung immer weiter erfolglos anfragen — im schlimmsten Fall
mit halbfertigen Anfragen, die die Buchhaltung durcheinanderbringen.

**Greift sie ins Geld ein?** Nur im Live-Modus, und nur als Bremse (kann
keinen Kauf auslösen, nur verhindern).

**Was bei Löschen?** Bei einer Börsen-Störung würde der Bot ungebremst
weiter senden, statt eine Pause einzulegen.

### 3. `retry_policy.py` — die Wiederholung

**Was tut sie?** Wenn eine Anfrage an Netzwerk-Problemen scheitert
(Timeout, Rate-Limit), versucht sie es automatisch erneut — mit wachsender
Wartezeit dazwischen. Bei einem **echten** Fehler (falsche Order, kein
Guthaben) wird **nicht** wiederholt, sondern sofort aufgegeben.

**Warum gibt es sie?** Unterscheidet „das Netz hatte kurz einen Hänger"
von „das war ein echter Fehler" — nur Ersteres verdient einen zweiten
Versuch.

**Greift sie ins Geld ein?** Nur im Live-Modus.

**Was bei Löschen?** Jede kurze Netzwerkstörung würde die Order sofort
scheitern lassen, statt es nochmal zu versuchen.

### 4. `idempotency.py` — die Doppel-Order-Sperre

**Was tut sie?** Gibt jeder Order eine eindeutige Kennung. Kommt dieselbe
Kennung ein zweites Mal (z. B. weil eine Antwort verloren ging und der
Bot es sicherheitshalber nochmal versucht), wird die zweite Order
**blockiert**.

**Warum gibt es sie?** Bei einem Netzwerk-Timeout weißt du nie sicher, ob
die erste Order angekommen ist. Ohne diese Sperre könnte derselbe Kauf
versehentlich zweimal ausgeführt werden.

**Greift sie ins Geld ein?** Ja — verhindert doppeltes Geldausgeben.

**Was bei Löschen?** Ein Netzwerk-Aussetzer könnte zu einer versehentlich
doppelt so großen Position führen.

### 5. `order_manager.py` — das Order-Gedächtnis

**Was tut sie?** Speichert jede Order lokal, **bevor** sie an die Börse
geht, und aktualisiert sie danach mit dem Ergebnis (gefüllt, abgelehnt,
Fehler). Führt zusätzlich eine Statistik: wie viele Orders liefen glatt,
wie viele scheiterten, wie schnell war die Börse im Schnitt.

**Warum gibt es sie?** Eine eigene Buchhaltung neben der Börse — falls
mal etwas nicht zusammenpasst, gibt es zwei unabhängige Aufzeichnungen
zum Vergleichen.

**Greift sie ins Geld ein?** Nein, reine Aufzeichnung.

**Was bei Löschen?** Kein Order-Verlauf mehr, keine Statistik. Der Handel
selbst liefe weiter.

### 6. `fill_reconciler.py` — der Abgleicher

**Was tut sie?** Vergleicht, alle 5 Minuten (aus `app.py`, Runde 1), was
die Börse als offene Orders und letzte Geschäfte meldet, mit dem, was der
Bot lokal glaubt zu wissen. Findet drei Arten von Abweichungen: eine
Order, die lokal offen scheint, aber bei der Börse verschwunden ist; eine
Order bei der Börse, von der der Bot nichts weiß; oder ein Preis, der
deutlich (>0,5 %) vom erwarteten abweicht.

**Warum gibt es sie?** Damit eine Diskrepanz zwischen „was der Bot denkt"
und „was wirklich passiert ist" nicht unbemerkt bleibt.

**Greift sie ins Geld ein?** Nein — meldet nur, greift nicht ein.

**Was bei Löschen?** Ein Auseinanderlaufen von Buchhaltung und Realität
würde nicht mehr auffallen, bis es sich an anderer Stelle zeigt.

### 7. `twap_executor.py` — der Order-Teiler

**Was tut sie?** Teilt große Orders (ab 1.000 $, aus `app.py`) in 2–5
kleinere Teilaufträge, die über mehrere Minuten verteilt gesendet werden.

**Warum gibt es sie?** Eine sehr große Order auf einmal bewegt den Kurs
gegen dich (der Markt „merkt" den großen Kauf). Kleinere Häppchen sind
unauffälliger und im Schnitt günstiger.

**Greift sie ins Geld ein?** Ja, bei großen Positionen — aktiv im Einsatz.

**Was bei Löschen?** Große Orders liefen wieder als ein einziger Block —
teurer bei starkem Kursimpakt.

### 8. `futures_trader.py`, `multi_exchange.py` — angeschlossen, aber im Leerlauf

**Was tun sie?** `futures_trader.py` könnte gehebelte Termingeschäfte
handeln (*Futures*, bis 3-fach Hebel), `multi_exchange.py` könnte
mehrere Börsen gleichzeitig nutzen und den besten Preis wählen.

**Ehrliche Einordnung:** Beide werden beim Start verbunden — aber
**keine einzige Kaufentscheidung im Bot ruft sie tatsächlich zum Handeln
auf.** Geprüft: nur `get_status()` wird gelesen (fürs Dashboard), nie
`buy()`/`sell()` bei Futures, nie ein echter Order-Weg über eine zweite
Börse. Reine Vorbereitung für später.

**Greift sie ins Geld ein?** Nein, aktuell nicht.

**Was bei Löschen?** Nichts würde sich am heutigen Handel ändern.

### Nicht angeschlossen: `exchange_client.py`

**Auffällig:** Diese Datei wird **von nirgends im ganzen Projekt
importiert** — anders als die Leichen unten trägt sie keinen `.bak`-
oder `.UNUSED`-Namen, sieht also auf den ersten Blick wie aktiver Code
aus. `engine.py` verbindet sich stattdessen direkt über `ccxt` (die
Börsen-Bibliothek) selbst. Vermutlich ein früherer Anlauf, der durch
`engine.py` ersetzt wurde, ohne aufgeräumt zu werden. Für Runde 11
vorgemerkt — kein Risiko, aber verwirrend, wenn man danach sucht.

### Leichen in diesem Ordner (Runde 11)

`engine.py.bak_paperbuy_20260805`, `engine.py.bak_sleepmode_20260804` —
Sicherungskopien, werden nicht geladen.

### Kurzfassung für `execution/` als Ganzes

- **Was tut er?** Die Kasse — führt genehmigte Orders tatsächlich aus,
  mit Sicherungen gegen Doppel-Orders, kranke Verbindungen und
  Netzwerk-Aussetzer.
- **Warum gibt es ihn?** Zwischen „genehmigt" und „tatsächlich passiert"
  liegt bei einer Börsen-Anbindung viel, das schiefgehen kann.
- **Greift er in den Handel ein?** Ja, direkt — hier wird das Geld
  tatsächlich bewegt.
- **Was bei Löschen?** Kein Trade mehr möglich, weder Papier noch echt.

**Nächste Runde:** `agents/` + `models/` — die Gedächtnisse und
Strategien.

## Runde 5 — `agents/` + `models/` (die Gedächtnisse und Strategien)

**Bild zuerst:** Das ist der **Ratssaal**. Viele Stimmen (technische
Indikatoren, externe Quellen, bewährte V4-Strategien, Marktphase) reden
mit, bevor der Signal-Agent daraus eine einzige Kauf-Entscheidung formt.

![Wie aus vielen Meinungen ein Kaufsignal wird: vier Quellen fließen in Signal-Agent + Strategie-Gehirn, das Ergebnis ist der Kaufwunsch. Eine eigene Zeile zeigt, was gebaut, aber nirgends angeschlossen ist.](grafiken/runde5_signalquellen.png)

### `agents/` — wer mitredet und wer handelt

**`signal_agent.py`** — das **Herzstück**: sammelt Punkte aus RSI, MACD,
EMA-Trend, ADX, Fear & Greed, Bollinger-Band, RSI-Divergenz,
Volumen-Sprung, den externen Ensemble-Quellen und der V4-Bridge. Ab
**3 von 10 möglichen Punkten** wird gekauft. Prüft daneben als
**Notaus-Netz** einen zweiten, unabhängigen Verkaufsgrund (0,5 % hinter
dem eigentlichen Stop aus Runde 3) — löst der aus, hat der
Exit-Monitor versagt, und das steht als Alarm im Verkaufsgrund.
*Greift direkt ins Geld ein — Löschen: keine Kaufsignale mehr.*

**`strategy_brain.py`** — das **Strategie-Gedächtnis** aus
Teil 1.1: wählt von 13 hinterlegten
Strategien die, die am besten zu Marktphase und Regime passt, gewichtet
mit der bisherigen Erfolgsbilanz. *Greift direkt ein — Löschen: alle
Strategien gelten gleich viel, unabhängig davon, was bisher funktioniert
hat.*

**`v4_strategies.py`** — die **V4-Bridge**: portiert 7 Strategien, die im
Vorgänger-Bot V4 nachweislich funktioniert haben (266 Trades,
+1.269,60 €), mit ihren echten Erfolgsquoten als Startgewicht.
*Greift direkt ein (Score-Boost bis +4 Punkte) — Löschen: der Bot startet
wieder bei null Erfahrung, wie am 04.08. vor dem V4-Bridge-Fix.*

**`cycle_theory.py`** — die **4-Jahres-Zyklus-Uhr**: bestimmt aus Tagen
seit dem letzten BTC-Halving und Abstand zum Allzeithoch, in welcher
Marktphase wir stecken (z. B. `MID_BEAR`, `ACCUMULATION`).
*Greift indirekt ein — beeinflusst Strategie-Wahl, Positionsgröße und
Risiko-Profil (Runde 2). Löschen: alle Phasen-Anpassungen verlieren ihre
Grundlage.*

**`btc_accumulator.py`** — der **BTC-Sparplan**: kauft regelmäßig BTC
unabhängig vom Handelssignal (1/3-Regel) und wandelt eingelöste Gewinne
zusätzlich in BTC um. *Greift direkt ein — eigener Kapital-Topf (E10-KAPITAL, 29.07., macht
20,7 % des Vermögens aus und zählt seither überall mit).
Löschen: kein langfristiger BTC-Aufbau mehr, nur noch die normale
Handelslogik.*

**`dca_advanced.py`** — der **Nachkäufer**: kauft in regelmäßigen,
durch Angst/Gier dynamisch verkürzten oder verlängerten Abständen nach
(4× öfter bei extremer Angst, 3× seltener bei Gier). *Aktiv im Einsatz —
Löschen: kein automatisches Nachkaufen mehr in fallenden Märkten.*

**`smart_entry.py`** — der **Geduldige**: wartet nach einem Kaufsignal
bis zu 5 Minuten auf einen 1-%-Rücksetzer, um günstiger einzusteigen —
kauft nach Timeout oder bei weiterem Anstieg trotzdem. *Aktiv im
Einsatz — Löschen: jeder Kauf geht sofort zum Signalpreis raus, ohne den
Versuch, günstiger reinzukommen.*

**`grid_bot.py`** — der **Raster-Käufer** für Seitwärtsphasen (kauft an
8 Bollinger-Stufen). **Aktuell abgeschaltet** (`grid_enabled: false`,
bewusste Entscheidung vom 29.07., siehe `app.py`-Kommentar E11-GRID —
sauberes Messfenster ohne zweiten Einstiegspfad).

**`context_agent.py`** — liest Krypto-News und bewertet sie als
bullisch/bärisch (Wortliste, kein Bezahl-KI-Zugang nötig), liefert dazu
Text-Erklärungen zu Trades. *Fließt als ein Signal unter vielen ein —
Löschen: eine Stimme weniger im Ratssaal, kein Totalausfall.*

**`arbitrage_agent.py`** — **reines Radar**: sucht Preisunterschiede
zwischen Binance und Bybit. Geprüft: löst **keinen einzigen Trade** aus,
meldet nur. *Kein Einfluss aufs Geld — reine Beobachtung.*

**`strategy_export.py`** — Werkzeug zum Exportieren der aktuellen
Einstellungen als JSON-Datei, auf Zuruf, nicht automatisch. *Kein
Handelseinfluss.*

**Angeschlossen, aber im Leerlauf:** `grid_trader.py` (zweite,
unabhängige Grid-Klasse — nur `get_status()` wird gelesen, `setup_grid()`
nie aufgerufen) und `llm_local.py` (lokales KI-Modell über Ollama, nur
`get_status()` gelesen). Beide bauen — wie `futures_trader.py` und
`multi_exchange.py` aus Runde 4 — Funktionen, die aktuell **niemand
aufruft**.

### `models/` — was gelernt wird (und was nicht)

**Bereits ausführlich in Teil 1 („Was der Bot lernt")
beschrieben** — hier nur die Datei-Zuordnung:

| Datei | Gehört zu | Stand |
|---|---|---|
| `brain_persistence.py` | 1.1 Strategie-Gedächtnis | lädt/speichert `brain_performance.json` |
| `lern_journal_v6.py` | 1.1 (neuer, sauberer Zähler) | sammelt seit 11.08., noch dünn |
| `v4_calibrator.py` | V4-Bridge-Gewichtung | sperrt Verlierer-Strategien (Gewicht 0,0) automatisch |
| `rl_feedback.py` | 1.2 Belohnungs-Zähler | Verfall seit 11.08. abgeschaltet |

**`meta_voting.py`** — gehört zu Teil 1.4 („Die Agenten-Abstimmung").
**Befund dieser Runde, seit 11.08. abends behoben (siehe Teil 4.7):**
Die Gewichte werden bei jedem Verkauf korrekt nachgerechnet — **aber**
an der einzigen Stelle, wo sie etwas bewirken könnten (`app.py:2147`),
landete das Ergebnis in einer Variable, die niemand danach noch las. Der
tatsächliche Signal-Score nutzte stattdessen die ungewichteten Rohwerte.
Die Lern-Blockade vom 27.07. war schon vorher behoben (siehe Teil 4.1) —
aber ohne diesen zweiten Fix hätte das für sich genommen keine Wirkung
auf künftige Käufe gehabt. Jetzt fließt der gewichtete Wert per
50/50-Mischung tatsächlich in jeden Handelstakt ein.

**`ensemble_signal.py`** — kombiniert alle externen Quellen
(technisch 30 %, ML-Modell 20 %, Fear&Greed 15 %, Funding 10 %, Onchain
8 %, VWAP 7 %, Reddit 5 %, Politiker-Trades 3 %, Wale 2 %) zu einem
Score. *Aktiv im Einsatz — fließt direkt in den Signal-Score.*

**Die ML-Baustelle — vier Dateien, seit 11.08. abends im Notizbuch-Modus
(siehe Teil 4.8):** `xgboost_model.py`, `signal_model.py`,
`regime_model.py` und `model_registry.py` sind ein vollständiges
Trainings- und Modell-Verwaltungssystem für maschinelles Lernen. In der
Formel von `ensemble_signal.py` ist ein 20-%-Platz für „ml_model"
reserviert — der bleibt **bewusst leer**. Das Modell rechnet seit dem
Fix bei jedem Takt mit und wird protokolliert, entscheidet aber nichts,
bis gemessen ist, ob es überhaupt Vorhersagekraft hat. Beim Reparieren
kamen drei versteckte Fehler ans Licht (falsches Modell geladen,
Vorhersage konnte technisch nie funktionieren, erfundene Versionsnummer)
— alle behoben, alle in Teil 4.8 erklärt. *Kein Einfluss aufs Geld.*

### Leichen in diesem Ordner (Runde 11)

`signal_agent.py.bak_einheit`, `strategy_brain.py.hooks_20260604_214935`,
`v4_strategies.py.bak_argmax_20260804` — Sicherungskopien, unbenutzt.

### Kurzfassung für `agents/` + `models/` als Ganzes

- **Was tut er?** Der Ratssaal — viele Meinungen (Indikatoren, externe
  Quellen, V4-Erfahrung, Marktphase) werden zu einem Score verdichtet,
  aus dem der Kaufwunsch entsteht. Danach lernen mehrere Gedächtnisse aus
  dem Ergebnis.
- **Warum gibt es ihn?** Eine einzelne Meinung liegt öfter daneben als
  ein gewichteter Konsens vieler.
- **Greift er in den Handel ein?** `signal_agent.py` und
  `strategy_brain.py` ja, zentral. Ein gutes Drittel der Dateien in
  diesem Ordnerpaar (Grid-Trader, lokales LLM, die vier ML-Dateien,
  Meta-Voting-Wirkung) ist gebaut, aber **aktuell ohne Wirkung** —
  ehrlich benannt statt verschwiegen.
- **Was bei Löschen?** `signal_agent.py` weg heißt: keine Kaufsignale
  mehr, der Bot verkauft nur noch bestehende Positionen leer. Die
  Leerlauf-Dateien wegzunehmen änderte am heutigen Handel nichts.

**Nächste Runde:** `features/` — Zusatzfunktionen wie Chartanalyse,
Regime-Erkennung und der Sensei.

## Runde 6 — `features/` (Zusatzfunktionen)

**Bild zuerst:** Der **Werkzeugkasten** — 26 Dateien, drei Fünftel davon
Werkzeuge, die messen, erklären oder aufschreiben, ohne selbst Geld zu
bewegen. Nach Aufgabe sortiert:

### Was in jede Kaufentscheidung einfließt

`rsi_divergence.py`, `vwap_agent.py` und `regime_detection.py`
(`RegimeDetector`, aus Runde 1 schon bekannt) — alle drei aktiv, alle
drei Stimmen im „Ratssaal" aus Runde 5.

**Korrektur (Runde 12):** `indicators.py` (`calc_all_indicators`) hatte
ich hier fälschlich als „gemeinsame Rechenbasis für alle Module"
beschrieben. Tatsächlich rechnet der Live-Signalpfad seine Indikatoren
**komplett separat** und doppelt in `data/market_data.py` (Runde 7) —
dieselben Formeln, aber eigener Code. `calc_all_indicators` hat nur
**einen** echten Aufrufer: `models/train_pipeline.py` — Teil der
ML-Baustelle aus Runde 5, die gerade nicht am Steuer ist. Bestätigt
durch die Architektur-Datenbank des Forschungsprogramms. Kein Bug —
nur doppelte statt gemeinsame Rechenlogik, was bedeutet: eine künftige
Änderung an einer Indikator-Formel muss an **zwei** Stellen gepflegt
werden, nicht an einer.

`multi_timeframe.py` gehört auch dazu, aber mit Einschränkung: läuft
laut `app.py:2082` nur für **einen** Coin (`coins[:1]`, also BTC) — genau
das Loch, das in Runde 3 den Trend-Ausstieg für ETH/SOL wirkungslos
machte.

### Die lernenden Wächter

`regime_adaptiv.py` ist **Teil 1.5** aus dem Gehirn-Kapitel — hier nur
die Datei-Zuordnung. `bottom_detection.py` (`BottomDetector`, Multi-
Indikator-Bodenerkennung) ist ein **neuer Fund**: wird beim Start gebaut
(sogar zweimal, siehe die Doppelung aus Runde 1), aber die einzige
Methode, die etwas berechnet (`evaluate()`), **ruft niemand im ganzen
Projekt auf**. Gebaut, nie angeschlossen.

### Buchhaltung, Diagnose, Doku

`waechter.py` — der Buchhaltungs-Prüfer: alle 5 Minuten drei eiserne
Regeln (keine Position größer als der echte Bestand, kein unbeobachteter
Coin-Bestand, USDC nie negativ). Liest nur, warnt per Telegram, greift
nie ein. `tickets_watcher.py` frisst `tickets.txt` alle 30 Sekunden und
reicht Einträge an `doc_agent.py` weiter, der daraus
`ENTWICKLERHANDBUCH.md` schreibt — das technische Gegenstück zu diesem
`BOT-HANDBUCH.md`. `impact_journal.py` ist **Teil 1.3** (das
Phasen-Gedächtnis).

### Nur Messung, kein Handel

`chartanalyse.py` (klassische Chartmuster — Support/Widerstand,
Doppel-Tief, Kopf-Schulter — mechanisch nachgerechnet, mit eingebauter
Absicherung gegen Zukunftswissen im Backtest) und `chartanalyse_agent.py`
(hält diese Messung täglich aktuell, Runde 1). Beide sagen von sich
selbst: „wird von keinem Kaufpfad importiert". Passt zur bereits
bekannten Zahl aus Teil 3.1: rund 70 % Trefferquote — **und trotzdem
nicht eingebaut**, weil Ziele zu nah und Stops zu weit lagen.

### Der Lehrer

`sensei.py` — passend zum Namen, den du mir gegeben hast: übersetzt
Signal-Begründungen aus dem Log in Klartext-Deutsch und schreibt nach
jedem Handelstag Lektionen mit konkreten Verbesserungsideen in
`SENSEI_LEKTIONEN.md`. Selbst dokumentiert: „Greift NIRGENDS in die
Trading-Logik ein — liest nur Dateien." Ein Erklärer, kein Händler —
genau wie ich hier gerade.

### Befehle in diesem Ordner (per Hand ausführbar)

Acht Dateien hier lassen sich direkt aufrufen, nicht nur vom Bot:

| Befehl | Was er tut |
|---|---|
| `python features/chartanalyse_agent.py` | Führt die tägliche Chartanalyse-Messung sofort aus (statt auf den Nacht-Takt zu warten) und druckt das Ergebnis — genau das Konsolen-Bild aus deinem Screenshot |
| `python features/regime_adaptiv.py` | Führt die Regime-Lernen-Messung sofort aus, zeigt Rendite, Entscheidung und Begründung |
| `python features/akademie.py` | Startet den Lerngang zu deinen echten Trades direkt in der Konsole (Textmenü) |
| `python features/chart_data.py` | Lädt Kerzendaten für alle 12 Handels-Coins in den Chart-Cache (`data_store/charts/`) |
| `python features/chart_view.py` | Selbsttest: rendert einen Beispiel-Chart als PNG, ohne dass ein Fenster nötig ist |
| `python features/stoploss_edge.py` | Stop-Loss-Kantenanalyse auf echten Kursdaten, druckt einen Bericht |
| `python features/strategy_lab.py` | Strategie-Labor-Analyse auf echten Kursdaten, druckt einen Bericht |
| `python features/situation_memory.py` | Nur ein Selbsttest mit erfundenen Daten — **kein** echtes Werkzeug für den Alltag |

Keiner dieser Befehle verändert etwas am laufenden Bot — sie lesen
Daten und drucken ein Ergebnis.

### Die Chart-Oberfläche (Desktop-Fenster)

**Wichtiger Fund:** `app.py` startet am Ende (Zeile 3552) standardmäßig
ein **Desktop-Fenster** (`ui/main_window.py`) — nur mit dem Schalter
`--headless` bleibt es weg. `start_bot.bat` übergibt diesen Schalter
**nicht**. Fünf Dateien hier gehören zu diesem Fenster und werden von
nirgends sonst gebraucht: `akademie.py` (Lerngang anhand deiner echten
Trades), `chart_view.py` + `chart_data.py` (der Kerzenchart mit deinen
Kauf/Verkauf-Markierungen), `stoploss_edge.py` und `strategy_lab.py`
(Was-wäre-wenn-Analysen auf echten Kursdaten — beide ausdrücklich „reine
Analyse, kein Trading-Eingriff"). `chart_refresher.py` hält den
Kerzen-Cache dafür automatisch frisch. Alle fünf werden **ausführlich in
Runde 9** (`ui/`) behandelt — hier nur vermerkt, damit klar ist: das sind
keine Karteileichen, sondern die Oberfläche, die du vermutlich gerade vor
dir hast, wenn der Bot läuft.

**Kurze Zwischenfrage an dich:** Siehst du beim Starten normalerweise
ein Fenster mit Charts, oder läuft bei dir nur das schwarze Konsolen-
Fenster? Das entscheidet, ob diese fünf Dateien bei dir wirklich aktiv
sind.

### `safety.py`

Schon in Runde 4 beschrieben (Cash-Reservation, Rate-Limit, Ablehnungs-
Zähler) — hier nur die Ordner-Zuordnung.

### Gebaut, aber an keiner Stelle angeschlossen

- **`market_regime.py`** — **verwirrender Fund:** enthält eine zweite
  Klasse, die genauso heißt wie die echte (`RegimeDetector`), aber
  komplett unabhängig und **nirgends importiert** ist. Zwei gleichnamige
  Klassen mit unterschiedlichem Inhalt in einem Projekt sind ein
  Stolperdraht für jede künftige Änderung — wer aus Versehen von hier
  statt aus `regime_detection.py` importiert, bekommt ein anderes
  Verhalten, ohne dass ein Fehler auftaucht.
- **`labels.py`** und **`portfolio_features.py`** — gehören zur
  ML-Baustelle aus Runde 5 (Trainings-Etiketten bzw. Portfolio-Kennzahlen
  fürs maschinelle Lernen). Niemand ruft sie auf.
- **`situation_memory.py`** — **schon selbst dokumentiert:** trägt einen
  Warnblock im Kopf der Datei („NICHT VERDRAHTET, Stand 11.08.2026") und
  eine ausdrückliche Entscheidung, sie so liegen zu lassen, weil Entfernen
  Arbeit kostet und `situation_replay.py` (ein Hand-Werkzeug) daran hängt.
  Kein Risiko, weil null Laufzeit-Bezug.
- **Drei leere Dateien:** `cd`, `dir` und `python` (0 Byte, vom
  11.06.2026) — vermutlich ein Tippfehler im Terminal, bei dem
  Windows-Befehle versehentlich als Dateinamen gelandet sind. Harmlos,
  aber gehören in keinen Code-Ordner. Kandidat zum Löschen in Runde 11.

### Kurzfassung für `features/` als Ganzes

- **Was tut er?** Ein Werkzeugkasten: ein Teil liefert Stimmen für die
  Kaufentscheidung (Runde 5), ein größerer Teil misst, erklärt oder
  dokumentiert, ohne einzugreifen.
- **Warum gibt es ihn?** Damit `app.py` schlank bleibt und jede
  Zusatzfunktion einzeln testbar ist.
- **Greift er in den Handel ein?** Nur die erste Gruppe (Indikatoren,
  RSI-Divergenz, VWAP, Regime). Alles mit „reine Analyse" oder „liest
  nur" im eigenen Kommentar greift nicht ein — und das steht bei
  auffällig vielen Dateien hier ausdrücklich so im Code.
- **Was bei Löschen?** Unterschiedlich stark: `indicators.py` weg würde
  den Bot lahmlegen (Grundlage für fast alles). `sensei.py` oder
  `waechter.py` weg würde nichts am Handel ändern, nur an dem, was du
  darüber erfährst.

**Nächste Runde:** `data/` — woher die Zahlen kommen.

## Runde 7 — `data/` (woher die Zahlen kommen)

**Bild zuerst:** Das **Beschaffungsamt** — 19 Dateien, die draußen
Zahlen einsammeln (Kurse, Stimmung, Wal-Bewegungen, Dollar-Stärke) und
sauber aufbereitet nach innen weiterreichen.

### Der Kern: Kurse holen

**`market_data.py`** (`DataAgent`) — die **Quelle allen Handels**: holt
Kerzen von der Börse, rechnet RSI/EMA/MACD/Bollinger/ADX/ATR direkt mit
rein und veröffentlicht das Ergebnis als `MarketSnapshot` — genau das
Signal, das in Runde 1 `_on_market_update` auslöst. Fällt die
Börsen-Anfrage aus, bleibt der **alte** Cache-Preis stehen (mit
Alters-Stempel), statt mit 0 weiterzurechnen.
*Greift direkt ein — Löschen: der Bot ist blind, kein einziger Kurs mehr,
kein Handel mehr möglich.*

**`websocket_stream.py`** — derselbe Zweck, aber in Echtzeit: eine
dauerhafte Verbindung zur Börse statt wiederholtem Nachfragen (*Polling*).
Schneller, weniger Anfragen. *Optional — fällt sie aus, greift
`market_data.py` normal weiter per Nachfrage.*

**`source_health.py`** — der **Gesundheits-Wächter** aus dem
E10-QUELLEN-Fix (schon in Runde 1 erwähnt): eine ausgefallene Quelle
(z. B. Reddit mit Status 403) fällt jetzt ganz aus der Gewichtung, statt
mit einer Ersatz-0,5 weiter mitzuzählen. Vorher zog eine tote Quelle
jedes echte Signal Richtung neutral — unsichtbar, weil überall
`except: pass` stand.
*Greift indirekt ein — entscheidet, welche der folgenden Quellen zählen.*

### Aktive Zusatzquellen (füttern den Ratssaal aus Runde 5)

| Datei | Liefert | Wirkung |
|---|---|---|
| `nupl_monitor.py` | Euphorie-Zone-Näherung | **blockiert Käufe** über 0,7 (Zeile `should_block_buys`) + Größen-Multiplikator |
| `dxy_monitor.py` | Dollar-Index-Trend | Größen-Multiplikator (steigt der Dollar, hält sich der Bot zurück) |
| `funding_rates.py` | Funding-Rate (Futures-Markt) | Ensemble-Score-Zutat |
| `whale_alerts.py` | große Geldbewegungen | Ensemble-Score-Zutat |
| `capitol_trades.py` | Politiker-Trades (USA) | Ensemble-Score-Zutat |
| `onchain_analytics.py` | SOPR, NVT, aktive Adressen | Ensemble-Score-Zutat |
| `orderbook_depth.py` | Kauf-/Verkaufsdruck im Orderbuch | fließt direkt in den Signal-Score |
| `sentiment_data.py` | Fear & Greed Index | zentraler Haupttreiber (siehe Runde 5) |
| `reddit_sentiment.py` | Reddit-Stimmung | Ensemble-Score-Zutat — **liefert seit Wochen HTTP 403** (Teil 5, Punkt 4), fällt dank `source_health.py` sauber aus der Gewichtung statt zu verfälschen |

Zwei davon (`nupl_monitor.py`, `dxy_monitor.py`) sind die einzigen in
diesem Ordner mit **direktem Eingriff** — alle anderen liefern nur eine
von vielen Stimmen im Ensemble.

**`feature_store.py`** — speichert berechnete Kennzahlen für das
ML-Training. Gehört zur ML-Baustelle aus Runde 5: sammelt fleißig, aber
das, was daraus trainiert würde, liest aktuell niemand.

### Gebaut, aber ohne Anschluss

**`cache.py`** (`DataCache`) und **`data_quality.py`**
(`DataQualityChecker`) — nur in `tests/test_data.py` referenziert, in
keinem Live-Pfad. `market_data.py` hat eine eigene, einfachere
Cache-Logik direkt eingebaut und nutzt diese beiden nicht.

**`dxy_filter.py`** (`DXYFilter`) und **`news_data.py`**
(`NewsDataProvider`) — nur von einem Forschungs-Skript
(`docs/messungen_2026-07/code/messung_f2_ic.py`) genutzt, nicht vom
laufenden Bot. Verwechslungsgefahr: `dxy_monitor.py` (aktiv) klingt fast
identisch zu `dxy_filter.py` (inaktiv).

**`top_coins.py`** (`TopCoinsUpdater`) — **komplett verwaist**, keine
einzige Fundstelle im ganzen Projekt außer der Datei selbst.

**`v4_importer.py`** — Werkzeug für die einmalige Übernahme alter
V4-Daten (`scripts/migrate_v4_to_v6.py`), kein Teil des laufenden
Betriebs.

### Leichen in diesem Ordner (Runde 11)

`market_data.py.bak_p1harden`, `market_data.py.bak_p4f` — Sicherungskopien.

### Kurzfassung für `data/` als Ganzes

- **Was tut er?** Beschafft alles, was von außen kommt: Kurse in
  Echtzeit, dazu neun externe Stimmungs- und Kontext-Quellen.
- **Warum gibt es ihn?** `app.py` und der Ratssaal (Runde 5) sollen sich
  nie selbst um HTTP-Anfragen und Caching kümmern müssen.
- **Greift er in den Handel ein?** `market_data.py` ist die Grundlage
  von allem. `nupl_monitor.py` und `dxy_monitor.py` greifen direkt ein.
  Der Rest liefert Stimmen fürs Ensemble — und vier Dateien
  (`cache.py`, `data_quality.py`, `dxy_filter.py`, `news_data.py`,
  `top_coins.py`) haben aktuell **gar keinen** Anschluss.
- **Was bei Löschen?** `market_data.py` weg heißt: Totalausfall, der Bot
  bekommt nie wieder einen Kurs. Die verwaisten Dateien wegzunehmen
  änderte am heutigen Handel nichts.

**Nächste Runde:** `core/` — das Innenleben: Ereignisse, Telemetrie,
Zeitplan.

## Runde 8 — `core/` (das Innenleben)

**Bild zuerst:** Der **Maschinenraum** — hier stehen keine
Handelsentscheidungen, sondern die Technik, die alles am Laufen hält:
die Poststelle, der Zeitplan, das Gedächtnis fürs Überleben, die
Fehlerakte.

**`bus.py`** (`EventBus`) — die **Poststelle** aus Runde 1: verteilt
jedes Ereignis an alle, die zugehört haben. Seit dem Sichtbarkeits-Fix
vom 06.08. landet jeder Fehler in einem Abonnenten zusätzlich in einer
eigenen, nie rotierenden Fehlerakte (`bus_errors.log`) — genau das hätte
den 15.000-Signale-Vorfall sofort sichtbar gemacht.
*Zentral — Löschen: kein Modul erführe mehr von einem anderen.*

**`events.py`** — die **Wörterbuch-Datei**: definiert die drei
Datenpakete, die durchs System fließen (Marktdaten, Kaufwunsch,
Ausführungs-Ergebnis) und alle Status-Namen. Reine Struktur, kein
eigenes Verhalten.

**`scheduler.py`** — der **Zeitplan** aus Runde 1: prüft jede Sekunde,
welche der ~25 wiederkehrenden Aufgaben fällig sind, und startet jede in
einem eigenen Thread — damit ein langsamer Task (z. B. der Trading-Loop)
niemals den Stop-Loss-Wächter blockiert.
*Zentral — Löschen: keine der wiederkehrenden Aufgaben liefe mehr.*

**`state_store.py`** — das **Überlebens-Gedächtnis**: speichert
jeden Zustand dreifach abgesichert (temporäre Datei → Sicherungskopie →
erst dann die echte Datei ersetzen), damit ein Absturz mitten im
Schreiben nie eine kaputte Datei hinterlässt. Lädt beim Start notfalls
aus der `.bak`- oder `.tmp`-Version. *Zentral für `state_manager.py` aus
Runde 3.*

**`health.py`** — der **Puls-Messer**: jede Komponente meldet sich
regelmäßig („Herzschlag"), bleibt der aus, gilt sie als tot. Kann bei
registrierten Komponenten sogar automatisch einen Neustart versuchen
(max. 3×).

**`logger.py`** — das **Protokoll**: jede Zeile mit Zeitstempel, Modul
und Stufe, gleichzeitig im Arbeitsspeicher (für die Oberfläche) und in
`system.log` (rotiert automatisch ab 20 MB, damit die Datei nicht
unbegrenzt wächst).

**`telemetrie.py`** — die **Telemetrie-Datenbank** aus Teil 2.1, hier
nur die Ordner-Zuordnung. Wichtig für dich: dies ist genau die
vollständige Betriebs-Telemetrie des Live-Bots, getrennt von
`forschung.db` — der offene Auftrag dazu ist mit dieser Datei bereits
weitgehend erfüllt (`evaluations`, `rule_evaluations`,
`lern_ereignisse`, `markt_historie`, `schatten_*`, `jobs` — alles
bereits in Betrieb).

**`hintergrund.py`** — Teil 4.4 (Keine schwarzen Fenster mehr): startet
Hintergrundjobs unsichtbar, aber mit Pflicht-Protokoll (Start, Ende,
Exit-Code, Fehlerauszug) und einer Sperrdatei gegen Doppelstart.

**`auto_restart.py`** — überwacht registrierte Agenten und versucht bei
Einfrieren (120 Sek. ohne Lebenszeichen) einen automatischen Neustart.

**`exceptions.py`** — eigene Fehlerklassen (`RiskVetoError`,
`InsufficientBalanceError`, …) statt allgemeiner Python-Fehler — macht
im Log auf den ersten Blick klar, **welche Art** Problem vorliegt.

**`regel_schalter.py`** — die **Technik hinter** dem
Drei-Stufen-Schalter aus Teil 4.5 (AN/Notizbuch/AUS). **Wichtiger
Fund:** Diese gemeinsame, fertig gebaute und getestete Technik ist
bislang von **keiner einzigen** der acht genannten Regeln tatsächlich
genutzt — nur eine Testdatei ruft sie auf. Die Regeln, die heute schon
im Notizbuch-Modus laufen (Trend-Ausstieg, Regime-Wächter), haben dafür
jeweils ihren **eigenen, einfachen Schalter** im eigenen Modul gebaut —
sie waren laut Kopfzeile dieser Datei sogar das *Vorbild* für
`regel_schalter.py`, sind aber technisch (noch) nicht darauf umgestellt.
Deckt sich mit `NAECHSTE-SESSION.md`: „Aufgabe 3, angefangen" ist genau
dieser Anschluss.

**`balance_reporter.py`** — meldet alle 30 Sekunden den echten
Kontostand fürs Log.

### Leichen in diesem Ordner (Runde 11)

`bus.py.bak_sichtbarkeit_20260806`, `logger.py.bak_logrot` —
Sicherungskopien. **Auffälliger Fund:** `balance_reporter(12).py` ist
**kein Backup**, sondern eine zweite, andere Fassung derselben Klasse
`BalanceReporter` — vermutlich beim Herunterladen/Kopieren aus
Versehen doppelt abgelegt (typisches „Datei(1).py"-Muster). Python kann
eine Datei mit Klammern im Namen ohnehin nicht importieren — sie liegt
komplett wirkungslos herum, aber verwirrend beim Suchen.

### Kurzfassung für `core/` als Ganzes

- **Was tut er?** Der Maschinenraum — Poststelle, Zeitplan,
  Überlebens-Gedächtnis, Protokoll, Telemetrie. Trifft selbst keine
  einzige Handelsentscheidung.
- **Warum gibt es ihn?** Jedes andere Modul verlässt sich darauf, dass
  Ereignisse ankommen, Aufgaben pünktlich laufen und nichts beim Absturz
  verloren geht.
- **Greift er in den Handel ein?** Nicht direkt — aber fällt er aus,
  steht der ganze Bot. Am empfindlichsten: `bus.py` und `scheduler.py`.
- **Was bei Löschen?** Der Bot liefe technisch nicht mehr — das ist das
  Fundament, auf dem alle bisherigen neun Runden stehen.

**Nächste Runde:** `ui/` — die Oberfläche(n): Web-Dashboard und das
Cockpit-Fenster aus deinem Screenshot.

## Runde 9 — `ui/` (die Oberflächen)

**Bild zuerst:** Du hast **zwei** Fenster, nicht eins. Ein
**Browser-Dashboard** zum Nur-Ansehen (`localhost:5050`) und das
**Cockpit-Fenster**, das du mir geschickt hast — und das kann, anders
als das Browser-Dashboard, wirklich Käufe und Verkäufe auslösen.

### Die Browser-Seite (nur lesen)

**`dashboard.py`** — Web-Dashboard auf Port 5050: Balance, P&L,
Win-Rate, Strategie, offene Positionen. Reine Anzeige, kein Knopf, der
etwas auslöst.

**`ngrok_dashboard.py`** — würde dieses Dashboard öffentlich im Internet
erreichbar machen (Tunnel). **Standardmäßig aus**
(`config.dashboard.ngrok_enabled = False`, siehe Runde 1), damit niemand
aus Versehen ein offenes Fenster ins Netz stellt.

### Der Webhook — der unauffälligste Kaufweg im ganzen Bot

**`webhook_server.py`** — Port 5051, wartet auf Nachrichten von
TradingView-Alarmen (`{"action": "BUY", "ticker": "...", "price": ...}`).
**Wichtiger Fund:** Trifft eine Nachricht ein, baut diese Datei **einen
echten Kaufwunsch** und schickt ihn ganz normal über die Poststelle
(Runde 1) — läuft also durch Signal→Risiko→Ausführung wie jedes andere
Signal auch, **umgeht nichts**. Aber: es ist ein zweiter, von außen
erreichbarer Eingang für Kauf-Ideen, den man leicht übersieht, weil er
nirgends im Cockpit auftaucht. Aktuell sendet dir vermutlich niemand
TradingView-Alarme — die Tür steht aber offen.
*Greift direkt ins Geld ein, sobald jemand etwas an Port 5051 schickt.*

### Das Cockpit-Fenster — dein Screenshot

**`main_window.py`** (3.221 Zeilen) — startet **standardmäßig** beim
Aufruf `python app.py` (Runde 6), zeigt zehn Reiter: Cockpit, Manuell,
Backtest, BTC, History, Agents, Settings, Log, Charts — plus vier
angedockte Beobachtungs-Reiter (unten).

- **Cockpit-Reiter:** die BTC/ETH/SOL-Kacheln aus deinem Screenshot,
  inklusive **echtem VERKAUFEN-Knopf** je Coin und den SL/HOLD/TP-Modus-
  Schaltern (Runde 1, `_coin_modes`).
- **Manuell-Reiter:** eigener Kauf-/Verkaufs-Knopf mit freiem Betrag.
  **Wichtiger Fund:** Ein manueller Kauf hier geht **direkt** an
  `execution.execute()` — er durchläuft **keine einzige** der acht
  Prüfungen aus Runde 2 (Exposure, Drawdown, Kill-Switch,
  Max-Positionen, Cooldown, NUPL-Euphorie-Bremse …). Einzige Bremse:
  Mindestbetrag 5 $. Das ist vermutlich gewollt — ein bewusster
  Handgriff soll nicht vom Automatik-Regelwerk blockiert werden — aber
  es bedeutet auch: ein Klick hier würde selbst bei aktivem Kill-Switch
  durchgehen. Wert, das einmal bewusst zu entscheiden statt es einfach
  so zu lassen.
- **Backtest, BTC, History, Agents, Settings, Log, Charts:** genau das,
  wonach sie klingen — Rückschau, Sparplan-Übersicht, Handelsverlauf,
  Agenten-Status, Einstellungen (u. a. der Risk-Block oben in deinem
  Screenshot), Protokoll, Kerzencharts.
- **Akademie, Strategie-Labor, Stop-Loss-Kantenanalyse:** öffnen sich
  als eigene Pop-up-Fenster über Knöpfe, nicht automatisch — reine
  Analyse auf echten Kursdaten, kein Trading-Eingriff (aus Runde 6).

### Die vier angedockten Beobachtungs-Reiter

**`terminal_tab.py`, `zyklus_tab.py`, `geldfluss_tab.py`,
`chartanalyse_tab.py`** — plus `metals_tab.py` aus einem anderen Ordner.
Alle vier/fünf tragen **wortgleich** denselben Warnhinweis im Dateikopf:
„REINE ANZEIGE — kein Einfluss auf den Handel, wird von keinem
Handelspfad importiert." Terminal zeigt den Konsolen-Blick mit
Epochen-Kennzahlen, Zyklus den 8-Jahres-BTC-Atlas, Geldfluss die
Markt-Rotation zwischen Aktien/Gold/Krypto, Chartanalyse die Muster aus
Runde 6. Diese bewusste Trennung — Anzeige ja, Handelseinfluss nein —
ist ausdrücklich gewollt und wurde bereits als Regel festgehalten:
Änderungen am Handelspfad hier nur nach ausdrücklicher Freigabe.

### Leichen in diesem Ordner (Runde 11)

**`main_window_backup_20260610.py`** (2.640 Zeilen) — eine komplette,
ältere Fassung von `main_window.py`, nicht importiert.
`main_window.py.bak_*` (3×), `terminal_tab.py.bak_*` (6×) —
Sicherungskopien.

### Kurzfassung für `ui/` als Ganzes

- **Was tut er?** Zwei Fenster: ein reines Ansichtsfenster im Browser,
  und ein Cockpit-Fenster, das sowohl anzeigt als auch selbst handeln
  kann.
- **Warum gibt es ihn?** Damit du siehst, was der Bot tut — und bei
  Bedarf von Hand eingreifen kannst.
- **Greift er in den Handel ein?** Ja, an drei Stellen: der
  VERKAUFEN-Knopf im Cockpit, der Manuell-Reiter (ohne
  Risiko-Prüfungen!), und der TradingView-Webhook. Die restlichen neun
  Zehntel des Ordners sind reine Anzeige.
- **Was bei Löschen?** Der Bot handelt automatisch unverändert weiter —
  du würdest nur nichts mehr davon sehen und nicht mehr von Hand
  eingreifen können.

**Nächste Runde:** `backtest/` + `portfolio/` — Auswertung und
Kontoführung.

## Runde 10 — `backtest/` + `portfolio/` (Auswertung und Kontoführung)

**Bild zuerst:** Zwei völlig verschiedene Ordner unter einem Dach.
`backtest/` ist der **Prüfstand** — ein Werkzeugkasten für Handanalyse
auf alten Kursdaten, größtenteils per Befehl von dir gestartet, nicht
automatisch. `portfolio/` ist die **Kontoführung** — läuft ständig mit
und rechnet bei jedem Kauf mit.

### `backtest/` — der Prüfstand (per Befehl, nicht automatisch)

**`engine.py`** (`BacktestEngine`) — das Fundament: simuliert Handel auf
historischen Kursen mit echten Gebühren und Slippage, rechnet Sharpe,
Drawdown, Win-Rate, Profit-Faktor. Nutzt `fees.py` (Gebühren-Modell) und
`slippage.py` (Preisverschlechterungs-Modell) als Bausteine.

**`optimizer.py`** (`BacktestOptimizer`) — sucht per **Grid-Search**
(alle Kombinationen durchprobieren) die beste Stop-Loss/Trailing/
Positionsgröße-Kombination. **Wichtig:** Das ist genau der Baustein
hinter dem entfernten Auto-Optimizer-Knopf aus Teil 4.6 — der Code lebt
noch (`app.py:_auto_optimize`), ist aber über `self.auto_optimize_enabled
= False` hart stillgelegt. Bleibt ausgeschaltet, weil er sonst „den
Regenschirm wählt, der zuletzt am wenigsten gestört hat" (Teil 4.6).

**`hyperopt.py`** (`HyperOptimizer`) — verfeinerte Parametersuche über
eine Bibliothek namens Optuna (falls installiert). Nur `get_status()`
wird aus `app.py` gelesen — **gebaut, aber nicht im Einsatz**.

**`walk_forward.py`** — testet, ob eine Regel auch auf Daten funktioniert,
die sie beim Training nicht gesehen hat (Schutz gegen Selbstbetrug/
Overfitting). **`monte_carlo.py`** — mischt die Reihenfolge echter
Trades tausendfach durch und zeigt: wie schlecht könnte es im
Extremfall laufen? Beide sind Bausteine von `engine.py`, kein
eigenständiger Aufruf aus `app.py`.

**Direkt per Befehl aufrufbare Werkzeuge** (für dich von Hand, nicht
Teil des laufenden Bots):

| Befehl | Was er tut |
|---|---|
| `python backtest/daten_holen.py` | Lädt einmalig historische 15-Minuten-Kerzen + Fear-&-Greed-Historie herunter, für Backtests offline nutzbar |
| `python backtest/ausstieg_vergleich.py` | Vergleicht alte gegen neue Ausstiegs-Leiter (Runde 2) |
| `python backtest/ausstieg_vergleich.py --suche` | Dasselbe, plus Parametersuche mit Walk-Forward-Absicherung gegen Selbstbetrug |
| `python backtest/strategie_studie.py` | Prüft, welche Strategie-Eigenschaft wirklich den Unterschied macht (nicht nur die Ausstiegs-Leiter) |
| `python backtest/ausstieg_backtest.py` | Rohe Backtest-Engine für die Ausstiegsregeln, Baustein der beiden Werkzeuge oben |

**`metrics.py`** — reine Rechenformeln (Sharpe, Profit-Faktor …), von
den Werkzeugen oben mitbenutzt, kein eigener Befehl.

### `portfolio/` — die Kontoführung (läuft ständig mit)

**`manager.py`** (`PortfolioManager`, 558 Zeilen) — die **zentrale
Kapitalverwaltung** aus Runde 1: alles prozentual statt in festen
Dollar-Beträgen, damit derselbe Bot mit 300 $ oder 100.000 $
funktioniert. Liefert `get_total_capital()`, `get_position_size()`,
`get_free_cash()` — wird von Signal-Agent, Risk-Engine, Portfolio-Agent
und Execution-Engine gleichermaßen genutzt statt eigener Rechnung.
*Greift direkt ein — praktisch jeder Kauf hängt an dieser Datei.*

**`agent.py`** (`PortfolioAgent`) — der **Klumpenrisiko-Wächter aus
Runde 1** (`_execute_approved_trade`): prüft vor jedem Kauf zusätzlich
Korrelation und Sektor-Verteilung, über `correlation_guard.py`.

**`correlation_guard.py`** — blockt zu viele gleichzeitig ähnliche
Positionen (z. B. drei L1-Coins, die sich fast immer gleich bewegen).

**`calculator.py`** (`PortfolioSnapshot`) — **Korrektur (Runde 12):**
hier fälschlich als aktive Rechenbausteine beschrieben. Tatsächlich
**komplett verwaist** — keine einzige Fundstelle im Projekt außer der
Datei selbst. Bestätigt durch die Architektur-Datenbank des
Forschungsprogramms (`docs/forschungsprogramm_2026-07`, Tabelle
`bot_architektur`).

**`daily_loss.py`** — die **„eine Wahrheit"** für den Tagesverlust-Wächter,
ersetzt zwei ältere, ausgemusterte Fassungen (`risk/daily_loss_guard.py.UNUSED`,
`daily_loss_guardian.py.UNUSED`). **Geprüft, Stand jetzt:** Modus
`aktiv`, Grenze `6,0 %` (`data_store/config.json`) — das ist **kein**
Notizbuch-Eintrag, sondern läuft scharf: bei 6 % realisiertem
Tagesverlust pausiert der Bot neue **Käufe**. Wichtig, was er
ausdrücklich **nicht** tut: keine Position wird deshalb verkauft, jede
offene Position behält ihren eigenen Stop-Loss.
*Greift direkt ein — deine schärfste Tagesbremse neben dem Kill-Switch
aus Runde 2.*

**`rebalancer.py`** — schon aus Runde 1 bekannt: baut die Gewichtung im
Depot Richtung Zielverteilung zurück, aktuell **abgeschaltet und im
Trockenlauf** (`enabled=False, dry_run=True`).

### Leichen in diesem Ordner (Runde 11)

`manager.py.bak_p5` — Sicherungskopie. `daily_loss_guardian.py.UNUSED`
— ausgemusterter Vorläufer von `daily_loss.py`, ausdrücklich markiert.

### Kurzfassung für `backtest/` + `portfolio/` als Ganzes

- **Was tun sie?** `backtest/` prüft auf alten Daten nach, was
  funktioniert hätte — auf Zuruf, nicht automatisch. `portfolio/` führt
  laufend Buch über dein Kapital und bremst bei Klumpenrisiko oder zu
  hohem Tagesverlust.
- **Warum gibt es sie?** Damit Entscheidungen auf Zahlen beruhen
  (`backtest/`) und damit derselbe Code bei jeder Kontogröße richtig
  rechnet (`portfolio/`).
- **Greifen sie in den Handel ein?** `backtest/` nicht — reine
  Werkzeuge für dich. `portfolio/` ja, ständig und direkt: Kapitalgröße,
  Klumpenrisiko-Bremse, Tagesverlust-Pause.
- **Was bei Löschen?** `backtest/` weg: du verlierst die Werkzeuge,
  der Bot handelt unverändert weiter. `portfolio/manager.py` weg: der
  Bot weiß nicht mehr, wie viel Geld er hat — Totalausfall der
  Kapitalrechnung.

**Nächste Runde:** Runde 11, der große Rest — alle Skripte im
Hauptordner, plus das Aufräumen der bisher gesammelten Leichen.

## Runde 11 — Der Rest (Hauptordner + vier übersehene Ordner)

**Bild zuerst:** Der **Dachboden** — hier liegt alles, was nicht in
einen der zehn bisherigen Räume passte. Zwei Sorten: vier echte,
laufende Ordner, die im ursprünglichen Plan übersehen wurden — und rund
150 Einzeldateien im Hauptordner, die meisten davon Werkzeuge, die du
von Hand aufrufst, nicht der Bot automatisch.

### Vier übersehene, aber aktive Ordner

**`config/`** — **`settings.py`** ist die zentrale Konfiguration
(`AppConfig`), aus der `app.py` beim Start alles liest — auch, ob Live-
oder Papiermodus läuft. Lädt API-Schlüssel ausschließlich aus `.env`,
nie aus dem Code selbst. **`versioning.py`** (`ConfigVersioning`) hält
frühere Config-Stände fest, damit eine Änderung rückverfolgbar bleibt.
*Zentral — ohne `settings.py` kein einziger Startparameter.*

**`live/`** — die **Schaltstelle zwischen Papier und Echtgeld**:
`live_runner.py` (echte Börsen-Verbindung) und `paper_runner.py`
(Simulation) sind austauschbare Zwillinge mit gleicher Schnittstelle —
`app.py` merkt kaum einen Unterschied, welcher gerade läuft. Dazu
`watchdog.py` (**startet tote Threads NICHT neu** — `check()` hat keinen
Aufrufer, siehe Befund 122; nur `get_status()` wird benutzt),
`state_recovery.py` (gleicht
nach einem Neustart den lokalen Stand mit der echten Börse ab — nur im
Live-Modus relevant) und `shadow_mode.py`: verfolgt seit dem
Lern-Fix (Runde 3) laufend den Gewinn der aktiven Strategie mit
(`record_active_pnl`); die drei eingebauten Vergleichs-Strategien
(„Konservativ" u. a.) sind vorbereitet, aber ohne eigene Kursdaten nur
begrenzt aussagekräftig.

**`reports/`** — **`telegram.py`** ist der aktive Telegram-Kanal
(Trade-Alerts, Tages-/Wochenbericht) aus mehreren bisherigen Runden.
**`equity_tracker.py`** zeichnet den Vermögensverlauf auf (Runde 8,
`state_manager.auto_save`). **Fund:** `trade_journal.py`,
`daily_report.py` und `weekly_report.py` sind **komplett verwaist** — es
gibt bereits ein aktives `TradeJournal` in `core/state_store.py` (Runde
8) unter demselben Klassennamen, und die echten Tages-/Wochenberichte
laufen über `TelegramReporter`s eigene Methoden (`runtime/reporting.py`,
Runde 3). Drei weitere Dateien, die wie aktiver Code aussehen und keiner
sind.

**`metals/`** — ein **komplett eigenständiges Zusatz-Feature**: die
METALLE-Kachel aus deinem Cockpit-Screenshot. `metals_engine.py`
bewertet Gold und Silber über sechs Indikatoren (Trend, RSI, MACD,
Bollinger, Gold-Silber-Ratio, Support/Resistance) zu einem Signal.
`metals_store.py` speichert Stand und Scan-Log in einem **eigenen**
Ordner (`metals_data/`), komplett getrennt von `data_store/`.
Selbst dokumentiert: „Reine Datenlogik. Fasst den Bot NICHT an, handelt
NICHT." *Kein Einfluss auf dein Krypto-Geld — eigene, isolierte Welt.*

### Betriebs-Skripte (das Tagesgeschäft)

| Befehl | Was er tut |
|---|---|
| `start_bot.bat` | Startet den Bot (`python app.py`) |
| `datenbank_ansehen.bat` | Doppelklick-Verknüpfung zu `telemetrie_frage.py status` |
| `python telemetrie_frage.py <status\|gruende\|kaeufe\|verkaeufe\|markt\|verlauf>` | Fragt die Telemetrie-Datenbank ab (Anhang, schon bekannt) |
| `job_forschung_capture.py`, `job_sammler.py` | Starter für die beiden Hintergrundjobs aus Runde 8 (`core/hintergrund.py`) — laufen über die Windows-Aufgabenplanung, nicht von Hand |
| `python sammler.py` | Sammelt Daten für Metalle/Geldfluss/Zyklus (wird von `job_sammler.py` aufgerufen) |
| `python config_update.py` | Migriert eine ältere `config.json` auf das aktuelle Format |

### Diagnose- und Check-Skripte (read-only, ändern nichts)

**Wichtigster Fund:** `go_live_check.py` ist **kein reines
Diagnose-Werkzeug** — es ist „Sicherung 1" aus Runde 4
(`execution/engine.py:_gate_bestanden`): der Bot ruft es beim Start
selbst als Unterprogramm auf, bevor er in den Live-Modus wechseln darf.
Lehnt es ab, bleibt der Bot im Papiermodus.

| Befehl | Was er prüft |
|---|---|
| `python go_live_check.py` | Ob die Statistik einen Live-Start überhaupt trägt (vom Bot selbst genutzt, s. o.) |
| `python voll_diagnose.py` / `python diagnose.py` | Kompletter bzw. schneller Selbsttest aller Komponenten |
| `python preflight.py` | Startvoraussetzungen prüfen |
| `python check_install.py` | Sind alle nötigen Pakete installiert? |
| `python analyse_readiness.py` | „Reifeprüfung" — reicht die Datenlage für belastbare Aussagen? |
| `python status.py` | Kurzer Systemstatus |
| `python inventar_agent.py` | Listet, welche Module/Agenten aktiv sind |
| `python telegram_test.py` | Prüft Telegram-Token und Chat-ID direkt gegen die API |
| `python cockpit_server.py` | Eigenständiges, lokales Analyse-Cockpit (read-only) |

### Auswertungs- und Forschungs-Skripte (die Belege hinter diesem Handbuch)

Genau diese Skripte haben die meisten Zahlen geliefert, die in Teil 3
und Teil 4 dieses Handbuchs stehen:

| Skript | Wofür |
|---|---|
| `e4_eval.py`, `e5_walkforward.py`, `e7_auswertung.py`, `e7_gegenprobe.py` | Epochen-Auswertungen (E4 = Stop-Loss-Test, E7 = Trailing-Test) |
| `epoch_report.py`, `epochs.py` | P&L getrennt nach Config-Epoche, Epochen-Definition |
| `gesamtauswertung.py`, `impact_report.py` | Gesamtbild über alle gemessenen Daten |
| `pnl_check.py`, `stoploss_analyse.py` | Wo genau entsteht ein Verlust, was würde helfen |
| `regime_filter_messung.py` | Ob der Bärenmarkt-Filter sein Geld wert ist |
| `journal_abgleich.py`, `backfill_impact_journal.py` | Gleicht Journal und Bestand ab, schließt Lücken |
| `macro_replay.py`, `phase_prior_check.py`, `history_harvester.py`, `situation_replay.py` | Zyklus-/Makro-Forschung (Teil des Forschungsprogramms, nicht des Live-Bots) |
| `chartanalyse_backtest.py` | Genau das Konsolen-Bild aus deinem Screenshot |
| `datenexport.py` | Exportiert alle gemessenen Daten in eine Excel-Mappe |

### Install- und Fix-Skripte — bereits erledigt, historisches Protokoll

Zwölf `install_*.py` und drei `fix_terminal_*.py` haben genau je **eine**
Funktion nachträglich in den Code gepatcht (Chart-Refresher, Daily-Loss
P5, E7-Trailing, E8-Nachkauf-Stop, Geldfluss-/Zyklus-/Terminal-Tab,
Metalle Stufe 2/3, MFE/MAE-Logging, P4-Diagnose/Frische, Tagesbericht
v2). **Nicht erneut ausführen** — die Änderung steckt bereits im Code,
ein zweiter Lauf würde bestenfalls nichts tun, schlimmstenfalls doppelt
patchen. Sie bleiben als Protokoll liegen, welche Änderung wann kam.

### Test-Skripte — bestätigen die Fixes vom 11.08.

`test_hintergrund.py`, `test_lern_journal_v6.py`, `test_markt_historie.py`,
`test_regel_schalter.py`, `test_schatten_sizing.py` — je ein Test für die
fünf Aufgaben der letzten Sitzung, schon in den Runden 3 und 8 erwähnt.
`python test_regel_schalter.py` ist genau der Beleg, dass
`core/regel_schalter.py` funktioniert — nur eben an nichts
angeschlossen (Fund #11).

### Sonstige Werkzeuge

`bot_navigator.py`, `brain_view.py` — Übersichts-/Navigationshilfen.
`cleanup.py`, `cleanup_daily_loss.py` — Aufräum-Skripte für alte
Zustände. `metals_check.py`, `metals_signals.py`,
`update_metals_indikatoren.py` — Kommandozeilen-Werkzeuge für das
Metalle-Feature.

### Handbücher, Doku, Konfig-Dateien

33 Markdown-Dateien: die wichtigsten sind bereits im Anhang gelistet
(`ENTWICKLERHANDBUCH.md`, `TESTLISTE.md`, `tickets.txt`). Der Rest sind
Bau- und Übergabe-Dokumente aus früheren Bauabschnitten
(`SPLIT_BAUPLAN.md`, `DAILY_LOSS_BAUPLAN_P5.md`,
`SIZING_BAUPLAN_E8(1).md`, `UEBERGABE-*.md` u. a.) — historische
Momentaufnahmen, nicht laufend gepflegt, aber als „warum wurde das damals
so entschieden" wertvoll. `config.example.json` /
`.env.example` zeigen die erwartete Struktur ohne echte Werte;
`config_epochs.json`, `config_regime_filter.json`, `config_v4_sync.json`
sind Arbeitsdateien einzelner Auswertungsskripte oben.

### Leichen in diesem Ordner (jetzt zum Aufräumen vorgemerkt)

Die mit Abstand meisten Leichen im ganzen Projekt liegen hier:

| Gruppe | Anzahl | Beispiel |
|---|---|---|
| `tickets.txt.bak_*` | 23 | Sicherungskopien des Tickets-Verlaufs |
| `app.py.bak_*` | 4 | Sicherungskopien des Hauptprogramms |
| `ENTWICKLERHANDBUCH.md.bak*` / `.nullbyte_*` / `_KORRUPT_*` | 6 | Sicherungen, eine davon nach einem Absturz beschädigt |
| `auto_export_*.txt` | 9 | Alte Analyse-Exporte |
| `_*_payload*.py` (terminal, daily_loss, chart_refresher, geldfluss, zyklus) | 7 | Rohfassungen, die die `install_*.py`-Skripte oben in die echten Module (`ui/`, `runtime/`) eingebaut haben — die echten Dateien leben jetzt dort |
| `install_e8_nachkauf_stop(1).py` | 1 | Doppel-Download desselben Install-Skripts |
| diverse `.txt`-Reste | mehrere | `out.txt`, `out2.txt`, `files.txt`, `check_a.txt`, `dateien_finden.txt` — Wegwerf-Ausgaben früherer Kommandos |

### Kurzfassung für Runde 11 als Ganzes

- **Was tut er?** Vier aktive Zusatz-Ordner (Konfiguration, Live/Papier-
  Umschaltung, Berichte, das eigenständige Metalle-Feature) plus rund
  150 Einzeldateien — größtenteils Werkzeuge für dich, dazu die
  Belege hinter den Zahlen in diesem Handbuch.
- **Warum gibt es ihn?** Sieben Monate Entwicklung hinterlassen Spuren —
  jedes Skript hat einmal ein echtes Problem gelöst oder eine echte
  Frage beantwortet.
- **Greift er in den Handel ein?** `config/settings.py` und `live/`
  zentral (jeder Start hängt daran). `go_live_check.py` ist die
  Torwache vor jedem Live-Wechsel. Alles andere hier: nein, reine
  Werkzeuge, Belege oder Altlasten.
- **Was bei Löschen?** Die vier Ordner: nicht löschen, echte
  Abhängigkeiten. Die Leichen-Tabelle oben: gefahrlos, Python lädt
  keine dieser Dateien.

---

## Runde 12 — `docs/forschungsprogramm_2026-07` (das Forschungsprogramm)

**Bild zuerst:** Ein **zweites Labor** neben dem Bot — komplett getrennt,
mit eigener Datenbank, eigenen Regeln, eigenem strengen Prüfverfahren.
Getestet werden hier **neue** Strategie-Ideen, bevor sie überhaupt zur
Debatte stehen, dürften in den Bot zu wandern. 1.643 Dateien insgesamt,
aber **91 % davon sind Messdaten** (821 CSV + 671 komprimierte Archive)
— keine Dateien zum Erklären, sondern Ergebnisse. Übrig bleiben rund
90 Code- und Doku-Dateien, die wirklich etwas erzählen.

### Die eigene Datenbank

`forschung.db` — **komplett getrennt von `data_store/telemetrie.db`**
(Teil 2.1): eigener Ordner, eigenes Schema, „liest nichts aus
`data_store/`, schreibt nichts dorthin, der laufende Bot wird nicht
angebunden" (so wörtlich in ihrer eigenen Dokumentation). Sieben
Tabellen: `trials` (79 getestete Konfigurationen), `bot_architektur`
(231 Module — dazu gleich mehr), `datenquellen` (28, live nachgemessen),
`befunde` (11, mit Konfidenz und Priorität), `kostenszenarien`,
`register_versionen`, `programm_status`.

**Wie du selbst reinschaust:**

```bash
cd docs/forschungsprogramm_2026-07/code
python db_frage.py status      Programmstatus und Gate-Ergebnisse
python db_frage.py befunde     alle Befunde nach Priorität
python db_frage.py bugs        Module mit dokumentierten Bugs
python db_frage.py tot         alle toten Module, nach Zeilen sortiert
python db_frage.py trial T-024 ein einzelner Test mit allen Details
python db_frage.py sql "SELECT …"   freie Leseabfrage
```

**Wichtig — der Stand ist eingefroren, 30.07.2026.** Das ist zwölf Tage
alt. Ein Stichprobentest hat gezeigt: ein als „KRITISCH" markierter Bug
(unprotokollierte Kauf-Ablehnungen in der Risiko-Prüfung) ist im
heutigen Code **längst behoben** — genau die Sichtbarkeits-Reparatur vom
06.08., die schon an mehreren Stellen in diesem Handbuch steht. Jeder
Befund von dort wurde deshalb einzeln gegen den heutigen Code geprüft,
nicht blind übernommen.

### Die Architektur-Datenbank hat mich kontrolliert — und einen Fehler gefunden

Ein automatischer Code-Scan (kein Raten: Python liest jeden Import
selbst aus) zählt für den Stand 30.07.: **117 Module aktiv, 100 tot,
13 ungeprüft, 1 abgeschaltet — 43 % von allem, was im Projekt liegt,
wird von nichts geladen.** Ich habe das gegen meine eigenen Runden 1–11
abgeglichen. Das meiste deckt sich exakt — `execution/exchange_client.py`,
`reports/trade_journal.py`, alle `_*_payload.py`-Dateien hatte ich
unabhängig genauso gefunden. **Aber:** `portfolio/calculator.py` hatte
ich in Runde 10 fälschlich als aktiv beschrieben. Ist tot — korrigiert.

**Eine Einschränkung der Methode, zum eigenen Schutz:** Der Scan zählt
nur Python-**Importe**. `go_live_check.py` steht deshalb dort als „tot"
— ist es aber nicht: `execution/engine.py` ruft es als **Unterprogramm**
auf (Runde 11), nicht als Import. Ein automatischer Scan ist ein
gutes Werkzeug, kein Ersatz fürs Nachdenken.

### Das Forschungs-Urteil bisher: zweimal Nein

Getestet wurden vier/fünf **neue** Strategie-Ideen als Kandidaten für
später — nicht die Strategien, die dein Bot heute live fährt:

| Idee | Kurzform | Ergebnis |
|---|---|---|
| Trendfolge (Faber, Momentum, Donchian) | „kaufe im Aufwärtstrend" | REJECTED — Vorteil war 2022/23 verschwunden, danach nur noch Marktrisiko |
| Funding-Rate-Extreme | „kaufe bei extrem negativer Finanzierungsrate" | REJECTED — schlägt den Zufall nicht |
| Volatilitäts-Kontraktion (Crabel NR7) | „enge Handelsspanne vor Ausbruch" | REJECTED — schlägt nicht mal den Zufall |
| Makro-Overlay (Dollar-Index) | „Dollar-Stärke als Bremse" | REJECTED — Konfidenzintervall enthält Null |

**Gate 1 und Gate 2: beide NEGATIV** (Regel des Programms: zwei negative
Gates beenden diese Runde des Programms — „mit unseren Mitteln nicht
erreichbar", kein Fehlschlag, ein zulässiges Ergebnis). Bedeutet **nicht**
„dein Bot funktioniert nicht" — bedeutet: vier geprüfte neue Ideen haben
unter strengen, vorregistrierten Kriterien keinen echten Vorteil gezeigt
und werden **nicht** eingebaut. Genau das soll ein Forschungsprogramm
leisten: schlechte Ideen aussortieren, bevor sie echtes Geld kosten.

**Bemerkenswerteste Einzel-Lektion:** In zwei unabhängigen Testrunden war
ausgerechnet die Strategie mit dem stärksten Signal die, deren Ergebnis
komplett aus **Survivorship** stammte (heute überlebende Coins wie AVAX,
NEAR, SOL, die 2023 nicht mehr gelistet worden wären, wenn sie
gescheitert wären). Ein Signal, das zu gut aussieht, sollte zuerst
danach durchsucht werden, *warum* es zu gut aussieht.

### Zwei neue, noch offene Funde aus dem Abgleich

**`data/market_data.py:54`** fällt bei fehlendem USDC-Paar auf USDT
zurück — unter der Zielbörse Bybit EU (MiCA, Teil 4.11) gibt es dort
**keine** USDT-Paare. Aktuell folgenlos, weil Kurse noch von Binance
kommen; eine stille Falle für den Tag, an dem sich das ändert. Details:
[GEFUNDENE-PROBLEME.md](GEFUNDENE-PROBLEME.md), Punkt 22.

**`execution/engine.py:274`** nimmt für jede Münze dieselbe zufällige
Slippage — gemessen reicht der reale Spread aber von 0,05 bis 65 Basis-
punkten, Faktor 1.210 zwischen den Münzen. Verzerrt die Papier-Ergebnisse
münzabhängig, ähnlich wie die schon behobene Gebühren-Baustelle aus Teil
4.11. Details: [GEFUNDENE-PROBLEME.md](GEFUNDENE-PROBLEME.md), Punkt 23.

### Kurzfassung für Runde 12 als Ganzes

- **Was tut es?** Ein unabhängiges Prüflabor für neue Strategie-Ideen,
  mit eigener, vorregistrierter Methodik gegen Selbstbetrug
  (Survivorship, Placebo-Tests, Blick-in-die-Zukunft-Fehler).
- **Warum gibt es das?** Damit keine Idee in den Bot wandert, nur weil
  sie in einem Backtest gut aussah — genau die Falle, die die
  Survivorship-Lektion oben zeigt.
- **Greift es in den Handel ein?** Nein, ausdrücklich nicht — bewusst
  vom laufenden Bot abgekoppelt.
- **Was bei Löschen?** Der Bot handelt unverändert weiter. Verloren ginge
  die Beleglage hinter vielen „warum haben wir das nicht eingebaut"-
  Entscheidungen — und die einzige unabhängige Gegenkontrolle für die
  eigene Architektur-Einschätzung dieses Handbuchs.

**Nächste Runde:** `docs/messungen_2026-07` — das ältere Mess-Audit
(E1/E2/E5), dann die restlichen kleinen Ordner (`scripts/`, `tests/`,
`v4_referenz/`, Archive).

## Runde 13 — `docs/messungen_2026-07` (das Mess-Audit vor der Live-Freigabe)

**Bild zuerst:** Die **Vorstufe** zum Forschungsprogramm aus Runde 12 —
15 einzelne Messläufe (E1/E2/E5, F1–F3, G1/G2), 29./30.07.2026, jeder mit
Rohausgabe und Kontrollanker (ein fester Testfall, der beweist: die
Messtechnik selbst rechnet noch richtig). Getestet wurde hier nicht eine
neue Idee, sondern das **damalige** Ein-/Ausstiegssystem des laufenden
Bots selbst.

**Die zwei schwersten Befunde — Grundlage für spätere Reparaturen:**

1. **„Kein Stop rettet das System."** Sieben Stop-Varianten über zwei
   Jahre getestet: das erzielte Chance/Risiko-Verhältnis erreicht nie den
   Break-even-Wert (bester Fall 0,50 gegen nötige 0,96). Das ist
   **derselbe Befund**, mit dem `risk/exit_rules.py` (Runde 2) seine
   neue Ausstiegs-Leiter begründet — die dortige Reparatur ist die
   direkte Antwort hierauf.
2. **„Kein Richtungsvorteil im Einstieg."** Symmetrischer Test: der
   Einstiegszeitpunkt trifft nicht besser als ein zufälliger Zeitpunkt am
   selben Tag. Er wählt Schwankungsbreite, keine Richtung. Wörtliches
   Urteil im Audit: die Annahme „der Einstieg funktioniert, das Leck ist
   nur Nachkauf und Ausstieg" ist **widerlegt** — Nachkauf und Ausstieg
   verstärken ein System ohne eigenes Vorzeichen, sie verursachen den
   Verlust nicht.

**Bereits durch spätere Fixes überholt (Stichprobe, nicht erneut
gemessen):** Befund „`config.json` listet 11 statt 12 Coins,
`coins[:12]` wirkungslos" — heute Stand: **3 Coins** (BTC/ETH/SOL),
seit der Messung deutlich verkleinert. Der Befund ist damit gegenstandslos,
nicht falsch.

**Bereits bekannt aus eigenen Runden, hier bestätigt:** „Der Bot kennt
nur Market-Orders" (Runde 4/10) — Belegzahl hier: 12 echte Order-Aufrufe
im ganzen Projekt, ausnahmslos `create_market_*`.

**Offen und ehrlich als Lücke benannt** (im Audit selbst, nicht von mir
ergänzt): die echten Binance-Kontokonditionen (VIP-Stufe, BNB-Rabatt)
stehen nirgends im Projekt — die Kostenrechnung vergleicht „Code gegen
Code, nicht Code gegen Wirklichkeit". Und: die Ist-Slippage einzelner
Trades wird zwar berechnet (`ExecutionResult.slippage_pct`), aber **nicht
ins Journal geschrieben** — die tatsächliche Reibung des Live-Betriebs
bleibt deshalb unbekannt, obwohl das Feld dafür existiert.

### Ein neuer, kleiner Fund

**`ExecutionResult.slippage_pct` wird berechnet, aber nie gespeichert.**
Passt zu Punkt 23 aus Runde 12 (Slippage-Annahme ignoriert
Münz-Unterschiede) — hier zusätzlich: selbst die berechnete Ist-Slippage
pro Trade geht verloren, statt ins Journal zu wandern. Ohne dieses Feld
lässt sich nie nachträglich prüfen, ob die Annahme aus Runde 12 stimmt.

### Kurzfassung für Runde 13

- **Was tut es?** Das ursprüngliche, sehr gründliche Mess-Audit, das die
  Schwächen des damaligen Ein-/Ausstiegssystems zuerst sichtbar gemacht
  hat.
- **Greift es in den Handel ein?** Nein — reine Vorstufen-Forschung,
  längst durch Runde 12 abgelöst und ergänzt.
- **Was bei Löschen?** Nichts am heutigen Handel — nur die Beweiskette
  hinter der Ausstiegs-Leiter-Reparatur (Runde 2) ginge verloren.

**Nächste Runde:** die letzten kleinen Ordner — `scripts/`, `tests/`,
`v4_referenz/`, Archive.

## Runde 14 — Die letzten kleinen Ordner (`scripts/`, `tests/`, `v4_referenz/`, Archive)

**Bild zuerst:** Der letzte Rest — fünf kleine Ordner, keiner davon vom
laufenden Bot geladen. Damit ist wirklich **jeder** Ordner im Projekt
einmal angeschaut.

### `scripts/` — Reset- und Migrations-Werkzeuge

| Befehl | Was er tut |
|---|---|
| `python scripts/full_reset_final_v3.py` | Setzt den Bot komplett auf null (Cash, Positionen, Impact-Journal, Reset-Marker) — die aktuellste von drei Fassungen |
| `python scripts/reset_paper.py` | Leichter Reset: nur Cash + Positionen, die gelernten Gedächtnisse (Teil 1) bleiben erhalten |
| `python scripts/migrate_v4_to_v6.py` | Einmalige V4→V6-Datenübernahme, längst erledigt |

`full_reset.py` und `full_reset_final_v2.py` sind die zwei Vorgänger-
Fassungen von v3 — funktionieren vermutlich noch, aber v3 ist die
vollständigste. Keiner der drei greift automatisch ein, alle drei
brauchst du nur auf Zuruf.

### `tests/` — die Test-Sammlung

`python tests/run_all.py` führt `test_backtest.py`, `test_data.py`,
`test_execution.py`, `test_portfolio.py`, `test_risk.py` und
`test_v6_modules.py` nacheinander aus. Ändert nichts, prüft nur, ob die
Kernmodule noch das tun, was sie sollen — unabhängig von den fünf
`test_*.py`-Dateien im Hauptordner aus Runde 11, die die Fixes vom
11.08. prüfen.

### `v4_referenz/` — der Vorgänger-Bot

Der komplette alte V4-Bot als Datenablage: Handbücher, Analyse-Exporte,
Equity-Verlauf — **kein aktiver Code**, der vom laufenden V6 geladen
wird. Dient ausschließlich als **Messquelle**, nie als Lernquelle (Teil
4, V4-Entscheidung) — die 756 V4-Verkäufe darin sind ein Vergleichsmaßstab,
kein Einfluss auf V6-Entscheidungen.

### `_archive_20260716_065427/` und `uebergabe-dust/` — Altlasten

Ein kompletter, durchnummerierter Schnappschuss alter `.bak`-Dateien und
längst erledigter `fix_*.py`/`install_*.py`-Skripte vom 16.07. — die
Vorgänger-Generation der Runde-11-Skripte, schon damals archiviert, nicht
mehr aktiv.

**Auffälligster Einzelfund:** `uebergabe-dust/dust_manager.py` —
950 Zeilen, ein vollständiges Werkzeug zur Verwaltung von
„Staubpositionen" (Restbeträge zu klein zum sinnvollen Verkaufen). Nie
angeschlossen, keine Fundstelle im ganzen Projekt außer sich selbst.
Möglicherweise für eine geplante, nie umgesetzte Funktion gebaut.

### Kurzfassung für Runde 14

- **Was tut es?** Werkzeuge auf Zuruf (Reset, Migration, Tests) plus
  reine Altlasten (V4-Referenz, zwei Archive).
- **Greift es in den Handel ein?** Nein, keine einzige Datei hier.
- **Was bei Löschen?** Reset-/Test-Skripte würden fehlen, wenn du sie
  brauchst — sonst nichts am laufenden Betrieb.

## Runde 15 — Die 17 Installer- und Fix-Skripte, einzeln

**Warum diese Runde nachgeschoben wurde:** In Runde 11 standen diese
Skripte nur als Gruppe in einer Tabelle („bereits erledigt, nicht erneut
ausführen"). Das war zu grob. Jedes einzelne ist ein **Zeitzeuge**: es
sagt, was wann warum am Bot geändert wurde — und ob die Änderung
tatsächlich angekommen ist.

**Wie ich geprüft habe:** nicht dem Docstring geglaubt, sondern für
jeden Installer im heutigen Code nach seiner Spur gesucht.

### Die 15, die angekommen sind

| Skript | Was es einbaute | Heute im Code |
|---|---|---|
| `install_chart_refresher.py` | Kerzen-Cache alle 60 Min automatisch frisch halten | ✅ `features/chart_refresher.py` |
| `install_daily_loss_p5.py` | Tagesverlust-Wächter, „eine Wahrheit" | ✅ `portfolio/daily_loss.py` (Runde 10) |
| `install_e7_trailing.py` | Trailing im Aufwärtstrend lockern (E7-UP) | ✅ Spur in `runtime/exit_monitor.py` |
| `install_mfe_mae_logging.py` | Höchst-/Tiefststand je Position mitschreiben | ✅ `mfe_pct`/`mae_pct` im Journal |
| `install_p4_diagnose.py` | Stille Preis-Fehler sichtbar machen | ✅ P1-HARDEN-Marker |
| `install_p4_frische.py` | Preis-Alter je Coin (`price_age`) | ✅ `price_ts` in `market_data.py` |
| `install_geldfluss_tab.py` | Geldfluss-Reiter | ✅ `ui/geldfluss_tab.py` |
| `install_zyklus_tab.py` | Zyklus-Reiter | ✅ `ui/zyklus_tab.py` |
| `install_terminal_v3.py` | Terminal-Reiter v3 | ✅ `ui/terminal_tab.py` |
| `install_tagesbericht_v2.py` | Tagesbericht aus dem Journal statt aus dem RAM | ✅ in `features/doc_agent.py` |
| `install_metals_stufe2.py` | Metalle: Trendfilter | ✅ (siehe Einschränkung unten) |
| `install_metals_stufe3.py` | Metalle: Long/Short | ⚠️ **wieder verloren** (siehe unten) |
| `fix_terminal_ampel.py` | Preis-Frische-Ampel im Terminal | ✅ |
| `fix_terminal_e7count.py` | E7-UP-Zähler im Terminal | ✅ |
| `fix_terminal_regime.py` | Rohes Regime zusätzlich anzeigen | ⬜ keine Spur — vermutlich verworfen, reine Anzeige |

### Der wichtigste Einzelfall: E8 wurde **bewusst nicht** eingespielt

`install_e8_nachkauf_stop.py` (zweimal vorhanden, `(1)` ist ein
Doppel-Download) hätte Nachkäufe in bestehende Positionen abgeschaltet.
Begründung im Skript: „Der Einstieg funktioniert. Das Leck ist das
Nachkaufen." Geplanter Einbau: 01.08.2026, mit eingebauter Datumssperre.

**Er wurde nie eingespielt — und das war richtig.** Zwei Tage vor dem
geplanten Termin, am 29./30.07., hat das Mess-Audit aus Runde 13 genau
diese Annahme geprüft und **widerlegt**: Der Einstieg trägt keinen
messbaren Richtungsvorteil, Nachkauf und Ausstieg verstärken nur ein
System ohne eigenes Vorzeichen — sie verursachen den Verlust nicht.
Die Grundlage von E8 war damit weg, bevor E8 laufen sollte.

**Das ist kein Versäumnis, sondern das System, das funktioniert hat:**
erst messen, dann bauen. Die Datei liegt als Beleg dafür da, nicht als
offene Aufgabe. **Nicht ausführen.**

### Der Fund: ein Installer, der andere Installer überschreibt

`update_metals_indikatoren.py` sagt über sich selbst: „**Ersetzt**
metals/metals_engine.py + metals_tab.py durch die erweiterte Version."
Ersetzen, nicht ergänzen — und genau das ist passiert:

| Wann | Was |
|---|---|
| bis 27.06. | Engine enthält Stufe 3 (Long/Short-Signale) |
| 29.07. | Handbuch bestätigt: Stufe 2 + 3 installiert, LONG-Pfeil im Reiter sichtbar |
| **06.08. 04:34** | `update_metals_indikatoren.py` läuft und **überschreibt die Datei komplett** |
| heute | Engine kennt nur noch LONG-Signale — Stufe 3 ist weg |

Nachgewiesen durch Vergleich: die Sicherungskopie daneben
(`.scoring_backup_20260806_043440`) enthält die Long/Short-Logik
siebenfach, die heutige Datei kein einziges Mal.

**Wie schwer wiegt das? Kaum.** Das Metalle-Feature handelt nicht mit
Geld (Runde 11) — es zeigt an. Und das Entwicklerhandbuch hat schon am
29.07. nachgemessen, dass der Trendfilter aus Stufe 2 keinen der fünf
dokumentierten Metall-Verluste verhindert hätte („die Begründung im
Installer-Docstring stimmt nicht mit den Daten überein"). Ein Feature,
dessen Nutzen ohnehin widerlegt war, ist verloren gegangen. Kein
Handlungsbedarf.

**Die Lehre daran ist das Wertvolle:** Es gibt im Projekt Skripte, die
Dateien **ersetzen** statt zu **patchen**. Läuft so eines erneut, sind
alle späteren Änderungen an dieser Datei weg — lautlos. Deshalb steht
über den `install_*`-Skripten die Regel: **nicht erneut ausführen.**

### Wofür diese 17 Skripte heute noch gut sind

Als Bauprotokoll. Jedes erklärt in seinem Kopf, *warum* eine Änderung
kam — oft mit Messzahlen, die sonst nirgends stehen. Beispiel aus
`install_metals_stufe2.py`: „ALLE 5 bisherigen Signale waren genau
deshalb Verluste." Sowas findet man in keinem Code-Kommentar.

**Zum Löschen taugen sie trotzdem** — die Änderungen sind längst im
Code, die Begründungen stehen im `ENTWICKLERHANDBUCH.md`. Wer aufräumt,
sollte vorher nur die Docstrings sichern.

## Runde 16 — Die Auswertungs-Skripte, einzeln — und zwei Korrekturen

**Zwei Dateien im Hauptordner sind keine Skripte, sondern aktiver
Bot-Code.** In Runde 11 hatte ich sie in der Sammel-Tabelle
„Auswertungs-Skripte" abgelegt. Das war falsch — beide werden vom
laufenden Bot importiert. Weil sie im Hauptordner zwischen 150 anderen
Dateien liegen statt in `risk/` oder `features/`, sehen sie aus wie
Werkzeuge.

### Korrektur 1: `regime_filter.py` blockiert aktiv deine Käufe

83 Zeilen, kein Docstring, mitten im Hauptordner — und **eine der
schärfsten Bremsen im ganzen Bot**. `app.py:905` ruft sie vor **jedem**
Kaufwunsch auf.

**Was sie tut:** Zählt vier Warnsignale (Preis unter dem Durchschnitt,
Mehrzeitrahmen bärisch, Regime bärisch, Zyklus im Bärenmarkt). Kommen
genug zusammen, wird der Kauf blockiert — **offene Positionen bleiben
unberührt**, der Stop-Loss läuft normal weiter.

**Der aktuelle Stand, aus `config_regime_filter.json` gelesen:**

| Einstellung | Wert | Bedeutung |
|---|---|---|
| `enabled` | `true` | **scharf** |
| `min_confirmations` | `3` | 3 von 4 Signalen nötig zum Blocken |

Diese Datei ist **live editierbar** — sie wird bei jeder Änderung neu
eingelesen, ohne Neustart. Das ist die einzige Stelle im Projekt mit
dieser Eigenschaft.

**Der Zusammenhang, der erst hier sichtbar wird:** Vier Dateien bilden
zusammen ein System, über zwei Ordner verteilt:

| Datei | Rolle |
|---|---|
| `regime_filter.py` (Hauptordner) | die Logik — blockt den Kauf |
| `config_regime_filter.json` (Hauptordner) | die Schwellen — live änderbar |
| `features/regime_adaptiv.py` (Runde 6, Teil 1.5) | der lernende Wächter, der `min_confirmations` anpasst |
| `regime_filter_messung.py` (Hauptordner) | das Messwerkzeug dahinter |

Der „lernende Wächter" aus Teil 1.5 — das Vorbild für alle Automatiken
in diesem Projekt — dreht also an genau **einer** Zahl: der `3` da oben.

**In der Konfigurationsdatei steht die ganze Geschichte mit drin** (der
Kommentar ist Teil der Datei, nicht von mir ergänzt): Am 10.08. wurde
von 2 auf 3 erhöht, weil die Messung zeigte, dass geblockte Käufe nach
4 Stunden im Mittel −0,417 % standen (der Block sparte Geld), nach
24 Stunden aber +1,056 % und nach 48 Stunden +3,643 % (der Block
kostete). Der Filter fängt den Rücksetzer und verpasst die Erholung —
und weil Positionen über Stunden bis Tage laufen, überwiegt der
Nachteil. Dazu die ehrliche Einschränkung: die Fälle sind nicht
unabhängig, deshalb ist „die Richtung belastbar, die Prozentzahlen
nicht".

Ebenfalls dort vermerkt: Der lernende Wächter drehte beim ersten Lauf
sofort auf 4 hoch — gestützt auf nur 14 Stunden Daten. Bei 4 müssten
**alle vier** Signale feuern, der Filter wäre praktisch aus. Deshalb
wurde von Hand auf 3 zurückgesetzt und die Mindestdatenmenge von 12 auf
24 unabhängige Stunden angehoben.

### Korrektur 2: `chartanalyse_backtest.py` läuft täglich mit

Ebenfalls als „Auswertungs-Skript" einsortiert — tatsächlich importiert
der Chartanalyse-Agent (Runde 6, läuft täglich im Bot) daraus die
Funktion `lauf`. Das Konsolen-Bild aus deinem Screenshot („URTEIL:
NEGATIV nach Kosten") stammt genau von hier. Kein Handelseingriff, aber
auch kein Werkzeug, das nur auf Zuruf läuft.

### Die echten Auswertungs-Skripte

Alle read-only, keiner ändert etwas am Bot:

| Befehl | Was er beantwortet |
|---|---|
| `python gesamtauswertung.py` | Das große Gesamtbild — zieht Journal, Telemetrie-Datenbank und Zustand zusammen |
| `python pnl_check.py` | „Wann und wo entstand das Minus?" |
| `python stoploss_analyse.py` | Wo genau der Verlust entsteht — und was helfen würde |
| `python impact_report.py` | Übersicht über das Phasen-Gedächtnis (Teil 1.3) |
| `python regime_filter_messung.py` | Ob der Kauf-Blocker oben sein Geld wert ist |
| `python epoch_report.py` | Ergebnis getrennt nach Epoche |
| `python e4_eval.py` | War der straffere Stop-Loss Rettung oder vorschnell? |
| `python e5_walkforward.py` | Welches Trailing hätte gewonnen — und hält es auch out-of-sample? |
| `python e7_auswertung.py` | Der große E7-Abschlussbericht |
| `python e7_gegenprobe.py` | Kontrafaktisch: hat E7 mehr gebracht als die alte Leiter? |

**`epochs.py`** ist kein Bericht, sondern die **Grundlage** darunter: es
definiert, wann eine Epoche anfing und aufhörte (also welche Trades
unter welchen Einstellungen liefen). Ohne diese Trennung würde man
Ergebnisse aus verschiedenen Regelwerken zu einem Durchschnitt
verrühren, der nichts bedeutet.

### Was davon Modul-Potenzial hat — ehrliche Einschätzung

Du hast gefragt, ob aus diesen Dateien noch etwas werden kann. Drei
Kandidaten, nach Aufwand-zu-Nutzen sortiert:

**1. `epochs.py` + `epoch_report.py` → automatischer Epochen-Schnitt.**
Der stärkste Kandidat. Aktuell muss man die Epochen von Hand pflegen.
Der Bot **weiß aber selbst**, wann sich eine Einstellung ändert (über
`config/versioning.py` aus Runde 11, das genau dafür da ist und
derzeit nichts damit anfängt). Ein Modul, das bei jeder
Konfigurationsänderung automatisch eine neue Epoche eröffnet, würde jede
künftige Auswertung sauber halten — ohne dass du daran denken musst.

**2. `stoploss_analyse.py` + `regime_filter_messung.py` → wiederkehrende
Berichte.** Beide beantworten Fragen, die sich **immer wieder** stellen,
laufen aber nur, wenn du sie von Hand startest. Als wöchentlicher
Bericht (wie der Chartanalyse-Agent aus Runde 6) würden sie eine
Verschlechterung von selbst melden, statt darauf zu warten, dass jemand
nachschaut.

**3. `e5_walkforward.py` → die Methodik, nicht das Skript.** Das Skript
selbst ist an die damalige Fragestellung gebunden. Wertvoll ist die
Methode darin: einen Parameter erst auf einem Zeitraum suchen und dann
auf einem **anderen** prüfen. Genau die Absicherung, die dem
Auto-Optimizer aus Teil 4.6 fehlte — deshalb musste der weg. Wer je
wieder Parameter sucht, sollte diesen Code als Vorlage nehmen.

**Was kein Potenzial hat:** `e4_eval.py`, `e7_auswertung.py`,
`e7_gegenprobe.py` sind an abgeschlossene Epochen gebunden — sie haben
ihre Frage beantwortet. Belege, keine Werkzeuge.

## Runde 17 — Alle 2.511 Dateien, mechanisch klassifiziert

**Die ehrliche Antwort auf „hast du wirklich alles angeschaut?"** Jede
Datei einzeln zu beschreiben ist bei 2.511 Stück weder möglich noch
sinnvoll — 1.541 davon sind Messdaten (CSV-Tabellen und komprimierte
Archive), die keinen eigenen Inhalt zum Erklären haben. Aber es gibt
einen besseren Weg, und er lag die ganze Zeit im Projekt: **dein eigener
Inventur-Agent.**

```bash
python inventar_agent.py
```

Er liest jede Datei, prüft mechanisch, ob der Bot sie lädt, und schreibt
das Ergebnis nach `INVENTAR.md`. Ausgeführt am 11.08.2026:

| Klasse | Dateien | Bedeutung |
|---|---|---|
| **KERN** | 125 | Code, den der Bot beim Start tatsächlich lädt |
| **WERKZEUG** | 130 | Skripte, die du auf Zuruf startest |
| **VERWAIST** | **39** | Code, den niemand lädt — die interessante Gruppe |
| BACKUP | 93 | Sicherungskopien |
| DUPLIKAT | 36 | doppelte Dateien |
| DATEN-ALT | 153 | veraltete Messdaten |
| DATEN/DOKU | 1.733 | Messwerte, Handbücher, Bilder |

**Der eigentliche Bot besteht aus 125 Dateien.** Alles andere ist
Werkzeug, Beleg oder Altlast. Genau diese 125 sind in den Runden 1–11
einzeln behandelt worden.

### Die 39 verwaisten Dateien — Gegenprobe zu meinem Rundgang

Die Liste des Agenten ist unabhängig von mir entstanden. Sie bestätigt
**jeden einzelnen** Verwaist-Fund aus meinen Runden: die fünf im
Datenordner (Runde 7), die drei in `reports/` (Runde 11),
`exchange_client.py` (Runde 4), `market_regime.py` (Runde 6),
`balance_reporter(12).py` (Runde 8), `calculator.py` (die Korrektur aus
Runde 12), `regel_schalter.py` (Runde 8), die ML-Reste und alle
`_*_payload*.py`.

**Eine Einschränkung, die man kennen muss** — dieselbe wie beim
Forschungs-Scan aus Runde 12: Der Agent prüft nur, ob eine Datei vom
Bot geladen wird. `backtest/ausstieg_backtest.py` und `tests/run_all.py`
stehen deshalb als „verwaist", obwohl sie von anderen Werkzeugen genutzt
werden. Und die leeren `__init__.py`-Dateien sind technisch notwendig,
auch wenn sie nichts enthalten. **Ein Scan ersetzt das Nachdenken
nicht.**

### Der neue Fund: ein zweiter Folgeschaden desselben Vorfalls

`metals/metals_store.py` steht als verwaist — das war neu für mich.
Nachgeprüft, und es hängt direkt an Runde 15 zusammen:

| | heute | in der Sicherungskopie vom 06.08. |
|---|---|---|
| Anbindung im Metalle-Reiter | **0 Stellen** | 2 Stellen |

Derselbe Replace-Installer (`update_metals_indikatoren.py`), der am
06.08. um 04:34 die Long/Short-Logik überschrieb, hat **auch** die
Anbindung an den Metalle-Speicher entfernt. Der Reiter verlor damit
seine Dauerhaftigkeit — er beginnt bei jedem Neustart wieder bei null,
statt den letzten Stand zu laden.

**Halb so wild, aus zwei Gründen:** Metalle handeln kein Geld (Runde 11),
und die Datensammlung selbst läuft weiter — `sammler.py` benutzt den
Speicher noch (der tägliche Sammler aus Runde 11). Verloren ist nur die
Anzeige-Dauerhaftigkeit im Reiter.

**Damit steht der Vorfall vom 06.08. vollständig da:** Ein Skript, das
Dateien ersetzt statt patcht, hat an einem Morgen zwei Dinge gelöscht,
ohne dass jemand es bemerkte. Das ist die Lehre, nicht der Schaden.

## Runde 18 — Ein Modul-Kandidat, endgültig gemessen

Du hast gesagt: „viele Dateien liegen nur da und wurden noch nicht
aktiviert bzw. noch nicht mal geprüft und gemessen — aus vielen können
wir bestimmt noch gute Module bauen." Genau dafür gibt es einen Fall,
der jetzt entschieden werden konnte.

### Das Situations-Gedächtnis

**Was es ist:** `features/situation_memory.py` merkt sich zu jedem Trade
die **Gesamtlage** (Regime, Zyklus, Angst-Index, RSI, ADX, NUPL,
Mehrzeitrahmen) und sucht bei einer neuen Entscheidung nach *ähnlichen
Situationen von früher*. Die Idee: „Als es zuletzt so aussah wie heute,
ging es so-und-so aus."

**Warum es nie angeschlossen wurde:** Dazu gehört ein Prüfstein,
`situation_replay.py`, mit einer klaren Ansage im Kopf der Datei:
> Beantwortet die Kernfrage **bevor** das Gedächtnis je mitentscheiden
> darf: „Hätte das Situation-Memory die Trade-Ergebnisse vorhersagen
> können?"

Diese Prüfung war bisher **nicht belastbar**, weil das Impact-Journal
Stop-Loss- und Trend-Exits nicht vollständig erfasste. Genau das wurde
inzwischen repariert (der Journal-Fix aus Runde 3). Nachgeprüft: das
Journal enthält heute **625 abgeschlossene Trades** mit allen
Ausstiegsarten — Trailing, Stop-Loss, Trend-Exit, Breakeven. Die
Voraussetzung ist erfüllt.

**Also habe ich die Prüfung laufen lassen** (sie liest nur, ändert
nichts):

```bash
python situation_replay.py
```

**Das Ergebnis, 622 bewertete Trades:**

| | Wert |
|---|---|
| Trefferquote des Gedächtnisses | **66,2 %** |
| „Immer Gewinn tippen" | **72,0 %** |
| Zusammenhang mit dem echten Ergebnis | +0,136 (ab +0,2 wäre es ein erstes Signal) |

**Das Gedächtnis ist schlechter als stur „wird schon gut gehen" zu
sagen.** Und der Blick auf die Feinaufteilung macht es noch deutlicher:

| Wenn das Gedächtnis sagt … | … tatsächlich gewonnen |
|---|---|
| „sehr wahrscheinlich Gewinn" (≥80 %) | 79,0 % ✅ passt |
| „mittel" (50–80 %) | 53,6 % ✅ passt |
| **„wahrscheinlich Verlust" (<50 %)** | **65,0 %** ❌ genau falsch herum |

In der Klasse, in der es warnt, liegt es am deutlichsten daneben — dort
wäre der Trade in zwei von drei Fällen gut gegangen. Ein Modul, das
genau bei seiner Warnung falsch liegt, würde nicht helfen, sondern
schaden.

**Damit ist eine offene Frage endgültig beantwortet:** Das
Situations-Gedächtnis wird **nicht** angeschlossen. Die Entscheidung, es
liegen zu lassen, war richtig — jetzt ist sie zum ersten Mal **gemessen**
statt vermutet.

**Dieselbe Lektion wie bei der KI (Teil 4.8):** Ein Modell, das
schlechter ist als die einfachste denkbare Regel, gehört nicht ans
Steuer — egal wie aufwendig es gebaut ist. Und man erfährt das nur,
wenn man es ausrechnet.

**Was jetzt trotzdem wertvoll bleibt:** Der Prüfstein selbst.
`situation_replay.py` ist die Vorlage dafür, wie **jeder** künftige
Modul-Kandidat geprüft werden sollte: gegen die einfachste Alternative,
ohne Blick in die Zukunft, mit ehrlicher Angabe der eigenen
Schwachstellen. Diese Datei ist wertvoller als das Modul, das sie prüfen
sollte.

## Runde 19 — Die restlichen Werkzeuge

### Diagnose und Selbsttest (alle read-only)

| Befehl | Was er beantwortet |
|---|---|
| `python voll_diagnose.py` | Der große Selbsttest: Zyklus-Simulation, alle Komponenten |
| `python diagnose.py` | Speziell: Was von der V4-Bridge ist in V6 wirklich aktiv? |
| `python preflight.py` | Ist der Bot bereit für Echtgeld? |
| `python check_install.py` | Sind alle Pakete installiert? |
| `python status.py` | Schnelle Übersicht in einem Befehl |
| `python analyse_readiness.py` | „Reifeprüfung": Ist der Bot profitabel — mit echten Netto-Zahlen? |
| `python brain_view.py` | **Drei Blicke nebeneinander:** echte V6-Zahlen · was das Gehirn benutzt · wie viel davon V4-Warmstart ist |
| `python cockpit_server.py` | Lokales Analyse-Cockpit im Browser, rechnet alles selbst nach |
| `python journal_abgleich.py` | Stimmt das Journal mit dem echten Bestand überein? |
| `python telegram_test.py` | Prüft Token und Chat-ID direkt gegen Telegram |

**`brain_view.py` ist der wertvollste davon** — er beantwortet genau die
Frage aus Teil 1.1: wie viel von dem, was das Gehirn für Entscheidungen
nutzt, stammt eigentlich aus V4-Altdaten? Ein Werkzeug gegen
Selbsttäuschung.

**`check_punkt_a.py`** prüft, ob bestimmte alte Epochen-Fixes (E6-A,
E6-B, F&G-URL, P1-Härtung) noch im Code stehen — historisch, an
abgeschlossene Epochen gebunden.

**`bot_navigator.py`** (687 Zeilen) baut eine interaktive HTML-Karte des
Projekts und öffnet sie im Browser. Die vorhandene `bot_uebersicht.html`
stammt allerdings vom **6. Mai** — drei Monate alt, aus einer Zeit, als
der Bot noch anders aussah. Wer sie nutzen will, muss das Skript neu
laufen lassen.

### Die 50 Skripte im Forschungsordner

Sie folgen einem klaren Muster und sind in `README.md` und `BEFUNDE.md`
dort dokumentiert — deshalb hier nur die Gruppen:

| Gruppe | Anzahl | Zweck |
|---|---|---|
| `messung_*.py` | 20 | Die eigentlichen Messläufe (E1/E2/E5, F1–F3, G1/G2, T-034) |
| `audit_*.py` | 12 | Selbstprüfungen: stimmen die eigenen Zahlen? |
| `batterie_h*.py` + `batterie_verdict.py` | 5 | Die Hypothesen-Testbatterien und ihr Urteil |
| `db_*.py` | 4 | Datenbank: Schema, Architektur-Scan, Befüllung, Abfrage |
| `kosten_matrix_v2/v3/v4.py` | 3 | Kostenszenarien in drei Generationen — nur v4 ist aktuell |
| `daten_*.py` | 2 | Datenbeschaffung (Download, Funding-Korrektur) |
| Rest | 4 | Instrumentierung, Statistik, Sonderauswertungen |

**Bemerkenswert:** Ein Drittel dieser Skripte prüft die **eigenen**
Ergebnisse nach (`audit_*`). Genau diese Selbstkontrolle hat den
45-Minuten-Blick-in-die-Zukunft gefunden, der in Runde 12 erwähnt ist —
ein Fehler in der eigenen Messung, den niemand von außen bemerkt hätte.

**`harness_ext.py` liegt bitgleich doppelt** (in beiden `code/`-Ordnern,
identische Prüfsumme). Vermutlich Absicht, damit jeder Ordner
eigenständig läuft — beim Ändern müssen aber beide angefasst werden.

---

# TEIL 10 — Betrieb: Messfenster, Freeze und der Weg live

**Stand: 25.08.2026.** Die Freigabeprüfung wurde am Tag des Schreibens
laufen gelassen; die Zahlen unten sind ihr Ergebnis.

---

## 10.1 Die eine Regel, an der alles hängt

> **Während das Messfenster läuft, wird keine einzige Regel geändert.**

Klingt kleinlich. Ist es nicht — es ist der Mechanismus, der dieses Projekt
sieben Monate lang zurückgeworfen hat.

**Warum.** Jede Verhaltensänderung setzt die Zählung auf null. Man kann
Handel, die unter *verschiedenen* Regelwerken entstanden sind, nicht
zusammenzählen. Aus sieben Monaten Laufzeit sind dadurch zeitweise
**sechs Tage verwertbare Daten** geworden.

**Das Fenster läuft bis zum 18.09.2026.** Die verbindliche Angabe steht in
`config_zielgroessen.json` unter `messfenster_ende` — **nicht** im
Programmtext und nicht in einem Dokument. `stichtag.py` und der
Terminal-Reiter lesen sie von dort. Wer sie ändert, ändert sie dort, sonst
laufen zwei Wahrheiten nebeneinander.

**Warum bis 18.09. und nicht früher:** Nicht wegen der 30 Fälle des
Messfensters — die sind erreicht. Sondern wegen **Kriterium A der
Freigabe: 100 Verkäufe.** Bei rund drei Verkäufen am Tag ist das um den
19.09. erreichbar. Zum ersten Mal steht damit eine Zahl in Aussicht, die
eine echte Antwort erlaubt.

---

## 10.2 Was während des Freeze erlaubt ist

| | |
|---|---|
| ✅ **Erlaubt** | Alles, was ausschließlich **aufschreibt**: Protokolle, Auswertungen, Messwerkzeuge, dieses Handbuch |
| ❌ **Gesperrt** | Alles, was das **Verhalten** berührt: Schwellen, Regeln, Modus-Schalter, Münzliste, Positionsgröße |

**Auch das Umlegen eines Regel-Schalters auf SHADOW ist eine
Verhaltensänderung** (Teil 1, Abschnitt 1.5). Der Schalter ist nicht die
Erlaubnis, ihn zu benutzen.

**Die Ausnahme:** Ein Fund mit **Kapital- oder Datenverlustrisiko** wird
sofort gemeldet — als eigener Block, mit Fundstelle. Der Freeze bleibt
trotzdem; die Entscheidung trifft Sven.

Genau so ist es am 24.08. gelaufen, als zwei Sammler vierzig Minuten lang
in einen leeren Ordner schrieben (Teil 8, Abschnitt 8.9, Fall 4).

---

## 10.3 Epochengrenzen — warum jede Änderung eine braucht

Eine **Epoche** ist ein Zeitraum, in dem das Regelwerk unverändert blieb.
Nur innerhalb einer Epoche darf man Zahlen zusammenzählen.

`config_epochs.json` führt bisher **acht**. Die letzten vier:

| Epoche | Beginn |
|---|---|
| `E4_btc_only` | 07.08.2026 |
| `E5_balanced_zurueck` | 10.08.2026 |
| `E6_messfenster` | 13.08.2026 |
| **`E7_filter_schaerfer`** | **15.08.2026** — die laufende |

**`E7` ist lehrreich, weil sie niemand von Hand gesetzt hat.** Der lernende
Wächter hat am 15.08. selbständig eine Schwelle verstellt — mitten im
Messfenster. Entdeckt wurde es durch eine Telegram-Meldung, die Sven
auffiel; der Regel-Wächter schlug **nicht** an, weil er nur den
Trend-Ausstieg überwacht.

> **Die Entscheidung war inhaltlich richtig** — drei unabhängige Messungen
> bestätigen sie. **Falsch war nur der Zeitpunkt.** Ohne diese Grenze hätte
> E6 Handel unter zwei verschiedenen Regelwerken verglichen.

Der Lerner läuft bewusst weiter, damit messbar bleibt, **ob** seine
Entscheidung richtig war (`schwelle_vergleich.py`).

---

## 10.4 Die Freigabeprüfung — der Stand von heute

```
python go_live_check.py       oder  freigabe_pruefen.bat doppelklicken
```

**Ergebnis am 25.08.2026: KEINE FREIGABE — fünf Kriterien nicht erfüllt.**

### Die Zahlen

| | Kriterium | ist | soll | |
|---|---|---|---|---|
| **A** | Stichprobe seit dem Umbau | 60 Verkäufe in 26,2 Tagen | ≥ 100 | ❌ |
| **B** | **Erwartungswert je Handel** | **+0,1213 $** (Summe +7,28 $) | > 0 | ✅ |
| **C** | Chance/Risiko gegen Break-even | 1,44 bei 45,0 % Trefferquote | ≥ 1,47 | ❌ |
| **D** | Gebühren-Kreisel | 3 Rückkäufe binnen 15 min (5 %) | ≤ 10 % | ✅ |
| **E** | Größter Kapitalrückgang | 0,66 % | ≤ 15 % | ✅ |
| **F** | **Vorteil statistisch belastbar** | 95-%-Intervall **−0,4974 … +0,7401 $** | untere Grenze > 0 | ❌ |
| **G** | Mindestlaufzeit | 26,2 Tage | ≥ 14 | ✅ |

### Technik und Sicherungen

| | | |
|---|---|---|
| H1 | Tagesverlust-Wächter scharf (Grenze 6 %) | ✅ |
| H2 | Notbremse aktiviert | ✅ |
| H3 | Klumpengrenze je Münze 35 % | ✅ |
| H4 | Nachkauf-Leiter begrenzt (3 Stufen) | ✅ |
| H5 | **API-Schlüssel** | **fehlt** ❌ |
| H6 | Schlüssel-Rechte — **von Hand prüfen**: „Enable Withdrawals" muss **aus** sein | — |
| H7 | **Journal deckungsgleich mit Bestand** | **weicht ab** ❌ |
| H8 | Modus `paper` bis zur Freigabe | ✅ |

### Wie man das liest

**Kriterium B ist die Kernfrage — und es steht auf grün.** Der
Erwartungswert je Handel ist positiv. Die Prüfung schreibt selbst dazu:
*„Trefferquote ohne positiven Erwartungswert ist wertlos — 71,9 % und
trotzdem Minus."*

**Kriterium F ist das strengste** und der eigentliche Wächter: Das
95-%-Intervall reicht von **−0,50 $ bis +0,74 $**. Auch das pessimistische
Ende muss im Plus liegen, sonst ist der Gewinn womöglich Zufall. Bei 60
Fällen ist das Intervall noch zu breit — **Kriterium F löst sich allein
durch mehr Daten**, wenn der Vorteil echt ist.

**Kriterium C ist ohne die Trefferquote nicht lesbar.** Bei 71,9 %
Trefferquote genügt ein Verhältnis von 0,39; bei 30 % braucht es 2,33. Die
Schwelle rechnet das mit.

**Kriterium H7 ist Befund 71** — zwei Werkzeuge geben zwei Antworten auf
dieselbe Bestandsfrage. Welches richtig rechnet, ist noch **nicht geklärt**.

> **Zwei der fünf offenen Punkte lösen sich durch Zeit** (A und F), einer
> durch das Konto (H5), einer durch bessere Handel (C), und einer verlangt
> eine Untersuchung (H7).

---

## 10.5 Der Weg zum Echtbetrieb

Zwischen Papierhandel und echtem Geld liegt eine Stufe, die es geben kann,
ohne etwas zu riskieren:

```
TESTNETZ_PROBE.bat        doppelklicken
```

Sie prüft den Order-Weg an einer **echten Börse mit Spielgeld**:

| Frage | warum sie zählt |
|---|---|
| Kommt die Order überhaupt an? | im Papiermodus nie geprüft |
| Wird bei einer Wiederholung **doppelt gekauft**? | **Befund 68** — der einzige als kritisch eingestufte |
| Wie reagiert die Börse auf eine zu kleine Order? | Mindestgrößen kennt der Papiermodus nicht |
| Ist der Auftragsstatus abfragbar? | Grundlage für jede Nachverfolgung |
| Wie groß sind Gebühr und Schlupf **wirklich**? | Gegenprobe zu K-BASIS (Teil 4) |
| Stimmt der Kontostand? | Gegenprobe zu H7 |

**Es fehlt nur eines:** Testnetz-Schlüssel. Sven holt sie bei
`testnet.binance.vision` und trägt sie als `BINANCE_TESTNET_KEY` und
`BINANCE_TESTNET_SECRET` in `.env` ein. **Kein Eingriff in den Bot, kein
Echtgeld.**

---

## 10.6 Die Stichtags-Regel — warum Befunde den Live-Weg nicht mehr blockieren

**Beschlossen am 21.08.2026 von Sven**, nachdem er sagte: *„jeden Tag kommen
neue Erkenntnisse, was noch fehlt — ich habe keine Hoffnung mehr, dass ich
den scharf kriege."*

Berechtigt: In sieben Monaten sind über siebzig Befunde entstanden, und
jeder neue schob den Live-Gang weiter nach hinten.

**Ab dem Ende des Messfensters gilt deshalb:**

| | |
|---|---|
| **Weiter sammeln** | Neue Befunde werden **unverändert** gesucht, gemessen und geschrieben |
| **Aber nicht mehr blockieren** | Ein Befund hält den Live-Weg nur auf, wenn er **Kapital- oder Datenverlust** riskiert |
| **Alles andere** | kommt hinten an die Liste und wird **nach** der Freigabe gemacht |

> Solange jeder Fund den Weg versperrt, kommt der Bot nie live — denn Funde
> hören nie auf. Das ist keine Nachlässigkeit, sondern die Trennung zwischen
> *gefährlich* und *verbesserungswürdig*.

**Nicht betroffen:** Die Freigabekriterien selbst bleiben unangetastet.
Kriterium F — der belegte Vorteil — entscheidet weiterhin allein.

---

## 10.7 Die fünf Zielgrößen

Sie stehen in `config_zielgroessen.json` und zerfallen in **zwei Klassen**:

| Zielgröße | Ziel | Warnung | Klasse |
|---|---:|---:|---|
| Erwartungswert je Handel | 0,30 % | 0,00 % | **sperrt den Live-Gang** |
| Größter Rückschlag | 15,0 % | 20,0 % | **sperrt den Live-Gang** |
| Gewinner / Verlierer | 1,27 | 1,00 | läuft im Schatten mit |
| Profit-Faktor | 1,20 | 1,00 | läuft im Schatten mit |
| Verschenkte Bewegung | 1,0 PP | 1,5 PP | läuft im Schatten mit |

Dazu die Mindestfallzahl: **30**. Darunter schreibt jedes Werkzeug dieses
Projekts ausdrücklich **„nicht entscheidbar"** statt einer Zahl.

---

## 10.8 Was noch zu dünn ist

Diese Messungen laufen, haben aber zu wenige Fälle für ein Urteil. Sie
brauchen **Wochen, keine Stunden** — und genau dafür ist das Messfenster da.

| Messung | Stand | nötig |
|---|---:|---|
| Verkäufe der laufenden Epoche | **62** *(29.08., vorher 39)* | 100 (Kriterium A) |
| Lern-Ereignisse | 45 | 100 für die Notizbücher |
| Schatten-Ausstiege | 39 | 30 je Regel, getrennt |
| Positionsgrößen-Notizbuch | 41 | Vergleich braucht abgeschlossene Verläufe |
| Nachlauf nach RSI-Ausstieg | 2 unabhängige | ~10 |

> **Nichts davon lässt sich beschleunigen.** Wer die Fallzahl erzwingen
> will, indem er dieselbe Marktlage mehrfach zählt, bekommt eine große Zahl
> und keine Antwort — siehe Teil 8, Abschnitt 8.9, Fall 1.

*Früher: D.2.*

*Früher verstreut in ALT 4.21, 4.29, 4.33, 4.49, 4.56, 4.97, 4.100, 4.111,
4.112, 4.113, 4.118, 4.119 sowie den alten Kapiteln D und G.*

---

## 10.9 Die äußere Latte — unser Bot gegen blind getestete Signalanbieter

**Stand: 29.08.2026.** Sven brachte einen Datensatz von sieben
Forex-Signalanbietern mit, die auf **echten MT4-Konten blind getestet**
wurden (teils zusätzlich Myfxbook-verifiziert), dazu einen eigenen
Programmentwurf für den Vergleich.

Bis dahin maß sich das Projekt nur an **sich selbst** — an den fünf
Zielgrößen aus 10.7 und an der Trivial-Latte. Das ist richtig, aber es
beantwortet eine Frage nicht: *Wo stünden wir neben Leuten, die davon
leben?*

### Die äußere Latte

| Kennzahl | Spanne der sieben | Schnitt |
|---|---|---|
| Winrate | 71 – 78 % | 74,1 % |
| Profit-Faktor | 2,0 – 2,8 | 2,33 |
| Größter Rückschlag | 12 – 15 % | 14,4 % |

### Wo wir stehen

Gemessen über **508 Verkäufe** (10.06.–28.08.), Geldzahl `pnl` — die
enthält die Gebühren, `pnl_pct` wäre geschönt:

| Kennzahl | gesamt | nur E7 | Anbieter-Ø |
|---|---:|---:|---:|
| Winrate | 67,1 % | 45,2 % | 74,1 % |
| **Profit-Faktor** | **0,880** | **0,806** | 2,33 |
| Größter Rückschlag | 18,8 % | 6,6 % | 14,4 % |
| Netto | −37,38 $ | −11,89 $ | — |
| **Trivial-Latte** | 0,00 $ | 0,00 $ | — |

**Gegengeprüft:** Das Netto von −37,38 $ steht unabhängig auch in
`data_store/equity_history.json` in der Reihe `trades`. Zwei Quellen,
dieselbe Zahl.

> **Der Vergleich hinkt, und das gehört dazugesagt.** Die Anbieter liefen
> auf echten Konten, wir im Papierhandel. Sie handeln Forex mit Spreads im
> Hundertstelbereich, wir Krypto mit **0,505 % je Runde**. Ein Rangvergleich
> wäre unredlich.
>
> Was bleibt, hängt an keinem Vergleich: **Ein Profit-Faktor unter 1,00 ist
> in jedem Markt ein Verlustgeschäft.**

### Der eigentliche Befund — zwei Krankheiten in zwei Epochen

Nicht die Winrate ist die interessante Zahl, sondern das Verhältnis von
mittlerem Gewinn zu mittlerem Verlust:

| | mittl. Gewinn | mittl. Verlust | Verhältnis | Winrate ist | Winrate **nötig** | Lücke |
|---|---:|---:|---:|---:|---:|---:|
| **gesamt** | +0,80 $ | −1,86 $ | **0,43 : 1** | 67,1 % | 69,9 % | −2,8 PP |
| **E7** | +1,77 $ | −1,81 $ | **0,98 : 1** | 45,2 % | 50,5 % | −5,4 PP |

**E7 hat das Verhältnis fast repariert** — von 0,43 auf 0,98. Die Gewinne
laufen jetzt so weit wie die Verluste. **Dafür ist die Trefferquote
eingebrochen**, von 67 auf 45 %. Das sind zwei verschiedene Probleme, und
sie brauchen zwei verschiedene Antworten.

> **Die auffallendste Bestätigung:** Aus den Zahlen ergibt sich ein nötiges
> Gewinner/Verlierer-Verhältnis von rund **1,22 : 1**. In
> `config_zielgroessen.json` steht als Ziel seit dem 19.08. **1,27**. Zwei
> voneinander unabhängige Wege, fast dieselbe Zahl — die Zielgröße war gut
> gewählt.

### KORREKTUR 02.09.2026 — die Trefferquote fiel wegen der Gebühr

Anlass war Svens Frage: *„warum ist die Win Rate so schlecht geworden? Wir
hatten früher eine WR/83, wenn ich mich nicht täusche."*

**Er täuschte sich nicht.** In der Chronik (`ENTWICKLERHANDBUCH.md:1313`)
steht zur E7-Auswertung um den 31.07.: *„R/R 0.84, WR 83%, +12.73$ — aber
nur **2 wirksame Fälle** (beide ADA)."* Das Werkzeug hat damals selbst
gewarnt. **Eine Trefferquote aus zwei Fällen ist ein Münzwurf mit
Kommastelle.**

Die Nachforschung deckte etwas Größeres auf. **Die Deutung oben — der
schärfere Filter habe auch gute Einstiege aussortiert — hält nicht.**

#### Ein Sprung auf den Tag genau

Die tatsächlich gebuchte Gebühr, gemessen als Anteil am Einsatz, je
Handelstag:

```
2026-08-11     0,1000 %
2026-08-12     0,2500 %      <== das Zweieinhalbfache
```

Und `config_epochs.json` sagt, was das war:

| Datum | Epoche | Bezeichnung |
|---|---|---|
| 12.08. | — | Gebühr springt 0,10 → 0,25 % |
| **13.08.** | **E6_messfenster** | *„Messfenster: eingefroren, **korrekte Gebuehren**"* |
| 15.08. | E7_filter_schaerfer | Regime-Filter strenger |

**Der Gebührensprung ist die E6-Änderung.** Er steht namentlich in der
eigenen Epochenliste.

#### Warum der Vergleich oben nicht trägt

Die Zeile „gesamt" umfasst 508 Verkäufe — **84 % davon liegen vor dem
12.08.** Sie sind mit 0,10 % gerechnet, die E7-Zeile mit 0,25 %.
Gegenübergestellt werden also nicht zwei Filter, sondern **zwei
Kostenwelten**.

Rechnet man beide Zeiträume auf **dieselbe** Gebühr um — der Faktor stammt
aus 158 Verkäufen mit vollständigen Feldern, Median **3,01** (das ist die
Doppelbuchung aus 4.5, deshalb streut er):

| Faktor | beide bei 0,10 % | beide bei 0,25 % |
|---|---:|---:|
| 2,0 | −23,6 PP | −17,7 PP |
| 2,5 | −18,7 PP | −12,5 PP |
| **3,0** | **−5,1 PP** | **−9,9 PP** |
| 3,5 | −1,4 PP | −3,4 PP |

Gemessen wurde ein Absturz von **37,2 Prozentpunkten** (77,9 % vor dem
12.08., n=77 → 40,7 % danach, n=81).

> **In jedem Szenario erklärt die Gebühr die Mehrheit des Absturzes.** Die
> echte Verschlechterung liegt zwischen etwa 1 und 24 Prozentpunkten, am
> wahrscheinlichsten bei 5 bis 12.

#### Die ehrliche Geschichte der Trefferquote

Gerechnet auf `pnl` — das einzige Feld, das über alle 522 Verkäufe zu
100 % vorhanden ist:

| Zeitraum | n | Trefferquote |
|---|---:|---:|
| 01.–15.06. | 80 | **92,5 %** |
| 16.–30.06. | 151 | 62,3 % |
| 01.–15.07. | 132 | 73,5 % |
| 16.–31.07. | 65 | 64,6 % |
| 01.–15.08. | 18 | 33,3 % |
| 16.–31.08. | 73 | 42,5 % |

**Der Bot ist nicht plötzlich schlechter geworden — er wird seit dem 12.08.
ehrlich gemessen.** Die 92,5 % vom ersten Junidrittel waren mit einer
Gebühr gerechnet, die es bei Bybit EU nie gab.

#### Der Fehlversuch davor, und was er lehrt

Die erste Auswertung stellte brutto (`pnl_pct > 0`) gegen netto (`pnl > 0`):

| Monat | brutto | netto |
|---|---:|---:|
| Juni | 46,3 % | **72,7 %** |
| Juli | 28,9 % | **70,6 %** |

**Netto über brutto ist unmöglich** — Kosten senken eine Quote, sie heben
sie nicht. Ursache: `pnl_pct` fehlt bei 42 % der Juni- und 68 % der
Juli-Verkäufe, und die Abfrage zählte „fehlt" als „kein Gewinn".

> **Ein fehlendes Feld ist keine Null.** Vor jedem Vergleich über die Zeit
> gehört die Frage: *Gab es dieses Feld damals überhaupt?*

#### Was offen bleibt

Die **Größe** der echten Verschlechterung. Sie hängt am Kostenfaktor, und
der ist wegen der Doppelbuchung (4.5) nicht sauber bestimmbar. Erst nach
deren Korrektur ist die Frage entscheidbar.

> **Die übergreifende Lehre:** Eine Kennzahl über einen Zeitraum, in dem
> sich die **Rechenregel** geändert hat, misst die Regeländerung mit. Genau
> dafür gibt es die Epochengrenzen (10.3) — bei der Trefferquote wurden sie
> nicht angewandt, obwohl die Datei die Änderung beim Namen nennt.

### Was daraus folgt

- **Erste Hürde ist nicht 2,33, sondern 1,00.** Erst muss der Bot aufhören
  zu verlieren. Das deckt sich mit der Warnschwelle in 10.7.
- **Zwei Wege dorthin, einer genügt:** Trefferquote von 45,2 auf über
  **50,5 %**, *oder* Verhältnis von 0,98 auf über **1,22 : 1**.
- **Der Rückschlag von 6,6 % in E7 ist kein Verdienst.** Ein Bot, der
  langsam verliert, hat wenig Rückschlag. Ohne Gewinn sagt die Zahl nichts.
- **62 Verkäufe sind kein Urteil.** Kriterium A verlangt 100. Konfidenz:
  **OFFEN**.

### Das Werkzeug: `provider_vergleich.py`

| Befehl | Wozu |
|---|---|
| `python provider_vergleich.py` | Gesamtlaufzeit **und** laufende Epoche gegen die Anbieter |
| `python provider_vergleich.py --epoche E7_filter_schaerfer` | nur eine Epoche |
| `python provider_vergleich.py --selbsttest` | sieben Tests, u. a. gegen eine Handrechnung |

Die Anbieterdaten liegen in `providers.json` und lassen sich erweitern.

**Was an Svens Entwurf geändert wurde — und warum es wichtig war:**

| Im Entwurf | Jetzt |
|---|---|
| `my_bot = {"win_rate": 0.74, "profit_factor": 2.10, ...}` — von Hand eingetragen | Zahlen kommen **aus dem Handelsbuch**. Es gibt keine Stelle mehr für eine Wunschzahl |
| Punktesystem ohne Sperre | **Profit-Faktor < 1,00 → „verlustbringend"**, unabhängig von der Punktzahl |
| Alle Trades in einem Topf | getrennt nach **Epoche** (10.3) |
| Keine Trivial-Latte | „gar nicht handeln" = 0,00 $ steht daneben |
| Eigene Schwellen | liest **`config_zielgroessen.json`** mit, damit nicht zwei Latten nebeneinanderstehen |

> **Warum der erste Punkt der wichtigste ist:** Mit den Platzhaltern hätte
> das Programm *„auf oder über Niveau der Top-Provider"* gemeldet. Die
> echten Zahlen waren 0,671 / 0,880 / 0,188. **Ein Prüfprogramm, in das man
> die Antwort selbst einträgt, prüft nichts.**

*Angelegt 29.08.2026 auf Svens Auftrag. Ergänzt 10.7 um die äußere Sicht;
die inneren Zielgrößen bleiben unverändert maßgeblich.*

---

## 10.10 Nur eine Instanz — eine Regel ohne Schloss

**Angelegt 02.09.2026 nach einem Vorfall.** Sven startete am 01.09.
versehentlich ein zweites Mal. Seine Frage danach — *„ich hoffe, das hat
nix kaputt gemacht?"* — war berechtigt, und die Antwort lautet: **den Daten
nicht, dem Zustand schon.**

### Was passiert ist

Im Systemlog steht **eine einzige** Zeile der zweiten Instanz:

```
[2026-09-01T21:00:40] [SIGNAL] SOL/USDC: Score 3/10 (30%) -> BUY 150.00$
```

Der laufende Bot rechnete in derselben Minute:

```
[20:53:01] [INFO]  [SIZING] Basis 466.92$ -> 30% = 140.08$
[20:53:01] [SIGNAL] SOL/USDC: Score 7/10 (70%) -> BUY 140.08$ | ... FIBONACCI_SUPPORT STARK
[20:53:01] [WARN]  [REGIME] SOL/USDC: BUY blockiert (Regime-Filter)
```

**Drei Unterschiede, jeder für sich beweisend:**

| | laufender Bot | die fremde Zeile |
|---|---|---|
| Positionsgröße | 140,08 $ (30 % von 466,92) | **150,00 $** (30 % von **500** — Startguthaben) |
| Zeile davor | immer `[SIZING]` | keine |
| Zeile danach | immer `[REGIME]` | keine |

**Die Folge:** Ab 20:53:01 — dem Moment des zweiten Starts — schrieb der
ursprüngliche Bot **keine Entscheidung mehr**. 37 Minuten lang, bei sonst
**~880 je Stunde ununterbrochen**. Der Prozess lebte dabei (41 Threads,
messbare Rechenzeit); der Faden für die Marktlage lief weiter, **die
Handelsschleife hing**.

Behoben durch Neustart. Danach gemessen: 13–15 Zeilen je Minute, also
wieder der Normaltakt.

### Warum nichts es verhindert hat

| Mechanismus | Greift für `app.py`? |
|---|---|
| Sperrdatei in `core/hintergrund.py` | **Nein** — nur für die Hintergrundjobs. Dort belegt: zweite Instanz bricht mit Exit-Code 3 ab |
| Portbelegung | **Nein** — mit `netstat -ano` nachgemessen: der Bot-Prozess hört **keinen einzigen Port** ab |
| Prüfung im `__main__`-Block | **Nein** — `app.py:4573` erzeugt sofort `TradingImperiumV6()` |

> **Und die Regel in `CLAUDE.md` hilft nicht.** Sie sagt: *„Vor jedem
> Neustart prüfen, wer Port 5050 hält."* Es hält ihn niemand. Die Prüfung
> meldet „frei", während der Bot läuft.

### Woran man den echten Bot erkennt

Beim Nachsehen im Taskmanager führen zwei Dinge in die Irre:

1. **Der Startwrapper.** `start_bot.bat` erzeugt eine Kette: `cmd` →
   `python.exe` (Alias-Stummel) → `python3.13.exe` (der Arbeiter). Drei
   Prozesse, **eine** Instanz.
2. **Der Name.** Der Arbeiter heißt **`python3.13.exe`**, nicht
   `python.exe`. Wer nur nach `python.exe` sucht, findet den Stummel und
   hält ihn für den Bot.

| | Alias-Stummel | echter Bot |
|---|---|---|
| Threads | 1 | **~40** |
| Arbeitsspeicher | ~1 MB | **~850 MB** |
| Rechenzeit | 0 | messbar |

> **Ein Messgerät, das den falschen Prozess ansieht, meldet einen toten
> Bot, der putzmunter ist.** Genau das ist am 01.09. passiert — und wurde
> nur bemerkt, weil dieselbe Messung an einem Prozess geeicht wurde, von
> dem sicher war, dass er lebt.

### Was zu tun ist

Eine Sperrdatei im `__main__`-Block, wie sie `core/hintergrund.py` schon
hat — **einschließlich der Prüfung, ob die eingetragene Prozessnummer noch
lebt**, sonst sperrt ein Absturz den nächsten Start dauerhaft aus.

> **Eine Regel, die nur im Handbuch steht, ist kein Schutz — sie ist eine
> Bitte.** Beim ersten Mal ging es gut. Das war Glück, kein Mechanismus.

### Gebaut am 13.09.2026 — und warum sie so vorsichtig ist

`core/startsperre.py`, aufgerufen im `__main__`-Block von `app.py`.

**Der Grundsatz ist nicht „sperren", sondern „im Zweifel starten lassen".**
Ein Bot, der fälschlich nicht startet, ist schlimmer als zwei, die kurz
nebeneinander laufen: den zweiten bemerkt man, beim ersten steht der Handel
still, bis jemand hinsieht. Deshalb sperrt sie nur in **einem** Fall und
lässt in allen anderen durch:

| Lage | Was passiert |
|---|---|
| Keine Sperrdatei | starten |
| Datei unlesbar oder halb geschrieben | starten |
| **Prozessnummer lebt nicht mehr** | **starten** — der Absturzfall |
| Nummer lebt, ist aber kein `app.py` | starten — Nummer neu vergeben |
| `psutil` fehlt | starten, mit Hinweis warum |
| **Nummer lebt UND ist ein `app.py`** | **sperren** |

Der dritte Punkt ist der wichtigste. Ohne die Lebendprüfung würde ein
einziger Absturz den nächsten Start **dauerhaft** aussperren — genau davor
warnt `OFFEN.md` Punkt 24, und genau das wäre der Fehler, der schlimmer ist
als das Problem.

**Notausgang:** `python app.py --trotzdem-starten`. Falls sie sich doch
einmal irrt, soll niemand im Quelltext suchen müssen.

**Geprüft mit `startsperre_test.py`, zehn Punkte — davon sieben
Durchlassfälle.** Eine Sperre, die immer sperrt, wäre an sechs von acht
gescheitert; eine, die nie sperrt, an einer. Der Test lief **vor** dem
Einbau in `app.py`: ein Bauteil, das den Start verhindern kann, wird nicht
eingebaut und dann getestet.

**Was sie nicht abdeckt:** zwei Starts in derselben Sekunde. Wer zweimal
gleichzeitig doppelklickt, kann beide durchkommen sehen — dagegen hilft nur
eine Sperre des Betriebssystems. Der gemessene Fall vom 01.09. war ein
Start Minuten später, und den fängt sie.

## 10.10b Was ein Netzausfall wirklich anrichtet

**Angelegt 03.09.2026.** Sven schickte ein Bot-Log voller
Verbindungsfehler und erklärte sie: *„das Internet war aus."* Die Erklärung
stimmte. Die Prüfung danach fand etwas, das damit nichts zu tun hatte.

### Das Erwartbare — und es ist in Ordnung

Ausfall am 02.09., 15:52–18:25 Ortszeit:

| Sammler | Lücke |
|---|---|
| `evaluations` | 60,7 + 91,5 min = **2,5 Stunden** |
| `feature_snapshots` | dieselbe Zeit |
| `markt_historie` | **keine** |

Die Kette ist im Log belegt: kein Netz → die Kursabrufe scheitern
(`[DATA] … api.binance.com/api/v3/klines`, gehäuft genau in den
Ausfallstunden) → keine Entscheidung → keine Zeile. **So soll es sein.**
Ohne Kurse gibt es nichts zu entscheiden, und eine Lücke ist eine ehrliche
Aussage.

### Das Unerwartete — dass eine Tabelle KEINE Lücke hat

`markt_historie` schrieb durchgehend weiter. Ein Blick auf die **Werte**
statt auf ihre Anzahl:

```
Ortszeit    BTC         ETH        SOL
16:02:03    77200.73    2404.15    99.20
16:17:03    77200.73    2404.15    99.20   <== alle drei gleich
16:32:04    77200.73    2404.15    99.20   <== alle drei gleich
17:02:04    77113.73    2396.33    99.08
   ... bis 18:17:07 unverändert
```

Drei Münzen, auf den Cent, sechsmal hintereinander. **Das ist keine
Messung, sondern ein weitergereichter alter Wert.**

Über die ganze Tabelle: **129 von 2.162 Zeilen (6,0 %)** sind exakte
Wiederholungen, verteilt auf **15 von 24 Tagen**, in 21 Serien, die längste
**6 Stunden 45 Minuten**. Und der Schreibabstand dieser Zeilen ist **129 von
129 Mal exakt 15,0 Minuten** — der Schreiber lief im vollkommen normalen
Takt.

**Geprüft und verworfen:** *Könnten es Stundenkerzen sein?* Deren
Schlusskurs bleibt innerhalb einer Stunde konstant, das erklärte bis zu
vier gleiche Zeilen. Es erklärt nicht eine Serie von 6,75 Stunden über jede
Stundengrenze hinweg.

### Warum das schlimmer ist als eine Lücke

> **Eine Lücke ist sichtbar. Ein eingefrorener Wert sieht aus wie eine
> Messung.**

`sammler_pruefen.py` meldet für `markt_historie` seit jeher „OK" — es prüft
Zeilenzahl, Abstand und leere Pflichtfelder, **nicht Wiederholung**. Ein
Prüfwerkzeug, das das Falsche misst, ist schlimmer als keines.

Betroffen ist alles, was auf dieser Tabelle aufbaut: Regime-Auswertung,
Zyklus-Reiter, jede Rückrechnung über Marktphasen.

### Was zu tun ist (Befund 95, nach dem Messfenster)

| | Aufwand | Wirkung |
|---|---|---|
| **minimal** — `sammler_pruefen.py` um eine Wiederholungsprüfung erweitern | klein | macht es *sichtbar*; berührt den Bot nicht, wäre sofort machbar |
| **sauber** — bei fehlgeschlagenem Abruf **keine Zeile schreiben** | mittel | **empfohlen**: ehrliche Lücke statt falscher Messung |
| **strukturell** — Spalte `quelle` (`live` / `letzter_bekannter`) | größer | Wert bleibt, ist aber gekennzeichnet |

### Die saubere Variante — gebaut am 13.09.2026

**Die empfohlene Zeile aus der Tabelle ist jetzt umgesetzt:** Der
Marktschnappschuss schreibt **keine Zeile**, wenn BTC, ETH und SOL exakt
dieselben Werte tragen wie beim letzten Mal.

**Woran man es erkennt, ohne einen Zeitstempel zu haben:** `price_cache`
führt keinen (`data/market_data.py:11`). Es gibt also kein Alter, das man
abfragen könnte. Erkannt wird es stattdessen am Prüfmuster aus `CLAUDE.md`:

> *Werte, die identisch sein dürfen, aber nicht identisch sein sollten.*

Drei Kurse zu zwei Zeitpunkten sind nie auf acht Stellen gleich. Sind sie
es doch, hat sich nichts bewegt — weil nichts abgerufen wurde.

**Was bewusst NICHT angefasst wurde, und das ist der wichtigere Teil:**
`fetch_current_price` (`runtime/exit_monitor.py:657`) nimmt weiterhin den
Cache ohne Altersprüfung. Diese Funktion versorgt auch den **Stop-Loss**.
Ihr bei altem Cache den Preis zu verweigern, wäre eine Verhaltensänderung
mit **Kapitalrisiko**: Der Bot könnte eine Position nicht mehr schließen.

> **Die Ursache sitzt im Handelspfad, die Reparatur nicht.** Das ist eine
> bewusste Abweichung von „Ursache vor Symptom" — hier ist die
> Ursachenbehebung gefährlicher als der Befund. Sie gehört in eine eigene
> Epoche mit eigener Messung, nicht in eine Nachtschicht.

Abgesichert ist deshalb nur das **Aufschreiben**. Die Meldung kommt beim
ersten Mal, beim vierten und dann alle acht Versuche — eine Warnung, die
alle 15 Minuten kommt, liest nach zwei Tagen niemand mehr. Kommen die Kurse
zurück, steht im Protokoll, wie viele Schnappschüsse ausgelassen wurden.

Geprüft mit `reparaturen_test.py`, einschließlich der Gegenprobe, dass
`fetch_current_price` unverändert ist.

### Die Wiederholungsprüfung — gebaut am 03.09.2026

Sven gab die minimale Variante frei. Sie ist **eingebaut** und ändert
nichts am Bot: `sammler_pruefen.py` liest, es schreibt nur einen Bericht.

**Wie sie prüft.** In den Sammler-Beschreibungen steht jetzt ein Feld
`nie_gleich`. Für `markt_historie` sind das `btc_preis`, `eth_preis`,
`sol_preis`. Gemeldet wird nur, wenn **alle** genannten Spalten
**gleichzeitig** mit der Vorzeile übereinstimmen.

> **Warum alle gleichzeitig?** Ein einzelner Kurs kann zufällig zweimal
> denselben Stand haben — drei verschiedene Münzen auf den Cent nicht. Das
> ist das Prüfmuster aus CLAUDE.md Abschnitt 0: *Werte, die identisch sein
> dürfen, aber nicht identisch sein sollten.*

**Wie sie sich meldet:**

```
  Marktlage stuendlich   [PRUEFEN]
    EINGEFROREN      : 59 von 500 Zeilen gleich wie die Vorzeile (11.8 %)
                       laengste Serie 26 Zeilen - alte Werte als frische
                       eingetragen (Befund 95)
```

**Gegengeprüft in beide Richtungen** — der Selbsttest hat drei neue Fälle:

| Fall | Erwartung | Ergebnis |
|---|---|---|
| eingefrorene Werte | **muss** anschlagen | 19 Zeilen gefunden ✓ |
| wechselnde Werte | darf **nicht** anschlagen | schweigt ✓ |
| **nur eine** Spalte gleich | darf **nicht** anschlagen | schweigt ✓ |

Der dritte ist der wichtige. Ein Werkzeug, das bei jeder zufälligen
Übereinstimmung schreit, wird nach zwei Tagen ignoriert.

`python sammler_pruefen.py --selbsttest` — sieben Fälle, alle bestanden.

**Was sie am ersten Tag fand:** 59 von 500 Zeilen (11,8 %), längste Serie
26 Zeilen. Über die ganze Tabelle sind es 129 von 2.162 (6,0 %) — der
höhere Anteil in den letzten 500 Zeilen kommt daher, dass genau diese die
Ausfalltage abdecken.

> **Damit ist der Fehler sichtbar, nicht behoben.** Die Tabelle enthält
> weiter falsche Werte; man sieht jetzt nur, wie viele. Die eigentliche
> Reparatur — bei fehlgeschlagenem Abruf keine Zeile schreiben — berührt
> den Bot und wartet auf das Ende des Messfensters.

### Was der schnellere Anschluss löst — und was nicht

Sven hat Starlink bestellt. Das nimmt die **Ursache** weg, nicht den
**Fehler**: Jede künftige Störung, und sei sie kurz, trägt weiter alte
Werte als frische ein. Ein selteneres Problem ist kein behobenes.

> **Die Lehre:** *„Der Sammler hat keine Lücke"* ist keine Aussage über
> Datenqualität. Er kann lückenlos Unsinn schreiben. Nur der Blick auf die
> **Werte** — nicht auf ihre Anzahl — beantwortet die Frage. Genau dafür
> steht in CLAUDE.md Abschnitt 0 das Prüfmuster: *Werte, die identisch sein
> dürfen, aber nicht identisch sein sollten.*

## 10.11 Den Bot auf einem anderen Rechner aufsetzen

**Angelegt 02.09.2026**, als Sven den Ordner auf einen neuen Rechner zog.
Der Auftrag dafür steht in `PROMPT_NEUER_RECHNER.md`.

### Die vier Fallen — alle nachgemessen

| Falle | Warum sie beißt |
|---|---|
| **Der Python-Platzhalter** | Windows liefert eine Attrappe `python.exe` mit. Tippt man `python`, öffnet sich der Microsoft Store. In geplanten Aufgaben scheitert sie **still**. Abhilfe: Python von python.org, dann die App-Ausführungsaliase abschalten |
| **Fest eingetragene Pfade** | `check_punkt_a.py:9` und `lage_erzeugen.py:229` zeigen auf den alten Benutzernamen. (`schatten_starter.py:45` hat einen Rückfallwert und ist harmlos) |
| **Die Aufgaben-XML** | `aufgabenplanung_backup/*.xml` enthalten die Benutzerkennung (SID) des alten Rechners. Ein Import erzeugt eine Aufgabe, die **aussieht, als liefe sie**, und nichts tut. Sie müssen neu angelegt werden |
| **Die drei Haken** | `.claude/settings.json` verweist absolut auf `.claude/hooks/`. Stimmt der Pfad nicht, brechen sie **still** — dann arbeitet Claude ohne die Projektregeln und ohne Schreibschutz |

### Was einfacher ist, als es aussieht

- **`start_bot.bat` genügt.** `app.py` ruft beim Hochfahren `starten()` aus
  `sammler_pruefen.py:54` selbst auf und bringt damit Schatten-Universum und
  Positionsverlauf mit. Nur die Forschungs-Erfassung hängt an der geplanten
  Aufgabe.
- **Leere Ordner muss niemand suchen.** Alle Laufzeitordner entstehen per
  `os.makedirs(..., exist_ok=True)` — an zwölf Stellen geprüft.

### Die Lehre aus Befund 92

Sven wandte ein: *„er startet eben nicht, weil Bibliotheken — wie kein
einziger cmd-Befehl eingegeben wurde."* Das führte auf eine echte Lücke:
**`requirements.txt` fehlten `reportlab` und `openpyxl`.**

Gemessen wurde mit `ast` über alle 313 Python-Dateien: jeden
Top-Level-Import gesammelt, Standardbibliothek und eigene Dateien
abgezogen, den Rest gegen die Datei gehalten. Zwanzig fremde Module, vier
ohne Eintrag — davon zwei Fehlalarme (`pandas_ta` steht als `pandas-ta`
drin; `optuna` ist gar nicht installiert und in `backtest/hyperopt.py:16-21`
mit `try/except` abgefangen).

Die Datei stammt vom 02.07.2026 und war damals vollständig.
`handbuch_pdf.py` und `zahlenbuch.py` kamen **später**; die Pakete wurden
von Hand nachinstalliert, die Datei nie nachgezogen. Auf einer frischen
Maschine wären ausgerechnet die **PDF-Bücher** nicht baubar gewesen.

> **Eine Abhängigkeitsliste, die einmal stimmte, stimmt nicht dauerhaft.
> Sie altert still** — auf der Maschine, auf der entwickelt wird, merkt es
> niemand, weil dort alles längst installiert ist. **Nur ein fremder
> Rechner ist der ehrliche Prüfstand.**

Prüfzeile, die alle zwanzig auf einmal lädt:

```
python -c "import ccxt, yfinance, websocket, requests, pandas, numpy, pandas_ta, sklearn, xgboost, matplotlib, mplfinance, customtkinter, PIL, praw, bs4, flask, pyngrok, psutil, reportlab, openpyxl; print('alle 20 Pakete geladen')"
```

---

## 10.12 Epoche L8 — Bybit-Einheitsgebühr, und der Autostart nach Anmeldung

**Angelegt 14.10.2026** aus dem Prüfstand (`Desktop\pruefstand`), Freigabe Sven im Chat.

### Epoche `L8_einheitsgebuehr` (Start 14.10.2026 09:51:17 UTC)

**Was Bybit geändert hat.** Seit **05.10.2026 11:00 UTC** gilt bei Bybit EU eine Einheitsgebühr. Für VIP 0 sind das **0,25 %**, ein Maker-Rabatt existiert nicht mehr. Quelle ist die Seite „Trading Fee Structure“ („Last updated on 2026-10-05 13:01:39“), abgerufen am 14.10.2026.

**Was v7 falsch gebucht hat.** Käufe über Warte-Aufträge wurden weiter mit 0,10 % gebucht (`engine.py:486` → `backtest/fees.py:24`). Zwischen 05.10. und 14.10. betraf das 9 Käufe, zusammen rund 3,2 $ zu wenig Gebühr. Die v7-Zahlen seit dem 05.10. sind damit zu günstig.

**Die Änderung.** Es wurde genau ein Wert geändert, der Maker-Satz. Er steht an drei Stellen:

| Stelle | vorher | nachher |
|---|---|---|
| `backtest/fees.py:24` bybit maker | 0,10 | 0,25 |
| `execution/engine.py:393` Rückfall maker | 0,0010 | 0,0025 |
| `core/kosten.py:61` `MAKER_PCT` | 0,10 | 0,25 (damit `K_WARTE_PCT` 0,505) |

Das ist keine Handelsregel, aber der Satz geht über `pnl` in Lernen und Verlustzähler ein. Deshalb gibt es eine Epochengrenze.

**Folge.** Warte-Aufträge sparen bei Bybit EU keine Gebühr mehr. Was bleibt, ist ein womöglich besserer Einstiegskurs, und dem steht die Gegenauslese gegenüber. Ob sich das lohnt, ist eine eigene Messfrage (Markout).

**Bekannt.** Die SOL-Position, die beim Stopp offen war (Kauf 14.10. 08:41 UTC), trägt noch den alten Satz von 0,10 %.

Skript: `pruefstand\patches\patch_v7_bybit_einheitsgebuehr.py`. Vorab-Registrierung: `pruefstand\epochen\L8_v7_einheitsgebuehr.md`.

### Autostart nach Anmeldung

**Anlass.** Windows Update startete den Rechner am 14.10. um 05:32 neu. v6 und v7 blieben aus, und niemand bemerkte es.

**Was jetzt läuft.** Die Windows-Aufgabe **`TI-Bots-Autostart`** startet 2 Minuten nach jeder Anmeldung `pruefstand\autostart\bots_starten.py`. Läuft v7 nicht und liegt keine Datei `v7.BEWUSST_AUS` vor, startet das Skript die vorhandene `start_bot.bat` mit `TI_AUTOSTART=1`.

**Der automatische Klick.** Im Fenster-Modus handelt der Bot erst nach „▶ STARTEN“. Deshalb drückt das Cockpit mit dieser Variable nach 5 s selbst STARTEN (`ui/main_window.py`, Ende von `MainWindow.__init__`, Marke `AUTOSTART-KLICK 14.10.2026`). Ein Doppelklick auf `start_bot.bat` setzt die Variable nicht, dann bleibt alles wie bisher.

**Bot absichtlich aus lassen.** `pruefstand\autostart\BOT_BEWUSST_AUS.bat` doppelklicken.

**Anhalten für Patches.** `pruefstand\autostart\bot_anhalten.py v7 "Grund"`. Das Skript wartet auf die nächste Speicherung, beendet dann den Prozess und prüft, dass `bot_state.json` unverändert ist. Jeder Start und Stopp steht in `pruefstand\autostart\start_stopp.log`.

---

## 10.13 Zielbörse Bitvavo USDC — die Kostenlatte fällt von 0,505 % auf 0,150 %

**Angelegt 14.10.2026** aus dem Prüfstand. **Entscheidung Sven** im Chat: „A Bitvavo, beide Bots umstellen“.

**Warum.** Der Bot verdiente vor Kosten +0,33 % je Runde, die Kosten bei Bybit EU lagen bei 0,50 %. Bitvavo verlangt auf seinen **USDC-Märkten 0,05 % je Seite** (Kategorie B, bitvavo.com/en/fees, geprüft 14.10.). Mit dem gemessenen Schlupf ergibt das **0,15 % je Runde**. Auf denselben 136 Runden aus E7 wären das **+42,66 $ statt −34,85 $** gewesen (berichtigt 14.10., siehe unten).

Bitvavo ist MiCA-zugelassen (AFM, Niederlande) mit Passporting nach Deutschland. Es bietet BTC, ETH und SOL gegen USDC, die Mindestorder liegt bei 5 USDC, und der Kurs weicht weniger als 0,01 % von Binance ab, der Kursquelle des Bots. Die Vorlage mit allen Börsen steht in `pruefstand\berichte\2026-10-14_zielboerse.md`.

**Was geändert wurde (eine Ursache, eine Epochengrenze):**

| Stelle | vorher | nachher |
|---|---|---|
| `backtest/fees.py` | – | neuer Eintrag `bitvavo_usdc` 0,05 / 0,05 |
| `execution/engine.py` `PAPER_GEBUEHR_BOERSE` | "bybit" (0,25 %) | "bitvavo_usdc" (0,05 %) |
| `execution/engine.py` `SPREAD_BP` BTC/ETH/SOL | Bybit-Messung 31.07. | Bitvavo-Stichprobe 14.10., 120 Proben: Median 2,78 / 4,27 / 5,72 bp, p90 4,35 / 5,15 / 8,12 bp |
| `K_BASIS_PCT` | 0,505 | **0,150** |
| Nullsicherung-Puffer (K + 0,045) | 0,55 | **0,195** |
| Nachzieh-Start ((1+K)/(1−1 %) − 1 + 0,05) | 1,57 | **1,21** |
| `config_zielgroessen.json` `kosten_je_runde_pct` | 0,505 | 0,150 |
| `CLAUDE.md` Abschnitt 8 | Bybit EU, 0,505 | Bitvavo USDC, 0,150 (alte Epochen weiter 0,505) |

**Wichtig für jede Auswertung:** Für Runden **vor** dieser Epoche gilt weiter K = 0,505 %. Wer alte und neue Runden mit derselben Latte rechnet, vermischt zwei Kostenwelten.

**Was es nicht beweist.** Auch mit Bitvavo-Kosten liegt der 95-%-Bereich je Runde noch unter null (Block-Bootstrap nach Tagen: −0,33 % bis +0,66 %). Billige Kosten sind die Voraussetzung, damit ein Vorsprung überhaupt sichtbar werden kann. Ob es einen gibt, prüfen die Prüf-Agenten A4 (Einstieg) und A5 (Ausstieg) im Prüfstand.

**Was bewacht werden muss.** Bitvavo kann den Satz ändern, so wie Bybit am 05.10. Der Kosten-Wächter W3 prüft künftig die Gebührenseite und misst die Bitvavo-Spanne rund um die Uhr. Die Stichprobe stammt von einem Nachmittag.

Werkzeuge: `pruefstand\patches\patch_kostenlatte_bitvavo.py`, `pruefstand\skripte\spanne_stichprobe.py`, `pruefstand\skripte\kosten_schatten.py`. Vorab-Registrierung: `pruefstand\epochen\E10_L9_kostenlatte_bitvavo.md`.

**Berichtigung 14.10.2026, 16:30 (nach Prüf-Agent A5).** Die E7-Zahlen dieses Abschnitts waren zuerst falsch. Bei den 21 Verkäufen über ein Verkaufssignal (`execute_approved_trade`) steht im Journal der Betrag **nach** Abzug der Gebühr. Das Prüfstand-Skript zog sie ein zweites Mal ab. Der Profitabilitäts-Bericht vom 14.10. hatte denselben Fehler. Richtig für E7 (136 Runden): **brutto +75,51 $ (+0,33 % je Runde), Gebühren 109,62 $, netto −34,11 $** (nicht −43,13 $). Unter Bitvavo-Kosten inkl. Schlupf wären es **+42,66 $** gewesen (nicht +33,65 $). Die doppelte Kaufgebühr (Befund 42) betraf **alle 136 Runden** (gebucht −88,89 $ = Kasse minus 54,78 $ Kaufgebühren), nicht nur die 115 über `exit_monitor`. Seit E9 ist sie für beide Wege behoben. Die Entscheidung für Bitvavo ändert das nicht.

---

## 10.14 Betriebs-Wächter W5 und der Sammler, der nur den eigenen Ordner zählen darf

**Angelegt 14.10.2026** aus dem Prüfstand.

**W5 Betrieb.** Die Windows-Aufgabe **`TI-Wächter-W5`** (Aufgabenname `TI-Waechter-W5`) läuft alle 5 Minuten und prüft nur lesend (`pruefstand\waechter\w5_betrieb.py`):

- je Bot den Prozess, den Cockpit-Port und das Alter von `bot_state.json`, `system.log`, `telemetrie.db`, `nachlauf.db`, `schatten_universum.db` und, bei offenen Positionen, `positionsverlauf.db`,
- ob die Windows-Aufgaben vorhanden sind,
- den freien Plattenplatz.

Ergebnis: Ampel in `pruefstand\status.json`, Verlauf in `pruefstand\waechter.db`. Telegram gibt es nur beim **Wechsel nach Rot** und bei Erholung, höchstens alle 6 h je Meldung, dazu täglich ab 08:00 ein Lebenszeichen. Das klappt, sobald `pruefstand\TELEGRAM_EINRICHTEN.bat` gelaufen ist.

**Was W5 im ersten Lauf fand.** v7 hielt eine Position, aber `positionsverlauf.db` war seit dem **02.10.2026** nicht mehr geschrieben worden (17.387 Minuten). Ursache in `sammler_pruefen.py`, Funktion `starten()`:

```
if skript.lower() in prozesse and skript not in trotzdem:   # alt
```

`prozesse` sind die Befehlszeilen **aller** Python-Prozesse. Läuft `positionsverlauf.py` aus dem v6-Ordner, hält v7 seinen eigenen für „läuft schon“ und startet ihn nie. Das ist dieselbe Fehlerklasse wie der tote v6-Nachlauf vom 27.09. bis 14.10. Der Tagescheck meldete es („läuft aus FREMDEM Ordner“), aber nur einmal am Tag und ohne Folge.

**Fix (v6 und v7):** Die neue Funktion `_laeuft_hier(skript)` zählt einen Sammler nur, wenn ein Python-Prozess ihn aus **genau diesem Ordner** fährt, über den Skriptpfad oder ersatzweise den Arbeitsordner. Gegenprobe vor dem Einspielen in beide Richtungen: v6 → True (sein Verlauf lief), v7 → False (keiner lief). Das betrifft nur das Datensammeln, nicht den Handel, deshalb gibt es **keine Epoche** (Abschnitt 5: Änderungen, die ausschließlich aufschreiben). Skript: `pruefstand\patches\patch_sammler_eigener_ordner.py`, Marke `SAMMLER EIGENER ORDNER 14.10.2026`.

**Lehre:** Jede Prüfung „läuft Prozess X?“ muss den Ordner prüfen, solange zwei Bot-Ordner nebeneinander laufen. Wer eine neue solche Prüfung schreibt, nimmt `_laeuft_hier()` als Vorlage.

---

## 10.15 Nachzieh-Start aus dem wirksamen Abstand (A5-V1)

**Angelegt 14.10.2026**, Entscheidung Sven („V1 Start aus wirksamem Abstand“). Epoche v6 **E11_trailstart_wirksam** (19:55 UTC), v7 **L10_trailstart_wirksam** (19:56 UTC).

**Befund (Prüf-Agent A5).** Der Nachzieh-Abstand im Bot ist nicht der Config-Wert 1,0 %. Wirksam ist Config × Regime (`risk/regime_profiles.py`, EARLY_BEAR ×0,85) × Leiter-Stufe × Trend-Bonus (×1,3 bei TRENDING_UP). In E7 lösten 40 von 61 Nachzieh-Stopps bei 0,85 % aus, 9 bei 1,274 %. Der Start (`TRAIL_AB_PCT`, zuletzt 1,21) war aber für 1,0 % gerechnet. Im Aufwärtstrend endete deshalb jeder Ausstieg zwischen 1,21 % und 1,52 % Hoch nach Kosten im Minus.

**Änderung.** In `risk/exit_rules.py` gibt es die neue Funktion `trail_start_pct(abstand)`, und `effektiver_trail()` startet erst ab

```
Start = (1 + K/100) / (1 − Abstand/100) − 1  + 0,05      Abstand = wirksamer Abstand, K = K_BASIS_PCT (0,150)
```

| wirksamer Abstand | Start vorher | Start jetzt |
|---|---|---|
| 0,85 % (EARLY_BEAR) | 1,21 | 1,06 |
| 1,0 % | 1,21 | 1,21 |
| 1,3 % (TRENDING_UP) | 1,21 | 1,52 |

`TRAIL_AB_PCT` bleibt als Richtwert für 1,0 % stehen, Auswerte-Skripte lesen ihn. Wird `trail_ab_pct` ausdrücklich übergeben, gilt er wie bisher.

**Geprüft.** Ein Funktionstest mit 7 Fällen ist bestanden, und am Start ergibt sich bei jedem Abstand ein Ausstieg von +0,05 % netto. Skript: `pruefstand\patches\patch_v1_trailstart_wirksam.py`. Vorab-Registrierung: `pruefstand\epochen\E11_L10_trailstart_wirksam.md`. E10–E11 bzw. L9–L10 werden gemeinsam ausgewertet, weil sie dieselbe Kostenlatte haben.

**Was die Prüf-Agenten dazu sagen.** Die Ausstiegsregeln sind insgesamt **kein messbarer Gewinnhebel** (A5: alle Varianten ±10 $ in zwei Monaten). Die Änderung beseitigt einen garantierten Verlust, sie schafft keinen Vorsprung. Laut A4 haben die **Einstiege keinen belegten Vorsprung gegen Zufall**, das Brutto entspricht der Marktdrift. Berichte: `pruefstand\berichte\2026-10-14_ausstieg.md`, `2026-10-14_einstieg.md`.

---

## 10.16 Puffer K + 0,10 und Kauf-Felder am Verkauf (E12 / L11)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung E5: „Puffer 0,25 mit der nächsten Bot-Änderung“. Die Aufzeichnungs-Änderung (Befund 88) fällt unter F8. Epoche v6 **E12_puffer_pflichtfelder**, v7 **L11_puffer_pflichtfelder**, beide ab 09:35:57 UTC.

**Änderung 1, verhaltensändernd: Puffer der Nullsicherung 0,195 → 0,25 %.** In `risk/exit_rules.py` steigt `BREAKEVEN_MARGE_PCT` von 0,045 auf 0,10. Der Puffer ist K + Marge = 0,150 + 0,10.
- **Warum:** Eine Nullsicherung löst im Mittel 0,072 % unter ihrer Linie aus (p90 0,17 %), weil der Bot alle 30 s prüft und der Kurs dazwischen weiterläuft. Mit 0,045 Marge endete sie deshalb im Mittel bei −0,027 % netto. Mit 0,10 sind es etwa +0,028 %.
- **Wirkung:** klein, rund +1 $ in zwei Monaten (Prüf-Agent A5, Vorschlag V2). Die Gegenprüfung A10 sagt: „trägt“.
- Wächter W3 zeigt die Invariante I1 jetzt grün.

**Änderung 2, nur Aufzeichnung: Kauf-Felder am Verkauf (Befund 88).** Diese Felder stehen am Kauf, fehlten aber am Verkauf: `stop_initial`, `trailing_stop_pct`, `decision_id`, `signal_score`, `signal_reasons` und `active_strategy`. Bei wiederhergestellten Positionen fehlten außerdem `entry_score` und `entry_strategie`. Jetzt ergänzt `app.py` `_journal_add()` die fehlenden Felder eines Verkaufs aus dem **ersten Kauf der laufenden Runde**, also aus den Käufen derselben Münze seit ihrem letzten Verkauf. Durch `_journal_add()` laufen alle Schreibwege.
- Vorhandene Werte bleiben unangetastet.
- Die Herkunft steht im neuen Feld `felder_aus_kauf` (Kauf-`_id`, Kaufzeit, Zahl der Käufe).
- Findet sich kein Kauf, zum Beispiel beim zweiten Teil eines Teilverkaufs, bleibt das Feld leer. Es wird nichts erfunden.
- Ein Fehler dabei blockiert nie einen Trade, es gibt nur eine Warnung im Log.
- Wächter W4 prüft die Pflichtfelder ab dieser Epoche.

**Geprüft:**
- Funktionstest: Puffer = 0,25, dazu 7 Fälle für die Feld-Übernahme. Abgedeckt sind: erbt alle Felder, vorhandene Werte bleiben, nach einem Verkauf wird nichts erfunden, andere Münze, zwei Käufe, Fehler wirft nicht, Kauf unberührt.
- Zeilenenden byte-genau erhalten: v6 `app.py` CRLF, `exit_rules.py` LF; v7 umgekehrt.
- Beide Bots wurden mit `bot_anhalten.py` gestoppt (Zustand unverändert, v7 mit 1 offener BTC-Position) und um 09:36 UTC per Autostart wieder gestartet.

Skript: `pruefstand\patches\patch_e12_puffer_pflichtfelder.py`. Vorab-Registrierung: `pruefstand\epochen\E12_L11_puffer_pflichtfelder.md`. Sicherungen: `*.bak_e12_puffer_pflichtfelder_*` neben den Dateien.

**Einordnung.** Diese Änderung beseitigt einen kleinen sicheren Verlust und eine Datenlücke. Einen Vorsprung schafft sie nicht. Laut Svens Entscheidung E1 vom 15.10. läuft der Kurzfrist-Bot auf Papier als Vergleich weiter. Die Hauptarbeit gilt der langsamen Trendregel im Papier-Wettkampf (`pruefstand\epochen\S7_papier_wettkampf.md`).

---

## 10.17 Nachzieh-Marge 0,10, STOPPEN-Knopf und Datenclient (E13 / L12)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung E5b („ja, auch 0,10“) und sein Auftrag „mach weiter mit den Kleinigkeiten“. Epoche v6 **E13_kleinigkeiten** (10:03:04 UTC), v7 **L12_kleinigkeiten** (10:03:05 UTC).

**1 · Nachzieh-Start mit derselben Sicherheit wie der Puffer (verhaltensändernd, v6 und v7).** In `risk/exit_rules.py` steigt `TRAIL_MARGE_PCT` von 0,05 auf 0,10. Der Start eines Nachzieh-Stopps liegt jetzt 0,10 Punkte über der Nulllinie:

| wirksamer Abstand | Start E11/L10 | Start E13/L12 |
|---|---|---|
| 0,85 % (EARLY_BEAR) | 1,06 | 1,11 |
| 1,0 % | 1,21 | 1,26 |
| 1,3 % (Trend) | 1,52 | 1,57 |

Der Grund ist derselbe wie beim Puffer (10.16): Ein Ausstieg löst im Mittel 0,072 % unter seiner Linie aus. Wächter W3 zeigt die Invarianten I1 und I2 jetzt grün.

**2 · STOPPEN-Knopf speichert wieder (nur v6, Befund 72).** `live/watchdog.py` hatte kein `stop()`, `app.py` rief es beim Abschalten trotzdem auf. Der Fehler brach das Abschalten ab, **bevor** der Positionsstand gespeichert wurde. Übernommen ist der Fix aus v7 (L6, 25.09.2026): `stop()` legt einen Riegel um, und `check()` startet danach nichts mehr neu. Für Patches gilt weiter `pruefstand\autostart\bot_anhalten.py`.

**3 · Kein roter Startfehler mehr (nur v6, P0-11).** `data/market_data.py` hat bei jedem Start eine feste Börsentabelle mit `ccxt.coinbasepro` gebaut. Das gibt es seit ccxt 4 nicht mehr. Die Folge war bei jedem Start „Client-Fehler (1. Versuch)“ und danach der Binance-Fallback. Jetzt wird nur die eingestellte Börse geholt, wie in v7 (`ccxt_id` = binance). Es ist also derselbe Client, nur ohne Fehlermeldung. Belegt im Log 10:03 UTC: „Client erstellt: Binance“ ohne Fallback.

**4 · `maker_schatten.py` rechnet mit Bitvavo-Gebühren (v6 und v7).** Bisher stand dort Bybit (Sofort-Auftrag 0,25 / Warte-Auftrag 0,10). Bei Bitvavo USDC kosten beide 0,05 %. Damit hat ein Warte-Auftrag keinen Gebührenvorteil mehr, messbar bleibt nur die halbe Spanne.

**Geprüft:**
- Funktionstest: Start ≥ Nulllinie + 0,10 für drei Abstände, Puffer bleibt 0,25, Bitvavo-Gebühren, Watchdog vor und nach `stop()`, kein `coinbasepro` mehr im Code.
- Zeilenenden byte-genau erhalten.
- Die Sicherung `watchdog.py.bak_e13_…` enthält das Original.
- Bots mit `bot_anhalten.py` gestoppt und per Autostart gestartet (10:04 UTC Ports offen).

Skript: `pruefstand\patches\patch_e13_kleinigkeiten.py`. Vorab-Registrierung: `pruefstand\epochen\E13_L12_kleinigkeiten.md`.

---

## 10.18 Kaufgröße aus dem Handelsgeld, ohne Sparplan (E14 / L13)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung KG1 („Die Kaufgröße wird nur aus dem Handelsgeld berechnet, das Sparplan-Bitcoin zählt nicht mit“) und KG1a („gilt für beide Bots“). Epoche v6 **E14_kaufgroesse_handelsgeld**, v7 **L13_kaufgroesse_handelsgeld** (beide 20:35:04 UTC).

**Was falsch war.** Seit E10-KAPITAL (29.07.) zählt `get_total_capital()` das Sparplan-BTC zum Kapital. Für den Drawdown-Guard und die Anzeige ist das gewollt. Der Block „MANUELLES SIZING“ in `app.py` rechnete daraus aber auch die **Kaufgröße**. Beleg aus v7 am 15.10. um 08:29 UTC:
1. Das Signal rechnete 117,44 $ (50 % von 234,88 $ Handelsgeld).
2. Der Sizing-Block überschrieb den Betrag mit 232,91 $ (50 % von 465,76 $ samt Sparplan).
3. Erst die Bargeld-Grenze kappte ihn auf 223,14 $.

Damit steckten 95 % der Handelskasse in einer einzigen Münze. In v6 war die Kasse nach dem dritten Kauf leer.

**Was jetzt gilt (v6 und v7 gleich).**
- `portfolio/manager.py` hat die neue Funktion `get_trading_capital()` = `get_total_capital()` minus Sparplan, nie unter 0. `get_total_capital()` ist unverändert.
- `app.py` rechnet im Block „MANUELLES SIZING“ die Kaufgröße aus `get_trading_capital()`. Das ist nur diese eine Stelle.
- Drawdown-Guard, Tagesverlust, Tagesstart-Kapital und Anzeige rechnen weiter **mit** Sparplan.
- **Folge:** v7 kauft für 50 % des Handelsgelds (≈ 117 $ statt ≈ 223 $), v6 für 30 % (≈ 122 $ statt ≈ 172 $). Ein Stopp kostet bei v7 rund 3 $ statt 6 $.

**Bewusst nicht geändert.** Der Münz-Deckel des Modus `balanced` in v7 (`max_coin_pct` 35) widerspricht Svens L7-Entscheidung „50 % und eine Position“ (25.09.) und wird weiterhin nicht durchgesetzt. Nach dieser Änderung bleiben Reserve und Deckel ohnehin eingehalten. Der stille Ersatz BTC/USDT in `fetch_snapshot` bleibt ebenfalls, er ist bekannt (`pruefstand\berichte\2026-10-15_kurse_nach_ausfall.md`).

**Geprüft:**
- Selbsttest: Kopie gepatcht, Zeilenenden byte-genau, idempotent, Original unberührt.
- 7 Funktionsfälle, darunter der v7-Log-Wert 117,44 $ und v6 122,44 $. Ohne Sparplan ändert sich nichts, und wirft die Sparplan-Bewertung einen Fehler, gilt das alte Verhalten.
- Sicherungen `*.bak_kg1_kaufgroesse_handelsgeld_20261015_2234*`.

**Betriebshinweis.** Die Bots liefen seit 20:11 Berlin nicht mehr. Ein Update der Claude-App hat sie beendet, weil sie mittags aus einer Claude-Sitzung heraus gestartet worden waren und dadurch an der App hingen. Ab jetzt startet eine Sitzung die Bots nur noch über die Windows-Aufgabe `TI-Bots-Autostart` (`schtasks /run /tn TI-Bots-Autostart`), nie direkt mit `bots_starten.py`.

Skript: `pruefstand\patches\patch_kg1_kaufgroesse_handelsgeld.py`. Vorab-Registrierung: `pruefstand\epochen\E14_L13_kaufgroesse_handelsgeld.md`.

---

## 10.19 Warte-Kauf trägt die Kauf-Felder, Log-Warteschlange gegen Hänger (19.10., ohne neue Epoche)

**Angelegt 19.10.2026.** Auftrag Sven im Chat am 19.10.2026. Eingespielt 19.10.2026 um 21:00 UTC. **Keine neue Epoche** (Svens Entscheidung H1: keine Handels-Epoche), die laufende Epoche bleibt L13. Beide Änderungen sind ohne Handelswirkung.

**1 · Warte-Kauf trägt die Kauf-Felder (Befund 88, Rest).** Seit `warteauftraege.aktiv = true` (12.09.) kauft v7 nur über Warte-Aufträge. Beim Bedienen baute `execution/engine.py` einen **neuen** Kauf-Intent nur aus Strategie, Score, Konfidenz und Begründung. Stopp-Kurs, Nachzieh-Abstand, Ziel, Agent, Risiko-Begründung und die Telemetrie-Kennung gingen verloren. Deshalb hatten alle 22 v7-Käufe `stop_initial = None` und `trailing_stop_pct = None`, und der Verkauf konnte nichts erben (W4 `pflichtfelder` GELB). Die Telemetrie verknüpfte keine Entscheidung mit ihrer Position.
- Jetzt merkt sich der Warte-Auftrag beim Anlegen zusätzlich `stop_loss`, `take_profit`, `trailing_stop_pct`, `agent_id`, `model_version`, `risk_reason` und `evaluation_id`. Nur einfache Werte, die Datei ist JSON, ein unbrauchbarer Wert wird weggelassen.
- Beim Bedienen bekommt der neue Intent diese Werte zurück, im Papier- und im Live-Pfad.
- Diese Felder liest weder die Ausführung noch der Ausstieg. Preis, Menge, Gebühr, Bestand und Order-Kennungen bleiben gleich (Funktionstest 12/12).
- Alt-Aufträge in `warteauftraege.json` von vor dem Patch werden normal bedient, ihre Felder bleiben leer. Die 4 alten Verkäufe und die offene BTC-Position werden nicht nachgetragen.

**2 · Log-Warteschlange gegen Hänger (wie v6 E15).** `ui/main_window.py` rief aus jedem Thread `self.after(0, …)` auf, und `core/logger.py` ruft die Rückrufe vor dem Schreiben in `system.log`. Steht das Fenster, steht jeder Thread, der loggt. v6 hing so vom 16.10. bis 17.10. für 35 h (`pruefstand\berichte\2026-10-17_v6_haenger.md`). v7 hat dieselbe Stelle. Jetzt reiht der Rückruf die Zeile nur in eine Warteschlange ein (Puffer 2000), und der Fenster-Thread holt alle 250 ms bis zu 200 Zeilen ab. Hängt das Fenster, laufen Handel, Stopps, `auto_save` und `system.log` weiter.

**Regel für künftige Änderungen.** Aus Bot-Threads nie Tk aufrufen, das Fenster bekommt Daten nur über Warteschlangen. Unter einer Sperre nie loggen und nie Netz oder Platte anfassen.

**Geprüft:** beide Selbsttests bestanden (Zeilenenden byte-genau: `ui/main_window.py` LF, `execution/engine.py` CRLF). Hänger-Verhaltenstests 3/3, L14-Funktionsfälle 12/12 mit der echten ExecutionEngine. Sicherungen `ui/main_window.py.bak_haenger_log_warteschlange_20261019_230027` und `execution/engine.py.bak_befund_88_wartekauf_17_10_2026_20261019_230028`.

Skripte: `pruefstand\patches\patch_l14_warte_kauf_felder.py`, `pruefstand\patches\patch_haenger_log_warteschlange.py`. Vorab-Registrierungen: `pruefstand\epochen\L14_warte_kauf_felder.md`, `pruefstand\epochen\E15_L14_log_warteschlange.md`.

---

# TEIL 11 — Wie wir arbeiten

**Stand: 25.08.2026.** Dieser Teil handelt nicht vom Bot, sondern von der
Zusammenarbeit an ihm. Er steht im Buch, weil die häufigste Fehlerquelle
dieses Projekts nie im Code lag.

---

## 11.1 Warum Besprochenes untergeht — gemessen, nicht vermutet

Sven fragte am 19.08.: *„Mir fällt auf, dass du vieles nicht
berücksichtigst, was wir in vorherigen Sessions besprochen haben. Liegt das
daran, dass ich kein Übergabeprotokoll erstellt habe?"*

**Nein.** Und die Zahl dazu ist eindeutig.

| | 19.08.2026 | **25.08.2026** |
|---|---:|---:|
| Dokumentation gesamt | 1,06 MB | **1,60 MB** |
| entspricht etwa | 264.593 Token | **401.033 Token** |
| Kontextfenster | 200.000 Token | 200.000 Token |
| **belegt davon** | **132 %** | **201 %** |

**Die Dokumentation passt nicht in eine Sitzung** — nicht annähernd, und der
Abstand wächst. Bevor eine einzige Codezeile gelesen, eine Messung gerechnet
oder eine Antwort geschrieben ist, wäre der Platz doppelt verbraucht.

**Ein weiteres Übergabeprotokoll erhöht diese Zahl, es senkt sie nicht.** Es
gibt bereits fünf. Und `OFFEN.md` sagt selbst, warum sie nicht tragen:

> *„Kein Punkt kommt auf diese Liste, weil er in einer Übergabe stand. Eine
> Übergabe ist eine Momentaufnahme mit Uhrzeit; was danach passiert ist,
> steht nicht drin."*

### Und dieses Buch macht es schlimmer, nicht besser

Ehrlichkeitshalber: Der größte Zuwachs seit dem 19.08. ist **dieses
Handbuch** — plus 313 KB, mehr als alle anderen Dateien zusammen. Der Umbau
lässt es vorübergehend wachsen, weil die fertigen Teile **oben** stehen,
während das alte Material darunter noch liegt, bis es eingeordnet ist.

Es wird wieder schrumpfen. Aber der Punkt bleibt:

> **Das Gedächtnis fehlt nicht — der Griff danach fehlt.** Kein
> Übergabeprotokoll behebt das. Ein weiteres Dokument macht die Zahl größer,
> nicht kleiner.

---

## 11.2 Der Griff nach dem Gedächtnis — drei Helferlein

Weil man die Dokumentation nicht *lesen* kann, muss man sie **durchsuchen**
können. Dafür gibt es drei Werkzeuge, die von selbst laufen:

| Werkzeug | Frage | Dauer |
|---|---|---|
| `python schon_bekannt.py <begriff>` | Steht das schon irgendwo? | ~2 Sekunden |
| `search_session_transcripts("<wort>")` | Wurde das schon besprochen? | ~2 Sekunden |
| `PROJEKT-ENTSCHEIDUNGEN.md` | Ist das bewusst so? | zuerst lesen |

**Warum das funktioniert, wo Vorsätze scheitern:**

> **Eine Regel, die man befolgen muss, wird vergessen. Eine Prüfung, die
> zwei Sekunden dauert, wird gemacht.**

---

## 11.3 Die zwei Pflichtprüfungen vor jedem Befund

**Beide, nicht eine davon.**

```
python schon_bekannt.py <datei.py:zeile>
python schon_bekannt.py <bezeichner>
search_session_transcripts("<stichwort>")     mit ZWEI Begriffen:
                                              Fachwort und Alltagswort
```

Meldet `schon_bekannt` **BEKANNT**, ist es kein neuer Fund, sondern
höchstens eine **Ergänzung** — und muss als solche geschrieben werden, mit
Verweis auf den vorhandenen Abschnitt.

**Warum es diese Pflicht gibt.** Am 19.08. wurde die Gebühren-Doppelbuchung
als neuer Fund gemeldet. Sie stand seit dem 18.08. im Handbuch, mit
derselben Codezeile. Grund war nicht Schlamperei, sondern Bauart: Das
Handbuch hat über 14.000 Zeilen, niemand liest es vor jedem Befund, und die
Überschriften sind erzählerisch — man erkennt sie nur, wenn man den Befund
schon kennt.

**Wie oft es greift, in diesem Buch nachweisbar:** Beim Schreiben von Teil 3
meldete `schon_bekannt` für den Breakeven-Puffer **BEKANNT** — der Punkt
stand schon in ALT 4.53. Aus einem vermeintlichen Fund wurde eine Ergänzung
mit acht frischen Belegen. Beim Kalibrator (Befund 76) meldete es dreimal
**NEU** — dort war es wirklich neu.

### Die zweite Pflicht gilt bei allem

Nicht nur bei Datenbanken. Sven am 19.08.: *„nicht nur das Wissen über
Datenbanken, sondern das Wissen um unser ganzes Projekt."*

**Vor jeder Arbeit an irgendeinem Thema** — bevor eine Datei angelegt, ein
Parameter geändert, etwas als Befund gemeldet oder etwas „repariert" wird.

Findet die Suche etwas, gilt es als **Entscheidung**, nicht als Vorschlag.
Eine bestehende Entscheidung wird nicht umgeworfen, sondern angesprochen.

**Der Anlass:** Am 19.08. wollte ich die Rundgang-Befunde in `forschung.db`
übertragen — es sah nach einer Lücke aus. Sven stoppte mich: *„das haben wir
doch absichtlich so gemacht, glaube ich?"* Er hatte recht. Die Trennung war
eine Entscheidung vom 13.08., wortwörtlich durchsuchbar.

> **Das Wissen war da. Es war durchsuchbar. Ich habe nicht gesucht.**

---

## 11.4 Vier Konfidenzstufen — und keine anderen

| Stufe | Bedeutung |
|---|---|
| **SICHER** | Im Code, Log oder Messwert nachweisbar — **mit Fundstelle**, also Datei und Zeilennummer |
| **WAHRSCHEINLICH** | Plausibel, aber ungeprüft |
| **VERMUTUNG** | Hypothese, kein Beleg |
| **OFFEN** | Information fehlt und **verhindert** eine sichere Entscheidung |

**Keine Prozentzahlen, keine Parallelsysteme.**

**OFFEN ist Pflicht, wo es zutrifft** — es ist die einzige Stufe, die zu
einer Handlung führt: Daten beschaffen.

Und der **Umfang der eigenen Prüfung** wird immer genannt. „Struktur
gesichtet, nicht jede Datei gelesen" ist eine Pflichtangabe, keine Schwäche.

---

## 11.5 Wo was hingehört — es gibt keine sechste Liste

| Datei | Wofür | Regel |
|---|---|---|
| `OFFEN.md` | **Die eine Liste offener Punkte.** Was hier nicht steht, ist nicht offen | Jeder Punkt wird gegen das Verzeichnis geprüft — nie aus einer Übergabe abgeschrieben |
| `GEFUNDENE-PROBLEME.md` | Befunde mit Nummer, dauerhaft. Auch behobene bleiben stehen | Neue bekommen die nächste freie Nummer |
| `BOT-HANDBUCH.md` | **Das Lehrbuch** — nach Gegenstand geordnet, zum Nachschlagen | Vorhandenes fortschreiben, nicht anhängen |
| `ENTWICKLERHANDBUCH.md` | **Die Chronik** — nach Datum | wird über `tickets.txt` gefüllt, nicht von Hand |
| `tickets.txt` | Eingang für die Chronik | `STICHWORT: Text`, wird binnen 30 s eingelesen und geleert |
| `PROJEKT-ENTSCHEIDUNGEN.md` | Was **bewusst** so ist | **Zuerst lesen**, bevor etwas „repariert" wird |
| `LAGE.md` | Was gerade läuft | **Nie von Hand** — `python lage_erzeugen.py` |
| `ZAHLENBUCH.md` / `.pdf` | Die Zahlen mit Quelle und Fallzahl | wird erzeugt |

**Die drei Bücher gibt es je zweimal — Markdown und PDF.** Das Risiko ist
nicht, dass eine Fassung fehlt, sondern dass beide **auseinanderlaufen**:
Wer das PDF liest, während das Markdown drei Abschnitte weiter ist, liest
einen alten Stand, ohne es zu merken. Am 18.08. war die Handbuch-PDF eine
Woche älter als das Markdown.

---

## 11.6 Die Regel, die die Fehlerquote wirklich senkt

Es gibt eine, die mehr bringt als alle anderen zusammen:

> **Keine ausgerechnete Zahl melden, bevor sie gegen einen von Hand
> nachgerechneten Einzelfall geprüft ist.** Nicht gegen Plausibilität, nicht
> gegen eine Anzahl — gegen einen bekannten Wert.

| Was | Wie gegenprüfen |
|---|---|
| **Code** | Vor dem Melden: nachsehen, ob jede benutzte Variable an dieser Stelle existiert. Nie „müsste passen" |
| **Reparaturen** | Danach die **Werte** ansehen, nicht ihre Anzahl. Prüfmuster: *Werte, die identisch sein dürfen, aber nicht identisch sein sollten* |
| **Diagnosen** | Vor „X ist kaputt": nachsehen, ob das Ergebnis von X trotzdem da ist |
| **Zahlen** | Zweite unabhängige Quelle suchen. Stimmen beide überein, gilt der Wert |
| **Fallzahlen** | Immer fragen, wie viele davon **unabhängig** sind |
| **Prüfwerkzeuge** | Gegentest in **beide** Richtungen: meldet es nichts Falsches — **und** findet es den echten Fall? |

**Lieber ein „nicht entscheidbar" melden als eine Zahl, die gut aussieht.**

### Drei Fälle aus diesem Buch, in denen die Regel gegriffen hat

| Beinahe gemeldet | Was die Gegenprobe ergab |
|---|---|
| „Rundenkosten 0,006 %" (Teil 4) | Die Spalte ist ein **Anteil**, kein Prozentwert. Faktor 100 daneben |
| „Das Prüfwerkzeug zählt Übersprungene als gescheitert" (Teil 8) | Falsch. Der gemeldete Ausfall war **echt** |
| „Sechs Abschnitte sauber gelöscht" (Teil 8) | 78 Zeilen statt 178 — 100 Zeilen blieben verwaist stehen. Aufgefallen nur durch Nachzählen |

**Alle drei fielen durch dieselbe Frage auf:** *Passt die Zahl zu einer
zweiten, die ich schon kenne?*

---

## 11.7 Was bewusst so ist — und deshalb nicht repariert wird

| | Warum |
|---|---|
| Die **vier Beobachtungsreiter** sind vom Handelspfad getrennt | Anzeigen heißt nicht handeln (Teil 7) |
| `forschung.db` und `telemetrie.db` sind **abgekoppelt** | keine Verbindung, kein gemeinsames Schema, kein Schreibzugriff in beide Richtungen |
| `brain_performance.json` bleibt aus dem **Cockpit** heraus | V4-verseucht (Teil 5) |
| Grid-Bot, Optimierer, Futures, Mehrbörsen sind **aus** | Entscheidungen, keine Fehler (Teil 1) |
| Der **V4-Referenzbot** läuft mit | eigener Prozess, eigener Zweck |
| Das **KI-Modell** entscheidet nicht | ungemessen (Teil 5) |

> **Was im Code als bewusst stillgelegt markiert ist, ist eine Entscheidung,
> kein Bug.** Solche Stellen werden nicht erneut als Befund gemeldet.

---

## 11.8 Die Dauerregeln in einem Kasten

```
1. Nichts anschliessen ohne Messung.
   Vier fertige Bausteine wurden schon verworfen, weil sie schlechter
   waren als die einfachste Alternative.

2. Die Trivial-Latte immer mit ausweisen.
   "Immer nein sagen" schlaegt viele Modelle. Ein Modell ohne diesen
   Vergleich gilt als UNGEMESSEN, nicht als vielversprechend.

3. Ursache vor Symptom.
   Kein try/except, kein Fallback, kein Umweg, um einen Fehler zu
   verstecken.

4. Kein stilles Scheitern.
   Kein Fehler darf nur geloggt und dann ignoriert werden.

5. Jede Aenderung -> Abschnitt im Handbuch UND Ticket.
   Was nur im Chat steht, ist vergessen, sobald das Fenster weiterlaeuft.

6. Vor jeder Auswertung: python prozess_frische.py
   Sonst wertet man Daten aus, die ein Prozess mit altem Code schrieb.

7. Erst bestehende Aufgaben fertig.
   Neue Wuensche kommen ausdruecklich hinten an.
```

*Früher verstreut in ALT 4.28, 4.31, 4.61, 4.67, 4.68, 4.69, 4.91, 4.106,
4.107, 4.117.*

---

# Schluss

**Dieses Buch war bis zum 25.08.2026 ein Tagebuch.** Es hatte über 120
Abschnitte, nach Datum aneinandergereiht, und 95 davon waren versehentlich
hinter die Überschrift „Anhang" gerutscht, ohne dass es jemandem auffiel.

Jetzt ist es nach **Gegenstand** geordnet. Wer wissen will, wie der
Schattenwächter arbeitet, schlägt an einer Stelle nach und findet dort den
heutigen Stand — nicht die Ablagerung von acht Monaten.

**Was beim Umbau herauskam,** weil jeder Teil aus dem Code und den
Messdaten neu geschrieben wurde statt abgeschrieben:

| | |
|---|---|
| Sieben von acht Zeilenangaben im Rundgang zeigten ins Leere | `app.py` war von 3.580 auf 4.634 Zeilen gewachsen |
| Der V4-Kalibrator rechnet mit Zahlen vom **6. Mai** | Befund 76 |
| Vier Objekte werden beim Start gebaut und nie benutzt | Befund 75 |
| Zwei `.bat` suchen den falschen Prozessnamen | Befund 74 |
| Der Stopp-Knopf verhindert das Speichern | Befund 72 |
| Take-Profit steht auf 0 und feuert nie | Teil 3 |
| Der Trend-Ausstieg kann für zwei von drei Münzen nicht greifen | Teil 3 |
| Das Verhältnis der zwei Kaufwege hat sich umgedreht | Teil 2 |

**Und dreimal hat die Regel gegriffen, bevor eine falsche Zahl im Buch
stand:** die Kostenspalte, die ein Anteil ist und kein Prozentwert; der
„Fehlalarm", der ein echter Ausfall war; und die V4-Bilanz von +1.330 $, die
an drei Handeln eines einzigen Tages hing.

> **Ein Lehrbuch ist nicht fertig, wenn nichts mehr hinzuzufügen ist,
> sondern wenn man es benutzen kann, ohne es ganz gelesen zu haben.**

Wie es fortgeschrieben wird, steht in Teil 11. Die kurze Fassung: Zu einem
Gegenstand, den es schon gibt, wird der vorhandene Abschnitt ergänzt und die
`Stand:`-Zeile aktualisiert. Ein neuer Abschnitt entsteht nur für einen
Gegenstand, den es vorher nicht gab — und er kommt in den Teil, wo er
hingehört, nie ans Dateiende.
