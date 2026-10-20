# Mitmachen bei Trading Imperium

Danke, dass du helfen willst. Dieses Projekt hat eine Besonderheit: **Wir glauben nur, was gemessen ist.**
Viele „Verbesserungen“ an Handels-Bots sehen in der Rückrechnung gut aus und verlieren danach Geld.
Deshalb gelten hier ein paar feste Regeln.

## Die Grundregeln

1. **Nur Papierhandel.** Kein Beitrag darf den Echtgeld-Modus einschalten oder voraussetzen.
2. **Keine Regeländerung ohne Vorab-Plan.** Wer das Handelsverhalten ändern will (Kauf, Verkauf,
   Positionsgröße, Kosten, Marktlage), schreibt zuerst eine **Vorab-Registrierung**
   (Vorlage: Dateien in `pruefstand/epochen/`):
   - Hypothese: was soll sich ändern und warum (mit Daten)
   - Messgrößen und **Erfolgskriterien**, bevor es Ergebnisse gibt
   - wie viele Runden es für ein Urteil braucht
   - wann abgebrochen oder zurückgenommen wird
3. **Jede Verhaltensänderung bekommt eine Epochengrenze** (`config_epochs.json`, `epochs.py add_epoch`).
   Runden vor und nach der Änderung werden nie zusammengerechnet.
4. **Kassenrechnung zählt.** Ergebnisse werden aus dem Handelsjournal als Geldfluss gerechnet
   (`pruefstand/skripte/runden_lib.py`), nicht aus gebuchten oder angezeigten Werten.
5. **Keine Optimierung auf den besten Rückrechnungswert.** Wer 20 Varianten testet und die beste zeigt,
   zeigt Zufall. Varianten vorher festlegen, Mehrfachtests korrigieren, Vertrauensbereiche angeben.
6. **Konfidenz mit Prozent.** Aussagen tragen eine Einschätzung wie `[SICHER 90 %]`,
   `[WAHRSCHEINLICH 70 %]` oder `[VERMUTUNG 55 %]`.
7. **Handbuch und Chronik pflegen.** Jede Änderung bekommt einen Abschnitt in `BOT-HANDBUCH.md` des Bots.
8. **Zeilenenden erhalten.** Manche Dateien sind CRLF, manche LF – nicht ungewollt umstellen.
9. **v6, v7 und Labor nie vermischen.** Zahlen immer getrennt je Instanz.

## Wie du beiträgst

- **Fehler melden:** Issue mit Fundstelle (`datei.py:zeile`), was passiert, was erwartet war, wie man es nachstellt.
- **Nachrechnen:** Issue oder Pull Request mit eigenem Skript und Ergebnis – Abweichungen sind wertvoll.
- **Code ändern:** Pull Request, klein und einzeln („eine Änderung je Schritt“), mit Test.
  Bei Verhaltensänderungen gehört die Vorab-Registrierung in denselben Pull Request.
- **Ideen:** Issue mit dem Label „Idee“ und einem Messplan.

## Was nicht ins Repo gehört

`.env`, API-Schlüssel, Tokens, Telegram-Kennungen, persönliche Daten, Handelsjournale, Datenbanken, Logs,
Code, der nicht von dir stammt oder für den du keine Erlaubnis hast. Siehe `SECURITY.md`.

## Lizenz

Mit deinem Beitrag stimmst du zu, dass er unter der **GPL-3.0** steht.
