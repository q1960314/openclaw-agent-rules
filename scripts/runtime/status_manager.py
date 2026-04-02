#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 status manager with guarded transitions."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class StatusManager:
    TERMINAL = {'failed', 'rejected', 'manual_review_required'}
    ALLOWED = {
        'queued': {'queued', 'claimed', 'running', 'failed', 'rejected', 'manual_review_required'},
        'claimed': {'claimed', 'running', 'failed', 'rejected', 'manual_review_required'},
        'running': {'running', 'artifact_ready', 'under_review', 'passed', 'failed', 'rejected', 'manual_review_required'},
        'artifact_ready': {'artifact_ready', 'under_review', 'passed', 'failed', 'rejected', 'manual_review_required'},
        'under_review': {'under_review', 'passed', 'failed', 'rejected', 'manual_review_required'},
        'passed': {'passed'},
        'failed': {'failed'},
        'rejected': {'rejected'},
        'manual_review_required': {'manual_review_required'},
    }

    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.task_dir / 'status.json'

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def load(self) -> dict[str, Any]:
        if self.status_file.exists():
            return json.loads(self.status_file.read_text(encoding='utf-8'))
        return {
            'task_id': self.task_dir.name,
            'status': 'queued',
            'progress': 0,
            'current_stage': 'queued',
            'updated_at': self._now(),
        }

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.status_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return payload

    def _validate_transition(self, current_status: str, new_status: str, allow_reopen: bool = False) -> None:
        if current_status in self.TERMINAL and new_status != current_status and not allow_reopen:
            raise ValueError(f'illegal status transition from {current_status} to {new_status}')
        allowed = self.ALLOWED.get(current_status, {current_status})
        if new_status not in allowed and not allow_reopen:
            raise ValueError(f'illegal status transition from {current_status} to {new_status}')

    def set(self, status: str, progress: int, current_stage: str, allow_reopen: bool = False, **extra: Any) -> dict[str, Any]:
        payload = self.load()
        self._validate_transition(payload.get('status', 'queued'), status, allow_reopen=allow_reopen)
        payload.update({
            'task_id': payload.get('task_id', self.task_dir.name),
            'status': status,
            'progress': max(0, min(100, int(progress))),
            'current_stage': current_stage,
            'updated_at': self._now(),
        })
        payload.update(extra)
        return self.write(payload)

    def set_claimed(self, claimed_by: str, allow_reopen: bool = False) -> dict[str, Any]:
        return self.set('claimed', 5, 'claimed', claimed_by=claimed_by, allow_reopen=allow_reopen)

    def set_running(self, stage: str = 'running', progress: int = 30, **extra: Any) -> dict[str, Any]:
        return self.set('running', progress, stage, **extra)

    def set_artifact_ready(self, artifacts: list[str] | None = None) -> dict[str, Any]:
        return self.set('artifact_ready', 70, 'artifact_ready', artifacts=artifacts or [])

    def set_under_review(self, reviewer: str | None = None) -> dict[str, Any]:
        return self.set('under_review', 80, 'under_review', reviewer=reviewer)

    def set_passed(self, **extra: Any) -> dict[str, Any]:
        return self.set('passed', 100, 'passed', **extra)

    def set_manual_review_required(self, reason: str = 'manual review required', **extra: Any) -> dict[str, Any]:
        return self.set('manual_review_required', 90, 'manual_review_required', review_reason=reason, allow_reopen=True, **extra)

    def set_failed(self, reason: str, **extra: Any) -> dict[str, Any]:
        return self.set('failed', 100, 'failed', blocked_reason=reason, allow_reopen=True, **extra)

    def set_rejected(self, reason: str, **extra: Any) -> dict[str, Any]:
        return self.set('rejected', 100, 'rejected', blocked_reason=reason, allow_reopen=True, **extra)

    def reset_for_retry(self, retried_by: str, retry_reason: str) -> dict[str, Any]:
        return self.set('queued', 0, 'queued', allow_reopen=True, retried_by=retried_by, retry_reason=retry_reason)
