#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, subprocess
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
    parser.add_argument('--stage-id', default='collect_build_diff')
    args = parser.parse_args()
    cycle_dir = Path(args.cycle_dir)
    build = load_json(cycle_dir / 'artifacts' / 'opencode_build' / 'opencode_build.json')
    worktree = build['worktree']
    status = subprocess.run(['git','-C',worktree,'status','--short'], capture_output=True, text=True, timeout=60)
    diffstat = subprocess.run(['git','-C',worktree,'diff','--stat'], capture_output=True, text=True, timeout=60)
    changed = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'worktree': worktree,
        'changed_files': changed,
        'changed_count': len(changed),
        'diff_stat': diffstat.stdout,
    }
    out = cycle_dir / 'artifacts' / args.stage_id / 'build_diff.json'
    write_json(out, result)
    (cycle_dir / 'artifacts' / args.stage_id / 'build_diff.md').write_text(diffstat.stdout or '', encoding='utf-8')
    print(json.dumps({'changed_count': len(changed), 'worktree': worktree}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
