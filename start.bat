@echo off
echo Starting Countdown Party...
python server.py
if errorlevel 1 (
    echo Trying 'py' command instead...
    py server.py
)
pause
