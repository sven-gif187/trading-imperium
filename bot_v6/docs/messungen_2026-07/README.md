# Messungen E1 / E2 / E5 — 29./30.07.2026

Reproduzierbare Ablage des Mess-Audits vor der Live-Freigabe.
Ergebnisse und Urteile: [BEFUNDE.md](BEFUNDE.md).
Interpretations-Warnung zum Giveback: `DIE-GESCHICHTE.md`, Anhang B.

## Der Kontrollanker — zuerst lesen

Jede Wiederholung ist nur gültig, wenn dieser Lauf vorher exakt stimmt:

```
cd docs/messungen_2026-07/code
python -c "from messung_e2_stops import kontrolle; from harness_ext import lade_jahr; d,f = lade_jahr(''); kontrolle(d,f)"
```

Erwartet: `Trades 1480 / 1480, Summe -450.5621 / -450.5621 -> IDENTISCH`.

Der Anker beweist, dass die Instrumentierung (`harness_ext.LaufMess`) bei
fester Stop-Regel bitgleich zum unveränderten Harness
(`backtest/ausstieg_backtest.py::Lauf`) rechnet. Weicht er ab, hat sich der
Harness, die Datenbasis oder Python geändert — dann sind alle Ausgaben in
`ausgaben/` nicht mehr vergleichbar und die Messung ist NEU zu bewerten,
nicht zu flicken.

## Umgebung

- Python 3.13.14, ausschließlich Standardbibliothek (kein numpy/pandas in
  den Messskripten)
- Projektstand 30.07.2026 (nach E9/E10/E11 vom 29.07.)
- Kerzendaten: `data_store/backtest/*.csv` (15m, zwei Jahresfenster:
  ohne Suffix = 2025-07-29..2026-07-29, `_v1` = 2024-07-29..2025-07-29)
  plus `fear_greed.json` (Tageswerte)
- Integrität prüfen: SHA256-Abgleich gegen
  `eingangsdaten/PRUEFSUMMEN.txt`
- Seeds: 20260730 in allen Zufallsläufen. Placebo I/II: 20 Ziehungen;
  phasengleiches Placebo: 40 Ziehungen; Block-Bootstrap: 2000 Resamples

## Reihenfolge der Läufe

| # | Skript | Frage | Rohausgabe |
|---|---|---|---|
| 1 | `code/messung_e1_nachkaufrate.py` | Warum misst der Harness 2,2 % statt 18,3 % Nachkaufrate? | `ausgaben/messung_e1_nachkaufrate_out.txt` |
| 2 | `code/messung_e1_fenster.py` | Hält das auch im Live-Zeitfenster? | `ausgaben/messung_e1_fenster_out.txt` |
| 3 | `code/messung_e2_stops.py` | Stop-Variation 2,0–5,0 % + ATR, beide Jahre | `ausgaben/messung_e2_stops_out.txt` |
| 4 | `code/messung_e2_einstieg.py` | Einstiegsqualität ohne Ausstiegsregel (MFE/MAE, Triple-Barrier) | `ausgaben/messung_e2_einstieg_out.txt` |
| 5 | `code/messung_e2_placebo.py` | Placebo I: echt gegen gleichverteilten Zufall | `ausgaben/messung_e2_placebo_out.txt` |
| 6 | `code/messung_e2_placebo2.py` | Placebo II: Richtung oder Volatilität? | `ausgaben/messung_e2_placebo2_out.txt` |
| 7 | `code/messung_e2_phasenplacebo.py` | Phasengleiches Placebo + Bootstrap-KIs | `ausgaben/messung_e2_phasenplacebo_out.txt` |
| 8 | `code/messung_e5_universum.py` | Coin-Kennzahlen, Universen, Reibung, Korrelation | `ausgaben/messung_e5_universum_out.txt` |
| 9 | `code/messung_ableitungen.py` | Verlust-Umverteilung, N_eff | `ausgaben/messung_ableitungen_out.txt` |
| 10 | `code/messung_f1_reibung.py` | Ordertypen, Gebühren, Break-even je Reibungsniveau, Horizontanalyse | `ausgaben/messung_f1_reibung_out.txt` |
| 11 | `code/messung_f1e_maker.py` | Maker statt Taker auf den realen Trades + Fill-Risiko | `ausgaben/messung_f1e_maker_out.txt` |
| 12 | `code/messung_f2_ic.py` | Feature-Screen: Information Coefficient, BH-FDR, Stabilität | `ausgaben/messung_f2_ic_out.txt` |
| 13 | `code/messung_f3_benchmark.py` | BTC kaufen-und-halten und wöchentliches DCA als Maßstab | `ausgaben/messung_f3_benchmark_out.txt` |
| 14 | `code/messung_g1_indikatoren.py` | Verifikation der F2-Nachbauten gegen die Projektimplementierungen | `ausgaben/messung_g1_indikatoren_out.txt` |
| 15 | `code/messung_g2_horizonte.py` | Barrierenrennen ±5/7/10 % über 7/14/30 Tage | `ausgaben/messung_g2_horizonte_out.txt` |

