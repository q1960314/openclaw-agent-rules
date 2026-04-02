#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles/build_candidate_cycle')

def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def latest_candidate() -> Optional[Path]:
    dirs = sorted([p for p in TRACE_ROOT.iterdir() if p.is_dir()]) if TRACE_ROOT.exists() else []
    for d in reversed(dirs):
        meta = d / 'meta.json'
        gate = d / 'artifacts' / 'build_gate' / 'build_gate.json'
        if not meta.exists() or not gate.exists():
            continue
        m = load_json(meta)
        g = load_json(gate)
        if m.get('status') == 'completed' and g.get('decision') == 'validation_cycle_candidate':
            return d
    return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='select_validation_target')
    args = parser.parse_args()
    src = latest_candidate()
    if not src:
        raise SystemExit('未找到 validation_cycle_candidate 的 build cycle')
    build = load_json(src / 'artifacts' / 'opencode_build' / 'opencode_build.json')
    diff = load_json(src / 'artifacts' / 'collect_build_diff' / 'build_diff.json')
    gate = load_json(src / 'artifacts' / 'build_gate' / 'build_gate.json')
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'selected': True,
        'source_build_cycle': src.name,
        'source_build_dir': str(src),
        'build': build,
        'diff': diff,
        'gate': gate,
    }
    out = Path(args.cycle_dir) / 'artifacts' / args.stage_id / 'selected_validation_target.json'
    write_json(out, result)
    print(json.dumps({'selected': True, 'source_build_cycle': src.name, 'changed_count': diff.get('changed_count', 0)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
