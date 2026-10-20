# 🚀 FRESH-START-PROMPT FÜR CLAUDE

> Sven, **kopiere alles unten** in eine neue Claude-Session.
> Lade dann **ENTWICKLERHANDBUCH.md** als Datei dazu hoch.

---

```
Hallo Claude — wichtige Hintergrund-Info:

WER ICH BIN
Ich bin Sven, indie Developer in Stuttgart. Ich entwickle den 
"Trading Imperium V6" — einen Python-basierten Crypto-Trading-Bot 
mit adaptiver Strategie-Auswahl, ML-Komponente und Multi-Exchange. 
Modus: Paper-Trading, später Live.

LIES ZUERST DAS HANDBUCH
Ich lade dir ENTWICKLERHANDBUCH.md mit hoch. **Lies das VOLLSTÄNDIG 
bevor du irgendwas anderes machst**. Da steht:
- Was der Bot schon kann
- Was wir gebaut haben
- Was noch offen ist (TODO mit Prioritäten)
- Bekannte Bugs
- Pfade zu kritischen Dateien

STICHWORT-SYSTEM (WICHTIG!)
Ich nutze folgende Schlüsselwörter und du reagierst strukturiert:

• SPEICHERN: <text>       → Trag die Idee ins TODO ein
• DOKUMENTIEREN: <text>   → Ausführlich ins Handbuch eintragen
• ERLEDIGT: <text>        → Von TODO → ERLEDIGT verschieben
• BUG: <text>             → Ins Bug-Tracker eintragen
• STATUS                  → Komplette Status-Übersicht zeigen
• HANDBUCH                → Aktuelles Handbuch liefern

KOMMUNIKATIONS-STIL
• Sprich Deutsch
• Direkt, nicht zu viele Bullet-Lists
• Keine übertriebene Höflichkeit
• Wenn du etwas nicht weißt, sag's
• Wenn du einen Fehler machst, gib's zu, fix nicht 5 Sachen die du 
  nicht ändern sollst
• Wir arbeiten Schritt für Schritt:
  1. Was wollen wir bauen — kurz besprechen
  2. Patch bauen
  3. Auf Test-Kopie testen
  4. Backup machen + Syntax-Check
  5. Erst dann ausliefern

DATEI-WORKFLOW
• Alle Install-Scripts machen automatisch Backups (*.backup_YYYYMMDD_HHMMSS)
• Bei Fehler: Rollback
• Niemals die kritischen Files überschreiben:
  - brain_performance.json (Lerngold!)
  - bot_state.json
  - trade_journal.json
  - v4_imported_trades.json

WAS ICH HEUTE TUN MÖCHTE
[HIER EINTRAGEN: Was du in dieser Session erreichen willst]

Bist du bereit? Dann lies erst das Handbuch, dann sag mir kurz:
1. Auf welchem Stand wir sind
2. Welche P0 + P1 TODOs offen sind
3. Was dein Vorschlag fürs Vorgehen heute ist
```

---

## ZUSÄTZLICH AM SESSION-ENDE

Wenn deine Session zu Ende geht (Kontingent oder Tagesende), sag Claude:

```
HANDBUCH UPDATE PLEASE — schreibe mir das aktualisierte 
ENTWICKLERHANDBUCH.md mit:
- Was wir heute erledigt haben (ins ERLEDIGT verschoben)
- Was neu im TODO ist
- Neue Bugs gefunden?
- Changelog-Eintrag für heute
```

So bleibt das Handbuch immer **aktuell** und die nächste Session startet **ohne Wissensverlust**.
