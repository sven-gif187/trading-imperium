# Übergabeprotokoll — Trading Imperium V6

Für Claude Code. Bitte diese Datei zuerst vollständig lesen, bevor irgendetwas am
Code geändert wird. Sie fasst zusammen, was in vorherigen Chat-Sessions mit
Claude (Web/App) erarbeitet wurde.

**Bot-Entwickler:** Sven, Stuttgart. Sole Developer, Paper-Trading (kein echtes Geld),
Python 3.13, Windows. Anrede: informell, "Bruder/Kollege", Deutsch.

---

## 1. Eiserne Regeln — bitte übernehmen

1. **Erst verstehen, dann ändern.** Vor jeder Änderung den betroffenen Code lesen,
   nicht aus Erinnerung/Notizen patchen.
2. **Jede Zahl selbst aus der frischen Rohdatei nachrechnen** (`trades_v5.json` o.ä.)
   — nie aus einem Report, Handbuch oder dieser Übergabe unkritisch übernehmen. Diese
   Regel existiert, weil in einer früheren Session ein falscher R/R-Wert aus einem
   fehlerhaften Report übernommen wurde und zusätzlich V4- mit V6-Daten vermischt
   wurden, ohne das kenntlich zu machen. Darf nicht wieder passieren.
3. **Keine Trading-Verhaltensänderung während einer laufenden Epochen-Auswertung**
   (siehe Abschnitt 3). Bugfixes und reines Logging sind immer erlaubt.
4. **Ein Schritt nach dem anderen, Bestätigung von Sven abwarten**, bevor der nächste
   Patch kommt.
5. **Vor Bot-Config-/Trade-Datei-Patches: Bot vollständig schließen.**
6. **Install-/Patch-Vorgehen:** idempotent (Marker-Check), Syntax-Check nach jeder
   Änderung, Backup vor jeder Änderung, exakter Zielpfad, Encoding der Datei
   respektieren (siehe Abschnitt 6 — gemischt CRLF/LF im Projekt).
7. **Nur V6-Daten für V6-Auswertungen.** Es gibt eine separate V4-Instanz
   (andere Coins: APT/OP/ARB/INJ/RENDER/SUI, andere Strategien) — die läuft in einem
   eigenen Projekt, nicht hier vermischen.

---

## 2. Projektpfade

```
Hauptordner:     C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\
Config:          data_store\config.json          (NICHT im Hauptordner!)
Trade-Journal:   data_store\trades_v5.json
Order-Historie:  data_store\order_history.json
Equity-Verlauf:  data_store\equity_history.json
Cockpit:         cockpit_server.py (Hauptordner) + Handbuch COCKPIT_HANDBUCH.md
Ticket-Datei:    tickets.txt (Format "STICHWORT: Text", Stichworte: SPEICHERN,
                 ERLEDIGT, BUG, DOKUMENTIEREN, NOTIZ)
```

Der Ordnername enthält Klammern `(21)` — bei `cd` immer in Anführungszeichen setzen.

**Wichtig:** app.py wurde in mehreren Split-Schritten modularisiert. Der komplette
Exit-Monitor (Stop-Loss/Trailing/SELL-Journal-Eintrag) liegt NICHT mehr in app.py,
sondern in `runtime/exit_monitor.py`. State-Management in `runtime/state_manager.py`,
Reporting in `runtime/reporting.py`. Vor jedem Patch prüfen, ob der gesuchte Code
noch in app.py ist oder schon ausgelagert wurde — Claude Code sollte das mit `grep`
selbst verifizieren statt sich auf alte Notizen zu verlassen.

---

## 3. AKTUELLER STAND — der wichtigste Abschnitt

### Laufende Epoche: E7 (phasen-angepasstes Trailing)

- Deployed: 17.07.2026
- Auswertungsfenster: 14 Tage / mind. 15 Sells — **beides erfüllt** (Stand 26.07.:
  40 Sells seit Deploy)
- **Fenster endet: 31.07.2026**
- Kriterium: R/R und Trailing-Exit-Gewinn müssen die E6.1-Basis schlagen
  (E6.1-Basis-R/R: 0,68)
