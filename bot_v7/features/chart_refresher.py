# -*- coding: utf-8 -*-
"""
Chart-Auto-Refresher. [CHART-REFRESH 21.07.2026]
================================================================
Haelt den Kerzen-Cache (data_store/charts/) automatisch frisch,
damit niemand mehr die Kerzendaten von Hand aktualisieren muss.

Ein Hintergrund-Thread laedt beim Start einmal alle Coins nach
und danach in festem Intervall (Vorgabe: alle 60 min). Nutzt die
vorhandene ChartData.load_all() - also exakt dieselbe Logik wie
der manuelle Charts-Tab, nur automatisch.

REINE DATENpflege: kein Trading-Eingriff, kein Signal, nichts am
Exit-Monitor. Laeuft als daemon-Thread, faengt alle Fehler ab -
der Bot kann dadurch nicht crashen. Wenn Binance offline ist,
bleibt der alte Cache stehen und der naechste Lauf versucht es
erneut.
"""
import os, threading, time

try:
    from core.logger import log
except Exception:
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
    log = _L()

INTERVALL_MIN = 60
TAGE = 90

# [20.08.2026] Von zwölf auf achtzehn - dieselbe Liste wie im
# Schatten-Universum (schatten_universum.MUENZEN).
#
# Sven fiel auf, dass im Log "12 Coins" steht, obwohl seit dem 17.08.
# achtzehn beobachtet werden. Es war nicht nur ein Text: die sechs
# Nachzuegler (SUI, OP, APT, ARB, INJ, RENDER) bekamen wirklich keine
# Kerzendaten. Wer sie spaeter mit der Chartanalyse bewerten will, haette
# fuer sie nichts gehabt - und Kerzen von gestern kann man zwar
# nachladen, aber niemand denkt daran, wenn die Frage erst in vier Wochen
# kommt.
#
# Reines Herunterladen und Ablegen. Kein Handelspfad, keine Entscheidung -
# der Bot handelt drei Muenzen und das bleibt so.
COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "XRP/USDC", "ADA/USDC",
         "AVAX/USDC", "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC",
         "UNI/USDC", "ATOM/USDC",
         "SUI/USDC", "OP/USDC", "APT/USDC", "ARB/USDC",
         "INJ/USDC", "RENDER/USDC"]


class ChartRefresher:
    def __init__(self, coins=None, intervall_min=INTERVALL_MIN, tage=TAGE):
        self.coins = coins or COINS
        self.intervall = max(10, intervall_min) * 60
        self.tage = tage
        self._thread = None
        self._stop = threading.Event()
        self.letzter_lauf = None
        self.letzter_status = "noch nicht gelaufen"

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._schleife, daemon=True,
                                        name="ChartRefresher")
        self._thread.start()
        log.info("CHART-REFRESH", f"gestartet - {len(self.coins)} Coins, "
                                  f"alle {self.intervall // 60} min")

    def stop(self):
        self._stop.set()

    def _schleife(self):
        # kurz warten, damit der Bot-Start nicht konkurriert
        if self._stop.wait(20):
            return
        while not self._stop.is_set():
            self._einmal_laden()
            if self._stop.wait(self.intervall):
                break

    def _einmal_laden(self):
        try:
            from features.chart_data import ChartData
        except Exception:
            try:
                from chart_data import ChartData
            except Exception as e:
                self.letzter_status = f"ChartData nicht gefunden: {str(e)[:50]}"
                log.warn("CHART-REFRESH", self.letzter_status)
                return
        try:
            cd = ChartData()
            t0 = time.time()
            ergebnis = cd.load_all(self.coins, interval="1h", days=self.tage)
            ok = sum(1 for v in ergebnis.values() if v)
            dauer = time.time() - t0
            self.letzter_lauf = time.time()
            self.letzter_status = f"{ok}/{len(self.coins)} Coins aktualisiert ({dauer:.0f}s)"
            log.info("CHART-REFRESH", self.letzter_status)
        except Exception as e:
            self.letzter_status = f"Fehler: {str(e)[:60]}"
            log.warn("CHART-REFRESH", self.letzter_status)

    def status(self):
        alter = (f"{(time.time() - self.letzter_lauf) / 60:.0f} min her"
                 if self.letzter_lauf else "nie")
        return f"{self.letzter_status} (letzter Lauf: {alter})"
