@echo off
echo === הגדרת פרטי כניסה ל-tenders.co.il ===
echo.
set /p PHONE=מספר טלפון (שם משתמש):
set /p PASS=סיסמה:

powershell -Command "(Get-Content 'backend\.env') -replace 'TENDERS_PHONE=.*', 'TENDERS_PHONE=%PHONE%' | Set-Content 'backend\.env'"
powershell -Command "(Get-Content 'backend\.env') -replace 'TENDERS_PASSWORD=.*', 'TENDERS_PASSWORD=%PASS%' | Set-Content 'backend\.env'"

echo.
echo נשמר! עכשיו המערכת יכולה להתחבר ל-tenders.co.il אוטומטית.
pause
