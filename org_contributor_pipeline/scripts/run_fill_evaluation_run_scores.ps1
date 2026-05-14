<#
.SYNOPSIS
  Fill mandatory L2 scores via Cursor agent, then merge (UTF-8 safe).

.DESCRIPTION
  Delegates to: python -m org_contributor_pipeline.run_fill_evaluation_scores
  so agent stdout is not corrupted by PowerShell encoding.

.PARAMETER EvaluationRunPath
  Path to evaluation_run.v1 JSON.

.PARAMETER WorkspaceRoot
  Repo root (default: two levels above this script).

.PARAMETER LogPath
  Optional agent log path.

.PARAMETER EmbedEvaluationJson
    If set, passes --embed-evaluation-json to Python (embed full evaluation_run in the spooled prompt).

.PARAMETER ScoredOutPath
  Optional merged output path.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$EvaluationRunPath,

    [string]$WorkspaceRoot = "",

    [string]$LogPath = "",

    [string]$ScoredOutPath = "",

    [switch]$EmbedEvaluationJson = $false
)

$ErrorActionPreference = "Stop"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}
$evalPath = (Resolve-Path -LiteralPath $EvaluationRunPath).Path

$args = @(
    "-m", "org_contributor_pipeline.run_fill_evaluation_scores",
    "-e", $evalPath,
    "-w", $WorkspaceRoot
)
if ($LogPath) { $args += @("-l", $LogPath) }
if ($ScoredOutPath) { $args += @("-o", $ScoredOutPath) }
if ($EmbedEvaluationJson) { $args += "--embed-evaluation-json" }

Push-Location $WorkspaceRoot
try {
    & python @args
}
finally {
    Pop-Location
}
