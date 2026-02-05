@echo off
echo ========================================================
echo   AUTONOMOUS AGENT - DOCKER LAUNCHER
echo ========================================================
echo.
echo Starting agent in interactive mode...
echo Logs are also being saved to ./logs/
echo.
echo To stop: Press Ctrl+C
echo.

docker compose up --build

echo.
echo Agent stopped.
pause
