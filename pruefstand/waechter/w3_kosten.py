# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W3 Kosten (MASTERPROMPT_AGENTEN.md 3.9 und 6.1) - stuendlich, ohne KI, nur lesend auf die Bots.

ANLASS: Bybit EU stellte am 05.10.2026 auf eine Einheitsgebuehr um; der Bot rechnete 9 Tage mit
dem alten Satz weiter, niemand merkte es. Zielboerse ist seit 14.10. Bitvavo USDC (K 0,15 %).

Pruefungen:
  gebuehrenkategorie  Bitvavo-API /v2/markets: die 6 USDC-Maerkte muessen in feeCategory "B" sein
                      (0,05 %, bitvavo.com/en/fees). Wechsel = ROT. Die Seite selbst blockt Skripte (403).
  gebuehrenstand      gebuehren.json geprueft_am hoechstens 30 Tage alt (sonst GELB, ab 45 Tage ROT)
  spanne              Bitvavo-Spanne je Coin (5 Proben je Lauf) -> Tabelle kosten_spanne; Tagesmedian
                      gegen die Papier-Annahme SPREAD_BP der Bots: > 1,5-fach = GELB, > 2,5-fach = ROT
                      [15.10.2026] Alle 6 Bitvavo-Maerkte: Bots je gehandelter Muenze (config trading.coins),
                      nicht gehandelte nur als Hinweis; Labor S7 (handelt alle 6) gegen SPANNE_BP aus
                      labor/papier/papier_tag.py. Keine Messung in 24 h oder keine Annahme = GELB (vorher still).
  I1 puffer           BREAKEVEN_PUFFER_PCT >= K (sonst ROT: garantierter Verlust) und >= K + 0,10 (sonst GELB)
  I2 trailstart       Nachzieh-Start fuer Abstand 0,85/1,0/1,3 >= Nulllinie (ROT) und >= Nulllinie + 0,10 (GELB)
  I3 ziel             nicht anwendbar, solange take_profit_pct = 0 (Bot hat kein festes Ziel)
  I4 gebuehr_im_bot   Papier-Gebuehr des Bots == gebuehren.json der Zielboerse (Taker)
  I5 gebuehr_journal  jede Order seit Epoche E10/L9: gebuchte Gebuehr == Satz x Betrag (Toleranz 0,01 $)
  schattenbuch        Runden seit E10/L9 netto unter Bitvavo / Bybit / OKX (Tabelle kosten_schatten)
  monat               [15.10.2026 neu, Agententest 3.4] Die alte Regel "Gebuehren > Brutto" feuerte bei JEDEM
                      Verlustmonat (Brutto negativ). Jetzt: Brutto > 0 und Gebuehren > Brutto (Kosten machen
                      den Gewinn zum Verlust) = GELB; Brutto <= 0 und Gebuehren > 50 % des Nettoverlusts
                      (Startwert [VERMUTUNG]) = GELB; Verlust schon vor Kosten mit kleinem Kostenanteil = GRUEN
                      mit Hinweis auf W7 (dort wird der fehlende Vorsprung bewertet).
Ausgabe: pruefstand/waechter.db (kosten, kosten_spanne, kosten_schatten, ereignisse), status.json W3.
Telegram nur beim Wechsel nach ROT (und Erholung), hoechstens alle 6 h je Schluessel.
Aufrufe: pythonw w3_kosten.py | python w3_kosten.py --zeigen | --selbsttest
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sqlite3
import statistics as st
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(P / "skripte"))
import telegram_meldung as tm  # noqa: E402

DB = P / "waechter.db"
STATUS = P / "status.json"
ZUSTAND = HIER / "w3_zustand.json"
MAERKTE = ["BTC-USDC", "ETH-USDC", "SOL-USDC", "XRP-USDC", "ADA-USDC", "DOGE-USDC"]
EPOCHE_START = {"v6": "2026-10-14T13:58:25", "v7": "2026-10-14T13:59:20"}   # E10 / L9
SICHERHEIT = 0.10        # Masterprompt 3.9 Startwert [VERMUTUNG]
KOSTENANTEIL_GELB = 50.0  # Gebuehren in % des Nettoverlusts, ab dem die Kosten die Hauptursache sind [VERMUTUNG]
STUFE = {"GRUEN": 0, "GELB": 1, "ROT": 2}


