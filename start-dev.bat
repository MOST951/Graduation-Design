@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ====================================================================
:: 微博情感分析系统 - Windows 本地开发启动脚本
:: ====================================================================
:: 使用方法: start-dev.bat [选项]
:: 停止方法: stop-dev.bat 或按 Ctrl+C
:: 选项:
::   --skip-java       跳过 Java 后端
::   --skip-python     跳过 Python 后端
::   --skip-frontend   跳过前端
::   --cascade-mode    启用 cascade 级联情感分析模式
::   --restart-spark   仅重启 Spark 服务 (核心参数变更后)
:: ====================================================================

set "PROJECT_ROOT=%~dp0"
set "SKIP_JAVA=0"
set "SKIP_PYTHON=0"
set "SKIP_FRONTEND=0"
set "CASCADE_MODE=0"
set "RESTART_SPARK=0"

:: 解析参数
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--skip-java"      set "SKIP_JAVA=1"
if /i "%~1"=="--skip-python"    set "SKIP_PYTHON=1"
if /i "%~1"=="--skip-frontend"  set "SKIP_FRONTEND=1"
if /i "%~1"=="--cascade-mode"   set "CASCADE_MODE=1"
if /i "%~1"=="--restart-spark"  set "RESTART_SPARK=1"
shift
goto :parse_args
:args_done

:: ==================== restart-spark 快捷模式 ====================
if %RESTART_SPARK%==1 (
    echo.
    echo ======================================================
    echo   Spark 服务重启 ^(核心参数变更后使用^)
    echo ======================================================
    echo.
    echo   通过免认证内部 API 通知 Flask 重启 Spark...
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5000/api/admin/spark/restart-internal' -Method POST -ContentType 'application/json' -Body '{\"confirm\":true}' -TimeoutSec 30 -UseBasicParsing; Write-Host $r.Content } catch { Write-Host 'ERROR:' $_.Exception.Message }" 2>nul
    echo.
    echo   Spark 重启请求已发送，请稍后查看状态。
    echo.
    pause
    exit /b 0
)

echo.
echo ======================================================
echo   微博情感分析系统 - Windows 本地开发环境启动
echo   改进: 线程安全采集 / cascade情感分析 / Spark热重载
echo ======================================================
echo.

:: ==================== 环境检查 ====================
echo [1/6] 检查环境依赖...

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Node.js 未安装
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo   [OK] Node.js: %%v

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Python 未安装
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   [OK] %%v

if %SKIP_JAVA%==0 (
    where java >nul 2>&1
    if %errorlevel% neq 0 (
        echo   [WARN] Java 未安装，跳过 Java 后端
        set "SKIP_JAVA=1"
    ) else (
        for /f "tokens=*" %%v in ('java -version 2^>^&1') do (
            echo   [OK] Java: %%v
            goto :java_done
        )
        :java_done
    )
)
echo.

:: ==================== 检查数据库服务 ====================
echo [2/6] 检查数据库服务...

:: 检查 MySQL (端口3306)
powershell -Command "try { $c = New-Object Net.Sockets.TcpClient('localhost',3306); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] MySQL  :3306
) else (
    echo   [FAIL] MySQL :3306 未运行，请先启动 MySQL 服务
    exit /b 1
)

:: 检查 Redis (端口6379)
powershell -Command "try { $c = New-Object Net.Sockets.TcpClient('localhost',6379); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo   [OK] Redis  :6379
) else (
    echo   [WARN] Redis :6379 未运行，部分缓存功能不可用
)
echo.

:: ==================== 检查配置文件 ====================
echo [3/6] 检查配置文件...

