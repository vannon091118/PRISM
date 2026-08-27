@echo off
REM User-Inputs Parser - SnipWar Projekt
REM Voraussetzung: Freebuff Desktop laeuft, Python im PATH

set PROJECT=C:\Users\Vannon\Documents\snippet-empire\snip-war
set SCRIPT=%~dp0parse_user_inputs.py
set OUTDIR=%~dp0

echo === User-Inputs Parser ===
echo Projekt: %PROJECT%
echo Output: %OUTDIR%
echo.

python "%SCRIPT%" "%PROJECT%" --html "%OUTDIR%USER_INPUTS_DASHBOARD.html" --output "%OUTDIR%USER_INPUTS_ARTIFACT.md"

echo.
echo Fertig! Oeffne USER_INPUTS_DASHBOARD.html im Browser.
pause
