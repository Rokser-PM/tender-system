@echo off
chcp 65001 >nul
echo === מערכת מכרזים — רוכסר ניהול פרויקטים ===
cd /d "%~dp0"

:: Activate venv
call venv\Scripts\activate.bat

:: קבל IP של הרשת
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo  גישה מהמחשב הזה:  http://localhost:8000
echo  גישה מהרשת:       http://%LOCAL_IP%:8000
echo.
echo  שלח את הקישור השני למנהלת המשרד
echo  לעצור: Ctrl+C
echo.

:: פתח דפדפן
start "" "http://localhost:8000"

:: הפעל שרת
cd backend
python main.py
