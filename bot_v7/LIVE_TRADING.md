# 🚀 Trading Imperium V6 - Live Trading Anleitung

## ⚠️ WICHTIG: Lese das KOMPLETT durch bevor du Live gehst!

---

## 1. UMSCHALTEN VON PAPER AUF LIVE

### Schritt 1: API-Keys sicher speichern

**NIEMALS** API-Keys in `config.json` oder Code eintragen! Nutze `.env`:

```bash
# Datei .env im Hauptordner erstellen
BINANCE_API_KEY=dein_api_key_hier
BINANCE_API_SECRET=dein_api_secret_hier
```

**API-Key in Binance erstellen mit DIESEN Berechtigungen:**
- ✅ **Spot Trading aktiviert**
- ❌ **Withdrawals DEAKTIVIERT** (NIEMALS aktivieren!)
- ❌ **Futures DEAKTIVIERT** (es sei denn du willst Futures)
- ✅ **IP-Restriktion** auf deine Heim-IP (sehr empfohlen!)

### Schritt 2: Modus in config.json umschalten

```json
{
  "trading": {
    "mode": "live"  // war: "paper"
  }
}
```

### Schritt 3: Trading-Modus wählen

```json
{
  "modes": {
    "active_mode": "balanced"  // "all_in" | "balanced" | "diversified"
  }
}
```

---

## 2. WIE DAS PROZENTUALE SIZING FUNKTIONIERT

Der Bot rechnet **NIEMALS** mit fixen USDC-Beträgen.
Alles ist prozentual und skaliert automatisch:

### Beispiel mit Modus "balanced" (30% pro Trade, max 3):

| Portfolio-Wert | Position Size | Cash-Reserve | Max Daily Loss |
|----------------|---------------|--------------|----------------|
| 300 USDC       | 90 USDC       | 30 USDC      | 30 USDC (-10%) |
| 1.500 USDC     | 450 USDC      | 150 USDC     | 150 USDC       |
| 5.000 USDC     | 1.500 USDC    | 500 USDC     | 500 USDC       |
| 10.000 USDC    | 3.000 USDC    | 1.000 USDC   | 1.000 USDC     |

### Wie der Bot das berechnet:

```python
# Vor JEDEM Trade:
capital = portfolio.get_total_capital()  # Live: von Binance, Paper: aus Config
mode = config.get_active_mode()
position_size = capital * (mode.position_size_pct / 100)  # 30% von capital
```

**Live-Modus:** `get_total_capital()` ruft `binance.fetch_balance()` auf und summiert:
- Cash (USDC + USDT)
- Aktuellen Wert aller Coin-Holdings

**Paper-Modus:** Liest aus `execution._paper_balances` Dict.

---

## 3. SICHERHEITS-FEATURES IM LIVE-MODUS

### ✅ Daily Loss Limit (-10%)
```python
# Tracking erfolgt in PortfolioManager:
# - Tagesstart-Kapital wird täglich um Mitternacht UTC gespeichert
# - Bei -10% Verlust: Bot schliesst ALLE Positionen + pausiert bis nächsten Tag
# - Telegram-Alert wird gesendet
```

### ✅ Spread-Check
```python
# Vor jedem Trade:
# - Wenn (ask - bid) / bid > 0.5% -> Trade blockiert
# - Verhindert Trades bei dünnen Markets
```

### ✅ Volume-Check
```python
# Vor jedem Trade:
# - Wenn 24h-Volumen < 1.000.000$ -> Trade blockiert
# - Verhindert Manipulation in low-cap Coins
```

### ✅ Cash-Reserve
```python
# Pro Modus:
# - all_in:       5%  immer als Cash
# - balanced:     10% immer als Cash
# - diversified:  10% immer als Cash
```

### ✅ Stop-Loss & Take-Profit (prozentual!)
```python
# Beim Kauf werden automatisch gesetzt:
# - SL = entry_price * (1 - 0.04)   # -4%
# - TP = entry_price * (1 + 0.08)   # +8%
# - Trailing 1.5% unter Höchststand
```

