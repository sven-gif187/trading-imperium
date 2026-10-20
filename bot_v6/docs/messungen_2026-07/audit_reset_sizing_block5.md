# Reset, Sizing, Wächter — Arbeitsbericht 05.08.2026

**UTC:** 2026-08-05T03:40Z · **Bot:** läuft, PID 12552

---

## Erledigt

| Punkt | Ergebnis | Beleg |
|---|---|---|
| Wächter-Alarme (Start) | behoben | Deine Telegram-Alarme `03:47` sind `01:47 UTC` = **vor** dem Fix-Neustart um 02:29. `[02:38:44] [EXEC] Paper-Bestand aus State ergaenzt: AVAX=8.129881, DOT=68.127421, ADA=320.779720, BTC=0.000818, ETH=0.027558` |
| Coins | BTC/ETH/SOL | `[03:13:37] [APP] Coins: 3` |
| Reset auf 500 USDC | sauber | `[03:14:21] [PORTFOLIO] Neuer Tag - Startkapital: 500.00$` |
| Historie unberührt | ja | trades_v5.json 957 · trades_journal 1143 · trials 147 |
| Strategievielfalt | **erreicht** | EMA_TREND 7×, DCA_FEAR_GREED 3× — vorher 2021× nur DCA |

**Reset-Details:** `open_positions`, `open_positions_backup`, `open_orders_backup`,
`equity_history`, `trade_markers` geleert; `realized_pnl`/`daily_pnl`/`daily_loss`
auf 0; `paper_balances_backup` auf `{"USDC": 500.0}`; `last_reset` gesetzt.
`trade_count` **bewusst behalten** (korrespondiert mit trades_v5.json).
Backup: `bot_state.json.bak_vor_reset_20260805`.

---

## Sizing — wo der wirksame Schalter liegt

`portfolio/manager.py:348` rechnet `size = capital * (mode.position_size_pct / 100)`.
Maßgeblich ist also **`modes.balanced`**, nicht `trading.position_size_pct`.

| Parameter | vorher | jetzt |
|---|---|---|
| `modes.balanced.position_size_pct` | 20,0 | **30,0** |
| `modes.balanced.max_positions` | 5 | **3** |
| `modes.balanced.max_coin_pct` | 35,0 | 35,0 (unverändert) |
| `trading.position_size_pct` | 20,0 | 30,0 |
| `risk.max_exposure_per_coin_pct` | 25,0 | 35,0 |
| `risk.max_open_positions` | 5 | 3 |

**Warum nicht 30/25:** `risk/exposure.py:31` lehnt jeden Kauf ab, der die
Coin-Grenze überschreitet — auch Erstkäufe. Bei 30 % Positionsgröße gegen
25 % Grenze wäre **jeder Kauf** blockiert. Mit 35 % bleiben 5 Punkte Luft
für Kursanstieg. Nachkäufe bleiben blockiert (30+30 = 60 % > 35 %) — das
ist der gewollte E9-Zustand.

Backup: `config.json.bak_sizing_20260805`.

---

## OFFEN 1 — Ordergröße stimmt noch nicht

Erwartet bei 500 USDC und 30 %: **150,00 $**. Beobachtet: **50,80 $**
(konstant, über alle drei Coins, `[03:36:18]` ff.).

50,80 $ entspricht rund 10 % von 500. Die Signalzeile stammt aus
`agents/signal_agent.py:172` (`pos_size = balance_usd * trading.position_size_pct/100`),
verwendet also eine andere Kapitalbasis als der PortfolioManager. Welche
der beiden Größen am Ende die Order bestimmt, ist **noch nicht geklärt** —
ich habe es nicht zu Ende verfolgt und will hier nicht raten.

**Nächster Schritt:** `balance_usd` im SignalAgent zur Laufzeit prüfen und
die beiden Sizing-Pfade zusammenführen.

---

## GELÖST (05.08. 04:05) — der Kaufpfad buchte nie ein

**Root Cause: eine fehlende Zeile in `execution/engine.py`.** Im
Paper-BUY-Pfad wurde USDC abgezogen (`:273-276`) und der Einstand gesetzt
(`:283-288`), aber **`self._paper_balances[asset]` nie erhöht**. Im ganzen
Modul gab es nur Stellen, die den Asset-Bestand verringern (`:318`) oder
löschen (`:320`).

