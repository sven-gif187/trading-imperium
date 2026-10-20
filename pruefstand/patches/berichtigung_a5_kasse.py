# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Berichtigung 14.10.2026 nach Befund A5: Verkaufs-"amount" der 21 Signal-Verkaeufe ist netto.
Richtige E7-Zahlen: brutto +75,51 $, netto -34,11 $, Befund 42 betraf alle 136 Runden (54,78 $).
Schattenbuch Bitvavo inkl. Schlupf +42,66 $ (vorher +33,65 $), Bybit -34,85 $ (vorher -43,85 $).
Ersetzt nur Text in Dokumenten (Pruefstand + BOT-HANDBUCH.md v6/v7), jede Stelle genau einmal,
Zeilenenden je Datei erhalten. Aufruf: python berichtigung_a5_kasse.py [--anwenden]
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = Path(r"C:\Users\<BENUTZER>\Desktop")
P = D / "pruefstand"
HB6, HB7 = D / "trading_imperium_v6(21)" / "BOT-HANDBUCH.md", D / "trading_imperium_v7" / "BOT-HANDBUCH.md"
WARUM_ALT = "**Warum.** Der Bot verdiente vor Kosten +0,29 % je Runde, die Kosten bei Bybit EU lagen bei 0,50 %."
WARUM_NEU = "**Warum.** Der Bot verdiente vor Kosten +0,33 % je Runde, die Kosten bei Bybit EU lagen bei 0,50 %."
BEWEIS_ALT = "(Block-Bootstrap nach Tagen: −0,35 % bis +0,60 %)"
BEWEIS_NEU = "(Block-Bootstrap nach Tagen: −0,33 % bis +0,66 %)"
ERSETZ = {
    HB6: [(WARUM_ALT, WARUM_NEU), (BEWEIS_ALT, BEWEIS_NEU),
          ("**+33,65 $ statt −43,85 $** gewesen.", "**+42,66 $ statt −34,85 $** gewesen (berichtigt 14.10., siehe unten)."),
          ("(in E7 115 von 136 Runden, 45,91 $)", "(in E7 **alle 136** Runden, 54,78 $ – berichtigt 14.10., zuerst stand hier „115 von 136, 45,91 $“)")],
    HB7: [(WARUM_ALT, WARUM_NEU), (BEWEIS_ALT, BEWEIS_NEU),
          ("**+33,65 $ statt −43,85 $** gewesen.", "**+42,66 $ statt −34,85 $** gewesen (berichtigt 14.10., siehe unten).")],
    P / "berichte" / "2026-10-14_zielboerse.md": [
        ("Dieselben 136 v6-Runden wären damit **+33,65 $** statt −43,85 $.",
         "Dieselben 136 v6-Runden wären damit **+42,66 $** statt −34,85 $ (berichtigt 14.10., Abschnitt 0)."),
        ("| **0,150 %** | **+33,65 $** |", "| **0,150 %** | **+42,66 $** |"),
        ("| 0,504 % | −43,85 $ |", "| 0,504 % | −34,85 $ |"),
        ("| 0,210 % | +20,52 $ |", "| 0,210 % | +29,52 $ |"),
        ("| 0,256 % | +10,44 $ |", "| 0,256 % | +19,45 $ |"),
        ("| 0,781 % | −104,49 $ |", "| 0,781 % | −95,51 $ |"),
        ("| vor Kosten (brutto) | +0,292 % | −0,20 % bis +0,75 % |", "| vor Kosten (brutto) | +0,332 % | −0,18 % bis +0,81 % |"),
        ("| Bitvavo USDC inkl. Schlupf | +0,142 % | −0,35 % bis +0,60 % |", "| Bitvavo USDC inkl. Schlupf | +0,181 % | −0,33 % bis +0,66 % |"),
        ("| OKX mit X-Perps inkl. Schlupf | +0,082 % | −0,41 % bis +0,54 % |", "| OKX mit X-Perps inkl. Schlupf | +0,121 % | −0,39 % bis +0,60 % |"),
        ("| Bybit EU heute | −0,212 % | −0,71 % bis +0,25 % |", "| Bybit EU heute | −0,173 % | −0,68 % bis +0,30 % |"),
    ],
    P / "epochen" / "E10_L9_kostenlatte_bitvavo.md": [
        ("+33,65 $ statt −43,85 $.", "+42,66 $ statt −34,85 $ (berichtigt 14.10. nach A5; zuerst +33,65 / −43,85)."),
    ],
    P / "epochen" / "E9_v6_kaufgebuehr_einfach.md": [
        ("In E7 betraf das 115 von 136 Runden mit zusammen 45,91 $.",
         "In E7 betraf das **alle 136 Runden** mit zusammen 54,78 $ (berichtigt 14.10. nach A5; zuerst „115 von 136, 45,91 $“ – die 21 Signal-Verkäufe buchen die Kaufgebühr ebenfalls doppelt)."),
    ],
}


def main(anwenden: bool) -> int:
    fehler = 0
    for datei, paare in ERSETZ.items():
        b = datei.read_bytes()
        nl = "\r\n" if b.count(b"\r\n") > b.count(b"\n") / 2 else "\n"
        t = b.decode("utf-8")
        for alt, neu in paare:
            n = t.count(alt)
            if n != 1:
                print(f"ANKER {n}x  {datei.name}: {alt[:60]}"); fehler += 1; continue
            t = t.replace(alt, neu, 1)
        neu_b = t.encode("utf-8")
        if nl == "\r\n" and neu_b.count(b"\r\n") != neu_b.count(b"\n"):
            print(f"Zeilenenden gemischt: {datei.name}"); fehler += 1; continue
        if anwenden and not fehler:
            datei.write_bytes(neu_b)
        print(f"{'GESCHRIEBEN' if anwenden and not fehler else 'BEREIT'} {datei.name} ({len(paare)} Stellen)")
    return fehler


if __name__ == "__main__":
    sys.exit(1 if main("--anwenden" in sys.argv) else 0)
