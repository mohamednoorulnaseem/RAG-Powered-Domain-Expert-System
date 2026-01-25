@echo off
REM ========================================
REM RAG Expert System - Quick Start
REM ========================================

echo.
echo ========================================
echo  RAG Expert System - Starting...
echo ========================================
echo.

REM Kill previous instances by port
echo Stopping previous servers...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
timeout /t 2 /nobreak >nul

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Start API Server
echo Starting API Server on port 8001...
start "RAG API Server" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn api.main:app --host 0.0.0.0 --port 8001"

REM Wait for API to start
timeout /t 3 /nobreak >nul

REM Start Dashboard
echo Starting Dashboard on port 8501...
start "RAG Dashboard" cmd /k "call venv\Scripts\activate.bat && streamlit run dashboard\app.py --server.port 8501"

REM Wait for Dashboard
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo  System Started Successfully!
echo ========================================
echo.
echo  Dashboard:  http://localhost:8501
echo  API:        http://localhost:8001
echo  API Docs:   http://localhost:8001/docs
echo.
echo Opening dashboard...
timeout /t 2 /nobreak >nul
start http://localhost:8501

echo.
pause