Zeile 282 beweist die Absicht: `_alt_qty = self._paper_balances.get(asset, 0) - qty`
rechnet den alten Bestand als "neuer minus qty" zurück — setzt also eine
Erhöhung voraus, die es nicht gab.

**Vier Folgen, alle belegt:**
1. Jede gekaufte Position hatte Bestand 0 → Wächter-Alarme
2. Jeder Verkauf scheiterte am Phantom-Schutz (`:302-306`) — am 05.08.
   01:58:02 traf es ADA bei **+19,37 %** Trailing-Stop
3. 10 Rejects in Folge → 15 Minuten Schlafmodus. **Das ist die Quelle der
   7 598 Sleep-Mode-Zeilen im 24-Stunden-Log.**
4. `_alt_qty` war immer negativ → die E9-Einstandsmittelung vom 29.07.
   konnte **nie** greifen, der Einstand wurde bei jedem Nachkauf
   überschrieben statt gemittelt

**Verifikation nach dem Neustart um 04:00:**

| Prüfung | Ergebnis |
|---|---|
| Wächter-Alarme | **0** |
| Phantom-Ablehnungen | **0** |
| Paper-Bestand | `{'USDC': 169.32, 'BTC': 0.00171745, 'ETH': 0.05904528, 'SOL': 1.49031218}` |

Zum ersten Mal stehen echte Coin-Bestände in der Paper-Balance.
Backup: `execution/engine.py.bak_paperbuy_20260805`.

---

## ERLEDIGT (vorher offen) — Geisterpositionen bei Käufen

Der Start-Sync wirkt, aber der Bug ist damit nicht vollständig weg:

```
[2026-08-05T03:21:50] [WAECHTER] ALARM: BTC Position 0.001717, Bestand nur 0.000000
[2026-08-05T03:21:52] [WAECHTER] ALARM: ETH Position 0.059045, Bestand nur 0.000000
```

Diese Positionen wurden **nach** dem Reset (03:04) gekauft. Ein Kauf trägt
also eine Position in den State ein, ohne dass auf der Paper-Börse ein
Bestand entsteht. Mein `_sync_paper_bestand()` deckt nur den Startfall ab.

**Das ist der wichtigere der beiden offenen Punkte** — er erzeugt genau die
Rejects, die den Bot in den 15-Minuten-Schlafmodus zwingen, und er hat am
05.08. um 01:58 einen ADA-Gewinn von +19,37 % unrealisierbar gemacht.

**Nächster Schritt:** Kaufpfad prüfen — wird `_paper_balances[asset]` beim
Fill wirklich erhöht, oder läuft der Eintrag in `open_positions` an der
Börse vorbei?

---

## VORGEMERKT — Werkzeugprüfung steht weiterhin aus

Ausdrücklich festgehalten, damit es nicht untergeht:

1. **Kapitaltod des Backtest-Harness** ab ~50 $ Eigenkapital bei 20 %
   Positionsgröße (Jahr 2: 143 von 366 Tagen ohne möglichen Einstieg).
   Noch **nicht** behoben, noch **nicht** quantifiziert.
2. **45 Minuten Look-ahead** in `zu_1h()` (`messung_f2_ic.py:57-70`),
   Verzerrung bis 4,77 pp, Richtung negativ. Noch **nicht** behoben.
3. **A/B-Werkzeugvalidierung**: derselbe Datensatz einmal mit altem, einmal
   mit repariertem Harness — beziffert, wie stark die bisherigen Ergebnisse
   verzerrt waren. Kein neuer Trial, kostet kein Trial-Budget.

Erst danach ist eine Vergleichsmessung auf BTC/ETH/SOL belastbar.

---

## Sicherheit

Kein Echtgeld, keine Order, keine Kontobewegung, keine Secrets, keine
`.env` geöffnet, keine Datei gelöscht. Für jede geänderte Datei liegt ein
Backup daneben. `trades_v5.json`, `forschung.db` und alle Messausgaben
unberührt.
