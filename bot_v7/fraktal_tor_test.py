# -*- coding: utf-8 -*-
"""Pruefung des Fraktal-Tors und der Live-Bestandsuebernahme (14.09.2026).

BEIDE RICHTUNGEN, wie CLAUDE.md Abschnitt 0 es verlangt:
  - laesst das Werkzeug nichts Falsches durch?
  - findet es den echten Fall AUCH?

Ein Tor, das alles ablehnt, besteht die erste Haelfte muehelos und ist
trotzdem wertlos. Deshalb steht zu jedem "muss ablehnen" ein "muss
erlauben" daneben.

Aufruf:  FRAKTAL_TOR_TEST.bat  (Doppelklick)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === LOG UMLENKEN - MUSS VOR JEDEM PROJEKT-IMPORT STEHEN ===
#
# Dieser Test importiert Produktionsmodule (fraktal_tor, state_manager),
# und die protokollieren ueber core.logger. Ohne diese Zeilen landen
# Testmeldungen mit dem Attrappen-Symbol TEST/USDC im echten
# data_store/system.log des laufenden Echtgeld-Bots - genau das ist in
# der Nacht zum 15.09. passiert, 23 Zeilen lang.
#
# Die Reihenfolge ist entscheidend: core.logger liest die Variable
# beim Anlegen des Logger-Objekts, und das passiert beim ERSTEN
# Import. Steht diese Zeile danach, wirkt sie nicht mehr.
os.environ["TI_LOG_FILE"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data_store", "test.log")

import pandas as pd

from features.fraktal_konfluenz import golden_pocket
from features.fraktal_tor import FraktalTor, MIN_ZONEN_SCORE

BESTANDEN = []
DURCHGEFALLEN = []


def pruefe(name, bedingung, zusatz=""):
    if bedingung:
        BESTANDEN.append(name)
        print(f"    OK    {name}")
    else:
        DURCHGEFALLEN.append(name)
        print(f"    FEHLT {name}   {zusatz}")


# ====================================================================
# Hilfen: kuenstliche Kerzen mit BEKANNTEN Swing-Punkten
# ====================================================================
def zickzack(punkte, kerzen_je_bein=12):
    """Baut Kerzen, die exakt die vorgegebenen Wendepunkte durchlaufen.

    So sind Hoch und Tief der Wellen VORHER bekannt - damit laesst sich
    die Fibonacci-Rechnung von Hand nachrechnen, statt sie nur
    plausibel zu finden. Genau das verlangt CLAUDE.md Abschnitt 0:
    gegen einen von Hand nachgerechneten Einzelfall pruefen.
    """
    reihe = []
    for a, b in zip(punkte, punkte[1:]):
        for i in range(kerzen_je_bein):
            reihe.append(a + (b - a) * (i / kerzen_je_bein))
    reihe.append(punkte[-1])

    zeilen = []
    for i, p in enumerate(reihe):
        vorher = reihe[i - 1] if i else p
        # High/Low haengen NUR am eigenen Schlusskurs, nicht am
        # Vorgaenger.
        #
        # Erster Versuch war `High = max(p, vorher) * 1.0005`. Damit
        # bekommen die Kerze AN der Spitze und die direkt danach
        # denselben High-Wert - und swing_punkte verwirft ihn dann zu
        # Recht: es verlangt ausdruecklich Eindeutigkeit
        # (features/chartanalyse.py:148, `(fenster == h[i]).sum() == 1`).
        # Ergebnis waren null Swing-Punkte und damit ein Test, der
        # nichts geprueft hat, aber gruen aussah, waere die Zeile
        # "ueberhaupt Zonen gefunden" nicht dabei gewesen.
        zeilen.append({
            "Open": vorher,
            "High": p * 1.0005,
            "Low": p * 0.9995,
            "Close": p,
            "Volume": 1000.0,
        })
    return pd.DataFrame(zeilen)


class AttrappeDataAgent:
    """Liefert vorbereitete Kerzen statt echter Boersendaten."""

    def __init__(self, je_zeitrahmen):
        self.je_zeitrahmen = je_zeitrahmen
        self.abrufe = 0

    def fetch_snapshot(self, symbol, tf="1h", limit=200):
        self.abrufe += 1
        df = self.je_zeitrahmen.get(tf)
        if df is None:
            return None

        class _S:
            pass
        s = _S()
        s._df = df
        return s


# ====================================================================
# TEIL 1 - Golden Pocket von Hand nachgerechnet
# ====================================================================
print()
print("=" * 72)
print("  TEIL 1  Golden Pocket - gegen eine Handrechnung")
print("=" * 72)

# Welle von 100 auf 200. Spanne 100.
#   0,618 Retracement:  200 - 100*0,618 = 138,20
#   0,65  Retracement:  200 - 100*0,650 = 135,00
# Das Band ist also 135,00 bis 138,20.
band = golden_pocket(200.0, 100.0, aufwaerts=True)
print(f"\n  Welle 100 -> 200, Golden Pocket = {band}")
print(f"  Handrechnung:  200 - 100*0,618 = {200 - 100 * 0.618:.2f}")
print(f"                 200 - 100*0,650 = {200 - 100 * 0.650:.2f}")

pruefe("Golden Pocket Unterkante = 135,00",
       abs(band[0] - 135.0) < 1e-9, f"ist {band[0]}")
pruefe("Golden Pocket Oberkante = 138,20",
       abs(band[1] - 138.2) < 1e-9, f"ist {band[1]}")
pruefe("Unterkante liegt unter Oberkante", band[0] < band[1])

# Abwaerts: dieselbe Welle, andere Richtung -> Band muss trotzdem
# sortiert zurueckkommen (Svens Abschnitt 1B).
band_ab = golden_pocket(200.0, 100.0, aufwaerts=False)
pruefe("auch abwaerts sortiert (unten < oben)", band_ab[0] < band_ab[1],
       f"ist {band_ab}")


# ====================================================================
# TEIL 2 - Das Tor: laesst es den guten Preis durch?
# ====================================================================
print()
print("=" * 72)
print("  TEIL 2  Das Tor - beide Richtungen")
print("=" * 72)

# Zwei Zeitrahmen mit DEMSELBEN Verlauf. Dadurch liegen die Stufen
# beider Zeitrahmen aufeinander: echte Multi-Timeframe-Konfluenz.
#
# Der Verlauf enthaelt MEHRERE AUFWAERTSWELLEN mit deutlicher Spanne.
# Das ist seit dem Richtungsfilter noetig: Das Tor benutzt nur noch
# Ruecksetzer von Aufwaertsbewegungen, weil die Ruecksetzer einer
# Abwaertsbewegung Widerstaende sind (siehe NUR_AUFWAERTSWELLEN).
#
# Der erste Entwurf hatte im sichtbaren Bereich fast nur
# Abwaertswellen. Ergebnis: null Zonen, und die beiden Pruefungen
# "Preis in der Zone wird ERLAUBT" und "Tor lehnt nicht pauschal alles
# ab" fielen durch - zu Recht. Ein Tor, das immer nein sagt, besteht
# jede Ablehnungspruefung und ist trotzdem wertlos.
welle = [100.0, 200.0, 150.0, 240.0, 180.0, 260.0, 205.0]
daten = {"1h": zickzack(welle), "4h": zickzack(welle, kerzen_je_bein=8)}

agent = AttrappeDataAgent(daten)
tor = FraktalTor(agent)

# Ueber das Tor selbst, nicht ueber zonen_aus_zeitrahmen: Nur das Tor
# kennt die drei Handelsfilter (Richtung, Wellengroesse, Ruecksetzer).
# Der Test muss pruefen, was der Bot wirklich benutzt.
zonen = tor._kaufzonen(daten, 260.0)
tauglich = [z for z in zonen if z["score"] >= MIN_ZONEN_SCORE]
print(f"\n  Gefundene Zonen: {len(zonen)}, davon Score >= {MIN_ZONEN_SCORE}: "
      f"{len(tauglich)}")
for z in tauglich[:5]:
    print(f"    {z['unten']:8.2f} - {z['oben']:8.2f}   Score {z['score']}"
          f"   Quellen {z['quellen']}   {'+'.join(z['zeitrahmen'])}"
          f"   {'GOLDEN POCKET' if z['golden_pocket'] else ''}")

pruefe("ueberhaupt taugliche Zonen gefunden", len(tauglich) > 0,
       "ohne Zonen sagt der Test nichts aus!")

if tauglich:
    # RICHTUNG A: Preis MITTEN in einer Zone -> muss erlaubt sein
    ziel = tauglich[0]
    preis_gut = ziel["mitte"]
    u_gut = tor.pruefe("TEST/USDC", preis_gut)
    print(f"\n  A) Preis {preis_gut:.2f} (Zonenmitte) -> "
          f"{'ERLAUBT' if u_gut['erlaubt'] else 'ABGELEHNT'}")
    print(f"     {u_gut['grund']}")
    pruefe("Preis in der Zone wird ERLAUBT", u_gut["erlaubt"],
           u_gut["grund"])

    # RICHTUNG B: Preis weit weg (am Hoch) -> muss abgelehnt werden.
    # Das ist genau der Fall vom 14.09.: Trendfolge kauft am Hoch.
    preis_hoch = 259.5
    u_hoch = tor.pruefe("TEST/USDC", preis_hoch)
    print(f"\n  B) Preis {preis_hoch:.2f} (am Hoch, wie am 14.09.) -> "
          f"{'ERLAUBT' if u_hoch['erlaubt'] else 'ABGELEHNT'}")
    print(f"     {u_hoch['grund']}")
    pruefe("Preis am Hoch wird ABGELEHNT", not u_hoch["erlaubt"],
           "das Tor haelt den Fehler vom 14.09. NICHT auf!")

    # Gegenprobe gegen ein Tor, das einfach alles ablehnt
    pruefe("Tor lehnt nicht pauschal alles ab",
           u_gut["erlaubt"] and not u_hoch["erlaubt"],
           "ein Tor, das immer nein sagt, ist wertlos")

# RICHTUNG C: nur EIN Zeitrahmen -> keine Konfluenz pruefbar -> ablehnen
tor_einzeln = FraktalTor(AttrappeDataAgent({"1h": zickzack(welle)}))
u_einzeln = tor_einzeln.pruefe("TEST/USDC", 205.0)
print(f"\n  C) nur ein Zeitrahmen -> "
      f"{'ERLAUBT' if u_einzeln['erlaubt'] else 'ABGELEHNT'}")
print(f"     {u_einzeln['grund']}")
pruefe("ein einzelner Zeitrahmen wird ABGELEHNT", not u_einzeln["erlaubt"],
       "ohne zweiten Zeitrahmen gibt es keine Konfluenz")

# RICHTUNG D: gar keine Daten -> ablehnen, nicht durchwinken
tor_leer = FraktalTor(AttrappeDataAgent({}))
u_leer = tor_leer.pruefe("TEST/USDC", 205.0)
pruefe("ohne Daten wird ABGELEHNT", not u_leer["erlaubt"], u_leer["grund"])

# RICHTUNG E: Preis 0 / ungueltig -> ablehnen
u_null = tor.pruefe("TEST/USDC", 0)
pruefe("Preis 0 wird ABGELEHNT", not u_null["erlaubt"])


# ====================================================================
# TEIL 3 - Der Kerzen-Cache
# ====================================================================
print()
print("=" * 72)
print("  TEIL 3  Cache - der Bot prueft alle 12 s")
print("=" * 72)

agent2 = AttrappeDataAgent(daten)
tor2 = FraktalTor(agent2)
tor2.pruefe("TEST/USDC", 205.0)
nach_erstem = agent2.abrufe
for _ in range(10):
    tor2.pruefe("TEST/USDC", 205.0)
nach_elftem = agent2.abrufe

print(f"\n  Abrufe nach 1 Pruefung: {nach_erstem}")
print(f"  Abrufe nach 11 Pruefungen: {nach_elftem}")
pruefe("Kerzen werden zwischengespeichert", nach_elftem == nach_erstem,
       f"{nach_elftem} Abrufe statt {nach_erstem} - laeuft ins Abruflimit!")


# ====================================================================
# TEIL 4 - Live-Bestandsuebernahme
# ====================================================================
print()
print("=" * 72)
print("  TEIL 4  Live-Bestandsuebernahme (runtime/state_manager.py)")
print("=" * 72)


class AttrappeExecution:
    """Tut so, als waere sie die Boerse - mit steuerbaren Antworten."""

    def __init__(self, bestand, einstaende, min_mengen=None):
        self._bestand = bestand
        self._einstaende = einstaende
        self._min = min_mengen or {}
        self.exchange = self

    def get_balance(self):
        return {"total": dict(self._bestand), "free": dict(self._bestand)}

    def bestand_einstand(self, symbol, menge, limit=100):
        return self._einstaende.get(symbol)

    def market(self, symbol):
        return {"limits": {"amount": {"min": self._min.get(symbol, 0)}}}


class AttrappeRiskEngine:
    def __init__(self):
        self.open_positions = {}


class AttrappeApp:
    def __init__(self, execution):
        self.execution = execution
        self.risk_engine = AttrappeRiskEngine()

        class _T:
            mode = "live"
            coins = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]

        class _C:
            trading = _T()
        self.config = _C()


from runtime.state_manager import StateManager   # noqa: E402

# --- Fall 1: echter Bestand mit belegtem Einstand -> UEBERNEHMEN ---
# Die Zahlen sind die echten vom 14.09.: 0,00041 BTC.
ex1 = AttrappeExecution(
    bestand={"BTC/USDC": 0, "BTC": 0.00041, "USDC": 3.69},
    einstaende={"BTC/USDC": {"preis_schnitt": 79170.0, "kostenbasis": 32.49,
                             "gebuehr": 0.03, "ungedeckt": 0.0,
                             "verkaeufe_gesehen": 0, "ausfuehrungen": 4}})
app1 = AttrappeApp(ex1)
StateManager(app1)._uebernehme_live_bestand()
pos1 = app1.risk_engine.open_positions.get("BTC/USDC")

print(f"\n  Fall 1: 0,00041 BTC mit belegtem Einstand")
if pos1:
    print(f"    Position angelegt: qty {pos1['qty']:.8f}, "
          f"Einstand {pos1['entry_price']:,.2f}$, "
          f"Kostenbasis {pos1['cost_basis']:.4f}$")
pruefe("Bestand mit Einstand wird uebernommen", pos1 is not None,
       "die 0,00041 BTC bleiben unueberwacht!")
if pos1:
    pruefe("echter Einstand, NICHT der Marktpreis",
           abs(pos1["entry_price"] - 79170.0) < 1e-6,
           f"ist {pos1['entry_price']}")
    pruefe("Position ist aktiv", pos1.get("active") is True)
    pruefe("als uebernommen gekennzeichnet",
           pos1.get("_uebernommen_live") is True)
    # Handrechnung Stop-Loss: 79170 * (1 - 0,025) = 77190,75
    sl = pos1["entry_price"] * (1 - 2.5 / 100)
    print(f"    Stop-Loss laege bei {sl:,.2f}$ "
          f"(Handrechnung 79170 * 0,975 = {79170 * 0.975:,.2f})")
    pruefe("Stop-Loss-Bezugspunkt stimmt", abs(sl - 77190.75) < 0.01)

# --- Fall 2: Bestand OHNE belegbaren Einstand -> NICHT anlegen ---
ex2 = AttrappeExecution(
    bestand={"BTC": 0.00041},
    einstaende={})                      # keine Ausfuehrungen auffindbar
app2 = AttrappeApp(ex2)
StateManager(app2)._uebernehme_live_bestand()
print(f"\n  Fall 2: Bestand ohne auffindbare Ausfuehrungen")
pruefe("ohne Einstand wird KEINE Position angelegt",
       "BTC/USDC" not in app2.risk_engine.open_positions,
       "ein Stop-Loss auf geratener Zahl sieht aus wie Schutz und ist keiner")

# --- Fall 3: Staub unter Mindestmenge -> NICHT anlegen ---
ex3 = AttrappeExecution(
    bestand={"BTC": 0.0000001},
    einstaende={"BTC/USDC": {"preis_schnitt": 79170.0, "kostenbasis": 0.01,
                             "gebuehr": 0.0, "ungedeckt": 0.0,
                             "verkaeufe_gesehen": 0, "ausfuehrungen": 1}},
    min_mengen={"BTC/USDC": 0.00001})
app3 = AttrappeApp(ex3)
StateManager(app3)._uebernehme_live_bestand()
print(f"\n  Fall 3: Staub unter Bybit-Mindestmenge")
pruefe("Staub wird NICHT als Position gefuehrt",
       "BTC/USDC" not in app3.risk_engine.open_positions,
       "ein Stop-Loss, der nicht verkaufen kann, scheitert bei jedem Auslosen")

# --- Fall 4: gar kein Bestand -> nichts tun, nicht abstuerzen ---
ex4 = AttrappeExecution(bestand={"USDC": 36.25}, einstaende={})
app4 = AttrappeApp(ex4)
StateManager(app4)._uebernehme_live_bestand()
print(f"\n  Fall 4: nur USDC, keine Coins")
pruefe("ohne Coin-Bestand passiert nichts",
       len(app4.risk_engine.open_positions) == 0)

# --- Fall 5: Position existiert schon -> nicht ueberschreiben ---
ex5 = AttrappeExecution(
    bestand={"BTC": 0.00041},
    einstaende={"BTC/USDC": {"preis_schnitt": 79170.0, "kostenbasis": 32.49,
                             "gebuehr": 0.03, "ungedeckt": 0.0,
                             "verkaeufe_gesehen": 0, "ausfuehrungen": 4}})
app5 = AttrappeApp(ex5)
app5.risk_engine.open_positions["BTC/USDC"] = {
    "active": True, "entry_price": 60000.0, "qty": 0.00041}
StateManager(app5)._uebernehme_live_bestand()
print(f"\n  Fall 5: Position ist schon da")
pruefe("bestehende Position wird NICHT ueberschrieben",
       app5.risk_engine.open_positions["BTC/USDC"]["entry_price"] == 60000.0,
       "sonst geht der echte Einstand einer laufenden Position verloren")


# ====================================================================
# TEIL 5 - Fibonacci-Ausstiegsziele
# ====================================================================
print()
print("=" * 72)
print("  TEIL 5  Fibonacci-Ausstiegsziele (features/fraktal_ziele.py)")
print("=" * 72)

from features.fraktal_ziele import (ziele_berechnen, erreichtes_ziel,   # noqa: E402
                                    ZIELE, ZIEL_VERKAUF, beschreibung)

# Welle 100 -> 200, Spanne 100. Von Hand:
#   1,000  =  100 + 100 * 1,000  =  200,00   (das Wellenhoch)
#   1,272  =  100 + 100 * 1,272  =  227,20
#   1,618  =  100 + 100 * 1,618  =  261,80
kaufwelle = {"hoch": 200.0, "tief": 100.0}
z = ziele_berechnen(kaufwelle)

print("\n  Welle 100 -> 200 (Spanne 100)")
print("  Handrechnung gegen das Werkzeug:")
erwartet = {1.0: 200.0, 1.272: 227.2, 1.618: 261.8}
for x in z:
    soll = erwartet[x["verhaeltnis"]]
    print(f"    {x['verhaeltnis']:.3f}:  Werkzeug {x['preis']:>8.2f}"
          f"   Handrechnung {soll:>8.2f}")
    pruefe(f"Ziel {x['verhaeltnis']:.3f} = {soll:.2f}",
           abs(x["preis"] - soll) < 1e-9, f"ist {x['preis']}")

pruefe("drei Ziele", len(z) == 3, f"sind {len(z)}")
pruefe("aufsteigend sortiert",
       all(z[i]["preis"] < z[i + 1]["preis"] for i in range(len(z) - 1)))

# --- Erreicht / nicht erreicht ---
print()
u = erreichtes_ziel(kaufwelle, 150.0)
print(f"  Kurs 150 (unter allen Zielen) -> {u}")
pruefe("Kurs unter dem ersten Ziel loest NICHT aus", u is None)

u = erreichtes_ziel(kaufwelle, 200.0)
print(f"  Kurs 200 (genau Ziel 1)      -> "
      f"{u['verhaeltnis'] if u else None}")
pruefe("Kurs genau am Ziel loest aus", u is not None and u["verhaeltnis"] == 1.0)

u = erreichtes_ziel(kaufwelle, 199.95)
pruefe("knapp darunter loest auch aus (Toleranz)",
       u is not None and u["verhaeltnis"] == 1.0,
       "sonst wird ein Ziel um zwei Cent verfehlt")

# Sprung ueber mehrere Ziele: das HOECHSTE gewinnt
u = erreichtes_ziel(kaufwelle, 270.0)
print(f"  Kurs 270 (ueber allen Zielen) -> "
      f"{u['verhaeltnis'] if u else None}")
pruefe("bei einem Sprung gewinnt das HOECHSTE Ziel",
       u is not None and u["verhaeltnis"] == 1.618,
       "sonst wartet der Rest auf einen Ruecklauf, der nie kommt")

# Schon bedientes Ziel wird uebersprungen
u = erreichtes_ziel(kaufwelle, 200.0, schon_verkauft=[1.0])
pruefe("bereits bedientes Ziel loest NICHT erneut aus", u is None,
       "der Bot prueft alle 12 s - sonst verkauft er dauernd")

# --- Unbrauchbare Wellen ---
pruefe("Welle ohne Werte gibt keine Ziele", ziele_berechnen(None) == [])
pruefe("Hoch unter Tief gibt keine Ziele",
       ziele_berechnen({"hoch": 100.0, "tief": 200.0}) == [])
pruefe("Hoch gleich Tief gibt keine Ziele",
       ziele_berechnen({"hoch": 100.0, "tief": 100.0}) == [])
pruefe("Preis 0 loest nichts aus", erreichtes_ziel(kaufwelle, 0) is None)

# --- Deckt Ziel 1 die Handelskosten? ---
# Gekauft wird im Golden Pocket (0,618 bis 0,65 Ruecksetzer), also bei
# 200 - 100*0,618 = 138,20 bis 200 - 100*0,65 = 135,00.
# Von 138,20 auf 200 sind das +44,7 % - weit ueber den 0,505 % Kosten.
kaufpreis = 200.0 - 100.0 * 0.618
weg = (200.0 - kaufpreis) / kaufpreis * 100.0
print(f"\n  Kauf im Golden Pocket bei {kaufpreis:.2f}, Ziel 1 bei 200,00")
print(f"  Weg zum Ziel: {weg:+.2f} %   nach 0,505 % Kosten: {weg - 0.505:+.2f} %")
pruefe("Ziel 1 deckt die Handelskosten", weg > 0.505)

print(f"\n  Zur Anzeige: {beschreibung(kaufwelle, kaufpreis)}")
print(f"  Verkauft wird ab Ziel {ZIEL_VERKAUF} (von {ZIELE})")


# ====================================================================
print()
print("=" * 72)
print(f"  ERGEBNIS: {len(BESTANDEN)} bestanden, {len(DURCHGEFALLEN)} durchgefallen")
print("=" * 72)
if DURCHGEFALLEN:
    print("\n  DURCHGEFALLEN:")
    for n in DURCHGEFALLEN:
        print(f"    - {n}")
    print()
    sys.exit(1)
print("\n  Alles in Ordnung.\n")
sys.exit(0)
