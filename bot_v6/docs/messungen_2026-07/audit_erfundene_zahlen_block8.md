# Audit: Wo erfindet der Bot Zahlen? — und was davon behoben wurde

**UTC:** 2026-08-05T18:20Z · **Skript:** `code/audit_erfundene_zahlen.py`
**Ausgabe:** `ausgaben/audit_erfundene_zahlen_out.txt`
**Durchsucht:** `app.py`, `agents/`, `risk/`, `portfolio/`, `execution/`,
`runtime/`, `features/`, `models/`, `data/`, `core/` — 69 Fundstellen.

> **Der gefährlichste Fund war kein erfundener Indikator, sondern ein
> Risiko-Gate, das bei fehlenden Daten jeden Kauf durchwinkte.**

---

## BEHOBEN 1 — Fail-Open im Exposure-Gate (kritisch)

### Was falsch war

`risk/exposure.py:29` und `:44`:

```python
pct = (new_total / total_equity * 100) if total_equity > 0 else 0
if pct > self.max_coin_pct:
    return {"ok": False, ...}
return {"ok": True, ...}          # <- bei Equity 0 landet man HIER
```

Ist die Equity nicht ermittelbar, wird `pct = 0` gesetzt. Null ist nie
größer als die Grenze — die Funktion gibt **`ok: True`** zurück. Ein
Risiko-Gate, das bei fehlenden Daten **alles erlaubt**.

**Zweite Ebene, `risk/engine.py:135`:** Der Aufrufer überspringt den
gesamten Block bei `total_eq <= 0`. Der E9-Kommentar darüber sagt
wörtlich *„Fehlender Wert = kein Freibrief: 0 → der Block unten wird
übersprungen statt blind durchgewinkt"* — aber das Überspringen **ist**
der Freibrief: es wird nichts geprüft und nichts abgelehnt, der Kauf
läuft ohne Exposure-Kontrolle weiter.

### Was jetzt gilt

Beide Ebenen lehnen ab, statt stillschweigend durchzulassen:

| Fall | vorher | jetzt |
|---|---|---|
| Equity 0, Kauf 999 999 $ | **ok = True** | ok = False, „Exposure nicht prüfbar" |
| Equity `None` | **ok = True** | ok = False |
| Equity 500, Kauf 150 $ (30 %) | ok = True | ok = True |
| Equity 500, Kauf 174 $ (34,8 %) | ok = True | ok = True |
| Equity 500, Kauf 180 $ (36 %) | ok = False | ok = False |

Normalbetrieb unverändert, nur der Datenausfall führt jetzt zu
Ablehnung statt Freigabe. Belegt durch isolierten Funktionstest.

Backups: `risk/exposure.py.bak_failsafe_20260805`,
`risk/engine.py.bak_failsafe_20260805`.

---

## BEHOBEN 2 — RSI 0 und ADX 0 als Messwerte im Journal

`app.py:1265-1276` schrieb bei fehlendem Indikator `0.0` ins
Impact-Journal:

```python
_ij_rsi = float(_ij_ind.get("rsi", 0) or 0)
```

**RSI und ADX können 0 praktisch nicht annehmen** — RSI liegt real
zwischen 10 und 90, ADX zwischen 5 und 60. Eine 0 war deshalb nie eine
Messung, sondern die Signatur eines fehlenden Werts. In jeder Auswertung
sah sie aber wie ein echter Extremwert aus und zog jeden Mittelwert nach
unten.

Jetzt `None` — in SQL und pandas als fehlend erkennbar, statt als
Extremwert mitgerechnet. Gleiches gilt für den MTF-Confluence-Wert.

---

## GEPRÜFT UND IN ORDNUNG — die Mehrheit der Fundstellen

**Die Indikator-Defaults im Signal-Agent sind konservativ gewählt.**
`agents/signal_agent.py:71-97`:

| Default | Wirkung im Score |
|---|---|
| `rsi = 50` | `rsi < 45` falsch → **kein Punkt** |
| `adx = 20` | `adx > 25` falsch → **kein Punkt** |
| `macd = 0, macd_signal = 0` | `macd > macd_sig` falsch → **kein Punkt** |
| `ema20 = 0, ema50 = 0` | `ema20 > 0` falsch → **kein Punkt** |

Jeder Ersatzwert führt dazu, dass die Bedingung **nicht** erfüllt ist.
Ein fehlender Indikator kann also keinen Kaufgrund erzeugen — nur einen
verhindern. Das ist die richtige Richtung und bleibt unverändert.

**Division-Schutz** (`max(price, 1e-9)`, `max(corr_count, 1)`,
`if total_equity > 0 else 0` in reinen Anzeigefunktionen) verhindert
Abstürze, ohne eine Entscheidung zu verfälschen — 29 Fundstellen, alle
unkritisch.

---

## NICHT BEHOBEN, DOKUMENTIERT

