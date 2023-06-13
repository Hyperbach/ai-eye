#!/bin/bash

: '
This script is used to restore a PostgreSQL database within a Docker environment. It takes three arguments: the name of the database user, the name of the database, and the path to the backup file.

Usage:
  ./<script-name> DB_USER DB_NAME BACKUP_FILE

The script will warn the user that the current database will be erased and a backup will be created. If the user agrees, it will proceed as follows:

1. Check if the backup file exists on the Docker machine.
2. Stop the web container using Docker Compose.
3. Drop the existing database if it exists.
4. Create a new database.
5. Restore the database from the backup file.
6. Start the web container again using Docker Compose.

If any of these steps fail, the script will log an error message and terminate immediately.

Example:
  ./db_restore.sh postgres mydatabase /path/to/backup/file.sql
'

# Function to display script usage
usage() {
  echo "Usage: $0 DB_USER DB_NAME BACKUP_FILE"
  exit 1
}

# Validate script parameters
if [ $# -ne 3 ]; then
  usage
fi

DB_USER="$1"
DB_NAME="$2"
BACKUP_FILE="$3"

# Function to log messages
log_message() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1"
}

# Function to check if a command executed successfully
check_command_status() {
  if [ $1 -ne 0 ]; then
    log_message "Error: $2"
    exit 1
  fi
}

echo "This will erase the current database and restore from the backup. A backup of the current database will be created."
read -p "Are you sure? [Y/n] " response
if [[ "$response" =~ ^[Yy]$ ]]; then
  # Check if the backup file exists on the Docker machine
  log_message "Checking the existence of the backup file on the Docker machine..."
  if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file '$BACKUP_FILE' not found."
    exit 1
  fi

  # Stop the web container
  log_message "Stopping the web container..."
  docker compose stop web

  # Drop the existing database if it exists
  log_message "Dropping the existing database if it exists..."
  docker exec aieye-db dropdb -U "$DB_USER" --if-exists "$DB_NAME"
  check_command_status $? "Failed to drop the existing database."

  # Create a new database
  log_message "Creating a new database..."
  docker exec aieye-db createdb -U "$DB_USER" "$DB_NAME"
  check_command_status $? "Failed to create a new database."

  log_message "Restoring the database from the backup file... $BACKUP_FILE"
  docker exec -i aieye-db psql -U "$DB_USER" -d "$DB_NAME" <"$BACKUP_FILE"

  check_command_status $? "Failed to restore the database from the backup file."

  # Check if the restore was successful
  docker exec aieye-db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1
  check_command_status $? "Database restore check failed."

  # Display the restore status
  log_message "Database restore completed successfully."

  # Start the web container
  log_message "Starting the web container..."
  docker compose start web

else
  echo "Restore cancelled."
fi
