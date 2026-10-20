# Audit Multi-Strategy — Block 2: Bug-Liste

**Lokal:** 04.08.2026 06:50 (MESZ) · **UTC:** 2026-08-04T04:50Z
**Status:** ERFOLG — alle 8 Punkte geprüft, keiner offen geblieben.
Belegskript `code/audit_bugliste.py` (read-only), Ausgabe
`ausgaben/audit_bugliste_out.txt`.

| Punkt | Status |
|---|---|
| 2.1 Handbuch-Nullbytes | **BESTEHT NOCH** (Anteil anders als gemeldet) |
| 2.2 E7-Fenster 12 h zu früh | **BESTEHT NOCH** — Fix-Diff liegt vor |
| 2.3 e7_final.txt nie erzeugt | **BESTEHT NOCH** — Skript ist lauffähig |
| 2.4 E8 nie installiert | **BESTEHT NOCH**, aber **GEGENSTANDSLOS** |
| 2.5 Backtest kapitaltot | **BESTEHT NOCH**, Block 1 **nicht** betroffen |
| 2.6 ccxt-Gebühren | **GEGENSTANDSLOS** für den Produktivcode |
| 2.7 app.py-Selbststart | **GEKLÄRT** — kein Automatismus |
| 2.8 Umgebungsproblem | **BESTEHT NOCH** — einmal getroffen, Regel eingehalten |

---

## 2.1 ENTWICKLERHANDBUCH.md — Nullbytes · BESTEHT NOCH

**Gemessen** (`ENTWICKLERHANDBUCH.md`, 250 362 B, mtime 04.08. 02:51:46):

| Datei | Größe | Nullbytes | Anteil | erster Null-Offset |
|---|---|---|---|---|
| `ENTWICKLERHANDBUCH.md` | 250 362 B | **68 328** | 27,29 % | 0 |
| `ENTWICKLERHANDBUCH.md.bak_2026-07-31` | 246 002 B | **68 328** | 27,78 % | 0 |
| `ENTWICKLERHANDBUCH_KORRUPT_28072026.md` | 201 356 B | **68 328** | 33,93 % | 0 |

**Korrektur der Meldung:** Der Anteil beträgt heute 27,29 %, nicht 34,5 %.
Die 33,93 % der KORRUPT-Datei vom 28.07. kommen dem gemeldeten Wert nahe.
Die **absolute** Schadensgröße ist in allen drei Dateien **exakt gleich:
68 328 Bytes**. Die Datei ist seit dem 28.07. nur gewachsen, der Anteil
dadurch gesunken. "Angeblich unverändert" ist also richtig, wo es zählt.

**Struktur:** genau **ein** zusammenhängender Nullblock, Offset 0 bis
68 328. Ab Byte 68 328 folgt intakter Markdown, beginnend mit
`\n\n## EVENTS-LOG\n\n*Auto-generiert vom DocAgent*`. Es sind keine
verstreuten Nullbytes, sondern ein sauber abgeschnittener Dateikopf.

**Ursache (SCHLIESSE, Konfidenz 80):** Das Muster „ein Nullblock ab Offset
0, Rest intakt" ist die Signatur eines NTFS-*delayed write* bei hartem
Systemabbruch: die Datei wurde auf die neue Länge erweitert, die späteren
Cluster wurden committed, die früheren nicht. Ein Codefehler in
`features/doc_agent.py` scheidet als Erstursache aus — der Agent hängt nur
unter `## EVENTS-LOG` an (`_append_to_handbook`, `:145-175`) und schreibt
den Dateianfang unverändert zurück. Er **konserviert** den Schaden, er
erzeugt ihn nicht: `open(..., encoding="utf-8")` akzeptiert `\x00` als
gültiges U+0000, wirft also keinen Fehler.

**Was das Projekt bereits richtig macht:** `_rotate_backups` (`:116-143`)
erkennt Nullbytes über `_has_nullbytes` (`:108-114`) und setzt die
Backup-Rotation aus, damit korrupte Stände keine intakten überschreiben.
Beleg zur Laufzeit: `data_store/system.log`, `2026-08-03T17:22:32`,
`[WARN] [DOC] Handbuch enthaelt Nullbytes - Backup-Rotation ausgesetzt`.
Das ist der Grund, warum es keine `.bak1/.bak2/.bak3` gibt.

**Reparaturvorschlag — NICHT ausgeführt, Plan zur Freigabe:**

