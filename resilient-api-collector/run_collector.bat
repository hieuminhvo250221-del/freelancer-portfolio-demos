@echo off
setlocal
cd /d "%~dp0"
python -m collector.cli --output output\snapshot.json
if errorlevel 1 (
    echo Collector exited with errors.
    pause
    exit /b 1
)
echo Done. Output saved to output\snapshot.json
pause
