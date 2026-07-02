@echo off
cd /d "%~dp0"
set "PATH=C:\Program Files\nodejs;%PATH%"
"C:\Program Files\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port 5173
