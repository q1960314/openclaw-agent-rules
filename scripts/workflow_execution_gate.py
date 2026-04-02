#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 execution_cycle 的 OpenCode 执行计划，判断是否形成 build candidate。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict


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
    parser.add_argument('--stage-id', default='execution_gate')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    plan = load_json(cycle_dir / 'artifacts' / 'opencode_execution_plan' / 'execution_plan.json')
    task = load_json(cycle_dir / 'artifacts' / 'prepare_execution_task' / 'execution_task.json')
    text = plan.get('text', '') or ''
    files = task.get('files', [])

    has_scope = '## 1. Scope' in text or 'Scope' in text
    has_order = '## 2. File Order' in text or 'File Order' in text
    has_changes = '## 3. Minimal Changes' in text or 'Minimal Changes' in text
    has_validation = '## 4. Validation' in text or 'Validation' in text
    has_approval = '## 5. Approval Gates' in text or 'Approval Gates' in text

    build_candidate = all([has_scope, has_order, has_changes, has_validation, has_approval]) and len(files) > 0

    if build_candidate:
        decision = 'build_candidate_ready'
        rationale = '执行计划包含范围、文件顺序、最小改动、验证和审批门，已可作为 build 候选输入'
    else:
        decision = 'manual_refine_required'
        rationale = '执行计划信息不完整，暂不进入 build 候选'

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'decision': decision,
        'rationale': rationale,
        'checks': {
            'has_scope': has_scope,
            'has_order': has_order,
            'has_changes': has_changes,
            'has_validation': has_validation,
            'has_approval': has_approval,
            'file_count': len(files),
        },
        'files': files,
    }

    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'execution_gate.json', result)
    (artifact_dir / 'execution_gate.md').write_text('\n'.join([
        '# Execution Gate', '',
        f"- decision: {decision}",
        f"- rationale: {rationale}",
        f"- file_count: {len(files)}",
    ]), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
