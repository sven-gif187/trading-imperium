# Begründungen der Einmal-Skripte

**Automatisch gerettet am 12.08.2026 14:44 mit `rette_docstrings.py`.**

Die 17 `install_*.py`/`fix_*.py`-Skripte im Hauptordner haben ihre
Arbeit getan — der Code, den sie eingebaut haben, steht heute im Bot.
Als Programme sind sie wertlos und können ins Archiv.

**Aber in ihren Kopfzeilen standen die Begründungen** — warum damals
etwas gebaut wurde, oft mit Messzahlen, die sonst nirgends im Projekt
stehen. Diese Datei hält sie fest, damit beim Aufräumen das *Warum*
nicht verloren geht und nur das *Was* übrig bleibt.

Reihenfolge: alphabetisch. Der Text ist unverändert übernommen.

---

## `fix_terminal_ampel.py`

*3293 Bytes, zuletzt geändert 22.07.2026*

```
FIX: Preis-Frische-Ampel im Terminal-Tab. [TERMINAL-AMPEL 22.07.2026]
Nutzt price_age() aus dem P4-Frische-Fix (market_data.py) und zeigt
in der Kopfzeile, wie alt der aelteste Preis ist:
   Preise 3s OK     (gruen,  < 30s)
   Preise 45s alt   (gelb,   30-120s)
   Preise 210s ALT! (rot,    > 120s  -> Feed haengt)
Faellt price_age zurueck (P4-Fix nicht installiert), zeigt sie nichts.
Nur Anzeige. Idempotent, Backup, AST.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\fix_terminal_ampel.py" > "C:\Users\<BENUTZER>\Desktop\ampel_log.txt" 2>&1
```

---

## `fix_terminal_e7count.py`

*2505 Bytes, zuletzt geändert 20.07.2026*

```
FIX: Terminal-Tab zeigt E7-UP direkt an - nie wieder findstr noetig.
[1] Neue Zeile im Risk Manager: "E7-UP Verkaeufe: N seit Deploy"
[2] Letzte-5-Verkaeufe: E7-UP-Tag ueberlebt die Textkuerzung und
    wird als " [E7-UP]" angehaengt.
Nur Anzeige (ui/terminal_tab.py). Idempotent, Backup, AST.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\fix_terminal_e7count.py" > "C:\Users\<BENUTZER>\Desktop\e7count_log.txt" 2>&1
```

---

## `fix_terminal_regime.py`

*1955 Bytes, zuletzt geändert 17.07.2026*

```
FIX: Terminal-Tab zeigt zusaetzlich das ROHE Regime (Quelle des E7-Triggers)
neben dem Risiko-Profil - beendet die Verwirrung BRAIN vs MONITOR.
Nur Anzeige (ui/terminal_tab.py). Idempotent, Backup, AST.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\fix_terminal_regime.py" > "C:\Users\<BENUTZER>\Desktop\regime_log.txt" 2>&1
```

---

## `install_chart_refresher.py`

*4860 Bytes, zuletzt geändert 22.07.2026*

```
================================================================
  CHART-AUTO-REFRESHER Installer (21.07.2026)
  Schluss mit manuellem Aktualisieren der 12 Coins!
================================================================
[A] Legt features/chart_refresher.py an: ein Hintergrund-Thread,
    der den Kerzen-Cache automatisch frisch haelt (alle 60 min,
    beim Start sofort einmal). Nutzt die vorhandene
    ChartData.load_all() - gleiche Logik wie der Charts-Tab.
[B] Startet ihn in app.py direkt nach dem Scheduler, isoliert in
    try/except - kann den Bot NICHT crashen.

REINE DATENpflege - kein Trading-Eingriff, E7-Messung unberuehrt.
Daemon-Thread, alle Fehler abgefangen. Idempotent, AST, Backup.

  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_chart_refresher.py" > "C:\Users\<BENUTZER>\Desktop\chartref_log.txt" 2>&1
================================================================
```

---

## `install_daily_loss_p5.py`

*6869 Bytes, zuletzt geändert 20.07.2026*

