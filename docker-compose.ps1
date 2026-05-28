#Requires -Version 5.0

# Check if database file exists
if (Test-Path "db/ciso-assistant.sqlite3") {
    Write-Host "The database seems already created. You should launch 'docker compose up -d' instead." -ForegroundColor Yellow
    Write-Host "For a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting CISO Assistant services..." -ForegroundColor Cyan
docker compose pull

Write-Host ""
Write-Host "Waiting for CISO Assistant backend to be ready, please wait..." -ForegroundColor Cyan
docker compose up -d

do {
    $backendReady = $false
    try {
        $result = docker compose exec -T backend curl -f http://localhost:8000/api/health/ 2>$null
        if ($LASTEXITCODE -eq 0) {
            $backendReady = $true
        }
    }
    catch {
        Write-Host "Backend is not ready - waiting 10s..." -ForegroundColor Cyan
        Start-Sleep -Seconds 10
    }
} while (-not $backendReady)

Write-Host "Backend is ready!" -ForegroundColor Green

Write-Host ""
Write-Host "Creating superuser..." -ForegroundColor Cyan
docker compose exec backend poetry run python manage.py createsuperuser

Write-Host ""
Write-Host "Initialization complete!" -ForegroundColor Green
Write-Host "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)" -ForegroundColor Green
