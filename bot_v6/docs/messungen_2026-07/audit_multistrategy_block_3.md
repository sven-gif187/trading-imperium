# Audit Multi-Strategy — Block 3: Diff für die drei Logzeilen

**Lokal:** 04.08.2026 06:55 (MESZ) · **UTC:** 2026-08-04T04:55Z
**Status:** ERFOLG — Diff ausformuliert. **NICHT eingebaut.**
Datei unverändert: `risk/engine.py`, 15 466 B, mtime 2026-07-29T17:57:17.

---

## Ausgangslage

Drei Frühabbrüche in `RiskEngine.check()` setzen `risk_approved = False`
und kehren zurück, ohne eine Zeile zu schreiben. Der Genehmigungspfad für
SELL loggt dagegen (`:85`). Deshalb stehen im Log ausschließlich
`APPROVED SELL`-Zeilen und **null** BUY-Zeilen — weder genehmigt noch
abgelehnt.

**Zur Laufzeit bestätigt** (`data_store/system.log`, 2026-08-03T04:39:05
bis 2026-08-04T04:40:27, also 24 Stunden, 102 332 Zeilen):

| Zählung | Wert |
|---|---|
| `[SIGNAL] … -> BUY` | **31 124** |
| `[SIGNAL] … SELL` | 5 989 |
| `[RISK]` gesamt | 2 995 |
| `[RISK]` mit `BUY` | **0** |
| Zeilen mit `Sleep-Mode`/`Schlafmodus` | 7 598 |
| Zeilen mit `Kill-Switch` | **0** |

Der Befund aus der Übergabe reproduziert sich mit frischen Zahlen und in
schärferer Form: 31 124 BUY-Signale, 0 BUY-Zeilen in der Risk-Engine.

---

## Der Diff

Kein Verhaltenswechsel. Keine neue Bedingung, kein neuer Import — `log`
ist bereits über `risk/engine.py:9` (`from core.logger import log`)
vorhanden, und `log.risk` wird in `:85` bereits im selben Format benutzt.
Jede neue Zeile steht **unmittelbar vor** dem bestehenden `return intent`
und ändert weder Status, noch Grund, noch Rückgabewert.

```diff
--- a/risk/engine.py
+++ b/risk/engine.py
@@ -88,6 +88,7 @@ class RiskEngine:
         if intent.side == Side.BUY and self.is_in_sleep_mode():
             remaining = int(self.sleep_mode_until - time.time())
             intent.status = IntentStatus.REJECTED
             intent.risk_reason = f"Schlafmodus aktiv (noch {remaining}s)"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED BUY {intent.symbol}: {intent.risk_reason}")
             return intent
 
         reasons = []
@@ -97,12 +98,14 @@ class RiskEngine:
         # 1. Kill-Switch
         if self.kill_switch.active:
             intent.status = IntentStatus.REJECTED
             intent.risk_reason = f"Kill-Switch: {self.kill_switch.trigger_reason}"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
             return intent
 
         if self.kill_switch.check():
             intent.status = IntentStatus.REJECTED
             intent.risk_reason = f"Kill-Switch ausgeloest: {self.kill_switch.trigger_reason}"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
             return intent
 
         # 2. Drawdown-Guard
```

**Warum Zeile 1 `BUY` fest schreibt, die anderen beiden nicht:** Der
Schlafmodus-Zweig ist durch `intent.side == Side.BUY` bereits auf BUY
eingegrenzt. Die beiden Kill-Switch-Zweige liegen **hinter** dem
SELL-Frühausstieg (`:81-86`), erreichen also faktisch nur BUY — aber das
ist eine Folgerung aus der Reihenfolge, keine Bedingung im Code. Deshalb
dort `intent.side.value` statt eines festen Literals. **Geprüft:**
`core/events.py:15-18` definiert `Side` als `Enum` mit `BUY = "BUY"`,
`SELL = "SELL"`, `HOLD = "HOLD"` — `.value` liefert also den erwarteten
String. Kein Ersatzausdruck nötig.

---

## Auswirkung auf das Logvolumen

Hochrechnung aus dem realen 24-Stunden-Fenster oben, nicht geschätzt:

| Größe | Wert |
|---|---|
| `system.log` heute | 12 512 389 B = **11,93 MB** / 24 h |
| mittlere Zeilenlänge | 122 B |
| neue Zeile, gemessen am Format | ~95 B |
| BUY-Intents in 24 h (Obergrenze) | **31 124** |
| Zuwachs | **+2,81 MB / 24 h** |
| neues Volumen | 14,74 MB / 24 h = **+23,5 %** |

**Verteilung auf die drei Zeilen:** Zeile 1 (Schlafmodus) trägt praktisch
alles — 7 598 Sleep-Mode-Meldungen in 24 h zeigen, dass der Schlafmodus
über weite Strecken aktiv war. Die Zeilen 2 und 3 (Kill-Switch) tragen im
Beobachtungszeitraum **null**: `Kill-Switch` kommt im gesamten Log nicht
ein einziges Mal vor. Sie kosten nichts und sind genau dann wertvoll, wenn
der Fall eintritt.

