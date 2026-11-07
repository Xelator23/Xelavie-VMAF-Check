@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vmaf-check.ps1" %*
exit /b %errorlevel%
