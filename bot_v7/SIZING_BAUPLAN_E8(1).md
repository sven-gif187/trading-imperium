# SIZING-BAUPLAN — E8-Kandidat "Risk-Parity-Sizing"

**Datum:** 11.07.2026 · **Status:** DESIGN (Deploy erst nach E6-Fenster, nach E7)
**Pflicht-vor-Live Nr. 4:** position_sizing verdrahten

---

## 1. Ist-Zustand (verstanden, nicht geraten)

- Größe heute: `fixed_amount = total_equity × pos_pct × _rr_size_mult` (app.py ~Z.1638)
  → Phasen-Multiplikator aus regime_profiles ist BEREITS verdrahtet.
- `risk/position_sizing.py` (PositionSizer): **0 Referenzen, verwaist** — und
  gefährlich als Direkteinbau: Es enthält EIGENE Zyklus-/Regime-Multiplikatoren.
  Einbau wie-es-ist = Phasen-Anpassung würde DOPPELT wirken (dieselbe
  Zwei-Wahrheiten-Struktur wie beim Daily-Loss-Audit P3/P5). → NICHT einbauen.
- Manuelles Sizing (Cockpit, ~Z.842): bleibt unangetastet (User-Override gilt).

## 2. Das Problem in Zahlen (E4/E6-Daten, 19 Stop-Outs)

Gleiche Positionsgröße + ungleiche Stops = ungleiches Risiko pro Trade:

| Coin | Ø-Kosten pro Stop | Stop |
|---|---|---|
| ETH | −1.54$ | 2.0–2.1% |
| SOL | −1.59$ | 2.0–2.1% |
| ADA | −1.87$ | 2.0–2.1% |
| XRP | −2.91$ | 2.0–2.1% (raus seit E6-A) |

Mit E6-B (ADA-Stop 3.0%) wächst das Ungleichgewicht: ADA-Stop kostet künftig
~−2.68$/Stop (×1.43) bei gleicher Größe. Jeder weitere Per-Coin-Stop
(Coin-Edge-Roadmap) verschärft das.

## 3. Das Prinzip: Gleiches Risiko pro Trade

**Formel (eine Zeile, rückwärtskompatibel kalibriert):**

    amount_i = fixed_amount × (stop_basis / stop_effektiv_i)

- `fixed_amount` = exakt die heutige Berechnung (Equity × pos_pct × Phasen-Mult)
- `stop_basis` = der globale phasen-angepasste Stop (heute 2.0–2.1%)
- `stop_effektiv_i` = der tatsächliche Stop des Coins (ADA: 3.0% → Faktor 0.70)
- Coins ohne Override: Faktor exakt 1.0 → **verhält sich heute identisch**,
  wirkt NUR wo Per-Coin-Stops existieren. Minimal-invasiv.

**Ehrliche Erwartung:** Kein Gratis-Gewinn. Gewinne skalieren mit demselben
Faktor. Der Nutzen: identisches $-Risiko pro Trade über alle Coins,
Voraussetzung für Coin-Edge-Ausbau, Pflicht-vor-Live sauber erfüllt.

## 4. Einbauort & Logging

- app.py ~Z.1638 (DCA-Sizing-Pfad): eine Formelzeile + Cap-Erhalt
  (min 5$, max_pct aus Config bleiben).
- Neue Log-Zeile pro Kauf: `[SIZING] ADA: 9.67$ (Basis 13.81$ × 0.70, Stop 3.0%)`
  → jede Größe jederzeit nachvollziehbar.
- Quelle für stop_effektiv_i: dieselbe Per-Coin-Override-Tabelle wie E6-B
  (eine Wahrheit, kein Duplikat).
- `position_sizing.py`: Kelly-Funktion bleibt als Analyse-Werkzeug, der
  Rest wird als DEPRECATED markiert (Doku-Kommentar), NICHT verdrahtet.

## 5. Kelly-Realitätscheck (Nebenbefund, wichtig)

Mit E4-Zahlen (WR 60.5%, AvgWin 0.79$, AvgLoss 1.65$):
**Voll-Kelly = −22% → Kelly sagt: Größe NULL.**
Die Mathematik bestätigt die eiserne Regel: Kein Live, kein Size-Up,
bevor R/R > 1. Kelly-basiertes Sizing wird erst NACH bewiesenem Edge
überhaupt diskutabel (separater, späterer Kandidat).

## 6. Vorregistrierte E8-Kriterien

- **Fenster:** 14 Tage oder 15 Sells nach Deploy (das Längere gilt)
- **Hauptkriterium:** Streuung der Stop-Out-Kosten (StdAbw in $) sinkt
  gegenüber E6/E7-Basis (aktuell 0.77$)
- **Nebenkriterien:** R/R nicht schlechter als Vorperiode; kein Trade unter
  Min-Größe 5$; Log-Zeile [SIZING] bei jedem Kauf vorhanden
- **Eisern:** Deploy erst nach E6-Fenster UND nach E7-Fenster
  (ein Experiment pro Epoche — E7 Phasen-Trailing hat Vorrang, größerer Hebel)

## 7. Reihenfolge der Epochen (Stand 11.07.)

E6 (läuft, bis ~24.07.) → E7 Phasen-Trailing (designed ✓) → **E8 Sizing (dieses Doc)**
→ danach je Datenlage: DOGE-Entscheidung, Daily-Loss scharf, Coin-Edge-Ausbau
