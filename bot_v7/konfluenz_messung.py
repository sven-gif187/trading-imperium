# -*- coding: utf-8 -*-
"""konfluenz_messung.py - prueft Marks Kernbehauptung an echten Kursen.

DIE BEHAUPTUNG
--------------
Aus Marks Vortrag (Merkvideo1.txt, 8:04-8:15), woertlich:

    "Wenn sich mehrere Anlaufzonen kreuzen, dann wird auch die Chance
     hoeher, dass der dort dreht."

Das ist KONFLUENZ: Fibonacci-Zonen aus verschiedenen Zeitrahmen liegen
uebereinander. Mark zeichnet dafuer Wellen und Subwellen ein und nimmt von
jeder die Rueckzugsmarken.

WAS HIER GEPRUEFT WIRD - UND WAS NICHT
--------------------------------------
GEPRUEFT:  Dreht der Kurs an einer Stelle, wo sich MEHRERE Fibonacci-Zonen
           aus verschiedenen Rueckblicklaengen treffen, haeufiger als an
           einer einzelnen Zone - und haeufiger als an einem Zufallspreis?

NICHT GEPRUEFT: Die Wellenzaehlung (1-2-3-4-5, A-B-C). Sie laesst sich nicht
           ohne Willkuer automatisieren, und genau darin liegt ihr Risiko:
           Ob etwas "Welle 4" war, weiss man erst hinterher. Der Vortrag ist
           durchgehend rueckblickend ("hat er perfekt gemacht"). Diese
           Messung schaut dagegen nur nach vorn.

KEIN BLICK IN DIE ZUKUNFT
-------------------------
Die Zonen werden ausschliesslich aus Kerzen berechnet, die VOR dem
Beruehrungszeitpunkt geschlossen waren. Ein Hoch gilt erst als Hoch, wenn
es von WEITE Kerzen auf beiden Seiten bestaetigt ist - und damit erst
WEITE Kerzen spaeter bekannt.

DIE TRIVIAL-LATTE
-----------------
Verglichen wird gegen ZUFALLSPREISE im selben Abstand vom Kurs. Ohne diesen
Vergleich sagt eine Trefferquote nichts: Wenn der Kurs ohnehin oft dreht,
trifft jede Linie.

QUELLEN
-------
  Kerzen  api.binance.com/api/v3/klines, 15 Minuten, 17.568 je Muenze,
          09.03. bis 08.09.2026. Echte gehandelte Preise.

AENDERT NICHTS AM BOT. Reines Rechnen auf gespeicherten Kerzen.
"""
import json
import io
import os
import random
import sys

ORD = (r"C:\Users\<BENUTZER>\AppData\Local\Temp\claude"
       r"\C--Users-sven7-Desktop-trading-imperium-v6-21-"
       r"\efb0dd76-0fbc-46d7-b8ff-7c7f12f375a5\scratchpad")

WEITE = 3                       # Kerzen links und rechts fuer einen Wendepunkt
RUECKBLICKE = (96, 384, 1344)   # 1 Tag, 4 Tage, 2 Wochen - die "Zeitrahmen"
VERHAELTNISSE = (0.382, 0.5, 0.618, 0.786)
NAEHE = 0.30                    # Prozent - so nah muessen zwei Zonen sein
TREFFER = 0.15                  # Prozent - so nah muss der Kurs an die Zone
UMKEHR = 1.0                    # Prozent Gegenbewegung = "er hat gedreht"
DURCHBRUCH = 0.5                # Prozent darunter = Zone hat NICHT gehalten
FENSTER = 16                    # Kerzen, in denen die Umkehr passieren muss
random.seed(20260911)           # damit die Zufallslatte reproduzierbar ist


def lade(sym):
    p = os.path.join(ORD, "kerzen_%s.json" % sym)
    if not os.path.exists(p):
        return None
    k = json.load(io.open(p, encoding="utf-8"))
    return [(float(x[2]), float(x[3]), float(x[4])) for x in k]   # hoch, tief, schluss


def zonen_bei(kerzen, i, rueckblick):
    """Fibonacci-Zonen aus dem Fenster VOR i. Nur bestaetigte Wendepunkte."""
    von = max(0, i - rueckblick)
    fenster = kerzen[von:i]
    if len(fenster) < 4 * WEITE + 2:
        return []
    # Bestaetigte Wendepunkte: WEITE Kerzen links UND rechts
    hochs, tiefs = [], []
    for j in range(WEITE, len(fenster) - WEITE):
        h = fenster[j][0]
        t = fenster[j][1]
        if all(fenster[j - d][0] <= h and fenster[j + d][0] <= h
               for d in range(1, WEITE + 1)):
            hochs.append(h)
        if all(fenster[j - d][1] >= t and fenster[j + d][1] >= t
               for d in range(1, WEITE + 1)):
            tiefs.append(t)
    if not hochs or not tiefs:
        return []
    hoch, tief = max(hochs), min(tiefs)
    spanne = hoch - tief
    if spanne <= 0:
        return []
    return [hoch - spanne * r for r in VERHAELTNISSE]


