#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
go_live_check.py - Freigabe-Pruefung fuer den Live-Betrieb   [E10 29.07.2026]
[COCKPIT-KEEP]  Dauer-Werkzeug, kein erledigter Installer.
=============================================================================

WOFUER

Der Wechsel von Papier auf echtes Geld ist die eine Entscheidung, die man
nicht zurueckdrehen kann. Dieses Skript trifft sie nicht - es misst nur und
sagt, ob die Zahlen sie tragen. Es fasst den Bot mit keiner Zeile an: es
liest ausschliesslich, schreibt nichts und aendert keine Config.

    python go_live_check.py                # Bericht
    python go_live_check.py --seit 2026-07-29T16:38:00+00:00
    python go_live_check.py --json         # maschinenlesbar

WARUM DIE SCHWELLEN SO STEHEN

Am 29.07.2026 sah der Stand ueber 423 Verkaeufe so aus:

    Trefferquote      71.9 %       <- sieht hervorragend aus
    Chance/Risiko      0.35        <- und ist trotzdem toedlich
    Ergebnis         -27.57 $ (gebucht) / ca. -47 $ (mit Kaufgebuehr)

Eine hohe Trefferquote allein sagt nichts. Was zaehlt, ist der
Erwartungswert je Trade - und der war negativ. Genau deshalb ist
Kriterium B hier das Herzstueck und die Trefferquote taucht nur als
Beiwerk auf.

Kriterium F (untere Grenze des 95-%-Intervalls > 0) ist die Bremse gegen
Selbstbetrug: bei kleinen Stichproben sieht ein Zufallslauf schnell nach
Koennen aus. Erst wenn auch das PESSIMISTISCHE Ende des Intervalls im
Plus liegt, ist der Vorteil belastbar. Das ist der Standardweg, mit dem
auch professionelle Haeuser Strategien freigeben.

