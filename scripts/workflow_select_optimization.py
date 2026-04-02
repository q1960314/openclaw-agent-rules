#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已完成工单中挑选一个适合进入 optimization_cycle 的目标。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

QUEUE_DONE = Path('/home/admin/.openclaw/workspace/master/reports/workflow/queue/done')
ACTIONABLE = {'strategy_review', 'weekly_optimization', 'data_quality'}


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='select_target')
    parser.add_argument('--ticket-id', default='')
    args = parser.parse_args()

    items: List[Dict] = []
    for path in sorted(QUEUE_DONE.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = load_json(path)
        except Exception:
            continue
        ticket = payload.get('ticket', {})
        if args.ticket_id and ticket.get('ticket_id') != args.ticket_id:
            continue
        if ticket.get('category') not in ACTIONABLE:
            continue
        items.append({
            'path': str(path),
            'payload': payload,
            'ticket': ticket,
            'mtime': path.stat().st_mtime,
        })

    target = items[0] if items else None
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'selected': bool(target),
        'selected_ticket': target['ticket'] if target else None,
        'source_queue_file': target['path'] if target else None,
        'candidate_count': len(items),
    }
    artifact = Path(args.cycle_dir) / 'artifacts' / args.stage_id / 'selected_target.json'
    write_json(artifact, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if target else 1


if __name__ == '__main__':
    raise SystemExit(main())
