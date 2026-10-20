# Prompt zum Kopieren — „Erklär mir meinen Analyse-Reiter"

*Angelegt 31.08.2026. Alles darin ist am Code nachgelesen, nicht aus dem
Gedächtnis geschrieben. Wenn sich der Reiter ändert, gehört diese Datei
mitgeändert — sonst erklärt der andere Claude einen Chart, den es nicht
mehr gibt.*

---

Alles ab hier kopieren:

---

Du hilfst mir, meinen eigenen Chart zu lesen. Ich schicke dir gleich
Bildschirmfotos aus einem Analyse-Reiter, den ich selbst gebaut habe.
Damit du weißt, was du da siehst, hier zuerst der Aufbau.

## Wie ich angesprochen werden möchte

Erklär in **Alltagssprache**, das Fachwort in Klammern dahinter — also
„Sperre nach Verlustserie (Cooldown)", nicht nur „Cooldown". Ich will die
Begriffe lernen, nicht überrollt werden. **Härte gehört ins Urteil, nicht
in die Wortwahl:** Sag mir klar, wenn etwas nichts taugt, aber erklär es
so, dass ich es verstehe.

Kein Lob ohne Befund. Wenn du etwas nicht weißt, sag „das kann ich am Bild
nicht erkennen" — geraten hilft mir nicht.

## Was das Ding ist — und was nicht

Ein **Beobachtungsdeck**. Der Reiter zeichnet und rechnet, aber er **löst
keinen einzigen Kauf und keinen Verkauf aus**. Kein Handelsweg importiert
ihn. Er läuft mit, damit über Wochen belegbar wird, ob seine Signale
überhaupt treffen.

Der Bot dahinter läuft im **Papierhandel** (kein echtes Geld). Zielbörse
wäre Bybit EU, Kosten **0,505 % je Runde** (Kauf und Verkauf zusammen).
Diese Zahl ist wichtig: Sie ist die Latte, die jedes Signal überspringen
muss, bevor es überhaupt etwas wert ist.

## Der Chart

Wählbar sind **BTC/USDC, ETH/USDC, SOL/USDC** und die Zeitrahmen
**15m, 30m, 1h, 4h, 1d, 1w, 1M**.

Geladen werden **300 Kerzen**, angezeigt die letzten **150**. Echte
Kerzen (grün = gestiegen, rot = gefallen), darunter keine Volumenspalten.

### Was jede Linie bedeutet

| Was du siehst | Was es ist |
|---|---|
| **grüne** Linie, durchgezogen | **Unterstützung** — hier hat der Kurs mehrfach nach oben gedreht |
| **rote** Linie, durchgezogen | **Widerstand** — hier hat er mehrfach nach unten gedreht |
| **gestrichelt**, mit `ema2`/`ema5` beschriftet | gleitender Durchschnitt (EMA 50 und 200) als *bewegliche* Zone |
| **kräftige** Farbe | starke Zone (Stärke ≥ 60 %) |
| **blasse** Farbe | schwache Zone |
| zartes Farbband um eine Linie | die Zone ist ein **Band**, kein Strich — sie reicht eine halbe Schwankungsbreite (ATR) nach oben und unten |
| **weiße** Linie mit Preiskästchen | der aktuelle Kurs |
| **`STOP`** und **`ZIEL`**, gepunktet | die Vorschläge des aktuellen Signals |
| **violett**, kräftig | Fibonacci-**Anker**: das Hoch (0) und das Tief (1) der Bewegung |
| **violett**, gestrichelt | Fibonacci-**Rückzugsmarken** (Retracement), 0,236 bis 0,866 |
| **violett**, fein gepunktet | Fibonacci-**Verlängerungen** (Extension), 1,272 bis 2,618 |
| **blau**, zwei durchgezogene Kurven | **Bollinger-Bänder**, oberes und unteres |
| **blau**, gestrichelte Kurve dazwischen | der gleitende Durchschnitt, die Mitte der Bänder |

Rechts am Rand stehen Preismarken. Sie werden **auseinandergeschoben**,
damit sich keine überdeckt — wenn zwei sehr nah beieinander liegen, sind
sie im Bild also etwas weiter auseinander gezeichnet als in Wirklichkeit.

