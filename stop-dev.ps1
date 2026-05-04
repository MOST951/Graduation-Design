# ====================================================================
# 微博情感分析系统 - 停止所有开发服务 (PowerShell)
# ====================================================================
# 使用方法: .\stop-dev.ps1
# 停止策略:
#   1. 读取 .dev-pids.json 中记录的进程 PID 并终止
#   2. 按端口匹配并终止所有占用进程（含子进程）
#   3. 等待端口完全释放并确认
# ====================================================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ProjectRoot ".dev-pids.json"

function Test-Port([int]$Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient('localhost', $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Stop-PortProcess([int]$Port, [string]$Label) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return $false }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
    $killed = $false
    foreach ($pid in $pids) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            # 尝试强制终止（含子进程树）
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  [KILL] $Label (PID $pid, $($proc.ProcessName))" -ForegroundColor Cyan
            $killed = $true
        }
    }
    # 等待端口释放
    for ($w = 0; $w -lt 15; $w++) {
        if (-not (Test-Port $Port)) { return $killed }
        Start-Sleep -Milliseconds 500
    }
    return $killed
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Yellow
Write-Host " 微博情感分析系统 - 停止开发服务" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""

# ==================== 阶段1: PID 文件 ====================
Write-Host "[1/3] 从 PID 文件停止进程..." -ForegroundColor Yellow

if (Test-Path $PidFile) {
    try {
        $pidInfo = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($prop in $pidInfo.PSObject.Properties) {
            $svcName = $prop.Name
            $pid = [int]$prop.Value
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] $svcName (PID $pid) 已停止" -ForegroundColor Cyan
            } else {
                Write-Host "  [--] $svcName (PID $pid) 已不存在" -ForegroundColor DarkGray
            }
        }
    } catch {
        Write-Host "  [WARN] PID 文件解析失败: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  未找到 PID 文件，跳过" -ForegroundColor DarkGray
}

Write-Host ""

# ==================== 阶段2: 端口级清理 ====================
Write-Host "[2/3] 按端口清理残留进程..." -ForegroundColor Yellow

$services = @(
    @{ Port = 3001; Label = "前端 (Vue/Vite)" },
    @{ Port = 5000; Label = "Flask 后端" },
    @{ Port = 8081; Label = "Java 后端" }
)

foreach ($svc in $services) {
    if (Test-Port $svc.Port) {
        Stop-PortProcess $svc.Port $svc.Label | Out-Null
    } else {
        Write-Host "  [--] $($svc.Label) 未在运行 (端口 $($svc.Port) 空闲)" -ForegroundColor DarkGray
    }
}

Write-Host ""

# ==================== 阶段3: 确认端口已释放 ====================
Write-Host "[3/3] 确认端口状态..." -ForegroundColor Yellow

$allClear = $true
foreach ($svc in $services) {
    if (Test-Port $svc.Port) {
        Write-Host "  [WARN] 端口 $($svc.Port) ($($svc.Label)) 仍被占用" -ForegroundColor Red
        $allClear = $false
    } else {
        Write-Host "  [OK] 端口 $($svc.Port) 已释放" -ForegroundColor Green
    }
}

Write-Host ""
if ($allClear) {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " 所有服务已停止，端口已释放" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} else {
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host " 部分端口未完全释放，请稍后重试或手动处理" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  重新启动: .\start-dev.ps1" -ForegroundColor DarkGray
Write-Host ""
