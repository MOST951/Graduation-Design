<#
.SYNOPSIS
  Monitors real-time performance metrics of all running containers.

.DESCRIPTION
  This script provides a live stream of CPU, memory, and network I/O for each container.
#>

Write-Host "Starting real-time performance monitoring... (Press CTRL+C to exit)" -ForegroundColor Cyan
docker stats
