#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles/execution_cycle')

def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def latest_completed_build_candidate() -> Optional[Path]:
    dirs = sorted([p for p in TRACE_ROOT.iterdir() if p.is_dir()]) if TRACE_ROOT.exists() else []
    for d in reversed(dirs):
        meta = d / 'meta.json'
        gate = d / 'artifacts' / 'execution_gate' / 'execution_gate.json'
        if not meta.exists() or not gate.exists():
            continue
        m = load_json(meta)
        g = load_json(gate)
        if m.get('status') == 'completed' and g.get('decision') == 'build_candidate_ready':
            return d
    return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='select_build_candidate')
    args = parser.parse_args()
    src = latest_completed_build_candidate()
    if not src:
        raise SystemExit('未找到 build_candidate_ready 的 execution_cycle')
    gate = load_json(src / 'artifacts' / 'execution_gate' / 'execution_gate.json')
    plan = load_json(src / 'artifacts' / 'opencode_execution_plan' / 'execution_plan.json')
    task = load_json(src / 'artifacts' / 'prepare_execution_task' / 'execution_task.json')
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'selected': True,
        'source_execution_cycle': src.name,
        'source_execution_dir': str(src),
        'execution_gate': gate,
        'execution_plan': plan,
        'execution_task': task,
    }
    out = Path(args.cycle_dir) / 'artifacts' / args.stage_id / 'selected_build_candidate.json'
    write_json(out, result)
    print(json.dumps({'selected': True, 'source_execution_cycle': src.name}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
