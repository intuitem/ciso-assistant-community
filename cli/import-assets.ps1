param(
    [string]$File = ".\sample_assets.csv",
    [string]$Folder = "Global",
    [ValidateSet("stop", "skip", "update")]
    [string]$OnConflict = "stop"
)

$pythonExe = "C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe"
    exit 1
}

Set-Location $PSScriptRoot

& $pythonExe clica.py import-assets --file $File --folder $Folder --on-conflict $OnConflict
