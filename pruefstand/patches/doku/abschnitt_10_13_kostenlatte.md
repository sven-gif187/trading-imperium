## 10.13 Zielbörse Bitvavo USDC — die Kostenlatte fällt von 0,505 % auf 0,150 %

**Angelegt 14.10.2026** aus dem Prüfstand. **Entscheidung Sven** im Chat: „A Bitvavo, beide Bots umstellen“.

**Warum.** Der Bot verdiente vor Kosten +0,29 % je Runde, die Kosten bei Bybit EU lagen bei 0,50 %. Bitvavo verlangt auf seinen **USDC-Märkten 0,05 % je Seite** (Kategorie B, bitvavo.com/en/fees, geprüft 14.10.). Mit dem gemessenen Schlupf ergibt das **0,15 % je Runde**. Auf denselben 136 Runden aus E7 wären das **+33,65 $ statt −43,85 $** gewesen.

Bitvavo ist MiCA-zugelassen (AFM, Niederlande) mit Passporting nach Deutschland. Es bietet BTC, ETH und SOL gegen USDC, die Mindestorder liegt bei 5 USDC, und der Kurs weicht weniger als 0,01 % von Binance ab, der Kursquelle des Bots. Die Vorlage mit allen Börsen steht in `pruefstand\berichte\2026-10-14_zielboerse.md`.

**Was geändert wurde (eine Ursache, eine Epochengrenze):**

| Stelle | vorher | nachher |
|---|---|---|
| `backtest/fees.py` | – | neuer Eintrag `bitvavo_usdc` 0,05 / 0,05 |
| `execution/engine.py` `PAPER_GEBUEHR_BOERSE` | "bybit" (0,25 %) | "bitvavo_usdc" (0,05 %) |
| `execution/engine.py` `SPREAD_BP` BTC/ETH/SOL | Bybit-Messung 31.07. | Bitvavo-Stichprobe 14.10., 120 Proben: Median 2,78 / 4,27 / 5,72 bp, p90 4,35 / 5,15 / 8,12 bp |
| `K_BASIS_PCT` | 0,505 | **0,150** |
| Nullsicherung-Puffer (K + 0,045) | 0,55 | **0,195** |
| Nachzieh-Start ((1+K)/(1−1 %) − 1 + 0,05) | 1,57 | **1,21** |
| `config_zielgroessen.json` `kosten_je_runde_pct` | 0,505 | 0,150 |
| `CLAUDE.md` Abschnitt 8 | Bybit EU, 0,505 | Bitvavo USDC, 0,150 (alte Epochen weiter 0,505) |

**Wichtig für jede Auswertung:** Für Runden **vor** dieser Epoche gilt weiter K = 0,505 %. Wer alte und neue Runden mit derselben Latte rechnet, vermischt zwei Kostenwelten.

**Was es nicht beweist.** Auch mit Bitvavo-Kosten liegt der 95-%-Bereich je Runde noch unter null (Block-Bootstrap nach Tagen: −0,35 % bis +0,60 %). Billige Kosten sind die Voraussetzung, damit ein Vorsprung überhaupt sichtbar werden kann. Ob es einen gibt, prüfen die Prüf-Agenten A4 (Einstieg) und A5 (Ausstieg) im Prüfstand.

**Was bewacht werden muss.** Bitvavo kann den Satz ändern, so wie Bybit am 05.10. Der Kosten-Wächter W3 prüft künftig die Gebührenseite und misst die Bitvavo-Spanne rund um die Uhr. Die Stichprobe stammt von einem Nachmittag.

Werkzeuge: `pruefstand\patches\patch_kostenlatte_bitvavo.py`, `pruefstand\skripte\spanne_stichprobe.py`, `pruefstand\skripte\kosten_schatten.py`. Vorab-Registrierung: `pruefstand\epochen\E10_L9_kostenlatte_bitvavo.md`.
