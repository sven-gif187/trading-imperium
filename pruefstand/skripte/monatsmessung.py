# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Monatsmessung v6 · Entscheidung Sven E6 (15.10.2026, entscheidungen.md): Ausstiegs- und Halte-Ideen und der
Einstieg werden monatlich OFFLINE aus den vorhandenen Daten nachgerechnet, ohne Eingriff in den Bot.

Varianten (vorab festgelegt aus A4/A5 nach dem A10-Urteil, berichte/2026-10-14_advocatus.md):
  Ist   heutige Regel nachgespielt: Verlustbremse 2,12 % (2,5 x 0,85), Abstand 0,85 %, Nachzieh-Start aus dem
        wirksamen Abstand (E11: ((1+K)/(1-Abstand)-1)+0,05), Nullsicherung ab +1,0 % mit Puffer aus
        risk/exit_rules.py (heute 0,195, nach E5 0,25), RSI-Verkaufssignal, Rueckkaufsperre 6 h wie heute.
  X1    wie Ist, Abstand = max(0,85; 2 x ATR(14, 1 h) beim Kauf), Start daraus (A5-X1, A10: einzeln messen)
  H12   12 h halten, nur Notstopp 2,12 %, kein Nachziehen, keine Nullsicherung, kein Signal (A4-V1 in A10-Form)
  oSig  Ist ohne RSI-Verkaufssignal (A5-V4)
Alle mit Kapitalbindung: eine Position je Muenze, hoechstens 3. Fruehere Ausstiege erzeugen keine Ersatzkaeufe.

Gepaart gegen Ist, ZERLEGT (A10-Befund 3, kein Nachspiel-Abschlag im Paarvergleich):
  Kurseffekt $     = Summe nominal x Kurs-% (Variante) - dasselbe fuer Ist
  Kostenersparnis $ = K x (nominal Ist - nominal Variante), K = 0,150 % je Runde
Bereiche: Block-Bootstrap nach Kauf-Kalendertag, 95 %, dazu Bonferroni ueber Varianten x Lagen.
Je W1-Lage (BTC am Vortag des Kaufs, mit Halteband) und gesamt. Eichung: Ist-Nachspielung gegen die echte
Kursbewegung derselben Runden (A5: Motor im Mittel -0,11 unter echt).
Einstieg (A4-V5): Kurs 1/4/12/24 h nach jedem echten Kauf (ab letztem Minutenschluss davor) minus Mittel eines 7-Minuten-Rasters
derselben Muenze im Fenster (Zufall), Block-Bootstrap nach Kauftag.

Fenster: Vormonat (Verkauf im Monat) und kumuliert seit 13.08.2026 13:21:19 UTC (Start E7).
Urteil erst ab rund 570-780 Runden je Vergleich (A5/A10) - vorher "nicht entscheidbar".
Ausgabe: berichte/monatsmessung_<JJJJ-MM>.md, daten/monatsmessung_<JJJJ-MM>.json
Aufrufe: pythonw monatsmessung.py  (Vormonat) | python monatsmessung.py --monat 2026-10 [--ohne_laden]
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
P = HIER.parent
sys.path.insert(0, str(HIER))
import a5_basis as ab  # noqa: E402
from a5_motor import Regel, RSIStunde, spiele  # noqa: E402

V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
START_KUM = "2026-08-13T13:21:19"
K = 0.150
SL, ABSTAND, BE_AB = 2.12, 0.85, 1.0
STUNDEN = (1, 4, 12, 24)
ENTSCHEIDBAR_AB = 570


def puffer_aus_bot() -> float:
    t = (V6 / "risk" / "exit_rules.py").read_text(encoding="utf-8")
    k = float(re.search(r"^K_BASIS_PCT\s*=\s*([0-9.]+)", t, re.M).group(1))
    m = float(re.search(r"^BREAKEVEN_MARGE_PCT\s*=\s*([0-9.]+)", t, re.M).group(1))
    return round(k + m, 3)


