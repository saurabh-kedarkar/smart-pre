@echo off
echo ===================================================
echo       Starting SmartPre AI Crypto Agent (Local)      
echo ===================================================

cd backend

:: Check if the virtual environment exists
if not exist "venv_win\Scripts\python.exe" (
    echo [ERROR] Virtual environment 'venv_win' not found!
    echo If you haven't set it up, please check the instructions.
    pause
    exit /b
)

:: Run the backend server using the virtual environment's Python
echo [INFO] Starting FastAPI server on http://localhost:8000
.\venv_win\Scripts\python.exe main.py

pause
