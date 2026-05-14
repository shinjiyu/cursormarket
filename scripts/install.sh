#!/usr/bin/env bash
# cursor-agent-memory installer (macOS / Linux)
#
# What this does, in order:
#   1. pip install cursor-agent-memory  (or upgrade)
#   2. run a one-off export, so the shared folder is non-empty
#   3. merge cursor-agent-memory-logs into ~/.cursor/mcp.json (never destructive)
#   4. add an hourly cron line that re-runs the sync
#
# Re-running this script is safe: every step is idempotent.
#
# Usage:
#   bash scripts/install.sh                       # default
#   bash scripts/install.sh --skip-schedule       # don't touch cron
#   bash scripts/install.sh --source git+https://github.com/shinjiyu/cursormarket.git
#       (install from Git instead of PyPI — useful while the package is unpublished)

set -euo pipefail

SOURCE="cursor-agent-memory"
EXPORT_DIR="${HOME}/.cursor-agent-memory/export"
MCP_NAME="cursor-agent-memory-logs"
INTERVAL_HOURS=1
SKIP_SCHEDULE=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)         SOURCE="$2"; shift 2 ;;
    --export-dir)     EXPORT_DIR="$2"; shift 2 ;;
    --mcp-name)       MCP_NAME="$2"; shift 2 ;;
    --interval-hours) INTERVAL_HOURS="$2"; shift 2 ;;
    --skip-schedule)  SKIP_SCHEDULE=1; shift ;;
    --force)          FORCE=1; shift ;;
    -h|--help)
      sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

step() { printf "\033[36m==> %s\033[0m\n" "$*"; }
ok()   { printf "\033[32m    %s\033[0m\n" "$*"; }
warn() { printf "\033[33m    %s\033[0m\n" "$*"; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ first." >&2; exit 1
fi
PY=$(command -v python3)

PY_VER=$("$PY" -c "import sys; print('%d.%d' % sys.version_info[:2])")
step "Using Python ${PY_VER} (${PY})"

step "Installing ${SOURCE} via pip"
"$PY" -m pip install --upgrade --quiet "$SOURCE"
ok "Installed."

SYNC_CMD=$(command -v cursor-agent-memory-sync || true)
MCP_CMD=$(command -v cursor-agent-memory-mcp || true)
if [[ -z "$SYNC_CMD" || -z "$MCP_CMD" ]]; then
  warn "Console scripts not on PATH; will fall back to 'python -m'."
fi

step "Running an initial export to ${EXPORT_DIR}"
export CURSOR_AGENT_MEMORY_EXPORT_DIR="${EXPORT_DIR}"
if [[ -n "$SYNC_CMD" ]]; then
  "$SYNC_CMD" --once
else
  "$PY" -m cursor_agent_memory.sync_daemon --once
fi
ok "Initial export done."

step "Wiring into ~/.cursor/mcp.json"
mkdir -p "${HOME}/.cursor"
MCP_PATH="${HOME}/.cursor/mcp.json"

# Merge JSON via python so we never clobber other servers the user has.
"$PY" - "$MCP_PATH" "$MCP_NAME" "$EXPORT_DIR" "${MCP_CMD:-}" "$FORCE" <<'PYEOF'
import json, os, sys
mcp_path, mcp_name, export_dir, mcp_cmd, force = sys.argv[1:6]
force = force == "1"

config = {}
if os.path.exists(mcp_path):
    try:
        with open(mcp_path, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
            config = json.loads(text) if text else {}
    except json.JSONDecodeError:
        if not force:
            sys.stderr.write(
                f"Existing {mcp_path} is not valid JSON. Re-run with --force to overwrite.\n"
            )
            sys.exit(3)
        config = {}

config.setdefault("mcpServers", {})
entry = {"env": {"CURSOR_AGENT_MEMORY_EXPORT_DIR": export_dir}}
if mcp_cmd:
    entry["command"] = "cursor-agent-memory-mcp"
else:
    entry["command"] = "python"
    entry["args"]    = ["-m", "cursor_agent_memory.mcp_server"]

if mcp_name in config["mcpServers"] and not force:
    sys.stderr.write(
        f"    mcpServers.{mcp_name} already exists in {mcp_path}; "
        "leaving it alone (use --force to replace).\n"
    )
    sys.exit(0)

config["mcpServers"][mcp_name] = entry
with open(mcp_path, "w", encoding="utf-8") as fh:
    json.dump(config, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print(f"    Wrote {mcp_name} entry to {mcp_path}.")
PYEOF

if [[ "$SKIP_SCHEDULE" -eq 1 ]]; then
  warn "Skipping cron registration (--skip-schedule)."
else
  step "Adding hourly cron entry"
  CRON_LINE="0 */${INTERVAL_HOURS} * * * ${SYNC_CMD:-${PY} -m cursor_agent_memory.sync_daemon} --once >/dev/null 2>&1"
  TAG="# cursor-agent-memory-sync"
  CURRENT=$(crontab -l 2>/dev/null || true)
  FILTERED=$(printf '%s\n' "$CURRENT" | grep -v -F "$TAG" || true)
  NEW="${FILTERED}
${CRON_LINE} ${TAG}
"
  printf '%s' "$NEW" | crontab -
  ok "Cron entry installed (use 'crontab -l' to verify)."
fi

printf '\n\033[32mAll set.\033[0m Restart Cursor, then in any chat:\n'
printf '    @ -> MCP -> %s\n' "${MCP_NAME}"
printf "    'find the session where I…'\n\n"
printf 'Export dir: %s\n' "${EXPORT_DIR}"
printf 'MCP config: %s\n' "${MCP_PATH}"
