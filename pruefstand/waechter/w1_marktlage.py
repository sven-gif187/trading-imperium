# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
W1 Marktlage (MASTERPROMPT_AGENTEN.md 6.1) - taeglich nach dem UTC-Tagesschluss, ohne KI.
Loest KEINE Trades aus: messen, melden, belegen.

Je Coin (12 Bot-Coins, Tageskerzen Binance gegen USDT), nur abgeschlossene Tage:
  Richtungssumme R = -8 .. +8:
    SMA200 (Schluss ueber/unter: +1/-1), EMA50 vs EMA200 (+1/-1),
    Zeitreihen-Momentum 7/14/28/56 Tage (je +1/-1),
    Donchian 20/55: Schluss >= Hoch der Vortage +1, <= Tief -1, sonst 0
  Filter: ADX(14) nach Wilder, Effizienz-Quote ER(20) nach Kaufman,
          20-Tage-Schwankung als Perzentil der letzten 365 Tage, Marktbreite
          (Anteil der Coins ueber ihrer 50-Tage-Linie)
  Label (Startwerte [VERMUTUNG], A7 eicht):
    HOCHVOLA/CRASH  Perzentil >= 90 und (7-Tage-Rendite <= -10 % oder Abstand zum 30-Tage-Hoch <= -15 %)
    AUFWAERTS       R >= +5 und (ADX >= 25 oder ER >= 0,30) und Marktbreite >= 60 %
    ABWAERTS        R <= -5 und (ADX >= 25 oder ER >= 0,30)
    SEITWAERTS      sonst
  Hysterese: neues Label erst nach 2 bestaetigenden Tagesschluessen (CRASH sofort).
  Gesamtlage = BTC-Label (BTC fuehrt), Marktbreite wird mitgemeldet.

Aufrufe: pythonw w1_marktlage.py           taeglicher Lauf (Daten nachladen, Labels, Meldung bei Wechsel)
         python w1_marktlage.py --abnahme  Abnahmetest walk-forward 15.06.2026 bis heute
         python w1_marktlage.py --zeigen   heutige Lage ohne Telegram
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
import telegram_meldung as tm  # noqa: E402

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE", "NEAR", "UNI", "ATOM"]
DATEN = HIER / "daten_w1"
LABOR_DATEN = P / "labor" / "daten"
DB = P / "waechter.db"
STATUS = P / "status.json"


# ------------------------------------------------------------------ Daten
def daten_aktualisieren() -> None:
    import ccxt
    DATEN.mkdir(exist_ok=True)
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 60000})
    heute = datetime.now(timezone.utc).date().isoformat()
    for c in COINS:
        ziel = DATEN / f"{c}_1d.csv"
        if not ziel.exists():
            shutil.copy2(LABOR_DATEN / f"{c}_1d.csv", ziel)
        letzter = int(pd.read_csv(ziel)["ts_ms"].iloc[-1])
        for v in range(3):
            try:
                k = ex.fetch_ohlcv(f"{c}/USDT", "1d", since=letzter + 86_400_000, limit=1000)
                break
            except Exception:
                if v == 2:
                    raise
                time.sleep(5)
        neu = [[x[0], datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat(), *x[1:6]] for x in k
               if datetime.fromtimestamp(x[0] / 1000, timezone.utc).date().isoformat() < heute]
        if neu:
            with ziel.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(neu)


