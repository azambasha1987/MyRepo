<#
.SYNOPSIS
    AzamLabs Windows 1-Click SecureCRT Protocol Integrator & Tab-Naming Wrapper
.DESCRIPTION
    Registers the 'telnet://' URL protocol handler in the Windows Registry to route
    through a smart SecureCRT launcher.
    Supports standard 'telnet://<host>:<port>' as well as AzamLabs sequenced format
    'telnet://<host>:<port>#<node_name>'.
    Ensures SecureCRT opens sessions in new tabs (/T) with clean device titles (/N "<node_name>"),
    preventing scrambled tabs and raw port names.
#>

param (
    [switch]$Uninstall
)

# Elevate to Admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsPrincipalScope]::Administrator)
if (-not $isAdmin) {
    Write-Host "[*] Requesting Administrator privileges to register SecureCRT Protocol Handler..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

$InstallDir = "$env:ProgramData\AzamLabs"
$SecureCRTWrapper = "$InstallDir\azamlabs-securecrt.bat"

if ($Uninstall) {
    Write-Host "Uninstalling AzamLabs SecureCRT Protocol Handler..." -ForegroundColor Yellow
    Remove-Item -Path "HKCR:\telnet" -Recurse -ErrorAction SilentlyContinue
    if (Test-Path $SecureCRTWrapper) {
        Remove-Item -Path $SecureCRTWrapper -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] AzamLabs SecureCRT handler removed. Standard Windows telnet restored." -ForegroundColor Green
    exit 0
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   AzamLabs 1-Click SecureCRT Sequenced Protocol Integrator  " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Locate SecureCRT.exe
$SecureCRTPaths = @(
    "C:\Program Files\VanDyke Software\SecureCRT\SecureCRT.exe",
    "C:\Program Files (x86)\VanDyke Software\SecureCRT\SecureCRT.exe",
    "$env:LOCALAPPDATA\Programs\VanDyke Software\SecureCRT\SecureCRT.exe",
    "$env:ProgramFiles\VanDyke Software\SecureCRT\SecureCRT.exe"
)

$FoundSecureCRT = ""
foreach ($path in $SecureCRTPaths) {
    if (Test-Path $path) {
        $FoundSecureCRT = $path
        break
    }
}

if (-not $FoundSecureCRT) {
    Write-Warning "SecureCRT.exe was not found in standard default paths."
    $inputPath = Read-Host "Please enter full path to SecureCRT.exe (e.g. C:\Tools\SecureCRT.exe)"
    if ($inputPath -and (Test-Path $inputPath)) {
        $FoundSecureCRT = $inputPath
    } else {
        $FoundSecureCRT = "C:\Program Files\VanDyke Software\SecureCRT\SecureCRT.exe"
    }
}

Write-Host "[1/3] SecureCRT Executable: $FoundSecureCRT" -ForegroundColor Green

# 2. Create Smart Wrapper Batch Script
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$BatchContent = @"
@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: AzamLabs SecureCRT Sequenced Launcher & Session Naming Stub
:: Input: telnet://<HOST>:<PORT>#<DEVICE_NAME> or telnet://<HOST>:<PORT>
:: ============================================================
set "RAW_URL=%~1"
set "RAW_URL=!RAW_URL:telnet://=!"
set "RAW_URL=!RAW_URL:/=!"

:: Check if fragment (#DEVICE_NAME) exists
set "NAME="
for /f "tokens=1,2 delims=#" %%A in ("!RAW_URL!") do (
    set "HOST_PORT=%%A"
    set "NAME=%%B"
)

:: Split Host and Port
for /f "tokens=1,2 delims=:" %%H in ("!HOST_PORT!") do (
    set "HOST=%%H"
    set "PORT=%%I"
)

if "!PORT!"=="" set "PORT=23"

:: Launch SecureCRT with /T (New Tab) and /N (Session/Tab Name)
if not "!NAME!"=="" (
    start "" "$FoundSecureCRT" /T /N "!NAME!" /TELNET !HOST! !PORT!
) else (
    start "" "$FoundSecureCRT" /T /TELNET !HOST! !PORT!
)
"@

Set-Content -Path $SecureCRTWrapper -Value $BatchContent -Encoding ASCII
Write-Host "[2/3] SecureCRT Launcher Wrapper Created: $SecureCRTWrapper" -ForegroundColor Green

# 3. Register 'telnet://' in Windows Registry
Write-Host "[3/3] Registering Windows 'telnet://' Protocol Handler for SecureCRT..." -ForegroundColor Yellow

$regPath = "Registry::HKEY_CLASSES_ROOT\telnet"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "(default)" -Value "URL:Telnet Protocol (AzamLabs SecureCRT)" | Out-Null
Set-ItemProperty -Path $regPath -Name "URL Protocol" -Value "" | Out-Null

$cmdPath = "$regPath\shell\open\command"
New-Item -Path $cmdPath -Force | Out-Null
Set-ItemProperty -Path $cmdPath -Name "(default)" -Value "`"$SecureCRTWrapper`" `"%1`"" | Out-Null

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  [SUCCESS] 1-Click SecureCRT Protocol Registered on Windows! " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Clicking 'Sequenced Console' in AzamLabs will now automatically"
Write-Host " dock sessions into ordered SecureCRT tabs with device titles!"
Write-Host "============================================================" -ForegroundColor Cyan