- Zwischenstand 26.07.: E7 R/R 0,69 (knapp über Basis), Netto +7,54$

**Bis zum 31.07.: keine Trading-Verhaltensänderung.** Reines Logging/Analyse ist ok.

### Was direkt danach ansteht: E8 (vorregistriert, noch NICHT umgesetzt)

**Kernbefund, an zwei unabhängigen Bots (V6 + V4) bestätigt:** Averaging Down
(Nachkauf in offene Verlustpositionen) ist der Haupt-Verlusttreiber.

- V6: Positionen ohne Nachkauf +75$ (R/R 0,82), mit 2 Käufen −65$, mit 3+ −47$
- V4 (5090 Trades): ohne Nachkauf +460$, mit 4+ Käufen −1419$

**E8-Plan:** Nachkauf in offene Verlustpositionen abschalten (`is_nachkauf`-Zweig,
war in app.py ~Zeile 1870, jetzt vermutlich in `runtime/exit_monitor.py` oder dem
Kaufpfad — verifizieren). Ersteinstieg bei Fear bleibt unverändert. Hypothese:
R/R steigt von 0,66 auf ~0,86.

**Bekannte technische Ursachen des DCA-Problems** (verifiziert im Code):
- `dca_max_levels`/`dca_drop_pct` aus config.json werden im Kaufpfad NICHT gelesen
- Nachkauf-Schwelle (2%) hängt am gemischten `entry_price` → wandert mit jedem
  Nachkauf nach unten (gleitende Leiter ohne Boden)
- Kein Nachkauf-Zähler vorhanden
- `max_exposure_per_coin_pct` wird im DCA-Pfad nicht geprüft (ADA wuchs auf 163$)
- Cooldown-Check ist fail-open (`except: pass` → kauft trotzdem bei Fehler)

### Zweiter Befund: Gebühren

Binance Roundtrip 0,20%. Median-Gewinntrade nur +0,545% → Gebühren fressen 35-37%
vom Rohgewinn. ~22% der "Gewinner" liegen unter der Fee-Schwelle = netto Nullnummern.
Trailing wird ab +0,3% scharf (real +0,1% nach Fee). Kandidat für E8/E9: Trailing-
Schwelle über das Fee-Niveau heben.

### MFE/MAE-Logging — LIVE, sammelt

Am 25.07. installiert und bestätigt: `runtime/exit_monitor.py` schreibt jetzt pro
SELL zusätzlich `mfe_pct`, `mae_pct` (Höchst-/Tiefststand relativ zum Einstand) sowie
den vorher fehlenden `pnl_pct` + `fee` (Regression seit ~15.07. war da, ist gefixt).
Auswertung sinnvoll ab ~20-30 gesammelten Trades (aktuell 2, Stand 26.07.).

### Cockpit — läuft

`cockpit_server.py` im Hauptordner, lokal, read-only, `127.0.0.1:8110`, liest
`trades_v5.json` + `equity_history.json`, refresht alle 60s. Nutzt bewusst NICHT
`brain_performance.json` (siehe Abschnitt 5). Handbuch liegt daneben.

---

## 4. Nicht-verhandelbare Trading-Regeln (Live-Voraussetzungen)

Vor JEDEM echten Geld:
1. R/R > 1,0 (aktuell ~0,66-0,69, verbessert sich)
2. Buchhaltungs-/Absturz-Robustheit bombenfest (siehe Historie Abschnitt 7)
3. MiCA/Börsen-Situation geklärt (Binance-EU-Risiko war im Juni akut, Bot ist
   Multi-Exchange-fähig als Ausweg, siehe Notiz 9 unten)
4. `position_sizing.py` ist im Code vorhanden, wird aber NIRGENDS aufgerufen —
   muss vor Live angebunden werden
5. P4 aus dem Audit (stille `except: pass` im Preis-Pfad, `market_data.py:90` +
   `live_runner.py:77`) — Härtungs-Installer existiert, Deploy-Status unklar

---

## 5. Wichtige Fallstricke — bereits einmal gegen die Wand gelaufen

