# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W2 Vergleich Bot gegen Markt (MASTERPROMPT_AGENTEN.md 6.1) - taeglich nach W1, ohne KI, nur lesend.

ANLASS: 13.08.-13.10.2026 stieg der Korb BTC/ETH/SOL um rund 35 %, der Bot verlor (E7 netto -34,11 $),
und war dabei im Schnitt nur etwa zur Haelfte investiert. Niemand hat Alarm geschlagen.

Je Instanz (v6, v7):
  bot_rendite_N   Summe netto der Runden mit Verkauf in den letzten N Tagen (Kasse, runden_lib) / 500 $
  korb_rendite_N  gleichgewichteter Korb BTC/ETH/SOL (Tagesschluesse aus W1-Daten)
  investiert_7    mittlerer Anteil in Positionen, aus telemetrie.db markt_historie (equity, cash, btc_preis),
                  Sparplan-BTC herausgerechnet (Befund 44)
Regeln (Startwerte [VERMUTUNG]):
  M1 Trend verpasst     Gesamtlage AUFWAERTS seit >= 5 Tagen und Bot 14 T minus Korb 14 T <= -5 Punkte  -> ROT
  M2 Zu wenig im Markt  AUFWAERTS und investiert_7 < 50 %                                              -> GELB
  M3 Falsches Werkzeug  AUFWAERTS und Bot macht > 1,5 Runden am Tag (Kurzfrist-Handel im Trend)          -> GELB
  M4 Zu frueh raus      folgt mit W6 (Nachlauf)
  [15.10.2026, Lagebericht Punkt 4] Nicht berechenbar -> GELB statt GRUEN: Fehlt ein Tagesschluss im Korb
  (14.10.: W1 ohne Netz, Korb "+nan %" stand GRUEN) oder fehlt markt_historie, meldet W2 "nicht berechenbar".
  Der Korb gilt nur mit allen drei Muenzen (vorher still aus den vorhandenen gemittelt).
Aufrufe: pythonw w2_vergleich.py | python w2_vergleich.py --zeigen | --rueckblick (Aug-Okt nachspielen) | --selbsttest
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(P / "skripte"))
import telegram_meldung as tm  # noqa: E402

DB = P / "waechter.db"
STATUS = P / "status.json"
DATEN = HIER / "daten_w1"
KORB = ("BTC", "ETH", "SOL")


def korb_rendite(bis: date, tage: int) -> tuple[float, list[str]]:
    """(Rendite in %, fehlende Tagesschluesse). Nur mit allen drei Muenzen, sonst nan."""
    r, fehlt = [], []
    a, b = (bis - timedelta(days=tage)).isoformat(), bis.isoformat()
    for c in KORB:
        df = pd.read_csv(DATEN / f"{c}_1d.csv").set_index("datum")["close"]
        lueck = [t for t in (a, b) if t not in df.index]
        if lueck:
            fehlt.append(f"{c} {'/'.join(lueck)}")
        else:
            r.append(df[b] / df[a] - 1)
    if fehlt or not r:
        return float("nan"), fehlt
    return sum(r) / len(r) * 100, []


def bot_rendite(rd: list[dict], bis: date, tage: int) -> tuple[float, int]:
    a = (bis - timedelta(days=tage)).isoformat()
    sel = [r for r in rd if a < r["tag"] <= bis.isoformat()]
    return sum(r["netto"] for r in sel) / 500 * 100, len(sel)


def investiert(pfad: Path, bis: date, tage: int = 7) -> float | None:
    db = pfad / "data_store" / "telemetrie.db"
    acc = pfad / "data_store" / "btc_accumulator.json"
    spar_btc = float(json.loads(acc.read_text(encoding="utf-8")).get("total_btc") or 0) if acc.exists() else 0.0
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=30)
    a, b = (bis - timedelta(days=tage)).isoformat(), (bis + timedelta(days=1)).isoformat()
    zeilen = con.execute("SELECT equity, cash, btc_preis FROM markt_historie WHERE ts_utc >= ? AND ts_utc < ? "
                         "AND equity IS NOT NULL AND cash IS NOT NULL", (a, b)).fetchall()
    con.close()
    werte = []
    for eq, cash, btc in zeilen:
        handel = eq - spar_btc * (btc or 0)
        if handel > 0:
            werte.append(max(0.0, min(1.0, (handel - cash) / handel)))
    return sum(werte) / len(werte) * 100 if werte else None


def lage_seit(bis: date) -> tuple[str, int]:
    con = sqlite3.connect(DB, timeout=30)
    z = con.execute("SELECT datum, label FROM marktlage WHERE coin = 'BTC' AND datum <= ? ORDER BY datum DESC", (bis.isoformat(),)).fetchall()
    con.close()
    if not z:
        return "UNBEKANNT", 0
    lab, n = z[0][1], 0
    for _, l in z:
        if l != lab:
            break
        n += 1
    return lab, n


