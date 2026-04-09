@echo off
setlocal EnableDelayedExpansion
title Weibo Sentiment Analysis - Launcher
color 0F

:: ================================================================
::  Configuration  (edit ports / paths here only)
:: ================================================================
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend-python"
set "FRONTEND_DIR=%ROOT%web-frontend"
set "BACKEND_ENTRY=run_server.py"
set "BACKEND_PORT=5000"
set "FRONTEND_PORT=3001"

:: ================================================================
::  Main Menu
:: ================================================================
:MENU
cls
echo.
echo  ============================================================
echo     Weibo Sentiment Analysis System
echo     Author: Luo Sen  ^|  ID: 2022407443
echo  ============================================================
echo.
echo     [1]  Start All Services   (Backend + Frontend)
echo     [2]  Start Backend Only   (Flask :%BACKEND_PORT%)
echo     [3]  Start Frontend Only  (Vite  :%FRONTEND_PORT%)
echo     [4]  Stop All Services
echo     [5]  Service Status
echo     [6]  Install / Update Deps
echo     [0]  Exit
echo.
set /p choice="  Select [0-6]: "

if "%choice%"=="1" goto START_ALL
if "%choice%"=="2" goto START_BACKEND
if "%choice%"=="3" goto START_FRONTEND
if "%choice%"=="4" goto STOP_ALL
if "%choice%"=="5" goto STATUS
if "%choice%"=="6" goto INSTALL_DEPS
if "%choice%"=="0" goto EXIT
echo.
echo  [~] Invalid choice, try again
timeout /t 1 /nobreak >nul
goto MENU

:: ================================================================
::  Environment Check
:: ================================================================
:CHECK_ENV
echo.
echo  [*] Checking environment...

:: Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Python not found. Please install Python 3.8+
    goto CHECK_ENV_FAIL
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo  [OK] Python %PY_VER%

:: Node
node --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Node.js not found. Please install Node.js 16+
    goto CHECK_ENV_FAIL
)
for /f "delims=" %%v in ('node --version 2^>^&1') do set "NODE_VER=%%v"
echo  [OK] Node.js %NODE_VER%

:: Backend entry
if not exist "%BACKEND_DIR%\%BACKEND_ENTRY%" (
    echo  [X] Backend entry not found: %BACKEND_DIR%\%BACKEND_ENTRY%
    goto CHECK_ENV_FAIL
)
echo  [OK] Backend entry: %BACKEND_ENTRY%

:: Frontend package.json
if not exist "%FRONTEND_DIR%\package.json" (
    echo  [X] Frontend package.json not found: %FRONTEND_DIR%
    goto CHECK_ENV_FAIL
)
echo  [OK] Frontend package.json

:: node_modules
if not exist "%FRONTEND_DIR%\node_modules" (
    echo  [~] node_modules missing, running npm install ...
    cd /d "%FRONTEND_DIR%"
    call npm install
    if errorlevel 1 (
        echo  [X] npm install failed
        goto CHECK_ENV_FAIL
    )
    echo  [OK] Frontend deps installed
)

:: .env
if not exist "%ROOT%.env" (
    if exist "%ROOT%.env.example" (
        echo  [~] .env missing, copying from .env.example
        copy "%ROOT%.env.example" "%ROOT%.env" >nul
    )
)

goto :eof

:CHECK_ENV_FAIL
echo.
echo  Environment check failed. Press any key to return to menu...
pause >nul
goto MENU

:: ================================================================
::  Port Conflict Check
:: ================================================================
:CHECK_PORT
set "_PORT=%~1"
set "_LABEL=%~2"
set "_CONFLICT=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%_PORT% " ^| findstr "LISTENING"') do set "_CONFLICT=1"
if "!_CONFLICT!"=="0" goto :eof
echo  [~] Port %_PORT% is occupied (%_LABEL%)
set /p _KC="      Kill occupying process? [Y/N]: "
if /i "!_KC!"=="Y" (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%_PORT% " ^| findstr "LISTENING"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    echo  [OK] Port %_PORT% freed
    timeout /t 1 /nobreak >nul
) else (
    echo  [~] Skipped, service may fail to start
)
goto :eof

:: ================================================================
::  Start Backend
:: ================================================================
:START_BACKEND
call :CHECK_ENV
echo.
echo  [1/2] Checking backend port...
call :CHECK_PORT %BACKEND_PORT% "Flask Backend"

echo  [2/2] Starting Flask backend...
cd /d "%BACKEND_DIR%"
start "WeiboBackend" cmd /k "title WeiboBackend Flask :%BACKEND_PORT% && python %BACKEND_ENTRY%"

echo.
echo  ----------------------------------------------------------
echo   Backend started: http://localhost:%BACKEND_PORT%
echo  ----------------------------------------------------------
echo.
if "%~1"=="silent" goto :eof
pause
goto MENU

