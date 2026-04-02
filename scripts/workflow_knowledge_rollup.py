#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总各 cycle 的最新报告，形成 knowledge_cycle 输入。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles')
TARGETS = ['daily_data_cycle', 'daily_research', 'weekly_health', 'optimization_cycle']


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def latest_cycle_dir(cycle_type: str) -> Optional[Path]:
    base = TRACE_ROOT / cycle_type
    if not base.exists():
        return None
    dirs = sorted([p for p in base.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='collect_cycle_reports')
    args = parser.parse_args()

    collected: List[Dict] = []
    for cycle_type in TARGETS:
        d = latest_cycle_dir(cycle_type)
        if not d:
            continue
        meta_path = d / 'meta.json'
        report_path = d / 'reports' / 'cycle_summary.md'
        if not meta_path.exists():
            continue
        meta = load_json(meta_path)
        item = {
            'cycle_type': cycle_type,
            'cycle_id': meta.get('cycle_id'),
            'status': meta.get('status'),
            'updated_at': meta.get('updated_at'),
            'cycle_dir': str(d),
            'report_path': str(report_path) if report_path.exists() else None,
            'summary': meta.get('summary', {}),
        }
        collected.append(item)

    payload = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'collected_cycles': collected,
        'count': len(collected),
    }

    cycle_dir = Path(args.cycle_dir)
    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'knowledge_rollup.json', payload)

    lines = ['# Knowledge Rollup', '']
    for item in collected:
        lines.extend([
            f"## {item['cycle_type']} / {item['cycle_id']}",
            f"- status: {item['status']}",
            f"- updated_at: {item['updated_at']}",
            f"- report_path: {item['report_path']}",
            '',
        ])
    (artifact_dir / 'knowledge_rollup.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'count': len(collected)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
