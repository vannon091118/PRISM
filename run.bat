@echo off
REM PRISM — Platform Recognition & Input Session Miner
REM Scannt alle Plattformen und generiert Dashboard

set SCRIPT=%~dp0parse_user_inputs.py
set OUTDIR=%~dp0

echo === PRISM Dashboard Generator ===
echo.

REM Scan all platforms and generate dashboard
python "%SCRIPT%" --scan --output "%OUTDIR%docs\screenshots\dashboard_data.json"

REM Generate interactive dashboard HTML
python -m parse_user_inputs.renderers.generate_dashboard

echo.
echo Fertig! Oeffne DASHBOARD.html im Browser.
pause
