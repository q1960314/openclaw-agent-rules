#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行 execution_cycle 的 OpenCode 执行计划（仅计划，不直接 build）。"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def extract_texts(lines: List[str]) -> str:
    texts = []
    for raw in lines:
        try:
            item = json.loads(raw)
        except Exception:
            continue
        if item.get('type') == 'text':
            part = item.get('part', {})
            if part.get('text'):
                texts.append(part['text'])
    return '\n'.join(texts).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='opencode_execution_plan')
    args = parser.parse_args()

    cfg = load_json(CONFIG)
    ocfg = cfg.get('opencode', {})
    model = ocfg.get('plan_model', 'bailian/qwen3-coder-plus')
    code_root = cfg['paths']['codebase_root']
    cycle_dir = Path(args.cycle_dir)
    task = load_json(cycle_dir / 'artifacts' / 'prepare_execution_task' / 'execution_task.json')
    prompt = task['prompt']

    cmd = [
        '/home/admin/.npm-global/bin/opencode', 'run',
        '--format', 'json',
        '--agent', 'plan',
        '--model', model,
        '--dir', code_root,
        prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
    lines = [x for x in proc.stdout.splitlines() if x.strip()]
    text = extract_texts(lines)

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model': model,
        'returncode': proc.returncode,
        'text': text,
        'raw_lines': len(lines),
        'stderr': proc.stderr[-2000:],
    }
    outdir = cycle_dir / 'artifacts' / args.stage_id
    write_json(outdir / 'execution_plan.json', result)
    (outdir / 'execution_plan.md').write_text(text or '', encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'returncode': proc.returncode, 'text_chars': len(text)}, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
