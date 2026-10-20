# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsdatenbank - Migration der .md-Ablage, 30.07.2026.
"""
A4 - Migration ohne Datenverlust: Trials T-001..T-030, Datenquellen,
Kostenszenarien, Befunde, Registerversionen, Programmstatus.

A5-VORRANG: Jede Zeile fuehrt die .md-Quelldatei in quelle_md. Bei
Widerspruch gilt die .md, nicht die Datenbank.

Zahlen sind woertlich aus den Rohausgaben in ausgaben/ uebernommen.
Wo eine Groesse fuer einen Trial nicht existiert (z. B. EV bei
Event-Studies vor Kostenabzug), steht NULL - nicht 0.
Datenquellen werden LIVE aus daten/ nachgemessen, nicht abgeschrieben.
"""
import csv
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from db_schema import verbinde

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JETZT = datetime.now(timezone.utc).isoformat()[:19] + "Z"
Q_BEF = "docs/messungen_2026-07/BEFUNDE.md"
Q_G1V = "docs/forschungsprogramm_2026-07/09_GATE-1-VERDICT.md"
Q_H1 = "docs/forschungsprogramm_2026-07/ausgaben/batterie_h1_out.txt"
Q_H2 = "docs/forschungsprogramm_2026-07/ausgaben/batterie_h2_out.txt"
Q_H4 = "docs/forschungsprogramm_2026-07/ausgaben/batterie_h4_out.txt"
Q_NEU = "docs/forschungsprogramm_2026-07/08_NEUBEWERTUNG-v1.2.md"

# ---------------------------------------------------------------- T-001..015
HIST = [
    ("T-001", "E1 Nachkaufrate", "Harness-Nachkaufrate 2,2 % vs 18,3 % live erklaert", "INCONCLUSIVE"),
    ("T-002", "E1 Live-Fenster", "Befund haelt auch im Live-Zeitfenster", "INCONCLUSIVE"),
    ("T-003", "E2 Stop-Variation", "Kein Stop rettet das System; erzieltes R/R nie am Break-even", "REJECTED"),
    ("T-004", "E2 Einstiegsqualitaet", "Einstieg selektiert Volatilitaet, keine Richtung", "REJECTED"),
    ("T-005", "E2 Placebo I", "Echt nicht von gleichverteiltem Zufall unterscheidbar", "REJECTED"),
    ("T-006", "E2 Placebo II", "Volatilitaetsselektion bestaetigt", "REJECTED"),
    ("T-007", "E2 Phasenplacebo", "Phasengleich bestaetigt; P(auf) 47,66 % J2 / 50,69 % J1", "REJECTED"),
    ("T-008", "E5 Universum", "Kein Coin mit EV>0; N_eff 1,23-1,42", "REJECTED"),
    ("T-009", "E5 Ableitungen", "Verlust wird umverteilt, nicht beseitigt", "INCONCLUSIVE"),
    ("T-010", "F1 Reibung", "Kostenuntergrenze 0,150 %, noetig waren 0,128 %", "REJECTED"),
    ("T-011", "F1e Maker", "Fill 79-99 %, Adverse Selection 0,019-0,041 % je Trade", "INCONCLUSIVE"),
    ("T-012", "F2 Feature-IC", "25 Features, staerkster stabiler |IC| 0,036 vs noetig 0,179", "REJECTED"),
    ("T-013", "F3 Benchmark", "BTC-Halten schlaegt den Bot um 223 $ (J2) / 684 $ (J1)", "REJECTED"),
    ("T-014", "G1 Indikator-Verifikation", "17 von 21 Nachbauten exakt; F2 BESTAETIGT", "INCONCLUSIVE"),
    ("T-015", "G2 Lange Horizonte", "J2 faellt monoton auf 35,72 %; J1 = Beta", "REJECTED"),
]

