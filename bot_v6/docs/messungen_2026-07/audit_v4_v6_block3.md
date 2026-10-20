# Block 3 — Sechs Freigaben, plus 3.7 und Block 4

**Lokal:** 04.08.2026 21:50 (MESZ) · **UTC:** 2026-08-04T19:50Z
**Status:** 6 von 6 Freigaben umgesetzt und verifiziert. 3.7 **NICHT
ENTSCHEIDBAR** (Werkzeug liefert nichts). Block 4 eingetragen, mit zwei
gemeldeten ID-Kollisionen.

---

## 3.1 Drei log.risk-Zeilen in `risk/engine.py` — UMGESETZT

**Backup:** `risk/engine.py.bak_logzeilen_20260804` (15 466 B)

```diff
--- a/risk/engine.py
+++ b/risk/engine.py
@@ -92,6 +92,7 @@
             intent.risk_reason = f"Schlafmodus aktiv (noch {remaining}s)"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED BUY {intent.symbol}: {intent.risk_reason}")
             return intent
@@ -101,6 +103,7 @@
             intent.risk_reason = f"Kill-Switch: {self.kill_switch.trigger_reason}"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
             return intent
@@ -107,6 +110,7 @@
             intent.risk_reason = f"Kill-Switch ausgeloest: {self.kill_switch.trigger_reason}"
             intent.risk_approved = False
+            log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
             return intent
```

Kein neuer Import (`log` über `:9`), kein Steuerfluss berührt,
`Side` ist ein Enum mit `.value` (`core/events.py:15-18`).

**Verifikation:**
- `python -m py_compile risk/engine.py` fehlerfrei.
- `diff` gegen das Backup zeigt genau drei eingefügte Zeilen (92a93,
  101a103, 107a110).
- AST-Prüfung über `check()`: **4** `return`-Anweisungen mit unmittelbar
  vorangehendem `log.risk` — Zeile 86 (bestehend, `APPROVED SELL`),
  94, 104, 111 (neu, `REJECTED`). Das ist genau das Soll.

**Was ich NICHT verifizieren konnte, und warum:** Der Nachweis, dass
BUY-Ablehnungen jetzt tatsächlich im Log erscheinen, verlangt, dass
`risk/engine.py` neu geladen wird. app.py läuft seit 04.08. 00:45:35 UTC
als PID 9300 und importiert das Modul beim Start. **Ein Neustart ist
untersagt.** Der Laufzeitnachweis ist deshalb erst nach dem nächsten
regulären Start möglich. Prüfbefehl für dann:

```bash
grep -c "REJECTED BUY" data_store/system.log
```

Erwartung nach 24 Stunden: einige tausend Zeilen, weit überwiegend mit
Grund `Schlafmodus aktiv` (im 24-h-Fenster 03./04.08. standen 7 598
Sleep-Mode-Zeilen gegen **0** Kill-Switch-Zeilen).

**Rollback:** `copy risk\engine.py.bak_logzeilen_20260804 risk\engine.py`,
dann Neustart. Kein persistenter Zustand.

---

## 3.2 `cockpit_server.py:112` — UMGESETZT

**Backup:** `cockpit_server.py.bak_e7fix_20260804` (21 197 B)

```diff
-    E7  = [t for t in sells if dt(t) >= datetime(2026, 7, 17, tzinfo=timezone.utc)]
+    # [FIX 04.08.] E7 wurde am 17.07.2026 um 12:00 UTC deployed, nicht 00:00.
+    # Quelle: e7_auswertung.py:36 (E7_DEPLOY = "2026-07-17T12").
+    E7  = [t for t in sells if dt(t) >= datetime(2026, 7, 17, 12, tzinfo=timezone.utc)]
```

`py_compile` fehlerfrei, `diff` zeigt genau diese Änderung. Reine
Auswertungsdatei, kein Entscheidungspfad.
**Rollback:** Backup zurückkopieren.

