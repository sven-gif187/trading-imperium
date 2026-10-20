# Forschungs- und Dokumentationsdatenbank

Stand 30.07.2026. SQLite, reine Standardbibliothek, keine neue Abhängigkeit.
Datei: `forschung.db` (SHA256 in `REGISTER-PRUEFSUMME.txt`).

## Grenze — nicht verhandelbar (A7)

Diese Datenbank gehört **ausschließlich zum Forschungsprogramm**. Sie
liegt unter `docs/`, liest nichts aus `data_store/`, schreibt nichts
dorthin, und der laufende Bot wird **nicht** angebunden. Eine Umstellung
des Bots auf SQLite ist eine offene, separate Grundsatzentscheidung
(`ENTWICKLERHANDBUCH.md:1205` führt sie auf der Tech-Schuld-Liste) und
wird hier **nicht vorweggenommen**.

## Vorrang (A5)

**Die .md-Dateien bleiben die verbindliche Fassung.** Die Datenbank
ergänzt sie um Abfragbarkeit, sie ersetzt sie nicht. Jede Zeile in
`trials`, `datenquellen`, `kostenszenarien`, `befunde` und
`register_versionen` führt die Spalte `quelle_md`. **Bei Widerspruch
gilt die .md.**

## A1 — Bestandsaufnahme: existierte schon eine Datenbank?

**Nein, im Workspace nicht** [SICHER]: keine `.db`/`.sqlite`-Datei, kein
`import sqlite3` in irgendeinem Projektmodul (verifiziert per Suche über
alle 256 .py).

**Zwei Hinweise auf externe SQLite außerhalb dieses Workspace — gemeldet,
nicht angenommen:**

1. **Peters `optimizer.py`** (`UEBERGABE-CLAUDE-CODE.md:208`,
   `ENTWICKLERHANDBUCH.md:1205`): 660 Zeilen, SQLite-basiert, read-only
   (`mode=ro`), stdlib-only, geprüft und als sauber bewertet. Gebaut für
   einen **Gold-Futures-Bot**, anderes Datenmodell, ausdrücklich *nicht*
   plug-and-play für V6. Liegt nicht in diesem Workspace. Kein Schema
   davon wurde übernommen. [SICHER, dass der Hinweis existiert;
   UNGEKLÄRT, wie das Schema aussieht — die Datei liegt hier nicht vor]
2. **`uebergabe-dust/README.md:156`**: `Datenbank: [z.B. SQLite über
   meinen DatabaseManager / keine]` — Platzhaltertext einer
   Startprompt-Vorlage, keine reale Datenbank. [SICHER]

Ferner dokumentiert `ENTWICKLERHANDBUCH.md:1205` eine **offene
Grundsatzentscheidung**: „V6 auf SQLite umstellen (stand eh auf
Tech-Schuld-Liste) oder gather() auf JSON umschreiben." Diese
Forschungsdatenbank ist **nicht** diese Umstellung und darf nicht mit ihr
verwechselt werden.

## Tabellen

| Tabelle | Zeilen | Inhalt |
|---|---|---|
| `trials` | 79 | T-001…T-030; je Trial eine Zeile pro Segment × Kostenszenario |
| `bot_architektur` | 231 | jede .py des Bots mit Zweck, Importgraph, Status, Bugs |
| `datenquellen` | 28 | Kerzen/Funding/Makro, **live nachgemessen**, nicht abgeschrieben |
| `befunde` | 11 | Befunde mit Konfidenz, Risiko, Impact, Priorität |
| `kostenszenarien` | 4 | K-MAKER/K-BASIS/K-KONSERVATIV + die verworfene v1.0-Annahme |
| `register_versionen` | 3 | v1.0/v1.1/v1.2 mit Prüfsumme |
| `programm_status` | 1 | Gate 1 = NEGATIV |

## A3 — Architektur-Scan: Methode und Ergebnis

Mechanisch, keine Schätzung: `zweck` = erste Zeile des Modul-Docstrings;
`abhaengigkeiten` = projektinterne Importe per `ast`; `status` aus der
transitiven Erreichbarkeit ab `app.py`.

