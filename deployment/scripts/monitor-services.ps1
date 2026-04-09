<#
.SYNOPSIS
  Monitors the health and status of all running Docker services.

.DESCRIPTION
  This script provides a real-time dashboard-like view of all containers,
  including their status, ports, and resource usage.
#>

Push-Location "..\docker"

function Get-Service-Status {
    docker-compose ps
    Write-Host "
Resource Usage:" -ForegroundColor Cyan
    docker stats --no-stream
}

while ($true) {
    Clear-Host
    Write-Host "--- Weibo Sentiment Analysis Platform Status ---" -ForegroundColor Yellow
    Get-Service-Status
    Write-Host "
(Press CTRL+C to exit)" -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

Pop-Location
