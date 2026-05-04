# ====================================================================
# 微博情感分析系统 - Windows 本地开发启动脚本 (PowerShell)
# ====================================================================
# 使用方法:
#   .\start-dev.ps1                     启动所有服务
#   .\start-dev.ps1 -SkipJava           跳过Java后端
#   .\start-dev.ps1 -SkipPython         跳过Python后端
#   .\start-dev.ps1 -SkipFrontend       跳过前端
#   .\start-dev.ps1 -RestartSpark       仅重启Spark服务
#   .\start-dev.ps1 -Only python        仅启动Python后端
#   .\start-dev.ps1 -Only frontend      仅启动前端
# 停止方法: .\stop-dev.ps1 或 Ctrl+C
# ====================================================================

param(
    [switch]$SkipJava,          # 跳过Java后端
    [switch]$SkipPython,        # 跳过Python后端
    [switch]$SkipFrontend,      # 跳过前端
    [switch]$BuildJava,         # 强制重新构建Java后端
    [switch]$RestartSpark,      # 仅重启Spark服务
    [string]$Only = ''          # 仅启动指定服务: frontend / python / java
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ProjectRoot ".dev-pids.json"

# ==================== 快捷模式: 仅重启 Spark ====================
if ($RestartSpark) {
    Write-Host ""
    Write-Host "========== Spark 服务重启 ==========" -ForegroundColor Cyan
    try {
        $resp = Invoke-WebRequest -Uri 'http://localhost:5000/api/admin/spark/restart-internal' `
            -Method POST -ContentType 'application/json' -Body '{"confirm":true}' `
            -TimeoutSec 30 -UseBasicParsing
        Write-Host "  Spark 重启请求已发送" -ForegroundColor Green
        Write-Host "  响应: $($resp.Content)" -ForegroundColor DarkGray
    } catch {
        Write-Host "  [FAIL] Flask后端未运行或Spark重启失败: $($_.Exception.Message)" -ForegroundColor Red
    }
    exit 0
}

# ==================== -Only 模式 ====================
if ($Only -ne '') {
    switch ($Only.ToLower()) {
        'frontend' { $SkipJava = $true; $SkipPython = $true }
        'python'   { $SkipJava = $true; $SkipFrontend = $true }
        'java'     { $SkipPython = $true; $SkipFrontend = $true }
        default    { Write-Host "[ERROR] -Only 参数仅支持: frontend, python, java" -ForegroundColor Red; exit 1 }
    }
}

# ==================== 工具函数 ====================
function Test-Port([int]$Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient('localhost', $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Stop-PortProcess([int]$Port, [string]$Label) {
    # 终止占用指定端口的所有进程
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
        foreach ($pid in $pids) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  清理残留 $Label (PID $pid $($proc.ProcessName))" -ForegroundColor DarkYellow
            }
        }
        # 等待端口释放
        for ($w = 0; $w -lt 10; $w++) {
            if (-not (Test-Port $Port)) { return }
            Start-Sleep -Milliseconds 500
        }
    }
}

function Wait-ServiceReady([string]$Name, [string]$Url, [int]$TimeoutSec = 60) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $r = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "  $Name  [OK] ($([math]::Round($sw.Elapsed.TotalSeconds))s)" -ForegroundColor Green
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 2
    }
    Write-Host "  $Name  [TIMEOUT ${TimeoutSec}s]" -ForegroundColor Red
    return $false
}

# ==================== 标题 ====================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 微博情感分析系统 - 本地开发环境启动" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ==================== [1/7] 环境检查 ====================
Write-Host "[1/7] 检查环境依赖..." -ForegroundColor Yellow

$checks = @()

# Node.js
if (-not (Get-Command -Name node -ErrorAction SilentlyContinue)) {
    if (-not $SkipFrontend) {
        Write-Host "  [FAIL] Node.js 未安装" -ForegroundColor Red
        exit 1
    }
} else {
    $nodeVer = node --version 2>$null
    $checks += "  Node.js: $nodeVer"
}

# Python
if (-not (Get-Command -Name python -ErrorAction SilentlyContinue)) {
    if (-not $SkipPython) {
        Write-Host "  [FAIL] Python 未安装" -ForegroundColor Red
        exit 1
    }
} else {
    $pyVer = python --version 2>$null
    $checks += "  Python:  $pyVer"
}

# Java
if (Get-Command -Name java -ErrorAction SilentlyContinue) {
    $javaVer = (java -version 2>&1 | Select-Object -First 1)
    $checks += "  Java:    $javaVer"
} elseif (-not $SkipJava) {
    Write-Host "  [WARN] Java 未安装，跳过Java后端" -ForegroundColor Yellow
    $SkipJava = $true
}