| Status | Module | Bedeutung |
|---|---|---|
| AKTIV | 117 | transitiv von app.py erreichbar |
| **TOT** | **100** | von keinem Modul importiert, kein Einstiegspunkt |
| UNGEPRÜFT | 13 | importiert, aber nicht von app.py erreichbar (Tests/Installer) |
| DEAKTIVIERT | 1 | erreichbar, aber per Config abgeschaltet |

**43 % der Module werden von nichts importiert.** AST-Parsefehler: keine.

**Wichtig:** `AKTIV` heißt **erreichbar, nicht aufgerufen**. Import ≠
Aufruf. Diese Unterscheidung steht in `status_belege` jeder Zeile.

### Zwei Korrekturen an den Auftragsannahmen

Der Auftrag nannte Module, die „bereits belegt" tot seien. Zwei davon
halten der Prüfung nicht stand:

- **`risk/position_sizing.py` ist nicht tot, sondern DEAKTIVIERT.**
  `risk/engine.py:13` importiert, `:53` instanziiert, `:179` ruft
  `self.sizer.calculate()` auf. Abgeschaltet wird es durch
  `config.json risk.use_dynamic_sizing=false` in Verbindung mit
  `app.py:886`. Reaktivierung wäre eine Config-Änderung, kein Code-Fix.
- **`calc_all_indicators` ist nicht global tot.** In `app.py:64`
  importiert, aber **0 Aufrufe in app.py** (verifiziert). Einziger echter
  Aufrufer: `models/train_pipeline.py:31`. Tot ist der *Import in
  app.py*, nicht die Funktion.

Bestätigt wurde dagegen: **`dca_drop_pct` ist toter Parameter** — einzige
Fundstelle `config/settings.py:236`, die −2-%-Schwelle ist in
`app.py:1798` hart codiert.

## Zwei Befunde, die erst die Datenbank sichtbar gemacht hat

1. **4h-Kerzen haben 8 Lücken, 1d hat keine.** `03_DATEN-COVERAGE.md`
   prüfte nur die Tagesreihen. BTC/ETH 4h haben je 8 Lücken (größte
   32 h nach 2018-02-08). Für Regeln auf 1d irrelevant, für 4h-Regeln
   nicht.
2. **Das Funding-Intervall ist nicht konstant 8 h.** SOLUSDT hat 101
   Nicht-8h-Abstände (98 × 2 h, 3 × 4 h); die anderen 11 Coins sind
   sauber (82 199 von 82 300 Abständen gesamt). **H2 lief nur auf
   BTC/ETH — T-025…T-028 sind nicht betroffen und bleiben gültig.** Aber
   die Registerregel „3 aufeinanderfolgende 8h-Intervalle" wäre auf SOL
   ein 6- statt 24-Stunden-Fenster gewesen. Jede künftige Funding-Regel
   auf breiterem Universum muss **in Kalenderzeit statt in Intervallen**
   definiert werden.

## A6 — Abfrage-Werkzeug

Aufruf aus `docs/forschungsprogramm_2026-07/code/`:

```bash
python db_frage.py status
```

| Befehl | Zweck |
|---|---|
| `status` | Programmstatus, Gates, Trials nach Status, Registerversionen |
| `trials [RUNDE]` | alle Trials (einer Runde) |
| `confirmed` | alle CONFIRMED — derzeit leer, Gate 1 negativ |
| `trial T-024` | ein Trial mit allen Segmenten und Szenarien |
| `tot` | alle toten Module, nach Zeilen sortiert |
| `bugs` | Module mit dokumentierten Bugs |
| `luecken` | Datenquellen mit Lücken |
| `quellen [TYP]` | Datenquellen (klines/funding/makro) |
| `kosten` | Kostenszenarien |
| `befunde` | Befunde nach Priorität |
| `register` | Registerversionen mit Prüfsumme |
| `sql "SELECT …"` | freie Leseabfrage, nur SELECT |

## Reproduktion von Null

```bash
python db_schema.py --neu && python db_scan_architektur.py && python db_fill_migration.py
```

Laufzeit unter 30 s. Der Architektur-Scan und die Datenquellen-Statistik
werden dabei **neu gemessen**, nicht aus dieser Datei gelesen — die
Datenbank kann also veralten, aber nicht stillschweigend falsch werden.
