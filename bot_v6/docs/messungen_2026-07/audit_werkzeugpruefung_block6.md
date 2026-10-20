# Werkzeugprüfung — sind die Messergebnisse belastbar?

**UTC:** 2026-08-05T06:45Z · **Skript:** `code/messung_werkzeug_ab.py`
**Ausgabe:** `ausgaben/messung_werkzeug_ab_out.txt`
**Status:** ERFOLG. Beide Blocker quantifiziert.
**Kein Trial, keine Hypothese** — reine Werkzeugvalidierung.

> **Kurzfassung: Die Strategie-Urteile stehen. Verzerrt sind
> ausschließlich die absoluten Geldbeträge — also F3 und alle
> Kapitalkurven, nicht die Aussagen über Strategiegüte.**

---

## Blocker 1 — Kapitaltod im Backtest-Harness

**Ursache, exakt:** `backtest/ausstieg_backtest.py:193-195`

```python
betrag = min(self.eigenkapital(preis_map=None) * self.groesse_pct / 100, self.bar)
if betrag < 10:
    return False
```

Mindestordergröße 10 $. Bei `groesse_pct=20` ist damit **unter 50 $
Eigenkapital jeder Einstieg blockiert**. Das ist kein Programmierfehler,
sondern eine bewusste Schwelle — sie verzerrt die Messung aber, sobald das
Kapital schrumpft: ab da misst der Lauf die Kapitalkurve statt die Strategie.

**A/B-Aufbau:** derselbe Datensatz, dieselbe Strategie, dieselbe Slippage,
Gebühr und Mittelung — einzige Änderung ist die Einsatzregel.
`A` = prozentual vom Eigenkapital (Original), `B` = konstant 100 $ je Trade.
`backtest/ausstieg_backtest.py` blieb **unverändert**; `B` ist eine
Subklasse (`LaufKonstant` in `messung_werkzeug_ab.py`).

### Ergebnis

| Kennzahl | J2: A | J2: B | Δ | J1: A | J1: B | Δ |
|---|---|---|---|---|---|---|
| Trades | 1 480 | 937 | **−543** | 783 | 681 | **−102** |
| Trefferquote % | 39,66 | 39,59 | −0,07 | 41,51 | 40,68 | −0,83 |
| R/R | 0,497 | 0,520 | +0,023 | 0,646 | 0,673 | +0,027 |
| **EV in R** | −0,4061 | −0,3980 | **+0,008** | −0,3167 | −0,3194 | **−0,003** |
| Summe $ | −450,56 | −490,01 | −39,45 | −313,44 | −346,31 | −32,87 |
| Gebühren $ | 115,68 | 130,31 | +14,63 | 106,94 | 125,70 | +18,75 |
| Endkapital $ | **49,44** | 9,99 | — | **186,56** | 153,69 | — |
| **abgelehnte Einstiege** | — | **190 127** | — | — | **6 471** | — |

### Was das heißt

**1. Der Kapitaltod ist real und in Jahr 2 massiv.** 190 127 Einstiegs-
versuche scheiterten dort an der Kapitalschwelle, gegen 6 471 in Jahr 1 —
Faktor 29. Das bestätigt den Block-A-Befund unabhängig: J2 endet bei
49,44 $ (die bekannte Kontrollzahl), J1 bei 186,56 $.

**2. Er verzerrt die Strategiegüte trotzdem nicht.** Der EV in R ändert
sich um **+0,008** (J2) und **−0,003** (J1). Die Trefferquote um 0,07 bzw.
0,83 Prozentpunkte. Beides liegt weit unterhalb jeder Schwelle, an der ein
Urteil kippen würde.

**3. Verzerrt sind die absoluten Zahlen.** Trade-Anzahl (−36,7 % in J2),
Summe in Dollar, Gebühren, Endkapital. Alles, was in **F3** (Vergleich
gegen BTC-Halten) und in Kapitalkurven steht, ist betroffen.

