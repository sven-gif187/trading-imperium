"""
Bestaetigt eine ABSICHTLICHE Aenderung an den Regel-Schaltern.

Der Waechter (core/regel_waechter.py) schlaegt Alarm, sobald die Schalter
anders stehen als hinterlegt. Das ist gewollt - am 12.08.2026 hatte ein
Speichervorgang in der Einstellungsmaske den ganzen Block geloescht und
damit den Trend-Ausstieg wieder scharf geschaltet, ohne dass es jemand
bemerkte.

Wer eine Stellung ABSICHTLICH aendert, sagt dem Waechter hier einmal
Bescheid. Danach gilt der neue Stand als Referenz und der Alarm verstummt.

Aufruf:
    python regel_waechter_bestaetigen.py            zeigt den Vergleich
    python regel_waechter_bestaetigen.py --ja       uebernimmt den Ist-Stand
"""
import sys

from core.regel_schalter import RegelSchalter, BEKANNTE_REGELN, ACTIVE, vorgabe
from core.regel_waechter import RegelWaechter, RISKANT_WENN_AKTIV


def main():
    schalter = RegelSchalter()
    waechter = RegelWaechter(schalter)
    st = waechter.status()

    print("=" * 62)
    print("REGEL-SCHALTER - Vergleich")
    print("=" * 62)
    if st["block_fehlt"]:
        print("ACHTUNG: Der Block \"regel_modi\" fehlt in der config.json.")
        print("Dann faellt JEDE Regel auf ACTIVE zurueck.\n")

    print(f"{'Regel':24} {'hinterlegt':>12} {'tatsaechlich':>14}")
    print("-" * 62)
    for regel in BEKANNTE_REGELN:
        s = st["soll"].get(regel, vorgabe(regel))
        i = st["ist"].get(regel, vorgabe(regel))
        markierung = ""
        if s != i:
            markierung = "  <-- abweichend"
            if i == ACTIVE and regel in RISKANT_WENN_AKTIV:
                markierung = "  <-- WIEDER SCHARF"
        print(f"{regel:24} {s:>12} {i:>14}{markierung}")

    if not st["abweichungen"] and not st["block_fehlt"]:
        print("\nAlles wie hinterlegt - nichts zu bestaetigen.")
        return 0

    print()
    for regel in st["abweichungen"]:
        if st["ist"].get(regel) == ACTIVE and regel in RISKANT_WENN_AKTIV:
            print(f"WARNUNG zu {regel}: {RISKANT_WENN_AKTIV[regel]}")

    if "--ja" not in sys.argv:
        print()
        print("Nichts geaendert. Wenn der IST-Zustand richtig ist:")
        print("    python regel_waechter_bestaetigen.py --ja")
        print()
        print("Wenn NICHT: regel_modi in data_store/config.json wiederherstellen")
        print("und den Bot neu starten.")
        return 0

    if waechter.soll_schreiben(dict(st["ist"]), "von Hand bestaetigt"):
        print("\nUebernommen. Der Ist-Zustand ist jetzt die Referenz.")
        return 0
    print("\nFEHLGESCHLAGEN - Referenz nicht schreibbar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
