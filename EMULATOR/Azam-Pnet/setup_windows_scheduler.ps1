# PowerShell Script to register Windows Task Scheduler job for 24-Hour Azam Basha Differential Sync
$TaskName = "AzamBasha-24h-Sync"

# Check Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Registering a scheduled task requires Administrator privileges."
    Write-Host "Please run this script from an elevated PowerShell prompt (Run as Administrator)." -ForegroundColor Yellow
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = $PSScriptRoot }
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }

$ScriptPath = Join-Path $ScriptDir "azambasha_daily_change_sync.py"
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python.exe" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Registering Windows Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Working Directory: $ScriptDir"
Write-Host "Python Executable: $PythonExe"
Write-Host "Target Script:     $ScriptPath"

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`"" -WorkingDirectory "$ScriptDir"
$Trigger = New-ScheduledTaskTrigger -Daily -At 03:00AM
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

# Unregister existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Register new task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Automated 24-hour differential check and download for PNetLab Git source and Codeberg Package API releases." | Out-Null

Write-Host ""
Write-Host "SUCCESS: Task '$TaskName' is registered to run daily at 03:00 AM with Highest Privileges." -ForegroundColor Green

# ------------------------------------------------------------------------------
# Task 2: 3-Months (Quarterly) Codeberg Intelligence Scan & Update Check Plan
# ------------------------------------------------------------------------------
$QuarterlyTaskName = "AzamBasha-Quarterly-Codeberg-Scan"
$WeeklyTaskName = "AzamBasha-Weekly-Codeberg-Scan"
$QuarterlyScriptPath = Join-Path (Join-Path $ScriptDir "scripts") "azambasha-weekly-codeberg-scanner.py"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Registering Windows Scheduled Task: $QuarterlyTaskName" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Script: $QuarterlyScriptPath"

$QuarterlyAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$QuarterlyScriptPath`"" -WorkingDirectory "$ScriptDir"
# Runs quarterly every 3 months at 09:00 AM IST
$QuarterlyTrigger = New-ScheduledTaskTrigger -Once -At "09:00AM" -RepetitionInterval (New-TimeSpan -Days 91)

# Unregister legacy weekly task and previous quarterly task
Unregister-ScheduledTask -TaskName $WeeklyTaskName -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $QuarterlyTaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $QuarterlyTaskName -Action $QuarterlyAction -Trigger $QuarterlyTrigger -Settings $Settings -Principal $Principal -Description "Quarterly 3-month Codeberg issues/PR/release intelligence audit generating docs/3_MONTHS_UPDATE_CHECK_PLAN.md" | Out-Null

Write-Host "SUCCESS: Task '$QuarterlyTaskName' is registered for quarterly execution at 09:00 AM IST." -ForegroundColor Green
Write-Host ""
Write-Host "To test or trigger manually now, run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host "  Start-ScheduledTask -TaskName '$QuarterlyTaskName'" -ForegroundColor White


