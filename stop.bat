@echo off
title Stopping ComplianceLog
color 0C

echo.
echo  Stopping ComplianceLog...
echo.

:: Kill any Python process running app.py
taskkill /F /FI "WINDOWTITLE eq ComplianceLog" /T >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

echo  ComplianceLog has been stopped.
echo.
timeout /t 2 >nul
