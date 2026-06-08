#Requires -Version 5.0

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DockerComposeFile = "docker-compose-build.yml"
$MigrationCheckAttempts = 60
$MigrationCheckDelaySeconds = 10

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [string[]] $Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Invoke-DockerCompose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]] $Arguments
    )

    $composeArguments = @("compose", "-f", $DockerComposeFile) + $Arguments
    Invoke-Checked -FilePath "docker" -Arguments $composeArguments
}

function Prepare-MetaFile {
    $version = (& git describe --tags --always)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine CISO Assistant version with git describe."
    }

    $build = (& git rev-parse --short HEAD)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine CISO Assistant build with git rev-parse."
    }

    $meta = "CISO_ASSISTANT_VERSION=$version`nCISO_ASSISTANT_BUILD=$build`n"
    [System.IO.File]::WriteAllText((Join-Path (Get-Location) ".meta"), $meta, [System.Text.Encoding]::ASCII)
    Copy-Item -Path ".meta" -Destination ".\backend\ciso_assistant\.meta" -Force
    Copy-Item -Path ".meta" -Destination ".\backend\.meta" -Force
}

function Wait-ForMigrations {
    for ($i = 1; $i -le $MigrationCheckAttempts; $i++) {
        & docker compose -f $DockerComposeFile exec -T backend poetry run python manage.py migrate --check *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Migrations complete!" -ForegroundColor Green
            return
        }

        if ($i -eq $MigrationCheckAttempts) {
            $timeoutSeconds = $MigrationCheckAttempts * $MigrationCheckDelaySeconds
            Write-Host "Migrations did not complete within ${timeoutSeconds}s. Recent backend logs:" -ForegroundColor Red
            Invoke-DockerCompose logs --tail=50 backend
            exit 1
        }

        Start-Sleep -Seconds $MigrationCheckDelaySeconds
    }
}

Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -Path $DockerComposeFile -PathType Leaf)) {
        throw "Compose file not found: $DockerComposeFile"
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git was not found in PATH."
    }

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker was not found in PATH."
    }

    $env:DOCKER_BUILDKIT = "1"
    $env:COMPOSE_DOCKER_CLI_BUILD = "1"

    if (Test-Path -Path "db\ciso-assistant.sqlite3" -PathType Leaf) {
        Write-Host "The database seems already created." -ForegroundColor Yellow
        Write-Host "For successive runs, you can now use `"docker compose up`"." -ForegroundColor Yellow
        exit 0
    }

    Prepare-MetaFile

    Write-Host "Building containers..." -ForegroundColor Cyan
    Invoke-DockerCompose build --pull

    New-Item -Path ".\db" -ItemType Directory -Force | Out-Null

    Write-Host ""
    Write-Host "Starting services..." -ForegroundColor Cyan
    Invoke-DockerCompose up --detach

    Write-Host ""
    Write-Host "Giving some time for the database to be ready, please wait..." -ForegroundColor Cyan
    Wait-ForMigrations

    Write-Host ""
    Write-Host "Initialize your superuser account..." -ForegroundColor Cyan
    # Keep TTY allocation for the interactive Django prompts in Windows terminals.
    Invoke-DockerCompose exec backend poetry run python manage.py createsuperuser

    Write-Host ""
    Write-Host "CISO Assistant is ready!" -ForegroundColor Green
    Write-Host "Connect to CISO Assistant on `"https://localhost:8443`"" -ForegroundColor Green
    Write-Host "For successive runs, you can now use `"docker compose up`"" -ForegroundColor Green
    Write-Host "If the webpage doesn't load, please wait 2-3 minutes" -ForegroundColor Green
}
finally {
    Pop-Location
}
