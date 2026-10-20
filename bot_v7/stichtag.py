# -*- coding: utf-8 -*-
"""
stichtag.py — prueft am Ende des Messfensters, ob alles gemessen wurde
======================================================================

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Am 27.08.2026 endet das Messfenster. Bis dahin sind Dutzende Befunde,
Vorhaben und offene Fragen zusammengekommen - verteilt auf OFFEN.md,
GEFUNDENE-PROBLEME.md, BOT-HANDBUCH.md und die Tickets.

Sven am 19.08.: "alles dokumentieren damit nichts in Vergessenheit geraet
und am Stichtag auch alles ueberprueft wird".

Eine Liste allein reicht dafuer nicht. Eine Liste wird gelesen und dann
liegengelassen. Dieses Programm PRUEFT stattdessen - es sagt bei jedem
Punkt, ob er erledigt ist, ob genug Daten da sind, und was noch fehlt.

    Was man von Hand pruefen muss, prueft man einmal.
    Was ein Programm prueft, wird jedes Mal geprueft.

WAS ES PRUEFT
-------------
A) Sind genug Daten fuer die anstehenden Entscheidungen da?
B) Stehen die Kennzahlen, wo sie stehen sollen?
C) Sind die Punkte aus OFFEN.md Gruppe C noch offen - oder erledigt?
D) Was muss ein Mensch entscheiden?

NUR LESEND. Aendert nichts, startet nichts, stoppt nichts.

AUFRUF
------
    python stichtag.py               volle Pruefung
    python stichtag.py --kurz        nur die Ampel
    python stichtag.py --selbsttest  Gegentest in beide Richtungen
"""
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
def _stichtag():
    """Das Ende des Messfensters - aus config_zielgroessen.json.

    [20.08.2026] Hier stand das Datum ein zweites Mal fest verdrahtet.
    Beim Verschieben vom 27. auf den 29.08. waeren zwei Wahrheiten
    entstanden: die Konfiguration haette das eine gesagt, dieses Werkzeug
    das andere. Genau das Muster, das diese Woche schon dreimal aufgefallen
    ist (Epochen im Cockpit 4.92, Muenzzahl 4.93, Allzeithoch 4.94).
    """
    try:
        import json as _j
        with open(os.path.join(HIER, "config_zielgroessen.json"),
                  encoding="utf-8") as f:
            d = _j.load(f).get("messfenster_ende")
        if d:
            return str(d)
    except Exception:
        pass
    return "2026-08-29"      # Rueckfall, falls die Konfiguration fehlt


STICHTAG = _stichtag()
K_BASIS = 0.505

GRUEN, GELB, ROT, GRAU = "OK", "PRUEFEN", "FEHLT", "-"


def _lies(datei):
    try:
        with open(os.path.join(HIER, datei), encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _db(name):
    p = os.path.join(HIER, "data_store", name)
    if not os.path.exists(p):
        return None
    try:
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=20)
    except Exception:
        return None


