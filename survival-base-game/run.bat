@echo off
cd /d "%~dp0"
echo Installing pygame if needed...
python -m pip install pygame -q
echo Starting game...
python main.py
if errorlevel 1 (
    echo.
    echo ERROR: python not found. Install Python 3.12 from python.org
    pause
)
