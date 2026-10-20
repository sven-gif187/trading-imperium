# -*- coding: utf-8 -*-
"""Unser Bot gegen die blind getesteten Signal-Anbieter.

HERKUNFT
--------
Sven hat am 29.08.2026 einen Entwurf geschrieben, der einen Datensatz
verifizierter Forex-Signalanbieter einliest und den eigenen Bot dagegen
haelt. Die Idee ist gut. Der Entwurf hatte eine Schwaeche, die das
Ergebnis wertlos gemacht haette:

    my_bot = {"win_rate": 0.74, "profit_factor": 2.10, "max_drawdown": 0.13}

Diese drei Zahlen waren VON HAND EINGETRAGEN - Platzhalter, im Entwurf
auch so gekennzeichnet. Wer sie stehen laesst, vergleicht nicht seinen
Bot, sondern seinen Wunsch. Die echten Zahlen lauteten 0,671 / 0,880 /
0,097. Das Programm haette "auf oder ueber Niveau der Top-Provider"
gemeldet, waehrend der Bot in Wahrheit Geld verliert.

Deshalb holt diese Fassung die Kennzahlen SELBST aus dem Handelsbuch.
Es gibt keine Stelle mehr, an der man eine Wunschzahl eintragen kann.

WAS GERECHNET WIRD
------------------
  Winrate        Anteil der Verkaeufe mit Gewinn
  Profit-Faktor  Summe der Gewinne / Summe der Verluste
                 Unter 1,00 heisst: der Bot verliert Geld.
  Drawdown       groesster Rueckgang der realisierten Gewinnkurve,
                 gemessen am echten Startkapital

TRIVIAL-LATTE
-------------
Pflicht in diesem Projekt: Jede Kennzahl steht neben der einfachsten
Alternative. Hier ist das "gar nicht handeln" - Ergebnis exakt 0,00 $,
Drawdown 0 %. Ein Bot mit negativem Netto ist schlechter als diese
Latte, egal wie gut seine Winrate aussieht.

WARUM DER VERGLEICH HINKT - und trotzdem etwas taugt
-----------------------------------------------------
Die Anbieter wurden auf ECHTEN MT4-Konten blind getestet, wir laufen im
Papierhandel. Sie handeln Forex mit Spreads im Bereich von Hundertsteln
eines Prozents, wir Krypto mit 0,505 % je Runde (K-BASIS). Ein direkter
Rangvergleich waere unredlich.

Was trotzdem gilt: Ein Profit-Faktor unter 1,00 ist in JEDEM Markt und
bei JEDER Kostenstruktur ein Verlustgeschaeft. Diese eine Aussage
haengt nicht am Vergleich.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python provider_vergleich.py
    python provider_vergleich.py --epoche E7
    python provider_vergleich.py --selbsttest
"""
import argparse
import json
import os
import sys
from statistics import mean

HANDELSBUCH = os.path.join("data_store", "trades_v5.json")
KONFIG = os.path.join("data_store", "config.json")
ANBIETER = "providers.json"
EPOCHEN = os.path.join("config_epochs.json")
ZIELE = "config_zielgroessen.json"


# ==================================================================
# Teil 1 - die echten Zahlen holen
# ==================================================================
def startkapital(pfad=KONFIG, standard=500.0):
    """Das echte Startkapital, nicht geraten."""
    try:
        d = json.load(open(pfad, encoding="utf-8"))
        for schluessel in ("trading", "risk"):
            teil = d.get(schluessel) or {}
            for k in ("initial_paper_balance", "start_balance", "initial_balance"):
                if k in teil:
                    return float(teil[k])
        if "initial_paper_balance" in d:
            return float(d["initial_paper_balance"])
    except Exception:
        pass
    return standard


def verkaeufe(pfad=HANDELSBUCH, ab=None, bis=None):
    """Alle Verkaeufe mit Geldergebnis, wahlweise auf ein Zeitfenster begrenzt.

    Genommen wird `pnl` - die GELDZAHL. Sie liegt rund 0,8 Prozentpunkte
    unter `pnl_pct`, enthaelt also die Gebuehren. Das ist die
    konservative Wahl; `pnl_pct` waere geschoent.
    """
    d = json.load(open(pfad, encoding="utf-8"))
    out = []
    for t in d:
        if t.get("type") != "SELL" or t.get("pnl") is None:
            continue
        z = str(t.get("time") or "")
        if ab and z < ab:
            continue
        if bis and z >= bis:
            continue
        out.append(t)
    return out


