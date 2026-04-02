#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / 'runtime'
ADAPTER = BASE / 'adapters' / 'opencode'
for p in (RUNTIME, ADAPTER):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from worker_base import WorkerBase  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402
from opencode_adapter import run_opencode  # noqa: E402
from opencode_fallback_policy import decide_fallback  # noqa: E402
from opencode_result_normalizer import OpenCodeResultNormalizer  # noqa: E402
from opencode_task_builder import build_opencode_request  # noqa: E402


class FinanceLearnerWorker(WorkerBase):
    def __init__(self):
        super().__init__('finance-learner')

    def execute_task(self, task_dir: Path, task: dict) -> None:
        self.update_status(task_dir, 'running', 40, 'build_opencode_request')
        request = build_opencode_request(task, task_dir)
        request['mode'] = 'plan'
        request['agent'] = 'plan'
        self.update_status(task_dir, 'running', 55, 'run_opencode', opencode_mode=request['mode'])
        result = run_opencode(request)
        normalized_request = result.get('effective_request', request)
        names = OpenCodeResultNormalizer(str(task_dir)).write(normalized_request, result)
        decision = decide_fallback(result)
        if decision['action'] != 'accept':
            self.fail_task(task_dir, decision['reason'])
            return

        artifacts = ArtifactManager(task_dir)
        plan_text = result.get('text', '').strip() or 'No finance learning note returned.'
        artifacts.write_text('finance_note.md', plan_text + '\n')
        candidate = {
            'task_id': task_dir.name,
            'objective': task.get('objective', ''),
            'mode': result.get('mode'),
            'model': result.get('model'),
            'learning_summary': plan_text.splitlines()[0] if plan_text else '',
            'target_files': normalized_request.get('target_files', []),
        }
        artifacts.write_json('finance_learning.json', candidate)
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'finance-learner OpenCode 产物已生成，等待验收')


if __name__ == '__main__':
    worker = FinanceLearnerWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
