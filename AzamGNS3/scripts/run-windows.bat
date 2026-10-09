@echo off
REM ====================================================================
REM  AzamGNS3 - Windows Quick-Start Launcher
REM  Launches the zero-install web server locally
REM ====================================================================

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
cd /d "%ROOT_DIR%"

if not exist "venv\Scripts\python.exe" (
    echo [-] Virtual environment not found. Creating venv...
    python -m venv venv
    venv\Scripts\python.exe -m pip install -r gns3-server\requirements.txt
    venv\Scripts\python.exe -m pip install -r gns3-server\win-requirements.txt
    venv\Scripts\python.exe -m pip install -e gns3-server
)

echo [!] Starting AzamGNS3 Web Server on http://localhost:3080...
echo [!] Open your browser and navigate to: http://localhost:3080/
echo.

venv\Scripts\gns3server.exe --host 0.0.0.0 --port 3080 --local
