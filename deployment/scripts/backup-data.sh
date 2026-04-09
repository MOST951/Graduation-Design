#!/bin/bash

# Database credentials
DB_USER="your_username"
DB_PASSWORD="your_password"
DB_NAME="your_database"

# Backup directory
BACKUP_DIR="/path/to/backups"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Dump the database to a file
mysqldump -u $DB_USER -p$DB_PASSWORD $DB_NAME > $BACKUP_DIR/backup-$(date +%F).sql