**Nicht mitgefixt:** `E61` (`:111`) verwendet dieselbe Konstruktion für
den 14.07. Ob E6.1 um 00:00 UTC deployed wurde, ist ohne Deploy-Zeitpunkt
aus dem Register **NICHT ENTSCHEIDBAR** — deshalb unangetastet.

---

## 3.3 `ENTWICKLERHANDBUCH.md` — REPARIERT

**Skript:** `docs/messungen_2026-07/code/audit_handbuch_reparatur.py`
(Dry-Run als Vorgabe, geschrieben mit `--schreiben`)
**Backup:** `ENTWICKLERHANDBUCH.md.nullbyte_20260804` (250 415 B,
unverändert)

| | vorher | nachher |
|---|---|---|
| Größe | 250 415 B | **182 861 B** |
| Nullbytes | 68 328 (27,29 %) | **0** |
| Blöcke | 1, ab Offset 0 | — |

Der Nullblock wurde entfernt und durch einen Reparaturvermerk ersetzt,
der den Datenverlust benennt. Der komplette `## EVENTS-LOG` blieb
erhalten. **Nichts gelöscht.**

Das Skript bricht ab statt zu schreiben, wenn (a) mehr als ein Block
oder ein Block nicht ab Offset 0 vorliegt, (b) der Rest weitere
Nullbytes enthält, (c) der Rest kein gültiges UTF-8 ist, (d) sich die
Dateigröße zwischen Analyse und Schreiben geändert hat — Letzteres wegen
des parallel laufenden DocAgent. Geschrieben wurde atomar
(`tmp` → `fsync` → `os.replace`).

**Rollback:** `copy ENTWICKLERHANDBUCH.md.nullbyte_20260804 ENTWICKLERHANDBUCH.md`

---

## 3.4 `features/doc_agent.py` gehärtet — UMGESETZT

**Backup:** `features/doc_agent.py.bak_haertung_20260804` (27 349 B)

Zwei Verteidigungslinien:

```diff
@@ _atomic_write @@
+        if "\x00" in data:
+            raise ValueError("Schreibvorgang abgelehnt: Inhalt enthaelt Nullbytes")
         target_dir = os.path.dirname(os.path.abspath(path)) or "."

@@ _append_to_handbook, nach book = f.read() @@
+                if "\x00" in book:
+                    if not self._corruption_warned:
+                        log.warn("DOC", "Handbuch enthaelt Nullbytes - Eintrag "
+                                        "VERWORFEN statt Schaden erneut zu schreiben.")
+                        self._corruption_warned = True
+                    return
```

Der Kern des Problems: Nullbytes sind gültiges UTF-8 (U+0000), der
Lesevorgang wirft deshalb keinen Fehler, und der Agent schrieb den
beschädigten Kopf bei **jedem** Event erneut fest — so überlebten
68 328 Nullbytes vom 28.07. bis zum 04.08. Jetzt geht im Schadensfall
ein Eintrag verloren statt der Schaden zementiert zu werden.

`_corruption_warned` existierte bereits (`:77`), es wurde kein neues
Attribut eingeführt. `py_compile` fehlerfrei.
**Rollback:** Backup zurückkopieren.
**Wirksam ab dem nächsten Start** (Modul ist im laufenden Prozess geladen).

---

## 3.5 Trial-ID-Kollision — AUFGELÖST

**Skript:** `docs/messungen_2026-07/code/audit_db_block3.py`
**Backup:** `forschung.db.bak_block3_20260804` (303 104 B)

`zeile_id` 83/84 belegen T-034 und T-035 seit dem 31.07. als
`runde=2, VORREGISTRIERT, "Runde 2, Reserve"`. Die Nachtragsmessung lag
mit `runde=0` unter denselben IDs daneben.

**Auflösung:** Die 48 Nachtragszeilen (`hypothese='MS-NACHTRAG'`) haben
das Suffix `N` erhalten → **T-034N … T-041N**. Die älteren
Vorregistrierungen blieben unberührt — sie sind die im Register
etablierte Vergabe, die Nachtragsmessung ist ausdrücklich „keine
Runde 3" und gehört nicht in die T-Serie der Runden.

