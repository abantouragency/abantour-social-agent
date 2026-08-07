@echo off
REM AbanTour Social Agent — Windows launcher
REM 1) install deps once:  python -m pip install -r requirements.txt
REM 2) copy .env.example to .env and fill secrets
REM 3) run:  run_bot.bat
cd /d %~dp0
set PYTHONIOENCODING=utf-8
IF NOT EXIST .env (
  echo [!] .env not found. Copy .env.example to .env and fill secrets.
  pause
  exit /b 1
)
python modules\run_bot.py --schedule
pause
