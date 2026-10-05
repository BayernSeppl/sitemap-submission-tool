@echo off
REM Sitemap Submission Tool Start Script (Windows)

echo.
echo ====================================================
echo   Sitemap Submission Tool
echo ====================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python ist nicht installiert oder nicht im PATH.
    echo Bitte Python von https://www.python.org/ herunterladen und installieren.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Erstelle virtuelle Umgebung...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installiere Abhaengigkeiten...
pip install -q -r requirements.txt

REM Start Flask app
echo.
echo ====================================================
echo   Server startet...
echo   Oeffne: http://localhost:5000
echo   Druecke Ctrl+C zum Beenden
echo ====================================================
echo.

python app.py

pause