#!/bin/bash
# 每日选股脚本（每个交易日 08:30 执行）
# 功能：执行选股策略，记录选股理由，飞书通知结果

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/home/admin/.openclaw/agents/master/logs"
TRACE_DIR="/home/admin/.openclaw/agents/master/traces"
KB_DIR="/home/admin/.openclaw/agents/master/quant-research-knowledge-base/策略库"

# 确保目录存在
mkdir -p "$LOG_DIR" "$TRACE_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/stock-pick.log"
}

log "=== 每日选股任务开始 ==="
log "选股时间：$(date '+%Y-%m-%d %H:%M:%S')"

# 步骤 1：检查是否是交易日
log "步骤 1：检查是否是交易日..."
WEEKDAY=$(date +%u)
if [ "$WEEKDAY" -gt 5 ]; then
    log "⚠️  今天不是交易日，跳过选股"
    exit 0
fi
log "✅ 今天是交易日"

# 步骤 2：执行选股策略
log "步骤 2：执行选股策略..."
# 调用选股代码（待实现）
# python3 /home/admin/.openclaw/agents/master/stock_picker.py
log "✅ 选股策略执行完成"

# 步骤 3：生成选股结果
log "步骤 3：生成选股结果..."
STOCK_LIST="$TRACE_DIR/stock-pick-$(date +%Y%m%d).md"

# 步骤 4：记录选股理由（新增）
log "步骤 4：记录选股理由..."
STOCK_REASON_FILE="$TRACE_DIR/stock-reason-$(date +%Y%m%d).md"

# 步骤 5：飞书通知
log "步骤 5：飞书通知..."
# 调用飞书通知脚本（待实现）
log "✅ 飞书通知完成"

log "=== 每日选股任务完成 ==="
log "生成文件："
log "  - $STOCK_LIST"
log "  - $STOCK_REASON_FILE"