- **`brain_performance.json` NICHT für V6-Auswertungen nutzen.** Sie ist
  V4-Bootstrap-verseucht (`source: v4_bootstrap`, `v6_trades_added: 0` bei den
  meisten Strategien wie ICHIMOKU/FIBONACCI/EMA_TREND). Nur `DCA_FEAR_GREED` hat
  nennenswerte echte V6-Trades.
- **V6 hat NICHT nur einen Einstieg**, auch wenn das Journal so aussieht:
  `signal_agent.analyze()` addiert Fear&Greed + Ensemble + V4-Ensemble
  (ICHIMOKU/FIBO/EMA via `v4_ensemble.evaluate_buy`) zu einem Score. Die
  V4-Strategien laufen mit, kriegen aber nicht das Trade-Label — daher steht
  überall `DCA_FEAR_GREED`. Kein toter Code. Mehr Einstiege sind NICHT die
  Priorität — der Entry funktioniert (siehe Abschnitt 3), das Leck ist beim
  Nachkauf/Ausstieg.
- **`config.json` liegt in `data_store/`**, nicht im Hauptordner. `settings.py`-
  Defaults werden zur Laufzeit überschrieben — immer `config.json` patchen, nie
  `settings.py`.
- **`__init__.py`-Dateien nie als verwaist einstufen** (bekannter Blindspot eines
  früher gebauten Inventur-Agenten).
- **CRLF vs. LF ist gemischt im Projekt:** `app.py` ist CRLF, `main_window.py` und
  `exit_monitor.py` sind teils LF/CRLF unterschiedlich — vor jedem Patch das
  tatsächliche Encoding der Zieldatei prüfen, nicht annehmen.
- **Order_history.json ist KEINE bessere DCA-Rekonstruktionsquelle** als
  `trades_v5.json` — sie reicht historisch nicht so weit zurück und hat kein
  `pnl`-Feld. Für DCA-Analysen bleibt `trades_v5.json` die Quelle.
- Frühere Absturzursache: Svens Laptop ging bei leerem Akku aus → Journal-Verlust.
  Mehrfach empfohlen, den Laptop am Ladekabel zu lassen während der Bot läuft.

---

## 6. Offene technische Schulden (nicht dringend, aber bekannt)

- app.py (~2500 Zeilen nach Splits) und main_window.py (~3000 Zeilen) — Monolith-
  Split läuft in Schritten (Reporting → State → Exit-Monitor bereits ausgelagert;
  weitere Schritte: Journal → Signale)
- Viele stille `except: pass`-Stellen im Projekt (Audit fand ~180) — P4 ist die
  kritischste (Preis-Pfad), Rest niedrigere Priorität
- Daily-Loss-Logik: zwei parallele Module (`daily_loss_guard.py` und
  `daily_loss_guardian.py`), aktuell deaktiviert, Neubau geplant: eine Quelle der
  Wahrheit, echter Tagesverlust statt Abstand zum Startkapital, nur Kauf-Pause statt
  Alles-Verkaufen
- `requirements.txt` war ungepinnt, sollte geprüft werden ob noch aktuell
- Diverse Backup-/Reset-Dateien im Projektbaum (aus `full_reset_final_v2/v3.py` etc.)
  — Sven hat ein eigenes `cleanup.py` (v3), das nur erledigte install*/fix_*-Dateien
  archiviert, nie löscht. `.md`/`.pdf` sind geschützt (außer `roadmap_*.pdf`).
  `__init__.py` NIE archivieren (siehe Fallstricke).

---

## 7. Historie in Kurzform (für Kontext, nicht zum sofortigen Handeln)

- Frühe Phase: mehrfache Buchhaltungs-Abstürze durch leeren Laptop-Akku, Journal-
  Recovery gebaut und mehrfach nachgebessert, inzwischen mit `fsync` + `.bak` +
  Order-History-Rekonstruktion gehärtet.
