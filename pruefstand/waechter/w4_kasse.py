# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W4 Kasse (MASTERPROMPT_AGENTEN.md 6.1) - alle 5 Minuten, ohne KI, nur lesend auf die Bots.

ANLASS: Die Kaufgebuehr wurde in v6 monatelang doppelt gebucht (Befund 42, 54,78 $ in E7),
das Cockpit zeigte -88,89 $ statt -34,11 $; eine Auswertung zog die Verkaufsgebuehr doppelt ab.
Zahlen muessen auf mehreren Wegen uebereinstimmen, sonst gilt keine (Masterprompt 5.4).

Pruefungen je Instanz:
  saldo        USDC-Konto: Veraenderung seit Startpunkt == Summe der Journal-Geldfluesse
               (Kauf -Abfluss, Verkauf +Erloes-Gebuehr) + Sparplan-Kaeufe (btc_accumulator). Toleranz 0,05 $.
  bestand      jede offene Position == Muenzbestand im Papierkonto (2 % Toleranz wie features/waechter.py)
  orders       gefuellte Orders der Order-Historie (seit Startpunkt) <-> Journal: gleiche Muenze, Seite,
               Menge, Gebuehr (0,01 $), Zeit (120 s) - in beide Richtungen
  gebucht      Runden mit Kauf nach dem Gebuehren-Fix (v6 E9, v7 immer): gebuchtes pnl == Kasse (0,01 $)
  pflichtfelder Verkaeufe seit Epoche E10/L9: fehlende Felder (Befund 88, bekannt -> GELB)
  plausibel    doppelte _id, Zeit nicht steigend, negatives Konto
  konto        eigene Kontokurve stuendlich: USDC + Positionen zum Marktpreis, Sparplan-BTC GETRENNT
               [15.10.2026] Fehlt ein noetiger Marktpreis (Internetausfall 14./15.10.: sparplan_btc_wert 10 h
               lang 0 statt ~166 $), wird keine Zeile mit 0 geschrieben, sondern GELB "nicht berechenbar"
               gemeldet und im naechsten Lauf (5 min) neu versucht. Takt je Instanz.
Eine Abweichung wird erst nach ZWEI Laeufen hintereinander ROT (der Bot schreibt Journal und
Zustand nicht im selben Augenblick). JSON wird als Kopie gelesen und bei halbem Schreibzustand wiederholt.
Aufrufe: pythonw w4_kasse.py | python w4_kasse.py --zeigen | --selbsttest
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(P / "skripte"))
import telegram_meldung as tm  # noqa: E402

DB = P / "waechter.db"
STATUS = P / "status.json"
ZUSTAND = HIER / "w4_zustand.json"
FIX_AB = {"v6": "2026-10-14T09:35:46", "v7": "2026-09-11T00:00:00"}       # Befund 42 behoben
EPOCHE = {"v6": "2026-10-14T13:58:25", "v7": "2026-10-14T13:59:20"}       # E10 / L9
# [15.10.2026] Befund 88 behoben mit v6 E12 / v7 L11: Pflichtfelder erst ab dort pruefen. Fehlt ein Feld,
# obwohl ein Kauf in derselben Runde lag, ist das ein neuer Fehler (GELB); ohne Kauf in der Runde nur Hinweis.
# [19.10.2026] v7 L14: Der bediente Warte-Auftrag verlor stop_initial/trailing_stop_pct schon am KAUF (alle 22 v7-Kaeufe
# bis L14). Pruefen erst ab L14 und nur Verkaeufe, deren Kauf (felder_aus_kauf.kauf_zeit) ab L14 liegt; aeltere
# Kaeufe sind nicht nachtragbar und zaehlen nur als Hinweis (sonst bliebe W4 v7 fuer immer GELB).
PFLICHT_AB = {"v6": "2026-10-15T09:35:57", "v7": "2026-10-19T21:00:50"}  # E12 / L14-Patch (keine Epoche)
PFLICHT_NAME = {"v6": "E12", "v7": "L14-Patch 19.10."}
KAUF_AB = {"v7": "2026-10-19T21:00:50"}                                   # nur v7 (Warte-Auftraege)
PFLICHT = ["fee", "mfe_pct", "mae_pct", "stop_initial", "trailing_stop_pct", "decision_id", "signal_score",
           "signal_reasons", "active_strategy", "market_regime", "fear_greed_at_entry"]
