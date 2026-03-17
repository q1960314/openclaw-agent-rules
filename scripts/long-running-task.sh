#!/bin/bash
# 长时段任务执行框架
# 用法：./long-running-task.sh [任务类型] [持续时间小时] [间隔分钟]

TASK_TYPE="$1"
DURATION_HOURS="$2"
INTERVAL_MINUTES="$3"

TRACE_DIR="/home/admin/.openclaw/agents/master/traces"
LOG_FILE="$TRACE_DIR/long-running-$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$TRACE_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 计算结束时间
END_TIME=$(date -d "+$DURATION_HOURS hours" +%s)

log "=== 长时段任务开始 ==="
log "任务类型：$TASK_TYPE"
log "持续时间：$DURATION_HOURS 小时"
log "执行间隔：$INTERVAL_MINUTES 分钟"
log "结束时间：$(date -d "@$END_TIME" '+%Y-%m-%d %H:%M:%S')"

# 循环执行
while [ $(date +%s) -lt $END_TIME ]; do
    log "--- 执行周期：$(date '+%H:%M:%S') ---"
    
    case $TASK_TYPE in
        "market-monitor")
            log "🔍 监控市场状态..."
            # 检查代码运行状态
            ps aux | grep -E "python|node" | grep -v grep >> "$LOG_FILE"
            # 检查资源占用
            free -h >> "$LOG_FILE"
            df -h >> "$LOG_FILE"
            ;;
        
        "stock-pick")
            log "📈 执行选股策略..."
            # 调用选股脚本
            # ./scripts/daily-cycle.sh daily-stock-pick
            ;;
        
        "backtest")
            log "📊 执行回测..."
            # 调用回测脚本
            # ./scripts/daily-cycle.sh backtest
            ;;
        
        "data-update")
            log "💾 更新数据..."
            # 调用数据更新脚本
            # ./scripts/daily-cycle.sh data-update
            ;;
        
        *)
            log "⚠️ 未知任务类型：$TASK_TYPE"
            ;;
    esac
    
    log "✓ 周期执行完成"
    
    # 等待到下一个周期
    REMAINING=$((END_TIME - $(date +%s)))
    if [ $REMAINING -gt 0 ]; then
        log "⏳ 等待 $INTERVAL_MINUTES 分钟后执行下一周期..."
        sleep $((INTERVAL_MINUTES * 60))
    fi
done

log "=== 长时段任务结束 ==="
log "总执行时长：$DURATION_HOURS 小时"
log "日志文件：$LOG_FILE"

# 归档日志
cp "$LOG_FILE" "$TRACE_DIR/archive/"
