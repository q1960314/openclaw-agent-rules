#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
DISPATCHER="$WORKSPACE_ROOT/scripts/workflow_auto_dispatcher.py"

cd "$WORKSPACE_ROOT"
"$PYTHON" "$DISPATCHER" --once
