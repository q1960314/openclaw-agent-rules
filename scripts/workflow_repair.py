#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 stale workflow：当 cycle 显示 running 但锁 pid 已不存在时，标记为 interrupted。"""

from __future__ import annotations

import argparse
import json
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List

TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles')
LOCK_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/locks')
STATE_ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/state')


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def append_event(event: Dict) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    with open(STATE_ROOT / 'events.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def latest_status_payload(cycle_meta: Dict) -> Dict:
    return {
        'cycle_id': cycle_meta.get('cycle_id'),
        'cycle_type': cycle_meta.get('cycle_type'),
        'description': cycle_meta.get('description'),
        'status': cycle_meta.get('status'),
        'current_stage': cycle_meta.get('current_stage'),
        'stage_status': 'interrupted',
        'updated_at': cycle_meta.get('updated_at'),
        'trigger': cycle_meta.get('trigger'),
        'cycle_dir': cycle_meta.get('paths', {}).get('cycle_dir'),
        'repair': True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-type', choices=['daily_research', 'weekly_health'])
    parser.add_argument('--latest-only', action='store_true')
    args = parser.parse_args()

    repaired: List[Dict] = []
    cycle_types = [args.cycle_type] if args.cycle_type else [p.name for p in TRACE_ROOT.iterdir() if p.is_dir()]

    for cycle_type in cycle_types:
        base = TRACE_ROOT / cycle_type
        if not base.exists():
            continue
        cycle_dirs = sorted([p for p in base.iterdir() if p.is_dir()])
        if args.latest_only and cycle_dirs:
            cycle_dirs = [cycle_dirs[-1]]

        lock_path = LOCK_ROOT / f'{cycle_type}.lock.json'
        lock_data = load_json(lock_path) if lock_path.exists() else None

        for cycle_dir in cycle_dirs:
            meta_path = cycle_dir / 'meta.json'
            if not meta_path.exists():
                continue
            meta = load_json(meta_path)
            if meta.get('status') != 'running':
                continue

            cycle_id = meta.get('cycle_id')
            lock_matches = lock_data and lock_data.get('cycle_id') == cycle_id
            pid = lock_data.get('pid') if lock_matches else None
            stale = False
            reason = None

            if lock_matches:
                if not pid_exists(int(pid)):
                    stale = True
                    reason = f'lock_pid_dead:{pid}'
            else:
                stale = True
                reason = 'lock_missing'

            if stale:
                meta['status'] = 'interrupted'
                meta['interrupted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                meta['interrupt_reason'] = reason
                meta['updated_at'] = meta['interrupted_at']
                write_json(meta_path, meta)

                cycle_log = cycle_dir / 'logs' / 'cycle.log'
                with open(cycle_log, 'a', encoding='utf-8') as f:
                    f.write(f"[{meta['interrupted_at']}] 修复器标记为 interrupted: {reason}\n")

                live_status = latest_status_payload(meta)
                write_json(cycle_dir / 'reports' / 'live_status.json', live_status)
                write_json(cycle_dir / 'reports' / 'heartbeat.json', live_status)
                write_json(STATE_ROOT / 'latest_status.json', live_status)

                latest_cycles_path = STATE_ROOT / 'latest_cycles.json'
                latest_cycles = load_json(latest_cycles_path) if latest_cycles_path.exists() else {}
                latest_cycles[cycle_type] = {
                    'cycle_id': cycle_id,
                    'status': meta['status'],
                    'current_stage': meta.get('current_stage'),
                    'updated_at': meta['updated_at'],
                    'cycle_dir': str(cycle_dir),
                }
                write_json(latest_cycles_path, latest_cycles)

                event = {
                    'event_type': 'cycle_interrupted_repaired',
                    'time': meta['interrupted_at'],
                    'cycle_id': cycle_id,
                    'cycle_type': cycle_type,
                    'status': meta['status'],
                    'current_stage': meta.get('current_stage'),
                    'reason': reason,
                }
                append_event(event)

                if lock_matches and lock_path.exists():
                    lock_path.unlink()

                repaired.append({'cycle_id': cycle_id, 'cycle_type': cycle_type, 'reason': reason, 'cycle_dir': str(cycle_dir)})

    print(json.dumps({'repaired': repaired, 'count': len(repaired)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