**4. Ein unerwarteter Nebenbefund:** Variante B endet *schlechter*
(9,99 $ gegen 49,44 $ in J2). Bei konstant 100 $ ist das Kapital nach fünf
Positionen gebunden; die prozentuale Regel lässt die Einsätze mitschrumpfen
und bleibt dadurch länger handlungsfähig. Der „Kapitaltod" wirkt also
gleichzeitig als unbeabsichtigter Kapitalschutz. Eine Umstellung auf
konstanten Einsatz wäre **keine reine Verbesserung** — sie würde die
Ruinwahrscheinlichkeit erhöhen.

---

## Blocker 2 — 45 Minuten Look-ahead

**Ursache:** `messung_f2_ic.py:57-70` (`zu_1h()`) vergibt den Stundenbeginn
als Zeitstempel, aber den Close am Stundenende als Preis. `rennen()`
startet bei H+15min — drei Viertelstunden werden mitgerennt, bevor der
Signalpreis bekannt ist.

**Datenbasis:** 48 Tests aus `messung_t034b_zwischenstand.jsonl`, Spalte
`q_la` (Sensitivitätslauf mit Start bei H+60min).

| Kennzahl | Wert |
|---|---|
| Deltas negativ | **16 von 48 (33 %)** |
| Mittleres Delta | **−0,125 pp** |
| Größter Betrag | 4,77 pp (BOLLINGER_BOUNCE J1 ±2,5 %/72h) |
| Größte Abweichung nach oben | +1,07 pp (RSI_DIVERGENZ J1) |
| **Tests, bei denen das Urteil kippt** | **0 von 48** |

### Korrektur einer früheren Aussage

Ich hatte berichtet, die Verzerrung sei „**durchweg negativ**". Das war
falsch — ich hatte aus den größten Einzelbeträgen auf die Gesamtrichtung
geschlossen. Tatsächlich sind nur **33 %** der Deltas negativ, und im
Mittel hebt sich der Effekt fast auf (−0,125 pp).

Die Kernaussage bleibt trotzdem gültig, sogar in verschärfter Form:
**kein einziges der 48 Urteile über/unter Kostenschwelle ändert sich**,
wenn man den Look-ahead entfernt.

---

## Gesamturteil zur Werkzeugtauglichkeit

| Frage | Antwort |
|---|---|
| Sind die Strategie-Urteile (EV in R, Trefferquote, über/unter Kostenschwelle) belastbar? | **Ja.** Beide Blocker verschieben sie um Größenordnungen weniger, als für einen Vorzeichenwechsel nötig wäre. |
| Sind die absoluten Dollarzahlen belastbar? | **Nein.** Der Kapitaltod verzerrt Trade-Zahl, Summe und Endkapital erheblich, in J2 um bis zu 36,7 % der Trades. |
| Muss E2/G2 neu gerechnet werden? | **Nein** — für ihre Urteile nicht. |
| Muss F3 neu gerechnet werden? | **Ja**, wenn die Dollar-Differenz gegen BTC-Halten tragend sein soll. |
| Soll der Harness auf konstanten Einsatz umgestellt werden? | **Nicht ohne weitere Prüfung.** Variante B endet in beiden Jahren schlechter; die prozentuale Regel schützt vor Ruin. |

---

## Offen

1. **F3 neu rechnen** mit kapitalunabhängiger Einsatzregel, falls die
   Dollar-Aussage gegen BTC-Halten gebraucht wird.
2. **`get_total_capital()`** liefert je nach Aufrufkontext unterschiedliche
   Werte (`portfolio/manager.py`) — in `app.py` umgangen, in der Sache
   ungeklärt.
3. **Drei stille Prozesstode** — Ursache ohne Windows-Ereignisprotokoll
   weiterhin NICHT ENTSCHEIDBAR.

---

## Sicherheit

`backtest/ausstieg_backtest.py` unverändert. Kein Echtgeld, keine Order,
keine Secrets, keine Datei gelöscht, Daten ausschließlich gelesen.
