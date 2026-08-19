param([Parameter(Mandatory = $true)][string]$Assets)
$ErrorActionPreference = 'Stop'
$Repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
& (Join-Path $Repository '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'verify.py') --assets $Assets
exit $LASTEXITCODE
