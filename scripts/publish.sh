#!/usr/bin/env bash
# Build (and optionally upload) the public `cursor-agent-memory` PyPI package.
#
# Usage:
#   bash scripts/publish.sh                          # build only
#   bash scripts/publish.sh --check                  # also run twine check
#   bash scripts/publish.sh --upload testpypi        # build + check + upload to TestPyPI
#   bash scripts/publish.sh --upload pypi            # build + check + upload to real PyPI
#
# Requires:  python -m pip install --upgrade build twine

set -euo pipefail

CHECK=0
UPLOAD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)  CHECK=1; shift ;;
    --upload) UPLOAD="$2"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG_DIR="${REPO_ROOT}/packaging/cursor-agent-memory"
SRC_PKG="${REPO_ROOT}/cursor_agent_memory"
SRC_README="${REPO_ROOT}/README.md"
SRC_LICENSE="${REPO_ROOT}/LICENSE"

[[ -d "$SRC_PKG"     ]] || { echo "missing $SRC_PKG"     >&2; exit 1; }
[[ -f "$SRC_README"  ]] || { echo "missing $SRC_README"  >&2; exit 1; }
[[ -f "$SRC_LICENSE" ]] || { echo "missing $SRC_LICENSE" >&2; exit 1; }

echo "==> Staging cursor_agent_memory + README + LICENSE into $PKG_DIR"
rm -rf "${PKG_DIR}/cursor_agent_memory" "${PKG_DIR}/build" "${PKG_DIR}/dist"
rm -f  "${PKG_DIR}/README.md" "${PKG_DIR}/LICENSE"
find "${PKG_DIR}" -maxdepth 1 -type d -name "*.egg-info" -exec rm -rf {} +

cp "$SRC_README"  "${PKG_DIR}/README.md"
cp "$SRC_LICENSE" "${PKG_DIR}/LICENSE"
cp -R "$SRC_PKG"  "${PKG_DIR}/cursor_agent_memory"
find "${PKG_DIR}/cursor_agent_memory" -type d -name __pycache__ -exec rm -rf {} +

echo "==> python -m build"
( cd "$PKG_DIR" && python -m build )

if [[ "$CHECK" -eq 1 || -n "$UPLOAD" ]]; then
  echo "==> twine check"
  ( cd "$PKG_DIR" && python -m twine check dist/* )
fi

if [[ -n "$UPLOAD" ]]; then
  REPO_ARG=()
  [[ "$UPLOAD" == "testpypi" ]] && REPO_ARG=(--repository testpypi)
  echo "==> twine upload $UPLOAD"
  ( cd "$PKG_DIR" && python -m twine upload "${REPO_ARG[@]}" dist/* )
fi

echo
echo "Artifacts in: ${PKG_DIR}/dist"
