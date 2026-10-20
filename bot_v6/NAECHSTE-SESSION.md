> **ÜBERHOLT — nicht mehr als Aufgabenliste benutzen.**
> Diese Datei ist eine **Momentaufnahme** vom Zeitpunkt ihres Schreibens.
> Am selben Tag wurde danach weitergearbeitet; einzelne Punkte darin
> waren schon erledigt, als sie hier hineingeschrieben wurden.
> **Die einzige gültige Liste ist `OFFEN.md`** (`python offen.py`).
> Wer von hier abschreibt, ohne gegen die Commits zu prüfen, trägt
> erledigte Punkte weiter — genau das ist am 18.08.2026 passiert.

> **VERALTET — NEUER: `UEBERGABE-NAECHSTER-CHAT.md` (17.08.2026, 11:05 UTC).**
> Bei Widerspruechen gilt die neuere Datei.

> **NEUER: Am 14.08.2026 wurde `UEBERGABE-MONTAG-17-08.md` geschrieben.**
> Diese Datei hier ist vom 13.08. Bei Widerspruechen gilt die Uebergabe.

# Auftrag für die nächste Sitzung

**Stand 13.08.2026, nachts.** Sven schläft; die Nachtschicht hat Schritt 1
und 2 des Messfenster-Plans abgearbeitet. Diese Datei ist der Startpunkt.

---

## Wo wir stehen

Beschlossen am 13.08.: Vor dem **Zwei-Wochen-Messfenster im Papiermodus**
läuft diese Reihenfolge. Die tragende Regel dabei:

> Änderungen, die nur **aufschreiben**, dürfen jederzeit rein.
> Änderungen, die **Verhalten** ändern, müssen VOR das Fenster und werden
> dann eingefroren — sonst misst man einen Mischmasch aus zwei Bots.

| Schritt | Was | Stand |
|---|---|---|
| 1 | Risiko-Umgehungen schließen | ✅ **fertig** (Punkte 13, 14, 32) |
| 2 | Startabbruch ohne Sicherungsbauteile | ✅ **fertig** (Punkt 34) |
| 3 | Telemetrie-DB erweitern | ✅ **gebaut 13.08.** — 20 Spalten + `feature_snapshots` |
| 4a | **Gewinn-Ratsche im Schattenmodus** | ✅ **gebaut 13.08.** |
| 4b | R-Vielfaches | ✅ **gebaut 13.08.** (statt RR — kein Kursziel) |
| 5 | Einfrieren, zwei Wochen messen | ▶ **hier weitermachen** |

### Vor dem Start des Messfensters abhaken

1. **Neustart** — alles aus dem 13.08. wirkt erst danach.
2. Nach ~10 Minuten Betrieb: `python telemetrie_pruefen.py`
   → jede Spalte außer `take_profit`, `rr_geplant_netto` (bewusst leer),
   `r_multiple_netto` (erst beim Verkauf) und `position_id` (erst nach
   einem Kauf) muss Werte zeigen.
3. `python schatten_leiter_auswertung.py` → muss laufen, Null Auslösungen
   ist am Anfang richtig.
4. Erst dann: **einfrieren**. Ab da keine Änderung mehr am Handelspfad.

### Schritt 4a ist fertig — die Gewinn-Ratsche läuft mit

Sven hatte gefragt, ob bei +20 % Gewinn erst 5 % fallen müssen, bevor
verkauft wird. Antwort: es sind 2,6 bis 3,4 Prozentpunkte, die Leiter
staffelt sich am Höchststand. **Aber die Messung zeigte etwas anderes:**
Beim Median-Trade (Hoch +1,54 %) werden zwei Drittel des Höchstgewinns
zurückgegeben, und bei 150 $ Positionsgröße bringt die Breakeven-Sperre
nach Kosten **vier Cent**.

Deshalb läuft ab dem nächsten Neustart eine zweite Regel **im
Schattenmodus** mit — sie verkauft nichts, sie rechnet nur mit:
`risk/exit_rules_schatten.py`, „gib höchstens 25 % des Höchstgewinns
zurück", mit Untergrenze 0,5 Pp gegen Kursrauschen und Kostenboden.

Wendepunkt: bis etwa +11 % ist sie besser, darüber die heutige Leiter.

- Testfälle: `python test_schatten_leiter.py` (alle bestanden)
- Auswertung: `python schatten_leiter_auswertung.py`
- Handbuch: Teil 4.22

