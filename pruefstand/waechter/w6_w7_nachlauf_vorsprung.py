# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W6 Nachlauf und W7 Vorsprung (MASTERPROMPT_AGENTEN.md 6.1) - taeglich nach W1, ohne KI, nur lesend.

W6 Nachlauf: Kurs 1 h / 4 h / 24 h / 7 Tage nach jedem Verkauf (Stundenkerzen Binance, gecacht),
   je Ausstiegsart und je W1-Marktlage am Verkaufstag. Alarm: Mittel des 7-Tage-Nachlaufs der letzten
   30 Tage in AUFWAERTS >= +3 % (Startwert [VERMUTUNG]) -> ROT ("zu frueh raus", liefert W2-M4).
W7 Vorsprung: Netto je Runde als Kassenrechnung (runden_lib) fuer die letzten 30/60/100 Runden und seit
   der laufenden Kostenlatten-Epoche (v6 E10, v7 L9): Mittel mit 95-%-Bereich (Block-Bootstrap nach Tagen),
   Profit-Faktor, Chance/Risiko, Trefferquote gegen noetige; CUSUM gegen Soll 0.
   Alarm: Mittel < -K mit 95 % Sicherheit (oberes Ende < -K) -> ROT; CUSUM-Bruch -> GELB.
   Unter 30 Runden: "nicht entscheidbar".
   [15.10.2026, Lagebericht Punkt 4] CUSUM-Bruch in den rollenden Fenstern (letzte 30/60/100, je n >= 30)
   -> GELB (Pruefung W7_cusum), mit Vermerk, wie viele Runden aus der alten Kostenwelt (vor E10/L9) stammen.
   Vorher wertete W7 den Bruch nur im Fenster "seit Epoche" aus, die rollenden Fenster blieben GRUEN.
