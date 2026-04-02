#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
REPAIR="$WORKSPACE_ROOT/scripts/workflow_repair.py"
CLEANUP="$WORKSPACE_ROOT/scripts/workflow_cleanup.py"

cd "$WORKSPACE_ROOT"
"$PYTHON" "$REPAIR" --latest-only || true
"$PYTHON" "$CLEANUP" --days 3 || true
