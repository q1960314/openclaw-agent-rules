#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
ENGINE="$WORKSPACE_ROOT/scripts/workflow_engine.py"
REPAIR="$WORKSPACE_ROOT/scripts/workflow_repair.py"
NOTIFY="$WORKSPACE_ROOT/scripts/workflow_notify.py"

cd "$WORKSPACE_ROOT"
if "$PYTHON" "$ENGINE" run --cycle-type weekly_health --trigger cron; then
  exit 0
else
  "$PYTHON" "$REPAIR" --cycle-type weekly_health --latest-only || true
  "$PYTHON" "$NOTIFY" --cycle-type weekly_health --mode failure --message "weekly_health 执行失败，请查看 latest_status / cycle logs" || true
  exit 1
fi
