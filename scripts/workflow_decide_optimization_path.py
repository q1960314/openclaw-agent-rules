#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据低风险验证结果决定 optimization_cycle 下一跳。"""

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


def classify(text: str) -> Dict:
    t = text or ''
    need_code = any(k in t for k in ['必须改代码', '需要改代码', '进入代码', '代码逻辑问题'])
    prefer_param = any(k in t for k in ['先不改代码', '先在现有框架', '参数问题', '参数优化'])
    return {'need_code': need_code, 'prefer_param': prefer_param}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='decide_next_path')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    val = load_json(cycle_dir / 'artifacts' / 'low_risk_validation' / 'low_risk_validation.json')
    ptxt = val.get('parameter_evolver', {}).get('reply', '')
    btxt = val.get('backtest_engine', {}).get('reply', '')

    pc = classify(ptxt)
    bc = classify(btxt)

    if pc['prefer_param'] and bc['prefer_param'] and not (pc['need_code'] or bc['need_code']):
        decision = 'continue_low_risk_validation'
        rationale = '两侧结论都倾向先做参数与回测低风险验证，不直接进入代码改造'
    elif pc['need_code'] or bc['need_code']:
        decision = 'build_candidate'
        rationale = '至少一侧结论认为必须或应尽快进入代码逻辑审查/改造'
    else:
        decision = 'manual_review'
        rationale = '两侧结论不够一致，建议人工复核后再决定'

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'decision': decision,
        'rationale': rationale,
        'parameter_classification': pc,
        'backtest_classification': bc,
    }
    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'decision.json', result)
    (artifact_dir / 'decision.md').write_text('\n'.join([
        '# Optimization Decision', '',
        f"- decision: {decision}",
        f"- rationale: {rationale}",
    ]), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
