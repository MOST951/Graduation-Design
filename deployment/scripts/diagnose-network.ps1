<#
.SYNOPSIS
  Diagnoses network connectivity between Docker containers.

.DESCRIPTION
  This script pings other services from within a specified container to test network health.
#>

param(
    [string]$SourceContainer = "backend"
)

$services = @("mysql", "redis", "kafka", "spark-master")

Write-Host "Running network diagnostics from container '$SourceContainer'..." -ForegroundColor Cyan

foreach ($service in $services) {
    Write-Host "Pinging '$service'..." -ForegroundColor Yellow
    docker exec $SourceContainer ping -c 3 $service
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to ping '$service' from '$SourceContainer'." -ForegroundColor Red
    }
}
