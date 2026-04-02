#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据专项诊断结果决定是否进入 execution_cycle。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def classify(reply: str) -> Dict:
    t = reply or ''
    need_code = any(k in t for k in ['是否需要改代码（是', '需要改代码', '必须改代码', '进入代码'])
    no_code = any(k in t for k in ['是否需要改代码（否', '先不改代码', '不直接改代码', '可先在现有框架'])
    return {'need_code': need_code, 'no_code': no_code}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='diagnosis_gate')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    diag = load_json(cycle_dir / 'artifacts' / 'specialist_diagnosis' / 'specialist_diagnosis.json')
    decisions: List[Dict] = []
    need_code_count = 0
    no_code_count = 0
    for item in diag.get('agents', []):
        cls = classify(item.get('reply', ''))
        if cls['need_code']:
            need_code_count += 1
        if cls['no_code']:
            no_code_count += 1
        decisions.append({'agent_id': item.get('agent_id'), **cls})

    if need_code_count >= 2:
        decision = 'execution_cycle_candidate'
        rationale = '多数专项 agent 认为应进入代码执行候选链'
    elif no_code_count >= 2:
        decision = 'continue_low_risk_validation'
        rationale = '多数专项 agent 认为应先做参数/回测/数据低风险验证，不应直接改代码'
    else:
        decision = 'manual_review'
        rationale = '专项结论不够一致，需要人工复核'

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'decision': decision,
        'rationale': rationale,
        'agent_votes': decisions,
        'source_ticket': diag.get('ticket', {}),
    }
    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'diagnosis_gate.json', result)
    (artifact_dir / 'diagnosis_gate.md').write_text('\n'.join([
        '# Diagnosis Gate', '',
        f"- decision: {decision}",
        f"- rationale: {rationale}",
    ]), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
