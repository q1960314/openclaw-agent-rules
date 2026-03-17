#!/bin/bash
# 任务发布脚本 - 触发子智能体执行任务
# 用法：bash scripts/dispatch-task.sh <agent-id> <task-description>

set -eo pipefail

AGENT_ID="${1:-}"
TASK_DESC="${2:-}"
AGENT_DIR="$HOME/.openclaw/agents/master"
MEMORY_DIR="$AGENT_DIR/memory"
LOG_FILE="$AGENT_DIR/logs/task-dispatch.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

if [ -z "$AGENT_ID" ] || [ -z "$TASK_DESC" ]; then
    echo "用法：$0 <agent-id> <task-description>"
    exit 1
fi

log "=== 发布任务 ==="
log "智能体：$AGENT_ID"
log "任务：$TASK_DESC"

# 更新任务队列
TASK_FILE="$MEMORY_DIR/task-queue.json"
if [ -f "$TASK_FILE" ]; then
    python3 << PYEOF
import json
from datetime import datetime

with open('$TASK_FILE', 'r') as f:
    data = json.load(f)

for task in data.get('tasks', []):
    if task.get('status') == 'pending' and '$AGENT_ID' in task.get('agent', ''):
        task['status'] = 'in_progress'
        task['started_at'] = datetime.now().isoformat()
        break

with open('$TASK_FILE', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ 任务状态已更新")
PYEOF
fi

# 创建触发文件
PENDING_FILE="$MEMORY_DIR/pending-dispatch.json"
cat >> "$PENDING_FILE" << EOF
{"agent_id": "$AGENT_ID", "task": "$TASK_DESC", "dispatched_at": "$(date -Iseconds)"}
EOF

log "✅ 触发文件已更新"
log "=== 完成 ==="
