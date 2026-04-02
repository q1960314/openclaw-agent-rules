#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 task queue with canonical task.json, audit, retry helpers, and claim authorization."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from audit_manager import AuditManager
from status_manager import StatusManager

LEASE_MINUTES = 30
OWNER_CLAIM_STATUSES = {'queued'}
HANDOFF_CLAIM_STATUSES = {'artifact_ready', 'under_review', 'passed'}


class TaskQueue:
    def __init__(self, jobs_root: str | Path = Path(__file__).resolve().parents[2] / 'traces' / 'jobs'):
        self.jobs_root = Path(jobs_root)
        self.jobs_root.mkdir(parents=True, exist_ok=True)

    def _now(self) -> datetime:
        return datetime.now().astimezone()

    def _now_iso(self) -> str:
        return self._now().isoformat()

    def _lease_until(self) -> str:
        return (self._now() + timedelta(minutes=LEASE_MINUTES)).isoformat()

    def task_dir(self, task_id: str) -> Path:
        return self.jobs_root / task_id

    def load_task(self, task_id: str) -> Optional[dict]:
        task_dir = self.task_dir(task_id)
        for name in ('task.json', 'spec.json'):
            f = task_dir / name
            if f.exists():
                return json.loads(f.read_text(encoding='utf-8'))
        return None

    def load_handoff(self, task_dir: Path) -> dict:
        path = task_dir / 'handoff.json'
        if path.exists():
            txt = path.read_text(encoding='utf-8').strip()
            if txt:
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        return {}

    def load_claim(self, task_dir: Path) -> dict:
        path = task_dir / 'claim.json'
        if path.exists():
            txt = path.read_text(encoding='utf-8').strip()
            if txt:
                try:
                    return json.loads(txt)
                except Exception:
                    return {}
        return {}

    def write_claim(self, task_dir: Path, claim: dict) -> None:
        (task_dir / 'claim.json').write_text(json.dumps(claim, ensure_ascii=False, indent=2), encoding='utf-8')

    def create_task(self, task: dict) -> Path:
        task_id = task['task_id']
        task_dir = self.task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / 'artifacts').mkdir(exist_ok=True)
        (task_dir / 'logs').mkdir(exist_ok=True)

        canonical = {
            'task_id': task_id,
            'role': task['role'],
            'objective': task['objective'],
            'constraints': task.get('constraints', []),
            'acceptance_criteria': task.get('acceptance_criteria', []),
            'input_artifacts': task.get('input_artifacts', []),
            'upstream': task.get('upstream', ''),
            'downstream': task.get('downstream', ''),
            'engine': task.get('engine', 'native'),
            'priority': task.get('priority', 'medium'),
            'created_at': task.get('created_at', self._now_iso()),
            'metadata': task.get('metadata', {}),
        }
        (task_dir / 'task.json').write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding='utf-8')

        legacy = {
            'task_id': task_id,
            'task_type': canonical['metadata'].get('task_type', canonical['role']),
            'title': canonical['objective'],
            'owner_role': canonical['role'],
            'validator_role': canonical['downstream'],
            'input_refs': canonical['input_artifacts'],
            'required_artifacts': canonical['metadata'].get('required_artifacts', []),
            'success_criteria': canonical['acceptance_criteria'],
            'status': 'queued',
            'created_at': canonical['created_at'],
        }
        (task_dir / 'spec.json').write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding='utf-8')

        self.write_claim(task_dir, {
            'task_id': task_id,
            'claimed_by': None,
            'attempt': 0,
            'status': 'unclaimed',
            'claimed_at': None,
            'lease_until': None,
        })

        StatusManager(task_dir).set('queued', 0, 'queued')
        (task_dir / 'handoff.json').write_text('{}\n', encoding='utf-8')
        (task_dir / 'review.json').write_text('{}\n', encoding='utf-8')
        AuditManager(task_dir).append('task_created', canonical['role'], engine=canonical['engine'], downstream=canonical['downstream'])
        return task_dir

    def create_retry_task(self, source_task_id: str, requested_by: str, reason: str) -> Path:
        source_task = self.load_task(source_task_id)
        if not source_task:
            raise FileNotFoundError(f'source task not found: {source_task_id}')
        source_dir = self.task_dir(source_task_id)
        source_status = StatusManager(source_dir).load().get('status')
        if source_status not in {'failed', 'rejected'}:
            raise ValueError(f'retry only allowed for failed/rejected tasks, got {source_status}')
        metadata = dict(source_task.get('metadata', {}))
        retry_index = int(metadata.get('retry_index', 0)) + 1
        new_task_id = f"{source_task_id}-R{retry_index}"
        new_metadata = dict(metadata)
        new_metadata.update({
            'retry_of': source_task_id,
            'retry_index': retry_index,
            'retry_requested_by': requested_by,
            'retry_reason': reason,
        })
        new_task = dict(source_task)
        new_task['task_id'] = new_task_id
        new_task['created_at'] = self._now_iso()
        new_task['metadata'] = new_metadata
        task_dir = self.create_task(new_task)
        AuditManager(task_dir).append('retry_created', requested_by, source_task_id=source_task_id, reason=reason, retry_index=retry_index)
        return task_dir

    def _claim_allowed(self, role: str, task_dir: Path, task: dict, status: dict, handoff: dict) -> tuple[bool, str]:
        current_status = status.get('status')
        task_role = task.get('role') or task.get('owner_role')
        handoff_to = handoff.get('to')
        if handoff_to:
            if role != handoff_to:
                return False, f'allowed_role={handoff_to}'
            if current_status not in HANDOFF_CLAIM_STATUSES:
                return False, f'status {current_status} not claimable for handoff target'
            return True, 'ok'
        if role != task_role:
            return False, f'allowed_role={task_role}'
        if current_status not in OWNER_CLAIM_STATUSES:
            return False, f'status {current_status} not claimable for owner'
        return True, 'ok'

    def find_claimable_tasks(self, role: Optional[str] = None) -> list[Path]:
        results: list[Path] = []
        for task_dir in sorted(self.jobs_root.iterdir()):
            if not task_dir.is_dir() or task_dir.name.startswith('_'):
                continue
            task = self.load_task(task_dir.name)
            if not task:
                continue
            status = StatusManager(task_dir).load()
            handoff = self.load_handoff(task_dir)
            if role is None:
                if status.get('status') in OWNER_CLAIM_STATUSES.union(HANDOFF_CLAIM_STATUSES):
                    results.append(task_dir)
                continue
            allowed, _ = self._claim_allowed(role, task_dir, task, status, handoff)
            if allowed:
                results.append(task_dir)
        return results

    def claim_task(self, role: str, task_id: Optional[str] = None) -> Optional[Path]:
        task_dir = self.task_dir(task_id) if task_id else next(iter(self.find_claimable_tasks(role)), None)
        if task_dir is None or not task_dir.exists():
            return None
        status = StatusManager(task_dir).load()
        task = self.load_task(task_dir.name) or {}
        handoff = self.load_handoff(task_dir)
        allowed, reason = self._claim_allowed(role, task_dir, task, status, handoff)
        if not allowed:
            AuditManager(task_dir).append('claim_blocked', role, reason=reason)
            return None
        claim = self.load_claim(task_dir)
        claim['task_id'] = task_dir.name
        claim['claimed_by'] = role
        claim['attempt'] = int(claim.get('attempt', 0)) + 1
        claim['status'] = 'claimed'
        claim['claimed_at'] = self._now_iso()
        claim['lease_until'] = self._lease_until()
        self.write_claim(task_dir, claim)
        StatusManager(task_dir).set_claimed(role, allow_reopen=True)
        AuditManager(task_dir).append('claimed', role, attempt=claim['attempt'], lease_until=claim['lease_until'])
        return task_dir

    def refresh_lease(self, task_dir: str | Path, actor: str) -> dict:
        task_dir = Path(task_dir)
        claim = self.load_claim(task_dir)
        if not claim:
            raise FileNotFoundError(f'claim.json missing under {task_dir}')
        if claim.get('claimed_by') != actor:
            raise ValueError(f'lease refresh denied: claimed_by={claim.get("claimed_by")} actor={actor}')
        claim['lease_until'] = self._lease_until()
        self.write_claim(task_dir, claim)
        AuditManager(task_dir).append('lease_refreshed', actor, lease_until=claim['lease_until'])
        return claim

    def release_claim(self, task_dir: str | Path, actor: str, reason: str) -> dict:
        task_dir = Path(task_dir)
        claim = self.load_claim(task_dir)
        if not claim:
            raise FileNotFoundError(f'claim.json missing under {task_dir}')
        claim['status'] = 'released'
        claim['lease_until'] = None
        claim['released_by'] = actor
        claim['release_reason'] = reason
        self.write_claim(task_dir, claim)
        AuditManager(task_dir).append('claim_released', actor, reason=reason)
        return claim