def start_aus_abstand(abstand: float) -> float:
    return ((1 + K / 100) / (1 - abstand / 100) - 1) * 100 + 0.05


def spiele_alle(R, regel_fn, k1m, rsis, sperre_h=6, abschlag_pct=1.0, ende_h=None):
    """Wie a5_explorativ.spiele_alle_band, aber Regel je Runde (Start aus dem Abstand) und optional fester Ausstieg."""
    aus, belegt, letzter = [], {}, {}
    for r in sorted(R, key=lambda x: x["kauf_ms"]):
        offen = [c for c, bis in belegt.items() if bis > r["kauf_ms"]]
        if r["coin"] in offen or len(offen) >= 3:
            continue
        if sperre_h is not None and r["coin"] in letzter:
            t_aus, p_aus = letzter[r["coin"]]
            if r["kauf_ms"] - t_aus < sperre_h * 3_600_000 and r["einstieg_preis"] > p_aus * (1 - abschlag_pct / 100):
                continue
        ende = None if ende_h is None else r["kauf_ms"] + ende_h * 3_600_000
        z = spiele(r, regel_fn(r), k1m, rsis.get(r["coin"]), ende_ms=ende)
        if ende is not None and z["art"] == "OFFEN_ENDE" and z["aus_ms"] >= ende:
            z["art"], z["offen"] = "ZEIT_12H", False
        z["kurs_pct"] = (z["preis"] / r["einstieg_preis"] - 1) * 100
        z["runde"] = r
        belegt[r["coin"]] = z["aus_ms"]
        letzter[r["coin"]] = (z["aus_ms"], z["preis"])
        aus.append(z)
    return aus


def lage_je_tag() -> dict[str, str]:
    con = sqlite3.connect(P / "waechter.db", timeout=30)
    try:
        return {d: l for d, l in con.execute("SELECT datum, label FROM marktlage WHERE coin = 'BTC'")}
    finally:
        con.close()


def lage_vor(lagen: dict, kauf_t: str) -> str:
    d = (date.fromisoformat(kauf_t[:10]) - timedelta(days=1)).isoformat()   # Lage vom Vortag: kein Blick nach vorn
    return lagen.get(d, "UNBEKANNT")


def kennzahl(z: list[dict]) -> dict:
    if not z:
        return {"n": 0}
    nom = [x["runde"]["kauf_nominal"] for x in z]
    kp = [x["kurs_pct"] for x in z]
    tage = [x["runde"]["kauf_t"][:10] for x in z]
    brutto = sum(n * k / 100 for n, k in zip(nom, kp))
    netto = brutto - sum(nom) * K / 100
    m, lo, hi = ab.block_bootstrap(tage, [k - K for k in kp], B=4000)
    arten: dict[str, int] = {}
    for x in z:
        arten[x["art"]] = arten.get(x["art"], 0) + 1
    return {"n": len(z), "brutto_usd": round(brutto, 2), "netto_usd_K150": round(netto, 2),
            "netto_je_runde_pct": round(m, 3), "bereich95": [round(lo, 3), round(hi, 3)],
            "offen_am_ende": sum(1 for x in z if x.get("offen")), "arten": arten}


