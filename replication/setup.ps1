[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Repository = Split-Path -Parent $PSScriptRoot
$Environment = Join-Path $Repository '.replication-venv'
$Distribution = Join-Path $Repository 'dist'

Set-Location -LiteralPath $Repository
python -m venv $Environment
$Python = Join-Path $Environment 'Scripts\python.exe'
& $Python -m pip install --disable-pip-version-check --requirement (Join-Path $PSScriptRoot 'environment_lock')
& $Python -m build
$Wheel = Get-ChildItem -LiteralPath $Distribution -Filter 'torusbrot-*.whl' |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if ($null -eq $Wheel) { throw 'No TORUS wheel was built.' }
& $Python -m pip install --disable-pip-version-check --no-deps --force-reinstall $Wheel.FullName
& (Join-Path $Environment 'Scripts\torusbrot.exe') --help | Out-Null
Write-Host "Installed replication wheel: $($Wheel.Name)"
