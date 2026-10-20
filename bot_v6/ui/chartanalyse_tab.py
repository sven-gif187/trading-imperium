# -*- coding: utf-8 -*-
"""CHARTANALYSE-Tab - reine Anzeige, kein Einfluss auf den Handel.

[CHARTANALYSE-TAB 07.08.2026]

Zeigt, was features/chartanalyse.py aus dem aktuellen Chart liest:
Unterstuetzungs- und Widerstandszonen, Trendstruktur, erkannte Formationen,
Fibonacci-Ziele und ein daraus abgeleitetes Einstiegssignal mit Stop und Ziel.

REINE ANZEIGE. Dieser Tab loest keinen Kauf und keinen Verkauf aus und wird
von keinem Handelspfad importiert - wie die uebrigen vier Tabs bleibt er
Beobachtungsdeck. Die Signale werden ausschliesslich gemessen, damit ueber
Wochen belegbar wird, ob sie ueberhaupt treffen.

Unten steht das Backtest-Ergebnis aus data_store/telemetrie.db - erzeugt von
chartanalyse_backtest.py. Es zeigt bewusst auch dann die Wahrheit, wenn sie
unbequem ist: eine hohe Trefferquote bei negativem Erwartungswert ist kein
gutes Signal, sondern ein teures.
"""
import os
import sqlite3

import customtkinter as ctk

CLR_CARD = "#16161a"
CLR_BORDER = "#2a2a30"
CLR_GRUEN = "#22c55e"
CLR_ROT = "#ef4444"
CLR_GELB = "#eab308"
CLR_DIM = "#888"
CLR_TXT = "#ddd"
# [27.08.2026] Fibonacci-Violett. Gruen und Rot sind an die Zonen
# vergeben, Weiss an die Jetzt-Linie, Grau an das Gitter. Violett ist
# die einzige Farbe, die daneben noch eigenstaendig bleibt - auch bei
# Rot-Gruen-Schwaeche, anders als ein Gelb oder Orange.
CLR_FIB = "#a78bfa"

# Bollinger-Blau. Gruen und Rot gehoeren den Zonen, Violett dem
# Fibonacci, Weiss der Jetzt-Linie, Grau dem Gitter. Blau ist die letzte
# Farbe, die daneben noch eigenstaendig bleibt.
CLR_BOLL = "#38bdf8"

# Bollinger-Einstellungen. 20 Perioden, 2 Standardabweichungen - die
# Standardwerte, dieselben wie in features/chart_view.py:91 und dieselben,
# die Mark in seinen Charts benutzt. Wer sie hier aendert, aendert nur die
# ANZEIGE; die Rechnung in chart_view.py bleibt davon unberuehrt.
BOLL_PERIODE = 20
BOLL_ABWEICHUNG = 2.0

# Wieviele Kerzen der Chart zeigt. Diese Zahl steht bewusst NUR HIER:
# sie bestimmt den Bildausschnitt UND die Fibonacci-Anker. Standen beide
# getrennt (150 im Bild, 300 in der Rechnung), lagen elf von dreizehn
# Stufen ausserhalb des Bildrands - gemessen am 27.08.2026.
ZEIGE_KERZEN = 150

_STATE = {"coin": "BTC/USDC", "tf": "1h"}


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db():
    return os.path.join(_root(), "data_store", "telemetrie.db")


