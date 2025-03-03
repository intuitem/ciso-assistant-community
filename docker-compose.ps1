#Requires -Version 5.0

# Check if database file exists
if (Test-Path "db/ciso-assistant.sqlite3") {
    Write-Output "The database seems already created. You should launch 'docker compose up -d' instead."
    Write-Output "`nFor a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over"
    exit 1
}

Write-Output "Starting CISO Assistant services..."
docker compose pull

Write-Output "Initializing the database. This can take a minute, please wait.."
docker compose up -d

Write-Output "Waiting for CISO Assistant backend to be ready..."
do {
    $backendReady = $false
    try {
        $result = docker compose exec -T backend curl -f http://localhost:8000/api/build 2>$null
        if ($LASTEXITCODE -eq 0) {
            $backendReady = $true
        }
    }
    catch {
        Write-Output "Backend is not ready - waiting 10s..."
        Start-Sleep -Seconds 10
    }
} while (-not $backendReady)

Write-Output "`nBackend is ready!"
Write-Output "Creating superuser..."
docker compose exec backend poetry run python manage.py createsuperuser

Write-Output "`nInitialization complete!"
Write-Output "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)"
