[CmdletBinding()]
param(
    [switch]$SkipWeb
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

Push-Location $repoRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $python = Get-Command python -ErrorAction Stop
        Write-Host "Creating Python environment at $venvRoot"
        & $python.Source -m venv $venvRoot
        if ($LASTEXITCODE -ne 0) { throw "Python environment creation failed with exit code $LASTEXITCODE." }
    }

    Write-Host "Installing TORUS Field Studio and Python development dependencies"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed with exit code $LASTEXITCODE." }
    & $venvPython -m pip install -e "${repoRoot}[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Python package installation failed with exit code $LASTEXITCODE." }

    if (-not $SkipWeb) {
        Write-Host "Installing browser dependencies with the repository-pinned pnpm version"
        $node = Get-Command node -ErrorAction SilentlyContinue
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
        $codexDependencies = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
        $codexNode = Join-Path $codexDependencies "node\bin\node.exe"
        $codexPnpm = Join-Path $codexDependencies "bin\fallback\pnpm.cmd"
        if ($npm -and $node) {
            & $npm.Source exec --yes --package=pnpm@11.19.0 -- pnpm install
            if ($LASTEXITCODE -ne 0) { throw "pnpm install failed with exit code $LASTEXITCODE." }
        }
        elseif ($pnpm -and $node) {
            & $pnpm.Source install
            if ($LASTEXITCODE -ne 0) { throw "pnpm install failed with exit code $LASTEXITCODE." }
        }
        elseif ((Test-Path -LiteralPath $codexNode) -and (Test-Path -LiteralPath $codexPnpm)) {
            $env:PATH = "$(Split-Path $codexNode);$env:PATH"
            & $codexPnpm install
            if ($LASTEXITCODE -ne 0) { throw "pnpm install failed with exit code $LASTEXITCODE." }
        }
        else {
            throw "Node.js/npm was not found. Install Node.js 24 or rerun with -SkipWeb for Python-only setup."
        }
    }

    Write-Host ""
    Write-Host "Setup complete. CLI: & .\.venv\Scripts\python.exe -m torusbrot.cli --help"
    if (-not $SkipWeb) {
        Write-Host "Studio: .\scripts\studio.ps1"
    }
}
finally {
    Pop-Location
}
