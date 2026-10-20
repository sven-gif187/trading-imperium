# Patches für den 28.08.2026

**Angelegt 19.08.2026.** Diese Änderungen sind **fertig gebaut und
getestet**, aber **bewusst nicht angewendet** — sie berühren das
Handelsverhalten und brauchen eine Epochengrenze.

Das Messfenster `E6`/`E7` läuft bis zum **18.09.2026**.

> **Berichtigt am 26.08.2026.** Hier stand **27.08.** — der Stichtag wurde
> am 21.08. auf den 18.09. verlängert (Entscheidung Sven, Handbuch 4.119).
> Das verbindliche Datum steht in `config_zielgroessen.json`
> (`messfenster_ende`), nicht in dieser Datei.

---

## Vor dem Anwenden — in dieser Reihenfolge

1. **Messfenster auswerten.** Erst wissen, wo man steht, dann ändern.
   ```bash
   python stichtag.py
   ```
2. **Epochengrenze eintragen** in `config_epochs.json` — sonst mischen die
   Auswertungen zwei Regelwerke.
3. **Patch anwenden** (siehe unten).
4. **Bot neu starten.** Ohne Neustart läuft der alte Code weiter.
5. **Kontrollieren:**
   ```bash
   python prozess_frische.py
   ```

---

## Die Patches

| Datei | Befund | Was er tut |
|---|---|---|
| `patch_00a_breakeven_puffer.py` | 0 | hebt `BREAKEVEN_PUFFER_PCT` von 0,35 auf **0,55 %** — die Sperre sicherte bisher einen kleinen **Verlust** statt der Null |
| `patch_45_trailing_schwelle.py` | 45 | hebt `TRAIL_AB_PCT` von 1,2 auf **1,57** — über die Kostenlinie |
| `patch_54_verlustzaehler.py` | 54 | speichert `coin_consecutive_losses`, damit der Cooldown überhaupt greifen kann |
| `patch_63_ath_dynamisch.py` | 63 | holt das Allzeithoch aus den Wochenkerzen statt der verdrahteten 109.114 $ — der Bot hielt den Bärenmarkt für 9 Prozentpunkte flacher als er ist |

**Reihenfolge:** `00a` zuerst, dann `45`. Beide fassen die Ausstiegs-Leiter an
und sollten zusammen gemessen werden — sonst weiß man hinterher nicht, welcher
der beiden gewirkt hat. `54` und `63` sind davon unabhängig.

> **Alle vier zusammen brauchen EINE Epochengrenze, nicht vier.** Wer sie
> einzeln einspielt, zerlegt die Messung in vier Abschnitte mit je zwei bis
> drei Verkäufen — und kann hinterher gar nichts mehr vergleichen.

Jeder Patch kennt drei Aufrufe:

```bash
python patches_nach_27_08/patch_45_trailing_schwelle.py --pruefen
python patches_nach_27_08/patch_45_trailing_schwelle.py --selbsttest
python patches_nach_27_08/patch_45_trailing_schwelle.py --anwenden
```

`--pruefen` und `--selbsttest` ändern **nichts** und sind jederzeit
gefahrlos. Beide legen vor `--anwenden` eine Sicherungskopie an, und
Patch 54 nimmt seine Änderung selbsttätig zurück, wenn die Datei danach
nicht mehr übersetzbar ist.

---

## Patch 45 — Trailing-Schwelle

**Das Problem:** Der Trailing-Stop wird ab +1,2 % scharf, rentabel wird er
erst ab **+1,52 %**. Dazwischen verliert jeder Ausstieg rechnerisch.
Gemessen: **74 von 135** Trailing-Ausstiegen (55 %) enden brutto im Plus
und netto im Minus.

**Die Änderung:** `TRAIL_AB_PCT` wird nicht mehr fest gesetzt, sondern
**aus den Kosten gerechnet**:

```
TRAIL_AB_PCT = (1 + K/100) / (1 - Trail/100) - 1  + 0,05 % Marge
```

Damit wandert die Schwelle mit, wenn sich Gebühren oder Trail-Abstand
ändern. **Der Fehler kann sich nicht wiederholen** — genau das war die
Ursache: Die Leiter war am 29.07. bei 0,10 % Gebühr korrekt gerechnet,
seit dem 13.08. sind es 0,25 %.

**Was er ausdrücklich NICHT tut:** den Trail enger machen. Die Messung an
43 Trades legt nahe, dass enger besser wäre (+1,274 % gegen +0,852 %) —
aber diese Rechnung kennt nur den Höchststand, nicht den Weg dorthin. Sie
ist eine Obergrenze, kein Ergebnis. **Diese Entscheidung gehört hinter
die Auswertung von `positionsverlauf.py`.**

---

## Patch 54 — Verlustzähler

**Das Problem:** Die Cooldown-Sperre nach drei Verlusten hat in 12 Tagen
**0×** gegriffen, obwohl es Serien von 4 (BTC), 3 (SOL) und 3 (ETH) gab.
`coin_consecutive_losses` ist ein reines Speicher-Dict und beginnt bei
jedem Neustart bei null — bei 12 Neustarts in 12 Tagen kann eine Serie
nie zusammenkommen.

**Die Änderung:** Zwei Stellen in `runtime/state_manager.py` — sichern und
zurückladen, genau wie bei den offenen Positionen und der Paper-Balance.

**Was er bewusst NICHT tut:** ändern, *was* als Verlust zählt. Der Zähler
misst weiterhin den gebuchten Dollar-Wert, nicht das Netto-Ergebnis. Nach
der ehrlichen Rechnung wären die Serien 37, 25, 25 statt 4, 3, 3.

Das gehört in denselben Schritt wie die Kostenkorrektur (Befund 42) —
**sonst ändert sich zweimal hintereinander das Verhalten, und keine der
beiden Wirkungen ist mehr zuzuordnen.**

---

## Was hier NICHT liegt

**Befund 51** (die Wiederherstellung zerstörte beim Live-Start jede
Position samt Stop-Loss) wurde am **19.08. bereits repariert**. Sie war
Freeze-sicher, weil `StateRecovery` im Papiermodus nie aufgerufen wird —
`config.json` führt `mode = paper`, der Code ist dort tot.

Datei: `live/state_recovery.py`, Sicherung
`live/state_recovery.py.bak_vor_fix51_20260819`.
Gegentest: `python live/state_recovery.py --selbsttest` (sechs Richtungen).

---

## Wenn ein Patch nicht mehr passt

Beide melden es selbst: Sie prüfen ihre Ankerpunkte, bevor sie etwas
ändern, und brechen ab, wenn die Zieldatei seit dem 19.08. umgebaut
wurde. In dem Fall die Beschreibung oben lesen und von Hand nachziehen —
die Begründung steht vollständig im Kopf der jeweiligen Datei.
