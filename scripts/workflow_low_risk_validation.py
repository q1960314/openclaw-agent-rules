#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""optimization_cycle: 自动执行低风险验证支线。

目标：
1. 读取 optimization_execution 工单
2. 自动调用 parameter-evolver / backtest-engine
3. 收集结构化回复
4. 形成后续 decision gate 输入
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE_ROOT = Path('/home/admin/.openclaw/workspace/master')
RECOVER_SCRIPT = WORKSPACE_ROOT / 'scripts' / 'workflow_agent_recover.py'
TICKET_ROOT = WORKSPACE_ROOT / 'reports' / 'workflow' / 'optimization_tickets'


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def extract_json_object(text: str) -> Optional[Dict]:
    text = (text or '').strip()
    if not text:
        return None
    for start in range(len(text)):
        if text[start] != '{':
            continue
        for end in range(len(text), start, -1):
            if text[end - 1] != '}':
                continue
            try:
                return json.loads(text[start:end])
            except Exception:
                continue
    return None


def extract_reply(parsed: Optional[Dict]) -> str:
    if not parsed:
        return ''
    if 'reply' in parsed and isinstance(parsed['reply'], str):
        return parsed['reply']
    result = parsed.get('result', {}) if isinstance(parsed, dict) else {}
    payloads = result.get('payloads', []) or []
    texts: List[str] = []
    for item in payloads:
        if isinstance(item, dict) and item.get('text'):
            texts.append(item['text'])
    return '\n'.join([t for t in texts if t]).strip()


def agent_health(agent_id: str) -> Dict:
    path = Path(f'/home/admin/.openclaw/agents/{agent_id}/sessions/sessions.json')
    if not path.exists():
        return {}
    obj = load_json(path)
    return obj.get(f'agent:{agent_id}:main', {})


def unhealthy(agent_id: str) -> bool:
    h = agent_health(agent_id)
    if not h:
        return False
    ctx = h.get('contextTokens') or 0
    total = h.get('totalTokens') or 0
    aborted = bool(h.get('abortedLastRun'))
    overloaded = bool(ctx and total and total / ctx >= 0.80)
    return aborted or overloaded


def recover(agent_id: str) -> Dict:
    cmd = [
        '/home/admin/miniconda3/envs/vnpy_env/bin/python',
        str(RECOVER_SCRIPT),
        '--agent-id', agent_id,
        '--force'
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {
        'returncode': proc.returncode,
        'stdout': proc.stdout[-2000:],
        'stderr': proc.stderr[-1000:],
        'parsed': extract_json_object(proc.stdout),
    }


def run_agent(agent_id: str, prompt: str, timeout: int = 300) -> Dict:
    recovery = None
    if unhealthy(agent_id):
        recovery = recover(agent_id)
    cmd = [
        '/home/admin/.local/share/pnpm/openclaw', 'agent',
        '--agent', agent_id,
        '--message', prompt,
        '--timeout', str(timeout),
        '--json',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    parsed = extract_json_object(proc.stdout)
    reply = extract_reply(parsed)
    return {
        'agent_id': agent_id,
        'returncode': proc.returncode,
        'recovery': recovery,
        'reply': reply,
        'parsed_json': bool(parsed),
        'stdout_tail': proc.stdout[-2000:],
        'stderr': proc.stderr[-1000:],
    }


def latest_ticket() -> Optional[Path]:
    files = sorted(TICKET_ROOT.glob('*.json'))
    return files[-1] if files else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='low_risk_validation')
    parser.add_argument('--ticket-file', default='')
    args = parser.parse_args()

    ticket_file = Path(args.ticket_file) if args.ticket_file else latest_ticket()
    if not ticket_file or not ticket_file.exists():
        raise SystemExit('未找到 optimization ticket')
    ticket = load_json(ticket_file)

    source = ticket.get('source_ticket', {})
    op_plan = ticket.get('opencode_plan_text', '')
    common = f"""【优化支线低风险验证】
来源工单: {ticket.get('ticket_id')}
原始策略工单: {source.get('ticket_id')}
标题: {source.get('title')}
原因: {source.get('reason')}

OpenCode 计划摘要：
{op_plan[:2500]}

请保持在研究/回测范围，不修改实盘参数，不做交易动作。
"""

    param_prompt = common + """
你是 parameter-evolver。
请只做低风险参数验证建议，输出：
1. 当前最值得先测的参数组
2. 参数扫描顺序
3. 是否必须改代码（是/否）
4. 进入下一阶段的判断条件
"""

    backtest_prompt = common + """
你是 backtest-engine。
请只做低风险回测验证建议，输出：
1. 先补跑哪些验证
2. 当前问题更偏参数还是代码
3. 是否必须改代码（是/否）
4. 进入下一阶段的判断条件
"""

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    param_result = run_agent('parameter-evolver', param_prompt, timeout=360)
    backtest_result = run_agent('backtest-engine', backtest_prompt, timeout=360)

    result = {
        'stage': args.stage_id,
        'generated_at': now,
        'ticket_file': str(ticket_file),
        'ticket_id': ticket.get('ticket_id'),
        'parameter_evolver': param_result,
        'backtest_engine': backtest_result,
    }
    artifact_dir = Path(args.cycle_dir) / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'low_risk_validation.json', result)

    lines = ['# Low Risk Validation', '', f"- ticket_id: {ticket.get('ticket_id')}", f"- generated_at: {now}", '']
    for label, item in [('parameter-evolver', param_result), ('backtest-engine', backtest_result)]:
        lines.extend([
            f"## {label}",
            f"- returncode: {item.get('returncode')}",
            '',
            item.get('reply') or '(no reply)',
            '',
        ])
    (artifact_dir / 'low_risk_validation.md').write_text('\n'.join(lines), encoding='utf-8')

    ok = param_result.get('returncode') == 0 and backtest_result.get('returncode') == 0
    print(json.dumps({'stage': args.stage_id, 'ticket_id': ticket.get('ticket_id'), 'ok': ok}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
