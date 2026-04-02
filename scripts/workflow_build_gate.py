#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
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

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='build_gate')
    args = parser.parse_args()
    cycle_dir = Path(args.cycle_dir)
    diff = load_json(cycle_dir / 'artifacts' / 'collect_build_diff' / 'build_diff.json')
    build = load_json(cycle_dir / 'artifacts' / 'opencode_build' / 'opencode_build.json')
    changed_count = diff.get('changed_count', 0)
    has_summary = bool(build.get('text'))
    if changed_count > 0:
        decision = 'validation_cycle_candidate'
        rationale = '已检测到 worktree 中存在实际代码改动，进入验证候选链'
    elif has_summary:
        decision = 'no_code_change'
        rationale = 'OpenCode 有输出但未产生代码 diff，暂不进入验证链'
    else:
        decision = 'manual_review'
        rationale = 'build 输出异常，需人工复核'
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'decision': decision,
        'rationale': rationale,
        'changed_count': changed_count,
        'changed_files': diff.get('changed_files', []),
    }
    out = cycle_dir / 'artifacts' / args.stage_id / 'build_gate.json'
    write_json(out, result)
    (cycle_dir / 'artifacts' / args.stage_id / 'build_gate.md').write_text('\n'.join([
        '# Build Gate', '',
        f"- decision: {decision}",
        f"- rationale: {rationale}",
        f"- changed_count: {changed_count}",
    ]), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
