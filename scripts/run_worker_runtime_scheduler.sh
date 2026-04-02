#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
PYTHON="/home/admin/miniconda3/envs/vnpy_env/bin/python"
SCHEDULER="$WORKSPACE_ROOT/scripts/runtime/worker_runtime_scheduler.py"
ACTION="${1:-run-once}"
shift || true

case "$ACTION" in
  run-once)
    exec "$PYTHON" "$SCHEDULER" run-once "$@"
    ;;
  loop)
    exec "$PYTHON" "$SCHEDULER" loop "$@"
    ;;
  status)
    exec "$PYTHON" "$SCHEDULER" status "$@"
    ;;
  *)
    echo "Usage: $0 {run-once|loop|status} [args...]" >&2
    exit 1
    ;;
esac
