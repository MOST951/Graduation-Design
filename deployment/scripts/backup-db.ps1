<#
.SYNOPSIS
  Backs up the MySQL database using mysqldump.

.DESCRIPTION
  This script creates a timestamped SQL dump of the production database.
  It reads database credentials from the project's .env file.
#>

# Load environment variables from .env file
Get-Content "..\..\.env" | ForEach-Object { 
    if ($_ -match '^([^=]+)=(.*)') {
        Set-Variable -Name $Matches[1] -Value $Matches[2]
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = "..\..\backup\${DB_NAME}_${timestamp}.sql"

Write-Host "Backing up database '$DB_NAME' to '$backupFile'..." -ForegroundColor Cyan

mysqldump.exe --user=$DB_USERNAME --password=$DB_PASSWORD --host=$DB_HOST --port=$DB_PORT $DB_NAME > $backupFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database backup completed successfully." -ForegroundColor Green
} else {
    Write-Host "Database backup failed." -ForegroundColor Red
}