**Nicht vor dem Ende des Messfensters scharf schalten** — sonst misst das
Fenster die neue Regel statt des bestehenden Systems.

## Der nächste Schritt: `SCHRITT3-DATENBANK-PLAN.md`

Dort steht die fertige Spaltenliste — welche Spalte, welcher Typ, welche
Code-Stelle sie füllt, in vier Gruppen nach Aufwand sortiert.

**Vor dem Anfangen brauchen wir drei Entscheidungen von Sven** (stehen am
Ende des Plans):

1. **R-Multiple statt RR-Netto?** Grund: `take_profit` wird im ganzen Code
   **nie gesetzt** — ohne Kursziel ist ein klassisches
   Chance-Risiko-Verhältnis nicht berechenbar. Bei regelbasierten
   Ausstiegen ist das R-Vielfache der übliche Ersatz und braucht kein Ziel.
   *Empfehlung: ja, mit `rr_geplant_netto` als leerer Reservespalte.*
2. **Kursziele einführen?** *Empfehlung: nein* — das wäre eine neue
   Strategie, kein Messwerkzeug.
3. **Umfang der Merkmals-Schnappschüsse?** *Empfehlung: alles, was ohnehin
   berechnet wird.*

## Wichtig für den nächsten Start

- **Die Änderungen von 4.20 sind bereits scharf** (Neustart 03:22 Uhr,
  Port 5051 nachweislich geschlossen).
- **Die Änderungen von 4.21 sind es noch nicht** — Punkte 32 bis 35
  brauchen einen weiteren Neustart.
- **Es ist nichts committet.** Vorschlag für den ersten Befehl morgen:

```bash
git add -A && git commit -m "Punkte 13, 14, 32-35: Risiko-Umgehungen zu, Startabbruch, Dashboard repariert"
```

- **Vor jedem Neustart prüfen, wer Port 5050 hält** — Prozesse zählen
  führt in die Irre, weil der Windows-Startwrapper immer ein
  Elternprozess-Paar erzeugt, das wie zwei Instanzen aussieht:

```bash
powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort 5050 | Select-Object OwningProcess"
```

## Neu seit gestern

- **`MASTERPROMPT.md`** ist ab sofort die verbindliche Arbeitsgrundlage
  (Fassung 2). Neu darin: Abschnitt 0 Bestandsschutz (was nicht angefasst
  wird), Abschnitt 1 Sprach- und Formatregel, Abschnitt 12 bewusst
  zurückgestellt (PostgreSQL/Parquet und Decimal, jeweils mit Begründung
  und Kriterium für eine Neubewertung).
- **`SCHRITT3-DATENBANK-PLAN.md`** — die Spaltenliste, umsetzungsreif.
- **`BOT-HANDBUCH.md` Teil 4.20 und 4.21** — die sechs Änderungen in
  Alltagssprache.

## Offene Punkte aus dieser Nacht (ehrlich vermerkt)

- **Negativtest zum Startabbruch nicht ausgeführt** — er bräuchte einen
  kontrollierten Start mit absichtlich kaputtem Modul. Statisch
  nachgewiesen ist: beide Bauteile sind importierbar (der Bot startet
  also normal), `raise` steht an beiden Stellen, `__main__` fängt ab.
- **Ob das Web-Dashboard nach dem Fix korrekt darstellt, ist ungeprüft.**
  Es hat seit dem ersten Commit nie Daten bekommen — dort können weitere
  Fehler schlummern, die bisher niemand sehen konnte.
- **`_baue_datensatz()` in `core/telemetrie.py:697`** ist nur überflogen,
  nicht Zeile für Zeile gelesen. Nötig vor Schritt 3.

## Weiterhin gültig

- **Ein Punkt nach dem anderen**, nach jedem Fix zeigen, was sich geändert hat.
- **Jede Änderung bekommt einen Handbuch-Eintrag** — Pflicht seit 11.08.
- **Bot und Forschungs-Capture laufen weiter**, nicht anhalten.
- Nach jedem behobenen Punkt Häkchen in `GEFUNDENE-PROBLEME.md`.
- Die vier Cockpit-Reiter bleiben Beobachtungsdeck.

## Nachschlagewerke aus dem Rundgang (fertig, nicht neu schreiben)

- `BOT-HANDBUCH.md` — die vollständige, laienverständliche Erklärung
- `RUNDGANG-CHECKLISTE.md` — welche Datei wann behandelt wurde
- `GEFUNDENE-PROBLEME.md` — die Reparaturliste
