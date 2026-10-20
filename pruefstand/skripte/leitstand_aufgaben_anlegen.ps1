# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# Legt die Windows-Aufgaben fuer den headless Leitstand an (Phase 6).
# Muster wie TI-Waechter-W6W7: pythonw.exe, Nachstarten wenn verpasst, 4 Wiederholungen alle 15 min.
# Erneut ausfuehren ist harmlos (-Force ersetzt die Aufgabe).
$ErrorActionPreference = 'Stop'
$py     = 'C:\Users\<BENUTZER>\AppData\Local\Python\pythoncore-3.13-64\pythonw.exe'
$skript = 'C:\Users\<BENUTZER>\Desktop\pruefstand\skripte\leitstand_lauf.py'
$ordner = 'C:\Users\<BENUTZER>\Desktop\pruefstand\skripte'
$nutzer = "$env:USERDOMAIN\$env:USERNAME"

$aufgaben = @(
    @{ Name = 'TI-Leitstand-Tag';   Art = 'tag';   Trigger = (New-ScheduledTaskTrigger -Daily -At '07:30');
       Limit = (New-TimeSpan -Hours 1);   Text = 'Pruefstand: Leitstand-Tagespruefung headless (claude -p --agent leitstand), Bericht nach pruefstand\berichte, Kurzfassung per Telegram' },
    @{ Name = 'TI-Leitstand-Woche'; Art = 'woche'; Trigger = (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '10:00');
       Limit = (New-TimeSpan -Hours 3);   Text = 'Pruefstand: Leitstand-Wochenpruefung (Deep Audit) headless, Bericht nach pruefstand\berichte, Kurzfassung per Telegram' }
)

foreach ($a in $aufgaben) {
    # Pfad mit Leerzeichen: Skriptpfad in doppelten Anfuehrungszeichen im Argument
    $aktion = New-ScheduledTaskAction -Execute $py -Argument ('"{0}" {1}' -f $skript, $a.Art) -WorkingDirectory $ordner
    $einst  = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 4 -RestartInterval (New-TimeSpan -Minutes 15) `
                -ExecutionTimeLimit $a.Limit -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $wer    = New-ScheduledTaskPrincipal -UserId $nutzer -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $a.Name -Action $aktion -Trigger $a.Trigger -Settings $einst -Principal $wer `
        -Description $a.Text -Force | Out-Null
    $t = Get-ScheduledTask -TaskName $a.Name
    $i = $t | Get-ScheduledTaskInfo
    '{0}: {1} | naechster Lauf {2} | {3} {4}' -f $a.Name, $t.State, $i.NextRunTime, $t.Actions[0].Execute, $t.Actions[0].Arguments
}