```
================================================================
  P5 DAILY-LOSS NEUBAU (20.07.2026) - Modus SCHATTEN
================================================================
[A] Legt daily_loss.py NEBEN die Datei mit is_paused_by_daily_loss()
    (Ordner wird automatisch gefunden, Import passt sich an).
    EINE Wahrheit fuer den Tagesverlust: realisierter Tages-P&L aus
    dem Journal (neustart-fest), lokaler Kalender, ein Regler.
    Reaktion ist ausschliesslich KAUFPAUSE - NIEMALS ein Verkauf.
[B] Verdrahtet is_paused_by_daily_loss() auf das neue Modul.
    app.py bleibt unberuehrt, alte Logik bleibt als
    _alt_is_paused_by_daily_loss erhalten.

VORGABE-MODUS "schatten": rechnet + protokolliert nach
data_store/daily_loss_schatten.json, greift NICHT ein.
-> Keine Verhaltensaenderung, waehrend des E7-Fensters sicher.
config.json wird NICHT angefasst (Bot darf laufen).

Idempotent, AST-Syntaxcheck, Backup. Wirkt nach Neustart.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_daily_loss_p5.py" > "C:\Users\<BENUTZER>\Desktop\p5_log.txt" 2>&1
================================================================
```

---

## `install_e7_trailing.py`

*4604 Bytes, zuletzt geändert 14.07.2026*

```
================================================================
  E7 PHASEN-TRAILING (vorregistriert 11.07., gebaut 14.07.2026)
================================================================
VORAUSSETZUNG: install_exit_einheit.py MUSS vorher deployed sein
(sonst hebelt das flache Agent-Trailing E7 aus). Der Installer
prueft das selbst und bricht sonst ab.

WAS: Nur im bestaetigten Aufwaertstrend (Regime TRENDING_UP) wird
die Stufen-Leiter gelockert, damit Trends laufen koennen:
  Zone 1-3%:  x1.0 -> x2.0     Zone 3-5%: x0.7 -> x1.4
  Zone >=5%:  x0.5 -> x1.0     Zone <1%:  x1.6 (unveraendert)
In ALLEN anderen Regimen (RANGING/VOLATILE/TRENDING_DOWN): alles
exakt wie bisher. Kerzen-Sim-Basis: nach Exits lief der Kurs im
Schnitt +2.66% weiter, in UP-Phasen +3.72%.

E7-Exits sind im Verkaufsgrund am Zusatz "E7-UP" erkennbar.

Ausfuehren (Deploy-Zeitpunkt: siehe E7-Registrierung):
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_e7_trailing.py" > "C:\Users\<BENUTZER>\Desktop\e7_log.txt" 2>&1
================================================================
```

---

## `install_e8_nachkauf_stop(1).py`

*8182 Bytes, zuletzt geändert 29.07.2026*

```
install_e8_nachkauf_stop.py  —  EPOCHE E8
==========================================
Schaltet Nachkaeufe in BESTEHENDE Positionen ab (Averaging Down).
Der ERSTE Einstieg (Fear&Greed-DCA in eine neue Position) bleibt unveraendert.

Hintergrund (Datenbasis V4 + V6, 27.07.2026):
    Positionen OHNE Nachkauf : +75 $   (R/R 0.82)
    Positionen mit 2 Nachkaeufen : -65 $
    Positionen mit 3+ Nachkaeufen: -47 $
    V4 (grosser Datensatz)   : ohne +460 $ / mit 4+ -1.419 $
    => Der Einstieg funktioniert. Das Leck ist das Nachkaufen.

ZIEL: C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\app.py

EIGENSCHAFTEN
    - idempotent (zweiter Lauf meldet "bereits gepatcht", aendert nichts)
    - Backup mit Zeitstempel (.bak_e8_JJJJMMTT_HHMMSS)
    - musterbasiert, NICHT zeilennummernbasiert
    - CRLF-Zeilenenden bleiben erhalten
    - AST-Syntaxpruefung; bei Fehler automatischer Rueckbau aus dem Backup
    - Datums-Guard: warnt, wenn vor dem 01.08.2026 ausgefuehrt

ROLLBACK
    In app.py  E8_NACHKAUF_ERLAUBT = True  setzen und Bot neu starten.
    Kein erneutes Patchen noetig.

WICHTIG: Bot vorher vollstaendig beenden.
```

---

## `install_e8_nachkauf_stop.py`

*8182 Bytes, zuletzt geändert 29.07.2026*

