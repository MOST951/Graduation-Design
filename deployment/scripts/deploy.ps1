<#
.SYNOPSIS
  A one-click deployment script for the Weibo Sentiment Analysis Platform.

.DESCRIPTION
  This script automates the entire deployment process, including:
  1. Running environment checks.
  2. Building the Java backend and Spark jobs with Maven.
  3. Building and starting all services with Docker Compose.
  4. Displaying the final status of all running services.

.EXAMPLE
  .\deploy.ps1
#>

Write-Host "Starting Weibo Sentiment Analysis Platform Deployment..." -ForegroundColor Green

# Step 1: Run Environment Check
Write-Host "
[Step 1/4] Running environment check..." -ForegroundColor Cyan
.\check-env.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Environment check failed. Please resolve the issues above before proceeding." -ForegroundColor Red
    exit 1
}
Write-Host "Environment check passed." -ForegroundColor Green

# Step 2: Build Java Backend and Spark Jobs
Write-Host "
[Step 2/4] Building Java backend and Spark jobs with Maven..." -ForegroundColor Cyan
# Navigate to the root of the project to run Maven
Push-Location "..\.."
./mvnw clean install -DskipTests
if ($LASTEXITCODE -ne 0) {
    Write-Host "Maven build failed. Please check the logs for errors." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Maven build completed successfully." -ForegroundColor Green
Pop-Location

# Step 3: Build and Start Docker Services
Write-Host "
[Step 3/4] Building and starting all services with Docker Compose..." -ForegroundColor Cyan
# Navigate to the docker-compose file location
Push-Location "..\docker"
docker-compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Compose failed to start. Please check the logs for errors." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Docker services are starting in the background." -ForegroundColor Green
Pop-Location

# Step 4: Monitor and Verify Services
Write-Host "
[Step 4/4] Verifying service status..." -ForegroundColor Cyan
# Give services a moment to initialize
Start-Sleep -Seconds 15
.\monitor-services.ps1

Write-Host "
Deployment script finished." -ForegroundColor Green