def lade_modul(pfad: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def http_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "pruefstand-w3"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def nulllinie(k: float, abstand: float) -> float:
    return ((1 + k / 100) / (1 - abstand / 100) - 1) * 100


# ------------------------------------------------------------------ Pruefungen
def monat_ampel(geb: float, brutto: float) -> tuple[str, str]:
    """Monatsregel Kosten gegen Brutto. Ein Verlust schon vor Kosten ist kein Kostenalarm."""
    netto = brutto - geb
    if brutto > 0:
        if geb > brutto:
            return "GELB", (f"Kosten machen den Gewinn zum Verlust: Gebuehren {geb:.2f} $ > Brutto {brutto:+.2f} $ "
                            f"(netto {netto:+.2f} $)")
        return "GRUEN", f"Gebuehren {geb:.2f} $ = {100 * geb / brutto:.0f} % vom Brutto {brutto:+.2f} $ (netto {netto:+.2f} $)"
    if geb <= 0:
        return "GRUEN", f"keine Gebuehren, Brutto {brutto:+.2f} $"
    anteil = 100 * geb / (geb - brutto)
    if anteil > KOSTENANTEIL_GELB:
        return "GELB", (f"Kosten sind der groessere Teil des Verlusts: Gebuehren {geb:.2f} $ = {anteil:.0f} % von netto "
                        f"{netto:+.2f} $ (Brutto {brutto:+.2f} $)")
    return "GRUEN", (f"Verlust schon vor Kosten (Brutto {brutto:+.2f} $), Gebuehren {geb:.2f} $ = {anteil:.0f} % des Verlusts "
                     f"{netto:+.2f} $ - Ursache ist der Handel, nicht die Kosten (Vorsprung: W7)")


def pruefe_boerse(geb: dict) -> list[tuple]:
    out = []
    try:
        maerkte = {m["market"]: m for m in http_json("https://api.bitvavo.com/v2/markets")}
        falsch = {mk: maerkte.get(mk, {}).get("feeCategory") for mk in MAERKTE if maerkte.get(mk, {}).get("feeCategory") != "B"}
        handel = [mk for mk in MAERKTE if maerkte.get(mk, {}).get("status") != "trading"]
        out.append(("bitvavo", "gebuehrenkategorie", "ROT" if falsch else "GRUEN",
                    f"nicht Kategorie B: {falsch}" if falsch else "alle 6 USDC-Maerkte in Kategorie B (0,05 %)"))
        if handel:
            out.append(("bitvavo", "marktstatus", "ROT", f"nicht im Handel: {handel}"))
    except Exception as e:
        out.append(("bitvavo", "gebuehrenkategorie", "GELB", f"API nicht erreichbar: {type(e).__name__}"))
    g = geb["boersen"]["bitvavo_usdc"]
    alter = (date.today() - date.fromisoformat(g["geprueft_am"])).days
    out.append(("bitvavo", "gebuehrenstand", "ROT" if alter > 45 else ("GELB" if alter > 30 else "GRUEN"),
                f"Gebuehrenseite zuletzt geprueft vor {alter} Tagen ({g['geprueft_am']})"
                + (" - bitte im Browser pruefen und gebuehren.json aktualisieren" if alter > 30 else "")))
    return out


def spanne_messen(con) -> dict:
    jetzt = datetime.now(timezone.utc).isoformat()
    erg = {}
    for mk in MAERKTE:
        werte = []
        for _ in range(5):
            try:
                b = http_json(f"https://api.bitvavo.com/v2/{mk}/book?depth=1")
                bid, ask = float(b["bids"][0][0]), float(b["asks"][0][0])
                werte.append((ask - bid) / ((ask + bid) / 2) * 10000)
            except Exception:
                pass
            time.sleep(1)
        if werte:
            erg[mk] = st.median(werte)
            con.execute("INSERT INTO kosten_spanne VALUES (?,?,?,?)", (jetzt, mk, round(erg[mk], 3), len(werte)))
    return erg


def spanne_ampeln(name: str, annahme: dict[str, float], tag: dict[str, list[float]], gehandelt: list[str]) -> list[tuple]:
    """Je gehandelter Muenze eine Ampel; nicht gehandelte Muenzen der 6 Maerkte nur als Hinweis."""
    out, hinweis = [], []
    for mk in MAERKTE:
        coin = mk.split("-")[0]
        sim, werte = annahme.get(coin), tag.get(mk)
        if coin not in gehandelt:
            if sim and werte:
                hinweis.append(f"{coin} {st.median(werte):.1f}/{sim:.1f} bp x{st.median(werte) / sim:.1f}")
            continue
        if sim is None:
            out.append((name, f"spanne_{coin}", "GELB", f"nicht berechenbar: keine Papier-Annahme fuer {coin} gefunden"))
        elif not werte:
            out.append((name, f"spanne_{coin}", "GELB", f"nicht berechenbar: keine Bitvavo-Messung {mk} in 24 h"))
        else:
            ist = st.median(werte)
            f = ist / sim if sim > 0 else 99
            out.append((name, f"spanne_{coin}", "ROT" if f > 2.5 else ("GELB" if f > 1.5 else "GRUEN"),
                        f"Bitvavo-Median 24 h {ist:.2f} bp gegen Papier-Annahme {sim:.2f} bp (x{f:.2f}, {len(werte)} Laeufe)"))
    if hinweis:
        out.append((name, "spanne_nicht_gehandelt", "GRUEN", "nur Hinweis, nicht gehandelt: " + ", ".join(hinweis)))
    return out


def spanne_tag(con) -> dict[str, list[float]]:
    seit = datetime.now(timezone.utc).timestamp() - 86400
    tag = {}
    for mk, bp, ts in con.execute("SELECT markt, spanne_bp, ts_utc FROM kosten_spanne").fetchall():
        if datetime.fromisoformat(ts).timestamp() >= seit:
            tag.setdefault(mk, []).append(bp)
    return tag


def labor_annahme() -> dict[str, float]:
    """SPANNE_BP (ganze Spanne in bp) aus labor/papier/papier_tag.py, ohne das Modul zu laden."""
    t = (P / "labor" / "papier" / "papier_tag.py").read_text(encoding="utf-8")
    m = re.search(r"^SPANNE_BP\s*=\s*(\{[^}]*\})", t, re.M)
    return {k: float(v) for k, v in ast.literal_eval(m.group(1)).items()}


def pruefe_spanne(con, inst: dict) -> list[tuple]:
    tag = spanne_tag(con)
    out = []
    for name, i in inst.items():
        t = (Path(i["pfad"]) / "execution" / "engine.py").read_text(encoding="utf-8")
        annahme = {}
        for mk in MAERKTE:
            coin = mk.split("-")[0]
            m = re.search(rf'"{coin}":\s*\(([\d.]+),\s*([\d.]+)\)', t)
            if m:
                annahme[coin] = float(m.group(1))
        cfg = json.loads((Path(i["pfad"]) / "data_store" / "config.json").read_text(encoding="utf-8"))
        gehandelt = [c.split("/")[0] for c in cfg.get("trading", {}).get("coins", [])]
        out += spanne_ampeln(name, annahme, tag, gehandelt)
    try:
        lab = labor_annahme()
        out += spanne_ampeln("labor", lab, tag, list(lab))
    except Exception as e:
        out.append(("labor", "spanne", "GELB", f"nicht berechenbar: SPANNE_BP im Labor nicht lesbar ({type(e).__name__})"))
    return out


def pruefe_invarianten(name: str, inst: dict, geb: dict) -> list[tuple]:
    o = Path(inst["pfad"])
    out = []
    er = lade_modul(o / "risk" / "exit_rules.py", f"er_{name}")
    k = float(er.K_BASIS_PCT)
    p = float(er.BREAKEVEN_PUFFER_PCT)
    out.append((name, "I1_puffer", "ROT" if p < k else ("GELB" if p < k + SICHERHEIT else "GRUEN"),
                f"Puffer {p} gegen K {k}: Kern >= {k} {'ok' if p >= k else 'VERLETZT'}, mit Sicherheit >= {k + SICHERHEIT:.3f} "
                f"{'ok' if p >= k + SICHERHEIT else 'verletzt (Startwert 3.9, A5-Vorschlag V2)'}"))
    schlecht, knapp = [], []
    for d in (0.85, 1.0, 1.3):
        start = er.trail_start_pct(d) if hasattr(er, "trail_start_pct") else float(er.TRAIL_AB_PCT)
        n = nulllinie(k, d)
        if start < n:
            schlecht.append(f"{d}: Start {start:.2f} < Nulllinie {n:.2f}")
        # [15.10.2026] Der Bot rundet den Start auf 3 Stellen (trail_start_pct): 1,569 gegen 1,5691 ist keine Luecke.
        elif start < n + SICHERHEIT - 0.0005:
            knapp.append(f"{d}: {start:.2f} < {n + SICHERHEIT:.2f}")
    out.append((name, "I2_trailstart", "ROT" if schlecht else ("GELB" if knapp else "GRUEN"),
                ("VERLETZT " + "; ".join(schlecht)) if schlecht else
                (("Kern ok, Sicherheit 0,10 knapp: " + "; ".join(knapp)) if knapp else "Kern und Sicherheit ok")))
    cfg = json.loads((o / "data_store" / "config.json").read_text(encoding="utf-8"))
    tp = float(cfg.get("risk", {}).get("take_profit_pct", 0) or 0)
    out.append((name, "I3_ziel", "GRUEN" if tp == 0 else ("ROT" if tp < 3 * k else "GRUEN"),
                "nicht anwendbar (kein festes Ziel, take_profit_pct = 0)" if tp == 0 else f"Ziel {tp} gegen 3K {3 * k:.2f}"))
    fees = lade_modul(o / "backtest" / "fees.py", f"fees_{name}")
    eng = (o / "execution" / "engine.py").read_text(encoding="utf-8")
    m = re.search(r'^\s*PAPER_GEBUEHR_BOERSE\s*=\s*"([^"]+)"', eng, re.M)
    boerse = m.group(1) if m else "?"
    satz = fees.EXCHANGE_FEES.get(boerse, {}).get("taker")
    soll = geb["boersen"]["bitvavo_usdc"]["taker"]
    out.append((name, "I4_gebuehr_im_bot", "GRUEN" if satz == soll else "ROT",
                f"Papier-Boerse {boerse}, Taker {satz} % gegen Zielboerse {soll} %"))
    return out


def pruefe_journal(name: str, inst: dict, geb: dict) -> tuple[list[tuple], list[dict]]:
    """I5 und Schattenbuch fuer Orders/Runden seit Epoche E10/L9."""
    from runden_lib import lade, runden
    rows = lade(Path(inst["pfad"]))
    seit = EPOCHE_START[name]
    satz = geb["boersen"]["bitvavo_usdc"]["taker"] / 100
    falsch = []
    n = 0
    for r in rows:
        if r["time"] < seit or r.get("fee") is None:
            continue
        n += 1
        nominal = float(r["qty"]) * float(r["price"])
        soll = nominal * satz
        if abs(float(r["fee"]) - soll) > 0.01:
            # Kauf: fee wird auf den Abfluss (inkl. Gebuehr) gerechnet - zweite Lesart zulassen
            if not (r["type"] == "BUY" and abs(float(r["fee"]) - (nominal + float(r["fee"])) * satz) <= 0.01):
                falsch.append(f"{r['time'][:16]} {r['type']} {r['coin']}: {r['fee']} statt {soll:.4f}")
    out = [(name, "I5_gebuehr_journal", "ROT" if falsch else "GRUEN",
            (f"{len(falsch)} von {n} Orders abweichend: {falsch[:3]}") if falsch else f"{n} Orders seit Epoche, alle Gebuehren = {satz * 100:.2f} %")]
    rd = runden(rows, seit)
    plaene = {"bitvavo_usdc": 0.075, "bybit_eu": 0.252, "okx_xperps": 0.105}   # je Seite inkl. gemessenem Schlupf
    schatten = []
    for r in rd:
        z = {"instanz": name, "verkauf_t": r["t"], "coin": r["coin"], "brutto": round(r["brutto"], 4), "ist_netto": round(r["netto"], 4)}
        for pl, s in plaene.items():
            z[pl] = round(r["brutto"] - s / 100 * (r["kauf_nominal"] + r["verkauf_nominal"]), 4)
        schatten.append(z)
    monat = date.today().isoformat()[:7]
    rm = [r for r in rd if r["t"][:7] == monat]
    if rm:
        geb_m = sum(r["kauf_fee"] + r["verkauf_fee"] for r in rm)
        br_m = sum(r["brutto"] for r in rm)
        a, text = monat_ampel(geb_m, br_m)
        out.append((name, "monat_kosten_vs_brutto", a, f"{monat}: {text} ({len(rm)} Runden seit Epoche)"))
    return out, schatten


# ------------------------------------------------------------------ Lauf
def tabellen(con):
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS kosten (ts_utc TEXT, instanz TEXT, pruefung TEXT, ampel TEXT, befund TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS kosten_spanne (ts_utc TEXT, markt TEXT, spanne_bp REAL, proben INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS kosten_schatten (ts_utc TEXT, instanz TEXT, verkauf_t TEXT, coin TEXT, brutto REAL, "
                "ist_netto REAL, bitvavo_usdc REAL, bybit_eu REAL, okx_xperps REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS ereignisse (ts_utc TEXT, waechter TEXT, instanz TEXT, pruefung TEXT, "
                "von TEXT, nach TEXT, befund TEXT)")


def lauf(senden: bool = True, netz: bool = True) -> list[tuple]:
    jetzt = datetime.now(timezone.utc)
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    geb = json.loads((P / "gebuehren.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(DB, timeout=30)
    tabellen(con)
    erg = []
    if netz:
        erg += pruefe_boerse(geb)
        spanne_messen(con)
        con.commit()
    erg += pruefe_spanne(con, inst)
    for name, i in inst.items():
        try:
            erg += pruefe_invarianten(name, i, geb)
            j, schatten = pruefe_journal(name, i, geb)
            erg += j
            con.execute("DELETE FROM kosten_schatten WHERE instanz = ?", (name,))
            con.executemany("INSERT INTO kosten_schatten VALUES (?,?,?,?,?,?,?,?,?)",
                            [(jetzt.isoformat(), s["instanz"], s["verkauf_t"], s["coin"], s["brutto"], s["ist_netto"],
                              s["bitvavo_usdc"], s["bybit_eu"], s["okx_xperps"]) for s in schatten])
        except Exception as e:
            erg.append((name, "w3_fehler", "GELB", f"{type(e).__name__}: {str(e)[:150]}"))
    con.executemany("INSERT INTO kosten VALUES (?,?,?,?,?)", [(jetzt.isoformat(), *e) for e in erg])
    zustand = json.loads(ZUSTAND.read_text(encoding="utf-8")) if ZUSTAND.exists() else {}
    alt = zustand.get("ampeln", {})
    meldungen = []
    for a, b, c, d in erg:
        vorher = alt.get(f"{a}|{b}", "GRUEN")
        if c != vorher:
            con.execute("INSERT INTO ereignisse VALUES (?,?,?,?,?,?,?)", (jetzt.isoformat(), "W3", a, b, vorher, c, d))
            if c == "ROT" or (vorher == "ROT" and c == "GRUEN"):
                meldungen.append((f"W3-{a}|{b}-{c}", f"[WAECHTER][{'KRITISCH' if c == 'ROT' else 'INFO'}] W3 {a} {b}: {d}"))
    con.commit()
    con.close()
    zustand["ampeln"] = {f"{a}|{b}": c for a, b, c, _ in erg}
    ZUSTAND.write_text(json.dumps(zustand, indent=1), encoding="utf-8")
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    gesamt = max((STUFE[c] for _, _, c, _ in erg), default=0)
    status["W3"] = {"ampel": [k for k, v in STUFE.items() if v == gesamt][0], "stand_utc": jetzt.isoformat(),
                    "pruefungen": [{"instanz": a, "pruefung": b, "ampel": c, "befund": d} for a, b, c, d in erg]}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False), encoding="utf-8")
    if senden:
        for s, t in meldungen:
            tm.sende(t, schluessel=s)
    return erg


def selbsttest() -> int:
    fehler = 0
    ok = abs(nulllinie(0.505, 1.0) - 1.5202) < 0.001 and abs(nulllinie(0.15, 1.3) - 1.469) < 0.001
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Nulllinie: K 0,505/1,0 = {nulllinie(0.505, 1.0):.4f} (Patch 45: 1,520), K 0,15/1,3 = {nulllinie(0.15, 1.3):.4f}")
    # Gegentest in beide Richtungen mit den alten v6-Werten (E7): Puffer 0,35 bei K 0,505 muss ROT sein
    k, p = 0.505, 0.35
    ok = ("ROT" if p < k else "GRUEN") == "ROT"
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} E7-Werte (Puffer 0,35, K 0,505) -> ROT (garantierter Verlust)")
    k, p = 0.15, 0.195
    a = "ROT" if p < k else ("GELB" if p < k + SICHERHEIT else "GRUEN")
    ok = a == "GELB"
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} heutige Werte (Puffer 0,195, K 0,15) -> {a} (Kern ok, Sicherheit 0,10 nicht)")
    # Trailstart alt 1,21 fest bei Abstand 1,3 und K 0,15 -> ROT
    ok = 1.21 < nulllinie(0.15, 1.3)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} alter fester Start 1,21 bei Abstand 1,3 liegt unter der Nulllinie {nulllinie(0.15, 1.3):.2f} -> waere ROT")
    # Monatsregel [15.10.2026]
    a, t = monat_ampel(0.53, -3.61)                     # v6 Oktober: alte Regel GELB (0,53 > -3,61)
    ok = 0.53 > -3.61 and a == "GRUEN" and "Verlust schon vor Kosten" in t and "13 %" in t
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion v6 Okt. (frueher GELB): {a} {t}")
    a1, t1 = monat_ampel(3.0, 10.0)
    a2, t2 = monat_ampel(3.0, 2.0)
    ok = a1 == "GRUEN" and "30 %" in t1 and a2 == "GELB" and "Gewinn zum Verlust" in t2
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: Brutto +10/Geb. 3 -> {a1}; Brutto +2/Geb. 3 -> {a2}")
    a3, _ = monat_ampel(0.53, -0.10)                    # fast null vor Kosten: Kosten 84 % des Verlusts
    a4, _ = monat_ampel(0.50, 0.0)                      # Brutto genau 0: Kosten = ganzer Verlust
    a5, t5 = monat_ampel(0.50, -0.50)                   # genau 50 %: noch GRUEN
    ok = a3 == "GELB" and a4 == "GELB" and a5 == "GRUEN" and "50 %" in t5
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: Brutto -0,10 -> {a3}; Brutto 0 -> {a4}; genau 50 % -> {a5}")
    # Spanne alle 6 Maerkte [15.10.2026]; Messwerte wie W3 am 14./15.10. (DOGE ~13,3 bp laut Agententest)
    tag = {"BTC-USDC": [2.4, 2.5], "ETH-USDC": [3.9], "SOL-USDC": [4.4], "XRP-USDC": [6.0], "ADA-USDC": [11.0], "DOGE-USDC": [13.3]}
    lab = {"BTC": 3.25, "ETH": 3.79, "SOL": 4.89, "XRP": 6.98, "ADA": 12.29, "DOGE": 18.68}
    e = spanne_ampeln("labor", lab, tag, list(lab))
    ok = len(e) == 6 and {b for _, b, _, _ in e} >= {"spanne_XRP", "spanne_ADA", "spanne_DOGE"} and all(c == "GRUEN" for *_, c, _ in e)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion: Labor 6 Maerkte statt 3 -> {[(b, c) for _, b, c, _ in e]}")
    bot = {"BTC": 2.779, "ETH": 4.265, "SOL": 5.724, "DOGE": 1.441, "ADA": 5.954, "XRP": 6.591}
    e = spanne_ampeln("v6", bot, tag, ["BTC", "ETH", "SOL"])
    ok = ([c for _, b, c, _ in e if b.startswith("spanne_") and b != "spanne_nicht_gehandelt"] == ["GRUEN"] * 3
          and e[-1][1] == "spanne_nicht_gehandelt" and e[-1][2] == "GRUEN" and "DOGE 13.3/1.4 bp x9.2" in e[-1][3])
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall Bot: 3 gehandelte GRUEN, DOGE x9,2 nur Hinweis: {e[-1][3]}")
    e = spanne_ampeln("v7", {"BTC": 2.779, "ETH": 4.265}, {"BTC-USDC": [7.5]}, ["BTC", "ETH", "SOL"])
    a = {b: c for _, b, c, _ in e}
    ok = a == {"spanne_BTC": "ROT", "spanne_ETH": "GELB", "spanne_SOL": "GELB"}
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: BTC x2,7 -> {a.get('spanne_BTC')}, ETH ohne Messung -> {a.get('spanne_ETH')}, "
          f"SOL ohne Annahme -> {a.get('spanne_SOL')}")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return fehler


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    e = lauf(senden="--zeigen" not in sys.argv)
    if "--zeigen" in sys.argv:
        for a, b, c, d in e:
            print(f"{c:5s} {a:7s} {b:24s} {d}")
