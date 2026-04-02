#!/bin/bash
# =====================================================
# 记忆自动同步服务 - 每小时自动同步一次
# =====================================================

# 添加到 crontab:
# 0 * * * * /home/admin/.openclaw/workspace/master/scripts/auto_memory_sync.sh

MEMORY_DIR="/home/admin/.openclaw/workspace/master/memory"
LOG_FILE="/home/admin/.openclaw/workspace/master/logs/memory_sync.log"

# 创建日志目录
mkdir -p $(dirname "$LOG_FILE")

# 记录时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始记忆同步" >> "$LOG_FILE"

# 同步知识库到共享路径
rsync -av --delete \
    /home/admin/.openclaw/workspace/master/quant-research-knowledge-base/智能体专属能力库/ \
    /data/quant_knowledge/智能体专属能力库/ 2>&1 >> "$LOG_FILE"

# 执行记忆注入
cd /home/admin/.openclaw/workspace/master
python memory/memory_sync_tool.py --sync-all >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 记忆同步完成" >> "$LOG_FILE"