Aufrufe: pythonw w6_w7_nachlauf_vorsprung.py | python ... --zeigen | --selbsttest
"""
from __future__ import annotations

import csv
import json
import random
import sqlite3
import statistics as st
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(P / "skripte"))
import telegram_meldung as tm  # noqa: E402

DB = P / "waechter.db"
STATUS = P / "status.json"
KERZEN = HIER / "daten_w6"
EPOCHE = {"v6": "2026-10-14T13:58:25", "v7": "2026-10-14T13:59:20"}
EPOCHE_NAME = {"v6": "E10", "v7": "L9"}
K = 0.15
MIN_RUNDEN = 30                                     # Masterprompt 6.1: darunter nur "nicht entscheidbar"
HORIZONTE = {"1h": 1, "4h": 4, "24h": 24, "7d": 168}


# ------------------------------------------------------------------ Stundenkerzen
def kerzen(coin: str) -> dict[int, float]:
    """{Stundenbeginn ms: Schluss}. Laedt seit 2026-08-01 und danach nur Neues."""
    import ccxt
    KERZEN.mkdir(exist_ok=True)
    pfad = KERZEN / f"{coin}_1h.csv"
    daten = {}
    if pfad.exists():
        with pfad.open(encoding="utf-8") as f:
            daten = {int(r["ts"]): float(r["close"]) for r in csv.DictReader(f)}
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 60000})
    seit = (max(daten) + 3_600_000) if daten else ex.parse8601("2026-08-01T00:00:00Z")
    jetzt_ms = int(time.time() * 1000)
    neu = {}
    while seit < jetzt_ms - 3_600_000:
        k = ex.fetch_ohlcv(f"{coin}/USDC", "1h", since=seit, limit=1000)
        if not k:
            break
        for x in k:
            if x[0] + 3_600_000 <= jetzt_ms:        # nur abgeschlossene Stunden
                neu[x[0]] = x[4]
        seit = k[-1][0] + 3_600_000
        if len(k) < 1000:
            break
    if neu:
        daten.update(neu)
        with pfad.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts", "close"])
            w.writerows(sorted(daten.items()))
    return daten


def kurs_nach(daten: dict[int, float], t: datetime, stunden: int) -> float | None:
    ziel = int((t + timedelta(hours=stunden)).timestamp() * 1000)
    stunde = ziel - ziel % 3_600_000
    return daten.get(stunde)


# ------------------------------------------------------------------ W6
def w6(inst: dict, lage: dict) -> tuple[list[tuple], list[dict]]:
    from runden_lib import lade
    k = {c: kerzen(c) for c in ("BTC", "ETH", "SOL")}
    out, zeilen = [], []
    seit = (datetime.now(timezone.utc) - timedelta(days=75)).isoformat()
    for name, i in inst.items():
        for r in lade(Path(i["pfad"])):
            if str(r["type"]).upper() != "SELL" or r["time"] < seit:
                continue
            coin = r["coin"].split("/")[0]
            if coin not in k:
                continue
            t = datetime.fromisoformat(r["time"].replace("Z", "+00:00"))
            z = {"instanz": name, "zeit": r["time"][:19], "coin": coin, "art": r.get("strategy"),
                 "lage": lage.get(r["time"][:10], "UNBEKANNT"), "preis": float(r["price"])}
            for h, n in HORIZONTE.items():
                p = kurs_nach(k[coin], t, n)
                z[h] = None if p is None else round((p / z["preis"] - 1) * 100, 3)
            zeilen.append(z)
    grenze = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    for name in inst:
        auf = [z["7d"] for z in zeilen if z["instanz"] == name and z["lage"] == "AUFWAERTS" and z["zeit"] >= grenze[:19] and z["7d"] is not None]
        alle = [z["7d"] for z in zeilen if z["instanz"] == name and z["zeit"] >= grenze[:19] and z["7d"] is not None]
        if len(auf) >= 5:
            m = st.mean(auf)
            out.append((name, "W6_nachlauf_aufwaerts", "ROT" if m >= 3 else "GRUEN",
                        f"7-Tage-Nachlauf nach Verkauf in AUFWAERTS (30 T): Mittel {m:+.2f} % aus {len(auf)} Verkaeufen"))
        else:
            out.append((name, "W6_nachlauf_aufwaerts", "GRUEN",
                        f"zu wenig Verkaeufe in AUFWAERTS (30 T): {len(auf)}; alle Lagen: "
                        + (f"Mittel {st.mean(alle):+.2f} % aus {len(alle)}" if alle else "keine mit 7 Tagen Abstand")))
    return out, zeilen


# ------------------------------------------------------------------ W7
def bootstrap_tage(werte: list[tuple[str, float]], n: int = 4000, seed: int = 11) -> tuple[float, float]:
    tage = {}
    for d, w in werte:
        tage.setdefault(d, []).append(w)
    schl = list(tage)
    rnd = random.Random(seed)
    m = []
    for _ in range(n):
        s = [w for d in (rnd.choice(schl) for _ in schl) for w in tage[d]]
        m.append(sum(s) / len(s))
    m.sort()
    return m[int(0.025 * n)], m[int(0.975 * n)]


def kennzahl(rd: list[dict]) -> dict:
    w = [(r["tag"], r["netto"] / r["kauf_abfluss"] * 100) for r in rd]
    x = [v for _, v in w]
    gew, ver = [v for v in x if v > 0], [v for v in x if v <= 0]
    lo, hi = bootstrap_tage(w)
    pf = sum(gew) / abs(sum(ver)) if ver and sum(ver) != 0 else None
    noetig = abs(st.mean(ver)) / (st.mean(gew) + abs(st.mean(ver))) * 100 if gew and ver else None
    cus, tief, bruch = 0.0, 0.0, False
    for v in x:                                         # CUSUM nach unten gegen Soll 0, Schwelle 4 Streuungen
        cus = min(0.0, cus + v)
        tief = min(tief, cus)
    sd = st.stdev(x) if len(x) > 1 else 0
    bruch = sd > 0 and tief < -4 * sd
    return {"n": len(x), "mittel": round(st.mean(x), 3), "bereich95": [round(lo, 3), round(hi, 3)],
            "profit_faktor": None if pf is None else round(pf, 2),
            "chance_risiko": round(st.mean(gew) / abs(st.mean(ver)), 2) if gew and ver else None,
            "treffer": round(100 * len(gew) / len(x), 1), "noetig": None if noetig is None else round(noetig, 1),
            "cusum_tief": round(tief, 2), "cusum_bruch": bruch}


def alt_vermerk(n_alt: int, n: int, ep: str) -> str:
    """Vermerk, ob die Runden aus der alten Kostenwelt (vor der Kostenlatten-Epoche) stammen."""
    if n_alt == n:
        return f"nur Alt-Daten: alle {n} Runden vor {ep} (alte Kostenwelt vor Bitvavo 0,05 %)"
    if n_alt:
        return f"gemischt: {n_alt} von {n} Runden vor {ep} (alte Kostenwelt)"
    return f"alle {n} Runden ab {ep} (neue Kostenwelt)"


def bewerte_w7(name: str, rd: list[dict], epoche: str, ep_name: str) -> tuple[list[tuple], dict]:
    """Ampeln W7 fuer eine Instanz aus ihren Runden (Kassenrechnung, zeitlich sortiert)."""
    out = []
    seit_ep = [r for r in rd if r["kauf_t"] >= epoche]
    d = {}
    for lab, sel in (("letzte_30", rd[-30:]), ("letzte_60", rd[-60:]), ("letzte_100", rd[-100:]), ("seit_epoche", seit_ep)):
        if len(sel) >= 2:
            d[lab] = kennzahl(sel)
            d[lab]["runden_vor_epoche"] = sum(r["kauf_t"] < epoche for r in sel)
    if len(seit_ep) < MIN_RUNDEN:
        out.append((name, "W7_vorsprung_epoche", "GRUEN",
                    f"seit Kostenlatten-Epoche {len(seit_ep)} Runden - nicht entscheidbar (< {MIN_RUNDEN})"))
    else:
        kz = d["seit_epoche"]
        rot = kz["bereich95"][1] < -K
        out.append((name, "W7_vorsprung_epoche", "ROT" if rot else ("GELB" if kz["cusum_bruch"] else "GRUEN"),
                    f"{kz['n']} Runden: netto {kz['mittel']:+.3f} % [{kz['bereich95'][0]:+.3f}; {kz['bereich95'][1]:+.3f}], "
                    f"PF {kz['profit_faktor']}, Treffer {kz['treffer']} % / noetig {kz['noetig']} %"
                    + (f", CUSUM-Bruch (tief {kz['cusum_tief']})" if kz["cusum_bruch"] else "")))
    # CUSUM-Bruch in den rollenden Fenstern (Masterprompt 6.1: Alarm). Gleich grosse Fenster nur einmal.
    rollend, gesehen = [], set()
    for lab in ("letzte_30", "letzte_60", "letzte_100"):
        if lab in d and d[lab]["n"] not in gesehen:
            gesehen.add(d[lab]["n"])
            rollend.append((lab, d[lab]))
    brueche = [(lab, kz) for lab, kz in rollend if kz["cusum_bruch"] and kz["n"] >= MIN_RUNDEN]
    klein = [(lab, kz) for lab, kz in rollend if kz["cusum_bruch"] and kz["n"] < MIN_RUNDEN]
    if brueche:
        teile = [f"{lab} (n {kz['n']}, tief {kz['cusum_tief']}, Mittel {kz['mittel']:+.3f} %; "
                 f"{alt_vermerk(kz['runden_vor_epoche'], kz['n'], ep_name)})" for lab, kz in brueche]
        out.append((name, "W7_cusum", "GELB", "CUSUM-Bruch (Dauer-Unterschreitung Soll 0) in " + " | ".join(teile)))
    elif klein:
        lab, kz = klein[-1]
        out.append((name, "W7_cusum", "GRUEN",
                    f"CUSUM-Bruch nur bei {kz['n']} Runden - nicht entscheidbar (< {MIN_RUNDEN}); "
                    + alt_vermerk(kz["runden_vor_epoche"], kz["n"], ep_name)))
    elif rollend:
        out.append((name, "W7_cusum", "GRUEN",
                    "kein CUSUM-Bruch in " + ", ".join(f"{lab} (n {kz['n']})" for lab, kz in rollend)))
    else:
        out.append((name, "W7_cusum", "GRUEN", f"{len(rd)} Runden - nicht entscheidbar (< {MIN_RUNDEN})"))
    if "letzte_100" in d:
        kz = d["letzte_100"]
        out.append((name, "W7_letzte_100", "GELB" if kz["bereich95"][1] < 0 else "GRUEN",
                    f"letzte {kz['n']} Runden (gemischte Epochen, Kasse): {kz['mittel']:+.3f} % "
                    f"[{kz['bereich95'][0]:+.3f}; {kz['bereich95'][1]:+.3f}], PF {kz['profit_faktor']}, Treffer {kz['treffer']} % / noetig {kz['noetig']} %"))
    return out, d


def w7(inst: dict) -> tuple[list[tuple], dict]:
    from runden_lib import lade, runden
    out, detail = [], {}
    for name, i in inst.items():
        rd = runden(lade(Path(i["pfad"])), "2026-08-13T13:21:19")
        o, detail[name] = bewerte_w7(name, rd, EPOCHE[name], EPOCHE_NAME[name])
        out += o
    return out, detail


def lauf(senden: bool = True) -> list[tuple]:
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    con = sqlite3.connect(DB, timeout=30)
    try:
        lage = {d: l for d, l in con.execute("SELECT datum, label FROM marktlage WHERE coin = 'BTC'")}
    except sqlite3.OperationalError:
        lage = {}
    con.close()
    erg6, zeilen = w6(inst, lage)
    erg7, detail = w7(inst)
    con = sqlite3.connect(DB, timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS nachlauf (instanz TEXT, zeit TEXT, coin TEXT, art TEXT, lage TEXT, preis REAL, "
                "r1h REAL, r4h REAL, r24h REAL, r7d REAL, PRIMARY KEY (instanz, zeit, coin))")
    con.executemany("INSERT OR REPLACE INTO nachlauf VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(z["instanz"], z["zeit"], z["coin"], z["art"], z["lage"], z["preis"], z["1h"], z["4h"], z["24h"], z["7d"]) for z in zeilen])
    con.execute("CREATE TABLE IF NOT EXISTS vorsprung (ts_utc TEXT, instanz TEXT, fenster TEXT, kennzahlen TEXT)")
    jetzt = datetime.now(timezone.utc).isoformat()
    for name, d in detail.items():
        for lab, kz in d.items():
            con.execute("INSERT INTO vorsprung VALUES (?,?,?,?)", (jetzt, name, lab, json.dumps(kz)))
    con.commit()
    con.close()
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    for w, erg in (("W6", erg6), ("W7", erg7)):
        stufe = max(({"GRUEN": 0, "GELB": 1, "ROT": 2}[c] for _, _, c, _ in erg), default=0)
        status[w] = {"ampel": ["GRUEN", "GELB", "ROT"][stufe], "stand_utc": jetzt,
                     "pruefungen": [{"instanz": a, "pruefung": b, "ampel": c, "befund": d} for a, b, c, d in erg]}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False), encoding="utf-8")
    if senden:
        for a, b, c, d in erg6 + erg7:
            if c == "ROT":
                tm.sende(f"[WAECHTER][HOCH] {b.split('_')[0]} {a} {b}: {d}", schluessel=f"{b}-{a}")
    return erg6 + erg7


def selbsttest() -> int:
    """W7_cusum ohne echte Daten: Reproduktion, Normalfall, Grenzfall (n = 29 / 30)."""
    ep = "2026-10-14T13:58:25"

    def runden_aus(werte: list[float], neu_ab: int) -> list[dict]:
        rd = []
        for i, v in enumerate(werte):
            t = (datetime(2026, 9, 1) if i < neu_ab else datetime(2026, 10, 15)) + timedelta(hours=12 * i)
            rd.append({"tag": t.date().isoformat(), "kauf_t": t.isoformat(), "netto": v, "kauf_abfluss": 100.0})
        return rd

    def ampel(out: list[tuple], pruefung: str) -> tuple[str, str]:
        return next((c, d) for _, b, c, d in out if b == pruefung)

    fehler = 0
    # 1 Reproduktion 14.10.: v6 letzte 30 alle vor E10, Mittel ~ -1 % -> Bruch, frueher GRUEN, jetzt GELB + Alt-Daten
    werte = [(-1.0 + 2.0 * (1 if i % 3 == 0 else -0.5)) for i in range(30)]
    c, d = ampel(bewerte_w7("v6", runden_aus(werte, 30), ep, "E10")[0], "W7_cusum")
    ok = c == "GELB" and "nur Alt-Daten" in d and "letzte_30" in d
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion Bruch alte Kostenwelt: {c} {d}")
    # 2 Normalfall: 40 Runden ab E10, Mittel +0,35 % -> kein Bruch, alles GRUEN
    out, _ = bewerte_w7("v6", runden_aus([1.5, -0.8] * 20, 0), ep, "E10")
    c, d = ampel(out, "W7_cusum")
    c2, _ = ampel(out, "W7_vorsprung_epoche")
    ok = c == "GRUEN" and c2 == "GRUEN" and "kein CUSUM-Bruch" in d
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: cusum {c}, epoche {c2}: {d}")
    # 3 Grenzfall: 29 Runden mit Bruch -> GRUEN "nicht entscheidbar"; 30 Runden (10 neu) -> GELB "gemischt: 20 von 30"
    c29, d29 = ampel(bewerte_w7("v7", runden_aus(([-1.0, -0.5, -1.5] * 10)[:29], 29), ep, "L9")[0], "W7_cusum")
    c30, d30 = ampel(bewerte_w7("v7", runden_aus([-1.0, -0.5, -1.5] * 10, 20), ep, "L9")[0], "W7_cusum")
    ok = (c29 == "GRUEN" and "nicht entscheidbar" in d29 and "29 Runden" in d29
          and c30 == "GELB" and "gemischt: 20 von 30" in d30)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall n 29: {c29} {d29}")
    print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall n 30: {c30} {d30}")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    for a, b, c, d in lauf(senden="--zeigen" not in sys.argv):
        if "--zeigen" in sys.argv:
            print(f"{c:5s} {a:4s} {b:24s} {d}")
