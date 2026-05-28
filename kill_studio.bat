@echo off
cd /d "%~dp0"
if not exist studio.pid (
    echo Studio not running.
    goto end
)
set /p PID=<studio.pid
taskkill /f /pid %PID% >nul 2>&1
del studio.pid >nul 2>&1
echo Studio stopped ^(PID %PID%^).
:end
