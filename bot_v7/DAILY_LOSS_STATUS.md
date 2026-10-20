# DAILY-LOSS-SCHUTZ — Status & Vor-Live-Checkliste

**Stand:** 09.07.2026 | **Audit-Punkt P5 — abgeschlossen**

---

## Kurzfassung

Der Daily-Loss-Schutz war im Audit als "doppelt/gefährlich" markiert. Die Analyse vom 09.07. ergab: **Die real laufende Logik ist bereits sauber.** Das Gefährliche (Zwangsverkauf aller Positionen, der den 18.06.-Crash verursachte) ist längst entfernt. Was blieb, war verwaister Code und ein deaktivierter Schutz für die Datensammel-Phase.

---

## Was WO läuft (die eine Quelle der Wahrheit)

Die aktive Logik liegt in **`portfolio/manager.py`**, verdrahtet über `is_paused_by_daily_loss()` in app.py (~Z. 1692).

Sie ist korrekt gebaut:
- **Echter Tagesreset:** `_update_day_start()` vergleicht das Datum, setzt das Startkapital bei jedem neuen Tag neu.
- **Echter Tagesverlust:** misst `(Tagesstart − aktuell) / Tagesstart`, NICHT den alten Denkfehler "Abstand zum 500$-Startkapital".
- **Nur Kauf-Pause, KEIN Zwangsverkauf:** setzt bei Limit nur das Flag `_daily_loss_active`. Offene Positionen laufen mit ihrem eigenen Stop-Loss weiter. (Der Cascade-Bug vom 18.06. ist raus.)

## Was verwaist war (aufgeräumt)

Zwei Module wurden von NICHTS importiert (verifiziert) und als `.UNUSED` markiert:
- `daily_loss_guard.py`
- `daily_loss_guardian.py`

Kein Code gelöscht — sie bleiben als Referenz. Damit ist die Verwirrung "welches Modul gilt?" beseitigt.

## Aktueller Zustand: DEAKTIVIERT (bewusst)

In `manager.py` steht `_daily_loss_disabled = True` → `is_paused_by_daily_loss()` gibt immer `False` zurück. Das ist **Absicht** für die Datensammel-Phase: Der Bot soll durchlaufen und über alle Marktlagen Daten sammeln. Der Einzel-Stop-Loss pro Position bleibt aktiv — das Risiko ist also gedeckelt.

---

## VOR-LIVE-CHECKLISTE (wenn scharf geschaltet wird)

Diese Schritte NICHT während der Datensammlung ausführen — nur beim Übergang zu Live:

1. **Schalter umlegen:** `_daily_loss_disabled = False` in `portfolio/manager.py` (bzw. das getattr-Default entfernen).
2. **Realistischen Prozentsatz setzen:** `config.risk.max_daily_loss_pct` steht auf **10%** — für einen TAGESverlust zu hoch. Empfehlung: **3–5%** diskutieren und datenbasiert festlegen.
3. **Kauf-Pause-Verdrahtung prüfen:** app.py ~Z.1692 nutzt `is_paused_by_daily_loss()` bereits als reine Kauf-Pause (kein Zwangsverkauf) — nach dem Schärfen einmal im Log verifizieren, dass die Pause greift und sich am nächsten Tag von selbst löst (`_update_day_start`).
4. **Test:** Einen Tagesverlust simulieren (Paper) und prüfen: Pausiert der Bot Käufe? Laufen offene Positionen mit Stop weiter? Reset am nächsten Tag?

---

## Warum das KEIN Zwangsverkauf mehr sein darf (Lehre aus dem 18.06.)

Der schlimmste Verlusttag der Projekthistorie entstand NICHT durch den Markt, sondern durch die alte "alles verkaufen"-Notbremse, die 5 Positionen gleichzeitig schloss — viele davon hätten sich erholt. Deshalb die eiserne Regel: **Daily-Loss = Kauf-Pause, niemals Zwangsverkauf.** Offene Positionen haben ihren eigenen Stop-Loss; der schützt sie einzeln und gezielt.
