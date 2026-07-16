$ErrorActionPreference = "Stop"

python -m PyInstaller --noconfirm --clean .\StellarisModManager.spec

$packageRoot = Join-Path $PSScriptRoot "dist\StellarisModManager"
$packageBytes = (
    Get-ChildItem -LiteralPath $packageRoot -Recurse -File |
        Measure-Object -Property Length -Sum
).Sum
$packageMiB = [math]::Round($packageBytes / 1MB, 2)
$packageLimitMiB = 400

Write-Host "Build complete. Output folder: dist\StellarisModManager"
Write-Host "Packaged size: $packageMiB MiB (limit: $packageLimitMiB MiB)"

if ($packageBytes -gt ($packageLimitMiB * 1MB)) {
    throw "Packaged application exceeds the $packageLimitMiB MiB size budget."
}
