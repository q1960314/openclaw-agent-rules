#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG = Path('/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json')


def load_config() -> dict[str, Any]:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    return {}


def build_opencode_request(task: dict[str, Any], task_dir: str | Path) -> dict[str, Any]:
    cfg = load_config()
    ocfg = cfg.get('opencode', {})
    metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
    worker_role = task.get('role') or metadata.get('worker_role') or 'coder'
    repo_root = metadata.get('code_root') or cfg.get('paths', {}).get('codebase_root') or '/data/agents/master'
    mode = metadata.get('opencode_mode') or ocfg.get('mode', 'plan')
    model = metadata.get('opencode_model') or (ocfg.get('build_model') if mode == 'build' else ocfg.get('plan_model')) or 'bailian/qwen3-coder-plus'
    agent = 'build' if mode == 'build' else 'plan'

    objective = task.get('objective') or task.get('title') or 'Complete the assigned task.'
    constraints = task.get('constraints', [])
    acceptance = task.get('acceptance_criteria', [])
    input_artifacts = task.get('input_artifacts') or task.get('input_refs') or []
    target_files = metadata.get('target_files', []) if isinstance(metadata.get('target_files', []), list) else []

    lines: list[str] = [
        f'You are the {worker_role} worker execution engine for a quantitative research system.',
        '',
        f'Repository root: {repo_root}',
        f'Mode: {mode}',
        f'Objective: {objective}',
        '',
        'Constraints:',
    ]
    if constraints:
        lines.extend(f'- {item}' for item in constraints)
    else:
        lines.append('- No additional constraints provided.')

    lines.extend(['', 'Acceptance criteria:'])
    if acceptance:
        lines.extend(f'- {item}' for item in acceptance)
    else:
        lines.append('- Produce a concise execution result.')

    lines.extend(['', 'Input artifacts:'])
    if input_artifacts:
        lines.extend(f'- {item}' for item in input_artifacts)
    else:
        lines.append('- No explicit input artifacts provided.')

    lines.extend(['', 'Preferred target files (relative to execution root):'])
    if target_files:
        lines.extend(f'- {item}' for item in target_files)
    else:
        lines.append('- No explicit target files provided.')

    lines.extend([
        '',
        'Execution rules:',
        '- The worker runtime captures artifacts separately; do not write into traces/jobs or task artifact directories.',
        '- Stay inside the provided execution root only.',
        '- If mode=plan, do not make risky code changes; output a concrete implementation plan.',
        '- If mode=build, make the minimal necessary code edits and summarize them.',
        '- Do not touch production secrets or runtime credentials.',
        '- Always end with a concise summary of what was done.',
    ])

    return {
        'task_id': task.get('task_id') or Path(task_dir).name,
        'mode': mode,
        'agent': agent,
        'model': model,
        'repo_root': repo_root,
        'code_root': repo_root,
        'worker_role': worker_role,
        'target_files': target_files,
        'prompt': '\n'.join(lines),
    }