1. **Zuerst nach einem intakten Stand suchen.** Im Projekt gibt es keinen:
   alle drei Kopien haben denselben Schaden. Ungeprüft sind
   Windows-Vorgängerversionen (Volumeschattenkopien). Das ist der einzige
   Weg zu den verlorenen 68 328 Bytes und muss **vor** jeder Reparatur
   passieren, weil er sonst wertlos wird.
2. **Falls nichts gefunden:** Nullblock abschneiden, nicht überschreiben.
   Konkret: `neu = alt[68328:]`, als `ENTWICKLERHANDBUCH.md` schreiben, das
   Original als `ENTWICKLERHANDBUCH.md.nullbyte_20260804` daneben behalten.
   Ergebnis: 182 034 B intakter Inhalt, der komplette EVENTS-LOG bleibt.
   Verloren bleibt der Handbuchkopf (Kapitelstruktur), der aus
   `ARCHITEKTUR.md`, `AUSWERTUNG-HANDBUCH.md` und `INVENTAR.md`
   rekonstruierbar wäre.
3. **DocAgent härten** (getrennte Freigabe): in `_append_to_handbook` vor
   dem Zurückschreiben prüfen, ob der gelesene Inhalt Nullbytes enthält,
   und den Schreibvorgang dann verweigern statt den Schaden erneut
   festzuschreiben. Heute schreibt jeder Event-Eintrag die 68 KB Nullen neu.

Ich habe nichts davon ausgeführt — du wolltest den Plan vorher sehen.

---

## 2.2 cockpit_server.py:112 — E7-Fenster · BESTEHT NOCH

**Beleg:**
- `cockpit_server.py:112`:
  `E7 = [t for t in sells if dt(t) >= datetime(2026, 7, 17, tzinfo=timezone.utc)]`
  → Fensterbeginn **17.07.2026 00:00 UTC**.
- `e7_auswertung.py:36`: `E7_DEPLOY = "2026-07-17T12"  # Messbeginn`
- `UEBERGABE-AN-CHAT_28072026.md:464`: `| **Deploy** | 17.07.2026 12:00 |`
- `AUSWERTUNG-HANDBUCH.md:487` benennt genau diesen Fehler bereits.

Differenz: **exakt 12 Stunden zu früh**. Die Journal-Zeitstempel sind
UTC-aware (`2026-06-10T20:53:07.685317+00:00`), ein Zeitzonenfehler kommt
also nicht hinzu — es ist reine Stunden-Auslassung.

**Fix trivial und isoliert** (reine Auswertungsdatei, kein
Entscheidungspfad). Diff:

```diff
--- a/cockpit_server.py
+++ b/cockpit_server.py
@@ -110,7 +110,9 @@
     E61 = [t for t in sells if dt(t) >= datetime(2026, 7, 14, tzinfo=timezone.utc)]
-    E7  = [t for t in sells if dt(t) >= datetime(2026, 7, 17, tzinfo=timezone.utc)]
+    # E7 wurde am 17.07.2026 um 12:00 UTC deployed, nicht um 00:00.
+    # Quelle: e7_auswertung.py:36 (E7_DEPLOY = "2026-07-17T12").
+    E7  = [t for t in sells if dt(t) >= datetime(2026, 7, 17, 12, tzinfo=timezone.utc)]
     out["e61"] = _rr(E61); out["e7"] = _rr(E7)
```

**Nicht eingebaut.** `cockpit_server.py` steht zwar nicht auf deiner
Sperrliste (`risk/`, `portfolio/`, `execution/`, `agents/`, `config.json`,
`app.py`), aber die Kennzahl ändert sich sichtbar — das gehört freigegeben,
nicht nebenbei gemacht. Auswirkung: E7-Fenster verliert die Sells vom
17.07. zwischen 00:00 und 12:00 UTC.

**Zusatzbefund:** `E61` verwendet dieselbe Konstruktion für den 14.07.
Ob E6.1 um 00:00 UTC deployed wurde, habe ich **nicht** verifiziert —
NICHT ENTSCHEIDBAR ohne Deploy-Zeitpunkt aus dem Register.

---

## 2.3 e7_final.txt · BESTEHT NOCH (Datei fehlt), Skript lauffähig

`ls e7_*.txt` → keine Datei. `e7_final.txt` wurde nie erzeugt.

`e7_auswertung.py` (8 004 B, mtime 22.07. 22:24) ist **read-only** —
kein `open(...,"w")`, kein `write`, kein `json.dump`, kein `shutil`,
kein `os.replace`, kein `os.remove`. Ausführung war deshalb unbedenklich.

**Ausgabe von heute (04.08.2026 06:34), unkommentiert:**

