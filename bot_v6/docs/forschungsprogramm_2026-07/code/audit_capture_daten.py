# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Audit der Capture-Daten nach dem Wochenende, 03.08.2026.
"""
Datenqualitaets-Audit des Live-Capture, Stand 03.08.2026.

ANLASS: Der Capture ist nicht mehr gelaufen. Im Log stehen 121
CAPTURE-START-Eintraege und 229 Singleton-Abbrueche, dazu lange Phasen
mit ok=0/fehler=36 und mehrere gleichzeitig laufende Instanzen mit
unterschiedlichen Zyklusnummern. Bevor irgendetwas ausgewertet wird,
muss geklaert sein, ob die Daten ueberhaupt brauchbar sind.

GEPRUEFT WIRD:
  1. Duplikate je Reihe (mehrere Instanzen schreiben in dieselbe Datei)
  2. Tatsaechliche zeitliche Abdeckung und Luecken je Tag
  3. Messpunktdichte gegen den Sollwert (Poll 120 s -> 720/Tag)
  4. Plausibilitaet der Spreads (Ausreisser, Nullwerte)

NUR LESEND. Keine Datei wird veraendert oder geloescht.
"""
import csv
import glob
import gzip
import io
import os
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(BASIS, "capture")
SOLL_POLL = 120


SCHADEN = {}     # pfad -> (gerettete_bytes, gesamt_bytes, mitglieder, fehler)


def _rette(roh):
    """Liest so viele gzip-Mitglieder wie moeglich. Bei Korruption wird das
    naechste 1f8b-Magic gesucht und dort fortgesetzt. Gibt (text, stats).

    Notwendig, weil mehrere Instanzen gleichzeitig in dieselbe Datei
    angehaengt haben - die gzip-Stroeme sind ineinander verschraenkt."""
    import zlib
    out, pos, mitglieder, fehler = [], 0, 0, 0
    n = len(roh)
    while pos < n - 1:
        if roh[pos:pos + 2] != b"\x1f\x8b":
            nx = roh.find(b"\x1f\x8b", pos + 1)
            if nx < 0:
                break
            pos = nx
            continue
        d = zlib.decompressobj(31)
        try:
            stueck = d.decompress(roh[pos:])
            out.append(stueck)
            mitglieder += 1
            verbraucht = n - pos - len(d.unused_data)
            pos += max(verbraucht, 1)
        except zlib.error:
            fehler += 1
            teil = getattr(d, "unconsumed_tail", b"")
            try:
                out.append(d.flush())
            except zlib.error:
                pass
            nx = roh.find(b"\x1f\x8b", pos + 1)
            if nx < 0:
                break
            pos = nx
    return b"".join(out), (mitglieder, fehler)


def lade(pfad):
    roh = open(pfad, "rb").read()
    try:
        txt = gzip.decompress(roh).decode("utf-8", "replace")
        SCHADEN[pfad] = (len(roh), len(roh), 1, 0)
    except (OSError, EOFError, Exception):
        daten, (m, f) = _rette(roh)
        txt = daten.decode("utf-8", "replace")
        SCHADEN[pfad] = (len(daten), len(roh), m, f)
    # Kopfzeilen aus angehaengten Mitgliedern entfernen
    zeilen = txt.splitlines()
    if not zeilen:
        return []
    kopf = zeilen[0]
    rein = [z for z in zeilen[1:] if z and z != kopf]
    return list(csv.DictReader(io.StringIO("\n".join([kopf] + rein))))


def iso(ms):
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")


