#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动续流器：根据已完成 cycle 自动判断并触发下一步。"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

WORKSPACE_ROOT = Path('/home/admin/.openclaw/workspace/master')
TRACE_ROOT = WORKSPACE_ROOT / 'traces' / 'cycles'
STATE_DIR = WORKSPACE_ROOT / 'reports' / 'workflow' / 'dispatcher'
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / 'state.json'
PYTHON = '/home/admin/miniconda3/envs/vnpy_env/bin/python'
ENGINE = WORKSPACE_ROOT / 'scripts' / 'workflow_engine.py'
MESSAGE_FILE = STATE_DIR / 'last_dispatch.json'


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def state() -> Dict:
    if STATE_FILE.exists():
        obj = load_json(STATE_FILE)
        obj.setdefault('handled', {})
        obj.setdefault('failed', {})
        obj.setdefault('history', [])
        return obj
    return {'handled': {}, 'failed': {}, 'history': []}


def latest_completed(cycle_type: str) -> Optional[Path]:
    base = TRACE_ROOT / cycle_type
    if not base.exists():
        return None
    dirs = sorted([p for p in base.iterdir() if p.is_dir()])
    for d in reversed(dirs):
        meta = d / 'meta.json'
        if not meta.exists():
            continue
        m = load_json(meta)
        if m.get('status') == 'completed':
            return d
    return None


def run_cycle(cycle_type: str) -> Dict:
    cmd = [PYTHON, str(ENGINE), 'run', '--cycle-type', cycle_type, '--trigger', 'auto_dispatcher']
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
    return {
        'cycle_type': cycle_type,
        'returncode': proc.returncode,
        'stdout': proc.stdout[-4000:],
        'stderr': proc.stderr[-2000:],
    }


def should_launch_diagnosis(st: Dict) -> Optional[Dict]:
    latest_research = latest_completed('daily_research')
    latest_weekly = latest_completed('weekly_health')
    candidates = [x for x in [latest_research, latest_weekly] if x]
    if not candidates:
        return None
    src = sorted(candidates, key=lambda p: p.name)[-1]
    if st['handled'].get('diagnosis_from') == src.name:
        return None
    return {'action': 'launch_diagnosis_cycle', 'source_cycle': src.name, 'source_dir': str(src)}


def should_launch_execution(st: Dict) -> Optional[Dict]:
    diag = latest_completed('diagnosis_cycle')
    if not diag:
        return None
    gate = diag / 'artifacts' / 'diagnosis_gate' / 'diagnosis_gate.json'
    if not gate.exists():
        return None
    gate_data = load_json(gate)
    if gate_data.get('decision') != 'execution_cycle_candidate':
        return None
    if st['handled'].get('execution_from') == diag.name:
        return None
    return {'action': 'launch_execution_cycle', 'source_cycle': diag.name, 'source_dir': str(diag)}


def should_launch_build_candidate(st: Dict) -> Optional[Dict]:
    exe = latest_completed('execution_cycle')
    if not exe:
        return None
    gate = exe / 'artifacts' / 'execution_gate' / 'execution_gate.json'
    if not gate.exists():
        return None
    gate_data = load_json(gate)
    if gate_data.get('decision') != 'build_candidate_ready':
        return None
    if st['handled'].get('build_from') == exe.name:
        return None
    if st['failed'].get('build_from') == exe.name:
        return None
    return {'action': 'launch_build_candidate_cycle', 'source_cycle': exe.name, 'source_dir': str(exe)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()

    st = state()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    decision = should_launch_build_candidate(st) or should_launch_execution(st) or should_launch_diagnosis(st)
    if not decision:
        result = {'time': now, 'action': 'no_action'}
        write_json(MESSAGE_FILE, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if decision['action'] == 'launch_diagnosis_cycle':
        launched = run_cycle('diagnosis_cycle')
        if launched['returncode'] == 0:
            st['handled']['diagnosis_from'] = decision['source_cycle']
    elif decision['action'] == 'launch_execution_cycle':
        launched = run_cycle('execution_cycle')
        if launched['returncode'] == 0:
            st['handled']['execution_from'] = decision['source_cycle']
    elif decision['action'] == 'launch_build_candidate_cycle':
        launched = run_cycle('build_candidate_cycle')
        if launched['returncode'] == 0:
            st['handled']['build_from'] = decision['source_cycle']
            st['failed'].pop('build_from', None)
        else:
            st['failed']['build_from'] = decision['source_cycle']
    else:
        launched = {'returncode': 1, 'stderr': f"unknown action {decision['action']}"}

    hist = {
        'time': now,
        'decision': decision,
        'launched': launched,
    }
    st['history'].append(hist)
    st['history'] = st['history'][-30:]
    write_json(STATE_FILE, st)
    write_json(MESSAGE_FILE, hist)
    print(json.dumps(hist, ensure_ascii=False, indent=2))
    return 0 if launched.get('returncode') == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
