#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
DASHBOARD="$WORKSPACE_ROOT/scripts/workflow_dashboard.py"
INTERVAL="${1:-5}"

while true; do
  clear || true
  "$PYTHON" "$DASHBOARD"
  sleep "$INTERVAL"
done