STUFE = {"GRUEN": 0, "GELB": 1, "ROT": 2}


def lies_json(pfad: Path, versuche: int = 5):
    for v in range(versuche):
        try:
            return json.loads(pfad.read_bytes().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            time.sleep(1.0 + v)
    raise RuntimeError(f"{pfad.name} nach {versuche} Versuchen nicht lesbar")


def zeit_s(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    return datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp()


def geldfluss(r: dict) -> float:
    """Wirkung einer Journal-Zeile auf das USDC-Konto."""
    qty, preis, fee, amt = float(r["qty"]), float(r["price"]), float(r.get("fee") or 0), float(r.get("amount") or 0)
    nominal = qty * preis
    if str(r["type"]).upper() == "BUY":
        ohne = abs(amt - nominal) <= max(0.01, fee * 0.2)          # amount ohne Gebuehr (seit Fix)
        return -(amt + fee) if ohne else -amt
    ist_netto = abs(amt - (nominal - fee)) <= 0.01 and abs(amt - nominal) > 0.01
    return (amt if ist_netto else amt - fee) if amt > 0 else nominal - fee


def preise() -> dict:
    out = {}
    for c in ("BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"):
        try:
            with urllib.request.urlopen(f"https://api.binance.com/api/v3/ticker/price?symbol={c}USDC", timeout=15) as r:
                out[c] = float(json.loads(r.read())["price"])
        except Exception:
            pass
    return out


def kontozeile(usdc: float, pos: dict, acc: dict, pr: dict) -> tuple[dict | None, list[str]]:
    """Werte fuer die Kontokurve oder (None, fehlende Preise). Ein fehlender Preis wird nie als 0 bewertet."""
    spar_btc = float(acc.get("total_btc") or 0)
    noetig = {s.split("/")[0] for s, p in pos.items() if float(p.get("qty") or 0) > 0}
    if spar_btc > 0:
        noetig.add("BTC")
    fehlt = sorted(c for c in noetig if not pr.get(c))
    if fehlt:
        return None, fehlt
    posw = sum(float(p.get("qty") or 0) * pr.get(s.split("/")[0], 0) for s, p in pos.items())
    return {"usdc": round(usdc, 4), "positionen": round(posw, 4), "handel_gesamt": round(usdc + posw, 4),
            "sparplan_btc_wert": round(spar_btc * pr.get("BTC", 0), 4),
            "sparplan_investiert": round(float(acc.get("total_invested_usd") or 0), 4)}, []


def pflicht_ampel(vk: list[dict], kauf_ab: str | None, seit: str) -> tuple[str, str]:
    """Pflichtfelder der Verkaeufe. Ein Verkauf, dessen Kauf vor kauf_ab lag, ist nicht nachtragbar (nur Hinweis).
    Fehlt die Kaufzeit, wird der Verkauf normal geprueft - so versteckt der Filter keinen neuen Fehler."""
    mit_kauf = [r for r in vk if r.get("felder_aus_kauf") or r.get("decision_id")]
    alt = []
    if kauf_ab:
        alt = [r for r in mit_kauf if (r.get("felder_aus_kauf") or {}).get("kauf_zeit")
               and str(r["felder_aus_kauf"]["kauf_zeit"]) < kauf_ab]
        mit_kauf = [r for r in mit_kauf if r not in alt]
    fehlt = {f: sum(1 for r in mit_kauf if r.get(f) in (None, "", [])) for f in PFLICHT}
    fehlt = {f: n for f, n in fehlt.items() if n}
    ohne = len(vk) - len(mit_kauf) - len(alt)
    return ("GELB" if fehlt else "GRUEN",
            f"{len(vk)} Verkaeufe seit {seit}" + (f", fehlend: {fehlt}" if fehlt else ", vollstaendig")
            + (f", {len(alt)} mit Kauf vor {seit} (nicht nachtragbar)" if alt else "")
            + (f", {ohne} ohne Kauf in der Runde (nicht nachtragbar)" if ohne else ""))


def pruefe(name: str, inst: dict, z: dict, mit_konto: bool) -> list[tuple]:
    from runden_lib import runden
    ds = Path(inst["pfad"]) / "data_store"
    st = lies_json(ds / "bot_state.json")
    journal = lies_json(ds / "trades_v5.json")
    acc = lies_json(ds / "btc_accumulator.json") if (ds / "btc_accumulator.json").exists() else {"buy_history": []}
    orders = lies_json(ds / "order_history.json") if (ds / "order_history.json").exists() else []
    bal = st.get("paper_balances_backup") or {}
    usdc = float(bal.get("USDC", 0))
    pos = st.get("open_positions_backup") or {}
    out = []
    jetzt = time.time()
    # Startpunkt beim ersten Lauf
    sp = z.setdefault(f"{name}_start", {"zeit": jetzt, "usdc": usdc,
                                        "journal_ids": [r.get("_id") for r in journal[-50:]],
                                        "spar": len(acc.get("buy_history", []))})
    # saldo
    neu = [r for r in journal if zeit_s(r["time"]) > sp["zeit"]]
    fluss = sum(geldfluss(r) for r in neu)
    spar = sum(-float(b.get("usd_spent", 0)) for b in acc.get("buy_history", [])[sp["spar"]:])
    soll = sp["usdc"] + fluss + spar
    abw = usdc - soll
    out.append((name, "saldo", "GRUEN" if abs(abw) <= 0.05 else "ROT?",
                f"USDC {usdc:.2f} $, erwartet {soll:.2f} $ (Start {sp['usdc']:.2f} + {len(neu)} Buchungen {fluss:+.2f} + Sparplan {spar:+.2f}), "
                f"Abweichung {abw:+.3f} $"))
    # bestand
    falsch = []
    for sym, p in pos.items():
        coin = sym.split("/")[0]
        q, b = float(p.get("qty") or 0), float(bal.get(coin, 0))
        if q > 0 and not (q / 1.02 <= b <= q * 1.02):
            falsch.append(f"{coin}: Position {q:.6f}, Konto {b:.6f}")
    geister = [f"{c}: {v:.6f}" for c, v in bal.items() if c != "USDC" and v > 1e-9 and f"{c}/USDC" not in pos]
    out.append((name, "bestand", "ROT?" if falsch else ("GELB" if geister else "GRUEN"),
                "; ".join(falsch) if falsch else (f"Bestand ohne Position: {geister}" if geister else f"{len(pos)} Position(en) = Konto")))
    # orders <-> journal
    gefuellt = [o for o in orders if o.get("status") == "filled" and float(o.get("created_at") or 0) > sp["zeit"]]
    ohne_journal, ohne_order = [], []
    for o in gefuellt:
        treffer = [r for r in neu if r["coin"] == o["symbol"] and str(r["type"]).upper() == o["side"]
                   and abs(float(r["qty"]) - float(o.get("fill_qty") or 0)) <= 1e-8 * max(1, float(r["qty"]))
                   and abs(zeit_s(r["time"]) - float(o["created_at"])) <= 120]
        if not treffer:
            ohne_journal.append(f"{o['side']} {o['symbol']} {o.get('fill_qty')}")
        elif abs(float(treffer[0].get("fee") or 0) - float(o.get("fee") or 0)) > 0.01:
            ohne_journal.append(f"Gebuehr {o['symbol']}: Order {o.get('fee')} / Journal {treffer[0].get('fee')}")
    for r in neu:
        if not any(o["symbol"] == r["coin"] and o["side"] == str(r["type"]).upper()
                   and abs(zeit_s(r["time"]) - float(o["created_at"])) <= 120 for o in gefuellt):
            ohne_order.append(f"{r['type']} {r['coin']} {r['time'][:19]}")
    out.append((name, "orders", "ROT?" if (ohne_journal or ohne_order) else "GRUEN",
                f"{len(gefuellt)} Orders / {len(neu)} Journalzeilen seit Start"
                + (f" | ohne Journal: {ohne_journal[:3]}" if ohne_journal else "") + (f" | ohne Order: {ohne_order[:3]}" if ohne_order else "")))
    # gebucht vs Kasse
    rd = [r for r in runden(sorted(journal, key=lambda x: x["time"]), FIX_AB[name]) if r["kauf_t"] >= FIX_AB[name] and r["gebucht"] is not None]
    schief = [f"{r['t'][:16]} {r['coin']}: gebucht {r['gebucht']:+.3f} / Kasse {r['netto']:+.3f}" for r in rd if abs(r["gebucht"] - r["netto"]) > 0.01]
    out.append((name, "gebucht_vs_kasse", "ROT?" if schief else "GRUEN",
                f"{len(rd)} Runden nach Gebuehren-Fix" + (f", abweichend: {schief[:3]}" if schief else ", alle gleich")))
    # pflichtfelder
    vk = [r for r in journal if str(r["type"]).upper() == "SELL" and r["time"] >= PFLICHT_AB[name]]
    out.append((name, "pflichtfelder", *pflicht_ampel(vk, KAUF_AB.get(name), PFLICHT_NAME[name])))
    # plausibel
    ids = [r.get("_id") for r in journal if r.get("_id") is not None]
    doppelt = len(ids) - len(set(ids))
    zeiten = [r["time"] for r in journal[-200:]]
    rueck = sum(1 for a, b in zip(zeiten, zeiten[1:]) if b < a)
    neg = [c for c, v in bal.items() if v < -1e-9]
    out.append((name, "plausibel", "ROT?" if (doppelt or neg) else ("GELB" if rueck else "GRUEN"),
                f"doppelte _id {doppelt}, Zeit rueckwaerts {rueck} (letzte 200), negativ {neg}"))
    # eigene Kontokurve (stuendlich je Instanz; nach fehlendem Preis im naechsten Lauf erneut)
    zuletzt = z.get(f"{name}_konto_zuletzt", z.get("konto_zuletzt", 0))
    if mit_konto and jetzt - zuletzt >= 3300:
        k, fehlt_pr = kontozeile(usdc, pos, acc, preise())
        if k is None:
            out.append((name, "konto", "GELB",
                        f"nicht berechenbar: kein Marktpreis fuer {', '.join(fehlt_pr)} (Binance) - Kontozeile ausgelassen "
                        f"statt mit 0 bewertet, letzte Zeile " + (f"vor {(jetzt - zuletzt) / 60:.0f} min" if zuletzt else "noch keine")
                        + ", neuer Versuch in 5 min"))
        else:
            con = sqlite3.connect(DB, timeout=30)
            con.execute("INSERT INTO konto VALUES (?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), name, k["usdc"],
                        k["positionen"], k["handel_gesamt"], k["sparplan_btc_wert"], k["sparplan_investiert"]))
            con.commit()
            con.close()
            z[f"{name}_konto_zuletzt"] = jetzt
            out.append((name, "konto", "GRUEN", f"Kontozeile geschrieben: Handel {k['handel_gesamt']:.2f} $, "
                        f"Sparplan-BTC {k['sparplan_btc_wert']:.2f} $"))
    else:
        out.append((name, "konto", "GRUEN", f"letzte Kontozeile vor {(jetzt - zuletzt) / 60:.0f} min"))
    return out


def lauf(senden: bool = True) -> list[tuple]:
    jetzt = datetime.now(timezone.utc)
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    z = json.loads(ZUSTAND.read_text(encoding="utf-8")) if ZUSTAND.exists() else {}
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS kasse (ts_utc TEXT, instanz TEXT, pruefung TEXT, ampel TEXT, befund TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS konto (ts_utc TEXT, instanz TEXT, usdc REAL, positionen REAL, handel_gesamt REAL, "
                "sparplan_btc_wert REAL, sparplan_investiert REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS ereignisse (ts_utc TEXT, waechter TEXT, instanz TEXT, pruefung TEXT, "
                "von TEXT, nach TEXT, befund TEXT)")
    con.commit()
    con.close()
    erg = []
    for name, i in inst.items():
        try:
            erg += pruefe(name, i, z, True)
        except Exception as e:
            erg.append((name, "w4_fehler", "GELB", f"{type(e).__name__}: {str(e)[:150]}"))
    # ROT? -> erst beim zweiten Lauf in Folge ROT
    endg = []
    for a, b, c, d in erg:
        key = f"{a}|{b}"
        if c == "ROT?":
            c = "ROT" if z.get("verdacht", {}).get(key) else "GELB"
            z.setdefault("verdacht", {})[key] = True
            d += " (zweiter Lauf in Folge)" if c == "ROT" else " (Verdacht, wird im naechsten Lauf bestaetigt)"
        else:
            z.setdefault("verdacht", {}).pop(key, None)
        endg.append((a, b, c, d))
    con = sqlite3.connect(DB, timeout=30)
    con.executemany("INSERT INTO kasse VALUES (?,?,?,?,?)", [(jetzt.isoformat(), *e) for e in endg])
    alt = z.get("ampeln", {})
    meldungen = []
    for a, b, c, d in endg:
        vorher = alt.get(f"{a}|{b}", "GRUEN")
        if c != vorher:
            con.execute("INSERT INTO ereignisse VALUES (?,?,?,?,?,?,?)", (jetzt.isoformat(), "W4", a, b, vorher, c, d))
            if c == "ROT" or (vorher == "ROT" and c == "GRUEN"):
                meldungen.append((f"W4-{a}|{b}-{c}", f"[WAECHTER][{'HOCH' if c == 'ROT' else 'INFO'}] W4 {a} {b}: {d}"))
    con.commit()
    con.close()
    z["ampeln"] = {f"{a}|{b}": c for a, b, c, _ in endg}
    ZUSTAND.write_text(json.dumps(z, indent=1), encoding="utf-8")
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    gesamt = max((STUFE[c] for _, _, c, _ in endg), default=0)
    status["W4"] = {"ampel": [k for k, v in STUFE.items() if v == gesamt][0], "stand_utc": jetzt.isoformat(),
                    "pruefungen": [{"instanz": a, "pruefung": b, "ampel": c, "befund": d} for a, b, c, d in endg]}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False), encoding="utf-8")
    if senden:
        for s, t in meldungen:
            tm.sende(t, schluessel=s)
    return endg


