# 📖 Trading Imperium V6 — Befehls-Referenz

> Alle wichtigen CMD-Befehle für deinen Bot.
> Stand: 04.06.2026

---

## 🚀 Bot-Lifecycle

### Bot starten

```cmd
cd Desktop\trading_imperium_v6(21)
python app.py
```

Der Bot läuft jetzt 24/7. Du siehst Logs im CMD-Fenster.

### Bot stoppen

**Variante A:** CMD-Fenster schließen (X oben rechts)

**Variante B:** Im CMD-Fenster `Strg + C` drücken

### Bot neu starten

```cmd
cd Desktop\trading_imperium_v6(21)
python app.py
```

Bei Restart: Bot stellt automatisch die letzten Positionen + Balance wieder her.

---

## 📊 Monitoring & Analyse

### Impact-Report (alle Trades + Strategien)

```cmd
cd Desktop\trading_imperium_v6(21)
python impact_report.py
```

Zeigt: Summary, Strategie-Performance, Top 5 Gewinner/Verlierer, letzte 10 Trades.

### Impact-Report Varianten

```cmd
python impact_report.py --top 20                       :: 20 letzte Trades
python impact_report.py --strategy DCA_FEAR_GREED      :: Nur eine Strategie
python impact_report.py --strategy RSI_OVERSOLD        :: Nur RSI Oversold
python impact_report.py --strategy GRID_BOT            :: Nur Grid Bot
python impact_report.py --no-recent                    :: Ohne letzte Trades
python impact_report.py --no-best                      :: Ohne Best/Worst
```

### Tickets-System nutzen

Datei `tickets.txt` im V6-Hauptordner öffnen mit Editor.
Stichworte:

```
SPEICHERN: Punkt den ich nicht vergessen will
ERLEDIGT: Was ich heute geschafft habe
BUG: Fehler den ich gefunden habe
DOKUMENTIEREN: Wichtige Erkenntnis fuer Handbuch
NOTIZ: Allgemeine Notiz
```

Bot frisst die Tickets alle 30s und schreibt sie ins `ENTWICKLERHANDBUCH.md`.

---

## 🔄 Reset auf 0

**WICHTIG: Bot vorher stoppen!**

```cmd
cd Desktop\trading_imperium_v6(21)
python scripts\full_reset_final_v3.py
python app.py
```

Leert: trades_v5.json, order_history.json, bot_state.json, impact_journal.json
Bleibt intakt: brain_performance.json (Lerngold!), v4_imported_*.json

---

## 🔧 Updates/Patches installieren

**ALLE Patches verlangen: Bot vorher stoppen!**

```cmd
cd Desktop\trading_imperium_v6(21)

:: Bugfix Sammlung (V4-Sync, Threading, KI-Prognose, Rebalancer)
python install_all_fixes.py

:: Live-Trading Safety (CashReservation + RateLimit + RejectionCounter)
python install_live_safety.py

:: Impact-Journal Modul (Trade-Begruendungen)
python install_impact_journal.py

:: Impact-Journal Hooks + Brain-Tuning
python install_journal_hooks_and_tuning.py
```

Nach Patch immer: `python app.py` zum Neustart.

---

## 🔍 Diagnose-Befehle

### Wo liegt eine Datei?

```cmd
cd Desktop\trading_imperium_v6(21)
dir /s /b main_window.py
dir /s /b strategy_brain.py
dir /s /b app.py
```

### Python-Version checken

```cmd
python --version
```

Sollte zeigen: `Python 3.13.x`

### Verzeichnis-Struktur anschauen

```cmd
cd Desktop\trading_imperium_v6(21)
dir
```

### Impact-Journal Inhalt direkt anschauen (raw JSON)

```cmd
cd Desktop\trading_imperium_v6(21)
type data_store\impact_journal.json
```

### Brain-Performance anschauen

```cmd
cd Desktop\trading_imperium_v6(21)
type data_store\brain_performance.json
```

---

## 🧪 Python-Interactive Befehle

Python-Konsole starten:

```cmd
cd Desktop\trading_imperium_v6(21)
python
```

Dann im Python:

```python
# Impact-Journal Summary
from features.impact_journal import ImpactJournal
j = ImpactJournal()
print(j.get_summary())

# Performance pro Strategie
import json
print(json.dumps(j.get_strategy_stats(), indent=2))

# Beste 5 Trades
for s in j.get_best_setups(5):
    print(f"{s['symbol']}: +{s['pnl_usd']}$ ({s['strategy']})")

# Schlechteste 5 Trades
for s in j.get_worst_setups(5):
    print(f"{s['symbol']}: {s['pnl_usd']}$ ({s['strategy']})")

# Offene Positionen
for s in j.get_open_positions():
    print(f"{s['symbol']} @ {s['entry_price']} ({s['strategy']})")

# Verlassen
exit()
```

---

## 🚨 Häufige Probleme & Loesungen

### Bot startet nicht — Import-Error

```cmd
cd Desktop\trading_imperium_v6(21)
python -c "import customtkinter; print('OK')"
python -c "import ccxt; print('OK')"
```

Wenn Fehler: Bibliothek fehlt. Installation:
```cmd
pip install customtkinter ccxt pandas numpy
```

### Patches schlagen fehl — "Anker nicht gefunden"

Bedeutet: Die Datei wurde verändert (z.B. durch früheren Patch). Lösung:
1. Backup wiederherstellen (`.backup_YYYYMMDD_HHMMSS` Datei umbenennen)
2. Patches in der richtigen Reihenfolge nochmal:
   1. install_all_fixes.py
   2. install_live_safety.py
   3. install_impact_journal.py
   4. install_journal_hooks_and_tuning.py

