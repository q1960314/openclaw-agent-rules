#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把优化执行工单拆成低风险先行步骤。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/optimization_tickets')


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticket-file', required=True)
    args = parser.parse_args()

    p = Path(args.ticket_file)
    ticket = load_json(p)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    execution_steps: List[Dict] = [
        {
            'step_id': 'opt_step_1_param_review',
            'owner': 'parameter-evolver',
            'risk_level': 'low',
            'goal': '先做参数空间和参数敏感性复核，不改核心代码结构',
            'requires_manual_approval': False,
        },
        {
            'step_id': 'opt_step_2_backtest_validation',
            'owner': 'backtest-engine',
            'risk_level': 'low',
            'goal': '基于现有代码框架做补充回测与归因，确认是否真需要改代码',
            'requires_manual_approval': False,
        },
        {
            'step_id': 'opt_step_3_code_build_candidate',
            'owner': 'coder/opencode',
            'risk_level': 'medium',
            'goal': '仅当步骤1-2确认需要代码改造后，才进入 OpenCode build 支线',
            'requires_manual_approval': True,
        },
    ]

    ticket['updated_at'] = now
    ticket['status'] = 'split_ready'
    ticket['execution_steps'] = execution_steps
    ticket['next_step'] = '先执行参数/回测低风险支线，再决定是否进入 OpenCode build'
    write_json(p, ticket)

    md_path = p.with_suffix('.steps.md')
    lines = ['# 优化工单执行拆解', '', f"- ticket_id: {ticket.get('ticket_id')}", f"- updated_at: {now}", '']
    for s in execution_steps:
        lines.extend([
            f"## {s['step_id']}",
            f"- owner: {s['owner']}",
            f"- risk_level: {s['risk_level']}",
            f"- goal: {s['goal']}",
            f"- requires_manual_approval: {s['requires_manual_approval']}",
            '',
        ])
    md_path.write_text('\n'.join(lines), encoding='utf-8')

    print(json.dumps({'ticket_id': ticket.get('ticket_id'), 'status': ticket['status'], 'steps': len(execution_steps)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
