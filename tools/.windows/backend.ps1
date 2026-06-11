#Requires -Version 5.1

# Starts the CISO Assistant backend with the right native Windows development
# settings. Place this script at the root of the CISO Assistant project, next to
# the backend/ directory.

$ErrorActionPreference = "Stop"

$ProjectDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$BackendDir = Join-Path $ProjectDir "backend"

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

if (-not (Test-Path -LiteralPath $BackendDir -PathType Container)) {
    throw "Backend directory not found: $BackendDir"
}

if (-not (Test-Path -LiteralPath $SelectedPythonExecutablePath -PathType Leaf)) {
    throw "Python executable not found: $SelectedPythonExecutablePath"
}

if (-not (Test-Path -LiteralPath $RunserverScript -PathType Leaf)) {
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

Push-Location -LiteralPath $BackendDir
try {
    # Run from backend/ so manage.py and relative paths resolve like Django expects.
    Invoke-WithEnvironment -Environment $MigrateEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList @("manage.py", "migrate") -CommandName "manage.py migrate"
    Invoke-WithEnvironment -Environment $RunserverEnvironment -FilePath $SelectedPythonExecutablePath -ArgumentList @($RunserverScript) -CommandName "manage.py runserver"
}
finally {
    Pop-Location
}