set "ENV_FILE=%PROJECT_ROOT%backend-python\.env"
if not exist "%ENV_FILE%" (
    echo   创建 backend-python\.env ...
    (
        echo # Database
        echo DB_HOST=localhost
        echo DB_PORT=3306
        echo DB_NAME=weibo_sentiment_graduation
        echo DB_USER=root
        echo DB_PASSWORD=123456
        echo.
        echo # Redis
        echo REDIS_HOST=localhost
        echo REDIS_PORT=6379
        echo REDIS_DB=0
        echo REDIS_PASSWORD=123456
        echo.
        echo # Flask
        echo FLASK_HOST=0.0.0.0
        echo FLASK_PORT=5000
        echo FLASK_DEBUG=true
        echo SECRET_KEY=dev-secret-key-for-local-testing-only-2024
        echo CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173
        echo.
        echo # Spark ^(local mode^)
        echo SPARK_MASTER_URL=local[*]
        echo.
        echo # Cascade sentiment analysis
        echo CASCADE_THRESHOLD=0.7
        echo.
        echo # Logging
        echo LOG_LEVEL=INFO
        echo LOG_FILE_PATH=logs/app.log
        echo.
        echo # Model
        echo CONFIDENCE_THRESHOLD=0.7
        echo MODEL_USE_GPU=false
    ) > "%ENV_FILE%"
    echo   [OK] .env 已创建
) else (
    echo   [OK] .env 已存在
)

:: 确保 logs 目录存在
if not exist "%PROJECT_ROOT%backend-python\logs" mkdir "%PROJECT_ROOT%backend-python\logs"
echo.

:: ==================== 安装依赖 ====================
echo [4/6] 检查并安装依赖...

:: 前端依赖
if %SKIP_FRONTEND%==0 (
    if not exist "%PROJECT_ROOT%web-frontend\node_modules" (
        echo   安装前端依赖 ^(npm install^)...
        pushd "%PROJECT_ROOT%web-frontend"
        call npm install --quiet 2>nul
        popd
        echo   [OK] 前端依赖安装完成
    ) else (
        echo   [OK] 前端依赖已存在
    )
)

:: Python 依赖
if %SKIP_PYTHON%==0 (
    echo   检查 Python 依赖...
    pip install -q flask flask-cors python-dotenv pymysql redis DBUtils jieba numpy pandas requests 2>nul
    echo   [OK] Python 依赖已就绪
)
echo.

:: ==================== 写入 PID 文件 ====================
set "PID_FILE=%PROJECT_ROOT%.dev-pids"
if exist "%PID_FILE%" del "%PID_FILE%"
echo.

:: ==================== 启动服务 ====================
echo [5/6] 启动服务...

