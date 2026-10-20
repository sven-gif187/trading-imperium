# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Strategie-Labor Stufe 7: Papier-Wettkampf (Freigabe Sven 14.10.2026, Z3).

  A = heutiger Bot v6 (laeuft ohnehin, hier nur ausgewertet)
  B = K2 Trend-Ensemble + BTC-200-Filter, 6 Bitvavo-USDC-Coins, 500 $ Papier
  C = K1 Trend-Ensemble ohne Filter,      6 Bitvavo-USDC-Coins, 500 $ Papier
  Messlatten M1 (BTC halten), M2 (Korb 6, monatlich), M3 (BTC ueber 200-Tage-Linie) rechnerisch.

ABLAUF je Lauf (Windows-Aufgabe taeglich 02:15 Berlin, nach dem UTC-Tagesschluss):
  1. Tageskerzen der 6 Coins von Binance nachladen (nur abgeschlossene Tage) und den
     Eroeffnungskurs des laufenden Tages holen.
  2. Signale aus der kompletten Historie (Aufwaermen ab 2018, damit die Trend-Stopps stimmen).
  3. Den Wettkampf ab Signaltag 14.10.2026 (Ausfuehrung 15.10. Eroeffnung) mit DEMSELBEN
     Simulator wie die Rueckrechnung durchrechnen - deterministisch, jeder Lauf ergibt fuer die
     Vergangenheit dasselbe. Kosten je Seite: Bitvavo 0,05 % + halbe gemessene Spanne je Coin.
  4. Journal, Kontokurve, Stand schreiben; montags Wochenbericht (+ Telegram, wenn eingerichtet).
Liest NICHTS aus den Bot-Ordnern ausser v6 trades_v5.json (fuer A) und schreibt nur unter labor/papier/.

Aufrufe: pythonw papier_tag.py | python papier_tag.py --zeigen | --selbsttest
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HIER = Path(__file__).resolve().parent
LABOR = HIER.parent
P = LABOR.parent
sys.path.insert(0, str(LABOR))
sys.path.insert(0, str(P / "skripte"))
sys.path.insert(0, str(P / "waechter"))
import backtest as bt  # noqa: E402

UNI6 = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"]
SIGNALTAG = "2026-10-14"                 # erster Signal-Tagesschluss, Ausfuehrung 15.10. Eroeffnung
WARMLAUF_AB = "2017-08-17"
DATEN = HIER / "daten"
BERLIN = ZoneInfo("Europe/Berlin")
# Bitvavo USDC 14.10.2026: Gebuehr 0,05 % je Seite + halbe Median-Spanne (labor/ergebnisse/bitvavo_universum.json)
SPANNE_BP = {"BTC": 3.25, "ETH": 3.79, "SOL": 4.89, "XRP": 6.98, "ADA": 12.29, "DOGE": 18.68}
KOSTEN_SEITE = {k: 0.0005 + bp / 2 / 10000 for k, bp in SPANNE_BP.items()}
INSTANZEN = {"B": ("K2 Trend + BTC-200-Filter", lambda: bt.K1Trend(filter_btc200=True, name="B K2")),
             "C": ("K1 Trend-Ensemble", lambda: bt.K1Trend(name="C K1"))}
MESSLATTEN = {"M1 BTC halten": bt.M1BTCHalten, "M2 Korb 6": bt.M2Korb, "M3 BTC-200": bt.M3BTC200}


