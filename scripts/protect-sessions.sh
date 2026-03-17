#!/bin/bash
# 会话持久化保护脚本
# 用途：防止会话文件被意外删除

SESSIONS_DIR="/home/admin/.openclaw/agents/master/sessions"
BACKUP_DIR="/mnt/data/backups/sessions"

# 确保备份目录存在
mkdir -p "$BACKUP_DIR"

# 备份 sessions.json
cp "$SESSIONS_DIR/sessions.json" "$BACKUP_DIR/sessions_$(date +%Y%m%d_%H%M%S).json"

# 设置 sessions.json 为不可变（需要 root 权限）
# chattr +i "$SESSIONS_DIR/sessions.json" 2>/dev/null || true

echo "✅ 会话备份完成：$(date)"
echo "📁 备份位置：$BACKUP_DIR"
