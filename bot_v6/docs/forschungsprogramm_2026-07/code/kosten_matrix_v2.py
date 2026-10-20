# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - Kostenmatrix v2, 30.07.2026.
"""
Neurechnung der Boersen-Kostenmatrix nach der Gebuehrenkorrektur des
Eigentuemers vom 30.07.2026.

ANLASS: Die Matrix v1 unterstellte fuer Bybit EU Maker 0,10 % / Taker
0,10 %. Der Eigentuemer hat die offizielle Gebuehrenseite direkt geprueft
(bybit.eu Help-Center "Bybit Spot Fees Explained", Stand 08.03.2026):
tatsaechlich **Maker 0,10 % / Taker 0,25 %**. Damit war die in Matrix v1
als UNGEKLAERT markierte Taker-Aenderungsankuendigung bestaetigt.

KEIN TRIAL: Dieses Skript wertet keine Handelsregel gegen Marktdaten aus.
Es rechnet ausschliesslich Kostenarithmetik. Trial-Zaehler bleibt T-015.

FORMEL: p_be = 0,5 + c/(2B)   (symmetrische Barrieren, Gewinn=+B,
Verlust=-B, c = Round-Trip-Reibung in Prozentpunkten des Einsatzes)

SLIPPAGE-KONVENTION (einheitlich, damit die Boersen vergleichbar sind):
  Market/Taker: 0,05 % je Seite (Majors). Das ist die Register-Annahme.
  Limit/Maker:  0,00 % Slippage, aber Adverse-Selection-Abschlag
                0,03 % je Trade (Mittelwert des in F1e GEMESSENEN
                Bereichs 0,019-0,041 %, messung_f1e_maker_out.txt).
Die Slippage-Werte sind Annahmen bis zur Live-Capture-Messung: UNGEKLAERT.
"""
import sys

# (Name, maker_pct_je_seite, taker_pct_je_seite, Quelle/Konfidenz)
BOERSEN = [
    ("Bybit EU", 0.10, 0.25,
     "bybit.eu Help-Center 08.03.2026, vom Eigentuemer direkt geprueft [SICHER]"),
    ("Bitvavo", 0.15, 0.25,
     "offizielle Gebuehrenseite (403 beim Abruf), Sekundaerquellen konsistent [WAHRSCHEINLICH]"),
    ("Kraken Pro", 0.25, 0.40,
     "offizielle Gebuehrenseite nicht abgerufen [WAHRSCHEINLICH]"),
]
BITPANDA_SPREAD = (1.00, 1.50)   # Broker-Spread je Seite, Bandbreite

SLIP_TAKER = 0.05        # je Seite
ADVERSE = 0.03           # je Trade, nur Maker-Fall (F1e-Mittelwert)
BARRIEREN = (5.0, 7.0, 10.0)


def p_be(c, B):
    return (0.5 + c / (2.0 * B)) * 100.0


def zeile(name, c, tag):
    werte = "  ".join(f"{p_be(c, B):8.2f} %" for B in BARRIEREN)
    return f"    {name:<22s} {tag:<8s} c={c:5.3f} %   {werte}"