def bewerten(name: str, pfad: Path, bis: date, lage: str, seit: int) -> list[tuple]:
    from runden_lib import lade, runden
    rd = runden(lade(pfad), (bis - timedelta(days=40)).isoformat())
    b14, n14 = bot_rendite(rd, bis, 14)
    k14, fehlt = korb_rendite(bis, 14)
    inv = investiert(pfad, bis)
    b7, n7 = bot_rendite(rd, bis, 7)
    return regeln(name, lage, seit, b14, n14, k14, fehlt, inv, n7)


def regeln(name: str, lage: str, seit: int, b14: float, n14: int, k14: float, fehlt: list[str],
           inv: float | None, n7: int) -> list[tuple]:
    out = []
    auf = lage == "AUFWAERTS"
    if not (math.isfinite(b14) and math.isfinite(k14)):
        out.append((name, "M1_trend_verpasst", "GELB",
                    f"nicht berechenbar: Korb 14 T fehlt ({', '.join(fehlt) or 'kein Wert'}) | Lage {lage} seit {seit} T | "
                    f"Bot 14 T {b14:+.2f} % ({n14} Runden)"))
    else:
        m1 = auf and seit >= 5 and (b14 - k14) <= -5
        out.append((name, "M1_trend_verpasst", "ROT" if m1 else "GRUEN",
                    f"Lage {lage} seit {seit} T | Bot 14 T {b14:+.2f} % ({n14} Runden) gegen Korb {k14:+.2f} % -> {b14 - k14:+.2f} Punkte"))
    if inv is None or not math.isfinite(inv):
        out.append((name, "M2_zu_wenig_im_markt", "GELB", "nicht berechenbar: keine markt_historie-Daten (7 T)"))
    else:
        m2 = auf and inv < 50
        out.append((name, "M2_zu_wenig_im_markt", "GELB" if m2 else "GRUEN", f"investiert im Mittel 7 T: {inv:.0f} %"))
    m3 = auf and n7 / 7 > 1.5
    out.append((name, "M3_falsches_werkzeug", "GELB" if m3 else "GRUEN",
                f"{n7} Runden in 7 T ({n7 / 7:.1f} je Tag) bei Lage {lage}"))
    return out


def lauf(senden: bool = True, bis: date | None = None) -> list[tuple]:
    bis = bis or (datetime.now(timezone.utc).date() - timedelta(days=1))
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    lage, seit = lage_seit(bis)
    erg = []
    # [15.10.2026] W1 fiel nachts ohne Netz aus, W2 rechnete mit der Lage vom Vortag weiter. Jetzt: fehlt die
    # W1-Lage fuer 'bis', wird das gemeldet und der Lauf endet mit Code 1 (Aufgabe wiederholt alle 15 min, W5 sieht es).
    con = sqlite3.connect(DB, timeout=30)
    neueste = con.execute("SELECT max(datum) FROM marktlage WHERE coin = 'BTC'").fetchone()[0] or ""
    con.close()
    w1_fehlt = neueste < bis.isoformat()
    if w1_fehlt:
        erg.append(("alle", "w1_aktuell", "GELB", f"W1-Lage fehlt fuer {bis} (neueste {neueste or 'keine'}) - Lage vom Vortag benutzt"))
    for name, i in inst.items():
        try:
            erg += bewerten(name, Path(i["pfad"]), bis, lage, seit)
        except Exception as e:
            erg.append((name, "w2_fehler", "GELB", f"{type(e).__name__}: {str(e)[:150]}"))
    con = sqlite3.connect(DB, timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS vergleich (tag TEXT, instanz TEXT, pruefung TEXT, ampel TEXT, befund TEXT)")
    con.executemany("INSERT INTO vergleich VALUES (?,?,?,?,?)", [(bis.isoformat(), *e) for e in erg])
    con.commit()
    con.close()
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    stufe = max(({"GRUEN": 0, "GELB": 1, "ROT": 2}[c] for _, _, c, _ in erg), default=0)
    status["W2"] = {"ampel": ["GRUEN", "GELB", "ROT"][stufe], "stand_tag": bis.isoformat(),
                    "pruefungen": [{"instanz": a, "pruefung": b, "ampel": c, "befund": d} for a, b, c, d in erg]}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False), encoding="utf-8")
    if senden:
        for a, b, c, d in erg:
            if c == "ROT":
                tm.sende(f"[WAECHTER][HOCH] W2 {a} {b}: {d}", schluessel=f"W2-{a}-{b}")
    return erg