# Maven
if (Get-Command -Name mvn -ErrorAction SilentlyContinue) {
    $mvnVer = (mvn --version 2>&1 | Select-Object -First 1)
    $checks += "  Maven:   $mvnVer"
} elseif (-not $SkipJava) {
    Write-Host "  [WARN] Maven 未安装，跳过Java后端" -ForegroundColor Yellow
    $SkipJava = $true
}

$checks | ForEach-Object { Write-Host $_ -ForegroundColor Green }

# ==================== [2/7] 检查数据库 ====================
Write-Host ""
Write-Host "[2/7] 检查数据库服务..." -ForegroundColor Yellow

if (Test-Port 3306) {
    Write-Host "  MySQL  :3306  [OK]" -ForegroundColor Green
} else {
    Write-Host "  MySQL  :3306  [FAIL] 请先启动MySQL服务" -ForegroundColor Red
    exit 1
}

if (Test-Port 6379) {
    Write-Host "  Redis  :6379  [OK]" -ForegroundColor Green
} else {
    Write-Host "  Redis  :6379  [WARN] Redis未运行，部分缓存功能不可用" -ForegroundColor Yellow
}

# ==================== [3/7] 端口冲突检测与清理 ====================
Write-Host ""
Write-Host "[3/7] 检查端口占用..." -ForegroundColor Yellow

$portMap = @(
    @{ Port = 3001; Label = "Frontend"; Skip = $SkipFrontend },
    @{ Port = 5000; Label = "Flask";    Skip = $SkipPython },
    @{ Port = 8081; Label = "Java";     Skip = $SkipJava }
)

foreach ($pm in $portMap) {
    if ($pm.Skip) { continue }
    if (Test-Port $pm.Port) {
        Write-Host "  端口 $($pm.Port) 已被占用，正在清理..." -ForegroundColor DarkYellow
        Stop-PortProcess $pm.Port $pm.Label
        if (Test-Port $pm.Port) {
            Write-Host "  [FAIL] 无法释放端口 $($pm.Port)，请手动处理" -ForegroundColor Red
            exit 1
        }
        Write-Host "  端口 $($pm.Port) 已释放" -ForegroundColor Green
    } else {
        Write-Host "  端口 $($pm.Port) ($($pm.Label)) 可用" -ForegroundColor Green
    }
}

# ==================== [4/7] 配置文件 ====================
Write-Host ""
Write-Host "[4/7] 检查配置文件..." -ForegroundColor Yellow

$envFile = Join-Path $ProjectRoot "backend-python\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "  创建 backend-python\.env ..." -ForegroundColor Yellow
    @"
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=weibo_sentiment_graduation
DB_USER=root
DB_PASSWORD=123456

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=123456

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=true
SECRET_KEY=dev-secret-key-for-local-testing-only-2024
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173

# Spark (local mode)
SPARK_MASTER_URL=local[*]

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log

# Model
CONFIDENCE_THRESHOLD=0.7
MODEL_USE_GPU=false
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  .env 已创建" -ForegroundColor Green
} else {
    Write-Host "  .env 已存在" -ForegroundColor Green
}

# 确保 logs 目录存在
$logsDir = Join-Path $ProjectRoot "backend-python\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

# ==================== [5/7] 安装依赖 ====================
Write-Host ""
Write-Host "[5/7] 检查并安装依赖..." -ForegroundColor Yellow

# 前端依赖
if (-not $SkipFrontend) {
    $nodeModules = Join-Path $ProjectRoot "web-frontend\node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "  安装前端依赖 (npm install)..." -ForegroundColor Yellow
        Push-Location (Join-Path $ProjectRoot "web-frontend")
        npm install 2>&1 | Out-Null
        Pop-Location
        Write-Host "  前端依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "  前端依赖已存在" -ForegroundColor Green
    }
}

# Python 依赖检查
if (-not $SkipPython) {
    $missingPkgs = @()
    @("flask", "pymysql", "redis", "jieba", "DBUtils") | ForEach-Object {
        $found = pip show $_ 2>$null
        if (-not $found) { $missingPkgs += $_ }
    }
    if ($missingPkgs.Count -gt 0) {
        Write-Host "  安装缺失Python包: $($missingPkgs -join ', ')..." -ForegroundColor Yellow
        pip install $missingPkgs 2>&1 | Out-Null
    }
    Write-Host "  Python依赖已就绪" -ForegroundColor Green
}

# Java 构建
if (-not $SkipJava) {
    $jarFile = Join-Path $ProjectRoot "web-backend\target\web-backend-1.0-SNAPSHOT.jar"
    if ($BuildJava -or -not (Test-Path $jarFile)) {
        Write-Host "  构建Java后端 (mvn package)..." -ForegroundColor Yellow
        Push-Location $ProjectRoot
        mvn -pl web-backend -am clean package -DskipTests -q 2>&1 | Out-Null
        Pop-Location
        if (Test-Path $jarFile) {
            Write-Host "  Java后端构建成功" -ForegroundColor Green
        } else {
            Write-Host "  Java后端构建失败，跳过" -ForegroundColor Red
            $SkipJava = $true
        }
    } else {
        Write-Host "  Java JAR已存在" -ForegroundColor Green
    }
}

