# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
Nachkauf-Raten-Attribution: warum misst der Harness 2,2 % statt 18,3 %?

Liest NUR aus dem Projekt (kein Schreiben). Instrumentierte Kopie der
Einstiegsschleife aus backtest/ausstieg_backtest.py::Lauf.laufe als
Subklasse HIER im Scratchpad - der Harness selbst bleibt unangetastet.

Varianten-Leiter (jeweils EINE Aenderung mehr Richtung Live-Verhalten):
  V0  Harness wie strategie_studie Schritt 2 "wie Bot"
      (NEUE_LEITER, breakeven, max_stufen=3, 1 Kauf/Stunde global inkl. break)
  V0a wie V0, aber ALTE_LEITER + breakeven=False (Exits wie Live vor 29.07.)
  V1  V0 + Nachkaeufe vom Stunden-Gate/break befreit
      (Live: Nachkaeufe zaehlen nicht gegen max_new_per_round; nur
       AdvancedDCA-Cooldown 15-45min je Coin -> hier 1-3 Kerzen je nach F&G)
  V2  V1 + bis zu 2 NEUE Positionen je 15m-Kerze statt 1 Kauf/Stunde
      (Live: max_new_per_round=2, Runde alle 12s, Cooldown je Coin)
  V3  V2 + max_stufen=unbegrenzt (Live vor 29.07.: kein Deckel)
  V4  V3 + ALTE_LEITER + breakeven=False (kompletter Vor-29.07.-Zustand)

