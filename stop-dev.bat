@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ====================================================================
:: 微博情感分析系统 - Windows 本地开发停止脚本
:: ====================================================================
:: 使用方法: stop-dev.bat
:: 功能:
::   1. 读取 .dev-pids 文件中记录的 PID 并终止
::   2. 兜底: 按进程窗口标题终止所有 WeiboDev-* 进程
::   3. 释放端口 3001 / 5000 / 8081
:: ====================================================================

set "PROJECT_ROOT=%~dp0"
set "PID_FILE=%PROJECT_ROOT%.dev-pids"

echo.
echo ======================================================
echo   微博情感分析系统 - 停止本地开发服务
echo ======================================================
echo.

:: ==================== 阶段1: 通过PID文件停止 ====================
if exist "%PID_FILE%" (
    echo [1/3] 读取 PID 文件停止进程...
    for /f "tokens=1,2 delims==" %%a in (%PID_FILE%) do (
        set "SVC_NAME=%%a"
        set "SVC_PID=%%b"
        if "!SVC_PID!" neq "" (
            tasklist /fi "PID eq !SVC_PID!" 2>nul | findstr /i "!SVC_PID!" >nul 2>&1
            if !errorlevel!==0 (
                echo   停止 !SVC_NAME! ^(PID: !SVC_PID!^)...
                :: 先优雅终止
                taskkill /PID !SVC_PID! /T >nul 2>&1
                :: 等待 5 秒后检查是否仍在运行
                powershell -Command "Start-Sleep -Seconds 5" >nul 2>&1
                tasklist /fi "PID eq !SVC_PID!" 2>nul | findstr /i "!SVC_PID!" >nul 2>&1
                if !errorlevel!==0 (
                    echo   [WARN] !SVC_NAME! 未响应优雅停止，强制终止...
                    taskkill /PID !SVC_PID! /T /F >nul 2>&1
                )
                echo   [OK] !SVC_NAME! 已停止
            ) else (
                echo   [SKIP] !SVC_NAME! ^(PID: !SVC_PID!^) 已不存在
            )
        )
    )
    del "%PID_FILE%" >nul 2>&1
    echo.
) else (
    echo [1/3] 未找到 PID 文件，跳过...
    echo.
)

:: ==================== 阶段2: 按窗口标题终止 ====================
echo [2/3] 终止 WeiboDev-* 窗口进程...

:: 先优雅终止所有 WeiboDev 窗口
taskkill /fi "WINDOWTITLE eq WeiboDev-Frontend*" /T >nul 2>&1
taskkill /fi "WINDOWTITLE eq WeiboDev-Flask*" /T >nul 2>&1
taskkill /fi "WINDOWTITLE eq WeiboDev-Java*" /T >nul 2>&1

echo   等待进程优雅退出 ^(5秒^)...
powershell -Command "Start-Sleep -Seconds 5" >nul 2>&1

:: 强制终止残留进程
taskkill /fi "WINDOWTITLE eq WeiboDev-Frontend*" /T /F >nul 2>&1
if %errorlevel%==0 ( echo   [OK] Frontend 窗口已强制关闭 ) else ( echo   [OK] Frontend 窗口已停止 )

taskkill /fi "WINDOWTITLE eq WeiboDev-Flask*" /T /F >nul 2>&1
if %errorlevel%==0 ( echo   [OK] Flask 窗口已强制关闭 ) else ( echo   [OK] Flask 窗口已停止 )

taskkill /fi "WINDOWTITLE eq WeiboDev-Java*" /T /F >nul 2>&1
if %errorlevel%==0 ( echo   [OK] Java 窗口已强制关闭 ) else ( echo   [OK] Java 窗口已停止 )
echo.

:: ==================== 阶段3: 端口兜底清理 ====================
echo [3/3] 检查残留端口占用...

:: 清理端口 5000 (Flask)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    if "%%p" neq "0" (
        echo   释放端口 5000 ^(PID: %%p^)...
        taskkill /PID %%p /T >nul 2>&1
        powershell -Command "Start-Sleep -Seconds 3" >nul 2>&1
        taskkill /PID %%p /T /F >nul 2>&1
    )
)

:: 清理端口 3001 (Frontend)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 " ^| findstr "LISTENING"') do (
    if "%%p" neq "0" (
        echo   释放端口 3001 ^(PID: %%p^)...
        taskkill /PID %%p /T >nul 2>&1
        powershell -Command "Start-Sleep -Seconds 3" >nul 2>&1
        taskkill /PID %%p /T /F >nul 2>&1
    )
)

:: 清理端口 8081 (Java)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8081 " ^| findstr "LISTENING"') do (
    if "%%p" neq "0" (
        echo   释放端口 8081 ^(PID: %%p^)...
        taskkill /PID %%p /T >nul 2>&1
        powershell -Command "Start-Sleep -Seconds 3" >nul 2>&1
        taskkill /PID %%p /T /F >nul 2>&1
    )
)
echo.

echo ======================================================
echo   所有开发服务已停止
echo ======================================================
echo.
echo   端口 3001 / 5000 / 8081 已释放
echo   重新启动: start-dev.bat
echo.
pause