# ==================== [6/7] 启动服务 ====================
Write-Host ""
Write-Host "[6/7] 启动服务..." -ForegroundColor Yellow

$pidInfo = @{}

# 启动前端 (port 3001)
if (-not $SkipFrontend) {
    Write-Host "  启动前端 (http://localhost:3001) ..." -ForegroundColor Cyan
    $frontendJob = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c title WeiboDev-Frontend && npm run dev" `
        -WorkingDirectory (Join-Path $ProjectRoot "web-frontend") `
        -PassThru -WindowStyle Minimized
    $pidInfo['frontend'] = $frontendJob.Id
}

# 启动 Python Flask (port 5000)
if (-not $SkipPython) {
    Write-Host "  启动Flask后端 (http://localhost:5000) ..." -ForegroundColor Cyan
    $pythonJob = Start-Process -FilePath "python" -ArgumentList "app.py" `
        -WorkingDirectory (Join-Path $ProjectRoot "backend-python") `
        -PassThru -WindowStyle Minimized
    $pidInfo['flask'] = $pythonJob.Id
}

# 启动 Java Spring Boot (port 8081)
if (-not $SkipJava) {
    Write-Host "  启动Java后端 (http://localhost:8081) ..." -ForegroundColor Cyan
    $javaJob = Start-Process -FilePath "java" `
        -ArgumentList "-jar", "web-backend\target\web-backend-1.0-SNAPSHOT.jar", "--spring.profiles.active=dev", "--DB_NAME=weibo_sentiment_graduation" `
        -WorkingDirectory $ProjectRoot `
        -PassThru -WindowStyle Minimized
    $pidInfo['java'] = $javaJob.Id
}

# 写入 PID 文件
$pidInfo | ConvertTo-Json | Out-File -FilePath $PidFile -Encoding utf8
Write-Host "  PID 已记录: $PidFile" -ForegroundColor DarkGray

# ==================== [7/7] 等待就绪 ====================
Write-Host ""
Write-Host "[7/7] 等待服务就绪..." -ForegroundColor Yellow

$allOk = $true

if (-not $SkipFrontend) {
    if (-not (Wait-ServiceReady "Frontend (Vue) :3001" "http://localhost:3001/" 30)) { $allOk = $false }
}
if (-not $SkipPython) {
    if (-not (Wait-ServiceReady "Flask API      :5000" "http://localhost:5000/" 60)) { $allOk = $false }
}
if (-not $SkipJava) {
    if (-not (Wait-ServiceReady "Java API       :8081" "http://localhost:8081/api/actuator/health" 60)) { $allOk = $false }
}

# ==================== 完成 ====================
Write-Host ""
if ($allOk) {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " 所有服务已启动！" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} else {
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host " 部分服务启动超时，请检查日志" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  前端界面:   http://localhost:3001" -ForegroundColor White
Write-Host "  Flask API:  http://localhost:5000" -ForegroundColor White
Write-Host "  Java  API:  http://localhost:8081/api" -ForegroundColor White
Write-Host "  Swagger UI: http://localhost:8081/api/swagger-ui.html" -ForegroundColor White
Write-Host ""
Write-Host "  管理命令:" -ForegroundColor DarkGray
Write-Host "    .\start-dev.ps1 -RestartSpark       仅重启Spark服务" -ForegroundColor DarkGray
Write-Host "    .\start-dev.ps1 -Only python        仅启动Python后端" -ForegroundColor DarkGray
Write-Host "    .\stop-dev.ps1                      停止所有服务" -ForegroundColor DarkGray
Write-Host ""
Write-Host "按 Ctrl+C 或关闭此窗口停止所有服务" -ForegroundColor Yellow
Write-Host ""

# 等待用户中断，Ctrl+C 触发 finally 清理
try {
    while ($true) { Start-Sleep -Seconds 5 }
} finally {
    Write-Host ""
    Write-Host "正在停止服务..." -ForegroundColor Yellow

    # 通过端口精确杀死所有子进程（包括 python debug fork）
    foreach ($pm in $portMap) {
        if ($pm.Skip) { continue }
        Stop-PortProcess $pm.Port $pm.Label
    }

    # 兜底：通过 PID 文件杀残留
    foreach ($key in $pidInfo.Keys) {
        $pid = $pidInfo[$key]
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  已停止 $key (PID $pid)" -ForegroundColor DarkGray
        }
    }

    # 删除 PID 文件
    Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue

    Write-Host "所有服务已停止" -ForegroundColor Green
}
