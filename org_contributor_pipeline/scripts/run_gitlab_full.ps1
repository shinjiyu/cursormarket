<#
.SYNOPSIS
  GitLab group ingest + org_contributor stages 1–3.

.DESCRIPTION
  Configuration: load ``<WorkspaceRoot>/.env`` inside Python (GITLAB_TOKEN, GITLAB_URL, GITLAB_TOKEN_FILE, etc.).
  Optional: ``.secrets/gitlab_token`` (first line only); if present, passed as ``--token-file`` and overrides .env token.

.PARAMETER Group
  GitLab group path (e.g. h5_game_sh_tpe)

.PARAMETER Since
  ISO8601 since (inclusive)

.PARAMETER Until
  ISO8601 until (GitLab exclusive)

.PARAMETER WorkspaceRoot
  Repo root (default: two levels above this script)

.PARAMETER AllBranches
  Pass through to ingest --all-branches

.PARAMETER AgentPath
  Passed to run_automated_stages.ps1
#>
param(
    [string]$Group = "h5_game_sh_tpe",
    [string]$Since = "2026-03-01T00:00:00Z",
    [string]$Until = "2026-05-13T00:00:00Z",
    [string]$WorkspaceRoot = "",
    [switch]$AllBranches,
    [string]$AgentPath = ""
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

$envPath = [System.IO.Path]::Combine($WorkspaceRoot, ".env")
$tokenFile = [System.IO.Path]::Combine($WorkspaceRoot, ".secrets", "gitlab_token")
if (-not (Test-Path -LiteralPath $envPath) -and -not (Test-Path -LiteralPath $tokenFile)) {
    throw "Need $envPath (e.g. GITLAB_TOKEN=...) or $tokenFile (one-line PAT)."
}

$out = [System.IO.Path]::Combine($WorkspaceRoot, "org_contributor_pipeline", "artifacts", "generated", "gitlab_group_ingest.json")

Push-Location $WorkspaceRoot
try {
    $ingestArgs = @(
        "-m", "org_contributor_pipeline.ingest.gitlab_commits",
        "--group", $Group,
        "--since", $Since,
        "--until", $Until,
        "-o", $out
    )
    if (Test-Path -LiteralPath $tokenFile) {
        $ingestArgs += @("--token-file", $tokenFile)
    }
    if ($AllBranches) {
        $ingestArgs += "--all-branches"
    }
    Write-Host "=== GitLab ingest -> $out ===" -ForegroundColor Cyan
    & python @ingestArgs
    if ($LASTEXITCODE -ne 0) {
        throw "ingest exited $LASTEXITCODE"
    }

    $auto = Join-Path $scriptDir "run_automated_stages.ps1"
    Write-Host "=== Stages 1-3 ===" -ForegroundColor Cyan
    if ($AgentPath) {
        & $auto -SkipEmit -ArtifactPath $out -AgentPath $AgentPath
    }
    else {
        & $auto -SkipEmit -ArtifactPath $out
    }
}
finally {
    Pop-Location
}