**Nebenwirkung Logrotation:** `core/logger.py` rotiert ab 20 MB mit genau
einer Vorgängerdatei. Heute wird diese Grenze nach rund 1,7 Tagen
erreicht, mit den neuen Zeilen nach rund 1,4 Tagen. Die Aufbewahrungszeit
der Historie sinkt also um etwa ein Fünftel — bei einem Bot, dessen
Prozess in den letzten 36 Stunden zweimal still gestorben ist (Block 2.7),
ist das kein Nebendetail.

**Wenn dir das zu viel ist**, gibt es eine belegbare Alternative, die ich
aber nicht zum Diff gemacht habe, weil du drei Zeilen bestellt hast:
dieselbe Meldung nur beim **Wechsel** des Ablehnungsgrundes schreiben
(ein `self._last_reject_reason`-Vergleich). Das reduziert den Zuwachs auf
wenige Zeilen pro Schlafmodus-Phase, kostet aber die Zählbarkeit — genau
die Eigenschaft, wegen der du die Zeilen willst.

---

## Regressionsrisiko

**Niedrig, mit einer benannten Ausnahme.**

| Aspekt | Bewertung |
|---|---|
| Steuerfluss | unverändert — jede Zeile steht vor einem bestehenden `return`, keine Bedingung berührt |
| Rückgabewerte | unverändert — `intent` wird nicht modifiziert |
| Imports | keine neuen; `log` ist über `:9` vorhanden |
| Nebenwirkungen von `log.risk` | schreibt in `_log_memory`, ruft UI-Callbacks, schreibt in Datei (`core/logger.py:36-49`) |
| Performance | 31 124 zusätzliche Aufrufe/Tag ≈ 0,36/s — im Rahmen der bestehenden 2 995 `[RISK]`-Zeilen unkritisch |

**Die Ausnahme:** `_emit` (`core/logger.py:36-49`) benachrichtigt **alle
registrierten UI-Callbacks** unter dem gemeinsamen `self._lock`.
`RiskEngine.check()` läuft im Decision-Cycle. Rund 31 000 zusätzliche
`_emit`-Aufrufe pro Tag laufen damit zusätzlich durch dieses Lock und
durch jeden UI-Callback. **Nachgezählt:** Es ist genau **ein** Callback
registriert (`ui/main_window.py:2977`), und der marshallt über
`self.after(0, …)` in den Tk-Thread, arbeitet also nicht selbst im
Decision-Cycle. Bei 31 124 zusätzlichen Aufrufen pro Tag sind das 0,36
Ereignisse pro Sekunde in der Tk-Event-Queue — unkritisch. Das Risiko
reduziert sich damit auf das Lock in `_emit`, das der bestehende
`APPROVED SELL`-Log in `:85` ohnehin schon nimmt.

**Was der Fix NICHT tut:** Er behebt den Multi-Strategy-Bug nicht. Er
macht die Ablehnung sichtbar, mehr nicht. Ein Logging-only-Fix ist kein
Kausalitätsnachweis — er liefert nur den Beleg, welcher der drei Zweige
wie oft greift. Genau das ist heute unbekannt.

---

## Rollback

Ein Schritt, kein Zustand zu bereinigen:

1. `copy risk\engine.py risk\engine.py.bak_logzeilen` **vor** dem Einbau.
2. Rollback: die drei eingefügten Zeilen entfernen oder die `.bak`-Datei
   zurückkopieren.
3. app.py neu starten, damit das Modul neu geladen wird.

Es entsteht keine Migration, kein Schema, kein persistenter Zustand.
Bereits geschriebene Logzeilen bleiben stehen und stören nicht.

---

## Tests vor dem Einbau

| ID | Prüfung | Erwartung |
|---|---|---|
| L1 | `python -c "from core.events import Side; print(Side.BUY.value)"` | liefert einen String — sonst `{intent.side}` verwenden |
| L2 | `python -m py_compile risk/engine.py` | fehlerfrei |
| L3 | Intent mit `side=BUY` bei aktivem Schlafmodus durch `check()` | genau eine `[RISK] REJECTED BUY …`-Zeile, `risk_approved is False` |
| L4 | Intent mit `side=SELL` | unverändert genau eine `APPROVED SELL`-Zeile |
| L5 | 24 h nach Einbau: `grep -c "REJECTED BUY" system.log` gegen `grep -c "\-> BUY"` | Verhältnis zeigt, welcher Zweig greift |

---

## Freigabebedarf

`risk/` steht auf deiner Sperrliste. **Nichts eingebaut, nichts
vorbereitet, keine `.bak` angelegt.** Der Diff wartet auf deine
Entscheidung.
