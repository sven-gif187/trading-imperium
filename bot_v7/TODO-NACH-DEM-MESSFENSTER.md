# Was nach dem Messfenster zu tun ist

**Stand 14.08.2026.** Zusammengetragen aus den Sitzungen vom 11.–14.08.
Das Messfenster läuft bis etwa **27.08.2026** (`E6_messfenster`, Beginn
13.08. 13:21 UTC).

**Während des Fensters wird am Handelspfad nichts geändert.** Alles hier
ist Auswertung oder wartet auf die Freigabe danach.

---

## ⚠️ Zuerst prüfen, wenn du wiederkommst

| # | Prüfung | Wie |
|---|---|---|
| 1 | Läuft der Bot noch? | `python lage_erzeugen.py`, dann `LAGE.md` lesen |
| 2 | Sammelt das Schatten-Universum? | `python schatten_universum.py --status` |
| 3 | Entstanden Zahlenbücher? | `ZAHLENBUCH_*.pdf` — sollte je Tag eines geben |
| 4 | Gab es Regel-Alarm? | in `tickets.txt` / `ENTWICKLERHANDBUCH.md` nach „REGEL-SCHALTER VERSTELLT" suchen |
| 5 | Messlücken? | `data_store/system.log` auf Takt-Aussetzer prüfen (Rechner läuft bei 100 % CPU) |

---

## Die fünf Auswertungen, in dieser Reihenfolge

### 1. War der Stop-Loss richtig? *(größter Hebel)*
`python nachlauf.py --status`

68 Stop-Verkäufe kosteten **−187,63 $** — mehr, als alle 169
Trailing-Gewinne einbrachten. Der Nachlauf zeigt, wie der Kurs 1/4/24/48 h
nach jedem Ausstieg stand.

- Erholte sich der Kurs → Stop war zu eng
- Fiel er weiter → Stop war richtig, das Problem sitzt beim **Einstieg**

### 2. Trailing-Schwelle gegen die Kostenschwelle
Reine Rechnung, braucht keine neuen Daten.

Der Trailing-Stop löst bei **0,8 %** aus. Die Mindest-Bruttobewegung, ab
der sich ein Trade lohnt, liegt bei rund **1,37 %**
(Kosten 0,505 % ÷ Trefferquote). **Verdacht: Die Ausstiegsregel realisiert
systematisch unter der Rentabilitätsschwelle.** Prüfen: Median-Gewinn der
Trailing-Exits gegen 1,37 %.

### 3. Ist Score 8 besser als Score 6?
`evaluations` hat jetzt `score` **und** Ergebnis. Netto-EV je Score-Stufe
rechnen, getrennt nach Münze und Regime. Bis das gemessen ist, gilt der
Score **nicht** als Qualitätsmerkmal.

### 4. Welche Münze verdient ihre Reibung?
`python schatten_universum.py --status`

12 Münzen, Kosten je Runde von 0,500 % (BTC) bis 0,901 % (UNI). Nach zwei
Wochen liegen ~4.000 Signale vor. **Erwartung: DOGE ist der beste
Erweiterungskandidat** (1,44 bp Spread, praktisch wie SOL) — nicht UNI,
NEAR, ATOM oder DOT.

### 5. Waren die Blockaden richtig?
Rund 98.000 Ablehnungen. Der Nachlauf misst stichprobenartig, wie sich der
Kurs nach einer Blockade entwickelte. `regime_lernen` macht das bereits
für **eine** Regel — dort steht z. B. „geblockte Käufe wären +1,40 % wert
gewesen, 79 % im Plus".

---

## Offene Punkte aus `GEFUNDENE-PROBLEME.md`

| | Punkt | Kurz |
|---|---|---|
| 🟡 | **17** | `technical` hängt auf 0,5 — Notizbuch läuft, Entscheidung nach dem Fenster |
| ⬜ | **22** | USDT-Rückfall unter MiCA sinnlos (`market_data.py:54`) |
| ⬜ | **1, 2** | `futures_trader`, `multi_exchange`, `exchange_client` — angeschlossen, aber tot |
| ⬜ | **5, 6, 7** | `bottom_detection` nie ausgewertet; Namens-Dopplung `market_regime`; Doppel-Init |
| ⬜ | **8** | Trend-Ausstieg wirkt technisch nur für BTC (`app.py:2082`, `coins[:1]`) |
| ⬜ | **9** | Töpfe Schritt 3: Positionen nach `position_id` statt Symbol |
| ⬜ | **10** | Fünf tote Dateien in `data/` |
| ⬜ | **13** | Manueller Kauf umgeht den Kill-Switch — **Design-Entscheidung nötig** |
| ⬜ | **14** | TradingView-Webhook (stillgelegt am 13.08.) |
| ⬜ | **15, 16** | `hyperopt` ungenutzt; drei verwaiste Dateien in `reports/` |

---

## Größere Vorhaben