def kennzahlen(trades, kapital):
    """Winrate, Profit-Faktor und Drawdown aus echten Verkaeufen."""
    if not trades:
        return None
    p = [float(t["pnl"]) for t in trades]
    gewinne = [x for x in p if x > 0]
    verluste = [x for x in p if x < 0]
    summe_g = sum(gewinne)
    summe_v = abs(sum(verluste))

    stand = kapital
    hoch = kapital
    dd = 0.0
    for x in p:
        stand += x
        hoch = max(hoch, stand)
        if hoch > 0:
            dd = max(dd, (hoch - stand) / hoch)

    return {
        "n": len(p),
        "win_rate": len(gewinne) / len(p),
        "profit_factor": (summe_g / summe_v) if summe_v > 0 else float("inf"),
        "max_drawdown": dd,
        "summe_gewinne": summe_g,
        "summe_verluste": -summe_v,
        "netto": summe_g - summe_v,
        "mittlerer_trade": sum(p) / len(p),
        "mittl_gewinn": (summe_g / len(gewinne)) if gewinne else 0.0,
        "mittl_verlust": (summe_v / len(verluste)) if verluste else 0.0,
        # Gewinner/Verlierer-Verhaeltnis, im Projekt "payoff_ratio"
        "payoff": ((summe_g / len(gewinne)) / (summe_v / len(verluste)))
                  if gewinne and verluste and summe_v > 0 else None,
        # Ab welcher Trefferquote waere das Netto null?
        "noetige_winrate": ((summe_v / len(verluste)) /
                            ((summe_g / len(gewinne)) + (summe_v / len(verluste))))
                           if gewinne and verluste else None,
        "von": trades[0].get("time", "")[:16],
        "bis": trades[-1].get("time", "")[:16],
    }


def epochen(pfad=EPOCHEN):
    """Die Regelwerks-Abschnitte. Nur innerhalb einer Epoche darf
    verglichen werden - sonst mischt man verschiedene Regeln."""
    try:
        d = json.load(open(pfad, encoding="utf-8"))
        # Die Datei sieht so aus: {"epochs": [{"id": "E7_...", "start": "..."}]}
        # Frueher wurde hier "name" gesucht - das Feld heisst "id", und die
        # Liste steckt unter "epochs". Ergebnis war eine leere Liste, und
        # der Bericht liess die wichtigste Tabelle einfach weg, ohne zu
        # murren. Genau die Sorte stiller Fehlschlag, die hier nicht sein darf.
        roh = d.get("epochs") if isinstance(d, dict) else d
        if not isinstance(roh, list):
            raise ValueError("Kein 'epochs'-Feld mit einer Liste gefunden")
        paare = []
        for e in roh:
            if not isinstance(e, dict):
                continue
            name = e.get("id") or e.get("name")
            ab = e.get("start") or e.get("ab")
            if name and ab:
                paare.append((name, str(ab)))
        if not paare:
            raise ValueError("Keine Epoche mit id und start gefunden")
        return sorted(paare, key=lambda x: x[1])
    except Exception as e:
        print("  WARNUNG: Epochen nicht lesbar (%s) - es wird nur die" % e)
        print("           Gesamtlaufzeit gezeigt, und die mischt Regelwerke.")
        return []


def eigene_ziele(pfad=ZIELE):
    """Die Zielwerte, die das Projekt SCHON HAT - nicht neu erfunden.

    `config_zielgroessen.json` (gelesen von stichtag.py) fuehrt fuenf
    Zielgroessen, zwei davon sind hier einschlaegig:
        profit_faktor   Ziel 1,20   Warnung 1,00
        payoff_ratio    Ziel 1,27   Warnung 1,00
    Wer daneben eine zweite Latte aufstellt, hat zwei Wahrheiten. Also
    wird diese hier gelesen und mit ausgegeben.
    """
    try:
        d = json.load(open(pfad, encoding="utf-8"))
        return {k: v for k, v in d.items() if isinstance(v, dict) and "ziel" in v}
    except Exception:
        return {}


# ==================================================================
# Teil 2 - die Latte aus den Anbietern
# ==================================================================
def benchmarks(anbieter):
    wr = [p["blind_test_win_rate"] for p in anbieter]
    pf = [p["blind_test_profit_factor"] for p in anbieter]
    dd = [p["blind_test_max_drawdown"] for p in anbieter]
    return {
        "avg_win_rate": mean(wr), "min_win_rate": min(wr), "max_win_rate": max(wr),
        "avg_profit_factor": mean(pf), "min_profit_factor": min(pf),
        "max_profit_factor": max(pf),
        "avg_drawdown": mean(dd), "max_drawdown": max(dd), "min_drawdown": min(dd),
        "n": len(anbieter),
    }


