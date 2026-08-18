[CmdletBinding()]
param(
    [string]$Source
)

$ErrorActionPreference = 'Stop'
$Repository = Split-Path -Parent $PSScriptRoot
if (-not $Source) {
    $Source = Join-Path $Repository 'external_cache\heldout-v0.2.1\PRSA2017_Data_20130301-20170228.zip'
}
$Executable = Join-Path $Repository '.replication-venv\Scripts\torusbrot.exe'
if (-not (Test-Path -LiteralPath $Executable)) { throw 'Run replication\setup.ps1 first.' }
& $Executable fetch heldout-source --output $Source
