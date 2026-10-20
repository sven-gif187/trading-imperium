# -*- coding: utf-8 -*-
"""
A4 einstiegs-pruefer · gemeinsame Basis (nur lesen, keine Bot-Dateien schreiben).

Kurse:   pruefstand/daten/binance_1h_<MUENZE>_USDC.csv (nur abgeschlossene Kerzen).
         P(T) = Schlusskurs der Kerze, die bei T endet (= letzter bekannter Kurs zum Zeitpunkt T).
Runden:  runden_lib (gegen Bericht geprueft: 136 Runden, brutto +66,49 $, netto -43,13 $).
         Jede Runde bekommt die Merkmale ihres Kaufs (Kaufweg, Score, market_regime, Fear&Greed).

Kein Blick in die Zukunft:
  - Vorwaertsrendite des Bots ab T0 = naechste volle Stunde NACH dem Kauf (Kauf 14:20 -> 15:00).
  - Zufallsvergleich: jede volle Stunde h derselben Muenze, gleiche Formel P(h+H)/P(h)-1.
  - Vorlauf (vor dem Kauf) endet bei der letzten abgeschlossenen Kerze VOR dem Kauf.

Kosten (wie A6, kosten_schatten.py): netto(K) = brutto - K/2 % * Kauf-Nominal - K/2 % * Verkauf-Nominal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runden_lib import lade, runden  # noqa: E402

PRUEF = Path(r"C:\Users\<BENUTZER>\Desktop\pruefstand")
DATEN = PRUEF / "daten"
V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
V7 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v7")
VON, BIS = "2026-08-13T13:21:19", "2026-10-14T09:18:25"     # Verkaeufe E7 (vor E8-Start)
GRENZE_LAGE = pd.Timestamp("2026-09-01T00:00:00Z")          # Aug-Aufwaertstrend | Sep/Okt seitwaerts
HORIZONTE = [1, 4, 12, 24, 48, 72, 168]                     # Stunden
K_NEU, K_ALT = 0.150, 0.505                                 # Kostenlatte je Runde in %
MUENZEN = ("BTC", "ETH", "SOL")


def kurse() -> dict[str, pd.Series]:
    """P(T) je Muenze: Index = Kerzen-ENDE (UTC), Wert = Schlusskurs."""
    aus = {}
    for c in MUENZEN:
        df = pd.read_csv(DATEN / f"binance_1h_{c}_USDC.csv")
        t = pd.to_datetime(df["open_utc"], utc=True) + pd.Timedelta(hours=1)
        aus[c] = pd.Series(df["close"].values, index=t).sort_index()
    return aus


def rendite(p: pd.Series, t0: pd.Timestamp, t1: pd.Timestamp) -> float:
    """P(t1)/P(t0)-1 in %, NaN wenn ein Zeitpunkt fehlt (z. B. Horizont reicht ueber heute hinaus)."""
    if t0 in p.index and t1 in p.index:
        return (p[t1] / p[t0] - 1) * 100
    return np.nan


def marktlage(t: pd.Timestamp) -> str:
    return "A_Aug_Trend" if t < GRENZE_LAGE else "B_SepOkt_seitwaerts"


def runden_mit_kauf(bot: Path = V6, von: str = VON, bis: str = BIS) -> pd.DataFrame:
    rows = lade(bot)
    rd = runden(rows, von, bis)
    kauf = {r["time"]: r for r in rows if str(r.get("type", "")).upper() == "BUY"}
    aus = []
    for r in rd:
        k = kauf[r["kauf_t"]]
        sc = k.get("signal_score", k.get("score"))
        aus.append({
            **r,
            "muenze": r["coin"].split("/")[0],
            "kauf_zeit": pd.Timestamp(r["kauf_t"]),
            "verkauf_zeit": pd.Timestamp(r["t"]),
            "score": np.nan if sc is None else float(sc),
            "regime": k.get("market_regime"),
            "fg": k.get("fear_greed_at_entry"),
            "kaufpreis": float(k["price"]),
            "brutto_pct": r["brutto"] / r["kauf_nominal"] * 100,
        })
    df = pd.DataFrame(aus)
    df["halte_h"] = (df["verkauf_zeit"] - df["kauf_zeit"]).dt.total_seconds() / 3600
    df["tag"] = df["kauf_zeit"].dt.strftime("%Y-%m-%d")          # Bootstrap-Block = Kauftag
    df["lage"] = df["kauf_zeit"].map(marktlage)
    for K, n in ((K_NEU, "150"), (K_ALT, "505")):
        df[f"kosten_{n}"] = K / 2 / 100 * (df["kauf_nominal"] + df["verkauf_nominal"])
        df[f"netto_{n}"] = df["brutto"] - df[f"kosten_{n}"]
        df[f"netto_{n}_pct"] = df[f"netto_{n}"] / df["kauf_nominal"] * 100
    return df


def vorwaerts(df: pd.DataFrame, P: dict[str, pd.Series], zeit_spalte: str = "kauf_zeit") -> pd.DataFrame:
    """Vorwaertsrendite je Horizont ab naechster voller Stunde; Vorlauf 24/72 h bis zur letzten Kerze vor dem Kauf."""
    df = df.copy()
    t0 = df[zeit_spalte].dt.ceil("h")
    tv = df[zeit_spalte].dt.floor("h")
    for H in HORIZONTE:
        df[f"f{H}"] = [rendite(P[c], a, a + pd.Timedelta(hours=H)) for c, a in zip(df["muenze"], t0)]
    for H in (24, 72):
        df[f"v{H}"] = [rendite(P[c], a - pd.Timedelta(hours=H), a) for c, a in zip(df["muenze"], tv)]
    return df


def zufall_stunden(P: dict[str, pd.Series], von: pd.Timestamp, bis: pd.Timestamp) -> pd.DataFrame:
    """Jede volle Stunde h jeder Muenze in [von, bis): Vorwaerts- und Vorlaufrendite mit derselben Formel."""
    aus = []
    for c, p in P.items():
        for h in p.index[(p.index >= von) & (p.index < bis)]:
            z = {"muenze": c, "h": h}
            for H in HORIZONTE:
                z[f"f{H}"] = rendite(p, h, h + pd.Timedelta(hours=H))
            for H in (24, 72):
                z[f"v{H}"] = rendite(p, h - pd.Timedelta(hours=H), h)
            aus.append(z)
    z = pd.DataFrame(aus)
    z["tag"] = z["h"].dt.strftime("%Y-%m-%d")
    z["lage"] = z["h"].map(marktlage)
    return z


def bootstrap_mittel(werte, bloecke, n: int = 20000, niveau: float = 0.95, seed: int = 11):
    """Block-Bootstrap: ziehe Bloecke (Kalendertage oder Mehrtagesbloecke) mit Zuruecklegen.
    Gibt (Mittel, unten, oben, Anzahl Bloecke) zurueck. NaN-Werte werden vorher entfernt."""
    w = np.asarray(werte, float)
    b = np.asarray(bloecke)
    ok = ~np.isnan(w)
    w, b = w[ok], b[ok]
    if len(w) == 0:
        return (np.nan, np.nan, np.nan, 0)
    ub, idx = np.unique(b, return_inverse=True)
    s = np.bincount(idx, weights=w)
    k = np.bincount(idx).astype(float)
    rng = np.random.default_rng(seed)
    z = rng.integers(0, len(ub), size=(n, len(ub)))
    m = s[z].sum(1) / k[z].sum(1)
    a = (1 - niveau) / 2
    return (w.mean(), float(np.quantile(m, a)), float(np.quantile(m, 1 - a)), len(ub))


def block_von_tag(tage: pd.Series, laenge_tage: int) -> np.ndarray:
    """Mehrtagesbloecke (fuer lange Horizonte, deren Fenster sich ueber Tage ueberlappen)."""
    d = pd.to_datetime(tage)
    return ((d - pd.Timestamp("2026-06-15")).dt.days // max(1, laenge_tage)).values


def bootstrap_spearman(x, y, bloecke, n: int = 5000, niveau: float = 0.95, seed: int = 13):
    x, y, b = np.asarray(x, float), np.asarray(y, float), np.asarray(bloecke)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y, b = x[ok], y[ok], b[ok]
    if len(x) < 5:
        return (np.nan, np.nan, np.nan, len(x))
    rho = pd.Series(x).rank().corr(pd.Series(y).rank())
    ub = np.unique(b)
    gruppen = [np.where(b == u)[0] for u in ub]
    rng = np.random.default_rng(seed)
    r = []
    for _ in range(n):
        ix = np.concatenate([gruppen[i] for i in rng.integers(0, len(ub), len(ub))])
        xs, ys = pd.Series(x[ix]).rank(), pd.Series(y[ix]).rank()
        if xs.std() > 0 and ys.std() > 0:
            r.append(xs.corr(ys))
    a = (1 - niveau) / 2
    return (rho, float(np.quantile(r, a)), float(np.quantile(r, 1 - a)), len(x))


def cluster_se_mittel(werte, bloecke):
    """Zweiter Weg zum Bootstrap: Mittel mit Cluster-robustem Standardfehler (Cluster = Block), 95 % ~ +-1,96 SE."""
    w = np.asarray(werte, float)
    b = np.asarray(bloecke)
    ok = ~np.isnan(w)
    w, b = w[ok], b[ok]
    m = w.mean()
    N = len(w)
    ub = np.unique(b)
    G = len(ub)
    s = np.array([(w[b == u] - m).sum() for u in ub])
    se = np.sqrt((s ** 2).sum()) / N * np.sqrt(G / max(G - 1, 1))
    return m, m - 1.96 * se, m + 1.96 * se, G
