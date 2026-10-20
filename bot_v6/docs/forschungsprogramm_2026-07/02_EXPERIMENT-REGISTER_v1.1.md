# EXPERIMENT-REGISTER v1.1 — Änderungsdokument zu v1.0

**Version 1.1 — 30.07.2026 — Status: §2 ZUR FREIGABE VORGELEGT.**

v1.0 bleibt als Datei unverändert erhalten (Audit-Trail). v1.1 ändert
**ausschließlich Abschnitt 2 (Kostenmodell)**. Alle übrigen Abschnitte von
v1.0 — Erfolgsdefinition, Gates, Datengrundlage, H1–H4, Regeln,
Parameterräume, Placebo-Design, Trial-Zählung, Verbotsliste — gelten
unverändert weiter und sind vom Eigentümer am 30.07.2026 freigegeben.

## Änderungsgrund

Der Eigentümer hat die offizielle Bybit-EU-Gebührenseite direkt geprüft
(Help-Center „Bybit Spot Fees Explained", Stand 08.03.2026): **Maker
0,10 % / Taker 0,25 %** je Seite. v1.0 unterstellte 0,10 %/0,10 % und war
damit in der Taker-Annahme um Faktor 2,5 zu günstig. Damit ist die in
Matrix v1 als UNGEKLÄRT markierte Taker-Änderungsankündigung aufgelöst —
sie war real und material. Eigene Nachprüfung scheiterte dreimal
technisch (Timeout/ECONNRESET auf bybit.eu); die Lesung des Eigentümers
ist die Primärquelle [SICHER].

**Nebenbefund (Sicherheitsrelevanz):** `ccxt.bybit().fees['trading']`
liefert maker 0,01 % / taker 0,075 % — für EU-Spot falsch. Gebühren
dürfen NIE aus ccxt-Metadaten stammen. Auflage in die
Migrationsspezifikation übernommen.

## §2 NEU — Kostenmodell

Reproduktion: `code/kosten_matrix_v2.py`, Ausgabe
`ausgaben_kosten_matrix_v2.txt`.

**Szenariengitter (ersetzt 0,15 / 0,30 / 0,50 % aus v1.0):**

| Szenario | c je Runde | Zusammensetzung | Rolle |
|---|---|---|---|
| **K-MAKER** | **0,26 %** | 2×0,10 % Maker + 2×0,03 % Adverse Selection | Best Case, **setzt Limit-Order-Pfad voraus** |
| **K-BASIS** | **0,60 %** | 2×0,25 % Taker + 2×0,05 % Slippage | **Hauptszenario** — heutiger Bot-Zustand (nur Market) |
| **K-KONSERVATIV** | **0,75 %** | 2×0,25 % Taker + 2×0,125 % Slippage | dünne Alt-Bücher; entspricht der 57,5-%-Angabe des Eigentümers |

Der Adverse-Selection-Abschlag 0,03 %/Trade ist der Mittelwert des in F1e
**gemessenen** Bereichs 0,019–0,041 %
(`docs/messungen_2026-07/ausgaben/messung_f1e_maker_out.txt`), keine
Annahme. Die Slippage-Werte sind Annahmen bis zur Live-Capture-Messung:
**UNGEKLÄRT**.

**Bindende Auswertungsregel:** Jede H1/H2/H3/H4-Auswertung berichtet alle
drei Szenarien. **CONFIRMED wird nur vergeben, wenn das Kriterium unter
K-BASIS (0,60 %) erfüllt ist.** K-MAKER darf ein Ergebnis nicht retten,
solange kein Limit-Order-Pfad existiert; K-MAKER-Ergebnisse werden als
„bedingt, setzt Limit-Pfad voraus" ausgewiesen. K-KONSERVATIV ist der
Stresstest.

**Ausführungsannahme unverändert:** Signal am Tagesschluss UTC,
Ausführung zum nächsten Tages-Open.

## Nötige Trefferquote p_be = 0,5 + c/(2B)

| Szenario | ±5 % | ±7 % | ±10 % |
|---|---|---|---|
| K-MAKER (0,26 %) | 52,60 % | 51,86 % | 51,30 % |
| **K-BASIS (0,60 %)** | **56,00 %** | **54,29 %** | **53,00 %** |
| K-KONSERVATIV (0,75 %) | 57,50 % | 55,36 % | 53,75 % |

Zum Vergleich der bisherige Messstand (G2, alte Kostenbasis): J2 erreichte
bei ±5/7/10 % nur 42,68 / 39,50 / 35,72 %. Die Hürde ist mit der
korrigierten Gebühr **um 3,0 Prozentpunkte höher** als in v1.0
angenommen — die Wahrscheinlichkeit eines negativen Gate 1 steigt
entsprechend.

## Folge für das Programm (keine Änderung der Hypothesen)

1. Der **Limit-Order-Pfad ist keine Optimierung mehr, sondern
   Voraussetzung**, um die günstige Kostenbasis dieser Börse überhaupt zu
   erreichen. Er bleibt trotzdem NACHGELAGERT: erst bauen, wenn ein
   Kandidat unter K-BASIS überlebt. Ein Kandidat, der nur unter K-MAKER
   trägt, rechtfertigt den Bau — und wird dann unter K-MAKER erneut
   geprüft, mit gemessenen Fill-Quoten statt Annahmen.
2. Regel 2 (kein Exit-Tuning) bleibt unberührt: Limit-Ausführung ist
   Execution, keine Signaländerung.
3. Trial-Budget unverändert 15 (T-016…T-030), inkl. der
   Portfolio-Trials T-022…T-024 (Eigentümer-Entscheid 30.07.).
4. Trial-Zähler steht bei **T-015**. Die Kostenneurechnung war kein Trial
   (keine Handelsregel gegen Marktdaten ausgewertet).
