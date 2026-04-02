#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from worker_base import WorkerBase  # noqa: E402
from artifact_manager import ArtifactManager  # noqa: E402
from ecosystem_stage_card import build_stage_card, write_stage_card_markdown  # noqa: E402
from heartbeat_monitor import dashboard, scan_jobs, write_dashboard_markdown  # noqa: E402
from recovery_runtime import jobs_recovery_dashboard, write_recovery_markdown  # noqa: E402
from task_lifecycle import lifecycle_dashboard, write_lifecycle_markdown  # noqa: E402

WORKSPACE = '/home/admin/.openclaw/workspace/master'
WORKFLOW_STATUS_SH = '/home/admin/.openclaw/workspace/master/scripts/check_workflow_status.sh'
JOBS_ROOT = '/home/admin/.openclaw/workspace/master/traces/jobs'


class OpsMonitorWorker(WorkerBase):
    def __init__(self):
        super().__init__('ops-monitor')

    def _run(self, cmd: list[str], artifacts: ArtifactManager, label: str, cwd: str = WORKSPACE, timeout: int = 120) -> subprocess.CompletedProcess:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        artifacts.append_log('run.log', f"[{label}] command={' '.join(cmd)}")
        if proc.stdout:
            artifacts.append_log('run.log', proc.stdout[-12000:])
        if proc.stderr:
            artifacts.append_log('run.log', proc.stderr[-12000:])
        return proc

    def execute_task(self, task_dir: Path, task: dict) -> None:
        artifacts = ArtifactManager(task_dir)
        self.update_status(task_dir, 'running', 30, 'openclaw_status')
        status_proc = self._run(['openclaw', 'status'], artifacts, 'openclaw_status')
        if status_proc.returncode != 0:
            self.fail_task(task_dir, f'openclaw status failed: {status_proc.returncode}')
            return

        self.update_status(task_dir, 'running', 45, 'workflow_status')
        workflow_proc = self._run(['bash', WORKFLOW_STATUS_SH], artifacts, 'workflow_status', timeout=180)

        self.update_status(task_dir, 'running', 60, 'system_snapshot')
        sys_proc = self._run(['bash', '-lc', 'uptime && echo --- && df -h / && echo --- && free -m | sed -n "1,3p"'], artifacts, 'system_snapshot')

        self.update_status(task_dir, 'running', 75, 'health_dashboard')
        health_payload = dashboard(JOBS_ROOT, max_age_minutes=30)
        recovery_payload = jobs_recovery_dashboard(JOBS_ROOT)
        lifecycle_payload = lifecycle_dashboard(JOBS_ROOT)
        stage_card = build_stage_card(latest_cycle={}, health=health_payload, recovery=recovery_payload, lifecycle=lifecycle_payload)
        stale_items = [item for item in scan_jobs(JOBS_ROOT, max_age_minutes=30) if item['stale']]
        dashboard_path = task_dir / 'artifacts' / 'health_dashboard.md'
        recovery_path = task_dir / 'artifacts' / 'recovery_dashboard.md'
        lifecycle_path = task_dir / 'artifacts' / 'lifecycle_dashboard.md'
        stage_card_path = task_dir / 'artifacts' / 'ecosystem_stage_card.md'
        write_dashboard_markdown(health_payload, dashboard_path)
        write_recovery_markdown(recovery_payload, recovery_path)
        write_lifecycle_markdown(lifecycle_payload, lifecycle_path)
        stage_card_path.write_text(write_stage_card_markdown(stage_card), encoding='utf-8')
        artifacts.write_json('health_dashboard.json', health_payload)
        artifacts.write_json('recovery_dashboard.json', recovery_payload)
        artifacts.write_json('lifecycle_dashboard.json', lifecycle_payload)
        artifacts.write_json('ecosystem_stage_card.json', stage_card)
        artifacts.write_json('stale_scan.json', {'stale_count': len(stale_items), 'items': stale_items})
        artifacts.write_json('governance_actions.json', health_payload.get('governance', {}))

        status_text = status_proc.stdout.strip()
        workflow_text = workflow_proc.stdout.strip()
        system_text = sys_proc.stdout.strip()
        gov = health_payload.get('governance', {})

        report_lines = [
            '# Ops Monitor Report',
            '## OpenClaw Status',
            status_text or '(empty)',
            '',
            '## Workflow Status',
            workflow_text or '(empty)',
            '',
            '## System Snapshot',
            system_text or '(empty)',
            '',
            '## Health Summary',
            f"job_count={health_payload.get('job_count')} stale_count={health_payload.get('stale_count')}",
            f"recoverability_counts={health_payload.get('recoverability_counts')}",
            f"quality_grade_counts={health_payload.get('quality_grade_counts')}",
            f"quality_average_score={health_payload.get('quality_average_score')}",
            f"formalization_state_counts={health_payload.get('formalization_state_counts')}",
            f"closure_counts={health_payload.get('closure_counts')}",
            f"lifecycle_bucket_counts={lifecycle_payload.get('bucket_counts')}",
            f"stage_label={stage_card.get('stage_label')}",
            '',
            '## Governance Recommendations',
        ]
        for action in gov.get('actions', []):
            report_lines.append(
                f"- {action['task_id']} | action={action['recommended_action']} | rationale={action['rationale']} | reason={action['reason']}"
            )
        if not gov.get('actions'):
            report_lines.append('- no governance actions needed')
        artifacts.write_text('ops_report.md', '\n'.join(report_lines) + '\n')

        summary = {
            'openclaw_status_returncode': status_proc.returncode,
            'workflow_status_returncode': workflow_proc.returncode,
            'system_snapshot_returncode': sys_proc.returncode,
            'openclaw_status_chars': len(status_text),
            'workflow_status_chars': len(workflow_text),
            'system_snapshot_chars': len(system_text),
            'workflow_ok': workflow_proc.returncode == 0,
            'job_count': health_payload.get('job_count'),
            'stale_count': health_payload.get('stale_count'),
            'governance_action_count': gov.get('action_count', 0),
            'recoverability_counts': recovery_payload.get('recoverability_counts', {}),
            'quality_grade_counts': health_payload.get('quality_grade_counts', {}),
            'quality_average_score': health_payload.get('quality_average_score'),
            'formalization_state_counts': health_payload.get('formalization_state_counts', {}),
            'closure_counts': health_payload.get('closure_counts', {}),
            'lifecycle_bucket_counts': lifecycle_payload.get('bucket_counts', {}),
            'stage_id': stage_card.get('stage_id'),
            'stage_label': stage_card.get('stage_label'),
            'maturity_band': stage_card.get('maturity_band'),
            'phase_completion_state': stage_card.get('phase_completion_state'),
            'next_action_title': (stage_card.get('next_action_card') or {}).get('title'),
        }
        artifacts.write_json('ops_summary.json', summary)
        artifacts.write_text(
            'result_summary.md',
            f"openclaw_status_rc={status_proc.returncode} workflow_status_rc={workflow_proc.returncode} system_snapshot_rc={sys_proc.returncode} workflow_ok={summary['workflow_ok']} stale_count={summary['stale_count']} governance_action_count={summary['governance_action_count']}\n",
        )
        names = artifacts.list_artifacts()
        self.update_status(task_dir, 'artifact_ready', 70, 'artifacts_ready', artifacts=names)
        self.handoff_task(task_dir, 'test-expert', names, 'ops-monitor 原生诊断产物已生成，等待验收')


if __name__ == '__main__':
    worker = OpsMonitorWorker()
    task_dir = worker.run_once(sys.argv[1] if len(sys.argv) > 1 else None)
    print(task_dir or 'NO_TASK')
