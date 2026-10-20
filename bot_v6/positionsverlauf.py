# -*- coding: utf-8 -*-
"""
positionsverlauf.py — zeichnet auf, WIE eine Position verlief, nicht nur wie sie endete
=======================================================================================

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Der Bot speichert ueber den Verlauf einer Position genau zwei Zahlen:
mfe_pct (hoechster Stand) und mae_pct (tiefster). Damit laesst sich KEINE
Ausstiegsregel nachrechnen, weil der Zeitpunkt fehlt.

Beispiel aus den echten Daten, Verkauf vom 18.08.2026:
    Hoechststand +1,67 %, realisiert +0,77 %, Haltedauer 5,1 Tage.
War das Hoch nach zwanzig Minuten oder am vierten Tag? Ein ATR-Stop haette
in beiden Faellen voellig anders reagiert - und wir koennen es nicht sagen.

Genau dort liegt der groesste Hebel des Bots. Gemessen ueber 220 Verkaeufe
(BOT-HANDBUCH.md 4.60): 38 Trades - 17,3 % - verursachen -106,6
Prozentpunkte. Und je Trade werden 1,495 Prozentpunkte zwischen
Hoechststand und Verkauf liegengelassen, dreimal die Kosten einer Runde.

WAS ES BEANTWORTET
    "Haette Ausstiegsregel X mehr verdient als die heutige?"
    - fuer JEDE Regel, rueckwirkend, ohne eine Zeile am Bot zu aendern.

WAS ES NICHT BEANTWORTET
    "Haette das Portfolio mehr verdient?" Schattenpositionen kennen keine
    Kapitalkonkurrenz. Fuer den Vergleich von Ausstiegsregeln spielt das
    keine Rolle - alle Regeln bewerten dieselben Positionen. Fuer die
    Portfolio-Frage schon.

ZWEI QUELLEN, WEIL EINE NICHT REICHT
------------------------------------
1. ECHTE Positionen des Bots (data_store/bot_state.json, nur gelesen).
   Wahrheitsgetreu - aber bei ~3 offenen Positionen und wenigen Trades
   kommen in zwei Wochen nur 15-20 vollstaendige Verlaeufe zusammen. Fuer
   eine belastbare Aussage braeuchte es 30-40.

2. SCHATTEN-Positionen aus schatten_universum.db. Jedes Einstiegssignal
   auf den 14 Muenzen eroeffnet eine Papierposition, die verfolgt wird -
   ohne Ausstieg, bis MAX_TAGE erreicht sind. Das ist Absicht: Wir wollen
   den ROHEN Verlauf, damit sich spaeter jede Ausstiegsregel darauf
   rechnen laesst.

WARUM EIN EIGENES PROGRAMM UND NICHT IM BOT
-------------------------------------------
Waehrend des Messfensters darf am Bot nichts geaendert werden. Dieses
Programm laeuft getrennt, schreibt in eine EIGENE Datenbank und liest den
Bot nur - genau wie schatten_universum.py und der Forschungs-Sammler.
Es kann den Handel nicht beeinflussen.

AUFRUF
------
    python positionsverlauf.py                 Dauerlauf (alle 5 Minuten)
    python positionsverlauf.py --einmal        ein einzelner Durchgang
    python positionsverlauf.py --status        was bisher gesammelt wurde
    python positionsverlauf.py --selbsttest    Gegentest in beide Richtungen
"""
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

DB = os.path.join(HIER, "data_store", "positionsverlauf.db")
LOG = os.path.join(HIER, "data_store", "positionsverlauf.log")
BOT_STATE = os.path.join(HIER, "data_store", "bot_state.json")
SCHATTEN_DB = os.path.join(HIER, "data_store", "schatten_universum.db")
JOURNAL = os.path.join(HIER, "data_store", "trades_v5.json")

TAKT_SEK = 300          # alle 5 Minuten
MAX_TAGE = 7            # so lange wird eine Schattenposition verfolgt
MAX_SCHATTEN_JE_MUENZE = 1   # wie im echten Bot: eine Position je Muenze

