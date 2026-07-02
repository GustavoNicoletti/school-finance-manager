@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\homologacao_local.ps1" %*
