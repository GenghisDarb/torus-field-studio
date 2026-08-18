[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
$codexDependencies = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$codexNode = Join-Path $codexDependencies "node\bin\node.exe"
$codexPnpm = Join-Path $codexDependencies "bin\fallback\pnpm.cmd"

Push-Location $repoRoot
try {
    if ($npm -and $node) {
        & $npm.Source exec --yes --package=pnpm@11.19.0 -- pnpm run dev
        if ($LASTEXITCODE -ne 0) { throw "Studio process failed with exit code $LASTEXITCODE." }
    }
    elseif ($pnpm -and $node) {
        & $pnpm.Source run dev
        if ($LASTEXITCODE -ne 0) { throw "Studio process failed with exit code $LASTEXITCODE." }
    }
    elseif ((Test-Path -LiteralPath $codexNode) -and (Test-Path -LiteralPath $codexPnpm)) {
        $env:PATH = "$(Split-Path $codexNode);$env:PATH"
        & $codexPnpm run dev
        if ($LASTEXITCODE -ne 0) { throw "Studio process failed with exit code $LASTEXITCODE." }
    }
    else {
        throw "Node.js/npm was not found. Install Node.js 24 before starting the browser studio."
    }
}
finally {
    Pop-Location
}