SCHEMA = """
CREATE TABLE IF NOT EXISTS positionen (
    pos_id      TEXT PRIMARY KEY,
    quelle      TEXT NOT NULL,          -- 'echt' oder 'schatten'
    muenze      TEXT NOT NULL,
    eroeffnet   TEXT NOT NULL,
    einstieg    REAL NOT NULL,
    menge       REAL,
    strategie   TEXT,
    score       REAL,
    geschlossen TEXT,                   -- NULL solange offen
    schluss_grund TEXT
);
CREATE TABLE IF NOT EXISTS verlauf (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pos_id      TEXT NOT NULL,
    ts_utc      TEXT NOT NULL,
    minuten     REAL,                   -- seit Eroeffnung
    preis       REAL,
    pnl_pct     REAL,                   -- brutto, ohne Kosten
    hoch_seit   REAL,                   -- Hoechstkurs seit Eroeffnung
    tief_seit   REAL,
    mfe_pct     REAL,                   -- bester Stand bisher
    mae_pct     REAL,                   -- schlechtester Stand bisher
    fall_vom_hoch_pct REAL,             -- fuer Ratschen-Regeln
    atr         REAL,
    atr_pct     REAL,                   -- ATR in Prozent vom Preis
    rsi         REAL,
    adx         REAL,
    macd_hist   REAL,
    swing_tief  REAL,                   -- letztes hoeheres Tief (Struktur)
    swing_hoch  REAL,
    regime      TEXT,
    spread_bp   REAL
);
CREATE INDEX IF NOT EXISTS idx_verlauf_pos ON verlauf(pos_id, ts_utc);
CREATE TABLE IF NOT EXISTS laeufe (
    lauf_id     TEXT PRIMARY KEY,
    ts_utc      TEXT,
    offen_echt  INTEGER,
    offen_schatten INTEGER,
    zeilen      INTEGER,
    neu         INTEGER,
    geschlossen INTEGER,
    dauer_sek   REAL,
    fehler      TEXT
);
"""


def notiz(text):
    zeile = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}] {text}"
    print(zeile)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except Exception:
        pass


def db_oeffnen():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(SCHEMA)
    con.commit()
    return con


