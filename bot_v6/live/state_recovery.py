# -*- coding: utf-8 -*-
"""
Trading Imperium V6 – State Recovery
Gleicht den internen Zustand mit der Boerse ab, nach Neustart oder Absturz.

WARUM DIESE DATEI AM 19.08.2026 UMGEBAUT WURDE
----------------------------------------------
Die alte Fassung verglich **Asset-Namen mit Symbolen**:

    fetch_balance()  liefert  "ETH"
    bot_state.json   fuehrt   "ETH/USDC"

"ETH" ist nicht "ETH/USDC". Beide Schleifen griffen deshalb IMMER:

    1) "ETH" fehlt lokal      -> neu anlegen als {"qty": …, "recovered": True}
    2) "ETH/USDC" fehlt aussen -> die ECHTE Position wurde GELOESCHT
    3) state.save()            -> und sofort dauerhaft festgeschrieben

Verloren gingen dabei entry_price, active, cost_basis, highest_price,
lowest_price, hoechst_pnl_pct, position_id, entry_score, entry_strategie
und dca_levels.

Der eigentliche Schaden stand im Exit-Monitor. runtime/exit_monitor.py
beginnt seine Schleife mit:

    if not pos.get("active"):
        continue

Die wiederhergestellten Positionen hatten kein "active" - sie wurden also
uebersprungen. **Kein Stop-Loss, kein Trailing, kein Breakeven, kein
Trend-Ausstieg.** Die Position lag im Depot und wurde von niemandem mehr
ueberwacht. Ohne entry_price waere selbst ein Verkauf von Hand ergebnislos
gewesen: es gab keinen Einstand mehr, gegen den man haette rechnen koennen.

Unsichtbar geblieben ist das, weil StateRecovery ausschliesslich im
Live-Modus laeuft (app.py, "if self.config.trading.mode == 'live'") - der
Bot laeuft seit Monaten auf Papier.

Befund 51 in GEFUNDENE-PROBLEME.md, Herleitung in BOT-HANDBUCH.md 4.72.

DIE DREI REGELN DER NEUEN FASSUNG
---------------------------------
1. **Einheitlicher Schluessel.** Verglichen wird ueber das Asset, das aus
   dem Symbol abgeleitet wird ("ETH/USDC" -> "ETH"). Nie wieder zwei
   Schluesselformen in einem Vergleich.

2. **Erhalten statt ersetzen.** Stimmt eine Position ueberein, wird NUR
   die Menge nachgezogen. Alle anderen Felder bleiben, wie sie waren.

3. **Nicht loeschen, sondern melden.** Ist eine Position lokal bekannt,
   an der Boerse aber nicht vorhanden, wird sie NICHT entfernt. Sie wird
   als Abweichung gemeldet und der Handel blockiert, bis ein Mensch
   entschieden hat. Eine Position stillschweigend zu loeschen ist die
   gefaehrlichste der drei moeglichen Reaktionen - sie sieht wie
   Aufraeumen aus und ist Datenverlust.

AUFRUF
------
    StateRecovery(runner, state_store, journal).run()
    python live/state_recovery.py --selbsttest    Gegentest ohne Boerse
"""
import os
import sys
from typing import Dict

# Beim direkten Aufruf (--selbsttest) liegt der Projektordner nicht im
# Suchpfad. Muss VOR dem core-Import stehen, sonst scheitert er.
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import log

# Menge gilt als gleich, wenn sie sich um weniger als das unterscheidet.
# Boersen runden unterschiedlich; 0,5 % Abweichung ist kein Widerspruch.
MENGEN_TOLERANZ = 0.005


def asset_von(schluessel: str) -> str:
    """'ETH/USDC' -> 'ETH'; 'ETH' bleibt 'ETH'.

    Der ganze Befund 51 haengt an dieser einen Zeile: Ohne sie wurden
    Asset-Namen mit Symbolen verglichen, und beide Seiten fanden sich nie.
    """
    if not schluessel:
        return ""
    return str(schluessel).split("/")[0].strip().upper()


