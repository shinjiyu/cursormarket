# cursor-agent-memory installer (Windows / PowerShell)
#
# What this does, in order:
#   1. pip install cursor-agent-memory  (or upgrade)
#   2. run a one-off export, so the shared folder is non-empty
#   3. merge cursor-agent-memory-logs into ~/.cursor/mcp.json (never destructive)
#   4. register an hourly Task Scheduler job that re-runs the sync
#
# Re-running this script is safe: every step is idempotent.
#
# Usage:
#   pwsh -File scripts/install.ps1                 # default
#   pwsh -File scripts/install.ps1 -SkipSchedule   # don't touch Task Scheduler
#   pwsh -File scripts/install.ps1 -Source git+https://github.com/shinjiyu/cursormarket.git
#       (install from Git instead of PyPI — useful while the package is unpublished)

[CmdletBinding()]
param(
    [string]$Source = "cursor-agent-memory",
    [string]$ExportDir = "$env:USERPROFILE\.cursor-agent-memory\export",
    [string]$McpServerName = "cursor-agent-memory-logs",
    [int]$IntervalHours = 1,
    [switch]$SkipSchedule,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Host "    $msg" -ForegroundColor Yellow }

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found on PATH. Install Python 3.10+ first (https://python.org/downloads)."
}

$pyVersion = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
Write-Step "Using Python $pyVersion"

Write-Step "Installing $Source via pip"
& python -m pip install --upgrade --quiet $Source
Write-Ok "Installed."

$syncCmd = (Get-Command cursor-agent-memory-sync -ErrorAction SilentlyContinue)
$mcpCmd  = (Get-Command cursor-agent-memory-mcp  -ErrorAction SilentlyContinue)
if (-not $syncCmd -or -not $mcpCmd) {
    Write-Warn2 "Console scripts not found on PATH; falling back to 'python -m'."
}

Write-Step "Running an initial export to $ExportDir"
$env:CURSOR_AGENT_MEMORY_EXPORT_DIR = $ExportDir
if ($syncCmd) {
    & cursor-agent-memory-sync --once
} else {
    & python -m cursor_agent_memory.sync_daemon --once
}
Write-Ok "Initial export done."

Write-Step "Wiring into ~/.cursor/mcp.json"
$cursorDir = Join-Path $env:USERPROFILE ".cursor"
if (-not (Test-Path $cursorDir)) { New-Item -ItemType Directory -Path $cursorDir | Out-Null }
$mcpPath = Join-Path $cursorDir "mcp.json"

$config = $null
if (Test-Path $mcpPath) {
    try {
        $raw = Get-Content $mcpPath -Raw -Encoding UTF8
        if ($raw.Trim()) { $config = $raw | ConvertFrom-Json -AsHashtable }
    } catch {
        if (-not $Force) {
            throw "Existing $mcpPath is not valid JSON. Re-run with -Force to overwrite, or fix it by hand."
        }
        Write-Warn2 "Existing mcp.json was unreadable; overwriting because -Force was given."
        $config = $null
    }
}
if ($null -eq $config) { $config = @{} }
if (-not $config.ContainsKey("mcpServers")) { $config["mcpServers"] = @{} }

$entry = @{
    env = @{ CURSOR_AGENT_MEMORY_EXPORT_DIR = $ExportDir }
}
if ($mcpCmd) {
    $entry["command"] = "cursor-agent-memory-mcp"
} else {
    $entry["command"] = "python"
    $entry["args"]    = @("-m", "cursor_agent_memory.mcp_server")
}

$existing = $config["mcpServers"][$McpServerName]
if ($existing -and -not $Force) {
    Write-Warn2 "mcpServers.$McpServerName already exists in $mcpPath; leaving it alone (use -Force to replace)."
} else {
    $config["mcpServers"][$McpServerName] = $entry
    $json = $config | ConvertTo-Json -Depth 8
    Set-Content -Path $mcpPath -Value $json -Encoding UTF8
    Write-Ok "Wrote $McpServerName entry to $mcpPath."
}

if ($SkipSchedule) {
    Write-Warn2 "Skipping Task Scheduler registration (-SkipSchedule)."
} else {
    Write-Step "Registering Task Scheduler job 'cursor-agent-memory-sync' (every $IntervalHours h)"
    $taskName = "cursor-agent-memory-sync"
    $cmdPath = if ($syncCmd) { $syncCmd.Source } else { (Get-Command python).Source }
    $args = if ($syncCmd) { "--once" } else { "-m cursor_agent_memory.sync_daemon --once" }
    $tr = "`"$cmdPath`" $args"
    & schtasks /Create /SC HOURLY /MO $IntervalHours /TN $taskName /TR $tr /F | Out-Null
    Write-Ok "Scheduled task '$taskName' installed."
}

Write-Host ""
Write-Host "All set. Restart Cursor, then in any chat:" -ForegroundColor Green
Write-Host "    @ -> MCP -> $McpServerName" -ForegroundColor Green
Write-Host "    'find the session where I…'" -ForegroundColor Green
Write-Host ""
Write-Host "Export dir: $ExportDir"
Write-Host "MCP config: $mcpPath"
