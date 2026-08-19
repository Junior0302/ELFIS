@echo off
cd /d "%~dp0backend"
call .venv\Scripts\activate
echo.
echo  ELFIS Core API — port 8000
echo  (doit correspondre au proxy Vite /api → 127.0.0.1:8000)
echo.
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