def rueckblick() -> None:
    """Haette W2 im August-Anstieg angeschlagen? Labels aus W1 (Startwerte oder --band N)."""
    import w1_marktlage as w1
    band = int(sys.argv[sys.argv.index("--band") + 1]) if "--band" in sys.argv else None
    t = w1.labels(w1.laden(DATEN), "2026-06-01", band=band)
    btc = t[t.coin == "BTC"].set_index("datum")["label"].to_dict()

    def lage_aus_labels(d: date) -> tuple[str, int]:
        tage = sorted(k for k in btc if k <= d.isoformat())[::-1]
        lab, n = btc[tage[0]], 0
        for k in tage:
            if btc[k] != lab:
                break
            n += 1
        return lab, n
    inst = json.loads((P / "instanzen.json").read_text(encoding="utf-8"))["instanzen"]
    print(f"W1-Variante: {'Halteband R <= ' + str(band) if band is not None else 'Startwerte'}")
    print("Tag         Lage (seit)        | v6: M1 / M2 / M3")
    d = date(2026, 8, 15)
    while d <= date(2026, 10, 13):
        lage, seit = lage_aus_labels(d)
        e = bewerten("v6", Path(inst["v6"]["pfad"]), d, lage, seit)
        if d.day in (1, 8, 15, 22, 29) or any(c != "GRUEN" for _, _, c, _ in e):
            print(f"{d}  {lage:11s} ({seit:2d} T) | " + " / ".join(f"{c}" for _, _, c, _ in e) + "   " + e[0][3][:90])
        d += timedelta(days=1)


def selbsttest() -> int:
    """Korb und Regeln ohne echte Daten: Reproduktion 14.10., Normalfall, Grenzfall."""
    import tempfile
    global DATEN
    alt_daten, fehler = DATEN, 0
    bis = date(2026, 10, 14)

    def csv_schreiben(ordner: Path, ohne: dict[str, str]) -> None:
        for i, c in enumerate(KORB):
            zeilen = ["ts_ms,datum,open,high,low,close,volume"]
            for k in range(20):
                d = (bis - timedelta(days=19 - k)).isoformat()
                if ohne.get(c) != d and ohne.get("alle") != d:
                    zeilen.append(f"0,{d},1,1,1,{100 * (i + 1) * (1 + 0.01 * k):.4f},1")
            (ordner / f"{c}_1d.csv").write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            DATEN = Path(tmp)
            # 1 Reproduktion 14.10. 02:35: W1 ohne Netz, Tagesschluss 14.10. fehlt -> frueher "+nan %" GRUEN
            csv_schreiben(DATEN, {"alle": bis.isoformat()})
            k14, fehlt = korb_rendite(bis, 14)
            m1 = regeln("v6", "SEITWAERTS", 8, -6.70, 21, k14, fehlt, 47.0, 12)[0]
            ok = math.isnan(k14) and len(fehlt) == 3 and m1[2] == "GELB" and "nicht berechenbar" in m1[3]
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Reproduktion 14.10.: {m1[2]} {m1[3]}")
            # 2 Normalfall: alle Schluesse da -> Korb +13,3 % (Schluss Tag 5 -> Tag 19), M1/M2 GRUEN
            csv_schreiben(DATEN, {})
            k14, fehlt = korb_rendite(bis, 14)
            erg = regeln("v6", "SEITWAERTS", 8, -6.70, 21, k14, fehlt, 47.0, 12)
            soll = (1.19 / 1.05 - 1) * 100
            ok = abs(k14 - soll) < 1e-6 and not fehlt and all(c == "GRUEN" for _, _, c, _ in erg)
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Normalfall: Korb {k14:+.3f} % (soll {soll:+.3f}), {[c for _, _, c, _ in erg]}")
            # 3 Grenzfall: nur ETH-Startwert fehlt -> nan statt Mittel aus 2 Muenzen; markt_historie leer -> M2 GELB;
            #   AUFWAERTS seit 5 T und genau -5 Punkte -> M1 ROT (Regelgrenze)
            csv_schreiben(DATEN, {"ETH": (bis - timedelta(days=14)).isoformat()})
            k14, fehlt = korb_rendite(bis, 14)
            m1, m2 = regeln("v7", "AUFWAERTS", 5, -1.0, 3, k14, fehlt, None, 3)[:2]
            r1 = regeln("v7", "AUFWAERTS", 5, -1.0, 3, 4.0, [], 60.0, 3)[0]
            ok = (math.isnan(k14) and fehlt == ["ETH 2026-09-30"] and m1[2] == "GELB" and m2[2] == "GELB"
                  and r1[2] == "ROT")
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Grenzfall: {m1[2]} {m1[3][:60]} | M2 {m2[2]} | -5 Punkte -> {r1[2]}")
    finally:
        DATEN = alt_daten
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    if "--rueckblick" in sys.argv:
        rueckblick()
    else:
        erg = lauf(senden="--zeigen" not in sys.argv)
        for a, b, c, d in erg:
            if "--zeigen" in sys.argv:
                print(f"{c:5s} {a:4s} {b:22s} {d}")
        if any(b == "w1_aktuell" for _, b, _, _ in erg):
            sys.exit(1)                                  # Aufgabe wiederholt, sobald W1 nachgeholt ist