def gepaart(var: list[dict], ist: list[dict], alpha: float) -> dict:
    """Tagesweise Differenz (Variante - Ist) in $, zerlegt in Kurseffekt und Kostenersparnis."""
    def je_tag(z):
        d = {}
        for x in z:
            t = x["runde"]["kauf_t"][:10]
            n = x["runde"]["kauf_nominal"]
            k, s = d.get(t, (0.0, 0.0))
            d[t] = (k + n * x["kurs_pct"] / 100, s + n)
        return d
    a, b = je_tag(var), je_tag(ist)
    tage = sorted(set(a) | set(b))
    kurs = [a.get(t, (0, 0))[0] - b.get(t, (0, 0))[0] for t in tage]
    kosten = [(b.get(t, (0, 0))[1] - a.get(t, (0, 0))[1]) * K / 100 for t in tage]
    if not tage:
        return {}
    _, klo, khi = ab.block_bootstrap(tage, kurs, stat="summe", B=4000)
    _, blo, bhi = ab.block_bootstrap(tage, kurs, stat="summe", B=4000, alpha=alpha)
    gesamt = [x + y for x, y in zip(kurs, kosten)]
    _, glo, ghi = ab.block_bootstrap(tage, gesamt, stat="summe", B=4000)
    return {"kurseffekt_usd": round(sum(kurs), 2), "kurseffekt_bereich95": [round(klo, 1), round(khi, 1)],
            "kurseffekt_bonferroni": [round(blo, 1), round(bhi, 1)],
            "kostenersparnis_usd": round(sum(kosten), 2),
            "gesamt_usd_K150": round(sum(gesamt), 2), "gesamt_bereich95": [round(glo, 1), round(ghi, 1)],
            "runden_variante": len(var), "runden_ist": len(ist)}


def einstieg(R: list[dict], k1m, von_ms: int, bis_ms: int) -> dict:
    """Kurs nach echtem Kauf gegen alle vollen Stunden derselben Muenze im Fenster."""
    out = {}
    for h in STUNDEN:
        werte, tage, zufall_je_coin = [], [], {}
        for c in k1m.d:
            t = k1m.d[c]["t"]
            # Zufall: Raster alle 7 Minuten (nicht auf vollen Stunden - A4 fand im Stundenraster 1 h +0,17 statt +0,08)
            stunden = np.arange(von_ms - von_ms % 60_000, min(bis_ms, int(t[-1]) - h * 3_600_000), 7 * 60_000)
            r = []
            for s in stunden:
                a, b = k1m.kurs_bei(c, int(s)), k1m.kurs_bei(c, int(s) + h * 3_600_000)
                if a and b:
                    r.append((b / a - 1) * 100)
            zufall_je_coin[c] = float(np.mean(r)) if r else None
        for x in R:
            # Basis = letzter abgeschlossener Minutenschluss VOR dem Kauf, nicht der Papier-Fuellkurs
            # (A10-Befund 5: Papier fuellt Kaeufe in Einbruechen unter dem Minutenschluss, 18,98 $ in E7)
            a0 = k1m.kurs_bei(x["coin"], x["kauf_ms"] - 60_000)
            b = k1m.kurs_bei(x["coin"], x["kauf_ms"] + h * 3_600_000)
            zc = zufall_je_coin.get(x["coin"])
            if a0 is None or b is None or zc is None or x["kauf_ms"] + h * 3_600_000 > k1m.ende(x["coin"]):
                continue
            werte.append((b / a0 - 1) * 100 - zc)
            tage.append(x["kauf_t"][:10])
        if werte:
            m, lo, hi = ab.block_bootstrap(tage, werte, B=4000)
            out[f"{h}h"] = {"n": len(werte), "vorsprung_pct": round(m, 3), "bereich95": [round(lo, 3), round(hi, 3)]}
    return out


