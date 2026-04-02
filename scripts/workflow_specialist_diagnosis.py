#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专项诊断链：由专项 agent 先判断问题归属，不让 OpenCode 前置诊断。"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE_ROOT = Path('/home/admin/.openclaw/workspace/master')
RECOVER_SCRIPT = WORKSPACE_ROOT / 'scripts' / 'workflow_agent_recover.py'
TRACE_ROOT = WORKSPACE_ROOT / 'traces' / 'cycles'
QUEUE_DONE = WORKSPACE_ROOT / 'reports' / 'workflow' / 'queue' / 'done'


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
    if isinstance(parsed.get('reply'), str):
        return parsed['reply']
    result = parsed.get('result', {}) if isinstance(parsed, dict) else {}
    payloads = result.get('payloads', []) or []
    texts = []
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


def latest_actionable_done_ticket() -> Optional[Path]:
    files = sorted(QUEUE_DONE.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            payload = load_json(path)
        except Exception:
            continue
        category = payload.get('ticket', {}).get('category')
        if category in {'strategy_review', 'weekly_optimization', 'data_quality'}:
            return path
    return None


def select_agents(ticket: Dict) -> List[str]:
    category = ticket.get('category')
    if category in {'strategy_review', 'weekly_optimization'}:
        return ['strategy-expert', 'parameter-evolver', 'backtest-engine']
    if category == 'data_quality':
        return ['data-collector', 'backtest-engine']
    return ['strategy-expert']


def build_prompt(ticket: Dict, source_cycle_dir: str, agent_id: str) -> str:
    prefix = f"""【专项诊断任务】
来源工单: {ticket.get('ticket_id')}
类别: {ticket.get('category')}
标题: {ticket.get('title')}
原因: {ticket.get('reason')}
建议下一步: {ticket.get('suggested_next_step')}
来源循环目录: {source_cycle_dir}

要求：
- 只从你的专项职责角度判断
- 不做交易动作
- 不修改实盘参数
- 不直接改代码
- 只回答你这个 agent 应该负责判断的部分

输出格式：
1. 当前判断
2. 问题归属
3. 是否需要改代码（是/否）
4. 下一步建议
5. 风险与验收要点
"""

    if agent_id == 'strategy-expert':
        suffix = '你是 strategy-expert。重点判断：这是否主要是策略逻辑/战法适配/市场环境错配问题。'
    elif agent_id == 'parameter-evolver':
        suffix = '你是 parameter-evolver。重点判断：这是否主要是参数空间、阈值、止损止盈、权重配置问题。'
    elif agent_id == 'backtest-engine':
        suffix = '你是 backtest-engine。重点判断：这是否主要是回测验证不足、样本外不足、归因不清，还是需要代码修改。'
    elif agent_id == 'data-collector':
        suffix = '你是 data-collector。重点判断：这是否主要是数据缺失、数据质量、字段问题，还是不需要你介入。'
    else:
        suffix = f'你是 {agent_id}。请从你的专项职责判断。'

    return prefix + '\n' + suffix


def run_agent(agent_id: str, prompt: str, timeout: int = 360) -> Dict:
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
        'reply': reply,
        'recovery': recovery,
        'parsed_json': bool(parsed),
        'stdout_tail': proc.stdout[-2000:],
        'stderr': proc.stderr[-1000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='specialist_diagnosis')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    target = latest_actionable_done_ticket()
    if not target:
        raise SystemExit('未找到可诊断的已完成工单')

    payload = load_json(target)
    ticket = payload.get('ticket', {})
    source_cycle_dir = payload.get('source_cycle_dir', '')
    agents = select_agents(ticket)

    results: List[Dict] = []
    for agent_id in agents:
        prompt = build_prompt(ticket, source_cycle_dir, agent_id)
        results.append(run_agent(agent_id, prompt))

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = {
        'stage': args.stage_id,
        'generated_at': now,
        'ticket': ticket,
        'source_queue_file': str(target),
        'source_cycle_dir': source_cycle_dir,
        'agents': results,
    }

    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'specialist_diagnosis.json', result)

    md = ['# Specialist Diagnosis', '', f"- ticket_id: {ticket.get('ticket_id')}", f"- generated_at: {now}", '']
    for item in results:
        md.extend([
            f"## {item['agent_id']}",
            item.get('reply') or '(no reply)',
            '',
        ])
    (artifact_dir / 'specialist_diagnosis.md').write_text('\n'.join(md), encoding='utf-8')
    ok = all(x.get('returncode') == 0 for x in results)
    print(json.dumps({'stage': args.stage_id, 'ticket_id': ticket.get('ticket_id'), 'agents': agents, 'ok': ok}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
