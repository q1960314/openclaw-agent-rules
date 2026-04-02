#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 diagnosis_cycle 的成功结果中选择 execution target。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles/diagnosis_cycle')


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def latest_completed_cycle() -> Optional[Path]:
    dirs = sorted([p for p in TRACE_ROOT.iterdir() if p.is_dir()]) if TRACE_ROOT.exists() else []
    for d in reversed(dirs):
        meta = d / 'meta.json'
        gate = d / 'artifacts' / 'diagnosis_gate' / 'diagnosis_gate.json'
        if meta.exists() and gate.exists():
            m = load_json(meta)
            g = load_json(gate)
            if m.get('status') == 'completed' and g.get('decision') == 'execution_cycle_candidate':
                return d
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='select_execution_target')
    args = parser.parse_args()

    source = latest_completed_cycle()
    if not source:
        raise SystemExit('未找到可进入 execution_cycle 的 diagnosis_cycle 结果')

    gate = load_json(source / 'artifacts' / 'diagnosis_gate' / 'diagnosis_gate.json')
    diag = load_json(source / 'artifacts' / 'specialist_diagnosis' / 'specialist_diagnosis.json')
    payload = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_diagnosis_cycle': source.name,
        'source_diagnosis_dir': str(source),
        'decision': gate,
        'specialist_diagnosis': diag,
        'selected': True,
    }
    out = Path(args.cycle_dir) / 'artifacts' / args.stage_id / 'selected_execution_target.json'
    write_json(out, payload)
    print(json.dumps({'stage': args.stage_id, 'selected': True, 'source_diagnosis_cycle': source.name}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
