# Weibo Sentiment Analysis Platform - Management Scripts

This directory contains a collection of PowerShell scripts to help you deploy, maintain, and troubleshoot the platform.

## Scripts Overview

### Deployment Scripts

- **`deploy.ps1`**: A one-click script that automates the entire deployment process.
  - **Usage**: `.\deploy.ps1`

- **`check-env.ps1`**: Checks for all required dependencies (Java, Docker, etc.).
  - **Usage**: `.\check-env.ps1`

- **`validate-config.ps1`**: Validates the syntax of all `application.yml` files.
  - **Usage**: `.\validate-config.ps1`

### Maintenance Scripts

- **`backup-db.ps1`**: Creates a timestamped backup of the MySQL database.
  - **Usage**: `.\backup-db.ps1`

- **`clean-logs.ps1`**: Cleans up old application and Docker container logs.
  - **Usage**: `.\clean-logs.ps1 -DaysToKeep 30`

- **`monitor-services.ps1`**: Provides a real-time dashboard of all running Docker services.
  - **Usage**: `.\monitor-services.ps1`

### Tool Scripts

- **`check-ports.ps1`**: Checks for potential port conflicts.
  - **Usage**: `.\check-ports.ps1`

- **`diagnose-network.ps1`**: Diagnoses network connectivity between Docker containers.
  - **Usage**: `.\diagnose-network.ps1 -SourceContainer backend`

- **`monitor-performance.ps1`**: Provides a live stream of performance metrics for all containers.
  - **Usage**: `.\monitor-performance.ps1`
