# Daten-Coverage-Report — Phase 3 (Pilot)

Stand 30.07.2026. Ablage: `daten/` mit `QUELLENPROTOKOLL.txt` (jede Datei:
URL, Zeitpunkt, Zeilen, Zeitbereich) und `PRUEFSUMMEN.txt` (SHA256).
Reproduktion: `code/daten_pilot_download.py` + `code/daten_funding_fix.py`.

## Abdeckung (alle Zeiten UTC; Kline-`zeit` = Balken-Open, Epoch-ms)

### Spot-Klines 1d (Quelle data-api.binance.vision, USDT-Paare als Preis-Proxy)

| Symbol | von | bis | Tage | Lücken |
|---|---|---|---|---|
| BTCUSDT | 2017-08-17 | 2026-07-30 | 3270 | 0 |
| ETHUSDT | 2017-08-17 | 2026-07-30 | 3270 | 0 |
| ADAUSDT | 2018-04-17 | 2026-07-30 | 3027 | 0 |
| XRPUSDT | 2018-05-04 | 2026-07-30 | 3010 | 0 |
| LINKUSDT | 2019-01-16 | 2026-07-30 | 2753 | 0 |
| ATOMUSDT | 2019-04-29 | 2026-07-30 | 2650 | 0 |
| DOGEUSDT | 2019-07-05 | 2026-07-30 | 2583 | 0 |
| SOLUSDT | 2020-08-11 | 2026-07-30 | 2180 | 0 |
| DOTUSDT | 2020-08-18 | 2026-07-30 | 2173 | 0 |
| UNIUSDT | 2020-09-17 | 2026-07-30 | 2143 | 0 |
| AVAXUSDT | 2020-09-22 | 2026-07-30 | 2138 | 0 |
| NEARUSDT | 2020-10-14 | 2026-07-30 | 2116 | 0 |

4h-Klines: BTCUSDT/ETHUSDT je 19 602 Kerzen (Pilot; Rest nach
Universums-Entscheid).

### Funding 8h (fapi.binance.com, v2 nach Korrektur)

BTC ab 2019-09-10 (7547), ETH ab 2019-11-27 (7313), übrige ab
2020-01..2020-10 (6346–7193). Kontinuität: nach Rundung auf volle Stunden
**100 % exakt 8h-Raster, 0 Lücken**; roher `fundingTime` trägt ±ms-Jitter
(dokumentiert, Diagnose 30.07.). **Korrekturvermerk:** Erstversion des
Downloads war durch `startTime=0`-Paginierungsfehler auf ~500 jüngste
Einträge verkürzt; vollständig ersetzt, beide Versionen im
QUELLENPROTOKOLL, alte Prüfsummen als ersetzt markiert.

### Makro (FRED, fredgraph.csv, ohne Key)

DTWEXBGS + DTWEXAFEGS, je 5366 Zeilen (Tagesreihe seit 2006, nur
Werktage; Wochenend-NaNs sind konstruktiv). **Publikationslag ⇒ im
Register nur mit ≥ 1 Woche Verzögerung nutzbar (H4).**

### Universums-Referenz

- Binance-Archiv: 480 USDT- / 280 USDC-Paare im Status TRADING (Abruf
  exchangeInfo 30.07.) — Basis für 30–60er-Auswahl.
- Bybit EU: 111 USDC-Spot-Paare Trading (api.bybit.eu, 30.07.) — alle 12
  Projekt-Coins enthalten.

## Risiken

1. **Survivorship:** exchangeInfo listet nur heute handelnde Paare;
   delistete Coins fehlen in dieser Aufzählung. Für H1-Primär (BTC/ETH)
   unkritisch, für das 12er-Portfolio real (heutige Überlebende), für H3
   zwingend zu behandeln (Registerauflage; Vision-Bucket enthält auch
   delistete Symbole — Erweiterung möglich [WAHRSCHEINLICH]).
2. **Proxy-Basis USDT→USDC:** Entwicklung auf USDT-Historie, Handel in
   USDC — Basisdifferenz normal wenige bp [WAHRSCHEINLICH], in
   Stress-Phasen (USDC-Depeg 03/2023!) größer; als Robustheitsnotiz im
   Register, Depeg-Fenster wird bei H-Auswertungen ausgewiesen.
3. **Früh-Historie 2017–2019:** dünne Bücher, andere Marktstruktur;
   Segment S-A ist deshalb Pflicht-Ausweis, nicht stiller Mittelwert.
4. Fear&Greed (vorhanden, alternative.me): Methodikwechsel möglich
   [VERMUTUNG] — wird ohnehin nicht als Signal verwendet (F&G ist
   gemessen tot), nur als Kontextvariable.

## Nächster konkreter Schritt

Nach Börsen-Freigabe: 1d-Klines für das 30–60er-Zieluniversum
(Schnitt Bybit-EU-USDC ∩ Binance-Archiv), 4h für alle 12, Delisting-
Kandidatenliste aus dem Vision-Bucket. Aufwand < 1 h, gleiche Skripte.
