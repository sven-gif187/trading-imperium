# Regel-Inventar v7 (Fraktal-Bot): Kaufweg, Verkaufsweg, Positionsgröße

**Erstellt:** 25.09.2026, 16:10–17:25, Agent `bot-pruefer`, **nur lesend**.
**Ordner:** `C:\Users\<BENUTZER>\Desktop\trading_imperium_v7`
**Nummern vergeben (25.09., v6-Sitzung):**

- SOFORT-1 bis SOFORT-4 → Befunde 113–116
- B-a bis B-e → Befunde 117–121
- SOFORT-5 und Abschnitt 5 → Ergänzungen

Maßgeblich ist `GEFUNDENE-PROBLEME.md`.

**Auftrag:** nur das Regel-Inventar (Abschnitt 2). Keine allgemeine Fehlersuche (Abschnitt 3). Was beim Verfolgen der Wege nach Kapital- oder Datenverlust aussah, steht im Sofort-Block.

> **Achtung, Zeilennummern:** Die andere Sitzung hat `app.py` um 16:28 geändert (Befund 111, Port) und `data_store/config.json` um 16:28 umgestellt. Alle `app.py`-Fundstellen unten sind **nach** dieser Änderung neu ausgelesen (Stand 17:15). Die anderen Dateien sind seit 21.09. unverändert.

---

## 1. Umfang der Prüfung

**Ganz gelesen (die Teile auf dem Handelsweg):**
- `app.py`: `__init__` (Z. 155–567), Verdrahtung und Takte (569–797), `_on_market_update`, `_on_signal`, `_on_risk_approved`, `_warteauftraege_takt`, `_execute_approved_trade`, `_buche_ergebnis`, `_trading_tick` (inkl. Direktkauf bei Angst), `_asset_erlaubt`, `_close_all_positions_safety`, `_on_kill_switch`, `_on_order_filled` (Ausschnitt). **Nicht** gelesen: Telemetrie-, Bericht-, V4-Sync- und Start/Stopp-Teile (zusammen gut die Hälfte der 5.042 Zeilen).
- `agents/signal_agent.py`, `features/fraktal_tor.py`, `features/fraktal_ziele.py`
- `risk/engine.py`, `risk/exit_rules.py`, `risk/coin_stops.py`, `risk/regime_profiles.py`, `risk/position_sizing.py`, `risk/exposure.py`, `risk/kill_switch.py`, `risk/drawdown_guard.py`, `risk/reentry_guard.py`
- `runtime/exit_monitor.py`
- `execution/engine.py` (bis auf die Papier-Gebührensätze Z. 320–400), `execution/warteauftraege.py`, `execution/warteauftraege_live.py`
- `portfolio/manager.py` (Z. 36–558), `portfolio/agent.py` (Z. 20–160)
- `data/nupl_monitor.py`, `agents/smart_entry.py`, `agents/dca_advanced.py`, `core/regel_schalter.py`
- `data_store/config.json` (zweimal: vor und nach der Umstellung um 16:28), `config_epochs.json`, `config_regime_filter.json`
- `CLAUDE.md`, `PROJEKT-ENTSCHEIDUNGEN.md`, `PROMPT_WEITERARBEIT_PC.md`, `BOT-HANDBUCH.md` Teil 1–3 sowie 4.9, 6.10–6.14, Teil 9 Runde 1–2

**Nur überflogen:** `portfolio/daily_loss.py` (Kopf und Funktionen), `features/safety.py` (Signaturen), `agents/cycle_theory.py` (nur wie die Phase entsteht), `agents/btc_accumulator.py` (Umbuchung), `reports/telegram.py` (`_do_sell`), `ui/main_window.py` (nur die Hand-Verkauf-Stellen), `live_einrichten.py` (Einstellungsblock).

**Gar nicht angesehen:** `features/fraktal_konfluenz.py` (Zonenbildung im Detail), `runtime/state_manager.py` und `live/state_recovery.py` (Bestandsübernahme nur über Handbuch 6.12 und das Log), `risk/hold_recovery.py`, `risk/exit_rules_schatten.py` (verkaufen beide nicht), `agents/v4_strategies.py`, `models/v4_calibrator.py`, `data/market_data.py`, `core/scheduler.py` (ob Aufgaben parallel laufen), `ordner_scan.py` (gehört zu Abschnitt 3).

