[CmdletBinding()]
param(
    [string]$Source,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$Repository = Split-Path -Parent $PSScriptRoot
$Study = Join-Path $Repository 'studies\heldout-v0.2.1'
if (-not $Source) {
    $Source = Join-Path $Repository 'external_cache\heldout-v0.2.1\PRSA2017_Data_20130301-20170228.zip'
}
if (-not $Output) { $Output = Join-Path $Repository 'results\external-replication' }
$Executable = Join-Path $Repository '.replication-venv\Scripts\torusbrot.exe'
if (-not (Test-Path -LiteralPath $Executable)) { throw 'Run replication\setup.ps1 first.' }
if (-not (Test-Path -LiteralPath $Source)) { throw 'Run replication\fetch.ps1 first.' }
$Marker = Join-Path $Output 'scored\.scored_execution_started'
if (Test-Path -LiteralPath $Marker) {
    throw "This attempt has already started. Preserve it and choose a new -Output path: $Output"
}

$Materialized = Join-Path $Output 'materialized'
$Scored = Join-Path $Output 'scored'
$Verification = Join-Path $Output 'verification'
$Adjudication = Join-Path $Output 'adjudication'
$Publication = Join-Path $Output 'publication'
$Bundles = Join-Path $Output 'bundles'
$ImplementationCommit = 'v0.2.1-source-archive'
try {
    $ImplementationCommit = (git -C $Repository rev-parse HEAD).Trim()
} catch {
    Write-Verbose 'Git metadata unavailable; using source-archive identity.'
}

& $Executable materialize heldout-study --source $Source --study $Study --output $Materialized
& $Executable authorize heldout-study --materialized $Materialized --study $Study --output $Scored `
    --preregistration-commit f15422bc64b1b101150240e612621683b15b3606 `
    --implementation-commit $ImplementationCommit
& $Executable execute heldout-study --materialized $Materialized --study $Study --output $Scored
& $Executable verify heldout-study --materialized $Materialized --study $Study --scored $Scored --output $Verification
& $Executable adjudicate heldout-study --scored $Scored --verification $Verification --output $Adjudication
& $Executable publish heldout-study --scored $Scored --verification $Verification --adjudication $Adjudication --output $Publication
& $Executable package heldout-study --study $Study --materialized $Materialized --scored $Scored `
    --verification $Verification --adjudication $Adjudication --publication $Publication --output $Bundles
& (Join-Path $Repository '.replication-venv\Scripts\python.exe') `
    (Join-Path $PSScriptRoot 'verify.py') --source $Source --output $Output