# ------------------------------------------------------------------ Daten
def daten_aktualisieren(netz: bool = True) -> dict:
    """Kopiert beim ersten Lauf die Labor-Daten, laedt dann fehlende abgeschlossene Tage nach.
    Rueckgabe: Eroeffnungskurse des laufenden UTC-Tages (leer, wenn ohne Netz)."""
    DATEN.mkdir(parents=True, exist_ok=True)
    heute_open = {}
    ex = None
    if netz:
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True, "timeout": 60000})
    heute = datetime.now(timezone.utc).date().isoformat()
    for c in UNI6:
        ziel = DATEN / f"{c}_1d.csv"
        if not ziel.exists():
            shutil.copy2(LABOR / "daten" / f"{c}_1d.csv", ziel)
        if ex is None:
            continue
        with ziel.open(encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        letzter = int(zeilen[-1]["ts_ms"])
        for versuch in range(3):
            try:
                k = ex.fetch_ohlcv(f"{c}/USDT", "1d", since=letzter + 86_400_000, limit=1000)
                break
            except Exception:
                if versuch == 2:
                    raise
                time.sleep(5)
        neu = []
        for x in k:
            d = datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat()
            if d < heute:
                neu.append([x[0], d, *x[1:6]])
            elif d == heute:
                heute_open[c] = float(x[1])
        if neu:
            with ziel.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(neu)
    return heute_open


def markt(heute_open: dict) -> bt.Markt:
    bt.COINS[:] = UNI6
    bt.DATEN = DATEN
    m = bt.Markt.laden()
    heute = datetime.now(timezone.utc).date().isoformat()
    if heute_open and len(heute_open) == len(UNI6) and m.datum[-1] < heute:
        m.datum.append(heute)
        for c in UNI6:
            m.o[c].append(heute_open[c])
            m.c[c].append(None)                  # laufender Tag: noch kein Schluss
    return m


# ------------------------------------------------------------------ Wettkampf rechnen
def rechnen(m: bt.Markt, ordner: Path = HIER, a_zeilen: list[dict] | None = None) -> dict:
    """ordner: wohin Journal und Kurven geschrieben werden (Selbsttest: Temp-Ordner, nie der Live-Ordner).
    a_zeilen: Trades fuer A (None = v6 trades_v5.json lesen)."""
    out = {"stand_utc": datetime.now(timezone.utc).isoformat(), "letzter_tag": m.datum[-1],
           "laufender_tag_offen": m.c["BTC"][-1] is None, "instanzen": {}, "messlatten": {}}
    if m.idx(SIGNALTAG) >= len(m.datum) - 1:
        out["hinweis"] = "Wettkampf hat noch nicht begonnen (erste Ausfuehrung 15.10. Eroeffnung)"
        return out
    for key, (name, fabrik) in INSTANZEN.items():
        s = fabrik()
        ziele = bt.ziele_berechnen(s, m, m.datum[200])           # Aufwaermen ab 2018
        journal = []
        e = bt.simuliere(s, m, 0.15, SIGNALTAG, ziele=ziele, kosten_je_coin=KOSTEN_SEITE, journal=journal)
        out["instanzen"][key] = auswerten(e, name, journal)
        schreibe_csv(ordner / f"{key}_journal.csv", journal)
        schreibe_csv(ordner / f"{key}_kurve.csv", [{"datum": d, "equity": round(v, 4), "investiert": round(x, 4)}
                                                   for d, v, x in zip(e.datum, e.equity, e.exposure)])
    for name, fabrik in MESSLATTEN.items():
        s = fabrik()
        e = bt.simuliere(s, m, 0.15, SIGNALTAG, ziele=bt.ziele_berechnen(s, m, SIGNALTAG), kosten_je_coin=KOSTEN_SEITE)
        out["messlatten"][name] = auswerten(e, name, None)
    out["A_bot_v6"] = bot_a(m, ordner, a_zeilen)
    out["kriterien"] = kriterien(out, m)
    return out


def auswerten(e: bt.Ergebnis, name: str, journal: list | None) -> dict:
    eq = e.equity
    hoch, mdd = bt.START_KAPITAL, 0.0
    for v in eq:
        hoch = max(hoch, v)
        mdd = min(mdd, v / hoch - 1)
    kz = bt.kennzahlen(e) if len(eq) >= 3 else {}
    return {"name": name, "tage": len(eq), "equity": round(eq[-1], 2) if eq else bt.START_KAPITAL,
            "rendite_pct": round((eq[-1] / bt.START_KAPITAL - 1) * 100, 2) if eq else 0.0,
            "max_rueckgang_pct": round(mdd * 100, 2), "kosten_usd": round(e.kosten, 2),
            "orders": len(journal) if journal is not None else None,
            "runden_geschlossen": len([r for r in e.runden if r.ende]),
            "investiert_pct": round(e.exposure[-1] * 100, 1) if e.exposure else 0.0,
            # S7-Nachtrag 1: dieselben Masse fuer alle (Sharpe, Kostenanteil am Brutto, mittlere Investitionsquote)
            "sharpe": kz.get("sharpe"), "investiert_mittel_pct": kz.get("investiert_mittel_pct"),
            "runden_je_monat": kz.get("runden_je_monat"),
            "kostenanteil_brutto_pct": round(100 * e.kosten / (eq[-1] - bt.START_KAPITAL + e.kosten), 1)
            if eq and (eq[-1] - bt.START_KAPITAL + e.kosten) > 0.01 else None,   # Brutto unter 1 Cent: kein Anteil
            "bestand": {k: round(v, 8) for k, v in getattr(e, "bestand", {}).items()},
            "kontrolle_usd": e.kontrolle}


V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
A_AB = "2026-10-15"


def a_ab() -> str:
    """Start von A = Tag der ersten Ausfuehrung (Signaltag + 1); live 15.10., im Selbsttest mitwandernd."""
    return (datetime.fromisoformat(SIGNALTAG) + timedelta(days=1)).date().isoformat()


def _f(x) -> float:
    try:
        return float(x or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _kauf_abfluss(k: dict) -> float:
    """Wie runden_lib: amount mit oder ohne Gebuehr je Kauf erkennen."""
    a, fe = _f(k.get("amount")), _f(k.get("fee"))
    return a + (fe if abs(a - _f(k.get("qty")) * _f(k.get("price"))) <= max(0.01, fe * 0.2) else 0.0)


def kurve_a(zeilen: list[dict], m: bt.Markt, ab: str = A_AB) -> tuple[list[str], list[float], list[float], list[dict]]:
    """S7-Nachtrag 1 (A10-Befund 1): Tageskurve fuer A zum UTC-Tagesschluss.
    Wert(d) = 500 + Netto der Runden mit Kauf ab 'ab' und Verkauf bis Ende d (Kasse, runden_lib)
              + offene Kaeufe ab 'ab': Menge x Tagesschluss - Mittelabfluss.
    Investiert(d) = Marktwert offener Kaeufe / Wert(d). Kaeufe vor 'ab' zaehlen nicht (wie bisher)."""
    from runden_lib import runden
    rd = [r for r in runden(zeilen) if r["kauf_t"] >= ab]
    tage, werte, quote = [], [], []
    for i, d in enumerate(m.datum):
        if d < ab[:10] or m.c["BTC"][i] is None:
            continue
        schnitt = (datetime.fromisoformat(d) + timedelta(days=1)).date().isoformat()
        real = sum(r["netto"] for r in rd if r["t"] < schnitt)
        offen: dict[str, list] = {}
        for z in zeilen:
            if z["time"] >= schnitt:
                break
            typ = str(z.get("type", "")).upper()
            if typ == "BUY":
                offen.setdefault(z["coin"], []).append(z)
            elif typ == "SELL":
                offen.pop(z["coin"], None)
        markt_wert = abfluss = 0.0
        for coin, kaeufe in offen.items():
            if not kaeufe or kaeufe[0]["time"] < ab:
                continue
            c = coin.split("/")[0]
            kurs = m.c[c][i] if c in m.c and m.c[c][i] is not None else _f(kaeufe[-1].get("price"))
            markt_wert += sum(_f(k.get("qty")) for k in kaeufe) * kurs
            abfluss += sum(_kauf_abfluss(k) for k in kaeufe)
        wert = bt.START_KAPITAL + real + markt_wert - abfluss
        tage.append(d)
        werte.append(wert)
        quote.append(max(0.0, min(1.0, markt_wert / wert)) if wert > 0 else 0.0)
    return tage, werte, quote, rd


def bot_a(m: bt.Markt, ordner: Path = HIER, zeilen: list[dict] | None = None) -> dict:
    """A = v6 ab 15.10. (jede Epoche, Grenzen im Wochenbericht): Tageskurve, Kasse der Runden, Kosten."""
    try:
        from runden_lib import lade
        zeilen = lade(V6) if zeilen is None else zeilen
        tage, werte, quote, rd = kurve_a(zeilen, m, a_ab())
        netto = sum(r["netto"] for r in rd)
        kosten = sum(r["kauf_fee"] + r["verkauf_fee"] for r in rd)
        e = bt.Ergebnis("A Bot v6", 0.15, datum=tage, equity=werte, exposure=quote)
        hoch, mdd = bt.START_KAPITAL, 0.0
        for v in werte:
            hoch = max(hoch, v)
            mdd = min(mdd, v / hoch - 1)
        kz = bt.kennzahlen(e) if len(werte) >= 3 else {}
        monate = max(1e-9, len(tage) / 30.44)
        schreibe_csv(ordner / "A_kurve.csv", [{"datum": d, "equity": round(v, 4), "investiert": round(x, 4)}
                                              for d, v, x in zip(tage, werte, quote)])
        return {"name": "A heutiger Bot v6", "tage": len(werte), "runden": len(rd), "netto_usd": round(netto, 2),
                "equity": round(werte[-1], 2) if werte else bt.START_KAPITAL,
                "rendite_pct": round((werte[-1] / bt.START_KAPITAL - 1) * 100, 2) if werte else 0.0,
                "rendite_pct_auf_500": round(netto / 5, 2), "kosten_usd": round(kosten, 2),
                "max_rueckgang_pct": round(mdd * 100, 2), "sharpe": kz.get("sharpe"),
                "investiert_mittel_pct": kz.get("investiert_mittel_pct"),
                "runden_je_monat": round(len(rd) / monate, 2) if tage else None,
                "kostenanteil_brutto_pct": round(100 * kosten / (netto + kosten), 1) if (netto + kosten) > 0.01 else None,
                "epochen_seit_start": epochen_v6(),
                # Datenguete: vor E7 gab es Nachkaeufe, deren Verkauf nur einen Teil zeigt (inventur.md, 05./06.08.:
                # drei Runden je ~ -55 $ statt ~0 gebucht). Seit E7 0 Faelle (A10). Taucht so etwas auf -> Kurve A pruefen.
                "warnung_unvollstaendige_runden": sum(1 for r in rd if r["n_kaeufe"] > 1
                                                      and r["verkauf_nominal"] < 0.8 * r["kauf_nominal"]),
                "hinweis": "Tageskurve = Kasse geschlossener Runden + offene Kaeufe zum Tagesschluss (S7-Nachtrag 1)"}
    except Exception as ex:
        return {"name": "A heutiger Bot v6", "fehler": f"{type(ex).__name__}: {ex}"[:200]}


def epochen_v6() -> list[str]:
    """Epochen von v6, die im Wettkampf gelten: die zum Start laufende und alle danach begonnenen."""
    try:
        ep = json.loads((V6 / "config_epochs.json").read_text(encoding="utf-8"))["epochs"]
        ep = sorted(ep, key=lambda x: x["start"])
        vorher = [x for x in ep if x["start"][:10] < A_AB]
        return [f"{x['id']} ab {x['start'][:16]}" for x in vorher[-1:] + [x for x in ep if x["start"][:10] >= A_AB]]
    except Exception as ex:
        return [f"Epochen nicht lesbar: {type(ex).__name__}"]


def kriterien(stand: dict, m: bt.Markt) -> dict:
    """S7-Nachtrag 1+2: Erfolgskriterien je Kandidat B/C maschinell.
    Nachtrag 2 (Entscheidung Sven E2, 15.10.2026): M3 ist Pflicht-Latte. K1 Rendite hoeher als A UND als M3,
    K2 Rueckgang nicht groesser als bei A UND bei M3, K3 Verhalten im Band der Rueckrechnung."""
    band_pfad = HIER / "s7_band.json"
    band = json.loads(band_pfad.read_text(encoding="utf-8"))["gruppen"] if band_pfad.exists() else {}
    i0 = m.idx(SIGNALTAG) + 1
    tage = [i for i in range(i0, len(m.datum)) if m.c["BTC"][i] is not None]
    anteil_ueber = sum(bt.btc_ueber_200(m, i) for i in tage) / len(tage) if tage else 1.0
    gruppe = "ueber" if anteil_ueber >= 0.5 else "unter"
    a = stand.get("A_bot_v6", {})
    m3 = stand["messlatten"].get("M3 BTC-200", {})
    out = {"marktlage_gruppe": gruppe, "anteil_tage_btc_ueber_200_pct": round(100 * anteil_ueber, 1)}
    for key, v in stand["instanzen"].items():
        b = band.get(f"{'B K2' if key == 'B' else 'C K1'} | {gruppe}", {})
        inv, rpm = v.get("investiert_mittel_pct"), v.get("runden_je_monat")
        ib, rb = b.get("investiert_pct_band_10_90"), b.get("runden_je_monat_band_10_90")
        k3 = None if None in (inv, rpm) or not ib or not rb else (ib[0] <= inv <= ib[1] and rb[0] <= rpm <= rb[1])
        k1a = None if "rendite_pct" not in a else v["rendite_pct"] > a["rendite_pct"]
        k2a = None if "max_rueckgang_pct" not in a else v["max_rueckgang_pct"] >= a["max_rueckgang_pct"]
        k1m = None if not m3 else v["rendite_pct"] > m3["rendite_pct"]
        k2m = None if not m3 else v["max_rueckgang_pct"] >= m3["max_rueckgang_pct"]
        k1 = None if None in (k1a, k1m) else (k1a and k1m)
        k2 = None if None in (k2a, k2m) else (k2a and k2m)
        out[key] = {"k1_rendite_hoeher_als_A_und_M3": k1, "k2_rueckgang_nicht_groesser_als_A_und_M3": k2,
                    "k3_verhalten_im_band": k3, "band": {"investiert": ib, "runden_je_monat": rb},
                    "alle_drei": None if None in (k1, k2, k3) else (k1 and k2 and k3),
                    "einzeln": {"rendite_gegen_A": k1a, "rendite_gegen_M3": k1m,
                                "rueckgang_gegen_A": k2a, "rueckgang_gegen_M3": k2m},
                    "abbruch_rueckgang_ueber_25": v["max_rueckgang_pct"] < -25}
    return out


def schreibe_csv(pfad: Path, zeilen: list[dict]) -> None:
    with pfad.open("w", newline="", encoding="utf-8") as f:
        if not zeilen:
            f.write("")
            return
        w = csv.DictWriter(f, fieldnames=list(zeilen[0].keys()))
        w.writeheader()
        w.writerows(zeilen)


def wochenbericht(stand: dict) -> str:
    z = [f"[LABOR] Papier-Wettkampf, Stand {stand['letzter_tag']}"]
    for k, v in stand["instanzen"].items():
        z.append(f"{k} {v['name']}: {v['rendite_pct']:+.2f} % | MaxDD {v['max_rueckgang_pct']} % | Sharpe {v.get('sharpe')} | "
                 f"Kosten {v['kosten_usd']} $ ({v.get('kostenanteil_brutto_pct')} % vom Brutto) | Orders {v['orders']} | "
                 f"investiert {v['investiert_pct']} % (Mittel {v.get('investiert_mittel_pct')} %)")
    a = stand.get("A_bot_v6", {})
    if "fehler" in a:
        z.append(f"A Bot v6: FEHLER {a['fehler']}")
    else:
        z.append(f"A Bot v6: {a['rendite_pct']:+.2f} % (Kurve) | MaxDD {a['max_rueckgang_pct']} % | Sharpe {a.get('sharpe')} | "
                 f"Kasse {a['netto_usd']:+.2f} $ aus {a['runden']} Runden | Kosten {a['kosten_usd']} $ ({a.get('kostenanteil_brutto_pct')} % vom Brutto) | "
                 f"investiert Mittel {a.get('investiert_mittel_pct')} %")
        z.append("   Epochen: " + "; ".join(a.get("epochen_seit_start", [])))
    for k, v in stand["messlatten"].items():
        z.append(f"{k}: {v['rendite_pct']:+.2f} % | MaxDD {v['max_rueckgang_pct']} % | Sharpe {v.get('sharpe')}")
    kr = stand.get("kriterien", {})
    if kr:
        z.append(f"Kriterien (Lage-Gruppe {kr['marktlage_gruppe']}, BTC ueber 200 an {kr['anteil_tage_btc_ueber_200_pct']} % der Tage):")
        for k in stand["instanzen"]:
            x = kr.get(k, {})
            e = x.get("einzeln", {})
            z.append(f"   {k}: K1 Rendite > A und M3 {x.get('k1_rendite_hoeher_als_A_und_M3')} (A {e.get('rendite_gegen_A')}, M3 {e.get('rendite_gegen_M3')}) | "
                     f"K2 Rueckgang <= A und M3 {x.get('k2_rueckgang_nicht_groesser_als_A_und_M3')} (A {e.get('rueckgang_gegen_A')}, M3 {e.get('rueckgang_gegen_M3')}) | "
                     f"K3 im Band {x.get('k3_verhalten_im_band')} {x.get('band')} | alle drei {x.get('alle_drei')} | Abbruch >25 %: {x.get('abbruch_rueckgang_ueber_25')}")
    z.append(ausfuehrung_zusammenfassung())
    z.append("Hinweis: vor 3 Monaten ist nichts davon eine Entscheidung (S7).")
    return "\n".join(z)


AUSFUEHRUNG = HIER / "ausfuehrung.csv"
MAX_MIN_NACH_EROEFFNUNG = 180     # nur Messungen bis 3 h nach 00:00 UTC zaehlen


def ausfuehrung_messen(datum: str, journal_pfad: Path = HIER / "B_journal.csv") -> list[dict]:
    """[15.10.2026, Entscheidung E1: Hauptarbeit Trendregel] S7 misst bisher keine echte Ausfuehrung.
    Hier: Bitvavo-Orderbuch (oeffentlich, nur lesen) beim Tageslauf kurz nach der UTC-Eroeffnung.
    Je Coin: halbe Spanne in bp und Kosten der Tagesorder von B (sonst 100 $) ueber das Buch gegen die Mitte.
    Vergleich mit der Annahme KOSTEN_SEITE - 0,05 % Gebuehr. Einmal je UTC-Tag und Coin (erste Messung zaehlt)."""
    import urllib.request
    vorhanden = set()
    if AUSFUEHRUNG.exists():
        with AUSFUEHRUNG.open(encoding="utf-8") as f:
            vorhanden = {(r["datum"], r["coin"]) for r in csv.DictReader(f)}
    order = {}
    if journal_pfad.exists():
        with journal_pfad.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["datum"] == datum:
                    order[r["coin"]] = (r["seite"], float(r["betrag"]))
    jetzt = datetime.now(timezone.utc)
    if (jetzt - jetzt.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() > MAX_MIN_NACH_EROEFFNUNG * 60:
        return []                     # zu weit weg von der Ausfuehrung zur Eroeffnung - keine Messung
    zeilen = []
    for c in UNI6:
        if (datum, c) in vorhanden:
            continue
        try:
            req = urllib.request.Request(f"https://api.bitvavo.com/v2/{c}-USDC/book?depth=50",
                                         headers={"User-Agent": "pruefstand-papier"})
            with urllib.request.urlopen(req, timeout=20) as r:
                buch = json.loads(r.read().decode("utf-8"))
            bids = [(float(p), float(q)) for p, q in buch["bids"]]
            asks = [(float(p), float(q)) for p, q in buch["asks"]]
        except Exception as e:
            zeilen.append({"datum": datum, "coin": c, "zeit_utc": jetzt.isoformat()[:19], "fehler": type(e).__name__})
            continue
        mitte = (bids[0][0] + asks[0][0]) / 2
        seite, betrag = order.get(c, ("KAUF", 100.0))
        stufen = asks if seite == "KAUF" else bids
        rest, wert, menge = betrag, 0.0, 0.0
        for p_, q_ in stufen:
            nimm = min(rest, p_ * q_)
            wert += nimm
            menge += nimm / p_
            rest -= nimm
            if rest <= 1e-9:
                break
        vwap = wert / menge if menge else None
        kosten_bp = None if (vwap is None or rest > 1e-6) else abs(vwap / mitte - 1) * 10000
        zeilen.append({"datum": datum, "coin": c, "zeit_utc": jetzt.isoformat()[:19],
                       "min_nach_eroeffnung": round((jetzt - jetzt.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 60),
                       "halbe_spanne_bp": round((asks[0][0] - bids[0][0]) / mitte * 10000 / 2, 2),
                       "seite": seite, "betrag_usd": round(betrag, 2), "buch_kosten_bp": None if kosten_bp is None else round(kosten_bp, 2),
                       "annahme_bp": round((KOSTEN_SEITE[c] - 0.0005) * 10000, 2), "aus_journal": c in order, "fehler": ""})
    if zeilen:
        felder = ["datum", "coin", "zeit_utc", "min_nach_eroeffnung", "halbe_spanne_bp", "seite", "betrag_usd",
                  "buch_kosten_bp", "annahme_bp", "aus_journal", "fehler"]
        neu = not AUSFUEHRUNG.exists()
        with AUSFUEHRUNG.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=felder)
            if neu:
                w.writeheader()
            w.writerows([{k: z.get(k, "") for k in felder} for z in zeilen])
    return zeilen


def ausfuehrung_zusammenfassung() -> str:
    if not AUSFUEHRUNG.exists():
        return "Ausfuehrung Bitvavo: noch keine Messung"
    with AUSFUEHRUNG.open(encoding="utf-8") as f:
        z = [r for r in csv.DictReader(f) if not r.get("fehler") and r.get("buch_kosten_bp")
             and float(r.get("min_nach_eroeffnung") or 9999) <= MAX_MIN_NACH_EROEFFNUNG]   # 15.10. 10:11 UTC Testlauf zaehlt nicht
    teile = []
    for c in UNI6:
        w = [float(r["buch_kosten_bp"]) for r in z if r["coin"] == c]
        if w:
            a = float([r for r in z if r["coin"] == c][0]["annahme_bp"])
            teile.append(f"{c} {sorted(w)[len(w) // 2]:.1f}/{a:.1f}")
    return "Ausfuehrung Bitvavo (Median Buchkosten / Annahme, bp je Seite ohne Gebuehr): " + (", ".join(teile) or "keine")


def lauf(netz: bool = True, senden: bool = True) -> dict:
    heute_open = daten_aktualisieren(netz)
    alle = list(bt.COINS)
    try:
        stand = rechnen(markt(heute_open))
    finally:
        bt.COINS[:] = alle
    if netz and stand.get("instanzen") and stand.get("laufender_tag_offen"):
        try:
            stand["ausfuehrung_heute"] = ausfuehrung_messen(stand["letzter_tag"])
        except Exception as ex:
            stand["ausfuehrung_heute"] = [{"fehler": f"{type(ex).__name__}: {ex}"[:120]}]
    (HIER / "stand.json").write_text(json.dumps(stand, indent=1, ensure_ascii=False), encoding="utf-8")
    with (HIER / "papier.log").open("a", encoding="utf-8") as f:
        kurz = {k: v.get("rendite_pct") for k, v in stand.get("instanzen", {}).items()}
        f.write(f"{stand['stand_utc']}  letzter Tag {stand['letzter_tag']}  {kurz}  {stand.get('hinweis', '')}\n")
    jetzt = datetime.now(BERLIN)
    zust = HIER / "bericht_zustand.json"
    z = json.loads(zust.read_text(encoding="utf-8")) if zust.exists() else {}
    woche = f"{jetzt.isocalendar().year}-W{jetzt.isocalendar().week}"
    if stand.get("instanzen") and jetzt.weekday() == 0 and z.get("woche") != woche:
        text = wochenbericht(stand)
        (HIER / f"wochenbericht_{jetzt:%Y-%m-%d}.md").write_text(text + "\n", encoding="utf-8")
        if senden:
            import telegram_meldung as tm
            tm.sende(text)
        z["woche"] = woche
        zust.write_text(json.dumps(z), encoding="utf-8")
    return stand


def selbsttest() -> int:
    """1 Determinismus: Wettkampf bis Tag D und bis D+30 - die ersten Tage muessen identisch sein.
    2 Laufender Tag (nur Eroeffnung) macht keinen Fehler und bewertet zur Eroeffnung.
    3 Kosten je Coin: DOGE teurer als BTC.
    4 Kurve A (S7-Nachtrag 1) rueckwaerts im E7-Fenster: an Tagen ohne offene Kaeufe gilt Wert = 500 + Kasse,
      an Tagen mit offenen Kaeufen weicht die Kurve von der reinen Kasse ab, Kasse = runden_lib.
    Schreibt nur in einen Temp-Ordner (A10-Hinweis: frueher wurden die Live-CSV geloescht)."""
    import tempfile
    from runden_lib import lade, runden
    global SIGNALTAG
    fehler = 0
    alle = list(bt.COINS)
    tmp = Path(tempfile.mkdtemp(prefix="papier_selbsttest_"))
    try:
        bt.COINS[:] = UNI6
        bt.DATEN = LABOR / "daten"
        voll = bt.Markt.laden()
        alt, SIGNALTAG = SIGNALTAG, "2026-07-01"
        kurz = bt.Markt(voll.datum[:-40], {k: v[:-40] for k, v in voll.o.items()}, {k: v[:-40] for k, v in voll.c.items()})
        zeilen = lade(V6)
        t1, t2 = tmp / "lang", tmp / "kurz"
        t1.mkdir()
        t2.mkdir()
        b = rechnen(voll, t1, zeilen)
        rechnen(kurz, t2, zeilen)
        ka = list(csv.DictReader((t1 / "B_kurve.csv").open(encoding="utf-8")))
        kb = list(csv.DictReader((t2 / "B_kurve.csv").open(encoding="utf-8")))
        gleich = all(x == y for x, y in zip(kb, ka[:len(kb)])) and len(kb) > 0
        fehler += not gleich
        print(f"  {'OK  ' if gleich else 'FEHL'} Determinismus: {len(kb)} Tage kurzer Lauf = Anfang des langen Laufs (B)")
        ok = all(abs(v.get("kontrolle_usd", 1)) < 1e-6 for v in list(b["instanzen"].values()) + list(b["messlatten"].values()))
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Konto = Summe der Runden in allen Instanzen und Messlatten")
        m2 = bt.Markt(list(voll.datum) + ["2099-01-01"], {k: v + [v[-1] * 1.01] for k, v in voll.o.items()},
                      {k: v + [None] for k, v in voll.c.items()})
        c = rechnen(m2, t1, zeilen)
        ok = c["laufender_tag_offen"] and c["instanzen"]["B"]["tage"] == b["instanzen"]["B"]["tage"] + 1
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} laufender Tag nur mit Eroeffnung: ein Tag mehr, kein Fehler")
        ok = all(k in b["kriterien"].get("B", {}) for k in ("k1_rendite_hoeher_als_A_und_M3", "k3_verhalten_im_band", "einzeln"))
        ok = ok and b["A_bot_v6"].get("sharpe") is not None and b["A_bot_v6"].get("max_rueckgang_pct") is not None
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} A hat Kurve, Rueckgang, Sharpe; Kriterien K1-K3 (gegen A und M3) werden berechnet "
              f"(A seit 01.07.: {b['A_bot_v6'].get('rendite_pct')} %, MaxDD {b['A_bot_v6'].get('max_rueckgang_pct')} %)")
        SIGNALTAG = alt
        ok = KOSTEN_SEITE["DOGE"] > KOSTEN_SEITE["BTC"] > 0.0005
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Kosten je Seite: BTC {KOSTEN_SEITE['BTC'] * 100:.4f} % < DOGE {KOSTEN_SEITE['DOGE'] * 100:.4f} %")
        # 4 Kurve A im E7-Fenster
        ab = "2026-08-13T13:21:19"
        tage, werte, quote, rd = kurve_a(zeilen, voll, ab)
        kasse = []
        for d in tage:
            s = (datetime.fromisoformat(d) + timedelta(days=1)).date().isoformat()
            kasse.append(bt.START_KAPITAL + sum(r["netto"] for r in rd if r["t"] < s))
        leer = [abs(w - k) < 1e-9 for w, k, q in zip(werte, kasse, quote) if q == 0]
        voll_t = [abs(w - k) > 1e-6 for w, k, q in zip(werte, kasse, quote) if q > 0]
        ok = all(leer) and any(voll_t) and len(leer) > 0
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Kurve A: {len(leer)} Tage ohne offene Kaeufe = 500 + Kasse, "
              f"{sum(voll_t)} von {len(voll_t)} Tagen mit offenen Kaeufen bewertet")
        e7 = sum(r["netto"] for r in runden(zeilen, ab, "2026-10-14"))
        ok = abs(e7 - (-34.11)) < 0.01
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} runden_lib E7 (Verkauf 13.08. 13:21 bis 13.10.) netto {e7:+.2f} $ = -34,11 $")
    finally:
        bt.COINS[:] = alle
        SIGNALTAG = "2026-10-14"
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER", f"(Temp-Ordner {tmp})")
    return fehler


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    s = lauf(senden="--zeigen" not in sys.argv)
    if "--zeigen" in sys.argv:
        print(json.dumps({k: v for k, v in s.items() if k != "instanzen"}, indent=1, ensure_ascii=False)[:1500])
        for k, v in s.get("instanzen", {}).items():
            print(k, v)
