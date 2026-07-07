@echo off
cd /d "d:\BI"
call venv\Scripts\activate.bat
pip install psycopg2-binary pymysql
echo.
echo Done! Restart the app now.
pause
