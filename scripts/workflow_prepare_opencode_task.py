#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 optimization_cycle 生成 OpenCode 任务提示。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')


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
    parser.add_argument('--stage-id', default='prepare_task')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    selected = load_json(cycle_dir / 'artifacts' / 'select_target' / 'selected_target.json')
    if not selected.get('selected'):
        raise SystemExit('未选择到 optimization target')

    cfg = load_json(CONFIG)
    code_root = cfg['paths']['codebase_root']
    ticket = selected['selected_ticket']

    prompt = f'''你正在维护一个中国A股量化回测/选股系统，代码根目录为 {code_root}。

当前进入 optimization_cycle，来源工单如下：
- ticket_id: {ticket.get('ticket_id')}
- category: {ticket.get('category')}
- title: {ticket.get('title')}
- reason: {ticket.get('reason')}
- suggested_next_step: {ticket.get('suggested_next_step')}

请先做“计划模式”输出，不要直接进行高风险改动。你的任务：
1. 阅读与该工单最相关的代码文件
2. 判断这是参数问题、策略逻辑问题、数据问题，还是回测框架问题
3. 给出最小改动路径
4. 给出建议修改文件列表
5. 给出验证方案（test/backtest）
6. 明确哪些改动必须人工审批后才能执行

强约束：
- 只围绕中国A股量化回测/选股系统
- 不做实盘交易动作
- 不修改实盘参数
- 不删除大量文件
- 默认输出“计划”，不要直接 build

输出格式：
# OpenCode Optimization Plan
## 1. Diagnosis
## 2. Minimal Change Path
## 3. Files To Touch
## 4. Validation Plan
## 5. Approval Gates
'''

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ticket': ticket,
        'code_root': code_root,
        'prompt': prompt,
    }
    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'opencode_task.json', result)
    (artifact_dir / 'opencode_task.md').write_text(prompt, encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'ticket_id': ticket.get('ticket_id'), 'code_root': code_root}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