# trial_id, hyp, regel, quelle, param, asset, segment, kMak, kBas, kKons,
# ki_u, ki_o, plc, p, status, begruendung
R1 = [
 ("T-016","H1","R1 Faber 10M-SMA","Faber 2007, J. of Wealth Management (US-Aktien/Renten/Rohstoffe)",
  {"sma_monate":10},"BTCUSDT","GESAMT",137.545,137.205,137.055,13.316,336.942,84.0,0.0060,
  "INCONCLUSIVE","n=4 Runden < 12; Placebo nicht geschlagen"),
 ("T-017","H1","R1 Faber 10M-SMA","Faber 2007",{"sma_monate":10},"ETHUSDT","GESAMT",
  139.769,139.429,139.279,-23.514,447.401,91.0,0.3355,"INCONCLUSIVE","n=8 < 12"),
 ("T-018","H1","R2 MOP 12M-Momentum","Moskowitz/Ooi/Pedersen 2012, JFE (58 Futures-Maerkte)",
  {"momentum_monate":12},"BTCUSDT","GESAMT",78.917,78.577,78.427,-1.768,211.668,68.0,0.0470,
  "INCONCLUSIVE","n=4 < 12"),
 ("T-019","H1","R2 MOP 12M-Momentum","Moskowitz/Ooi/Pedersen 2012",{"momentum_monate":12},
  "ETHUSDT","GESAMT",135.191,134.851,134.701,-16.813,412.556,84.0,0.2180,"INCONCLUSIVE","n=5 < 12"),
 ("T-020","H1","R3 Donchian 20/10","Donchian 4-Wochen-Regel 1960er; Lukac/Brorsen/Irwin 1988 (Futures)",
  {"einstieg_tage":20,"ausstieg_tage":10},"BTCUSDT","GESAMT",21.125,20.785,20.635,1.510,52.695,99.0,0.0135,
  "REJECTED","v1.2 Klausel A: Segment S-C +0,504 % < K-BASIS 0,60 %"),
 ("T-021","H1","R3 Donchian 20/10","Donchian 1960er; Lukac et al. 1988",
  {"einstieg_tage":20,"ausstieg_tage":10},"ETHUSDT","GESAMT",19.549,19.209,19.059,1.786,44.298,98.0,0.0115,
  "REJECTED","v1.2 Klausel A: Segment S-C +0,157 % < K-BASIS 0,60 %"),
 ("T-022","H1","R1 Faber 10M-SMA","Faber 2007",{"sma_monate":10},"12er-Portfolio","GESAMT",
  302.418,302.078,301.928,39.896,715.882,96.0,0.0000,"REJECTED",
  "Segment S-A -13,683 % negativ; zudem sekundaerer Trial (v1.2 Klausel B)"),
 ("T-023","H1","R2 MOP 12M-Momentum","Moskowitz et al. 2012",{"momentum_monate":12},
  "12er-Portfolio","GESAMT",183.147,182.807,182.657,35.889,410.637,73.0,0.0000,"REJECTED",
  "Segment S-A -9,492 %; Placebo nicht geschlagen; sekundaer"),
 ("T-024","H1","R3 Donchian 20/10","Donchian 1960er; Lukac et al. 1988",
  {"einstieg_tage":20,"ausstieg_tage":10},"12er-Portfolio","GESAMT",27.010,26.670,26.520,15.976,38.401,99.0,0.0000,
  "REJECTED","v1.2 Klausel B: sekundaerer Trial traegt Gate 1 nicht allein. "
  "Survivorship: S-C Alts +9,780 % (n=88) vs BTC+ETH +0,331 % (n=22), Faktor 30"),
]
# trial_id -> [(segment, ev_kbasis, n, ki_u, ki_o)]
R1_SEG = {
 "T-016":[("S-A",41.089,1,None,None),("S-B",213.052,2,-9.455,435.559),("S-C",81.627,1,None,None)],
 "T-017":[("S-A",-19.483,3,-36.576,0.119),("S-B",581.888,2,-39.520,1203.297),("S-C",3.368,3,-17.508,25.686)],
 "T-018":[("S-A",-1.768,2,-9.752,6.216),("S-B",280.152,1,None,None),("S-C",37.692,1,None,None)],
 "T-019":[("S-A",-15.306,1,None,None),("S-B",223.885,3,-26.842,686.727),("S-C",17.907,1,None,None)],
 "T-020":[("S-A",18.989,9,-2.825,44.450),("S-B",50.691,8,-2.148,142.540),("S-C",0.504,11,-7.056,9.696)],
 "T-021":[("S-A",4.852,11,-10.247,29.195),("S-B",65.147,8,15.771,148.502),("S-C",0.157,11,-7.620,9.648)],
 "T-022":[("S-A",-13.683,7,-29.578,7.560),("S-B",727.429,20,86.113,1785.904),("S-C",28.309,23,1.824,62.943)],
 "T-023":[("S-A",-9.492,4,-17.217,0.835),("S-B",351.771,17,49.459,810.401),("S-C",42.594,15,20.574,67.803)],
 "T-024":[("S-A",3.678,43,-4.381,13.541),("S-B",58.821,95,34.602,85.635),("S-C",7.890,110,-0.455,18.660)],
}
H2 = [
 ("T-025","H2","E-neg Funding <=0 x3, Halten 7d","Positionierungs-Ueberhang (keine Literaturregel, Schwellen fix)",
  {"schwelle":0.0,"konsekutiv":3,"halten_tage":7},"BTCUSDT",30,3.294,2.954,0.101,5.652,88.0,0.0185,
  "REJECTED","Vol-gematchtes Placebo +5,57 % im 95. Perzentil nicht geschlagen - selektiert Volatilitaet"),
 ("T-026","H2","E-neg Funding <=0 x3","dito",{"schwelle":0.0,"konsekutiv":3,"halten_tage":7},
  "ETHUSDT",25,3.954,3.614,-1.412,8.880,85.0,0.0865,"INCONCLUSIVE","25 Events < 30"),
 ("T-027","H2","E-pos Funding >=0,05 % x3","dito",{"schwelle":0.0005,"konsekutiv":3,"halten_tage":7},
  "BTCUSDT",16,None,None,None,None,20.0,0.2000,"INCONCLUSIVE","16 Events < 30"),
 ("T-028","H2","E-pos Funding >=0,05 % x3","dito",{"schwelle":0.0005,"konsekutiv":3,"halten_tage":7},
  "ETHUSDT",18,None,None,None,None,92.5,0.9250,"INCONCLUSIVE",
  "18 Events < 30; Forward +5,93 % - Gegenteil der Hypothese"),
]

