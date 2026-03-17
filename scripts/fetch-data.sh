#!/bin/bash
# 数据抓取任务脚本
# 用法：./fetch-data.sh [抓取类型]

FETCH_TYPE="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TRACE_DIR="/home/admin/.openclaw/agents/master/traces"
DATA_DIR="/home/admin/.openclaw/agents/master/quant_data_project/data"
CODE_DIR="/home/admin/.openclaw/agents/master/quant_data_project/code"
LOG_DIR="/home/admin/.openclaw/agents/master/quant_data_project/logs"

# 确保目录存在
mkdir -p "$TRACE_DIR" "$DATA_DIR" "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/fetch-data.log"
}

# 并发线程数（根据服务器配置）
MAX_WORKERS=4

# 限流配置（每分钟请求数）
MAX_REQUESTS_PER_MINUTE=500

case $FETCH_TYPE in
    "full")
        log "=== 全量数据抓取任务开始 ==="
        log "并发线程数：$MAX_WORKERS"
        log "限流配置：$MAX_REQUESTS_PER_MINUTE 次/分钟"
        
        # 调用 Python 抓取脚本
        cd "$CODE_DIR"
        python3 fetch_all_data.py \
            --workers $MAX_WORKERS \
            --rate-limit $MAX_REQUESTS_PER_MINUTE \
            --market 主板 \
            --start-date 20200101 \
            --end-date $(date +%Y%m%d) \
            >> "$LOG_DIR/fetch-data.log" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 全量数据抓取完成"
        else
            log "❌ 全量数据抓取失败"
        fi
        ;;
    
    "daily")
        log "=== 每日增量数据抓取任务开始 ==="
        log "并发线程数：$MAX_WORKERS"
        
        # 调用 Python 抓取脚本（仅最新交易日）
        cd "$CODE_DIR"
        python3 fetch_daily_data.py \
            --workers $MAX_WORKERS \
            --market 主板 \
            >> "$LOG_DIR/fetch-data.log" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 每日增量数据抓取完成"
        else
            log "❌ 每日增量数据抓取失败"
        fi
        ;;
    
    "finance")
        log "=== 财务数据抓取任务开始 ==="
        log "并发线程数：$MAX_WORKERS"
        
        cd "$CODE_DIR"
        python3 fetch_finance_data.py \
            --workers $MAX_WORKERS \
            --market 主板 \
            >> "$LOG_DIR/fetch-data.log" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 财务数据抓取完成"
        else
            log "❌ 财务数据抓取失败"
        fi
        ;;
    
    "moneyflow")
        log "=== 资金流向数据抓取任务开始 ==="
        log "并发线程数：$MAX_WORKERS"
        
        cd "$CODE_DIR"
        python3 fetch_moneyflow_data.py \
            --workers $MAX_WORKERS \
            --market 主板 \
            >> "$LOG_DIR/fetch-data.log" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 资金流向数据抓取完成"
        else
            log "❌ 资金流向数据抓取失败"
        fi
        ;;
    
    "quality-check")
        log "=== 数据质量校验任务开始 ==="
        
        cd "$CODE_DIR"
        python3 data_quality_check.py \
            --market 主板 \
            >> "$LOG_DIR/fetch-data.log" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 数据质量校验完成"
        else
            log "❌ 数据质量校验失败"
        fi
        ;;
    
    *)
        echo "用法：$0 {full|daily|finance|moneyflow|quality-check}"
        exit 1
        ;;
esac

log "=== 任务完成 ==="