```
[1] FENSTER (ab 2026-07-17, 54 Sells)
    WR 74% | AvgWin +0.83$ | AvgLoss -1.24$
    R/R 0.67  (Basis E6.1: 0.54)  -> K1 erfuellt
    Gesamt-P&L: +15.98$
[2] E7-UP-BILANZ
    Treffer gesamt: 5 | Coins: ['ADA/USDC']
    Wirksam (PnL>=1%): 2 | Neutral (<1%): 3
[3] GEGENPROBE (E7 vs alte Leiter, Kerzen 1h)
    07-20T20:03 ADA/USDC: E7 +1.91% vs ALT +1.32% = +0.59pp (+0.62$)
    07-21T07:22 ADA/USDC: E7 +3.03% vs ALT +0.19% = +2.84pp (+1.57$)
[4] URTEIL (vorregistrierte Kriterien)
    K1 R/R >= 0.54:            JA (0.67)
    K2 Gegenprobe-Summe > 0:      JA (+3.42pp ueber 2 Faelle)
    K4 mind. 3 wirksame Faelle:   NEIN (2)
    >> DATENLAGE ZU DUENN. E7-Fenster verlaengern, weiter sammeln.
```

Das Skript nutzt selbst `E7_DEPLOY = "2026-07-17T12"` und ist damit von
Punkt 2.2 **nicht** betroffen. Wie beauftragt: nur ausgeführt und
dokumentiert, keine Schlussfolgerung fürs Programm.

---

## 2.4 E8 Nachkauf-Stop · nie installiert, und GEGENSTANDSLOS

**Installer existiert** (`install_e8_nachkauf_stop.py`, 8 182 B,
mtime 29.07. 14:55; identische Zweitkopie `install_e8_nachkauf_stop(1).py`
vom 29.07. 15:09).

**Anker-Prüfung gegen das heutige `app.py`:**

| Element | in app.py |
|---|---|
| `MARKER = "E8_NACHKAUF_ERLAUBT"` | **0 Vorkommen** → nicht installiert |
| `ANKER_1` (sys.path-Block) | **1 Vorkommen** → passt |
| `ANKER_2` (`is_nachkauf = False` … `pos = self.risk_engine.open_positions[coin]`) | **1 Vorkommen** → passt |

Beide Anker sind eindeutig; der Installer wäre technisch noch lauffähig.
**Nicht installiert**, wie angewiesen.

### Zusatzfrage: Ist E8 überhaupt noch nötig? — Nein.

Konfiguration aus `data_store/config.json`:
`position_size_pct = 20.0`, `max_exposure_per_coin_pct = 25.0`,
`dca_max_levels = 3`.

`app.py:1814-1818` blockiert einen Nachkauf, wenn
`(Coin-Wert + Nachkaufbetrag) / Equity × 100 > 25,0`. Eine frische Position
bindet 20 %; ein Nachkauf gleicher Größe ergäbe **40 %**. Das ist immer
größer als 25 % → **jeder Nachkauf wird blockiert**. Erst unter einer
Positionsgröße von 12,5 % könnte überhaupt ein erster Nachkauf passieren.

**Zahlen aus dem Journal** (`data_store/trades_v5.json`, 954 Einträge,
2026-06-10T20:53 bis 2026-07-31T02:02):

- Erstkäufe: **426** · Nachkäufe: **100**
- Nachkäufe je Coin: ADA 46, SOL 20, XRP 15, ETH 14, AVAX 4, DOT 1
- Letzte Nachkauf-Tage: 16.07. (2), 18.07. (1), 20.07. (2), 24.07. (2),
  28.07. (1), **29.07. (2)** — danach **keiner mehr**.

**Zur Laufzeit** (`data_store/system.log`, 03.08. 04:39 bis 04.08. 04:40,
also 24 Stunden): **5 116 mal** `Exposure-Limit ... kein Nachkauf`,
**0 mal** `Nachkauf-Limit erreicht`.

Der Exposure-Check greift also 5 116 mal pro Tag, der DCA-Level-Zähler nie —
weil es gar nicht erst zu Levels kommt. Der letzte Nachkauf fiel auf den
29.07., den Tag des E9-Exposure-Fixes. **E8 hätte heute keine Wirkung**,
solange `position_size_pct × 2 > max_exposure_per_coin_pct` gilt.

---

## 2.5 Backtest kapitaltot · Block 1 ist NICHT betroffen

**Betrifft es die Strategiemessung aus Block 1? Nein.**

