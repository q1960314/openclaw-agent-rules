#!/bin/bash
# 数据抓取恢复 - 快速启动脚本
# 版本：v1.0
# 创建时间：2026-03-12

set -e

WORK_DIR="/home/admin/.openclaw/agents/master"
cd "$WORK_DIR"

echo "================================================================================"
echo "  🚀 数据抓取恢复 - 快速启动"
echo "================================================================================"
echo ""

# 1. 检查进程锁
echo "🔍 检查进程锁状态..."
if [ -f /tmp/fetch_data.lock ]; then
    echo "⚠️  检测到进程锁文件，检查是否已有进程在运行..."
    LOCK_PID=$(cat /tmp/fetch_data.lock 2>/dev/null | head -1)
    if ps -p "$LOCK_PID" > /dev/null 2>&1; then
        echo "❌ 进程 $LOCK_PID 正在运行，无法启动新进程"
        echo "   如需强制启动，请先停止现有进程：kill $LOCK_PID"
        echo "   或清理锁文件：rm /tmp/fetch_data.lock"
        exit 1
    else
        echo "⚠️  发现残留锁文件（进程已终止），清理中..."
        rm -f /tmp/fetch_data.lock
        echo "✅ 锁文件已清理"
    fi
else
    echo "✅ 无进程锁，可以启动"
fi
echo ""

# 2. 检查 Python 环境
echo "🔍 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ Python 环境：$PYTHON_VERSION"
echo ""

# 3. 检查依赖
echo "🔍 检查必要依赖..."
python3 -c "import fcntl, json, logging, threading" 2>/dev/null && echo "✅ 标准库依赖正常" || {
    echo "❌ 标准库依赖缺失"
    exit 1
}
echo ""

# 4. 显示配置
echo "📋 当前配置："
echo "   工作目录：$WORK_DIR"
echo "   并发线程：10（保守配置）"
echo "   限流：2000 次/分钟"
echo "   保存频率：每 20 只股票"
echo "   验证频率：每 100 只股票"
echo ""

# 5. 确认启动
echo "================================================================================"
echo "  准备启动数据抓取（保守配置）"
echo "================================================================================"
echo ""
echo "⚠️  注意事项："
echo "   1. 抓取过程请勿关闭终端"
echo "   2. 如需查看进度，请另开终端运行：python3 monitor_progress.py"
echo "   3. 日志文件：logs/fetch_conservative_*.log"
echo "   4. 中断后可从检查点恢复：checkpoints/"
echo ""
echo "✅ 所有检查通过，准备启动..."
echo ""

# 6. 启动抓取
echo "🚀 启动抓取进程..."
echo "================================================================================"
python3 fetch_data_conservative.py

# 7. 检查退出状态
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "  ✅ 数据抓取完成！"
    echo "================================================================================"
    echo ""
    echo "📊 下一步操作："
    echo "   1. 验证数据完整性：python3 validate_data_integrity.py"
    echo "   2. 查看监控报告：ls -lh dashboards/"
    echo "   3. 查看日志：tail -f logs/fetch_conservative_*.log"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo "  ❌ 数据抓取异常退出（退出码：$EXIT_CODE）"
    echo "================================================================================"
    echo ""
    echo "🔍 排查步骤："
    echo "   1. 查看错误日志：tail logs/fetch_conservative_*.log"
    echo "   2. 检查进程锁：cat /tmp/fetch_data.lock"
    echo "   3. 检查网络：ping -c 3 www.baidu.com"
    echo ""
fi

exit $EXIT_CODE
