# Ist-Zustand Trading Imperium V6 — Migrations- und Forschungs-Audit

Stand 30.07.2026, Phase 1 des Forschungsprogramms Pfad B.
Nur Lesen — kein produktiver Code geändert. Alle Zeilenangaben geprüft.

## Börse und Integration

- Exchange über ccxt, `config.json` → `exchange.ccxt_id = "binance"`,
  `quote_currency = "USDC"`, Modus **paper** (data_store/config.json).
- **Drei parallele Client-Konstruktionen** (Migrationsrisiko: dreifacher
  Anpassungspunkt):
  1. `execution/exchange_client.py:219-223` — ex_map {binance, coinbasepro,
     kraken, **bybit**, okx, kucoin}, Fallback ccxt.binance
  2. `data/market_data.py:15-17` — eigene ex_map, Fallback ccxt.binance,
     danach Test-Ticker `BTC/USDC` mit **USDT-Fallback** (Z. 32-43)
  3. `execution/engine.py:138` — `getattr(ccxt, ccxt_id)`, Fallback binance
- Weitere Binance-Hartverdrahtung: `data/funding_rates.py:21`
  (fapi.binance.com), `data/websocket_stream.py` (Binance-WS),
  `backtest/daten_holen.py:81` (ccxt.binance), `data/whale_alerts.py`,
  `execution/futures_trader.py` (Binance-Futures), `agents/arbitrage_agent.py`.

## Quote-Währung

- USDC hart in: `execution/engine.py:36,42,153,185,259-263,311`
  (Paper-Balances führen USDC **und** USDT als Bar-Quellen),
  `config/settings.py:54,222-224` (Default-Coinliste `*/USDC`),
  `data/market_data.py:32-54` (Ticker-Test + `replace("USDC","USDT")`-
  Fallback je Symbol).
- Symbolformat durchgehend ccxt-Stil `BASE/QUOTE`; Backtest-CSVs ohne
  Schrägstrich (`BTCUSDC_15m.csv`).

## Gebühren-Hardcodings

- `backtest/fees.py:8-14`: statische Tabelle (binance maker=taker=0,10 %,
  bnb_discount 0,075 %) — **von nichts Produktivem importiert** außer
  `backtest/engine.py:118-122` und Tests.
- `execution/engine.py:253` `fee_rate = 0.001` **hart** im Paper-Pfad;
  Slippage dort `random.uniform(0.02, 0.08) %` (Z. 242-247) — Zufall, kein
  Marktmodell.
- Harness: `backtest/ausstieg_backtest.py:59-60` GEBUEHR 0.001,
  SLIPPAGE 0.0005 (Konstanten der Messungen E1–G2, **nicht anfassen**).

## Market- vs. Limit-Orderpfade

- **Ausschließlich Market-Orders**: `execution/engine.py:384-385`,
  `execution/exchange_client.py:364-366`, `execution/multi_exchange.py:147-149`,
  `live/live_runner.py:60-68`, `execution/futures_trader.py:67-109`.
- Kein Limit-, Cancel/Replace- oder Post-Only-Pfad vorhanden. TWAP-Executor
  existiert, nutzt aber dieselben Market-Calls.

## Paper- vs. Live-Trennung

- `engine._paper_mode` aus `trading.mode`; Live nur nach Gate
  (`go_live_check.py`, E10), sonst Rückfall auf Paper (engine:107-163).
- Live-Deckel: `live_max_order_usd = 25`, `live_max_capital_usd = 200`
  (config risk). Ausführungsprüfung E9 (kein blindes "filled").

## Datenquellen und historische Abdeckung (vor Phase 3)

- `data_store/backtest/`: 15m-Kerzen, 11 Coins × 2 Jahre (2024-07..2026-07,
  USDC-Paare), `fear_greed.json` (Tageswerte, volle Historie) — per
  Prüfsummen eingefroren (Messablage).
- Live-Journal `trades_v5.json` (Snapshot eingefroren 30.07.).
- Kein Funding-, kein Orderbuch-, kein Makro-Archiv im Projekt.

## Migrationsrisiken (Börsenwechsel)

1. Drei Client-Baustellen + fünf Binance-Spezialmodule (oben) — ohne
   Adapter-Schicht wird jede Migration zur Streuänderung.
2. USDT-Fallback-Logik (`market_data.py:54`) ist unter MiCA **falsch**
   (USDT existiert auf EU-Börsen nicht mehr) und würde stumm ins Leere
   laufen.
3. Harte fee_rate im Paper-Pfad entkoppelt Paper von der echten
   Kostenstruktur der Zielbörse.
4. Symbol-Mapping: Bybit v5 nutzt `BTCUSDC` (ohne Slash) in API,
   ccxt normalisiert auf `BTC/USDC` — Backtest-CSV-Namen kompatibel,
   aber `replace()`-basierte Symbol-Hacks brechen.
5. WebSocket-Stream, Funding, Whale-Alerts sind Binance-gebunden —
   als **Datenquellen** weiter nutzbar (öffentlich), als Handelsanbindung
   nicht.
6. `coinbasepro` in beiden ex_maps ist in aktuellem ccxt entfernt
   [WAHRSCHEINLICH] — toter Eintrag.
