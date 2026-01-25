@echo off
REM ========================================
REM RAG Expert System - Quick Start Script
REM ========================================

echo.
echo  ========================================
echo   RAG Expert System - Setup
echo  ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -r requirements.txt --quiet

REM Check for .env file
if not exist ".env" (
    echo.
    echo [SETUP] Creating .env file from template...
    copy .env.example .env
    echo.
    echo  ========================================
    echo   IMPORTANT: Configure your API key!
    echo  ========================================
    echo.
    echo  Please edit the .env file and add your OpenAI API key:
    echo  OPENAI_API_KEY=your-key-here
    echo.
    echo  Get your key at: https://platform.openai.com/api-keys
    echo.
    notepad .env
)

echo [4/4] Setup complete!
echo.
echo  ========================================
echo   Ready to Start!
echo  ========================================
echo.
echo  Run these commands to start the system:
echo.
echo    1. Start API Server:
echo       python api/main.py
echo.
echo    2. Start Dashboard (new terminal):
echo       streamlit run dashboard/app.py
echo.
echo  Then open: http://localhost:8501
echo.
pause