**Verifikation nach Commit:**

| trial_id | runde | Zeilen |
|---|---|---|
| T-034 | 2 | 1 (Vorregistrierung, unberührt) |
| T-035 | 2 | 1 (Vorregistrierung, unberührt) |
| T-034N … T-041N | 0 | je 6 = 48 |

`UPDATE` betraf genau 48 Zeilen, Restprüfung `trial_id NOT LIKE '%N'`
ergab 0. **Jede ID hat jetzt genau eine Bedeutung.**
**Rollback:** DB-Backup zurückkopieren, oder
`UPDATE trials SET trial_id=rtrim(trial_id,'N') WHERE hypothese='MS-NACHTRAG'`.

---

## 3.6 Look-ahead-Korrekturvermerk — EINGETRAGEN

**Datenbank:** Tabelle `befunde`, **befund_id 31**, `konfidenz='SICHER'`,
`risiko_0_10=4`, `impact_0_10=5`, `prioritaet='HOCH'`,
`trial_bezug='E2, G2, T-034N..T-041N'`. Zeilenzahl `befunde`: 30 → **31**.

**Register:** `docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v2.0.md`,
Abschnitt „NACHTRAG 04.08.2026 / N1" angehängt (14 146 → 17 345 B,
Backup `…_v2.0.md.bak_20260804`). Das eingefrorene Register wurde
**nicht** inhaltlich geändert — der Nachtrag hängt an.

Inhalt beider Einträge: 45 Minuten Look-ahead in `zu_1h()`
(`messung_f2_ic.py:57-70`), betrifft E2, G2 und T-034N…T-041N;
größter Verzerrungsbetrag **4,77 pp**, Richtung **durchweg negativ**;
die Urteile werden dadurch **bestätigt, nicht entwertet**; eine
Neurechnung wäre nur nötig, wenn aus diesen Messungen ein **positives**
Ergebnis abgeleitet werden sollte.

---

## 3.7 Die zwei stillen Prozesstode — NICHT ENTSCHEIDBAR

### Was das Werkzeug angeht

`wevtutil` liefert in dieser Umgebung **keinerlei Ausgabe** — auch nicht
beim einfachsten Aufruf (`wevtutil qe System /f:text /c:3 /rd:true`,
Exit 0, leer). Es ist also kein „keine Events gefunden", sondern ein
Werkzeug- oder Rechteproblem. Nach zwei erfolglosen Abfragen **abgebrochen
und gemeldet**, wie vereinbart. Das Windows-Ereignisprotokoll steht mir
hier nicht zur Verfügung.

### Was die Logs hergeben

**Korrektur meines eigenen früheren Befunds:** Ich hatte berichtet, das
Log ende am 03.08. um 12:32:37 UTC. Es endet bei **12:32:57**
(Zeile 55046). Der Unterschied ändert nichts an der Sache, aber die Zahl
war falsch.

Die letzten Sekunden (`data_store/system.log`, Zeilen 55039-55046):

```
[2026-08-03T12:32:56] [RISK]  APPROVED SELL BTC/USDC
[2026-08-03T12:32:56] [WARN]  [EXEC] Order nicht gefuellt: rejected | Sleep-Mode (676s remaining)
[2026-08-03T12:32:57] [SIGNAL] SELL ETH/USDC: NOTAUS-NETZ Stop (-3.5% <= -3.0%) - MONITOR PRUEFEN!
[2026-08-03T12:32:57] [RISK]  APPROVED SELL ETH/USDC
[2026-08-03T12:32:57] [WARN]  [EXEC] Order nicht gefuellt: rejected | Sleep-Mode (676s remaining)
```

Kein Traceback, keine Abschaltmeldung, kein `_shutdown_handler`-Eintrag.

**Was ich ausschließen kann:** Ein geordnetes Herunterfahren über SIGINT
oder SIGTERM. `app.py:427-428` registriert `_shutdown_handler`
(`:2533`), der geloggt hätte. Ein GUI-Schließen-Handler
(`WM_DELETE_WINDOW`) existiert **nicht** — das Schließen des
Tkinter-Fensters würde den Prozess ohne Logeintrag beenden und wäre mit
dem Bild vereinbar.

