@echo off
setlocal EnableDelayedExpansion
title Weibo Sentiment - Stop All

set "BACKEND_PORT=5000"
set "FRONTEND_PORT=3001"
set "_KILLED=0"

echo.
echo  [*] Stopping Weibo Sentiment Analysis services...
echo.

echo  Checking backend (:%BACKEND_PORT%)...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
    echo  [OK] Killed backend PID: %%a
    set "_KILLED=1"
)

echo  Checking frontend (:%FRONTEND_PORT%)...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
    echo  [OK] Killed frontend PID: %%a
    set "_KILLED=1"
)

taskkill /FI "WINDOWTITLE eq WeiboBackend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq WeiboFrontend*" /F >nul 2>&1

echo.
if !_KILLED!==0 (
    echo  [*] No running services found
) else (
    echo  [OK] All services stopped
)

endlocal
pause