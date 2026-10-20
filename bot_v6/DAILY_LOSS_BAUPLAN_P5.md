# DAILY-LOSS NEUBAU — Bauplan P5

**Stand: 20.07.2026 · Pre-Live-Checkliste Punkt 2**
*Status: Konzept zur Freigabe. Bau erst nach Svens OK.*

---

## 1. Ist-Zustand (Code-Analyse)

**Drei Implementierungen für eine Aufgabe:**

| Datei | Zeilen | Verdrahtet? | Verhalten |
|---|---|---|---|
| `risk/manager.py` (Methoden) | ~80 | **JA** — aber per Flag deaktiviert | Buy-Pause |
| `risk/daily_loss_guard.py` | 205 | nein | Alle Positionen schließen |
| `risk/daily_loss_guardian.py` | 134 | nein | Alle Positionen schließen (Thread) |

**Das Gute:** Die Einbindung in `app.py` (Z. 1631) ist bereits **korrekt gebaut** —
sie pausiert ausschließlich neue Käufe, offene Positionen behalten ihren
Einzel-Stop-Loss, der Exit-Monitor läuft unabhängig weiter. Genau diese Trennung
fehlte am 18.06. Diese Stelle bleibt unverändert.

**Der Schalter:** `is_paused_by_daily_loss()` gibt wegen
`_daily_loss_disabled = True` immer `False` zurück — bewusst für die
Datensammelphase.

## 2. Die fünf Mängel

**M1 — Kein Neustart-Gedächtnis (kritisch).**
`_day_start_capital` wird im Konstruktor gesetzt. Startet der Bot mittags neu,
gilt der *aktuelle* Wert als Tagesstart — der bis dahin aufgelaufene Verlust ist
vergessen. Ein Absturz nach einem schlechten Vormittag hebt den Schutz auf.
Genau der Fall, in dem man ihn braucht.

**M2 — Falsche Messgröße.**
Gemessen wird Gesamtkapital *inklusive unrealisierter* Buchverluste offener
Positionen. Eine Position, die 3% im Minus steht und sich später erholt, zählt
voll gegen das Limit. Das Limit feuert also auf Marktrauschen statt auf
tatsächlich realisierte Verluste — es "sieht" Verluste, die nie eintreten.

**M3 — Zwei Kalender.**
`manager.py` nutzt das **UTC**-Datum, Journal und Terminal-Tab das **lokale**
Datum. Im Sommer liegen dazwischen 2 Stunden: Verkäufe zwischen 00:00 und 02:00
Uhr zählen für den Bot zum Vortag, für dich zu heute. Unterschiedliche Zahlen,
gleiche Wahrheit — Verwirrungsquelle.

**M4 — Zwei geladene Waffen im Schrank.**
`daily_loss_guard.py` und `daily_loss_guardian.py` schließen beide *alle*
Positionen gleichzeitig — der Mechanismus des 18.06. Aktuell ruft sie niemand
auf. Aber sie liegen da, und ein späterer Handgriff könnte sie verdrahten.

**M5 — Doppelte Konfiguration.**
`max_daily_loss_pct` (10.0) und `max_daily_loss_usd` (100.0) existieren parallel,
dazu ein Feld im Settings-Tab. Ein Regler pro Regel — sonst weiß niemand, welcher
gilt.

## 3. Der Neubau: `risk/daily_loss.py`

**Ein Modul, eine Wahrheit.** Kernentscheidungen:

**Messgröße = realisierter Tages-P&L aus dem Journal.**
Bei jeder Prüfung wird `data_store/trades_v5.json` nach den heutigen SELLs
gefiltert und deren P&L summiert. Vorteile: Das Journal ist ohnehin die Wahrheit,
und die Zahl ist **automatisch neustart-fest** — sie wird jedes Mal neu berechnet
statt im RAM gehalten. M1 und M2 sind damit strukturell gelöst, ganz ohne
zusätzliche Zustandsdatei.

