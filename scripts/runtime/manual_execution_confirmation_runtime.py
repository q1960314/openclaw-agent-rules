#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from artifact_manager import ArtifactManager
from execution_binding_runtime import extract_run_context_from_plan, validate_run_context
from execution_protocol_runtime import sync_all_execution_protocols
from release_closure_runtime import _load_json, load_release_closure_snapshot

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'

TARGET_CONFIG = {
    'release': {
        'label': 'official_release',
        'precheck_artifact': 'official_release_execution_precheck.json',
        'status_artifact': 'official_release_execution_status.json',
        'record_artifact': 'official_release_execution_confirmation_record.json',
    },
    'rollback': {
        'label': 'rollback',
        'precheck_artifact': 'rollback_execution_precheck.json',
        'status_artifact': 'rollback_execution_status.json',
        'record_artifact': 'rollback_execution_confirmation_record.json',
    },
}


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _resolve_task_dir(*, task_dir: str | Path | None = None, task_id: str | None = None, jobs_root: str | Path = JOBS_ROOT) -> Path:
    if task_dir:
        resolved = Path(task_dir)
        if not resolved.exists():
            raise FileNotFoundError(f'task_dir not found: {resolved}')
        return resolved
    if task_id:
        resolved = Path(jobs_root) / task_id
        if not resolved.exists():
            raise FileNotFoundError(f'task_id not found under jobs_root: {resolved}')
        return resolved
    raise ValueError('task_dir or task_id is required')