```
install_e8_nachkauf_stop.py  —  EPOCHE E8
==========================================
Schaltet Nachkaeufe in BESTEHENDE Positionen ab (Averaging Down).
Der ERSTE Einstieg (Fear&Greed-DCA in eine neue Position) bleibt unveraendert.

Hintergrund (Datenbasis V4 + V6, 27.07.2026):
    Positionen OHNE Nachkauf : +75 $   (R/R 0.82)
    Positionen mit 2 Nachkaeufen : -65 $
    Positionen mit 3+ Nachkaeufen: -47 $
    V4 (grosser Datensatz)   : ohne +460 $ / mit 4+ -1.419 $
    => Der Einstieg funktioniert. Das Leck ist das Nachkaufen.

ZIEL: C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\app.py

EIGENSCHAFTEN
    - idempotent (zweiter Lauf meldet "bereits gepatcht", aendert nichts)
    - Backup mit Zeitstempel (.bak_e8_JJJJMMTT_HHMMSS)
    - musterbasiert, NICHT zeilennummernbasiert
    - CRLF-Zeilenenden bleiben erhalten
    - AST-Syntaxpruefung; bei Fehler automatischer Rueckbau aus dem Backup
    - Datums-Guard: warnt, wenn vor dem 01.08.2026 ausgefuehrt

ROLLBACK
    In app.py  E8_NACHKAUF_ERLAUBT = True  setzen und Bot neu starten.
    Kein erneutes Patchen noetig.

WICHTIG: Bot vorher vollstaendig beenden.
```

---

## `install_geldfluss_tab.py`

*3559 Bytes, zuletzt geändert 20.07.2026*

```
================================================================
  GELDFLUSS-TAB Installer (20.07.2026) - reine ANZEIGE
================================================================
[A] Erstellt ui/geldfluss_tab.py (Intermarket-Deck: Landkarte der
    Marktgroessen, BTC-Dominanz-Rotation, Asset-Rennen BTC/Gold/S&P,
    Ratios, taegliches Snapshot-Archiv geldfluss_history.json)
[B] Haengt den Tab in ui/main_window.py ein - nach dem ZYKLUS-Tab,
    isoliert in try/except, kann den Bot NIE crashen.
Netz-Quellen: CoinGecko /global (kein Key) + yfinance (wie Metals).
Trading-Logik bleibt zu 100% unberuehrt. Idempotent, AST, Backup.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_geldfluss_tab.py" > "C:\Users\<BENUTZER>\Desktop\geldfluss_log.txt" 2>&1
================================================================
```

---

## `install_metals_stufe2.py`

*3449 Bytes, zuletzt geändert 27.06.2026*

```
================================================================
  EDELMETALL STUFE 2 - Trendfilter (patcht metals/metals_engine.py)
================================================================
Problem:
  Die Engine gibt EINSTIEG/STARKER EINSTIEG allein anhand des
  Score-Summenwerts. In einem Abwaertstrend treiben ueberverkaufte
  Indikatoren (RSI, Bollinger unten, Naehe Support) den Score
  trotzdem hoch -> Dip-Kauf ins fallende Messer. ALLE 5 bisherigen
  Signale waren genau deshalb Verluste.

Fix (Stufe 2):
  Nach der Signal-Entscheidung ein Veto: ist der Trend bestaetigt
  ABWAERTS (SMA50 < SMA200) und das Signal ein Einstieg, wird es
  auf WARTEN heruntergestuft. Kein Einstieg gegen den Trend.
  HALTEN/WARTEN bleiben unveraendert; Aufwaertstrend-Einstiege
  bleiben voll erhalten.

  Reine Analyse-Logik. Der Tab handelt nicht - kein Bot-Einfluss.

Idempotent. Backup .bak. AST-Check. CRLF bleibt CRLF.
Wirkt beim naechsten Bot-Neustart.
================================================================
```

---

## `install_metals_stufe3.py`

*10305 Bytes, zuletzt geändert 27.06.2026*