### Limit-Orders (größter Execution-Hebel)
Maker 0,10 % statt Taker 0,25 % je Seite → Runde von 0,50 % auf 0,20 %.

**Aber:** Bei Ø 71 $ Positionsgröße sind das 0,21 $ je Trade. Wichtiger
wäre die **Positionsgröße** selbst. Und: Nie pauschal umstellen —
Stop-Loss, Kill-Switch und Notfall-Ausstiege müssen **Market** bleiben.

Vorher zwingend als Schattenrechnung messen: Fill-Rate, Teilfills,
verpasste Bewegung, Netto-Vergleich. Erst ab 100 Fällen entscheiden.

### Hardware
Mini-PC (8 GB, Ubuntu) in etwa einem Monat. **Grund:** Der jetzige Rechner
hat 3,9 GB und läuft bei 100 % CPU. Bot und Sammler brauchen davon nur
71 MB — die Last kommt von Claude Desktop (805 MB) und Firefox. Zum Messen
sollten beide geschlossen sein.

### Reddit
Stillgelegt seit 29.07. (403). Rückweg steht im Kopf von
`data/reddit_sentiment.py`. Falls je zurück: **vier Wochen Notizbuch**,
bevor die Quelle wieder Gewicht bekommt.

### ML-Modell
Bleibt ohne Stimme. Die Trainingsdaten sind repariert, aber bei jeder
kostendeckenden Schwelle bleiben zu wenige Fälle. Urteil:
**nicht entscheidbar**, nicht „taugt nichts".

---

## Verwertung *(eigener Ordner, `Desktop\V6_Verwertung`)*

- Wochenbericht läuft montags 08:00
- **Engpass aller Wege: ein Referenzfall.** Erste Prüfung eines fremden
  Bots verschenken
- Rechtsfrage klären (Anwalt): ab wann gilt die Software als
  Anlageberatung?
- **Datenverkauf erst nach Prüfung der Börsen-Nutzungsbedingungen** —
  Weitergabe ist oft untersagt

---

## Dauerregeln

1. **Nichts anschließen ohne Messung.** Vier fertige Bausteine wurden
   bereits verworfen, weil sie schlechter waren als die einfachste
   Alternative.
2. **Trivial-Latte immer mit ausweisen** — „immer nein sagen" schlägt
   viele Modelle.
3. **Jede Verhaltensänderung braucht eine Epochengrenze.** Sonst sind alle
   Vorher-Nachher-Vergleiche wertlos.
4. **Hintergrund-Jobs:** echter `pythonw`-Pfad, kein ungeschütztes
   `print()`, nach dem Anlegen **prüfen, ob wirklich etwas passiert**.
5. **Jede Änderung** → Eintrag in `BOT-HANDBUCH.md` + Ticket in
   `tickets.txt`.

---

## Nachtrag 18.08.2026 — zwei Punkte ganz nach vorn

### 0a. Die Kaufgebühr wird doppelt abgezogen *(kleiner Aufwand, sofort wirksam)*

`execution/engine.py:401` schreibt `filled_cost = amount` — die
Kaufgebühr ist darin **schon enthalten**, weil `qty = (amount - fee) /
price` gerechnet wird. `app.py:1861` und `app.py:2933` addieren sie
danach ein zweites Mal auf die `cost_basis`.

**Folge:** Jeder abgeschlossene Handel steht um eine Kaufgebühr zu
schlecht in den Büchern — früher 0,10 %, seit dem Messfenster 0,25 %
des Kaufbetrags.

| | gebucht | richtig (Untergrenze) |
|---|---|---|
| 220 auswertbare Verkäufe | −2,99 $ | **+16,72 $** |
| Breakeven-Sperre (10 Auslösungen) | −3,20 $ | −1,37 $ |

Gegenprobe liegt vor: `python gebuehren_gegenprobe.py`.
Begründung und die zwei falschen Anläufe: Handbuch **4.50**.

**Warum nicht sofort:** Der gebuchte Wert geht in `adaptive_sizer`,
`meta_voting`, `risk_engine` und die Tagesverlust-Bremse. Eine
Korrektur ändert Verhalten — also mit **Epochengrenze** nach dem 27.08.

**Reihenfolge-Empfehlung:** zusammen mit dem Breakeven-Puffer (Punkt 0),
weil beide dieselbe Wurzel haben — eine Kostenannahme, die von der
Gebührenkorrektur überholt wurde.

### 0b. Vor jeder Auswertung: `python prozess_frische.py`

Neu seit dem 18.08. Beantwortet in einem Satz, ob ein laufender Prozess
noch mit altem Programmtext arbeitet. Anlass: Die sechs am 17.08.
ergänzten Münzen sammelten einen ganzen Tag lang nichts, weil beide
Sammler seit dem 14.08. durchliefen. Handbuch **4.49**.

Gehört ab sofort in die Liste „Zuerst prüfen, wenn du wiederkommst" —
als Punkt 6.
