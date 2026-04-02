#!/bin/bash
# =====================================================
# 记忆同步脚本 - Memory Sync Script v3.0
# =====================================================
# 用途：同步记忆到各子智能体，执行压力监控和陈旧检测
# 使用：bash scripts/memory_sync.sh
# =====================================================

MEMORY_DIR="/home/admin/.openclaw/workspace/master/memory"
KNOWLEDGE_BASE="/home/admin/.openclaw/workspace/master/quant-research-knowledge-base"
WORKSPACE="/home/admin/.openclaw/workspace/master"

echo "=========================================="
echo "  记忆同步 v3.0 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 检查 Core Memory
echo ""
echo "【1】检查 Core Memory..."
if [ -f "$MEMORY_DIR/core_memory.yaml" ]; then
    echo "    ✅ core_memory.yaml 存在"
else
    echo "    ❌ core_memory.yaml 不存在"
    exit 1
fi

# 2. 检查 Working Memory
echo ""
echo "【2】检查 Working Memory..."
if [ -f "$MEMORY_DIR/working_memory.json" ]; then
    echo "    ✅ working_memory.json 存在"
else
    echo "    ❌ working_memory.json 不存在"
    exit 1
fi

# 3. 压力监控
echo ""
echo "【3】压力监控..."
python3 "$MEMORY_DIR/pressure_monitor.py" --action check --tokens 0 > /dev/null 2>&1
echo "    ✅ 压力监控已执行"

# 4. 陈旧检测
echo ""
echo "【4】陈旧检测..."
python3 "$MEMORY_DIR/staleness_detector.py" --action check > /dev/null 2>&1
echo "    ✅ 陈旧检测已执行"

# 5. 检查知识库同步
echo ""
echo "【5】检查知识库..."
if [ -d "$KNOWLEDGE_BASE" ]; then
    echo "    ✅ 知识库目录存在"
    echo "    分类："
    ls -d "$KNOWLEDGE_BASE"/*/ 2>/dev/null | xargs -n1 basename | while read dir; do
        echo "      - $dir"
    done
else
    echo "    ❌ 知识库目录不存在"
fi

# 6. 生成状态摘要
echo ""
echo "【6】当前记忆状态..."
python3 "$MEMORY_DIR/memory_manager.py" --action summary

# 7. 陈旧报告
echo ""
echo "【7】陈旧检测报告..."
python3 "$MEMORY_DIR/staleness_detector.py" --action report 2>/dev/null | head -15

echo ""
echo "=========================================="
echo "  同步完成 ✅"
echo "=========================================="