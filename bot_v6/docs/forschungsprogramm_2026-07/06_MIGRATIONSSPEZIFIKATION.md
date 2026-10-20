# Migrationsspezifikation Binance → Bybit EU (USDC) — NUR Spezifikation

Kein produktiver Wechsel. Umsetzung erst nach: (1) Börsen-Freigabe,
(2) Datei-für-Datei-Diff-Plan, (3) Rollback-Test. Der laufende Bot bleibt
bis dahin unverändert auf Paper/Binance-Konfiguration.

## Prinzip: Adapter statt Streuänderung

Neu: `execution/adapters/exchange_adapter.py` — eine Klasse kapselt
ccxt-Instanzierung, Symbol-Mapping, Gebührenmodell, Präzision. Alle drei
bisherigen Client-Baustellen (exchange_client:219, market_data:15,
engine:138) beziehen den Client künftig NUR noch von dort. Bestehende
Module bleiben als Dateien unangetastet lauffähig (Adapter ist additiv;
Umschaltung per Konfig).

## Betroffene Dateien (Änderungsplan, noch nicht ausgeführt)

| Datei | Änderung |
|---|---|
| config.json / config/settings.py:52-54 | `ccxt_id: "bybit"`, `quote_currency: "USDC"`; NEU: `fee_maker_pct`, `fee_taker_pct`, `slippage_pct` statt Hardcode |
| execution/engine.py:253 | `fee_rate` aus Config lesen (Paper spiegelt Zielbörse) |
| execution/engine.py:36-311 | Paper-Balances: Quote aus Config; **USDT-Nebenbuchung entfernen** |
| data/market_data.py:32-54 | Test-Ticker aus Config-Quote; **USDT-Fallback ersatzlos streichen** (unter MiCA irreführend) |
| execution/exchange_client.py:219 | ex_map um `bitvavo` ergänzen, toten `coinbasepro` entfernen |
| data/websocket_stream.py | Binance-WS → Adapter-WS (Phase 2 der Migration, nicht kritisch für Paper) |
| data/funding_rates.py | bleibt (globale Signalquelle, kein Handelsplatz) |
| backtest/* , docs/messungen_2026-07/* | **UNVERÄNDERT** (eingefrorene Messbasis) |

## Symbol-Mapping

ccxt normalisiert Bybit auf `BTC/USDC` — identisch zum Bot-Format.
Mapping-Tabelle nur für Rohdaten-Ebene (`BTCUSDT`-Archiv ↔ `BTC/USDC`
Handel) im Adapter, als explizites Dict, kein `str.replace`.

## Gebührenmodell

Konfig-getrieben: maker/taker/slippage je Börse; Paper-Slippage ersetzt
den `random.uniform`-Generator durch: gemessene Spread-Hälfte aus
Live-Capture (sobald vorhanden), bis dahin konservativ 0,05 %.

**Auflage (30.07.2026):** Gebühren dürfen NIE aus ccxt-Metadaten
gelesen werden. Nachweis: `ccxt.bybit().fees['trading']` liefert maker
0,01 % / taker 0,075 % — für EU-Spot beides falsch (Ist: 0,10 % / 0,25 %).
Der Adapter liest ausschließlich die Konfigurationswerte; ein Startup-
Check protokolliert Konfig gegen ccxt-Metadaten und **warnt** bei
Abweichung, übernimmt aber nie automatisch.

## Limit-Order-Pfad — von „später" zu „Voraussetzung", aber nachgelagert

Mit Taker 0,25 % ist die günstige Kostenbasis von Bybit EU (0,26 % statt
0,60 % je Runde) nur über Maker-Ausführung erreichbar. Der Limit-Pfad ist
damit **Voraussetzung der Kostenbasis**, nicht Optimierung.

Er wird trotzdem NICHT vorgezogen: gebaut wird er erst, wenn ein
H1/H2-Kandidat unter K-BASIS (0,60 %, Taker) überlebt — oder wenn ein
Kandidat ausschließlich unter K-MAKER trägt und der Bau dadurch
gerechtfertigt ist. Andernfalls bauen wir Execution für ein Signal, das
es nicht gibt (genau der Fehler, den E1–G2 dokumentiert haben).

Spezifikation für diesen Fall (noch nicht umzusetzen):
- `create_limit_buy_order` / `create_limit_sell_order` mit PostOnly,
  Preis = Bid (Kauf) bzw. Ask (Verkauf) zum Signalzeitpunkt.
- Wartefenster 4 h (Tageshorizont verträgt das; F1e maß bei 4 h
  98,9 % Fill „am Close" / 95,3 % bei 0,05 % passiv, Adverse Selection
  −0,019 bis −0,021 %). **Extrapolationsvorbehalt:** F1e wurde auf
  Binance-15m-Daten für die Einstiege des ALTEN Bots gemessen; die
  Übertragung auf Tagessignale und Bybit-EU-Bücher ist plausibel, aber
  ungemessen — die Live-Capture liefert die Ersatzmessung.
- Nichtfill nach Ablauf: Signal verfällt (kein Market-Nachfassen — das
  würde die Kostenbasis wieder auf Taker heben und die Messung
  verfälschen). Verfallsquote wird protokolliert und geht als
  Selektionseffekt in die Auswertung ein.
- Cancel/Replace, Orderstatus-Polling, Teilfill-Behandlung
  (Teilfill = Position in gefüllter Größe, Rest verfällt).

## Testplan (vor Aktivierung)

1. Read-only-Smoke: fetch_ticker/fetch_ohlcv/orderbook gegen api.bybit.eu
   für alle 12 Paare (öffentlich, ohne Key).
2. Paper-Lauf 48 h parallel (neuer Prozessordner, eigener data_store-Klon)
   — Alt-Bot bleibt unberührt.
3. Vergleichsreport: Preise Alt/Neu, Abweichung < 0,1 % erwartet.
4. Erst danach Entscheidung über Konto/KYC/Keys (Nutzer-Sache; Keys
   werden nie von mir angezeigt oder gespeichert).

## Rollback

Konfig-Umschaltung zurück (`ccxt_id: "binance"`, Quote USDC) + Adapter
deaktivieren; da alle Altmodule unverändert bleiben, ist der Rollback ein
reiner Konfig-Revert plus Neustart. Backups: config.json vor jeder
Änderung mit Datumssuffix.
