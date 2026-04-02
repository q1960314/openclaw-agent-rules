#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把最新 cycles 的摘要归档到知识索引。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

INDEX_DIR = Path('/home/admin/.openclaw/workspace/master/quant-research-knowledge-base/规则手册')
INDEX_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = INDEX_DIR / '生态循环知识索引_runtime.md'


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='archive_knowledge')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    rollup = load_json(cycle_dir / 'artifacts' / 'collect_cycle_reports' / 'knowledge_rollup.json')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines: List[str] = []
    lines.append(f"\n## 更新于 {now}\n")
    for item in rollup.get('collected_cycles', []):
        summary = item.get('summary', {})
        lines.append(f"### {item.get('cycle_type')} / {item.get('cycle_id')}")
        lines.append(f"- 状态: {item.get('status')}")
        lines.append(f"- 更新时间: {item.get('updated_at')}")
        if summary.get('followup_ticket_count') is not None:
            lines.append(f"- 后续工单数: {summary.get('followup_ticket_count')}")
        if summary.get('recommended_actions'):
            lines.append(f"- 建议动作数: {len(summary.get('recommended_actions', []))}")
        if item.get('report_path'):
            lines.append(f"- 报告路径: {item.get('report_path')}")
        lines.append('')

    if INDEX_FILE.exists():
        content = INDEX_FILE.read_text(encoding='utf-8')
    else:
        content = '# 生态循环知识索引（runtime）\n\n'
    content += '\n'.join(lines)
    INDEX_FILE.write_text(content, encoding='utf-8')

    out = cycle_dir / 'artifacts' / args.stage_id / 'knowledge_archive.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'stage': args.stage_id, 'updated_at': now, 'index_file': str(INDEX_FILE), 'collected': len(rollup.get('collected_cycles', []))}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'index_file': str(INDEX_FILE), 'collected': len(rollup.get('collected_cycles', []))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