| Fundstelle | Befund | Warum nicht angefasst |
|---|---|---|
| `agents/grid_bot.py:92` | `adx = indicators.get("adx", 100)` — ADX 100 ist praktisch unmöglich (Maximum real ~60) | Grid Bot ist abgeschaltet (`grid_enabled=false`), der Wert erreicht keine Entscheidung |
| `models/v4_calibrator.py:108` | Unbekannte Strategie bekommt Gewicht **1.0** — also volles Vertrauen, mehr als jede gemessene Strategie (beste: 0,909) | Seit dem Argmax-Fix vom 04.08. entscheidet das Gewicht die Auswahl nicht mehr |
| `models/rl_feedback.py:39/59/71` | Default 1.0 für unbekannte Strategien | Der RL-Agent schreibt nur, seine Gewichte werden nirgends gelesen |
| `features/regime_detection.py:111` | `total = sum(scores.values()) or 1` | Division-Schutz; bei leerem Score sind alle Anteile 0 |
| `portfolio/rebalancer.py:33` | `cash_pct = … else 100` — bei Equity 0 werden 100 % Cash gemeldet | Rebalancer läuft im Dry-Run (`DISABLED`) |

---

## BEHOBEN 3 — Kennzahlen ohne Mindeststichprobe (Nachtrag)

Zweites Audit: `code/audit_kennzahlen_stichprobe.py`,
Ausgabe `ausgaben/audit_kennzahlen_stichprobe_out.txt`.

### Der Sensei gab Handlungsempfehlungen aus Zufallszahlen

`features/sensei.py:238` löste die Lektion *„Dein Risk/Reward trägt — du
darfst mehr Trades verlieren als gewinnen"* bei `rr >= 1,5` und
`win_rate >= 40` aus. Das kann bei **zwei** abgeschlossenen Trades
zutreffen, einem Gewinn und einem Verlust.

**Schwellen, begründet aus der eigenen Messreihe:** bei n = 30 ist das
95-%-Konfidenzintervall einer Trefferquote rund ±18 Prozentpunkte breit,
bei n = 20 129 waren es ±4.

| Stichprobe | Verhalten jetzt |
|---|---|
| < 10 Trades | Kennzahlen ausweisen, aber als **nicht belastbar** markieren, **keine** Lektion |
| < 30 Trades | Kennzahlen mit Vorbehalt („Richtung möglich, Größe nicht") |
| ≥ 30 Trades | wie bisher |

Speichern und DB-Eintrag laufen unverändert weiter — es entsteht keine
Lücke in der Historie, nur die Empfehlung entfällt.

### Und eine Ebene tiefer dasselbe

Der erste Testlauf nach dem Fix zeigte den Fehler sofort erneut:

```
SCORE-CHECK: Trades mit Score >=7: 4 Stueck, Win-Rate 100%.
```

Vier Trades, als Kennzahl ausgegeben. Die Untergruppen sind zwangsläufig
kleiner als die Gesamtstichprobe und brauchen eine eigene Schwelle
(`MIN_GRUPPE = 20`). Jetzt:

```
SCORE-CHECK: Trades mit Score >=7: 4 Stueck - zu wenige fuer eine
belastbare Quote (Richtwert 20). Roh: 100%, keine Ableitung.
```

Die Zahl bleibt sichtbar — sie verliert nur ihren Anspruch.

Backup: `features/sensei.py.bak_stichprobe_20260805`.

### Was dabei sonst noch auffiel

`features/akademie.py:416-417` (`sum(wins)/len(wins)` ohne
Längenprüfung) und `features/sensei.py:294/302` waren
**Absturzkandidaten** bei leerer Liste. Die Sensei-Stellen sind durch
`if low:` / `if high:` abgesichert, die Akademie-Stellen durch einen
vorgelagerten Filter — beide also latent, nicht akut. Nicht angefasst.

---

## Was das Audit nicht abdeckt

Gesucht wurde nach **Mustern** — `dict.get(key, zahl)`, `or zahl`,
`except: return zahl`, `if x > 0 else zahl`. Nicht gefunden werden
dadurch:

- Werte, die als Konstante am Dateianfang stehen und wie eine Messung
  aussehen
- Zahlen, die über mehrere Funktionen weitergereicht und erst spät zum
  Ersatzwert werden
- Berichte, die eine echte Messung mit zu wenig Stichprobe als Kennzahl
  ausweisen (z. B. Win-Rate aus drei Trades)

Der dritte Punkt ist der wahrscheinlichste Rest — er ist mit
Textsuche nicht auffindbar und bräuchte eine Durchsicht der
Reporting-Pfade.

---

## Sicherheit

Kein Echtgeld, keine Order, keine Secrets, keine Datei gelöscht. Drei
Dateien geändert (`risk/exposure.py`, `risk/engine.py`, `app.py`), für
jede liegt ein Backup daneben. Fail-Safe-Verhalten durch isolierten
Funktionstest belegt, nicht nur behauptet.
