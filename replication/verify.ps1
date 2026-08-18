[CmdletBinding()]
param(
    [string]$Source,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$Repository = Split-Path -Parent $PSScriptRoot
if (-not $Source) {
    $Source = Join-Path $Repository 'external_cache\heldout-v0.2.1\PRSA2017_Data_20130301-20170228.zip'
}
if (-not $Output) { $Output = Join-Path $Repository 'results\external-replication' }
$Python = Join-Path $Repository '.replication-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run replication\setup.ps1 first.' }
& $Python (Join-Path $PSScriptRoot 'verify.py') --source $Source --output $Output