### Permission denied bei JSON-Datei

```
[V4-SYNC] Fehler beim Auto-Sync: [Errno 13] Permission denied: 'data_store\brain_performance.json'
```

Lösung: Bot komplett beenden, dann neu starten. Datei war von vorherigem Run noch gelockt.

### Impact-Journal ist leer obwohl Trades laufen

Check: Sind die Hooks installiert?

```cmd
type app.py | findstr "IMPACT-JOURNAL HOOK"
```

Wenn KEINE Treffer: `python install_journal_hooks_and_tuning.py` ausführen.

### Bot zeigt falsche ROI / Balance

Symptom: ROI zeigt +30% obwohl gerade erst angefangen
Grund: Balance-Reload-Bug nach Reset (bekannt)
Lösung: Bot stoppen, 5 Min warten, neu starten

---

## 📁 Wichtige Dateien & Pfade

```
trading_imperium_v6(21)\
├── app.py                              :: Haupt-Datei
├── impact_report.py                    :: Report-Tool
├── tickets.txt                         :: TODO/Notes (vom Bot gelesen)
├── ENTWICKLERHANDBUCH.md               :: Auto-Dokumentation
│
├── data_store\                         :: Daten (NIE manuell editieren!)
│   ├── trades_v5.json                  :: Aktive Trades
│   ├── order_history.json              :: Order-Tracking
│   ├── bot_state.json                  :: Equity History
│   ├── brain_performance.json          :: STRATEGIE-LERNGOLD!
│   ├── impact_journal.json             :: Trade-Begruendungen
│   ├── v4_strategy_weights.json        :: V4-Wissen
│   └── v4_imported_*.json              :: V4 Trade-Import
│
├── agents\
│   └── strategy_brain.py               :: Brain-Logic
│
├── execution\
│   └── engine.py                       :: Trade-Execution
│
├── features\
│   ├── safety.py                       :: Live-Safety
│   ├── impact_journal.py               :: Impact-Journal
│   ├── tickets_watcher.py              :: Tickets-Reader
│   └── doc_agent.py                    :: Auto-Doku
│
├── ui\
│   └── main_window.py                  :: Hauptfenster GUI
│
└── scripts\
    └── full_reset_final_v3.py          :: Reset-Tool
```

---

## 🎯 Workflow für 24h-Trading-Session

### Tag-Beginn

```cmd
:: 1. Bot-Ordner
cd Desktop\trading_imperium_v6(21)

:: 2. Status checken
python impact_report.py

:: 3. Bot starten (falls noch nicht laufend)
python app.py
```

### Mid-Day Check

```cmd
:: In NEUEM CMD-Fenster (Bot läuft im ersten weiter):
cd Desktop\trading_imperium_v6(21)
python impact_report.py --top 20
```

### Tag-Ende

```cmd
:: 1. Heutige Performance loggen in tickets.txt:
:: NOTIZ: Heute: +X.XX$ realisiert, Win-Rate Y%

:: 2. Bot weiterlaufen lassen (24/7) oder stoppen
```

### Wochen-Recap

```cmd
:: Ganzen Trade-Verlauf:
python impact_report.py --top 100

:: Pro Strategie schauen welche am besten lief:
python impact_report.py --strategy DCA_FEAR_GREED
python impact_report.py --strategy RSI_OVERSOLD
python impact_report.py --strategy ICHIMOKU
```

---

## 💡 Pro-Tips

1. **CMD-Fenster in den Pin Bar** für schnellen Zugriff (Windows-Taste + drag)

2. **Mehrere CMD-Fenster** offen: eines mit dem Bot laufend, eines fuer impact_report

3. **`UP-Arrow`** im CMD: holt letzten Befehl wieder

4. **`TAB`** im CMD: vervollstaendigt Dateinamen automatisch

5. **CMD-Inhalt kopieren**: rechte Maustaste -> Markieren -> Enter

6. **Log durchsuchen**: Strg+F im CMD-Fenster oeffnet die Suche

7. **Im Bot-Ordner bleiben**: Wenn das Fenster zumacht, `cd Desktop\trading_imperium_v6(21)` immer wieder eingeben

---

## 📞 Notfall-Befehle

### Wenn Bot komplett kaputt ist

```cmd
:: 1. Bot stoppen (CMD-Fenster schließen)

:: 2. Alle .backup-Dateien anschauen:
cd Desktop\trading_imperium_v6(21)
dir /s *.backup_*

:: 3. Letztes funktionierendes Backup wiederherstellen
:: Beispiel:
copy app.py.allfixes_backup_20260603_123456 app.py

:: 4. Bot starten
python app.py
```

### Wenn impact_journal.json korrupt ist

```cmd
cd Desktop\trading_imperium_v6(21)

:: Backup erstellen
copy data_store\impact_journal.json data_store\impact_journal.json.corrupt

:: Leer machen
echo {"entries":[]} > data_store\impact_journal.json
```

### Wenn Bot keine Daten mehr lädt

```cmd
:: Reset auf 0 (loescht alles Aktive, behält Lerngold)
cd Desktop\trading_imperium_v6(21)
python scripts\full_reset_final_v3.py
python app.py
```

---

*Diese Referenz wird vom Doc-Agent automatisch im Handbuch synchronisiert.*
*Bei Fragen oder neuen Befehlen: in tickets.txt eintragen mit Stichwort DOKUMENTIEREN.*
