@echo off
chcp 65001 >nul
echo.
echo === מערכת מכרזים — רוכסר ניהול פרויקטים ===
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set IP=%%a
)
set IP=%IP: =%
echo הקישור למערכת:
echo.
echo   http://%IP%:8000
echo.
echo שלח קישור זה למנהלת המשרד
echo (בתנאי שהמחשב דלוק ו-start.bat פועל)
echo.
pause
