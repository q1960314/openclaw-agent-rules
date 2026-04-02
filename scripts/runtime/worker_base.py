#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared P1 worker base with stage authorization, handoff validation, audit logging, heartbeat, and result envelopes."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from artifact_manager import ArtifactManager
from audit_manager import AuditManager
from heartbeat_monitor import HeartbeatMonitor
from review_manager import ReviewManager
from status_manager import StatusManager
from task_queue import TaskQueue


ALLOWED_HANDOFFS = {
    'master-quant': {
        'coder', 'strategy-expert', 'parameter-evolver', 'backtest-engine',
        'data-collector', 'factor-miner', 'sentiment-analyst', 'finance-learner', 'ops-monitor'
    },
    'coder': {'test-expert'},
    'strategy-expert': {'test-expert'},
    'parameter-evolver': {'test-expert'},
    'factor-miner': {'test-expert'},
    'sentiment-analyst': {'test-expert'},
    'finance-learner': {'test-expert'},
    'backtest-engine': {'test-expert'},
    'data-collector': {'test-expert'},
    'ops-monitor': {'test-expert'},
    'test-expert': {'doc-manager'},
    'doc-manager': {'knowledge-steward'},
    'knowledge-steward': set(),
}


class WorkerBase:
    def __init__(self, role: str, jobs_root: str | Path | None = None):
        self.role = role
        self.queue = TaskQueue(jobs_root or Path(__file__).resolve().parents[2] / 'traces' / 'jobs')

    def audit(self, task_dir: str | Path) -> AuditManager:
        return AuditManager(task_dir)

    def heartbeat(self, task_dir: str | Path, stage: str, status: str | None = None) -> dict:
        return HeartbeatMonitor(task_dir).touch(self.role, stage, status=status)

    def _refresh_lease_if_owned(self, task_dir: str | Path) -> None:
        task_dir = Path(task_dir)
        claim_path = task_dir / 'claim.json'
        if not claim_path.exists():
            return
        try:
            claim = json.loads(claim_path.read_text(encoding='utf-8'))
        except Exception:
            return
        if claim.get('claimed_by') != self.role:
            return
        if claim.get('status') != 'claimed':
            return
        try:
            self.queue.refresh_lease(task_dir, self.role)
        except Exception:
            return

    def _result_boundary(self, task_dir: str | Path) -> dict:
        task = self.load_task(task_dir)
        review = self.load_review(task_dir)
        metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
        manual_review_required = bool(metadata.get('manual_review_required', False)) or review.get('decision') == 'manual_review_required'
        approval_state = 'manual_review_required' if manual_review_required else 'technically_validated_candidate'
        return {
            'result_tier': 'candidate',
            'approval_state': approval_state,
            'formalization_required': True,
            'manual_review_required': manual_review_required,
            'review_decision': review.get('decision'),
        }

    def _write_result_envelope(self, task_dir: str | Path, to_role: str, status: str, summary: str, artifacts: list[str]) -> Path:
        manager = ArtifactManager(task_dir)
        boundary = self._result_boundary(task_dir)
        payload = {
            'task_id': Path(task_dir).name,
            'from_role': self.role,
            'to_role': to_role,
            'status': status,
            'summary': summary,
            'artifacts': artifacts,
            'generated_at': datetime.now().astimezone().isoformat(),
            **boundary,
        }
        return manager.write_json('result_envelope.json', payload)

    def load_task(self, task_dir: str | Path) -> dict:
        task_dir = Path(task_dir)
        for name in ('task.json', 'spec.json'):
            f = task_dir / name
            if f.exists():
                return json.loads(f.read_text(encoding='utf-8'))
        raise FileNotFoundError(f'No task.json/spec.json found under {task_dir}')

    def load_handoff(self, task_dir: str | Path) -> dict:
        path = Path(task_dir) / 'handoff.json'
        if path.exists():
            txt = path.read_text(encoding='utf-8').strip()
            if txt:
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        return {}

    def load_review(self, task_dir: str | Path) -> dict:
        path = Path(task_dir) / 'review.json'
        if path.exists():
            txt = path.read_text(encoding='utf-8').strip()
            if txt:
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        return {}

    def current_status(self, task_dir: str | Path) -> dict:
        return StatusManager(task_dir).load()

    def claim_task(self, task_id: Optional[str] = None) -> Optional[Path]:
        task_dir = self.queue.claim_task(self.role, task_id)
        if task_dir:
            self.heartbeat(task_dir, 'claimed', status='claimed')
        return task_dir

    def update_status(self, task_dir: str | Path, status: str, progress: int, current_stage: str, **extra) -> dict:
        self._refresh_lease_if_owned(task_dir)
        payload = StatusManager(task_dir).set(status, progress, current_stage, **extra)
        self.audit(task_dir).append('status', self.role, status=status, progress=progress, current_stage=current_stage, extra=extra)
        self.heartbeat(task_dir, current_stage, status=status)
        return payload

    def write_artifact(self, task_dir: str | Path, name: str, content, as_json: bool = False) -> Path:
        self._refresh_lease_if_owned(task_dir)
        manager = ArtifactManager(task_dir)
        if as_json:
            path = manager.write_json(name, content)
        else:
            path = manager.write_text(name, content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2))
        self.audit(task_dir).append('artifact', self.role, path=str(path.relative_to(Path(task_dir))))
        self.heartbeat(task_dir, f'artifact:{name}', status=self.current_status(task_dir).get('status'))
        return path

    def validate_handoff(self, task_dir: str | Path, to_role: str) -> tuple[bool, str]:
        allowed_targets = ALLOWED_HANDOFFS.get(self.role, set())
        if to_role not in allowed_targets:
            return False, f'illegal handoff: {self.role} -> {to_role}'
        review = self.load_review(task_dir)
        if self.role in {'test-expert', 'doc-manager'} and review.get('decision') != 'passed':
            return False, f'{self.role} cannot handoff because review decision is not passed'
        return True, 'ok'

    def handoff_task(self, task_dir: str | Path, to_role: str, artifacts: list[str], summary: str) -> dict:
        ok, reason = self.validate_handoff(task_dir, to_role)
        if not ok:
            raise ValueError(reason)
        self._write_result_envelope(task_dir, to_role=to_role, status=self.current_status(task_dir).get('status', 'unknown'), summary=summary, artifacts=artifacts)
        task_dir = Path(task_dir)
        payload = {
            'task_id': task_dir.name,
            'from': self.role,
            'to': to_role,
            'artifacts': artifacts,
            'summary': summary,
            **self._result_boundary(task_dir),
        }
        (task_dir / 'handoff.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        self.audit(task_dir).append('handoff', self.role, to=to_role, artifacts=artifacts, summary=summary)
        self.heartbeat(task_dir, f'handoff:{to_role}', status=self.current_status(task_dir).get('status'))
        return payload

    def fail_task(self, task_dir: str | Path, reason: str) -> dict:
        payload = StatusManager(task_dir).set_failed(reason, failed_by=self.role)
        self.audit(task_dir).append('failed', self.role, reason=reason)
        self.heartbeat(task_dir, 'failed', status='failed')
        return payload

    def complete_task(self, task_dir: str | Path, passed: bool = True, **extra) -> dict:
        if passed:
            payload = StatusManager(task_dir).set_passed(completed_by=self.role, **extra)
            self.audit(task_dir).append('completed', self.role, passed=True, extra=extra)
            self.heartbeat(task_dir, 'passed', status='passed')
            return payload
        payload = StatusManager(task_dir).set_failed(extra.get('reason', 'worker failed'), completed_by=self.role)
        self.audit(task_dir).append('completed', self.role, passed=False, extra=extra)
        self.heartbeat(task_dir, 'failed', status='failed')
        return payload

    def review(self, task_dir: str | Path, decision: str, issues: list[str] | None = None, evidence: list[str] | None = None, **extra) -> dict:
        payload = ReviewManager(task_dir).write(self.role, decision, issues or [], evidence or [], **extra)
        self.audit(task_dir).append('review', self.role, decision=decision, issues=issues or [], evidence=evidence or [], extra=extra)
        self.heartbeat(task_dir, f'review:{decision}', status=self.current_status(task_dir).get('status'))
        return payload

    def can_execute(self, task_dir: str | Path, task: dict) -> tuple[bool, str]:
        task_dir = Path(task_dir)
        task_role = task.get('role') or task.get('owner_role')
        handoff = self.load_handoff(task_dir)
        review = self.load_review(task_dir)

        authorized = False
        if task_role == self.role:
            authorized = True
        elif handoff.get('to') == self.role:
            authorized = True

        if not authorized:
            return False, f'unauthorized execution: worker={self.role} task_role={task_role} handoff_to={handoff.get("to")}'

        if self.role in {'doc-manager', 'knowledge-steward'} and review.get('decision') != 'passed':
            return False, f'{self.role} blocked: review decision is not passed'

        return True, 'ok'

    def execute_task(self, task_dir: Path, task: dict) -> None:
        raise NotImplementedError

    def run_once(self, task_id: Optional[str] = None) -> Optional[Path]:
        task_dir = self.claim_task(task_id)
        if not task_dir:
            return None
        task = self.load_task(task_dir)
        allowed, reason = self.can_execute(task_dir, task)
        if not allowed:
            self.fail_task(task_dir, reason)
            return task_dir
        self.update_status(task_dir, 'running', 25, 'execute_task')
        try:
            self.execute_task(task_dir, task)
        except Exception as exc:
            self.fail_task(task_dir, str(exc))
            raise
        return task_dir
