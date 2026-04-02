#!/bin/bash
# =====================================================
# 一键落地工具 - 真正可执行的生态维护脚本
# =====================================================
# 使用方法: bash scripts/eco_maintenance.sh
# =====================================================

BASE_DIR="/home/admin/.openclaw/workspace/master"
MEMORY_DIR="$BASE_DIR/memory"
KB_DIR="$BASE_DIR/quant-research-knowledge-base"
SHARED_KB="/data/quant_knowledge"

echo "==========================================="
echo "  生态系统维护 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

# 1. 从代码提取参数
echo ""
echo "【1】提取代码参数到知识库..."
python "$MEMORY_DIR/extract_params.py"

# 2. 同步知识库到共享路径
echo ""
echo "【2】同步知识库到共享路径..."
rsync -av --delete "$KB_DIR/智能体专属能力库/" "$SHARED_KB/智能体专属能力库/" 2>/dev/null
echo "✅ 已同步"

# 3. 记忆注入
echo ""
echo "【3】注入记忆到子智能体..."
python "$MEMORY_DIR/memory_sync_tool.py" --sync-all

# 4. 检查避坑指南
echo ""
echo "【4】避坑指南统计..."
ERROR_COUNT=$(ls "$KB_DIR/避坑指南"/避坑_*.md 2>/dev/null | wc -l)
echo "当前避坑记录数: $ERROR_COUNT"

# 5. 检查沉淀文档
echo ""
echo "【5】沉淀文档统计..."
for agent in coder strategy-expert test-expert; do
    count=$(ls "$KB_DIR/智能体专属能力库/$agent"/决策_*.md 2>/dev/null | wc -l)
    echo "  $agent: $count 条决策"
done

echo ""
echo "==========================================="
echo "  ✅ 维护完成"
echo "==========================================="