---

## 4. ERSTER LIVE-START - CHECKLISTE

```
[ ] Mit Paper-Mode 2-4 Wochen erfolgreich getestet
[ ] Backtest auf historischen Daten gewinnt mehr als verliert
[ ] .env Datei erstellt mit API-Keys
[ ] Binance API-Key OHNE Withdraw-Berechtigung
[ ] IP-Whitelist in Binance aktiviert
[ ] config.json: mode = "live"
[ ] config.json: Korrekter Modus gewählt (all_in/balanced/diversified)
[ ] config.json: max_daily_loss_pct = 10.0 (oder weniger!)
[ ] Mit kleinem Betrag starten (z.B. 100$ - selbst wenn 1000$ verfügbar)
[ ] Telegram konfiguriert für Alerts
[ ] Bot 1 Tag beobachten bevor man weg geht
```

---

## 5. WAS DU IM LOG SEHEN WIRST

### Beim Start:
```
[APP] 🟢 LIVE-MODUS aktiv!
[PORTFOLIO] 📅 Neuer Tag - Startkapital: 300.00$
[HEALTH] 💓 Heartbeat-Pulse gestartet (alle 30s)
```

### Beim Trade:
```
[SIGNAL] BTC/USDC: Score 4 -> BUY 90.00$  (30% von 300$)
[RISK] APPROVED BTC/USDC BUY 90.00$
[LIVE-SAFETY] OK: Spread 0.02%, Volume 250M$
[EXEC] BUY BTC/USDC: 0.0012 @ 75,000$ (echter Trade!)
```

### Bei Daily Loss Limit:
```
[PORTFOLIO] 🛑 DAILY LOSS LIMIT! Verlust: -10.20% (Limit: -10.0%)
[APP] 🛑 DAILY LOSS LIMIT - Schliesse alle Positionen!
[EXEC] SELL BTC/USDC: 0.0012 @ 73,500$ (-2.00$)
[TELEGRAM] 🛑 DAILY LOSS LIMIT erreicht! Bot pausiert.
```

---

## 6. WAS WENN ES NICHT FUNKTIONIERT?

### "API key not valid"
- Check: API-Key korrekt in .env?
- Check: IP-Whitelist in Binance richtig?
- Check: Spot-Trading aktiviert?

### "Insufficient balance"
- Check: Hast du wirklich USDC auf Spot? (nicht Futures/Margin)
- Check: Andere Trades blockieren dein Cash?

### "Bot kauft nicht"
- Check: F&G zu hoch (>70 = Bot wartet auf Korrektur)
- Check: NUPL zu hoch (Euphorie-Zone blockiert Käufe)
- Check: Daily-Loss-Limit aktiv? (`portfolio.is_paused_by_daily_loss()`)

---

## 7. NOTFALL: BOT KOMPLETT STOPPEN

```bash
# Im Terminal: Strg+C drücken
# Bot speichert State + schliesst Connections sauber
# Offene Positionen bleiben offen (manuell schliessen wenn nötig!)
```

**Wichtig:** Wenn du Positionen behalten willst → Bot stoppt nicht automatisch verkaufen.
Wenn du alle Positionen schließen willst → Im UI: "🔓 NUR POSITIONEN SCHLIESSEN" Button.

---

## 8. EMPFEHLUNGEN VOM ENTWICKLER

1. **Starte IMMER mit Paper-Mode** für mindestens 4 Wochen
2. **Teste alle 3 Modi** im Paper bevor du Live gehst
3. **Beginne klein**: 50-100$ am Anfang, auch wenn du mehr hast
4. **Beobachte aktiv** die ersten 24h
5. **Setze Daily-Loss-Limit auf 5%** für die ersten Wochen (statt 10%)
6. **Telegram-Alerts** sind dein Frühwarnsystem - nutze sie!
7. **Niemals "set and forget"** in den ersten Wochen

---

**Viel Erfolg, Bruder! 💪 Vorsichtig anfangen, langsam skalieren.**
