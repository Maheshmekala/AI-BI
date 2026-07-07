@echo off
title Instant BI Setup
echo ============================================
echo   📊 Instant BI — Setup
echo ============================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [✗] Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo [✓] Python found

:: Create virtual environment
if not exist "venv" (
    echo [..] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [✗] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [✓] Virtual environment created
) else (
    echo [✓] Virtual environment exists
)

:: Activate and install
echo [..] Installing core dependencies (Streamlit, Pandas, Plotly, etc.)
call venv\Scripts\activate.bat

pip install streamlit pandas numpy plotly python-dotenv openpyxl scipy streamlit-option-menu -q

if %errorlevel% neq 0 (
    echo [✗] Install failed. Check your internet connection.
    pause
    exit /b 1
)

echo [✓] Core dependencies installed
echo.
echo ============================================
echo   Setup complete! Run the app with run.bat
echo ============================================
pause