KOSTEN = [
 ("K-MAKER","Bybit EU",0.10,None,0.03,0.26,
  "v1.1 Par.2; Adverse Selection 0,03 % = Mittel des in F1e GEMESSENEN Bereichs 0,019-0,041 %",
  "2026-07-30","WAHRSCHEINLICH"),
 ("K-BASIS","Bybit EU",None,0.25,0.05,0.60,
  "Taker 0,25 % vom Eigentuemer an der offiziellen Gebuehrenseite geprueft (Stand 08.03.2026); "
  "Slippage 0,05 %/Seite ist Annahme bis zur Live-Capture","2026-07-30","SICHER"),
 ("K-KONSERVATIV","Bybit EU",None,0.25,0.125,0.75,
  "Konservative Slippage-Variante fuer duenne Alt-Buecher","2026-07-30","WAHRSCHEINLICH"),
 ("ALT-v1.0 (verworfen)","Bybit EU",0.10,0.10,0.05,0.30,
  "FALSCHE Annahme der Matrix v1: Taker 0,10 %. Durch Pruefung des Eigentuemers widerlegt.",
  "2026-07-30","SICHER"),
]

REGISTER = [
 ("v1.0","2026-07-30","886eda8bbe69d080994460b18da897865fcabbddf62e5429345063759d242e80",
  "Erstfassung: H1-H4, Kontaminationsregel 14, Placebo-Design, Trial-Budget 15","2026-07-30","offen",
  "docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.0.md"),
 ("v1.1","2026-07-30","6aeb588717a92d7a0fa15d59d04160b704026feb03a152db27cbcfd6377f184c",
  "Nur Par.2: Kostenszenarien K-MAKER/K-BASIS/K-KONSERVATIV nach Gebuehrenkorrektur; "
  "CONFIRMED nur unter K-BASIS","2026-07-30","offen",
  "docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.1.md"),
 ("v1.2","2026-07-30","2e744b4d4937dead5f6be5fc25192e31a7f4cd0887a77f5def13c50d13556ea1",
  "Klausel A: Netto-EV je Segment > K-BASIS (Lesart L2). Klausel B: sekundaere Trials "
  "tragen ein Gate nicht allein. Rueckwirkend.","2026-07-30","offen",
  "docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.2.md"),
]

