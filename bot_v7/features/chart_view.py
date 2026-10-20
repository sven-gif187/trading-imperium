"""
CHART-VIEW  -  Baustein 2 des Chart-Tabs
=========================================
Render-Logik fuer den Kerzen-Chart: laedt Kerzen ueber ChartData,
zeichnet Candlesticks + Volumen und legt DEINE echten Trades als
Kauf/Verkauf-Marker drueber.

Getrennt von der GUI, damit es einzeln testbar ist.
Reine Anzeige/Analyse, KEIN Trading-Eingriff.
"""
import os
import json
from datetime import datetime, timezone

import pandas as pd
import mplfinance as mpf


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def candles_to_df(rows):
    """Wandelt Kerzen-Dicts (von ChartData) in einen mplfinance-DataFrame."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                            "close": "Close", "volume": "Volume"})
    df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
    return df


def load_trades_for(symbol, root=None):
    """Laedt Kauf/Verkauf-Punkte fuer einen Coin aus trades_v5.json."""
    root = root or _project_root()
    path = os.path.join(root, "data_store", "trades_v5.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        trades = d if isinstance(d, list) else d.get("trades", [])
    except Exception:
        return []
    base = symbol.split("/")[0].upper()
    out = []
    for t in trades:
        sym = str(t.get("symbol", t.get("coin", "")))
        if not sym.upper().startswith(base):
            continue
        ts = t.get("time", t.get("timestamp", ""))
        try:
            when = pd.to_datetime(ts, utc=True)
        except Exception:
            continue
        out.append({
            "time": when,
            "price": float(t.get("price", 0) or 0),
            "side": "BUY" if "BUY" in str(t.get("side", t.get("type", ""))).upper() else "SELL",
            "strategy": str(t.get("strategy", t.get("active_strategy", ""))),
            "pnl": float(t.get("pnl") or 0),
        })
    return out


# ============================================================
#  INDIKATOREN  -  Berechnung + Klartext-Erklaerung
# ============================================================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(series, period=20, mult=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    return mid + mult * std, mid, mid - mult * std


def vwap(df):
    typ = (df["High"] + df["Low"] + df["Close"]) / 3
    return (typ * df["Volume"]).cumsum() / df["Volume"].cumsum()


def erklaere_indikatoren(df, aktiv):
    """Klartext-Erklaerung, was die Indikatoren JETZT aussagen."""
    if df.empty:
        return ""
    c = df["Close"]
    zeilen = []
    if "rsi" in aktiv:
        r = rsi(c).iloc[-1]
        if r < 30:
            d = "ueberverkauft - koennte drehen (aber im Abwaertstrend kann er tief bleiben)"
        elif r > 70:
            d = "ueberkauft - koennte fallen"
        else:
            d = "neutral"
        zeilen.append(f"RSI {r:.0f}: {d}")
    if "ema" in aktiv:
        e20 = ema(c, 20).iloc[-1]
        e50 = ema(c, 50).iloc[-1]
        if e20 > e50:
            d = "EMA20 ueber EMA50 -> Aufwaertstrend (bullisch)"
        else:
            d = "EMA20 unter EMA50 -> Abwaertstrend (baerisch)"
        zeilen.append(f"EMA: {d}")
    if "macd" in aktiv:
        ml, sl, h = macd(c)
        if h.iloc[-1] > 0 and h.iloc[-2] <= 0:
            d = "frischer bullischer Schwung (MACD kreuzt nach oben)"
        elif h.iloc[-1] < 0 and h.iloc[-2] >= 0:
            d = "frischer baerischer Schwung (MACD kreuzt nach unten)"
        elif h.iloc[-1] > 0:
            d = "positiver Schwung"
        else:
            d = "negativer Schwung"
        zeilen.append(f"MACD: {d}")
    if "boll" in aktiv:
        up, mid, lo = bollinger(c)
        price = c.iloc[-1]
        if price > up.iloc[-1]:
            d = "Preis ueber oberem Band - ungewoehnlich teuer/ueberdehnt"
        elif price < lo.iloc[-1]:
            d = "Preis unter unterem Band - ungewoehnlich billig/ueberdehnt"
        else:
            d = "Preis innerhalb der Baender - normal"
        zeilen.append(f"Bollinger: {d}")
    if "vwap" in aktiv:
        v = vwap(df).iloc[-1]
        price = c.iloc[-1]
        d = "ueber VWAP (Kaeufer dominieren)" if price > v else "unter VWAP (Verkaeufer dominieren)"
        zeilen.append(f"VWAP: {d}")
    return "   |   ".join(zeilen)


def render(fig, ax_price, ax_vol, symbol, interval="1h", days=60,
           show_trades=True, chart_data=None, root=None, indicators=None):
    """Zeichnet den Kerzen-Chart in die uebergebenen Achsen.
    Gibt eine kurze Info-Zeile zurueck (fuer die Status-Leiste)."""
    root = root or _project_root()
    if chart_data is None:
        from features.chart_data import ChartData
        chart_data = ChartData(root)

    rows = chart_data.load(symbol, interval=interval, days=days)
    df = candles_to_df(rows)
    ax_price.clear()
    ax_vol.clear()
    if df.empty:
        ax_price.text(0.5, 0.5, "Keine Daten - 'Aktualisieren' druecken",
                      ha="center", va="center", color="#888", transform=ax_price.transAxes)
        return "Keine Kerzendaten im Cache."

    # Dunkler Hintergrund auf BEIDEN Achsen erzwingen (sonst weiss)
    ax_price.set_facecolor("#0e0e10")
    ax_vol.set_facecolor("#0e0e10")
    mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350",
                               edge="inherit", wick="inherit", volume="in")
    style = mpf.make_mpf_style(base_mpf_style="nightclouds", marketcolors=mc,
                               facecolor="#0e0e10", edgecolor="#0e0e10",
                               gridcolor="#1c1c22", figcolor="#0e0e10",
                               rc={"axes.edgecolor": "#333"})

    mpf.plot(df, type="candle", ax=ax_price, volume=ax_vol, style=style,
             datetime_format="%m-%d", xrotation=0, show_nontrading=False,
             warn_too_much_data=100000, tight_layout=False)
    ax_price.set_facecolor("#0e0e10")
    ax_vol.set_facecolor("#0e0e10")

    ax_price.set_ylabel("Preis (USDT)", color="#aaa", fontsize=8)
    ax_vol.set_ylabel("Vol", color="#aaa", fontsize=8)
    ax_price.tick_params(colors="#888", labelsize=7)
    ax_vol.tick_params(colors="#888", labelsize=7)

    # === Indikatoren ueber die Kerzen zeichnen ===
    aktiv = indicators or []
    n = len(df)
    xr = range(n)
    if "ema" in aktiv:
        ax_price.plot(xr, ema(df["Close"], 20).values, color="#42a5f5", lw=1.1, label="EMA20")
        ax_price.plot(xr, ema(df["Close"], 50).values, color="#ffa726", lw=1.1, label="EMA50")
    if "boll" in aktiv:
        up, mid, lo = bollinger(df["Close"])
        ax_price.plot(xr, up.values, color="#888", lw=0.8, ls="--")
        ax_price.plot(xr, lo.values, color="#888", lw=0.8, ls="--")
        ax_price.fill_between(xr, lo.values, up.values, color="#888", alpha=0.06)
    if "vwap" in aktiv:
        ax_price.plot(xr, vwap(df).values, color="#ab47bc", lw=1.0, label="VWAP")
    if aktiv and any(k in aktiv for k in ("ema", "vwap")):
        leg = ax_price.legend(loc="upper left", fontsize=7, facecolor="#141417",
                              edgecolor="#333", labelcolor="#ccc")

    info = f"{symbol}  {interval}  |  {len(df)} Kerzen  |  {df.index[0]:%d.%m} - {df.index[-1]:%d.%m}"
    expl = erklaere_indikatoren(df, aktiv)
    if expl:
        info += "\n" + expl

    # === DEINE echten Trades als Marker ===
    if show_trades:
        trades = load_trades_for(symbol, root)
        chart_start = df.index[0]
        chart_end = df.index[-1]
        buys = [t for t in trades if t["side"] == "BUY"
                and chart_start <= t["time"] <= chart_end]
        sells = [t for t in trades if t["side"] == "SELL"
                 and chart_start <= t["time"] <= chart_end]
        # x-Position = Index-Nummer der naechsten Kerze (mplfinance nutzt 0..N-1)
        def xpos(when):
            pos = df.index.get_indexer([when], method="nearest")
            return pos[0] if len(pos) else None

        for t in buys:
            x = xpos(t["time"])
            if x is not None:
                ax_price.scatter(x, t["price"], marker="^", s=60,
                                 color="#26a69a", edgecolors="white",
                                 linewidths=0.5, zorder=5)
        for t in sells:
            x = xpos(t["time"])
            if x is not None:
                col = "#ef5350" if t["pnl"] < 0 else "#ffd54f"
                ax_price.scatter(x, t["price"], marker="v", s=60,
                                 color=col, edgecolors="white",
                                 linewidths=0.5, zorder=5)
        _hover = []
        for _t in buys:
            _x = xpos(_t["time"])
            if _x is not None:
                _hover.append((_x, _t["price"], "KAUF", _t.get("pnl", 0), _t["time"]))
        for _t in sells:
            _x = xpos(_t["time"])
            if _x is not None:
                _hover.append((_x, _t["price"], "VERKAUF", _t.get("pnl", 0), _t["time"]))
        ax_price._hover_markers = _hover
        try:
            _setup_hover(fig, ax_price)
        except Exception:
            pass
        info += f"  |  Trades: {len(buys)} Kauf / {len(sells)} Verkauf"

    return info


def _setup_hover(fig, ax_price):
    """Hover-Tooltip ueber Kauf-/Verkauf-Markern: Seite, Preis, Zeit, P&L."""
    annot = ax_price.annotate(
        "", xy=(0, 0), xytext=(14, 14), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.5", fc="#141417", ec="#42a5f5", lw=1.2),
        color="#eee", fontsize=8, ha="left", zorder=12,
        arrowprops=dict(arrowstyle="->", color="#42a5f5", lw=1))
    annot.set_visible(False)
    ax_price._hover_annot = annot
    ax_price._hover_last = None

    if getattr(fig, "_hover_connected", False):
        return
    fig._hover_connected = True

    def _on_move(event):
        try:
            annot = getattr(ax_price, "_hover_annot", None)
            markers = getattr(ax_price, "_hover_markers", [])
            if annot is None:
                return
            if event.inaxes is not ax_price or not markers:
                if annot.get_visible():
                    annot.set_visible(False)
                    ax_price._hover_last = None
                    fig.canvas.draw_idle()
                return
            best, best_d = None, 1e18
            for m in markers:
                px, py = ax_price.transData.transform((m[0], m[1]))
                d = (px - event.x) ** 2 + (py - event.y) ** 2
                if d < best_d:
                    best_d, best = d, m
            if best is not None and best_d <= 196:
                if ax_price._hover_last is best and annot.get_visible():
                    return
                x, price, side, pnl, when = best
                try:
                    zeit = when.strftime("%d.%m. %H:%M")
                except Exception:
                    zeit = str(when)[:16]
                pnl_s = ("\nP&L: %+.2f$" % pnl) if side == "VERKAUF" else ""
                annot.xy = (x, price)
                annot.set_text("%s\nPreis: %s\n%s%s" % (
                    side, format(price, ",.4f"), zeit, pnl_s))
                annot.set_visible(True)
                ax_price._hover_last = best
                fig.canvas.draw_idle()
            else:
                if annot.get_visible():
                    annot.set_visible(False)
                    ax_price._hover_last = None
                    fig.canvas.draw_idle()
        except Exception:
            pass

    fig.canvas.mpl_connect("motion_notify_event", _on_move)


if __name__ == "__main__":
    # Standalone-Test: rendert in eine PNG-Datei (kein GUI noetig)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (axp, axv) = plt.subplots(2, 1, figsize=(11, 5),
                                   gridspec_kw={"height_ratios": [4, 1]})
    fig.patch.set_facecolor("#0e0e10")
    msg = render(fig, axp, axv, "BTC/USDC", interval="1h", days=30)
    print(msg)
    out = os.path.join(_project_root(), "data_store", "charts", "_test_render.png")
    fig.savefig(out, facecolor="#0e0e10", dpi=90)
    print("Test-Chart gespeichert:", out)