**Was ich nicht ausschließen kann:** Fenster geschlossen,
`TerminateProcess` (Task-Manager), Speichermangel, oder ein
Interpreter-Absturz mit Traceback auf **stderr** — app.py läuft über
`python app.py` in einer Konsole, ein Traceback landet dort und **nicht**
in `system.log`. Ohne Konsolen-Mitschnitt ist das nicht rekonstruierbar.

**Urteil: NICHT ENTSCHEIDBAR.** Nichts geändert, nichts abgeschaltet.

### Zusatzbefund, nicht beauftragt, aber ernst

In denselben Zeilen steht ein zweites Problem: `risk/engine.py:81-86`
genehmigt Verkäufe ausnahmslos („SELLS IMMER genehmigen! Nie Verkauf
blockieren!"), aber die Ausführungsschicht lehnt sie danach ab —
`[EXEC] Order nicht gefuellt: rejected | Sleep-Mode`. **Der Schlafmodus
blockiert auch NOTAUS-Stops**, hier zweimal hintereinander auf ETH bei
−3,5 %. Es gibt also ein zweites, nachgelagertes Gate, das genau das tut,
was die Risk-Engine ausdrücklich verhindern will. `execution/` steht
nicht auf meiner Freigabeliste — deshalb nur dokumentiert.

---

## Block 4 — H5 vorgemerkt, mit zwei gemeldeten Kollisionen

Eingetragen als Abschnitt „N2" in
`docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v2.0.md`.
**Eine Registerzeile, keine Spezifikation, kein Entwurf, kein Code,
kein Trial, kein Budget.**

**Kollision 1 — die ID.** H5 ist seit Runde 2 durch **Crabel NR7 /
Volatilitätskontraktion und Ausbruch** belegt (Register Abschnitt 2,
Trials T-031 bis T-033, 18 Zeilen in `trials`). H6, H7 und H8 sind
vergeben und gestrichen. Die Vormerkung erhielt daher die nächste freie
Nummer **H9**, mit ausdrücklichem Hinweis, dass der Auftraggeber sie
„H5" nennt.

**Kollision 2 — der Inhalt.** Register-Abschnitt 0 (Zeile 46) stellt
fest, dass H5, H6 und H7 „Varianten derselben Grundannahme" sind. H6
(Rhea 1932) und H7 (Darvas 1960) wurden nach **Regel 14 gestrichen**,
weil ihre Quellen keine Swing-Weite zahlenmäßig nennen. Mindestens drei
der fünf H9-Kandidaten — bestätigter Widerstand, bestätigter Support,
Marktstrukturwechsel — haben genau dieses Problem. Ohne eine Quelle vor
2015, die die Bestätigungsweite **beziffert**, scheitert H9 an derselben
Stelle. Das ist kein Ausschluss, sondern die Hürde vor der
Vorregistrierung. Sie steht so im Register.

---

## Alle Änderungen dieser Sitzung

| Datei | Art | Backup |
|---|---|---|
| `risk/engine.py` | 3 Zeilen ergänzt | `.bak_logzeilen_20260804` |
| `cockpit_server.py` | 1 Zeile geändert | `.bak_e7fix_20260804` |
| `features/doc_agent.py` | 2 Prüfungen ergänzt | `.bak_haertung_20260804` |
| `ENTWICKLERHANDBUCH.md` | Nullblock entfernt | `.nullbyte_20260804` |
| `forschung.db` | 48 UPDATE, 1 INSERT | `.bak_block3_20260804` |
| `02_EXPERIMENT-REGISTER_v2.0.md` | Nachtrag angehängt | `.bak_20260804` |

**Nicht angefasst:** `app.py`, `portfolio/`, `execution/`, `agents/`,
`config.json`, `data_store/` (nur gelesen), `v4_referenz/` (nur gelesen).
Kein Prozess gestartet, gestoppt oder neu gestartet.
