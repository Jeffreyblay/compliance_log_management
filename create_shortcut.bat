@echo off
title Creating Desktop Shortcut
echo.
echo  Creating ComplianceLog desktop shortcut...

set "APP_DIR=%~dp0"
set "SHORTCUT=%USERPROFILE%\Desktop\ComplianceLog.lnk"
set "START_BAT=%APP_DIR%start.bat"

:: Write a temporary PowerShell script to disk instead of inline
set "PS_FILE=%TEMP%\make_shortcut.ps1"

echo $ws = New-Object -ComObject WScript.Shell > "%PS_FILE%"
echo $s = $ws.CreateShortcut('%SHORTCUT%') >> "%PS_FILE%"
echo $s.TargetPath = '%START_BAT%' >> "%PS_FILE%"
echo $s.WorkingDirectory = '%APP_DIR%' >> "%PS_FILE%"
echo $s.Description = 'Start ComplianceLog' >> "%PS_FILE%"
echo $s.IconLocation = 'shell32.dll,21' >> "%PS_FILE%"
echo $s.Save() >> "%PS_FILE%"

powershell -ExecutionPolicy Bypass -File "%PS_FILE%"
del "%PS_FILE%"

echo.
echo  Done! A shortcut called "ComplianceLog" is now on your Desktop.
echo  Double-click it every morning to start the app.
echo.
pause
