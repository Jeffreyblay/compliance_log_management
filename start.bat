@echo off
title ComplianceLog
color 0A

echo.
echo  ================================
echo   ComplianceLog is starting...
echo  ================================
echo.

:: Install dependencies if needed
echo  Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo  ================================
echo   App is running!
echo.

:: Get local IP address automatically
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%

echo   Open this in your browser:
echo.
echo     This PC:       http://localhost:5000
echo     Your team:     http://%IP%:5000
echo.
echo   Default login:  admin / admin123
echo   (Change this after first login!)
echo.
echo  ================================
echo   Keep this window open.
echo   Close it to stop the app.
echo  ================================
echo.

:: Start the app
python app.py

pause
