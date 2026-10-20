# Diese Sicherungskopien NICHT wegräumen

**Angelegt 12.08.2026 beim Aufräumen (Aufgabe 4).**

---

## ✅ STAND 12.08.2026: Der Code ist zurückgeholt

Beide Dateien sind wiederhergestellt. **Nicht** durch Zurückkopieren —
das wäre ein zweiter Datenverlust gewesen:

| Datei | Vorgehen | Grund |
|---|---|---|
| `metals_engine.py` | Sicherung komplett zurück | enthielt **keine** späteren Verbesserungen, war reine Abspeckung |
| `metals_tab.py` | **von Hand zusammengeführt** | enthielt vier absichtliche `[AUDIT 06.08.]`-Verbesserungen von 10:52 Uhr — also **nach** dem Überschreiben |

**Was in `metals_tab.py` erhalten bleiben musste:** ein echter Rechenfehler
im Konfidenzintervall war behoben worden (`treffer_pct/100` → `treffer/n`),
und die Überschrift „wie gut die Signale waren" war zu „Signal-Aufzeichnung
(Mitschrift, noch kein Urteil)" korrigiert. Ein Zurückkopieren hätte beides
gelöscht.

**Wieder eingesetzt wurden vier Blöcke:** Persistenz-Import, gespeicherter
Stand beim Start, Speichern nach jedem Scan, Richtungsanzeige (▲ LONG grün
/ ▼ SHORT rot).

**Die Sicherungen bleiben trotzdem noch liegen**, bis du den Reiter einmal
geöffnet und gesehen hast, dass alles stimmt. Danach dürfen sie ins Archiv
— der Stand ist in Git.

---

## Die ursprüngliche Lage (zur Nachvollziehbarkeit)

In diesem Ordner liegen fünf Dateien, die wie gewöhnliche
Sicherungskopien aussehen. **Zwei davon sind es nicht** — sie sind der
einzige erhaltene Beleg für Code, der am 06.08.2026 zerstört wurde.

## Worum es geht

`update_metals_indikatoren.py` **ersetzt** Dateien, statt sie zu patchen
— es sagt das selbst in seinem Kopf. Am **06.08.2026 um 04:34** lief es
und überschrieb `metals_engine.py` und `metals_tab.py` mit einer
Fassung, in der zwei zuvor eingebaute Funktionen fehlten.

Das steht als **Punkt 25** in `GEFUNDENE-PROBLEME.md`. Was genau
verloren ging, war bis jetzt nicht dokumentiert. Beim Aufräumen kam es
heraus:

| Datei | heute | Sicherung 04:34:40 | fehlende Zeilen |
|---|---|---|---|
| `metals_engine.py` | 437 | 475 | **48** |
| `metals_tab.py` | 335 | 372 | **68** |

## Was inhaltlich fehlt

**Stufe-2 — Trendfilter.** Kein Einstieg gegen einen bestätigten
Abwärtstrend (SMA50 < SMA200):

> „Verhindert Dip-Käufe ins fallende Messer."

**Stufe-3 — Richtungsbestimmung.** Im bestätigten Abwärtstrend nicht
nur „WARTEN", sondern ggf. SHORT — aber nur, wenn der Kurs in eine
Verkaufszone hochgelaufen ist (kein Short am überverkauften Boden).

Eingebaut hatten das `install_metals_stufe2.py` und
`install_metals_stufe3.py`. Beide sind inzwischen archiviert; ihre
Begründungen stehen in `BEGRUENDUNGEN-EINMAL-SKRIPTE.md`.

## Die beiden wichtigen Dateien

```
metals_engine.py.scoring_backup_20260806_043440
metals_tab.py.scoring_backup_20260806_043440
```

**Nicht archivieren, nicht löschen**, solange nicht entschieden ist, ob
der Code zurückgeholt wird.

Die drei anderen (`*_20260607_*`, `*threadfix_20260607*`) sind ältere,
gewöhnliche Sicherungen — die dürfen weg.

## Noch zu entscheiden

Ob die beiden Funktionen zurückgeholt werden, ist **offen**. Metals
gehört zum Beobachtungsdeck, nicht zum Handelspfad — ein Rückbau ändert
also kein Kaufverhalten. Die Entscheidung liegt trotzdem beim
Eigentümer, weil die Tabs bewusst unangetastet bleiben.
