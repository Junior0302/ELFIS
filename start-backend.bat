@echo off
cd /d "%~dp0backend"
call .venv\Scripts\activate
echo.
echo  ELFIS Core API v0.4 — port 8001
echo  (8000 peut etre occupe par une ancienne version)
echo.
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001
