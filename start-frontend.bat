@echo off
cd /d "%~dp0frontend"
echo.
echo  ComptaPilot IA — accessible sur le reseau local
echo  Ouvre depuis un autre appareil: http://VOTRE_IP:5173
echo.
npm run dev -- --host 0.0.0.0 --port 5173
