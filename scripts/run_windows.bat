@echo off
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe python -m venv .venv
call .venv\Scriptsctivate.bat
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo Configure o DATABASE_URL e SECRET_KEY no arquivo .env antes de iniciar.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
