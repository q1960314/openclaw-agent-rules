#!/bin/bash
# ==============================================
# 任务调度器 - 监听子智能体完成状态，自动触发下一步
# ==============================================
export PATH="$HOME/.local/share/pnpm:$HOME/.local/bin:$PATH"

AGENT_DIR="$HOME/.openclaw/agents/master"
MEMORY_DIR="$AGENT_DIR/memory"
LOG_FILE="$AGENT_DIR/logs/task-dispatcher.log"
COMPLETED_FILE="$MEMORY_DIR/completed-tasks.json"
TRIGGER_FILE="$MEMORY_DIR/pending-dispatch.json"

mkdir -p "$MEMORY_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== 任务调度器启动 ==="

# 检查是否有新完成的任务
if [ -f "$COMPLETED_FILE" ]; then
    log "检测到已完成任务文件"
    
    last_completed=$(cat "$COMPLETED_FILE" 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[-1]['task_id'] if data else '')" 2>/dev/null)
    
    if [ -n "$last_completed" ]; then
        log "最近完成任务：$last_completed"
        
        # 写入触发文件（Master 会轮询这个文件）
        echo "{\"task_id\": \"$last_completed\", \"notified_at\": \"$(date -Iseconds)\"}" >> "$TRIGGER_FILE"
        
        log "✅ 已写入触发文件：$TRIGGER_FILE"
    fi
fi

log "=== 任务调度器完成 ==="
echo "" >> "$LOG_FILE"