def bewerten(bot, bm):
    """Fuenf Kriterien, wie in Svens Entwurf - aber mit einer Sperre davor.

    Die Sperre: Ein Profit-Faktor unter 1,00 bedeutet Verlust. Dann ist
    jede Punktzahl irrefuehrend, denn eine hohe Winrate kann das nicht
    aufwiegen. Der Entwurf kannte diese Sperre nicht - mit den echten
    Zahlen (Winrate 67 %, PF 0,88) haette er 1 von 5 Punkten vergeben
    und "im Mittelfeld" gemeldet, obwohl der Bot Geld verliert.
    """
    r = {
        "meets_min_winrate": bot["win_rate"] >= bm["min_win_rate"],
        "meets_avg_winrate": bot["win_rate"] >= bm["avg_win_rate"],
        "meets_min_profit_factor": bot["profit_factor"] >= bm["min_profit_factor"],
        "meets_avg_profit_factor": bot["profit_factor"] >= bm["avg_profit_factor"],
        "meets_drawdown_cap": bot["max_drawdown"] <= bm["max_drawdown"],
    }
    r["score"] = sum(1 for k, v in r.items() if k.startswith("meets") and v)

    if bot["profit_factor"] < 1.0:
        r["quality_label"] = "VERLUSTBRINGEND - schlechter als gar nicht handeln"
        r["gesperrt"] = True
    elif r["score"] >= 4:
        r["quality_label"] = "auf oder ueber Niveau der Top-Anbieter"
        r["gesperrt"] = False
    elif r["score"] >= 2:
        r["quality_label"] = "im Mittelfeld, mit Optimierungspotenzial"
        r["gesperrt"] = False
    else:
        r["quality_label"] = "deutlich unter der Latte"
        r["gesperrt"] = False
    return r


# ==================================================================
# Teil 3 - Ausgabe
# ==================================================================
def _pf(x):
    return "unendlich" if x == float("inf") else "%.3f" % x


