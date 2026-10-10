@echo off
REM ====================================================================
REM  AzamGNS3 - Windows Daily Upstream Update Checker
REM  Scans upstream GNS3 remotes and cross-audits for conflicts
REM ====================================================================

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
cd /d "%ROOT_DIR%"

set PYTHON_BIN=python
if exist "venv\Scripts\python.exe" (
    set PYTHON_BIN=venv\Scripts\python.exe
)

echo [!] Checking for upstream updates against official GNS3 remotes...
echo.

"%PYTHON_BIN%" scripts\azamgns3-update-checker.py --generate-patches %*

echo.
echo [!] Check completed. Detailed reports saved in docs\reports\
pause
