#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _parse_status_lines(text: str) -> set[str]:
    lines = set()
    for raw in text.splitlines():
        if raw.strip():
            lines.add(raw.rstrip())
    return lines


def _status_to_paths(lines: set[str]) -> list[str]:
    paths: list[str] = []
    for line in sorted(lines):
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if path:
            paths.append(path)
    return paths


def _extract_texts(stdout: str) -> str:
    texts: list[str] = []
    for raw in stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except Exception:
            continue
        if item.get('type') == 'text':
            part = item.get('part', {})
            if part.get('text'):
                texts.append(part['text'])
    return '\n'.join(texts).strip()


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-1000:]}")
    return proc


def _ensure_build_worktree(repo_root: Path, task_id: str) -> Path:
    sandbox_root = Path('/home/admin/.openclaw/workspace/master/traces/jobs') / task_id / 'sandbox'
    sandbox_root.mkdir(parents=True, exist_ok=True)
    worktree_path = sandbox_root / 'worktree'

    _run(['git', 'worktree', 'prune'], cwd=repo_root, check=False)
    _run(['git', 'worktree', 'remove', '--force', str(worktree_path)], cwd=repo_root, check=False)
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)

    _run(['git', 'worktree', 'add', '--force', '--detach', str(worktree_path), 'HEAD'], cwd=repo_root)
    return worktree_path


def _capture_diff(execution_root: Path) -> tuple[list[str], str]:
    _run(['git', 'add', '-N', '--all'], cwd=execution_root, check=False)
    status_proc = _run(['git', 'status', '--short'], cwd=execution_root, check=False)
    changed_paths = _status_to_paths(_parse_status_lines(status_proc.stdout))
    diff_proc = _run(['git', 'diff', '--binary', '--no-ext-diff', '--', '.'], cwd=execution_root, check=False)
    return changed_paths, diff_proc.stdout


def run_opencode(request: dict[str, Any], timeout: int = 240) -> dict[str, Any]:
    repo_root = Path(request.get('repo_root') or request['code_root'])
    execution_root = repo_root
    worktree_path: str | None = None

    effective_request = dict(request)
    if request.get('mode') == 'build':
        execution_root = _ensure_build_worktree(repo_root, request['task_id'])
        worktree_path = str(execution_root)
        prefix = '\n'.join([
            f'Execution root for this run: {execution_root}',
            'Only modify files under this execution root.',
            'Do not create or edit files under traces/jobs, task directories, or other external paths.',
            '',
        ])
        effective_request['prompt'] = prefix + request['prompt']
    effective_request['code_root'] = str(execution_root)

    cmd = [
        'opencode', 'run',
        '--format', 'json',
        '--agent', effective_request['agent'],
        '--model', effective_request['model'],
        '--dir', str(execution_root),
        effective_request['prompt'],
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(cmd, 124, stdout=exc.stdout or '', stderr=(exc.stderr or '') + '\nTIMEOUT')
        timed_out = True

    changed_paths, diff_text = _capture_diff(execution_root)

    return {
        'returncode': proc.returncode,
        'timed_out': timed_out,
        'mode': effective_request['mode'],
        'agent': effective_request['agent'],
        'model': effective_request['model'],
        'repo_root': str(repo_root),
        'code_root': str(execution_root),
        'worktree_path': worktree_path,
        'prompt': effective_request['prompt'],
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'text': _extract_texts(proc.stdout),
        'changed_paths': changed_paths,
        'diff_text': diff_text,
        'raw_line_count': len([x for x in proc.stdout.splitlines() if x.strip()]),
        'effective_request': effective_request,
    }
