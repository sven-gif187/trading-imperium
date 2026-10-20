# Sicherheit

## Niemals committen

- `.env` und jede Datei mit API-Schlüsseln, Secrets, Tokens oder Passwörtern
- Telegram-Bot-Token und Chat-IDs
- Börsen-Schlüssel – und wenn du je echte Schlüssel nutzt: **nur Leserechte, niemals Auszahlungsrechte**
- Handelsjournale, Datenbanken (`data_store/`), Logs

Die `.gitignore` schließt das aus. Prüfe vor jedem Push trotzdem `git status` und `git diff --staged`.

## Wenn doch etwas durchrutscht

Ein einmal veröffentlichter Schlüssel gilt als verbrannt: **sofort beim Anbieter widerrufen** und neu erzeugen.
Das Löschen aus dem Repo reicht nicht, die Git-Geschichte und Kopien behalten ihn.

## Sicherheitslücken melden

Bitte **kein öffentliches Issue** für Lücken, die Geld oder Schlüssel gefährden könnten. Schreib stattdessen eine
Direktnachricht an den Projektbetreuer (GitHub: sven-gif187, TikTok: @make.a.better_world).

## Echtgeld

Das Projekt ist für **Papierhandel** gebaut. Der Echtgeld-Modus ist nicht freigegeben und nicht dafür geprüft.
