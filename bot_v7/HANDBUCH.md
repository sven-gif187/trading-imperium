# ⚡ TRADING IMPERIUM V6 – ENTWICKLERHANDBUCH

## Version: 6.0.0 | 93 Module | 27 Tests | Multi-Agent System

---

## INSTALLATION

### 1. Voraussetzungen
- Python 3.10+ (empfohlen 3.13)
- Windows 10/11

### 2. Alle pip-Befehle (CMD Fenster)
```
pip install ccxt --upgrade
pip install pandas pandas_ta numpy
pip install customtkinter matplotlib mplfinance
pip install psutil requests
pip install scikit-learn
pip install websocket-client
pip install praw
pip install beautifulsoup4
pip install pyngrok          (optional, fuer ngrok Public Dashboard)
```

### 3. Bot starten
```
cd Desktop\trading_imperium_v6
python app.py
```

### 4. Was passiert beim Start:
1. Config wird geladen (oder Standard erstellt)
2. DataAgent verbindet mit Binance (Test: BTC/USDC Preis)
3. Multi-Exchange: Binance + Bybit verbunden
4. UI oeffnet sich mit 8 Tabs
5. Web-Dashboard startet auf http://localhost:5000
6. ngrok Tunnel (wenn pyngrok installiert) -> Link per Telegram
7. Auto-Restart Monitor startet (ueberwacht alle Agenten)
8. WebSocket verbindet fuer Echtzeit-Preise
9. Klicke ▶ STARTEN

---

## WEB-DASHBOARD
- **Lokal:** http://localhost:5000
- **Oeffentlich:** ngrok-Link wird per Telegram geschickt (braucht pyngrok)
- Zeigt: Balance, P&L, Trades, Strategie, Zyklus, F&G
- Auto-Refresh alle 10 Sekunden
- Read-only (keine Steuerung)

---

## 8 TABS

| Tab | Funktionen |
|-----|------------|
| COCKPIT | Coin-Karten mit Kerzen-Charts + EMA20 + VWAP (gestrichelt), Preise, 24h-Change, Guthaben, VERKAUFEN-Button, Risk-Controls (SL%, Trail%, Pos%, Max Trades), Sparplan-Switch |
| MANUELL | Coin-Dropdown, Betrag/$, Menge, KAUFEN/VERKAUFEN/ALLES VERKAUFEN, Live-Preis, Trade-Log |
| BACKTEST | Einzel-Test, Multi-Coin-Test (8 Coins), OPTIMIZER (findet beste SL/Trail/Pos Parameter per Grid-Search), Coin/Timeframe/Kerzen waehlbar |
| BTC | Akkumulations-Uebersicht: BTC Gesamt, Investiert, Aktueller Wert, P&L, Ø-Preis, Kauf-Historie, Sparplan-Status |
| HISTORY | Trade-Verlauf mit Filter (Alle/BUY/SELL/Gewinn/Verlust), Stats-Zeile, Analyse-Export (wie V4) |
| AGENTS | 20 Agenten-Status-Karten mit Live-Updates und Ampel-System |
| SETTINGS | Exchange API, Risk-Parameter, Sparplan AN/AUS + %, Telegram, SESSION ZURUECKSETZEN Button |
| LOG | Echtzeit-Log aller Module |

---

## ARCHITEKTUR (93 Module, 16 Ordner)

### Core (8)
bus, events, state_store, logger, scheduler, health, exceptions, auto_restart

### Config (2)
settings, versioning (Backup bei jeder Aenderung)

### Agents (9)
signal_agent, context_agent, strategy_brain, cycle_theory,
btc_accumulator, smart_entry, grid_trader, dca_advanced, arbitrage_agent, llm_local

### Execution (9)
engine, retry_policy, circuit_breaker, idempotency, order_manager,
fill_reconciler, exchange_client, twap_executor, multi_exchange

### Risk (6)
engine, exposure, drawdown_guard, kill_switch, position_sizing, adaptive_sizing

### Portfolio (3)
agent, rebalancer, correlation_guard

### Data (12)
market_data, feature_store, news_data, sentiment_data, cache, data_quality,
capitol_trades, funding_rates, whale_alerts, reddit_sentiment,
websocket_stream, onchain_analytics, orderbook_depth, top_coins

### Features (7)
indicators, market_regime, labels, portfolio_features,
rsi_divergence, multi_timeframe, regime_detection, vwap_agent