# ============================================================
# Daten
# ============================================================
def _hole_df(engine, coin, tf):
    """Kerzen besorgen - erst ueber den Bot, sonst direkt von der Boerse."""
    try:
        snap = engine.data_agent.fetch_snapshot(coin, tf)
        df = getattr(snap, "_df", None)
        if df is not None and len(df) >= 60:
            return df
    except Exception:
        pass
    try:
        import ccxt
        import pandas as pd
        roh = ccxt.binance({"enableRateLimit": True}).fetch_ohlcv(coin, tf, limit=300)
        return pd.DataFrame(roh, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    except Exception:
        return None


def _backtest_zahlen():
    """Letzte Backtest-Laeufe aus der Datenbank."""
    p = _db()
    if not os.path.exists(p):
        return []
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        r = con.execute(
            "SELECT symbol,timeframe,signale,treffer,quote_pct,ev_netto_pct,"
            "kosten_pct,ts_utc FROM chart_laeufe ORDER BY ts_utc DESC LIMIT 8"
        ).fetchall()
        con.close()
        return [dict(z) for z in r]
    except Exception:
        return []


def _signalarten():
    p = _db()
    if not os.path.exists(p):
        return []
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        r = con.execute(
            "SELECT signal, COUNT(*) n, SUM(ergebnis='ZIEL') treffer, "
            "AVG(rendite_netto) ev FROM chart_signale GROUP BY signal "
            "ORDER BY n DESC").fetchall()
        con.close()
        return [dict(z) for z in r]
    except Exception:
        return []


# ============================================================
# Grafik
# ============================================================
def _spanne(werte):
    """Kleinste und groesste Zahl, oder (0,1) wenn nichts da ist."""
    if not werte:
        return 0.0, 1.0
    return min(werte), max(werte)


def _entzerre(marken, mindest=13.0, oben=6.0, unten=None):
    """Beschriftungen auseinanderschieben, damit keine die andere ueberdeckt.

    [LESBARKEIT 19.08.2026] Sven: "beim Analyse-Tab ist es schwer was zu
    erkennen". Auf dem Bild standen acht Preismarken in rund 110 Pixeln
    uebereinander - lesbar war keine.

    marken: Liste von [y, ...] - die Listen werden an Stelle 0 veraendert.
    Verfahren: nach y sortieren, von oben nach unten durchgehen und jede
    Marke nach unten schieben, die ihrer Vorgaengerin zu nahe kommt. Danach
    dasselbe von unten nach oben, damit unten nichts aus dem Bild faellt.
    """
    if not marken:
        return marken
    marken.sort(key=lambda m: m[0])
    letzte = oben - mindest
    for m in marken:
        if m[0] < letzte + mindest:
            m[0] = letzte + mindest
        letzte = m[0]
    if unten is not None and marken[-1][0] > unten:
        letzte = unten + mindest
        for m in reversed(marken):
            if m[0] > letzte - mindest:
                m[0] = letzte - mindest
            letzte = m[0]
    return marken


def _nette_schritte(lo, hi, wunsch=6):
    """Runde Preisstufen fuer die Achse (1 / 2 / 2,5 / 5 mal Zehnerpotenz)."""
    import math
    spanne = max(hi - lo, 1e-9)
    roh = spanne / max(1, wunsch)
    stelle = 10 ** math.floor(math.log10(roh))
    for f in (1, 2, 2.5, 5, 10):
        if roh <= stelle * f:
            schritt = stelle * f
            break
    else:
        schritt = stelle * 10
    start = math.ceil(lo / schritt) * schritt
    raus = []
    w = start
    while w <= hi and len(raus) < 20:
        raus.append(w)
        w += schritt
    return raus


def _blass(hexfarbe, anteil=0.45):
    """Dieselbe Farbe, nur zum Hintergrund hin abgeschwaecht.

    Fuer schwache Zonen: sie sollen sichtbar bleiben, aber nicht mit den
    starken um Aufmerksamkeit streiten.
    """
    try:
        r = int(hexfarbe[1:3], 16); g = int(hexfarbe[3:5], 16)
        bl = int(hexfarbe[5:7], 16)
        hg = (13, 13, 15)                      # #0d0d0f, der Chartgrund
        m = lambda a, b2: int(b2 + (a - b2) * anteil)
        return "#%02x%02x%02x" % (m(r, hg[0]), m(g, hg[1]), m(bl, hg[2]))
    except Exception:
        return hexfarbe


def _zeichne(canvas, df, analyse):
    """Kerzenchart mit Preisachse, Zeitachse und entzerrten Zonenmarken.

    [UMBAU 19.08.2026] Vorher: eine duenne weisse Linie, darueber breite
    Farbbaender ueber die volle Breite, und rechts acht Preismarken
    uebereinander. Drei Fehler auf einmal -

      1. Die Skala richtete sich nach den ZONEN, nicht nach dem Kurs.
         Lagen Zonen weit weg, wurde die eigentliche Kursbewegung auf
         wenige Pixel zusammengedrueckt.
      2. Die Zonen waren gefuellte Rechtecke ueber die ganze Breite -
         der Kurs verschwand darin.
      3. Die Beschriftungen ueberlappten sich.

    Jetzt: echte Kerzen wie in den Charts von Mark und Tilo, Preisachse
    rechts mit runden Stufen, Zeitachse unten, Zonen als duenne Linie mit
    zartem Band, und keine Beschriftung mehr auf einer anderen.

    Bleibt reine Anzeige - dieser Tab loest keinen Handel aus.
    """
    canvas.delete("all")
    if df is None or analyse is None or len(df) < 10:
        canvas.create_text(20, 20, anchor="w", fill=CLR_DIM,
                           text="Keine Daten", font=("Consolas", 11))
        return
    b = int(canvas.winfo_width() or 1200)
    h = int(canvas.winfo_height() or 420)
    if b < 120 or h < 120:
        return

    zeige = df.tail(ZEIGE_KERZEN)
    try:
        opens = [float(x) for x in zeige["Open"]]
        highs = [float(x) for x in zeige["High"]]
        lows = [float(x) for x in zeige["Low"]]
    except Exception:
        opens = highs = lows = None
    kurse = [float(x) for x in zeige["Close"]]
    n = len(kurse)
    if opens is None or len(opens) != n:
        opens, highs, lows = kurse, kurse, kurse      # Notfall: nur Linie

    # --- 1. Skala: der KURS bestimmt sie, nicht die Zonen ---
    lo, hi = min(lows), max(highs)
    puffer = (hi - lo) * 0.06 or (hi * 0.001)
    lo, hi = lo - puffer, hi + puffer
    # Zonen duerfen die Skala nur leicht dehnen (hoechstens ein Drittel),
    # damit eine weit entfernte Zone die Kursbewegung nicht plattdrueckt.
    grenze = (hi - lo) * 0.33
    for z in analyse.zonen:
        if lo - grenze <= z.preis <= hi + grenze:
            hi, lo = max(hi, z.bis), min(lo, z.von)
    spanne = (hi - lo) or 1.0

    rand_l, rand_r, rand_o, rand_u = 10, 96, 12, 48

    def y(p):
        return rand_o + (hi - p) / spanne * (h - rand_o - rand_u)

    def x(i):
        return rand_l + (i + 0.5) / max(1, n) * (b - rand_l - rand_r)

    # --- 2. Zonenmarken zuerst berechnen (gezeichnet werden sie ganz zum
    #        Schluss). Nur so weiss die Preisachse, wo schon etwas steht.
    marken = []
    for z in analyse.zonen:
        if not (lo <= z.preis <= hi):
            continue
        # [19.08.2026] Starke Zonen kraeftig, schwache blass. Vorher waren
        # alle gleich laut - neun Linien in derselben Staerke ergeben eine
        # Wand, in der die wichtige nicht mehr auffaellt. Mark und Tilo
        # zeichnen in ihren Charts genau drei bis vier Linien kraeftig ein,
        # der Rest ist Andeutung.
        stark = float(getattr(z, "staerke", 0) or 0) >= 0.6
        grund = CLR_GRUEN if z.art == "SUPPORT" else CLR_ROT
        marken.append([y(z.preis), grund if stark else _blass(grund),
                       format(z.preis, ",.0f") + "  " + z.quelle[:4].lower()])
    # [FIBONACCI 27.08.2026] Marks Stufen mit in die Marken, BEVOR entzerrt
    # wird - sonst legen sie sich auf die Zonenbeschriftungen.
    #
    # Nur die Anker (0 und 1) und die drei viel benutzten Stufen bekommen
    # eine Beschriftung. Alle dreizehn zu beschriften ergaebe genau die
    # Textwand, gegen die am 19.08. schon einmal aufgeraeumt wurde.
    _fib = getattr(analyse, "fibonacci", None) or {}
    for _r, _p, _art in _fib.get("stufen", []):
        if not (lo <= _p <= hi):
            continue
        if _art == "anker" or _r in (0.382, 0.5, 0.618):
            _txt = ("%.3f" % _r).rstrip("0").rstrip(".").replace(".", ",")
            marken.append([y(_p), CLR_FIB if _art == "anker" else _blass(CLR_FIB),
                           _txt + "  " + format(_p, ",.0f")])

    _entzerre(marken, mindest=13.0, oben=rand_o + 6, unten=h - rand_u - 6)
    belegt = [m[0] for m in marken] + [y(kurse[-1])]

    # --- 3. Preisachse rechts mit runden Stufen + waagerechtem Raster ---
    #
    # [19.08.2026] Die Achsenzahl wird WEGGELASSEN, wo schon eine Zonenmarke
    # steht. Beides nebeneinander war auf dem Bild vom 19.08. der Grund,
    # warum rechts nichts mehr zu lesen war - und die Zonenmarke traegt
    # ihren Preis ohnehin bei sich, es geht also nichts verloren.
    for w in _nette_schritte(lo, hi):
        yy = y(w)
        canvas.create_line(rand_l, yy, b - rand_r, yy, fill="#1c1c22")
        if any(abs(yy - bb) < 12 for bb in belegt):
            continue
        canvas.create_text(b - rand_r + 6, yy, anchor="w", fill="#6b7280",
                           font=("Consolas", 9), text=format(w, ",.0f"))

    # --- 3. Zeitachse unten ---
    try:
        stempel = list(zeige.index)
    except Exception:
        stempel = []
    if stempel:
        for i in range(0, n, max(1, n // 6)):
            try:
                txt = stempel[i].strftime("%d.%m %H:%M")
            except Exception:
                continue
            canvas.create_line(x(i), rand_o, x(i), h - rand_u, fill="#17171d")
            # Am Rand nach innen ausrichten, sonst wird die Beschriftung
            # abgeschnitten - auf dem Bild vom 19.08. stand links "08 14:00".
            anker = "nw" if i < n * 0.06 else ("ne" if i > n * 0.94 else "n")
            canvas.create_text(x(i), h - rand_u + 6, anchor=anker,
                               fill="#6b7280", font=("Consolas", 9), text=txt)

    # --- 4. Zonen: duenne Linie mit zartem Band, Kurs bleibt sichtbar ---
    for z in analyse.zonen:
        if not (lo <= z.preis <= hi):
            continue
        stark = float(getattr(z, "staerke", 0) or 0) >= 0.6
        grund = CLR_GRUEN if z.art == "SUPPORT" else CLR_ROT
        farbe = grund if stark else _blass(grund)
        dyn = z.quelle.startswith("EMA")
        if stark and not dyn and z.bis > z.von:
            # [19.08.2026] Hoehe begrenzen. Eine Zone kann breit sein
            # (z.von bis z.bis); auf dem Bild vom 19.08. ueberlappten sich
            # acht solcher Baender zu einer grauen Flaeche, in der die
            # Kerzen verschwanden. Das Band zeigt jetzt die Lage, nicht
            # die volle Breite - die steht ohnehin im Text darunter.
            _o, _u = y(z.bis), y(z.von)
            if _u - _o > 7:
                _m = (_o + _u) / 2.0
                _o, _u = _m - 3.5, _m + 3.5
            canvas.create_rectangle(rand_l, _o, b - rand_r, _u,
                                    fill=farbe, outline="", stipple="gray12")
        canvas.create_line(rand_l, y(z.preis), b - rand_r, y(z.preis),
                           fill=farbe, width=2 if stark else 1,
                           dash=(4, 4) if dyn else None)

    # --- 4b. Fibonacci nach Marks Verfahren -------------------------
    #
    # [27.08.2026] Bewusst VOR den Kerzen gezeichnet: Die Kerzen kommen
    # danach darueber und bleiben lesbar. Dieselbe Lehre wie am 19.08.,
    # als gefuellte Zonenbaender den Kursverlauf verschluckt haben.
    #
    # Drei Staerken, damit dreizehn Linien kein Gitter ergeben:
    #   anker (0 und 1)  durchgezogen, kraeftig  - die Bewegung selbst
    #   rueck            duenn gestrichelt       - die Rueckzugsmarken
    #   vor              ganz blass gepunktet    - die Verlaengerungen
    if _fib.get("stufen"):
        for _r, _p, _art in _fib["stufen"]:
            if not (lo <= _p <= hi):
                continue
            if _art == "anker":
                canvas.create_line(rand_l, y(_p), b - rand_r, y(_p),
                                   fill=CLR_FIB, width=2)
            elif _art == "rueck":
                canvas.create_line(rand_l, y(_p), b - rand_r, y(_p),
                                   fill=_blass(CLR_FIB, 0.55), width=1,
                                   dash=(5, 5))
            else:
                canvas.create_line(rand_l, y(_p), b - rand_r, y(_p),
                                   fill=_blass(CLR_FIB, 0.3), width=1,
                                   dash=(2, 6))
        # Die Spanne, aus der alles gerechnet ist - links klein dazu.
        canvas.create_text(rand_l + 4, rand_o + 2, anchor="nw",
                           fill=_blass(CLR_FIB, 0.7), font=("Consolas", 8),
                           text="Fib %s  %s - %s"
                                % (_fib.get("richtung", "?"),
                                   format(_fib["tief"], ",.0f"),
                                   format(_fib["hoch"], ",.0f")))

    # --- 4c. Bollinger-Baender -------------------------------------
    #
    # [29.08.2026] Svens Wunsch vom 26.08. Anders als Zonen und Fibonacci
    # sind das KURVEN, die dem Kurs folgen - deshalb Polygonzuege statt
    # waagerechter Linien.
    #
    # Gerechnet wird auf dem VOLLEN df, angezeigt nur der sichtbare
    # Ausschnitt. Andernfalls waeren die ersten 20 Punkte im Bild leer,
    # weil ein gleitender Durchschnitt ueber 20 Kerzen erst ab der
    # zwanzigsten einen Wert hat.
    #
    # Vor den Kerzen gezeichnet - dieselbe Lehre wie am 19.08.: was nach
    # dem Kurs kommt, verdeckt ihn.
    if len(df) >= BOLL_PERIODE + 2:
        try:
            _mid = df["Close"].rolling(BOLL_PERIODE).mean()
            _std = df["Close"].rolling(BOLL_PERIODE).std()
            _ob = (_mid + BOLL_ABWEICHUNG * _std).tail(n).tolist()
            _mi = _mid.tail(n).tolist()
            _un = (_mid - BOLL_ABWEICHUNG * _std).tail(n).tolist()
        except Exception:
            _ob = _mi = _un = []

        def _zug(werte, farbe, breite, strich=None):
            """Einen Polygonzug zeichnen - Luecken (NaN) unterbrechen ihn.

            Ein durchgezogener Strich ueber eine Luecke hinweg wuerde eine
            Verbindung behaupten, die es nicht gibt.
            """
            teil = []
            for i, w in enumerate(werte):
                gut = w is not None and w == w        # NaN ist nie gleich sich selbst
                if gut and lo <= w <= hi:
                    teil += [x(i), y(w)]
                else:
                    if len(teil) >= 4:
                        canvas.create_line(*teil, fill=farbe, width=breite,
                                           dash=strich, smooth=False)
                    teil = []
            if len(teil) >= 4:
                canvas.create_line(*teil, fill=farbe, width=breite,
                                   dash=strich, smooth=False)

        if _ob and _un:
            _zug(_ob, _blass(CLR_BOLL, 0.75), 1)
            _zug(_un, _blass(CLR_BOLL, 0.75), 1)
            # Die Mitte ist ein gleitender Durchschnitt und blasser -
            # sie ist die Orientierung, nicht das Signal.
            _zug(_mi, _blass(CLR_BOLL, 0.35), 1, (3, 5))

    # --- 5. Kerzen ---
    breite = max(1.0, (b - rand_l - rand_r) / max(1, n) * 0.62)
    for i in range(n):
        o, c = opens[i], kurse[i]
        steigt = c >= o
        farbe = "#26a69a" if steigt else "#ef5350"
        xi = x(i)
        canvas.create_line(xi, y(highs[i]), xi, y(lows[i]), fill=farbe, width=1)
        yo, yc = y(o), y(c)
        if abs(yo - yc) < 1:
            canvas.create_line(xi - breite / 2, yo, xi + breite / 2, yo,
                               fill=farbe, width=1)
        else:
            canvas.create_rectangle(xi - breite / 2, min(yo, yc),
                                    xi + breite / 2, max(yo, yc),
                                    fill=farbe, outline=farbe)

    # --- 6. Stop und Ziel des aktuellen Vorschlags ---
    for wert, farbe, name in ((analyse.vorschlag_stop, CLR_ROT, "STOP"),
                              (analyse.vorschlag_ziel, CLR_GRUEN, "ZIEL")):
        if wert and lo <= wert <= hi:
            canvas.create_line(rand_l, y(wert), b - rand_r, y(wert),
                               fill=farbe, width=2, dash=(7, 4))
            # [19.08.2026] Die Beschriftung bekommt einen dunklen Grund.
            # Vorher stand sie direkt auf den Kerzen am linken Rand und war
            # dort nicht zu entziffern - auf Svens Tages-Chart lagen "STOP
            # 67.601" und "ZIEL 70.242" mitten im Kerzengewimmel vom Maerz.
            _t = name + " " + format(wert, ",.0f")
            _x, _y = rand_l + 6, y(wert) - 9
            canvas.create_rectangle(_x - 3, _y - 7, _x + 7 * len(_t), _y + 7,
                                    fill="#0d0d0f", outline="")
            canvas.create_text(_x, _y, anchor="w", fill=farbe,
                               font=("Consolas", 9, "bold"), text=_t)

    # --- 7. Aktueller Kurs: eigene Marke, damit man ihn sofort findet ---
    jetzt = kurse[-1]
    yj = y(jetzt)
    canvas.create_line(rand_l, yj, b - rand_r, yj, fill="#e5e7eb", width=1,
                       dash=(2, 4))
    canvas.create_rectangle(b - rand_r + 2, yj - 8, b - 2, yj + 8,
                            fill="#e5e7eb", outline="")
    canvas.create_text(b - rand_r + 6, yj, anchor="w", fill="#0d0d0f",
                       font=("Consolas", 9, "bold"), text=format(jetzt, ",.0f"))

    # --- 8. Zonenmarken an den rechten Rand (Lage steht schon fest) ---
    for yy, farbe, txt in marken:
        if abs(yy - yj) < 12:
            continue                      # nicht ueber die Kursmarke schreiben
        canvas.create_text(b - rand_r + 6, yy, anchor="w", fill=farbe,
                           font=("Consolas", 9), text=txt)

    # --- 9. Legende, zweizeilig ---
    #
    # [27.08.2026] Einzeilig ging nicht mehr: mit dem Fibonacci-Teil misst
    # der Text 1596 px, der Chart ist rund 1090 px breit - der Rest waere
    # unsichtbar abgeschnitten worden. Nachgemessen mit tkinter.font,
    # nicht geschaetzt. Die zweite Zeile passt in den unteren Rand (48 px),
    # ohne die Zeitachse zu beruehren.
    canvas.create_text(rand_l + 4, h - 20, anchor="w", fill=CLR_DIM,
                       font=("Consolas", 9),
                       text=str(n) + " Kerzen   ·   gruen = Unterstuetzung, "
                            "rot = Widerstand   ·   durchgezogen = Swing-Zone, "
                            "gestrichelt = gleitender Durchschnitt")
    if _fib.get("stufen"):
        canvas.create_text(rand_l + 4, h - 7, anchor="w",
                           fill=_blass(CLR_FIB, 0.75), font=("Consolas", 9),
                           text="violett = Fibonacci   ·   kraeftig = Hoch und Tief, "
                                "gestrichelt = Rueckzugsmarke, "
                                "gepunktet = Verlaengerung")
    canvas.create_text(b - rand_r, h - 7, anchor="e",
                       fill=_blass(CLR_BOLL, 0.8), font=("Consolas", 9),
                       text="blau = Bollinger (%d/%g)" % (BOLL_PERIODE, BOLL_ABWEICHUNG))


# ============================================================
# Aufbau
# ============================================================
def build_chartanalyse_tab(parent, engine):
    kopf = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=8)
    kopf.pack(fill="x", padx=6, pady=(6, 3))

    ctk.CTkLabel(kopf, text="📐 CHARTANALYSE", font=("Arial", 13, "bold"),
                 text_color=CLR_GELB).pack(side="left", padx=10, pady=6)
    ctk.CTkLabel(kopf, text="reine Anzeige und Messung - loest keinen Handel aus",
                 font=("Arial", 10), text_color=CLR_DIM).pack(side="left", padx=4)

    coin_var = ctk.StringVar(value=_STATE["coin"])
    tf_var = ctk.StringVar(value=_STATE["tf"])
    try:
        coins = list(engine.config.trading.coins)[:6] or ["BTC/USDC"]
    except Exception:
        coins = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]

    status = ctk.CTkLabel(kopf, text="", font=("Consolas", 10),
                          text_color=CLR_DIM)
    status.pack(side="right", padx=10)

    body = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    body.pack(expand=True, fill="both", padx=6, pady=3)

    canvas = ctk.CTkCanvas(body, height=420, bg="#0d0d0f", highlightthickness=1,
                           highlightbackground=CLR_BORDER)
    canvas.pack(fill="x", pady=(2, 6))

    info = ctk.CTkLabel(body, text="", font=("Consolas", 11), justify="left",
                        anchor="w", text_color=CLR_TXT)
    info.pack(fill="x", padx=4, pady=2)

    mess = ctk.CTkLabel(body, text="", font=("Consolas", 10), justify="left",
                        anchor="w", text_color=CLR_DIM)
    mess.pack(fill="x", padx=4, pady=(8, 4))

    def aktualisieren(*_):
        _STATE["coin"], _STATE["tf"] = coin_var.get(), tf_var.get()
        status.configure(text="rechne ...")
        parent.update_idletasks()
        try:
            from features.chartanalyse import analysiere
            df = _hole_df(engine, _STATE["coin"], _STATE["tf"])
            if df is None:
                info.configure(text="Keine Kursdaten verfuegbar.")
                status.configure(text="")
                return
            a = analysiere(df, _STATE["coin"], _STATE["tf"],
                           fib_rueckblick=ZEIGE_KERZEN)
            if a is None:
                info.configure(text="Zu wenig Kerzen fuer eine Analyse.")
                status.configure(text="")
                return
            _zeichne(canvas, df, a)
            info.configure(text=_text(a))
            mess.configure(text=_messtext())
            status.configure(text=f"Stand {_STATE['coin']} {_STATE['tf']}")
        except Exception as e:
            info.configure(text=f"Analyse fehlgeschlagen: {e}")
            status.configure(text="Fehler")

    ctk.CTkOptionMenu(kopf, variable=coin_var, values=coins, width=120,
                      height=26, font=("Arial", 10),
                      command=aktualisieren).pack(side="left", padx=(14, 4))
    ctk.CTkOptionMenu(kopf, variable=tf_var, values=["15m", "30m", "1h", "4h", "1d", "1w", "1M"],
                      width=70, height=26, font=("Arial", 10),
                      command=aktualisieren).pack(side="left", padx=4)
    ctk.CTkButton(kopf, text="Neu berechnen", width=110, height=26,
                  font=("Arial", 10), command=aktualisieren).pack(side="left", padx=6)

    parent.after(700, aktualisieren)


def _zeile(x, preis):
    """Eine Zonenzeile. Merkt an, wenn die Zone die Seite gewechselt hat."""
    # Eine aus Tiefpunkten gebildete Zone (SUPPORT), die jetzt UEBER dem
    # Kurs liegt, wurde durchbrochen und wirkt fortan als Widerstand -
    # und umgekehrt. In der Chartlehre heisst das Polaritaetswechsel.
    gewechselt = ((x.art == "SUPPORT" and x.preis > preis)
                  or (x.art == "RESISTANCE" and x.preis < preis))
    hinweis = "   (durchbrochen)" if gewechselt else ""
    return (f"    {x.preis:>12,.2f}   {x.treffer}x beruehrt   "
            f"Staerke {x.staerke:.0%}{hinweis}")


def _text(a):
    z = [x for x in a.zonen if x.quelle == "SWING"]
    # [FIX 17.08.2026] Vorher wurde nach ZONENTYP getrennt und trotzdem
    # "ueber dem Kurs" / "unter dem Kurs" darueber geschrieben. Sobald der
    # Kurs durch eine alte Unterstuetzung faellt, bleibt diese vom Typ her
    # SUPPORT - steht aber ueber dem Kurs. Genau das war am 17.08. zu
    # sehen: Preis 63.129, darunter drei "Unterstuetzungen" bei 64.814,
    # 64.438 und 64.124, also allesamt DARUEBER.
    # Jetzt entscheidet die LAGE ZUM KURS, nicht der Typ - und wo beides
    # auseinanderfaellt, steht "(durchbrochen)" dabei.
    ueber = sorted([x for x in z if x.preis > a.preis], key=lambda x: x.preis)[:3]
    unter = sorted([x for x in z if x.preis < a.preis], key=lambda x: -x.preis)[:3]

    t = [f"  Preis {a.preis:,.2f}   Trend {a.trend}   Schwankung (ATR) {a.atr:,.2f}", ""]
    t.append("  WIDERSTAENDE (ueber dem Kurs)")
    t += [_zeile(x, a.preis) for x in ueber] or ["    keine erkannt"]
    t.append("")
    t.append("  UNTERSTUETZUNGEN (unter dem Kurs)")
    t += [_zeile(x, a.preis) for x in unter] or ["    keine erkannt"]

    if a.formationen:
        t += ["", "  FORMATIONEN"]
        for f in a.formationen:
            ziel = f"  Ziel {f.kursziel:,.2f}" if f.kursziel else ""
            t.append(f"    {f.name:<14s} {f.richtung:<8s} Guete {f.guete:.0%}{ziel}")
            t.append(f"      {f.detail}")

    t += ["", f"  SIGNAL: {a.einstieg_signal}"]
    if a.einstieg_signal != "KEIN":
        t.append(f"    Guete       {a.einstieg_guete:.0%}")
        t.append(f"    Stop        {a.vorschlag_stop:,.2f}" if a.vorschlag_stop else "")
        t.append(f"    Ziel        {a.vorschlag_ziel:,.2f}" if a.vorschlag_ziel else "")
        if a.rr_verhaeltnis:
            t.append(f"    Chance/Risiko {a.rr_verhaeltnis:.2f}  "
                     f"(unter 1.5 lohnt sich nach Kosten selten)")
    t.append(f"    Begruendung: {a.begruendung}")
    return "\n".join(x for x in t if x != "")


def _messtext():
    laeufe = _backtest_zahlen()
    arten = _signalarten()
    if not laeufe and not arten:
        return ("\n  MESSUNG: noch kein Backtest gelaufen.\n"
                "  Starte:  python chartanalyse_backtest.py BTC/USDC 1h 1000\n")
    t = ["", "  " + "=" * 78,
         "  MESSUNG - trifft die Analyse ueberhaupt? (aus telemetrie.db)",
         "  " + "=" * 78, ""]
    if arten:
        t.append(f"    {'Signalart':<16s} {'n':>6s} {'Quote':>7s} {'EV netto':>10s}")
        t.append("    " + "-" * 44)
        for a in arten:
            q = (a["treffer"] or 0) / a["n"] * 100 if a["n"] else 0
            t.append(f"    {a['signal']:<16s} {a['n']:6d} {q:6.1f}% "
                     f"{a['ev'] or 0:+9.3f}%")
        t.append("")
        t.append("    EV netto = Erwartungswert je Signal NACH Handelskosten.")
        t.append("    Negativ heisst: die Regel kostet Geld, egal wie hoch die Quote ist.")
    if laeufe:
        t += ["", "    Letzte Laeufe:"]
        for l in laeufe[:5]:
            t.append(f"      {l['symbol']:<10s} {l['timeframe']:<4s} "
                     f"{l['signale']:5d} Signale  Quote {l['quote_pct']:5.1f}%  "
                     f"EV {l['ev_netto_pct']:+.3f}%  ({l['ts_utc'][:10]})")
    return "\n".join(t)
