@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ELFIS Developer Launcher V1
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\elfis-launcher.ps1" %*
set EXITCODE=%ERRORLEVEL%
exit /b %EXITCODE%