**Log („Wirkt sie?"):** `data_store/system.log`, die sieben letzten Tage mit Einträgen vor Auftragsbeginn: **15.–21.09.2026**.
- Der Handelstakt lief nur vom **15.09. bis 17.09. gegen 12 Uhr (UTC)**. Vom 18.–21.09. stehen nur 14/4/36/38 Zeilen im Log, alles Datenabrufe ohne Handel.
- Gezählt sind **Logzeilen**, keine unabhängigen Fälle. Der Bot prüft alle 12 Sekunden. In Klammern steht deshalb die Zahl der **verschiedenen Stunden** mit mindestens einem Treffer, als grober Ersatz für unabhängige Fälle.
- Testzeilen (`TEST/USDC`, `ORD-1`) sind herausgerechnet. Die Testskripte schreiben ins echte Log.
- `system.log.1` gibt es nicht. `system.log.vor_saeuberung_20260915_112346` (14.–15.09.) ist nicht mitgezählt, um nichts doppelt zu zählen.
- Log-Zeiten sind UTC (Ortszeit = UTC + 2 h).
- **Nicht gezählt:** Der heutige Lauf (25.09. ab 14:23 UTC) kam erst während der Prüfung dazu. Er hat Kapitalbasis 0,00 $ und keinen einzigen Kaufkandidaten.
- Zählskript (nur lesend): `regel_inventar_zaehlen.py` im Hauptordner.

**Pflichtprüfungen:**
- `python schon_bekannt.py` in **beiden** Ordnern für 20 Stichworte. Beide Ordner liefern dieselben Antworten, Ergebnisse siehe Abschnitte 4 und 5.
- `search_session_transcripts` stand zur Verfügung. Gesucht wurde nach: `acknowledged`, `NICHT einsehbar`, `Paper-Bestand aus State`, `update_equity`, `[balanced]`, `Fraktal-Tor umgeht`, `Warte-Auftrag live`, `Direktkauf`, `regel_modi`, `Drawdown-Guard`, `Rückfall auf Papier`. Zu keinem Befund unten gibt es eine frühere Besprechung. `[balanced]` taucht nur als Logzeile auf, `regel_modi` nur als Konfigurationsauszug.

**Handprobe (CLAUDE.md §0), Größenkette am ersten Echtgeld-Kauf, system.log Z. 247–256 (14.09. 19:22):**

| Schritt | Rechnung | Log |
|---|---|---|
| Signal: 50 % von 36,25 $ | 18,125 | `-> 50% = 18.12$` ✓ |
| Münz-Klumpengrenze 35 % | 36,25 × 0,35 = 12,69 | `Exposure angepasst: 12.69$` ✓ |
| Größenrechner: 36,25 × 30 % × (0,5 + 0,9) × 0,5 (MID_BEAR) × 1,0 | 7,6125 | `Sizing: 7.61$` ✓ |
| Überschreibung auf balanced 30 % | 36,25 × 0,30 = 10,875 | `[balanced] 7.61$ -> 10.87$` ✓, Order 10,87 $ ✓ |

---

## 2. SOFORT-BLOCK: Risiko für Kapital- oder Datenverlust

**Stand jetzt, zuerst lesen:**
- Laut Log läuft seit **25.09. 14:23 UTC (16:23 Ortszeit)** ein v7-Prozess, gestartet mit `mode=live`: „🔴 LIVE-MODUS aktiv", Bybit EU verbunden, USDC 0,00, ETH 0,000268.
- Um 16:28 wurde `config.json` auf `paper` gestellt, und im Log steht „Paper-Balance gesetzt: 500.00", danach aber durchgehend `USDC: 0.00$`.
- Die Ausführung (`execution/engine.py:35`) liest den Modus **nur beim Start**. **OFFEN:** ob dieser Prozess noch echt ausführt. Solange auf dem Konto 0 USDC liegen, kann er nicht kaufen (Kapital unter 10 $, Regel K5). Der Prozess wurde nicht angefasst.

### SOFORT-1: Echte Warteaufträge (Limit-Order) werden nie als ausgeführt erkannt
*Vorschlag: v7-Befund 113. `schon_bekannt`: `warteauftraege_live.py:133` und `acknowledged` NEU in beiden Ordnern. `fetch_order` ist nur als alter Punkt aus Befund 68 bekannt.*

- **Fundstelle:** `execution/warteauftraege_live.py:133` fragt den Status **nur** über `fetch_order` ab. Bybit wirft dort `ArgumentsRequired … can only access an order if it is in last 500 orders … Set params["acknowledged"]`. `status()` liefert dann immer „unklar" (Z. 163–167). Der Takt überspringt „unklar" (`execution/engine.py:1173-1174`).
- **Ursachenkette:** Die Börse führt den Auftrag aus → der Takt fragt nach → „unklar" → es wird nichts gebucht. Beim Ablauf ruft er `zuruecknehmen` auf → wieder „unklar" → der Auftrag bleibt für immer in der Liste. Die Münze ist damit für neue Käufe gesperrt („läuft bereits"), und der gekaufte Bestand steht in keinem Register. **Kein Stop-Loss.**
- **Beleg im Log:**
  - 17.09. 01:25:54: echter BTC-Auftrag, Limit 76.470,33, Menge 0,000135.
  - 01:26:08 bis 01:29:10: sechsmal „nicht abfragbar (ArgumentsRequired …)".
  - 17.09. 08:45:23, nach einem Neustart: `RECOVERY BTC: 0.00013549 an der Boerse, lokal unbekannt`, übernommen mit „Echter Einstand 76,472.08$".
  - Rund **7 Stunden ungeschützt**, etwa 10,36 $ oder 30 % des Kontos. Bis 08:44 verdeckte zusätzlich der schon bekannte `'str' object`-Fehler den Takt. Nach dessen Behebung wurde kein echter Warteauftrag mehr gestellt, die Stelle ist im Betrieb also ungeprüft.
- **Reichweite:** jede künftige Füllung eines echten Warteauftrags (alle Käufe, solange `warteauftraege.aktiv=true` und `nur_paper=false`), beide Kaufwege.
- **Lösungswege** (Risiko / Aufwand / Wirkung, je 0–10):
  - **minimal:** vor jedem Echtstart `warteauftraege.nur_paper=true` (1 / 1 / 6). Das ist eine Verhaltensänderung und braucht eine Epochengrenze.
  - **sauber:** `status()` wie der Sofortkauf in `engine.py:861-957` bauen: `fetch_order` mit `{"acknowledged": True}`, dann `fetch_open_order`/`fetch_closed_order`, zuletzt `fetch_my_trades` nach `orderLinkId`. Dazu ein echter Durchlauf gegen die Börse statt nur Tests mit Nachbildungen (4 / 4 / 9).
  - **strukturell:** im laufenden Betrieb Börsenbestand und Register regelmäßig abgleichen, nicht nur beim Start (5 / 7 / 10).
- **Empfehlung:** der saubere Weg, und bis er steht kein Echtbetrieb mit Warteaufträgen.
- **Konfidenz:** SICHER für den scheiternden Abruf (Log 17.09. 01:26–01:29, Code `warteauftraege_live.py:133`). WAHRSCHEINLICH, dass jede künftige Füllung verloren geht.

### SOFORT-2: Jeder weitere Kaufwunsch stellt einen echten Zusatzauftrag, und dessen Rücknahme wird nicht verfolgt
*Vorschlag: v7-Befund 114. `schon_bekannt`: „laeuft bereits" ist nur in anderem Zusammenhang bekannt (Chronik 11.08., Aufgabenplanung). Dieser Mechanismus ist NEU.*

- **Fundstelle:** `execution/engine.py:1075-1087` stellt die echte Order **vor** der Listenprüfung. Läuft schon einer (Z. 1101–1110), wird der neue Auftrag über `zuruecknehmen()` storniert, dessen Rückgabe aber **ignoriert**. Der Stornostatus läuft über dasselbe `fetch_order` wie in SOFORT-1 und bleibt „unklar".
- **Ursachenkette:** Die Münze hat noch keine Position, solange ihr Auftrag wartet. Jeder Takt (12 s) mit Score ≥ 7 und offenem Tor wird deshalb vom Türsteher genehmigt → echte Order → Rücknahme → Ergebnis unbekannt. Eine Rücknahme, die nicht greift, hinterlässt einen **verwaisten Auftrag**. Er bindet Geld und kann später ausgeführt werden, wieder ohne Register und ohne Stop.
- **Beleg:** 17.09. 01:26:04 bis 01:29:10, fünf Zusatzaufträge (IDs 2305796514733517056 … 2305798044001921280), alle mit „nach Ruecknahmeversuch NICHT einsehbar". Ob sie wirklich storniert wurden: **OFFEN** (steht nur in der Bybit-Auftragshistorie).
- **Reichweite:** alle echten Warteaufträge. Kaufweg 2 verstärkt das: Er vermerkt „wartet" nicht (Regel D13) und versucht es deshalb alle 12 s erneut.
- **Lösungswege:**
  - **minimal:** vor dem Stellen `symbol in warteschlange.offene()` prüfen und gar nicht erst senden (2 / 1 / 8).
  - **sauber:** zusätzlich das Ergebnis jeder Rücknahme festhalten und unklare Aufträge in einer Liste „verwaist" weiterverfolgen (3 / 3 / 9).
  - **strukturell:** bei jedem Takt `fetch_open_orders` gegen die Warteschlange abgleichen (4 / 5 / 10).
- **Empfehlung:** minimal. Das behebt die Ursache, also die Reihenfolge.
- **Konfidenz:** SICHER (Code `engine.py:1075-1110`, Log 17.09. 01:26–01:29).

### SOFORT-3: Verbindungsfehler beim Start → stiller Wechsel auf Papier, obwohl die Einstellung „live" sagt
*Vorschlag: v7-Befund 115. `schon_bekannt`: `engine.py:227` NEU. `_paper_mode` kennt die Doku nur aus Befund 49 und Handbuch 1.2, dort aber nur für den Fall „Schlüssel fehlt".*

- **Fundstelle:** `execution/engine.py:226-227`. Jeder Fehler beim Verbinden (auch eine kurze Netzstörung) setzt `self._paper_mode = True`. Die Einstellung bleibt „live".
- **Ursachenkette:** Die Papierkasse wird mit `initial_paper_balance` = 500 $ angelegt. Die echten Positionen aus dem Register werden in die Papierkasse übernommen („Paper-Bestand aus State ergaenzt"). Stop-Loss und Trailing verkaufen dann **auf Papier** und löschen die Position aus dem Register, während der echte Bestand auf der Börse ohne Schutz liegen bleibt. Das Journal des Echtgeld-Bots bekommt Papier-Handel. Kapital-Deckel (`portfolio/manager.py:61`), Telegram-Kennung und Startmeldung behandeln den Bot weiter als „live".
- **Beleg:**
  - 17.09. 11:28:40 und 11:56:06: `[EXEC] Exchange-Fehler: bybit … query-info`.
  - 11:30:23: `Paper-Bestand aus State ergaenzt: BTC=0.000135, ETH=0.000268`.
  - 11:45:26: `[PAPER] SELL ETH/USDC: Netto 0.65$`. Nachgerechnet: 0,000268 × 2.427,63 = 0,6506 $ ✓.
  - `trades_v5.json`, letzter Eintrag `2026-09-17T11:45:27 SELL ETH 0.000268 TRAILING_STOP`, **ohne Papier-Kennzeichen**. `PROMPT_WEITERARBEIT_PC.md` §1 zählt ihn als echten Trade („Letzter Trade 17.09. 11:45").
  - Die ETH lag danach weiter auf der Börse (heute 14:27 UTC: `ETH: 0.00026800 an der Boerse, lokal unbekannt`).
  - Dazu 11:45:07: `Exposure angepasst: 70.00$` = 35 % von 200 $ Deckel bei 511 $ Papierkapital. Der Deckel für echtes Geld griff also auf Papiergeld.
- **Reichweite:** jeder Echtstart mit Netzstörung. Folgen: echte Bestände ohne Stop, verfälschtes Journal (Datenverlust für Kriterium A und alle Auswertungen).
- **Lösungswege:**
  - **minimal:** bei `mode=live` und Verbindungsfehler den Start abbrechen, laut, per Telegram (3 / 1 / 8).
  - **sauber:** Rückfall nur mit eigenem, getrenntem Zustand und Journal, jeder Eintrag mit `modus` gekennzeichnet (4 / 4 / 7).
  - **strukturell:** den Modus aus **einer** Quelle lesen (die Ausführung) für alle Module (5 / 6 / 10).
- **Empfehlung:** minimal.
- **Konfidenz:** SICHER (Code und Log wie oben).

### SOFORT-4: Eine ausgeführte Warteauftrags-Füllung geht verloren, wenn die Handelssperre 10 s belegt ist
*Vorschlag: v7-Befund 116. `schon_bekannt`: „NICHT gebucht" NEU.*

- **Fundstelle:** `app.py:1328-1333`. Ist die Sperre (Trade-Lock) belegt, steht nur eine Fehlerzeile im Log („NICHT gebucht") und es geht weiter mit `continue`. Der Auftrag ist zu diesem Zeitpunkt **schon aus der Liste**: `execution/engine.py:1186` (echt) bzw. `execution/warteauftraege.py:216` (Papier). Ein Fehler in `_buche_ergebnis` endet genauso (`app.py:1334-1336`).
- **Folge:** Gekaufter Bestand ohne Register bis zum nächsten Neustart. Das ist das Muster „nur geloggt, dann ignoriert" (CLAUDE.md 7.4).
- **Wirkt:** 0 Fälle am 15.–21.09.
- **Lösungswege:**
  - **minimal:** ohne Zeitlimit auf die Sperre warten (3 / 1 / 7).
  - **sauber:** den Auftrag erst nach erfolgreicher Buchung aus der Liste nehmen (3 / 3 / 9).
  - **strukturell:** wie SOFORT-1 (5 / 7 / 10).
- **Empfehlung:** sauber.
- **Konfidenz:** SICHER für den Code. Wie oft es passiert: OFFEN.

### SOFORT-5: Kaufweg 2 (Direktkauf bei Angst) umgeht Svens Verfahren, und sein Abschalter ist ein Scheinschalter
*Ergänzung zur Chronik 25.07.2026 (BUG REPORT „DCA-Config wirkungslos"). `dca_enabled` ist BEKANNT. Neu ist die Verbindung zum Fraktal-Tor und zu den Warteaufträgen.*

- **Fundstelle:** `app.py:2948` (`if fg < 30`) bis 3269. `trading.dca_enabled=false` wird im ganzen Handelscode **nicht gelesen** (nur `config/settings.py:323` und `live_einrichten.py:101`).
- **Was Weg 2 nicht prüft:** Fraktal-Tor, Score-Schwelle 7, Bärenmarkt-Regel, Verlustserie, Sektor, Bargeld-Reserve, NUPL, Spanne und Volumen, Handelssperre, Größen-Überschreibung.
- **Kaufbetrag:** 50 % × Regime-Faktor, mindestens 10 $ (`app.py:2987-2992`). Bei 23,50 $ Konto sind das 43–100 %.
- **Dazu:** Der Rückgabewert „wartet" wird nicht vermerkt (`app.py:3162-3169`, `record_dca` nur bei „filled"). Im Echtbetrieb entsteht damit alle 12 s ein Zusatzauftrag wie in SOFORT-2.
- **Wirkt:** 0. Der Angst-und-Gier-Wert lag im Zeitraum bei 50–71 (Log „F&G: 50/51/57/69/71"). Der Weg ist nicht abgeschaltet, er wartet auf Angst.
- **Lösungswege:**
  - **minimal:** `dca_enabled` in `app.py:2948` abfragen (2 / 1 / 8; Verhaltensänderung nur für F&G < 30, braucht trotzdem eine Epochengrenze).
  - **sauber:** Weg 2 durch den gemeinsamen Trichter schicken (`_on_signal` → Türsteher → Tor) (5 / 5 / 9).
  - **strukturell:** ein einziger Kaufweg (6 / 7 / 10).
- **Empfehlung:** minimal.
- **Konfidenz:** SICHER für den Code. Dass der Weg in dieser Woche geschlafen hat: SICHER (Log).

---

## 3. Regel-Inventar

**Legende**
- **Modus:** P = greift nur im Papierhandel, L = nur im Echtbetrieb, P+L = beide.
- **Schalter:** `cfg:` = `data_store/config.json`, `rm:` = `regel_modi`, **fest** = im Code.
- **Handbuch:** Abschnitt in `BOT-HANDBUCH.md`. „nein" = nirgends im Handbuch.
- **Gemessen:** Nummer oder Stelle, an der die **Wirkung** der Regel gemessen wurde.
- **Wirkt?** Logzeilen 15.–21.09. (verschiedene Stunden).

**Einstellungen, Stand 25.09. 17:15:**
- `trading.mode = "paper"` (bis 16:28: `"live"`)
- `min_signal_score 7`, `trading.position_size_pct 50`
- `modes.active_mode balanced`: 30 %, 3 Positionen, 10 % Reserve, Münze 35 %, Sektor 80 %
- `risk.stop_loss_pct 2.5`, `trailing_stop_pct 1.0`, `take_profit_pct 0.0`
- `risk.max_exposure_per_coin_pct` **55** (bis 16:28: 35)
- `risk.max_daily_loss_usd 100`, `daily_loss {aktiv, 6}`
- `live_max_order_usd 25`, `live_max_capital_usd 200`
- `warteauftraege {aktiv: true, abstand 0.1, 4 × 15 min, nur_paper: false}`
- `fraktal_tor_aktiv true`, `nur_messen false`

**Zahl der Regeln:** Takt/Weiche **5** · Kaufweg 1 **37** · Kaufweg 2 **13** · Ausführung (beide Kaufwege) **13** · Positionsgröße **11** · Verkaufsweg **24**. **Zusammen 103.**

### 3a. Takt und Weiche (gilt für beide Kaufwege, teils auch für den Verkauf)

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| T1 | `app.py:2731` | Handelspause per Telegram (`/botstop`): der ganze Takt fällt aus, also Kauf auf **beiden** Wegen, **Verkauf bei überkauftem Markt (RSI > 80)** und Gewinnziel. Nur die Stop-Loss-Überwachung läuft weiter | aus | fest, nur im Speicher | nein | nein | nicht protokolliert | P+L | SICHER |
| T2 | `app.py:2743`, `portfolio/daily_loss.py:186-220` | Tagesverlust-Pause: realisierter Tagesverlust ≥ 6 % des Tagesstart-Kapitals → Takt fällt aus. Auch hier fällt der RSI-Verkauf mit weg | 6 %, aktiv | cfg: `risk.daily_loss` | nein (Teil 9, Runde 10) | nein | 0 (nur „Neuer Tag") | P+L | SICHER |
| T3 | `app.py:2758` | nur die ersten 12 Münzen | 3 Münzen, greift nicht | fest | nein | nein | – | P+L | SICHER |
| T4 | `app.py:817-820` | Wartet für die Münze ein zurückgestellter Kauf (Smart-Entry), wird **nur** dieser geprüft. Keine Analyse, auch keine Verkaufsprüfung im Signalpfad | – | fest | 2.2 (nur Kauf erwähnt) | nein | 0 | P+L | SICHER |
| T5 | `app.py:932-941` | Weiche: Münze mit Position → erst Verkaufsprüfung. Ohne Verkaufsgrund läuft **trotzdem** die Kaufprüfung weiter (Tor wird gerechnet, der Türsteher lehnt dann „Bereits in Position" ab) | – | fest | 2.2 sagt das Gegenteil | nein | siehe K32 | P+L | SICHER |

### 3b. Kaufweg 1: Signal → Punktzahl (Score) → Fraktal-Tor → Sperren → Türsteher → letzte Hürden

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| K1 | `signal_agent.py:56` | mindestens 30 Kerzen, sonst kein Kandidat | 30 | fest | nein | nein | nicht protokolliert | P+L | SICHER |
| K2 | `signal_agent.py:63` | Gitter-Handel (Grid) vor der Punktzählung | aus | cfg: `grid_enabled=false` (bewusst stillgelegt) | 1.7 | – | aus | P+L | SICHER |
| K3 | `signal_agent.py:90-175` | Punktetabelle, 14 Posten: RSI < 30/35/45 → +3/2/1 · MACD +2/+1 · EMA-Trend +1 · ADX > 25 +1 · Angst-und-Gier < 15/25/35 → +3/2/1 · Bollinger + RSI < 40 → +2 · RSI-Divergenz +2 · Volumen > 2× → +1 · Ensemble > 0,75/0,65 → +2/+1 · VWAP +1 · Orderbuch > 0,15 → +1 · V4 ≥ 0,7/0,5/0,3 → +4/3/2 | alle fest | fest | 2.3 teilweise (RSI, MACD, EMA, Orderbuch fehlen) | Befund 103 (Score als Ganzes) | – | P+L | SICHER |
| K4 | `signal_agent.py:199-200` | Kauf nur bei Punktzahl ≥ Schwelle | **7** | cfg: `trading.min_signal_score` | 6.11 (2.3 nennt noch 3) | Befund 103 (57 Papier-Verkäufe, **ohne** Tor) | 7.373 Kandidaten über der Schwelle (36 Std). Unterschreitungen werden nicht protokolliert | P+L | SICHER |
| K5 | `signal_agent.py:200` | Kapital (Cash + Positionen) muss > 10 $ sein | 10 $ | fest | 2.3 („10 $ frei", ungenau) | nein | nicht protokolliert. **Heute 25.09.: Kapital 0 $ → sperrt alles** | P+L | SICHER |
| K6 | `app.py:341-356` | Lässt sich das Tor beim Start nicht bauen, kauft der Bot **ohne Tor** weiter (nur eine Fehlerzeile) | – | fest | nein | nein | 0 | P+L | SICHER |
| K7 | `signal_agent.py:219-226` | Fehler im Tor zur Laufzeit → Kauf abgelehnt | – | fest | 6.11 | nein | 0 | P+L | SICHER |
| K8 | `fraktal_tor.py:366` | weniger als 2 Zeitrahmen mit Kerzen → ablehnen | 2 von 1h/4h/1d | fest | nein | nein | 0 | P+L | SICHER |
| K9 | `fraktal_tor.py:172,299` | nur Aufwärtswellen bilden Kaufzonen | an | fest (`NUR_AUFWAERTSWELLEN`) | nein (nur `config_epochs.json` L2 und PROMPT §2) | Rückmessung 14.09. (4 von 4 Käufen abgelehnt) | im Tor-Grund mitgezählt | P+L | SICHER |
| K10 | `fraktal_tor.py:131,305` | Welle muss ≥ 2,0 % Spanne haben | 2,0 % | fest | 6.11 | wie K9 | wie K9 | P+L | SICHER |
| K11 | `fraktal_tor.py:144,331` | nur Rücksetzer ab 0,5 der Welle | 0,5 | fest | 6.11 | wie K9 | wie K9 | P+L | SICHER |
| K12 | `fraktal_tor.py:191` | höchstens 6 rohe Wellen je Zeitrahmen | 6 | fest | nein | nein | – | P+L | SICHER |
| K13 | `fraktal_tor.py:87,92,249` | 200 Kerzen je Zeitrahmen, gültig 5/20/60 min, nach Fehlabruf 60 s gesperrt | – | fest | nein | nein | 6 Zeilen „keine verwertbaren Kerzen" | P+L | SICHER |
| K14 | `fraktal_tor.py:111,338` | Zonen nur bis 0,5 % über dem Preis | 0,5 % | fest | nein (PROMPT §2) | nein | – | P+L | SICHER |
| K15 | `fraktal_tor.py:106,375` | Zonen-Score ≥ 3 | 3 | fest | nein (PROMPT §2) | nein | – | P+L | SICHER |
| K16 | `fraktal_tor.py:97,393-399` | Preis im Zonenband **oder** ≤ 0,35 % von der Zonenmitte | 0,35 % | fest | nein (PROMPT §2) | nein | **Tor gesamt: lehnt ab 9.065** (8.528 „keine Zone", 541 „neben Zone"; 35 Std), **lässt durch 7.366** (36 Std) | P+L | SICHER |
| K17 | `app.py:2090-2096` | Die Kaufwelle für das Fibonacci-Ziel ist das **letzte** Tor-Urteil der Münze **zum Buchungszeitpunkt**. Bei einem Warteauftrag kann das bis 60 min später sein, dann fehlt die Welle oder es ist eine andere | – | fest | nein | nein | 3 Wellen gemerkt (nur Sofortkäufe) | P+L | SICHER (Code), Wirkung VERMUTUNG |
| K18 | `app.py:1038-1057` | Regime-Filter: bestätigter Abwärtstrend → kein Kauf. Bei eigenem Fehler: Kauf durchgelassen | **aus seit L3** | `config_regime_filter.json enabled=false` | 2.4, 6.13 | 2.4 (gemessen **ohne** Tor) | 1.019 (6 Std, nur 15.09. vor 12:23 UTC) | P+L | SICHER |
| K19 | `app.py:1085-1099`, Werte `app.py:484-485` | Wiedereinstiegs-Sperre 1: 90 min nach einem Verkauf kein Kauf, danach bis 6 h nur ≥ 1 % unter dem Verkaufspreis. Bei eigenem Fehler: Kauf durchgelassen | 90 min / 6 h / 1 % | fest. `rm: wiedereinstieg_sperre` wird **nicht gelesen** | 2.4, Teil 9 | nur das Problem (338 Fälle), nicht die Wirkung | 1.861 (13 Std) | P+L | SICHER |
| K20 | `app.py:1106`, `3514` | Modus-Sperre „nur eine Münze" | leer → aus | cfg: `modes.balanced.nur_asset` | 2.4 | nein | 0 | P+L | SICHER |
| K21 | `app.py:1150`, `smart_entry.py:15` | Smart-Entry: Kurs in 5 Kerzen > 3 % gestiegen → zurückstellen. Kauf bei 1 % Rücksetzer, nach 300 s oder bei weiteren +2 %. Beim späteren Kauf **keine** neue Tor-, Regime- oder Modusprüfung | 3 % / 1 % / 2 % / 300 s | fest. `rm: smart_entry` wird **nicht gelesen** | 2.2 (ohne Zahlen) | nein | 0 | P+L | SICHER |
| K22 | `app.py:1231-1245` | Wiedereinstiegs-Sperre 2 im gemeinsamen Trichter | wie K19 | fest | 2.4 | nein | 0 | P+L | SICHER |
| K23 | `risk/engine.py:84-85,200-206` | Schlafmodus des Türstehers: 10 echte Störungen in Folge → 15 min keine Käufe | 10 / 15 min | fest | 2.5, Teil 9 | nein | 0 | P+L | SICHER |
| K24 | `risk/engine.py:64-68,228-240`, `kill_switch.py:27` | Notbremse (Kill-Switch): Verluste ≥ 100 $ → keine Käufe. Zähler seit **Programmstart** (kein automatischer Tagesreset, nur Knopf im Cockpit), nur im Speicher. `kill_switch_enabled` wird nicht gelesen | 100 $ (Konto 23,50 $, **unerreichbar**) | cfg: `risk.max_daily_loss_usd` | 2.5 („Tagesverlust") | nein | 0 | P+L | SICHER |
| K25 | `risk/engine.py:243-247` | Rückgang vom Höchststand (Drawdown) ≥ 15 % → keine Käufe. **Tot:** `update_equity()` hat keinen Aufrufer, der Höchststand bleibt 0 | 15 % | cfg: `risk.max_drawdown_pct` | 2.5, Teil 9 | nein | 0 | P+L | SICHER |
| K26 | `risk/engine.py:250-259`, `portfolio/manager.py:360` | höchstens so viele Positionen wie der Modus erlaubt | **3** (`live_einrichten.py:96` wollte 1) | cfg: `modes.balanced.max_positions` | 2.5, 1.3 | nein | 0 | P+L | SICHER |
| K27 | `risk/engine.py:273-277` | Kapital unbekannt oder ≤ 0 → ablehnen (zählt als Störung für K23) | – | fest | nein | nein | 0 | P+L | SICHER |
| K28 | `risk/engine.py:278-286` | Münz-Klumpen: über der Grenze → auf die Grenze kürzen (wenn > 5 $), sonst ablehnen | 35 %, nach der ersten Freigabe **55 %** (siehe G11) | cfg: `modes.balanced.max_coin_pct` + `risk.max_exposure_per_coin_pct` | 2.5 | nein | **Kürzung 3.515 (30 Std)**, Ablehnung 0 | P+L | SICHER |
| K29 | `risk/engine.py:60,288-291` | Sektor ≤ 80 %. Fest im Code, `sector_limit_pct` wird hier nicht gelesen | 80 % | fest | 2.5 (Teil 9 nennt falsch 40 %) | nein | 0 | P+L | SICHER |
| K30 | `risk/engine.py:79,294-305` | Sperre nach Verlustserie: ≥ 3 Verluste in Folge je Münze. Aufhebung ab Score 50, bei einer Skala 0–10 **unerreichbar** | 3 / 50 | cfg: `cooldown_after_losses`, 50 fest | 2.5 | nein | 0 (BTC-Zähler stand bei 2) | P+L | SICHER |
| K31 | `risk/engine.py:308-311` | Bärenmarkt: Zyklus MID_BEAR, DEEP_BEAR oder CAPITULATION → nur BTC und ETH. Die Phase kommt fest aus Halving-Datum und Allzeithoch (`agents/cycle_theory.py`) | heute EARLY_BEAR → greift nicht | fest. `rm: baerenmarkt` wird **nicht gelesen** | 2.5 | nein | 1.748 (19 Std; SOL) | P+L | SICHER |
| K32 | `risk/engine.py:314-316` | bereits in Position | – | fest | 2.5 | nein | 2.735 (21 Std) | P+L | SICHER |
| K33 | `app.py:1272-1276` | Handelssperre (Trade-Lock) belegt → Kauf **verworfen** | – | fest | 2.6 | nein | 0 | P+L | SICHER |
| K34 | `app.py:1517` | Kapital ≤ 0 → Abbruch | – | fest | nein | nein | 0 | P+L | SICHER |
| K35 | `app.py:1544-1551`, `portfolio/agent.py:42-159` | Portfolio-Prüfung: Bargeld-Reserve 10 %, Mindestauftrag max(0,5 % Kapital; 5 $), Münze 35 %, Sektor 80 %, Korrelation höchstens 3 (Korrelationsfehler → durchlassen, Z. 144) | 10 % / 5 $ / 35 / 80 / 3 | cfg: `modes.balanced`, Rest fest | 2.6 (nur Klumpenrisiko) | nein | 0 | P+L | SICHER |
| K36 | `app.py:1554-1565`, `portfolio/manager.py:507-533` | Spanne (Spread) > 0,5 % oder 24h-Volumen < 1 Mio. $ → Abbruch. Bei Fehler **übersprungen** | 0,5 % / 1 Mio. | cfg: `max_spread_pct`, `min_volume_24h_usd` | 2.6 | nein | 0 | **L** | SICHER |
| K37 | `app.py:1583`, `data/nupl_monitor.py:54-56,86` | Euphorie-Bremse (NUPL > 0,7). Ersatzwert: gleitender 200-Tage-Schnitt = 80 % des BTC-Kurses **beim Start**, danach eingefroren. Greift erst, wenn BTC seit dem Start um 167 % steigt | 0,7 | fest | 2.6 („immer aktiv") | nein | 0 | P+L | SICHER |

### 3c. Kaufweg 2: Direktkauf bei Angst (DCA_FEAR_GREED), `app.py:2948-3269`

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| D1 | `app.py:2948` | Angst-und-Gier < 30 → Weg 2 läuft. `dca_enabled=false` wird **nicht** gelesen | 30 | fest | 2.7 | nein | 0 (F&G 50–71) | P+L | SICHER |
| D2 | `app.py:3011-3032` | Notbremse, Schlafmodus oder Drawdown → Runde aus (Drawdown tot, siehe K25) | – | fest | 2.7 | nein | 0 | P+L | SICHER |
| D3 | `app.py:3046` | Modus-Sperre | aus | cfg: `nur_asset` | 2.4 | nein | 0 | P+L | SICHER |
| D4 | `app.py:3000,3064` | höchstens 2 neue Positionen je Runde | 2 | fest | nein | nein | 0 | P+L | SICHER |
| D5 | `app.py:3061,3070` | Runde nur mit Cash ≥ Betrag ≥ 10 $, Cash-Prüfung vor jedem Kauf | – | fest | nein | nein | 0 | P+L | SICHER |
| D6 | `app.py:3074` | Münze gerade im Verkauf → überspringen | – | fest | nein | nein | 0 | P+L | SICHER |
| D7 | `app.py:3083`, `dca_advanced.py:27-57` | Abklingzeit je Münze: 15/30/45 min je nach Angst-und-Gier, nur im Speicher. Bei Fehler trotzdem kaufen | 15–45 min | fest | nein (Teil 9 nur Name) | nein | 0 | P+L | SICHER |
| D8 | `app.py:3095` | Nachkauf nur bei Kurs ≤ 98 % des Einstands. `dca_drop_pct` wird nicht gelesen | 2 % | fest | nein (Chronik 25.07.) | nein | 0 | P+L | SICHER |
| D9 | `app.py:3104` | höchstens 3 Nachkaufstufen | 3 | cfg: `dca_max_levels` | nein | nein | 0 | P+L | SICHER |
| D10 | `app.py:3112` | Nachkauf nur, wenn der Münzanteil danach ≤ Grenze bleibt | **55 %** | cfg: `risk.max_exposure_per_coin_pct` | nein | nein | 0 | P+L | SICHER |
| D11 | `app.py:3120` | neue Position nur, wenn weniger als die Höchstzahl offen ist | 3 | cfg: `risk.max_open_positions` (anderer Schlüssel als K26) | 2.7 | nein | 0 | P+L | SICHER |
| D12 | `app.py:3132` | Wiedereinstiegs-Sperre | wie K19 | fest | 2.4 | nein | 0 | P+L | SICHER |
| D13 | `app.py:3162-3169` | direkte Ausführung **ohne** Türsteher, Tor und Handelssperre. Ergebnis „wartet" wird nicht vermerkt → neuer Versuch alle 12 s | – | fest | 2.7 (ohne Folgen) | nein | 0 | P+L | SICHER |

### 3d. Ausführung (beide Kaufwege), hier trennen sich Papier und Echtbetrieb

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| A1 | `execution/engine.py:35,125-227` | Weiche Papier/Echt, **nur beim Start** gelesen. Rückfall auf Papier bei fehlendem Schlüssel (150–156), nicht bestandener Freigabe (130–140; `live_require_gate=false` → aus), Schlüssel mit Abhebe-Recht (209–212) oder **jedem Fehler beim Verbinden** (226–227) | `paper` in der Datei, laufender Prozess OFFEN | cfg: `trading.mode` | 1.2 (nur fehlender Schlüssel) | nein | **17.09. zweimal Rückfall** (11:28, 11:56) → siehe SOFORT-3 | L→P | SICHER |
| A2 | `engine.py:234-235` | doppelte Order (gleiche Kennung) → ablehnen | – | fest | Teil 9 | nein | 0 | P+L | SICHER |
| A3 | `engine.py:28,245-252,307-314` | Schlafmodus der Ausführung: 10 abgelehnte oder fehlerhafte Aufträge in Folge, **auch Verkäufe**, Mindestbetrag und „läuft bereits" → 15 min keine Käufe | 10 / 15 min | fest | 2.4 (erwähnt) | nein | 35 Zeilen (3 Std, 15.09.; ausgelöst von Staub-Verkäufen, siehe V21) | P+L | SICHER |
| A4 | `engine.py:254-271` | Cash-Reservierung gegen parallele Käufe | 60 s | fest | nein | nein | 0 | P+L | SICHER |
| A5 | `engine.py:419-443`, `warteauftraege.py:127-222` | Warteauftrag (Limit-Order) im Papier: Angebot 0,10 % unter Markt, 4 × 15 min gültig, **einer je Münze** (Z. 140), gefüllt bei Kurs ≤ Limit, verfällt danach. Notverfall bei doppelter Frist ohne Kurs. Abgelaufene werden beim Start verworfen (Z. 296–298) | aktiv | cfg: `warteauftraege.*` | 4.9 | 4.9 (382 Käufe, +0,161 PP) | 0 im Zeitraum | **P** | SICHER |
| A6 | `engine.py:494-496` | Papier: zu wenig Papiergeld beim Füllen → abgelehnt | – | fest | 4.9 | nein | 0 | P | SICHER |
| A7 | `engine.py:619-622,708-712` | kein Referenzpreis oder Menge nach Rundung 0 → ablehnen | – | fest | nein | nein | 0 | L | SICHER |
| A8 | `engine.py:732-752` | Mindestbetrag der Börse (5 USDT) → nicht senden. Gilt auch für Verkäufe (siehe V21) | 5 $ | fest (aus Börsendaten) | 6.12 (nur Übernahme) | Befund 68 | siehe V21 | L | SICHER |
| A9 | `engine.py:811-816,1056-1122` | Echter Warteauftrag: echte Limit-Order stellen. Läuft schon einer, wird **trotzdem erst gestellt**, dann zurückgenommen, ohne das Ergebnis zu verfolgen | aktiv (`nur_paper=false`) | cfg: `warteauftraege.nur_paper` | **nein** (nur Chronik 17.09., PROMPT §2) | nur Papier-Messung (4.9) | 1 echter + 5 Zusatzaufträge (17.09. 01:25–01:29), 18× „läuft bereits" | L | SICHER, siehe SOFORT-2 |
| A10 | `engine.py:1124-1186`, `warteauftraege_live.py:114-167` | Warteauftrag-Takt im Echtbetrieb: Status nur über `fetch_order`; „unklar" → nichts tun | – | fest | nein | nein | 6× „nicht abfragbar", 0 gebucht | L | SICHER, siehe SOFORT-1 |
| A11 | `app.py:1314-1336` | Buchung einer Füllung: Handelssperre 10 s belegt → **nicht gebucht** | 10 s | fest | nein | nein | 0 | P+L | SICHER, siehe SOFORT-4 |
| A12 | `engine.py:823-1027` | Sofortauftrag (Market) mit Wiederholung; nicht gefüllt nach 3 Nachfragewegen → abgelehnt | – | fest | nein (Befund 68, Chronik) | nein | 173 „Order nicht gefuellt" (4 Std, meist Verkäufe 15.09.) | L | SICHER |
| A13 | `engine.py:275-278` | Papier: simulierter Schlupf (Slippage) und Gebühr (Maker 0,10 % bei Warteauftrag, sonst Taker 0,25 %) | – | fest | 4.9, 4.10 | 4.x | – | P | WAHRSCHEINLICH (Gebührenteil nicht gelesen) |

### 3e. Positionsgröße: in dieser Reihenfolge, **die letzte Überschreibung gewinnt**

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| G1 | `app.py:975-999`, `signal_agent.py:244` | Kandidat = (Cash + bewertete Positionen, **ohne** Sparplan) × 50 % | 50 % | cfg: `trading.position_size_pct` | 2.3 | nein | jeder Kandidat, wird aber überschrieben (G4) | P+L | SICHER |
| G2 | `app.py:1013-1023` | höchstens 98 % des freien Cash | 98 % | fest | 2.4 | nein | 1.169 (7 Std, 15.09.) | P+L | SICHER |
| G3 | `risk/engine.py:319-334`, `position_sizing.py:17-57` | Größenrechner: Kapital × 30 % × (0,5 + Zuversicht) × Zyklus (MID_BEAR 0,5, EARLY_BEAR 0,6, sonst 0,8 …) × Regime; nie unter 50 % des gewollten Betrags | – | fest (30 % aus dem Modus) | Teil 9 | nein | 11 (5 Std), wird überschrieben | P+L | SICHER |
| G4 | `app.py:1588-1604`, `portfolio/manager.py:336-349` | **Überschreibung:** Betrag = Kapital × Modus-Prozent (mind. 5 $), sobald die Abweichung > 1 $ ist. **Das ist die wirksame Größenregel**; G1 und G3 bleiben ohne Folge | **30 %** | cfg: `modes.balanced.position_size_pct` | 1.3 (Wert), Mechanismus nein | nein | 11 von 11 Freigaben (Handprobe oben) | P+L | SICHER |
| G5 | `app.py:1567-1575` | mehr als freies Cash → 98 % davon; unter 5 $ → Abbruch | 98 % / 5 $ | fest | 2.6 | nein | 0 | P+L | SICHER |
| G6 | `app.py:1683-1700` | höchstens 95 % des Cash; darunter < 10 $ → Abbruch | 95 % / 10 $ | fest | nein | nein | 0 | P+L | SICHER |
| G7 | `app.py:468,1703` | ab 1.000 $ in Teilen kaufen (TWAP) | 1.000 $ | fest | nein | nein | 0 | P+L | SICHER |
| G8 | `engine.py:628-632` | Order-Deckel je Kauf | 25 $ | cfg: `live_max_order_usd` | Teil 9 | nein | 0 (Aufträge 10–11 $) | L | SICHER |
| G9 | `portfolio/manager.py:51-68` | Rechenkapital höchstens 200 $, sobald in der **Datei** „live" steht, auch nach einem Papier-Rückfall | 200 $ | cfg: `live_max_capital_usd` | nein | nein | griff 17.09. 11:45 auf Papiergeld (70 $ = 35 % × 200) | L (Datei) | SICHER |
| G10 | `app.py:2987-2992` | Weg 2: (Cash + Positionen) × **50 %** × Regime-Größenfaktor (0,5–1,5), mind. 10 $, höchstens Cash. Hier wirkt die 50 % tatsächlich | 50 % | cfg + fest | nein | nein | 0 | P+L | SICHER |
| G11 | `risk/engine.py:321-323` | Selbstlockerung: Nach jeder Freigabe steigt die Münz-Grenze auf max(`max_exposure_per_coin_pct`, Betrag% + 5). Sie sinkt nie, bis zum Neustart | 35 → **55 %** | cfg: `risk.max_exposure_per_coin_pct` (heute 16:28 von 35 auf 55) | nein | nein | – | P+L | SICHER |

### 3f. Verkaufsweg: offene Position → Ausstiegsregeln → Auftrag

| # | Fundstelle | Bedingung in Alltagssprache | Wert jetzt | Schalter | Handbuch | Gemessen | Wirkt? | Modus | Konfidenz |
|---|---|---|---|---|---|---|---|---|---|
| V1 | `app.py:828`, `exit_monitor.py:104` | Verkauf läuft schon → nichts tun | – | fest | 3.1 | – | – | P+L | SICHER |
| V2 | `app.py:834`, `exit_monitor.py:111-113` | Modus HOLD je Münze → **nie** automatisch verkaufen, **auch kein Stop-Loss** | SL (Vorgabe) | Cockpit je Münze, im Speicher bzw. Positionsfeld `mode` | 3.1, 3.2 | nein | nicht protokolliert | P+L | SICHER |
| V3 | `app.py:845-903`, `risk/engine.py:469-507` | Auto-Verteidigung (Abwärtstrend + Mehrzeitrahmen bärisch + Verlust > 2 % → die 2 schlechtesten verkaufen). **Tot:** `self.market_data` und `self.mtf_analyzer` werden nie gesetzt (`app.py:853,864`) | 2 % / 2 | fest | 3.1 (als aktiv beschrieben) | nein | 0 | P+L | SICHER |
| V4 | `signal_agent.py:289-293` | Notaus-Netz: Verlust ≥ Stop + 0,5 % → Verkauf über den Bus. Nimmt den Stop **ohne** Marktphasen-Anpassung (2,5 → 3,0 %) | 3,0 % | cfg `stop_loss_pct` + 0,5 fest | 4.9, Teil 9 | nein | 334 (3 Std, 15.09., Staubrest) | P+L | SICHER |
| V5 | `signal_agent.py:300` | RSI > 80 und Gewinn > 1 % (brutto) → Verkauf. Fällt bei T1 und T2 mit aus | 80 / 1 % | fest | 3.2 | 3.5 (v6: 12 von 12 netto im Plus) | 0 | P+L | SICHER |
| V6 | `app.py:908-930` | Gewinnziel im Signalpfad: Modus TP → ab `take_profit_pct`, bei 0 **fest 3 %**. Modus SL → nur bei `take_profit_pct` > 0 | aus (Modus SL, TP 0) | cfg + 3 % fest | 3.2 (ohne TP-Modus) | nein | 0 | P+L | SICHER |
| V7 | `exit_monitor.py:129-138`, `regime_profiles.py:13-35` | Stop und Nachzieh-Abstand je Marktphase: Stop = 2,5 × Zyklus × Regime (1,5–6,0), Trail = 1,0 × … (0,5–4,0) | MID_BEAR: 2,0 %; EARLY_BEAR: 2,125 % × Regime | cfg-Basis, Faktoren fest | Teil 9; PROMPT §2 | nein | alle 4 Stop-Loss-Verkäufe bei −2,0 % | P+L | SICHER |
| V8 | `coin_stops.py:8` | Mindest-Stop je Münze (nur ADA 3 %) | für BTC/ETH/SOL ohne Wirkung | fest | Teil 9 | nein | – | P+L | SICHER |
| V9 | `exit_monitor.py:106-109` | Menge ≤ 0 oder Einstand ≤ 0 → nicht überwacht (übernommene Bestände ohne Einstand haben **keinen Stop**) | – | fest | 6.12 (Entscheidung) | – | heute 14:27: ETH „NICHT handelbar" | L | SICHER |
| V10 | `exit_monitor.py:164-167` | kein Preis → Position in diesem Durchlauf übersprungen | – | fest | nein | nein | 30 (2 Std, 17.09.) | P+L | SICHER |
| V11 | `exit_monitor.py:220-295` | Schattenregeln (Gewinn-Ratsche, Hold/Recovery) verkaufen nie | – | fest | 6.10 | 6.10 | 26 Notizen | P+L | SICHER |
| V12 | `exit_monitor.py:331-389` | Trend-Ausstieg: Verlust > 1 % und Mehrzeitrahmen bärisch. **Schattenbetrieb.** Der **einzige** Eintrag in `regel_modi`, der überhaupt gelesen wird (Z. 367–371). Mehrzeitrahmen-Daten gibt es nur für BTC | SHADOW | `rm: trend_exit` | 3.2, 3.6 | 46 Fälle (Grund für den Schatten) | 4 Schatten-Notizen | P+L | SICHER |
| V13 | `exit_monitor.py:392-394` | Stop-Loss: Verlust ≥ V7 | 2,0 % (MID_BEAR) | cfg + V7 | 3.2 | 3.5, 3.6 (v6) | 187 Zeilen (6 Std): 4 echte Verkäufe + Wiederholungen | P+L | SICHER |
| V14 | `exit_monitor.py:396-398` | Take-Profit, wenn > 0 | 0 → aus | cfg: `take_profit_pct` (Entscheidung 19.08.) | 3.2 | – | 0 | P+L | SICHER |
| V15 | `exit_monitor.py:419-443`, `fraktal_ziele.py:54-90`, `fraktal_tor.py:427-435` | Fibonacci-Ziel: Kurs ≥ Wellenhoch − 0,05 % → **ganze** Position verkaufen. Welle = die **größte** Welle der Kaufzone. Teilverkäufe (`ANTEILE`) nicht angeschlossen | Ziel 1,0 | fest | 6.13 (Wahl der größten Welle: nein) | nein | 0 (Ziele lagen +6,1 bis +9,7 % über dem Einstand) | P+L | SICHER |
| V16 | `exit_monitor.py:469-477`, `exit_rules.py:139-177` | Nachzieh-Stopp (Trailing), nur Modus SL: ab Höchststand ≥ 1,57 %. Abstand = Trail (V7) × Leiter 1,0/1,3/1,7/2,2 × 1,3 bei TRENDING_UP. Faktor hängt am Höchststand (Ratsche) | 1,57 % | fest. `rm: trailing_leiter` wird **nicht gelesen** | 3.3 (**veraltet:** nennt 1,2) | 3.5, Befund 66 (v6) | 1 (17.09. 11:45, **Papier-Rückfall**) | P+L | SICHER |
| V17 | `exit_monitor.py:478-481`, `exit_rules.py:83,129-131` | Breakeven-Sperre: war ≥ +1,0 %, jetzt ≤ +0,55 % → verkaufen | 1,0 / 0,55 % | fest. `rm: breakeven_sperre` wird **nicht gelesen** | 3.4 (**veraltet:** nennt 0,35) | 3.4 (alter Wert) | 1 (17.09. 01:01) | P+L | SICHER |
| V18 | `exit_monitor.py:503-504`, `risk/engine.py:193-198` | Monitor verkauft direkt (ohne Bus, ohne Handelssperre). Bus-Verkäufe winkt der Türsteher immer durch | – | fest | 2.1, 3.1 | – | – | P+L | SICHER |
| V19 | `app.py:1726-1735` | Verkaufsschutz: Position nicht mehr aktiv → abbrechen; Menge aus dem Register | – | fest | nein | nein | 0 | P+L | SICHER |
| V20 | `engine.py:677-700` | Echt: Verkaufsmenge auf den echten Bestand gekappt | – | fest | nein (Chronik 15.09.) | nein | 349 (3 Std, 15.09.) | L | SICHER |
| V21 | `engine.py:736-747` | Echt: Verkauf unter 5 $ wird **nicht gesendet**. Staubreste sind unverkäuflich, der Stop feuert alle 30 s erneut | 5 $ | fest | nein | nein | 1.080 (3 Std, 15.09.: 0,21 $ ETH) | L | SICHER |
| V22 | `engine.py:562-570` | Papier: nie mehr verkaufen als im Papierbestand | – | fest | nein | nein | 0 | P | SICHER |
| V23 | `app.py:2259-2305` | Sammel-Notbremse „alle schließen". **Tot:** kein Aufrufer, und `EVENT_KILL_SWITCH` wird nirgends gesendet | – | fest | Teil 9 Runde 1 Nr. 7 (als aktiv beschrieben) | nein | 0 | P+L | SICHER |
| V24 | `exit_monitor.py:765-771` | Verkauf gescheitert → Merker zurück, nach 30 s erneut. Keine Obergrenze, keine Meldung nach n Fehlversuchen | – | fest | nein | nein | 183 „Sell rejected" (4 Std, 15.09.) | P+L | SICHER |

**Nebenweg ohne echte Order:** Sparplan-Umbuchung (`app.py:3277-3290`, `btc_accumulator.py:179-218`). Der Sparplan ist aus (`btc_dca_enabled=false`). Die Umbuchung „Gewinne in BTC" läuft aber ab 3 $ Gewinn aus Bus-Verkäufen. Sie zieht nur von der **Papierkasse** ab und bucht BTC in die eigene Datei, das auch im Echtbetrieb. Nicht als Regel gezählt, siehe OFFEN 6.

### 3g. Die VERSTECKTEN Regeln
*Kriterium: weder in `config.json` noch in `BOT-HANDBUCH.md`. Diese Regeln sind die Kandidaten für einen Prüfstand.*

1. `app.py:2731`: Telegram-Pause stoppt den **ganzen** Takt, auch den RSI-Verkauf (T1)
2. `app.py:817-820`: ein zurückgestellter Smart-Entry-Kauf überspringt auch die Verkaufsprüfung im Signalpfad (T4)
3. `app.py:932-941`: die Weiche fällt bei Positionen in die Kaufprüfung durch (T5, Handbuch 2.2 sagt das Gegenteil)
4. `app.py:341-356`: Tor fehlt beim Start → Kauf ohne Tor (K6)
5. `fraktal_tor.py:366`: unter 2 Zeitrahmen → ablehnen (K8)
6. `fraktal_tor.py:191`: höchstens 6 rohe Wellen je Zeitrahmen (K12)
7. `fraktal_tor.py:87,92,249`: 200 Kerzen, Frische 5/20/60 min, 60 s Sperre (K13)
8. `fraktal_tor.py:172 / 111 / 106 / 97`: nur Aufwärtswellen, Puffer 0,5 %, Zonen-Score 3, Nähe 0,35 %. Stehen **nur** in `PROMPT_WEITERARBEIT_PC.md` bzw. `config_epochs.json`, nicht im Handbuch (K9, K14–K16)
9. `app.py:2090-2096`: Kaufwelle aus dem letzten Tor-Urteil zum **Buchungs**zeitpunkt (K17)
10. `app.py:1150` + `smart_entry.py:15`: Smart-Entry 3 % / 1 % / 2 % / 300 s (K21)
11. `risk/engine.py:273`: Kapital unbekannt zählt als Störung (K27)
12. `risk/engine.py:60`: Sektor fest 80 %, der Modus-Wert wird ignoriert (K29)
13. `portfolio/agent.py:32,83`: Korrelation höchstens 3, Mindestauftrag max(0,5 %; 5 $) (K35)
14. `data/nupl_monitor.py:54-56`: eingefrorener NUPL-Ersatzwert (K37)
15. `app.py:3000`: höchstens 2 neue Käufe je Runde auf Weg 2 (D4)
16. `app.py:3061`: Weg 2 nur ab 10 $ (D5)
17. `dca_advanced.py:27-57`: Abklingzeit 15–45 min (D7)
18. `app.py:3095`: Nachkauf ab −2 % (D8, nur Chronik)
19. `app.py:3162-3169`: „wartet" auf Weg 2 nicht vermerkt (D13)
20. `engine.py:226-227`: Papier-Rückfall bei **jedem** Verbindungsfehler (A1)
21. `engine.py:307-314`: Ausführungs-Schlafmodus zählt auch Verkäufe und Warteauftrag-Ablehnungen (A3)
22. `warteauftraege.py:140`: höchstens ein Warteauftrag je Münze (A5)
23. `engine.py:1075-1110`: echter Warteauftrag wird vor der Listenprüfung gestellt (A9)
24. `warteauftraege_live.py:133`: Status nur über `fetch_order` (A10)
25. `app.py:1328-1333`: 10 s Sperre → Füllung nicht gebucht (A11)
26. `app.py:1588-1604`: Größen-Überschreibung. Die Werte stehen in der Datei, der **Mechanismus** nirgends (G4)
27. `app.py:1683-1700`: 95 % Cash, Abbruch unter 10 $ (G6)
28. `app.py:468,1703`: Aufteilen ab 1.000 $ (G7)
29. `app.py:2987-2992`: Weg-2-Betrag mit Regime-Faktor, mind. 10 $ (G10)
30. `risk/engine.py:321-323`: Münz-Grenze lockert sich selbst (G11)
31. `app.py:914`: Gewinnziel im TP-Modus fest 3 % (V6)
32. `fraktal_tor.py:427-435`: Ausstiegsziel = größte Welle der Zone (V15)
33. `engine.py:736-747`: 5 $ Mindestbetrag auch beim Verkauf (V21)
34. `exit_monitor.py:765-771`: endlose Verkaufswiederholung ohne Obergrenze (V24)

**Dazu Scheinschalter:** Sie stehen in `config.json`, der Code liest sie aber nicht. Wer sie ändert, ändert nichts.
- `trading.dca_enabled` (bekannt seit 25.07.)
- `trading.max_trades` (NEU)
- `trading.dca_drop_pct` (bekannt seit 25.07.)
- `risk.kill_switch_enabled` (NEU, nur `go_live_check.py:307` liest ihn)
- sieben von acht Einträgen in `regel_modi`: `baerenmarkt`, `breakeven_sperre`, `trailing_leiter`, `smart_entry`, `wiedereinstieg_sperre`, `dca_stufen`, `meta_voting`. `core/regel_schalter.wirkt()` hat genau **einen** Aufrufer: `runtime/exit_monitor.py:369` (`trend_exit`).

---

## 4. Neue Befunde

Vorschläge für die nächsten freien v7-Nummern ab 113. Die aufrufende Sitzung vergibt die Nummern. Die Kapitalrisiken stehen oben als SOFORT-1 bis SOFORT-5, mit Ursachenkette, Lösungswegen und Empfehlung.

Die übrigen Punkte sind Auffälligkeiten aus dem Inventar, ohne Kapitalrisiko. Lösungswege stehen nur dort, wo eine Änderung naheliegt. **Alle wären Verhaltensänderungen und brauchen eine Epochengrenze.**

**B-a: Die Echtgeld-Einrichtung wirkt nicht wie beabsichtigt.** (SICHER)
- `live_einrichten.py:95-101` setzt `position_size_pct 50`, `max_open_positions 1`, `max_trades 1`, `dca_enabled False`.
- Tatsächlich wirken:
  - 30 % (G4, Handprobe 18,12 → 12,69 → 7,61 → **10,87 $**)
  - 3 Positionen (K26, `modes.balanced`). Am 15.09. waren ETH und BTC zugleich offen (05:34 bzw. 11:33 gekauft, ETH erst 14:23 verkauft).
  - `max_trades` und `dca_enabled` wirken gar nicht.
- Die Analyse im ENTWICKLERHANDBUCH vom 17.09. („bei 17 USD Order genauso wie bei 10.20") ging von 50 % aus. Die Journal-Käufe lagen bei 10,32–10,54 $.
- **Lösungswege:**
  - **minimal:** `modes.balanced.position_size_pct` und `max_positions` auf die gewollten Werte setzen (2 / 1 / 7).
  - **sauber:** eine Größenregel statt vier (G1, G3, G4, G10) (5 / 5 / 9).
  - **strukturell:** jeder Wert an genau einer Stelle, und der Start meldet laut, welche Schlüssel nicht gelesen werden (4 / 6 / 10).
- **Empfehlung:** minimal, erst nach Svens Entscheidung, welche Größe gelten soll.

**B-b: Regel-Schalter sind überwiegend Attrappen.** (SICHER) `regel_modi` wirkt nur für `trend_exit`. Das Handbuch 1.5 und `LAGE.md` erwecken den Eindruck, alle acht seien schaltbar. Wer z. B. `baerenmarkt` auf OFF stellt, ändert nichts. Ergänzung zu Handbuch 1.5 / Befund 11.

**B-c: Tote Schutzregeln.** (SICHER) Diese Regeln stehen im Handbuch als wirksam, greifen aber nicht:
- Drawdown (K25, `update_equity` ohne Aufrufer)
- Auto-Verteidigung (V3)
- NUPL (K37)
- Sammel-Notbremse (V23)
- Notbremse (K24): 100 $ bei 23,50 $ Konto, kein Tagesreset
- Aufhebung der Verlustsperre (K30): Score 50 unerreichbar

`schon_bekannt`: `update_equity`, `mtf_analyzer`, `check_auto_defense_sells`, `coin_cooldown_override_score` jeweils NEU.

**B-d: Der Fibonacci-Ausstieg liegt fast außer Reichweite.** (SICHER für die Zahlen, VERMUTUNG für den Grund)
- Weil die **größte** Welle der Zone das Ziel stellt, lagen alle drei Ziele +6,1 bis +9,7 % entfernt, bei −2,0 % Stop.
- Im Zeitraum hat es 0-mal ausgelöst. Ausgestiegen wurde über Stop-Loss (4), Breakeven (1) und Trailing (1, auf Papier).
- Dazu schalten die Tagesverlust- und die Telegram-Pause den RSI-Verkauf mit ab (T1, T2). In v6 war das der einzige netto positive Ausstieg (Handbuch 3.5).

**B-e: Die Handbuch-Angaben sind auseinandergelaufen.** (SICHER)

| Stelle | Handbuch sagt | Code sagt |
|---|---|---|
| 2.3 | Schwelle 3 | 7 |
| 3.3 | Trailing ab 1,2 % | 1,57 % (`exit_rules.py:139`) |
| 3.4 | Breakeven-Puffer 0,35 % | 0,55 % (`exit_rules.py:131`) |
| 3.1 | Auto-Verteidigung aktiv | tot |
| Teil 9 | Sammel-Notbremse aktiv | kein Aufrufer |
| Teil 9 | Exposure „20/40 %" | 35/80 % |
| 4.9 | Schalter `warteauftraege.aktiv` „false" | `true` |

Echte Warteaufträge (`warteauftraege_live.py`) fehlen im Handbuch ganz.

---

## 5. Ergänzungen zu bekannten Befunden

- **Chronik 25.07.2026** (BUG REPORT „DCA-Config wirkungslos"): gilt weiterhin für `dca_enabled` und `dca_drop_pct`. `dca_max_levels` wird inzwischen gelesen (`app.py:3035`). Neu: Weg 2 umgeht auch das Fraktal-Tor (SOFORT-5).
- **Handbuch 1.2** (Rückfall auf Papier nur bei fehlendem Schlüssel): Der Rückfall passiert auch bei jedem Verbindungsfehler (SOFORT-3).
- **Befund 68 / Chronik 14.09.** (`fetch_order` scheitert bei Bybit): Für den Sofortauftrag wurde das mit drei Nachfragewegen gelöst, für den echten Warteauftrag nicht (SOFORT-1).
- **Chronik 17.09. 08:44** (`'str' object`-Fehler im Warteauftrag-Takt): Der Fehler verdeckte SOFORT-1. Nach der Behebung wurde kein echter Warteauftrag mehr gestellt, der Takt ist im Echtbetrieb weiter ungeprüft.
- **Handbuch 2.6** (Euphorie-Bremse „immer aktiv"): eingefrorener Ersatzwert, greift praktisch nie (K37).
- **Handbuch 2.2** (Weiche „ja → Verkaufsprüfung"): fällt ohne Verkaufsgrund in die Kaufprüfung durch (T5). Beleg: 2.735 „Bereits in Position".
- **Handbuch 6.14** (Bestandsabgleich ist nur eine Warnung): heute 14:27 UTC wieder zwei Abweichungen (ETH ohne Register, BTC im Register ohne Börsenbestand). Der Bot handelt laut eigener Meldung weiter.
- **Befund 97** (Speichervorgang setzt Einstellungen zurück): `risk.max_exposure_per_coin_pct` stand um 16:28 plötzlich auf 55 statt 35. Ob das Absicht der anderen Sitzung war: OFFEN 5.

---

## 6. OFFEN: was nicht entscheidbar war und welche Daten es entscheiden würden

1. **Wurden die fünf Zusatzaufträge vom 17.09. 01:26–01:29 UTC storniert?** → Bybit-Auftragshistorie, von Sven selbst nachzusehen (Börse abfragen war nicht erlaubt).
2. **Führt der seit 25.09. 16:23 laufende v7-Prozess noch echt aus?** Er wurde mit `live` gestartet, die Datei steht seit 16:28 auf `paper`, und die Ausführung liest den Modus nur beim Start. → andere Sitzung, `prozess_frische.py`, Startzeile im Log.
3. **Wirkung fast aller Regeln im Fraktal-Betrieb:** ungemessen. 15.–17.09. gab es nur 4 Sofortkäufe und 1 Warteauftrag-Füllung, dazu 36 verschiedene Stunden mit offenem Tor. Befund 103 (Schwelle 7) und die Ausstiegszahlen aus Teil 3 stammen aus v6-Papier **ohne** Tor. → Messfenster mit Epoche und mindestens 30 unabhängigen Käufen.
4. **Wie oft greift die Telegram-Pause?** Sie schreibt kein Log-Kennzeichen. → Protokollzeile beim Setzen und Aufheben.
5. **`risk.max_exposure_per_coin_pct` 35 → 55 um 16:28:** Absicht oder Speicher-Nebenwirkung (Befund 97)? → andere Sitzung fragen.
6. **Sparplan-Umbuchung im Echtbetrieb** bucht BTC nur im Zähler (`btc_accumulator.py:193-207`) und würde über `get_total_capital()` Kapital ausweisen, das es nicht gibt. VERMUTUNG, nicht bis zum Ende verfolgt. → `btc_accumulator.json` im v7-Ordner lesen (existiert derzeit nicht) und `record_purchase` prüfen.
7. **Kaufwelle bei Warteauftrag-Füllungen (K17):** Wie oft fehlt sie oder ist falsch? Es gibt noch keine gebuchte Füllung. → nach dem Beheben von SOFORT-1 die Logzeile „Kaufwelle … gemerkt" gegen das Tor-Urteil beim Anlegen halten.
8. **Log-Lücke 16.09. 10:52 bis 21:50 UTC** mit Null-Bytes (um Zeile 103.622): Absturz oder Stromausfall? Elf Stunden ohne Einträge, auch ohne Stop-Überwachung. → Windows-Ereignisanzeige für diesen Zeitraum.
9. **Laufen Aufgaben im Scheduler parallel?** Nicht geprüft (`core/scheduler.py` nicht gelesen). Davon hängt ab, wie oft A11/SOFORT-4 tatsächlich eintreten kann.
