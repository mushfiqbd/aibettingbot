#!/bin/bash

# AI Betting Bot Startup Script for Linux/Mac

echo ""
echo "================================"
echo "  AI Betting Telegram Bot"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8+ using:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Mac: brew install python3"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "[OK] Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if requirements are installed
if ! pip show python-telegram-bot &> /dev/null; then
    echo "[INFO] Installing required packages..."
    pip install -r requirements.txt
    echo "[OK] Packages installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "[WARNING] .env file not found!"
    echo "Please copy env_example.txt to .env and fill in your credentials"
    echo ""
    exit 1
fi

# Start the bot
echo ""
echo "[INFO] Starting AI Betting Bot..."
echo "[INFO] Press Ctrl+C to stop the bot"
echo ""

python main.py