### Wie eine Zone entsteht

1. **Wendepunkte finden.** Ein *Swing-Hoch* ist eine Kerze, deren Hoch
   höher liegt als die **drei davor und die drei danach**.
   **Wichtig:** Ein Swing-Hoch ist erst **drei Kerzen später** erkennbar.
   Vorher weiß niemand, dass es das Hoch war. Der Code führt dafür einen
   Vermerk mit und benutzt eine Zone vor diesem Zeitpunkt **nicht**.
2. **Nahe Punkte zusammenfassen.** Liegen mehrere Wendepunkte innerhalb
   einer Schwankungsbreite (ATR), werden sie **eine** Zone. Ein einzelnes
   Hoch ist noch kein Widerstand — es braucht **mindestens zwei**
   Berührungen.
3. **Stärke vergeben.** `Stärke = Berührungen ÷ 5`, gedeckelt bei 100 %.
   Also: 2× berührt = 40 %, 3× = 60 %, 5× = 100 %.

### Fibonacci — die Regel, auf die es ankommt

Die Anker sind das **höchste Hoch** und das **tiefste Tief** unter den
bestätigten Wendepunkten der angezeigten 150 Kerzen.

> **Die 0 liegt immer am ENDE der Bewegung, die 1 an ihrem Anfang.**
> Welcher Anker das Ende ist, entscheidet die **Zeit**, nicht die Höhe.

| Bewegung | zuletzt | 0 liegt | Stufen laufen |
|---|---|---|---|
| **aufwärts** (Tief zuerst) | das Hoch | am **Hoch** | nach **unten** |
| **abwärts** (Hoch zuerst) | das Tief | am **Tief** | nach **oben** |

Gezeichnet werden **dreizehn** Stufen: die zwei Anker, sieben Rückzüge
(0,236 · 0,382 · 0,5 · 0,618 · **0,707** · 0,786 · **0,866**) und vier
Verlängerungen (1,272 · 1,618 · 2,0 · 2,618).

**Beschriftet sind nur fünf** — die beiden Anker und 0,382 / 0,5 / 0,618.
Alle dreizehn zu beschriften ergäbe eine Textwand.

0,618 heißt **Goldener Schnitt**. 0,707 und 0,866 sind
**Wurzelverhältnisse** (√0,5 und √0,75); die meisten Programme zeigen sie
nicht — sie sind drin, weil ein Bekannter von mir sie benutzt.

### Bollinger-Bänder

Ein gleitender Durchschnitt über **20 Kerzen**, darüber und darunter je
eine Linie im Abstand von **zwei Standardabweichungen** (ein Maß dafür,
wie weit der Kurs zuletzt gestreut hat).

