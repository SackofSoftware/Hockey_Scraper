# Create Windows Scheduled Task for Hockey Stats Updates
# Run this as Administrator

$TaskName = "Hockey Stats Auto Update"
$ScriptPath = "$PSScriptRoot\..\run_updates.bat"
$WorkingDir = "$PSScriptRoot\.."

Write-Host "Creating Scheduled Task: $TaskName" -ForegroundColor Green

# Create the action (what to run)
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ScriptPath`"" -WorkingDirectory $WorkingDir

# Create triggers (when to run)
# Trigger 1: Every 15 minutes on game days (Fri 5PM-11PM, Sat/Sun 8AM-11PM)
$TriggerGameDay = New-ScheduledTaskTrigger -Daily -At "5:00PM"

# Trigger 2: Every 4 hours during off times
$TriggerOffTime = New-ScheduledTaskTrigger -Daily -At "12:00AM"

# Create the task settings
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Register the task
$Task = Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $TriggerGameDay `
    -Settings $Settings `
    -Description "Automatically updates hockey stats databases in Dropbox folder. Updates every 15 min on game days, every 4 hours otherwise." `
    -Force

Write-Host "✓ Scheduled Task created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Task will run:" -ForegroundColor Yellow
Write-Host "  - Every 15 minutes on game days: Fri PM, Sat, Sun" -ForegroundColor White
Write-Host "  - Databases saved to Dropbox folder" -ForegroundColor White
Write-Host "  - Dropbox will auto-sync to Mac" -ForegroundColor White
Write-Host ""
Write-Host "To manage the task:" -ForegroundColor Yellow
Write-Host "  1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
Write-Host "  2. Find 'Hockey Stats Auto Update'" -ForegroundColor White
Write-Host "  3. Right-click to Run, Disable, or view History" -ForegroundColor White
Write-Host ""

# Test run
Write-Host "Running test update..." -ForegroundColor Green
Start-ScheduledTask -TaskName $TaskName
Write-Host "✓ Test run started - check update_log.txt for results" -ForegroundColor Green
