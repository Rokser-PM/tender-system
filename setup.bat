@echo off
echo === מערכת מכרזים — הגדרת API Keys ===
echo.
cd /d "%~dp0"

echo הגדרת מפתחות API:
echo.
set /p CLAUDE_KEY=Claude API Key (מ-console.anthropic.com):
set /p GMAIL_ADDR=כתובת Gmail:
set /p GMAIL_PASS=Gmail App Password (מ-myaccount.google.com/apppasswords):

echo CLAUDE_API_KEY=%CLAUDE_KEY%> backend\.env
echo GMAIL_ADDRESS=%GMAIL_ADDR%>> backend\.env
echo GMAIL_APP_PASSWORD=%GMAIL_PASS%>> backend\.env

echo.
echo נשמר! עכשיו הרץ start.bat
pause