def laden(ordner: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for c in COINS:
        df = pd.read_csv(ordner / f"{c}_1d.csv")
        df["datum"] = pd.to_datetime(df["datum"])
        out[c] = df.set_index("datum")[["open", "high", "low", "close"]].astype(float)
    return out


# ------------------------------------------------------------------ Indikatoren (alle nur rueckwaerts)
def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up, dn = h.diff(), -l.diff()
    plus = ((up > dn) & (up > 0)) * up
    minus = ((dn > up) & (dn > 0)) * dn
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * plus.ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * minus.ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def merkmale(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    m = pd.DataFrame(index=df.index)
    m["close"] = c
    sma200, sma50 = c.rolling(200).mean(), c.rolling(50).mean()
    ema50, ema200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    stimmen = [(c > sma200).astype(int) * 2 - 1, (ema50 > ema200).astype(int) * 2 - 1]
    for n in (7, 14, 28, 56):
        stimmen.append(((c / c.shift(n) - 1) > 0).astype(int) * 2 - 1)
    for n in (20, 55):
        hoch, tief = c.shift(1).rolling(n).max(), c.shift(1).rolling(n).min()
        stimmen.append((c >= hoch).astype(int) - (c <= tief).astype(int))
    m["R"] = sum(stimmen)
    m.loc[sma200.isna(), "R"] = pd.NA                                    # erst ab 200 Tagen
    m["adx"] = adx(df)
    m["er"] = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    vol = (c / c.shift()).apply(math.log).rolling(20).std() * math.sqrt(365)
    m["vol"] = vol
    m["vol_pct"] = vol.rolling(365, min_periods=200).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    m["r7"] = c / c.shift(7) - 1
    m["ab_hoch30"] = c / c.rolling(30).max() - 1
    m["ueber_sma50"] = c > sma50
    return m


# [15.10.2026] Entscheidung Sven E4 (entscheidungen.md, berichte/2026-10-15_entscheidungsvorlage.md): Halteband im
# Tageslauf. Ein AUFWAERTS/ABWAERTS endet erst bei R <= 2 bzw. R >= -2. Abnahmetest: 0 statt 5 Mal Flackern bei BTC,
# W2 haette den August-Trend am 24.08. statt am 23.09. als verpasst gemeldet. Abnahme ohne --band = Startwerte.
HALTEBAND = 2


def roh_label(z: pd.Series, breite: float, vorher: str = "", band: int | None = None) -> str:
    """band: Halteband-Variante (Abnahmetest-Vergleich). Ein bestehendes AUFWAERTS/ABWAERTS haelt,
    bis R auf +band bzw. -band faellt/steigt, statt schon unter 5 zu kippen. None = Masterprompt-Startwerte."""
    if pd.isna(z["R"]):
        return "UNBEKANNT"
    trend = (z["adx"] >= 25) or (z["er"] >= 0.30)
    if z["vol_pct"] >= 90 and (z["r7"] <= -0.10 or z["ab_hoch30"] <= -0.15):
        return "HOCHVOLA/CRASH"
    if band is not None and vorher == "AUFWAERTS" and z["R"] > band:
        return "AUFWAERTS"
    if band is not None and vorher == "ABWAERTS" and z["R"] < -band:
        return "ABWAERTS"
    if z["R"] >= 5 and trend and breite >= 60:
        return "AUFWAERTS"
    if z["R"] <= -5 and trend:
        return "ABWAERTS"
    return "SEITWAERTS"


def labels(daten: dict[str, pd.DataFrame], von: str | None = None, band: int | None = None) -> pd.DataFrame:
    """Tabelle je Tag und Coin: roh-Label, Label nach Hysterese, Eingangswerte. Kausal (nur Vergangenheit)."""
    mk = {c: merkmale(df) for c, df in daten.items()}
    tage = mk["BTC"].index
    breite = pd.DataFrame({c: mk[c]["ueber_sma50"].reindex(tage) for c in COINS}).mean(axis=1) * 100
    zeilen = []
    for c in COINS:
        m = mk[c].reindex(tage)
        aktuell, kandidat, n = "UNBEKANNT", None, 0
        for d in tage:
            z = m.loc[d]
            if pd.isna(z["close"]):
                continue
            r = roh_label(z, breite.loc[d], aktuell, band)
            if r == aktuell:
                kandidat, n = None, 0
            elif r == "HOCHVOLA/CRASH" or aktuell == "UNBEKANNT":
                aktuell, kandidat, n = r, None, 0
            elif r == kandidat:
                n += 1
                if n >= 2:
                    aktuell, kandidat, n = r, None, 0
            else:
                kandidat, n = r, 1
            if von is None or d >= pd.Timestamp(von):
                zeilen.append({"datum": d.date().isoformat(), "coin": c, "roh": r, "label": aktuell,
                               "R": None if pd.isna(z["R"]) else int(z["R"]), "adx": round(float(z["adx"]), 1),
                               "er": round(float(z["er"]), 2), "vol_pct": None if pd.isna(z["vol_pct"]) else round(float(z["vol_pct"]), 0),
                               "breite": round(float(breite.loc[d]), 0), "close": float(z["close"])})
    return pd.DataFrame(zeilen)


# ------------------------------------------------------------------ Abnahmetest
def abnahme() -> None:
    daten = laden(DATEN if DATEN.exists() else LABOR_DATEN)
    if "--band" in sys.argv:
        b = int(sys.argv[sys.argv.index("--band") + 1])
        print(f"VARIANTE Halteband: AUFWAERTS haelt bis R <= {b} (ABWAERTS bis R >= -{b})\n")
        t = labels(daten, "2026-06-15", band=b)
    else:
        t = labels(daten, "2026-06-15")
    print(f"W1-Abnahmetest walk-forward {t['datum'].min()} .. {t['datum'].max()} (Indikatoren nur aus der Vergangenheit)\n")
    for c in ("BTC", "ETH", "SOL"):
        s = t[t.coin == c].reset_index(drop=True)
        wechsel = s[s["label"] != s["label"].shift()]
        print(f"== {c}: {len(wechsel) - 1} Wechsel")
        for _, w in wechsel.iterrows():
            print(f"   {w['datum']}  {w['label']:15s} (R {w['R']}, ADX {w['adx']}, ER {w['er']}, Breite {w['breite']} %, Schluss {w['close']:,.2f})")
        auf = s[(s["label"] == "AUFWAERTS") & (s["datum"] >= "2026-08-13")]
        if len(auf):
            d0 = auf.iloc[0]["datum"]
            k0 = s[s["datum"] == "2026-08-13"]["close"].iloc[0]
            k1 = auf.iloc[0]["close"]
            print(f"   -> AUFWAERTS erkannt am {d0}: Verzug {(pd.Timestamp(d0) - pd.Timestamp('2026-08-13')).days} Tage, "
                  f"Kurs bis dahin schon {(k1 / k0 - 1) * 100:+.1f} % seit 13.08.")
        else:
            print("   -> AUFWAERTS nach dem 13.08. NICHT erkannt")
        kurz = 0
        for i in range(1, len(wechsel)):
            dauer = (pd.Timestamp(wechsel.iloc[i]["datum"]) - pd.Timestamp(wechsel.iloc[i - 1]["datum"])).days
            kurz += dauer <= 5
        print(f"   Flackern (Label haelt <= 5 Tage): {kurz}")
        mon = wechsel.iloc[1:].assign(m=lambda x: x["datum"].str[:7]).groupby("m").size().to_dict()
        print(f"   Wechsel je Monat: {mon}\n")
    g = t[t.coin == "BTC"][["datum", "label", "breite"]]
    g.to_csv(HIER / "w1_abnahme_btc.csv", index=False)
    t.to_csv(HIER / "w1_abnahme_alle.csv", index=False)
    print("gespeichert:", HIER / "w1_abnahme_alle.csv")


# ------------------------------------------------------------------ Tageslauf
def lauf(senden: bool = True) -> dict:
    daten_aktualisieren()
    t = labels(laden(DATEN), "2026-01-01", band=HALTEBAND)      # schreibt die Lage ab 01.01. mit Halteband neu
    letzter = t["datum"].max()
    heute = t[t.datum == letzter].set_index("coin")
    gestern_tag = sorted(t["datum"].unique())[-2]
    gestern = t[t.datum == gestern_tag].set_index("coin")
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS marktlage (datum TEXT, coin TEXT, label TEXT, roh TEXT, R INTEGER, adx REAL, er REAL, "
                "vol_pct REAL, breite REAL, close REAL, PRIMARY KEY (datum, coin))")
    con.execute("CREATE TABLE IF NOT EXISTS ereignisse (ts_utc TEXT, waechter TEXT, instanz TEXT, pruefung TEXT, von TEXT, nach TEXT, befund TEXT)")
    con.executemany("INSERT OR REPLACE INTO marktlage VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(r.datum, r.coin, r.label, r.roh, r.R, r.adx, r.er, r.vol_pct, r.breite, r.close) for r in t.itertuples()])
    meldungen = []
    for c in COINS:
        a, b = gestern.loc[c, "label"], heute.loc[c, "label"]
        if a != b:
            z = heute.loc[c]
            text = (f"[WAECHTER][{'HOCH' if c == 'BTC' or b == 'HOCHVOLA/CRASH' else 'INFO'}] W1 Marktlage {c}: {a} -> {b} "
                    f"(R {z['R']}, ADX {z['adx']}, ER {z['er']}, Breite {z['breite']} %)")
            con.execute("INSERT INTO ereignisse VALUES (?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), "W1", c, "marktlage", a, b, text))
            if c == "BTC" or b == "HOCHVOLA/CRASH":
                meldungen.append((f"W1-{c}-{b}-{letzter}", text))
    con.commit()
    con.close()
    btc = heute.loc["BTC"]
    stand = {"stand_tag": letzter, "gesamtlage": btc["label"], "breite_pct": btc["breite"],
             "coins": {c: {"label": heute.loc[c, "label"], "R": heute.loc[c, "R"]} for c in COINS}}
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    status["W1"] = {"ampel": "ROT" if btc["label"] == "HOCHVOLA/CRASH" else ("GELB" if btc["label"] == "ABWAERTS" else "GRUEN"),
                    "stand_utc": datetime.now(timezone.utc).isoformat(), **{k: (int(v) if hasattr(v, "item") else v) for k, v in stand.items() if k != "coins"},
                    "coins": {c: {"label": v["label"], "R": None if pd.isna(v["R"]) else int(v["R"])} for c, v in stand["coins"].items()}}
    STATUS.write_text(json.dumps(status, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if senden:
        for s, txt in meldungen:
            tm.sende(txt, schluessel=s)
    return status["W1"]


if __name__ == "__main__":
    if "--abnahme" in sys.argv:
        abnahme()
    else:
        s = lauf(senden="--zeigen" not in sys.argv)
        if "--zeigen" in sys.argv:
            print(json.dumps(s, indent=1, ensure_ascii=False, default=str))
