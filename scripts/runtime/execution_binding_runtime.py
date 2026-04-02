#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from artifact_manager import ArtifactManager
from release_closure_runtime import _load_json


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _new_id(prefix: str, task_id: str) -> str:
    return f"{prefix}-{task_id}-{uuid4().hex[:10]}"


def ensure_execution_batch(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    existing = _load_json(task_dir / 'artifacts' / 'execution_batch.json')
    if existing.get('batch_id') and existing.get('release_run_id') and existing.get('rollback_run_id'):
        return existing
    payload = {
        'task_id': task_dir.name,
        'record_type': 'execution_batch',
        'batch_id': existing.get('batch_id') or _new_id('batch', task_dir.name),
        'release_run_id': existing.get('release_run_id') or _new_id('run-release', task_dir.name),
        'rollback_run_id': existing.get('rollback_run_id') or _new_id('run-rollback', task_dir.name),
        'generated_at': existing.get('generated_at') or _now(),
        'updated_at': _now(),
        'note': 'Execution batch binds release/rollback manual execution planning, confirmation, registration, protocol, and observation into one auditable batch without enabling automatic execution.',
    }
    manager.write_json('execution_batch.json', payload)
    return payload


def get_execution_run_context(task_dir: str | Path, target: str) -> dict[str, Any]:
    batch = ensure_execution_batch(task_dir)
    run_id = batch['release_run_id'] if target == 'release' else batch['rollback_run_id']
    return {
        'batch_id': batch['batch_id'],
        'run_id': run_id,
        'release_run_id': batch['release_run_id'],
        'rollback_run_id': batch['rollback_run_id'],
    }


def extract_run_context_from_plan(plan: dict[str, Any], target: str) -> dict[str, Any]:
    run_id = plan.get(f'{target}_run_id') or plan.get('run_id')
    return {
        'batch_id': plan.get('batch_id'),
        'run_id': run_id,
        'release_run_id': plan.get('release_run_id'),
        'rollback_run_id': plan.get('rollback_run_id'),
    }


def validate_run_context(*, expected: dict[str, Any], candidate: dict[str, Any], label: str) -> None:
    if not candidate:
        return
    expected_batch = expected.get('batch_id')
    expected_run = expected.get('run_id')
    candidate_batch = candidate.get('batch_id')
    candidate_run = candidate.get('run_id')
    if expected_batch and candidate_batch and expected_batch != candidate_batch:
        raise ValueError(f'{label} batch_id mismatch: expected {expected_batch}, got {candidate_batch}')
    if expected_run and candidate_run and expected_run != candidate_run:
        raise ValueError(f'{label} run_id mismatch: expected {expected_run}, got {candidate_run}')


def collect_run_refs(*, task_dir: str | Path, target: str) -> dict[str, Any]:
    task_dir = Path(task_dir)
    artifacts_dir = task_dir / 'artifacts'
    plan = _load_json(artifacts_dir / 'official_release_execution_plan.json')
    status_name = 'official_release_execution_status.json' if target == 'release' else 'rollback_execution_status.json'
    record_name = 'official_release_execution_confirmation_record.json' if target == 'release' else 'rollback_execution_confirmation_record.json'
    registration_name = 'official_release_record.json' if target == 'release' else 'rollback_registration_record.json'
    protocol_name = 'official_release_execution_protocol.json' if target == 'release' else 'rollback_execution_protocol.json'
    observation = _load_json(artifacts_dir / 'post_execution_observation.json')
    return {
        'plan': extract_run_context_from_plan(plan, target),
        'status': {
            'batch_id': _load_json(artifacts_dir / status_name).get('batch_id'),
            'run_id': _load_json(artifacts_dir / status_name).get('run_id'),
        },
        'confirmation': {
            'batch_id': _load_json(artifacts_dir / record_name).get('batch_id'),
            'run_id': _load_json(artifacts_dir / record_name).get('run_id'),
        },
        'registration': {
            'batch_id': _load_json(artifacts_dir / registration_name).get('batch_id'),
            'run_id': _load_json(artifacts_dir / registration_name).get('run_id'),
        },
        'protocol': {
            'batch_id': _load_json(artifacts_dir / protocol_name).get('batch_id'),
            'run_id': _load_json(artifacts_dir / protocol_name).get('run_id'),
        },
        'observation': {
            'batch_id': observation.get('batch_id'),
            'run_id': observation.get('run_id'),
            'execution_target': observation.get('execution_target'),
            'observation_state': observation.get('observation_state'),
        },
    }