def _journal():
    try:
        with open(os.path.join(HIER, "data_store", "trades_v5.json"),
                  encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _ziele():
    try:
        with open(os.path.join(HIER, "config_zielgroessen.json"),
                  encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ============================================================ A) Datenlage
def pruefe_datenlage():
    """Reicht das Gesammelte fuer die anstehenden Entscheidungen?"""
    out = []

    # 1. Trades im Messfenster
    j = _journal()
    mf = [e for e in j if e.get("type") == "SELL"
          and str(e.get("time", "")) >= "2026-08-13T13:21"]
    out.append(("Verkaeufe im Messfenster", len(mf), 30,
                "Unter 30 ist jede Kennzahl Rauschen (Handbuch 4.44)"))

    # 2. Positionsverlaeufe - Grundlage fuer den Ausstiegsvergleich
    con = _db("positionsverlauf.db")
    fertig = 0
    if con:
        try:
            fertig = con.execute(
                "SELECT COUNT(*) FROM positionen p WHERE "
                "(SELECT COUNT(*) FROM verlauf v WHERE v.pos_id=p.pos_id) >= 12"
            ).fetchone()[0]
        except Exception:
            pass
        con.close()
    out.append(("Positionsverlaeufe mit >=12 Messpunkten", fertig, 30,
                "Grundlage fuer den Vergleich der Ausstiegsregeln (4.64)"))

    # 3. Schatten-Universum
    con = _db("schatten_universum.db")
    sig = 0
    if con:
        try:
            sig = con.execute("SELECT COUNT(*) FROM signale").fetchone()[0]
        except Exception:
            pass
        con.close()
    out.append(("Schatten-Signale (Muenzfrage)", sig, 1000,
                "Fuer die Frage, welche Muenze ihre Reibung verdient"))

    # 4. Nachlauf nach Ausstiegen
    con = _db("nachlauf.db")
    nach = 0
    if con:
        try:
            nach = con.execute(
                "SELECT COUNT(*) FROM nachlauf WHERE art='exit' AND p24h IS NOT NULL"
            ).fetchone()[0]
        except Exception:
            pass
        con.close()
    out.append(("Ausstiege mit 24-h-Nachlauf", nach, 30,
                "War der Stop-Loss richtig? (TODO Punkt 1)"))

    # 4b. RSI-Ausstieg: unabhaengige TAGE, nicht Verkaeufe
    #
    # [19.08.2026] Sven: "wichtig dass wir das auf dem Schirm behalten und
    # wenn es soweit ist nicht vergessen zu bearbeiten". Genau dafuer steht
    # es hier - eine Zeile, die am Stichtag von selbst rot oder gruen wird.
    #
    # Gezaehlt werden TAGE, nicht Verkaeufe. Am 19.08. lagen 35 Faelle vor,
    # davon 16 an einem einzigen Tag: auf Verkaufsebene t=2,88 (bedeutsam),
    # auf Tagesebene t=0,61 (nichts). Wer Verkaeufe zaehlt, zaehlt dieselbe
    # Marktbewegung mehrfach. Handbuch 4.84.
    con = _db("nachlauf.db")
    rsi_tage = 0
    if con:
        try:
            rsi_tage = con.execute(
                "SELECT COUNT(DISTINCT substr(ts_utc,1,10)) FROM nachlauf "
                "WHERE art='exit' AND r1h IS NOT NULL "
                "AND UPPER(grund) LIKE '%RSI%'").fetchone()[0]
        except Exception:
            pass
        con.close()
    out.append(("Tage mit RSI-Ausstieg (nicht Verkaeufe!)", rsi_tage, 25,
                "Steigt der Kurs nach RSI-Ausstiegen weiter? (Befund 59/60)"))

    # 5. Schatten-Ausstiege (trend_exit im Schattenmodus)
    con = _db("telemetrie.db")
    sch = 0
    if con:
        try:
            sch = con.execute("SELECT COUNT(*) FROM schatten_exits").fetchone()[0]
        except Exception:
            pass
        con.close()
    out.append(("Schatten-Ausstiege (trend_exit)", sch, 20,
                "Vergleich: Ausstieg bei -1 % gegen Aussitzen"))

    return out


# ============================================================ B) Kennzahlen
def pruefe_kennzahlen():
    """Wo stehen die Zielgroessen?"""
    z = _ziele()
    j = _journal()
    sells = [e for e in j if e.get("type") == "SELL" and e.get("pnl_pct") is not None]
    if not sells:
        return []
    netto = [float(e["pnl_pct"]) - K_BASIS for e in sells]
    gew = [v for v in netto if v > 0]
    ver = [v for v in netto if v <= 0]
    ev = sum(netto) / len(netto)
    g = sum(gew) / len(gew) if gew else 0.0
    v = abs(sum(ver) / len(ver)) if ver else 0.0
    payoff = g / v if v else None
    pf = sum(gew) / abs(sum(ver)) if ver and sum(ver) else None
    mfe = [e for e in sells if e.get("mfe_pct") is not None]
    versch = (sum(float(e["mfe_pct"]) - float(e["pnl_pct"]) for e in mfe) / len(mfe)
              if mfe else None)

    def zeile(schluessel, wert, nk=3):
        d = z.get(schluessel) or {}
        ziel, richtung = d.get("ziel"), d.get("richtung", "hoch")
        titel = d.get("titel", schluessel)
        if wert is None or ziel is None:
            return (titel, None, ziel, GRAU)
        erreicht = wert >= ziel if richtung == "hoch" else wert <= ziel
        return (titel, round(wert, nk), ziel, GRUEN if erreicht else ROT)

    out = [zeile("ev_netto_pct", ev), zeile("payoff_ratio", payoff),
           zeile("profit_faktor", pf), zeile("verschenkt_pp", versch)]

    # Drawdown aus der eigenen Auswertung
    try:
        sys.path.insert(0, HIER)
        from drawdown_auswertung import kapitalkurve, drawdown, zwei_niveaus, geteilte_kurven
        k = kapitalkurve()
        if k:
            verdacht, _, _, _ = zwei_niveaus(k)
            teil = geteilte_kurven(k)[0] if verdacht else k
            d = drawdown(teil)
            if d:
                out.append(zeile("max_drawdown_pct", d["max_dd_pct"], 2))
    except Exception:
        out.append(("Groesster Rueckschlag", None, None, GRAU))
    return out


# ============================================================ C) Offene Punkte
def pruefe_offene_punkte():
    """Punkte aus OFFEN.md Gruppe C - was davon ist im Code erledigt?"""
    offen = _lies("OFFEN.md")
    m = re.search(r"^## C —.*?(?=^## D —|\Z)", offen, re.S | re.M)
    punkte = re.findall(r"^- \[([ x])\] \*\*([^*]+)\*\*", m.group(0), re.M) if m else []

    # Automatisch pruefbare Punkte: (Kennzeichen, Datei, Muster, erwartet)
    proben = [
        ("Breakeven-Puffer", "risk/exit_rules.py",
         r"BREAKEVEN_PUFFER_PCT\s*=\s*([\d.]+)", 0.35,
         "muss ueber den echten Kosten liegen (0,505 % + Marge)"),
        ("Trailing-Schwelle", "risk/exit_rules.py",
         r"TRAIL_AB_PCT\s*=\s*([\d.]+)", 1.2,
         "Nulllinie liegt bei 1,52 % (Handbuch 4.64)"),
        ("Regime-Filter Kosten", "features/regime_adaptiv.py",
         r"KOSTEN_PCT\s*=\s*([\d.]+)", 0.32,
         "muss auf 0,505 (Handbuch 4.53)"),
    ]
    # [13.09.2026] Seit der Zentralisierung stehen an diesen Stellen keine
    # ZAHLEN mehr, sondern Rechnungen: BREAKEVEN_PUFFER_PCT = round(
    # K_BASIS_PCT + MARGE, 3) und KOSTEN_PCT = K_BASIS_PCT. Das Muster
    # unten sucht Ziffern und fand deshalb "nicht gefunden" - bei
    # RICHTIGEM Code. Ein Pruefwerkzeug, das nichts findet, wo alles
    # stimmt, ist so wertlos wie eines, das falsch meldet: beide Male
    # lernt man, die Zeile zu ueberlesen.
    aus_der_quelle = (
        (r"BREAKEVEN_PUFFER_PCT\s*=\s*round\(\s*K_BASIS_PCT",
         "gerechnet aus K_BASIS_PCT"),
        (r"KOSTEN_PCT\s*=\s*K_BASIS_PCT",
         "aus core/kosten.py"),
        (r"K_BASIS\s*=\s*K_BASIS_PCT",
         "aus core/kosten.py"),
    )
    ergebnis = []
    for name, datei, muster, alt, warum in proben:
        txt = _lies(datei)
        tref = re.search(muster, txt)
        if not tref:
            zentral = next((t for m, t in aus_der_quelle
                            if re.search(m, txt)), None)
            if zentral:
                ergebnis.append((name, zentral, GRUEN, warum))
            else:
                ergebnis.append((name, "nicht gefunden", GRAU, warum))
            continue
        wert = float(tref.group(1))
        zustand = ROT if abs(wert - alt) < 1e-9 else GRUEN
        ergebnis.append((name, f"{wert}", zustand, warum))

    # Alte Kostenkonstanten im ganzen Projekt
    alt_treffer = 0
    for wurzel, _, dateien in os.walk(HIER):
        # patches_nach_27_08 ist ausgenommen: die Patch-Skripte
        # dokumentieren in ihrem Kopftext die Rechnung, die zum ALTEN Wert
        # fuehrte. Das ist Chronik und dort richtig - sie wurden am
        # 12.09. angewendet und aendern nichts mehr.
        if any(x in wurzel for x in ("__pycache__", ".git", "_archive", "docs",
                                     "v4_referenz", "patches_nach_27_08")):
            continue
        for d in dateien:
            if not d.endswith(".py"):
                continue
            t = _lies(os.path.relpath(os.path.join(wurzel, d), HIER))
            # [13.09.2026] Nur AUSFUEHRBARE Zeilen zaehlen. Vorher schlug das
            # Muster auch in Kommentaren an - nach der Korrektur aller
            # Konstanten blieben zwei Kommentar-Treffer stehen, die die
            # Herleitung des ALTEN Werts erklaeren und dort richtig sind.
            # Eine Warnung, die nie weggeht, wird nach drei Tagen nicht mehr
            # gelesen - genau das macht sie wertlos.
            _code = "\n".join(z.split("#", 1)[0] for z in t.split("\n"))
            if re.search(r"(KOSTEN|GEBUEHR|FEE)[\w_]*\s*=\s*0\.32\b", _code, re.I):
                alt_treffer += 1
    ergebnis.append(("Dateien mit alter Kostenannahme 0,32",
                     str(alt_treffer), ROT if alt_treffer else GRUEN,
                     "Liste in Handbuch 4.53"))
    return punkte, ergebnis


# ============================================================ D) Entscheidungen
ENTSCHEIDUNGEN = [
    ("Ausstiegsregel", "Welche Leiter ab dem 28.08.?",
     "Handbuch 4.64 + Auswertung von positionsverlauf.py. "
     "Nicht raten - erst die Verlaeufe rechnen."),
    ("Kostenkonstanten", "Alle neun Stellen auf 0,505 ziehen?",
     "Handbuch 4.53. Braucht eine Epochengrenze, sonst sind die "
     "Schattenwerte nicht mehr vergleichbar."),
    ("Gebuehren-Doppelbuchung", "An der Quelle reparieren?",
     "GEFUNDENE-PROBLEME 42: engine.py:401, NICHT app.py. Vorher das "
     "ccxt-Verhalten belegen."),
    ("total_equity", "In zwei Spalten trennen?",
     "GEFUNDENE-PROBLEME 44. Betrifft Positionsgroesse und Risikopruefung."),
    ("DCA-Telemetrie", "Den Hauptkaufpfad protokollieren?",
     "GEFUNDENE-PROBLEME 40: 98,4 % der Kaeufe stehen in keiner Statistik."),
    ("Warte-Auftraege", "Limit-Orders im Schattenlauf messen?",
     "OFFEN.md C1: groesster gemessener Hebel, aber Gegenauslese ungemessen."),
    ("Muenzfrage", "Universum erweitern?",
     "Schatten-Universum, 18 Muenzen. Erwartung: DOGE."),
    ("Take-Profit", "Bleibt er abgeschaltet?",
     "GEFUNDENE-PROBLEME 46: take_profit_pct = 0.0, ohne Begruendung."),
    # [20.08.2026] Sven: "stelle sicher, dass nach dem Freeze nach der
    # bestmoeglichen Moeglichkeit geguckt wird, damit nicht so viel
    # hergeschenkt wird."
    ("Allzeithoch", "Dynamisch statt verdrahtet?",
     "GEFUNDENE-PROBLEME 63: im Code 109.114 $, tatsaechlich 126.200 $. "
     "Der Bot haelt den Baerenmarkt fuer 9 Prozentpunkte flacher als er "
     "ist und kauft 20 % groessere Positionen. Patch liegt bereit: "
     "patches_nach_27_08/patch_63_ath_dynamisch.py"),
    ("Verschenkte Bewegung", "Welche Ausstiegsregel holt am meisten?",
     "Gemessen 20.08.: im Schnitt 1,24 PP je Verkauf zurueckgegeben "
     "(n=20 Tage, t=7,2 - kein Zufall). STOP_LOSS und TREND_EXIT sind "
     "die teuersten. Kandidaten gegeneinander rechnen auf "
     "positionsverlauf.db, NICHT raten."),
]


# ============================================================ Bericht
def bericht(kurz=False):
    heute = datetime.now(timezone.utc).date()
    ziel = datetime.strptime(STICHTAG, "%Y-%m-%d").date()
    tage = (ziel - heute).days
    print("\n" + "=" * 74)
    print(f"  STICHTAG-PRUEFUNG  —  Messfenster endet {STICHTAG}")
    if tage > 0:
        print(f"  Heute {heute}, noch {tage} Tage.")
    elif tage == 0:
        print(f"  HEUTE IST DER STICHTAG.")
    else:
        print(f"  Stichtag war vor {-tage} Tagen.")
    print("=" * 74)

    print("\n--- A) Reichen die Daten? ---\n")
    print(f"  {'Was':<42}{'ist':>8}{'noetig':>8}   Status")
    print("  " + "-" * 70)
    ampel_a = []
    for name, ist, soll, warum in pruefe_datenlage():
        st = GRUEN if ist >= soll else (GELB if ist >= soll * 0.5 else ROT)
        ampel_a.append(st)
        print(f"  {name:<42}{ist:>8}{soll:>8}   {st}")
        if not kurz:
            print(f"    {warum}")

    print("\n--- B) Wo stehen die Zielgroessen? ---\n")
    print(f"  {'Kennzahl':<32}{'ist':>10}{'Ziel':>10}   Status")
    print("  " + "-" * 66)
    ampel_b = []
    for titel, ist, soll, st in pruefe_kennzahlen():
        ampel_b.append(st)
        i = f"{ist}" if ist is not None else "-"
        s = f"{soll}" if soll is not None else "-"
        print(f"  {titel:<32}{i:>10}{s:>10}   {st}")

    punkte, proben = pruefe_offene_punkte()
    print("\n--- C) Was steht noch im Code, wie es war? ---\n")
    print(f"  {'Stelle':<38}{'Wert':>14}   Status")
    print("  " + "-" * 66)
    for name, wert, st, warum in proben:
        print(f"  {name:<38}{wert:>14}   {st}")
        if not kurz:
            print(f"    {warum}")

    offen_n = sum(1 for z, _ in punkte if z == " ")
    print(f"\n  OFFEN.md Gruppe C: {offen_n} von {len(punkte)} Punkten noch offen")
    if not kurz:
        for zeichen, titel in punkte:
            print(f"    [{zeichen}] {titel[:66]}")

    print("\n--- D) Was ein Mensch entscheiden muss ---\n")
    for i, (thema, frage, hinweis) in enumerate(ENTSCHEIDUNGEN, 1):
        print(f"  {i}. {thema}: {frage}")
        if not kurz:
            print(f"     {hinweis}")

    print("\n" + "=" * 74)
    rot = ampel_a.count(ROT) + ampel_b.count(ROT)
    gelb = ampel_a.count(GELB)
    if rot == 0 and gelb == 0:
        print("  ERGEBNIS: Datenlage und Kennzahlen sind bereit.")
    else:
        print(f"  ERGEBNIS: {rot}x FEHLT, {gelb}x PRUEFEN — noch nicht entscheidungsreif.")
    print("=" * 74 + "\n")


def selbsttest():
    fehler = 0
    print("\n=== Richtung 1: findet es die echten Daten? ===")
    for name, ist, soll, _ in pruefe_datenlage():
        print(f"  {name:<42} {ist:>7}")
        if ist is None:
            fehler += 1
    k = pruefe_kennzahlen()
    print(f"\n  Kennzahlen berechnet: {len(k)}")
    if len(k) < 4:
        print("    FEHLER: zu wenige Kennzahlen"); fehler += 1
    for titel, ist, soll, st in k:
        print(f"    {titel:<32}{str(ist):>10}  {st}")

    print("\n=== Richtung 2: erkennt es UNVERAENDERTE Stellen als offen? ===")
    _, proben = pruefe_offene_punkte()
    rot = [p for p in proben if p[2] == ROT]
    print(f"  {len(rot)} von {len(proben)} Proben melden 'noch nicht geaendert'")
    for p in rot:
        print(f"    {p[0]}: {p[1]}")
    if not rot:
        print("    ACHTUNG: keine einzige Probe meldet offen - stimmt das?")
        fehler += 1

    print("\n=== Richtung 3: faellt es sauber aus, wenn Dateien fehlen? ===")
    global HIER
    merk = HIER
    HIER = os.path.join(merk, "gibt_es_nicht")
    try:
        d = pruefe_datenlage()
        k2 = pruefe_kennzahlen()
        print(f"  Ohne Projektordner: {len(d)} Datenzeilen, {len(k2)} Kennzahlen"
              f"  {'OK' if k2 == [] else 'FEHLER'}")
        if k2 != []:
            fehler += 1
    except Exception as e:
        print(f"  FEHLER: Exception nach aussen: {type(e).__name__}: {e}")
        fehler += 1
    HIER = merk

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    bericht(kurz=(arg == "--kurz"))