| Was du siehst | Was es bedeutet |
|---|---|
| Bänder **weit** auseinander | unruhiger Markt, große Ausschläge |
| Bänder **eng** beieinander | ruhiger Markt („Enge", engl. *squeeze*) |
| Kurs am **oberen** Band | ungewöhnlich hoch gemessen an der jüngsten Streuung |
| Kurs am **unteren** Band | ungewöhnlich tief |

**Ein Kurs am oberen Band ist KEIN Verkaufssignal.** In einem starken
Aufwärtstrend läuft er tagelang dort entlang. Die Bänder sagen *wie weit
weg vom Durchschnitt*, nicht *wohin als Nächstes*.

## Der Textblock unter dem Chart

```
  Preis 78.172,26   Trend AUFWAERTS   Schwankung (ATR) 412,55

  WIDERSTAENDE (ueber dem Kurs)
        79.480,00   3x beruehrt   Staerke 60%
  UNTERSTUETZUNGEN (unter dem Kurs)
        77.900,00   2x beruehrt   Staerke 40%   (durchbrochen)

  FORMATIONEN
    DOPPELBODEN    BULLISH  Guete 70%  Ziel 79.900,00

  SIGNAL: SUPPORT_BOUNCE
    Guete       72%
    Stop        77.680,00
    Ziel        79.480,00
    Chance/Risiko 2.65  (unter 1.5 lohnt sich nach Kosten selten)
    Begruendung: Kurs in Unterstuetzung 77.900 (2 Beruehrungen) + ...
```

**Zu „(durchbrochen)":** Eine aus Tiefpunkten gebildete Zone, die jetzt
*über* dem Kurs liegt, wurde durchbrochen und wirkt fortan als Widerstand
— und umgekehrt. In der Chartlehre heißt das **Polaritätswechsel**.
Sortiert wird nach der **Lage zum Kurs**, nicht nach dem Typ.

### Die drei Signalarten

| Signal | wann | Güte-Grundwert |
|---|---|---|
| `SUPPORT_BOUNCE` | Kurs steht *in* einer Unterstützungszone | 0,40 + 0,60 × Stärke |
| `BREAKOUT` | Kurs hat einen Widerstand nach oben durchbrochen | 0,35 + 0,55 × Stärke |
| `RETEST` | ein gebrochener Widerstand wird von oben getestet | 0,50 + 0,50 × Stärke |

Danach wird die Güte noch verrechnet: Aufwärtstrend **× 1,2**,
Abwärtstrend **× 0,6**, passende Formation **× 1,15**.

**Stop** = Unterkante der Zone minus eine halbe Schwankungsbreite.
**Ziel** = der nächste Widerstand darüber.
**Chance/Risiko** = (Ziel − Kurs) ÷ (Kurs − Stop).

## Was du unbedingt wissen musst, bevor du das Ding lobst

Ich habe die Signale über Monate messen lassen. Das Ergebnis:

| Signalart | Fälle | Trefferquote | Erwartungswert je Signal **nach Kosten** |
|---|---:|---:|---:|
| SUPPORT_BOUNCE | 86.316 | 69,7 % | **−0,554 %** |
| RETEST | 44.067 | 70,1 % | **−0,349 %** |
| BREAKOUT | 10.726 | 64,3 % | **−0,528 %** |

> **Rund 70 % Trefferquote — und trotzdem verliert jede Signalart Geld.**
> Das ist kein Widerspruch, sondern der wichtigste Satz über diesen
> Reiter: Die Treffer sind zu klein, um die 0,505 % Kosten zu decken.
> Eine hohe Trefferquote ohne den Erwartungswert daneben ist eine Zahl,
> die gut aussieht und nichts sagt.

Zwei bekannte Schwächen, die ich schon gemessen habe:

1. **Das Ziel liegt zu nah.** Es wird immer der *nächste* Widerstand
   genommen — dadurch ist die mögliche Bewegung oft kleiner als die
   Kosten.
2. **Die Gütezahl hat keinen messbaren Wert.** Signale mit hoher Güte
   enden nicht besser als solche mit niedriger. Sie sieht nach Präzision
   aus, ist aber ungeprüft.

**Auch Fibonacci und Bollinger sind in diesem Reiter ungemessen.** Sie
werden gezeichnet, weil ich sie sehen will — ob sie tragen, weiß ich
nicht.

## Deine Aufgabe

Ich schicke dir jetzt Bildschirmfotos. Erklär mir daran:

1. **Was steht da gerade?** Geh das Bild von oben nach unten durch — Kurs,
   Zonen, Fibonacci, Bollinger, dann der Textblock.
2. **Was heißt das in einfachen Worten?** Was sagt mir dieses Bild über
   den Markt?
3. **Wo täusche ich mich leicht?** Welche Linie sieht bedeutsam aus, ist
   es aber nicht — und warum?
4. **Was fehlt im Bild**, um eine Frage zu beantworten, die ich stelle?

**Was du nicht tun sollst:**

- Mir sagen, ob ich kaufen oder verkaufen soll. Ich will **lesen lernen**,
  keine Empfehlung.
- Aus einem einzelnen Bild eine Regel ableiten. Ein Chart ist ein
  Einzelfall.
- Die Trefferquoten schönreden. Sie sind gemessen, und sie sind negativ.

Wenn dir am Bild etwas auffällt, das ich nicht gefragt habe — sag es.