:: ================================================================
::  Start Frontend
:: ================================================================
:START_FRONTEND
if not "%~1"=="silent" call :CHECK_ENV
echo.
echo  [1/2] Checking frontend port...
call :CHECK_PORT %FRONTEND_PORT% "Vite Frontend"

echo  [2/2] Starting Vite frontend...
cd /d "%FRONTEND_DIR%"
start "WeiboFrontend" cmd /k "title WeiboFrontend Vite :%FRONTEND_PORT% && npm run dev"

echo.
echo  ----------------------------------------------------------
echo   Frontend started: http://localhost:%FRONTEND_PORT%
echo  ----------------------------------------------------------
echo.
if "%~1"=="silent" goto :eof
pause
goto MENU

:: ================================================================
::  Start All
:: ================================================================
:START_ALL
call :CHECK_ENV
echo.
echo  ============================================================
echo   [1/4] Checking ports...
echo  ============================================================
call :CHECK_PORT %BACKEND_PORT% "Flask Backend"
call :CHECK_PORT %FRONTEND_PORT% "Vite Frontend"

echo.
echo  ============================================================
echo   [2/4] Starting Backend (Flask :%BACKEND_PORT%)...
echo  ============================================================
cd /d "%BACKEND_DIR%"
start "WeiboBackend" cmd /k "title WeiboBackend Flask :%BACKEND_PORT% && python %BACKEND_ENTRY%"

echo.
echo  ============================================================
echo   [3/4] Waiting for backend...
echo  ============================================================
set "_READY=0"
for /L %%i in (1,1,10) do (
    if !_READY!==0 (
        timeout /t 1 /nobreak >nul
        netstat -ano 2>nul | findstr ":%BACKEND_PORT% " | findstr "LISTENING" >nul 2>&1
        if not errorlevel 1 (
            set "_READY=1"
            echo  [OK] Backend is ready
        ) else (
            <nul set /p=". "
        )
    )
)
if !_READY!==0 (
    echo.
    echo  [~] Backend not responding in 10s, starting frontend anyway...
)

echo.
echo  ============================================================
echo   [4/4] Starting Frontend (Vite :%FRONTEND_PORT%)...
echo  ============================================================
cd /d "%FRONTEND_DIR%"
start "WeiboFrontend" cmd /k "title WeiboFrontend Vite :%FRONTEND_PORT% && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo  ============================================================
echo   All services started
echo  ============================================================
echo.
echo   Backend API :  http://localhost:%BACKEND_PORT%
echo   Frontend UI :  http://localhost:%FRONTEND_PORT%
echo.
echo   Modules:
echo     /collection        Data Collection
echo     /preprocess        Data Preprocessing
echo     /analysis          Sentiment Analysis
echo     /dual-dimension    Dual-Dimension Ranking
echo     /monitor           Real-time Monitor
echo     /pipeline          Pipeline Manager
echo     /visualization     Visualization Dashboard
echo     /admin             System Admin
echo.
echo  Press any key to open browser...
pause >nul
start http://localhost:%FRONTEND_PORT%
goto MENU

:: ================================================================
::  Stop All
:: ================================================================
:STOP_ALL
echo.
echo  [*] Stopping services...

set "_KILLED=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
    echo  [OK] Killed backend PID: %%a
    set "_KILLED=1"
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
    echo  [OK] Killed frontend PID: %%a
    set "_KILLED=1"
)
taskkill /FI "WINDOWTITLE eq WeiboBackend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq WeiboFrontend*" /F >nul 2>&1

if !_KILLED!==0 (
    echo  [*] No running services found
) else (
    echo  [OK] All services stopped
)
echo.
pause
goto MENU

:: ================================================================
::  Service Status
:: ================================================================
:STATUS
echo.
echo  ============================================================
echo   Service Status
echo  ============================================================
echo.

set "_BE=OFFLINE"
netstat -ano 2>nul | findstr ":%BACKEND_PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 set "_BE=RUNNING"
echo   Backend  (:%BACKEND_PORT%)   [ !_BE! ]

set "_FE=OFFLINE"
netstat -ano 2>nul | findstr ":%FRONTEND_PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 set "_FE=RUNNING"
echo   Frontend (:%FRONTEND_PORT%)   [ !_FE! ]

echo.
pause
goto MENU

:: ================================================================
::  Install / Update Deps
:: ================================================================
:INSTALL_DEPS
echo.
echo  [1/2] Installing Python backend deps...
if exist "%BACKEND_DIR%\requirements.txt" (
    cd /d "%BACKEND_DIR%"
    pip install -r requirements.txt -q
    echo  [OK] Python deps installed
) else (
    echo  [~] requirements.txt not found
)

echo.
echo  [2/2] Installing frontend Node deps...
if exist "%FRONTEND_DIR%\package.json" (
    cd /d "%FRONTEND_DIR%"
    call npm install
    echo  [OK] Node deps installed
) else (
    echo  [~] package.json not found
)

echo.
pause
goto MENU

:: ================================================================
::  Exit
:: ================================================================
:EXIT
echo.
echo  Bye
endlocal
exit /b 0
