<#
.SYNOPSIS
  Checks if required ports are available.

.DESCRIPTION
  This script checks for potential conflicts on ports used by the application.
#>

$ports = @(8080, 3306, 6379, 9092, 5000, 9090, 5601, 9200)

Write-Host "Checking for port conflicts..." -ForegroundColor Cyan

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "Port $port is in use by process with ID $($connection.OwningProcess)." -ForegroundColor Red
    } else {
        Write-Host "Port $port is available." -ForegroundColor Green
    }
}
