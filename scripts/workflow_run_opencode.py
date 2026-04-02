#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 optimization_cycle 中运行 OpenCode（默认 plan 模式）。"""

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
    texts: List[str] = []
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
    parser.add_argument('--stage-id', default='/home/admin/.npm-global/bin/opencode_plan')
    args = parser.parse_args()

    cfg = load_json(CONFIG)
    ocfg = cfg.get('/home/admin/.npm-global/bin/opencode', {})
    mode = ocfg.get('mode', 'plan')
    model = ocfg.get('plan_model') if mode == 'plan' else ocfg.get('build_model')
    agent = 'plan' if mode == 'plan' else 'build'
    code_root = cfg['paths']['codebase_root']

    cycle_dir = Path(args.cycle_dir)
    task = load_json(cycle_dir / 'artifacts' / 'prepare_task' / '/home/admin/.npm-global/bin/opencode_task.json')
    prompt = task['prompt']

    cmd = [
        '/home/admin/.npm-global/bin/opencode', 'run',
        '--format', 'json',
        '--agent', agent,
        '--model', model,
        '--dir', code_root,
        prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    text = extract_texts(lines)

    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mode': mode,
        'agent': agent,
        'model': model,
        'returncode': proc.returncode,
        'text': text,
        'raw_lines': len(lines),
        'stderr': proc.stderr[-2000:],
    }
    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / '/home/admin/.npm-global/bin/opencode_result.json', result)
    (artifact_dir / '/home/admin/.npm-global/bin/opencode_result.md').write_text(text or '', encoding='utf-8')
    print(json.dumps({'stage': args.stage_id, 'mode': mode, 'agent': agent, 'model': model, 'returncode': proc.returncode, 'text_chars': len(text)}, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
