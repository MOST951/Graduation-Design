<#
.SYNOPSIS
  Cleans up old application and Docker container logs.

.DESCRIPTION
  This script removes log files older than a specified number of days and prunes Docker logs.
#>

param(
    [int]$DaysToKeep = 30
)

$logPath = "..\..\logs"

Write-Host "Deleting log files older than $DaysToKeep days from '$logPath'..." -ForegroundColor Cyan
Get-ChildItem -Path $logPath -Recurse -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$DaysToKeep) } | Remove-Item -Force

Write-Host "Pruning Docker container logs..." -ForegroundColor Cyan
docker ps -q | ForEach-Object { docker logs --tail 100 $_ }
