# -*- coding: utf-8 -*-
"""
TERMINAL-Tab v2: Profi-Konsolen-Cockpit + Epochen-Kontrollzentrum.
[TERMINAL-TAB v3 17.07.2026] (inkl. v2+Scrollfix+Regime)
NEU in v2: E6.1-Epochen-Block (Sells/Tage/R/R/WR live), NOTAUS-NETZ-
Waechter, letzte 5 Verkaeufe mit Grund, Trail-Abstand pro Position
(E7-aware: erkennt automatisch ob E7 in exit_monitor.py installiert ist).
Read-only, alle Zugriffe defensiv, Refresh im Main-Thread via .after().
"""
import os
from datetime import datetime, date

REFRESH_MS = 2000
_SESSION_START = datetime.now()
_EQ_CACHE = {"t": 0.0, "serie": []}
_ERR = {"n": 0, "last": ""}          # [AUDIT 06.08.2026] Render-Fehler sichtbar machen


def _equity_serie():
    """Kapitalverlauf aus data_store/equity_history.json (30s-Cache)."""
    import time as _time, json as _json
    if _time.time() - _EQ_CACHE["t"] < 30:
        return _EQ_CACHE["serie"]
    serie = []
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data_store", "equity_history.json")
        serie = [float(x[1]) for x in _json.load(open(p, encoding="utf-8")).get("total", [])]
    except Exception:
        serie = []
    _EQ_CACHE["t"] = _time.time()
    _EQ_CACHE["serie"] = serie
    return serie


def _sparkline(vals, width=40):
    if len(vals) < 2:
        return ""
    vals = vals[-width:]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return "-" * len(vals)
    blocks = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    return "".join(blocks[int((v - lo) / (hi - lo) * 7)] for v in vals)


def _fg_label(v):
    try:
        v = int(v)
    except Exception:
        return "?"
    return ("Extreme Fear" if v < 25 else "Fear" if v < 45 else
            "Neutral" if v < 55 else "Greed" if v < 75 else "Extreme Greed")
E61_START = "2026-07-14"          # Exit-Einheit-Deploy = Messbeginn E6.1
E61_TAGE_ZIEL, E61_SELLS_ZIEL = 14, 15
E4_BASIS_RR = 0.48

C_HDR, C_LBL, C_POS, C_NEG, C_MAG, C_DIM, C_TXT, C_WRN = \
    "hdr", "lbl", "pos", "neg", "mag", "dim", "txt", "wrn"

_E7_INSTALLED = None


def _e7_installed():
    """Einmalig pruefen ob E7 im Monitor installiert ist (Marker-Lese)."""
    global _E7_INSTALLED
    if _E7_INSTALLED is None:
        try:
            p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "runtime", "exit_monitor.py")
            _E7_INSTALLED = "[E7 PHASEN-TRAILING" in open(p, encoding="utf-8").read()
        except Exception:
            _E7_INSTALLED = False
    return _E7_INSTALLED


def _f(v, nd=2):
    try:
        return f"{float(v):,.{nd}f}"
    except Exception:
        return "-"


def _usdc(engine):
    try:
        bal = engine.execution.get_balance()
        t = bal.get("total", {}) if bal else {}
        return float(t.get("USDC", 0)) + float(t.get("USDT", 0))
    except Exception:
        return 0.0


def _prices(engine):
    out = {}
    try:
        for sym, p in (engine.data_agent.price_cache or {}).items():
            if p:
                out[sym] = float(p)
                if "/" in sym:
                    out[sym.split("/")[0]] = float(p)
    except Exception:
        pass
    return out


def _price_alter(engine):
    """[TERMINAL-AMPEL] Alter des aeltesten Preises in Sekunden (None = unbekannt)."""
    try:
        da = engine.data_agent
        fn = getattr(da, "price_age", None)
        if not fn:
            return None
        alter = []
        for sym in (da.price_cache or {}):
            a = fn(sym)
            if a is not None:
                alter.append(a)
        return max(alter) if alter else None
    except Exception:
        return None


def _positions(engine):
    try:
        return {s: p for s, p in engine.risk_engine.open_positions.items()
                if p.get("active", False)}
    except Exception:
        return {}


def _journal_trades(engine):
    for attr in ("trade_journal", "journal", "_journal"):
        j = getattr(engine, attr, None)
        if j is None:
            continue
        try:
            t = j.get_all()
            if isinstance(t, list):
                return t
        except Exception:
            pass
        t = getattr(j, "_trades", None)
        if isinstance(t, list):
            return list(t)
    return []