### Models (7)
signal_model, train_pipeline, model_registry, regime_model,
xgboost_model, rl_feedback, ensemble_signal

### Backtest (7)
engine, fees, slippage, metrics, walk_forward, monte_carlo, optimizer

### Live (4)
live_runner, paper_runner, state_recovery, watchdog

### Reports (4)
telegram, daily_report, weekly_report, trade_journal

### UI (3)
main_window (8 Tabs), dashboard (Web), ngrok_dashboard

### Tests (7)
test_risk, test_execution, test_backtest, test_portfolio,
test_data, test_v6_modules, run_all (27 Tests)

---

## AGENTEN-PIPELINE (komplett)

```
Marktdaten -> DataAgent (OHLCV + 15 Indikatoren)
  -> Regime Detector (Bull/Bear/Sideways/Volatile)
  -> Multi-Timeframe (5m + 15m + 1h + 4h Confluence)
  -> VWAP Agent (Preis vs VWAP = Bias)
  -> Orderbook (Bid/Ask Imbalance)
  -> Ensemble Signal (9 Quellen gewichtet)
  -> Signal Agent (Score >= 3 -> BUY Intent)
  -> Smart Entry (Pump? -> Warte auf Pullback)
  -> Context Agent + LLM (Erklaerung auf Deutsch)
  -> Risk Engine (Veto + Kill-Switch + Drawdown)
  -> Adaptive Sizing (KI passt Betrag an)
  -> Portfolio Agent (Klumpenrisiko + Sektor-Check)
  -> TWAP (> 200$? -> Split in 3-5 Teilorders)
  -> Execution (Paper/Live + Retry + Circuit Breaker)
  -> RL Feedback (Q-Learning -> Gewichtung anpassen)
  -> BTC Akkumulator (Gewinne -> BTC)
  -> Telegram Reporter (Alerts + Berichte)
```

---

## SIGNAL-QUELLEN (Ensemble)

| Quelle | Gewicht | Was |
|--------|---------|-----|
| Technical (RSI, MACD, BB) | 30% | Klassische Indikatoren |
| ML Model (XGBoost) | 20% | Machine Learning Signal |
| Fear & Greed | 15% | Markt-Sentiment |
| Funding Rates | 10% | Binance Futures Sentiment |
| On-Chain (NVT, Mempool) | 8% | Blockchain-Metriken |
| VWAP Bias | 7% | Volume Weighted Average Price |
| Reddit Sentiment | 5% | Social Media Stimmung |
| Capitol Trades | 3% | US-Politiker Trades |
| Whale Alerts | 2% | Grosse On-Chain Transfers |

---

## MULTI-EXCHANGE SUPPORT

Unterstuetzte Boersen:
- **Binance** (Standard, EU/USDC)
- **Bybit** (automatisch verbunden)
- **Kraken** (optional, per API-Key)
- **OKX** (optional)
- **Coinbase** (optional)

Funktionen:
- Besten Preis ueber alle Boersen finden
- OHLCV-Daten von jeder Boerse holen
- Orders auf jeder Boerse ausfuehren
- Cross-Exchange Arbitrage (erkennt Preisunterschiede)

---

## BACKTESTING

| Feature | Was |
|---------|-----|
| Einzel-Test | 1 Coin, beliebiger Timeframe + Kerzenanzahl |
| Multi-Coin | 8 Coins gleichzeitig, Rangliste |
| Walk-Forward | 5 Fenster, Out-of-Sample Test |
| Monte Carlo | 500 Simulationen, Ruin-Wahrscheinlichkeit |
| Optimizer | Grid-Search: SL x Trail x Pos = 125 Kombinationen |
| Realistische Fees | Pro Exchange (Binance 0.1%, Coinbase 0.6%) |
| Slippage-Modell | Volume-Impact + Random-Faktor |
| 11 Metriken | Sharpe, Sortino, Calmar, Max DD, Profit Factor... |

---

## RISK MANAGEMENT

| Feature | Was |
|---------|-----|
| Kill-Switch | Stoppt bei Tagesverlust > 50$ |
| Drawdown Guard | Stoppt bei > 15% Portfolio-Drawdown |
| Exposure Manager | Max 20% pro Coin, 40% pro Sektor |
| Correlation Guard | Max 3 Coins aus gleichem Sektor (z.B. L1) |
| Position Sizing | Kelly-Kriterium + Half-Kelly |
| Adaptive Sizing (KI) | Passt an: Win-Rate, Vol, DD, F&G, Regime |
| Trailing Stop | Dynamisch, schuetzt Gewinne |
| Cooldown | Pause nach 3 Verlusten |

