<#
.SYNOPSIS
  Checks if all required dependencies are installed and configured.

.DESCRIPTION
  This script verifies the versions of Java, Docker, Maven, and Node.js.
  It exits with a non-zero status code if any dependency is missing.
#>

$ErrorActionPreference = "SilentlyContinue"
$global:exitCode = 0

function Check-Command($command, $requiredVersion) {
    $versionInfo = & $command --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: '$command' is not installed or not in PATH." -ForegroundColor Red
        $global:exitCode = 1
    } else {
        Write-Host "'$command' found. Version: $versionInfo" -ForegroundColor Green
    }
}

Write-Host "Checking required dependencies..." -ForegroundColor Cyan

Check-Command "java" "1.8"
Check-Command "docker" "20.10"
Check-Command "docker-compose" "1.29"
Check-Command "mvn" "3.6"
Check-Command "node" "16"

exit $global:exitCode