def _realized(engine, trades):
    for attr in ("session_pnl", "_session_pnl", "realized_pnl", "_realized_pnl",
                 "total_pnl", "_total_pnl"):
        v = getattr(engine, attr, None)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    try:
        return sum(float(t.get("pnl", 0)) for t in trades if t.get("type") == "SELL")
    except Exception:
        return 0.0


def _journal_speicher(engine):
    """[AUDIT 06.08.2026] Sieht die Buchhaltung die Platte noch?

    Am 06.08.2026 schlug os.replace() auf trades_v5.json ueber eine Stunde
    fehl (WinError 5, Thread-Kollision). Der Fehler stand NUR im cmd-Fenster
    - kein Log, kein Waechter, kein UI. core/state_store.py meldet ihn jetzt;
    diese Zeile macht ihn im Terminal sichtbar.
    """
    try:
        st = engine.journal.speicher_status()
    except Exception:
        return None                      # alte Journal-Version: Zeile weglassen
    if not isinstance(st, dict):
        return None
    if st.get("gesund"):
        alter = st.get("alter_sec", -1)
        if st.get("gesamt"):
            return (f"OK (heute {st['gesamt']}x kollidiert, geloest)", C_WRN)
        return (f"OK{'' if alter < 0 else f' - zuletzt vor {alter}s'}", C_POS)
    return (f"!! {st.get('fehler_serie', '?')}x FEHLGESCHLAGEN - "
            f"Trades nur im RAM: {str(st.get('letzter', ''))[:40]}", C_NEG)


def _daily_loss(engine):
    """[AUDIT 06.08.2026] Echter Waechter-Stand statt Festtext.

    Vorher stand in der Risk-Zeile hart "Inaktiv (Datensammelphase)" -
    waehrend config.risk.daily_loss auf mode="aktiv"/limit_pct=6.0 steht
    und app.py den Waechter im Trading-Tick abfragt (_trading_tick ->
    portfolio.is_paused_by_daily_loss). Die Anzeige behauptete also das
    Gegenteil der Wirklichkeit. portfolio.daily_loss_status() war schon
    fuer genau diesen Zweck gebaut ("fuer UI/Terminal-Tab"), wurde aber
    nie gerufen. Read-only, keine Wirkung auf den Handel.
    """
    try:
        e = engine.portfolio.daily_loss_status() or {}
    except Exception as ex:
        return f"unbekannt ({str(ex)[:26]})", C_WRN
    if not e:
        return "unbekannt (Waechter antwortet nicht)", C_WRN
    modus = str(e.get("modus", "?"))
    if modus == "aus":
        return "AUS - kein Tagesverlust-Schutz", C_WRN
    txt = (f"-{float(e.get('verlust_pct', 0)):.1f}% von "
           f"{float(e.get('limit_pct', 0)):.0f}%  (Modus: {modus})")
    if e.get("limit_erreicht"):
        if modus == "aktiv":
            return txt + "  !! KAEUFE PAUSIERT !!", C_NEG
        return txt + "  (wuerde pausieren)", C_WRN
    return txt, C_POS if modus == "aktiv" else C_WRN


def _risk_params(engine):
    try:
        cycle = engine.state.get("cycle_phase", "UNKNOWN")
    except Exception:
        cycle = "UNKNOWN"
    regime = "UNKNOWN"
    try:
        if getattr(engine, "regime_detector", None):
            regime = str(engine.regime_detector.current_regime)
    except Exception:
        pass
    try:
        base_sl = engine.config.risk.stop_loss_pct
        base_tr = engine.config.risk.trailing_stop_pct
    except Exception:
        base_sl, base_tr = 0.0, 0.0
    try:
        from risk.regime_profiles import get_adjusted_risk, get_profile_name
        sl, tr, _ = get_adjusted_risk(cycle, regime, base_sl, base_tr)
        name = get_profile_name(cycle, regime)
    except Exception:
        sl, tr, name = base_sl, base_tr, "config"
    return sl, tr, name, regime


def _eff_stop(symbol, sl_pct):
    try:
        from risk.coin_stops import effective_stop
        return effective_stop(symbol, sl_pct)
    except Exception:
        return sl_pct


def _stufe(pnl_pct, regime):
    """Stufen-Leiter wie im Monitor - E7-aware."""
    up = _e7_installed() and regime == "TRENDING_UP"
    if pnl_pct >= 5.0:
        return 1.0 if up else 0.5
    elif pnl_pct >= 3.0:
        return 1.4 if up else 0.7
    elif pnl_pct >= 1.0:
        return 2.0 if up else 1.0
    else:
        return 1.6


_ZIEL_CACHE = {"t": 0.0, "daten": None}


