@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo   ComptaPilot IA — lien reseau local
echo ========================================
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i /c:"IPv4"') do (
  set "ip=%%a"
  set "ip=!ip: =!"
  if not "!ip!"=="" (
    echo   App     : http://!ip!:5173
    echo   API     : http://!ip!:8001
    echo   Docs    : http://!ip!:8001/docs
    echo.
  )
)

echo Partage le lien App avec les appareils du meme Wi-Fi / reseau.
echo Assure-toi que le pare-feu Windows autorise les ports 5173 et 8001.
echo.
pause
