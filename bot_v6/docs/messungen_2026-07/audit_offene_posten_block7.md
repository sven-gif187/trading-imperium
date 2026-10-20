# Offene Posten abgearbeitet — F3, Kapitalquellen, Prozesstode

**UTC:** 2026-08-05T07:15Z · **Status:** alle drei Posten geschlossen,
zwei davon mit einem Ergebnis, das eine geplante Arbeit überflüssig macht.

---

## Posten 1 — F3 neu rechnen? **Nicht nötig.**

Die Frage war, ob der Kapitaltod die Aussage „BTC-Halten schlägt den Bot"
entwertet. Antwort mit den A/B-Zahlen aus der Werkzeugprüfung:

| Jahr | BTC halten | Bot A (prozentual) | Bot B (kapitalunabhängig) | Abstand A | Abstand B |
|---|---|---|---|---|---|
| J2 | 272,85 $ | 49,44 $ | **9,99 $** | −223,41 $ | **−262,86 $** |
| J1 | 870,62 $ | 186,56 $ | **153,69 $** | −684,06 $ | **−716,93 $** |

**Die Korrektur macht den Bot in beiden Jahren schlechter**, nicht besser.
Der Abstand zu BTC-Halten wächst um 39,45 $ (J2) und 32,87 $ (J1). Die
F3-Aussage wird also **bestätigt und in der Größe verstärkt**. Eine
vollständige Neurechnung würde nur die bereits bekannte Richtung mit
schlechteren Zahlen wiederholen.

**Status: ERLEDIGT** — keine Neurechnung.

---

## Posten 2 — `get_total_capital()`-Inkonsistenz

**Es gibt keine Inkonsistenz in einer Funktion, sondern drei
Kapitalberechnungen nebeneinander:**

| Ort | Formel | Sparplan-BTC |
|---|---|---|
| `portfolio/manager.py:70` `get_total_capital()` | Balance + bewertete Coins (3 Preis-Fallbacks) | über die Balance |
| `core/balance_reporter.py:168` | `usdc_free + positions_value + sparplan_wert` | **ja, explizit** |
| `app.py` (Fix vom 05.08.) | `usdc + bewertete offene Positionen` | **nein, bewusst** |

Der BalanceReporter ruft `get_total_capital()` **gar nicht** auf — er
rechnet selbst. Daher die widersprüchlichen Zahlen: 596,58 $ im Report
gegen 169,32 $ im Sizing-Pfad.

**Bewertung:** technische Schuld, kein Bug. Jede der drei Formeln ist für
sich korrekt, sie beantworten nur unterschiedliche Fragen (Gesamtvermögen
vs. handelbares Kapital). Gefährlich wird es, wenn eine Zahl für die
falsche Frage benutzt wird — genau das war beim Sizing der Fall.

**Vorschlag, nicht ausgeführt:** eine Quelle mit zwei benannten Größen —
`gesamtvermoegen()` (inkl. Sparplan, für Reporting) und
`handelskapital()` (ohne Sparplan, für Sizing und Risiko). Die drei
Aufrufer darauf umstellen. Betrifft `portfolio/`, `core/` und `app.py` —
gehört freigegeben, nicht nebenbei gemacht.

**Status: GEKLÄRT**, Umbau offen.

---

## Posten 3 — Die stillen Prozesstode: **URSACHE GEFUNDEN**

Bisher als NICHT ENTSCHEIDBAR geführt, weil `wevtutil` in dieser Umgebung
**keinerlei Ausgabe** liefert — auch beim einfachsten Aufruf, Exit 0, leer.

**`Get-WinEvent` funktioniert.** Das war ein Werkzeugproblem, kein
Datenproblem.

### Der Beleg

```
04.08.2026 02:51:36  Application Hang  Id 1002
04.08.2026 02:51:08  Application Hang  Id 1002
Das Programm python3.13.exe Version 3.13.14150.1013 hat die Interaktion
mit Windows beendet und wurde geschlossen.
Prozess-ID: 14e8 / 3ae8
```

**SICHER:** Windows hat den Bot-Prozess beendet, weil er nicht mehr auf
Fensternachrichten reagierte. Das ist kein Absturz — deshalb gab es nie
einen Traceback, nie eine Abschaltmeldung und nie einen
`_shutdown_handler`-Eintrag. Der Prozess verschwand einfach.

**Zeitlicher Abgleich:** PID 9300 wurde am 04.08. um 02:45:35 lokal
gestartet; die Hangs sind um 02:51:08 und 02:51:36 protokolliert. Sechs
Minuten Laufzeit, dann Zwangsschließung durch Windows.

### Warum hängt die GUI — WAHRSCHEINLICH

`app.py:2842` ruft `window.mainloop()`; der GUI-Thread ist damit der
Hauptthread. `ui/main_window.py:2977` registriert einen Log-Callback, der
**jede einzelne Logzeile** per `self.after(0, …)` in die Tk-Event-Queue
stellt.

Gemessene Last: 31 124 BUY-Signalzeilen in 24 Stunden, dazu Monitor-,
Loop- und Brain-Zeilen — rund **360 Logzeilen pro Minute**, jede als
eigenes Tk-Event. Bleibt die Queue voll, kommt Tk nicht mehr zur
Fensternachrichten-Verarbeitung, Windows markiert das Fenster als „keine
Rückmeldung" und der Hang-Detector schließt den Prozess.

Das ist **WAHRSCHEINLICH**, nicht SICHER: Der Hang ist bewiesen, seine
Entstehung nicht direkt gemessen.

### Gegenmaßnahmen, nicht ausgeführt

1. **Log-Callback drosseln** — Zeilen sammeln und gebündelt alle 500 ms
   in die GUI schreiben statt einzeln. Kleinster Eingriff, größte Wirkung.
2. **Logvolumen senken** — die Signalzeile wird pro Coin und Zyklus
   geschrieben, auch wenn sich nichts ändert. Nur bei Änderung schreiben
   würde die Last um Größenordnungen senken.
3. **Watchdog** — externer Prozess, der den Bot neu startet, wenn er
   verschwindet. Behandelt das Symptom, nicht die Ursache.

**Status: GEKLÄRT** (SICHER für das Was, WAHRSCHEINLICH für das Warum),
Gegenmaßnahme offen.

---

## Sicherheit

Nichts geändert. Alle drei Posten wurden ausschließlich lesend
untersucht. Kein Echtgeld, keine Order, keine Secrets, keine Datei
gelöscht.
