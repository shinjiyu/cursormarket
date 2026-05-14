<#
.SYNOPSIS
  Run Cursor agent stages 1–3 on a pipeline artifact (demo emit or custom JSON path).

.DESCRIPTION
  By default: emit demo JSON, then run_cursor_stage.ps1 for stages 1–3; each stage output is a UTF-8 Markdown file under artifacts/reports/.
  With -ArtifactPath: skip emit and use that file (e.g. output of gitlab_commits ingest).

.PARAMETER SkipEmit
  Do not regenerate demo JSON (reuse existing artifact path).

.PARAMETER Full
  Emit and analyze the five-project synthetic artifact (demo_pipeline_full.json) instead of the two-person minimal demo.

.PARAMETER WorkspaceRoot
  Repository root (default: two levels above this script).

.PARAMETER AgentPath
  Passed through to run_cursor_stage.ps1.

.PARAMETER ArtifactPath
  Use this JSON for stages 1–3 (relative to WorkspaceRoot if not absolute). Implies no demo emit; file must exist unless you also run ingest separately.
#>
param(
    [switch]$SkipEmit,
    [switch]$Full,
    [string]$WorkspaceRoot = "",
    [string]$AgentPath = "",
    [string]$ArtifactPath = ""
)

$ErrorActionPreference = "Stop"
# Agent prints UTF-8; avoid Tee-Object (writes UTF-16 LE on Windows PowerShell 5.x) -> mojibake when opened as UTF-8.
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

if ($ArtifactPath) {
    if ([System.IO.Path]::IsPathRooted($ArtifactPath)) {
        $artifact = $ArtifactPath
    }
    else {
        $artifact = [System.IO.Path]::Combine($WorkspaceRoot, $ArtifactPath)
    }
}
else {
    $artifactFile = if ($Full) { "demo_pipeline_full.json" } else { "demo_pipeline_input.json" }
    $artifact = [System.IO.Path]::Combine($WorkspaceRoot, "org_contributor_pipeline", "artifacts", "generated", $artifactFile)
}
$reportDir = [System.IO.Path]::Combine($WorkspaceRoot, "org_contributor_pipeline", "artifacts", "reports")
New-Item -ItemType Directory -Force -Path (Split-Path $artifact) | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

Push-Location $WorkspaceRoot
try {
    if (-not $ArtifactPath -and -not $SkipEmit) {
        if ($Full) {
            python -m org_contributor_pipeline.emit_demo_artifact --full -o $artifact
        }
        else {
            python -m org_contributor_pipeline.emit_demo_artifact -o $artifact
        }
    }
    if (-not (Test-Path -LiteralPath $artifact)) {
        throw "Artifact missing: $artifact (run without -SkipEmit)"
    }
    $runner = Join-Path $scriptDir "run_cursor_stage.ps1"
    foreach ($stage in 1..3) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $log = Join-Path $reportDir "stage-${stage}-${stamp}.md"
        Write-Host "=== Stage $stage -> $log ===" -ForegroundColor Cyan
        if ($AgentPath) {
            $raw = & $runner -Stage $stage -WorkspaceRoot $WorkspaceRoot -ArtifactPath $artifact -AgentPath $AgentPath 2>&1
        }
        else {
            $raw = & $runner -Stage $stage -WorkspaceRoot $WorkspaceRoot -ArtifactPath $artifact 2>&1
        }
        $logText = $raw | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                $_ | Out-String -Width 4096
            }
            else {
                "$_"
            }
        } | Out-String -Width 4096
        [System.IO.File]::WriteAllText($log, $logText.TrimEnd(), [System.Text.UTF8Encoding]::new($false))
        Write-Host $logText
    }
    Write-Host "Done. Reports under: $reportDir" -ForegroundColor Green
}
finally {
    Pop-Location
}