class StateRecovery:
    def __init__(self, live_runner, state_store, journal):
        self.runner = live_runner
        self.state = state_store
        self.journal = journal
        self.abweichungen = []

    # ------------------------------------------------------------------
    def abgleichen(self, boersen_bestand: Dict[str, float],
                   lokale_positionen: Dict[str, dict]):
        """Reine Rechenlogik - ohne Boerse, damit sie testbar ist.

        Rueckgabe: (neue_positionen, abweichungen)
        """
        abweichungen = []
        ergebnis = dict(lokale_positionen)

        # Zuordnung Asset -> lokaler Schluessel (Symbol ODER Asset)
        lokal_nach_asset = {}
        for schluessel in lokale_positionen:
            lokal_nach_asset.setdefault(asset_von(schluessel), schluessel)

        # --- 1. Was die Boerse hat --------------------------------------
        for asset, menge in boersen_bestand.items():
            a = asset_von(asset)
            schluessel = lokal_nach_asset.get(a)

            if schluessel is None:
                # Wirklich unbekannt: anlegen, aber NICHT als handelbare
                # Position. Ohne entry_price waere jede Ausstiegsrechnung
                # Fantasie - deshalb active=False und ein sichtbarer Grund.
                ergebnis[a] = {
                    "qty": menge,
                    "active": False,
                    "recovered": True,
                    "recovered_grund": "an der Boerse gefunden, lokal unbekannt "
                                       "- kein Einstand, deshalb nicht handelbar",
                }
                abweichungen.append({
                    "art": "nur_boerse", "asset": a, "menge": menge,
                    "text": f"{a}: {menge:.8f} an der Boerse, lokal unbekannt. "
                            f"Angelegt als NICHT handelbar (kein Einstand).",
                })
                log.warn("RECOVERY", abweichungen[-1]["text"])
                continue

            # Bekannt: NUR die Menge nachziehen, alles andere behalten.
            pos = dict(ergebnis[schluessel])
            alt = float(pos.get("qty") or 0)
            if alt <= 0 or abs(menge - alt) / max(alt, 1e-12) > MENGEN_TOLERANZ:
                pos["qty"] = menge
                pos["qty_korrigiert_von"] = alt
                abweichungen.append({
                    "art": "menge_weicht_ab", "asset": a,
                    "lokal": alt, "boerse": menge,
                    "text": f"{a}: Menge lokal {alt:.8f}, Boerse {menge:.8f} "
                            f"- lokal nachgezogen.",
                })
                log.warn("RECOVERY", abweichungen[-1]["text"])
            else:
                log.info("RECOVERY", f"{a}: stimmt ueberein ({menge:.8f})")
            ergebnis[schluessel] = pos

        # --- 2. Was nur lokal steht -------------------------------------
        boersen_assets = {asset_von(a) for a in boersen_bestand}
        for schluessel, pos in list(ergebnis.items()):
            if not isinstance(pos, dict):
                continue
            if pos.get("recovered") and not pos.get("active"):
                continue          # gerade eben selbst angelegt
            if asset_von(schluessel) in boersen_assets:
                continue
            if not pos.get("active"):
                continue          # ohnehin nicht handelbar
            # NICHT loeschen. Melden und den Handel anhalten.
            abweichungen.append({
                "art": "nur_lokal", "asset": asset_von(schluessel),
                "schluessel": schluessel,
                "text": f"{schluessel}: lokal aktiv, an der Boerse NICHT "
                        f"vorhanden. Position bleibt stehen, Handel wird "
                        f"blockiert bis zur Klaerung.",
            })
            log.error("RECOVERY", abweichungen[-1]["text"])

        return ergebnis, abweichungen

    # ------------------------------------------------------------------
    def run(self):
        log.info("RECOVERY", "=== STATE RECOVERY GESTARTET ===")
        if not getattr(self.runner, "connected", False):
            log.warn("RECOVERY", "Nicht verbunden - uebersprungen")
            return None

        bal = self.runner.fetch_balance() or {}
        boersen_bestand = {}
        for asset, menge in (bal.get("total", {}) or {}).items():
            try:
                m = float(menge)
            except Exception:
                continue
            if m > 0 and str(asset).upper() not in ("USDC", "USDT", "USD", "EUR"):
                boersen_bestand[asset] = m
                log.info("RECOVERY", f"Boerse: {asset} = {m:.8f}")

        lokal = self.state.get("open_positions", {}) or {}
        log.info("RECOVERY", f"Lokal: {len(lokal)} Positionen")

        neu, abweichungen = self.abgleichen(boersen_bestand, lokal)
        self.abweichungen = abweichungen

        self.state.set("open_positions", neu)

        # Handelssperre setzen, wenn etwas nicht zusammenpasst. Ohne sie
        # wuerde der Bot auf einem Zustand weiterhandeln, den niemand
        # geprueft hat.
        ernst = [a for a in abweichungen if a["art"] in ("nur_lokal", "nur_boerse")]
        if ernst:
            self.state.set("recovery_blockade", {
                "seit": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc).isoformat(),
                "anzahl": len(ernst),
                "gruende": [a["text"] for a in ernst][:10],
            })
            log.error("RECOVERY",
                      f"{len(ernst)} ungeklaerte Abweichung(en) - "
                      f"Handel bleibt blockiert, bis sie geklaert sind.")
        else:
            self.state.delete("recovery_blockade")

        usdc = 0.0
        for w in ("USDC", "USDT"):
            try:
                usdc += float((bal.get("total", {}) or {}).get(w, 0) or 0)
            except Exception:
                pass
        self.state.set("last_known_balance", round(usdc, 2))
        self.state.save()

        log.info("RECOVERY",
                 f"=== FERTIG: {len(boersen_bestand)} Boersen-Bestaende, "
                 f"{len(abweichungen)} Abweichung(en), {usdc:.2f} $ ===")
        return neu


