#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$ProjectDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$FrontendDir = Join-Path $ProjectDir "frontend"
$BackendDir = Join-Path $ProjectDir "backend"
$EnterpriseFrontendSrcDir = Join-Path $ProjectDir "enterprise\frontend\src"
$EnterpriseBackendDir = Join-Path $ProjectDir "enterprise\backend"


# External commands do not always throw in PowerShell when they fail, so this
# helper stops the script on a non-zero exit code and avoids false success.
function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [string[]] $ArgumentList = @(),

        [string] $CommandName = ""
    )

    & $FilePath @ArgumentList
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        if ([string]::IsNullOrEmpty($CommandName)) {
            $CommandName = "$FilePath $($ArgumentList -join ' ')"
        }

        throw "$CommandName failed with exit code $exitCode."
    }
}

function Invoke-InDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Directory,

        [Parameter(Mandatory = $true)]
        [scriptblock] $ScriptBlock
    )

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        throw "Directory not found: $Directory"
    }

    Push-Location -LiteralPath $Directory
    try {
        & $ScriptBlock
    }
    finally {
        Pop-Location
    }
}



Invoke-InDirectory -Directory $FrontendDir -ScriptBlock {
    Write-Host "Formatting frontend..." -ForegroundColor Cyan
    Invoke-CheckedCommand -FilePath "pnpm" -ArgumentList @("exec", "prettier", ".", "--write") -CommandName "pnpm exec prettier . --write"

    Write-Host "`nFormatting enterprise frontend..." -ForegroundColor Cyan
    Invoke-CheckedCommand -FilePath "pnpm" -ArgumentList @("exec", "prettier", $EnterpriseFrontendSrcDir, "--write") -CommandName "pnpm exec prettier enterprise frontend --write"
}

Invoke-InDirectory -Directory $BackendDir -ScriptBlock {
    Write-Host "`nFormatting backend..." -ForegroundColor Cyan
    Invoke-CheckedCommand -FilePath "ruff" -ArgumentList @("format", ".") -CommandName "ruff format backend"
}

Invoke-InDirectory -Directory $EnterpriseBackendDir -ScriptBlock {
    Write-Host "`nFormatting enterprise backend..." -ForegroundColor Cyan
    Invoke-CheckedCommand -FilePath "ruff" -ArgumentList @("format", ".") -CommandName "ruff format enterprise backend"
}
