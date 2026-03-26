# Script one-click pour importer tes assets

# 1. Renomme ce fichier en import-mes-assets.ps1 et place-le dans le dossier cli/
# 2. Prépare ton fichier CSV mes_assets.csv dans le dossier cli/
# 3. Lance simplement: .\import-mes-assets.ps1

$pythonExe = "C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe"
$csvFile = ".\mes_assets.csv"
$folder = "Global"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe"
    exit 1
}

if (-not (Test-Path $csvFile)) {
    Write-Error "CSV file not found: $csvFile`nVérifiez que le fichier mes_assets.csv existe dans le dossier cli/"
    exit 1
}

Set-Location $PSScriptRoot

Write-Host "Importation des assets depuis: $csvFile vers le domaine: $folder" -ForegroundColor Cyan
& $pythonExe clica.py import-assets --file $csvFile --folder $folder

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Importation réussie !" -ForegroundColor Green
} else {
    Write-Host "✗ Erreur lors de l'importation" -ForegroundColor Red
}
