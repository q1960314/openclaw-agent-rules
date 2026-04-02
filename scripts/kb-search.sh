#!/bin/bash
# 知识库快速检索脚本（按分类/目录缩小范围，再做内容匹配）
set -euo pipefail

KB_DIR="/home/admin/.openclaw/workspace/master/quant-research-knowledge-base"
PYTHON_BIN="/home/admin/miniconda3/envs/vnpy_env/bin/python"

KEYWORD=""
CATEGORY=""
TAG=""
AGENT=""
LIMIT="20"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keyword) KEYWORD="$2"; shift 2 ;;
        --category) CATEGORY="$2"; shift 2 ;;
        --tag) TAG="$2"; shift 2 ;;
        --agent) AGENT="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        *) echo "未知参数：$1"; exit 1 ;;
    esac
done

if [[ -z "$KEYWORD" && -z "$CATEGORY" && -z "$TAG" && -z "$AGENT" ]]; then
    echo "用法：kb-search.sh [--keyword 关键词] [--category 分类] [--tag 标签] [--agent 智能体] [--limit 数量]"
    echo "\n可用顶层分类："
    find "$KB_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
    exit 0
fi

export KB_DIR KEYWORD CATEGORY TAG AGENT LIMIT
exec "$PYTHON_BIN" - <<'PY'
import os
from pathlib import Path

kb_dir = Path(os.environ['KB_DIR'])
keyword = os.environ.get('KEYWORD', '').strip()
category = os.environ.get('CATEGORY', '').strip()
tag = os.environ.get('TAG', '').strip()
agent = os.environ.get('AGENT', '').strip()
limit = int(os.environ.get('LIMIT', '20') or 20)

search_root = kb_dir
notes = []
if category:
    candidate = kb_dir / category
    if candidate.exists():
        search_root = candidate
        notes.append(f'分类范围: {candidate}')
    else:
        print(f'❌ 分类不存在: {candidate}')
        raise SystemExit(1)
if agent:
    candidate = kb_dir / '智能体专属能力库' / agent
    if candidate.exists():
        search_root = candidate
        notes.append(f'智能体范围: {candidate}')
    else:
        print(f'❌ 智能体目录不存在: {candidate}')
        raise SystemExit(1)

files = sorted(search_root.rglob('*.md'))
if not files:
    print(f'⚠️ 未找到 Markdown 文件: {search_root}')
    raise SystemExit(0)

filename_hits = []
content_hits = []
tag_hits = []

for path in files:
    rel = path.relative_to(kb_dir)
    rel_str = str(rel)
    name = path.name
    matched = False

    if keyword and (keyword.lower() in name.lower() or keyword in rel_str):
        filename_hits.append((rel_str, 'filename'))
        matched = True

    lines = None
    if (keyword or tag) and (not matched or len(content_hits) < limit or len(tag_hits) < limit):
        try:
            lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

    if tag and lines is not None:
        needle = f'#{tag}'
        for idx, line in enumerate(lines, start=1):
            if needle in line:
                tag_hits.append((rel_str, idx, line.strip()))
                break

    if keyword and lines is not None:
        for idx, line in enumerate(lines, start=1):
            if keyword in line:
                content_hits.append((rel_str, idx, line.strip()))
                break

# 去重：同一文件若已在 filename_hits 中，就不在 content_hits/tag_hits 中重复刷太多
seen_files = set(x[0] for x in filename_hits)
content_hits = [x for x in content_hits if x[0] not in seen_files]
tag_hits = [x for x in tag_hits if x[0] not in seen_files]

print('=== 知识库快速检索 ===')
print(f'范围: {search_root}')
if notes:
    for n in notes:
        print(f'- {n}')
if keyword:
    print(f'- 关键词: {keyword}')
if tag:
    print(f'- 标签: #{tag}')
print('')

shown = 0
if filename_hits:
    print('## 文件名命中')
    for rel_str, _ in filename_hits[:limit]:
        print(f'- {rel_str}')
        shown += 1
    print('')

if content_hits and shown < limit * 2:
    print('## 内容命中')
    for rel_str, idx, line in content_hits[:limit]:
        print(f'- {rel_str}:{idx} | {line[:180]}')
    print('')

if tag_hits and shown < limit * 2:
    print('## 标签命中')
    for rel_str, idx, line in tag_hits[:limit]:
        print(f'- {rel_str}:{idx} | {line[:180]}')
    print('')

if not filename_hits and not content_hits and not tag_hits:
    print('⚠️ 未命中结果')
else:
    print(f'✓ 检索完成 | 文件总数: {len(files)} | 命中文件: {len(set([x[0] for x in filename_hits] + [x[0] for x in content_hits] + [x[0] for x in tag_hits]))}')
PY
