#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送 workflow 结果到 Feishu（或其他 OpenClaw channel）。"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')
TRACE_ROOT = Path('/home/admin/.openclaw/workspace/master/traces/cycles')


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def latest_cycle_dir(cycle_type: str) -> Optional[Path]:
    base = TRACE_ROOT / cycle_type
    if not base.exists():
        return None
    dirs = sorted([p for p in base.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir')
    parser.add_argument('--cycle-type', choices=['daily_research', 'weekly_health'])
    parser.add_argument('--mode', choices=['success', 'failure', 'interrupted'], default='success')
    parser.add_argument('--message')
    args = parser.parse_args()

    cfg = load_json(CONFIG)
    notif = cfg.get('notifications', {})
    cycle_dir = Path(args.cycle_dir) if args.cycle_dir else (latest_cycle_dir(args.cycle_type) if args.cycle_type else None)
    if not cycle_dir:
        raise SystemExit('未提供可用 cycle_dir')

    meta = load_json(cycle_dir / 'meta.json')
    payload_path = cycle_dir / 'reports' / 'notification_payload.json'
    brief_path = cycle_dir / 'reports' / 'user_brief.md'

    if args.message:
        text = args.message
    elif payload_path.exists():
        text = load_json(payload_path).get('message', '')
    elif brief_path.exists():
        text = brief_path.read_text(encoding='utf-8')
    else:
        text = f"循环 {meta.get('cycle_id')} 状态: {meta.get('status')}"

    prefix = {
        'success': '【生态循环完成】',
        'failure': '【生态循环失败】',
        'interrupted': '【生态循环中断】',
    }[args.mode]
    final_text = f"{prefix}\n{text}"

    cmd = [
        '/home/admin/.local/share/pnpm/openclaw', 'message', 'send',
        '--channel', notif.get('channel', 'feishu'),
        '--account', notif.get('account_id', 'master-feishu'),
        '--target', notif.get('target', ''),
        '--message', final_text,
        '--json',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    result = {
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'message': final_text,
        'cycle_id': meta.get('cycle_id'),
    }
    out = cycle_dir / 'reports' / f'notify_{args.mode}.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
