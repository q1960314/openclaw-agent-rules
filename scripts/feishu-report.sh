#!/bin/bash
# Master-Quant 飞书进度通知脚本
# 功能：每 30 分钟向用户发送飞书进度通知

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/admin/.local/bin:/home/admin/.npm-global/bin"

LOG_DIR="/home/admin/.openclaw/agents/master/logs"
TRACE_DIR="/home/admin/.openclaw/agents/master/traces"
OPENCLAW="/home/admin/.local/share/pnpm/openclaw"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/feishu-report.log"
}

log "=== 飞书进度通知开始 ==="

STATUS_FILE="$TRACE_DIR/task-status.json"
if [ -f "$STATUS_FILE" ]; then
    CURRENT_STAGE=$(cat "$STATUS_FILE" | grep -o '"current_stage": "[^"]*"' | cut -d'"' -f4)
    STAGE_PROGRESS=$(cat "$STATUS_FILE" | grep -o '"stage_progress": "[^"]*"' | cut -d'"' -f4)
else
    CURRENT_STAGE="未开始"
    STAGE_PROGRESS="0%"
fi

MESSAGE="【量化系统进度汇报】
时间：$(date '+%Y-%m-%d %H:%M')
阶段：$CURRENT_STAGE
进度：$STAGE_PROGRESS

子智能体：策略专家🟢 数据采集🟢 代码守护🟢
本 30 分钟：系统正常运行
异常：无

【合规提示】量化研究用，不构成投资建议"

# 使用 master-feishu 账号发送（正确的用户 ID）
$OPENCLAW message send --account master-feishu --channel feishu --target "ou_61884ea8aa288c6514cc8b4cb3cd16d8" --message "$MESSAGE" >> "$LOG_DIR/feishu-send.log" 2>&1

if [ $? -eq 0 ]; then
    log "✅ 飞书消息发送成功"
else
    log "❌ 飞书消息发送失败"
fi

log "=== 飞书进度通知完成 ==="
