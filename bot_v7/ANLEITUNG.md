# ⚡ TRADING IMPERIUM V6 – BEDIENUNGSANLEITUNG
## Fuer Anfaenger – Schritt fuer Schritt erklaert

---

## WAS IST DIESER BOT?
Ein automatischer Krypto-Trading-Bot, der selbststaendig Bitcoin, Ethereum
und andere Coins kauft und verkauft. Er nutzt 20 verschiedene KI-Agenten
die zusammenarbeiten um die besten Zeitpunkte zu finden.

**WICHTIG:** Starte IMMER zuerst im Demo-Modus (Paper Trading)!
Im Demo-Modus wird mit virtuellem Geld gehandelt (10.000$ Startguthaben).

---

## INSTALLATION (Windows)

### Schritt 1: Python installieren
- Gehe auf https://www.python.org/downloads/
- Lade Python 3.13 herunter und installiere es
- WICHTIG: Haken bei "Add Python to PATH" setzen!

### Schritt 2: Bibliotheken installieren
- Oeffne CMD (Windows-Taste, "cmd" eingeben, Enter)
- Kopiere und fuehre diese Befehle nacheinander aus:
```
pip install ccxt --upgrade
pip install pandas pandas_ta numpy
pip install customtkinter matplotlib mplfinance
pip install psutil requests
pip install scikit-learn
pip install websocket-client
pip install praw
pip install beautifulsoup4
```

### Schritt 3: Bot starten
- Entpacke die ZIP-Datei auf den Desktop
- Oeffne CMD
- Tippe: `cd Desktop\trading_imperium_v6`
- Tippe: `python app.py`
- Der Bot oeffnet sich!

---

## DIE 8 TABS ERKLAERT

### 1. COCKPIT (Hauptbildschirm)
Was du siehst:
- Oben: USDC-Guthaben, Session P&L, BTC gesamt, Strategie, Zyklus, Trades
- Mitte: Coin-Karten mit Kerzen-Charts (gruen=Kurs steigt, rot=faellt)
- Gelbe Linie = EMA20 (Durchschnitt 20 Kerzen)
- Gestrichelte blaue Linie = VWAP (Volumen-gewichteter Durchschnitt)
- Unter jeder Karte: VERKAUFEN Button (manuell verkaufen)

Einstellungen (oben):
- Stop-Loss %: Bei wie viel % Verlust automatisch verkauft wird (Standard: 4%)
- Trailing %: Schuetzt Gewinne – wenn Kurs 1.5% faellt wird verkauft
- Position %: Wie viel % des Guthabens pro Trade investiert wird
- Max Trades: Maximale gleichzeitige Positionen
- Anwenden: Speichert die Aenderungen
- Sparplan: BTC-Sparplan AN/AUS

### 2. MANUELL (Handeln per Hand)
- Waehle einen Coin aus dem Dropdown
- Gib einen Betrag in $ ein
- Klicke KAUFEN oder VERKAUFEN
- ALLES VERKAUFEN: Verkauft alle offenen Positionen sofort

### 3. BACKTEST (Strategie testen)
- EINZELTEST: Testet einen Coin mit historischen Daten
- MULTI-COIN TEST: Testet 8 Coins und erstellt Rangliste
- OPTIMIZER: Findet automatisch die besten Parameter (SL, Trail, Pos)
  → Die besten Werte werden automatisch eingesetzt!
- Kerzen: Wie viele Kerzen getestet werden (max 1000)
- Timeframe: 5m, 15m, 1h, 4h, 1d

### 4. BTC (Bitcoin Akkumulation)
- Zeigt wie viel BTC du angesammelt hast
- Sparplan-Status (AN/AUS, Intervall, Betrag)
- Kauf-Historie aller BTC-Kaeufe
- Der Bot kauft automatisch BTC wenn er Gewinne macht

### 5. HISTORY (Trade-Verlauf)
- Alle bisherigen Trades (Kaeufe und Verkaeufe)
- Filter: Alle, nur BUY, nur SELL, nur Gewinne, nur Verluste
- Analyse Export: Erstellt eine .txt Datei mit allen Details

### 6. AGENTS (KI-Agenten Status)
Hier siehst du welche Agenten aktiv sind:
- 🟢 Gruen = Laeuft
- 🟡 Gelb = Langsam/Neustart
- 🔴 Rot = Fehler/Gestoppt

