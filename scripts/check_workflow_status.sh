#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
ENGINE="$WORKSPACE_ROOT/scripts/workflow_engine.py"
DASHBOARD="$WORKSPACE_ROOT/scripts/workflow_dashboard.py"
WORKER_RUNTIME="$WORKSPACE_ROOT/scripts/run_worker_runtime_scheduler.sh"

if [ $# -gt 0 ]; then
  case "$1" in
    worker-runtime|worker_runtime|runtime-scheduler)
      shift || true
      bash "$WORKER_RUNTIME" status "$@"
      ;;
    all|dashboard)
      "$PYTHON" "$DASHBOARD"
      ;;
    *)
      "$PYTHON" "$ENGINE" status --cycle-type "$1"
      ;;
  esac
else
  "$PYTHON" "$DASHBOARD"
fi
