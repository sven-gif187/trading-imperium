# Trading Imperium V6 — Handbuch-Kapitel: Sizing, Optimizer & Settings-Maske

*Erstellt: 06.06.2026 — ausführliche Erklärung aller Sizing-Mechanismen und der GUI-Einstellungen*

---

## 1. Die Settings-Maske (SETTINGS-Tab) — was greift wo?

Die Maske im SETTINGS-Tab schreibt beim Klick auf **EINSTELLUNGEN SPEICHERN** alle Werte direkt in `data_store/config.json`. Es ist **keine** Attrappe — die Eingaben sind echt und werden vom Bot genutzt.

### Welche Felder gibt es und wohin schreiben sie?

| Maskenfeld | Config-Eintrag | Wann wird es aktiv? |
|---|---|---|
| Paper-Balance (USDC) | `trading.initial_paper_balance` | **Erst nach SESSION ZURUECKSETZEN** |
| Max Tages-Verlust $ | `risk.max_daily_loss_usd` | Sofort (nächster Loop) |
| Max Positionen | `risk.max_open_positions` | Sofort |
| Stop-Loss % | `risk.stop_loss_pct` | Sofort (für neue Trades) |
| Trailing-Stop % | `risk.trailing_stop_pct` | Sofort |
| Position Size % | `trading.position_size_pct` | Sofort |
| Sparplan AN/AUS | `trading.btc_dca_enabled` | Sofort |
| DCA Anteil % | `trading.btc_dca_pct` | Sofort |
| Intervall (Min) | `trading.btc_dca_interval_min` | Sofort |
| API-Key / Secret | `exchange.api_key/secret` | Beim nächsten Start |
| Telegram Token / Chat-ID | `telegram.token/chat_id` | Sofort |

### Wichtig: Startkapital ändern

Das Startkapital ist der einzige Wert der einen Reset braucht. Grund: Würde man es mitten im Betrieb ändern, käme das laufende Geld (Cash + offene Positionen) durcheinander. Deshalb:

1. Feld `Paper-Balance (USDC)` auf den Wunschwert setzen (z.B. 1000)
2. **EINSTELLUNGEN SPEICHERN** klicken
3. **SESSION ZURUECKSETZEN** klicken → Bot startet frisch mit dem neuen Kapital

Alle anderen Werte (Max Positionen, Stop-Loss, Position Size etc.) greifen sofort beim nächsten Trading-Loop — kein Reset nötig.

---

## 2. Position Sizing — wie viel Geld pro Trade?

Position Sizing bestimmt, wie groß jeder einzelne Kauf ist. Die Grundformel ist einfach:

```
Position Size %  ×  Gesamtkapital  =  Betrag pro Trade
```

Beispiele:
- 20% × 500$ = 100$ pro Trade
- 20% × 1000$ = 200$ pro Trade
- 10% × 1000$ = 100$ pro Trade

**Merksatz:** Wenn du das Kapital verdoppelst aber denselben Euro-Betrag pro Trade willst, musst du den Prozentsatz halbieren.

Es gibt im Bot **drei** Mechanismen die an der Positionsgröße drehen können. Nur einer ist aktuell aktiv:

### Mechanismus A — Fester Prozentsatz (AKTUELL AKTIV) ✅

Der einfachste und vorhersehbarste Weg. Du gibst `position_size_pct` vor (z.B. 20%), und jeder Trade nutzt exakt diesen Anteil. Bei 500$ Kapital also genau 100$ pro Trade. Keine Überraschungen.

Der reparierte DCA-Loop nutzt **immer** diesen festen Prozentsatz — unabhängig von den beiden anderen Mechanismen.

### Mechanismus B — Dynamic Sizing (Toggle, aktuell AUS) ⬜

Hinter dem Toggle „Dynamic Sizing (AdaptiveSizer + NUPL + DXY)" steckt der **AdaptivePositionSizer**. Bei AN passt er die Größe automatisch an:
- **Win-Rate**: Läuft es gut, größere Positionen; läuft es schlecht, kleinere.
- **NUPL**: Eine On-Chain-Kennzahl (Net Unrealized Profit/Loss) für Marktphasen.
- **DXY**: Der US-Dollar-Index (Makro-Umfeld).

Bei AUS wird dein fester % exakt verwendet. Der Hinweis in der Maske sagt es selbst: *„AUS = Dein % wird genau verwendet | AN = KI optimiert"*.

Wichtig: Dynamic Sizing betrifft nur die **normalen Signal-Trades**, nicht die DCA-Käufe (die nutzen immer den festen %).

### Mechanismus C — Auto-Optimizer (Toggle, aktuell AUS) ⬜

Siehe nächster Abschnitt. Der Auto-Optimizer ist kein reiner Sizer, sondern sucht die besten Risk-Parameter insgesamt.

---

## 3. Auto-Optimizer — was macht er, und sollte man ihn nutzen?

### Was er tut

Wenn aktiviert, läuft er **alle 30 Minuten** und testet auf historischen BTC-Daten verschiedene Parameter-Kombinationen per Backtest:
- Stop-Loss: 3% / 4% / 5%
- Trailing-Stop: 1.0% / 1.5% / 2.0%
- Position Size: 15% / 20% / 25%

