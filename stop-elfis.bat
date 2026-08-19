@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ELFIS — arrêt des services
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\elfis-stop.ps1" %*
exit /b %ERRORLEVEL%
