<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · Epoche E9 · Instanz v6 · „Kaufgebühr einfach buchen“ (Befund 42)

Registriert: 14.10.2026, vor dem Einspielen. Freigabe: Sven, Chat 14.10.2026 („alles tun, was das Projekt voranbringt“, F8).

## Hypothese

v6 bucht die Kaufgebühr bei allen Verkäufen über `exit_monitor` doppelt. In E7 betraf das **alle 136 Runden** mit zusammen 54,78 $ (berichtigt 14.10. nach A5; zuerst „115 von 136, 45,91 $“ – die 21 Signal-Verkäufe buchen die Kaufgebühr ebenfalls doppelt). Mit `filled_cost = amount - fee` (`engine.py:401`, wortgleich mit v7 seit 11.09.) stimmt der gebuchte `pnl` mit der Kasse überein. Lernsystem, Verlustzähler (Patch 54) und Tagesverlust-Modul sehen danach echte Zahlen.

## Änderung

Genau eine: `execution/engine.py:401`. Skript `pruefstand/patches/patch_42_v6_kaufgebuehr_einfach.py`.

## Verhältnis zu E8

E8 (Start 09:18:25 UTC) hat bis zum E9-Start **keine abgeschlossene Runde**. Geprüft wird das direkt vor dem Stopp. Die Messgrößen M1–M3 aus E8 rechnen ohnehin als Kassenrechnung, der Buchungsfix ändert sie nicht. **Ausgewertet wird E8+E9 gemeinsam.** Damit ist auch die Forderung aus `00_LIES_MICH.md` erfüllt, Patch 54 zusammen mit der Korrektur von Befund 42 zu messen.

## Messgrößen und Erfolgskriterien

| # | Messgröße | Vorher (E7) | Erfolg | Entscheidbar ab |
|---|---|---|---|---|
| B1 | gebucht − Kasse je Runde, für Positionen mit Kauf **nach** E9-Start | −Kaufgebühr bei 115/136 | \|Δ\| ≤ 0,01 $ bei **jeder** Runde | erste Runde |
| B2 | Kauf-`amount` im Journal = qty × Kurs | amount = qty × Kurs + Gebühr | Abweichung ≤ 0,01 $ | erster Kauf |
| B3 | gebuchte Kosten je Runde (aus `pnl`) | 0,75 % | ≈ 0,50 % | 10 Runden |

## Abbruch

- Kauf schlägt fehl oder bucht einen falschen Bestand.
- Abweichung bei B1 bei einer Runde, deren Kauf nach dem E9-Start lag.

## Bekannt vorab

Die drei Positionen, die beim Stopp offen sind (BTC 13.10., ETH und SOL 14.10.), tragen ihre doppelte `cost_basis` im `bot_state.json` weiter. Ihr Verkauf wird **noch einmal falsch** gebucht, und zwar um je eine Kaufgebühr (≈ 0,44 / 0,44 / 0,15 $). In der Auswertung werden sie als „Kauf vor E9“ gekennzeichnet, nicht als Fehler.

## Start

- **Eintrag:** `E9_kaufgebuehr_einfach`, Start **2026-10-14T09:35:46.683656+00:00** (11:35 Berlin). Direkt davor geprüft: keine Verkäufe seit E8-Start.
- **Patch:** `engine.py:401` → Zeile 411 `result.filled_cost = amount - fee`. Byte-genau LF erhalten (632 Zeilen, 0 CRLF), Import ok.
- **Nebenbei behoben:** `exit_rules.py` und `cycle_theory.py` von CRLF zurück auf LF (Befund P0-10, alte Patches im Textmodus).
- **Start:** Der erste Start um 11:35 blieb im Fenster stehen (Klick auf STARTEN fehlte, P0-9). Nach `patch_autostart_klick.py` Neustart um 11:48:53, „V6 startet“ um 11:49:37, Port 5050 um 11:49:59, 3 Positionen wiederhergestellt.
- **Doku:** BOT-HANDBUCH 10.11/10.12 berichtigt, 3 Tickets eingelesen. `prozess_frische.py`: aktuell.
