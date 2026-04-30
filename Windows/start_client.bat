@echo off
setlocal
cd /d "%~dp0"
python scripts\start_client.py %*
if errorlevel 1 pause
