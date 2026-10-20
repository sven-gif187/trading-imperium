# -*- coding: utf-8 -*-
"""
A4: Wirkung, Vertrauensbereich und noetige Rundenzahl fuer die vorab registrierbaren Einstiegs-Vorschlaege.

n_runden = ((z_alpha + z_beta) * sigma / effekt)^2 * DEFF       (Masterprompt 3.1)
  z_alpha = 1,645 (einseitig 5 %, Richtung vorab registriert), z_beta = 0,84 (80 % Trennschaerfe)
  DEFF (Design-Effekt) = (Breite Block-Bootstrap / Breite einfacher Bereich)^2 -> Tage-Klumpung der Runden
Tempo: 68 Runden je Monat (Masterprompt 3.8).
Grundlage: pruefstand/daten/a4_minuten_zerfall.csv (minutengenau, korrigierte runden_lib).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from a4_basis import DATEN, K_ALT, K_NEU, block_von_tag, bootstrap_mittel  # noqa: E402

a = pd.read_csv(DATEN / "a4_minuten_zerfall.csv")
ZA, ZB, TEMPO = 1.645, 0.84, 68


def bedarf(werte, bloecke, effekt, name, beleg, extra=None):
    w = pd.Series(werte).astype(float)
    ok = w.notna().values
    w, b = w[ok], np.asarray(bloecke)[ok]
    n, s = len(w), float(w.std())
    bs = bootstrap_mittel(w, b)
    iid_breite = 2 * 1.96 * s / math.sqrt(n)
    deff = max(1.0, ((bs[2] - bs[1]) / iid_breite) ** 2)
    n80 = ((ZA + ZB) * s / abs(effekt)) ** 2 * deff if effekt else float("inf")
    z = {"vorschlag": name, "n_heute": n, "mittel": round(bs[0], 3), "ci95": [round(bs[1], 3), round(bs[2], 3)],
         "sigma": round(s, 3), "deff": round(deff, 2), "effekt_angenommen": round(effekt, 3),
         "n_runden_80pct": int(math.ceil(n80)), "monate_bei_68": round(n80 / TEMPO, 1), "beleg": beleg}
    if extra:
        z.update(extra)
    print(f"{name}: n {n} Mittel {bs[0]:+.3f} [{bs[1]:+.2f};{bs[2]:+.2f}] sigma {s:.2f} DEFF {deff:.2f} -> Effekt {effekt:+.3f}: "
          f"{n80:,.0f} Runden ({n80 / TEMPO:.1f} Monate)")
    return z


V = []
tag12 = block_von_tag(a.tag, 1)
# V1 Schattenbuch feste Haltedauer 12 h (gleiche Kaeufe): Differenz fest12 - ist, minus 0,15 Nachspiel-Abschlag
d12 = a.m12 - a.brutto_pct
V.append(bedarf(d12, tag12, float(d12.mean()) - 0.15, "V1 Halteband 12 h (fest12 - ist, nach 0,15 Abschlag)",
                "a4_minuten_zerfall.json fest_gegen_ist.H12"))
# V1b: Einstiegsvorsprung 12 h ueber K (zeigt der Einstieg allein mehr als die Kosten?)
V.append(bedarf(a.xm12, tag12, float(a.xm12.mean()) - K_NEU, "V1b Vorsprung 12 h > K 0,150",
                "a4_minuten_zerfall.json zerfall_minutengenau.alle H12",
                {"netto_vorsprung_150": round(float(a.xm12.mean()) - K_NEU, 3), "netto_vorsprung_505": round(float(a.xm12.mean()) - K_ALT, 3)}))
# V1c: dasselbe bei 1 h (zeigt, warum kurze Haltedauer nicht traegt)
V.append(bedarf(a.xm1, tag12, float(a.xm1.mean()) - K_NEU, "V1c Vorsprung 1 h > K 0,150", "zerfall_minutengenau.alle H1"))
# V2 EMA_TREND im Seitwaertsmarkt: netto(K 0,150) je Runde < 0 ?
eb = a[(a.kaufweg == "EMA_TREND") & (a.lage == "B_SepOkt_seitwaerts")]
V.append(bedarf(eb.netto_150_pct, block_von_tag(eb.tag, 1), float(eb.netto_150_pct.mean()),
                "V2 EMA_TREND Sep/Okt netto(0,150) < 0", "a4_ergebnisse.json kaufweg.B_SepOkt_seitwaerts.EMA_TREND",
                {"netto_505_mittel": round(float(eb.netto_505_pct.mean()), 3), "vorsprung4_min": round(float(eb.xm4.mean()), 3),
                 "vorsprung12_min": round(float(eb.xm12.mean()), 3), "fest12_minus_ist": round(float((eb.m12 - eb.brutto_pct).mean()), 3)}))
ea = a[(a.kaufweg == "EMA_TREND") & (a.lage == "A_Aug_Trend")]
diff = float(ea.netto_150_pct.mean() - eb.netto_150_pct.mean())
s_pool = math.sqrt((ea.netto_150_pct.var() + eb.netto_150_pct.var()) / 2)
n_je_gruppe = 2 * ((ZA + ZB) * s_pool / diff) ** 2
V.append({"vorschlag": "V2b EMA_TREND Trend minus Seitwaerts (netto 0,150)", "diff": round(diff, 3), "sigma_pool": round(s_pool, 3),
          "n_je_lage_80pct_ohne_deff": int(math.ceil(n_je_gruppe)), "n_heute": [len(ea), len(eb)]})
print(f"V2b EMA Trend-Seitwaerts: Differenz {diff:+.3f}, sigma {s_pool:.2f} -> {n_je_gruppe:,.0f} Runden je Lage (ohne DEFF)")
# V3 Score: IC 12 h (minutengenau) - Runden fuer Beleg mit/ohne Bonferroni (7 Horizonte)
from a4_basis import bootstrap_spearman  # noqa: E402
ok = a[a.score.notna() & a.m12.notna()]
ic = bootstrap_spearman(ok.score, ok.m12, block_von_tag(ok.tag, 1))
for ic_ziel in (0.10, round(ic[0], 3)):
    n95 = ((1.96 + ZB) / math.atanh(ic_ziel)) ** 2 + 3
    nb = ((2.69 + ZB) / math.atanh(ic_ziel)) ** 2 + 3
    V.append({"vorschlag": f"V3 Score-IC 12 h = {ic_ziel}", "ic_heute": round(ic[0], 3), "ci95_heute": [round(ic[1], 3), round(ic[2], 3)],
              "n_runden_80pct_zweiseitig": int(math.ceil(n95)), "n_runden_80pct_bonferroni7": int(math.ceil(nb)),
              "monate_bonf_bei_68": round(nb / TEMPO, 1)})
    print(f"V3 IC {ic_ziel}: {n95:,.0f} Runden (zweiseitig) / {nb:,.0f} mit Bonferroni 7 (heute IC {ic[0]:+.3f} [{ic[1]:+.2f};{ic[2]:+.2f}])")
# Score 8 gegen Rest (Warnung vor Ueberanpassung)
s8 = a[a.score == 8]
rest = a[(a.score != 8) & a.score.notna()]
b8 = bootstrap_mittel(s8.brutto_pct, s8.tag)
br = bootstrap_mittel(rest.brutto_pct, rest.tag)
V.append({"vorschlag": "V3b Score 8 gegen Rest (nur Warnung)", "score8": [len(s8), round(b8[0], 3), [round(b8[1], 3), round(b8[2], 3)]],
          "rest": [len(rest), round(br[0], 3), [round(br[1], 3), round(br[2], 3)]],
          "score8_aug": round(float(s8[s8.lage == "A_Aug_Trend"].brutto_pct.mean()), 3),
          "score8_sepokt": round(float(s8[s8.lage == "B_SepOkt_seitwaerts"].brutto_pct.mean()), 3)})
print("V3b Score 8 vs Rest:", V[-1])
# V4 Vorlauf-Drittel: oberes gegen unteres Drittel, Vorsprung 4 h
hoch = a[a.v_drittel == "hoch"]
tief = a[a.v_drittel == "tief"]
d4 = float(hoch.xm4.mean() - tief.xm4.mean())
sp = math.sqrt((hoch.xm4.var() + tief.xm4.var()) / 2)
V.append({"vorschlag": "V4 Kauf nach Anstieg (oberes - unteres Drittel, Vorsprung 4 h)", "diff": round(d4, 3), "sigma_pool": round(sp, 3),
          "n_je_drittel_80pct_ohne_deff": int(math.ceil(2 * ((1.96 + ZB) * sp / d4) ** 2))})
print("V4:", V[-1])
(DATEN / "a4_vorschlaege.json").write_text(json.dumps(V, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("Geschrieben:", DATEN / "a4_vorschlaege.json")
