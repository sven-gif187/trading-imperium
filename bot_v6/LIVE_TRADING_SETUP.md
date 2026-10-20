# Trading Imperium V6 - Live-Trading Setup

## 🎯 KERN-PRINZIP: Alles ist PROZENTUAL!

Der Bot rechnet **NIEMALS** mit hardcoded USDC-Beträgen.
Alles ist prozentual zum **aktuellen Portfolio-Kapital** - skaliert automatisch:

| Kapital | Modus "Balanced" (30% pro Trade) |
|---------|----------------------------------|
| 300 USDC | 90 USDC pro Trade |
| 1.500 USDC | 450 USDC pro Trade |
| 5.000 USDC | 1.500 USDC pro Trade |
| 10.000 USDC | 3.000 USDC pro Trade |

## 📋 DIE 3 TRADING-MODI

| Modus | Pro Trade | Max Trades | Cash-Reserve | Sektor-Limit |
|-------|-----------|------------|--------------|---------------|
| **all_in** | 95% | 1 | 5% | 100% (aus) |
| **balanced** | 30% | 3 | 10% | 80% |
| **diversified** | 10% | 10 | 10% | 40% |

In `config.json` setzen:
```json
"trading_modes": {
    "active_mode": "balanced"
}
```

## 🔑 API-KEYS (NIEMALS in den Code!)

### Schritt 1: `.env` Datei erstellen

Im Hauptordner eine Datei `.env` erstellen mit:

```bash
# Binance API (Live-Trading)
BINANCE_API_KEY=dein_binance_api_key_hier
BINANCE_API_SECRET=dein_binance_secret_hier

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Ngrok (optional)
NGROK_AUTHTOKEN=
```

### Schritt 2: API-Key Berechtigungen

In Binance unter API Management:
- ✅ **Enable Reading**
- ✅ **Enable Spot Trading**
- ❌ **Enable Withdrawals** (NIEMALS aktivieren!)
- ❌ **Enable Futures** (außer du nutzt Futures bewusst)

### Schritt 3: IP-Restriction (empfohlen)

Setze die IP-Restriction auf deine eigene IP-Adresse für maximale Sicherheit.

## 🔄 PAPER ↔ LIVE UMSCHALTEN

In `config.json`:
```json
"trading": {
    "mode": "paper"   // oder "live"
}
```

Oder in der UI: Settings-Tab → "Mode: paper/live"

## 📊 SL/TP - PROZENTUAL VOM EINSTIEGSPREIS

In `config.json`:
```json
"risk": {
    "stop_loss_pct": 4.0,         // -4% vom Entry
    "take_profit_pct": 8.0,       // +8% vom Entry (0 = aus)
    "trailing_stop_pct": 1.5      // 1.5% unter Höchststand
}
```

**Beispiel:** Entry bei 75.000$ BTC:
- Stop-Loss bei: 72.000$ (-4%)
- Take-Profit bei: 81.000$ (+8%)
- Trailing-Stop: 1.5% unter Höchststand

## 🛡️ DAILY LOSS LIMIT

Bot pausiert AUTOMATISCH bei -10% Tagesverlust:
- Schließt alle offenen Positionen
- Sendet Telegram-Alert
- Pausiert bis nächster Tag (UTC)
- Kein Restart nötig

In `config.json`:
```json
"risk": {
    "max_daily_loss_pct": 10.0
}
```

## 🚦 LIVE-SAFETY FILTER

Trades werden automatisch abgelehnt bei:
- **Spread > 0.5%**: Kurs zu volatil
- **Volumen < 1M$**: Zu illiquide
- **Daily Loss erreicht**: Bot pausiert

In `config.json`:
```json
"risk": {
    "min_volume_24h_usd": 1000000,
    "max_spread_pct": 0.5
}
```

## ✅ ERSTER LIVE-TEST CHECKLISTE

Bevor du mit echtem Geld startest:

1. **Mindestens 2 Wochen Paper-Trading** mit konsistenten Gewinnen
2. **Klein anfangen**: 100-300 USDC, nicht mehr
3. **API-Keys** in `.env` (NIE in Code committen!)
4. **Withdrawal AUS** in Binance API
5. **Daily Loss Limit** auf 5-10% setzen
6. **Modus "balanced"** verwenden (nicht all_in!)
7. **Telegram** einrichten für Live-Alerts
8. **Erste 24h** den Bot beobachten

## 📈 KAPITAL-WACHSTUM IST AUTOMATISCH

Bei Gewinn von 300$ → 500$:
- Position-Size steigt automatisch von 90$ auf 150$ (30%)
- Cash-Reserve steigt von 30$ auf 50$ (10%)
- Alles passt sich an, ohne dass du was ändern musst!

Bei Verlust von 300$ → 200$:
- Position-Size sinkt auf 60$ (30%)
- Risiko reduziert sich automatisch
- Bot tradiert kleiner

## 🔧 TROUBLESHOOTING

**"Keine API-Keys in .env"**
→ Erstelle `.env` Datei im Hauptordner mit `BINANCE_API_KEY=...`

**"Live-Balance Fehler: 401"**
→ API-Key falsch oder ungültig

**"Live-Balance Fehler: -2015"**
→ IP-Restriction blockiert dich (Whitelist deine IP)

**"Cash-Reserve! 50$ < 60$"**
→ Normal: Bot will 10% Reserve halten. Trade wird auf max möglichen reduziert.

**"DAILY LOSS LIMIT erreicht"**
→ Bot pausiert bis morgen 00:00 UTC. Kann manuell zurückgesetzt werden via UI.