BEFUNDE = [
 (1,"Krypto-Trendfolge ist 2022-2023 verschwunden",
  "Donchian 20/10 netto EV je Runde nach Segment: BTC +18,99 / +50,69 / +0,50 %, "
  "ETH +4,85 / +65,15 / +0,16 %. Zerfallsmuster einer arbitrierten Anomalie, und zwar "
  "bei der meistpublizierten Krypto-Strategiefamilie.","SICHER",2,10,"KRITISCH","T-020,T-021",None),
 (1,"Trendfolge ist in Krypto ein Risiko-, kein Ertragswerkzeug",
  "Gesamtzeitraum: BTC Calmar 1,08 vs Halten 0,52, MaxDD 55,1 vs 83,2 %. ABER im Bullenmarkt "
  "S-B verliert die Regel (+533 vs +542 %, ETH +1914 vs +2711 %). Der Vorsprung stammt komplett "
  "aus geringeren Verlusten in Abwaerts-/Seitwaertsphasen.","SICHER",3,8,"HOCH","T-020,T-021",None),
 (1,"Funding-Extreme selektieren Volatilitaet, nicht Richtung",
  "T-025: +2,95 % netto ueber 7 Tage mit KI>0, aber vol-gematchtes Placebo +5,57 %. Dieselbe "
  "Pathologie wie der F&G-Einstieg aus E2 - zwei unabhaengige Signalquellen, identische Fehlerart.",
  "SICHER",2,8,"HOCH","T-025",None),
 (1,"Survivorship betraegt Faktor 30",
  "Segment S-C: 10 survivorship-selektierte Alts +9,780 % je Runde (n=88) gegen BTC+ETH "
  "+0,331 % (n=22). Groesste Beitraege AVAX +52 %, NEAR +26 %, SOL +23 % - genau die Coins mit "
  "2023er-Erholung, die bis 2026 gelistet blieben.","SICHER",1,9,"KRITISCH","T-024",None),
 (1,"Makro-Overlays kaufen nichts",
  "Dollar-Overlay: MaxDD 46,9 -> 34,4 %, aber CAGR 85,0 -> 63,6 %. Calmar-Differenz +0,036, "
  "KI [-1,476; +0,802] enthaelt 0; EV -4,48 bp/Tag signifikant negativ.","SICHER",1,5,"MITTEL","T-030",None),
 (1,"Der Limit-Order-Pfad muss nicht gebaut werden",
  "K-MAKER gegen K-BASIS macht bei niederfrequenten Regeln 1,3-1,8 % des Effekts aus "
  "(0,34 pp bei 19-27 % EV je Runde). Gegenbeispiel T-025 (H2): dort waeren es 11,5 % gewesen.",
  "SICHER",1,7,"HOCH","T-020,T-021,T-024",None),
 (1,"USDT ist als EU-Handels-Quote tot",
  "Per API verifiziert (api.bybit.eu, 30.07.2026): 133 Spot-Paare im Status Trading - "
  "111 USDC, 18 EUR, 4 PLN, 0 USDT. Alle 12 Projekt-Coins als USDC-Paar vorhanden.",
  "SICHER",1,8,"HOCH",None,None),
 (1,"ccxt-Gebuehrenmetadaten sind unbrauchbar",
  "ccxt.bybit().fees meldet maker 0,01 % / taker 0,075 % - fuer EU-Spot beides falsch "
  "(Ist 0,10 / 0,25). Ein naiv gebauter Adapter haette die Kostenbasis um Faktor 3 zu "
  "guenstig angesetzt.","SICHER",6,6,"HOCH",None,None),
 (1,"43 % der Bot-Module werden von nichts importiert",
  "Architektur-Scan 30.07.2026: 231 Module, davon 100 TOT (kein Importeur, kein "
  "Einstiegspunkt), 117 AKTIV, 13 UNGEPRUEFT, 1 DEAKTIVIERT. Mechanisch ermittelt ueber "
  "AST-Importgraph ab app.py.","SICHER",4,6,"MITTEL",None,None),
]


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except OSError:
        return None