def main():
    print("=" * 100)
    print(" KOSTENMATRIX v2 - nach Gebuehrenkorrektur Bybit EU (Taker 0,25 %)")
    print(" p_be = 0,5 + c/(2B).  Kein Trial - reine Kostenarithmetik.")
    print("=" * 100)

    print("\n  Gebuehrenbasis je Boerse (je Seite):")
    for name, mk, tk, q in BOERSEN:
        print(f"    {name:<12s} Maker {mk:.2f} %  Taker {tk:.2f} %   {q}")
    print(f"    {'Bitpanda':<12s} Broker-Spread {BITPANDA_SPREAD[0]:.2f}-"
          f"{BITPANDA_SPREAD[1]:.2f} % je Seite [WAHRSCHEINLICH]")

    print("\n" + "=" * 100)
    print(" NOETIGE TREFFERQUOTE p_be")
    print("=" * 100)
    print(f"\n    {'Boerse':<22s} {'Pfad':<8s} {'Reibung':<13s} "
          f"{'+/-5 %':>10s}  {'+/-7 %':>10s}  {'+/-10 %':>10s}")
    print("    " + "-" * 82)

    ergebnis = {}
    for name, mk, tk, _q in BOERSEN:
        c_taker = 2 * tk + 2 * SLIP_TAKER
        c_maker = 2 * mk + 2 * ADVERSE
        ergebnis[name] = (c_taker, c_maker)
        print(zeile(name, c_taker, "TAKER"))
        print(zeile(name, c_maker, "MAKER"))
        print("    " + "-" * 82)
    for lo_hi, bez in ((BITPANDA_SPREAD[0], "min"), (BITPANDA_SPREAD[1], "max")):
        print(zeile("Bitpanda", 2 * lo_hi, f"BROKER{bez[:1]}"))

    print("\n" + "=" * 100)
    print(" VERGLEICH ZUR MATRIX v1 (Bybit EU)")
    print("=" * 100)
    alt_c = 0.30
    neu_t, neu_m = ergebnis["Bybit EU"]
    print(f"\n    {'Szenario':<40s} {'c':>8s}  {'+/-5 %':>9s}  {'+/-7 %':>9s}  {'+/-10 %':>9s}")
    print("    " + "-" * 82)
    for bez, c in (("v1 ANNAHME Taker 0,10 % (FALSCH)", alt_c),
                   ("v2 IST Taker 0,25 %, Market-Pfad", neu_t),
                   ("v2 IST Maker 0,10 %, Limit-Pfad", neu_m)):
        print(f"    {bez:<40s} {c:7.3f} %  " +
              "  ".join(f"{p_be(c, B):8.2f} %" for B in BARRIEREN))

    print("\n" + "=" * 100)
    print(" ABGLEICH MIT DER 57,5-%-ANGABE DES EIGENTUEMERS")
    print("=" * 100)
    print(f"""
    Angabe Eigentuemer: +/-5 % erfordert 57,50 % statt 53,00 %.
    Rueckrechnung: p=57,50 % bei B=5 % impliziert c = {2*5*(0.575-0.5):.3f} %.
    Diese Reibung entsteht bei Taker 0,25 %/Seite NUR mit einer
    Slippage-Annahme von {(0.75 - 2*0.25)/2:.3f} % je Seite.
    Die Register-Konvention ist {SLIP_TAKER:.2f} % je Seite (Majors); damit
    ergibt sich c = {neu_t:.2f} % und p_be = {p_be(neu_t, 5.0):.2f} %.

    Beide Zahlen sind verteidigbar - die Differenz ist REIN die
    Slippage-Annahme, nicht die Gebuehr. {p_be(neu_t, 5.0):.1f} % gilt fuer
    liquide Majors, 57,5 % ist die konservativere Variante und trifft
    duenne Alt-Buecher eher. Die Live-Capture-Messung entscheidet das;
    bis dahin wird BEIDES ausgewiesen.
    """)

    print("=" * 100)
    print(" GEWICHTETE MATRIX v2")
    print("=" * 100)
    gew = {"Kosten": 0.25, "EU-Nutzbarkeit": 0.20, "API/Integration": 0.20,
           "Liquiditaet/Paare": 0.15, "Quote-Asset": 0.10,
           "Migration": 0.05, "Gegenpartei": 0.05}
    # Kosten-Score v2 neu vergeben (Begruendung im Bericht), Rest unveraendert v1
    scores = {
        "Bybit EU":  {"Kosten": 6, "EU-Nutzbarkeit": 9, "API/Integration": 9,
                      "Liquiditaet/Paare": 7, "Quote-Asset": 8, "Migration": 9,
                      "Gegenpartei": 6},
        "Bitvavo":   {"Kosten": 5, "EU-Nutzbarkeit": 9, "API/Integration": 7,
                      "Liquiditaet/Paare": 6, "Quote-Asset": 5, "Migration": 6,
                      "Gegenpartei": 7},
        "Kraken":    {"Kosten": 3, "EU-Nutzbarkeit": 9, "API/Integration": 7,
                      "Liquiditaet/Paare": 7, "Quote-Asset": 7, "Migration": 7,
                      "Gegenpartei": 8},
        "Bitpanda":  {"Kosten": 1, "EU-Nutzbarkeit": 9, "API/Integration": 3,
                      "Liquiditaet/Paare": 4, "Quote-Asset": 5, "Migration": 2,
                      "Gegenpartei": 8},
    }
    alt_summe = {"Bybit EU": 8.20, "Bitvavo": 6.50, "Kraken": 6.70, "Bitpanda": 4.25}
    print(f"\n    {'Boerse':<12s} " +
          " ".join(f"{k[:9]:>10s}" for k in gew) + f" {'SUMME v2':>10s} {'v1':>7s} {'Delta':>7s}")
    print("    " + "-" * 108)
    rang = []
    for name, sc in scores.items():
        s = sum(sc[k] * w for k, w in gew.items())
        rang.append((s, name))
        print(f"    {name:<12s} " + " ".join(f"{sc[k]:10d}" for k in gew) +
              f" {s:10.2f} {alt_summe[name]:7.2f} {s - alt_summe[name]:+7.2f}")
    rang.sort(reverse=True)
    print("\n    Rangfolge v2: " + "  >  ".join(f"{n} ({s:.2f})" for s, n in rang))
    zweiter = rang[1][0]
    print(f"    Abstand Platz 1 zu Platz 2: {rang[0][0] - zweiter:.2f} "
          f"(v1: {8.20 - 6.70:.2f})")

    print("\n" + "=" * 100)
    print(" ROBUSTHEITSPRUEFUNG DER RANGFOLGE")
    print("=" * 100)
    print("\n    Ab welchem Kosten-Gewicht kippt Platz 1?")
    for w in (0.25, 0.35, 0.45, 0.55, 0.65, 0.75):
        rest = 1.0 - w
        skal = rest / (1.0 - gew["Kosten"])
        tab = []
        for name, sc in scores.items():
            s = sc["Kosten"] * w + sum(sc[k] * gew[k] * skal
                                       for k in gew if k != "Kosten")
            tab.append((s, name))
        tab.sort(reverse=True)
        print(f"    Kosten-Gewicht {w:.0%}: " +
              "  ".join(f"{n} {s:.2f}" for s, n in tab[:3]))
    print("\n    Lesart: Bleibt derselbe Name vorn, ist die Empfehlung nicht")
    print("    von der (unsicheren) Kostenschaetzung allein getragen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
