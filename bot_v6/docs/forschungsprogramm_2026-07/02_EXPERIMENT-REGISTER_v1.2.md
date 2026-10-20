# EXPERIMENT-REGISTER v1.2 — Änderungsdokument zu v1.0/v1.1

**Version 1.2 — 30.07.2026 — Status: EINGEFROREN, vom Eigentümer
freigegeben.** Prüfsumme in `REGISTER-PRUEFSUMME.txt`.

v1.0 (Struktur, H1–H4, Kontaminationsregel, Placebo-Design,
Trial-Budget) und v1.1 §2 (Kostenszenarien K-MAKER/K-BASIS/
K-KONSERVATIV) bleiben als Dateien unverändert und gelten fort. v1.2
ergänzt **zwei Klauseln** und ändert sonst nichts.

## Klausel A — Segment-Kriterium (ersetzt „Vorzeichenstabilität")

v1.0 §0.2 verlangte, dass das Vorzeichen des EV in allen Segmenten
positiv ist. Das war zu schwach: ein netto-EV von +0,16 % je Runde
erfüllt es formal, ist aber von null nicht unterscheidbar.

**NEU, verbindlich:** Der **Netto-EV je Runde muss in JEDEM Segment
(S-A/S-B/S-C) die Kostenschwelle K-BASIS = 0,60 % überschreiten.**

Da die Netto-Rechnung die Kosten bereits abzieht
(`netto_ev = brutto − c`), heißt das operativ:
**brutto-EV je Runde > 1,20 % in jedem Segment** — die Runde muss ihre
Kosten zweimal verdienen. Dies ist die Lesart **L2** aus
`08_NEUBEWERTUNG-v1.2.md` §1 und wurde vom Eigentümer am 30.07.2026
ausdrücklich als verbindlich gewählt; die schwächere Lesart L1
(netto > 0) ist damit ausgeschlossen.

Der Sicherheitsaufschlag in Höhe der vollen Kosten ist Absicht: er
verhindert, dass ein Kandidat allein durch die Unsicherheit der
Kostenschätzung (Slippage [UNGEKLÄRT] bis zur Live-Capture-Messung)
über die Schwelle rutscht.

## Klausel B — Sekundäre Trials tragen Gate 1 nicht allein

v1.0 §3 stuft ein: H1-Assets **primär** BTCUSDT/ETHUSDT, **sekundär**
das 12er-Portfolio; H3 ist durchgehend survivorship-belastet und trug
bereits die Klausel *„ein CONFIRMED aus H3 allein kann Gate 1 nicht
tragen"*. Die analoge Klausel für H1-Portfolio-Trials fehlte.

**NEU, verbindlich und rückwirkend für die Bewertung vom 30.07.2026:**
Ein CONFIRMED aus einem **sekundären** Trial (H1-Portfolio T-022/T-023/
T-024 oder H3 T-029) **kann Gate 1 nicht allein tragen.** Gate 1 ist nur
positiv, wenn mindestens ein **primärer** Trial (BTC oder ETH, H1 oder
H2) alle Kriterien erfüllt.

Begründung: Sekundäre Trials beruhen auf einem Universum heutiger
Überlebender. Der Survivorship-Effekt ist in dieser Bewertung erstmals
beziffert worden (`08_NEUBEWERTUNG-v1.2.md` §3.2): im Segment S-C
liefern die 10 survivorship-selektierten Alts +9,780 % je Runde (n = 88),
BTC und ETH zusammen +0,331 % (n = 22) — Faktor 30. Ein Kriterium, das
diesen Effekt nicht neutralisiert, misst die Auswahl, nicht die Regel.

## Unverändert

Erfolgsdefinition im Übrigen, Gates, Regel 13 (zwei negative Gates =
Ende), Datengrundlage, Zeiträume, H1–H4-Regeln und Parameterräume,
Placebo-Design, Kostenszenarien, Trial-Budget 15, Verbotsliste.

## Wirkung auf die Bewertung vom 30.07.2026

Angewendet in `09_GATE-1-VERDICT.md`. Ergebnis: **kein CONFIRMED,
GATE 1 NEGATIV** — erstes von zwei negativen Gates nach Regel 13.