**Bezugsgröße = Tagesstart-Equity**, persistiert in
`data_store/daily_loss_state.json` (Datum + Startwert). Fehlt der Eintrag, wird
er beim ersten Tick des Tages angelegt. Damit ist "−10%" auch nach Neustart
dieselbe Zahl.

**Kalender = lokale Zeit**, identisch zu Journal und Terminal-Tab (M3).

**Auslöser:** `realisierter_tagesverlust >= limit_pct% der Tagesstart-Equity`.
Ein Regler: `daily_loss.limit_pct`. Der USD-Wert entfällt (M5).

**Reaktion — unverändert und ausschließlich:**
- Keine neuen Käufe (inkl. DCA-Nachkäufe) bis Mitternacht
- Offene Positionen bleiben, Stops und Trailing laufen weiter
- Telegram-Meldung einmalig
- **Niemals** Zwangsverkauf. Diese Zeile steht als Kommentar im Modul.

**Reset:** automatisch beim ersten Tick nach lokalem Tageswechsel; zusätzlich
`reset()` für die UI.

## 4. Sicherheitsstufen (entscheidend für den Zeitplan)

Das Modul kennt drei Modi über `config.risk.daily_loss.mode`:

| Modus | Verhalten | Wann |
|---|---|---|
| `aus` | Nichts. | Rückfallebene |
| `schatten` | Rechnet und **loggt** ("WÜRDE jetzt pausieren"), greift aber nicht ein | **jetzt** — null Verhaltensänderung, E7-Fenster bleibt sauber |
| `aktiv` | Käufe werden tatsächlich pausiert | **nach** E7-Auswertung, als eigene Epoche |

Der Schattenmodus ist der eigentliche Trick: Wir bekommen ab sofort echte Daten
darüber, **wie oft und bei welchem Schwellwert** das Limit überhaupt gefeuert
hätte — bevor es je eingreift.

## 5. Vorregistrierte Kriterien für die Scharfschaltung

Zur Einordnung: Der schlechteste Tag der laufenden Epoche lag bei **−8,75 $** auf
rund 370 $ Equity, also etwa **−2,4%**. Ein 10%-Limit hätte nie ausgelöst.

Vor der Aktivierung wird festgelegt (Vorschlag):
1. Mindestens **14 Tage Schattenbetrieb** mit protokollierten Tageswerten.
2. Der gewählte Schwellwert hätte im Zeitraum **höchstens 1×** ausgelöst —
   ein Notbremse, die wöchentlich zieht, ist keine Notbremse, sondern eine
   Handbremse.
3. Kein ausgelöster Tag darf ein Tag gewesen sein, der sich danach ins Plus
   gedreht hätte (Prüfung im Nachhinein anhand der Tagesendwerte).
4. Erst dann Modus `aktiv`, Schwellwert schriftlich fixiert.

## 6. Bauschritte

1. `risk/daily_loss.py` neu (~150 Zeilen), Modus `schatten` als Vorgabe
2. `manager.py`: alte Methoden rufen intern das neue Modul auf
   (Rückwärtskompatibilität — `app.py` bleibt unangetastet)
3. Config-Block `risk.daily_loss` mit `mode` und `limit_pct` in `config.json`
4. Terminal-Tab: Zeile "Tagesverlustlimit" zeigt echte Zahlen
   (`−2,4% von 10% · Modus: Schatten`)
5. Die zwei toten Module nach Dynamik-Import-Prüfung ins Archiv (nicht löschen)
6. Nach E7: Auswertung der Schatten-Protokolle → Schwellwert → Modus `aktiv`

## 7. Was dieser Umbau NICHT tut

Er ändert kein Handelsverhalten, solange der Modus auf `schatten` steht.
Er fasst den Exit-Monitor nicht an. Er verkauft nie etwas. Er ist damit
während des laufenden E7-Fensters deploybar.
