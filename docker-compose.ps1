#Requires -Version 5.0

$DockerComposeFile = "docker-compose.yml"
$MigrationCheckAttempts = 60
$MigrationCheckDelaySeconds = 10

function Wait-ForMigrations {
    for ($i = 1; $i -le $MigrationCheckAttempts; $i++) {
        & docker compose -f $DockerComposeFile exec -T backend uv run python manage.py migrate --check *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Migrations complete!" -ForegroundColor Green
            return
        }

        if ($i -eq $MigrationCheckAttempts) {
            $timeoutSeconds = $MigrationCheckAttempts * $MigrationCheckDelaySeconds
            Write-Host "Migrations did not complete within ${timeoutSeconds}s. Recent backend logs:" -ForegroundColor Red
            docker compose -f $DockerComposeFile logs --tail=50 backend
            exit 1
        }

        Start-Sleep -Seconds $MigrationCheckDelaySeconds
    }
}

if (-not (Test-Path -Path $DockerComposeFile -PathType Leaf)) {
    Write-Host "Compose file not found: $DockerComposeFile" -ForegroundColor Red
    exit 1
}

# Check if database file exists
if (Test-Path "db/ciso-assistant.sqlite3") {
    Write-Host "The database seems already created. You should launch 'docker compose up -d' instead." -ForegroundColor Yellow
    Write-Host "For a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting CISO Assistant services..." -ForegroundColor Cyan
docker compose -f $DockerComposeFile pull

Write-Host ""
Write-Host "Giving some time for the database to be ready, please wait..." -ForegroundColor Cyan
docker compose -f $DockerComposeFile up -d
Wait-ForMigrations

Write-Host ""
Write-Host "Creating superuser..." -ForegroundColor Cyan
docker compose -f $DockerComposeFile exec backend uv run python manage.py createsuperuser

Write-Host ""
Write-Host "Initialization complete!" -ForegroundColor Green
Write-Host "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)" -ForegroundColor Green
