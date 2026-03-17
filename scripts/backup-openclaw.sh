#!/bin/bash
# OpenClaw 轻量级配置备份脚本（保留 7 天）
# 备份：身份信息 + 技能列表 + 运行环境 + 当天代码

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/admin/backups"
TEMP_DIR="/tmp/openclaw-config-backup-$TIMESTAMP"
OPENCLAW_DIR="/home/admin/.openclaw"

# 创建临时目录
mkdir -p "$TEMP_DIR"

echo "=========================================="
echo "OpenClaw 轻量级备份开始"
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 备份智能体身份信息
echo "[1/7] 备份智能体身份信息..."
mkdir -p "$TEMP_DIR/agents-config"
cp "$OPENCLAW_DIR/agents/master/"*.md "$TEMP_DIR/" 2>/dev/null || true
cp -r "$OPENCLAW_DIR/agents/master/.openclaw/" "$TEMP_DIR/agents-config/" 2>/dev/null || true

# 2. 备份当天代码（*.py 文件）
echo "[2/7] 备份当天代码..."
mkdir -p "$TEMP_DIR/code"
cp "$OPENCLAW_DIR/agents/master/"*.py "$TEMP_DIR/code/" 2>/dev/null || true
cp "$OPENCLAW_DIR/agents/master/"*.md "$TEMP_DIR/code/" 2>/dev/null || true

# 3. 备份技能列表
echo "[3/7] 备份技能列表..."
cp "$OPENCLAW_DIR/openclaw.json" "$TEMP_DIR/" 2>/dev/null || true
pip list > "$TEMP_DIR/pip-list.txt" 2>/dev/null || true
npm list -g --depth=0 > "$TEMP_DIR/npm-list.txt" 2>/dev/null || true

# 4. 备份运行环境描述
echo "[4/7] 备份运行环境描述..."
python3 --version > "$TEMP_DIR/python-version.txt" 2>/dev/null || true
node --version > "$TEMP_DIR/node-version.txt" 2>/dev/null || true
uname -a > "$TEMP_DIR/system-info.txt" 2>/dev/null || true
df -h > "$TEMP_DIR/disk-info.txt" 2>/dev/null || true

# 5. 备份定时任务配置
echo "[5/7] 备份定时任务配置..."
mkdir -p "$TEMP_DIR/cron"
cp "$OPENCLAW_DIR/cron/jobs.json" "$TEMP_DIR/cron/" 2>/dev/null || true
crontab -l > "$TEMP_DIR/crontab-backup.txt" 2>/dev/null || true

# 6. 备份记忆文件
echo "[6/7] 备份记忆文件..."
cp -r "$OPENCLAW_DIR/memory/" "$TEMP_DIR/" 2>/dev/null || true

# 7. 备份知识库索引
echo "[7/7] 备份知识库索引..."
cp -r "$OPENCLAW_DIR/agents/master/knowledge-base/" "$TEMP_DIR/" 2>/dev/null || true

# 压缩备份
echo "正在压缩备份文件..."
cd "$TEMP_DIR"
tar -czf "$BACKUP_DIR/openclaw-config-$TIMESTAMP.tar.gz" .

# 获取备份大小
BACKUP_SIZE=$(du -h "$BACKUP_DIR/openclaw-config-$TIMESTAMP.tar.gz" | cut -f1)

# 清理临时目录
rm -rf "$TEMP_DIR"

# 清理 7 天前的备份
echo "清理 7 天前的备份..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "openclaw-config-*.tar.gz" -mtime +7 -delete | wc -l)

echo "=========================================="
echo "备份完成"
echo "备份文件：$BACKUP_DIR/openclaw-config-$TIMESTAMP.tar.gz"
echo "备份大小：$BACKUP_SIZE"
echo "删除旧备份：$DELETED_COUNT 个"
echo "=========================================="

# 记录备份日志
echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份完成 - $BACKUP_SIZE" >> "$BACKUP_DIR/backup-log.txt"