Kennzahl je Lauf: Anteil geschlossener Positionen mit stufen >= 2
(= mind. 1 Nachkauf), identisch zur 18,3%-Messung aus trades_v5.json.
Zusaetzlich fuer V0: Zaehlung der Blockadegruende je Nachkauf-Gelegenheit
und Anteil geschlossener Positionen, deren MAE nie -2 % erreichte.
"""
import os
import sys

def _finde_projekt():
    """Projektwurzel relativ zum Skriptort suchen (Marker: app.py).

    Ersetzt den frueher fest verdrahteten absoluten Pfad. Damit laeuft das
    Skript unabhaengig davon, wohin der Projektordner verschoben wird.
    """
    p = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(p, "app.py")):
            return p
        p = os.path.dirname(p)
    raise RuntimeError("Projektwurzel nicht gefunden - app.py in keiner "
                       "uebergeordneten Ebene")


PROJEKT = _finde_projekt()
if PROJEKT not in sys.path:
    sys.path.insert(0, PROJEKT)

from backtest.ausstieg_backtest import (Lauf, ALTE_LEITER, NEUE_LEITER,
                                        lade_kerzen, lade_fear_greed)
from datetime import datetime, timezone

COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "AVAX/USDC",
         "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC", "UNI/USDC",
         "ATOM/USDC"]


def lade_daten():
    d = {}
    for c in COINS:
        k = lade_kerzen(c)
        if k:
            d[c] = k
    return d, lade_fear_greed()


def cooldown_kerzen(fg):
    """AdvancedDCA base_interval=60min: fg<15 -> 15min, fg<25 -> 30min,
    fg<40 -> 45min. In 15m-Kerzen: 1 / 2 / 3."""
    if fg < 15:
        return 1
    if fg < 25:
        return 2
    return 3


class LaufInstr(Lauf):
    """Instrumentierte Kopie der Hauptschleife. Schalter:
    nk_frei      - Nachkaeufe unterliegen NICHT dem Stunden-Gate/break
    neue_je_kerze- >0: so viele NEUE Positionen je Kerze statt 1 Kauf/h global
    """

    def __init__(self, *a, nk_frei=False, neue_je_kerze=0, nk_intrabar=False, **kw):
        super().__init__(*a, **kw)
        self.nk_frei = nk_frei
        self.neue_je_kerze = neue_je_kerze
        self.nk_intrabar = nk_intrabar
        self.cool_bis = {}     # symbol -> zeit_ms bis Cooldown ablaeuft
        self.blocked = {"stunden_gate": 0, "preis_nicht_2pct": 0,
                        "stufen_deckel": 0, "cooldown": 0, "gekauft": 0,
                        "kein_cash": 0}

    def laufe(self, kerzen_je_coin, fg_tabelle, regime="RANGING"):
        zeitpunkte = sorted({k[0] for ks in kerzen_je_coin.values() for k in ks})
        index = {s: {k[0]: k for k in ks} for s, ks in kerzen_je_coin.items()}
        letzter_kauf_h = -1

        if self.trend_sma_bars > 0 or self.markt_sma_bars > 0:
            raise RuntimeError("Filter hier nicht abgebildet")

        for t in zeitpunkte:
            tag = datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
            fg = fg_tabelle.get(tag, 50)
            preis_map = {}

            # --- 1. Ausstiege (unveraendert aus dem Original) ---
            for s in list(self.positionen):
                k = index.get(s, {}).get(t)
                if not k:
                    continue
                _, o, hi, lo, cl = k
                preis_map[s] = cl
                p = self.positionen[s]
                # V5: Intra-Kerzen-Nachkauf. Live prueft der DCA-Pfad alle
                # 12s gegen den Echtzeitpreis - beim Fall durch -2,0 % feuert
                # der Nachkauf, BEVOR der Preis -2,5 % (Stop) erreicht. Der
                # Harness kann nur zum Schlusskurs kaufen und prueft Exits
                # vorher am Tief -> der Stop gewinnt das Rennen immer.
                # Hier: Kauf zum Schwellenpreis einstand*0.98, sobald das
                # Tief die Schwelle reisst. Exit-Pruefung danach wie gehabt
                # (gegen den NEUEN, gemittelten Einstand - pessimistisch
                # bleibt das Kerzentief massgeblich).
                if (self.nk_intrabar and fg < self.fg_grenze
                        and p.stufen < self.max_stufen
                        and t >= self.cool_bis.get(s, 0)
                        and lo < p.einstand * (1 - self.nachkauf_ab_pct / 100)):
                    schwelle = p.einstand * (1 - self.nachkauf_ab_pct / 100)
                    if self._kaufe(s, max(lo, schwelle), t):
                        self.blocked["gekauft"] += 1
                        self.cool_bis[s] = t + cooldown_kerzen(fg) * 900_000
                    else:
                        self.blocked["kein_cash"] += 1
                if lo < p.tief:
                    p.tief = lo
                grund = self._pruefe_ausstieg(p, lo, regime)
                if grund:
                    self._verkaufe(p, lo, t, grund)
                    continue
                if hi > p.hoch:
                    p.hoch = hi
                pnl_hoch = (hi / p.einstand - 1) * 100
                if pnl_hoch > p.hoechst_pnl:
                    p.hoechst_pnl = pnl_hoch
                grund = self._pruefe_ausstieg(p, cl, regime)
                if grund:
                    self._verkaufe(p, cl, t, grund)

            # --- 2. Einstiege ---
            stunde = t // 3_600_000
            if fg >= self.fg_grenze:
                continue

            neue_diese_kerze = 0
            stunden_slot_frei = (stunde != letzter_kauf_h)

            for s, ks in index.items():
                k = ks.get(t)
                if not k:
                    continue
                preis = k[4]
                preis_map.setdefault(s, preis)
                p = self.positionen.get(s)

                if p is not None:
                    # ---- Nachkauf-Gelegenheit: Position existiert, fg<30 ----
                    if p.stufen >= self.max_stufen:
                        self.blocked["stufen_deckel"] += 1
                        continue
                    if preis >= p.einstand * (1 - self.nachkauf_ab_pct / 100):
                        self.blocked["preis_nicht_2pct"] += 1
                        continue
                    if self.nk_frei:
                        if t < self.cool_bis.get(s, 0):
                            self.blocked["cooldown"] += 1
                            continue
                        if self._kaufe(s, preis, t):
                            self.blocked["gekauft"] += 1
                            self.cool_bis[s] = t + cooldown_kerzen(fg) * 900_000
                        else:
                            self.blocked["kein_cash"] += 1
                        continue
                    else:
                        if not stunden_slot_frei:
                            self.blocked["stunden_gate"] += 1
                            continue
                        if self._kaufe(s, preis, t):
                            self.blocked["gekauft"] += 1
                            letzter_kauf_h = stunde
                            stunden_slot_frei = False
                        else:
                            self.blocked["kein_cash"] += 1
                        continue

                # ---- Neue Position ----
                if len(self.positionen) >= self.max_pos:
                    continue
                bis, aus = self.gesperrt.get(s, (0, 0))
                if t < bis:
                    continue
                if aus > 0 and preis > aus * (1 - self.sperre_unter_pct / 100) \
                        and t < bis + 6 * 3_600_000:
                    continue
                if self.neue_je_kerze > 0:
                    if neue_diese_kerze >= self.neue_je_kerze:
                        continue
                    if t < self.cool_bis.get(s, 0):
                        continue
                    if self._kaufe(s, preis, t):
                        neue_diese_kerze += 1
                        self.cool_bis[s] = t + cooldown_kerzen(fg) * 900_000
                else:
                    if not stunden_slot_frei:
                        continue
                    if self._kaufe(s, preis, t):
                        letzter_kauf_h = stunde
                        stunden_slot_frei = False

        return self.auswertung()


def rate(lauf):
    n = len(lauf.trades)
    nk = sum(1 for t in lauf.trades if t["stufen"] >= 2)
    return n, nk, (nk / n * 100 if n else 0.0)


def zeile(name, lauf):
    n, nk, r = rate(lauf)
    tiefe = {}
    for t in lauf.trades:
        tiefe[t["stufen"]] = tiefe.get(t["stufen"], 0) + 1
    print(f"{name:<56s} Trades={n:5d}  mit NK={nk:4d}  Rate={r:5.1f}%  "
          f"Stufen={sorted(tiefe.items())}")
    return r


def main():
    daten, fg = lade_daten()
    if not daten:
        print("KEINE DATEN in data_store/backtest")
        return 1
    z = sorted({k[0] for ks in daten.values() for k in ks})
    v = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    print(f"Daten: {len(daten)} Coins, {v(z[0])} .. {v(z[-1])}, Kerzen(BTC)={len(daten.get('BTC/USDC', []))}")
    print()

    # Referenz: Original-Lauf unveraendert (Plausibilisierung der Subklasse)
    ref = Lauf(NEUE_LEITER, "ref", breakeven=True, max_stufen=3)
    ref.laufe(daten, fg)
    zeile("REF Original-Lauf (unveraendert, wie Studie S.2)", ref)

    v0 = LaufInstr(NEUE_LEITER, "v0", breakeven=True, max_stufen=3)
    v0.laufe(daten, fg)
    zeile("V0  instrumentiert, identische Regeln", v0)
    print(f"     V0-Blockaden je NK-Gelegenheit: {v0.blocked}")
    mae_ok = sum(1 for t in v0.trades if t["mae_pct"] <= -2.0)
    print(f"     V0: geschlossene Positionen, deren Tief je -2% erreichte: "
          f"{mae_ok}/{len(v0.trades)} = {mae_ok/len(v0.trades)*100:.1f}%")

    v0a = LaufInstr(ALTE_LEITER, "v0a", breakeven=False, max_stufen=3)
    v0a.laufe(daten, fg)
    zeile("V0a wie V0, aber ALTE Leiter ohne Breakeven", v0a)
    mae_ok = sum(1 for t in v0a.trades if t["mae_pct"] <= -2.0)
    print(f"     V0a: Positionen mit Tief <= -2%: {mae_ok}/{len(v0a.trades)}"
          f" = {mae_ok/len(v0a.trades)*100:.1f}%")

    v1 = LaufInstr(NEUE_LEITER, "v1", breakeven=True, max_stufen=3, nk_frei=True)
    v1.laufe(daten, fg)
    zeile("V1  V0 + Nachkaeufe ohne Stunden-Gate (Cooldown je Coin)", v1)
    print(f"     V1-Blockaden: {v1.blocked}")

    v2 = LaufInstr(NEUE_LEITER, "v2", breakeven=True, max_stufen=3,
                   nk_frei=True, neue_je_kerze=2)
    v2.laufe(daten, fg)
    zeile("V2  V1 + bis 2 neue Pos. je 15m-Kerze", v2)

    v3 = LaufInstr(NEUE_LEITER, "v3", breakeven=True, max_stufen=999,
                   nk_frei=True, neue_je_kerze=2)
    v3.laufe(daten, fg)
    zeile("V3  V2 + Nachkauf-Deckel entfernt (vor 29.07.)", v3)

    v4 = LaufInstr(ALTE_LEITER, "v4", breakeven=False, max_stufen=999,
                   nk_frei=True, neue_je_kerze=2)
    v4.laufe(daten, fg)
    zeile("V4  V3 + ALTE Leiter ohne Breakeven (Vor-29.07.-Zustand)", v4)
    print(f"     V4-Blockaden: {v4.blocked}")

    v5 = LaufInstr(ALTE_LEITER, "v5", breakeven=False, max_stufen=999,
                   nk_frei=True, neue_je_kerze=2, nk_intrabar=True)
    v5.laufe(daten, fg)
    zeile("V5  V4 + Intra-Kerzen-Nachkauf (Rennen NK vs. Stop)", v5)
    print(f"     V5-Blockaden: {v5.blocked}")

    v5n = LaufInstr(NEUE_LEITER, "v5n", breakeven=True, max_stufen=3,
                    nk_frei=True, neue_je_kerze=2, nk_intrabar=True)
    v5n.laufe(daten, fg)
    zeile("V5n HEUTIGE Regeln (Deckel 3, Ratsche) + Live-Frequenz", v5n)
    print(f"     V5n-Blockaden: {v5n.blocked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