**Lauf 14 (G1), 30.07.2026 — Ausnahme von der Stdlib-Konvention.**
G1 verifiziert die F2-Indikator-Nachbauten gegen die Projektimplemen-
tierungen selbst (pandas 2.3.3, pandas_ta, numpy 2.2.6, scipy) — die
Referenz *ist* hier die Fremdbibliothek, deshalb gilt die
Stdlib-Konvention für diesen einen Lauf nicht. Der Lauf patcht die
Log-Methoden des Projekt-Loggers im Messprozess auf No-Ops, damit
`rsi_divergence.detect` nicht in die `system.log` des laufenden Bots
schreibt. Laufzeit ~6 min. Ergebnis: 17 von 21 numerisch geprüften
Features exakt (Spearman 1,0000); die vier Abweichungen und ihre
IC-Neuberechnung stehen in BEFUNDE.md 37–41.

**Lauf 15 (G2), 30.07.2026.** Reine Stdlib. First-Touch über
Block-Max/Min-Dekomposition beschleunigt; die Referenzkombination
±2,5 %/72 h reproduziert die E2-Werte 47,66 % (J2) / 50,69 % (J1)
exakt, das beweist die numerische Identität zur naiven E2-Schleife.
Kontrollanker und alle 26 Prüfsummen vor und nach beiden Läufen
unverändert. Laufzeit ~31 s.

`code/harness_ext.py` ist kein Lauf, sondern die gemeinsame
Instrumentierung (Subklasse des Harness, ATR ohne Look-ahead, Kennzahlen).
`code/messung_f_stat.py` ist ebenfalls kein Lauf, sondern die gemeinsame
Statistik für F1/F2/F3 (Spearman, Student-t über die unvollständige
Betafunktion, Benjamini-Hochberg, IC↔Trefferquote) — reine
Standardbibliothek, wie alles andere hier.

**Läufe 10–13 (F1/F2/F3), 30.07.2026.** Alle vier mit Exit-Code 0
ausgeführt, Datenbasis vor dem Lauf per SHA256 gegen `PRUEFSUMMEN.txt`
geprüft: 26 von 26 Dateien identisch, obwohl der Bot währenddessen im
Leerlauf weiterlief. Der Kontrollanker wurde vor und nach den Läufen
gerechnet, beide Male `1480 / -450.5621 -> IDENTISCH`. Laufzeiten:
`messung_f2_ic.py` ~120 s, `messung_f1e_maker.py` ~25 s, die übrigen
unter 20 s.

**Nachbau von Indikatoren in `messung_f2_ic.py`.** Die Features werden
ohne pandas/pandas_ta nachgebaut. Die Nachbauten folgen der jeweils im
Bot verwendeten Variante, nicht der Lehrbuchform: ADX nach
`data/market_data.py::_adx` (einfache rollende Mittel, **nicht** Wilder),
RSI/ATR mit Wilder-Glättung wie `pandas_ta`, Bollinger mit ddof=0, VWAP
als rollendes 120-Balken-Fenster wie `features/vwap_agent.py` es auf den
120 geholten Balken rechnet. Rundungsunterschiede zu pandas_ta sind für
eine Rangkorrelation ohne Belang; systematische Formelunterschiede wären
es nicht — deshalb steht die Quelle jeder Nachbildung im Docstring.

