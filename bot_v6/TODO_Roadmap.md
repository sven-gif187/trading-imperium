# Trading Imperium V6 — TODO & Roadmap

*Stand: 06.06.2026*

---

## ✅ ERLEDIGT (06.06.2026)

- **DCA-Loop komplett gefixt** (`install_dca_fix.py`)
  - Fester Betrag pro Trade (100$ statt Mini-Trades 2-7$)
  - AdvancedDCA-Cooldown aktiv (15 Min - 3h statt 12s-Takt)
  - Max 2 neue Positionen pro Runde
  - Live-Cash-Check vor jedem Kauf (kein Overdraft mehr)
  - Impact-Journal-Hook eingebaut
- **Config-Sizing gesetzt** (`config_update.py`): 500$ Kapital, 20% = 100$/Trade, 5 Positionen
- **Balance-Restore-Bug gefixt** (`install_balance_fix_v2.py`): kein 220$-Mysterium / +40% ROI mehr
- **Impact-Journal füllt sich** — erster echter Report mit 5 Trades
- **GUI-Maske geklärt**: greift voll, schreibt in config.json
- **Sizing-Mechanismen erklärt**: fester %, Dynamic Sizing, Auto-Optimizer (beide AUS)
- **Handbuch-Kapitel erstellt** (`Handbuch_Sizing_und_Optimizer.md`)

---

## 🟢 LÄUFT VON SELBST (nur beobachten)

- Bot läuft mit 5 DCA-Positionen — abwarten bis sie sich schließen (erste Win-Rate)
- Brain lernt mit jedem Trade dazu
- V4-Sync importiert weiter Lerngold (103 V4-Trades, +845$ PnL)

**Check-Befehle:** `python status.py` / `python impact_report.py`

---

## 🟡 BOT FERTIGSTELLEN (Phase 1 — als Nächstes)

1. **Bot stabil laufen lassen** (1-2 Wochen) — wichtigster Punkt für echte Daten
2. **Erste geschlossene Trades beobachten** — schließen Stop-Loss/Trailing sauber?
3. **tickets.txt ins Handbuch** — die dokumentierten Befehle reinkopieren (DocAgent erledigt Rest)
4. **Ordner aufräumen** — wenn Kopf dafür frei ist (`aufraeumen.py` oder altes `cleanup.py` prüfen)
5. **Sensei-Handbuch gemeinsam durchgehen** — Bot-Mechanik verstehen (wenn gewünscht)

---

## 🟠 LIVE-TRADING VORBEREITEN (Phase 1.5 — wenn Bot stabil)

1. `python preflight.py` bis möglichst viele Punkte grün (braucht 14 Tage Laufzeit + Win-Rate ≥ 50%)
2. Binance API-Keys einrichten — **NIE Withdraw-Recht aktivieren!**
3. Klein starten: 50-100$ echtes Geld, 1-2 Wochen beobachten

---

## 🟣 EDELMETALLE-TAB (Phase 2 — nach Kryptobot)

**Idee:** Eigener Tab in V6 nur für Edelmetall-Handel mit eigenen Strategien.

**Weg A (gewählt):** Tokenisierte Metalle über Binance/ccxt
- **PAXG** (PAX Gold) — durch echtes physisches Gold gedeckt, 1 PAXG = 1 Feinunze
- Läuft über die gleiche Anbindung die der Bot schon hat

**Was gebraucht wird:**
- Eigene Datenquelle (PAXG + ggf. Silber-Token)
- Eigene Strategien — Gold tickt anders als Krypto:
  - Weniger volatil, ruhigere Trends
  - Treiber: DXY (Dollar-Index, invers), Zinsen, Safe-Haven-Nachfrage
  - Fear & Greed Index gibt's für Gold NICHT → eigene Indikatoren nötig
- Eigener Tab im UI
- Eigene Risk-Parameter

**Hinweis:** Eigenständiges Projekt, nicht nebenbei. Erst Kryptobot stabil, dann angehen.

---

## 📌 WICHTIGE PRINZIPIEN (gelernt)

- **Klassen-Namenskollisionen vermeiden** — neue Klasse niemals alte überschreiben
- **Keine hardcodierten Pfade** — Auto-Discovery scannt mehrere Pfade
- **Reset-Scripts müssen ALLE State-Dateien treffen** (trades_v5, order_history, bot_state, impact_journal)
- **Install-Scripts nach jedem Schritt testen** bevor weiter
- **DCA-Loop nutzt immer festen %** — Dynamic Sizing betrifft nur normale Signal-Trades