def fuelle_trials(con):
    ins = ("INSERT INTO trials (trial_id,runde,hypothese,regel_name,"
           "literatur_quelle,parameter,asset,datenzeitraum,segment,"
           "kostenszenario,ev_je_runde,ki_unten,ki_oben,placebo_perzentil,"
           "p_wert,status,begruendung,zeitstempel,pfad_rohausgabe,"
           "skript_sha256,quelle_md) VALUES "
           "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    for tid, hyp, begr, st in HIST:
        con.execute(ins, (tid, 0, hyp, None, None, None, None,
                          "2024-07..2026-07", "GESAMT", "ALT-0,30 %", None,
                          None, None, None, None, st, begr, JETZT, None,
                          None, Q_BEF))
    h1sha = sha(os.path.join(BASIS, "code", "batterie_h1.py"))
    for (tid, hyp, regel, quelle, par, asset, seg, km, kb, kk, kiu, kio,
         plc, p, st, begr) in R1:
        for szen, ev in (("K-MAKER", km), ("K-BASIS", kb),
                         ("K-KONSERVATIV", kk)):
            con.execute(ins, (tid, 1, hyp, regel, quelle, json.dumps(par),
                              asset, "2017-08-17..2023-12-31", seg, szen, ev,
                              kiu if szen == "K-BASIS" else None,
                              kio if szen == "K-BASIS" else None,
                              plc if szen == "K-BASIS" else None,
                              p if szen == "K-BASIS" else None,
                              st, begr, JETZT, Q_H1, h1sha, Q_G1V))
        for sg, ev, n, u, o in R1_SEG.get(tid, []):
            con.execute(ins, (tid, 1, hyp, regel, quelle,
                              json.dumps({"n_runden": n}), asset,
                              "2017-08-17..2023-12-31", sg, "K-BASIS", ev,
                              u, o, None, None, st,
                              f"Segmentwert, n={n} Runden", JETZT, Q_H1,
                              h1sha, Q_NEU))
    h2sha = sha(os.path.join(BASIS, "code", "batterie_h2.py"))
    for (tid, hyp, regel, quelle, par, asset, n, km, kb, kiu, kio, plc, p,
         st, begr) in H2:
        for szen, ev in (("K-MAKER", km), ("K-BASIS", kb)):
            con.execute(ins, (tid, 1, hyp, regel, quelle,
                              json.dumps(dict(par, n_events=n)), asset,
                              "2019-09..2023-12-31", "GESAMT", szen, ev,
                              kiu if szen == "K-BASIS" else None,
                              kio if szen == "K-BASIS" else None,
                              plc if szen == "K-BASIS" else None,
                              p if szen == "K-BASIS" else None,
                              st, begr, JETZT, Q_H2, h2sha, Q_G1V))
    con.execute(ins, ("T-029", 1, "H3", "Cross-Sectional Momentum 4W-Rang",
                      "Jegadeesh/Titman 1993 (US-Aktien)",
                      json.dumps({"rang_wochen": 4, "quintil": 1}), None,
                      None, "GESAMT", None, None, None, None, None, None,
                      "NICHT_AUSGEFUEHRT",
                      "Registerbedingung Universum >= 30 und N_eff >= 5 nicht "
                      "erfuellt (12 Coins, N_eff 1,23-1,42). Formal mit Gate 1 "
                      "abgeschlossen, verwiesen in eine etwaige Runde 2.",
                      JETZT, None, None, Q_G1V))
    con.execute(ins, ("T-030", 1, "H4", "Dollar-Overlay 13W, Lag 7d, Groesse x0,5",
                      "FRED DTWEXBGS (Makro-Reihe, keine Handelsregel)",
                      json.dumps({"wochen": 13, "lag_tage": 7, "faktor": 0.5}),
                      "12er-Portfolio", "2017-08-17..2023-12-31", "GESAMT",
                      "K-BASIS", None, -1.476, 0.802, None, None, "REJECTED",
                      "Calmar-Differenz +0,036, KI enthaelt 0; EV-Differenz "
                      "-4,48 bp/Tag signifikant negativ. Werte in ki_unten/"
                      "ki_oben sind die Calmar-Differenz, nicht EV.",
                      JETZT, Q_H4, sha(os.path.join(BASIS, "code",
                                                    "batterie_h4.py")), Q_G1V))


def fuelle_quellen(con):
    """LIVE aus daten/ nachgemessen, nicht abgeschrieben."""
    n = 0
    for typ, muster, iv in (("klines", "daten/klines_1d/*.csv", "1d"),
                            ("klines", "daten/klines_4h/*.csv", "4h"),
                            ("funding", "daten/funding/*.csv", "8h"),
                            ("makro", "daten/makro/*.csv", "1d")):
        for p in sorted(glob.glob(os.path.join(BASIS, muster))):
            name = os.path.basename(p)
            coin = name.split("_")[0] if typ != "makro" else None
            zeit_sp = {"klines": "zeit", "funding": "fundingTime"}.get(typ)
            erst = letzt = None
            zeilen = 0
            luecken = []
            if zeit_sp:
                ts = []
                for r in csv.DictReader(open(p, encoding="utf-8")):
                    try:
                        ts.append(int(r[zeit_sp]))
                    except (KeyError, ValueError):
                        continue
                zeilen = len(ts)
                if ts:
                    erst = datetime.fromtimestamp(
                        ts[0] / 1000, timezone.utc).strftime("%Y-%m-%d")
                    letzt = datetime.fromtimestamp(
                        ts[-1] / 1000, timezone.utc).strftime("%Y-%m-%d")
                    soll = 86400000 if iv == "1d" else (
                        14400000 if iv == "4h" else 28800000)
                    for i in range(1, len(ts)):
                        d = ts[i] - ts[i - 1]
                        if abs(d - soll) > 60000:
                            luecken.append({
                                "nach": datetime.fromtimestamp(
                                    ts[i - 1] / 1000,
                                    timezone.utc).strftime("%Y-%m-%d"),
                                "intervalle": round(d / soll, 2)})
            else:
                zeilen = sum(1 for _ in open(p, encoding="utf-8-sig")) - 1
            con.execute(
                "INSERT INTO datenquellen (name,url,typ,coin,intervall,"
                "erster_datenpunkt,letzter_datenpunkt,anzahl_zeilen,luecken,"
                "sha256,abrufdatum,lizenzstatus,quelle_md) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (name,
                 {"klines": "https://data-api.binance.vision/api/v3/klines",
                  "funding": "https://fapi.binance.com/fapi/v1/fundingRate",
                  "makro": "https://fred.stlouisfed.org/graph/fredgraph.csv"}[typ],
                 typ, coin, iv, erst, letzt, zeilen,
                 json.dumps(luecken[:20]), sha(p), "2026-07-30",
                 "oeffentlich, keyfrei, kostenlos",
                 "docs/forschungsprogramm_2026-07/03_DATEN-COVERAGE.md"))
            n += 1
    return n


