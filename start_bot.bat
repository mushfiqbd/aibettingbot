@echo off
REM AI Betting Bot Startup Script for Windows

echo.
echo ================================
echo  AI Betting Telegram Bot
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if requirements are installed
pip show python-telegram-bot >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required packages...
    pip install -r requirements.txt
    echo [OK] Packages installed
)

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo [WARNING] .env file not found!
    echo Please copy env_example.txt to .env and fill in your credentials
    echo.
    pause
    exit /b 1
)

REM Start the bot
echo.
echo [INFO] Starting AI Betting Bot...
echo [INFO] Press Ctrl+C to stop the bot
echo.

python main.py

pause