def main():
    tage = sorted(d for d in glob.glob(os.path.join(CAP, "2026-*"))
                  if os.path.isdir(d))
    print("=" * 100)
    print(" AUDIT CAPTURE-DATEN  -  Stand 03.08.2026")
    print(" Nur lesend. Frage: sind die Daten trotz Mehrfachinstanzen brauchbar?")
    print("=" * 100)

    # ---------- 1. Heartbeat: Instanzen und Abdeckung ----------
    print("\n" + "=" * 100)
    print(" 1. HEARTBEAT - Abdeckung und Mehrfachinstanzen")
    print("=" * 100)
    print(f"\n  {'Tag':<12s} {'Zeilen':>7s} {'eindeut.ts':>11s} {'Dupl.':>7s} "
          f"{'ok>0':>7s} {'ok=0':>7s} {'von':<20s} {'bis':<20s}")
    print("  " + "-" * 96)
    for d in tage:
        p = os.path.join(d, "heartbeat.csv.gz")
        if not os.path.exists(p):
            continue
        r = lade(p)
        ts = [x["ts"] for x in r if x.get("ts") and str(x["ts"]).isdigit()]
        ok0 = sum(1 for x in r if x.get("ok") == "0")
        okp = sum(1 for x in r
                  if x.get("ok") and str(x["ok"]).isdigit() and int(x["ok"]) > 0)
        if not ts:
            print(f"  {os.path.basename(d):<12s} {len(r):7d} "
                  f"{'KEINE gueltigen Zeitstempel - Datei zerstoert':>60s}")
            continue
        print(f"  {os.path.basename(d):<12s} {len(r):7d} {len(set(ts)):11d} "
              f"{len(ts)-len(set(ts)):7d} {okp:7d} {ok0:7d} "
              f"{iso(min(ts)):<20s} {iso(max(ts)):<20s}")

    # ---------- 2. Ticker: Duplikate und Luecken ----------
    print("\n" + "=" * 100)
    print(" 2. TICKER BTCUSDC - Duplikate, Luecken, Dichte")
    print("=" * 100)
    print(f"\n  {'Tag':<12s} {'Zeilen':>7s} {'eindeut.':>9s} {'Dupl.%':>7s} "
          f"{'Soll':>6s} {'Abdeck.%':>9s} {'Luecken>10min':>14s} {'max Luecke':>12s}")
    print("  " + "-" * 92)
    ges_zeilen = ges_eind = 0
    for d in tage:
        p = os.path.join(d, "ticker_BTCUSDC.csv.gz")
        if not os.path.exists(p):
            continue
        r = lade(p)
        ts = sorted(int(x["ts"]) for x in r
                    if x.get("ts") and str(x["ts"]).isdigit())
        if not ts:
            print(f"  {os.path.basename(d):<12s} {'-':>7s} "
                  f"{'keine gueltigen Zeilen':>40s}")
            continue
        eind = sorted(set(ts))
        ges_zeilen += len(ts)
        ges_eind += len(eind)
        # Sollwert: Tageslaenge in Sekunden / Poll
        spanne = (eind[-1] - eind[0]) / 1000 if len(eind) > 1 else 0
        soll = int(spanne / SOLL_POLL) + 1 if spanne else 1
        luecken = [(eind[i] - eind[i-1]) / 1000 for i in range(1, len(eind))]
        gross = [x for x in luecken if x > 600]
        print(f"  {os.path.basename(d):<12s} {len(ts):7d} {len(eind):9d} "
              f"{(len(ts)-len(eind))/len(ts)*100:6.1f}% {soll:6d} "
              f"{len(eind)/soll*100:8.1f}% {len(gross):14d} "
              f"{max(luecken)/60 if luecken else 0:11.1f}m")
    print(f"\n  GESAMT: {ges_zeilen} Zeilen, {ges_eind} eindeutige Zeitstempel, "
          f"{(ges_zeilen-ges_eind)/ges_zeilen*100:.1f} % Duplikate")

    # ---------- 3. Duplikat-Natur: identisch oder abweichend? ----------
    print("\n" + "=" * 100)
    print(" 3. NATUR DER DUPLIKATE - identische Zeile oder Widerspruch?")
    print("=" * 100)
    for d in tage[-2:]:
        p = os.path.join(d, "ticker_BTCUSDC.csv.gz")
        if not os.path.exists(p):
            continue
        r = lade(p)
        nach_ts = {}
        for x in r:
            nach_ts.setdefault(x.get("ts"), []).append(x.get("mid"))
        mehr = {t: v for t, v in nach_ts.items() if len(v) > 1}
        gleich = sum(1 for v in mehr.values() if len(set(v)) == 1)
        print(f"\n  {os.path.basename(d)}: {len(mehr)} Zeitstempel mehrfach, "
              f"davon {gleich} mit identischem mid, "
              f"{len(mehr)-gleich} mit abweichendem mid")

    # ---------- 4. Spread-Plausibilitaet ueber alle Tage ----------
    print("\n" + "=" * 100)
    print(" 4. SPREADS ueber die gesamte Erfassung (dedupliziert)")
    print("=" * 100)
    coins = sorted({os.path.basename(p)[len("ticker_"):-len(".csv.gz")]
                    for d in tage
                    for p in glob.glob(os.path.join(d, "ticker_*.csv.gz"))})
    print(f"\n    {'Coin':<10s} {'n':>7s} {'min':>8s} {'p25':>8s} "
          f"{'median':>8s} {'p75':>8s} {'p90':>8s} {'max':>9s} {'Nullen':>7s}")
    print("    " + "-" * 80)
    ergebnis = {}
    for c in coins:
        werte = {}
        for d in tage:
            p = os.path.join(d, f"ticker_{c}.csv.gz")
            if not os.path.exists(p):
                continue
            for x in lade(p):
                if x.get("ts") and x.get("spread_bp"):
                    try:
                        werte[int(x["ts"])] = float(x["spread_bp"])
                    except ValueError:
                        continue
        sp = list(werte.values())
        if len(sp) < 50:
            continue
        nullen = sum(1 for v in sp if v <= 0)
        q = st.quantiles(sp, n=100)
        ergebnis[c] = {"n": len(sp), "median": st.median(sp),
                       "p25": q[24], "p75": q[74], "p90": q[89],
                       "min": min(sp), "max": max(sp), "nullen": nullen}
        print(f"    {c:<10s} {len(sp):7d} {min(sp):8.3f} {q[24]:8.3f} "
              f"{st.median(sp):8.3f} {q[74]:8.3f} {q[89]:8.3f} "
              f"{max(sp):9.3f} {nullen:7d}")

    # ---------- 5. Vergleich zur Eintagesmessung ----------
    print("\n" + "=" * 100)
    print(" 5. VERGLEICH zur Eintagesmessung vom 31.07. (Kostenmatrix v3)")
    print("=" * 100)
    alt = {"ETHUSDC": 0.054, "BTCUSDC": 0.118, "SOLUSDC": 1.366,
           "DOGEUSDC": 1.441, "ADAUSDC": 5.954, "XRPUSDC": 6.591,
           "LINKUSDC": 12.105, "AVAXUSDC": 12.372, "UNIUSDC": 16.519,
           "NEARUSDC": 18.276, "ATOMUSDC": 56.887, "DOTUSDC": 65.232}
    print(f"\n    {'Coin':<10s} {'Median 31.07.':>14s} {'Median gesamt':>14s} "
          f"{'Faktor':>8s}")
    print("    " + "-" * 50)
    for c in sorted(ergebnis, key=lambda x: alt.get(x, 0)):
        if c in alt:
            neu = ergebnis[c]["median"]
            print(f"    {c:<10s} {alt[c]:13.3f}  {neu:13.3f}  "
                  f"{neu/alt[c]:7.2f}x")
    print("\n  Faktor deutlich ueber 1 heisst: die Eintagesmessung war zu")
    print("  guenstig. Faktor unter 1: sie war zu pessimistisch.")

    # ---------- 6. Schadensbilanz ----------
    print("\n" + "=" * 100)
    print(" 6. SCHADENSBILANZ DER GZIP-DATEIEN")
    print("=" * 100)
    intakt = [p for p, v in SCHADEN.items() if v[3] == 0]
    kaputt = [p for p, v in SCHADEN.items() if v[3] > 0]
    print(f"\n  geprueft: {len(SCHADEN)} Dateien")
    print(f"  intakt  : {len(intakt)}")
    print(f"  beschaedigt, teilweise gerettet: {len(kaputt)}")
    if kaputt:
        ges_roh = sum(SCHADEN[p][1] for p in kaputt)
        ges_ret = sum(SCHADEN[p][0] for p in kaputt)
        print(f"  In den beschaedigten Dateien: {ges_ret/1024/1024:.1f} MB "
              f"entpackt aus {ges_roh/1024/1024:.1f} MB Rohdaten")
        print(f"\n  {'Datei':<46s} {'Mitglieder':>11s} {'Fehler':>7s}")
        print("  " + "-" * 68)
        for p in sorted(kaputt)[:15]:
            v = SCHADEN[p]
            kurz = os.path.join(os.path.basename(os.path.dirname(p)),
                                os.path.basename(p))
            print(f"  {kurz:<46s} {v[2]:11d} {v[3]:7d}")
        if len(kaputt) > 15:
            print(f"  ... und {len(kaputt)-15} weitere")
    print("\n  URSACHE: mehrere Instanzen haben gleichzeitig per gzip-Append")
    print("  in dieselben Dateien geschrieben. Die gzip-Mitglieder sind")
    print("  ineinander verschraenkt. Kein Schreibschutz, keine Dateisperre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
