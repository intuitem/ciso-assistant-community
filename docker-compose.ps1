#! /usr/bin/env pwsh

# Check if the database file exists
if (Test-Path "db/ciso-assistant.sqlite3") {
    Write-Output "The database seems already created."
    Write-Output "You should launch docker-compose up -d."
    Write-Output "For a clean start, you can remove the database file, run docker-compose down and then docker-compose rm and start again."
} else {
    # Remove existing Docker images
    docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> $null
    # Bring up the Docker Compose services
    docker-compose up -d
    Write-Output "Giving some time for the database to be ready, please wait ..."
    Start-Sleep -Seconds 20
    Write-Output "Initialize your superuser account..."
    docker-compose exec backend python manage.py createsuperuser
    Write-Output "Connect to CISO Assistant on https://localhost:8443"
    Write-Output "For successive runs, you can now use docker-compose up."
}