Beleg: `messung_t034b_strategien.py:80` importiert aus `harness_ext`
ausschließlich `lade_jahr` und `TAG_MS`. Es wird **kein** `Lauf`-Objekt
instanziiert, es gibt keinen Kapitalstand, keine Positionsgröße, keine
Slot-Grenze und keine Order. Die Messung ist eine reine
Ereignis-Statistik: je Signalzeitpunkt wird der First-Touch der
Preisbarriere ermittelt (`tabelle()`, `:250-275`). Ein Signal, das bei
50 $ Eigenkapital nicht handelbar wäre, wird trotzdem gezählt — genau das
ist gewollt, weil die Frage lautet „trägt das Signal Richtung", nicht
„könnte der Harness es handeln".

Der Befund bleibt für den **Backtest-Harness** bestehen (Jahr 2: 143 von
366 Tagen), ist aber für Block 1 gegenstandslos und wurde dort deshalb
nicht behandelt.

---

## 2.6 ccxt-Gebühren · GEGENSTANDSLOS für den Produktivcode

Systematische Suche über alle `.py`-Dateien, die `ccxt` importieren, nach
`.fees`, `fetch_trading_fees`, `fetchTradingFees`, `['taker']`,
`['maker']` (`audit_bugliste.py:punkt_26`):

**Keine einzige Fundstelle im Produktivcode.** Die drei Treffer sind:

- `docs/forschungsprogramm_2026-07/code/db_fill_migration.py:165` — Kommentar
- `docs/forschungsprogramm_2026-07/code/db_scan_architektur.py:86` — Kommentar
- `docs/messungen_2026-07/code/audit_bugliste.py:128` — das Suchmuster selbst

Die beiden Kommentare dokumentieren genau diesen Bug:
*„ccxt.bybit().fees meldet maker 0,01 % / taker 0,075 % — für EU-Spot
beides falsch"*.

**Woher die Gebühren tatsächlich kommen:**
- `backtest/fees.py:9-13` — statische Tabelle, bybit maker/taker je 0,10 %
- `backtest/ausstieg_backtest.py:59-60` — `GEBUEHR = 0.001` (0,1 % je
  Seite), `SLIPPAGE = 0.0005`

Kein Fix nötig, weil nichts zu fixen ist. **Aber:** ob 0,10 % taker für
EU-Spot bei Bybit realistisch ist, ist eine andere Frage — die
Kostenschwellen aus `12_SPREAD-MESSUNG.md` (0,50 bis 1,15 %) sind
coinweise gemessen und ersetzen die Tabellenwerte in der Bewertung ohnehin.

---

## 2.7 app.py-Selbststart am 03.08. um 19:22:11 · GEKLÄRT

**Was passiert ist** (`data_store/system.log`, Zeitstempel sind UTC,
lokal = UTC+2):

| Zeit UTC | lokal | Ereignis |
|---|---|---|
| 2026-08-03T12:32:37 | 14:32:37 | letzte Zeile des laufenden Prozesses: `[WARN] [SL_TP] AVAX/USDC: Sell rejected: Sleep-Mode (696s remaining)` — **keine Abschaltmeldung, kein Traceback** |
| — | — | 4 h 50 min Lücke |
| 2026-08-03T17:22:25 | **19:22:25** | `[INFO] [APP] Konfiguration geladen (Modus: paper)` — Kaltstart |
| 2026-08-04T00:45:35 | 02:45:35 | Prozessstart des heute laufenden `python app.py`, PID 9300 |
| 2026-08-04T00:47:12 | 02:47:12 | zugehöriges `Konfiguration geladen` |

Der Prozess davor lief laut `[HEART] Uptime: 76h 37m 58s` (03.08. 12:32:36)
seit dem 31.07. gegen 07:54 UTC.

**Ursachen ausgeschlossen, mit Beleg:**

1. **`core/auto_restart.py` (AutoRestartMonitor) — GEGENSTANDSLOS.**
   `_monitor_loop` (`:44-70`) läuft als `daemon=True`-Thread **innerhalb**
   von app.py und ruft `agent["restart_fn"]()` in-process auf. Es gibt kein
   `subprocess`, kein `os.execv`, keinen Prozessstart. Stirbt app.py,
   stirbt der Thread mit. Er kann sich definitionsgemäß nicht selbst
   wiederbeleben. Registriert werden Agenten (`app.py:2505`), nicht der
   Prozess.
2. **Aufgabenplanung — ausgeschlossen.** `schtasks /query` listet genau
   **eine** projektbezogene Aufgabe: `\ForschungCapture` (nächster Lauf
   04.08. 06:32). Keine Aufgabe startet app.py.
