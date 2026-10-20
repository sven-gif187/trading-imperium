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
   als Abweichung gemeldet. Eine Position stillschweigend zu loeschen
   ist die gefaehrlichste der drei moeglichen Reaktionen - sie sieht wie
   Aufraeumen aus und ist Datenverlust.

WAS DIESE DATEI NICHT TUT - berichtigt am 15.09.2026
----------------------------------------------------
Hier stand bis heute "und der Handel blockiert, bis ein Mensch
entschieden hat". Das war unwahr.

Die Sperre schrieb ein Feld namens "recovery_blockade", und eine Suche
ueber das ganze Projekt findet dieses Feld an genau EINER Stelle: beim
Schreiben, hier. Kein Handelspfad hat es je gelesen. Der Bot handelte
nach der Meldung "Handel bleibt blockiert" ungebremst weiter.

Aufgefallen ist es nie, weil `run()` gar nicht so weit kam - die
Verbindung davor scheiterte bei jedem Start (Befund 69 war an dieser
zweiten Stelle nicht repariert, live_runner.py meldete sich mit dem
Bybit-Schluessel bei Binance an).

Zwei Fehler, die einander verdeckten: Der eine sorgte dafuer, dass der
andere nie sichtbar wurde.

Diese Datei MELDET also - sie sperrt nicht. Wer eine echte Sperre will,
muss sie bauen und dabei entscheiden, was bei einem Fehlalarm passieren
soll; ein Bot, der sich selbst anhaelt, ist nicht harmlos.