```
================================================================
  EDELMETALL STUFE 3 - Long/Short (patcht metals_engine.py + metals_tab.py)
================================================================
Bisher kennt der Tab nur LONG (Dip kaufen). Stufe 3 erlaubt im
bestaetigten Abwaertstrend ein SHORT-Signal statt nur WARTEN -
aber NUR wenn der Kurs in eine Verkaufszone hochgelaufen ist
(kein Short am ueberverkauften Boden). Plus LONG/SHORT-Anzeige.

WICHTIG: Ein SHORT gewinnt, wenn der Kurs FAELLT. Darum wird auch
das Tracking (WIN/LOSS) richtungsabhaengig gespiegelt - sonst
wuerden Shorts falsch gebucht.

4 Aenderungen:
  metals_engine.py
    E1) analyze_metal: Richtung bestimmen + SHORT-Signal +
        richtungsabhaengige SL/TP + is_entry/direction im Return.
    E2) _check_open_signal: WIN/LOSS fuer SHORT gespiegelt
        (Stop ueber Einstieg, Ziel darunter).
    E3) track_signals: direction im Journal-Eintrag mitspeichern.
  metals_tab.py
    T1) _render: LONG (gruen) / SHORT (rot) anzeigen.

VORAUSSETZUNG: Stufe 2 (Trendfilter) sollte vorher installiert sein.
Alte Journal-Signale ohne 'direction' gelten automatisch als LONG.
Reine Analyse-Logik - der Tab handelt nicht.

Idempotent (Marker 'STUFE-3' je Datei). Backup .bak. AST-Check.
CRLF bleibt CRLF. Wirkt beim naechsten Bot-Neustart.
================================================================
```

---

## `install_mfe_mae_logging.py`

*7473 Bytes, zuletzt geändert 25.07.2026*

```
install_mfe_mae_logging.py
==========================================================================
Idempotenter Installer fuer MFE/MAE-Logging + pnl_pct/fee-Regression-Fix
im Exit-Monitor (runtime/exit_monitor.py).

WAS ES TUT (reines Logging - KEIN Eingriff ins Handelsverhalten, E7-konform):
  1. MAE-Tracking: fuehrt pos["lowest_price"] parallel zu highest_price mit.
     Wird NIE in einer Verkaufsentscheidung gelesen - nur aufgezeichnet.
  2. Schreibt mfe_pct + mae_pct in den SELL-Journal-Eintrag
     (Hoechst-/Tiefststand relativ zum Einstand, in %).
  3. Regression-Fix: pnl_pct + fee werden wieder ins SELL-Journal geschrieben
     (seit ~15.07. fehlend). Beide Werte liegen bereits berechnet daneben.

WAS ES NICHT TUT:
  - kein sell_reason / strategy / Schwellen-Wert wird veraendert
  - keine Kauf-/Verkauf-Logik wird angefasst
  - trailing/SL/TP unveraendert

SICHERHEIT:
  - marker-basiert idempotent (mehrfaches Ausfuehren = No-Op)
  - AST-Syntaxcheck NACH dem Patch, Rollback bei Fehler
  - .bak-Backup vor jeder Aenderung
  - EOL (CRLF) wird beibehalten

ZIELDATEI (BITTE SELBST PLATZIEREN - ich kann nicht auf deine Platte schreiben):
  C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\runtime\exit_monitor.py

BEDIENUNG:
  1. Bot VOLLSTAENDIG schliessen (Datei wird zur Laufzeit importiert).
  2. Dieses Skript in den Projekt-Ordner legen und ausfuehren:
       cd "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)"
       python install_mfe_mae_logging.py > install_mfe_log.txt 2>&1
  3. install_mfe_log.txt hochladen zur Kontrolle.
```

---

## `install_p4_diagnose.py`

*5644 Bytes, zuletzt geändert 20.07.2026*

```
================================================================
  P4 STUFE 1: Stille Exceptions im Preis-Pfad -> Diagnose
  (20.07.2026)  KEINE Verhaltensaenderung - epochensicher
================================================================
PROBLEM (Audit-Befund, Pre-Live-Checkliste Punkt 1):
  [A] data/market_data.py  fetch_prices:  "except: pass"
      -> Preis-Abruf scheitert lautlos, ALTER Wert bleibt im Cache.
         Der Exit-Monitor rechnet dann Stops auf einem Geisterpreis.
  [B] live/live_runner.py  get_price:     "except: return 0"
      -> Preis 0 statt Fehler (Ursache des stillen Positionsverlusts).

DIESER PATCH (Stufe 1):
  Beide Stellen bekommen echtes Logging + Frische-Stempel je Coin
  (self.price_ts). Der Bot verhaelt sich EXAKT wie bisher - es wird
  nichts verworfen, nichts uebersprungen, nichts anders gehandelt.
  Nur: Fehler werden ab jetzt SICHTBAR.
  Stufe 2 (veraltete Preise aktiv verwerfen) = NACH dem E7-Fenster.

Idempotent, AST-Syntaxcheck, Backup (.bak_p4). Bot darf laufen,
wirkt nach Neustart.

Ausfuehren:
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_p4_diagnose.py" > "C:\Users\<BENUTZER>\Desktop\p4_log.txt" 2>&1
================================================================
```