def bericht(bot, bm, name, kapital):
    r = bewerten(bot, bm)
    print("=" * 78)
    print(" %s" % name)
    print("=" * 78)
    print("  Zeitraum %s bis %s   Startkapital %.2f $" % (bot["von"], bot["bis"], kapital))
    print("  Verkaeufe: %d   davon Gewinn: %d" % (bot["n"], round(bot["n"] * bot["win_rate"])))
    print()
    print("  Kennzahl            unser Bot     Anbieter-Schnitt   Spanne          erfuellt?")
    print("  " + "-" * 74)
    print("  Winrate             %7.1f %%      %7.1f %%          %.0f-%.0f %%         %s"
          % (100 * bot["win_rate"], 100 * bm["avg_win_rate"],
             100 * bm["min_win_rate"], 100 * bm["max_win_rate"],
             "JA" if r["meets_avg_winrate"] else ("knapp" if r["meets_min_winrate"] else "nein")))
    print("  Profit-Faktor       %9s      %7.2f           %.1f-%.1f        %s"
          % (_pf(bot["profit_factor"]), bm["avg_profit_factor"],
             bm["min_profit_factor"], bm["max_profit_factor"],
             "JA" if r["meets_avg_profit_factor"] else ("knapp" if r["meets_min_profit_factor"] else "NEIN")))
    print("  Max. Drawdown       %7.1f %%      %7.1f %%          %.0f-%.0f %%         %s"
          % (100 * bot["max_drawdown"], 100 * bm["avg_drawdown"],
             100 * bm["min_drawdown"], 100 * bm["max_drawdown"],
             "JA" if r["meets_drawdown_cap"] else "nein"))
    print("  " + "-" * 74)
    print("  Netto realisiert    %+9.2f $   (Gewinne %+.2f, Verluste %+.2f)"
          % (bot["netto"], bot["summe_gewinne"], bot["summe_verluste"]))
    print("  Mittlerer Trade     %+9.3f $" % bot["mittlerer_trade"])
    if bot.get("payoff") is not None:
        print("  Mittlerer Gewinn    %+9.3f $   mittlerer Verlust %+9.3f $"
              % (bot["mittl_gewinn"], -bot["mittl_verlust"]))
        print("  Gewinner/Verlierer  %9.2f : 1" % bot["payoff"])
        print("  Winrate NOETIG      %8.1f %%   (ab hier waere das Netto null) - "
              "wir haben %.1f %%, Luecke %+.1f PP"
              % (100*bot["noetige_winrate"], 100*bot["win_rate"],
                 100*(bot["win_rate"] - bot["noetige_winrate"])))
    z = eigene_ziele()
    if z:
        print()
        print("  UNSERE EIGENEN ZIELE (config_zielgroessen.json, gelesen von stichtag.py):")
        pf_z = z.get("profit_faktor", {})
        po_z = z.get("payoff_ratio", {})
        if pf_z:
            print("     Profit-Faktor   Ziel %.2f  Warnung %.2f   -> wir: %s  %s"
                  % (pf_z.get("ziel", 0), pf_z.get("warnung", 0), _pf(bot["profit_factor"]),
                     "erreicht" if bot["profit_factor"] >= pf_z.get("ziel", 0)
                     else ("ueber der Warnschwelle" if bot["profit_factor"] >= pf_z.get("warnung", 0)
                           else "UNTER der Warnschwelle")))
        if po_z and bot.get("payoff") is not None:
            print("     Gewinner/Verlierer  Ziel %.2f  Warnung %.2f   -> wir: %.2f  %s"
                  % (po_z.get("ziel", 0), po_z.get("warnung", 0), bot["payoff"],
                     "erreicht" if bot["payoff"] >= po_z.get("ziel", 0)
                     else ("ueber der Warnschwelle" if bot["payoff"] >= po_z.get("warnung", 0)
                           else "UNTER der Warnschwelle")))
    print()
    print("  TRIVIAL-LATTE  'gar nicht handeln':  Netto 0,00 $   Drawdown 0,0 %")
    besser = bot["netto"] > 0
    print("  Unser Bot ist gegenueber dieser Latte: %s (%+.2f $)"
          % ("BESSER" if besser else "SCHLECHTER", bot["netto"]))
    print()
    print("  Punktzahl (0-5): %d" % r["score"])
    print("  URTEIL: %s" % r["quality_label"])
    if r["gesperrt"]:
        print()
        print("  Die Punktzahl ist hier ohne Bedeutung. Ein Profit-Faktor unter")
        print("  1,00 heisst, dass die Verluste groesser sind als die Gewinne -")
        print("  daran aendert eine hohe Winrate nichts. Viele kleine Gewinne,")
        print("  wenige grosse Verluste ergeben genau dieses Bild.")
    print("=" * 78)
    return r


def lauf(nur_epoche=None):
    if not os.path.exists(ANBIETER):
        print("FEHLER: %s fehlt." % ANBIETER)
        return 1
    if not os.path.exists(HANDELSBUCH):
        print("FEHLER: %s fehlt." % HANDELSBUCH)
        return 1
    anb = json.load(open(ANBIETER, encoding="utf-8"))
    bm = benchmarks(anb)
    kapital = startkapital()

    print()
    print("  Latte aus %d blind getesteten Anbietern:" % bm["n"])
    print("     Winrate %.0f-%.0f %% (Schnitt %.1f %%)   Profit-Faktor %.1f-%.1f "
          "(Schnitt %.2f)   Drawdown bis %.0f %%"
          % (100*bm["min_win_rate"], 100*bm["max_win_rate"], 100*bm["avg_win_rate"],
             bm["min_profit_factor"], bm["max_profit_factor"], bm["avg_profit_factor"],
             100*bm["max_drawdown"]))
    print()

    ep = epochen()
    aktuell = ep[-1] if ep else None

    if nur_epoche:
        treffer = [e for e in ep if e[0] == nur_epoche]
        if not treffer:
            print("Epoche '%s' unbekannt. Bekannt: %s" % (nur_epoche, ", ".join(n for n, _ in ep)))
            return 1
        name, ab = treffer[0]
        b = kennzahlen(verkaeufe(ab=ab), kapital)
        if not b:
            print("Keine Verkaeufe in Epoche %s." % name)
            return 1
        bericht(b, bm, "EPOCHE %s" % name, kapital)
        return 0

    alle = kennzahlen(verkaeufe(), kapital)
    bericht(alle, bm, "GESAMTE LAUFZEIT  (mehrere Regelwerke gemischt)", kapital)

    if aktuell:
        name, ab = aktuell
        b = kennzahlen(verkaeufe(ab=ab), kapital)
        if b:
            print()
            bericht(b, bm, "NUR DIE LAUFENDE EPOCHE %s  (ab %s)" % (name, ab[:16]), kapital)
            print()
            print("  Die zweite Tabelle ist die aussagekraeftigere: nur sie zeigt das")
            print("  Regelwerk, das der Bot HEUTE benutzt. Die erste mischt %d Epochen."
                  % len(ep))
    print()
    print("  EINSCHRAENKUNGEN, die bei jedem Lesen mitzudenken sind:")
    print("   - Die Anbieter liefen auf ECHTEN Konten, wir im Papierhandel.")
    print("   - Sie handeln Forex, wir Krypto mit 0,505 % Kosten je Runde.")
    print("   - Ein Rangvergleich waere unredlich. Was bleibt: Profit-Faktor")
    print("     unter 1,00 ist in jedem Markt ein Verlustgeschaeft.")
    return 0