# ======================================================================
def selbsttest():
    """Gegentest ohne Boerse - stellt genau den Fall von Befund 51 nach."""
    fehler = 0
    sr = StateRecovery.__new__(StateRecovery)

    print("\n=== Richtung 1: der Fall aus Befund 51 ===")
    lokal = {"ETH/USDC": {"qty": 0.0923, "active": True, "entry_price": 1899.1,
                          "cost_basis": 176.3, "highest_price": 1921.16,
                          "position_id": "pos_ETH_287ff7e1"}}
    boerse = {"ETH": 0.0923}
    neu, abw = sr.abgleichen(boerse, lokal)
    print(f"  vorher : {list(lokal)}")
    print(f"  nachher: {list(neu)}")
    p = neu.get("ETH/USDC", {})
    pruef = [("Schluessel erhalten", "ETH/USDC" in neu),
             ("active erhalten", p.get("active") is True),
             ("entry_price erhalten", p.get("entry_price") == 1899.1),
             ("cost_basis erhalten", p.get("cost_basis") == 176.3),
             ("position_id erhalten", p.get("position_id") == "pos_ETH_287ff7e1"),
             ("keine Abweichung gemeldet", len(abw) == 0),
             ("kein Geister-Eintrag 'ETH'", "ETH" not in neu)]
    for name, ok in pruef:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: Menge weicht ab -> nachziehen, Rest behalten ===")
    neu, abw = sr.abgleichen({"ETH": 0.0800}, lokal)
    p = neu.get("ETH/USDC", {})
    for name, ok in [("Menge nachgezogen", p.get("qty") == 0.0800),
                     ("alte Menge festgehalten", p.get("qty_korrigiert_von") == 0.0923),
                     ("entry_price erhalten", p.get("entry_price") == 1899.1),
                     ("Abweichung gemeldet", any(a["art"] == "menge_weicht_ab" for a in abw))]:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 3: lokal aktiv, Boerse leer -> NICHT loeschen ===")
    neu, abw = sr.abgleichen({}, lokal)
    for name, ok in [("Position bleibt stehen", "ETH/USDC" in neu),
                     ("active unveraendert", neu["ETH/USDC"].get("active") is True),
                     ("als nur_lokal gemeldet", any(a["art"] == "nur_lokal" for a in abw))]:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 4: Boerse hat etwas Unbekanntes ===")
    neu, abw = sr.abgleichen({"SOL": 1.5}, lokal)
    p = neu.get("SOL", {})
    for name, ok in [("SOL angelegt", "SOL" in neu),
                     ("aber NICHT handelbar", p.get("active") is False),
                     ("Grund vermerkt", bool(p.get("recovered_grund"))),
                     ("ETH/USDC unberuehrt", neu.get("ETH/USDC", {}).get("entry_price") == 1899.1),
                     ("als nur_boerse gemeldet", any(a["art"] == "nur_boerse" for a in abw))]:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 5: leere Eingaben ===")
    for name, b, l in [("beides leer", {}, {}), ("nur Boerse leer", {}, lokal)]:
        try:
            n, a = sr.abgleichen(b, l)
            print(f"    OK   {name}: {len(n)} Positionen, {len(a)} Abweichungen")
        except Exception as e:
            print(f"    FEHLER {name}: {type(e).__name__}: {e}")
            fehler += 1

    print("\n=== Richtung 6: asset_von() ===")
    for ein, soll in [("ETH/USDC", "ETH"), ("ETH", "ETH"), ("btc/usdt", "BTC"),
                      ("", ""), (None, "")]:
        ist = asset_von(ein)
        ok = ist == soll
        print(f"    {'OK  ' if ok else 'FEHLER'} {str(ein):<12} -> {ist!r} (soll {soll!r})")
        if not ok:
            fehler += 1

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(1 if selbsttest() else 0)
    print(__doc__)