def dreht_er(kerzen, i, preis):
    """Kommt der Kurs ab i an preis heran - und dreht dann WIRKLICH nach oben?

    [KORREKTUR 11.09.2026] Die erste Fassung rechnete hoechstes minus
    tiefstes im Fenster und nannte das "gedreht". Das ist die
    SCHWANKUNGSBREITE, nicht die Umkehr - ein Kurs, der einfach
    weiterfaellt, hat auch eine Spanne von 1 %. Gemessen wurde damit
    Volatilitaet, nicht Richtung. Ergebnis: Konfluenz schien schlechter
    als Zufall, was unplausibel war und den Fehler verriet.

    Jetzt richtig: Die Zone gilt als gehalten, wenn der Kurs nach der
    Beruehrung um UMKEHR steigt, OHNE vorher um DURCHBRUCH darunter zu
    fallen. Faellt er zuerst durch, hat die Zone NICHT gehalten - egal,
    was danach passiert.
    """
    for j in range(i, min(i + FENSTER, len(kerzen))):
        if abs(kerzen[j][1] - preis) / preis * 100 <= TREFFER:
            ziel = preis * (1 + UMKEHR / 100.0)
            bruch = preis * (1 - DURCHBRUCH / 100.0)
            for m in range(j, min(j + FENSTER, len(kerzen))):
                if kerzen[m][1] <= bruch:
                    return True, False          # durchgefallen
                if kerzen[m][0] >= ziel:
                    return True, True           # gehalten und gedreht
            return True, False                  # weder noch: nicht gedreht
    return False, False


def messe(kerzen, schritt=24):
    einzeln = [0, 0]      # [beruehrt, gedreht]
    konfluent = [0, 0]
    zufall = [0, 0]
    i = max(RUECKBLICKE)
    while i < len(kerzen) - FENSTER * 2:
        alle = []
        for rb in RUECKBLICKE:
            alle += zonen_bei(kerzen, i, rb)
        if len(alle) >= 2:
            kurs = kerzen[i][2]
            # Konfluenz: mindestens zwei Zonen aus VERSCHIEDENEN Rueckblicken nah beieinander
            konf = []
            for a in range(len(alle)):
                nah = [b for b in range(len(alle)) if a != b
                       and abs(alle[a] - alle[b]) / alle[a] * 100 <= NAEHE]
                if nah:
                    konf.append(alle[a])
            allein = [z for z in alle if z not in konf]

            for z in konf[:3]:
                b, d = dreht_er(kerzen, i, z)
                if b:
                    konfluent[0] += 1
                    konfluent[1] += 1 if d else 0
            for z in allein[:3]:
                b, d = dreht_er(kerzen, i, z)
                if b:
                    einzeln[0] += 1
                    einzeln[1] += 1 if d else 0
            # Trivial-Latte: Zufallspreise im GLEICHEN ABSTAND wie die
            # Konfluenzzonen.
            #
            # [KORREKTUR 11.09.2026] Vorher wurden Zufallspreise ueber
            # plus/minus 4 % gestreut. Konfluenzzonen liegen aber viel
            # naeher am Kurs - sie wurden 727 Mal beruehrt, die Zufalls-
            # preise nur 264 Mal. Eine nahe Zone wird schon bei kleinen
            # Bewegungen beruehrt, und kleine Bewegungen drehen seltener
            # um 1 %. Damit verglich die Messung nicht Konfluenz gegen
            # Zufall, sondern NAH gegen FERN. Jetzt bekommt jede
            # Zufallszone denselben Abstand wie die Konfluenzzone, der
            # sie gegenuebersteht - nur an zufaelliger Stelle.
            for z0 in konf[:3]:
                abstand = abs(z0 - kurs) / kurs
                if abstand < 1e-6:
                    continue
                z = kurs * (1 - abstand) if random.random() < 0.5 else kurs * (1 + abstand)
                b, d = dreht_er(kerzen, i, z)
                if b:
                    zufall[0] += 1
                    zufall[1] += 1 if d else 0
        i += schritt
    return einzeln, konfluent, zufall


def zeile(name, w):
    if not w[0]:
        return "  %-28s keine Beruehrungen" % name
    return ("  %-28s beruehrt %5d   gedreht %5d   = %5.1f %%"
            % (name, w[0], w[1], 100.0 * w[1] / w[0]))


def main():
    print("=" * 78)
    print("  KONFLUENZ - Marks Kernbehauptung, an echten Kursen geprueft")
    print("  Zone getroffen bei %.2f %% Naehe, Umkehr = %.1f %% in %d Kerzen"
          % (TREFFER, UMKEHR, FENSTER))
    print("=" * 78)

    fehlt = [s for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT") if lade(s) is None]
    if fehlt:
        print("\n  Kerzendateien fehlen: %s" % ", ".join(fehlt))
        return 2

    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        k = lade(sym)
        e, kf, z = messe(k)
        print("\n%s" % sym)
        print(zeile("KONFLUENZ (2+ Zonen)", kf))
        print(zeile("Einzelne Zone", e))
        print(zeile("TRIVIAL: Zufallspreis", z))
        if kf[0] and z[0]:
            vk = 100.0 * kf[1] / kf[0]
            vz = 100.0 * z[1] / z[0]
            print("  %-28s %+.1f Prozentpunkte gegen Zufall"
                  % ("-> Konfluenz bringt", vk - vz))
    print("\n" + "=" * 78)
    print("  Ohne die Zufallslatte sagt eine Trefferquote nichts: Wenn der Kurs")
    print("  ohnehin staendig dreht, trifft jede Linie. Entscheidend ist der")
    print("  UNTERSCHIED zur Zufallszone.")
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
