#!/bin/bash
# ==================== Cron 任务监控脚本 ====================
# 用途：检查数据抓取任务的执行状态和日志
# 使用：./monitor-cron-jobs.sh [today|yesterday|all]

LOG_DIR="/home/admin/.openclaw/agents/master/logs"
SCRIPT_DIR="/home/admin/.openclaw/agents/master/scripts"
DATE_FILTER="${1:-today}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  OpenClaw 数据抓取任务监控报告"
echo "  生成时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查 cron 服务状态
echo "【1. Cron 服务状态】"
if pgrep -x "cron" > /dev/null; then
    echo -e "${GREEN}✓ Cron 服务运行中${NC}"
else
    echo -e "${RED}✗ Cron 服务未运行${NC}"
fi
echo ""

# 检查 crontab 配置
echo "【2. Crontab 配置】"
CRON_COUNT=$(crontab -l 2>/dev/null | grep -c "fetch-data.sh")
echo "数据抓取任务数量：$CRON_COUNT"
if [ "$CRON_COUNT" -eq 7 ]; then
    echo -e "${GREEN}✓ 所有 7 个任务已配置${NC}"
else
    echo -e "${YELLOW}⚠ 任务数量异常（应为 7 个）${NC}"
fi
echo ""

# 检查脚本权限
echo "【3. 脚本权限检查】"
if [ -x "$SCRIPT_DIR/fetch-data.sh" ]; then
    echo -e "${GREEN}✓ fetch-data.sh 可执行${NC}"
else
    echo -e "${RED}✗ fetch-data.sh 权限不足${NC}"
fi
echo ""

# 检查日志目录
echo "【4. 日志目录状态】"
if [ -d "$LOG_DIR" ]; then
    LOG_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
    LOG_COUNT=$(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l)
    echo "日志目录：$LOG_DIR"
    echo "日志文件数量：$LOG_COUNT"
    echo "日志总大小：$LOG_SIZE"
    echo -e "${GREEN}✓ 日志目录正常${NC}"
else
    echo -e "${RED}✗ 日志目录不存在${NC}"
fi
echo ""

# 检查最近的日志
echo "【5. 最近任务执行状态】"
if [ "$DATE_FILTER" = "today" ]; then
    TODAY=$(date '+%Y%m%d')
    echo "筛选日期：今天 ($TODAY)"
    LOG_PATTERN="*$TODAY*.log"
elif [ "$DATE_FILTER" = "yesterday" ]; then
    YESTERDAY=$(date -d "yesterday" '+%Y%m%d')
    echo "筛选日期：昨天 ($YESTERDAY)"
    LOG_PATTERN="*$YESTERDAY*.log"
else
    echo "筛选日期：全部"
    LOG_PATTERN="*.log"
fi

RECENT_LOGS=$(ls -t "$LOG_DIR"/$LOG_PATTERN 2>/dev/null | head -7)

if [ -n "$RECENT_LOGS" ]; then
    for log in $RECENT_LOGS; do
        if [ -f "$log" ]; then
            FILENAME=$(basename "$log")
            LAST_LINE=$(tail -1 "$log" 2>/dev/null)
            LINE_COUNT=$(wc -l < "$log")
            echo ""
            echo "文件：$FILENAME"
            echo "行数：$LINE_COUNT"
            echo "最后更新：$(stat -c '%y' "$log" 2>/dev/null | cut -d'.' -f1)"
            echo "末行：$LAST_LINE"
        fi
    done
else
    echo "未找到日志文件"
fi
echo ""

# 任务时间表
echo "【6. 任务执行时间表】"
echo "┌───────┬──────────────────┬────────────────────────────────────┐"
echo "│ 时间  │ 任务名称         │ Cron 表达式                        │"
echo "├───────┼──────────────────┼────────────────────────────────────┤"
echo "│ 01:00 │ 增量数据抓取     │ 0 1 * * *                          │"
echo "│ 03:00 │ 日线行情补全     │ 0 3 * * *                          │"
echo "│ 05:00 │ 财务数据更新     │ 0 5 * * *                          │"
echo "│ 06:00 │ 资金流向更新     │ 0 6 * * *                          │"
echo "│ 07:00 │ 龙虎榜/涨跌停    │ 0 7 * * *                          │"
echo "│ 08:00 │ 数据质量校验     │ 0 8 * * *                          │"
echo "│ 16:00 │ 盘后增量抓取     │ 0 16 * * 1-5 (工作日)              │"
echo "└───────┴──────────────────┴────────────────────────────────────┘"
echo ""

echo "=========================================="
echo "  监控报告结束"
echo "=========================================="
