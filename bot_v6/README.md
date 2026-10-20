# V4 -> V6 Bridge

Verbindet V4-Performance mit der V6-Architektur.

## Was ist drin?

| Datei | Was es tut |
|---|---|
| `agents/v4_strategies.py` | Die 7 profitablen V4-Strategien als V6-Modul |
| `models/v4_calibrator.py` | Strategie-Gewichte aus echter V4-Performance |
| `data/v4_importer.py` | Importiert V4 Trade-History + Equity ins V6-Format |
| `scripts/migrate_v4_to_v6.py` | Ein-Klick Migration |
| `docs/INTEGRATION_GUIDE.md` | Schritt-für-Schritt Anleitung |
| `v4_data/` | Deine V4 JSON-Dateien (bereits enthalten) |

## Quick Start

```bash
# 1. Alle Files in den V6-Hauptordner kopieren
# 2. Migration laufen lassen:
python scripts/migrate_v4_to_v6.py

# 3. app.py erweitern (siehe docs/INTEGRATION_GUIDE.md)
# 4. V6 starten:
python app.py
```

## Was die Bridge bewirkt

**V4 hat real bewiesen** (266 Trades, +1.269€):
- DCA_FEAR_GREED ist der Star (74% des Gewinns)
- FIBONACCI_SUPPORT, ICHIMOKU_CLOUD, TSI_SIGNAL sind solide
- STOCHRSI_REVERSAL kostet Geld trotz hoher Win-Rate
- MANUELL ist immer ein Verlust (Hand weg vom Bot!)

**V6 ohne Bridge:** behandelt alle 12 Strategien gleich -> verwässert Signale.

**V6 mit Bridge:** gewichtet jede Strategie nach ihrer realen V4-Performance.

## Strategie-Gewichte (aus V4 berechnet)

| Strategie | Gewicht | V4 PnL |
|---|---|---|
| DCA_FEAR_GREED | **0.91** | +935 EUR |
| TSI_SIGNAL | **0.88** | +43 EUR |
| FIBONACCI_SUPPORT | **0.73** | +234 EUR |
| MACD_CROSS | 0.63 | +39 EUR |
| ICHIMOKU_CLOUD | 0.61 | +158 EUR |
| RSI_OVERSOLD | 0.43 | +10 EUR |
| MOMENTUM_BREAKOUT | 0.43 | +10 EUR |
| EMA_TREND | **BLOCKED** | -19 EUR |
| RSI_DIVERGENCE | **BLOCKED** | -27 EUR |
| MANUELL | **BLOCKED** | -50 EUR |
| STOCHRSI_REVERSAL | **BLOCKED** | -63 EUR |