**Startprobe 30.07.2026:** Alle neun Läufe wurden am neuen Ort einmal
komplett ausgeführt, alle mit Exit-Code 0. Die sieben Läufe mit bereits
abgelegter Rohausgabe ergaben durchweg einen identischen Diff. Laufzeiten
zur Orientierung: `messung_e2_placebo.py` 731 s (langsamster, naive
Vorwärtssuche), `messung_e1_nachkaufrate.py` und `messung_e2_einstieg.py`
je 44 s, alle übrigen unter 30 s.

Alle Skripte laufen aus `code/` heraus ohne Argumente. Die Projektwurzel
wird relativ gesucht (Marker `app.py`), es gibt keine fest verdrahteten
Pfade mehr.

## Eingangsdaten

- `eingangsdaten/trades_v5_snapshot_2026-07-30.json` — eingefrorenes
  Live-Journal, **950 Einträge**, 10.06.2026 20:53 bis 29.07.2026 21:04.
  Das Original `data_store/trades_v5.json` wächst weiter, sobald der Bot
  läuft — für E1-Nachrechnungen NUR den Snapshot verwenden.

  **Achtung, Stichtagsdifferenz:** Die E1d-Kennzahlen (18,3 %
  Nachkaufrate, 421 abgeschlossene Positionen) wurden auf den **ersten
  942 Einträgen** gerechnet, Stand 29.07.2026 04:17. Der Bot lief danach
  bis 21:04 weiter und erzeugte 8 weitere Einträge (4 SELL, 4 BUY). Auf
  allen 950 Einträgen lauten dieselben Kennzahlen: 425 abgeschlossene
  Positionen, 78 mit mindestens einem Nachkauf, **18,35 %**. Der
  Unterschied zur ursprünglichen Auswertung beträgt +0,06 Prozentpunkte
  und ändert keine Schlussfolgerung (Faktor gegen die Harness-Rate von
  2,2 %: 8,31 statt 8,34). Wer nachrechnet und 18,35 % statt 18,29 %
  erhält, hat richtig gerechnet — nicht die Auswertung, sondern der
  Stichtag ist verschieden.
- `eingangsdaten/PRUEFSUMMEN.txt` — SHA256 über 23 Kerzen-/F&G-Dateien,
  `config.json`, Journal und Snapshot zum Stand 30.07.2026.

## Schutz vor cleanup.py — und wie dünn er ist

**Der Schutz hängt an einer einzigen Zeile fremden Codes:** `docs` steht in
`KEEP_DIRS` (cleanup.py:71-76). Trifft `collect_candidates()` auf ein
Verzeichnis aus dieser Menge, überspringt es den Ordner per `continue`
(cleanup.py:177-179) und betritt ihn nie. Wer diese Zeile ändert, ohne
diese Messungen zu kennen, hebt den Schutz auf.

Der `[CLEANUP-KEEP]`-Marker in Zeile 2 jeder `.py` ist **reine
Rückfallebene und greift heute an keiner einzigen Stelle**: Er wird nur im
Hauptordner (cleanup.py:191) und in der Unterordner-Schleife
(cleanup.py:208) geprüft. Letztere läuft ausschließlich über
`SUBDIRS_TO_SCAN` (cleanup.py:114-115), wo `docs` fehlt, und sie ist nicht
rekursiv — sie erreichte `messungen_2026-07/code/` selbst dann nicht, wenn
`docs` aufgenommen würde. Der Marker wirkt erst, wenn jemand die
Scan-Logik erweitert.

Der Buch-Schutz für `.md` (cleanup.py:160-168) deckt genau zwei der 23
Dateien ab: diese README und BEFUNDE.md.

**Es gibt keine Kopie außerhalb dieses Rechners.** Kein Git, keine
Versionierung, kein externes Backup. Ein Festplattenfehler löscht Messung
und Beleg gleichzeitig.
