<#
.SYNOPSIS
  Run Cursor Agent CLI (agent) for org_contributor_pipeline prompt stages 1–3.

.DESCRIPTION
  Composes a prompt from AGENTS constraints + prompts/0x_*.md, then invokes:
    agent -p --mode=ask --workspace <repo-root> <prompt>
  Requires the Cursor CLI `agent` (PATH, ORG_CONTRIBUTOR_AGENT, or -AgentPath). See Authentication below.

.PARAMETER Stage
  1 = identity/scope, 2 = metrics→narrative, 3 = rubric alignment

.PARAMETER WorkspaceRoot
  Repository root (default: two levels above this script)

.PARAMETER ArtifactPath
  Optional path to a JSON/text file whose path is injected into the prompt (agent reads via tools)

.PARAMETER OutputFormat
  Passed to agent --output-format (e.g. text, json)

.PARAMETER AgentPath
  Full path to the `agent` executable if not on PATH. Overrides env ORG_CONTRIBUTOR_AGENT.

.EXAMPLE
  .\run_cursor_stage.ps1 -Stage 1
  .\run_cursor_stage.ps1 -Stage 2 -ArtifactPath D:\data\plugin_results.json
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 3)]
    [int]$Stage,

    [string]$WorkspaceRoot = "",

    [string]$ArtifactPath = "",

    [string]$OutputFormat = "text",

    [string]$AgentPath = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}
$names = @{
    1 = "01_identity_and_scope.md"
    2 = "02_metrics_to_narrative.md"
    3 = "03_rubric_alignment.md"
}
$promptPath = [System.IO.Path]::Combine($WorkspaceRoot, "org_contributor_pipeline", "prompts", $names[$Stage])
if (-not (Test-Path $promptPath)) {
    throw "Prompt not found: $promptPath"
}

$stageBody = Get-Content -LiteralPath $promptPath -Raw -Encoding UTF8
$header = @"
You are executing org_contributor_pipeline stage $Stage.
Follow the repository root AGENTS.md and .cursor/rules. Do not modify source files unless the user explicitly requests edits.
Output the full analysis in the reply.
"@

$artifactNote = ""
if ($ArtifactPath) {
    $ap = Resolve-Path -LiteralPath $ArtifactPath
    $artifactNote = "`n`n## Artifact file path (read with your tools as needed)`n$($ap.Path)`n"
}

$fullPrompt = "$header$artifactNote`n`n---`n`n$stageBody"

function Resolve-AgentExecutable {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path -LiteralPath $Explicit)) {
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $fromEnv = $env:ORG_CONTRIBUTOR_AGENT
    if ($fromEnv -and (Test-Path -LiteralPath $fromEnv)) {
        return (Resolve-Path -LiteralPath $fromEnv).Path
    }
    $cmd = Get-Command agent -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        "$env:USERPROFILE\.local\bin\agent.exe",
        "$env:USERPROFILE\.local\bin\agent.cmd",
        "$env:LOCALAPPDATA\Programs\cursor\resources\app\bin\agent.exe",
        "$env:LOCALAPPDATA\Programs\cursor\resources\app\bin\agent.cmd"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) {
            return (Resolve-Path -LiteralPath $c).Path
        }
    }
    return $null
}

$agentExe = Resolve-AgentExecutable -Explicit $AgentPath
if (-not $agentExe) {
    throw @"
Cursor CLI 'agent' not found. Install: irm 'https://cursor.com/install?win32=true' | iex
Then re-open the terminal, or set ORG_CONTRIBUTOR_AGENT to the full path of agent.exe / agent.cmd.
Docs: https://cursor.com/docs/cli/installation
"@
}

Push-Location $WorkspaceRoot
try {
    if ($OutputFormat) {
        & $agentExe -p --mode=ask --workspace $WorkspaceRoot --trust --output-format $OutputFormat $fullPrompt
    }
    else {
        & $agentExe -p --mode=ask --workspace $WorkspaceRoot --trust $fullPrompt
    }
}
finally {
    Pop-Location
}
