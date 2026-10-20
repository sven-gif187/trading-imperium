# Umbau-Liste BOT-HANDBUCH — ABGESCHLOSSEN am 25.08.2026

Der Umbau ist **fertig**. Im Handbuch steht kein Altbestand mehr.

## Was mit dem alten Material geschehen ist

| | |
|---|---|
| Abschnitte im Altbestand vorher | **122** mit `4.x`-Nummer, dazu 19 Runden und 20 weitere |
| davon eingearbeitet in die elf neuen Teile | **alle** — jeder neue Teil nennt am Ende seine Quellen |
| Der Text selbst | **vollstaendig nach `ENTWICKLERHANDBUCH.md` verschoben** |
| geloescht | **nichts** |

Die alten Nummern stehen weiterhin in den Ueberschriften, dort als
`ALT 4.53`. Eine Textsuche findet sie, `schon_bekannt.py` durchsucht die
Chronik mit.

## Der Weg dorthin

| Schritt | Zeilen |
|---|---:|
| Handbuch vor dem Umbau | 12.605 |
| davon in die elf Teile neu geschrieben | 5.360 |
| als Tageschronik verschoben (15 Abschnitte, gezielt) | 1.442 |
| als Altbestand verschoben (Rest) | 8.281 |
| geleerte Kapitel entfernt (ALT-TEIL B, C, D) | 190 |
| restlos eingearbeitet und geloescht (6 Abschnitte) | 519 |

## Was dabei gefunden wurde

Befunde 72 bis 76, dazu drei Berichtigungen eigener Zahlen. Alles steht im
Handbuch unter *Schluss* und in `GEFUNDENE-PROBLEME.md`.

Alle Zeilenangaben im fertigen Buch geprueft: **63 von 63 stimmen**
(`python handbuch_zeilen_pruefen.py`).


## Bereits fertig — ALLE ELF TEILE STEHEN

| Teil | Umfang | erledigt |
|---|---|---|
| **TEIL 1** — Was der Bot ist | 1.1–1.7, 158 Zeilen | 25.08.2026 |
| **TEIL 2** — Wie der Bot kauft | 2.1–2.9, 317 Zeilen | 24.08.2026 |
| **TEIL 3** — Wie der Bot verkauft | 3.1–3.7, 210 Zeilen | 24.08.2026 |
| **TEIL 4** — Was der Handel kostet | 4.1–4.9, 289 Zeilen | 24.08.2026 |
| **TEIL 5** — Was der Bot lernt | 5.1–5.8, 293 Zeilen | 24.08.2026 |
| **TEIL 6** — Beobachten ohne handeln | 6.1–6.8, 243 Zeilen | 25.08.2026 |
| **TEIL 7** — Das Cockpit | 7.1–7.7, 195 Zeilen | 25.08.2026 |
| **TEIL 8** — Der Werkzeugkasten | 8.1–8.10, rund 450 Zeilen | 24.08.2026 |
| **TEIL 9** — Der Rundgang | 19 Runden, 2.151 Zeilen | 24.08.2026 |
| **TEIL 10** — Betrieb | 10.1–10.7, 211 Zeilen | 25.08.2026 |
| **TEIL 11** — Wie wir arbeiten | 11.1–11.8, 233 Zeilen | 25.08.2026 |

Alle Zeilenangaben im Buch geprueft: **130 von 130 stimmen**
(`python handbuch_zeilen_pruefen.py`).

## Namensgebung im Altbestand

Alte Kapitel heissen `ALT-TEIL A` bis `G`, alte Abschnitte `## ALT 4.x`.
Die ZAHL bleibt absichtlich stehen: eine Textsuche nach `4.53` findet
weiterhin `ALT 4.53`. Darauf verweisen Chronik, Tickets, `schon_bekannt.py`
und die `Frueher:`-Zeilen der fertigen Teile.
