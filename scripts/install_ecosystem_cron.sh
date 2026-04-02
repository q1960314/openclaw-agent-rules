#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="/home/admin/.openclaw/workspace/master"
CRON_FILE="$WORKSPACE_ROOT/config/ecosystem.crontab.example"
BACKUP_FILE="$WORKSPACE_ROOT/logs/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "$WORKSPACE_ROOT/logs"
crontab -l > "$BACKUP_FILE" 2>/dev/null || true
cp "$CRON_FILE" "$WORKSPACE_ROOT/logs/last_installed_ecosystem.crontab"
crontab "$CRON_FILE"

echo "已安装 ecosystem cron 配置"
echo "原 crontab 备份: $BACKUP_FILE"
echo "当前安装文件: $CRON_FILE"
