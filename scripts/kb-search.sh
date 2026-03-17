#!/bin/bash
# 知识库检索脚本

KB_DIR="/home/admin/.openclaw/agents/master/knowledge-base"

# 参数解析
KEYWORD=""
CATEGORY=""
TAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --keyword) KEYWORD="$2"; shift 2 ;;
        --category) CATEGORY="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        *) echo "未知参数：$1"; exit 1 ;;
    esac
done

# 检索逻辑
if [ -n "$KEYWORD" ]; then
    echo "检索关键词：$KEYWORD"
    grep -r "$KEYWORD" "$KB_DIR" --include="*.md" 2>/dev/null
fi

if [ -n "$CATEGORY" ]; then
    echo "检索分类：$CATEGORY"
    ls -la "$KB_DIR/$CATEGORY/" 2>/dev/null
fi

if [ -n "$TAG" ]; then
    echo "检索标签：$TAG"
    grep -r "#$TAG" "$KB_DIR" --include="*.md" 2>/dev/null
fi

echo "✓ 检索完成"
