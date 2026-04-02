#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 optimization_cycle 的 OpenCode 计划结果转成正式优化工单。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

OUT_ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/optimization_tickets')
OUT_ROOT.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def extract_files(plan_text: str) -> List[str]:
    files = []
    for line in plan_text.splitlines():
        line = line.strip()
        if line.startswith('- `/') and '`' in line:
            try:
                files.append(line.split('`')[1])
            except Exception:
                pass
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='create_optimization_ticket')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    meta = load_json(cycle_dir / 'meta.json')
    op_path = cycle_dir / 'artifacts' / 'opencode_plan' / 'opencode_result.json'
    sel_path = cycle_dir / 'artifacts' / 'select_target' / 'selected_target.json'
    if not op_path.exists() or not sel_path.exists():
        raise SystemExit('缺少 opencode 计划结果或 target 选择结果')

    op = load_json(op_path)
    sel = load_json(sel_path)
    ticket = sel.get('selected_ticket') or {}
    plan_text = op.get('text', '')
    files = extract_files(plan_text)

    ticket_id = f"{meta.get('cycle_id')}::optimization_execution"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    payload = {
        'ticket_id': ticket_id,
        'created_at': now,
        'source_cycle_id': meta.get('cycle_id'),
        'source_cycle_type': meta.get('cycle_type'),
        'source_ticket': ticket,
        'owner': 'coder',
        'execution_engine': 'opencode',
        'mode': 'plan_to_build_pending_approval',
        'status': 'planned',
        'summary': {
            'title': ticket.get('title'),
            'reason': ticket.get('reason'),
            'category': ticket.get('category'),
        },
        'proposed_files': files,
        'validation_required': [
            'test-expert',
            'backtest-engine'
        ],
        'approval_gates': [
            'strategy parameter changes require review',
            'risk threshold changes require review',
            'no live trading changes',
            'code modifications stay in research/backtest scope'
        ],
        'opencode_plan_text': plan_text,
        'next_step': '等待 master-quant 决定进入 build 或先走低风险参数/验证支线',
    }

    out_json = OUT_ROOT / f"{ticket_id.replace(':', '__')}.json"
    write_json(out_json, payload)

    md = []
    md.append(f"# 优化执行工单\n")
    md.append(f"- ticket_id: {ticket_id}")
    md.append(f"- source_cycle: {meta.get('cycle_id')}")
    md.append(f"- source_ticket: {ticket.get('ticket_id')}")
    md.append(f"- owner: coder")
    md.append(f"- execution_engine: opencode")
    md.append(f"- status: planned")
    md.append("")
    md.append("## 原始问题")
    md.append(f"- title: {ticket.get('title')}")
    md.append(f"- reason: {ticket.get('reason')}")
    md.append("")
    md.append("## 建议修改文件")
    for f in files:
        md.append(f"- {f}")
    md.append("")
    md.append("## OpenCode 计划")
    md.append(plan_text)
    md.append("")
    md.append("## 下一步")
    md.append(payload['next_step'])
    (OUT_ROOT / f"{ticket_id.replace(':', '__')}.md").write_text('\n'.join(md), encoding='utf-8')

    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'optimization_ticket.json', payload)
    print(json.dumps({'ticket_id': ticket_id, 'status': 'planned', 'proposed_files': len(files)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