---

## TELEGRAM (12 Befehle)

/status, /btc, /strategy, /cycle, /equity, /coins,
/buy, /sell, /botstart, /botstop, /sparplan, /export

Automatische Berichte:
- Taeglich um 20:00 Uhr
- Woechentlich Sonntags um 18:00 Uhr

---

## NEUE V6 FEATURES

| Feature | Modul | Was |
|---------|-------|-----|
| Web-Dashboard | ui/dashboard.py | http://localhost:5000 |
| ngrok Public | ui/ngrok_dashboard.py | Oeffentlicher Zugang per Telegram-Link |
| VWAP Charts | ui/main_window.py | Cyan-gestrichelte VWAP-Linie in Kerzen-Charts |
| Multi-Exchange | execution/multi_exchange.py | Binance + Bybit + Kraken + OKX + Coinbase |
| TWAP Splitting | execution/twap_executor.py | Grosse Orders in 3-5 Teile aufteilen |
| Smart Entry | agents/smart_entry.py | Wartet auf Pullback statt Peak-Kauf |
| Grid Trading | agents/grid_trader.py | Grid-Strategie fuer Seitwaertsmaerkte |
| DCA Advanced | agents/dca_advanced.py | Dynamisches DCA (4x oefter bei Extreme Fear) |
| Lokales LLM | agents/llm_local.py | Ollama (Mistral/Llama3) fuer Erklaerungen |
| Arbitrage | agents/arbitrage_agent.py | Cross-Exchange Preisunterschiede |
| RL Feedback | models/rl_feedback.py | Q-Learning Strategie-Optimierung |
| Ensemble Signal | models/ensemble_signal.py | 9 Quellen gewichtet kombiniert |
| On-Chain | data/onchain_analytics.py | NVT, Hashrate, Mempool, TX Count |
| Orderbook | data/orderbook_depth.py | Bid/Ask Imbalance Analyse |
| Top Coins | data/top_coins.py | Auto-Update nach MarketCap |
| Regime Detection | features/regime_detection.py | Bull/Bear/Sideways/Volatile (multi-indikator) |
| Multi-Timeframe | features/multi_timeframe.py | 5m+15m+1h+4h Confluence |
| VWAP Agent | features/vwap_agent.py | Volume Profile + Point of Control |
| Adaptive Sizing | risk/adaptive_sizing.py | KI-Position Sizing |
| Auto-Restart | core/auto_restart.py | Ueberwacht + restartet Agenten |
| Config Backup | config/versioning.py | Backup bei jeder Aenderung |
| BT Optimizer | backtest/optimizer.py | Grid-Search fuer beste Parameter |

---

## TROUBLESHOOTING

| Problem | Loesung |
|---------|---------|
| Bot startet nicht | Fehlermeldung lesen, pip install [fehlende lib] |
| "Keine Rueckmeldung" | Normal bei Backtest/Optimizer. Warte ab. |
| Charts laden nicht | pip install ccxt --upgrade |
| Bot tradet nicht | F&G muss < 25 ODER Signal Score >= 3 |
| Alte BTC-Daten | Settings -> SESSION ZURUECKSETZEN |
| Port 5000 belegt | Bot neustarten oder Port in config aendern |
| ngrok fehlt | pip install pyngrok (optional) |
| Ollama fehlt | LLM nutzt Fallback-Erklaerungen (kein Problem) |

---

## PAKET-UEBERSICHT

| Paket | Pflicht? | Wofuer |
|-------|----------|--------|
| ccxt | JA | Exchange-Verbindung |
| pandas + pandas_ta | JA | Daten + Indikatoren |
| customtkinter | JA | Desktop-UI |
| matplotlib | JA | Charts |
| psutil | JA | System-Monitoring |
| requests | JA | API-Calls |
| scikit-learn | EMPFOHLEN | ML Signal-Modell |
| websocket-client | OPTIONAL | Echtzeit-Preise |
| praw | OPTIONAL | Reddit Sentiment |
| beautifulsoup4 | OPTIONAL | Capitol Trades |
| pyngrok | OPTIONAL | ngrok Public Dashboard |

---

Erstellt: April 2026 | Version 6.0.0
Entwickler: Sven | KI-Assistent: Claude
93 Module | 27 Tests | Multi-Agent Elite Trading System
"Schritt fuer Schritt zum Elite-Bot"
