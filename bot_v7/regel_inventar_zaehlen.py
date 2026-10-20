# -*- coding: utf-8 -*-
# NUR LESEND. Zaehlt Log-Kennungen je Tag in v7/data_store/system.log.
import re, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOG = r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v7\data_store\system.log"
TAGE = ["2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20", "2026-09-21"]
MUSTER = [
    ("Signal BUY-Kandidat", r"\[SIGNAL\] \[SIGNAL\] .*Score \d+/10 .*-> BUY"),
    ("Tor lehnt ab", r"Kauf abgelehnt trotz Score"),
    ("Tor: <2 Zeitrahmen", r"Zeitrahmen verfuegbar - Konfluenz nicht pruefbar"),
    ("Tor bestaetigt", r"Einstiegspreis bestaetigt"),
    ("Tor-Fehler", r"Tor-Fehler, Kauf abgelehnt"),
    ("Tor keine Kerzen", r"keine verwertbaren Kerzen"),
    ("Cash-Deckel 98%", r"gedeckelt \(freies Cash"),
    ("Regime-Filter", r"BUY blockiert \(Regime-Filter\)"),
    ("Wiedereinstieg Stufe1", r"BUY gesperrt - Wiedereinstiegs-Sperre"),
    ("Wiedereinstieg Stufe2", r"BUY gesperrt \(2\. Stufe\)"),
    ("Modus-Sperre", r"\[MODUS\] .*BUY gesperrt"),
    ("Smart-Entry zurueckgestellt", r"zurueckgestellt - Pump"),
    ("Smart-Entry kauft", r"\[SMART-ENTRY\] .*(Pullback|kaufe trotzdem)"),
    ("Risk REJECTED gesamt", r"REJECTED \[(Kapazitaet|STOERUNG)\]"),
    ("Risk Schlafmodus", r"REJECTED BUY .*Schlafmodus"),
    ("Risk Kill-Switch", r"REJECTED .*Kill-Switch"),
    ("Risk Drawdown", r"REJECTED .*Drawdown"),
    ("Risk Max Positionen", r"REJECTED .*Max Positionen"),
    ("Risk Exposure nicht pruefbar", r"REJECTED .*Exposure nicht pruefbar"),
    ("Risk Coin-Exposure", r"REJECTED .*wuerde \d+% sein"),
    ("Risk Sektor", r"REJECTED .*Sektor"),
    ("Risk Cooldown", r"REJECTED .*Cooldown:"),
    ("Risk Baerenmarkt", r"REJECTED .*Baerenmarkt"),
    ("Risk Bereits in Position", r"REJECTED .*Bereits in Position"),
    ("Exposure angepasst", r"\[RISK\] Exposure angepasst"),
    ("Risk-Sizer kuerzt", r"\[RISK\] Sizing:"),
    ("Risk APPROVED BUY", r"APPROVED \S+ BUY"),
    ("Trade-Lock belegt", r"Trade-Lock belegt"),
    ("Portfolio BLOCKED", r"\[PORTFOLIO\] BLOCKED"),
    ("Portfolio Betrag", r"\[PORTFOLIO\] Betrag:"),
    ("Live Spread/Volumen BLOCKED", r"LIVE-SAFETY\] BLOCKED"),
    ("Live Spread/Vol uebersprungen", r"Spread/Volume-Check uebersprungen"),
    ("Cash zu niedrig (<5$)", r"Cash zu niedrig"),
    ("Sizing auf Cash reduziert", r"Sizing reduziert auf"),
    ("NUPL-Sperre", r"KAUFE NICHT: Euphorie"),
    ("Groesse -> balanced 30%", r"\[SIZING\] \[balanced\]"),
    ("SIZING-CAP", r"\[SIZING-CAP\]"),
    ("Order-Deckel 25$", r"auf Deckel .* gekuerzt"),
    ("Mindestbetrag Boerse", r"unter dem Mindestbetrag"),
    ("Sleep-Mode Execution", r"Sleep-Mode \(|Bot pausiert"),
    ("Schlafmodus aktiviert", r"Schlafmodus aktiviert"),
    ("Doppelte Order", r"Doppelte Order"),
    ("Cash-Reservation abgelehnt", r"Cash-Reservation abgelehnt"),
    ("Warte laeuft bereits", r"laeuft bereits"),
    ("Warte ECHT gestellt", r"ECHTER Warte-Auftrag"),
    ("Warte BEDIENT", r"BEDIENT"),
    ("Warte verfallen", r"Warte-Auftrag .*verfallen"),
    ("Warte nicht einsehbar", r"NICHT einsehbar"),
    ("Warte Takt-Fehler", r"Warte-Auftraege: Takt fehlgeschlagen"),
    ("Warte NICHT gebucht", r"NICHT gebucht"),
    ("Daily-Loss", r"DAILY LOSS LIMIT|\[DAILY-LOSS\]"),
    ("DCA-Pfad", r"\[DCA\]"),
    ("Order nicht gefuellt", r"Order nicht gefuellt"),
    ("SELL: STOP_LOSS", r"STOP_LOSS TRIGGERED"),
    ("SELL: TRAILING", r"TRAILING_STOP TRIGGERED"),
    ("SELL: BREAKEVEN", r"BREAKEVEN_LOCK TRIGGERED"),
    ("SELL: FIBONACCI", r"FIBONACCI_ZIEL TRIGGERED"),
    ("SELL: TAKE_PROFIT", r"TAKE_PROFIT TRIGGERED|Take-Profit \("),
    ("SELL: TREND_EXIT scharf", r"TREND_EXIT TRIGGERED"),
    ("Schatten TREND_EXIT", r"TREND_EXIT haette ausgeloest"),
    ("Schatten Leiter/Hold", r"\[SCHATTEN\] .*haette ausgeloest"),
    ("SELL: RSI>80", r"SELL -> RSI overbought"),
    ("SELL: NOTAUS-NETZ", r"NOTAUS-NETZ"),
    ("Auto-Defense", r"AUTO-DEFENSE"),
    ("Sell rejected/Fehler", r"Sell rejected|Sell-Fehler"),
    ("Verkaufsmenge gekappt", r"Verkaufsmenge auf echten"),
    ("Geister-Position live", r"auf dem Konto, aber Verkauf"),
    ("SELL abgebrochen", r"SELL abgebrochen"),
    ("Kein Preis fuer Monitor", r"Kein Preis verfuegbar, ueberspringe"),
    ("Paper-Rueckfall", r"Live-Verbindung fehlgeschlagen|Fallback: Paper|Exchange-Fehler"),
    ("[PAPER] Buchung", r"\[PAPER\] (SELL|Warte)"),
    ("Recovery unbekannt", r"lokal unbekannt"),
    ("Monitor-Lauf mit Positionen", r"\[MONITOR\] Checking \d+ Position"),
]
TEST = re.compile(r"TEST/USDC|ID ORD-1|ORD-1\b")
reg = [(n, re.compile(m)) for n, m in MUSTER]
zeilen = collections.defaultdict(lambda: collections.Counter())
stunden = collections.defaultdict(set)
tag_re = re.compile(r"^\[(\d{4}-\d{2}-\d{2})T(\d{2})")
with open(LOG, "rb") as f:
    for roh in f:
        z = roh.replace(b"\x00", b"").decode("utf-8", "replace")
        m = tag_re.match(z)
        if not m or m.group(1) not in TAGE:
            continue
        if TEST.search(z):
            continue
        tag, std = m.group(1), m.group(2)
        for n, r in reg:
            if r.search(z):
                zeilen[n][tag] += 1
                stunden[n].add(tag + " " + std)
kopf = "Regel".ljust(32) + "".join(t[5:].rjust(7) for t in TAGE) + "  Summe  Std"
print(kopf)
for n, _ in MUSTER:
    c = zeilen[n]
    print(n.ljust(32) + "".join(str(c.get(t, 0)).rjust(7) for t in TAGE)
          + str(sum(c.values())).rjust(7) + str(len(stunden[n])).rjust(5))