Die 20 Agenten und was sie tun:
| Agent | Aufgabe |
|-------|---------|
| Data Agent | Holt Kursdaten von Binance |
| Strategy Brain | Waehlt die beste Strategie |
| Signal Agent | Erkennt Kauf/Verkauf-Signale |
| Zyklustheorie | Erkennt ob Bullen- oder Baerenmarkt |
| Risk Agent | Verhindert zu grosse Verluste |
| Portfolio Agent | Verhindert dass zu viel in einem Coin steckt |
| Execution Engine | Fuehrt die Orders aus |
| LLM Agent | Erklaert Entscheidungen auf Deutsch |
| Telegram | Schickt dir Nachrichten aufs Handy |
| BTC Akkumulator | Kauft automatisch Bitcoin |
| Regime Detector | Erkennt Markt-Stimmung (Trend/Seitwaerts) |
| Multi-Timeframe | Prueft Signal auf 4 Zeitebenen |
| Capitol Trades | Ueberwacht US-Politiker Trades |
| Funding Rates | Ueberwacht Futures-Markt |
| Whale Alerts | Erkennt grosse Transaktionen |
| RL Feedback | Lernt aus vergangenen Trades |
| Grid Trader | Handel in Preisrastern |
| Smart Entry | Wartet auf besten Einstiegspunkt |
| Arbitrage | Findet Preisunterschiede zwischen Boersen |
| Adaptive Sizing | Passt Positionsgroesse intelligent an |

### 7. SETTINGS (Einstellungen)
- Exchange API: Binance API Key und Secret eingeben
- Risk: Stop-Loss, Max Positionen, Kill-Switch
- Sparplan: BTC DCA AN/AUS, Prozentsatz
- Telegram: Token und Chat-ID fuer Benachrichtigungen
- SESSION ZURUECKSETZEN: Loescht alle Daten und startet frisch

### 8. LOG (Protokoll)
- Zeigt in Echtzeit was der Bot tut
- Jede Zeile zeigt: [Uhrzeit] [Modul] Nachricht
- Gut zum Debuggen bei Problemen

---

## WEB-DASHBOARD
Nach dem Start: Oeffne http://localhost:5000 im Browser
- Zeigt alle wichtigen Daten im Browser
- Funktioniert auch auf dem Handy (gleiches WLAN)
- Aktualisiert sich alle 10 Sekunden

---

## DEMO vs LIVE MODUS

### Demo (Standard)
- Kein echtes Geld, kein Risiko
- 10.000$ virtuelles Guthaben
- Perfekt zum Testen und Lernen

### Live (nur fuer Erfahrene!)
- Handelt mit echtem Geld auf Binance
- Benoetigt Binance API Key
- Settings-Tab -> API Key + Secret eingeben
- ERST nach 3 Monaten erfolgreichem Paper Trading!

---

## HAEUFIGE FRAGEN

**Warum kauft der Bot nicht?**
→ Der Fear & Greed Index muss unter 25 sein (Angst im Markt)
  ODER das Signal-Score muss mindestens 3/10 sein.

**Was bedeutet "Keine Rueckmeldung"?**
→ Normal beim Backtest mit vielen Kerzen. Warte 30-60 Sekunden.

**Wie bekomme ich Telegram-Nachrichten?**
→ Erstelle einen Telegram-Bot via @BotFather
→ Trage Token und Chat-ID im Settings-Tab ein

**Was passiert bei einem Crash?**
→ Der Bot speichert seinen Zustand alle 60 Sekunden
→ Beim Neustart werden offene Positionen wiederhergestellt

---

Erstellt: April 2026 | Trading Imperium V6

---

## SL / HOLD / TP – Per-Coin Kontrolle (NEU!)

Unter jedem Coin-Chart gibt es 3 Buttons:

| Button | Was passiert |
|--------|-------------|
| **SL** (Standard) | Stop-Loss aktiv. Bot verkauft automatisch bei Verlust (z.B. -4%) oder wenn Trailing-Stop greift. Normal-Modus. |
| **HOLD** | KEIN automatischer Verkauf! Der Bot haelt den Coin egal was passiert. Nur manueller Verkauf moeglich. Gut wenn du glaubst der Kurs kommt zurueck. |
| **TP** | Take-Profit Modus. Bot verkauft automatisch bei +3% Gewinn. Gut fuer schnelle Gewinne in Seitwaertsmaerkten. |

### Wann welchen Modus nutzen?
- **SL:** Standard, fuer die meisten Situationen
- **HOLD:** Wenn du an einen Coin glaubst und Crashs aussitzen willst
- **TP:** Wenn der Markt seitwaerts laeuft und du kleine Gewinne mitnehmen willst

---

## PORTS (V6 benutzt andere als V4!)
- **V4 Dashboard:** http://localhost:5000
- **V6 Dashboard:** http://localhost:5050
- **V6 Webhook:** http://localhost:5051/webhook

So koennen V4 und V6 gleichzeitig laufen!

---

## TRADINGVIEW WEBHOOK
1. Erstelle einen TradingView-Alert mit Webhook-URL: `http://localhost:5051/webhook`
2. Alert-Body (JSON):
```json
{"action": "buy", "ticker": "BTCUSDC", "price": 72000}
```
oder:
```json
{"action": "sell", "ticker": "ETHUSDC"}
```
3. Der Bot empfaengt das Signal und fuehrt es ueber die normale Pipeline aus
   (Risk-Check → Portfolio-Check → Execution)

---

## LATENZ-MONITORING
- Bot prueft alle 5 Minuten die Latenz zu Binance
- Ziel: unter 500ms
- Alle 24 Stunden: Auto-Export aller Daten + Cache-Clear
- Export wird als `auto_export_DATUM.txt` gespeichert