:: 启动前端 (port 3001 / 5173)
if %SKIP_FRONTEND%==0 (
    echo   启动前端 ^(http://localhost:3001^) ...
    pushd "%PROJECT_ROOT%web-frontend"
    start "WeiboDev-Frontend" cmd /c "npm run dev"
    popd
    :: 获取 PID
    powershell -Command "Start-Sleep -Milliseconds 2000; Get-Process -Name node -ErrorAction SilentlyContinue | Select-Object -Last 1 -ExpandProperty Id" > "%TEMP%\frontend_pid.txt" 2>nul
    set /p FRONTEND_PID=<"%TEMP%\frontend_pid.txt"
    echo frontend=!FRONTEND_PID! >> "%PID_FILE%"
)

:: 启动 Python Flask (port 5000)
if %SKIP_PYTHON%==0 (
    echo   启动 Flask 后端 ^(http://localhost:5000^) ...
    if %CASCADE_MODE%==1 (
        echo   [INFO] Cascade 级联模式已启用 ^(threshold=0.7^)
        set "SENTIMENT_MODE=cascade"
    )
    pushd "%PROJECT_ROOT%backend-python"
    start "WeiboDev-Flask" cmd /c "python app.py"
    popd
    powershell -Command "Start-Sleep -Milliseconds 2000; Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object -Last 1 -ExpandProperty Id" > "%TEMP%\flask_pid.txt" 2>nul
    set /p FLASK_PID=<"%TEMP%\flask_pid.txt"
    echo flask=!FLASK_PID! >> "%PID_FILE%"
)

:: 启动 Java Spring Boot (port 8081)
if %SKIP_JAVA%==0 (
    if exist "%PROJECT_ROOT%web-backend\target\web-backend-1.0-SNAPSHOT.jar" (
        echo   启动 Java 后端 ^(http://localhost:8081^) ...
        pushd "%PROJECT_ROOT%web-backend"
        start "WeiboDev-Java" cmd /c "java -jar target\web-backend-1.0-SNAPSHOT.jar --spring.profiles.active=dev --DB_NAME=weibo_sentiment_graduation"
        popd
        powershell -Command "Start-Sleep -Milliseconds 3000; Get-Process -Name java -ErrorAction SilentlyContinue | Select-Object -Last 1 -ExpandProperty Id" > "%TEMP%\java_pid.txt" 2>nul
        set /p JAVA_PID=<"%TEMP%\java_pid.txt"
        echo java=!JAVA_PID! >> "%PID_FILE%"
    ) else (
        echo   [WARN] Java JAR 不存在，跳过。请先执行: mvn -pl web-backend -am clean package -DskipTests
    )
)
echo.

:: ==================== 等待就绪 ====================
echo [6/6] 等待服务就绪 ^(约 20 秒^)...
timeout /t 20 /nobreak >nul

:: 检查服务是否就绪
if %SKIP_FRONTEND%==0 (
    powershell -Command "try { (Invoke-WebRequest -Uri 'http://localhost:3001' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }" > "%TEMP%\check_fe.txt" 2>nul
    set /p FE_STATUS=<"%TEMP%\check_fe.txt"
    if "!FE_STATUS!"=="200" ( echo   [OK] Frontend ^(3001^) ) else ( echo   [WAIT] Frontend 仍在启动中... )
)

if %SKIP_PYTHON%==0 (
    powershell -Command "try { (Invoke-WebRequest -Uri 'http://localhost:5000/' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }" > "%TEMP%\check_flask.txt" 2>nul
    set /p FLASK_STATUS=<"%TEMP%\check_flask.txt"
    if "!FLASK_STATUS!"=="200" ( echo   [OK] Flask API ^(5000^) ) else ( echo   [WAIT] Flask API 仍在启动中... )
)

if %SKIP_JAVA%==0 (
    echo   检查 Java API ^(8081^)...
    powershell -Command "$ok=$false; for($i=0;$i -lt 10;$i++){try{$c=New-Object Net.Sockets.TcpClient('localhost',8081);$c.Close();$ok=$true;break}catch{Start-Sleep -Seconds 3}};if($ok){'OK'}else{'WAIT'}" > "%TEMP%\check_java.txt" 2>nul
    set /p JAVA_STATUS=<"%TEMP%\check_java.txt"
    if "!JAVA_STATUS!"=="OK" ( echo   [OK] Java API ^(8081^) ) else ( echo   [WAIT] Java API 仍在启动中 ^(首次约需 30s^)... )
)

echo.
echo ======================================================
echo   所有服务已启动！
echo ======================================================
echo.
echo   前端界面:   http://localhost:3001
echo   Flask API:  http://localhost:5000
echo   Java  API:  http://localhost:8081/api
echo.
echo   改进功能:
echo     - 采集任务: threading.Event 线程安全暂停/恢复/终止
echo     - 情感分析: cascade 级联模式 ^(词典→BERT自动升级^)
echo     - 预处理:   繁→简转换蓝色高亮 + 删除红色标注
echo     - 流水线:   终止按钮 + clearHistory 后端 DELETE
echo     - 热点分析: 四象限分类标签 ^(情感×热度^)
echo     - 网络图:   节点颜色=情感 / 大小=转发量 / 富tooltip
echo     - 监控:     visibilitychange 自动停止标题闪烁
echo     - Spark:    核心参数变更→提示重启 / 非核心→热加载
echo.
echo   管理命令:
echo     start-dev.bat --restart-spark   仅重启Spark服务
echo     start-dev.bat --cascade-mode    启用级联分析
echo     stop-dev.bat                    停止所有服务
echo.
echo   PID 文件: %PID_FILE%
echo ======================================================
echo.
pause
