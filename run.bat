@echo off
title Instant BI
setlocal enabledelayedexpansion
echo ============================================
echo        📊 Instant BI — Chat with your data
echo ============================================
echo.

:: Check if virtual env exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [..] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [FAIL] Could not create virtual environment. Make sure Python 3.10+ is installed.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment created
)

:: Pre-install numpy using a pre-built wheel (avoids Meson build requirement on Windows)
echo [..] Installing NumPy...
python -m pip install numpy --only-binary=:all: -q
if errorlevel 1 (
    echo [FAIL] NumPy could not be installed via pre-built wheel.
    echo This is a known issue on Windows.
    echo.
    echo Manually run:  pip install numpy --only-binary :all:
    pause
    exit /b 1
)
echo [OK] NumPy installed

:: Install remaining dependencies
echo [..] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [WARN] Some packages failed to install. Attempting to launch anyway...
) else (
    echo [OK] Dependencies installed
)

:: Create uploads directory
if not exist "uploads" mkdir uploads

:: Verify streamlit is available
where streamlit >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Streamlit not found. Try manually: pip install streamlit
    pause
    exit /b 1
)

:: Launch the app
echo.
echo [OK] Starting Instant BI...
echo      Open http://localhost:8501 in your browser
echo.
streamlit run app.py --server.port 8501 --server.headless true

pause