def messen(von: str, bis: str, lagen: dict, k1m, k1h, rsis, atr, puffer: float) -> dict:
    ab.VON, ab.BIS, ab.V6 = von, bis, V6
    R = [r for r in ab.runden_e7() if r["coin"] in k1m.d and r["kauf_ms"] + 120_000 < k1m.ende(r["coin"])]
    for r in R:
        r["lage"] = lage_vor(lagen, r["kauf_t"])

    def trail_atr(r):
        tg, ap = atr[r["coin"]]
        return max(ABSTAND, 2.0 * ab.atr_bei(tg, ap, r["kauf_ms"]))

    basis = Regel("Ist", sl=SL, start=start_aus_abstand(ABSTAND), trail=ABSTAND, be_ab=BE_AB, puffer=puffer)
    varianten = {
        "Ist": (lambda r: basis, None),
        "X1": (lambda r: replace(basis, name="X1", trail=trail_atr(r), start=start_aus_abstand(trail_atr(r))), None),
        "H12": (lambda r: Regel("H12", sl=SL, start=999.0, trail=ABSTAND, be_ab=None, signal=False), 12),
        "oSig": (lambda r: replace(basis, name="oSig", signal=False), None),
    }
    z = {n: spiele_alle(R, f, k1m, rsis, ende_h=e) for n, (f, e) in varianten.items()}
    lagen_da = sorted({r["lage"] for r in R})
    alpha = 0.05 / max(1, (len(varianten) - 1) * (len(lagen_da) + 1))
    erg = {"fenster": [von, bis], "runden_echt": len(R), "puffer": puffer,
           "start_ist": round(start_aus_abstand(ABSTAND), 3), "alpha_bonferroni": alpha,
           "eichung": {}, "varianten": {}, "gepaart": {}, "einstieg": {}}
    echt_kurs = [r["kurs_pct"] for r in R]
    ist_kurs = {x["runde"]["kauf_t"]: x["kurs_pct"] for x in z["Ist"]}
    paare = [(ist_kurs[r["kauf_t"]], r["kurs_pct"]) for r in R if r["kauf_t"] in ist_kurs]
    erg["eichung"] = {"runden_gleich": len(paare),
                      "nachspielung_minus_echt_pct": round(float(np.mean([a - b for a, b in paare])), 3) if paare else None,
                      "echt_kurs_mittel_pct": round(float(np.mean(echt_kurs)), 3) if echt_kurs else None}
    for teil in ["gesamt"] + lagen_da:
        sel = (lambda x: True) if teil == "gesamt" else (lambda x, t=teil: x["runde"]["lage"] == t)
        erg["varianten"][teil] = {n: kennzahl([x for x in zz if sel(x)]) for n, zz in z.items()}
        erg["gepaart"][teil] = {n: gepaart([x for x in zz if sel(x)], [x for x in z["Ist"] if sel(x)], alpha)
                                for n, zz in z.items() if n != "Ist"}
    erg["einstieg"] = einstieg(R, k1m, ab.ts_ms(von if von.endswith("Z") else von + "Z"),
                               ab.ts_ms(bis if bis.endswith("Z") else bis + "Z"))
    return erg