# ==================================================================
# Selbsttest - in beide Richtungen
# ==================================================================
def selbsttest():
    print("SELBSTTEST")
    print("-" * 62)
    f = 0

    bm = benchmarks([
        {"blind_test_win_rate": 0.70, "blind_test_profit_factor": 2.0, "blind_test_max_drawdown": 0.10},
        {"blind_test_win_rate": 0.80, "blind_test_profit_factor": 3.0, "blind_test_max_drawdown": 0.20},
    ])
    ok = abs(bm["avg_win_rate"] - 0.75) < 1e-9 and abs(bm["avg_profit_factor"] - 2.5) < 1e-9
    print("  %s Latte wird richtig gemittelt" % ("OK  " if ok else "FEHL")); f += 0 if ok else 1

    # Ein klarer Gewinner
    gut = {"win_rate": 0.85, "profit_factor": 3.5, "max_drawdown": 0.05}
    r = bewerten(gut, bm)
    ok = r["score"] == 5 and not r["gesperrt"]
    print("  %s guter Bot -> 5 Punkte, nicht gesperrt (ist: %d)" % ("OK  " if ok else "FEHL", r["score"]))
    f += 0 if ok else 1

    # Die Sperre: hohe Winrate, aber Verlust
    schlecht = {"win_rate": 0.90, "profit_factor": 0.88, "max_drawdown": 0.05}
    r = bewerten(schlecht, bm)
    ok = r["gesperrt"] and "VERLUST" in r["quality_label"]
    print("  %s Winrate 90 %% aber PF 0,88 -> als verlustbringend erkannt" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # Genau 1,00 ist noch nicht gesperrt
    r = bewerten({"win_rate": 0.5, "profit_factor": 1.0, "max_drawdown": 0.1}, bm)
    ok = not r["gesperrt"]
    print("  %s Profit-Faktor genau 1,00 -> nicht gesperrt (Grenze stimmt)" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # Kennzahlen gegen einen von Hand nachgerechneten Fall
    trades = [{"pnl": 10.0, "time": "a"}, {"pnl": -4.0, "time": "b"},
              {"pnl": 6.0, "time": "c"}, {"pnl": -2.0, "time": "d"}]
    k = kennzahlen(trades, 100.0)
    # Gewinne 16, Verluste 6 -> PF 2,667; Winrate 2/4 = 0,5
    # Kurve: 110, 106, 112, 110 -> groesster Rueckgang 4/110 = 3,64 %
    ok = (abs(k["profit_factor"] - 16/6) < 1e-9 and abs(k["win_rate"] - 0.5) < 1e-9
          and abs(k["max_drawdown"] - 4/110) < 1e-9)
    print("  %s Kennzahlen gegen Handrechnung (PF %.3f, WR %.2f, DD %.4f)"
          % ("OK  " if ok else "FEHL", k["profit_factor"], k["win_rate"], k["max_drawdown"]))
    f += 0 if ok else 1

    ok = kennzahlen([], 100.0) is None
    print("  %s leere Liste -> None statt Absturz" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # Nur Gewinne: Profit-Faktor unendlich, kein Absturz durch Division
    k = kennzahlen([{"pnl": 5.0, "time": "a"}], 100.0)
    ok = k["profit_factor"] == float("inf")
    print("  %s nur Gewinne -> unendlich statt Division durch Null" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    print("-" * 62)
    print("ALLE TESTS BESTANDEN" if f == 0 else "%d TEST(S) FEHLGESCHLAGEN" % f)
    return 0 if f == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epoche", default=None, help="nur diese Epoche auswerten, z. B. E7_filter_schaerfer")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        return selbsttest()
    return lauf(a.epoche)


if __name__ == "__main__":
    sys.exit(main())