# ------------------------------------------- Einstieg aus dem Handelsbuch
#
# [29.08.2026, Befund 88] Warum diese Funktion noetig wurde
# ---------------------------------------------------------
# `positionen.strategie` war bei ALLEN 58 echten Positionen leer und
# `score` durchgehend NULL - auch bei denen von gestern. Es ist also
# kein Altlastenproblem.
#
# Die Ursache ist eine Kette aus vier Gliedern mit DREI Namen fuer
# dieselbe Sache:
#     agents/signal_agent.py:182   setzt  strategy_id   am Auftrag
#     app.py:1873                  setzt  entry_strategie  an der Position
#     runtime/state_manager.py     speichert nach einer WHITELIST, die
#                                  `strategie_id` kennt - aber weder
#                                  `entry_strategie` noch `entry_score`
#     positionsverlauf.py:179      liest `entry_strategie`, sonst
#                                  `strategie_id`, sonst ""
#
# Der Kommentar der Whitelist warnt selbst davor: "was nicht aufgezaehlt
# ist, ueberlebt keinen Neustart."
#
# Drei Namen ueber vier Glieder zu synchronisieren waere die aufwendigste
# und fehleranfaelligste Loesung - und sie wuerde die Whitelist beruehren,
# also das Verhalten nach einem Neustart. Das braeuchte eine Epochengrenze.
#
# Der kuerzere Weg: Die Angabe steht laengst im Handelsbuch. JEDER Kauf
# traegt sein `strategy`-Feld - 605 von 605, also 100 %. Wir holen sie
# von dort. Das ist ein reiner Lesevorgang in einem Sammler, beruehrt
# keinen Handelspfad und schreibt nur auf.
def einstieg_aus_journal(muenze, eroeffnet_iso, pfad=JOURNAL, fenster_min=30):
    """Strategie und Score des Kaufs, der diese Position eroeffnet hat.

    Gesucht wird der letzte KAUF derselben Muenze VOR dem Eroeffnungs-
    zeitpunkt, hoechstens `fenster_min` Minuten davor. Das Fenster ist
    wichtig: ohne es wuerde irgendein alter Kauf gefunden und seine
    Strategie faelschlich zugeordnet - dieselbe Falle, in die die
    FIFO-Zuordnung am 29.08. gelaufen ist.

    Rueckgabe: (strategie, score). Leere Werte bleiben leer - eine leere
    Zeichenkette ist KEIN Wert und wuerde die Vollstaendigkeitsstatistik
    schoenen.
    """
    if not eroeffnet_iso:
        return "", None
    try:
        ziel = datetime.fromisoformat(str(eroeffnet_iso).replace("Z", "+00:00"))
    except Exception:
        return "", None
    try:
        with open(pfad, encoding="utf-8") as f:
            eintraege = json.load(f)
    except Exception:
        return "", None

    bester, bester_ts = None, None
    for t in eintraege:
        if t.get("type") != "BUY" or t.get("coin") != muenze:
            continue
        try:
            ts = datetime.fromisoformat(str(t.get("time") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        abstand = (ziel - ts).total_seconds()
        if abstand < 0 or abstand > fenster_min * 60:
            continue
        if bester_ts is None or ts > bester_ts:
            bester, bester_ts = t, ts

    if bester is None:
        return "", None
    strat = bester.get("strategy") or bester.get("active_strategy") or ""
    if isinstance(strat, str) and not strat.strip():
        strat = ""
    score = bester.get("score")
    if score is None:
        score = bester.get("signal_score")
    return strat, score


# --------------------------------------------------------------- Quelle 1: Bot
def echte_positionen():
    """Offene Positionen des Bots. NUR LESEND aus bot_state.json.

    open_positions ist waehrend eines Neustarts kurz leer; dann gilt
    open_positions_backup. Beides wird geprueft, damit ein Neustart keine
    Luecke in die Zeitreihe reisst.
    """
    out = {}
    try:
        with open(BOT_STATE, encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        return out
    for schluessel in ("open_positions", "open_positions_backup"):
        for muenze, p in (st.get(schluessel) or {}).items():
            if not isinstance(p, dict) or not p.get("active"):
                continue
            if muenze in out:
                continue
            einstieg = p.get("entry_price") or 0
            if einstieg <= 0:
                continue
            pid = p.get("position_id") or f"echt_{muenze.replace('/', '')}"
            eroeffnet = p.get("eroeffnet_ts")
            try:
                eroeffnet = (datetime.fromtimestamp(float(eroeffnet), timezone.utc)
                             .isoformat()) if eroeffnet else None
            except Exception:
                eroeffnet = None
            out[muenze] = {
                "pos_id": pid, "quelle": "echt", "muenze": muenze,
                "einstieg": float(einstieg), "menge": p.get("qty"),
                "strategie": p.get("entry_strategie") or p.get("strategie_id") or "",
                "score": p.get("entry_score"),
                "_eroeffnet_roh": eroeffnet,
                "eroeffnet": eroeffnet or datetime.now(timezone.utc).isoformat(),
            }
            # Was der Bot nicht mitgibt, holen wir aus dem Handelsbuch.
            # Vorhandene Werte werden NIE ueberschrieben.
            eintrag = out[muenze]
            if not eintrag["strategie"] or eintrag["score"] is None:
                strat, score = einstieg_aus_journal(muenze, eintrag["eroeffnet"])
                if not eintrag["strategie"] and strat:
                    eintrag["strategie"] = strat
                if eintrag["score"] is None and score is not None:
                    eintrag["score"] = score
            eintrag.pop("_eroeffnet_roh", None)
    return out


# ---------------------------------------------------------- Quelle 2: Schatten
def neue_schattensignale(con, seit_ts):
    """Signale aus schatten_universum.db, die noch keine Position haben."""
    if not os.path.exists(SCHATTEN_DB):
        return []
    out = []
    try:
        s = sqlite3.connect(f"file:{SCHATTEN_DB}?mode=ro", uri=True, timeout=15)
        offen = {r[0] for r in con.execute(
            "SELECT muenze FROM positionen WHERE quelle='schatten' AND geschlossen IS NULL")}
        for z in s.execute(
                "SELECT id, ts_utc, muenze, preis, score, strategie FROM signale "
                "WHERE ts_utc > ? ORDER BY ts_utc", (seit_ts,)):
            sid, ts, muenze, preis, score, strat = z
            if not preis or preis <= 0:
                continue
            if muenze in offen:
                continue           # eine Position je Muenze, wie im echten Bot
            offen.add(muenze)
            out.append({"pos_id": f"sch_{sid}", "quelle": "schatten",
                        "muenze": muenze, "einstieg": float(preis),
                        "menge": None, "strategie": strat or "", "score": score,
                        "eroeffnet": ts})
        s.close()
    except Exception as e:
        notiz(f"Schattensignale nicht lesbar: {str(e)[:80]}")
    return out


def letzter_schatten_ts(con):
    r = con.execute("SELECT MAX(eroeffnet) FROM positionen WHERE quelle='schatten'").fetchone()
    return r[0] or "2026-08-14T00:00:00+00:00"


# ------------------------------------------------------------------- Marktdaten
def _swings(df, fenster=5):
    """Letztes hoeheres Tief und letztes Hoch - die einfachste brauchbare
    Strukturdefinition: ein Punkt ist ein Swing, wenn er in einem Fenster
    von +/- N Kerzen der tiefste (bzw. hoechste) ist."""
    try:
        # Der DataAgent liefert GROSS geschriebene Spalten (High/Low/Close).
        # Die Kleinschreibung steht als Rueckfall drin, weil Testdaten und
        # aeltere Quellen sie benutzen. Genau diese Verwechslung liess den
        # ersten Selbsttest gruen und den echten Lauf leer ausgehen.
        sp_h = "High" if "High" in df.columns else "high"
        sp_t = "Low" if "Low" in df.columns else "low"
        hoch = df[sp_h].values
        tief = df[sp_t].values
        n = len(tief)
        s_tief = s_hoch = None
        for i in range(n - fenster - 1, fenster - 1, -1):
            if s_tief is None and tief[i] == min(tief[i - fenster:i + fenster + 1]):
                s_tief = float(tief[i])
            if s_hoch is None and hoch[i] == max(hoch[i - fenster:i + fenster + 1]):
                s_hoch = float(hoch[i])
            if s_tief is not None and s_hoch is not None:
                break
        return s_tief, s_hoch
    except Exception:
        return None, None


def marktbild(data_agent, muenze, timeframe):
    """Preis + Indikatoren + Struktur fuer eine Muenze. None bei Fehler."""
    try:
        snap = data_agent.fetch_snapshot(muenze, timeframe, limit=200)
        if snap is None:
            return None
        ind = getattr(snap, "indicators", {}) or {}
        # MarketSnapshot fuehrt den Kurs als .close - NICHT .price.
        preis = getattr(snap, "close", None)
        df = getattr(snap, "_df", None)
        s_tief, s_hoch = _swings(df) if df is not None else (None, None)
        if preis is None and df is not None:
            sp_c = "Close" if "Close" in df.columns else "close"
            preis = float(df[sp_c].iloc[-1])
        # macd_hist steht nur im DataFrame, nicht im indicators-Wörterbuch.
        mh = ind.get("macd_hist")
        if mh is None and df is not None and "MACD_hist" in df.columns:
            try:
                mh = float(df["MACD_hist"].iloc[-1])
            except Exception:
                mh = None
        if mh is None:
            mh = ind.get("macd")
        return {"preis": float(preis) if preis else None,
                "atr": ind.get("atr"), "rsi": ind.get("rsi"),
                "adx": ind.get("adx"),
                "macd_hist": mh,
                "swing_tief": s_tief, "swing_hoch": s_hoch,
                "regime": str(getattr(snap, "regime", "") or "")}
    except Exception:
        return None


# ------------------------------------------------------------------- Ein Lauf
def ein_lauf(con, data_agent, timeframe):
    lauf_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    start = time.time()
    jetzt = datetime.now(timezone.utc)
    fehler = []
    neu = zeilen = geschlossen = 0

    # 1) Neue Positionen aufnehmen
    for p in list(echte_positionen().values()) + neue_schattensignale(
            con, letzter_schatten_ts(con)):
        vorhanden = con.execute("SELECT 1 FROM positionen WHERE pos_id=?",
                                (p["pos_id"],)).fetchone()
        if vorhanden:
            continue
        con.execute(
            "INSERT INTO positionen (pos_id,quelle,muenze,eroeffnet,einstieg,"
            "menge,strategie,score) VALUES (?,?,?,?,?,?,?,?)",
            (p["pos_id"], p["quelle"], p["muenze"], p["eroeffnet"],
             p["einstieg"], p["menge"], p["strategie"], p["score"]))
        neu += 1

    # 2) Geschlossene echte Positionen als beendet markieren
    noch_offen = set(echte_positionen().keys())
    for pid, muenze in con.execute(
            "SELECT pos_id, muenze FROM positionen "
            "WHERE quelle='echt' AND geschlossen IS NULL").fetchall():
        if muenze not in noch_offen:
            con.execute("UPDATE positionen SET geschlossen=?, schluss_grund=? "
                        "WHERE pos_id=?",
                        (jetzt.isoformat(), "vom Bot geschlossen", pid))
            geschlossen += 1

    # 3) Schattenpositionen nach MAX_TAGE beenden
    for pid, eroeffnet in con.execute(
            "SELECT pos_id, eroeffnet FROM positionen "
            "WHERE quelle='schatten' AND geschlossen IS NULL").fetchall():
        try:
            alter = (jetzt - datetime.fromisoformat(eroeffnet)).total_seconds() / 86400
            if alter >= MAX_TAGE:
                con.execute("UPDATE positionen SET geschlossen=?, schluss_grund=? "
                            "WHERE pos_id=?",
                            (jetzt.isoformat(), f"Hoechstdauer {MAX_TAGE} Tage", pid))
                geschlossen += 1
        except Exception:
            continue
    con.commit()

    # 4) Fuer jede offene Position eine Verlaufszeile
    offen = con.execute(
        "SELECT pos_id, quelle, muenze, eroeffnet, einstieg FROM positionen "
        "WHERE geschlossen IS NULL").fetchall()
    bilder = {}
    n_echt = n_schatten = 0
    for pid, quelle, muenze, eroeffnet, einstieg in offen:
        if quelle == "echt":
            n_echt += 1
        else:
            n_schatten += 1
        if muenze not in bilder:
            bilder[muenze] = marktbild(data_agent, muenze, timeframe)
            time.sleep(0.4)          # freundlich zur Boersen-Schnittstelle
        b = bilder[muenze]
        if not b or not b.get("preis"):
            fehler.append(f"{muenze}: kein Preis")
            continue
        preis = b["preis"]
        pnl = (preis / einstieg - 1) * 100 if einstieg else None

        vor = con.execute(
            "SELECT MAX(hoch_seit), MIN(tief_seit), MAX(mfe_pct), MIN(mae_pct) "
            "FROM verlauf WHERE pos_id=?", (pid,)).fetchone()
        hoch = max(preis, vor[0]) if vor and vor[0] is not None else preis
        tief = min(preis, vor[1]) if vor and vor[1] is not None else preis
        mfe = max(pnl, vor[2]) if vor and vor[2] is not None else pnl
        mae = min(pnl, vor[3]) if vor and vor[3] is not None else pnl
        fall = ((hoch - preis) / hoch * 100) if hoch else None
        try:
            minuten = (jetzt - datetime.fromisoformat(eroeffnet)).total_seconds() / 60
        except Exception:
            minuten = None
        atr = b.get("atr")
        atr_pct = (float(atr) / preis * 100) if atr and preis else None

        con.execute(
            "INSERT INTO verlauf (pos_id,ts_utc,minuten,preis,pnl_pct,hoch_seit,"
            "tief_seit,mfe_pct,mae_pct,fall_vom_hoch_pct,atr,atr_pct,rsi,adx,"
            "macd_hist,swing_tief,swing_hoch,regime,spread_bp) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, jetzt.isoformat(), minuten, preis, pnl, hoch, tief, mfe, mae,
             fall, atr, atr_pct, b.get("rsi"), b.get("adx"), b.get("macd_hist"),
             b.get("swing_tief"), b.get("swing_hoch"), b.get("regime"), None))
        zeilen += 1

    con.execute(
        "INSERT OR REPLACE INTO laeufe (lauf_id,ts_utc,offen_echt,offen_schatten,"
        "zeilen,neu,geschlossen,dauer_sek,fehler) VALUES (?,?,?,?,?,?,?,?,?)",
        (lauf_id, jetzt.isoformat(), n_echt, n_schatten, zeilen, neu, geschlossen,
         round(time.time() - start, 1), "; ".join(fehler)[:400] or None))
    con.commit()

    notiz(f"Lauf {lauf_id}: {n_echt} echt + {n_schatten} schatten offen, "
          f"{zeilen} Zeilen, {neu} neu, {geschlossen} beendet, "
          f"{time.time()-start:.0f}s"
          + (f" | Fehler: {'; '.join(fehler)[:120]}" if fehler else ""))
    return zeilen


def status():
    if not os.path.exists(DB):
        print("Noch keine Datenbank - das Programm lief noch nie.")
        return
    con = db_oeffnen()
    p = con.execute("SELECT COUNT(*), SUM(geschlossen IS NULL) FROM positionen").fetchone()
    v = con.execute("SELECT COUNT(*), MIN(ts_utc), MAX(ts_utc) FROM verlauf").fetchone()
    print("\n=== POSITIONSVERLAUF ===\n")
    print(f"  Positionen  : {p[0]} gesamt, davon {p[1] or 0} offen")
    print(f"  Verlaufszeilen: {v[0]}")
    if v[1]:
        print(f"  Zeitraum    : {str(v[1])[:16]} bis {str(v[2])[:16]}")
    # [18-MUENZEN-FRAGE 19.08.2026] Sven fiel auf, dass nur 14 Muenzen
    # auftauchten, obwohl 18 gesammelt werden. Kein Defekt: der Schatten-
    # Sammler schreibt nur, WENN ein Signal zustande kommt. Damit die Frage
    # nicht wieder aufkommt, steht die Differenz jetzt hier.
    try:
        s = sqlite3.connect(f"file:{SCHATTEN_DB}?mode=ro", uri=True, timeout=10)
        geprueft = s.execute("SELECT muenzen_geprueft FROM laeufe "
                             "ORDER BY ts_utc DESC LIMIT 1").fetchone()
        mit_signal = s.execute("SELECT COUNT(DISTINCT muenze) FROM signale").fetchone()
        s.close()
        if geprueft and mit_signal:
            print(f"\n  Schatten-Universum: {geprueft[0]} Muenzen werden geprueft, "
                  f"{mit_signal[0]} hatten bisher ein Signal.")
            print("    (Der Sammler schreibt nur bei Signal ab Score 3 - keine Luecke.)")
    except Exception:
        pass

    print("\n  Je Quelle:")
    # [FIX 19.08.2026] SUM(...) zaehlte durch den JOIN die VERLAUFSZEILEN
    # statt der Positionen - die Anzeige meldete "2 Positionen (49 offen)".
    # Eine Zahl, die groesser ist als ihre eigene Grundgesamtheit, ist immer
    # ein Zaehlfehler. Jetzt zwei getrennte Abfragen statt einer mit JOIN.
    for q, n, off in con.execute(
            "SELECT quelle, COUNT(*), SUM(geschlossen IS NULL) "
            "FROM positionen GROUP BY quelle"):
        z = con.execute(
            "SELECT COUNT(*) FROM verlauf v JOIN positionen p "
            "ON p.pos_id=v.pos_id WHERE p.quelle=?", (q,)).fetchone()[0]
        print(f"    {q:10s} {n:4d} Positionen ({off or 0} offen), {z} Verlaufszeilen")
    print("\n  Vollstaendige Verlaeufe (geschlossen, mind. 12 Messpunkte):")
    fertig = con.execute(
        "SELECT p.quelle, COUNT(*) FROM positionen p WHERE p.geschlossen IS NOT NULL "
        "AND (SELECT COUNT(*) FROM verlauf v WHERE v.pos_id=p.pos_id) >= 12 "
        "GROUP BY p.quelle").fetchall()
    if fertig:
        for q, n in fertig:
            print(f"    {q:10s} {n}")
    else:
        print("    noch keine")
    print("\n  Letzte 5 Laeufe:")
    for z in con.execute("SELECT ts_utc,offen_echt,offen_schatten,zeilen,fehler "
                         "FROM laeufe ORDER BY ts_utc DESC LIMIT 5"):
        print(f"    {str(z[0])[:16]}  {z[1]} echt + {z[2]} schatten -> {z[3]} Zeilen"
              + (f"  [{str(z[4])[:40]}]" if z[4] else ""))
    print()


def selbsttest():
    """Gegentest in beide Richtungen (Regel aus CLAUDE.md Abschnitt 0)."""
    fehler = 0
    print("\n=== Richtung 1: findet es die ECHTEN Daten? ===")
    ep = echte_positionen()
    print(f"  Echte Positionen aus bot_state.json: {len(ep)}")
    for m, p in ep.items():
        print(f"    {m:12s} Einstieg {p['einstieg']:.4f}  id={p['pos_id']}")
    if not ep:
        print("    HINWEIS: keine offenen Positionen - das kann richtig sein.")

    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    sig = neue_schattensignale(con, "2026-01-01T00:00:00+00:00")
    print(f"  Schattensignale ohne Position: {len(sig)}")
    if not sig:
        print("    FEHLER: schatten_universum.db lieferte nichts")
        fehler += 1
    else:
        print(f"    erstes: {sig[0]['muenze']} @ {sig[0]['einstieg']}")
        muenzen = [s["muenze"] for s in sig]
        if len(muenzen) != len(set(muenzen)):
            print("    FEHLER: dieselbe Muenze mehrfach - Regel 'eine je Muenze' greift nicht")
            fehler += 1
        else:
            print(f"    OK: {len(set(muenzen))} verschiedene Muenzen, keine doppelt")

    print("\n=== Richtung 2: faellt es sauber aus, wenn Daten FEHLEN? ===")
    global BOT_STATE
    merk = BOT_STATE
    BOT_STATE = os.path.join(HIER, "gibt_es_nicht.json")
    try:
        leer = echte_positionen()
        print(f"  Ohne bot_state.json: {len(leer)} Positionen (erwartet 0)"
              + ("  OK" if not leer else "  FEHLER"))
        if leer:
            fehler += 1
    except Exception as e:
        print(f"  FEHLER: Exception nach aussen: {e}")
        fehler += 1
    BOT_STATE = merk

    print("\n=== Richtung 3: rechnet die Struktur-Erkennung richtig? ===")
    try:
        import pandas as pd
        # Kuenstlicher Verlauf mit EINEM klaren Swing-Tief bei 90 und Hoch bei 130
        tiefs = [100, 98, 95, 90, 95, 99, 105, 110, 115, 120, 118, 116, 114, 112, 110]
        hochs = [v + 10 for v in tiefs]
        hochs[9] = 130
        # ECHTE Spaltennamen verwenden - der erste Anlauf testete mit
        # "high"/"low" und uebersah damit genau den Fehler, den er
        # finden sollte.
        df = pd.DataFrame({"High": hochs, "Low": tiefs})
        st, sh = _swings(df, fenster=3)
        print(f"  Swing-Tief erkannt: {st}  (erwartet 90)")
        print(f"  Swing-Hoch erkannt: {sh}  (erwartet 130)")
        if st != 90:
            print("    FEHLER: falsches Swing-Tief"); fehler += 1
        if sh != 130:
            print("    FEHLER: falsches Swing-Hoch"); fehler += 1
        leer_df = pd.DataFrame({"High": [1, 2], "Low": [1, 2]})
        st2, sh2 = _swings(leer_df, fenster=3)
        print(f"  Zu wenig Daten -> ({st2}, {sh2})  (erwartet (None, None))"
              + ("  OK" if st2 is None and sh2 is None else "  FEHLER"))
        if st2 is not None or sh2 is not None:
            fehler += 1
    except ImportError:
        print("  pandas fehlt - Strukturtest uebersprungen")

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--status":
        status(); return
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)

    from config.settings import AppConfig
    from data.market_data import DataAgent
    cfg = AppConfig.load()
    data_agent = DataAgent(cfg)
    tf = cfg.trading.default_timeframe
    con = db_oeffnen()

    if arg == "--einmal":
        ein_lauf(con, data_agent, tf); con.close(); return

    notiz(f"START | Takt {TAKT_SEK}s | Hoechstdauer Schatten {MAX_TAGE} Tage")
    try:
        while True:
            try:
                ein_lauf(con, data_agent, tf)
            except Exception as e:
                notiz(f"Lauf fehlgeschlagen: {type(e).__name__}: {str(e)[:100]}")
            time.sleep(TAKT_SEK)
    except KeyboardInterrupt:
        notiz("STOP (Strg+C)")
    finally:
        con.close()


if __name__ == "__main__":
    main()