def selbsttest() -> int:
    fehler = 0
    # Kauf alt (amount mit Gebuehr), Kauf neu (ohne), Verkauf brutto (exit_monitor), Verkauf netto (Signalweg)
    faelle = [
        # v6 bis E9: qty = (amount - fee) / Kurs, amount enthaelt die Gebuehr
        ({"type": "BUY", "qty": 0.0009975, "price": 100000, "fee": 0.25, "amount": 100.0}, -100.0, "Kauf, amount MIT Gebuehr (v6 bis E9)"),
        ({"type": "BUY", "qty": 0.001, "price": 100000, "fee": 0.05, "amount": 100.0}, -100.05, "Kauf, amount OHNE Gebuehr (seit Fix)"),
        ({"type": "SELL", "qty": 0.001, "price": 101000, "fee": 0.0505, "amount": 101.0}, 100.9495, "Verkauf brutto (exit_monitor)"),
        ({"type": "SELL", "qty": 0.001, "price": 101000, "fee": 0.0505, "amount": 100.9495}, 100.9495, "Verkauf netto (Signalweg)"),
    ]
    for r, soll, text in faelle:
        ist = geldfluss(r)
        ok = abs(ist - soll) < 1e-6
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} {text}: {ist:+.4f} (soll {soll:+.4f})")
    # Kontokurve [15.10.2026]: fehlender Preis darf nie als 0 bewertet werden
    acc = {"total_btc": 0.00204534, "total_invested_usd": 136.51}
    pos = {"BTC/USDC": {"qty": 0.0027474431}}
    k, fehlt = kontozeile(11.7442, pos, acc, {})                              # Internetausfall: keine Preise
    ok = k is None and fehlt == ["BTC"]
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion Netz weg: {k}, fehlt {fehlt} (frueher Sparplan 0,00 $)")
    k, fehlt = kontozeile(11.7442, pos, acc, {"BTC": 81000.0})
    ok = (k is not None and not fehlt and abs(k["sparplan_btc_wert"] - 165.6725) < 1e-3
          and abs(k["positionen"] - 222.5429) < 1e-3 and abs(k["handel_gesamt"] - 234.2871) < 1e-3)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: {k}")
    k0, f0 = kontozeile(408.14, {}, {"total_btc": 0}, {})                       # nichts zu bewerten -> 0 ist echt
    k1, f1 = kontozeile(100.0, {"ETH/USDC": {"qty": 0.05}}, acc, {"BTC": 81000.0})  # nur ETH fehlt
    ok = k0 is not None and k0["sparplan_btc_wert"] == 0 and k0["handel_gesamt"] == 408.14 and k1 is None and f1 == ["ETH"]
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: ohne Sparplan/Position {k0}; nur ETH fehlt -> {k1}, {f1}")
    # Pflichtfelder v7 ab L14 [19.10.2026]
    voll = {f: 1 for f in PFLICHT}
    l14 = "2026-10-19T21:00:50"
    alt_vk = {**voll, "stop_initial": None, "trailing_stop_pct": None,
              "felder_aus_kauf": {"kauf_zeit": "2026-10-17T05:35:28.1+00:00"}}         # offene Position von vor L14
    a, t = pflicht_ampel([alt_vk], l14, "L14")
    a_vorher, _ = pflicht_ampel([alt_vk], None, "L14")
    ok = a_vorher == "GELB" and a == "GRUEN" and "1 mit Kauf vor L14" in t
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion Altkauf vor L14: vorher {a_vorher}, jetzt {a} ({t})")
    neu_voll = {**voll, "felder_aus_kauf": {"kauf_zeit": "2026-10-20T08:00:00+00:00"}}
    a1, t1 = pflicht_ampel([neu_voll], l14, "L14")
    a2, _ = pflicht_ampel([{**voll, "stop_initial": None, "decision_id": "x"}], None, "E12")   # v6 unveraendert scharf
    ok = a1 == "GRUEN" and "vollstaendig" in t1 and a2 == "GELB"
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: Neukauf vollstaendig -> {a1}; v6 Feld fehlt -> {a2}")
    grenz = {**voll, "stop_initial": None, "felder_aus_kauf": {"kauf_zeit": l14}}      # Kauf genau zum Start
    ohne_zeit = {**voll, "trailing_stop_pct": None, "decision_id": "y", "felder_aus_kauf": {}}  # Kaufzeit fehlt
    a3, t3 = pflicht_ampel([grenz], l14, "L14")
    a4, t4 = pflicht_ampel([ohne_zeit], l14, "L14")
    ok = a3 == "GELB" and "stop_initial" in t3 and a4 == "GELB" and "trailing_stop_pct" in t4
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: Kauf genau am Start ohne Feld -> {a3}; Kaufzeit fehlt -> {a4} (nicht versteckt)")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return fehler


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    e = lauf(senden="--zeigen" not in sys.argv)
    if "--zeigen" in sys.argv:
        for a, b, c, d in e:
            print(f"{c:5s} {a:4s} {b:18s} {d}")
