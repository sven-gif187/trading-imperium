# Profitabilitäts-Bericht v6 — Kurzfassung (14.10.2026)

**Die bearbeitbare Fassung mit Diagrammen und Entscheidungsspalte liegt als
Claude-Dokument:** „Profitabilitäts-Bericht v6",
https://claude.ai/code/artifact/be02d398-cc1c-437f-bb0f-f4dfd9e96b2a

Diese Datei ist die Kurzfassung im Projekt, damit `schon_bekannt.py` und
spätere Sitzungen die Zahlen finden. *Anlass:* Sven am 14.10.: „wir müssten
jetzt mittlerweile ja genug Käufe/Verkäufe haben … wo liegen die Schwächen
und Stärken des Bots?"

> **BERICHTIGUNG 16.10.2026.** Die erste Fassung (14.10.) nannte netto
> −43,13 $ und vor Kosten +66,49 $. Richtig sind **−34,11 $ / +75,51 $**.
> Der Signal-Pfad (`execute_approved_trade`) schreibt den Verkaufsbetrag schon
> NACH Gebühr, `runden.py` zog sie bei den 21 Signal-Verkäufen ein zweites Mal
> ab (9,02 $). Gefunden vom Prüfstand (A5/A10, `Desktop\pruefstand\berichte\2026-10-14_zielboerse.md`
> Abschnitt 0). `runden.py` erkennt seit 16.10. beide Schreibweisen (auch den
> Kaufbetrag ohne Gebühr ab E9). Handprobe: Signal-Verkauf BTC 19.08. 14:54,
> 179,641 − 0,449 = 179,192 $ Erlös, minus 176,236 $ = **+2,956 $**. Ebenfalls
> zurückgenommen: „Vorsprung vor Kosten wahrscheinlich echt" — im
> Block-Bootstrap nach Kalendertagen nicht belegt (−0,18 bis +0,81 %), Einstieg
> nicht besser als Zufall (A4: −0,05 % je Runde). Seit E8–E14 (14./15.10.)
> sind Patches, einfache Kaufgebühr und Bitvavo-Kosten (0,15 %) eingespielt.

## Ergebnis in einem Satz

136 Runden seit 13.08. (alle Epoche E7): **vor Kosten +75,51 $, Gebühren
109,62 $, netto −34,11 $**, während BTC +31 %, ETH +33 % und SOL +42 % stiegen.
Der Vorsprung je Runde (+0,33 %, nicht belegt) ist kleiner als die Kosten je Runde (0,505 %).

## Kernzahlen (SICHER, `data_store/trades_v5.json`, berichtigt 16.10.)

| | |
|---|---|
| Trefferquote nach Kosten | 52,2 % (nötig bei diesem Verhältnis: 58,8 %) |
| Ø Gewinn / Ø Verlust | +1,05 % / −1,50 % |
| Stop-Loss | 33 Runden, −144,48 $ (−2,78 % je Runde) |
| Breakeven-Sperre | 21 Runden, alle im Minus, −7,90 $ |
| Trailing-Stop | 61 Runden, +68,15 $ |
| Verkaufssignale | 21 Runden, alle im Plus, +50,11 $ |
| EMA_TREND als Einstieg | 84 Runden, 23 Stopps, −37,97 $ |
| Monate | Aug +11,10 $ · Sep −22,19 $ · Okt −23,02 $ |
| Im Cockpit gebucht | −88,89 $ (Kaufgebühr doppelt, Befund 42; seit E9 behoben) |
| Eingefangener Anstieg vor/nach Kosten | BTC +11,1/−8,8 % · ETH +19,8/−5,0 % · SOL +15,3/−10,9 % |
| Haltedauer Median | 7,3 h |
| Laufzeit | rund 43 von 61 Tagen (08.–20.09. von Sven abgeschaltet) |

## Fünf Probleme

1. **Kosten** fressen den Vorsprung (+0,33 % brutto gegen 0,505 % je Runde).
2. **Asymmetrie:** Ein Stopp kostet 2,78 %, ein Trailing-Gewinn bringt 0,87 %.
3. **Trend verpasst:** kurze Haltedauer, halbes Kapital im Markt, 18 Tage aus.
4. **Einstieg ohne belegten Vorsprung:** gegen Zufall +0,37 Punkte (Aug),
   −0,46 (Sep), −0,40 (Okt); der Bot kauft nach +1,9 % Anstieg.
5. **Bekannte Fehler ungepatcht:** `risk/exit_rules.py:107` (Puffer 0,35),
   `:108` (Trailing ab 1,2), `execution/engine.py:401` (Gebühr doppelt),
   `agents/cycle_theory.py:28` (ATH 109.114). Ergänzung: fester Stopp 2,5 %
   für alle Münzen — SOL 31 % Stopps gegen ETH 17 % (WAHRSCHEINLICH).

## Gegenprobe (WAHRSCHEINLICH)

Breitere Ausstiege (4/3/3, 8/5/5) auf dieselben Käufe gewinnen nur, wenn der
Markt danach steigt: 13.–31.08. +4,34 % je Runde (8/5/5), September −2,67 %,
Oktober −3,81 % — heutige Regel −0,38 / −0,96 %. Über alle 321 Käufe seit
22.06. +3,5 % gegen −0,3 %, weil der Markt insgesamt stieg. **Keine Lösung,
sondern eine Wette auf den Trend.**

## Lösungsansätze (Entscheidung offen, im Dokument)

1. Vier fertige Patches + Epoche E8 · 2. Warteaufträge (0,505 → 0,355 %,
≈ +33 $ auf 136 Runden) · 3. EMA_TREND herunterwichten · 4. Chance/Risiko-
Filter (OFFEN 81) · 5. Stopp nach ATR je Münze · 6. Trend-Baustein ·
7. Festlegen, ob v6 oder v7 die Korrekturen bekommt. 1+2 zusammen: knapp
über null (−34 + 33 + 8 $, Schätzung). Belegt ins Plus erst mit einem
Einstiegsvorteil.

**Stand 16.10.:** 1 umgesetzt (E8, E9). 2 überholt durch Bitvavo USDC, 0,05 %
je Seite für Markt- und Warteaufträge gleich, K 0,15 % (E10). Mit
Bitvavo-Kosten wären die 136 Runden +42,66 $ gewesen (Prüfstand). 6 läuft
als Papier-Wettkampf bis Mitte Januar 2027 (Svens Entscheidung E1,
`Desktop\pruefstand\entscheidungen.md`). 7 = beide Bots (F6, KG1a).

## Nachrechnen

Aus dem Projektordner, in dieser Reihenfolge (Ergebnisdateien landen in
diesem Ordner):

```
python docs/profitabilitaet_2026-10-14/kurse_holen.py
python docs/profitabilitaet_2026-10-14/runden.py 2026-08-13T13:21:19+00:00
python docs/profitabilitaet_2026-10-14/analyse.py
python docs/profitabilitaet_2026-10-14/analyse2.py
python docs/profitabilitaet_2026-10-14/analyse3b.py
python docs/profitabilitaet_2026-10-14/analyse4.py
python docs/profitabilitaet_2026-10-14/pruef.py
```

Handprobe: BTC 18.08. 09:51 → 19.08. 00:59, netto +0,105 $ (gebucht −0,335 $);
BTC 12.10. 03:17 → 23:39, netto −4,98 $ (gebucht −5,435 $). Unterschied
jeweils genau die Kaufgebühr. Zuordnung Kauf↔Verkauf: letzter offener Kauf
zuerst (LIFO); FIFO scheitert an alten Restbeständen (BTC 0,0008, DOT 68,1).