def bericht(monat: str, m: dict, kum: dict) -> str:
    z = [f"<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->",
         f"# Monatsmessung v6 · {monat}", "",
         "Entscheidung E6 (15.10.2026): offline nachgerechnet, ohne Eingriff in den Bot. Instanz **v6**. "
         f"Kostenlatte K = {K} % je Runde. Puffer aus dem Bot: {m['puffer']} %. Nachzieh-Start Ist: {m['start_ist']} %.",
         f"**Ein Urteil gibt es erst ab etwa {ENTSCHEIDBAR_AB} Runden je Vergleich.** Bis dahin sind die Zahlen eine Beobachtung, keine Entscheidung.", ""]
    for titel, e in ((f"Monat {monat}", m), ("Kumuliert seit 13.08.2026", kum)):
        z += [f"## {titel} · {e['runden_echt']} echte Runden", ""]
        ei = e["eichung"]
        z.append(f"Eichung: Die Ist-Nachspielung liegt im Mittel {ei['nachspielung_minus_echt_pct']} Punkte neben der echten Kursbewegung "
                 f"({ei['runden_gleich']} gleiche Runden).")
        z += ["", "| Lage | Variante | Runden | netto je Runde (K 0,150) | 95 %-Bereich | Kurseffekt gegen Ist | Kostenersparnis | gesamt gegen Ist |",
              "|---|---|---|---|---|---|---|---|"]
        for teil, vs in e["varianten"].items():
            for n, k in vs.items():
                if not k.get("n"):
                    continue
                g = e["gepaart"][teil].get(n)
                gp = (f"{g['kurseffekt_usd']:+.2f} $ [{g['kurseffekt_bereich95'][0]:+.1f}; {g['kurseffekt_bereich95'][1]:+.1f}]",
                      f"{g['kostenersparnis_usd']:+.2f} $",
                      f"{g['gesamt_usd_K150']:+.2f} $ [{g['gesamt_bereich95'][0]:+.1f}; {g['gesamt_bereich95'][1]:+.1f}]") if g else ("–", "–", "–")
                z.append(f"| {teil} | {n} | {k['n']} | {k['netto_je_runde_pct']:+.3f} % | [{k['bereich95'][0]:+.2f}; {k['bereich95'][1]:+.2f}] | "
                         f"{gp[0]} | {gp[1]} | {gp[2]} |")
        z += ["", "Einstieg gegen Zufall (Kurs nach dem Kauf ab letztem Minutenschluss, minus Mittel eines 7-Minuten-Rasters derselben Münze):", "",
              "| nach | Käufe | Vorsprung | 95 %-Bereich |", "|---|---|---|---|"]
        for h, v in e["einstieg"].items():
            z.append(f"| {h} | {v['n']} | {v['vorsprung_pct']:+.3f} % | [{v['bereich95'][0]:+.2f}; {v['bereich95'][1]:+.2f}] |")
        z.append("")
    n_kum = kum["runden_echt"]
    z += ["## Was das heißt", "",
          f"- Kumuliert liegen {n_kum} Runden vor. Für ein Urteil braucht es etwa {ENTSCHEIDBAR_AB}, also **"
          + ("entscheidbar, Vorlage an Sven**." if n_kum >= ENTSCHEIDBAR_AB else "noch nicht entscheidbar**."),
          "- Ein Kurseffekt-Bereich ohne die Null (Bonferroni-Spalte im JSON) wäre ein Hinweis auf eine bessere Ausstiegsregel. "
          "Gesparte Kosten allein sind kein Können (A10).", ""]
    return "\n".join(z)


def main() -> None:
    if "--monat" in sys.argv:
        monat = sys.argv[sys.argv.index("--monat") + 1]
    else:
        heute = datetime.now(timezone.utc).date()
        vm = heute.replace(day=1) - timedelta(days=1)
        monat = f"{vm.year}-{vm.month:02d}"
    j, mo = map(int, monat.split("-"))
    von = f"{monat}-01T00:00:00"
    bis = f"{j + (mo == 12)}-{(mo % 12) + 1:02d}-01T00:00:00"
    if "--ohne_laden" not in sys.argv:
        import a5_kerzen_laden
        a5_kerzen_laden.main()
    k1m, k1h = ab.Kerzen("1m"), ab.Kerzen("1h")
    ende = min(k1m.ende(c) for c in k1m.d)
    bis = min(bis, ab.iso(ende)[:19])
    rsis = {c: RSIStunde(k1h, k1m, c) for c in k1m.d}
    atr = {c: ab.atr_pct_1h(k1h, c) for c in k1h.d}
    lagen = lage_je_tag()
    puffer = puffer_aus_bot()
    m = messen(max(von, START_KUM), bis, lagen, k1m, k1h, rsis, atr, puffer)
    kum = messen(START_KUM, bis, lagen, k1m, k1h, rsis, atr, puffer)
    (P / "daten" / f"monatsmessung_{monat}.json").write_text(json.dumps({"monat": m, "kumuliert": kum}, indent=1, ensure_ascii=False),
                                                           encoding="utf-8")
    (P / "berichte" / f"monatsmessung_{monat}.md").write_text(bericht(monat, m, kum), encoding="utf-8")
    print(f"fertig: berichte/monatsmessung_{monat}.md ({m['runden_echt']} Runden im Monat, {kum['runden_echt']} kumuliert)")


if __name__ == "__main__":
    main()
