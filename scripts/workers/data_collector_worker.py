#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from worker_base import WorkerBase  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402

PYTHON_BIN = '/home/admin/miniconda3/envs/vnpy_env/bin/python'
CODE_ROOT = '/data/agents/master'
SNAPSHOT_SCRIPT = '/home/admin/.openclaw/workspace/master/scripts/workflow_data_snapshot.py'
CHECK_SCRIPT = '/home/admin/.openclaw/workspace/master/scripts/workflow_data_check.py'
SCORE_SCRIPT = '/home/admin/.openclaw/workspace/master/scripts/workflow_data_quality_score.py'


class DataCollectorWorker(WorkerBase):
    def __init__(self):
        super().__init__('data-collector')

    def _run_cmd(self, cmd: list[str], task_dir: Path, artifacts: ArtifactManager, label: str) -> subprocess.CompletedProcess:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        artifacts.append_log('run.log', f"[{label}] command={' '.join(cmd)}")
        if proc.stdout:
            artifacts.append_log('run.log', proc.stdout[-12000:])
        if proc.stderr:
            artifacts.append_log('run.log', proc.stderr[-12000:])
        return proc

    def execute_task(self, task_dir: Path, task: dict) -> None:
        artifacts = ArtifactManager(task_dir)

        self.update_status(task_dir, 'running', 35, 'data_snapshot')
        snapshot_cmd = [
            PYTHON_BIN, SNAPSHOT_SCRIPT,
            '--code-root', CODE_ROOT,
            '--cycle-dir', str(task_dir),
            '--stage-id', 'data_snapshot',
            '--sample-size', '10',
        ]
        proc = self._run_cmd(snapshot_cmd, task_dir, artifacts, 'snapshot')
        if proc.returncode != 0:
            self.fail_task(task_dir, f'data snapshot failed: {proc.returncode}')
            return

        self.update_status(task_dir, 'running', 55, 'data_validate')
        validate_cmd = [
            PYTHON_BIN, CHECK_SCRIPT,
            '--code-root', CODE_ROOT,
            '--cycle-dir', str(task_dir),
            '--stage-id', 'data_validate',
        ]
        proc = self._run_cmd(validate_cmd, task_dir, artifacts, 'validate')
        if proc.returncode not in (0, 1):
            self.fail_task(task_dir, f'data validate failed unexpectedly: {proc.returncode}')
            return

        self.update_status(task_dir, 'running', 70, 'data_quality_score')
        score_cmd = [
            PYTHON_BIN, SCORE_SCRIPT,
            '--cycle-dir', str(task_dir),
            '--stage-id', 'data_quality_score',
        ]
        proc = self._run_cmd(score_cmd, task_dir, artifacts, 'score')
        if proc.returncode != 0:
            self.fail_task(task_dir, f'data quality score failed: {proc.returncode}')
            return

        snapshot_json = task_dir / 'artifacts' / 'data_snapshot' / 'data_snapshot.json'
        validate_json = task_dir / 'artifacts' / 'data_validate' / 'data_check.json'
        score_json = task_dir / 'artifacts' / 'data_quality_score' / 'data_quality_score.json'
        if not snapshot_json.exists() or not validate_json.exists() or not score_json.exists():
            self.fail_task(task_dir, 'data artifacts missing after execution')
            return

        snapshot_payload = json.loads(snapshot_json.read_text(encoding='utf-8'))
        validate_payload = json.loads(validate_json.read_text(encoding='utf-8'))
        score_payload = json.loads(score_json.read_text(encoding='utf-8'))
        artifacts.write_json('data_snapshot.json', snapshot_payload)
        artifacts.write_json('data_check.json', validate_payload)
        artifacts.write_json('data_quality_score.json', score_payload)
        summary = (
            f"stock_dir_count={snapshot_payload.get('stock_dir_count')} sample_size={snapshot_payload.get('sample_size')} "
            f"status={validate_payload.get('summary', {}).get('status')} score={score_payload.get('score')} grade={score_payload.get('grade')}"
        )
        artifacts.write_text('result_summary.md', summary + '\n')
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'data-collector 原生数据检查产物已生成，等待验收')


if __name__ == '__main__':
    worker = DataCollectorWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
