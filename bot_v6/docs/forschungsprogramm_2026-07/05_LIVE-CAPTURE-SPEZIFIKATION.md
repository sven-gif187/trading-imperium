# Live-Capture-Spezifikation (NUR Spezifikation — Start erst nach Börsen-Freigabe)

Zweck: nicht-backfillbare Marktzustände der ZIELBÖRSE archivieren
(Orderbuch, Spread, Trades) plus globale Derivate-Zustände (Funding/OI).
Begründung des Nicht-Starts: Orderbuchdaten sind börsenspezifisch —
Erfassung vor der Börsenentscheidung wäre potenziell wertlos.

## Architektur

- **Eigenständiger Prozess** (`capture_daemon.py`, eigener Ordner, eigene
  Konsole/Task), KEIN Import aus Bot-Modulen, kein Zugriff auf
  `data_store/`, keine Schreibrechte dort. Kommunikationsrichtung: keine.
- **Nur öffentliche Endpunkte, keine API-Keys**, keine Order-Funktionen im
  Code (kein ccxt-Trade-Objekt, nur HTTP-GET/WS-Subscribe).
- Zielbörse Primärvorschlag: api.bybit.eu (v5 public). Global-Derivate:
  fapi.binance.com (Funding/OI als Signalquelle, kein Handelsplatz).

## Erfasste Reihen (je Ziel-Universum, initial die 12 Coins)

| Reihe | Endpunkt | Frequenz | Felder |
|---|---|---|---|
| Orderbuch Top-50 | v5/market/orderbook | 60 s Poll | ts, 50×(Preis,Menge) je Seite |
| Best-Bid/Ask+Spread | v5/market/tickers | 60 s | bid, ask, mid, spread_bp |
| Letzte Trades | v5/market/recent-trade | 60 s | Aggregat: n, vol, vwap seit letztem Poll |
| Funding live | fapi fundingRate/premiumIndex | 15 min | rate, markPrice |
| Open Interest | fapi openInterest | 15 min | oi |
| Heartbeat | — | 60 s | Latenz, HTTP-Status, Fehlerzähler |

## Speicherung

- Tagesdateien `capture/YYYY-MM-DD/<reihe>_<symbol>.csv.gz`, Rotation um
  00:00 UTC; append-only; SHA256 je abgeschlossener Tagesdatei in
  `capture/PRUEFSUMMEN.txt`.
- Datenbudget: Obergrenze ~50 MB/Tag komprimiert (Orderbuch Top-50 × 12
  Coins × 1440 Polls dominiert); Konfig-Schalter Top-N und Poll-Intervall.
- Retention: unbegrenzt (das ist der Zweck); Warnung bei < 10 GB frei.

## Robustheit

- Restart-fähig: kein In-Memory-Zustand nötig, Wiederanlauf schreibt
  weiter; Lücken sind erkennbar (Heartbeat-Reihe), werden NIE aufgefüllt.
- Fehlerbehandlung: Exponentielles Backoff, nach 10 Fehlfolgen Pause
  15 min; Rate-Limit-Konservativ (max. 1 Request/s gesamt).
- Logging: eigene Logdatei im Capture-Ordner — NICHT data_store/system.log.
- Watchdog: geplanter Task prüft stündlich Prozess + letzte Schreibzeit.

## Explizit ausgeschlossen

Kein Trading, keine Keys, keine Secrets, keine Bot-Änderung, kein
Zugriff auf bestehende Messdaten, kein Autostart vor Freigabe.

## Definition of Done (nach Start)

7 Tage lückenlos (Heartbeat-Abdeckung ≥ 99 %), Prüfsummen vorhanden,
erste Spread-Statistik je Coin als Report — diese Statistik ersetzt die
[UNGEKLÄRT]-Spread-Annahmen der Börsenmatrix durch Messwerte.
