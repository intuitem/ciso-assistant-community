#Requires -Version 5.1

# Starts the CISO Assistant backend with the right native Windows development
# settings. Place this script at the root of the CISO Assistant community
# project, next to the backend/ directory.

$ErrorActionPreference = "Stop"

# Parse arguments
$UsePostgres = $false
$UseEnterprise = $false
$CreateSuperuserOnly = $false
$MigrateOnly = $false
$RunserverOnly = $false
$UnknownArguments = @()

foreach ($argument in $args) {
    switch ($argument) {
        "-p" {
            $UsePostgres = $true
        }
        "--pg" {
            $UsePostgres = $true
        }
        "-z" {
            $UseEnterprise = $true
        }
        "--enterprise" {
            $UseEnterprise = $true
        }
        "-c" {
            $CreateSuperuserOnly = $true
        }
        "--createsuperuser" {
            $CreateSuperuserOnly = $true
        }
        "-m" {
            $MigrateOnly = $true
        }
        "--migrate" {
            $MigrateOnly = $true
        }
        "-r" {
            $RunserverOnly = $true
        }
        "--runserver" {
            $RunserverOnly = $true
        }
        default {
            $UnknownArguments += $argument
        }
    }
}

if ($UnknownArguments.Count -gt 0) {
    throw "Unknown argument(s): $($UnknownArguments -join ', '). Supported arguments: -p, --pg, -z, --enterprise, -c, --createsuperuser, -m, --migrate, -r, --runserver."
}

if (
    ($CreateSuperuserOnly -and $MigrateOnly) -or
    ($CreateSuperuserOnly -and $RunserverOnly) -or
    ($MigrateOnly -and $RunserverOnly)
) {
    throw "Arguments -c/--createsuperuser, -m/--migrate and -r/--runserver cannot be used together."
}

$ProjectDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$BackendDir = Join-Path $ProjectDir "backend"
$ManageWorkingDir = $BackendDir
$ManagePy = "manage.py"
$ManageSettingsArguments = @()

# Put the path to the Python executable that should run Django here. A local
# .venv is recommended because it keeps dependencies isolated and makes this
# path predictable.
$PythonRelativeExecutablePath = ".venv\Scripts\python.exe"
$PythonExecutablePath = Join-Path $ProjectDir $PythonRelativeExecutablePath

# Compatibility fallback for local workspaces where the virtual environment is
# stored one directory above the CISO Assistant repository.
$ParentPythonExecutablePath = Join-Path (Split-Path -Parent $ProjectDir) $PythonRelativeExecutablePath
$SelectedPythonExecutablePath = if (Test-Path -LiteralPath $PythonExecutablePath -PathType Leaf) {
    $PythonExecutablePath
}
else {
    $ParentPythonExecutablePath
}

$RunserverScript = Join-Path $BackendDir ".win_native_dev_runserver.py"

if ($UseEnterprise) {
    $ManageWorkingDir = Join-Path $ProjectDir "enterprise\backend"
    $ManagePy = Join-Path $BackendDir "manage.py"
    $EnterpriseSettings = "enterprise_core.settings"
    $ManageSettingsArguments = @("--settings=$EnterpriseSettings")
}

# Sets or removes one process-level environment variable.
function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,

        [AllowNull()]
        [string] $Value
    )

    if ([string]::IsNullOrEmpty($Value)) {
        Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
        return
    }

    Set-Item -LiteralPath "Env:$Name" -Value $Value
}

# Runs a command with temporary environment variables, then restores the previous
# process environment so migrations and runserver do not leak settings globally.
function Invoke-WithEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Environment,

        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [string[]] $ArgumentList = @(),

        [string] $CommandName = ""
    )

    $previousValues = @{}
    foreach ($name in $Environment.Keys) {
        $previousValues[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    }

    try {
        foreach ($entry in $Environment.GetEnumerator()) {
            Set-EnvValue -Name $entry.Key -Value $entry.Value
        }

        & $FilePath @ArgumentList
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            if ([string]::IsNullOrEmpty($CommandName)) {
                $CommandName = "$FilePath $($ArgumentList -join ' ')"
            }

            throw "$CommandName failed with exit code $exitCode."
        }
    }
    finally {
        foreach ($name in $previousValues.Keys) {
            Set-EnvValue -Name $name -Value $previousValues[$name]
        }
    }
}

