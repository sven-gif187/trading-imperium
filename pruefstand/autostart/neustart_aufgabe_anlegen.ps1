# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# Legt die Aufgabe TI-Bots-Neustart an (Entscheidung Sven F5b, 15.10.2026):
# alle 15 min "bots_starten.py --takt" - startet einen ausgefallenen Bot neu,
# laesst Bots mit autostart\<instanz>.BEWUSST_AUS in Ruhe, startet nie doppelt.
# Muster wie TI-Waechter-W4 (Zeit-Ausloeser mit Wiederholung, Dauer 3650 Tage).
# Erneut ausfuehren ist harmlos (-Force ersetzt die Aufgabe).
$ErrorActionPreference = 'Stop'
$py     = 'C:\Users\<BENUTZER>\AppData\Local\Python\pythoncore-3.13-64\pythonw.exe'
$skript = 'C:\Users\<BENUTZER>\Desktop\pruefstand\autostart\bots_starten.py'
$ordner = 'C:\Users\<BENUTZER>\Desktop\pruefstand\autostart'
$nutzer = "$env:USERDOMAIN\$env:USERNAME"

$aktion  = New-ScheduledTaskAction -Execute $py -Argument ('"{0}" --takt' -f $skript) -WorkingDirectory $ordner
$start   = (Get-Date).AddMinutes(2)
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)
# 14 min: bots_starten.py wartet bis zu 10 min auf den Port (v6 braucht beim Start ~4 min)
$einst   = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 14) `
             -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$wer     = New-ScheduledTaskPrincipal -UserId $nutzer -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'TI-Bots-Neustart' -Action $aktion -Trigger $trigger -Settings $einst -Principal $wer `
    -Description 'Pruefstand: startet v6/v7 neu, wenn sie ausgefallen sind (alle 15 min, Sperre BEWUSST_AUS wird beachtet). Entscheidung Sven F5b 15.10.2026.' -Force | Out-Null
$t = Get-ScheduledTask -TaskName 'TI-Bots-Neustart'
$i = $t | Get-ScheduledTaskInfo
'TI-Bots-Neustart: {0} | naechster Lauf {1} | Wiederholung {2} | {3} {4}' -f $t.State, $i.NextRunTime, $t.Triggers[0].Repetition.Interval, $t.Actions[0].Execute, $t.Actions[0].Arguments
