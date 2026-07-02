@echo off
cd /d "%~dp0"
".venv-local\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> server.log 2>> server.err.log