def _ziel_config():
    """Zielgroessen aus config_zielgroessen.json. Fehlt sie, gilt None."""
    import json as _json
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "config_zielgroessen.json")
        return _json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def _freeze_status():
    """Welche Epoche laeuft, wie lange gilt der Freeze noch?

    [ZIELGROESSEN 19.08.2026] Der Freeze ist der wichtigste Zustand des
    Systems und stand nirgends im Cockpit. Wer ihn nicht sieht, aendert
    versehentlich Verhalten mitten im Messfenster - und alle Vorher-
    Nachher-Vergleiche sind wertlos.
    """
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    basis = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    epoche, epoche_ab = "?", None
    try:
        eps = _json.load(open(os.path.join(basis, "config_epochs.json"),
                              encoding="utf-8"))
        liste = eps.get("epochs") or eps.get("epochen") or eps
        if isinstance(liste, dict):
            paare = sorted(((k, v) for k, v in liste.items()
                            if isinstance(v, str)), key=lambda x: x[1])
        else:
            paare = sorted(((e.get("id") or e.get("name") or "?",
                             e.get("start") or e.get("ab") or "")
                            for e in liste), key=lambda x: x[1])
        jetzt = _dt.now(_tz.utc).isoformat()
        for name, ab in paare:
            if ab and ab <= jetzt:
                epoche, epoche_ab = name, ab
    except Exception:
        pass

    cfg = _ziel_config() or {}
    ende = cfg.get("messfenster_ende", "")
    rest_txt, offen = "-", None
    try:
        if ende:
            ziel = _dt.fromisoformat(ende + "T00:00:00+00:00")
            delta = ziel - _dt.now(_tz.utc)
            offen = delta.total_seconds() > 0
            tage = abs(delta.days)
            std = abs(int(delta.total_seconds() % 86400 // 3600))
            rest_txt = ("noch %d Tage %d h" % (tage, std) if offen
                        else "seit %d Tagen abgelaufen" % tage)
    except Exception:
        pass
    return epoche, epoche_ab, ende, rest_txt, offen


def _zielgroessen(engine):
    """Ist-Kennzahlen gegen die Ziele aus config_zielgroessen.json.

    [ZIELGROESSEN 19.08.2026] Rechenweg exakt wie BOT-HANDBUCH.md 4.60:
    netto = pnl_pct minus K-BASIS (Kosten je Runde). Das Ergebnis wird
    60 s gecacht, damit die 2-Sekunden-Anzeige nicht bei jedem Takt
    tausend Journalsaetze liest.

    NUR LESEND. Gibt None zurueck, wenn etwas fehlt - die Anzeige laesst
    den Block dann weg, statt zu raten.
    """
    import time as _time
    if _time.time() - _ZIEL_CACHE["t"] < 60 and _ZIEL_CACHE["daten"] is not None:
        return _ZIEL_CACHE["daten"]
    ergebnis = None
    try:
        cfg = _ziel_config()
        if not cfg:
            return None
        K = float(cfg.get("kosten_je_runde_pct", 0.505))
        trades = _journal_trades(engine)
        sells = [x for x in trades if x.get("type") == "SELL"
                 and x.get("pnl_pct") is not None]
        netto = []
        for x in sells:
            try:
                netto.append(float(x["pnl_pct"]) - K)
            except Exception:
                continue
        if not netto:
            return None
        gew = [v for v in netto if v > 0]
        ver = [v for v in netto if v <= 0]
        ev = sum(netto) / len(netto)
        g = (sum(gew) / len(gew)) if gew else 0.0
        v = abs(sum(ver) / len(ver)) if ver else 0.0
        payoff = (g / v) if v > 0 else None
        pf = (sum(gew) / abs(sum(ver))) if ver and sum(ver) != 0 else None
        tq = 100.0 * len(gew) / len(netto)
        mfe = [x for x in sells if x.get("mfe_pct") is not None]
        verschenkt = None
        if mfe:
            try:
                verschenkt = sum(float(x["mfe_pct"]) - float(x["pnl_pct"])
                                 for x in mfe) / len(mfe)
            except Exception:
                verschenkt = None
        ergebnis = {"n": len(netto), "tq": tq, "ev": ev, "payoff": payoff,
                    "pf": pf, "verschenkt": verschenkt, "cfg": cfg,
                    "n_mfe": len(mfe)}
    except Exception as _e:
        _ERR["n"] += 1
        _ERR["last"] = "zielgroessen: " + str(_e)[:60]
        ergebnis = None
    _ZIEL_CACHE["t"] = _time.time()
    _ZIEL_CACHE["daten"] = ergebnis
    return ergebnis


def _ziel_tag(wert, ziel, warn, richtung):
    """Gruen = Ziel erreicht, gelb = zwischen Warnung und Ziel, rot = darunter."""
    if wert is None:
        return C_DIM
    try:
        if richtung == "hoch":
            return C_POS if wert >= ziel else (C_WRN if wert >= warn else C_NEG)
        return C_POS if wert <= ziel else (C_WRN if wert <= warn else C_NEG)
    except Exception:
        return C_TXT


def render_snapshot(engine):
    L = []
    now = datetime.now().strftime("%H:%M:%S")
    trades = _journal_trades(engine)
    sells = [t for t in trades if t.get("type") == "SELL"]
    today = date.today().isoformat()
    daily = sum(float(t.get("pnl", 0)) for t in sells
                if str(t.get("time", "")).startswith(today))
    lifetime = _realized(engine, trades)
    usdc = _usdc(engine)
    prices = _prices(engine)
    poss = _positions(engine)
    try:
        maxpos = engine.config.risk.max_open_positions
    except Exception:
        maxpos = "-"
    streak = 0
    for t in reversed(sells):
        try:
            if float(t.get("pnl", 0)) < 0:
                streak += 1
            else:
                break
        except Exception:
            break
    sl_pct, tr_pct, phase, regime = _risk_params(engine)

    # --- E6.1-Statistik ---
    e61 = [t for t in sells if str(t.get("time", "")) >= E61_START]
    e61_wins = [float(t.get("pnl", 0)) for t in e61 if float(t.get("pnl", 0)) > 0]
    e61_loss = [float(t.get("pnl", 0)) for t in e61 if float(t.get("pnl", 0)) <= 0]
    rr = (sum(e61_wins) / len(e61_wins)) / abs(sum(e61_loss) / len(e61_loss)) \
        if e61_wins and e61_loss else None
    wr = 100.0 * len(e61_wins) / len(e61) if e61 else None
    tage = (date.today() - date.fromisoformat(E61_START)).days
    netz = sum(1 for t in e61 if "NOTAUS-NETZ" in str(t.get("reason", "")))

    def row(label, value, vtag):
        L.append((f"| {label:<18}| ", C_LBL))
        L.append((f"{value}\n", vtag))

    _up = datetime.now() - _SESSION_START
    _uph, _upm = int(_up.total_seconds() // 3600), int(_up.total_seconds() % 3600 // 60)
    _btc = prices.get("BTC/USDC", 0) or prices.get("BTC", 0)
    _alter = _price_alter(engine)  # [TERMINAL-AMPEL]
    if _alter is None:
        _ampel, _atag = "", C_DIM
    elif _alter < 30:
        _ampel, _atag = f" --- Preise {_alter:.0f}s OK", C_POS
    elif _alter < 120:
        _ampel, _atag = f" --- Preise {_alter:.0f}s alt", C_WRN
    else:
        _ampel, _atag = f" --- Preise {_alter:.0f}s ALT!", C_NEG
    L.append((f"--- TRADING IMPERIUM V6 --- STATUS {now} --- Session {_uph}h {_upm}m", C_HDR))
    L.append((_ampel + " ---\n\n", _atag))
    L.append(("+-------------------+------------------------+\n", C_DIM))
    row("Balance", f"{_f(usdc)} USDC", C_TXT)
    row("Daily PnL", f"{daily:+.2f} USD", C_POS if daily >= 0 else C_NEG)
    row("Lifetime PnL", f"{lifetime:+.2f} USD", C_MAG)
    row("Offene Trades", f"{len(poss)}/{maxpos}", C_TXT)
    L.append(("+-------------------+------------------------+\n\n", C_DIM))

    st = getattr(engine, "state", {}) or {}
    fg = st.get("fear_greed")
    if fg is None and sells:
        fg = sells[-1].get("fear_greed_at_entry")
    strat = None
    for t in reversed(trades):
        if t.get("active_strategy"):
            strat = t.get("active_strategy")
            break
    L.append(("--- Marktlage ---\n", C_HDR))
    L.append(("+-------------------+------------------------+\n", C_DIM))
    row("Zyklus / Regime", f"{st.get('cycle_phase', '?')} / {regime}",
        C_POS if regime == "TRENDING_UP" else C_TXT)
    row("Fear & Greed", f"{fg}  ({_fg_label(fg)})" if fg is not None else "-",
        C_NEG if _fg_label(fg) in ("Extreme Fear", "Fear") else C_POS if "Greed" in _fg_label(fg) else C_TXT)
    row("Strategie", strat or "-", C_MAG)
    row("BTC", f"{_f(_btc)} $" if _btc else "-", C_TXT)
    _dxy = st.get("dxy")
    row("DXY / News", f"{_dxy if _dxy is not None else '-'} {st.get('dxy_trend','')}  |  News: {st.get('news_sentiment','-')}", C_DIM)
    # [AUDIT 06.08.2026] Frueher stand hier "NUPL / Onchain". Der Wert aus
    # data/nupl_monitor.py ist KEINE NUPL (die braucht Realized Cap aus
    # On-Chain-UTXO-Daten), sondern (Preis - SMA200)/Preis - und der SMA200
    # friert dort nach dem ersten Aufruf auf 0.80 x Startpreis ein. Der
    # Rechenfehler selbst gehoert in den Bot-Pfad und wird hier NICHT
    # angefasst; die Anzeige nennt den Wert ab jetzt beim richtigen Namen.
    _nupl = st.get("nupl")
    row("Preis/SMA200-Proxy", f"{_nupl if _nupl is not None else '-'} {st.get('nupl_zone','')}"
        f"  |  Onchain-Score: {st.get('onchain_score','-')}", C_WRN)
    L.append(("+-------------------+------------------------+\n", C_DIM))
    L.append(("  Hinweis: 'Proxy' ist keine On-Chain-NUPL. Siehe Ticket NUPL-PROXY.\n\n", C_DIM))

    L.append((f"--- Epoche E6.1 (seit {E61_START[8:]}.{E61_START[5:7]}.) ---\n", C_HDR))
    L.append(("+-------------------+------------------------+\n", C_DIM))
    row("Sells", f"{len(e61)} / {E61_SELLS_ZIEL}",
        C_POS if len(e61) >= E61_SELLS_ZIEL else C_TXT)
    row("Tage", f"{tage} / {E61_TAGE_ZIEL}",
        C_POS if tage >= E61_TAGE_ZIEL else C_TXT)
    row("R/R", f"{rr:.2f}  (Basis E4: {E4_BASIS_RR})" if rr is not None else "- (zu wenig Daten)",
        (C_POS if rr >= E4_BASIS_RR else C_NEG) if rr is not None else C_DIM)
    row("Win-Rate", f"{wr:.0f}%" if wr is not None else "-", C_TXT)
    L.append(("+-------------------+------------------------+\n\n", C_DIM))

    serie = _equity_serie()
    L.append(("--- Performance ---\n", C_HDR))
    L.append(("+-------------------+------------------------+\n", C_DIM))
    _heute = [t for t in sells if str(t.get("time", "")).startswith(today)]
    _hw = sum(1 for t in _heute if float(t.get("pnl", 0)) > 0)
    row("Heute", f"{len(_heute)} Sells | WR {(_hw/len(_heute)*100):.0f}%" if _heute else "0 Sells", C_TXT)
    _d7 = [float(t.get("pnl", 0)) for t in sells
           if str(t.get("time", ""))[:10] >= (date.today() - __import__("datetime").timedelta(days=7)).isoformat()]
    row("7-Tage P&L", f"{sum(_d7):+.2f} USD ({len(_d7)} Sells)", C_POS if sum(_d7) >= 0 else C_NEG)
    if serie:
        _peak, _mdd = serie[0], 0.0
        for v in serie:
            _peak = max(_peak, v)
            _mdd = max(_mdd, (_peak - v) / _peak * 100 if _peak > 0 else 0)
        # [AUDIT 06.08.2026] equity_history.json wird beim Prozessstart neu
        # aufgebaut, enthaelt also NUR die laufende Session (gemessen: 330
        # Punkte = 3,9 h). "Max-DD" las sich als Lifetime-Drawdown. Label und
        # Punktzahl sagen jetzt, worauf sich der Wert bezieht.
        row("Equity / DD (Session)",
            f"{_f(serie[-1])} $  |  DD {_mdd:.1f}%  ({len(serie)} Punkte)", C_TXT)
        L.append((f"| {'Verlauf':<18}| ", C_LBL))
        L.append((_sparkline(serie) + "\n", C_POS if serie[-1] >= serie[0] else C_NEG))
    L.append(("+-------------------+------------------------+\n\n", C_DIM))

    L.append(("--- Risk Manager ---\n", C_HDR))
    L.append(("+-------------------+------------------------+\n", C_DIM))
    _dl_txt, _dl_tag = _daily_loss(engine)          # [AUDIT 06.08.2026]
    row("Tagesverlustlimit", _dl_txt, _dl_tag)
    _js = _journal_speicher(engine)                 # [AUDIT 06.08.2026]
    if _js:
        row("Journal-Speicher", _js[0], _js[1])
    row("Verluste in Folge", str(streak), C_POS if streak == 0 else C_NEG)
    row("Notaus-Netz", f"{netz} Ausloesungen" + ("  ✓" if netz == 0 else "  !! MONITOR PRUEFEN !!"),
        C_POS if netz == 0 else C_WRN)
    row("Stop/Trail (Phase)", f"{sl_pct}% / {tr_pct}%  ({phase})", C_TXT)
    row("Regime (roh, E7)", regime + ("  -> E7 AKTIV" if regime == "TRENDING_UP" and _e7_installed() else ""),
        C_POS if regime == "TRENDING_UP" else C_TXT)  # [TERMINAL-REGIME]
    # [AUDIT 06.08.2026] _e7_installed() sucht nur einen Textmarker im
    # Quelltext von runtime/exit_monitor.py - das ist kein Laufzeitbeweis.
    # Das Label sagt jetzt, worauf die Aussage beruht.
    row("E7 Phasen-Trailing",
        "Marker im Quelltext" if _e7_installed() else "kein Marker (Deploy ab 19.07.)",
        C_POS if _e7_installed() else C_DIM)
    _e7n = sum(1 for t in sells
               if str(t.get("time", "")) >= "2026-07-17"
               and "E7-UP" in str(t.get("reason", "")))  # [TERMINAL-E7COUNT]
    row("E7-UP Verkaeufe", f"{_e7n} seit Deploy (17.07.)" +
        ("  <- erster Beweis!" if _e7n == 1 else ""),
        C_POS if _e7n > 0 else C_DIM)
    _inv = sum((prices.get(s, 0) or prices.get(s.split("/")[0], 0)) * (p.get("qty", 0) or 0)
               for s, p in poss.items())
    _tot = _inv + usdc
    row("Exposure", f"{_f(_inv)} $ investiert / {_f(usdc)} $ Cash ({(_inv/_tot*100):.0f}%)" if _tot > 0 else "-", C_TXT)
    row("Status", "Aktiv", C_POS)
    L.append(("+-------------------+------------------------+\n\n", C_DIM))

    # =================== [ZIELGROESSEN 19.08.2026] ===================
    # Zwei Bloecke: WO STEHEN WIR (Freeze/Messfenster) und WO WOLLEN WIR HIN
    # (Ziele aus config_zielgroessen.json). Reine Anzeige, kein Handelspfad.
    try:
        _ep, _epab, _mfende, _rest, _offen = _freeze_status()
        L.append(("--- Freeze / Messfenster ---\n", C_HDR))
        L.append(("+-------------------+------------------------+\n", C_DIM))
        row("Epoche", _ep, C_MAG)
        row("Epoche ab", (_epab or "-")[:16].replace("T", " "), C_DIM)
        if _offen is True:
            row("FREEZE", "AKTIV bis " + str(_mfende), C_WRN)
            row("Messfenster", _rest, C_TXT)
            L.append(("| Kein Verhalten aendern. Nur lesen und aufschreiben.\n", C_WRN))
        elif _offen is False:
            row("FREEZE", "abgelaufen (" + str(_mfende) + ")", C_POS)
            row("Messfenster", _rest, C_TXT)
        else:
            row("FREEZE", "unbekannt - config_zielgroessen.json pruefen", C_DIM)
        _mf = [x for x in sells if str(x.get("time", "")) >= "2026-08-13T13:21"]
        row("Verkaeufe im Fenster", str(len(_mf)), C_TXT if len(_mf) >= 10 else C_WRN)
        L.append(("+-------------------+------------------------+\n\n", C_DIM))
    except Exception as _fe:
        _ERR["n"] += 1
        _ERR["last"] = "freeze-block: " + str(_fe)[:60]

    try:
        _z = _zielgroessen(engine)
        if _z:
            _c = _z["cfg"]
            _mind = int(_c.get("mindest_fallzahl", 30))
            _duenn = _z["n"] < _mind
            L.append(("--- Zielgroessen ---\n", C_HDR))
            if _duenn:
                L.append(("  Achtung: nur %d Faelle, belastbar ab %d. "
                          "Alles darunter ist Rauschen.\n" % (_z["n"], _mind), C_WRN))
            L.append(("+-------------------+------------------------+\n", C_DIM))

            def zrow(schluessel, wert, nachkomma=2):
                d = _c.get(schluessel) or {}
                ziel, warn = d.get("ziel"), d.get("warnung")
                titel = d.get("titel", schluessel)
                einheit = d.get("einheit", "")
                richtung = d.get("richtung", "hoch")
                if wert is None or ziel is None:
                    row(titel[:18], "-", C_DIM)
                    return
                pfeil = ">=" if richtung == "hoch" else "<="
                txt = ("%+.*f%s (Ziel %s %.2f%s)"
                       % (nachkomma, wert, einheit, pfeil, ziel, einheit))
                row(titel[:18], txt,
                    C_DIM if _duenn else _ziel_tag(wert, ziel, warn, richtung))

            zrow("ev_netto_pct", _z["ev"], 3)
            zrow("payoff_ratio", _z["payoff"])
            zrow("profit_faktor", _z["pf"])
            zrow("verschenkt_pp", _z["verschenkt"])
            row("Trefferquote", "%.1f%%  (kein Ziel - siehe 4.60)" % _z["tq"], C_DIM)
            row("Faelle", "%d Verkaeufe, davon %d mit Hoechststand"
                % (_z["n"], _z["n_mfe"]), C_TXT if not _duenn else C_WRN)
            L.append(("+-------------------+------------------------+\n", C_DIM))
            L.append(("  Netto = Ergebnis minus %s%% Kosten je Runde. "
                      "Rechenweg: BOT-HANDBUCH.md 4.60\n\n"
                      % _c.get("kosten_je_runde_pct", 0.505), C_DIM))
    except Exception as _ze:
        _ERR["n"] += 1
        _ERR["last"] = "ziel-block: " + str(_ze)[:60]

    L.append(("--- Offene Positionen ---\n", C_HDR))
    hdr = (f"| {'Symbol':<10}| {'Einstieg':>12} | {'Akt. Preis':>12} | {'PnL %':>8} |"
           f" {'PnL USD':>9} | {'Stop-Loss':>12} | {'Fall/Trail':>11} |\n")
    sep = "+" + "-" * (len(hdr) - 3) + "+\n"
    L.append((sep, C_DIM))
    L.append((hdr, C_LBL))
    L.append((sep, C_DIM))
    if not poss:
        L.append(("|  (keine offenen Positionen)\n", C_DIM))
    for sym, pos in poss.items():
        entry = pos.get("entry_price", 0) or pos.get("entry", 0)
        qty = pos.get("qty", 0) or pos.get("quantity", 0)
        cur = prices.get(sym, 0) or prices.get(sym.split("/")[0], 0)
        eff = _eff_stop(sym, sl_pct)
        stop_p = entry * (1 - eff / 100) if entry else 0
        if cur and entry:
            pct = (cur / entry - 1) * 100
            usd = (cur - entry) * qty
            high = pos.get("highest_price", entry) or entry
            fall = (high - cur) / high * 100 if high > 0 else 0
            eff_trail = round(tr_pct * _stufe(pct, regime), 3)
            trail_s = f"{fall:.2f}/{eff_trail}" if pct > 0.3 else "-"
            tag = C_POS if pct >= 0 else C_NEG
            L.append((f"| {sym:<10}| {_f(entry,4):>12} | {_f(cur,4):>12} | "
                      f"{pct:+8.2f} | {usd:+9.2f} | {_f(stop_p,4):>12} | {trail_s:>11} |\n", tag))
        else:
            L.append((f"| {sym:<10}| {_f(entry,4):>12} | {'?':>12} | {'-':>8} | "
                      f"{'-':>9} | {_f(stop_p,4):>12} | {'-':>11} |\n", C_DIM))
    L.append((sep + "\n", C_DIM))

    # [AUSFUEHRLICHER 19.08.2026] Sven fiel auf, dass die RSI-Verkaeufe
    # knapper beschrieben waren als die Trailing-Verkaeufe. Der Grund liegt
    # nicht in der Anzeige, sondern an zwei verschiedenen Ausstiegswegen:
    #   runtime/exit_monitor.py:356  schreibt "Fall X% >= Y%, PnL, Hoch"
    #   agents/signal_agent.py:229   schreibt nur "RSI overbought (80), PnL"
    # Statt den einen Text anzugleichen, zeigt die Anzeige jetzt die Zahlen,
    # die in JEDEM Verkauf stehen - dann ist jeder Ausstieg gleich gut
    # beurteilbar, egal welcher Weg ihn ausgeloest hat.
    L.append(("--- Letzte 5 Verkaeufe ---\n", C_HDR))
    _k_runde = 0.505
    try:
        _zcfg = _ziel_config() or {}
        _k_runde = float(_zcfg.get("kosten_je_runde_pct", 0.505))
    except Exception:
        pass
    for t in list(reversed(sells))[:5]:
        try:
            pnl = float(t.get("pnl", 0))
            ts = str(t.get("time", ""))[5:16].replace("T", " ")
            coin = str(t.get("coin", t.get("symbol", "?"))).split("/")[0]
            tag = C_POS if pnl > 0 else C_NEG

            # Zeile 1: Geld, Brutto/Netto, Hoechststand und was davon blieb
            _bp = t.get("pnl_pct")
            _mfe = t.get("mfe_pct")
            _mae = t.get("mae_pct")
            kopf = f"  {ts}  {coin:<6}{pnl:+7.2f}$"
            if _bp is not None:
                _netto = float(_bp) - _k_runde
                kopf += f"  brutto {float(_bp):+5.2f}%  netto {_netto:+5.2f}%"
            L.append((kopf + "\n", tag))

            # Zeile 2: wieviel vom Hoechststand zurueckgegeben wurde.
            # Das ist die Zahl, die den Ausstieg bewertet - bei den beiden
            # RSI-Verkaeufen vom 19.08. war sie 0,00 (Verkauf exakt am Hoch),
            # beim Trailing liegt sie im Median bei 0,98 Prozentpunkten.
            if _mfe is not None and _bp is not None:
                _zurueck = float(_mfe) - float(_bp)
                _rest = (float(_bp) / float(_mfe) * 100) if float(_mfe) else 0
                _rtag = C_POS if _zurueck < 0.3 else (C_WRN if _zurueck < 1.0 else C_NEG)
                zeile = (f"        Hoch {float(_mfe):+5.2f}%"
                         f"  ->  {_zurueck:4.2f}PP zurueckgegeben"
                         f"  ({_rest:3.0f}% behalten)")
                if _mae is not None:
                    zeile += f"   Tief {float(_mae):+5.2f}%"
                _rm = t.get("r_multiple")
                if _rm is not None:
                    zeile += f"   R {float(_rm):+.2f}"
                L.append((zeile + "\n", _rtag))

            # Zeile 3: der Grund im Wortlaut, plus Reibung
            _r = str(t.get("reason", t.get("strategy", "")))
            zeile3 = f"        {_r[:66]}"
            if "E7-UP" in _r:
                zeile3 += " [E7-UP]"
            _fee, _slip = t.get("fee"), t.get("slippage_pct")
            if _fee is not None:
                zeile3 += f"   Gebuehr {float(_fee):.2f}$"
            if _slip is not None:
                zeile3 += f"  Slippage {float(_slip):.3f}%"
            L.append((zeile3 + "\n", C_DIM))
        except Exception:
            continue
    if not sells:
        L.append(("  (noch keine Verkaeufe)\n", C_DIM))
    else:
        L.append(("  Netto = brutto minus Kosten je Runde. 'zurueckgegeben' = "
                  "Hoechststand minus realisiert.\n", C_DIM))
    return L


def build_terminal_tab(parent, engine):
    import tkinter as tk
    sb = tk.Scrollbar(parent)  # [TERMINAL-SCROLLFIX]
    sb.pack(side="right", fill="y")
    txt = tk.Text(parent, bg="#000000", fg="#d0d0d0", insertbackground="#00ff88",
                  font=("Consolas", 11), relief="flat", wrap="none", cursor="arrow",
                  yscrollcommand=sb.set)
    txt.pack(fill="both", expand=True, padx=4, pady=4)
    sb.config(command=txt.yview)
    for tag, col in [(C_HDR, "#00ff88"), (C_LBL, "#00c8ff"), (C_POS, "#00ff88"),
                     (C_NEG, "#ff4655"), (C_MAG, "#ff66ff"), (C_DIM, "#666666"),
                     (C_TXT, "#e8e8e8"), (C_WRN, "#ffb020")]:
        txt.tag_configure(tag, foreground=col)

    def _refresh():
        try:
            lines = render_snapshot(engine)
            _view = txt.yview()  # [TERMINAL-SCROLLFIX] Position merken
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            for line, tag in lines:
                txt.insert("end", line, tag)
            txt.configure(state="disabled")
            txt.yview_moveto(_view[0])  # Position wiederherstellen
            _ERR["n"] = 0
        except Exception as _e:
            # [AUDIT 06.08.2026] Vorher "except Exception: pass" - bei einem
            # dauerhaften Fehler blieb das letzte Bild stehen und der Tab sah
            # weiter aktuell aus, obwohl er eingefroren war. Der Crash-Schutz
            # bleibt, der Ausfall wird jetzt sichtbar.
            _ERR["n"] += 1
            _ERR["last"] = f"{datetime.now().strftime('%H:%M:%S')} {str(_e)[:90]}"
            try:
                txt.configure(state="normal")
                txt.delete("1.0", "end")
                txt.insert("end", f"--- TERMINAL: Anzeige gestoert "
                                  f"({_ERR['n']} Fehler in Folge) ---\n\n", C_NEG)
                txt.insert("end", f"  {_ERR['last']}\n\n", C_WRN)
                txt.insert("end", "  Der Bot laeuft weiter - nur diese Anzeige\n"
                                  "  konnte nicht gerendert werden.\n", C_DIM)
                txt.configure(state="disabled")
            except Exception:
                pass
        finally:
            try:
                txt.after(REFRESH_MS, _refresh)
            except Exception:
                pass

    _refresh()
