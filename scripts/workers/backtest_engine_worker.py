#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
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
SCRIPT_PATH = '/home/admin/.openclaw/workspace/master/scripts/run_smoke_backtest.py'


class BacktestEngineWorker(WorkerBase):
    def __init__(self):
        super().__init__('backtest-engine')

    def _infer_strategy(self, objective: str) -> str:
        if '缩量潜伏' in objective:
            return '缩量潜伏策略'
        return '打板策略'

    def _infer_days(self, objective: str) -> int:
        m = re.search(r'(\d{2,4})\s*(?:days|day|日|天)', objective, flags=re.IGNORECASE)
        if m:
            return max(10, min(240, int(m.group(1))))
        return 20

    def execute_task(self, task_dir: Path, task: dict) -> None:
        artifacts = ArtifactManager(task_dir)
        objective = task.get('objective', '')
        strategy = self._infer_strategy(objective)
        days = self._infer_days(objective)

        cmd = [
            PYTHON_BIN,
            SCRIPT_PATH,
            '--code-root', CODE_ROOT,
            '--cycle-dir', str(task_dir),
            '--stage-id', 'backtest_run',
            '--strategy', strategy,
            '--days', str(days),
        ]

        self.update_status(task_dir, 'running', 45, 'run_native_backtest', strategy=strategy, days=days)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        artifacts.append_log('run.log', f"command={' '.join(cmd)}")
        if proc.stdout:
            artifacts.append_log('run.log', proc.stdout[-12000:])
        if proc.stderr:
            artifacts.append_log('run.log', proc.stderr[-12000:])

        if proc.returncode != 0:
            self.fail_task(task_dir, f'backtest command failed: {proc.returncode}')
            return

        result_path = task_dir / 'artifacts' / 'backtest_run' / 'smoke_backtest.json'
        report_path = task_dir / 'artifacts' / 'backtest_run' / 'smoke_backtest_report.md'
        if not result_path.exists() or not report_path.exists():
            self.fail_task(task_dir, 'backtest artifacts missing after execution')
            return

        payload = json.loads(result_path.read_text(encoding='utf-8'))
        artifacts.write_json('backtest_metrics.json', payload)
        artifacts.write_text('backtest_report.md', report_path.read_text(encoding='utf-8', errors='ignore'))
        summary = (
            f"strategy={payload.get('strategy_type')} days={payload.get('days')} total_return={payload.get('metrics', {}).get('total_return')} "
            f"max_drawdown={payload.get('metrics', {}).get('max_drawdown')} sharpe={payload.get('metrics', {}).get('sharpe_ratio')}"
        )
        artifacts.write_text('result_summary.md', summary + '\n')
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'backtest-engine 原生回测产物已生成，等待验收')


if __name__ == '__main__':
    worker = BacktestEngineWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
