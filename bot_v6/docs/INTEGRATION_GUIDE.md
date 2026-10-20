# V4 -> V6 Integration Guide

**Ziel:** V6 nutzt die echte V4-Performance um die richtigen Strategien zu feuern.

---

## Schritt 1 – Dateien einsortieren

Aus dem ZIP entpacken und in deinen V6-Ordner legen:

```
trading_imperium_v6/
├── agents/
│   └── v4_strategies.py        <- NEU
├── models/
│   └── v4_calibrator.py        <- NEU
├── data/
│   └── v4_importer.py          <- NEU
├── scripts/
│   └── migrate_v4_to_v6.py     <- NEU
├── v4_data/                    <- NEU (deine V4 JSONs hierher)
│   ├── strategy_stats.json
│   ├── trades_log_v4.json
│   ├── equity_history.json
│   └── imperium_state.json
└── app.py
```

---

## Schritt 2 – Migration ausführen

Aus dem V6-Hauptverzeichnis:

```bash
python scripts/migrate_v4_to_v6.py
```

Das macht:
- Importiert deine V4-Trades (266 abgeschlossene Trades, +1.269€)
- Berechnet die Strategie-Gewichte aus echter V4-Performance
- Sperrt Verlierer-Strategien (STOCHRSI_REVERSAL, MANUELL, EMA_TREND, RSI_DIVERGENCE)
- Cached die Gewichte in `data_store/v4_strategy_weights.json`

---

## Schritt 3 – app.py erweitern

Im Init-Block der `TradingImperiumV6` Klasse, nach den anderen Agents:

```python
# === V4 BRIDGE (lernt aus echter V4-Performance) ===
from agents.v4_strategies import V4StrategyEnsemble
from models.v4_calibrator import V4Calibrator

self.v4_ensemble = V4StrategyEnsemble()
self.v4_calibrator = V4Calibrator.load("v4_data/strategy_stats.json")
log.info("APP", f"V4-Bridge geladen: {len(self.v4_calibrator.weights)} Strategien kalibriert")
log.info("APP", f"V4 Top-3: {[s for s, w in self.v4_calibrator.get_ranking()[:3]]}")
```

In `get_system_status()` (Dashboard) am Ende des Dicts:

```python
"v4_ensemble": self.v4_ensemble.get_status(),
"v4_calibrator": self.v4_calibrator.get_status(),
```

---

## Schritt 4 – Signal-Agent erweitern

In `agents/signal_agent.py` musst du das V4-Ensemble einhängen.
Suche die Stelle wo das Signal berechnet wird (oft `analyze()` oder `evaluate()`)
und füge den V4-Pfad als zusätzliche Quelle hinzu:

```python
def analyze(self, snapshot, df):
    # ... bestehende V6-Signal-Berechnung ...
    v6_score = self._compute_v6_score(snapshot, df)

    # === V4 BRIDGE ===
    v4_score, v4_reason, v4_strategy = self.app.v4_ensemble.evaluate_buy(
        df=df,
        price=snapshot.price,
        fear_greed=self.app.state.get("fear_greed", 50),
        calibrator=self.app.v4_calibrator,   # WICHTIG: Calibrator uebergeben!
    )
    # v4_score ist bereits kalibriert (raw_score * weight)

    # FUSION: V4 hat Vorrang wenn das Signal stark ist
    # (V4 hat real bewiesen dass es funktioniert!)
    if v4_score > 0.6:
        log.info("SIGNAL", f"V4 fired: {v4_strategy} ({v4_score:.2f}) - {v4_reason}")
        final_score = v4_score
        final_strategy = v4_strategy
    else:
        # V4 ist schwach -> nutze V6 Ensemble
        final_score = v6_score
        final_strategy = "v6_ensemble"

    return final_score, final_strategy
```

**Alternative – sanftere Fusion (empfohlen für die ersten Wochen):**

```python
# 70% V4 (bewiesen) + 30% V6 (Innovation)
final_score = 0.7 * v4_score + 0.3 * v6_score
```

---

## Schritt 5 – Dashboard-Karte (optional)

In `ui/main_window.py` oder `ui/dashboard.py` wo die Agent-Karten gerendert werden,
zwei neue Karten hinzufügen:

```python
# V4 Ensemble Karte
v4_status = engine.v4_ensemble.get_status()
top_score = max(v4_status['last_scores'].values()) if v4_status['last_scores'] else 0
render_card("V4 Ensemble",
            f"{len(v4_status['strategies'])} Strategien aktiv",
            f"Letzter Top-Score: {top_score}/9")

# V4 Calibrator Karte
cal_status = engine.v4_calibrator.get_status()
render_card("V4 Calibrator",
            f"Top: {cal_status['top_performers'][0] if cal_status['top_performers'] else '-'}",
            f"Blocked: {len(cal_status['blocked'])}")
```

---

## Schritt 6 – Verifizieren

Nach dem Start sollten in den Logs zu sehen sein:

```
[APP] V4-Bridge geladen: 13 Strategien kalibriert
[APP] V4 Top-3: ['DCA_FEAR_GREED', 'TSI_SIGNAL', 'FIBONACCI_SUPPORT']
[SIGNAL] V4 fired: DCA_FEAR_GREED (0.82) - Fear (22) -> Starker Kauf
```

Wenn du das siehst, läuft die Bridge.

---

## Was passiert jetzt fachlich?

**Vorher (V6 ohne Bridge):**
- 12 Strategien gleichberechtigt
- STOCHRSI_REVERSAL feuert -> Verlust
- DCA_FEAR_GREED hat gleichen Einfluss wie EMA_TREND
- Ensemble verwässert starke Signale

**Nachher (V6 mit Bridge):**
- DCA_FEAR_GREED hat Gewicht 0.91 (in V4 +935€ Gewinn!)
- STOCHRSI_REVERSAL gesperrt (Gewicht 0)
- TSI_SIGNAL und FIBONACCI hoch gewichtet
- V6 fokussiert sich auf das was real funktioniert hat

---

## Troubleshooting

**Problem:** `ImportError: No module named 'agents.v4_strategies'`
- Prüfe: liegen die Files im richtigen Ordner?
- Prüfe: hast du `__init__.py` in agents/ und models/?

**Problem:** `FileNotFoundError: v4_data/strategy_stats.json`
- Lege die V4 JSON-Dateien in den `v4_data/` Ordner

**Problem:** `Calibrator zeigt alle Gewichte 1.0`
- strategy_stats.json wurde nicht gefunden -> Fallback auf Default
- Pfad prüfen