Er findet die Kombination die im Backtest am besten abgeschnitten hätte und **überschreibt dann automatisch** `stop_loss_pct`, `trailing_stop_pct` und `position_size_pct` in der Config.

### Empfehlung: AUS lassen (vorerst)

Drei Gründe:

1. **Er überschreibt bewusste Einstellungen.** Wenn du gerade 100$ pro Trade (20%) eingestellt hast, kann der Optimizer das auf 15% oder 25% ändern — ohne dass du es merkst.

2. **Er optimiert nur auf BTC.** Die getesteten Parameter werden auf alle 12 Coins angewendet, obwohl nur BTC-Daten zugrunde lagen.

3. **Overfitting-Gefahr.** Was in der Vergangenheit optimal war, ist nicht automatisch in Zukunft optimal. Backtests können trügerisch sein.

**Fazit:** Behalte am Anfang die Kontrolle. Wenn der Bot mehrere Wochen stabil läuft und du die Mechanik verstehst, kannst du den Optimizer testweise einschalten und beobachten was er ändert.

---

## 4. Empfohlene Einstellungen (Stand jetzt)

Für einen sauberen, vorhersehbaren Paper-Bot mit ~100$ pro Trade:

| Einstellung | Wert | Warum |
|---|---|---|
| Paper-Balance | 500$ (oder 1000$) | Dein Wunsch-Startkapital |
| Position Size % | 20% (bei 500$) / 10% (bei 1000$) | Ergibt 100$ pro Trade |
| Max Positionen | 4 oder 5 | Bei 5 voll investiert, bei 4 bleibt Reserve |
| Stop-Loss % | 3% | Solide Standardabsicherung |
| Trailing-Stop % | 2% | Gewinne mitnehmen |
| Max Tages-Verlust $ | 50$ | Kill-Switch-Schutz |
| Auto-Optimizer | AUS | Kontrolle behalten |
| Dynamic Sizing | AUS | Fester % = 100$ exakt |

**Hinweis zur Reserve:** Bei 5 Positionen × 100$ = 500$ ist das gesamte Kapital investiert (Cash ~0$). Wenn du lieber Reserve für Nachkäufe/neue Signale willst, setz Max Positionen auf 4 → 400$ investiert, 100$ frei.

---

## 5. Die heute gefixten Bugs (06.06.2026)

### Bug 1: DCA-Mini-Trades + Overdraft (install_dca_fix.py)

**Problem:** Der DCA-Loop machte dutzende winzige Trades (2-7$) und überzog teils das Guthaben.

**Ursachen:**
- Sizing war `remaining * 0.15` → schrumpfte mit jedem Durchlauf
- Kein Cooldown → feuerte alle 12 Sekunden
- Die AdvancedDCA-Klasse (mit Cooldown-Logik) wurde gar nicht genutzt
- Cash wurde nur einmal pro Runde gelesen → Overdraft-Risiko
- Impact-Journal-Hook fehlte im DCA-Pfad

**Fix:**
- Fester Betrag pro Trade (`position_size_pct` vom Equity)
- AdvancedDCA-Cooldown aktiv (15 Min bis 3h je nach Fear & Greed)
- Max 2 neue Positionen pro Runde
- Live-Cash-Check vor jedem einzelnen Kauf
- Impact-Journal-Hook im DCA-Pfad eingebaut

### Bug 2: Balance-Restore (das 220$-Mysterium) (install_balance_fix_v2.py)

**Problem:** Cash zeigte 220$ obwohl für 480$ gekauft wurde (von 500$ Start). Total zeigte fälschlich +40% ROI.

**Ursache:** Die Restore-Funktion lief zweimal beim Start. Der zweite Durchlauf (else-Zweig) lud `paper_balances_backup = {USDC:500}` und überschrieb die bereits gekauften Coins → Cash sprang fälschlich zurück auf 500$, dann wurde weiter gekauft.

**Fix:** Der else-Zweig überspringt den Restore jetzt, sobald `_paper_balances` bereits Coins (aktive Trades) enthält. Im Log erscheint dann „Balance-Restore uebersprungen (aktive Trades: X Assets)".

---

## 6. Neue Tools (CMD-Befehle)

| Befehl | Was es macht |
|---|---|
| `python install_dca_fix.py` | Repariert den DCA-Loop (fester Betrag, Cooldown, kein Overdraft, Impact-Hook) |
| `python config_update.py` | Setzt Sizing-Config (500$ Kapital, 20% = 100$/Trade, 5 Positionen) |
| `python install_balance_fix_v2.py` | Fixt das 220$-Balance-Restore-Problem |
| `python preflight.py` | Prüft 8 Punkte ob der Bot Live-ready ist |
| `python status.py` | Schnelle Übersicht: Cash, P&L heute, Strategien, V4-Wissen |
| `python impact_report.py` | Detaillierter Trade-Report mit Begründungen pro Strategie |

---

*Ende des Kapitels. Bei weiteren Änderungen wird dieses Dokument ausführlich ergänzt.*
