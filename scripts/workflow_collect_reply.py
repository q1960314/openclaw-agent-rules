#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收集 dispatched ticket 的回执；没有真实回复时不要假装成功。"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

QUEUE_ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/queue')
PENDING = QUEUE_ROOT / 'pending'
DISPATCHED = QUEUE_ROOT / 'dispatched'
DONE = QUEUE_ROOT / 'done'
FAILED = QUEUE_ROOT / 'failed'
for d in [PENDING, DISPATCHED, DONE, FAILED]:
    d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def agent_session_store(agent_id: str) -> Path:
    return Path(f'/home/admin/.openclaw/agents/{agent_id}/sessions/sessions.json')


def agent_health(agent_id: str) -> Dict:
    p = agent_session_store(agent_id)
    if not p.exists():
        return {}
    obj = load_json(p)
    key = f'agent:{agent_id}:main'
    item = obj.get(key, {})
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=False)
    parser.add_argument('--stage-id', default='collect_reply')
    args = parser.parse_args()

    cycle_dir = str(Path(args.cycle_dir).resolve()) if args.cycle_dir else None
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    done: List[Dict] = []
    failed: List[Dict] = []
    pending_followup: List[Dict] = []

    for f in sorted(DISPATCHED.glob('*.json')):
        payload = load_json(f)
        if cycle_dir and payload.get('source_cycle_dir') != cycle_dir:
            continue
        result = payload.get('dispatch_result', {})
        agent_id = result.get('agent_id')
        reply_text = result.get('assistant_text')
        ticket_id = payload.get('ticket', {}).get('ticket_id')

        if reply_text:
            payload['queue_status'] = 'done'
            payload['updated_at'] = now
            out = DONE / f.name
            write_json(out, payload)
            f.unlink()
            done.append({'ticket_id': ticket_id, 'agent_id': agent_id, 'reason': 'assistant_text_present'})
            continue

        health = agent_health(agent_id) if agent_id else {}
        aborted = bool(health.get('abortedLastRun'))
        ctx = health.get('contextTokens') or 0
        total = health.get('totalTokens') or 0
        overloaded = bool(ctx and total and total / ctx >= 0.8)

        if aborted or overloaded:
            payload['queue_status'] = 'failed'
            payload['updated_at'] = now
            payload['collect_reply'] = {
                'reason': 'agent_aborted_or_overloaded',
                'abortedLastRun': aborted,
                'contextTokens': ctx,
                'totalTokens': total,
            }
            out = FAILED / f.name
            write_json(out, payload)
            f.unlink()
            failed.append({'ticket_id': ticket_id, 'agent_id': agent_id, 'reason': 'agent_aborted_or_overloaded'})
        else:
            payload['queue_status'] = 'waiting_reply'
            payload['updated_at'] = now
            write_json(f, payload)
            pending_followup.append({'ticket_id': ticket_id, 'agent_id': agent_id, 'reason': 'no_reply_yet'})

    result = {
        'stage': args.stage_id,
        'generated_at': now,
        'done': done,
        'failed': failed,
        'pending_followup': pending_followup,
    }
    if args.cycle_dir:
        artifact = Path(args.cycle_dir) / 'artifacts' / args.stage_id / 'collect_result.json'
        write_json(artifact, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
