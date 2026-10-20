# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH 42 fuer v6 - die Kaufgebuehr wird nur noch EINMAL abgezogen.

BEFUND 42 (Handbuch 4.5/4.50, GEFUNDENE-PROBLEME 42):
  execution/engine.py:401   result.filled_cost = amount      <- Gebuehr steckt in amount
  app.py:1896               cost_basis = filled_cost + fee   <- und kommt nochmal dazu
  runtime/exit_monitor.py:434  pnl = Erloes - cost_basis - Verkaufsgebuehr
In E7 (136 Runden) traf das 115 Runden (alle Verkaeufe ueber exit_monitor),
zusammen 45,91 $: Cockpit -88,89 $ statt Kasse -43,13 $ (pruefstand/inventur.md 3/4).

FIX genau wie in v7 seit 11.09.2026 (v7 execution/engine.py:536-551):
  result.filled_cost = amount - fee
Ort laut GEFUNDENE-PROBLEME 42 bewusst engine.py, NICHT app.py: im Livepfad
liefert ccxt "cost" = filled * price OHNE Gebuehr (ccxt base/exchange.py
safe_order), dort ist filled_cost + fee richtig. Nach dem Fix bedeuten
Papier und Live dasselbe.

FOLGE fuer das Journal: der KAUF-"amount" in trades_v5.json ist ab E9 ohne
Gebuehr (= qty * Kurs), genau wie in v7 und wie beim VERKAUF. Kein Auswerte-
Skript rechnet den Gewinn aus dem Kauf-amount (geprueft 14.10.: datenexport,
gesamtauswertung, cockpit_server, stoploss_analyse, doc_agent).

BEKANNT: Positionen, die VOR dem Patch gekauft wurden, tragen ihre doppelte
cost_basis im bot_state.json weiter und werden beim Verkauf noch einmal
falsch gebucht (14.10.: BTC, ETH, SOL).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
MARKE = "BEFUND 42, behoben 14.10.2026"

ALT = '            result.filled_cost = amount; result.fee = round(fee, 4); result.status = "filled"\n'
NEU = (
    "            # [" + MARKE + " - Epoche E9, aus dem Pruefstand]\n"
    "            # filled_cost OHNE Gebuehr, wortgleich mit v7 (engine.py:551, 11.09.2026).\n"
    "            # Vorher stand hier \"result.filled_cost = amount\". In amount steckt\n"
    "            # die Kaufgebuehr schon (oben: fee = amount * fee_rate,\n"
    "            # qty = (amount - fee) / price). app.py:1896 und :3085 rechnen\n"
    "            # danach cost_basis = filled_cost + fee - also ein ZWEITES Mal.\n"
    "            # E7: 115 von 136 Runden betroffen, 45,91 $ zu schlecht gebucht.\n"
    "            # amount - fee ist genau qty * price - dasselbe, was ccxt im\n"
    "            # Livepfad als \"cost\" liefert (:546). filled_cost + fee ist jetzt\n"
    "            # in beiden Wegen der echte Mittelabfluss. Livepfad unberuehrt.\n"
    '            result.filled_cost = amount - fee; result.fee = round(fee, 4); result.status = "filled"\n'
)


def rechenprobe() -> int:
    """Zahlenbeispiel: Kauf 100 $, 0,25 %, Verkauf zum gleichen Kurs."""
    amount, rate, price = 100.0, 0.0025, 50_000.0
    fee = amount * rate
    qty = (amount - fee) / price
    alt_cb = amount + fee                 # vorher: filled_cost(=amount) + fee
    neu_cb = (amount - fee) + fee         # nachher
    erloes = qty * price
    vfee = erloes * rate
    pnl_alt, pnl_neu = erloes - alt_cb - vfee, erloes - neu_cb - vfee
    soll = -(fee + vfee)                  # Kasse: nur die zwei echten Gebuehren
    ok = abs(pnl_neu - soll) < 1e-9 and abs(pnl_alt - (soll - fee)) < 1e-9
    print(f"  {'OK  ' if ok else 'FEHL'} Rechenprobe: alt {pnl_alt:+.4f} $, neu {pnl_neu:+.4f} $, "
          f"Kasse {soll:+.4f} $ (Unterschied alt = eine Kaufgebuehr {fee:.4f} $)")
    return 0 if ok else 1


if __name__ == "__main__":
    main(V6, [Ersetzung("execution/engine.py", ALT, NEU)], MARKE,
         "PATCH 42 v6 - Kaufgebuehr einfach buchen", zusatztest=rechenprobe)
