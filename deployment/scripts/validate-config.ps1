<#
.SYNOPSIS
  Validates the syntax of YAML configuration files.

.DESCRIPTION
  This script checks all `application.yml` files in the project for correct YAML syntax.
  It requires the 'powershell-yaml' module to be installed.
#>

# Ensure the required module is installed
if (-not (Get-Module -ListAvailable -Name 'powershell-yaml')) {
    Write-Host "'powershell-yaml' module not found. Installing..." -ForegroundColor Yellow
    Install-Module -Name 'powershell-yaml' -Scope CurrentUser -Force
}
Import-Module 'powershell-yaml'

$configFiles = Get-ChildItem -Path "..\.." -Recurse -Filter "application*.yml"

$allValid = $true

foreach ($file in $configFiles) {
    try {
        Get-Content $file.FullName | ConvertFrom-Yaml | Out-Null
        Write-Host "Validation successful for: $($file.FullName)" -ForegroundColor Green
    } catch {
        Write-Host "Validation failed for: $($file.FullName)" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $allValid = $false
    }
}

if (-not $allValid) {
    exit 1
}