def main():
    con = verbinde()
    for t in ("trials", "datenquellen", "kostenszenarien", "befunde",
              "register_versionen", "programm_status"):
        con.execute(f"DELETE FROM {t}")
    fuelle_trials(con)
    nq = fuelle_quellen(con)
    for name, boerse, mk, tk, sl, rt, q, v, kf in KOSTEN:
        con.execute("INSERT INTO kostenszenarien (name,boerse,maker_pct,"
                    "taker_pct,slippage_pct,roundtrip_pct,quelle,"
                    "verifiziert_am,konfidenz,quelle_md) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (name, boerse, mk, tk, sl, rt, q, v, kf,
                     "docs/forschungsprogramm_2026-07/"
                     "02_EXPERIMENT-REGISTER_v1.1.md"))
    for r, kurz, lang, kf, ri, im, pr, tb, wid in BEFUNDE:
        con.execute("INSERT INTO befunde (runde,kurztext,langtext,konfidenz,"
                    "risiko_0_10,impact_0_10,prioritaet,trial_bezug,"
                    "widerlegt_befund_id,zeitstempel,quelle_md) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (r, kurz, lang, kf, ri, im, pr, tb, wid, JETZT, Q_G1V))
    for v, d, s, a, ab, bis, qm in REGISTER:
        con.execute("INSERT INTO register_versionen (version,datum,sha256,"
                    "aenderung,gueltig_ab,gueltig_bis,quelle_md) "
                    "VALUES (?,?,?,?,?,?,?)", (v, d, s, a, ab, bis, qm))
    con.execute("INSERT INTO programm_status (gate_nummer,ergebnis,datum,"
                "begruendung,verdict_pfad) VALUES (?,?,?,?,?)",
                (1, "NEGATIV", "2026-07-30",
                 "0 CONFIRMED, 7 REJECTED, 7 INCONCLUSIVE, 1 nicht "
                 "ausgefuehrt. Erstes von zwei negativen Gates nach Regel 13.",
                 Q_G1V))
    con.commit()
    for t in ("trials", "datenquellen", "kostenszenarien", "befunde",
              "register_versionen", "programm_status", "bot_architektur"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<20s} {n:5d} Zeilen")
    print(f"  (davon Datenquellen live nachgemessen: {nq})")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