3. **Autostart-Ordner — ausgeschlossen.** Enthält `ForschungCapture.lnk`
   und `Ollama.lnk`, sonst nur `desktop.ini`.
4. **Registry `HKCU\...\CurrentVersion\Run` — ausgeschlossen.** OneDrive,
   Firefox, NordVPN. Kein app.py.

**Schlussfolgerung (SCHLIESSE, Konfidenz 85):** Der Start am 03.08. um
19:22 lokal war ein **manueller Start**. Alle vier Automatismen sind
ausgeschlossen; ein fünfter ist mir nicht bekannt. Positiv beweisen lässt
sich „manuell" nicht — das ist die Grenze dieses Befunds.

**Der eigentlich beunruhigende Teil ist ein anderer:** Der Prozess ist am
03.08. um 12:32:37 UTC mitten im Betrieb **ohne Abschaltmeldung und ohne
Traceback** verschwunden, und zwischen 03.08. 17:22 und 04.08. 00:45 ein
zweites Mal. Zwei stille Prozesstode in 36 Stunden. Nichts abgeschaltet,
wie angewiesen — aber das ist ein eigener Befund, kein Selbststart.

**Zusatzbefund (nicht beauftragt):** Beim Start vom 04.08. 00:47 erscheinen
die **Initialisierungsmeldungen** mehrfach: `Konfiguration geladen` 3×
(alle 00:47:12), `TELEGRAM Befehls-Empfaenger` 3×, `WAECHTER` 3×,
`Bottom Detector initialisiert` 6× im Fenster 00:45–00:55. Beim Start vom
03.08. 17:22 waren sie einfach. Es läuft nur **ein** app.py-Prozess
(PID 9300) — die Initialisierung wurde also mehrfach durchlaufen.

**Der laufende Betrieb ist davon nicht betroffen** (geprüft, weil ich es
zunächst als globale Log-Verdreifachung gelesen hatte): im Fenster
03:00–04:00 UTC erscheint jede wiederkehrende Meldung 185–186 mal, was
exakt der Decision-Loop-Frequenz von rund 19,5 Sekunden entspricht, und
von 7 454 BUY-Signalzeilen nach 00:47 ist **keine einzige** eine exakte
Wiederholung ihrer Vorzeile. Zählungen über `system.log` sind also
belastbar; nur die Startup-Meldungen sind aufgebläht.

---

## 2.8 Umgebungsproblem · BESTEHT NOCH, Regel eingehalten

Es hat mich getroffen: die beiden **ersten** PowerShell-Aufrufe der Sitzung
(`Get-ChildItem` auf Projektwurzel und `docs/`) lieferten vollständigen
Output, terminierten aber nicht und liefen in den 2-Minuten-Timeout.
Kosten: 4 Minuten.

**Danach sofort auf Bash umgestellt** — dort funktionierten `tasklist`,
`wmic`, `schtasks` und `reg query` ohne Hänger. Die Aufgabenplanung habe
ich **einmal** abgefragt, nicht mehrmals. Kein drittes Timeout, keine
Wiederholungsschleife.

**Für die nächste Sitzung:** PowerShell für Verzeichnis- und
Prozessabfragen in diesem Projekt meiden, direkt Bash nehmen.

---

## Untersuchte Dateien

| Datei | Größe | mtime |
|---|---|---|
| `ENTWICKLERHANDBUCH.md` | 250 362 B | 04.08. 02:51:46 |
| `ENTWICKLERHANDBUCH.md.bak_2026-07-31` | 246 002 B | 31.07. 10:58:31 |
| `ENTWICKLERHANDBUCH_KORRUPT_28072026.md` | 201 356 B | 28.07. 01:17:19 |
| `cockpit_server.py` | — | — |
| `e7_auswertung.py` | 8 004 B | 22.07. 22:24:33 |
| `install_e8_nachkauf_stop.py` | 8 182 B | 29.07. 14:55:23 |
| `core/auto_restart.py` | 3 635 B | 06.05. 11:18 |
| `features/doc_agent.py` | — | — |
| `app.py` | 132 847 B | 29.07. 20:45:56 |
| `data_store/system.log` | 12 512 389 B | 04.08. 06:27 |
| `data_store/trades_v5.json` | 330 258 B | 04.08. 06:27 |
| `data_store/config.json` | — | — |

Alle nur gelesen. Keine Datei geändert, keine gelöscht, kein Prozess
gestartet oder gestoppt.

**Nächster sicherer Schritt:** Freigabe zu 2.1 (Vorgängerversionen prüfen)
und 2.2 (Ein-Zeilen-Fix in `cockpit_server.py`) einholen.
