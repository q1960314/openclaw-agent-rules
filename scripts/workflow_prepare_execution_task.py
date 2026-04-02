#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据专项诊断结果生成 coder/OpenCode 执行任务单。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

OPT_TICKET_ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/optimization_tickets')
CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')
FALLBACK_FILES = [
    '/data/agents/master/modules/param_optimizer.py',
    '/data/agents/master/fetch_data_optimized.py',
    '/data/agents/master/run_backtest_v4.py',
    '/data/agents/master/modules/backtest_engine.py',
    '/data/agents/master/modules/strategy_core.py',
]


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def latest_opt_ticket() -> Dict:
    files = sorted(OPT_TICKET_ROOT.glob('*.json'))
    if not files:
        return {}
    return load_json(files[-1])


def collect_replies(diag: Dict) -> List[str]:
    replies = []
    for item in diag.get('agents', []):
        if item.get('reply'):
            replies.append(f"## {item.get('agent_id')}\n{item.get('reply')}")
    return replies


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='prepare_execution_task')
    args = parser.parse_args()

    cfg = load_json(CONFIG)
    code_root = cfg['paths']['codebase_root']
    cycle_dir = Path(args.cycle_dir)
    selected = load_json(cycle_dir / 'artifacts' / 'select_execution_target' / 'selected_execution_target.json')
    gate = selected['decision']
    diag = selected['specialist_diagnosis']
    ticket = gate.get('source_ticket', {})
    opt = latest_opt_ticket()
    files = opt.get('proposed_files') or FALLBACK_FILES
    specialist_text = '\n\n'.join(collect_replies(diag))

    prompt = f'''你是 OpenCode 的代码执行代理，这次不是让你前置诊断，而是执行 coder 任务单。

代码根目录：{code_root}
来源工单：{ticket.get('ticket_id')}
标题：{ticket.get('title')}
原因：{ticket.get('reason')}

专项 agent 已完成诊断，结论如下（供你执行时参考，不要重新做大范围问题归属判断）：
{specialist_text[:5000]}

请你只围绕以下文件工作：
{chr(10).join(['- ' + f for f in files])}

你的任务：
1. 基于上述专项诊断，输出 build-ready 的最小执行计划
2. 明确哪些文件最值得先改，哪些可暂缓
3. 输出最小改动顺序
4. 输出 test/backtest 验证计划
5. 不要扫描无关目录，不要看备份文件，不要自行扩展问题范围

输出格式：
# Execution Plan
## 1. Scope
## 2. File Order
## 3. Minimal Changes
## 4. Validation
## 5. Approval Gates
'''

    payload = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_ticket': ticket,
        'code_root': code_root,
        'files': files,
        'prompt': prompt,
    }
    outdir = cycle_dir / 'artifacts' / args.stage_id
    write_json(outdir / 'execution_task.json', payload)
    (outdir / 'execution_task.md').write_text(prompt, encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'ticket_id': ticket.get('ticket_id'), 'files': len(files)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
