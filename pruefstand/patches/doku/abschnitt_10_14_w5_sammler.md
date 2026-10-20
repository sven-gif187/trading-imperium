## 10.14 Betriebs-Wächter W5 und der Sammler, der nur den eigenen Ordner zählen darf

**Angelegt 14.10.2026** aus dem Prüfstand.

**W5 Betrieb.** Die Windows-Aufgabe **`TI-Wächter-W5`** (Aufgabenname `TI-Waechter-W5`) läuft alle 5 Minuten und prüft nur lesend (`pruefstand\waechter\w5_betrieb.py`):

- je Bot den Prozess, den Cockpit-Port und das Alter von `bot_state.json`, `system.log`, `telemetrie.db`, `nachlauf.db`, `schatten_universum.db` und, bei offenen Positionen, `positionsverlauf.db`,
- ob die Windows-Aufgaben vorhanden sind,
- den freien Plattenplatz.

Ergebnis: Ampel in `pruefstand\status.json`, Verlauf in `pruefstand\waechter.db`. Telegram gibt es nur beim **Wechsel nach Rot** und bei Erholung, höchstens alle 6 h je Meldung, dazu täglich ab 08:00 ein Lebenszeichen. Das klappt, sobald `pruefstand\TELEGRAM_EINRICHTEN.bat` gelaufen ist.

**Was W5 im ersten Lauf fand.** v7 hielt eine Position, aber `positionsverlauf.db` war seit dem **02.10.2026** nicht mehr geschrieben worden (17.387 Minuten). Ursache in `sammler_pruefen.py`, Funktion `starten()`:

```
if skript.lower() in prozesse and skript not in trotzdem:   # alt
```

`prozesse` sind die Befehlszeilen **aller** Python-Prozesse. Läuft `positionsverlauf.py` aus dem v6-Ordner, hält v7 seinen eigenen für „läuft schon“ und startet ihn nie. Das ist dieselbe Fehlerklasse wie der tote v6-Nachlauf vom 27.09. bis 14.10. Der Tagescheck meldete es („läuft aus FREMDEM Ordner“), aber nur einmal am Tag und ohne Folge.

**Fix (v6 und v7):** Die neue Funktion `_laeuft_hier(skript)` zählt einen Sammler nur, wenn ein Python-Prozess ihn aus **genau diesem Ordner** fährt, über den Skriptpfad oder ersatzweise den Arbeitsordner. Gegenprobe vor dem Einspielen in beide Richtungen: v6 → True (sein Verlauf lief), v7 → False (keiner lief). Das betrifft nur das Datensammeln, nicht den Handel, deshalb gibt es **keine Epoche** (Abschnitt 5: Änderungen, die ausschließlich aufschreiben). Skript: `pruefstand\patches\patch_sammler_eigener_ordner.py`, Marke `SAMMLER EIGENER ORDNER 14.10.2026`.

**Lehre:** Jede Prüfung „läuft Prozess X?“ muss den Ordner prüfen, solange zwei Bot-Ordner nebeneinander laufen. Wer eine neue solche Prüfung schreibt, nimmt `_laeuft_hier()` als Vorlage.