- E3/E4/E5: Stop-Loss-Straffung (4,0% → 2,5%) war der große Hebel, bestätigt über
  mehrere unabhängige Analysen. E5 (Trailing-Änderung) wurde nach Walk-Forward-
  Validierung als reine Regime-Wette erkannt und verworfen — wichtige Lektion für
  jede künftige Parameteränderung: erst walk-forward validieren.
- Makro-/Zyklus-Hypothese (kNN-Ähnlichkeit historischer Marktphasen) wurde nach
  sauberem Shadow-Test auf 8 Jahren Daten widerlegt und bewusst geparkt — gutes
  Beispiel für "These vor Kapital-Einsatz falsifiziert, nicht danach".
  situation_history.json bleibt als reines Analysewerkzeug.
- Coin-Expansion (neue Coins wie ARB/RENDER) wurde geprüft und verworfen: im
  V4-Bullenmarkt liefen sie gut, im Bärenmarkt kollabierten sie härter als das
  Kernportfolio — Bull-Markt-Illusion, kein bewiesener Edge.
- XRP wurde aus dem aktiven Handel genommen (klarster struktureller Verlierer über
  V4 und V6 hinweg).

---

## 8. Peters Hilfe / geplanter Hardware-Umzug

Ein erfahrener Freund (Peter, eigener Bot seit 4 Jahren) unterstützt Sven fachlich
und schenkt ihm einen Mini-PC (Ubuntu, 8GB RAM, SSD) für 24/7-Betrieb. Geplanter
Ablauf: Bot zieht auf die Box um, Zugriff per SSH, Claude Code arbeitet dort direkt
auf den Dateien (mit tmux für persistente Sessions). Timing: nach E7-Abschluss
(31.07.) und Peters Urlaubsrückkehr. Sicherheits-Punkt für später: API-Keys nie in
Dateien, sondern Umgebungsvariablen/Secrets-Manager, sobald es Richtung Live geht.

Peters Fine-Tuning-Cockpit (`optimizer.py`, SQLite-basiert, für seinen Gold-Futures-
Bot) wurde geprüft: sauberer Code, read-only, aber nicht plug-and-play für V6
(anderes Datenmodell). Konzept ist gut (MFE/MAE, n≥20-Gate, Drift-Selbstcheck) —
falls später gewünscht, mit Claude Code auf der neuen Box gezielt für V6 verdrahten,
nicht blind übernehmen.

---

## 9. Wie mit Sven zusammenarbeiten

- Deutsch, informeller Ton, direkt und ehrlich — auch unbequeme Befunde klar
  benennen, aber konstruktiv.
- Sven ist kein professioneller Softwareentwickler — Erklärungen praktisch halten,
  nicht nur Fachjargon.
- Bei jeder ausgelieferten Datei/jedem Patch: genauen Zielpfad nennen und daran
  erinnern, dass er selbst platziert werden muss.
- Nach ca. 5 erledigten Aufgaben: proaktiv ein Ticket-Update für `tickets.txt`
  anbieten.
- Sven reagiert gereizt, wenn Wiederholungsfehler passieren (z.B. Copy-Paste-Befehle
  die nicht als ein Befehl funktionieren) — sorgfältig und getestet liefern, nicht
  drauflos.
- Langfristiges Ziel: Bot irgendwann kostenlos veröffentlichen (Satoshi-inspiriert),
  parallel entsteht eine ehrliche TikTok-Serie über die Entwicklung (inkl. Fehler
  und Verluste, bewusst gegen "Lambo-Bot"-Content positioniert).

---

## 10. Erster sinnvoller Schritt für Claude Code

Nichts überstürzen. Vorschlag für den Einstieg:

1. Diese Datei vollständig gelesen haben.
2. `git status`/Ordnerstruktur ansehen, sich einen eigenen aktuellen Überblick
   verschaffen (nicht blind dieser Übergabe vertrauen — Stand kann sich seit dem
   Schreiben dieser Datei geändert haben).
3. Prüfen, ob E7 noch läuft oder das Fenster (31.07.) schon erreicht ist — das
   bestimmt, ob Verhaltensänderungen erlaubt sind.
4. Sven fragen, was er als Erstes angehen möchte, statt eigenständig loszulegen.
