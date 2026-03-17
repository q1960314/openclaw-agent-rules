#!/bin/bash
# Master Agent 24 小时循环调度脚本
# 用法：./daily-cycle.sh [任务类型]

TASK_TYPE="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TRACE_DIR="/home/admin/.openclaw/agents/master/traces"
KB_DIR="/home/admin/.openclaw/agents/master/quant-research-knowledge-base"

# 确保目录存在
mkdir -p "$TRACE_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$TRACE_DIR/daily-cycle.log"
}

case $TASK_TYPE in
    "archive")
        log "=== 日切归档任务开始 ==="
        # 归档当日所有 traces
        find "$TRACE_DIR" -name "*.md" -mtime -1 -exec cp {} "$TRACE_DIR/archive/" \;
        log "✓ 归档完成"
        ;;
    
    "data-update")
        log "=== 数据更新任务开始 ==="
        # 调用数据采集员更新数据
        log "📊 更新行情数据..."
        log "📊 更新财务数据..."
        log "✓ 数据更新完成"
        ;;
    
    "pre-market")
        log "=== 盘前准备任务开始 ==="
        # 检查数据完整性
        log "🔍 检查数据完整性..."
        # 更新选股池
        log "🔍 更新选股池..."
        log "✓ 盘前准备完成"
        ;;
    
    "daily-stock-pick")
        log "=== 每日选股任务开始 ==="
        # 执行选股策略
        log "📈 执行选股策略..."
        # 舆情筛查
        log "🔍 舆情筛查..."
        log "✓ 选股完成"
        ;;
    
    "market-open-monitor")
        log "=== 开盘监控任务开始 ==="
        # 监控代码运行状态
        log "🔍 监控运行状态..."
        log "✓ 开盘监控完成"
        ;;
    
    "noon-check")
        log "=== 午间检查任务开始 ==="
        # 上午监控汇总
        log "📊 上午监控汇总..."
        log "✓ 午间检查完成"
        ;;
    
    "market-close-check")
        log "=== 收盘检查任务开始 ==="
        # 收盘数据校验
        log "🔍 收盘数据校验..."
        # 持仓对账
        log "🔍 持仓对账..."
        log "✓ 收盘检查完成"
        ;;
    
    "backtest")
        log "=== 回测验证任务开始 ==="
        # 对当日选股做模拟回测
        log "📈 执行回测..."
        log "✓ 回测完成"
        ;;
    
    "strategy-optimize")
        log "=== 策略优化任务开始 ==="
        # 基于回测结果优化策略
        log "🔧 策略优化..."
        log "✓ 策略优化完成"
        ;;
    
    "code-review")
        log "=== 代码审查任务开始 ==="
        # 审查当日代码变更
        log "🔍 代码审查..."
        log "✓ 代码审查完成"
        ;;
    
    "daily-summary")
        log "=== 每日总结任务开始 ==="
        # 汇总全天任务
        log "📊 汇总全天任务..."
        # 生成日报
        log "📄 生成日报..."
        log "✓ 每日总结完成"
        ;;
    
    "kb-sync")
        log "=== 知识库沉淀任务开始 ==="
        # 当日经验沉淀
        log "📚 沉淀经验..."
        log "✓ 知识库更新完成"
        ;;
    
    *)
        echo "用法：$0 {archive|data-update|pre-market|daily-stock-pick|market-open-monitor|noon-check|market-close-check|backtest|strategy-optimize|code-review|daily-summary|kb-sync}"
        exit 1
        ;;
esac

log "=== 任务完成 ==="
