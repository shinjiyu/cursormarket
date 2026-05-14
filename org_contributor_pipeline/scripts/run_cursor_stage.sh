#!/usr/bin/env bash
# Run Cursor Agent CLI for org_contributor_pipeline stages 1–3.
# Usage: ./run_cursor_stage.sh <1|2|3> [artifact_path] [workspace_root]
set -euo pipefail
STAGE="${1:?stage 1|2|3}"
ARTIFACT="${2:-}"
ROOT="${3:-$(cd "$(dirname "$0")/../.." && pwd)}"
case "$STAGE" in
  1) FILE="01_identity_and_scope.md" ;;
  2) FILE="02_metrics_to_narrative.md" ;;
  3) FILE="03_rubric_alignment.md" ;;
  *) echo "stage must be 1, 2, or 3"; exit 2 ;;
esac
PROMPT_PATH="$ROOT/org_contributor_pipeline/prompts/$FILE"
BODY=$(cat "$PROMPT_PATH")
HEADER="You are executing org_contributor_pipeline stage ${STAGE}.
Follow the repository root AGENTS.md and .cursor/rules. Do not modify source files unless the user explicitly requests edits.
Output the full analysis in the reply."
ARTIFACT_NOTE=""
if [[ -n "$ARTIFACT" ]]; then
  ARTIFACT_NOTE="

## Artifact file path (read with your tools as needed)
$(cd "$(dirname "$ARTIFACT")" && pwd)/$(basename "$ARTIFACT")
"
fi
FULL="${HEADER}${ARTIFACT_NOTE}

---

${BODY}"
if ! command -v agent >/dev/null 2>&1; then
  echo "Cursor CLI 'agent' not found on PATH" >&2
  exit 127
fi
cd "$ROOT"
exec agent -p --mode=ask --workspace "$ROOT" --output-format text "$FULL"
