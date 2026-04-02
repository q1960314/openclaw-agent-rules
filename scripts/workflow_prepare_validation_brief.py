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
    parser.add_argument('--stage-id', default='prepare_validation_brief')
    args = parser.parse_args()
    cycle_dir = Path(args.cycle_dir)
    sel = load_json(cycle_dir / 'artifacts' / 'select_validation_target' / 'selected_validation_target.json')
    diff = sel['diff']
    build = sel['build']
    changed = diff.get('changed_files', [])
    brief = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_build_cycle': sel.get('source_build_cycle'),
        'changed_files': changed,
        'changed_count': diff.get('changed_count', 0),
        'build_summary': build.get('text', '')[:4000],
        'validation_targets': ['test-expert', 'backtest-engine'],
    }
    out = cycle_dir / 'artifacts' / args.stage_id / 'validation_brief.json'
    write_json(out, brief)
    (cycle_dir / 'artifacts' / args.stage_id / 'validation_brief.md').write_text('\n'.join([
        '# Validation Brief', '',
        f"- source_build_cycle: {sel.get('source_build_cycle')}",
        f"- changed_count: {diff.get('changed_count', 0)}",
        '## Changed Files',
        *[f'- {x}' for x in changed]
    ]), encoding='utf-8')
    print(json.dumps({'changed_count': diff.get('changed_count', 0), 'targets': ['test-expert', 'backtest-engine']}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