---

## `install_p4_frische.py`

*4912 Bytes, zuletzt geändert 20.07.2026*

```
================================================================
  P4 ERGAENZUNG: Preis-Frische-Stempel (20.07.2026)
  KEINE Verhaltensaenderung - epochensicher
================================================================
BEFUND: Die stillen Exceptions im Preis-Pfad sind BEREITS behoben
(Marker P1-HARDEN in market_data.py + live_runner.py). live_runner
braucht nichts mehr.

DIESER PATCH ergaenzt nur data/market_data.py:
  [1] price_ts je Coin  -> wann wurde der Preis zuletzt WIRKLICH
      erneuert? (Grundlage fuer Stufe 2 + Frische-Ampel im Tab)
  [2] price_age(symbol) -> Alter in Sekunden, oder None
  [3] Log-Drosselung: Warnung beim 1., 10., 20. ... Fehlversuch
      statt bei jedem Zyklus (verhindert Log-Fluten bei Ausfall),
      plus Entwarnung wenn der Feed zurueckkommt.
Cache-Verhalten bleibt EXAKT wie bisher (alter Wert bleibt stehen).

Idempotent, AST-Syntaxcheck, Backup (.bak_p4f). Bot darf laufen,
wirkt nach Neustart.

  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_p4_frische.py" > "C:\Users\<BENUTZER>\Desktop\p4f_log.txt" 2>&1
================================================================
```

---

## `install_tagesbericht_v2.py`

*5818 Bytes, zuletzt geändert 22.07.2026*

```
================================================================
  TAGESBERICHT-FIX v2 (22.07.2026) - baut auf DOC-DEDUPE auf
================================================================
PROBLEM: write_daily_report() liest aus dem RAM-Puffer
(daily_buffer). Beim ersten Tagesstart ist der leer -> Bericht
zeigt 0 Trades / n/a. (Ein frueherer Fix wurde vom spaeteren
DOC-DEDUPE-Patch ueberschrieben.)

FIX v2: Direkt nach dem DOC-DEDUPE-Guard werden die Kennzahlen aus
dem JOURNAL (data_store/trades_v5.json) des ABGESCHLOSSENEN VORTAGS
gezogen und die RAM-Puffer-Variablen damit ueberschrieben. Der Rest
der Methode (Formatierung, Schreiben, Persist, Dedupe) bleibt
voellig unangetastet.

Nur Doku-Pfad. Idempotent (Marker TAGESBERICHT-FIX2), AST, Backup.
Bot KOMPLETT schliessen -> ausfuehren -> starten.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_tagesbericht_v2.py" > "C:\Users\<BENUTZER>\Desktop\tb2_log.txt" 2>&1
================================================================
```

---

## `install_terminal_v3.py`

*2292 Bytes, zuletzt geändert 17.07.2026*

```
================================================================
  TERMINAL-TAB v3 Installer (17.07.2026) - reine ANZEIGE
================================================================
NEU: Marktlage-Block (Zyklus/Regime, F&G mit Label, Strategie, BTC,
DXY/News, NUPL/Onchain), Performance-Block (Heute-WR, 7-Tage-P&L,
Equity + Max-Drawdown, Kapitalverlauf-Sparkline), Exposure-Zeile,
Session-Uptime in der Kopfzeile. Enthaelt alle v2-Features.
Voraussetzung: v2 installiert. Idempotent, Backup, AST.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_terminal_v3.py" > "C:\Users\<BENUTZER>\Desktop\terminal3_log.txt" 2>&1
================================================================
```

---

## `install_zyklus_tab.py`

*3550 Bytes, zuletzt geändert 19.07.2026*

```
================================================================
  ZYKLUS-TAB Installer (19.07.2026) - reine ANZEIGE
================================================================
[A] Erstellt ui/zyklus_tab.py (Bitcoin-Zyklus-Atlas: Heute-Status,
    F&G-Statistik-Tabelle, Phasen-Ranking, Extreme, 8-Jahres-
    Zeitstrahl - aus data_store/situation_history.json)
[B] Haengt den Tab in ui/main_window.py ein - nach dem TERMINAL-
    Tab, isoliert in try/except, kann den Bot NIE crashen.
Trading-Logik bleibt zu 100% unberuehrt. Idempotent, AST, Backup.
  python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\install_zyklus_tab.py" > "C:\Users\<BENUTZER>\Desktop\zyklus_log.txt" 2>&1
================================================================
```

---
