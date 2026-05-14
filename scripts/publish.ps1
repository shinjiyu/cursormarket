# Build (and optionally upload) the public `cursor-agent-memory` PyPI package.
#
# Usage:
#   pwsh -File scripts/publish.ps1                       # build only, into packaging/cursor-agent-memory/dist/
#   pwsh -File scripts/publish.ps1 -Check                # also run twine check
#   pwsh -File scripts/publish.ps1 -Upload testpypi      # build + check + upload to TestPyPI
#   pwsh -File scripts/publish.ps1 -Upload pypi          # build + check + upload to real PyPI
#
# Requires:  python -m pip install --upgrade build twine

[CmdletBinding()]
param(
    [switch]$Check,
    [ValidateSet('', 'testpypi', 'pypi')]
    [string]$Upload = ''
)

$ErrorActionPreference = "Stop"

function Invoke-Native {
    param([Parameter(Mandatory)][scriptblock]$Action, [string]$Label)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Action
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($LASTEXITCODE -ne 0) {
        throw "$Label exited with code $LASTEXITCODE"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$pkgDir   = Join-Path $repoRoot "packaging\cursor-agent-memory"
$srcPkg   = Join-Path $repoRoot "cursor_agent_memory"
$srcReadme= Join-Path $repoRoot "README.md"
$srcLicense = Join-Path $repoRoot "LICENSE"

if (-not (Test-Path $srcPkg))     { throw "missing $srcPkg" }
if (-not (Test-Path $srcReadme))  { throw "missing $srcReadme" }
if (-not (Test-Path $srcLicense)) { throw "missing $srcLicense" }

Write-Host "==> Staging cursor_agent_memory + README + LICENSE into $pkgDir" -ForegroundColor Cyan
Remove-Item -Recurse -Force (Join-Path $pkgDir "cursor_agent_memory") -ErrorAction SilentlyContinue
Remove-Item            -Force (Join-Path $pkgDir "README.md")          -ErrorAction SilentlyContinue
Remove-Item            -Force (Join-Path $pkgDir "LICENSE")            -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $pkgDir "build")               -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $pkgDir "dist")                -ErrorAction SilentlyContinue
Get-ChildItem $pkgDir -Filter "*.egg-info" -Directory | Remove-Item -Recurse -Force

Copy-Item $srcReadme  (Join-Path $pkgDir "README.md")
Copy-Item $srcLicense (Join-Path $pkgDir "LICENSE")
Copy-Item -Recurse $srcPkg (Join-Path $pkgDir "cursor_agent_memory")
Get-ChildItem -Recurse -Force (Join-Path $pkgDir "cursor_agent_memory") -Filter "__pycache__" -Directory |
    Remove-Item -Recurse -Force

Write-Host "==> python -m build" -ForegroundColor Cyan
Push-Location $pkgDir
try {
    Invoke-Native -Label "python -m build" { & python -m build }
    if ($Check -or $Upload) {
        Write-Host "==> twine check" -ForegroundColor Cyan
        Invoke-Native -Label "twine check" { & python -m twine check (Join-Path "dist" "*") }
    }
    if ($Upload) {
        $repoArg = if ($Upload -eq 'testpypi') { @('--repository','testpypi') } else { @() }
        Write-Host "==> twine upload $Upload" -ForegroundColor Cyan
        Invoke-Native -Label "twine upload" { & python -m twine upload @repoArg (Join-Path "dist" "*") }
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Artifacts in: $(Join-Path $pkgDir 'dist')" -ForegroundColor Green
