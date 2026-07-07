@echo off
cd /d "d:\BI"
call venv\Scripts\activate.bat
pip install fastapi uvicorn python-multipart
echo.
echo Backend dependencies installed. Run with: uvicorn backend.main:app --reload --port 8000
pause
