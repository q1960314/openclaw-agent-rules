#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, shutil, subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

REPO = Path('/data/agents/master')
WORKTREES = Path('/data/agents/worktrees')
WORKTREES.mkdir(parents=True, exist_ok=True)

def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='create_worktree')
    args = parser.parse_args()
    cycle_dir = Path(args.cycle_dir)
    wt = WORKTREES / cycle_dir.name
    if wt.exists():
        shutil.rmtree(wt)
    proc = subprocess.run(['git','-C',str(REPO),'worktree','add','--detach',str(wt)], capture_output=True, text=True, timeout=120)
    result = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'worktree': str(wt),
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }
    out = cycle_dir / 'artifacts' / args.stage_id / 'worktree.json'
    write_json(out, result)
    print(json.dumps({'worktree': str(wt), 'returncode': proc.returncode}, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