# Validate local paths
if (-not (Test-Path -LiteralPath $BackendDir -PathType Container)) {
    throw "Backend directory not found: $BackendDir"
}

if (-not (Test-Path -LiteralPath $ManageWorkingDir -PathType Container)) {
    throw "Django working directory not found: $ManageWorkingDir"
}

if (-not (Test-Path -LiteralPath $SelectedPythonExecutablePath -PathType Leaf)) {
    throw "Python executable not found: $SelectedPythonExecutablePath"
}

if (($RunserverOnly -or (-not $CreateSuperuserOnly -and -not $MigrateOnly)) -and -not (Test-Path -LiteralPath $RunserverScript -PathType Leaf)) {
    throw "Windows development runserver script not found: $RunserverScript"
}

$MigrateEnvironment = @{
    DJANGO_DEBUG = "True"
}

# Django's default development server listen backlog is 10, which can refuse
# SvelteKit SSR connection bursts on Windows before requests reach Django.
$RunserverBacklog = if ($env:DJANGO_RUNSERVER_BACKLOG) { $env:DJANGO_RUNSERVER_BACKLOG } else { "512" }
$RunserverEnvironment = @{
    DJANGO_DEBUG = "True"
    LOG_LEVEL = "INFO"
    DJANGO_RUNSERVER_BACKLOG = $RunserverBacklog
}

if ($UseEnterprise) {
    $PythonPathValue = if ($env:PYTHONPATH) {
        "$ManageWorkingDir$([IO.Path]::PathSeparator)$env:PYTHONPATH"
    }
    else {
        $ManageWorkingDir
    }

    $EnterpriseEnvironment = @{
        ENTERPRISE_SETTINGS = $EnterpriseSettings
        PYTHONPATH = $PythonPathValue
    }

    foreach ($entry in $EnterpriseEnvironment.GetEnumerator()) {
        $MigrateEnvironment[$entry.Key] = $entry.Value
        $RunserverEnvironment[$entry.Key] = $entry.Value
    }
}

if ($UsePostgres) {
    $PostgresEnvironment = @{
        POSTGRES_NAME = "ciso-assistant"
        POSTGRES_USER = "ciso-assistantuser"
        POSTGRES_PASSWORD = "<XXX>"
        DB_HOST = "localhost"
        DB_PORT = "5432"
    }

    foreach ($entry in $PostgresEnvironment.GetEnumerator()) {
        $MigrateEnvironment[$entry.Key] = $entry.Value
        $RunserverEnvironment[$entry.Key] = $entry.Value
    }
}

Push-Location -LiteralPath $ManageWorkingDir
try {
    $CreateSuperuserArguments = @($ManagePy, "createsuperuser") + $ManageSettingsArguments
    $MigrateArguments = @($ManagePy, "migrate") + $ManageSettingsArguments
    $RunserverArguments = @($RunserverScript) + $ManageSettingsArguments

    if ($CreateSuperuserOnly) {
        Invoke-WithEnvironment -Environment $MigrateEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList $CreateSuperuserArguments -CommandName "manage.py createsuperuser"
        return
    }

    if ($MigrateOnly) {
        Invoke-WithEnvironment -Environment $MigrateEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList $MigrateArguments -CommandName "manage.py migrate"
        return
    }

    if ($RunserverOnly) {
        Invoke-WithEnvironment -Environment $RunserverEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList $RunserverArguments -CommandName "manage.py runserver"
        return
    }

    # Run from the selected Django working directory so relative paths resolve like Django expects.
    Invoke-WithEnvironment -Environment $MigrateEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList $MigrateArguments -CommandName "manage.py migrate"
    Invoke-WithEnvironment -Environment $RunserverEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList $RunserverArguments -CommandName "manage.py runserver"
}
finally {
    Pop-Location
}