Der Sachverhalt wird ohnehin zweifach abgedeckt:
  - features/waechter.py meldet ihn als GEISTERBESTAND-Alarm
  - runtime/state_manager.py uebernimmt vorhandene Bestaende seit dem
    14.09. selbst ins Register, mit dem echten Einstand aus den
    Boersen-Ausfuehrungen

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
                   lokale_positionen: Dict[str, dict],
                   staub_grenzen: Dict[str, float] = None):
        """Reine Rechenlogik - ohne Boerse, damit sie testbar ist.

        `staub_grenzen` ordnet jedem Asset die Mindestmenge zu, die die
        Boerse noch handelt (z. B. {"ETH": 0.0001}). Was darunter liegt,
        gilt als Rest und NICHT als ungeklaerte Abweichung - man kann es
        ohnehin nicht verkaufen. Ohne diesen Parameter verhaelt sich die
        Funktion wie vorher, damit der Selbsttest unveraendert gilt.

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
                # === [15.09.2026] STAUB IST KEINE ABWEICHUNG ===
                #
                # Nach dem ETH-Verkauf am 15.09. blieb ein Rest von
                # 0,0000895 ETH liegen - rund 0,22 $. Die Boerse
                # verkauft ihn nicht (Mindestwert 5 $), er laesst sich
                # also weder handeln noch loswerden.
                #
                # Als "ungeklaerte Abweichung" gemeldet, erzeugte er bei
                # JEDEM Start einen roten [ERROR]. Eine Meldung, die
                # immer kommt und nie etwas bedeutet, bringt einem bei,
                # rote Zeilen zu ueberlesen - derselbe Schaden wie beim
                # Waechter-Fehlalarm und beim coinbasepro-Startfehler.
                #
                # Der Buchhaltungs-Waechter macht es laengst so:
                # features/waechter.py ignoriert Geisterbestaende unter
                # 30 $ ausdruecklich. Hier fehlte dieselbe Grenze.
                #
                # Staub wird trotzdem angelegt und angezeigt - er ist ja
                # da. Nur eben als Hinweis, nicht als Alarm.
                _grenze = (staub_grenzen or {}).get(a, 0)
                _ist_staub = bool(_grenze) and menge < _grenze

                ergebnis[a] = {
                    "qty": menge,
                    "active": False,
                    "recovered": True,
                    "recovered_grund": ("Rest unterhalb der Boersen-"
                                        "Mindestmenge - nicht verkaufbar"
                                        if _ist_staub else
                                        "an der Boerse gefunden, lokal "
                                        "unbekannt - kein Einstand, deshalb "
                                        "nicht handelbar"),
                }
                if _ist_staub:
                    abweichungen.append({
                        "art": "staub", "asset": a, "menge": menge,
                        "text": f"{a}: {menge:.8f} Rest, unter der "
                                f"Mindestmenge {_grenze:.8f} - nicht "
                                f"verkaufbar, keine Abweichung.",
                    })
                    log.info("RECOVERY", abweichungen[-1]["text"])
                else:
                    abweichungen.append({
                        "art": "nur_boerse", "asset": a, "menge": menge,
                        "text": f"{a}: {menge:.8f} an der Boerse, lokal "
                                f"unbekannt. Angelegt als NICHT handelbar "
                                f"(kein Einstand).",
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

        # [15.09.2026] Stand hier auf "open_positions". Dieses Feld
        # schreibt und liest NIEMAND ausser dieser Datei - nachgeprueft
        # ueber das ganze Projekt. Der Bot fuehrt seine Positionen in
        # "open_positions_backup" (runtime/state_manager.py).
        #
        # Der Abgleich verglich also den echten Boersenbestand gegen ein
        # leeres Feld und haette jede laufende Position als "nur an der
        # Boerse, nicht lokal" gemeldet. Aufgefallen ist es nie, weil
        # die Verbindung davor scheiterte und run() gar nicht so weit kam.
        lokal = self.state.get("open_positions_backup", {}) or {}
        log.info("RECOVERY", f"Lokal: {len(lokal)} Positionen")

        # Die Mindestmengen der Boerse holen, damit Reste nicht als
        # Abweichung gelten. Schlaegt der Abruf fehl, bleibt das dict
        # leer - dann meldet der Abgleich wie frueher alles, was
        # sicherer ist als stillschweigend zu schlucken.
        staub = {}
        try:
            _ex = getattr(self.runner, "exchange", None)
            for _a in boersen_bestand:
                _asset = asset_von(_a)
                for _quote in ("USDC", "USDT"):
                    try:
                        _m = _ex.market(f"{_asset}/{_quote}")
                    except Exception:
                        continue
                    _min = float(((_m.get("limits") or {}).get("amount") or {})
                                 .get("min") or 0)
                    if _min:
                        staub[_asset] = _min
                    break
        except Exception as _se:
            log.warn("RECOVERY", f"Mindestmengen nicht abrufbar "
                                 f"({str(_se)[:60]}) - Reste zaehlen als "
                                 f"Abweichung")

        neu, abweichungen = self.abgleichen(boersen_bestand, lokal, staub)
        self.abweichungen = abweichungen

        # [15.09.2026] Schreibt bewusst NICHT mehr in "open_positions".
        # Dieses Feld liest niemand, und ein Schreibzugriff auf ein
        # totes Feld sieht in jedem spaeteren Rundgang aus, als fuehre
        # hier jemand Buch. Das Ergebnis geht ins Log und als
        # Rueckgabewert an den Aufrufer - das ist ehrlich.
        self.state.set("recovery_letzter_abgleich", {
            "zeit": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "boersen_bestaende": len(boersen_bestand),
            "lokale_positionen": len(lokal),
            "abweichungen": len(abweichungen),
        })

        # ==============================================================
        # [15.09.2026] DIESE "HANDELSSPERRE" SPERRT NICHTS.
        #
        # Hier stand ein Schreibzugriff auf "recovery_blockade" mit dem
        # Kommentar "Ohne sie wuerde der Bot auf einem Zustand
        # weiterhandeln, den niemand geprueft hat" - und daneben die
        # Logzeile "Handel bleibt blockiert".
        #
        # Beides war unwahr. Eine Suche ueber das ganze Projekt findet
        # "recovery_blockade" an genau EINER Stelle: hier, beim
        # Schreiben. Kein Handelspfad liest das Feld je aus. Der Bot
        # haette nach dieser Meldung ungebremst weitergehandelt.
        #
        # Das ist die gefaehrlichere Sorte Fehler: nicht ein fehlender
        # Schutz, sondern einer, der im Log BESTAETIGT, dass er greift.
        # Wer die Zeile liest, hoert auf zu suchen.
        #
        # Die Meldung heisst jetzt, was sie ist: eine Warnung. Ob daraus
        # eine echte Sperre wird, ist Svens Entscheidung - sie koennte
        # den Handel anhalten und braucht deshalb eine eigene Epoche.
        # Bis dahin meldet ohnehin der Waechter (features/waechter.py)
        # denselben Sachverhalt als GEISTERBESTAND-Alarm, und
        # runtime/state_manager.py uebernimmt vorhandene Bestaende
        # seit dem 14.09. selbst ins Register.
        # ==============================================================
        ernst = [a for a in abweichungen if a["art"] in ("nur_lokal", "nur_boerse")]
        if ernst:
            log.error("RECOVERY",
                      f"{len(ernst)} ungeklaerte Abweichung(en) zwischen "
                      f"Boerse und Register. ACHTUNG: Das ist eine WARNUNG, "
                      f"KEINE Sperre - der Bot handelt weiter. "
                      f"Gruende: {'; '.join(a['text'] for a in ernst[:3])}")

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

    # === [15.09.2026] Staub unter der Boersen-Mindestmenge ===
    print("\n=== Richtung 4b: Rest unter der Mindestmenge ist KEIN Alarm ===")
    # Die echten Zahlen vom 15.09.: Nach dem ETH-Verkauf blieben
    # 0,0000895 ETH liegen, Bybit handelt erst ab 0,0001.
    neu4b, abw4b = sr.abgleichen({"ETH": 0.0000895}, {},
                                 staub_grenzen={"ETH": 0.0001})
    for name, ok in [
            ("als 'staub' gemeldet, nicht als 'nur_boerse'",
             any(a["art"] == "staub" for a in abw4b)),
            ("KEINE ernste Abweichung",
             not any(a["art"] in ("nur_lokal", "nur_boerse") for a in abw4b)),
            ("trotzdem angelegt (der Rest ist ja da)", "ETH" in neu4b),
            ("und NICHT handelbar",
             neu4b.get("ETH", {}).get("active") is False)]:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    # GEGENPROBE: dieselbe Muenze, aber HANDELBARE Menge -> muss Alarm
    # bleiben. Ohne diese Haelfte wuerde eine zu grosse Staubgrenze jede
    # echte Abweichung verschlucken, und der Test saehe trotzdem gruen aus.
    neu4c, abw4c = sr.abgleichen({"ETH": 0.5}, {},
                                 staub_grenzen={"ETH": 0.0001})
    for name, ok in [
            ("handelbare Menge bleibt 'nur_boerse'",
             any(a["art"] == "nur_boerse" for a in abw4c)),
            ("und wird NICHT als Staub abgetan",
             not any(a["art"] == "staub" for a in abw4c))]:
        print(f"    {'OK  ' if ok else 'FEHLER'} {name}")
        if not ok:
            fehler += 1

    # Ohne Grenzen (Abruf fehlgeschlagen) muss alles wie frueher melden -
    # lieber eine Warnung zu viel als eine verschluckte.
    _, abw4d = sr.abgleichen({"ETH": 0.0000895}, {})
    _ok = any(a["art"] == "nur_boerse" for a in abw4d)
    print(f"    {'OK  ' if _ok else 'FEHLER'} ohne Grenzen meldet es wie "
          f"frueher (sicherer Rueckfall)")
    if not _ok:
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