Kriterium A (Mindeststichprobe SEIT dem Umbau) verhindert, dass alte
Trades mit alter Mechanik die Freigabe erschleichen. Am 29.07. wurden
zwoelf Defekte behoben, darunter drei, die direkt aufs Ergebnis wirken
(Gebuehren-Kreisel, Kaufgebuehr in der P&L, Trailing nach Nachkauf).
Alles davor ist fuer diese Frage wertlos.
"""
import os
import sys
import json
import math
import argparse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))


def _pfad(*teile):
    return os.path.join(ROOT, *teile)


# ---------------------------------------------------------------------------
# Stichtag des Umbaus. Alles davor zaehlt fuer die Freigabe NICHT.
#
# 29.07.2026 21:00 Ortszeit (MESZ) = 19:00 UTC.
# ZURUECKGESETZT von 16:38 auf 19:00: dazwischen lief der Grid Bot als
# zweiter Einstiegspfad mit (2 Verkaeufe). Eine Stichprobe aus zwei
# gleichzeitig laufenden Strategien laesst sich hinterher nicht
# auseinanderrechnen - deshalb werden diese Trades bewusst verworfen und
# die Zaehlung beginnt neu mit ausgeschaltetem Grid.
# Siehe config.trading.grid_enabled und Ticket E11-GRID.
#
# REGEL: Jede Aenderung im Entscheidungspfad (Einstieg, Ausstieg, Sizing,
# Risiko-Tore, Coin-Liste) setzt dieses Datum neu. Aenderungen an UI,
# Berichten, Auswertung oder Backtest nicht.
# ---------------------------------------------------------------------------
UMBAU_STICHTAG = "2026-07-29T19:00:00+00:00"

# Schwellen
MIN_VERKAEUFE = 100          # A: Stichprobe seit Umbau
MIN_ERWARTUNG = 0.0          # B: Erwartungswert je Trade in $

# --------------------------------------------------------------------------
# C: Chance/Risiko - relativ zum Break-even, nicht absolut.  [E12 29.07.2026]
# --------------------------------------------------------------------------
# Vorher stand hier MIN_RR = 0.8 als feste Schwelle. Das ist konzeptionell
# falsch, weil ein R/R ohne die zugehoerige Trefferquote nicht interpretierbar
# ist. Break-even liegt bei
#
#       noetiges R/R = (1 - Trefferquote) / Trefferquote
#
# Eine feste 0.8 ist deshalb gleichzeitig zu streng UND zu lax:
#
#   Trefferquote | Break-even | feste 0.8 sagt        | Faktor-Regel verlangt
#   -------------|------------|-----------------------|----------------------
#      71.9 %    |    0.39    | zu streng (2x noetig) |   0.47
#      50.0 %    |    1.00    | zu lax (laesst durch) |   1.20
#      30.0 %    |    2.33    | irrefuehrend          |   2.80
#
# Ein System mit 30 % Trefferquote und R/R 0.9 bestand die alte Pruefung und
# verlor sicher Geld. Der reale Bot (71.9 % Trefferquote, R/R 0.35) scheiterte
# an ihr, obwohl er nur 0.04 R/R-Punkte vom Break-even entfernt war.
#
# SICHERHEITSFAKTOR 1.2 = 20 % Reserve ueber dem rechnerischen Break-even.
# Er faengt ab, dass Trefferquote und R/R aus derselben Stichprobe geschaetzt
# werden und beide streuen. Ohne Reserve wuerde jedes System freigegeben, das
# im Mittel exakt null verdient.
#
# Das ist KEINE Lockerung: fuer schlechte Systeme ist die Regel deutlich
# strenger als die alte feste Schwelle. Kriterium B (Erwartungswert > 0) und
# F (unteres Ende des Konfidenzintervalls > 0) bleiben unveraendert scharf und
# sind weiterhin das eigentliche Mass.
RR_SICHERHEITSFAKTOR = 1.2


def noetiges_rr(wr_pct):
    """Break-even-R/R bei gegebener Trefferquote, mit Sicherheitsreserve."""
    w = float(wr_pct) / 100.0
    if w <= 0:
        return float("inf")     # keine Gewinner -> nicht erfuellbar
    if w >= 1:
        return 0.0              # nur Gewinner -> jedes R/R genuegt
    return (1.0 - w) / w * RR_SICHERHEITSFAKTOR
MAX_CHURN_PCT = 10.0         # D: Rueckkaeufe binnen 15 min, Anteil der Verkaeufe
MAX_DRAWDOWN_PCT = 15.0      # E: groesster Rueckgang der Equity-Kurve
MIN_TAGE = 14                # G: Mindestlaufzeit seit Umbau


class Pruefung:
    def __init__(self, kuerzel, titel):
        self.kuerzel, self.titel = kuerzel, titel
        self.bestanden = None        # None = nicht bewertbar
        self.ist = ""
        self.soll = ""
        self.hinweis = ""

    def setze(self, bestanden, ist, soll, hinweis=""):
        self.bestanden, self.ist, self.soll, self.hinweis = bestanden, ist, soll, hinweis
        return self


def _lade_json(pfad, standard):
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return standard


def _zeit(t):
    try:
        d = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def sammle(seit_iso):
    """Liest Journal + Config und rechnet alle Kennzahlen."""
    seit = _zeit(seit_iso)
    trades = _lade_json(_pfad("data_store", "trades_v5.json"), [])
    if not isinstance(trades, list):
        trades = []

    neu = []
    for t in trades:
        z = _zeit(t.get("time"))
        if z is not None and seit is not None and z >= seit:
            neu.append(t)

    verkaeufe = [t for t in neu if t.get("type") == "SELL"]
    pnl = []
    for t in verkaeufe:
        try:
            pnl.append(float(t.get("pnl") or 0))
        except Exception:
            pnl.append(0.0)

    n = len(pnl)
    summe = sum(pnl)
    mittel = (summe / n) if n else 0.0
    gewinne = [p for p in pnl if p > 0]
    verluste = [p for p in pnl if p <= 0]
    wr = (len(gewinne) / n * 100) if n else 0.0
    avg_w = (sum(gewinne) / len(gewinne)) if gewinne else 0.0
    avg_v = (sum(verluste) / len(verluste)) if verluste else 0.0
    rr = abs(avg_w / avg_v) if avg_v else 0.0

    # 95-%-Intervall des Erwartungswerts (Normalnaeherung)
    unten = oben = 0.0
    if n > 1:
        var = sum((p - mittel) ** 2 for p in pnl) / (n - 1)
        stdfehler = math.sqrt(var) / math.sqrt(n)
        unten, oben = mittel - 1.96 * stdfehler, mittel + 1.96 * stdfehler

    # Churn: Rueckkauf desselben Coins binnen 15 min nach einem Verkauf
    je_coin = {}
    for t in sorted(neu, key=lambda x: _zeit(x.get("time")) or datetime.min.replace(tzinfo=timezone.utc)):
        je_coin.setdefault(t.get("coin"), []).append(t)
    churn = 0
    for _c, folge in je_coin.items():
        for i in range(len(folge) - 1):
            if folge[i].get("type") == "SELL" and folge[i + 1].get("type") == "BUY":
                a, b = _zeit(folge[i].get("time")), _zeit(folge[i + 1].get("time"))
                if a and b and (b - a).total_seconds() < 900:
                    churn += 1
    churn_pct = (churn / n * 100) if n else 0.0

    # Groesster Equity-Rueckgang seit Umbau
    eq = _lade_json(_pfad("data_store", "equity_history.json"), {})
    reihe = eq.get("total") if isinstance(eq, dict) else None
    dd = 0.0
    if isinstance(reihe, list) and reihe:
        grenze = seit.timestamp() if seit else 0
        werte = [w for z, w in reihe if isinstance(z, (int, float)) and z >= grenze]
        hoch = None
        for w in werte:
            hoch = w if hoch is None or w > hoch else hoch
            if hoch and hoch > 0:
                dd = max(dd, (hoch - w) / hoch * 100)

    tage = 0.0
    if seit:
        tage = (datetime.now(timezone.utc) - seit).total_seconds() / 86400

    return {
        "seit": seit_iso, "tage": tage,
        "trades_gesamt": len(trades), "trades_neu": len(neu),
        "verkaeufe": n, "summe": summe, "mittel": mittel,
        "wr": wr, "avg_w": avg_w, "avg_v": avg_v, "rr": rr,
        "ki_unten": unten, "ki_oben": oben,
        "churn": churn, "churn_pct": churn_pct, "drawdown": dd,
        "config": _lade_json(_pfad("data_store", "config.json"), {}),
    }


def pruefe_zahlen(d):
    p = []

    a = Pruefung("A", "Stichprobe seit dem Umbau")
    a.setze(d["verkaeufe"] >= MIN_VERKAEUFE,
            f"{d['verkaeufe']} Verkaeufe in {d['tage']:.1f} Tagen",
            f">= {MIN_VERKAEUFE} Verkaeufe",
            "Alles vor dem Stichtag lief mit der defekten Mechanik und zaehlt nicht.")
    p.append(a)

    b = Pruefung("B", "Erwartungswert je Trade")
    b.setze(d["verkaeufe"] > 0 and d["mittel"] > MIN_ERWARTUNG,
            f"{d['mittel']:+.4f} $ (Summe {d['summe']:+.2f} $)",
            "> 0.00 $",
            "DAS ist die Kernfrage. Trefferquote ohne positiven "
            "Erwartungswert ist wertlos - 71.9 % und trotzdem Minus.")
    p.append(b)

    c = Pruefung("C", "Chance/Risiko gegen Break-even")
    _noetig = noetiges_rr(d["wr"]) if d["verkaeufe"] > 0 else float("inf")
    _be = (100 - d["wr"]) / d["wr"] if d["wr"] > 0 else float("inf")
    c.setze(d["verkaeufe"] > 0 and d["rr"] >= _noetig,
            f"{d['rr']:.2f} bei {d['wr']:.1f} % Trefferquote "
            f"(Gewinn {d['avg_w']:+.3f} $ / Verlust {d['avg_v']:+.3f} $)",
            f">= {_noetig:.2f}  (Break-even {_be:.2f} x {RR_SICHERHEITSFAKTOR} Reserve)",
            "R/R ist ohne Trefferquote nicht lesbar: bei 71.9 % genuegen 0.39, "
            "bei 30 % braucht es 2.33. Die Schwelle rechnet das mit.")
    p.append(c)

    e = Pruefung("D", "Gebuehren-Kreisel")
    e.setze(d["verkaeufe"] == 0 or d["churn_pct"] <= MAX_CHURN_PCT,
            f"{d['churn']} Rueckkaeufe binnen 15 min ({d['churn_pct']:.1f} %)",
            f"<= {MAX_CHURN_PCT:.0f} %",
            "Vor dem Umbau: 338 von 423 = 80 %, davon 94 % teurer.")
    p.append(e)

    f = Pruefung("E", "Groesster Equity-Rueckgang")
    f.setze(d["drawdown"] <= MAX_DRAWDOWN_PCT,
            f"{d['drawdown']:.2f} %",
            f"<= {MAX_DRAWDOWN_PCT:.0f} %", "")
    p.append(f)

    g = Pruefung("F", "Vorteil statistisch belastbar")
    if d["verkaeufe"] > 1:
        g.setze(d["ki_unten"] > 0,
                f"95-%-Intervall {d['ki_unten']:+.4f} .. {d['ki_oben']:+.4f} $",
                "untere Grenze > 0",
                "Auch das pessimistische Ende muss im Plus liegen, sonst ist "
                "der Gewinn womoeglich nur Zufall.")
    else:
        g.setze(False, "zu wenig Daten", "untere Grenze > 0", "")
    p.append(g)

    h = Pruefung("G", "Mindestlaufzeit")
    h.setze(d["tage"] >= MIN_TAGE, f"{d['tage']:.1f} Tage", f">= {MIN_TAGE} Tage",
            "Verschiedene Marktlagen erlebt zu haben ist Teil des Beweises.")
    p.append(h)
    return p


def pruefe_technik(d):
    p = []
    cfg = d["config"]
    risk = cfg.get("risk", {}) or {}
    trading = cfg.get("trading", {}) or {}

    t1 = Pruefung("H1", "Tagesverlust-Waechter scharf")
    dl = risk.get("daily_loss", {}) or {}
    t1.setze(str(dl.get("mode", "")).lower() == "aktiv",
             f"mode={dl.get('mode', 'fehlt')}, limit={dl.get('limit_pct', '?')} %",
             "mode=aktiv", "Im Modus 'schatten' rechnet er nur und greift nie ein.")
    p.append(t1)

    t2 = Pruefung("H2", "Kill-Switch aktiviert")
    t2.setze(bool(risk.get("kill_switch_enabled")),
             str(risk.get("kill_switch_enabled")), "true", "")
    p.append(t2)

    t3 = Pruefung("H3", "Per-Coin-Exposure begrenzt")
    mc = float(risk.get("max_exposure_per_coin_pct", 0) or 0)
    t3.setze(0 < mc <= 35, f"{mc:.0f} %", "> 0 und <= 35 %", "")
    p.append(t3)

    t4 = Pruefung("H4", "Nachkauf-Leiter begrenzt")
    lv = int(trading.get("dca_max_levels", 0) or 0)
    t4.setze(0 < lv <= 5, f"{lv}", "1 bis 5",
             "Ohne Deckel wird das Mitteln zum Martingale ohne Boden.")
    p.append(t4)

    t5 = Pruefung("H5", "API-Schluessel vorhanden")
    key = os.environ.get("BINANCE_API_KEY", "")
    if not key:
        try:
            with open(_pfad(".env"), "r", encoding="utf-8") as f:
                for zeile in f:
                    if zeile.strip().startswith("BINANCE_API_KEY="):
                        key = zeile.split("=", 1)[1].strip()
        except Exception:
            pass
    t5.setze(bool(key), "gesetzt" if key else "fehlt", "in .env gesetzt",
             "Ohne Schluessel faellt der Bot beim Start still auf Papier zurueck.")
    p.append(t5)

    t6 = Pruefung("H6", "Schluessel-Rechte")
    t6.setze(None, "nicht automatisch pruefbar",
             "nur Lesen + Spot-Handel, KEIN Withdrawal",
             "Von Hand bei Binance pruefen: API-Management -> Berechtigungen. "
             "'Enable Withdrawals' muss AUS sein.")
    p.append(t6)

    t7 = Pruefung("H7", "Journal deckungsgleich mit Bestand")
    stand = _lade_json(_pfad("data_store", "bot_state.json"), {})
    bestand = stand.get("paper_balances_backup", {}) or {}
    trades = _lade_json(_pfad("data_store", "trades_v5.json"), [])
    netto = {}
    for t in trades if isinstance(trades, list) else []:
        try:
            q = float(t.get("qty") or 0)
        except Exception:
            continue
        c = str(t.get("coin", "")).split("/")[0]
        netto[c] = netto.get(c, 0) + (q if t.get("type") == "BUY" else -q)
    abweichungen = []
    for c, q in netto.items():
        ist = float(bestand.get(c, 0) or 0)
        if abs(q - ist) > max(1e-6, abs(ist) * 0.01):
            abweichungen.append(f"{c}: Journal {q:.4f} vs Bestand {ist:.4f}")
    t7.setze(not abweichungen,
             "deckungsgleich" if not abweichungen else "; ".join(abweichungen[:3]),
             "keine Abweichung",
             "Ein Journal mit Luecken kann keine Freigabe begruenden.")
    p.append(t7)

    t8 = Pruefung("H8", "Aktueller Modus")
    t8.setze(None, str(trading.get("mode", "?")), "paper bis zur Freigabe", "")
    p.append(t8)
    return p


def bericht(d, zahlen, technik, als_json=False):
    harte = [x for x in zahlen + technik if x.bestanden is not None]
    offen = [x for x in zahlen + technik if x.bestanden is None]
    durchgefallen = [x for x in harte if not x.bestanden]
    freigabe = not durchgefallen

    if als_json:
        print(json.dumps({
            "freigabe": freigabe,
            "kennzahlen": {k: v for k, v in d.items() if k != "config"},
            "pruefungen": [{"kuerzel": x.kuerzel, "titel": x.titel,
                            "bestanden": x.bestanden, "ist": x.ist, "soll": x.soll}
                           for x in zahlen + technik],
        }, indent=2, ensure_ascii=False))
        return freigabe

    def block(titel, liste):
        print(f"\n{titel}")
        print("-" * 78)
        for x in liste:
            zeichen = "OK  " if x.bestanden else ("-- " if x.bestanden is None else "NEIN")
            print(f" [{zeichen}] {x.kuerzel}  {x.titel}")
            print(f"        ist:  {x.ist}")
            print(f"        soll: {x.soll}")
            if x.hinweis:
                print(f"        ->    {x.hinweis}")

    print("=" * 78)
    print(" FREIGABE-PRUEFUNG LIVE-BETRIEB")
    print(f" Stichtag Umbau: {d['seit']}   Laufzeit seither: {d['tage']:.1f} Tage")
    print(f" Journal gesamt: {d['trades_gesamt']} Eintraege, davon seit Umbau: {d['trades_neu']}")
    print("=" * 78)

    block("ZAHLEN", zahlen)
    block("TECHNIK UND SICHERUNGEN", technik)

    print("\n" + "=" * 78)
    if freigabe:
        print(" ERGEBNIS: FREIGABE MOEGLICH - alle harten Kriterien erfuellt.")
        print(" Trotzdem: klein anfangen. Der erste Live-Betrag sollte ein")
        print(" Betrag sein, dessen Totalverlust nichts aendert.")
    else:
        print(f" ERGEBNIS: KEINE FREIGABE - {len(durchgefallen)} Kriterium(en) nicht erfuellt:")
        for x in durchgefallen:
            print(f"   - {x.kuerzel} {x.titel}: {x.ist} (noetig: {x.soll})")
    if offen:
        print("\n Von Hand zu pruefen:")
        for x in offen:
            print(f"   - {x.kuerzel} {x.titel}: {x.soll}")
    print("=" * 78)
    return freigabe


def main():
    ap = argparse.ArgumentParser(description="Freigabe-Pruefung fuer den Live-Betrieb")
    ap.add_argument("--seit", default=UMBAU_STICHTAG,
                    help=f"Stichtag des Umbaus (ISO). Vorgabe: {UMBAU_STICHTAG}")
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    a = ap.parse_args()

    d = sammle(a.seit)
    frei = bericht(d, pruefe_zahlen(d), pruefe_technik(d), a.json)
    return 0 if frei else 1


if __name__ == "__main__":
    sys.exit(main())