def _load_target_artifacts(task_dir: Path, target: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = TARGET_CONFIG[target]
    artifacts_dir = task_dir / 'artifacts'
    plan = _load_json(artifacts_dir / 'official_release_execution_plan.json')
    precheck = _load_json(artifacts_dir / config['precheck_artifact'])
    status = _load_json(artifacts_dir / config['status_artifact'])
    if not plan:
        raise FileNotFoundError('missing required artifact: official_release_execution_plan.json')
    if not precheck:
        raise FileNotFoundError(f"missing required artifact: {config['precheck_artifact']}")
    return plan, precheck, status


def _validate_target_transition(*, target: str, action: str, closure_snapshot: dict[str, Any], precheck: dict[str, Any], status: dict[str, Any], task_dir: Path, run_context: dict[str, Any]) -> None:
    if closure_snapshot.get('human_approval_state') != 'approved':
        raise ValueError(f'{target} execution confirmation requires an approved human decision')
    if not precheck.get('precheck_ready'):
        raise ValueError(f'{target} execution confirmation requires {TARGET_CONFIG[target]["precheck_artifact"]} to be ready')
    validate_run_context(expected=run_context, candidate={'batch_id': precheck.get('batch_id'), 'run_id': precheck.get('run_id')}, label=f'{target} precheck')
    validate_run_context(expected=run_context, candidate={'batch_id': status.get('batch_id'), 'run_id': status.get('run_id')}, label=f'{target} status')

    if target == 'release':
        if closure_snapshot.get('official_release_registered'):
            raise ValueError('official release already registered; execution confirmation can no longer advance')
        if closure_snapshot.get('rollback_registered'):
            raise ValueError('rollback already registered; release execution confirmation is closed')
    else:
        if not (task_dir / 'artifacts' / 'official_release_record.json').exists() and action != 'start':
            # start is allowed pre-registration preparation only after release exists? Keep strict to prior release existence for all rollback actions.
            raise ValueError('rollback execution confirmation requires a prior official_release_record.json')
        if not (task_dir / 'artifacts' / 'official_release_record.json').exists():
            raise ValueError('rollback execution confirmation requires a prior official_release_record.json')
        if closure_snapshot.get('rollback_registered'):
            raise ValueError('rollback already registered; rollback execution confirmation can no longer advance')

    current_state = status.get('confirmation_state')
    if action == 'start':
        if current_state == 'in_progress':
            raise ValueError(f'{target} execution already confirmed in progress')
        if current_state == 'completed':
            raise ValueError(f'{target} execution already confirmed completed')
    elif action == 'complete':
        if current_state != 'in_progress':
            raise ValueError(f'{target} execution completion requires a prior start confirmation')
    elif action in {'fail', 'abort'}:
        if current_state != 'in_progress':
            raise ValueError(f'{target} execution {action} requires a prior start confirmation')
    else:
        raise ValueError(f'unsupported action: {action}')


def _build_record(*, task_id: str, target: str, action: str, confirmed_by: str, note: str, status_before: dict[str, Any], precheck: dict[str, Any], closure_snapshot: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    state_after = {'start': 'in_progress', 'complete': 'completed', 'fail': 'failed', 'abort': 'aborted'}[action]
    return {
        'task_id': task_id,
        'record_type': 'manual_execution_confirmation',
        'execution_target': TARGET_CONFIG[target]['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'action': action,
        'confirmation_state': state_after,
        'confirmed_by': confirmed_by,
        'confirmed_at': _now(),
        'note': note,
        'status_before': status_before.get('confirmation_state'),
        'human_approval_state': closure_snapshot.get('human_approval_state'),
        'precheck_state': precheck.get('precheck_state'),
        'precheck_ready': precheck.get('precheck_ready'),
    }


def _build_status(*, task_id: str, target: str, action: str, confirmed_by: str, note: str, existing: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    status = dict(existing) if existing else {
        'task_id': task_id,
        'status_type': 'manual_execution_status',
        'execution_target': TARGET_CONFIG[target]['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'confirmation_state': 'planned_not_started',
        'execution_started': False,
        'execution_completed': False,
        'execution_failed': False,
        'execution_aborted': False,
    }
    status.update({
        'task_id': task_id,
        'status_type': 'manual_execution_status',
        'execution_target': TARGET_CONFIG[target]['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'updated_at': _now(),
        'latest_action': action,
        'latest_actor': confirmed_by,
        'latest_note': note,
    })

    if action == 'start':
        status.update({
            'confirmation_state': 'in_progress',
            'execution_started': True,
            'execution_completed': False,
            'execution_failed': False,
            'execution_aborted': False,
            'start_confirmed_at': _now(),
            'start_confirmed_by': confirmed_by,
            'next_step': f'wait_for_manual_{target}_completion_or_failure_confirmation',
        })
    elif action == 'complete':
        status.update({
            'confirmation_state': 'completed',
            'execution_started': True,
            'execution_completed': True,
            'execution_failed': False,
            'execution_aborted': False,
            'completion_confirmed_at': _now(),
            'completion_confirmed_by': confirmed_by,
            'next_step': 'record_manual_release_registration' if target == 'release' else 'record_manual_rollback_registration',
        })
    elif action == 'fail':
        status.update({
            'confirmation_state': 'failed',
            'execution_started': True,
            'execution_completed': False,
            'execution_failed': True,
            'execution_aborted': False,
            'failure_confirmed_at': _now(),
            'failure_confirmed_by': confirmed_by,
            'failure_reason': note,
            'next_step': f'keep_{target}_path_blocked_and_require_manual_recovery',
        })
    elif action == 'abort':
        status.update({
            'confirmation_state': 'aborted',
            'execution_started': True,
            'execution_completed': False,
            'execution_failed': False,
            'execution_aborted': True,
            'abort_confirmed_at': _now(),
            'abort_confirmed_by': confirmed_by,
            'abort_reason': note,
            'next_step': f'keep_{target}_path_blocked_until_manual_restart_or_rework',
        })
    return status


def _build_release_state(*, task_id: str, target: str, action: str, existing_state: dict[str, Any], status: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    payload = dict(existing_state) if existing_state else {'task_id': task_id, 'official_release': False}
    mapping = {
        'release': {
            'start': ('manual_release_execution_in_progress', 'wait_for_manual_release_completion_or_failure_confirmation'),
            'complete': ('manual_release_execution_completed_pending_registration', 'record_manual_release_registration'),
            'fail': ('manual_release_execution_failed', 'keep_release_closed_until_manual_recovery'),
            'abort': ('manual_release_execution_aborted', 'keep_release_closed_until_manual_restart_or_rework'),
        },
        'rollback': {
            'start': ('manual_rollback_execution_in_progress', 'wait_for_manual_rollback_completion_or_failure_confirmation'),
            'complete': ('manual_rollback_execution_completed_pending_registration', 'record_manual_rollback_registration'),
            'fail': ('manual_rollback_execution_failed', 'keep_rollback_closed_until_manual_recovery'),
            'abort': ('manual_rollback_execution_aborted', 'keep_rollback_closed_until_manual_restart_or_rework'),
        },
    }
    state, next_step = mapping[target][action]
    payload.update({
        'task_id': task_id,
        'official_release_state': state,
        'official_release': False,
        'execution_confirmation_target': TARGET_CONFIG[target]['label'],
        'execution_confirmation_state': status.get('confirmation_state'),
        'execution_confirmation_updated_at': status.get('updated_at'),
        'current_execution_batch_id': run_context['batch_id'],
        'current_execution_run_id': run_context['run_id'],
        'next_step': next_step,
        'note': 'Manual execution confirmation updates state visibility only. It does not execute release or rollback automatically.',
    })
    return payload


def _build_pipeline_summary(*, task_id: str, target: str, action: str, existing_summary: dict[str, Any], closure_snapshot: dict[str, Any], status: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    ready_signals = dict(existing_summary.get('ready_signals', {}) or {})
    ready_signals.update({
        'human_decision_recorded': bool(closure_snapshot.get('human_approval_result_recorded')),
        'human_approved': closure_snapshot.get('human_approval_state') == 'approved',
        'manual_execution_target': TARGET_CONFIG[target]['label'],
        'manual_execution_started': bool(status.get('execution_started')),
        'manual_execution_completed': bool(status.get('execution_completed')),
        'manual_execution_failed': bool(status.get('execution_failed')),
        'manual_execution_aborted': bool(status.get('execution_aborted')),
        'manual_execution_confirmation_state': status.get('confirmation_state'),
    })
    state_map = {
        'release': {
            'start': ('manual_release_execution_in_progress', 'wait_for_manual_release_completion_or_failure_confirmation'),
            'complete': ('manual_release_execution_completed_pending_registration', 'record_manual_release_registration'),
            'fail': ('manual_release_execution_failed', 'keep_release_closed_until_manual_recovery'),
            'abort': ('manual_release_execution_aborted', 'keep_release_closed_until_manual_restart_or_rework'),
        },
        'rollback': {
            'start': ('manual_rollback_execution_in_progress', 'wait_for_manual_rollback_completion_or_failure_confirmation'),
            'complete': ('manual_rollback_execution_completed_pending_registration', 'record_manual_rollback_registration'),
            'fail': ('manual_rollback_execution_failed', 'keep_rollback_closed_until_manual_recovery'),
            'abort': ('manual_rollback_execution_aborted', 'keep_rollback_closed_until_manual_restart_or_rework'),
        },
    }
    blocker_map = {
        'release': {'fail': ['manual_release_execution_failed'], 'abort': ['manual_release_execution_aborted']},
        'rollback': {'fail': ['manual_rollback_execution_failed'], 'abort': ['manual_rollback_execution_aborted']},
    }
    pipeline_state, next_step = state_map[target][action]
    blockers = blocker_map[target].get(action, [])
    return {
        'task_id': task_id,
        'pipeline_state': pipeline_state,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'official_release_executable': False,
        'ready_signals': ready_signals,
        'blockers': blockers,
        'blocker_count': len(blockers),
        'official_release_state': state_map[target][action][0],
        'next_step': next_step,
        'note': 'Manual execution confirmation has been recorded. The system still does not execute release or rollback automatically; registration remains a separate human step.',
    }


def confirm_execution(*, action: str, target: str, task_dir: str | Path | None = None, task_id: str | None = None, jobs_root: str | Path = JOBS_ROOT, confirmed_by: str = 'human', note: str = '') -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    task_name = resolved_task_dir.name
    artifacts_dir = resolved_task_dir / 'artifacts'
    manager = ArtifactManager(resolved_task_dir)
    closure_snapshot = load_release_closure_snapshot(resolved_task_dir)
    plan, precheck, existing_status = _load_target_artifacts(resolved_task_dir, target)
    run_context = extract_run_context_from_plan(plan, target)
    _validate_target_transition(target=target, action=action, closure_snapshot=closure_snapshot, precheck=precheck, status=existing_status, task_dir=resolved_task_dir, run_context=run_context)

    record = _build_record(task_id=task_name, target=target, action=action, confirmed_by=confirmed_by, note=note, status_before=existing_status, precheck=precheck, closure_snapshot=closure_snapshot, run_context=run_context)
    status = _build_status(task_id=task_name, target=target, action=action, confirmed_by=confirmed_by, note=note, existing=existing_status, run_context=run_context)

    existing_state = _load_json(artifacts_dir / 'official_release_state_placeholder.json')
    existing_summary = _load_json(artifacts_dir / 'official_release_pipeline_summary.json')
    release_state = _build_release_state(task_id=task_name, target=target, action=action, existing_state=existing_state, status=status, run_context=run_context)
    pipeline_summary = _build_pipeline_summary(task_id=task_name, target=target, action=action, existing_summary=existing_summary, closure_snapshot=closure_snapshot, status=status, run_context=run_context)

    manager.write_json(TARGET_CONFIG[target]['record_artifact'], record)
    manager.write_json(TARGET_CONFIG[target]['status_artifact'], status)
    manager.write_json('official_release_state_placeholder.json', release_state)
    manager.write_json('official_release_pipeline_summary.json', pipeline_summary)
    manager.append_log('manual_execution_confirmation_runtime.log', json.dumps({
        'time': _now(),
        'task_id': task_name,
        'target': target,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'action': action,
        'confirmed_by': confirmed_by,
        'confirmation_state': status.get('confirmation_state'),
        'note': note,
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)

    refreshed = load_release_closure_snapshot(resolved_task_dir)
    return {
        'task_id': task_name,
        'execution_target': TARGET_CONFIG[target]['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'action': action,
        'confirmation_state': status.get('confirmation_state'),
        'official_release_state': refreshed.get('official_release_state'),
        'official_release_pipeline_state': refreshed.get('official_release_pipeline_state'),
        'release_execution_confirmation_state': refreshed.get('release_execution_confirmation_state'),
        'rollback_execution_confirmation_state': refreshed.get('rollback_execution_confirmation_state'),
        'next_step': status.get('next_step'),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    for action in ('start', 'complete', 'fail', 'abort'):
        p = sub.add_parser(action)
        p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
        p.add_argument('--task-dir', default='')
        p.add_argument('--task-id', default='')
        p.add_argument('--jobs-root', default=str(JOBS_ROOT))
        p.add_argument('--confirmed-by', default='human')
        p.add_argument('--note', default='')

    args = parser.parse_args()
    result = confirm_execution(action=args.action, target=args.target, task_dir=args.task_dir or None, task_id=args.task_id or None, jobs_root=args.jobs_root, confirmed_by=args.confirmed_by, note=args.note)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
